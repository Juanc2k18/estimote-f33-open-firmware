#!/usr/bin/env python3
"""I²C on P0.14/P0.15 with the {6,7} rail on or off (r36 hypothesis).

Owner report (r36): RTC1/SDA has continuity with pin ~17
of the nRF (P0.14), perhaps 16 (P0.13, already E1/TX) or 18 (P0.15). Reinterpretation
of the r31 topology: 14 or 15 high pull up {6,7} but not the other way round. That fits
14/15 being **SDA/SCL** and {6,7} the **sensor power/pull-ups**:
a line held high powers the rail through the pull-ups or the sensors' ESD diodes,
and the rail does not pull the line up because the diode blocks that direction.
Until now 14/15 had only been used as "enables", never as a bus.

States: off (6/7 with pull-down), 67 (6 and 7 high with H0H1). For each state and
orientation (SDA14/SCL15 and SDA15/SCL14): open drain with internal pull-up and,
separately, SCL in push-pull. Full 0x08–0x77 sweep on W; ACKs are validated
3× with controls and identified (sensor ID or RTC reading).
From RAM, no flash/UICR; reset on close. 12/13 (UART) and 21 are not touched.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd
import i2c_pushpull_scl as pp
import rail_survey as rs

PAIRS=[(14,15),(15,14)]
STATE_PINS={'off':(),'67':(6,7)}


def run(board,emit,deadline,states,modes,addresses):
    complete=True
    for state in states:
        phase=f'rail_{state}'
        for p in rs.RAIL:board.configure(p,rs.CNF_PD)
        board.sleep(.05)
        if STATE_PINS[state]:
            levels=board.rail_set(True,pins=STATE_PINS[state]);board.sleep(.3)
            emit(kind='rail_on',phase=phase,levels=levels)
            if not (levels[6] and levels[7]):raise RuntimeError(f'rail 6/7 does not reach high: {levels}')
        else:
            for p in (14,15):board.configure(p,rs.CNF_IN)
            emit(kind='rail_off',phase=phase,levels={p:(board.gpio_in()>>p)&1 for p in rs.RAIL})
        for mode in modes:
            label=dict(phase=phase,mode=mode)
            if mode=='push_pull':
                with pp.pushpull_lines():ok=bd.scan_i2c(board,PAIRS,addresses,lambda **e:emit(**label,**e),deadline)
            else:ok=bd.scan_i2c(board,PAIRS,addresses,lambda **e:emit(**label,**e),deadline)
            complete=complete and ok
        if STATE_PINS[state]:board.rail_set(False);board.sleep(.2)
    return complete


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example:\n  python3 scripts/i2c_rail_bus.py --supply "3,3 V C/F" --out docs/evidence/i2c-14-15-r36-2026-11-19')
    ap.add_argument('--states',default='67,off')
    ap.add_argument('--modes',default='od,push_pull')
    ap.add_argument('--addresses',default='all',help="'all' = 0x08–0x77, or a comma-separated list")
    ap.add_argument('--supply',default='not stated')
    ap.add_argument('--max-seconds',type=float,default=900)
    ap.add_argument('--out',type=Path)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--frequency',type=int,default=100000)
    ap.add_argument('--uart-port',default='/dev/cu.usbmodem21202')
    ap.add_argument('--plan',action='store_true')
    a=ap.parse_args(argv)
    try:
        states=[x.strip() for x in a.states.split(',')]
        modes=[x.strip() for x in a.modes.split(',')]
        if any(s not in STATE_PINS for s in states) or len(set(states))!=len(states):raise ValueError('--states: 67, off')
        if any(m not in ('od','push_pull') for m in modes):raise ValueError('--modes: od, push_pull')
        addresses=list(range(8,120)) if a.addresses=='all' else [int(x,0) for x in a.addresses.split(',')]
        if any(not 8<=x<120 for x in addresses):raise ValueError('addresses 0x08..0x77')
        if not math.isfinite(a.max_seconds) or a.max_seconds<=0:raise ValueError('--max-seconds')
    except ValueError as exc:ap.error(str(exc))
    plan=dict(tool='i2c_rail_bus',supply=a.supply,pairs=PAIRS,states=states,modes=modes,
              addresses=f'{len(addresses)} ({hex(addresses[0])}–{hex(addresses[-1])})',max_seconds=a.max_seconds)
    if a.plan:print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    out=a.out or Path('docs/evidence')/('i2c-14-15-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
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
                if not run(board,journal.emit,bd.Deadline(a.max_seconds),states,modes,addresses):
                    raise RuntimeError('incomplete sweep; check the log')
        status='complete';code=0
    except KeyboardInterrupt:journal.emit(kind='interrupted');status='interrupted';code=130
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:
        summary=journal.finish(status)
        found=[dict(phase=e.get('phase'),mode=e.get('mode'),sda=e.get('sda'),scl=e.get('scl'),address=hex(e['address']),status=e['status'])
               for e in journal.events if e['kind']=='i2c_candidate']
        print(json.dumps(dict(output=str(out.resolve()),status=status,candidates=found,counts=summary['counts']),ensure_ascii=False))
    return code


if __name__=='__main__':raise SystemExit(main())
