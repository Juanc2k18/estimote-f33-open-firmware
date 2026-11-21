#!/usr/bin/env python3
"""Looks for the pin that powers or enables the sensors (nRF52832, over SWD).

For each candidate pin: the rest stay as inputs with pull-down; the candidate is
set as an output HIGH and then LOW for 30 ms. If other pins go high when doing so,
those pins have pull-ups to a supply that the candidate controls
(typical of I2C SDA/SCL or an SPI CS). Resets the chip when finished.

Accepted risk: a candidate tied to GND or to another output is short-circuited
for a few milliseconds with the nRF52 standard output current.
"""
import time

from pyocd.core.helpers import ConnectHelper

P0 = 0x50000000
OUTSET, OUTCLR, IN = P0 + 0x508, P0 + 0x50C, P0 + 0x510
PIN_CNF = P0 + 0x700
SKIP = {0, 1, 9, 10, 12, 13, 21}  # crystal, NFC, UART, reset

opts = dict(target_override='nrf52832', frequency=1000000, auto_unlock=False)
with ConnectHelper.session_with_chosen_probe(options=opts) as s:
    t = s.target
    t.halt()
    pins = [p for p in range(32) if p not in SKIP]
    if t.read32(0x1000120C) & 1 == 0:
        pins += [9, 10]
    for p in pins:
        t.write32(PIN_CNF + 4 * p, 0x4)  # input with pull-down
    time.sleep(0.01)
    base = t.read32(IN)
    print('baseline with pull-down:', [p for p in pins if base >> p & 1])
    for d in pins:
        for level, reg in (('HIGH', OUTSET), ('LOW', OUTCLR)):
            t.write32(reg, 1 << d)
            t.write32(PIN_CNF + 4 * d, 0x3)  # output, input buffer disconnected
            time.sleep(0.03)
            v = t.read32(IN)
            t.write32(PIN_CNF + 4 * d, 0x4)
            t.write32(OUTCLR, 1 << d)
            time.sleep(0.01)
            up = [p for p in pins if p != d and (v >> p & 1) and not (base >> p & 1)]
            if up:
                print(f'P0.{d:02d} {level}: rising {["P0.%02d" % p for p in up]}')
    for p in pins:
        t.write32(PIN_CNF + 4 * p, 0x2)  # reset value
    print('done')
    t.reset()
