# Board diagnostics and UART validation · 2026

## Log run by the owner

Original file preserved: `../monitor-dfu-uart-2026-11-19/beacon-live.jsonl`.
349 attempts, from 19 November 11:39:35 to 12:09:03 (America/Lima), duration
29 min 27.905 s: **344 ACK and 5 resynchronizations**. No silences, port
errors, malformed JSON lines or false ACKs. The final audit cross-checks HCI/SLIP
TX of type 0x7f with checksum/CRC, RX ACK, metadata and sequence
transitions. The resynchronizations are logged events; they are not ACK samples
and do not by themselves allow the cause to be deduced. Audit in `uart-audit-final/`.

## Delivered code

- `scripts/board_diagnostics.py`: SWD CLI and diagnostic suite.
- `scripts/sensor_identification.py`: I²C register reading, validation of
  identifiers/RTC and targeted SPI transport.
- `tests/test_board_diagnostics.py`: 26 new tests; full suite **47/47**,
  plus the existing C test with exit 0.

Python 3 and pyOCD 0.46.1 available on this Mac. No dependencies were installed.
The transport reuses `I2CProbe` from `scripts/bus_probe.py`. The UART monitor and
the beacon firmware were not changed. Code/tests remain in the existing project
without an initial commit or worktree; HEAD does not exist.

## What it tests

| Profile | Test |
| --- | --- |
| `baseline` (default) | FICR, GPIO configuration, UART, reset and radio over SWD. Does not change GPIO, does not deliberately halt/resume the core. The SWD link manages debug registers. A disconnected input buffer is reported as unknown level, not as 0 V. |
| `gpio` | Floating input, pull-down, pull-up, low OD pulse and release on permitted GPIOs. Keeps full IN masks to examine couplings; does not assign physical function automatically. |
| `adc` | Four calibrated samples of six analog inputs and VDD. Does not turn a voltage into a sensor identity. |
| `i2c` | Targeted pairs or permutations of GPIOs that pass the OD matrix; checks idle, independence and STOP. Default addresses 0x18/19/29/39/50/68/76/77, repeated W/R ACKs and negative controls that allow for adjacent devices. |
| `spi` | Explicit CS/SCK/MOSI/MISO, modes 0/3; checks real CS, clock and MOSI, repeats ID and contrasts with CS inactive. No mass pin sweep. |
| `auto` | GPIO + ADC + I²C search and identification reads; SPI only if its pins are supplied. |

After validating an address, it attempts a repeated ID read: LIS3DH/
LIS2DH12 family and BMP280/BME280. Address 0x68: reads registers 0..7 twice, without writing
date/time/alarm. Validates BCD, calendar, ST and advance within the observation
windows of both reads. Tolerates OFIE and the SQW frequency bits; a compatible
clock does not by itself identify the exact model. Without ACK there is no RTC
reading or proof of operation: the search is logged, not an identification.

GPIOs excluded from driving: 0/1 crystal; 12/13 UART; 19 reported RTC IRQ;
21 nRESET; 3/4/11/22/25 previous incidents; 9/10 coupled. 14/15 are reserved for an
optional experimental state `--enable 14` or `--enable 15`, never both high
nor presented as identified enables. Without that option both stay as inputs.
Protected GPIOs are not attempted with a forcing argument.

## Physical test performed

Setup kept as confirmed by the owner: single 3.3 V power supply on
C/F, H/E3/batteries removed; SWD Pico pin 4/GP2→A, pin 5/GP3→B and GND F;
UART pin 6/GP4→E2 and pin 7/GP5←E1, E/SWO removed. The monitor no longer had the
port open. UART signals 12/13 were not remapped or driven as GPIO.

`baseline/`: nRF52832, UART active TX13/RX12 and reset 21/21. The first capture
showed GPIO19 as a bootloader output, consistent with r29. Its levels with
INPUT disconnected are not considered physical measurements; `post-active-baseline/`
already uses the raw/input_connected fields of the final code.

`active-bounded/`: `--profile auto --max-pairs 24 --max-seconds 180`.
Actual results:

- 16 GPIOs examined; 14 individually suitable for OD under these conditions.
  GPIO6/7 did not pass the matrix. This does not prove absence or sensor function.
- 7 SAADC sources, four samples each. VDD estimated 3.165–3.173 V with
  internal calibration; this does not replace a metrological measurement of the power supply.
- 24 I²C pairs processed; 177 W transactions: 176 NACK and one clock failure
  SDA2/SCL17 (`clock_not_high`), which leaves 7 addresses untested on that pair.
  No ACK candidates or new identification. A valid idle line does not
  guarantee all edges during a transaction.
- Overall result **incomplete**/exit 1 due to that incomplete electrical test;
  kept without hiding it or turning it into a NACK. The time limit was not reached.
  Coverage limited to 24 pairs in this integration test; it is not the full
  sweep and does not rule out sensors/RTC under other power conditions.
- SPI skipped for lack of traced CS/SCK/MOSI/MISO.
- Closure verified: bootloader active PC 0x7510A, bootloader/UICR hashes
  identical, GPIO19 input without pull, temporarily in RAM. No flash
  or UICR writes. `post-active-uart.jsonl`: one subsequent ping with correct ACK.

The active session halts the normal program, runs a loop in RAM, disables the
radio and resets at closure. The LED19 define is temporarily mitigated after reset;
a later reset returns to the binary's configuration. Hash, release and reset
failures are logged separately; if reset fails, it tries to leave
the core halted, without deliberately resuming the RAM loop. Automatic recovery
is not guaranteed when the SWD link is lost.

## Use in Terminal

From the project root, with the power and wiring above:

```sh
# First stop dfu_ping with Ctrl-C. Do not run both tools at the same time.
python3 scripts/board_diagnostics.py --profile auto --plan
python3 scripts/board_diagnostics.py --profile auto --max-seconds 600
```

The second command automatically creates a NEW directory under
`docs/evidence/board-diagnostics-<date-time>/` relative to the current folder.
It holds `events.jsonl`, `summary.json` and `report.md`. Each event is flushed
to disk. There is no need to wait indefinitely: 10-minute limit for the suite,
plus connection/closure. It may finish earlier; if it reaches the limit it saves incomplete.
Ctrl-C attempts the closure and keeps the log (exit 130). It does not use `--watch`;
it is a finite suite. To repeat after moving/covering/lighting, run it again.

Targeted examples (the numbers are nRF GPIOs, not pads or Pico GPIOs):

```sh
# Only ADC or GPIO, without searching for buses:
python3 scripts/board_diagnostics.py --profile adc
python3 scripts/board_diagnostics.py --profile gpio
# SDA/SCL after continuity; 6:7 only illustrates the syntax, not a confirmed assignment:
python3 scripts/board_diagnostics.py --profile i2c --i2c 6:7 --addresses 0x68
# Audit another existing UART log, without connecting to the beacon:
python3 scripts/board_diagnostics.py --uart-log PATH.jsonl
```

SPI requires `--profile spi --spi CS:SCK:MOSI:MISO`, replacing each name
with a genuinely traced GPIO. No invented SPI pinout is provided.
`--out NEW_PATH` sets the directory; it is rejected if it already exists.
`--uart-port` selects the path to check in order to detect the concurrent monitor
(by default `/dev/cu.usbmodem21202` in this session). If macOS renumbers the Pico,
adjust that option; SWD selects the Pico serial with `--probe`.

Exit 0 means the selected tests completed, not that a sensor was discovered.
Exit 1 indicates an incomplete test/connection/closure; check the events. Exit 2 is
a parameter/output error; 130 means Ctrl-C.

## Pending physical limits

The code can search for and validate devices that respond on accessible buses;
it does not deduce trace continuity or identify a pad from a logic level alone.
RTC SDA/SCL and VCC still have no confirmed tracing; with power via C, the supply
to all external circuits has not been proven. Absence of ACK
does not prove a faulty RTC or an absent sensor. The next targeted physical step
is continuity RTC 1/SDA and 8/SCL and measuring VCC 5 relative to VSS 3 at an accessible point.

## Primary sources for the validators

- [ST M41T62, tables and clock reading](https://www.st.com/resource/en/datasheet/m41t62.pdf): registers 0..7, ST, OFIE and SQW; 7-bit address 0x68. The alarm is not read and its configuration is not written.
- [ST LIS2DH12](https://www.st.com/resource/en/datasheet/lis2dh12.pdf): WHO_AM_I 0x0F=0x33; the compatible-family category is kept because it shares that ID with LIS3DH.
- [Bosch BMP280](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf) and [BME280](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf): repeated identification, without putting the sensors into measurement.

## Software verification and review

RED/GREEN tests saved in this directory. 26 new tests: edge-level I²C slave,
missing ACK at each stage, busy bus, RTC/BCD/control/windows,
SPI 0/3 and MOSI/SCK, GPIO reservations, corrupt/empty audit and closure on failures.
Full suite 47/47 in `software-tests.txt`; existing C compiled with
`clang -Wall -Wextra -Werror`, exit 0. Independent read-only review:
the important problems were fixed with regressions. There was no second
review after the fixes; the subsequent verification is those regressions
and the full suite. The physical tests and their limitations are recorded above.
