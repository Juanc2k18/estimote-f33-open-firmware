# Agent notes — Estimote F3.3 open firmware

Guidance for AI coding agents (and humans) working on this repository. The
user-facing guide is [docs/guide-f33.md](docs/guide-f33.md); per-test detail is
in [docs/status.md](docs/status.md), the [logbook](docs/logbook/) and
[docs/evidence/](docs/evidence/).

## Guide the user

- Start with the next practical step. Keep instructions brief and avoid repeating background.
- Use [the guide](docs/guide-f33.md) for the current setup; treat logs as historical evidence.
- Before a hardware test, give the goal, exact wiring, voltage, command and expected result.
- Ask the user to make physical connections. BLE tests used macOS; on other systems, check Bluetooth support, permissions, device identifiers, ports and commands before adapting the steps.
- Separate owner reports, measurements and hypotheses. Never present an unresolved pin as confirmed.
- Publish only `docs/diagrams/pin-map-guide-nrf.svg`, embedded in the main README. Use VectorCraft for diagram edits/exports; do not commit native masters, PNG exports or additional diagrams. Keep the SVG checksum updated.
- Update the guide and checksums when published instructions or diagrams change. Keep test results concise.

## Critical steps and informed authorization

- Explain before proceeding: the original Estimote firmware on an APPROTECT-locked unit cannot be backed up through SWD; unlocking by full erase permanently removes it. This project provides no factory recovery image. The reference unit has already been erased.
- State what the user gains: open firmware, BLE/UART sensor access and firmware updates. State what is lost: the original firmware, its configuration and proprietary Estimote behavior; factory calibration and features are not guaranteed to carry over.
- Explain that incorrect wiring, unsuitable voltage, interrupted programming or a wrongly executed step can damage hardware or make the change irreversible. A successful flash does not guarantee that the original state can be restored.
- Obtain explicit authorization for the specific critical step before erasing/unlocking, flashing firmware or UICR, or changing power/wiring in a way that could damage equipment. Give the exact target, action, wiring, voltage and expected result first; wait for the user's answer.
- Do not treat a request to explore the project, a previous test or historical owner consent as authorization for a new critical step. Read-only documentation and offline checks do not need hardware authorization.
- Never publish personal risk-acceptance statements. Use 2026 for public validation dates. Remove calendar-date metadata from published evidence JSON; preserve measurement values, relative timings and existing evidence paths.
- Authorization never establishes an unknown pin or voltage as safe. Verify electrical compatibility and protect the computer, Pico and other equipment.
- For every hardware test, record the goal, wiring, parameters, tools and result. Separate owner reports, measurements and hypotheses.

## Current state (validated in 2026)

- nRF52832 QFAA (FICR `00052832`/`AAB0`), unlocked.
- Adafruit bootloader 0.11.0 **r46** + S132 6.1.1 on the board, matching the
  published HEX byte for byte including UICR. BLE DIS identity and app BLE data
  validated in 2026. Earlier BLE/UART DFU uploads used r43; not repeated with r46.
- Application **`f33-ble-sensors` 1.0.0** (`firmware/ble-sensors/`, release
  binaries in `release/`).
  BLE advertisement `F33`, GATT data + control, Battery and Device Information
  services, UART JSON host interface on E1/E2.
- Reprogramming validated over BLE OTA, UART (`dfu` command, BLE command or
  power cycle on E3) and SWD.

## Pinout (antenna up, eight pads on the right: A/B, C/D, E/F, G/H by rows; E1–E4 left to right)

| Pad | Signal | Basis |
|---|---|---|
| E1 | nRF TX, P0.13 (pin 16) | continuity (owner) + DFU ACK |
| E2 | nRF RX, P0.12 (pin 15) | continuity (owner) + DFU ACK |
| E3 | external power input | owner; 5 V gives VDD 4.58 V (above abs. max) → use 3.3 V |
| E4 | GND | owner |
| A | SWDCLK (pin 25) | continuity + SWD link |
| B | SWDIO (pin 26) | continuity + SWD link |
| C | VDD | continuity (owner); do not power C while H or E3 is powered |
| D | unresolved | — |
| E | P0.18 / SWO (pin 21) | functional (UART and ITM frames) |
| F | GND / battery − | owner |
| G | P0.21 / nRESET (pin 24) | ≈2.1 Ω + functional reset |
| H | battery + (orig. 4 × CR2477, 2S2P per owner) | VDD regulated to 2.0 V; shuts down < ≈3.0 V, restarts ≈3.3 V |

nRF pin 1 is at the bottom-left corner (chip rotated 90° CCW): pins 1–12 bottom,
13–24 right, 25–36 top, 37–48 left. No NFC.

Internal assignments: I²C **SDA = P0.14, SCL = P0.15** with the **internal
pull-up**; drive **P0.06/P0.07 high** first (likely sensor power) and wait ≈1 s.
Devices: LIS2DH12 0x19, LIS3MDL 0x1E, MAX44009 0x4A, M41T62 0x68, BMP280 0x77.
LED on P0.17 (transistor, active high). RTC IRQ on P0.19 (not an LED).
Battery divider on P0.05/AIN3 (≈1:6; V_bat ≈ 5.825·AIN3 + 0.122 V).
`PSELRESET[0:1] = 21`.

## Rules of thumb

- Check logic levels against measured VDD; listen before transmitting on an unknown line.
- E3 recommendation: 3.3 V. At VDD ≈3.0 V, nominal 3.3 V host TX has little or no margin; verify levels or use suitable translation.
- H/F accepts the original ≈6 V battery pack but VDD stays at 2.0 V. Direct 3.3 V Pico SWD needs compatible levels; for 3.3 V on C/F disconnect H and E3.
- Validate the target first. BLE DFU selects by name: only one matching beacon in range unless selection is adapted and validated by ID. `nrf_ctrlap.py` uses the first probe: only the intended probe connected unless its selection is adapted.
- Never connect two supplies at once (H and E3). With a UART host, power from E3
  (3.3 V) and leave H disconnected: on H, VDD is 2.0 V and 3.3 V UART levels
  exceed VDD + 0.3 V.
- GPIO 12/13 belong to the UART (bootloader and app). Do not repurpose them in
  SWD diagnostics. Do not touch GPIO 21 (reset).
- `pyocd erase --mass` reports a false timeout: verify with `scripts/nrf_ctrlap.py`.
- After a DFU upload, the bootloader settings page 0x7F000 is written; erase it
  before reflashing the app over SWD.
- Automated bus sweeps produced false positives (e.g. "SDA25/SCL9/0x46"):
  validate idle levels, repeat, and read ID registers before claiming a device.
- BLE was tested on macOS using `bleak` from a terminal with Bluetooth permission; the agent process in that environment had none. Windows or other hosts may need adapted dependencies, identifiers, ports and permissions. ESP32 DevKit V1 basic UART JSON reception and BLE discovery/connection/GATT reads are validated by owner report and screenshots (`docs/evidence/esp32-readers-2026/`). Notifications, control commands, induced reconnection and DFU on ESP32 are untested; S3/C3 have compilation checks only. SWD and UART still require suitable interfaces.
- The Pico's serial port name (`/dev/cu.usbmodem…`) changes with the USB port.
- Keep the third-party UWB images unmodified; their license is CC BY-NC-SA 4.0
  (see [THIRD_PARTY.md](THIRD_PARTY.md)). The UWB pinout does **not** apply to
  the F3.3.

## Latest hardware validation and owner preference

- 2026: owner reports C/F at 3.3 V for the final intended direct-C session.
  SWD r46 installation and 1.0.0 restoration succeeded; all published HEX
  segments match readback. BLE DIS identifies r46; app BLE data has all sensors
  valid. App reset/return verified. No BLE/UART DFU payload upload repeated.
- After this session, owner requests operation at 6 V on H/F, already validated
  as a battery input. Do not extend that validation to C/E3 or assume 3.3 V SWD
  signal compatibility at the resulting 2.0 V VDD. See
  `docs/evidence/swd-c-power-r46-2026/README.md`.

## Open items

Pad D; RF amplifier (SKY66110) control pins; accelerometer interrupt; RTC time
setting; 32 kHz crystal use; BTHome advertising; low-power mode; testing the
UART host on a real Raspberry Pi; extended ESP32 tests (basic DevKit V1 UART/BLE reading is validated). See [docs/guide-f33.md](docs/guide-f33.md) §8.
