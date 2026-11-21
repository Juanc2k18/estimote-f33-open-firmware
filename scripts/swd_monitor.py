#!/usr/bin/env python3
"""Reads the measurements of the F3.3 r45c app over (wired) SWD without halting the CPU.

The app leaves an `f33_status` structure in RAM ("F33S", RESETREAS, counter and the
last 31-byte packet, the same format as BLE). This script locates it by
searching for the marker, reads it every `--interval` s and logs every new measurement.
If SWD is lost (board without power) it retries; if the counter starts
over, a boot is logged with its cause (RESETREAS).

Does not write to the board. Does not need Bluetooth. The Pico SWD lines (3.3 V)
stay connected: when the supply is lowered they can partly power the board
through the protection diodes, so the shutdown threshold measured over SWD
may differ somewhat from the real one without cables.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f33_packet as fp

MAGIC=0x53333346;RAM=0x20003000;SEARCH=0x800;SIZE=12+fp.LAYOUT.size
RESETREAS={0:'RESETPIN',1:'DOG',2:'SREQ',3:'LOCKUP',16:'OFF',17:'LPCOMP',18:'DIF',19:'NFC'}


def now():return datetime.now().astimezone().isoformat(timespec='milliseconds')


def reasons(v):
    names=[n for b,n in RESETREAS.items() if v>>b&1]
    return names or ['POR/BOR']   # no bits: power-on or brown-out


def locate(t):
    block=bytes(t.read_memory_block8(RAM,SEARCH))
    for off in range(0,SEARCH-SIZE,4):
        if struct.unpack_from('<I',block,off)[0]==MAGIC:return RAM+off
    return None


def read_status(t,addr):
    for _ in range(3):
        raw=bytes(t.read_memory_block8(addr,SIZE))
        magic,rr,count=struct.unpack_from('<III',raw)
        if magic!=MAGIC:return None
        if t.read32(addr+8)==count:return rr,count,raw[12:]
    return None


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--duration',type=float,default=300)
    ap.add_argument('--interval',type=float,default=0.25)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--note',default='')
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    from pyocd.core.helpers import ConnectHelper
    out=None
    if a.out:a.out.mkdir(parents=True,exist_ok=True);out=(a.out/'samples.jsonl').open('w')
    result=dict(tool='swd_monitor',started=now(),note=a.note,samples=0,events=[])
    def event(**kw):
        kw={'t':now()}|kw;result['events'].append(kw);print(json.dumps(kw,ensure_ascii=False),flush=True)
    end=time.monotonic()+a.duration;last=None;swd_ok=None
    try:
        while time.monotonic()<end:
            try:
                with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options={
                        'target_override':'nrf52','connect_mode':'attach','frequency':1000000,
                        'resume_on_disconnect':True}) as s:
                    t=s.target;addr=locate(t)
                    if addr is None:raise RuntimeError('f33_status not found (app older than r45c?)')
                    if swd_ok is not True:event(kind='swd_ok',status_addr=hex(addr));swd_ok=True
                    while time.monotonic()<end:
                        st=read_status(t,addr)
                        if st is None:raise RuntimeError('invalid structure (restart?)')
                        rr,count,pkt=st
                        if last is None or count<last[1] or rr!=last[0]:
                            event(kind='boot' if last is not None else 'first',resetreas=hex(rr),reasons=reasons(rr),count=count)
                        if count==0:time.sleep(a.interval);continue   # just booted: packet still empty
                        if last is None or count!=last[1]:
                            d=fp.decode(pkt)|{'t':now(),'count':count}
                            result['samples']+=1
                            if out:out.write(json.dumps(d,ensure_ascii=False)+'\n');out.flush()
                            adc=d.get('adc',{})
                            print(f"{d['t'][11:23]} #{count:<5} VDD {adc.get('vdd_v',0):.3f} V · AIN3 {adc.get('ain3_v',0):.3f} V"
                                  f" · bat≈{adc.get('battery_v_estimate',0):.2f} V {adc.get('battery_percent','?')} %",flush=True)
                        last=(rr,count);time.sleep(a.interval)
            except KeyboardInterrupt:raise
            except Exception as exc:
                if swd_ok is not False:event(kind='swd_lost',error=repr(exc)[:200]);swd_ok=False
                time.sleep(0.5)
    except KeyboardInterrupt:event(kind='interrupted')
    finally:
        if out:out.close()
        result['finished']=now()
        if a.out:(a.out/'result.json').write_text(json.dumps(result,indent=1,ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k!='events'},ensure_ascii=False))
    return 0


if __name__=='__main__':raise SystemExit(main())
