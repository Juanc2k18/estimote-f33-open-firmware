#!/usr/bin/env python3
"""Survey of the nRF52832 GPIOs over SWD to locate sensor buses and power.

Halts the core, configures each pin as an input (no pull, pull-down, pull-up) and reads
P0.IN. A pin that stays high with pull-down has a strong external pull-up or is
driven (typical of I2C SDA/SCL); one that stays low with pull-up is driven or
has an external pull-down. Resets the chip when finished.

Skipped: P0.00/P0.01 (32 kHz crystal), P0.09/P0.10 if they are in NFC mode,
P0.12/P0.13 (UART on E2/E1) and P0.21 (nRESET).
"""
import time

from pyocd.core.helpers import ConnectHelper

P0 = 0x50000000
IN = P0 + 0x510
PIN_CNF = P0 + 0x700
UICR_NFCPINS = 0x1000120C
CFG = {'no pull': 0x0, 'pull-down': 0x4, 'pull-up': 0xC}

opts = dict(target_override='nrf52832', frequency=1000000, auto_unlock=False)
with ConnectHelper.session_with_chosen_probe(options=opts) as s:
    t = s.target
    t.halt()
    nfc = t.read32(UICR_NFCPINS)
    skip = {0, 1, 12, 13, 21}
    if nfc & 1:
        skip |= {9, 10}
    pins = [p for p in range(32) if p not in skip]
    print('UICR.NFCPINS', hex(nfc), '· skipped', sorted(skip))
    saved = {p: t.read32(PIN_CNF + 4 * p) for p in pins}
    res = {}
    for name, cfg in CFG.items():
        for p in pins:
            t.write32(PIN_CNF + 4 * p, cfg)
        time.sleep(0.01)
        res[name] = t.read32(IN)
    for p in pins:
        t.write32(PIN_CNF + 4 * p, saved[p])
    print('pin  ' + '  '.join(f'{n:>9}' for n in CFG) + '  interpretation')
    for p in pins:
        v = [(res[n] >> p) & 1 for n in CFG]
        if v == [0, 0, 1]:
            note = 'floating'
        elif v == [1, 1, 1]:
            note = 'stuck HIGH (external pull-up or output high)'
        elif v == [0, 0, 0]:
            note = 'stuck LOW (to GND or output low)'
        else:
            note = 'mixed'
        print(f'P0.{p:02d} ' + '  '.join(f'{x:>9}' for x in v) + '  ' + note)
    t.reset()
