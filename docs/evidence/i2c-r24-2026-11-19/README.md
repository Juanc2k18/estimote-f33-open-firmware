# r24 · I²C electrical validation and SPI audit · 2026

Objective: determine whether GPIO6/7 support I²C in ZZ, HZ or ZH and whether an address
acknowledges W without register/data. Result: **no electrically valid state**;
there is no negative address result nor a sensor candidate on 6/7.

## Provenance and setup

- **Earlier owner report:** power supply set to 6 V on H/F, C without
  supply, G free; Pico SWD/UART reconnected. Wires and power supply were not changed.
  H/F, C/F, G free and current were not reconfirmed by instrument in r24.
- **Software measurement:** Pico E660C0D1C75C942F available; SWD at 100 kHz,
  DP IDR 0x2BA01477; FICR PART=0x52832, VARIANT=AAB0, RAM=64 KB.
  Initial PC 0x75108 in bootloader, PSELRESET=[21,21], APPROTECT=FFFFFFFF.
- **Power control:** `scripts/sensor_diagnostics.py adc` was reused
  without enables between the two I²C passes. SAADC calibrated, internal reference
  0.6 V, gain 1/6, 12 bits, 40 µs; mean VDD ~1.9989 V and AIN3/P0.05
  without pull ~1.0088 V. Compatible with the historical situation; it does not measure H/F nor
  confirm physical connections. Raw data in `adc.log`.
- **Provisional assignments:** 14/15 could control another net (including the
  FEM visually identified in r22); they are not labelled as sensor power
  nor CTX/CRX without continuity. Both were not set high.

AGENTS.md, the logbook and evidence r17–r23 were read, including the 2/8 control,
coupling, false ACKs on SDA25, SPI clock failures, reset G, r22 photos
and the D/AIN3 comparison of r23. UWB routes were not carried over to this unit.

## Method and validation

The OD primitives of `i2c_bitbang_swd.py` in `bus_probe.py`,
the RAM loop of `sensor_diagnostics.py` and the existing SPI loader were reused. CPU in
RAM loop with CPSID i, RADIO.TASKS_DISABLE and STATE=0 checked in each case.
NVMC was not used and flash/UICR were not programmed. OUT=0 and DIRSET/DIRCLR emulate standard
open drain: 6/7 and 2/8 were never driven high. High via external pull-up
if present, plus internal pull-up only in the cases indicated. Z=input without pull.
Between **each** case 2/8/6/7/14/15 were released; wait of 150 ms after configuring
the state, minimum 1 ms per operation and a 50 ms limit to reach a level.
SWD latency lengthens the pulses: no calibrated I²C frequency is claimed.

First pass: reading of the low after 1 ms (`first-pass/`). Second pass:
the individual low must be reached with the other line high within 50 ms;
both must recover high on release, also within 50 ms. Same
result in both passes, both orientations and with/without internal pulls.
The readings come from the GPIO.IN register, not from an oscilloscope.

Historical control **SDA2/SCL8**, internal pull-ups, 14/15 in Z:
idle=1/1; driving 2 gives 0/1 and driving 8 gives 1/0, both release to 1/1.
Each pass completed **112 NACK W + 112 NACK R** (0x08–0x77), 0 ACK,
0 `clock_not_high`, 0 `bus_busy`, 0 `timeout`. SCL=1 checked on each pulse
and on the ninth sample; high idle after each STOP. W transmits only START,
byte `(addr<<1)|0`, ninth pulse and STOP, with no register or data. R transmits the
R bit; if there were an ACK, it reads one byte and ends with NACK/STOP, like the historical
tool. There was no data read because there was no ACK.

**A known I²C device is missing to validate the physical positive path.**
The simulation validates the code's ACK branch, but does not replace that control.

## Results table

| P0.14/15 | Internal pull-up 6/7 | SDA/SCL | Idle 6/7 | Electrical validity | ACK W | ACK R | Repeatability |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ZZ | no | 6/7 | 0/0 | invalid: does not recover high | not tested | not tested | electrical condition repeated¹ |
| ZZ | no | 7/6 | 0/0 | invalid: does not recover high | not tested | not tested | electrical condition repeated¹ |
| ZZ | yes | 6/7 | 0/0 | invalid: does not recover high | not tested | not tested | electrical condition repeated¹ |
| ZZ | yes | 7/6 | 0/0 | invalid: does not recover high | not tested | not tested | electrical condition repeated¹ |
| HZ | no | 6/7 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| HZ | no | 7/6 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| HZ | yes | 6/7 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| HZ | yes | 7/6 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| ZH | no | 6/7 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| ZH | no | 7/6 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| ZH | yes | 6/7 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |
| ZH | yes | 7/6 | 1/1 | invalid: neither line goes low | not tested | not tested | electrical condition repeated¹ |

¹ The electrical condition repeats, not an ACK. In ZZ the IN register gives 0/0
before, during and after releasing each line; the internal pull-up does not recover the bus.
In HZ/ZH it gives 1/1 even when individually driving 6 or 7 low and waiting
50 ms. The other line stays high. These readings alone do not demonstrate a short circuit, resistance,
internal connection or the cause of the opposition to the low.

**Scope of the exclusion:** 6/7 does not work as a standard open-drain I²C bus
in these three states, under the existing power supply and the pulls tested.
The 12 cases were closed at the electrical validation, before addressing.
They do not count as NACKs, and do not rule out sensors nor their possible W response under
another condition. There is no ACK to repeat three times nor a signature to compare with a
datasheet; no targeted identification read was attempted.

## SPI: audit, classification and decision

In `scanner-r18-spi.c`, `progress++` counts **pin combinations** before
the 2 modes × 5 commands. A CS that did not go low returned 0xFF, indistinguishable from a
completed 0xFF byte; SCK was not physically read. The historical 137,700/88,320
are not retroactively converted into electrically valid transactions.

`scanner-r24-spi.c` keeps the header/hits format and adds 7 counters
at offset 996: `cs_not_low`, `sck_not_toggle`, `completed`, `no_signature`,
`signatures`, `validation_incomplete`, `cs_not_high`. `spi_read` returns -1
if the selected CS does not go low, -2 if SCK does not reach some level (including idle),
-3 if the inactive CS control does not rise, or a byte 0–255 if it completes. It counts all
calls in `completed`, including repetition/control; `no_signature`
counts completed primary probes with no retained signature, and separates incomplete
validations. `progress` still counts combinations, with a documented name.
Each failure releases the GPIOs; the original r18 is kept. The binaries in `source/` were withdrawn from
publication (2026); they are rebuilt with `tools/ram-scanner/`.
The r24 variant is SPI-only. The loader has `--spi-stats`, requires `--i2c ''`,
and rejects both 14/15 high and SCK3/4/11/22/25 in that mode.

**Validation before use:** 7 Python tests of the protocol/errors and a C
host test with stuck CS, SCK fixed low and high, modes 0/3, byte 0 completed without
signature and counters of 10 commands against 1 combination; ABI offset 996.
Arm GCC 7.2.1 build for Cortex-M4 completed. The r24 binary **was not loaded**
onto the beacon: there are no CS/SCK justified by continuity or documentation of this
F3.3. No mass sweep was repeated and the clocks that caused SWD loss were not used.

**Next concrete measurement:** without power and without the Pico USB, number in
a macro photo the contacts of the pressure candidate (capsule with a hole below/
right of the nRF). First measure each contact relative to F and C, and then
the resistance of each signal contact to the nRF pins, starting
with GPIO6/7 and following the accessible vias; record ohms, probe
resistance, photo and exact pin, including paths with a series resistor.
Obtain the marking/model and manufacturer's pinout to distinguish CSB, SCK/SCL,
SDI/SDA and SDO. Choose CS and SCK only when those contacts have recorded
continuity to the corresponding GPIO of **this** unit. Without an ID, a physical
contact of the capsule cannot responsibly be named CS or SCK.
Also map 14/15 relative to the FEM CTX/CRX contacts to explain the
net without assuming it powers sensors. This measurement is pending on the hardware.

## Closure and files

Test GPIOs read as CNF=0 (input without pull) before the reset.
Final reset: PC **0x7510a**, inside the bootloader, radio STATE=0 and
PSELRESET=[21,21]; core resumed. Bootloader SHA-256 before/after:
`589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`.
UICR SHA-256 before/after:
`82ea7e308fcc09c6dd9dee4d9686e9e261f4848d49d6c540f9b1ea670dbc7ad7`.
The intermediate verification after the ADC is kept separately.

`transactions.jsonl`: records per address/case and closure; `gpio-trace.jsonl`:
SWD commands and digital samples with monotonic time, including all the
control transactions. It is a software trace, with no external waveform
capture. `first-pass/` keeps the initial pass and its sources intact.
`summary.json`, `baseline.json`, `final.json`, `adc.log`, `run.log`,
`software-tests.log`, `verification.json`, `parameters.json` and `source/` complete
the parameters, versions, executed code and tools. Repo without commits:
versions identified through copies and `SHA256SUMS`.

There was no SWD loss nor a test interrupted by disconnection. Not executed:
addresses on 6/7 due to electrical invalidity; SPI for lack of demonstrated CS/SCK;
positive control for lack of a known peripheral. There are no new candidates.

Exact command to repeat the campaign with the existing physical setup:

```bash
cd .
python3 scripts/i2c_trial_r24.py --out docs/evidence/i2c-r24-repeticion
```
