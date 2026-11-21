#!/usr/bin/env python3
"""Reads the F3.3 BLE sensor application (r44–r45) with bleak (tested on macOS).

Looks for the `F33` advertisement, subscribes to the data characteristic and decodes
every notification (format in `f33_packet.py`). `--dfu` writes 0x01 to the
control characteristic: the board restarts into the bootloader as `AdaDFU`.
`--serial-dfu` writes 0x02: DFU over UART on E1/E2 for 3 s (r45).
Since r45 it also reads the version (0x2A26) and the battery level (0x2A19).
`--duration S` records for S seconds and reconnects after every disconnection, which is
logged in `result.json`; each sample is written as it arrives.

Tests used a macOS terminal with Bluetooth permission; the agent process in that
environment had none. Other hosts may need adapted permissions and identifiers.
"""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import f33_packet as fp

BASE='239d{:04x}-86eb-4a92-8ec1-0e38f13e0817'
SERVICE,DATA,CONTROL=(BASE.format(n) for n in (1,2,3))
FW_REV='00002a26-0000-1000-8000-00805f9b34fb'
BATTERY='00002a19-0000-1000-8000-00805f9b34fb'


def now():return datetime.now().astimezone().isoformat(timespec='milliseconds')


def line(d):
    parts=[f"#{d['seq']}"]
    if 'accel' in d:parts.append('accel {:.2f}/{:.2f}/{:.2f} g'.format(*d['accel']['g']))
    if 'magnet' in d:parts.append('mag |{:.2f}| G'.format(d['magnet']['norm_gauss']))
    if 'baro' in d:parts.append(f"{d['baro']['pressure_hpa']:.1f} hPa {d['baro']['temp_c']:.1f} °C")
    if 'light' in d:parts.append(f"{d['light']['lux']:.1f} lx")
    if 'adc' in d:parts.append(f"VDD {d['adc']['vdd_v']:.2f} V AIN3 {d['adc']['ain3_v']:.3f} V"
                               f" bat≈{d['adc']['battery_v_estimate']:.2f} V {d['adc']['battery_percent']} %")
    if 'rtc_seconds' in d:parts.append(f"rtc {d['rtc_seconds']}s")
    return ' · '.join(parts)


async def session(a,result,emit,event):
    """One connection: reads, subscribes and waits until done, disconnection or the deadline."""
    from bleak import BleakClient, BleakScanner
    dev=await BleakScanner.find_device_by_name(a.name,timeout=a.scan)
    if dev is None:event(kind='not_found');return False
    result.update(found=True,mac_os_identifier=dev.address)
    lost=asyncio.Event()
    async with BleakClient(dev,disconnected_callback=lambda _:lost.set()) as client:
        event(kind='connected',mtu=client.mtu_size)
        result['mtu']=client.mtu_size
        result['first_read']=fp.decode(bytes(await client.read_gatt_char(DATA)))
        try:result['firmware_revision']=bytes(await client.read_gatt_char(FW_REV)).decode()
        except Exception as exc:result['firmware_revision']=f'not available: {exc!r}'   # r44 does not have it
        try:result['battery_level']=bytes(await client.read_gatt_char(BATTERY))[0]
        except Exception as exc:result['battery_level']=f'not available: {exc!r}'
        print(f"version {result['firmware_revision']} · battery {result['battery_level']} %",flush=True)
        if a.dfu or a.serial_dfu:
            # The board restarts on receiving the command, often before sending the reply.
            from bleak.exc import BleakError
            cmd=b'\x02' if a.serial_dfu else b'\x01';result['dfu_command']=cmd.hex()
            try:await client.write_gatt_char(CONTROL,cmd,response=True);result['dfu_write']='answered'
            except BleakError as exc:result['dfu_write']=f'disconnected before answering: {exc}'
            result['dfu_requested']=now();return True
        done=asyncio.Event()
        def on_data(_,data):
            try:d=fp.decode(bytes(data))|{'t':now()}
            except ValueError as exc:d={'t':now(),'error':str(exc),'raw':bytes(data).hex()}
            emit(d);print(line(d) if 'seq' in d else d,flush=True)
            if not a.duration and result['samples']>=a.count:done.set()
        await client.start_notify(DATA,on_data)
        waits=[asyncio.ensure_future(e.wait()) for e in (done,lost)]
        remaining=a.deadline-asyncio.get_running_loop().time() if a.duration else a.count*2+10
        finished,_=await asyncio.wait(waits,timeout=max(remaining,0),return_when=asyncio.FIRST_COMPLETED)
        for w in waits:w.cancel()
        if lost.is_set():event(kind='disconnected');return False
        if not finished:result['timeout']=not a.duration
        try:await client.stop_notify(DATA)
        except Exception:pass
    return True


async def run(a):
    result=dict(tool='ble_sensors',started=now(),name=a.name,note=a.note,found=False,samples=0,events=[])
    out=None
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True);out=(a.out/'samples.jsonl').open('w')
    def emit(d):
        result['samples']+=1
        if out:out.write(json.dumps(d,ensure_ascii=False)+'\n');out.flush()
    def event(**kw):
        kw={'t':now()}|kw;result['events'].append(kw);print(json.dumps(kw,ensure_ascii=False),flush=True)
    loop=asyncio.get_running_loop()
    a.deadline=loop.time()+(a.duration or 0)
    try:
        while True:
            try:ok=await session(a,result,emit,event)
            except Exception as exc:ok=False;event(kind='error',error=repr(exc))
            if not a.duration or loop.time()>=a.deadline:break   # with --duration it reconnects
            if ok:break
    finally:
        if out:out.close()
    result['finished']=now()
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name',default='F33')
    ap.add_argument('--count',type=int,default=15,help='notifications to receive')
    ap.add_argument('--duration',type=float,help='recording seconds; reconnects if the board is lost')
    ap.add_argument('--scan',type=float,default=15)
    ap.add_argument('--dfu',action='store_true',help='0x01: DFU over BLE (AdaDFU)')
    ap.add_argument('--serial-dfu',action='store_true',help='0x02: DFU over UART for 3 s')
    ap.add_argument('--note',default='')
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    result=asyncio.run(run(a))
    if a.out:(a.out/'result.json').write_text(json.dumps(result,indent=1,ensure_ascii=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ('first_read','events')},ensure_ascii=False))
    return 0 if result.get('found') else 1


if __name__=='__main__':raise SystemExit(main())
