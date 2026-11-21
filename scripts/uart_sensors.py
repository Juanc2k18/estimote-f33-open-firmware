#!/usr/bin/env python3
"""Reads the JSON lines of the F3.3 1.0.0 application over UART (E1/E2) and saves them.

Host with 3.3 V logic: a Mac with the Pico as a bridge (`/dev/cu.usbmodem…`) or a
Raspberry Pi (`/dev/serial0`). The board is powered through E3 at 3.3 V (verify logic-level margin against measured VDD), never at 5 V.
The board UART turns itself on, within the next second, when it sees E2 high
(host TX idle). The `--send` commands are sent after the first
data line, one every 3 s, preceded by '\\n' to discard earlier garbage.
Standard library only.
"""
import argparse
from datetime import datetime
import json
import math
import os
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dfu_ping import open_port, read_available


def now():return datetime.now().astimezone().isoformat(timespec='milliseconds')


class LineReader:
    """Splits a byte stream into text lines; discards those that are not UTF-8."""
    def __init__(self,limit=1024):self.buf=bytearray();self.limit=limit

    def feed(self,data:bytes)->list:
        self.buf.extend(data);lines=[]
        while b'\n' in self.buf:
            raw,_,rest=bytes(self.buf).partition(b'\n');self.buf=bytearray(rest)
            try:text=raw.decode().strip()
            except UnicodeDecodeError:continue
            if text:lines.append(text)
        if len(self.buf)>self.limit:self.buf.clear()
        return lines


def to_decoded(obj:dict)->dict:
    """UART data line → same format as f33_packet.decode (BLE packet)."""
    valid=dict(accel='acc_mg' in obj,magnet='mag_mg' in obj,baro='temp_cc' in obj,
               light='mlux' in obj,rtc='rtc_s' in obj,adc='vdd_mv' in obj)
    out=dict(version=1,seq=obj['seq'],valid=valid)
    if valid['accel']:
        g=[v/1000 for v in obj['acc_mg']];out['accel']=dict(g=g,norm_g=round(math.hypot(*g),3))
    if valid['magnet']:
        gs=[v/1000 for v in obj['mag_mg']];out['magnet']=dict(gauss=gs,norm_gauss=round(math.hypot(*gs),3))
    if valid['baro']:out['baro']=dict(temp_c=obj['temp_cc']/100,pressure_hpa=round(obj['press_pa']/100,2))
    if valid['light']:out['light']=dict(lux=obj['mlux']/1000)
    if valid['rtc']:out['rtc_seconds']=obj['rtc_s']
    if valid['adc']:out['adc']=dict(vdd_v=obj['vdd_mv']/1000,ain3_v=obj['ain3_mv']/1000,
                                    battery_v_estimate=obj['bat_mv']/1000,battery_percent=obj['bat_pct'])
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--port',default='/dev/cu.usbmodem1131202')
    ap.add_argument('--baud',type=int,default=115200)
    ap.add_argument('--duration',type=float,default=30)
    ap.add_argument('--send',action='append',default=[],help="command after the first line, e.g. 'int 5'")
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    result=dict(tool='uart_sensors',port=a.port,started=now(),samples=0,events=[])
    def event(**kw):
        kw={'t':now()}|kw;result['events'].append(kw);print(json.dumps(kw,ensure_ascii=False),flush=True)
    out=None
    if a.out:a.out.mkdir(parents=True,exist_ok=True);out=(a.out/'samples.jsonl').open('w')
    fd=open_port(a.port,a.baud);rd=LineReader();queue=list(a.send);next_send=None
    try:
        end=time.monotonic()+a.duration
        while time.monotonic()<end:
            if queue and next_send is not None and time.monotonic()>=next_send:
                cmd=queue.pop(0);os.write(fd,f'\n{cmd}\n'.encode());event(kind='sent',command=cmd)
                next_send=time.monotonic()+3
            for line in rd.feed(read_available(fd,min(end,time.monotonic()+0.2))):
                try:obj=json.loads(line)
                except ValueError:event(kind='not_json',line=line[:120]);continue
                if not isinstance(obj,dict):event(kind='not_json',line=line[:120]);continue
                if 'seq' not in obj:event(kind='reply',reply=obj);continue
                d=to_decoded(obj)|{'t':now(),'raw':obj};result['samples']+=1
                if next_send is None:next_send=time.monotonic()
                if out:out.write(json.dumps(d,ensure_ascii=False)+'\n');out.flush()
                adc=d.get('adc',{})
                print(f"{d['t'][11:23]} #{d['seq']:<5} T {d.get('baro',{}).get('temp_c','?')} °C"
                      f" · light {d.get('light',{}).get('lux','?')} lx · VDD {adc.get('vdd_v','?')} V",flush=True)
    except KeyboardInterrupt:event(kind='interrupted')
    finally:
        os.close(fd)
        if out:out.close()
        result['finished']=now()
        if a.out:(a.out/'result.json').write_text(json.dumps(result,indent=1,ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k!='events'},ensure_ascii=False))
    return 0 if result['samples'] else 1


if __name__=='__main__':raise SystemExit(main())
