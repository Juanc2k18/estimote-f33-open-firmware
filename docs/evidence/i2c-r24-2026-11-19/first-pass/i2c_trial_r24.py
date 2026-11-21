#!/usr/bin/env python3
"""r24 RAM/SWD campaign. No flash/UICR writes and no power changes.
Reuses the open drain from i2c_bitbang_swd and the loop from sensor_diagnostics.
Usage: python3 scripts/i2c_trial_r24.py --out docs/evidence/i2c-r24-2026-11-19
"""
import argparse,collections,hashlib,json,sys,time,traceback
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
from bus_probe import I2CProbe
P=0x50000000
class SWDLines:
 def __init__(self,t,pins,pull,log):
  self.t,self.pins,self.log=t,pins,log
  for p in pins:
   t.write32(P+0x700+4*p,12 if pull else 0)
  t.write32(P+0x50c,sum(1<<p for p in pins))
 def low(self,p):self.t.write32(P+0x518,1<<p);self.log({'op':'low','pin':p})
 def release(self,p):self.t.write32(P+0x51c,1<<p);self.log({'op':'release','pin':p})
 def sample(self):
  raw=self.t.read32(P+0x510);v={p:raw>>p&1 for p in self.pins}
  self.log({'op':'sample','raw':raw,'pins':v});return v

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 a.out.mkdir(parents=True,exist_ok=True)
 f=(a.out/'transactions.jsonl').open('w');trace=(a.out/'gpio-trace.jsonl').open('w')
 def emit(v):
  v={'unix':time.time(),**v};f.write(json.dumps(v)+'\n');f.flush()
 def tr(v):trace.write(json.dumps({'monotonic':time.monotonic(),**v})+'\n')
 rows=[];t=None;before=None
 def digest(addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
 with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
  t=s.target
  def release_all():
   # Inputs without pull between cases; 14/15 are never enabled together.
   for p in (2,8,6,7,14,15):t.write32(P+0x700+4*p,0)
  try:
   t.halt();before={'bootloader':digest(0x74000,0xc000),'uicr':digest(0x10001000,0x400)}
   emit({'kind':'before','hashes':before,'ficr':t.read32(0x10000100),'resetpins':[t.read32(x) for x in (0x10001200,0x10001204)]})
   assert t.read32(0x10000100)==0x52832
   assert [t.read32(x) for x in (0x10001200,0x10001204)]==[21,21]
   t.reset_and_halt()
   t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
   for reg,val in [('pc',0x20000000),('xpsr',1<<24),('sp',0x20010000)]:t.write_core_register(reg,val)
   t.resume();t.write32(0x40001504,0) # RADIO.INTENCLR below, no enable
   t.write32(0x40001308,0xffffffff) # RADIO.INTENCLR
   t.write32(0x40001010,1) # RADIO.TASKS_DISABLE
   time.sleep(.02)
   assert t.read32(0x40001550)==0,'RADIO not disabled'
   emit({'kind':'ram','radio_state':t.read32(0x40001550)})
   def run_case(state,enable,pull,sda,scl,control=False):
    release_all()
    if enable is not None:
     t.write32(P+0x508,1<<enable);t.write32(P+0x700+4*enable,1)
    time.sleep(.15)
    label={'state':state,'pullup_internal':pull,'sda':sda,'scl':scl}
    tr({'case':label})
    io=SWDLines(t,(sda,scl),pull,tr);bus=I2CProbe(io,sda,scl)
    electrical=bus.electrical();emit({'kind':'electrical',**label,**electrical})
    row={**label,'electrical':electrical,'W':{},'R':{},'repeats':[]}
    if electrical['valid']:
     for read in (False,True):
      rw='R' if read else 'W';counts=collections.Counter();acks=[]
      for addr in range(8,120):
       r=bus.address(addr,read);emit({'kind':'address',**label,**r});counts[r['status']]+=1
       if r['status']=='ack':acks.append(addr)
       if r['status'] not in ('ack','nack'):
        row['incomplete']=f'{rw}: {r["status"]}';break
      row[rw]={'counts':dict(counts),'acks':acks}
      if row.get('incomplete'):break
     candidates=sorted(set(row['W'].get('acks',[])+row['R'].get('acks',[])))
     for passno in range(3):
      for addr in sorted({v for x in candidates for v in (x-1,x,x+1) if 8<=v<120}):
       for read in (False,True):
        r=bus.address(addr,read);v={'pass':passno+1,**r};row['repeats'].append(v)
        emit({'kind':'repeat',**label,**v})
    emit({'kind':'case_summary',**row});rows.append(row)
    release_all();trace.flush()
    print(json.dumps({**label,'valid':electrical['valid'],'W':row['W'],'R':row['R']}),flush=True)
    if control:
     assert electrical['valid'],'Control electrically invalid'
     assert all(row[rw].get('counts')=={'nack':112} for rw in ('W','R')),'Control does not give 112 NACK per direction'
   run_case('control-ZZ',None,True,2,8,True)
   for state,enable in [('ZZ',None),('HZ',14),('ZH',15)]:
    for pull in (False,True):
     for sda,scl in ((6,7),(7,6)):
      run_case(state,enable,pull,sda,scl)
      assert t.read32(0x40001550)==0
   emit({'kind':'completed'})
  except BaseException as e:
   emit({'kind':'incomplete','error':repr(e),'traceback':traceback.format_exc()});raise
  finally:
   try:
    t.halt();release_all();emit({'kind':'released','cnf':{p:t.read32(P+0x700+4*p) for p in (2,8,6,7,14,15)}})
    after={'bootloader':digest(0x74000,0xc000),'uicr':digest(0x10001000,0x400)}
    emit({'kind':'after','hashes':after,'unchanged':after==before})
    t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
    emit({'kind':'closure','pc':hex(pc),'bootloader_running':0x74000<=pc<0x80000,'radio_state':t.read32(0x40001550),'resetpins':[t.read32(x) for x in (0x10001200,0x10001204)]})
    t.resume()
    assert after==before,'Hash changed'
    assert 0x74000<=pc<0x80000,'Bootloader not observed'
   finally:
    (a.out/'summary.json').write_text(json.dumps(rows,indent=2)+'\n');f.close();trace.close()
if __name__=='__main__':main()
