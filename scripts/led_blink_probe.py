#!/usr/bin/env python3
"""Identifies the LED pin: slow blinking on P0.17 and fast on P0.19, over SWD.

Halts the CPU, disables PWM0 (the bootloader uses it on 17/19) and toggles the
pins with OUTSET/OUTCLR from the host. No flash/UICR and no code in RAM. At the end,
SYSRESETREQ reset: the bootloader recovers its configuration. P0.19 is the RTC
IRQ (open drain, OUT=1 → high impedance), so it is only used as a control.
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd

P=0x50000000;PWM0=0x4001C000
PHASES=[(17,4.0,12),(19,4.0,12)]   # (pin, period s, duration s): 3 flashes of 2 s


def blink(t,pin,period,seconds,emit):
    t.write32(P+0x50c,1<<pin);t.write32(P+0x700+4*pin,1)
    emit(kind='phase_start',pin=pin,period=period,seconds=seconds,local=datetime.now().astimezone().isoformat(timespec='seconds'))
    end=time.monotonic()+seconds;n=0;levels=[]
    while time.monotonic()<end:
        t.write32(P+(0x508 if n%2==0 else 0x50c),1<<pin);time.sleep(period/2)
        levels.append((t.read32(P+0x510)>>pin)&1);n+=1
    t.write32(P+0x50c,1<<pin)
    emit(kind='phase_end',pin=pin,toggles=n,in_samples=levels)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--delay',type=float,default=10)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    a=ap.parse_args(argv)
    j=bd.Journal(a.out);status='incomplete'
    try:
        from pyocd.core.helpers import ConnectHelper
        from pyocd.core.target import Target
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=bd.session_options('auto',100000)|{'resume_on_disconnect':True}) as s:
            t=s.target;j.emit(kind='baseline',**bd.snapshot(t))
            # Dark from the start: the bootloader blinking is not confused with the phases.
            t.halt();t.write32(PWM0+0x500,0)
            for pin in (17,19):t.write32(P+0x50c,1<<pin);t.write32(P+0x700+4*pin,1)
            j.emit(kind='pwm0_disabled',enable=t.read32(PWM0+0x500))
            print(f'Bootloader LED stopped; starting in {a.delay:g} s',flush=True);time.sleep(a.delay)
            for i,(pin,period,secs) in enumerate(PHASES):
                if i:time.sleep(5)
                print(f'Phase P0.{pin}: period {period} s',flush=True);blink(t,pin,period,secs,j.emit)
            t.reset(Target.ResetType.SYSRESETREQ);time.sleep(.5)
            j.emit(kind='after_reset',pwm0_enable=t.read32(PWM0+0x500),halted=t.is_halted())
        status='complete'
    except Exception as exc:j.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:j.finish(status)
    return 0 if status=='complete' else 1


if __name__=='__main__':raise SystemExit(main())
