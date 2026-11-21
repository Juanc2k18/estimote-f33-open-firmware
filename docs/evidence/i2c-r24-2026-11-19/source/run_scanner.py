#!/usr/bin/env python3
"""Loads scanner.bin into the nRF52832 RAM over SWD, runs it and shows the results.
Does not touch flash. Resets the chip when finished (the bootloader comes back).

Usage: python3 tools/ram-scanner/run_scanner.py [--power 14,15] [--cs 6,7]
                                              [--sck ...] [--miso ...] [--i2c ...]
"""
import argparse
import struct
import time
from pathlib import Path

from pyocd.core.helpers import ConnectHelper

HERE = Path(__file__).resolve().parent
RES = 0x20006000
SKIP = {0, 1, 9, 10, 12, 13, 21}


def mask(s):
    return sum(1 << int(x) for x in s.split(',') if x != '')


ap = argparse.ArgumentParser()
ap.add_argument('--image', type=Path, default=HERE / 'scanner.bin')
ap.add_argument('--require-pin', type=int)
ap.add_argument('--spi-stats', action='store_true', help='scanner-r24-spi ABI only: electrical counters')
ap.add_argument('--mosi', help='scanner-r18-spi only: independent MOSI mask')
ap.add_argument('--frequency', type=int, default=1000000)
ap.add_argument('--power', default='14,15')
ap.add_argument('--low', default='')
ap.add_argument('--cs', default='6,7')
free = [p for p in range(32) if p not in SKIP | {6, 7, 14, 15}]
low_fixed = [3, 4, 11, 22, 25]
ap.add_argument('--sck', default=','.join(str(p) for p in free if p not in low_fixed))
ap.add_argument('--miso', default=','.join(str(p) for p in free))
ap.add_argument('--i2c', default=','.join(str(p) for p in range(32) if p not in SKIP | {14, 15}))
ap.add_argument('--timeout', type=float, default=600)
a = ap.parse_args()
if a.spi_stats:
    if mask(a.i2c): ap.error('r24 is SPI only: use an empty --i2c')
    if mask(a.power) & (3 << 14) == (3 << 14): ap.error('r24: never 14 and 15 high together')
    if mask(a.sck) & mask('3,4,11,22,25'): ap.error('r24: clocks with a history of SWD loss are excluded')
if a.mosi is not None and a.require_pin is not None:
    ap.error('--mosi and --require-pin are mutually exclusive')

image = a.image.read_bytes()
opts = dict(target_override='nrf52832', frequency=a.frequency, auto_unlock=False)
with ConnectHelper.session_with_chosen_probe(options=opts) as s:
    t = s.target
    try:
        t.reset_and_halt()
        t.write_memory_block8(0x20000000, list(image))
        for p in [int(x) for x in a.low.split(',') if x]:
            if p in {0,1,12,13,21}: raise ValueError('reserved pin')
            t.write32(0x5000050C, 1 << p)
            t.write32(0x50000700 + 4*p, 1)
        hdr = struct.pack('<9I', mask(a.mosi) if a.mosi is not None else (0 if a.require_pin is None else a.require_pin+1), 0, 0, 0, mask(a.power), mask(a.sck), mask(a.miso), mask(a.cs), mask(a.i2c))
        t.write_memory_block8(RES, list(hdr))
        t.write_core_register('pc', 0x20000001 & ~1)
        t.write_core_register('xpsr', 1 << 24)
        t.write_core_register('sp', 0x20010000)
        t.resume()
        start = time.time()
        while time.time() - start < a.timeout:
            time.sleep(2)
            done = t.read32(RES + 4)
            print(f'\r{time.time() - start:5.0f} s · SPI combinations {t.read32(RES + 12)} · findings {t.read32(RES + 8)}', end='', flush=True)
            if done:
                break
        print()
        t.halt()
        print('core', {r: hex(t.read_core_register(r)) for r in ('pc', 'xpsr', 'sp')}, 'CFSR', hex(t.read32(0xE000ED28)), 'HFSR', hex(t.read32(0xE000ED2C)))
        count = t.read32(RES + 8)
        raw = bytes(t.read_memory_block8(RES + 36, 8 * min(count, 120)))
        for i in range(min(count, 120)):
            kind, cs, sck, mosi, miso, mode, reg, val = raw[8 * i:8 * i + 8]
            if kind == 1:
                print(f'SPI  CS P0.{cs:02d}  SCK P0.{sck:02d}  MOSI P0.{mosi:02d}  MISO P0.{miso:02d}  mode {mode}  cmd 0x{reg:02X} -> 0x{val:02X}')
            else:
                print(f'I2C  SDA P0.{mosi:02d}  SCL P0.{sck:02d}  address 0x{reg:02X}  first byte 0x{val:02X}')
        if a.spi_stats:
            names = ('cs_not_low', 'sck_not_toggle', 'completed', 'no_signature', 'signatures', 'validation_incomplete', 'cs_not_high')
            values = struct.unpack('<7I', bytes(t.read_memory_block8(RES + 36 + 120 * 8, 28)))
            print('SPI stats', dict(zip(names, values)))
        print('total', count, '· finished' if t.read32(RES + 4) else '· NOT FINISHED')
    finally:
        t.halt()
        t.reset()
