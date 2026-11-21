#!/usr/bin/env python3
"""I2C scan of the nRF52832 driving the TWI0 peripheral over SWD (core halted).

Usage: python3 scripts/i2c_scan_swd.py SDA SCL [PIN{H|L} ...]

Example: python3 scripts/i2c_scan_swd.py 6 7 14H 15H
Each PINH/PINL is set as an output HIGH/LOW before the scan (sensor power or
enable).
Resets the chip when finished.
"""
import sys
import time

from pyocd.core.helpers import ConnectHelper

P0 = 0x50000000
OUTSET, OUTCLR, IN = P0 + 0x508, P0 + 0x50C, P0 + 0x510
PIN_CNF = P0 + 0x700
TWI = 0x40003000
STARTRX, STOP = TWI + 0x000, TWI + 0x014
EV_STOPPED, EV_RXDREADY, EV_ERROR = TWI + 0x104, TWI + 0x108, TWI + 0x124
SHORTS, ERRORSRC, ENABLE = TWI + 0x200, TWI + 0x4C4, TWI + 0x500
PSEL_SCL, PSEL_SDA, RXD, FREQ, ADDR = TWI + 0x508, TWI + 0x50C, TWI + 0x518, TWI + 0x524, TWI + 0x588

sda, scl = int(sys.argv[1]), int(sys.argv[2])
enables = [(int(x[:-1]), x[-1].upper()) for x in sys.argv[3:]]

opts = dict(target_override='nrf52832', frequency=1000000, auto_unlock=False)
with ConnectHelper.session_with_chosen_probe(options=opts) as s:
    t = s.target
    t.halt()
    for e, lvl in enables:
        t.write32(OUTSET if lvl == 'H' else OUTCLR, 1 << e)
        t.write32(PIN_CNF + 4 * e, 0x3)
    for p in (sda, scl):
        t.write32(PIN_CNF + 4 * p, 0x608)  # S0D1, no internal pull: the external pull-ups are visible
    time.sleep(0.05)
    lv = t.read32(IN)
    print(f'idle levels: SDA P0.{sda:02d}={lv >> sda & 1}  SCL P0.{scl:02d}={lv >> scl & 1}')
    t.write32(ENABLE, 0)
    t.write32(PSEL_SCL, scl)
    t.write32(PSEL_SDA, sda)
    t.write32(FREQ, 0x01980000)  # 100 kHz
    t.write32(ENABLE, 5)
    found = []
    for a in range(0x08, 0x78):
        for ev in (EV_STOPPED, EV_RXDREADY, EV_ERROR):
            t.write32(ev, 0)
        t.write32(ERRORSRC, 0x7)
        t.write32(ADDR, a)
        t.write32(SHORTS, 0x2)  # BB_STOP: one byte and STOP
        t.write32(STARTRX, 1)
        end = time.time() + 0.05
        ok = err = False
        while time.time() < end:
            if t.read32(EV_RXDREADY):
                ok = True
                break
            if t.read32(EV_ERROR):
                err = True
                break
        if not ok:
            t.write32(STOP, 1)
        end = time.time() + 0.05
        while time.time() < end and not t.read32(EV_STOPPED):
            pass
        if ok:
            found.append((a, t.read32(RXD) & 0xFF))
    t.write32(ENABLE, 0)
    print('devices:', ', '.join(f'0x{a:02X} (reads 0x{b:02X})' for a, b in found) or 'none')
    for p in [sda, scl] + [e for e, _ in enables]:
        t.write32(PIN_CNF + 4 * p, 0x2)
    t.reset()
