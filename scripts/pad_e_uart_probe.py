#!/usr/bin/env python3
"""R26: identifies the E←P0.18 route with a UART nonce pattern via RAM/SWD.
Receive only on Pico GP5/pin7. Does not transmit from the Pico. No flash/UICR.
A negative reception does not rule out the route (levels/logic/wiring).
"""
import argparse,hashlib,json,os,secrets,select,termios,time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
U=0x40002000;P=0x50000000

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',required=True);ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--e-volts',type=float,required=True);a=ap.parse_args()
 if not 0<=a.e_volts<=3.3:ap.error('E/F out of range for the Pico receiver')
 a.out.mkdir(parents=True,exist_ok=True)
 nonce=secrets.token_hex(4);frames=[f'R26-P18-{nonce}-{n:02d}\r\n'.encode() for n in range(6)]
 log=(a.out/'events.jsonl').open('w')
 def emit(v):log.write(json.dumps({'unix':time.time(),**v})+'\n');log.flush()
 fd=os.open(a.port,os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK);attrs=termios.tcgetattr(fd);saved=list(attrs);saved[6]=list(attrs[6])
 attrs[0]=attrs[1]=attrs[3]=0;attrs[2]=termios.CS8|termios.CREAD|termios.CLOCAL;attrs[4]=attrs[5]=termios.B9600
 termios.tcsetattr(fd,termios.TCSANOW,attrs);termios.tcflush(fd,termios.TCIFLUSH)
 def capture(seconds):
  raw=bytearray();end=time.monotonic()+seconds
  while time.monotonic()<end:
   if select.select([fd],[],[],min(.05,max(0,end-time.monotonic())))[0]:raw.extend(os.read(fd,4096))
  return bytes(raw)
 def digest(t,addr,n):return hashlib.sha256(bytes(t.read_memory_block8(addr,n))).hexdigest()
 try:
  emit({'kind':'parameters','e_volts_report':a.e_volts,'e_connection_report':'E→Pico physical 7 GP5/RX, GP4 disconnected','baud':9600,'tx_pin':18,'nonce':nonce,'expected_hex':[f.hex() for f in frames]})
  with ConnectHelper.session_with_chosen_probe(options=dict(target_override='nrf52832',frequency=100000,auto_unlock=False,connect_mode='attach')) as s:
   t=s.target;t.halt();before=[digest(t,0x74000,0xc000),digest(t,0x10001000,0x400)]
   try:
    t.resume();baseline=capture(2);(a.out/'baseline-rx.bin').write_bytes(baseline);emit({'kind':'baseline_rx','hex':baseline.hex()})
    t.reset_and_halt();t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
    for reg,val in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:t.write_core_register(reg,val)
    t.resume();t.write32(0x40001010,1);time.sleep(.02);assert t.read32(0x40001550)==0
    t.write32(U+0x500,0)
    for off,val in [(0x508,0xffffffff),(0x50c,18),(0x510,0xffffffff),(0x514,0xffffffff),(0x524,0x00275000),(0x56c,0)]:t.write32(U+off,val)
    t.write32(P+0x508,1<<18);t.write32(P+0x700+4*18,1)
    t.write32(U+0x500,4);t.write32(U+8,1)
    emit({'kind':'uart_config','registers':{hex(off):hex(t.read32(U+off)) for off in (0x500,0x508,0x50c,0x510,0x514,0x524,0x56c)},'p18_cnf':hex(t.read32(P+0x700+4*18))})
    rx=bytearray(capture(.1));txcount=0
    for frame in frames:
     for byte in frame:
      t.write32(U+0x11c,0);t.write32(U+0x51c,byte)
      end=time.monotonic()+.3
      while not t.read32(U+0x11c):
       if time.monotonic()>=end:raise TimeoutError('UART TXDRDY no responde')
      txcount+=1
     rx.extend(capture(.2));emit({'kind':'sent','frame_hex':frame.hex(),'tx_bytes':txcount})
    rx.extend(capture(.5));t.write32(U+0xc,1);t.write32(U+0x500,0);t.write32(P+0x700+4*18,0)
    (a.out/'active-rx.bin').write_bytes(rx);off=capture(1);(a.out/'off-rx.bin').write_bytes(off)
    matches=[f.decode().strip() for f in frames if f in rx]
    result={'kind':'result','received_hex':bytes(rx).hex(),'off_hex':off.hex(),'matched_frames':matches,'baseline_matches':sum(f in baseline for f in frames),'tx_bytes':txcount,'route_positive':len(matches)>=3}
    emit(result);(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
   finally:
    t.halt();t.write32(U+0x500,0);t.write32(P+0x700+4*18,0)
    after=[digest(t,0x74000,0xc000),digest(t,0x10001000,0x400)]
    t.reset();time.sleep(.4);t.halt();pc=t.read_core_register('pc')
    emit({'kind':'closure','hashes_before':before,'hashes_after':after,'unchanged':before==after,'pc':hex(pc),'bootloader':0x74000<=pc<0x80000,'radio':t.read32(0x40001550)})
    t.resume();assert before==after and 0x74000<=pc<0x80000
 finally:
  termios.tcsetattr(fd,termios.TCSANOW,saved);os.close(fd);log.close()
if __name__=='__main__':main()
