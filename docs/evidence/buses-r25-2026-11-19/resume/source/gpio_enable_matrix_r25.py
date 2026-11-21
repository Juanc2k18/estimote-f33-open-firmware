#!/usr/bin/env python3
"""One GPIO high at a time, radio disabled; the rest as inputs without pull.
Repeats every state starting from Z. Allows checking nets/enables without assuming
UWB routes. UART must be physically disconnected. No flash/UICR.
"""
import argparse,hashlib,json,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
P=0x50000000

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--uart-disconnected',action='store_true',required=True)
 ap.add_argument('--pins',default='2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,22,23,24,25,26,27,28,29,30,31')
 a=ap.parse_args();pins=[int(x) for x in a.pins.split(',')]
 if any(x not in range(32) or x in {0,1,21} for x in pins):ap.error('crystal/nRESET excluded')
 a.out.mkdir(parents=True,exist_ok=True)
 with (a.out/'enable.jsonl').open('w') as f:
  def emit(v):f.write(json.dumps({'unix':time.time(),**v})+'\n');f.flush()
  with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
   t=s.target;t.halt()
   def digest(addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
   def release():
    for p in range(32):
     if p not in {0,1,21}:t.write32(P+0x700+4*p,0)
   def sample():
    raw=t.read32(P+0x510);return {'raw':raw,'pins':{p:raw>>p&1 for p in range(32)}}
   before=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
   emit({'kind':'parameters','hashes':before,'pins':pins,'uart_disconnected_report':True,'hold_s':.01,'rest':'input_no_pull','radio':'disabled'})
   try:
    t.reset_and_halt();t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
    for reg,val in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,val)
    t.resume();t.write32(0x40001010,1);time.sleep(.02);assert t.read32(0x40001550)==0
    for passno in (1,2,3):
     for p in pins:
      release();time.sleep(.05);baseline=sample()
      # Set the latch before enabling the output; only one GPIO active.
      t.write32(P+0x508,1<<p);t.write32(P+0x700+4*p,1);time.sleep(.01)
      high=sample();cnf=t.read32(P+0x700+4*p)
      direction=t.read32(P+0x514);latch=t.read32(P+0x504)
      assert direction & ((1<<14)|(1<<15)) != ((1<<14)|(1<<15)),'14/15 both outputs'
      t.write32(P+0x700+4*p,0);time.sleep(.05);released=sample()
      emit({'kind':'trial','pass':passno,'pin':p,'baseline':baseline,'high':high,'released':released,'cnf_high':cnf,'dir_high':direction,'out_high':latch})
    emit({'kind':'completed','radio':t.read32(0x40001550)})
   finally:
    t.halt();release();after=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
    t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
    emit({'kind':'closure','hashes':after,'unchanged':before==after,'pc':hex(pc),'bootloader':0x74000<=pc<0x80000});t.resume()
    assert before==after and 0x74000<=pc<0x80000
if __name__=='__main__':main()
