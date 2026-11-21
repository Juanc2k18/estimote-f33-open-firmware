# Campaign r17 · 2026 (America/Lima)

Goal: widen the sensor search without confusing low or floating lines with an ACK, and compare powering VDD directly with the battery input.

## Connections in the first phase

Owner report: the 3.3 V power supply on C/F is kept; Pico connected; LED blinking. SWD: GP2→A, GP3↔B, GND→F; UART: GP4→E2, GP5←E1. No wires were changed by software. P0.12/P0.13, connected to the Pico's UART, were not driven. P0.00/P0.01 and P0.21 were also excluded from the sweeps.

Tools: pyOCD 0.46.1; Arm GCC 7.2.1 available in Arduino15. Diagnostic code in RAM; flash and UICR not programmed. `scripts/sensor_diagnostics.py` runs a RAM loop with interrupts disabled and drives peripherals over SWD. Reset in `finally`.

## Evidence

- `adc-baseline.log`: calibrated SAADC, 0.6 V internal reference, gain 1/6, 12 bits, 40 µs acquisition. Four samples per input and configuration with no pull/pull-down/pull-up. Estimated VDD ~3.086 V (internal reference, not a multimeter). P0.03/P0.04 ~0 V even with pull-up; P0.05 ~0.478 V with no pull and slow charge/discharge when pulls are applied. The other inputs tested follow the pulls.
- `adc-14H-15H.log`: same procedure with P0.14/P0.15 high. Estimated VDD ~3.08 V. Similar input profile.
- `light-p05.log`: 120 samples, approximately 61 s. The owner signaled «ok ahora» (ok now) to alternate covered/flashlight. No timestamps for each transition. P0.05: mean 474.257 mV; minimum 467.58; maximum 481.64; standard deviation 2.899 mV. There is no clear response that identifies a light sensor. It does not exclude a photodetector with another reading/enable method.
- `twi-6-7.log`: TWI0, 100 kHz, SDA6/SCL7, P0.14/P0.15 high, CPU running. 112 addresses: no RXDREADY or ERRORSRC. The peripheral is still not validated as a scanner; this is not equivalent to 112 NACKs.
- `power-probe-repeat.log`: repetition of the old tool; includes transients and residual bootloader activity. Do not use it to assign an active-low enable.
- `power-matrix.log`: sequential matrix of P0.14/P0.15 as input/low/high; 250 ms per reading with three pulls on 6/7. Either one high keeps 6/7 high; both low bring 6/7 low. A residual high after a transition disappears: it does not demonstrate an active-low enable.
- `i2c-6-7-14L15L.log`: SDA/SCL low at idle and ACK at every address with the old tool: false positive, no devices found.
- `i2c-expanded-pu.log`: first widened test, interrupted by the 60 s limit; **incomplete**, no findings. Do not use as a complete sweep.
- `i2c-control-short.log`: RAM execution control on 6/7, finished; core without fault.
- `spi-i2c-expanded.log`: complete run in ~126 s, 13,464 SPI combinations, modes 0/3 and five commands from the original scanner; then I2C with internal pull-ups on all pairs of 25 candidates. I2C candidates: 2,3,4,5,6,7,8,9,10,11,16,17,18,19,20,22,23,24,25,26,27,28,29,30,31. GPIO14/15 power high; SPI CS6/7. **Zero findings**, CFSR/HFSR=0 and end marker reached. Pins 9/10 added compared with the previous campaign; UICR.NFCPINS=0xFFFFFFFE allows GPIO.
- `coupling.log`: with 14/15 high, trying to drive 6 or 7 low with standard drive does not bring their reading low: they do not behave like a free I2C bus. 9 and 10 follow each other's low level when it is applied to either of them. This does not determine whether it is a direct connection, an inductor or another route.

After this phase: reset and `scripts/dfu_ping.py /dev/cu.usbmodem113202` got a valid ACK (response `c0 10 00 00 f0 c0`).

## Interpretation notes

During the session an error was suspected in the SPI condition `miso != mosi`; the code was reread and **the original condition was correct**. There is no demonstrated MISO configuration failure. `scanner-r17.c` keeps the original SPI; it changes the I2C to allow internal pull-ups, check SCL during ACK and require high lines after STOP; it adds CPSID i at the start. These checks rule out some false positives, but they do not replace validation with a known peripheral or an oscilloscope.

Pending hypothesis: C powers the nRF but another sensor branch could depend on H/the original input. The owner offered 6 V power from batteries. A comparison at 3.3 V through H/F, with no power supply on C, was requested first. The physical change is not yet considered done.

## Continuation r18 · Power through H/F

Owner report: they completed the requested move to H/F with the power supply set to 3.3 V, C without power supply; LED blinking. Raising to 6 V was neither requested nor done.

- `adc-H33.log`: calibrated SAADC, mean VDD ~1.997 V. P0.03/P0.04, previously ~0 V with pull-up when powered through C, now rise to ~1.0 V with pull-up. P0.05 ~0.52 V with no pull. The power supply and C/F have not yet been checked with a multimeter in this phase.
- `gpio-H33.log`: the old probe aborted on an SWD error (Unexpected ACK 0 / No ACK); it does not contain a valid map. The link recovered on the next connection. The error is not attributed to a demonstrated cause.
- `twi-control-2-8-H33.log`: SDA=P0.02/SCL=P0.08 with internal pull-ups, 100 kHz, core running a RAM loop. **112 ANACK errors (ERRORSRC=2)**, no RX. Correct negative control: the peripheral can indeed generate events; it does not validate positive communication with a real sensor.
- `ctrlap-after-H33-survey.log`: SWD and CTRL-AP accessible. The subsequent UART attempt got no response. nRF VDD ~2 V and Pico with 3.3 V logic: UART level compatibility not checked in this phase; do not infer loss of the bootloader from the absence of an ACK.
- `i2c-H33-no-enable.log`: complete I2C sweep with internal pull-ups and no power GPIOs forced; 27 candidate pins, including 14/15 and 9/10; without 0/1/12/13/21. Finished in ~106 s, no findings; CFSR/HFSR=0.
- `p21-gpio-H33.log`: P0.21 temporarily released from reset by erasing/reprogramming **UICR only**. All defined UICR fields were saved in `uicr-before-p21.json`, the bootloader/APPROTECT/NFCPINS values were kept and PSELRESET[0:1]=0xFFFFFFFF was left during the test. I2C sweep of both orders of the pairs that include P0.21 (27 partners), no findings, finished in ~14 s, no fault. **Original UICR restored and verified**, PSELRESET=21 again. SHA-256 of the bootloader block 0x74000–0x7FFFF identical before/after: `589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`.

The phrase «flash and UICR not programmed» in the first phase refers to r17; the r18 P0.21 test did temporarily reprogram UICR and restored it. It did not erase the main flash.

The owner measured **2 V between C and F** with a multimeter (power supply set to 3.3 V on H/F), matching the SAADC. Instrument/range/resolution not recorded.

- `spi-all-cs-H33.log`: complete sweep of **137,700 SPI combinations**, modes 0/3, five WHO_AM_I commands, 4/3 wires, **no power GPIOs forced**, with `scanner-r18-spi.bin`. CS: 2,5,6,7,8,14,15,16,17,18,19,20,23,24,26,27,28,29,30,31. SCK/MOSI: 2,5,8,14,15,16,17,18,19,20,23,24,26,27,28,29,30,31. MISO: 2,3,4,5,6,7,8,9,10,11,14,15,16,17,18,19,20,22,23,24,25,26,27,28,29,30,31. Zero candidates, finished in ~108 s, CFSR/HFSR=0. The variant rejects a CS that cannot be driven low; it requires a repeatable reading that differs from the control with CS deasserted. The count includes electrically rejected combinations; not all of them represent transactions with an effective CS. It does not exclude sensors with another protocol, command, mode, power or omitted pins.

`scanner-r18-spi-extended.bin` was prepared, which allows a MOSI mask different from SCK via `run_scanner.py --mosi ...`; not yet run at this point. The source `scanner-r18-spi.c` includes this extension, whose behavior without `--mosi` is the same as the first SPI build.

Next comparison requested from the owner: 6 V on H/F (they already reported earlier tests up to 6.6 V). To check the levels towards the Pico, they were asked to temporarily remove A/B/E1/E2, set the power supply with it off and measure C/F before reconnecting signals. This phase is not yet recorded as done.

## Continuation r19 · H/F input at 6 V

The owner reported C/F still at **2 V** after setting the power supply to 6 V on H/F,
with signals A/B/E1/E2 temporarily removed; they then confirmed reconnecting them.
C remains without power supply. Power supply set to 6 V: independent H/F reading not
recorded. The C/F measurement was the owner's with their multimeter, with no model or
range documented.

- `adc-H60.log`: calibrated SAADC, mean VDD **1.9984 V**. P0.05 with no pull: **0.99955 V**
  mean (4 samples); before, it was 0.520975 V with H set to 3.3 V and 0.47725 V
  when powered through C/F. P0.03/04 stay near zero with no pull and ~1 V with pull-up.
- **Provisional assignment:** P0.05/AIN3 could be a reading of the battery
  supply through a resistive divider, approximately 1:6. It follows the variation of H
  while VDD stays at 2 V. This is not confirmation of continuity, resistors
  or calibration; two set power supply points are not enough to fix a
  precise conversion. The earlier flashlight test showed no clear response.
- `spi-low-clock-H60.log` and `spi-low-clock-H60-retry100k.log`: SPI attempt with
  SCK=3/4/11/22/25, independent MOSI, 20 CS; the first SWD RAM poll failed
  after starting the scanner. Repeated at 100 kHz SWD, it lost the
  link again. **Both tests incomplete**, with no valid count/findings. Do not use
  as negative SPI results. It is not demonstrated whether this is due to a power
  drop, a GPIO effect, SWD levels or contacts.
- Afterwards, CTRL-AP responded and `pyocd reset -t nrf52832 -f 100000` ended without error.
- An I2C sweep of 27 candidates was started at 6 V through H/F, with no power GPIOs
  forced, SWD=100 kHz (`i2c-H60-no-enable.log`). Result pending at the time of writing
  this paragraph.

### Result of the I2C sweep at 6 V and rejection of the candidate

`i2c-H60-no-enable.log` finished in ~111 s, with no CPU faults, and recorded **one
candidate**: SDA=P0.25, SCL=P0.09, address 0x46, byte FF. It is not considered a located
sensor: validation rejected it.

- `candidate-46-manufacturer.log`: idle SDA=0/SCL=1, apparent ACKs, reg.7E→03 01.
- `candidate-46-device.log`: same invalid idle, reg.7F→0F 00.
- Those registers were tested because 0x46 may correspond to an OPT3001. The
  [official TI identification registers](https://www.ti.com/lit/ds/symlink/opt3001.pdf)
  are 7E=5449 and 7F=3001: they did not match. This check alone does not rule out
  other devices at that address; the following electrical problem does
  invalidate interpreting its ACKs.
- `candidate-25-9-rescan.log`: with internal pull-up and slow bit-bang over SWD,
  apparent ACK at **107 of 112 addresses**, with SDA low before START.
- `candidate-25-10-control.log`: SCL on P0.10 (coupled to 9), reading 00 00;
  SDA also low at idle. It is not a positive identification.
- `candidate-low-idle-guard.log`: after adding the idle check to
  `scripts/i2c_bitbang_swd.py`, it correctly aborts with «BUS INVALIDO» and resets
  the chip, instead of reporting fictitious devices. The tool now
  allows `--pullup`, uses SWD at 100 kHz and requires SCL high when sampling the ACK.

The native r17/r18 filter checks instantaneous levels, but **it is not enough to
reject all transients**: an isolated candidate requires slow validation,
high idle and consistent registers. Do not present that 0x46 as a real sensor.

A normal SPI repetition was also started with the same 20 CS as r18, at 6 V through
H/F, SWD=100 kHz, with no enables forced. This is different from the incomplete test
on SCK3/4/11/22/25. File `spi-all-cs-H60.log`; final result pending at
this point.

`spi-all-cs-H60.log` finished: **137,700 combinations**, zero valid candidates,
~109 s, CFSR/HFSR=0. It repeats the CS/SCK/MISO masks of `spi-all-cs-H33.log`,
but now with the H/F input at 6 V and SWD clock=100 kHz.

A last combined pass was started with H/F at 6 V and GPIO14/15 high:
`spi-i2c-H60-enable14-15.log`. CS=2,5,6,7,8,16,17,18,19,20,23,24,26,27,28,29,30,31;
SCK/MOSI=2,5,8,16,17,18,19,20,23,24,26,27,28,29,30,31;
MISO and I2C=2,3,4,5,6,7,8,9,10,11,16,17,18,19,20,22,23,24,25,26,27,28,29,30,31.
14/15 are not included as a bus while they are driven high. Result pending.

## Closure r19

The `spi-i2c-H60-enable14-15.log` pass **finished in ~195 s**, CFSR/HFSR=0:
**88,320 SPI combinations, no SPI candidates**. One I2C candidate:
SDA25/SCL29/0x20/7F. It is not considered a located device:

- `candidate-20-low-idle-check.log`: high idle, but NACK to the write
  address (ACK False,True,True); the following bytes are not a valid register
  reading.
- `candidate-20-repeat1.log` and `candidate-20-repeat2.log`: apparent ACKs, but the
  bytes of the same register change 00 00 / 3F 00 (first 7F 00 after NACK).
- Two native repetitions of the SDA25/SCL29 pair with the same GPIO14/15 high,
  `candidate-20-native-repeat1.log` and `candidate-20-native-repeat2.log`, **end
  with no findings**, no faults. There is no reproducible response nor a consistent ID.
- P0.25 already produced the invalid 0x46 candidate with another SCL. Do not attribute a bus
  or component to it based on these transients.

**Verified state** in `final-state-H60.json`: PC `0x75102` inside the
bootloader, UICR entry `0x74000`, PSELRESET[0:1]=`0x15`, APPROTECT=`FFFFFFFF`,
NFCPINS=`FFFFFFFE`. The bootloader SHA-256 matches the one before the tests:
`589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`.
A reset was performed after the check and after each native repetition.
Flash and UICR were not programmed again in r19.

**Connection at closure:** power supply set to **6 V on H/F**, C without power supply,
Pico SWD/UART reconnected according to the owner; C/F measured by them at **2 V**, SAADC
matching. UART is not guaranteed because of the level difference between the nRF and the Pico;
no new DFU ACK was obtained in this condition. SWD responds.

**Result:** pressure, light and acceleration still unidentified. P0.05/AIN3 is a
battery reading candidate, not a definitive identification. The nRF's internal
temperature was already accessible; this does not demonstrate which source the original
firmware used for its temperature telemetry.

**Next evidence needed:** legible macros of both sides of the unit,
markings/packages of the small chips and continuity of their power and
buses. The existing reference images do not allow reading those markings nor
replace measurements on this unit. The sweeps cover the recorded
conditions, not all possible enables, protocols or combinations.

## Input curve · r20 · first point

The owner offers to vary H/F between 3 and 6 V and confirms the power supply set to
**3.0 V**. C still without power supply; G is not connected to the Pico. `adc-H30.log`:
calibrated SAADC, P0.05/AIN3 with no pull = 562/562/564/561 counts, mean **494.17 mV**
(computed from unrounded counts); mean VDD **1.99556 V**.
Nominal H/P0.05 ratio ~6.07. Power supply set; H/F not measured
independently at this point. Reset at the end. Next point requested: 4 V.
The assignment of G is still pending; UICR identifies P0.21, not pad G.

### r20 · Second point: H set to 4.0 V

The owner confirms the requested setting of 4 V on H/F. `adc-H40.log`: calibrated
SAADC, P0.05 with no pull = 758/757/762/764 counts, mean **668.19 mV**;
mean VDD **2.00215 V**. Nominal H/P0.05 ratio ~5.99. Reset performed.
C without power supply, G not connected; next point requested: 5.0 V.

### r20 · Third point: H set to 5.0 V

The owner confirms the requested setting of 5 V on H/F. `adc-H50.log`: calibrated SAADC; P0.05 with no pull mean **838.257 mV**, mean VDD **2003.027 mV**. C without power supply, G not connected. Reset performed. Next point requested: 6 V. The H values are reported power supply settings, not independent measurements on H/F.

## Closure r20 · H/F power curve

The owner set the power supply sequentially to 3/4/5/6 V and confirmed each step.
C without power supply; G not connected. SAADC calibrated in each run, four samples
with no pull per point; reset at the end of each tool.

| Set power supply H/F (V) | P0.05/AIN3 (V, SAADC) | VDD (V, SAADC) |
| --- | --- | --- |
| 3.0 | 0.494165 | 1.995557 |
| 4.0 | 0.668188 | 2.002148 |
| 5.0 | 0.838257 | 2.003027 |
| 6.0 | 1.008765 | 1.998193 |

Descriptive fit: P0.05 ≈ 0.171387 × power supply setting -0.018896 V;
R²=0.999972. Consistent with a battery reading through an approximately
1:6 divider; the provisional practical formula is H≈6×V_AIN3. It is not a metrological calibration:
H/F was not measured with an independent instrument at each point, internal ADC
reference, four samples per point and no traced continuity or resistors.
Do not fix resistor values nor declare a demonstrated direct connection to H.

Processed data: `battery-curve-r20.json`; last log `adc-H60-r20.log`.
Setup at closure: power supply set to **6 V on H/F**, C without power supply, Pico connected,
G not connected. Pressure/light/acceleration sensors still unidentified.
G is not validated as nRESET by this curve: PSELRESET=21 only identifies the GPIO,
it does not demonstrate continuity of pad G. Do not drive G from the Pico without measuring it first.

### r21 · Pad G voltage

With the power supply set to 6 V on H/F, C without power supply and G not connected to the Pico,
the owner reports **2 V DC between G (+) and F (−)**. It matches the measured VDD,
but it does not by itself identify nRESET: it may be another GPIO/signal with a pull-up.
Instrument/range not recorded. UICR PSELRESET[0:1]=21 verified in r19.
Next proposed test: with no power supply and no Pico USB (to avoid powering through
signals), measure resistance between G and QFN48 pin 24/P0.21. r11 background:
the owner found no continuity; do not overwrite that report without a new measurement.
G was not connected or driven by software.

### r21 · Continuity and preparation of the functional reset

The owner reported **~2.1 Ω between G and QFN48 pin 24/P0.21**, after a
test with no power supply and no Pico USB was requested. This corrects the historical negative r11 result;
instrument/probe resistance not recorded. Together with PSELRESET[0:1]=21,
it identifies a connection of G to the pin configured as nRESET. Functional test pending.
They then confirmed the Pico reconnected and power at 6 V on H/F, C without power supply.

`G-reset-baseline.json`: PC in the bootloader, PSELRESET=21, RESETREAS=0; a
marker was placed in high RAM. That marker is not used as a reset criterion because it can
be altered by the stack. Instead `scripts/reset_g_probe.py` was prepared:
an active counter from RAM, interrupts disabled, without writing flash or
UICR and without a software reset. `G-reset-prepare.json`: the counter went from 453915 to
899473 and PC=0x20000008, confirming the RAM loop is running. After a manual
G→F pulse, it will be checked whether the core went back to running flash/bootloader. Keep
power and USB; do not reset by software before `check`.

## Closure r21 · Functional reset through G confirmed

After running the RAM counter and with no intermediate software reset, the owner
reports having briefly joined G to F and removed the jumper.
`python3 scripts/reset_g_probe.py check` observes PC **0x77A0A** inside the bootloader,
outside the RAM loop, and **RESETREAS=0x1 (RESETPIN)**; PSELRESET[0:1]=21.
The tool connects in attach mode, halts to read and resumes; it does not send a
reset. This is functional evidence, added to the reported ~2.1 Ω G↔QFN48 pin 24 and
2 V G/F, of **G=P0.21/nRESET active low** in the current configuration.
It updates the historical negative r11 result. Log: `G-reset-check.json`.
The core was left resumed in the bootloader, with no new flash/UICR writes.
Power supply still set to 6 V H/F, C without power supply, Pico connected; G/F jumper removed
according to the owner report. The reset does not by itself locate the sensors.

## r23 · Pad D, reported voltage

The owner reports D/F=0.94 V DC. Last reported setup: H/F at 6 V, C without
power supply; H/F setting not reconfirmed in this message. It is compared with SAADC in
`adc-D-comparison-r23.log`: P0.05/AIN3 with no pull=1.005908203125 V; VDD=1.9927001953125 V.
D→P0.05/pin 7 is a **hypothesis**, not confirmed continuity. Next test:
with no power supply and no Pico USB, resistance D↔QFN48 pin 7/P0.05.

## Checksum scope

The current `SHA256SUMS` checks the files distributed with this evidence folder.
The obsolete r18–r21 manifests were removed: they referred to earlier text/source
contents and three scanner binaries no longer distributed. Measurement records
remain historical evidence; their removal was not required to document the
reference unit's validated BLE and UART operation. See the consolidated guide
for current validation scope and limitations.
