#!/usr/bin/env python3
"""Reads the Nordic CTRL-AP (AP#1) of the nRF52 and, optionally, clears or erases.

Usage:
  python3 scripts/nrf_ctrlap.py           # read CTRL-AP registers only
  python3 scripts/nrf_ctrlap.py clear     # ERASEALL=0 and reset pulse through CTRL-AP
  python3 scripts/nrf_ctrlap.py erase     # full erase (ERASEALL): destroys flash and UICR

APPROTECTSTATUS: 0 = protection active, 1 = unprotected.
Written because `pyocd erase --mass` (0.46.1) reported a timeout even though the erase
had finished (r13, 2026-11-19).
"""
import sys
import time

from pyocd.core.session import Session
from pyocd.probe.aggregator import DebugProbeAggregator

REGS = [('RESET', 0x00), ('ERASEALL', 0x04), ('ERASEALLSTATUS', 0x08),
        ('APPROTECTSTATUS', 0x0C), ('IDR', 0xFC)]


def main():
    probe = DebugProbeAggregator.get_all_connected_probes()[0]
    with Session(probe, frequency=1000000):
        probe.connect()
        print('DP IDR', hex(probe.read_dp(0x0)))
        probe.write_dp(0x0, 0x1E)        # ABORT: clear sticky errors
        probe.write_dp(0x4, 0x50000000)  # CTRL/STAT: debug and system power-up
        t = time.time()
        while (probe.read_dp(0x4) & 0xA0000000) != 0xA0000000 and time.time() - t < 1:
            pass

        def rap(reg):
            probe.write_dp(0x8, (1 << 24) | (reg & 0xF0))  # SELECT: APSEL=1
            return probe.read_ap((1 << 24) | reg)

        def wap(reg, value):
            probe.write_dp(0x8, (1 << 24) | (reg & 0xF0))
            probe.write_ap((1 << 24) | reg, value)

        for name, reg in REGS:
            print(name, hex(rap(reg)))

        if 'erase' in sys.argv:
            wap(0x00, 1)
            wap(0x04, 1)
            t = time.time()
            while time.time() - t < 30 and rap(0x08) != 0:
                time.sleep(0.1)
            print('ERASEALLSTATUS', hex(rap(0x08)), 'after', round(time.time() - t, 2), 's')
        if 'erase' in sys.argv or 'clear' in sys.argv:
            wap(0x04, 0)
            wap(0x00, 1)
            time.sleep(0.05)
            wap(0x00, 0)
            time.sleep(0.2)
            for name, reg in REGS[1:4]:
                print('after reset', name, hex(rap(reg)))


if __name__ == '__main__':
    main()
