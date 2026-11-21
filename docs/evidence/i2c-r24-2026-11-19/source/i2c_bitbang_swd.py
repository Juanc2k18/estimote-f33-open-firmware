#!/usr/bin/env python3
"""I2C scan by bit-banging GPIOs over SWD (core halted). Slow (~100 Hz)
but independent of peripherals: every edge is a register write.

Usage: python3 scripts/i2c_bitbang_swd.py SDA SCL [PIN{H|L} ...] [--read ADDR REG N]

The PINH/PINL are set as outputs HIGH/LOW beforehand (sensor power).
The lines use emulated open drain: OUT=0 and DIR is toggled; the high level comes
from the external pull-ups.
"""
import sys
import time

from pyocd.core.helpers import ConnectHelper

P0 = 0x50000000
OUTSET, OUTCLR, IN, DIRSET, DIRCLR = (P0 + o for o in (0x508, 0x50C, 0x510, 0x518, 0x51C))
PIN_CNF = P0 + 0x700

args = sys.argv[1:]
pullup = '--pullup' in args
if pullup: args.remove('--pullup')
read_req = None
if '--read' in args:
    i = args.index('--read')
    read_req = tuple(int(x, 0) for x in args[i + 1:i + 4])
    args = args[:i]
sda, scl = int(args[0]), int(args[1])
enables = [(int(x[:-1]), x[-1].upper()) for x in args[2:]]

opts = dict(target_override='nrf52832', frequency=100000, auto_unlock=False)
with ConnectHelper.session_with_chosen_probe(options=opts) as s:
    t = s.target
    t.reset_and_halt()
    for e, lvl in enables:
        t.write32(OUTSET if lvl == 'H' else OUTCLR, 1 << e)
        t.write32(PIN_CNF + 4 * e, 0x3)
    for p in (sda, scl):
        t.write32(PIN_CNF + 4 * p, 0xC if pullup else 0x0)  # optional pull-up
    t.write32(OUTCLR, (1 << sda) | (1 << scl))
    time.sleep(0.1)

    def low(p): t.write32(DIRSET, 1 << p)
    def rel(p): t.write32(DIRCLR, 1 << p)
    def rd(p): return t.read32(IN) >> p & 1

    def start():
        rel(sda); rel(scl); low(sda); low(scl)

    def stop():
        low(sda); rel(scl); rel(sda)

    def write_byte(b):
        for i in range(7, -1, -1):
            (rel if b >> i & 1 else low)(sda)
            rel(scl); low(scl)
        rel(sda); rel(scl)
        ack = rd(scl) == 1 and rd(sda) == 0
        low(scl)
        return ack

    def read_byte(ack):
        rel(sda)
        v = 0
        for _ in range(8):
            rel(scl)
            v = v << 1 | rd(sda)
            low(scl)
        (low if ack else rel)(sda)
        rel(scl); low(scl); rel(sda)
        return v

    print(f'idle: SDA P0.{sda:02d}={rd(sda)}  SCL P0.{scl:02d}={rd(scl)}')
    if not (rd(sda) and rd(scl)):
        t.reset()
        raise SystemExit('INVALID BUS: SDA/SCL are not high at idle; ACK cannot be interpreted')
    if read_req:
        addr, reg, n = read_req
        start(); a1 = write_byte(addr << 1); a2 = write_byte(reg)
        start(); a3 = write_byte(addr << 1 | 1)
        data = [read_byte(i < n - 1) for i in range(n)]
        stop()
        print(f'0x{addr:02X} reg 0x{reg:02X}: ACK {a1},{a2},{a3} ->', ' '.join(f'{d:02X}' for d in data))
    else:
        found = []
        for a in range(0x08, 0x78):
            start()
            if write_byte(a << 1 | 1):
                read_byte(False)
                found.append(a)
            stop()
        print('devices:', ', '.join(f'0x{a:02X}' for a in found) or 'none')
    for p in [sda, scl] + [e for e, _ in enables]:
        t.write32(PIN_CNF + 4 * p, 0x2)
    t.reset()
