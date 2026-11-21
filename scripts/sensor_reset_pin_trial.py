#!/usr/bin/env python3
"""Temporary test of P0.21 as a GPIO; restores UICR when finished.
Erases only UICR; keeps the defined bootloader and NFCPINS fields.
Uses scanner-r18.bin, which filters out I2C pairs that contain P0.21.
"""
import hashlib, json, subprocess, sys, time
from pathlib import Path
from pyocd.core.helpers import ConnectHelper
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/sensors-r17-2026-11-19'
ADDRS=list(range(0x14,0x100,4))+[0x200,0x204,0x208,0x20c]
OPTS=dict(target_override='nrf52832',frequency=1000000,auto_unlock=False)
def session():return ConnectHelper.session_with_chosen_probe(options=OPTS)
def ready(t):
 end=time.monotonic()+2
 while not t.read32(0x4001e400):
  if time.monotonic()>end:raise TimeoutError('NVMC READY')
def program(t,words):
 t.halt()
 t.write32(0x4001e504,2);ready(t)
 t.write32(0x4001e514,1);ready(t)
 t.write32(0x4001e504,1);ready(t)
 for off,val in words.items():
  if val!=0xffffffff:
   t.write32(0x10001000+off,val);ready(t)
 t.write32(0x4001e504,0);ready(t)
 for off,val in words.items():
  actual=t.read32(0x10001000+off)
  if actual!=val:raise RuntimeError(f'UICR {off:x}: {actual:x} != {val:x}')
 t.reset_and_halt()
 print('UICR verified', {hex(k):hex(words[k]) for k in (0x14,0x200,0x204,0x208,0x20c)},flush=True)
with session() as s:
 t=s.target;t.reset_and_halt()
 saved={o:t.read32(0x10001000+o) for o in ADDRS}
 assert saved[0x200]==saved[0x204]==21
 assert saved[0x208]==0xffffffff
 (OUT/'uicr-before-p21.json').write_text(json.dumps({hex(k):hex(v) for k,v in saved.items()},indent=2)+'\n')
 original_boot_hash=hashlib.sha256(bytes(t.read_memory_block8(0x74000,0xc000))).hexdigest()
trial=dict(saved);trial[0x200]=trial[0x204]=0xffffffff
try:
 with session() as s:program(s.target,trial)
 subprocess.run([sys.executable,str(ROOT/'tools/ram-scanner/run_scanner.py'),'--image',str(ROOT/'tools/ram-scanner/scanner-r18.bin'),'--require-pin','21','--power','','--cs','','--i2c','2,3,4,5,6,7,8,9,10,11,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31','--timeout','90'],check=True)
finally:
 with session() as s:
  program(s.target,saved)
  final_hash=hashlib.sha256(bytes(s.target.read_memory_block8(0x74000,0xc000))).hexdigest()
  print('bootloader SHA256 before/after', original_boot_hash,final_hash,flush=True)
  assert final_hash==original_boot_hash
  s.target.reset()
 print('P0.21 restored as reset',flush=True)
