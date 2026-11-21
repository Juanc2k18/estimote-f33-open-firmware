# Current state of the research

Documentation closing: **2026**, America/Lima. To resume: [SWD/bootloader/sensors handover report](reports/swd-bootloader-sensors-2026-11-19.md) and [logbook for the 19th](logbook/2026-11-19.md).

## Current result (2026)

**Custom firmware complete and validated.** Summary, versions and instructions in the
[consolidated guide](guide-f33.md).

| Area | State |
| --- | --- |
| MCU | nRF52832 QFAA unlocked; original firmware lost (r13). |
| Firmware | Adafruit bootloader 0.11.0 r46 + S132 6.1.1; application **`f33-ble-sensors` 1.0.0** with BLE and UART with a host (loaded via BLE OTA and via UART, verified by its version). |
| Sensors | LIS2DH12, LIS3MDL, BMP280, MAX44009 and M41T62 on I²C P0.14/15, validated with stimuli (r37–r39, r44c–d). |
| BLE | Advertisement `F33`, data every 1 s, Battery Service and version (r44–r45). |
| Host E1–E4 | JSON every second, commands `read`/`int`/`ver`/`dfu`/`ota`, detection via E2; validated with the Pico (2026). |
| Reprogramming | BLE OTA, UART E1/E2 (UART command `dfu`, BLE command or cutting E3) and SWD (A/B/F + power). |
| Power | H/F: VDD 2.0 V, works from ≈3.0 V. E3/E4: 3.3 V recommended (5 V → VDD 4.58 V). |
| Consumption | ≈0.15–0.45 mA idle (multimeter; no detectable increase from the UART), ≈4 mA during boot. |
| Setup at closing | With host: power supply at 3.3 V on E3/E4, Pico on GP4→E2, GP5←E1, GND→E4; H disconnected. |

Latest validation (2026): owner reports C/F at 3.3 V; r46 and app 1.0.0 were
written over SWD and all published HEX segments match memory readback.
Bootloader r46 BLE identity and app BLE sensor notifications were checked.
BLE/UART DFU uploads were not repeated with r46. [Record](evidence/swd-c-power-r46-2026/README.md).
The closing setup above describes the earlier UART session.

ESP32 DevKit V1 follow-up (2026): the owner reports both Arduino readers work.
Screenshots show UART JSON and BLE GATT reads with all sensor-valid flags,
using Arduino IDE 2.3.11 and the ESP32 Dev Module profile. [Results](evidence/esp32-readers-2026/README.md).
No ESP32 commands, notifications, DFU or induced reconnection test is claimed.

Pending: data in the advertisement (BTHome), configurable low power, real Raspberry Pi host and extended ESP32 tests,
magnetometer calibration, RTC time, amplifier pins and
accelerometer interrupt pin, pad D.

The log below is chronological (r17–r45). The older sections
keep the conclusions of their date, even if they were later corrected (for example,
"sensors not identified" until r36).

## Latest clarification of the external connector

The owner identified E4=GND and E3=5 V input; E1=TX/P0.13 and E2=RX/P0.12 were confirmed in 2026 (r15). The owner corrected the internal polarity to F=negative/GND and H=positive/battery. The consolidated summary adds candidates for A/B/E/G; they have not been confirmed by continuity. C/D still have no firm assignment.

## Project scope

The project reused an unsupported F3.3 in 2026. The reference beacon has been erased and reprogrammed with the Adafruit bootloader (r13–r14); the original firmware is irrecoverable. Critical steps require explicit authorization under [AGENTS.md](../AGENTS.md).

Latest pinout: see [full table and provenance](pin-candidates.md). The battery topology and the H/E3/VDD relationship are still pending. The current map is the **only consolidated one**, with three sheets; the native r02/r03/r04 files were removed at the owner's request. Historical graphics are not current instructions.


The [r04 update of the unit sheet](unit.md#polarity-correction-and-power-tests--revision-r04) gathers the owner report and the new BLE captures, with an observed reboot and the percentage still unavailable after reconnecting.

## Update r17–r18: power and new sweeps

Sensors still not identified. SAADC was checked, SPI was extended to 20 CS (137,700
combinations, no valid candidates) and I2C with internal pull-ups. P0.21 was tested
temporarily released from reset and then **UICR was restored and verified**; bootloader
with identical SHA-256. TWI does produce NACK on free pins 2/8.

The owner changed power to **3.3 V via H/F, no power supply on C**. SAADC ~2 V
internally and the owner's multimeter **2 V between C/F**. The hardware should no longer
be assumed to be powered through C. A comparison at 6 V via H/F was requested, with the signals
to the Pico temporarily removed to measure C/F before reconnecting them;
owner report pending. [Evidence and limitations](evidence/sensors-r17-2026-11-19/README.md).

## Closing r19: 6 V via H/F, sensors not identified

The requested change **was carried out**: the owner measures C/F=2 V with H/F at
6 V and reconnected A/B/E1/E2. SAADC VDD~1.998 V. This is the current connection.

SPI at 6 V: 137,700 combinations without enables, and another 88,320 with GPIO14/15 high:
no valid candidates. I2C under both conditions produced transient candidates
on SDA25, none validated; the first gave ACK on 107/112 addresses, the
second was not reproduced in two native tests of the same pair. The SPI tests
on SCK3/4/11/22/25 were incomplete due to SWD loss.

**P0.05/AIN3 battery candidate** (~0.521 V with H at 3.3 V and ~1.000 V with H at
6 V, VDD constant ~2 V). Does not confirm a divider/calibration or a light sensor.
Bootloader verified by SHA-256 and PC 0x75102; UICR restored, PSELRESET=21,
chip unlocked. Final reset executed. Chips and buses still need to be physically
identified with macro photos and continuity. [Closing and records](evidence/sensors-r17-2026-11-19/README.md#closure-r19).

## r20 · Battery curve

P0.05/AIN3 follows the H/F setting: power supply at 3/4/5/6 V → ADC
0.494/0.668/0.838/1.009 V. VDD stays ~2 V. Strong evidence of a battery
reading through an approximately 1:6 divider; still without continuity or confirmed
resistor values/calibration. Power supply left at 6 V on H/F, C without power supply,
G not connected. Data: `evidence/sensors-r17-2026-11-19/battery-curve-r20.json`.


## r24 · Valid I²C control; GPIO6/7 electrically invalid

With the existing power (latest report 6 V H/F, C without power supply, G free),
SDA2/SCL8 gave 112 NACK W and 112 NACK R with SCL high and a valid STOP per pass.
GPIO6/7: with 14/15 in Z they stay low; with only 14 or only 15 high, they do not go low
individually. Same in both orientations and with/without internal pull-up,
repeated up to 50 ms. Addresses on 6/7 not tested due to electrical invalidity;
sensors are not ruled out. Known physical ACK control still pending.
SPI audited and the new classification validated in software; not run on the board
for lack of traced CS/SCK. Bootloader/UICR with identical hashes and normal boot
confirmed. [r24 evidence](evidence/i2c-r24-2026-11-19/README.md).


## r25 · UART removed, 29 GPIO checked and closing recovered

Pico SWD reconnected and UART E1/E2 removed by the owner. Matrix of 29 GPIO;
20 individually suitable for OD with pull-up, including 12/13 and 25. 380
I²C orientations on those 20: 378 valid (9/10 coupled), 3,024 NACK W/R at
0x18/19/76/77, no ACK. Test without forced enables: not an absence of sensors.
GPIO3/4 do read high with the output active, although the pull-up does not raise them.
The output-high test was interrupted when trying 11 (No ACK), recovered
without erasing via reset and CTRL-AP; 51 tests on 17 other GPIO completed.
Level retention limits assigning enables. Final r24 control repeats the invalidity of
6/7 in ZZ/HZ/ZH. Bootloader PC=0x779FC and bootloader/UICR hashes intact.
SAADC VDD=1.99248 V and P0.05=1.00503 V. UART stays removed; power supply kept.
[r25 results and exclusions table](evidence/buses-r25-2026-11-19/RESULTS.md).


## r26 · Pad E and SWO confirmed

**E=P0.18/QFN48 pin 21**, functional validation via temporary UART and then
Cortex-M4 SWO/ITM from RAM: six intact messages in each test, with
empty before/after controls. In SWO, nRF UART disabled, radio=0 and
CFSR/HFSR=0. E/F=2.43 V per owner report; no new ohmic measurement.
E connected to Pico physical pin 7/GP5 RX; E1/E2 removed and pin 6/GP4 free.
Trace disabled and normal boot at closing, PC 0x750ec; bootloader/UICR
hashes identical. [r26 evidence](evidence/pad-E-r26-2026-11-19/README.md).


## r28 · Components from macro photography

RTC **M41T62** identified visually by marking/package, without its operation
tested. New I²C reference 0x68 to locate the bus by continuity.
Barometer **BMP280 very likely**: Kx code and compatible package; reading the ID still pending.
FEM66110-11 clearly legible. Accelerometer, EEPROM and light sensor still without a
confirmed model. No new GPIO or power assignment from these photos.
[r28 analysis and originals](evidence/photos-unit-r28-2026-11-19/README.md).


## r29 · RTC IRQ reported on GPIO19; I²C not located

Owner: M41T62 pin 6→nRF pin 22/P0.19, no ohms recorded.
LCC8 pin 6 corresponds to IRQ/OUT according to the ST datasheet; it does not identify SDA/SCL.
0x68 probed ZZ/HZ/ZH on 340 valid pairs per state: 2,040 NACK,
no candidate. RTC VCC indeterminate due to contact difficulty; do not record 0 V.
GPIO11 caused an SWD failure in OD and was excluded after recovery. The bootloader uses 19
as output/LED: at closing it was temporarily left as input CNF0, bootloader active
PC 0x77A06 and identical hashes. Reset restores the LED use of the current binary.
Continuity of RTC1/SDA and 8/SCL and checking power at an accessible point are still pending.
[r29 evidence](evidence/rtc-r29-2026-11-19/README.md).


## RTC photographs

The M41T62 contacts are visible in IMG_0576–0581. See the [RTC photo details](evidence/photos-rtc-r30-2026-11-19/README.md) and the [photo evidence](evidence/photos-rtc-r30-2026-11-19/README.md). Package orientation remains unverified by continuity; no alarm IRQ test was performed.

## SWD diagnostics suite and monitor validation · 2026

Current setup confirmed by the owner: single 3.3 V power supply on C/F,
H/E3/batteries removed; SWD A→Pico pin 4/GP2, B→pin 5/GP3; UART
GP4/pin 6→E2 and GP5/pin 7←E1; E/SWO disconnected. The owner's UART monitor
recorded 349 attempts (344 ACK + 5 resync) over 29 min 28 s, audited with no false ACKs.

New `scripts/board_diagnostics.py`: GPIO/ADC/I2C/RTC suite and targeted SPI,
with `--profile auto`, JSONL and a report. 47 Python tests and the existing C test pass.
Bounded physical integration: 16 GPIO, 7 ADC sources, 24 I2C pairs; 176 NACK and one
clock failure SDA2/SCL17, no new identification. Partial result documented,
not an absence of sensors. Bootloader/UICR intact, subsequent UART valid;
GPIO19 left as input without pull temporarily, restored to output by a reset.
RTC SDA/SCL and power still pending continuity/measurement.
[Evidence and commands](evidence/board-diagnostics-2026-11-19/README.md).

## Owner's complete run · sensors-session-01

Suite finished and audited in 2 min 3 s: 16 GPIO, 13 suitable for OD; GPIO6/7/17
excluded after the matrix. All 156 pairs of the suitable pins with electrical validation;
1,248 NACK W on eight addresses, including 156 NACK to RTC 0x68. No devices
identified, no functional RTC test and no SPI for lack of a pinout. Complete
means the selection was covered, not an absence of sensors. SAADC VDD~3.17 V;
closing and hashes correct, GPIO19 temporary input. Still to confirm RTC GND/VCC
and SDA/SCL continuity. [Report](evidence/sensors-session-01/report.md).

## I²C/CLK audit and rail tool · 2026

[Audit](reports/audit-i2c-clk-2026-11-19.md): 6/7/14/15 behave as
a single low-impedance node, compatible with a sensor rail powered by
GPIO. The previous matrices were done with that rail off and excluded the pins
fixed low, the probable SDA/SCL. The «32 kHz crystal» was only inferred from the
LFXO start. New `scripts/rail_survey.py` with 9 software tests:
topology, full conditioned rail, matrix per state, edge counting,
LFCLK crystal/external and I²C on new pins. **Not run on the board.**

## r31 · Targeted rail and LFCLK from its own crystal

Owner's run at 3.3 V C/F. 6↔7 are joined; 14 or 15 raise {6,7}
in one direction only: it is not a single node, but a switched output or an OR. The
rail did not turn on. **LFCLK: passive crystal** (32 760 Hz; bypass does not start);
the RTC SQW does not go to XL1. GPIO19 no longer follows the pull-up at 3 ms; GPIO17 gives
~35 Hz with anomalous readings. 3, 4, 5, 22 and 25 are fixed low with the rail
off. The r31b tool now tests states 14, 15 and 6+7 separately.
[r31 evidence](evidence/rail-r31-2026-11-19/README.md).

## r32 · States 14/15/6+7 without a new bus

No rail state makes 3, 4, 5, 22 and 25 valid. P0.03 and P0.04 are at
~0 mV always, so the hypothesis of SDA/SCL on 3/4 is left without support. GPIO17
has its own ~35.4 Hz signal that does not depend on the rail (a light sensor with
frequency output?). GPIO19 is held low, compatible with an active RTC
IRQ. Reported wiring E1→Pico pin 8 (GND): pending correction.
New tool `scripts/pin_frequency_watch.py`.
[r32 evidence](evidence/rail-r32-2026-11-19/README.md).

## r33 · Correction: GPIO17 is not a frequency

With 1 s windows, 17 gives 8–9 edges, the same as with 0.25 s, and does not change with
light. The «35 Hz» of r31/r32 was a fixed burst when configuring the pin. More
likely: the LED on 17 leaves the node near the input threshold. It is not a light
sensor nor a bus. [r33 evidence](evidence/gpio17-light-r33-2026-11-19/README.md).

## r34 · UWB precedent: RTC directly to the nRF

On the top layer of the UWB I1.2, the same M41T62 goes directly to the nRF with no
intermediate component: SDA→41/P0.29, SCL→42/P0.30 and IRQ→43/P0.31, only with
vias and test points. SDA and SCL go to internal layers right away, so
the complete route cannot be seen by eye. On the F3.3 the GPIO are different
(IRQ→P0.19), but the pattern suggests SDA/SCL adjacent to the IRQ. Candidates:
pins 20/P0.17, 23/P0.20 and 21/P0.18. Proposed measurement: RTC1/RTC8 against
those pins. [r34 evidence](evidence/rtc-uwb-routes-r34-2026-11-19/README.md).
Prepared `scripts/i2c_pushpull_scl.py` (SCL in push-pull) to address
pairs with GPIO17 at an intermediate voltage, which OD validation always discarded.
Not run.

## r35 · Push-pull SCL on 16/17/18/20: no response

108 NACK on valid pairs of 16/18/20 in the off/15/14 states; no ACK.
GPIO17 reads 0 even when driven high with H0H1: it has an external *driver* or
a load almost to ground. It is not SDA/SCL and must not be driven again. The bus
is still not located via SWD; physical continuity of RTC1/RTC8 is missing.
[r35 evidence](evidence/i2c-pp-r35-2026-11-19/README.md).

## r36 · RTC SDA → pin ~17 (P0.14)

The owner reports continuity RTC1/SDA → pin ~17 (P0.14; neighbors 16 =
P0.13/TX and 18 = P0.15). SCL does not beep and the display drops to ~550 (unit and
pin to be confirmed). The r31 topology is reinterpreted: 14/15 would be
SDA/SCL and {6,7} the sensors' power supply. 14/15 had never been tested
as a bus. New `scripts/i2c_rail_bus.py`; not run.
[r36](evidence/rtc-continuity-r36-2026-11-19/README.md).
**Update r36:** the owner reports RTC8/SCL → pin 18 (P0.15),
with a beep. The pair is SDA=P0.14 / SCL=P0.15 by continuity (difficult contact,
no ohms). Pending validation with `i2c_rail_bus.py`.

## r36 · I²C bus located and sensors identified

**SDA=P0.14, SCL=P0.15**, with the pull-ups powered by P0.06/P0.07.
Devices: **LIS2DH12 0x19** (0x33), **LIS3MDL 0x1E** (0x3D), **MAX44009
probable 0x4A** (≈90 lx), **M41T62 0x68** (oscillator running, OF=1,
calendar not set) and **BMP280 0x77** (0x58). No EEPROM on the bus.
Reads only; valid closing. [r36 evidence](evidence/i2c-14-15-r36-2026-11-19/README.md).

## r37 · Real sensor reading

`scripts/sensor_readout.py` turns the sensors on writing only volatile
registers and reads 6 rounds. The registers are restored at the end.
- **Accelerometer:** ≈1.04 g on Z.
- **BMP280:** ≈1006.6 hPa and 28.4 °C.
- **MAX44009 probable:** ≈22 lx.
- **RTC:** its seconds advance.
- **LIS3MDL:** gives live data with a constant magnitude of ≈1.61 G, mostly on
  X/Y. Probable hard-iron offset; a test rotating the board is pending.

The first access to 0x19 after raising 6/7 may give NACK. This was solved with a
1 s wait and presence retries. Valid closing.
[r37 evidence](evidence/sensors-reading-r37-2026-11-19/README.md).

## r38 · Guided stimuli

`sensor_readout.py --guided`. The owner did not see the instructions; alternated
strong/dim light and moved the board slightly without a defined orientation.
**Light: responds** (22 → 1060 lx and back). **Accelerometer: responds** (up to
Y=−0.40 / Z=0.83 g). **Magnetometer: no conclusion** (the board was not rotated;
variation < 0.06 G). Slow 360° rotation pending.
[r38 evidence](evidence/sensors-stimuli-r38-2026-11-19/README.md).

## r39 · Magnetometer validated with a rotation

With a 360° rotation in the plane (accelerometer Z ≈ 1.04 g constant), the LIS3MDL X/Y
trace a **circle of radius 0.251 G** (RMS 0.024 G), of the order
of the Earth's horizontal component, **centered at (1.08; 0.75) G**. That is,
there is a hard-iron offset of ≈1.3 G attached to the board. **The five
devices on the bus are validated as measuring.** SWD was lost in round 35
(wires during the rotation): invalid closing and sensor registers not
restored (volatile). Pending: check wires, power-cycle C and reverify.
[r39 evidence](evidence/magnetometer-rotation-r39-2026-11-19/README.md).

## r40 · Power via H/F

Power supply on H/F, C without power supply. SWD and closing valid; **VDD = 2.00 V** by SAADC.
AIN3 = 0.538 V, which corresponds to H ≈ 3.25 V according to the r20 curve. The five
sensors respond and measure at 2 V. Current setup for continuing the tests.
[r40 evidence](evidence/sensors-hf-r40-2026-11-19/README.md).

## r41 · BLE works

Bootloader in DFU OTA (GPREGRET=0xA8 and reset via SWD). `AdaDFU` is visible and accepts
connections from the phone (nRF Connect) and from the Mac (bleak): median RSSI
−59 dBm and Device Information "Estimote F3.3 (reutilizado)". BLE address the same
as the original, according to the owner. **The radio goes through the amplifier without
controlling it.** The DFU LED is driven by PWM0 on P0.17/P0.19. Hypothesis: the LED
is on 17, which would reinterpret the r35 reading.
[r41 evidence](evidence/ble-ota-r41-2026-11-19/README.md).

## r42 · LED on P0.17

The owner follows pin 20 (P0.17) to a three-leg transistor,
a resistor and the LED. Via SWD with PWM0 stopped, only the P0.17 flashes
light the LED, which is **active high**; **P0.19 has no LED**. GPIO17 does not
have an external *driver*: it drives a transistor. This corrects the reading of
r33–r35 and removes the restriction on driving it.
[r42 evidence](evidence/led-r42-2026-11-19/README.md).

## r43 · Bootloader corrected and reflashed

Same Adafruit 0.11.0 with S132 6.1.1. The build is reproducible: without
changes it gives the same hex as r14. Changes:
- only the P0.17 LED;
- no buttons;
- BLE model "Estimote F3.3 r43".

Flashed via SWD and verified: flash equal to the hex, UICR correct with PSELRESET =
P0.21, and PWM only on 17 (19/20/22 disconnected). BLE OTA mode works and the
Mac reads "r43". **The bootloader hash becomes `8e6f23cb…`.** UART DFU: **10 of 10
ACK** with E1/E2 connected, via `/dev/cu.usbmodem1131202`. In OTA mode the
bootloader does not service the UART.
[r43 evidence](evidence/bootloader-r43-2026-11-19/README.md).

## r44 · BLE sensors application · 2026

First custom application (`firmware/ble-sensors/`, C on S132 6.1.1) flashed
via SWD at 0x26000. Advertises `F33`; the Mac receives by notification the five
I²C sensors, VDD and AIN3 every 2 s (10/10, MTU 64). Writing `0x01` to the control
reboots into `AdaDFU`: **it is now possible to switch to DFU without the Pico.** Finding: the
P0.14/15 bus needs the **internal pull-up**; without it the lines stay at 0 even though
P0.06/07 are high. P0.06/07 would be the sensors' power supply
(provisional). [r44 evidence](evidence/app-ble-sensors-r44-2026-11-19/README.md).
r44c: with scheduled stimuli, 75 of 75 valid notifications. Light goes from
0.135 to 11 382 lx, gravity changes axis (+z, +x on edge, −z face down), the
magnetometer covers more than half a turn of the r39 circle and the temperature
rises with the hand.
r44d: with a hair dryer, the BMP280 temperature rises from 26.8 to 43.7 °C in
about 15 s and cools with τ ≈ 67 s; 70 of 70 valid notifications.

## r45 · Battery, upload without SWD and power via E1–E4 · 2026/20

The application publishes the **battery level** (Battery Service 0x180F) from
AIN3, with two cells in series and a provisional table, and its version in Device
Information. **The four upload paths work:**
- SWD.
- BLE OTA (`scripts/ble_dfu.py`, three times; the first verified byte by byte
  via SWD).
- UART E1/E2 after the BLE command `0x02`.
- **UART with E1–E4 only**, cutting and restoring E3 power
  (`scripts/uart_dfu.py` catches the bootloader's 1 s window).

Curve via SWD (`scripts/swd_monitor.py`): VDD = 2.00 V fixed down to H ≈ 3.02 V,
then it shuts off abruptly and boots again at ≈3.31 V. **E3 at 5 V gives VDD =
4.58 V** (owner's multimeter; SAADC saturated), above the nRF absolute
maximum. With E3 at 3.7 V, VDD = 3.42 V: use E3 ≈ 3.6–3.9 V. At the
owner's request the UART was also tested with E3 at 5 V and the Pico connected. It worked in
both directions (upload of r45c-uart3), but out of spec for the nRF
and for the RP2040. The order of
E1–E4 matches the Location Beacon article (GPIO0 = RX = E2,
GPIO1 = TX = E1).
[r45 evidence](evidence/dfu-battery-r45-2026-11-19/README.md).
Current with a multimeter in series with H at 6 V: ≈4 mA during the ≈2 s
boot, **≈0.15 mA idle while advertising** (and similar while connected), and more than 2 mA
in `AdaDFU` because of the LED. This is a multimeter estimate.

**Closing 1.0.0 (2026):** the r45c code is published as the single version
`1.0.0` (`firmware/ble-sensors/release/`, with SHA-256). It was loaded via BLE OTA and
advertises `1.0.0` with all sensors. The `r45-*` builds were only
test tags.

## 1.0.0 · UART with a host on E1–E4 · 2026

The final 1.0.0 adds to r45c a UART on E1/E2 to work with a 3.3 V
host, and replaces the earlier 1.0.0 without UART, which was not published. Its
functions:

- one JSON line per measurement;
- the commands `read`, `int N` (from 1 to 3600 s), `ver`, `dfu` and `ota`;
- host detection via E2 idle high (internal pull-down), checked
  every second.

Codex implemented the code according to the plan. It was audited here and five
risks were corrected.

Tests with the Pico as host and the power supply at 3.7 V on E3/E4:
- data identical to BLE (pressure rounded to Pa);
- all commands;
- disconnection and return in ≤1 s;
- upload via the `dfu` command without cutting power;
- rescue by cutting E3.

Consumption without a host with a multimeter: 0.17–0.45 mA idle, no detectable
increase. Issue fixed in `uart_dfu.py`: a leftover old line when
opening the port hid the `dfu` ACK. Last test: **E3 at 3.3 V** → VDD ≈ 3.0 V, with data, commands, BLE and upload via
`dfu`, all correct. Setup at closing: with host (E3 at 3.3 V, Pico, H
disconnected). [Evidence](evidence/uart-host-2026-11-20/README.md).
