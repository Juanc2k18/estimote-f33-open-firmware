#!/usr/bin/env python3
"""Switched 6/7/14/15 rail, OD matrix per state, per-GPIO frequency and LFCLK.

Hypothesis to test (audit 2026-11-19): P0.06/07/14/15 form a single
low-impedance node that powers the sensors; the real SDA/SCL stay stuck
low with that rail off, and that is why the historical matrix excluded them.

Phases, all from a loop in RAM (no flash/UICR; reset on close):
  1. topology   each rail pin high separately; do the other three rise?
  2. rail_off   per-GPIO frequency, LFCLK test, SAADC and OD matrix.
  3. rail_on    the four outputs high (H0H1) at the same time, only if topology
                shows a single node; repeats frequency, LFCLK, SAADC, matrix
                and sweeps I²C on pairs with at least one "new" pin (invalid without
                the rail, valid with it), unless --all-pairs.
Counter: GPIOTE IN[0] → PPI CH0 → TIMER1 in counter mode. Positive control:
toggle pull-up/pull-down over SWD on a GPIO that follows the pulls (19 by
default, the RTC IRQ; pulls only, never output).
"""
import argparse
from datetime import datetime
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from board_diagnostics import (ActiveBoard,Deadline,Journal,P,gpio_survey,scan_i2c,
                               session_options,snapshot)

RAIL=(6,7,14,15)
NEVER={12,13,21}            # UART to the Pico and nRESET
DRIVE_GUARD={0,1,19}        # crystal/LF and RTC IRQ: input only
RISKY={11}                  # lost SWD in r25/r29; only with --include-11
DEFAULT_ADDRESSES=[0x18,0x19,0x29,0x39,0x44,0x48,0x50,0x51,0x52,0x53,0x54,0x55,0x56,0x57,0x68,0x76,0x77]
CNF_IN,CNF_PD,CNF_PU,CNF_OUT,CNF_OUT_H0H1=0,4,12,1,0x301
CNF_DISCONNECT=2
GPIOTE=0x40006000;TIMER1=0x40009000;PPI=0x4001F000;CLOCK=0x40000000;RTC2=0x40024000


class RailBoard(ActiveBoard):
    """ActiveBoard with its own reservations; the rail is not released between tests."""
    def __init__(self,target,emit,sleep=time.sleep,allow=()):
        super().__init__(target,emit,sleep);self.rail_on=False;self.rail_pins=();self.allow=set(allow)
    def configure(self,pin,value):
        if pin in NEVER:raise ValueError(f'GPIO{pin} is never touched')
        guarded=DRIVE_GUARD|(RISKY-self.allow)
        if pin in guarded and value&1:raise ValueError(f'GPIO{pin} only as an input')
        if self.rail_on and pin in self.rail_pins:raise ValueError('rail on: do not reconfigure its driven pins')
        self.pins.add(pin);self.t.write32(P+0x700+4*pin,value)
    def release(self):
        # The rail pins are managed only with rail_topology/rail_set.
        for pin in sorted(self.pins-set(RAIL)):self.t.write32(P+0x700+pin*4,0)
    def rail_set(self,on,pins=RAIL,settle=.05):
        if on:
            self.t.write32(P+0x508,sum(1<<p for p in pins))
            for p in pins:self.pins.add(p);self.t.write32(P+0x700+4*p,CNF_OUT_H0H1)
            self.rail_on=True;self.rail_pins=tuple(pins)
        else:
            self.rail_on=False;self.rail_pins=()
            for p in RAIL:self.t.write32(P+0x700+4*p,CNF_PD)
        self.sleep(settle)
        raw=self.t.read32(P+0x510)
        return {p:(raw>>p)&1 for p in RAIL}
    def gpio_in(self):return self.t.read32(P+0x510)


def rail_topology(board,emit,settle=.02):
    """One rail pin high (S0H1, limited current) and the others with pull-down."""
    rows=[];single=True
    for p in RAIL:board.configure(p,CNF_PD)
    board.sleep(settle);idle=board.gpio_in();idle_bits={q:(idle>>q)&1 for q in RAIL}
    for p in RAIL:
        for q in RAIL:board.configure(q,CNF_PD)
        board.t.write32(P+0x508,1<<p);board.configure(p,CNF_OUT);board.sleep(settle)
        raw=board.gpio_in();others={q:(raw>>q)&1 for q in RAIL if q!=p}
        board.configure(p,CNF_PD)
        follows=all(others.values());single=single and follows
        rows.append(dict(driven=p,others=others,all_follow=follows))
    for p in RAIL:board.configure(p,CNF_IN)
    emit(kind='rail_topology',idle_pull_down=idle_bits,rows=rows,single_node=single,
         interpretation='single low-impedance node' if single else 'not a single node: the full rail is not switched on')
    return {r['driven']:r['others'] for r in rows}


# Power states: pins to drive and node that must end up high.
# Never 14 and 15 at the same time unless topology shows a single node ('all').
STATES={'14':((14,),(6,7)),'15':((15,),(6,7)),'67':((6,7),(6,7)),'all':(RAIL,RAIL)}


def state_allowed(name,topo):
    drive,node=STATES[name]
    if name=='all':return all(all(v.values()) for v in topo.values())
    return all(topo[d].get(n,1)==1 for d in drive for n in node if n!=d)


class EdgeCounter:
    """GPIOTE IN[0] → PPI CH0 → TIMER1 COUNT. Window measured by the host."""
    def __init__(self,board):
        self.b=board;self.t=board.t
        t=self.t
        t.write32(PPI+0x508,1)                       # CHENCLR CH0
        t.write32(TIMER1+0x004,1);t.write32(TIMER1+0x504,1);t.write32(TIMER1+0x508,3)
        t.write32(PPI+0x514,TIMER1+0x008)            # TEP=TASKS_COUNT
    def _route(self,eep):
        self.t.write32(PPI+0x510,eep);self.t.write32(PPI+0x504,1)
    def _window(self,gate):
        t=self.t;t.write32(TIMER1+0x00c,1);t.write32(TIMER1,1)
        t0=time.monotonic();self.b.sleep(gate);t.write32(TIMER1+0x040,1);t1=time.monotonic()
        return t.read32(TIMER1+0x540),t1-t0
    def stop(self):
        t=self.t;t.write32(PPI+0x508,1);t.write32(TIMER1+0x004,1);t.write32(GPIOTE+0x510,0)
    def count_pin(self,pin,gate):
        t=self.t
        self.b.configure(pin,CNF_IN)
        t.write32(GPIOTE+0x100,0)
        t.write32(GPIOTE+0x510,1|(pin<<8)|(1<<16))   # event, rising edge
        self._route(GPIOTE+0x100)
        level=(self.b.gpio_in()>>pin)&1
        count,elapsed=self._window(gate)
        t.write32(GPIOTE+0x510,0);t.write32(PPI+0x508,1)
        # hz_estimate is only a frequency if the count scales with the window (r33):
        # a fixed burst when configuring the pin gives the same count with any gate.
        return dict(pin=pin,rising_edges=count,gate_s=round(elapsed,4),
                    hz_estimate=round(count/elapsed,1) if elapsed>0 else None,level_before=level)
    def control_pull_toggle(self,pin,toggles=20):
        """Positive control of the GPIOTE/PPI/TIMER path: N rising edges via pulls."""
        t=self.t
        self.b.configure(pin,CNF_PD);self.b.sleep(.005)
        t.write32(GPIOTE+0x100,0);t.write32(GPIOTE+0x510,1|(pin<<8)|(1<<16))
        self._route(GPIOTE+0x100)
        t.write32(TIMER1+0x00c,1);t.write32(TIMER1,1)
        for _ in range(toggles):
            self.b.configure(pin,CNF_PU);self.b.sleep(.003)
            self.b.configure(pin,CNF_PD);self.b.sleep(.003)
        t.write32(TIMER1+0x040,1);count=t.read32(TIMER1+0x540)
        t.write32(GPIOTE+0x510,0);t.write32(PPI+0x508,1);self.b.configure(pin,CNF_IN)
        return dict(pin=pin,toggles=toggles,rising_edges=count,valid=count==toggles)


def lf_state(t):
    stat=t.read32(CLOCK+0x418)
    return dict(lfclkstat=hex(stat),running=bool(stat>>16&1),src=stat&3,lfclksrc=hex(t.read32(CLOCK+0x518)))


def lf_stop(board,timeout=.5):
    t=board.t;t.write32(CLOCK+0x00c,1);end=time.monotonic()+timeout
    while time.monotonic()<end:
        if not t.read32(CLOCK+0x418)>>16&1:return True
        board.sleep(.01)
    return False


def lf_start(board,src,timeout=1.5):
    t=board.t;t.write32(CLOCK+0x104,0);t.write32(CLOCK+0x518,src);t.write32(CLOCK+0x008,1)
    end=time.monotonic()+timeout;start=time.monotonic()
    while time.monotonic()<end:
        if t.read32(CLOCK+0x104):return round(time.monotonic()-start,3)
        board.sleep(.01)
    return None


def rtc2_rate(board,gate=.5):
    """LFCLK frequency against the host clock, using RTC2 without prescaler."""
    t=board.t;t.write32(RTC2+0x004,1);t.write32(RTC2+0x508,0);t.write32(RTC2+0x008,1);t.write32(RTC2,1)
    a=t.read32(RTC2+0x504);t0=time.monotonic();board.sleep(gate)
    b=t.read32(RTC2+0x504);t1=time.monotonic();t.write32(RTC2+0x004,1)
    ticks=(b-a)&0xffffff
    return dict(ticks=ticks,gate_s=round(t1-t0,4),hz_estimate=round(ticks/(t1-t0),1) if t1>t0 else None)


def lfclk_probe(board,counter,emit,phase,gate):
    """Distinguishes a passive crystal from an external square wave (e.g. M41T62 SQW) on XL1."""
    t=board.t;result=dict(initial=lf_state(t))
    if not lf_stop(board):
        emit(kind='lfclk',phase=phase,status='incomplete',reason='LFCLK did not stop',**result);return False
    t.write32(CLOCK+0x518,0)                         # RC not started: XL1/XL2 return to GPIO
    result['xl_as_gpio']=[counter.count_pin(p,gate) for p in (0,1)]
    board.t.write32(P+0x700,CNF_DISCONNECT);board.t.write32(P+0x704,CNF_DISCONNECT)
    modes={'xtal':1,'external_bypass':1|1<<16|1<<17}
    for name,src in modes.items():
        started=lf_start(board,src)
        row=dict(started_s=started,state=lf_state(t))
        if started is not None:row['rate']=rtc2_rate(board)
        result[name]=row
        if not lf_stop(board):
            emit(kind='lfclk',phase=phase,status='incomplete',reason=f'did not stop after {name}',**result);return False
    t.write32(CLOCK+0x518,1);lf_start(board,1)
    xl1=result['xl_as_gpio'][0]['hz_estimate'] or 0
    ext=result['external_bypass'].get('rate',{}).get('hz_estimate') or 0
    near=lambda f:abs(f-32768)<0.05*32768
    if near(xl1) or near(ext):verdict='external ~32 kHz square wave on XL1 (consistent with the RTC SQW)'
    elif result['xtal'].get('started_s') is not None:verdict='consistent with a passive crystal: no edges on XL1 and no 32 kHz in bypass'
    else:verdict='undetermined'
    emit(kind='lfclk',phase=phase,status='complete',verdict=verdict,**result)
    return True


def analog(board,emit,phase):
    """SAADC VDD and AIN0–AIN7 (includes AIN1/AIN2 = P0.03/P0.04, skipped before)."""
    t=board.t;adc=0x40007000;rows=[]
    def wait(off):
        end=time.monotonic()+.3
        while time.monotonic()<end:
            if t.read32(adc+off):return
        raise TimeoutError('SAADC without event')
    pins={1:2,2:3,3:4,4:5,5:28,6:29,7:30,8:31,9:None}
    try:
        t.write32(adc+0x514,0);t.write32(adc+0x518,5<<16);t.write32(adc+0x5f0,2);t.write32(adc+0x500,1)
        t.write32(adc+0x110,0);t.write32(adc+0xc,1);wait(0x110)
        for ain,pin in pins.items():
            if pin is not None and pin in RAIL:continue
            if pin is not None:board.configure(pin,CNF_DISCONNECT)
            t.write32(adc+0x510,ain);t.write32(adc+0x62c,0x20005000);t.write32(adc+0x630,1)
            t.write32(adc+0x100,0);t.write32(adc+0x104,0);t.write32(adc,1);wait(0x100)
            t.write32(adc+4,1);wait(0x104)
            raw=int.from_bytes(bytes(t.read_memory_block8(0x20005000,2)),'little',signed=True)
            t.write32(adc+0x114,0);t.write32(adc+8,1);wait(0x114)
            rows.append(dict(pin=pin,source='VDD' if pin is None else f'AIN{ain-1}',raw=raw,mv=round(raw*3600/4096,1)))
            if pin is not None:board.configure(pin,CNF_IN)
    finally:t.write32(adc+0x500,0)
    emit(kind='analog',phase=phase,channels=rows)
    return rows


def slow_pull(board,pin,waits=(.005,.05,.3)):
    """Level with pull-up/pull-down after increasing waits: detects a slow RC or a held line."""
    out={}
    for name,cnf in (('pull_up',CNF_PU),('pull_down',CNF_PD)):
        board.configure(pin,cnf);row=[];last=0
        for w in waits:board.sleep(w-last);last=w;row.append((board.gpio_in()>>pin)&1)
        out[name]=row
    board.configure(pin,CNF_IN)
    return dict(pin=pin,waits_s=list(waits),**out)


def run_phase(board,counter,emit,deadline,phase,pins,freq_pins,gate,lfclk):
    deadline.check()
    emit(kind='phase',phase=phase,snapshot=snapshot(board.t))
    freqs=[]
    for p in freq_pins:
        deadline.check();row=counter.count_pin(p,gate);freqs.append(row);emit(kind='frequency',phase=phase,**row)
    for p in (17,19):
        deadline.check();emit(kind='slow_pull',phase=phase,**slow_pull(board,p))
    if lfclk:lfclk_probe(board,counter,emit,phase,gate)
    analog(board,emit,phase)
    eligible=gpio_survey(board,pins,lambda **e:emit(phase=phase,**e),deadline)
    emit(kind='matrix',phase=phase,eligible=eligible,tested=pins)
    return eligible,freqs


def choose_pairs(off,on,all_pairs):
    new=[p for p in on if p not in off]
    if all_pairs:return list(itertools.permutations(on,2)),new
    return [(a,b) for a,b in itertools.permutations(on,2) if a in new or b in new],new


def rail_report(journal,out):
    """Own summary: topology, control, LFCLK, frequencies >0 and matrix difference."""
    ev=journal.events;pick=lambda k:[e for e in ev if e['kind']==k]
    report=dict(topology=pick('rail_topology'),counter_control=pick('counter_control'),lfclk=pick('lfclk'),
                active_pins=[e for e in pick('frequency') if e.get('rising_edges')],
                matrix_diff=pick('matrix_diff'),analog=pick('analog'),
                i2c_ack=[e for e in ev if e['kind']=='i2c_address' and e.get('status')=='ack'],
                candidates=pick('i2c_candidate'),identification=pick('identification')+pick('rtc'),
                errors=pick('error'))
    (out/'rail_summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['','## Rail, frequency and LFCLK','']
    for e in report['topology']:lines.append(f"- Topology: single node={e['single_node']}; idle with pull-down {e['idle_pull_down']}")
    for e in report['counter_control']:lines.append(f"- Counter control GPIO{e['pin']}: {e['rising_edges']}/{e['toggles']} valid={e['valid']}")
    for e in report['lfclk']:lines.append(f"- LFCLK {e['phase']}: {e.get('verdict',e.get('reason'))}")
    for e in report['active_pins']:lines.append(f"- Edges {e['phase']} GPIO{e['pin']}: {e['rising_edges']} (~{e['hz_estimate']} Hz)")
    for e in pick('slow_pull'):lines.append(f"- Slow pull {e['phase']} GPIO{e['pin']}: up {e['pull_up']} down {e['pull_down']}")
    for e in report['matrix_diff']:lines.append(f"- Matrix {e.get('phase')}: new with rail {e['new_with_rail']}; lost with rail {e['lost_with_rail']}; pairs {e['pairs']}")
    for e in report['i2c_ack']:lines.append(f"- ACK SDA{e.get('sda')}/SCL{e.get('scl')}: `{json.dumps(e,ensure_ascii=False)}`")
    with (out/'report.md').open('a') as f:f.write('\n'.join(lines)+'\n')


def parser():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python3 scripts/rail_survey.py --plan
  python3 scripts/rail_survey.py --out docs/evidence/rail-r31-2026-11-19
  python3 scripts/rail_survey.py --skip-i2c --out NEW_PATH        # topology/frequency/matrix only

Requirements: stop the UART monitor; Pico SWD on A/B/F. Power supply: note it in the log
(--supply), e.g. "3.3 V C/F" or "6 V H/F". Numbers = nRF GPIOs, not pads.
Exit code: 0 complete (does not imply a finding), 1 incomplete, 2 CLI, 130 Ctrl-C.''')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--supply',required=False,default='not stated',help='power setup, stored as given')
    ap.add_argument('--include-11',action='store_true',help='include GPIO11 (lost SWD before)')
    ap.add_argument('--all-pairs',action='store_true',help='all valid pairs with the rail, not only the new ones')
    ap.add_argument('--skip-i2c',action='store_true')
    ap.add_argument('--no-lfclk',action='store_true',help='skip the crystal/SQW test on XL1')
    ap.add_argument('--gate',type=float,default=.25,help='counting window per pin, s')
    ap.add_argument('--control-pins',default='19,18',help='candidate GPIOs that follow the pulls (positive control); the first valid one is used')
    ap.add_argument('--addresses',default=','.join(hex(x) for x in DEFAULT_ADDRESSES))
    ap.add_argument('--max-seconds',type=float,default=1200)
    ap.add_argument('--frequency',type=int,default=100000)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--uart-port',default='/dev/cu.usbmodem21202')
    ap.add_argument('--states',default='14,15,67,all',help="power states in order: 14, 15, 67 (6+7), all (only if single node)")
    ap.add_argument('--plan',action='store_true')
    return ap


def selection(include11):
    blocked=NEVER|DRIVE_GUARD|set(RAIL)|(set() if include11 else RISKY)
    matrix=[p for p in range(32) if p not in blocked]
    freq=[p for p in range(32) if p not in NEVER|{0,1}|set(RAIL)]   # input only: 11 included
    return matrix,freq


def main(argv=None):
    ap=parser();a=ap.parse_args(argv)
    try:
        addresses=[int(x,0) for x in a.addresses.split(',')]
        if not addresses or len(set(addresses))!=len(addresses) or any(not 8<=x<120 for x in addresses):
            raise ValueError('unique addresses 0x08..0x77')
        if not (math.isfinite(a.gate) and 0.02<=a.gate<=2):raise ValueError('--gate between 0.02 and 2 s')
        states=[x.strip() for x in a.states.split(',') if x.strip()]
        if not states or any(x not in STATES for x in states) or len(set(states))!=len(states):
            raise ValueError('--states accepts 14, 15, 67, all without repeats')
        controls=[int(x,0) for x in a.control_pins.split(',')]
        if not controls or any(c in NEVER|set(RAIL)|{0,1} or not 0<=c<32 for c in controls):
            raise ValueError('control-pins not allowed')
        if not math.isfinite(a.max_seconds) or a.max_seconds<=0:raise ValueError('--max-seconds must be positive')
    except ValueError as exc:ap.error(str(exc))
    matrix,freq=selection(a.include_11)
    plan=dict(tool='rail_survey',supply=a.supply,rail=list(RAIL),never=sorted(NEVER),input_only=sorted(DRIVE_GUARD),
              matrix_pins=matrix,frequency_pins=freq,risky_excluded=[] if a.include_11 else sorted(RISKY),
              addresses=addresses,all_pairs=a.all_pairs,skip_i2c=a.skip_i2c,lfclk=not a.no_lfclk,
              gate_s=a.gate,control_pins=controls,states=states,max_seconds=a.max_seconds,probe=a.probe)
    if a.plan:print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    out=a.out or Path('docs/evidence')/('rail-survey-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    try:journal=Journal(out)
    except OSError as exc:ap.error(f'cannot create new directory: {exc}')
    status='incomplete';code=1
    try:
        journal.emit(kind='parameters',**plan)
        busy=subprocess.run(['lsof','-t',a.uart_port,a.uart_port.replace('/cu.','/tty.')],capture_output=True,text=True)
        if busy.stdout.strip():raise RuntimeError('UART busy; stop the monitor first')
        from pyocd.core.helpers import ConnectHelper
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=session_options('auto',a.frequency)) as s:
            if s is None:raise RuntimeError('Pico not available')
            t=s.target;journal.emit(kind='baseline',**snapshot(t));deadline=Deadline(a.max_seconds)
            allow={11} if a.include_11 else set()
            with RailBoard(t,journal.emit,allow=allow) as board:
                counter=EdgeCounter(board)
                for pin in controls:
                    control=counter.control_pull_toggle(pin);journal.emit(kind='counter_control',**control)
                    if control['valid']:break
                else:raise RuntimeError('positive counter control failed; do not interpret zeros')
                topo=rail_topology(board,journal.emit)
                off,_=run_phase(board,counter,journal.emit,deadline,'rail_off',matrix,freq,a.gate,not a.no_lfclk)
                complete=True
                for name in states:
                    phase=f'rail_{name}';drive,node=STATES[name]
                    if not state_allowed(name,topo):
                        journal.emit(kind='skipped',test=phase,reason='topology does not support this state');continue
                    levels=board.rail_set(True,pins=drive);board.sleep(.2)
                    journal.emit(kind='rail_on',phase=phase,levels=levels,drive='H0H1',pins=list(drive),node=list(node))
                    if not all(levels[n] for n in node):
                        board.rail_set(False);raise RuntimeError(f'{phase}: node does not reach high: {levels}')
                    on,_=run_phase(board,counter,journal.emit,deadline,phase,matrix,freq,a.gate,False)
                    pairs,new=choose_pairs(off,on,a.all_pairs)
                    journal.emit(kind='matrix_diff',phase=phase,valid_off=off,valid_on=on,new_with_rail=new,
                                 lost_with_rail=[p for p in off if p not in on],pairs=len(pairs))
                    print(f'{phase}: new pins {new}; I2C pairs {len(pairs)}',flush=True)
                    if not a.skip_i2c and pairs:
                        complete=scan_i2c(board,pairs,addresses,lambda **e:journal.emit(phase=phase,**e),deadline) and complete
                    levels={p:(board.gpio_in()>>p)&1 for p in RAIL}
                    journal.emit(kind='rail_check_end',phase=phase,levels=levels,held=all(levels[n] for n in node))
                    board.rail_set(False);board.sleep(.2);journal.emit(kind='rail_off',phase=phase)
                if not complete:raise RuntimeError('I2C incomplete; check the log')
                counter.stop()
        status='complete';code=0
    except KeyboardInterrupt:journal.emit(kind='interrupted');status='interrupted';code=130
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(str(exc),file=sys.stderr)
    finally:
        summary=journal.finish(status);rail_report(journal,out)
        print(json.dumps(dict(output=str(out.resolve()),status=status,counts=summary['counts']),ensure_ascii=False),flush=True)
    return code


if __name__=='__main__':raise SystemExit(main())
