#!/usr/bin/env python3
"""Scans BLE with bleak (tested on macOS/CoreBluetooth), measures RSSI and reads Device Information.

macOS does not expose the MAC address: it identifies the peripheral with its own UUID.
The identity is confirmed by name and by the DIS strings (manufacturer/model).
Read-only; does not write characteristics or start DFU.

Requires `bleak` (e.g. in a virtual environment) and Bluetooth permission for the
application that runs Python.
"""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
import statistics

DIS={'manufacturer':'00002a29-0000-1000-8000-00805f9b34fb','model':'00002a24-0000-1000-8000-00805f9b34fb',
     'firmware':'00002a26-0000-1000-8000-00805f9b34fb'}


async def scan(name,seconds):
    from bleak import BleakScanner
    hits=[];device=None
    def seen(dev,adv):
        nonlocal device
        if (adv.local_name or dev.name)==name:
            device=dev
            hits.append(dict(t=datetime.now().astimezone().isoformat(timespec='milliseconds'),rssi=adv.rssi,
                             tx_power=adv.tx_power,service_uuids=adv.service_uuids,
                             manufacturer_data={k:v.hex() for k,v in adv.manufacturer_data.items()}))
    async with BleakScanner(seen):await asyncio.sleep(seconds)
    return device,hits


async def read_dis(device):
    from bleak import BleakClient
    async with BleakClient(device) as client:
        services=[dict(uuid=s.uuid,description=s.description,
                       characteristics=[dict(uuid=c.uuid,properties=c.properties) for c in s.characteristics])
                  for s in client.services]
        values={}
        for key,uuid in DIS.items():
            try:values[key]=(await client.read_gatt_char(uuid)).decode(errors='replace')
            except Exception as exc:values[key]=f'error: {exc!r}'
        return services,values


async def main_async(a):
    result=dict(tool='ble_scan_read',name=a.name,seconds=a.seconds,note=a.note,
                started=datetime.now().astimezone().isoformat(timespec='seconds'))
    device,hits=await scan(a.name,a.seconds)
    rssi=[h['rssi'] for h in hits if h['rssi']<0]   # 127 = not available in CoreBluetooth
    result.update(found=device is not None,mac_os_identifier=getattr(device,'address',None),advertisements=len(hits),
                  rssi=dict(min=min(rssi),median=statistics.median(rssi),max=max(rssi)) if rssi else None,
                  first_advertisement=hits[0] if hits else None)
    if device and not a.no_connect:
        try:result['services'],result['dis']=await read_dis(device)
        except Exception as exc:result['connect_error']=repr(exc)
    return result,hits


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--name',default='AdaDFU')
    ap.add_argument('--seconds',type=float,default=10)
    ap.add_argument('--no-connect',action='store_true')
    ap.add_argument('--note',default='',help='stated position/distance')
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    result,hits=asyncio.run(main_async(a))
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'result.json').write_text(json.dumps(result,indent=1,ensure_ascii=False))
        (a.out/'advertisements.jsonl').write_text(''.join(json.dumps(h)+'\n' for h in hits))
    print(json.dumps(result,indent=1,ensure_ascii=False))
    return 0 if result['found'] else 1


if __name__=='__main__':raise SystemExit(main())
