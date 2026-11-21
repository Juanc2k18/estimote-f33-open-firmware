#!/usr/bin/env python3
"""Watches the frequency of a GPIO (and optionally an AIN) for N seconds.

Typical use: check whether GPIO17 (~35 Hz in r31/r32) changes with light. While it
runs, the owner alternates covered/flashlight and notes the time; the log stores
one sample per window with local time. Read-only: the pin stays an input without
pull; from RAM, no flash/UICR; reset on close (ActiveBoard).
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from board_diagnostics import Journal,session_options,snapshot
import rail_survey as rs


def watch(board,counter,emit,pin,seconds,gate,rail,clock=time.monotonic):
    if rail:
        levels=board.rail_set(True,pins=rs.STATES[rail][0]);emit(kind='rail_on',state=rail,levels=levels)
    end=clock()+seconds;rows=[]
    while clock()<end:
        row=counter.count_pin(pin,gate);rows.append(row)
        emit(kind='window',**row)
        print(f"{datetime.now().strftime('%H:%M:%S')} GPIO{pin}: {row['rising_edges']} edges ≈ {row['hz_estimate']} Hz",flush=True)
    if rail:board.rail_set(False);emit(kind='rail_off')
    hz=[r['hz_estimate'] for r in rows if r['hz_estimate'] is not None]
    summary=dict(windows=len(rows),hz_min=min(hz) if hz else None,hz_max=max(hz) if hz else None)
    emit(kind='watch_summary',pin=pin,**summary)
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--pin',type=int,default=17)
    ap.add_argument('--seconds',type=float,default=60)
    ap.add_argument('--gate',type=float,default=1.0)
    ap.add_argument('--rail',choices=sorted(rs.STATES),help='hold a rail state during the watch')
    ap.add_argument('--supply',default='not stated')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--frequency',type=int,default=100000)
    a=ap.parse_args(argv)
    if a.pin in rs.NEVER|set(rs.RAIL)|{0,1}:ap.error('pin not allowed')
    if not (math.isfinite(a.seconds) and 0<a.seconds<=600 and 0.05<=a.gate<=5):ap.error('seconds 0–600, gate 0,05–5')
    if a.rail=='all':ap.error('all is not supported by the r31 topology')
    journal=Journal(a.out);status='incomplete';code=1
    try:
        journal.emit(kind='parameters',pin=a.pin,seconds=a.seconds,gate=a.gate,rail=a.rail,supply=a.supply)
        from pyocd.core.helpers import ConnectHelper
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=session_options('auto',a.frequency)) as s:
            if s is None:raise RuntimeError('Pico not available')
            journal.emit(kind='baseline',**snapshot(s.target))
            with rs.RailBoard(s.target,journal.emit) as board:
                counter=rs.EdgeCounter(board)
                control=counter.control_pull_toggle(18);journal.emit(kind='counter_control',**control)
                if not control['valid']:raise RuntimeError('counter control failed')
                watch(board,counter,journal.emit,a.pin,a.seconds,a.gate,a.rail)
                counter.stop()
        status='complete';code=0
    except KeyboardInterrupt:journal.emit(kind='interrupted');status='interrupted';code=130
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:journal.finish(status)
    return code


if __name__=='__main__':raise SystemExit(main())
