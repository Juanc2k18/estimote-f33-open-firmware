# r26 · Pad E = P0.18 / SWO functionally confirmed

2026, America/Lima. **E corresponds functionally to P0.18, QFN48
pin 21 of the nRF52832, and carries SWO/ITM**. This updates the UWB hypothesis and the
historical r11 report of no continuity found. It is not a new ohmic
measurement nor proof of a direct connection without intermediate components.

## Setup and provenance

- The owner connected E to **Pico physical pin 7, GP5/RX**. After a measurement was requested
  with E removed from the Pico, they reported **2.43 V DC between E (+) and F (−)** and then
  confirmed E reconnected to pin 7. Multimeter/range/resolution not recorded.
- Pico GP4/physical pin 6 was left unconnected; UART E1/E2 removed in r25.
  SWD GP2/pin4→A, GP3/pin5→B and GND→F kept as in the confirmed setup.
  Last reported power supply 6 V on H/F, C without power supply, G free. The power supply was not changed.
- SWD responded at 100 kHz. Initial PC 0x750FE, PSELRESET=[21,21], P18.CNF=2
  (input buffer disconnected, so its initial IN=0 does not measure the physical
  level), TRACECONFIG=0. Bootloader/UICR with historical hashes.

## First test: GPIO route via a temporary UART

`scripts/pad_e_uart_probe.py` reuses the serial configuration of dfu_ping and the
RAM loop of the diagnostics. The Pico only receives: port opened O_RDONLY,
no `os.write` and no transmission from GP4. The nRF runs CPSID i/RAM loop; radio
TASKS_DISABLE and STATE=0. Legacy UART0 ENABLE=4, TXD=P0.18, RXD/CTS/RTS
unconnected (PSEL=FFFFFFFF), 9600 baud, 8N1, no HWFC/parity.

**126 bytes** were emitted, six 21-byte messages with a specific nonce and
counter 00–05: `R26-P18-27ff78e5-XX\r\n`. GPIO18 configured as a standard
output with input connected, PSELTXD read=18. The E→GP5 capture contains
**all six messages, complete and exact**, with no extra bytes. Two seconds of
prior reception: empty. After stopping/disabling the UART and releasing GPIO18:
one second of reception, empty. Return to the bootloader and identical hashes were
verified. This validates the functional route from GPIO18 to E, not yet SWO.

## Second test: real SWO from the Cortex-M4 ITM

`tools/ram-scanner/pad-e-itm-r26.c` is compiled for RAM. The core, with IRQs
disabled, reads the string from RAM and writes each byte with **STRB to ITM
STIM0 (0xE0000000)** after checking availability; it keeps a counter and state.
It does not call the UART. UART0 ENABLE=0 before and after this test.

`scripts/pad_e_swo_probe.py` configures:

- CLOCK.TRACECONFIG=0x00010000: TRACEMUX Serial, 32 MHz trace port clock,
  only P0.18 multiplexed as SWO; parallel trace is not enabled.
- DEMCR.TRCENA=1; ITM unlocked via LAR=C5ACCE55.
- ITM.TER=1 (stimulus 0), TPR=0, TCR=0x00010011.
- TPIU.CSPSR=1, SPPR=2 (SWO NRZ), ACPR=3332 and FFCR=0x100 (no continuous formatting).
  32 MHz/(3332+1) ≈ 9600.96 bit/s; Pico receiver configured at 9600 8N1.
- P0.18 with standard S0S1 drive. nRF UART disabled. The radio stayed
  in its disabled state after reset, STATE=0 read at the end of the run.

The core transmitted **126 bytes of ITM payload**: six distinct messages
`R26-SWO-cd605e34-00` to `...-05`, with CR/LF. RAM state DONE=1, counter=126,
PC in RAM=0x20000064, CFSR=HFSR=0. The capture contains **all six exact messages
with ITM header 0x01 in front of each byte**, characteristic of stimulus 0
with a one-byte payload. Arbitrary characters are not enough: each complete
message was checked against its ITM packet representation. An additional initial
0x00 was received, kept in the raw data, and not used to identify anything.

One-second prior control: empty. After turning ITM off, returning TRACECONFIG to GPIO
and releasing 18, one second with no reception. **SWO/ITM functionally validated** in
this setup at this speed and level. It does not verify Manchester, other speeds,
ETM/parallel trace, nor that the original Estimote firmware used SWO.

## Closure and current state

ITM/TER/TCR disabled, TRACECONFIG=0 and GPIO18 released before the reset.
Final reset: PC=0x750ec in the bootloader, PSELRESET=[21,21], core resumed.
Temporary UART disabled; the reset restores the bootloader's normal
configuration. No flash/UICR writes. Identical hashes before/after
both tests:

- Bootloader: `589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`
- UICR: `82ea7e308fcc09c6dd9dee4d9686e9e261f4848d49d6c540f9b1ea670dbc7ad7`

E remains physically connected to GP5/pin7 per confirmed report. E1/E2 and GP4
remain removed; do not route the Pico's TX back to pad E. Power did not change.
The pin documents were updated; no other graphic master was generated.

## Files and sources

`baseline.json`, `uart/events.jsonl`, `uart/*-rx.bin`, `uart/result.json`;
`swo-32/events.jsonl`, `swo-32/*-rx.bin`, `swo-32/result.json` contain raw data,
parameters, registers and controls. `source/` keeps the scripts and C (ELF and binary removed from publication on
2026; they are rebuilt with `tools/ram-scanner/`, hashes in `SHA256SUMS`);
`verification.json` and `SHA256SUMS` identify versions in a repo without commits.
The diagnosis uses received frames; there is no oscilloscope capture nor an
independent measurement of rise time or actual baud rate.

- [Nordic, nRF52832 pins](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html).
- [Nordic, debug and trace](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/dif.html).
- [Nordic nrfx v3.14.0 nrf52.h](https://github.com/NordicSemiconductor/nrfx/blob/v3.14.0/mdk/nrf52.h)
  and [bitfields](https://github.com/NordicSemiconductor/nrfx/blob/v3.14.0/mdk/nrf52_bitfields.h),
  originals saved in this folder. The master URLs served by search
  returned 404 when downloaded; this tagged version was used, with hashes.
- [Arm CMSIS, ITM/TPIU registers](https://arm-software.github.io/CMSIS_6/latest/Core/regMap_pg.html).
- [Pico, pinout](https://datasheets.raspberrypi.com/pico/Pico-R3-A4-Pinout.pdf).

Repetition with the confirmed setup (E/F previously measured):

```bash
python3 scripts/pad_e_uart_probe.py --port /dev/cu.usbmodem113202 --e-volts 2.43 --out docs/evidence/pad-E-r26-repeticion/uart
python3 scripts/pad_e_swo_probe.py --port /dev/cu.usbmodem113202 --out docs/evidence/pad-E-r26-repeticion/swo
```
