#!/usr/bin/env python3
"""Puts the Adafruit bootloader into DFU OTA (BLE "AdaDFU") and watches the radio over SWD.

Mechanism: the Adafruit bootloader reads NRF_POWER->GPREGRET at boot; the value
0xA8 (DFU_MAGIC_OTA_RESET) requests DFU over BLE. GPREGRET survives a software
reset (SYSRESETREQ). Does not write flash or UICR; does not load code into RAM.

After the reset it only reads registers without halting the CPU: GPREGRET (the
bootloader clears it when consuming it), RADIO->STATE and the RADIO frequency. If the radio
is transmitting, STATE should be TX (11) and FREQUENCY 2/26/80 (channels 37/38/39).
The device keeps advertising until the next reset or power-off.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd

GPREGRET=0x4000051C
RADIO=0x40001000
STATE,FREQ,TXPOWER,PCNF0=RADIO+0x550,RADIO+0x508,RADIO+0x50C,RADIO+0x514
OTA_MAGIC=0xA8
STATES={0:'Disabled',1:'RxRu',2:'RxIdle',3:'Rx',4:'RxDisable',9:'TxRu',10:'TxIdle',11:'Tx',12:'TxDisable'}


def sample_radio(target,seconds,clock=time.monotonic,pause=.002):
    states=Counter();freqs=Counter();tx_power=Counter();n=0
    end=clock()+seconds
    while clock()<end:
        s=target.read32(STATE)&0xF;states[STATES.get(s,str(s))]+=1;n+=1
        if s:freqs[target.read32(FREQ)&0x7F]+=1;tx_power[target.read32(TXPOWER)&0xFF]+=1
        time.sleep(pause)
    return dict(samples=n,states=dict(states),frequencies=dict(freqs),tx_power_raw=dict(tx_power),
                active_fraction=round(1-states['Disabled']/n,4) if n else None,
                advertising_channels=sorted(f for f in freqs if f in (2,26,80)))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--seconds',type=float,default=5)
    ap.add_argument('--supply',default='not stated')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--frequency',type=int,default=100000)
    a=ap.parse_args(argv)
    out=a.out or Path('docs/evidence')/('ble-ota-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    journal=bd.Journal(out);status='incomplete';code=1;result=None
    try:
        journal.emit(kind='parameters',seconds=a.seconds,supply=a.supply,magic=hex(OTA_MAGIC))
        from pyocd.core.helpers import ConnectHelper
        from pyocd.core.target import Target
        opts=bd.session_options('auto',a.frequency)|{'resume_on_disconnect':True}
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=opts) as s:
            if s is None:raise RuntimeError('Pico not available')
            t=s.target;journal.emit(kind='baseline',**bd.snapshot(t))
            before=sample_radio(t,1.0);journal.emit(kind='radio_before',**before)
            t.halt();t.write32(GPREGRET,OTA_MAGIC)
            journal.emit(kind='gpregret_set',value=hex(t.read32(GPREGRET)&0xFF))
            t.reset(Target.ResetType.SYSRESETREQ);time.sleep(.5)
            after=dict(gpregret=hex(t.read32(GPREGRET)&0xFF),pc_sample=hex(t.read_core_register('pc')) if t.is_halted() else 'running')
            result=sample_radio(t,a.seconds)|after
            journal.emit(kind='radio_after',**result)
        status='complete';code=0
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:
        journal.finish(status)
        print(json.dumps(dict(output=str(out.resolve()),status=status,radio=result),ensure_ascii=False))
    return code


if __name__=='__main__':raise SystemExit(main())
