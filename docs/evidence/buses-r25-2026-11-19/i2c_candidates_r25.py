#!/usr/bin/env python3
"""Targeted W/R probes for LIS2DH12/BMP280 on pairs chosen after the OD matrix.
Reuses bus_probe and i2c_trial_r24. No flash/UICR. Radio disabled.
Uses no enables and no high drive. Does not attempt ID automatically.
"""
import argparse,hashlib,itertools,json,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
from bus_probe import I2CProbe
from i2c_trial_r24 import SWDLines,P

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--matrix',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--uart-disconnected',action='store_true')
 ap.add_argument('--addresses',default='0x18,0x19,0x76,0x77')
 a=ap.parse_args();matrix=json.loads(a.matrix.read_text())
 if matrix[-1].get('kind')!='closure' or not matrix[-1].get('bootloader') or not matrix[-1].get('unchanged'):ap.error('incomplete matrix or invalid closure')
 if a.uart_disconnected and not matrix[0].get('uart_disconnected_report'):ap.error('the matrix does not include UART disconnected')
 skip={0,1,21}|(set() if a.uart_disconnected else {12,13})
 pins=[r['pin'] for r in matrix if r['kind']=='pin' and r['can_low'] and r['can_high'] and r['pin'] not in skip]
 pairs=[(x,y) for x,y in itertools.permutations(pins,2) if {x,y}!={14,15}]
 addrs=[int(v,0) for v in a.addresses.split(',')]
 if not all(8<=v<120 for v in addrs):ap.error('address out of range 0x08–0x77')
 a.out.mkdir(parents=True,exist_ok=True)
 with (a.out/'probes.jsonl').open('w') as log:
  def emit(v):log.write(json.dumps({'unix':time.time(),**v})+'\n');log.flush()
  emit({'kind':'parameters','pins':pins,'pairs':pairs,'addresses':addrs,'pullup':True,'radio':'disabled','enables':'none','uart_disconnected_report':a.uart_disconnected})
  with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
   t=s.target;t.halt()
   def digest(addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
   def release():
    for p in range(32):
     if p not in skip:t.write32(P+0x700+4*p,0)
   before=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
   try:
    t.reset_and_halt();t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
    for reg,val in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,val)
    t.resume();t.write32(0x40001010,1);time.sleep(.02)
    assert t.read32(0x40001550)==0
    release()
    control=I2CProbe(SWDLines(t,(2,8),True,lambda v:None),2,8)
    e=control.electrical();emit({'kind':'control_electrical',**e})
    assert e['valid'],'control 2/8 invalid'
    for addr in addrs:
     for read in (False,True):
      r=control.address(addr,read);emit({'kind':'control_probe',**r})
      assert r['status']=='nack','control 2/8 did not produce a valid NACK'
    release()
    for x,y in pairs:
     release();io=SWDLines(t,(x,y),True,lambda v:None)
     bus=I2CProbe(io,x,y);e=bus.electrical();emit({'kind':'electrical','sda':x,'scl':y,**e})
     if not e['valid']:continue
     ack=[]
     for addr in addrs:
      for read in (False,True):
       r=bus.address(addr,read);emit({'kind':'probe','sda':x,'scl':y,**r})
       if r['status']=='ack':ack.append(addr)
       if r['status'] not in ('ack','nack'):break
     if ack:
      for passno in range(1,4):
       for addr in sorted({v for z in ack for v in (z-1,z,z+1) if 8<=v<120}):
        for read in (False,True):emit({'kind':'repeat','pass':passno,'sda':x,'scl':y,**bus.address(addr,read)})
     release();print('SDA',x,'SCL',y,'ACK',sorted(set(ack)),flush=True)
    emit({'kind':'completed'})
   finally:
    t.halt();release();after=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
    t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
    emit({'kind':'closure','pc':hex(pc),'bootloader':0x74000<=pc<0x80000,'hashes':after,'unchanged':before==after});t.resume()
    assert before==after and 0x74000<=pc<0x80000
if __name__=='__main__':main()
