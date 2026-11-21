#!/usr/bin/env python3
"""R26 SWO NRZ: the CPU writes bytes to ITM STIM0 from RAM; the Pico only receives.
Nordic nrfx 3.14.0 and CMSIS registers. No nRF UART and no flash/UICR.
"""
import argparse,hashlib,json,os,secrets,select,struct,termios,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
P=0x50000000; ITM=0xE0000000;TPI=0xE0040000

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--trace-clock',type=int,choices=(32000000,64000000),default=32000000);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 nonce=secrets.token_hex(4);frames=[f'R26-SWO-{nonce}-{n:02d}\r\n'.encode() for n in range(6)];payload=b''.join(frames)
 image=Path('tools/ram-scanner/pad-e-itm-r26.bin').read_bytes()
 fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK);saved=termios.tcgetattr(fd);attrs=list(saved);attrs[6]=list(saved[6]);attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[4]=attrs[5]=termios.B9600;termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
 def capture(seconds):
  raw=bytearray();end=time.monotonic()+seconds
  while time.monotonic()<end:
   if select.select([fd],[],[],min(.05,max(0,end-time.monotonic())))[0]:raw.extend(os.read(fd,4096))
  return bytes(raw)
 with (a.out/'events.jsonl').open('w') as f:
  def emit(v):f.write(json.dumps({'unix':time.time(),**v})+'\n');f.flush()
  try:
   with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
    t=s.target;t.halt()
    def digest(addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
    before=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
    try:
     t.resume();baseline=capture(1);(a.out/'baseline-rx.bin').write_bytes(baseline)
     t.reset_and_halt();t.write32(0x40002500,0);t.write_memory_block8(0x20000000,list(image));t.write_memory_block8(0x20005000,list(payload));t.write_memory_block8(0x20005400,list(struct.pack('<3I',len(payload),0,0)))
     # UART disabled. Serial trace uses P0.18 only, not other trace pins.
     t.write32(P+0x508,1<<18);t.write32(P+0x700+4*18,1)
     t.write32(0xE000EDFC,t.read32(0xE000EDFC)|(1<<24))
     t.write32(ITM+0xfb0,0xC5ACCE55);t.write32(ITM+0xe80,0);t.write32(ITM+0xe00,0)
     t.write32(0x4000055c,1<<16)
     t.write32(TPI+4,1);t.write32(TPI+0xf0,2);t.write32(TPI+0x10,round(a.trace_clock/9600)-1);t.write32(TPI+0x304,0x100)
     t.write32(ITM+0xe40,0);t.write32(ITM+0xe00,1);t.write32(ITM+0xe80,0x10011)
     regs={hex(addr):hex(t.read32(addr)) for addr in (0x40002500,0x4000055c,0xE000EDFC,ITM+0xe00,ITM+0xe80,ITM+0xfb4,TPI+4,TPI+0x10,TPI+0xf0,TPI+0x304,TPI+0xfc8)}
     emit({'kind':'configuration','trace_clock_assumed':a.trace_clock,'baud_receiver':9600,'registers':regs,'expected_frames_hex':[x.hex() for x in frames]})
     # No IRQ or RADIO code; reset defaults RADIO disabled.
     for reg,val in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,val)
     t.resume();raw=capture(3);t.halt();done=t.read32(0x20005404);sent=t.read32(0x20005408)
     emit({'kind':'cpu','done':done,'sent':sent,'pc':hex(t.read_core_register('pc')),'cfsr':hex(t.read32(0xE000ED28)),'hfsr':hex(t.read32(0xE000ED2c)),'radio':t.read32(0x40001550)})
     t.write32(ITM+0xe00,0);t.write32(ITM+0xe80,0);t.write32(0x4000055c,0);t.write32(P+0x700+4*18,0);off=capture(1)
     (a.out/'active-rx.bin').write_bytes(raw);(a.out/'off-rx.bin').write_bytes(off)
     # STIM0 u8 emits 0x01 header followed by payload byte. Require complete
     # identifiable ITM frames, not merely arbitrary UART characters.
     def wire(frame):return b''.join(bytes((1,b)) for b in frame)
     matches=[x.decode().strip() for x in frames if wire(x) in raw]
     result={'kind':'result','received_hex':raw.hex(),'matched_frames':matches,'cpu_done':done,'cpu_sent':sent,'uart_nrf_enabled':t.read32(0x40002500),'swo_positive':len(matches)>=3 and done==1 and sent==len(payload),'off_hex':off.hex(),'baseline_hex':baseline.hex()}
     emit(result);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    finally:
     t.halt();t.write32(ITM+0xe00,0);t.write32(ITM+0xe80,0);t.write32(0x4000055c,0);t.write32(P+0x700+4*18,0)
     after=[digest(0x74000,0xc000),digest(0x10001000,0x400)]
     t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc');emit({'kind':'closure','unchanged':before==after,'hashes':after,'pc':hex(pc),'bootloader':0x74000<=pc<0x80000,'traceconfig':t.read32(0x4000055c),'resetpins':[t.read32(x) for x in (0x10001200,0x10001204)]});t.resume();assert before==after and 0x74000<=pc<0x80000
  finally:termios.tcsetattr(fd,termios.TCSANOW,saved);os.close(fd)
if __name__=='__main__':main()
