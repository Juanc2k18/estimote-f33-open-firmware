#!/usr/bin/env python3
"""Observes P0.19 as an input; M41T62 pin6 IRQ/OUT as reported by the owner.
Does not drive the line as an output. RAM and reset, no flash/UICR. At the end it overrides,
in RAM only, the bootloader's use of P0.19 as an LED and checks that it stays an input.
"""
import argparse,hashlib,json,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
P=0x50000000;PIN=19

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 events=[]
 def emit(v):
  v={'unix':time.time(),**v};events.append(v);(a.out/'events.json').write_text(json.dumps(events,indent=2)+'\n')
 with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
  t=s.target;t.halt()
  def hashes():return [hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest() for addr,n in ((0x74000,0xc000),(0x10001000,0x400))]
  before=hashes()
  emit({'kind':'baseline','pc':hex(t.read_core_register('pc')),'cnf19':t.read32(P+0x700+4*PIN),'dir19':(t.read32(P+0x514)>>PIN)&1,'in19':(t.read32(P+0x510)>>PIN)&1,'hashes':before})
  try:
   t.reset_and_halt();t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
   for reg,v in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,v)
   t.resume();t.write32(0x40001010,1);time.sleep(.02);assert t.read32(0x40001550)==0
   for cfg in (0,12,4,0):
    t.write32(P+0x700+4*PIN,cfg);time.sleep(.05);samples=[]
    for _ in range(64):
     samples.append({'monotonic':time.monotonic(),'level':(t.read32(P+0x510)>>PIN)&1});time.sleep(.002)
    emit({'kind':'input','cnf':t.read32(P+0x700+4*PIN),'dir19':(t.read32(P+0x514)>>PIN)&1,'samples':samples,'ones':sum(x['level'] for x in samples)})
   emit({'kind':'completed','radio':t.read32(0x40001550)})
  finally:
   t.halt();t.write32(P+0x700+4*PIN,0);after=hashes();t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
   bootcnf=t.read32(P+0x700+4*PIN)
   t.write32(P+0x700+4*PIN,0);t.resume();time.sleep(.1);cnf1=t.read32(P+0x700+4*PIN);time.sleep(.1);cnf2=t.read32(P+0x700+4*PIN)
   emit({'kind':'closure','pc':hex(pc),'bootloader':0x74000<=pc<0x80000,'bootloader_cnf19_before_override':bootcnf,'cnf19_samples_after_resume':[cnf1,cnf2],'temporary_override':'P0.19 input without pull; bootloader flash intact','hashes':after,'unchanged':before==after})
   assert before==after and 0x74000<=pc<0x80000 and cnf1==cnf2==0
if __name__=='__main__':main()
