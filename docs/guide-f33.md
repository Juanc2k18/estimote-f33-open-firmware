# Estimote F3.3 with custom firmware · consolidated guide (version 1.0.0)

Validated in **2026**, when this F3.3 was no longer supported. This document summarizes the final state, how to
use and reprogram the board, and what was learned. The details of each test (r01–r45)
are in [status](status.md), in the [logbooks](logbook/) and in
[`evidence/`](evidence/). Those distinguish between measurement, owner report and
provisional assignment; here this is noted where it matters.

## 1. Final state

| Area | State |
|---|---|
| MCU | nRF52832 QFAA (FICR `00052832`/`AAB0`), unlocked. **The original Estimote firmware was lost** (APPROTECT; full erase r13). |
| Bootloader | Adafruit 0.11.0 + SoftDevice S132 6.1.1, custom build **r46** installed; published HEX verified byte for byte over SWD, BLE identity and app BLE data validated in 2026 ([firmware/adafruit-bootloader](../firmware/adafruit-bootloader/README.md)). |
| Application | **`f33-ble-sensors` 1.0.0** ([firmware/ble-sensors](../firmware/ble-sensors/README.md)): BLE and UART with a host on E1/E2. Flashed on the board. |
| Sensors | **All five validated** with stimuli: LIS2DH12 (acceleration), LIS3MDL (magnetometer), BMP280 (pressure and temperature), MAX44009 (light) and M41T62 (RTC); also VDD and battery (AIN3). |
| Bluetooth | **Validated.** Advertises `F33`; data over GATT (read and notify every 1 s), standard battery level and version. |
| Host on E1–E4 | **Validated** with a Pico: JSON, commands, detection and UART DFU ([evidence](evidence/uart-host-2026-11-20/README.md)). ESP32 DevKit V1 UART JSON reception and BLE sensor reads also work ([screenshots](evidence/esp32-readers-2026/README.md)); commands and DFU were not retested on ESP32. |
| Reprogramming | **Validated through five paths:** BLE OTA, UART via the UART command `dfu`, via a BLE command or by cutting E3, and SWD. |
| Consumption | ≈0.15–0.45 mA idle while advertising (multimeter estimate; the UART adds no detectable consumption without a host), ≈4 mA during the 2 s boot. |

Before any critical step, review what changes: open BLE/UART access and updates replace the original Estimote firmware, configuration and proprietary behavior. Unlocking an APPROTECT-protected unit requires full erase; the original firmware cannot be recovered from this project. Factory calibration and features may be lost. Incorrect wiring, voltage or programming can cause permanent damage. Explicit authorization is required for each erase, unlock, flash or potentially damaging wiring/power change.

## 2. Board connections

Orientation: antenna up, eight pads on the right (A/B, C/D, E/F, G/H by
rows). External connector E1–E4 from left to right. See the [nRF pad guide](diagrams/pin-map-guide-nrf.svg), also embedded in the main README.

| Pad | Signal | Use | How it is known |
|---|---|---|---|
| **E1** | nRF TX (P0.13) | UART: data to the host and reprogramming | Continuity and DFU ACK (r08, r15); app 1.0.0 |
| **E2** | nRF RX (P0.12) | UART: commands from the host and reprogramming | Same |
| **E3** | External power input | Power through the connector | Owner; measured r45 |
| **E4** | GND | Connector ground | Owner |
| A | SWDCLK (pin 25) | Advanced programming (SWD) | Continuity and link (r10–r12) |
| B | SWDIO (pin 26) | Advanced programming (SWD) | Same |
| C | nRF VDD | Measure VDD (do not power it if H or E3 are connected) | Continuity (r09) |
| D | Unresolved | — | — |
| E | P0.18 / SWO | SWO trace (optional; not needed for programming) | Functional (r26) |
| F | GND / battery negative | Ground | Owner |
| G | P0.21 / nRESET | Hardware reset (optional) | ≈2.1 Ω and functional reset (r21) |
| H | Battery positive | Battery power | Owner; curve r20 and r45 |

The order of E1–E4 matches the one in the [Location Beacon article](https://mlusiak.com/estimoge-uart-raspberry-pi/) that
the owner found (GND, Vcc IN, GPIO0 = RX, GPIO1 = TX).

Internal assignment (see [AGENTS.md](../AGENTS.md)): I²C SDA = P0.14, SCL = P0.15
with **internal pull-up**; P0.06/P0.07 high (probably the sensors' power
supply); LED on P0.17 (active high, with transistor); RTC IRQ on P0.19;
battery divider on P0.05/AIN3. GPIO 12/13 are the E1/E2 UART (bootloader and app); do not use them for anything else. Do not touch GPIO 21 (reset).

## 3. Power

| Input | Tested range | Resulting VDD | Notes |
|---|---|---|---|
| **H/F (batteries)** | 3.0–6.5 V | **2.00 V fixed** | Shuts off abruptly below ≈3.0 V and boots again at ≈3.3 V (r45). Original: 4 × CR2477 in 2S2P (owner). |
| **E3/E4** | 3.7 V | 3.36–3.42 V | Historical measurement; the recommended E3 input for this guide is 3.3 V. The E3→VDD drop is ≈0.3–0.4 V. |
| **E3/E4** | 3.3 V | 2.99–3.00 V | **Recommended E3 input.** UART and `dfu` validated in 2026 with a lab supply; VDD samples reached 2.985 V. A nominal 3.3 V host TX has little or no margin against VDD + 0.3 V: measure actual levels and use suitable level translation where needed. |
| E3/E4 | 5.0 V | **4.58 V** | Exceeds the nRF absolute maximum (3.9 V). The UART worked with the Pico (r45), but out of spec for the nRF and the RP2040. |
| C/F | 3.3 V | 3.3 V | Used in r09–r15; bypasses the regulator. |

The original battery holder is reported by the owner as four CR2477 cells in
2S2P (two series pairs in parallel), approximately 6 V nominal on H/F.
The application maps 6 V to 100% using a provisional battery table; this is
separate from the measured 2.0 V MCU supply on that input.

The [external UART reference](research.md) describes 5 V Vcc IN for its setup.
That does not establish compatibility here: this F3.3 measured 4.58 V on VDD
with 5 V on E3. **Use 3.3 V on E3; do not apply 5 V.**

- Do not connect two power supplies at the same time (H and E3).
- With H, VDD is 2.0 V. A 3.3 V UART on E2 is above VDD + 0.3 V:
  for UART, power through E3 (3.3 V) or through C.

The latest [SWD installation and validation on C/F](evidence/swd-c-power-r46-2026/README.md)
confirmed r46 installation, byte-identical bootloader/SoftDevice/UICR and application,
and bootloader identity plus application data over BLE, with the owner
reporting a 3.3 V supply on C. The owner requests future operation on the
previously validated 6 V H/F battery input after this session. This applies to
H/F only; check interface levels against its resulting 2.0 V VDD.

## 4. Firmware and versions

### Stack on the board

| Region | Contents |
|---|---|
| 0x00000–0x25FFF | MBR + SoftDevice S132 6.1.1 (FWID 0xB7) |
| 0x26000–0x73FFF | Application `f33-ble-sensors` 1.0.0 (9244 B) |
| 0x74000–0x7DFFF | Adafruit bootloader 0.11.0 r46 |
| 0x7F000 | Bootloader settings (written after each DFU) |

### Application `f33-ble-sensors`

| Version | Date | Changes |
|---|---|---|
| r44 | 2026 | First app: `F33` advertisement, custom service with data (31 bytes) and control `0x01` → DFU OTA. Reads only while connected, every 2 s. |
| r45 | 2026 | Battery Service 0x180F, Device Information (revision), control `0x02` → DFU UART. |
| r45b | 2026 | Percentage with two cells in series, fixed (the original showed 100 % only between 6 and 6.5 V). |
| r45c | 2026 | Measures every 1 s also without a connection; state in RAM for reading over SWD. |
| **1.0.0** | 2026 | **Single release version:** r45c plus the UART with a host on E1/E2 (JSON, commands, detection via E2, interval from 1 to 3600 s). Binaries in `firmware/ble-sensors/release/` with SHA-256 (`.zip` `1ba16459…`). An earlier 1.0.0 without UART (commit `406e0e1`) was not published: this one replaces it. |

The tags `r45-swd`, `r45-ota`, `r45b-ota`, `r45c-ota`, `r45c-uart`,
`r45c-uart2` and `r45c-uart3` were test builds that only changed the
version string to demonstrate each upload path. They are in the r45 evidence;
they are not versions for use.

### Bootloader

| Version | Changes |
|---|---|
| r14 | First build for the board: UART DFU on E1/E2, LED on P0.17 and P0.19, buttons on P0.20/P0.22. |
| r43 | LED on P0.17 only (P0.19 is the RTC IRQ), no buttons, BLE model "Estimote F3.3 r43". Previously validated on the reference board; replaced by r46. |
| **r46** | Same as r43 with English BLE Device Information strings: manufacturer "Estimote F3.3 (repurposed)", model "Estimote F3.3 r46". Installed and verified over SWD; BLE identity and application data validated ([record](evidence/swd-c-power-r46-2026/README.md)). |

## 5. BLE interface (version 1.0.0)

- Advertisement `F33`, connectable, every 1 s; service UUID in the scan response.
- Service `239d0001-86eb-4a92-8ec1-0e38f13e0817`:
  - `…0002` data: read and notify every 1 s, 31 bytes, packet version 1.

    | Byte | Type | Field |
    |---|---|---|
    | 0 | u8 | version = 1 |
    | 1 | u8 | valid: b0 accel., b1 mag., b2 baro., b3 light, b4 RTC, b5 ADC |
    | 2 | u16 | sequence |
    | 4 | 3 × i16 | acceleration (mg) |
    | 10 | 3 × i16 | magnetic field (mG; uncalibrated, hard-iron offset ≈1.3 G) |
    | 16 | i16 | temperature (hundredths of °C) |
    | 18 | u32 | pressure (Pa/256) |
    | 22 | u32 | light (thousandths of lux) |
    | 26 | u16 | VDD (mV) |
    | 28 | u16 | AIN3 (mV); battery ≈ 5.825·AIN3 + 0.122 V |
    | 30 | u8 | RTC seconds |
  - `…0003` control (write): `0x01` → BLE DFU (`AdaDFU`); `0x02` → UART DFU for 3 s.
- Battery Service `0x180F` / `0x2A19`: battery %, two cells in series,
  provisional table (per cell: 3.0 V = 100 %, 2.9 V = 80 %, 2.8 V = 60 %,
  2.7 V = 40 %, 2.6 V = 20 %, 2.4 V = 5 %, 2.0 V = 0 %).
- Device Information `0x180A` / `0x2A26`: firmware version.

Reader: `scripts/ble_sensors.py` (decoder: `scripts/f33_packet.py`).

BLE was tested on **macOS with Bleak**. Windows or other hosts may need adapted dependencies, permissions, identifiers, ports and commands ([platform notes](https://bleak.readthedocs.io/en/latest/backends/index.html)). ESP32 DevKit V1 BLE discovery, connection and GATT sensor reads were validated in 2026 with the Arduino example; notifications, control commands and DFU on ESP32 were not tested. DFU requires this bootloader's protocol; SWD and UART need their corresponding interfaces. Two [Arduino ESP32 examples](../examples/esp32/README.md) provide UART JSON forwarding and BLE sensor reads; both have basic physical validation on the owner's DevKit V1, supported by screenshots; S3/C3 have offline compilation checks only.

On the tested macOS setup, run Bleak from a terminal with Bluetooth permission.

## 5b. Use with a host on E1–E4 (version 1.0.0)

Any host with 3.3 V logic: Raspberry Pi, Pico or ESP32. BLE keeps
working in parallel.

| Pad | Host |
|---|---|
| E4 | GND |
| E3 | **3.3 V recommended** → VDD ≈ 3.0 V. Check logic-level margin (§3). Never 5 V. |
| E2 (nRF RX) | Host TX |
| E1 (nRF TX) | Host RX |

- **With a host, the board is powered through E3, not from the batteries.** With H, VDD is
  2.0 V and the levels are not compatible without a level shifter.
- **Automatic detection.** E2 has an internal pull-down. If the host's TX
  is idle (high), the app turns the UART on at boot or within the next
  second. If the host disconnects, it turns it off and leaves E1 in high impedance.
  The host must have its UART active, with TX high.
- UART: 115200 baud, 8N1, no flow control.
- **Data:** one JSON line per measurement, in integers. A sensor without a valid
  reading does not appear.

  ```json
  {"seq":123,"acc_mg":[12,-30,1035],"mag_mg":[1080,750,-210],"temp_cc":2810,"press_pa":100660,"mlux":22000,"rtc_s":41,"vdd_mv":3420,"ain3_mv":40,"bat_mv":355,"bat_pct":0}
  ```

  Units: mg, mG, hundredths of °C, Pa, thousandths of lux, s and mV. With
  power through E3, `bat_mv` and `bat_pct` do not correspond to any battery.
- **Commands:** one line terminated by `\n`, case-insensitive. Empty
  lines are ignored.

  | Command | Response | Effect |
  |---|---|---|
  | `read` | `{"ok":"read"}` and one data line | Measures immediately |
  | `int N` | `{"ok":"int","s":N}` or `{"err":"range"}` | Interval from 1 to 3600 s, shared by UART and BLE; returns to 1 s on reboot |
  | `ver` | `{"ok":"ver","fw":"1.0.0"}` | — |
  | `dfu` | `{"ok":"dfu"}` | Reboots into UART DFU (3 s) |
  | `ota` | `{"ok":"ota"}` | Reboots into BLE DFU (`AdaDFU`) |
  | other | `{"err":"cmd"}`; more than 32 characters: `{"err":"long"}` | — |

- **Reader:** `python3 scripts/uart_sensors.py --port <port> [--send 'int 5'] [--out folder]`.
  - Uses only the standard library.
  - On the Mac with the Pico, the port is `/dev/cu.usbmodem…`, which changes depending on the
    USB.
  - On a Raspberry, the port is `/dev/serial0`. The UART has to be enabled and
    the serial console disabled in `raspi-config`. This has not been tested on a
    Raspberry.

## 6. Reprogramming

Tools: `.venv` with `bleak` and `adafruit-nrfutil` 0.5.3.post16, pyOCD
0.46.1 and Arm GNU Toolchain 15.2.rel1 in `tools/bootloader-build/` (ignored by
git). For a fresh checkout, use the [build instructions](build.md), including
dependency installation and path selection. Once prepared, build with
`make -C firmware/ble-sensors zip`.

### Device selection limitation

Validate the target before any upload or erase. BLE scripts discover devices by
name (`F33` / `AdaDFU`); `ble_dfu.py` uses the first matching `AdaDFU` and does
not bind it to a previously selected application. Keep only one matching beacon
powered and discoverable in range, or adapt and validate selection by the
platform-specific device identifier before proceeding. `--app-name` alone does
not select a particular `AdaDFU`.

For SWD, use the intended probe ID where supported. `nrf_ctrlap.py` selects the
first connected probe and has no ID option: connect only the intended probe,
or adapt and validate its selection first. UART requires checking the current
`--port`; published probe IDs and serial paths are examples from the reference setup.

### Validation scope

BLE and UART updates and sensor access were validated on the reference unit.
The published application was renamed without changing its firmware payload;
renaming a file does not demonstrate a new upload. To distinguish a test upload,
build with a unique `FW_REV` and check the running revision afterwards. This
confirms functional upload and boot, not byte-for-byte flash identity.
The r46 bootloader was installed over SWD and verified against all populated
published HEX segments; its BLE identity and the application's BLE data were
checked in the [C/F session](evidence/swd-c-power-r46-2026/README.md). No BLE/UART
DFU payload upload was repeated with r46; earlier upload tests used r43.

### Basic, without opening the case: Bluetooth or E1–E4

| Path | Wiring | Command |
|---|---|---|
| BLE OTA | None | `.venv/bin/python scripts/ble_dfu.py package.zip` (if the app is present, it switches it to `AdaDFU`) |
| **UART via the `dfu` command (host)** | Host on E1–E4, power through E3 | `scripts/uart_dfu.py --command --port <port> package.zip`: without cutting power |
| UART via BLE command | 3.3 V adapter: TX→E2, RX←E1, GND→E4 | `scripts/uart_dfu.py package.zip` and then `scripts/ble_sensors.py --serial-dfu` |
| **UART with E1–E4 only** | Same, power through E3 | `scripts/uart_dfu.py package.zip`; then cut and restore power |

`uart_dfu.py` catches the 1 s window the bootloader opens on every boot
and launches `adafruit-nrfutil`. It works even if the application is damaged, because the
bootloader always boots first. Each upload takes ≈2–3 s over UART and ≈7–10 s
over BLE. With a Raspberry Pi Pico, the port is the debugprobe UART
(GP4 = TX → E2, GP5 = RX ← E1).

### Advanced, with the case open: SWD with a Raspberry Pi Pico

Pico with debugprobe v2.3.1 firmware:

| Pico | Board |
|---|---|
| GP2 (pin 4) | A (SWDCLK) |
| GP3 (pin 5) | B (SWDIO) |
| GND | F |
| (optional) GP5 (pin 7) | E (SWO), for traces only |
| — | G (nRESET), optional: a pulse to F resets |

Power for a Pico with 3.3 V SWD signals: a regulated 3.3 V supply on C/F,
with H and E3 disconnected. Verify the pad and voltage before connecting.
H/F can power the board from its battery pack, but VDD then stays at 2.0 V:
use a probe compatible with that target voltage or suitable SWD level
translation; direct Pico wiring at that voltage is not established as safe.
With SWD you can:
- flash the application: `pyocd flash -t nrf52 -u <id> app.hex`;
- flash the bootloader and the SoftDevice ([instructions](../firmware/adafruit-bootloader/README.md));
- verify the flash (`scripts/swd_app_check.py`);
- read live data without halting the CPU (`scripts/swd_monitor.py`);
- recover the chip if the bootloader gets damaged (full erase with `scripts/nrf_ctrlap.py`).

After a DFU, the settings page 0x7F000 is left written. Before flashing the
application again over SWD it is advisable to erase it (not verified whether this is necessary).

## 7. Lessons learned

- **I²C bus:** SDA = P0.14, SCL = P0.15. Needs the internal pull-up; without it
  the lines stay at 0. The sensors respond ≈1 s after driving P0.06/07 high.
  Addresses: LIS2DH12 0x19, LIS3MDL 0x1E, MAX44009 0x4A, M41T62 0x68, BMP280 0x77.
- **Magnetometer:** measures correctly. When rotated it traces a 0.25 G circle with a
  hard-iron offset of ≈1.3 G attached to the board; calibration still pending.
- **BMP280:** responds to heat (26.8 → 43.7 °C with a hair dryer; τ ≈ 67 s). After the
  hair dryer the pressure dropped 0.25 hPa without explanation.
- **Battery:** AIN3 ≈ V(H)/6 (r20 fit: 5.825·AIN3 + 0.122 V). With H, VDD is
  regulated to 2.0 V and the board cuts off below ≈3.0 V.
- **E3:** no apparent regulation (5 V → 4.58 V VDD). Use 3.3 V and check logic-level margin (§3).
- **UART in the app:** classic interrupt-driven UART0. The 24-bit RTC
  overflows at 512 s, so the interval is counted in seconds. When opening the
  Pico port, the remainder of an old line without `\n` may arrive: the
  scripts tolerate it.
- **Consumption:** the chip sleeps between events. ≈0.15 mA average idle with
  advertising and measurement every 1 s. The LED draws more than 2 mA when on.
  Order of magnitude with 2 × 2 CR2477 (≈2000 mAh): more than a year, not verified.
- **Bootloader on nRF52832:** 1 s serial DFU window on every boot. A single
  valid HCI packet is enough for it to wait with no timeout. GPREGRET 0xA8 = BLE DFU,
  0x4E = serial DFU (3 s).
- **Host adaptation:** tests used macOS with a Bluetooth-authorized terminal and CoreBluetooth peripheral UUIDs. Other systems may use different identifiers, dependencies, permissions and serial ports; the Arduino ESP32 DevKit V1 reader is now validated for basic GATT sensor reads.
- **Tools:** `pyocd erase --mass` gives a false timeout (verify with
  `scripts/nrf_ctrlap.py`).

## 8. Pending or possible

### Limitations

- **Platforms:** the validated setup is macOS with a Pico debugprobe. The
  Makefile defaults to a macOS ARM64 compiler path and a local Adafruit source
  tree; prepare its pinned commit and submodules, Python dependencies and paths
  before rebuilding elsewhere. UART scripts use POSIX `termios` and require
  adaptation for native Windows. A real Raspberry Pi host remains unvalidated. ESP32 DevKit V1 basic UART/BLE
  reading is validated; S3/C3 have compilation checks only.
- **BLE notifications:** the data packet is 31 bytes, requiring ATT MTU ≥34
  for a single notification. The firmware offers MTU 64; a client must negotiate
  sufficient MTU. At a smaller MTU, notifications can be dropped without an
  explicit client-facing firmware error. Verify full-length data on each host.
- **Other boards:** validation covers one F3.3. Confirm continuity, power rails,
  logic levels and sensor identities on another unit before reusing the pinout.
  Other revisions/models require their own characterization, including the
  P0.06/P0.07 sensor-enable hypothesis; the UWB pinout does not apply here.

### Pending work

- Data in the advertisement (BTHome v2) to read it without connecting, for example from Home Assistant.
- Configurable low power (measure every 30–60 s, turn sensors off between readings)
  and accurate measurement with a peak-capable meter (for example, PPK2).
- Test a real Raspberry Pi host. [ESP32 Arduino readers](../examples/esp32/README.md) have basic DevKit V1 UART/BLE validation ([record](evidence/esp32-readers-2026/README.md)); extended operation, reconnection and ESP32 control/DFU tests remain pending.
- Power E3 directly from a host's 3.3 V pin (validated at 3.3 V with a lab power supply; not yet with the real pin and its current).
- Batteries and host at the same time: needs a level shifter.
- BLE configuration stored in flash; watchdog; 32 kHz crystal; RTC time.
- Untraced pins: SKY66110 amplifier, accelerometer interrupt, pad D.
- Unexplained: the pressure drift after the hair dryer, and AIN3 ≈ 0.28 V with H
  disconnected after a boot.

## 9. Tests

```bash
python3 -m unittest tests.test_ble_firmware tests.test_sensor_readout
python3 -m unittest discover -s tests -p 'test_*uart*.py'
```

They compile `f33_math.c` and `f33_uart.c` on the Mac. They compare the conversions, the
battery, the packing, the JSON line and the commands against the Python code. The
`dfu` command is tested over a pty. There are 16 + 13 tests.
