"""Experimental capture of advertisements and GATT. Reads and temporary subscriptions only.
Does not write configuration characteristics, does not authenticate, does not flash.
"""
import asyncio,json,time,platform,importlib.metadata
from datetime import datetime
from pathlib import Path
from bleak import BleakScanner,BleakClient
OUT=Path('docs/evidence/mac-ble-2026-11-18');OUT.mkdir(parents=True,exist_ok=True)
FE9A='0000fe9a-0000-1000-8000-00805f9b34fb'
FILE=OUT/'capture-gatt.jsonl'
SESSION=None
def log(event,**kw):
 row={'time':datetime.now().astimezone().isoformat(),'monotonic':time.monotonic(),'session':SESSION,'event':event,**kw}
 with FILE.open('a') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
 if event!='advertisement':print(json.dumps(row,ensure_ascii=False),flush=True)
def adv(d,a):
 if FE9A not in a.service_data:return
 log('advertisement',connectable=bool(a.platform_data[1].get('kCBAdvDataIsConnectable',False)),id=d.address,name=d.name,local_name=a.local_name,rssi=a.rssi,tx_power=a.tx_power,service_uuids=a.service_uuids,manufacturer_data={str(k):v.hex() for k,v in a.manufacturer_data.items()},service_data={k:v.hex() for k,v in a.service_data.items()})
async def scan(seconds):
 log('scan_start',seconds=seconds)
 async with BleakScanner(detection_callback=adv):await asyncio.sleep(seconds)
 log('scan_end')
async def session(number,notify):
 global SESSION
 SESSION=number
 dev=await BleakScanner.find_device_by_filter(lambda d,a: a.service_data.get(FE9A,b'')[:17] == bytes.fromhex('00bb6b7d16b94a4e265cb6b304024bd423') and bool(a.platform_data[1].get('kCBAdvDataIsConnectable',False)),timeout=18)
 if not dev:log('target_not_found');return
 ended=asyncio.Event();began=time.monotonic()
 def disconnected(client):log('disconnected',elapsed_since_connect_request=time.monotonic()-began);ended.set()
 client=BleakClient(dev,disconnected_callback=disconnected,timeout=12)
 try:
  log('connect_request',id=dev.address)
  await asyncio.wait_for(client.connect(),18)
  log('connected_services_ready',mtu=client.mtu_size,name=dev.name,elapsed_since_connect_request=time.monotonic()-began)
  services=list(client.services)
  # Do not operate on a peripheral whose expected Estimote service is absent.
  if not any(s.uuid=='6c372000-d2cc-11e4-9a1f-0002a5d5c51b' for s in services):
   log('unexpected_services_abort');return
  reads=[];notifies=[];descriptors=[]
  for s in services:
   log('service',uuid=s.uuid,handle=s.handle,description=s.description)
   for c in s.characteristics:
    log('characteristic',service=s.uuid,uuid=c.uuid,handle=c.handle,properties=c.properties,description=c.description,descriptors=[{'uuid':d.uuid,'handle':d.handle,'description':d.description} for d in c.descriptors])
    if 'read' in c.properties:reads.append(c)
    if 'notify' in c.properties or 'indicate' in c.properties:notifies.append(c)
    descriptors.extend(c.descriptors)
  reads.sort(key=lambda c:0 if c.uuid.startswith('6c372004') else 1)
  for c in reads:
   if not client.is_connected:break
   try:
    value=bytes(await asyncio.wait_for(client.read_gatt_char(c),2))
    log('read',uuid=c.uuid,handle=c.handle,hex=value.hex(),length=len(value))
   except Exception as e:log('read_error',uuid=c.uuid,error=repr(e))
  if notify:
   for c in notifies:
    if not client.is_connected:break
    try:
     await asyncio.wait_for(client.start_notify(c,lambda char,data:log('notification',uuid=char.uuid,hex=bytes(data).hex())),2)
     log('subscribed',uuid=c.uuid)
    except Exception as e:log('subscribe_error',uuid=c.uuid,error=repr(e))
  else:
   for d in descriptors:
    if not client.is_connected:break
    try:log('descriptor_read',uuid=d.uuid,handle=d.handle,hex=bytes(await asyncio.wait_for(client.read_gatt_descriptor(d.handle),2)).hex())
    except Exception as e:log('descriptor_error',uuid=d.uuid,handle=d.handle,error=repr(e))
  if client.is_connected:
   try:await asyncio.wait_for(ended.wait(),16)
   except TimeoutError:log('observation_limit_reached')
 except Exception as e:log('session_error',error=repr(e))
 finally:
  if client.is_connected:
   log('local_disconnect_request');await client.disconnect()
  log('session_end')
 SESSION=None
async def main():
 log('run_start',python=platform.python_version(),os=platform.platform(),bleak=importlib.metadata.version('bleak'))
 await scan(5)
 for n in range(1,4):
  await session(n,notify=n==2)
  await scan(6)
 await scan(30)
 log('run_end')
asyncio.run(main())
