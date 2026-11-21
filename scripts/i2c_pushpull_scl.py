#!/usr/bin/env python3
"""I²C with SCL in push-pull: tests pairs rejected by the OD matrix.

Reason (r32–r34): GPIO17 sits at an intermediate voltage and reads 0/1 at random, so
as an OD line it never passes the electrical validation. On the UWB I1.2 the M41T62
RTC has SDA/SCL adjacent to its IRQ; on the F3.3 the IRQ goes to P0.19 (pin
22), whose neighbours are P0.16/17/18/20 (pins 19/20/21/23).

The M41T62, the LIS2DH12 and the BMP280 do not stretch the clock: the master can
drive SCL high and low. SDA stays open drain with the internal pull-up,
and only SDA has to pass the electrical validation. From RAM (RailBoard), no
flash/UICR; reset on close.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd
import rail_survey as rs

P=bd.P
NEIGHBOURS=[16,18,20]       # r35: 17 has an external driver; input only
WIDE=[2,8,9,10,16,18,20,23,24,26,27,28,29,30,31]
ADDRESSES=[0x68,0x18,0x19,0x50,0x76,0x77]


class PushPullSCL:
    """io for I2CProbe: SDA OD + internal pull-up; SCL driven H0H1 output."""
    def __init__(self,active,pins):
        self.a=active;self.t=active.t;self.sda,self.scl=pins;self.pins=pins
        active.configure(self.sda,rs.CNF_PU);self.t.write32(P+0x50c,1<<self.sda)
        self.t.write32(P+0x508,1<<self.scl);active.configure(self.scl,rs.CNF_OUT_H0H1)
    def low(self,p):
        if p==self.scl:self.t.write32(P+0x50c,1<<p)
        else:self.t.write32(P+0x518,1<<p)
    def release(self,p):
        if p==self.scl:self.t.write32(P+0x508,1<<p)
        else:self.t.write32(P+0x51c,1<<p)
    def sample(self):
        v=self.t.read32(P+0x510);return {p:(v>>p)&1 for p in self.pins}


@contextmanager
def pushpull_lines():
    """scan_i2c builds SWDLines internally; it is replaced during the sweep."""
    original=bd.SWDLines;bd.SWDLines=PushPullSCL
    try:yield
    finally:bd.SWDLines=original


def pairs_for(candidates,scl_only=None):
    scls=scl_only or candidates
    return [(sda,scl) for sda,scl in itertools.permutations(candidates,2) if scl in scls]


def run(board,emit,deadline,states,pairs,addresses):
    complete=True
    topo=rs.rail_topology(board,emit)
    for state in states:
        phase='rail_off' if state=='off' else f'rail_{state}'
        if state!='off':
            if not rs.state_allowed(state,topo):emit(kind='skipped',test=phase,reason='topology');continue
            levels=board.rail_set(True,pins=rs.STATES[state][0]);board.sleep(.2)
            emit(kind='rail_on',phase=phase,levels=levels)
        emit(kind='pp_phase',phase=phase,pairs=pairs,addresses=addresses)
        with pushpull_lines():
            ok=bd.scan_i2c(board,pairs,addresses,lambda **e:emit(phase=phase,mode='scl_push_pull',**e),deadline)
        complete=complete and ok
        if state!='off':board.rail_set(False);board.sleep(.2);emit(kind='rail_off',phase=phase)
    return complete


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python3 scripts/i2c_pushpull_scl.py --plan
  python3 scripts/i2c_pushpull_scl.py --supply "3,3 V C/F" --out docs/evidence/i2c-pp-r35-2026-11-19
  python3 scripts/i2c_pushpull_scl.py --wide --supply "3,3 V C/F" --out NEW_PATH''')
    ap.add_argument('--pins',default=','.join(map(str,NEIGHBOURS)),help='SDA/SCL candidates (nRF GPIOs)')
    ap.add_argument('--wide',action='store_true',help='use every GPIO not stuck low as a candidate')
    ap.add_argument('--states',default='off,15,14',help='off, 14, 15, 67')
    ap.add_argument('--addresses',default=','.join(hex(x) for x in ADDRESSES))
    ap.add_argument('--supply',default='not stated')
    ap.add_argument('--max-seconds',type=float,default=900)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--frequency',type=int,default=100000)
    ap.add_argument('--uart-port',default='/dev/cu.usbmodem21202')
    ap.add_argument('--plan',action='store_true')
    a=ap.parse_args(argv)
    try:
        pins=WIDE if a.wide else [int(x,0) for x in a.pins.split(',')]
        bad=set(pins)&(rs.NEVER|set(rs.RAIL)|rs.DRIVE_GUARD|rs.RISKY|{3,4,5,17,22,25})
        if bad or len(set(pins))!=len(pins) or len(pins)<2:raise ValueError(f'pins not allowed or repeated: {sorted(bad)}')
        states=[s.strip() for s in a.states.split(',')]
        if any(s not in ('off','14','15','67') for s in states):raise ValueError('--states: off,14,15,67')
        addresses=[int(x,0) for x in a.addresses.split(',')]
        if any(not 8<=x<120 for x in addresses):raise ValueError('addresses 0x08..0x77')
        if not math.isfinite(a.max_seconds) or a.max_seconds<=0:raise ValueError('--max-seconds')
    except ValueError as exc:ap.error(str(exc))
    pairs=pairs_for(pins)
    plan=dict(tool='i2c_pushpull_scl',supply=a.supply,pins=pins,pairs=len(pairs),states=states,
              addresses=addresses,scl='push-pull H0H1',sda='OD + internal pull-up',max_seconds=a.max_seconds)
    if a.plan:print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    out=a.out or Path('docs/evidence')/('i2c-pp-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    journal=bd.Journal(out);status='incomplete';code=1
    try:
        journal.emit(kind='parameters',**plan)
        busy=subprocess.run(['lsof','-t',a.uart_port,a.uart_port.replace('/cu.','/tty.')],capture_output=True,text=True)
        if busy.stdout.strip():raise RuntimeError('UART busy; stop the monitor first')
        from pyocd.core.helpers import ConnectHelper
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=bd.session_options('auto',a.frequency)) as s:
            if s is None:raise RuntimeError('Pico not available')
            journal.emit(kind='baseline',**bd.snapshot(s.target))
            with rs.RailBoard(s.target,journal.emit) as board:
                if not run(board,journal.emit,bd.Deadline(a.max_seconds),states,pairs,addresses):
                    raise RuntimeError('incomplete sweep; check the log')
        status='complete';code=0
    except KeyboardInterrupt:journal.emit(kind='interrupted');status='interrupted';code=130
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:
        summary=journal.finish(status)
        acks=[e for e in journal.events if e['kind'] in ('i2c_candidate','identification','rtc')]
        print(json.dumps(dict(output=str(out.resolve()),status=status,findings=len(acks),counts=summary['counts']),ensure_ascii=False))
    return code


if __name__=='__main__':raise SystemExit(main())
