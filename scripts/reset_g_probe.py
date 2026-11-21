#!/usr/bin/env python3
"""Functional test of G: prepare runs a counter in RAM; check detects the return to flash.
Does not issue a software reset, does not write flash/UICR. G is operated by hand.
"""
import argparse,json,struct,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','check']);a=ap.parse_args()
out=Path(__file__).resolve().parents[1]/'docs/evidence/sensors-r17-2026-11-19'
with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
 t=s.target;t.halt()
 state={'mode':a.mode,'pc_before':hex(t.read_core_register('pc')),'resetreas':hex(t.read32(0x40000400)),'pselreset':[hex(t.read32(x)) for x in (0x10001200,0x10001204)]}
 if a.mode=='prepare':
  assert state['pselreset']==['0x15','0x15']
  # CPSID i; LDR r0,=counter; loop: LDR r1,[r0]; ADDS r1,1; STR r1,[r0]; B loop
  code=struct.pack('<6HI',0xb672,0x4802,0x6801,0x3101,0x6001,0xe7fb,0x20005000)
  t.write_memory_block8(0x20000000,list(code));t.write32(0x20005000,0)
  t.write_core_register('pc',0x20000000);t.write_core_register('xpsr',1<<24)
  t.write_core_register('sp',0x20010000);t.resume()
  time.sleep(.05);v1=t.read32(0x20005000);time.sleep(.05);v2=t.read32(0x20005000)
  state['counter_samples']=[v1,v2];assert v1!=v2,'RAM counter not advancing'
  t.halt();state['pc_in_loop']=hex(t.read_core_register('pc'));t.resume()
 else:
  pc=int(state['pc_before'],16);state['counter']=hex(t.read32(0x20005000))
  state['returned_to_flash']=0<=pc<0x80000
  state['still_in_ram_loop']=0x20000000<=pc<0x20000010
  t.resume()
 (out/f'G-reset-{a.mode}.json').write_text(json.dumps(state,indent=2)+'\n')
 print(json.dumps(state,indent=2))
