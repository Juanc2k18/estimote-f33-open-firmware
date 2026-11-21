#!/usr/bin/env python3
"""r25 single-pin matrix: a single pull/OD active, the rest inputs without pull.
Does not touch UART/crystal/nRESET or flash/UICR. Does not force an output high.
"""
import argparse,hashlib,json,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
P=0x50000000

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--uart-disconnected',action='store_true',help='confirms GP4/GP5→E2/E1 removed; adds GPIO12/13')
 ap.add_argument('--frequency',type=int,default=100000)
 ap.add_argument('--exclude',default='',help='GPIOs that are reserved or interrupt SWD')
 a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 excluded={int(v) for v in a.exclude.split(',') if v}
 if not all(0<=v<32 for v in excluded):ap.error('excluded GPIO out of range')
 skip={0,1,21} | excluded | (set() if a.uart_disconnected else {12,13})
 pins=[p for p in range(32) if p not in skip]
 records=[]
 with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=a.frequency,auto_unlock=False,connect_mode='attach')) as s:
  t=s.target
  def digest(addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
  def sample():
   raw=t.read32(P+0x510)
   return {'raw':raw,'pins':{p:raw>>p&1 for p in range(32)}}
  def release():
   for p in pins:t.write32(P+0x700+4*p,0)
  def record(r):
   r={'unix':time.time(),**r};records.append(r)
   (a.out/'matrix.json').write_text(json.dumps(records,indent=2)+'\n')
  t.halt();before=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
  record({'kind':'baseline','pc':hex(t.read_core_register('pc')),'part':hex(t.read32(0x10000100)),'nfcpins':hex(t.read32(0x1000120c)),'uicr_reset':[t.read32(x) for x in (0x10001200,0x10001204)],'hashes':before,'pins_tested':pins,'pins_not_driven':sorted(skip),'uart_disconnected_report':a.uart_disconnected})
  try:
   assert t.read32(0x10000100)==0x52832
   assert t.read32(0x1000120c)&1==0
   t.reset_and_halt();t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
   for reg,val in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,val)
   t.resume();t.write32(0x40001010,1);time.sleep(.02);assert t.read32(0x40001550)==0
   release();time.sleep(.1);record({'kind':'all_inputs','sample':sample()})
   for p in pins:
    release();rows=[]
    for pull in (0,4,12):
     t.write32(P+0x700+4*p,pull);time.sleep(.02)
     rows.append({'pull':pull,'sample':sample(),'cnf':t.read32(P+0x700+4*p)})
    # OUT=0, only DIR output; the high level comes from the internal pull-up on release.
    t.write32(P+0x50c,1<<p);t.write32(P+0x518,1<<p);time.sleep(.01)
    low={'sample':sample(),'cnf':t.read32(P+0x700+4*p),'dir':t.read32(P+0x514),'out':t.read32(P+0x504)}
    t.write32(P+0x51c,1<<p);time.sleep(.05)
    high={'sample':sample(),'cnf':t.read32(P+0x700+4*p),'dir':t.read32(P+0x514),'out':t.read32(P+0x504)}
    r={'kind':'pin','pin':p,'pulls':rows,'od_low':low,'released':high,'can_low':low['sample']['pins'][p]==0,'can_high':high['sample']['pins'][p]==1}
    record(r);print(p,r['can_low'],r['can_high'],flush=True)
    t.write32(P+0x700+4*p,0)
   record({'kind':'completed','radio':t.read32(0x40001550)})
  finally:
   t.halt();release();after=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
   t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
   record({'kind':'closure','hashes':after,'unchanged':after==before,'pc':hex(pc),'bootloader':0x74000<=pc<0x80000});t.resume()
   assert before==after and 0x74000<=pc<0x80000
if __name__=='__main__':main()
