"""Experimental decoding following the public Estimote format.
Source: https://github.com/Estimote/estimote-specs/blob/master/estimote-telemetry.js
Run from the repository root after a capture; keeps the original bytes.
"""
import json,struct
from pathlib import Path
root=Path('docs/evidence/mac-ble-2026-11-18')
rows=[]
for file in ['capture.jsonl','capture-gatt.jsonl']:
 p=root/file
 if p.exists():rows.extend(json.loads(l) for l in p.read_text().splitlines())
seen=set();out=[]
for r in rows:
 if r['event']!='advertisement':continue
 for h in r['service_data'].values():
  b=bytes.fromhex(h)
  if not b or b[0]&15!=2 or b[0]>>4!=2 or len(b)<20 or h in seen:continue
  seen.add(h)
  d={'first_seen':r['time'],'raw':h,'protocol_version':b[0]>>4,'short_id':b[1:9].hex(),'subframe':b[9]&3}
  if d['subframe']==0:
   d.update(acceleration_g=[x*2/127 for x in struct.unpack('bbb',b[10:13])],motion_code=b[15]&3,gpio_reported_high=[bool(b[15]&(1<<i)) for i in range(4,8)],firmware_error=bool(b[15]&4),clock_error=bool(b[15]&8),pressure_pa=int.from_bytes(b[16:20],'little')/256)
  elif d['subframe']==1:
   t=((b[17]&3)<<10)|(b[16]<<2)|((b[15]&192)>>6)
   if t>2047:t-=4096
   mv=(b[18]<<6)|((b[17]&252)>>2)
   d.update(temperature_c=t/16,light_lux=2**(b[13]>>4)*(b[13]&15)*.72,magnetic_normalized=[int.from_bytes(bytes([v]),signed=True)/128 for v in b[10:13]],uptime_value=((b[15]&15)<<8)|b[14],uptime_unit=['seconds','minutes','hours','days'][(b[15]>>4)&3],battery_mv=None if mv==16383 else mv,battery_percent=None if b[19]==255 else b[19])
  out.append(d)
(root/'telemetry-decoded.json').write_text(json.dumps({'source':'https://github.com/Estimote/estimote-specs/blob/master/estimote-telemetry.js','frames':out},indent=2))
print(json.dumps(out,indent=2))
