#!/usr/bin/env python3
"""Uploads an application over BLE to the Adafruit bootloader (legacy DFU from SDK 11, revision 0.8).

Takes the .zip from `adafruit-nrfutil dfu genpkg` (or `make zip` in firmware/ble-sensors).
If it finds `F33`, it first writes 0x01 to its control so that it restarts as
`AdaDFU`; if it is already advertising `AdaDFU`, it uploads directly.

Sequence (Nordic legacy DFU): START (application) → INIT (.dat) → PRN →
RECEIVE (20-byte packets) → VALIDATE → ACTIVATE_AND_RESET.

Tests used a macOS terminal with Bluetooth permission; the agent process in that
environment had none. Other hosts may need adapted permissions and identifiers.
"""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import struct
import sys
import time
import zipfile

BASE='0000{:04x}-1212-efde-1523-785feabcd123'
CTRL,PKT,REV=(BASE.format(n) for n in (0x1531,0x1532,0x1534))
F33_CONTROL='239d0003-86eb-4a92-8ec1-0e38f13e0817'
START,INIT,RECEIVE,VALIDATE,ACTIVATE,PRN_REQ=1,2,3,4,5,8
RESPONSE,PRN_NOTIF=0x10,0x11
STATUS={1:'success',2:'invalid state',3:'not supported',4:'data size exceeds limit',5:'CRC',6:'operation failed'}
APPLICATION=0x04


def now():return datetime.now().astimezone().isoformat(timespec='milliseconds')


def load(zpath):
    with zipfile.ZipFile(zpath) as z:
        app=json.loads(z.read('manifest.json'))['manifest']['application']
        return z.read(app['dat_file']),z.read(app['bin_file'])


async def find(name,timeout):
    from bleak import BleakScanner
    return await BleakScanner.find_device_by_name(name,timeout=timeout)


async def to_bootloader(a,log):
    from bleak import BleakClient
    from bleak.exc import BleakError
    dev=await find('AdaDFU',3)
    if dev:log(kind='adadfu_already');return dev
    f33=await find(a.app_name,a.scan)
    if f33 is None:raise RuntimeError(f'found neither {a.app_name} nor AdaDFU')
    async with BleakClient(f33) as c:
        try:await c.write_gatt_char(F33_CONTROL,b'\x01',response=True)
        except BleakError as exc:log(kind='control_write_disconnected',error=str(exc))
    log(kind='dfu_requested')
    dev=await find('AdaDFU',a.scan)
    if dev is None:raise RuntimeError('the board did not appear as AdaDFU')
    return dev


async def upload(a,log):
    from bleak import BleakClient
    dat,image=load(a.zip)
    log(kind='package',zip=str(a.zip),dat_len=len(dat),bin_len=len(image))
    dev=await to_bootloader(a,log)
    q=asyncio.Queue()
    async with BleakClient(dev) as c:
        rev=bytes(await c.read_gatt_char(REV));log(kind='dfu_revision',raw=rev.hex(),mtu=c.mtu_size)
        await c.start_notify(CTRL,lambda _,d:q.put_nowait(bytes(d)))

        async def expect(proc,timeout=20):
            while True:
                d=await asyncio.wait_for(q.get(),timeout)
                if d[0]==RESPONSE and d[1]==proc:
                    if d[2]!=1:raise RuntimeError(f'procedure {proc}: {STATUS.get(d[2],d[2])}')
                    return
                log(kind='unexpected_notification',raw=d.hex())

        t0=time.monotonic()
        await c.write_gatt_char(CTRL,bytes([START,APPLICATION]),response=True)
        await c.write_gatt_char(PKT,struct.pack('<III',0,0,len(image)),response=False)
        await expect(START,timeout=60)          # includes erasing the bank
        log(kind='start_ok',s=round(time.monotonic()-t0,2))
        await c.write_gatt_char(CTRL,bytes([INIT,0]),response=True)
        await c.write_gatt_char(PKT,dat,response=False)
        await c.write_gatt_char(CTRL,bytes([INIT,1]),response=True)
        await expect(INIT);log(kind='init_ok')
        await c.write_gatt_char(CTRL,struct.pack('<BH',PRN_REQ,a.prn),response=True)
        await c.write_gatt_char(CTRL,bytes([RECEIVE]),response=True)
        sent=0;n=0;t1=time.monotonic()
        while sent<len(image):
            chunk=image[sent:sent+20]
            await c.write_gatt_char(PKT,chunk,response=False);sent+=len(chunk);n+=1
            if n%a.prn==0 and sent<len(image):
                while True:
                    d=await asyncio.wait_for(q.get(),20)
                    if d[0]==PRN_NOTIF:
                        got=struct.unpack('<I',d[1:5])[0]
                        if got!=sent:raise RuntimeError(f'the board confirms {got} bytes, sent {sent}')
                        break
                    log(kind='unexpected_notification',raw=d.hex())
            if n%50==0:print(f'{sent}/{len(image)} bytes',flush=True)
        await expect(RECEIVE,timeout=30)
        rate=len(image)/(time.monotonic()-t1)
        log(kind='image_ok',bytes=sent,packets=n,bytes_per_s=round(rate))
        await c.write_gatt_char(CTRL,bytes([VALIDATE]),response=True)
        await expect(VALIDATE);log(kind='validate_ok')
        try:await c.write_gatt_char(CTRL,bytes([ACTIVATE]),response=True)
        except Exception as exc:log(kind='activate_disconnected',error=str(exc))
        log(kind='activated',total_s=round(time.monotonic()-t0,2))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('zip',type=Path)
    ap.add_argument('--app-name',default='F33')
    ap.add_argument('--scan',type=float,default=15)
    ap.add_argument('--prn',type=int,default=10,help='packets per receipt notification')
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    events=[]
    def log(**kw):
        kw={'t':now()}|kw;events.append(kw);print(json.dumps(kw,ensure_ascii=False),flush=True)
    status='ok'
    try:asyncio.run(upload(a,log))
    except Exception as exc:status='error';log(kind='error',error=repr(exc))
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'events.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events))
        (a.out/'result.json').write_text(json.dumps(dict(tool='ble_dfu',zip=str(a.zip),status=status),indent=1))
    return 0 if status=='ok' else 1


if __name__=='__main__':raise SystemExit(main())
