# SWD, erase, serial bootloader and sensor search · 2026/19

Handover report for resuming in another session. It covers r07–r16. The chronological detail is in the [logbook for the 18th](../logbook/2026-11-18.md) and [for the 19th](../logbook/2026-11-19.md).

**Status in one line:** the nRF52832 is **erased and unlocked**; it has a **custom Adafruit bootloader with serial DFU over E1/E2** flashed, validated in both directions. **No application is loaded.** The original sensors have not been located.

## 1. Confirmed physical pinout

Orientation: antenna at the top, pads A–H on the right, connector E1–E4 at the bottom. nRF pin 1 **at the bottom left** (owner, r07): the chip is rotated 90° counter-clockwise. Numbering viewed from above: bottom 1–12 (left→right), right 13–24 (bottom→top), top 25–36 (right→left), left 37–48 (top→bottom).

| Contact | QFN48 pin / signal | How it was confirmed | Revision |
| --- | --- | --- | --- |
| A | 25 · SWDCLK | Continuity (owner) and working SWD link | r10, r12 |
| B | 26 · SWDIO | Continuity (owner) and working SWD link | r10, r12 |
| C | VDD (13/36/48) | Continuity (owner); the unit works with 3.3 V on C | r09 |
| F | GND | Owner; common ground in all tests | — |
| E1 | 16 · P0.13 · **beacon TX** | Continuity + serial DFU ACK | r08, r15 |
| E2 | 15 · P0.12 · **beacon RX** | Continuity + serial DFU ACK | r08, r15 |
| E3 / E4 | External 5 V / GND | Owner | — |
| E | candidate 21 (SWO) | No continuity found by the owner | r11 |
| **G** | **24 · P0.21/nRESET** | **~2.1 Ω reported + G→F pulse causes RESETPIN and return to the bootloader** | **r21** |
| D, H | unresolved / battery + | — | — |

- **No NFC according to the owner**, and the UWB's triangular mark **is not visible** on this unit (r07). However, P0.09/P0.10 are joined to each other at low resistance (r16), consistent with a coil.
- The UWB I1.2 routes **do not carry over**: there E1/E2 went to 8/9, here they go to 16/15. Only the SWD block A/B/C/F matched.
- Historical diagram work used a VectorCraft master and several exports. The current publication keeps only [the nRF SVG](../diagrams/pin-map-guide-nrf.svg). Solid lines distinguish validated links; see the current guide for each assignment's evidence.

## 2. SWD and erase

**Setup:**
- Raspberry Pi Pico (RP2040) with **debugprobe v2.3.1** (`debugprobe_on_pico.uf2`, SHA-256 `6649ebba…792d4`).
- **pyOCD 0.46.1** installed with `pip --user`; it is used as `python3 -m pyocd`, because it is not on the PATH.

| Pico | Beacon |
| --- | --- |
| pin 4 · GP2 · SWCLK | A |
| pin 5 · GP3 · SWDIO | B |
| pin 3 · GND | F |
| pin 6 · GP4 · probe TX | E2 |
| pin 7 · GP5 · probe RX | E1 |

Power: external 3.3 V power supply on C / GND on F; the Pico's 3V3 is not connected. Probe UART on `/dev/cu.usbmodem113202`.

**Results:**
- **r12:** DP IDR `0x2BA01477` and CTRL-AP `0x02880000`. **APPROTECT was active**: the original firmware could not be read or backed up.
- **r13:** full erase via CTRL-AP. **The Estimote firmware was lost.**
  - `pyocd erase --mass` reports a **false timeout**: the erase does complete, but leaves ERASEALL=1. `scripts/nrf_ctrlap.py` reads the real state and `clear` clears it.
- **Chip:** INFO.PART `00052832`, VARIANT **`AAB0`**, RAM 64 KB. APPROTECT `0xFFFFFFFF` (unprotected).

## 3. Adafruit bootloader with UART on E1/E2 (r14–r15)

- Adafruit_nRF52_Bootloader **0.11.0** built with a custom board `estimote_f33`: **TX = P0.13, RX = P0.12**. It includes SoftDevice **S132 6.1.1**.
- The LEDs and buttons were left as on the Feather: LED on P0.17/P0.19, DFU buttons on P0.20/P0.22.
- Files, hashes and procedure in [firmware/adafruit-bootloader](../../firmware/adafruit-bootloader/README.md).
- **Compiler:** Arm GNU Toolchain 15.2.rel1 in the session's temporary folder. **It is not persistent**: it may have been deleted, in which case it has to be downloaded again.
- **Verification via SWD:**
  - Bootloader address in UICR = `0x74000`.
  - SoftDevice with FWID `0xB7` (S132 6.1.1).
  - With the chip running, the program counter was inside the bootloader.
- **Behavior:** the LED blinks in DFU mode, probably the one on P0.17. With no application, it stays in DFU; with an application, it listens for serial DFU for 1 s after each reset.
- **UART validation (r15):** `scripts/dfu_ping.py` sent a harmless HCI/SLIP packet and the bootloader returned an ACK. This confirms **E1 = TX and E2 = RX**.

## 4. Sensor search (r16): no success yet

The original firmware broadcast **temperature, pressure, light and acceleration** over BLE (capture from the 18th), so those sensors exist.

**Measured via SWD, with the core halted and without touching flash:**

| Finding | Detail |
| --- | --- |
| 32 kHz crystal | LFXO running in ~400 ms; suitable for the SoftDevice |
| nRF internal temperature | 32.5 °C (chip, uncalibrated) |
| P0.14 / P0.15 | Either one high drives P0.06/P0.07 high even with pull-down: **they appear to power a pull-up network** |
| P0.06 / P0.07 | Stuck high with P0.14/P0.15 high; low without them |
| P0.03, 04, 11, 22, 25 | **Stuck low** even with pull-up, with or without P0.14/P0.15. They may be push-pull outputs idling low (e.g. interrupts) or GND |
| P0.09 / P0.10 | Joined to each other (NFC coil?) |
| P0.17 | Probable LED |
| Rest | Floating |

**Sweeps with no response:**
- I2C on all pairs with a real external pull-up. The only pair is P0.06/P0.07, and nothing responds in 0x08–0x77.
- Bit-banged SPI with CS on P0.06/P0.07: 17 640 combinations, 4- and 3-wire, modes 0 and 3, WHO_AM_I `0x8F`/`0xCF`/`0xD0`/`0x80`/`0x92`.
- P0.06/P0.07 as power with I2C on the rest, and each pin forced high or low with P0.14/P0.15 active: nothing changes.

**Tools:**
- `scripts/gpio_survey.py`, `scripts/gpio_power_probe.py`, `scripts/i2c_scan_swd.py` and `scripts/i2c_bitbang_swd.py`.
- [tools/ram-scanner](../../tools/ram-scanner/README.md): a scanner in C that runs from RAM at native speed.
- The TWI0 peripheral driven from the debugger **generated no events**; it was not understood why. Bit-banging does work.

## 5. Could the firmware misrecognize the pins?

Owner's question: "considering that TX and RX did not match".

**It is unlikely that the problem is the firmware's pin numbering.**

1. **The firmware does not use package pins, it uses P0.n numbers.** The package pin↔P0.n mapping is fixed by the package (Nordic table). It was checked on the board:
   - You measured E2↔pin 15 and E1↔pin 16.
   - The bootloader was built with RX = P0.12 and TX = P0.13, which the table assigns to those pins.
   - The link worked **on the first try and in the direction of your label** (E1 = TX).

   If the chip orientation or the numbering were wrong, the UART would not have responded.
2. **What did not match was the UWB prediction** (8/9), not the firmware. It is a routing difference between boards, not a numbering error.
3. **The scanners do not use a board definition.** They write bit *n* of the P0 port registers directly, with no layers that could remap pins.

**Most likely causes for not finding the sensors:**
- **Pins excluded from the sweep:**
  - P0.00/P0.01 (crystal; confirmed in use).
  - P0.12/P0.13 (UART).
  - P0.21 (reset).
  - P0.09/P0.10, which might not be a coil but sensor lines.
- **Different power or enable:** only P0.14/P0.15 high were tested. Some sensor could be powered by a low level, by another pin or with a specific sequence.
- **«Stuck low» pins (3, 4, 11, 22, 25):** they could be sensor power that draws current when pulling the line, or a bus that is only released after enabling something. Forcing them high changed nothing, but only other nRF pins were looked at; no communication was attempted in that state.
- **Identification:** WHO_AM_I values or sensor addresses not covered, or analog sensors (light on an SAADC input: AIN0–AIN7 = P0.02–P0.05 and P0.28–P0.31). P0.03 and P0.04, two of the «stuck low» ones, are **AIN1/AIN2**: a photodiode or phototransistor to GND could explain that level.
- **TWI from the debugger did not work.** If the bit-banging had a subtle defect we did not see, both methods would fail. It is worth validating the scanner with a known I2C sensor connected to free pins.

**Recommended next step:**
1. **Macro photo of the chips** to identify marking and package.
2. **Continuity of their power and bus pins** to the nRF pins.
3. **Read the SAADC** on P0.02–05/28–31 to look for an analog light sensor.

## 6. To resume

- **Connected hardware (updated r19):** Pico (SWD + UART), power supply at **6 V on H/F**, C unpowered. The owner measures **2 V between C/F**, also confirmed by SAADC. See the r17–r19 sections at the end; the initial setup in section 2 used C/F.
- **Quick checks:**
  ```bash
  python3 scripts/nrf_ctrlap.py
  ```
  ```bash
  python3 scripts/dfu_ping.py /dev/cu.usbmodem113202
  ```
- **BLE application:** proposed, not yet done. Arduino with the Adafruit nRF52 (Bluefruit) core, compatible with the bootloader and S132 6.1.1. It would publish the internal temperature and VDD over BTHome and GATT. It requires downloading arduino-cli, the core and adafruit-nrfutil (pending approval). Upload via serial DFU, resetting with `pyocd reset` just before, because of the 1 s window.
- **Not done:** there are no Git commits and nothing has been published.

## 7. Continuation r17–r18 · Sweeps and power comparison

[Complete records and parameters](../evidence/sensors-r17-2026-11-19/README.md).

- Calibrated SAADC: VDD ~3.08 V powering via C/F; **~2.00 V powering via
  H/F with the power supply at 3.3 V**. The owner confirmed **2 V on C/F with a multimeter**
  in this last condition. H is still not equated with VDD.
- P0.05 ~0.47 V via C/F; 120 samples during a reported alternation of
  covered/flashlight show no clear response. It does not identify a light sensor.
- TWI0 on free pins 2/8 does produce ANACK on 112 addresses: the absence of
  events on 6/7 is not a demonstrated general limitation of access via SWD.
- The original SPI condition `miso != mosi` was correct; the
  suspected MISO defect that was considered during the review was not found.
- Extended sweeps with internal pull-ups, including 9/10 and 14/15 when not
  used as power: no findings. P0.09/10 still follow each other's low level.
- P0.21 was temporarily released from reset by reprogramming UICR; its
  I2C pairs gave no response. **UICR restored and verified**, bootloader with
  identical SHA-256 before/after.
- SPI with 20 CS: **137,700 combinations with no valid candidates**, using
  a CS-low check and CS control disabled. The earlier results
  that depended on CS6/7 have limited scope: those lines do not go low as
  expected with 14/15 high.

The sensors are still unidentified. The last reported connection is the power supply at
3.3 V via **H/F**, C unpowered. A comparison with 6 V via H/F was requested, first removing
A/B/E1/E2 and measuring C/F before reconnecting the Pico; **that change is still
pending a report**. Do not run tests assuming it has already been done.

## 8. Continuation r19 · Comparison at 6 V via H/F

The owner confirmed **2 V on C/F** after setting H/F to 6 V; they temporarily removed
the signals to the Pico and then reported reconnecting them. SAADC measured VDD ~1.998 V.
The current setup is **6 V via H/F, C unpowered**, not the initial setup via C.

P0.05/AIN3 went from ~0.521 V (H at 3.3 V) to ~1.000 V (H at 6 V), while
VDD stayed at ~2 V. **Candidate battery reading via a ~1:6 divider**, with no continuity,
resistors or calibration confirmed. Do not identify it as a light sensor.

I2C at 6 V ended with a candidate SDA25/SCL9/0x46/FF, but the slow repetition
gave SDA low at idle and ACK on 107/112 addresses: **false positive ruled out**.
The ID reads were not consistent. The native filter does not remove all
transients; validate each candidate. The bit-bang script now rejects a low idle level.

Normal SPI at 6 V: **137,700 combinations, zero candidates**, completed without a fault.
The additional attempts with SCK3/4/11/22/25 lost SWD before delivering
results, also at 100 kHz: **incomplete tests**, not valid SPI negatives.
A final combined pass at 6 V with 14/15 high was recorded separately
in `spi-i2c-H60-enable14-15.log`; see its closing in the evidence.

The saved images do not allow the sensor markings on the unit to be read.
The next useful step is a macro photo of both sides and continuity of power
and bus for the small chips, to direct the tests to the real component.
[Parameters and evidence r17–r19](../evidence/sensors-r17-2026-11-19/README.md).

**Closing of the last r19 pass:** 88,320 SPI combinations with no candidates; one
I2C candidate SDA25/SCL29/0x20 not validated (variable readings, initial NACK and two
native repetitions with no findings). PC 0x75102 inside the bootloader, identical SHA-256,
UICR restored and chip unlocked; reset performed. The power supply remains at
6 V on H/F, C unpowered. The sensors are still unidentified; macro photos
and targeted continuity are needed. [Detailed closing](../evidence/sensors-r17-2026-11-19/README.md#closure-r19).

## r21 closing · Working reset via G confirmed

After running the RAM counter and without an intermediate software reset, the owner
reports having briefly joined G to F and then removed the jumper.
`python3 scripts/reset_g_probe.py check` observes PC **0x77A0A** inside the bootloader,
outside the RAM loop, and **RESETREAS=0x1 (RESETPIN)**; PSELRESET[0:1]=21.
The tool connects in attach mode, halts to read and resumes; it does not send a
reset. This is functional evidence, together with the reported ~2.1 Ω G↔QFN48 pin 24 and
2 V G/F, of **G=P0.21/nRESET active low** in the current configuration.
It updates the historical negative result from r11. Log: `G-reset-check.json`.
The core was left resumed in the bootloader, with no new flash/UICR writes.
The power supply remains set to 6 V H/F, C unpowered, Pico connected; G/F jumper removed
according to the owner's report. The reset does not by itself locate the sensors.
