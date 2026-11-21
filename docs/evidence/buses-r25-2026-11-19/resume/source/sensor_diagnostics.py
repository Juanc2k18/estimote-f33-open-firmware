#!/usr/bin/env python3
"""r17 diagnostics: SAADC and TWI with the CPU running a loop in RAM; no flash.
Does not drive UART P0.12/13 (Pico connected), the crystal or SWD. Reset in finally.
"""
import argparse, json, struct, time
from pyocd.core.helpers import ConnectHelper
P=0x50000000
A=0x40007000
T=0x40003000
ap=argparse.ArgumentParser()
ap.add_argument('mode', choices=['adc','twi','matrix','coupling'])
ap.add_argument('--power', default='')
ap.add_argument('--watch', action='store_true')
ap.add_argument('--sda', type=int, default=6)
ap.add_argument('--scl', type=int, default=7)
a=ap.parse_args()
enables=[(int(x[:-1]),x[-1].upper()) for x in a.power.split(',') if x]
assert all(p not in {0,1,9,10,12,13,21} and l in 'HL' for p,l in enables)
with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=4000000,auto_unlock=False)) as s:
 t=s.target
 def w(addr,v): t.write32(addr,v)
 def wait(addr,limit=.15):
  end=time.monotonic()+limit
  while time.monotonic()<end:
   if t.read32(addr): return True
  return False
 try:
  t.reset_and_halt()
  print(json.dumps({'mode':a.mode,'power':enables,'ficr':hex(t.read32(0x10000100)),'nfcpins':hex(t.read32(0x1000120c)),'resetpins':[hex(t.read32(x)) for x in (0x10001200,0x10001204)]}),flush=True)
  # CPSID i; B .  Core running, so peripheral clocks are not debug-halted.
  t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
  t.write_core_register('pc',0x20000000); t.write_core_register('xpsr',1<<24)
  t.write_core_register('sp',0x20010000)
  t.resume()
  for p,l in enables:
   w(P+(0x508 if l=='H' else 0x50c),1<<p); w(P+0x700+4*p,3)
  time.sleep(.2)
  if a.mode=='adc':
   for ch in range(8): w(A+0x510+16*ch,0); w(A+0x514+16*ch,0)
   w(A+0x518,5<<16) # internal .6V, gain 1/6, 40us, single ended
   w(A+0x5f0,2); w(A+0x500,1)
   w(A+0x110,0); w(A+0xc,1)
   print('calibrated',wait(A+0x110),flush=True)
   for ain,p in enumerate([2,3,4,5,28,29,30,31,None],1):
    if a.watch and p != 5: continue
    vals=[]
    for pull in ([0] if a.watch else ([0,4,12] if p is not None else [0])):
     if p is not None: w(P+0x700+4*p,pull)
     time.sleep(.01)
     w(A+0x510,ain)
     samples=[]
     for _ in range(120 if a.watch else 4):
      w(A+0x62c,0x20005000); w(A+0x630,1)
      w(A+0x100,0);w(A+0x104,0); w(A,1)
      started=wait(A+0x100)
      w(A+4,1); ended=wait(A+0x104)
      if not ended: raise RuntimeError('ADC without END')
      value=struct.unpack('<h',bytes(t.read_memory_block8(0x20005000,2)))[0]
      samples.append(value)
      if a.watch:
       print(json.dumps({'unix':time.time(),'pin':p,'raw':value,'mV':round(value*3600/4096,2)}),flush=True)
       time.sleep(.5)
      w(A+0x114,0);w(A+8,1);wait(A+0x114)
     vals.append({'pull':pull,'raw':samples,'mV':[round(v*3600/4096,1) for v in samples]})
    print(json.dumps({'ain':ain,'pin':p,'samples':vals}),flush=True)
   w(A+0x500,0)
  elif a.mode=='coupling':
   pins=[6,7,9,10,14,15]
   for p in pins: w(P+0x700+4*p,12)
   for p in (14,15): w(P+0x508,1<<p);w(P+0x700+4*p,1)
   for driven in (6,7,9,10):
    for level in ('Z','L','Z','H','Z'):
     w(P+(0x508 if level=='H' else 0x50c),1<<driven)
     w(P+0x700+4*driven,12 if level=='Z' else 1)
     time.sleep(.15)
     val=t.read32(P+0x510)
     print(json.dumps({'driven':driven,'level':level,'pins':{p:val>>p&1 for p in pins}}),flush=True)
  elif a.mode=='matrix':
   import itertools
   for levels in itertools.product('ZLH',repeat=2):
    for p,l in zip((14,15),levels):
     w(P+(0x508 if l=='H' else 0x50c),1<<p)
     w(P+0x700+4*p,0 if l=='Z' else 1)
    rows=[]
    for pull in (0,4,12):
     for p in (6,7): w(P+0x700+4*p,pull)
     time.sleep(.25)
     v=t.read32(P+0x510)
     rows.append({'pull':pull,'p6':v>>6&1,'p7':v>>7&1})
    print(json.dumps({'levels':levels,'rows':rows}),flush=True)
  else:
   for p in (a.sda,a.scl): w(P+0x700+4*p,0x60c)
   w(P+0x508,(1<<a.sda)|(1<<a.scl))
   w(T+0x500,0);w(T+0x508,a.scl);w(T+0x50c,a.sda)
   w(T+0x524,0x01980000);w(T+0x500,5);w(T+0x200,2)
   print('idle',hex(t.read32(P+0x510)), 'config', {hex(o):hex(t.read32(T+o)) for o in (0x500,0x508,0x50c,0x524)},flush=True)
   stats={};found=[]
   for addr in range(8,120):
    for off in (0x104,0x108,0x124):w(T+off,0)
    w(T+0x4c4,7);w(T+0x588,addr);w(T,1)
    end=time.monotonic()+.03
    while time.monotonic()<end:
     if t.read32(T+0x108) or t.read32(T+0x124):break
    rx=t.read32(T+0x108);err=t.read32(T+0x4c4)
    key=f'rx={rx},err={err}';stats[key]=stats.get(key,0)+1
    if rx:found.append([addr,t.read32(T+0x518)])
    w(T+0x14,1);wait(T+0x104,.03)
   print(json.dumps({'sda':a.sda,'scl':a.scl,'stats':stats,'found':found}),flush=True)
 finally:
  t.halt();t.reset()
  print('RESET: bootloader restored',flush=True)
