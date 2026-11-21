# r45 · Battery, firmware upload without SWD and power via E1–E4 · 2026/20

Objective: check whether the board can depend only on the four pins E1–E4 (or
on the batteries on H/F plus E1–E2) to be used and reprogrammed. The battery
voltage, the operating threshold, the E3 voltage and the four
application upload paths were measured.

## r45 firmware (`firmware/ble-sensors/`)

- **r45:** Battery Service 0x180F (level 0x2A19, read and notify),
  Device Information 0x180A (revision 0x2A26 = `FW_REV`) and control command
  `0x02` → GPREGRET 0x4E → UART DFU for 3 s.
- **r45b:** percentage with two cells in series, fixed. The owner reports that
  the original only showed 100 % between 6 and 6.5 V and less at 3.3 V. So
  r45 (automatic 1S/2S, which gave 100 % at 3.3 V) was discarded.
- **r45c:** measures every 1 s also without a connection and leaves `f33_status` in RAM
  ("F33S", RESETREAS, counter and packet) so it can be read over SWD without halting the CPU.

Battery (provisional): V(H) ≈ 5.825·AIN3 + 0.122 V, a fit of the r20 curve
with power supply setpoints and no metrology. Per cell: 3.0 V = 100 %,
2.9 V = 80 %, 2.8 V = 60 %, 2.7 V = 40 %, 2.6 V = 20 %, 2.4 V = 5 %, 2.0 V = 0 %,
with linear interpolation. It is a typical lithium CR curve, not that of the original
firmware. SoftDevice FWID read over SWD at 0x300C: **0xB7** (S132 6.1.1), used
in `--sd-req`.

The versions differ only in the `FW_REV` string. Thus, the version the board
advertises shows which image was uploaded by each path. The images and packages in
`hex/` were withdrawn from publication on 2026: only version 1.0.0 is distributed; the hashes are kept as a record in `SHA256SUMS`.

## Firmware upload: all four paths work

| Path | Image | Result | Evidence |
|---|---|---|---|
| SWD (`pyocd flash`) | r45-swd | Advertises `r45-swd` | `flash-r45-swd.log`, `mac-r45-swd/` |
| BLE OTA, command `0x01` + `scripts/ble_dfu.py` | r45-ota | 6856 B in 8.3 s; advertises `r45-ota`; **flash = .bin byte for byte via SWD** | `mac-ota-r45-ota/`, `swd-check-after-ota.json` |
| BLE OTA (repeat) | r45b-ota | 7.0 s; advertises `r45b-ota` | `mac-ota-r45b-ota/`, `mac-after-ota-r45b/` |
| BLE OTA (repeat) | r45c-ota | 7.0 s, ≈1.1 kB/s | `mac-ota-r45c-ota/` |
| UART E1/E2, BLE command `0x02` + `scripts/uart_dfu.py` | r45c-uart | Bootloader caught; nrfutil 2.2 s; advertises `r45c-uart` | `uart-ble-0x02/`, `mac-command-0x02/`, `mac-after-uart/` |
| **UART E1/E2 with E1–E4 only:** E3 cut and restored | r45c-uart2 | 1 s window caught at power-on; 2.2 s; advertises `r45c-uart2` | `uart-cold-start/`, `mac-after-uart-cold/` |
| UART E1/E2 with E1–E4 only, **E3 at 5 V** (owner's decision, Pico connected) | r45c-uart3 | Caught at power-on; 2.2 s; advertises `r45c-uart3`; SAADC VDD saturated at 3.60 V | `uart-e3-5v/`, `mac-after-uart-e3-5v/` |

- After the first DFU, the bootloader writes the settings page 0x7F000
  (`0x1`, size `0x1AC8`). To flash again over SWD it is advisable to erase
  that page first; otherwise, the application check may use data from the
  previous image. Not verified.
- `scripts/uart_dfu.py` sends a reliable HCI packet of type 0x06 every 30 ms, which
  the bootloader discards, until it receives its ACK. This signals activity and the
  bootloader no longer has a timeout. It then completes the sequence wrap-around and
  launches `adafruit-nrfutil` (0.5.3.post16, installed in `.venv` from PyPI).
- The UART uploads were not verified byte for byte, because A/B were
  disconnected. Only the advertised version was checked.

## Battery curve (power supply on H/F, reading over SWD)

`swd-battery-curve/` (r45c, `scripts/swd_monitor.py`, 86 samples,
00:06:55–00:09:32). The owner lowered and raised the power supply by hand. He reports that
the power supply was the beacon's only power source (the Pico only SWD).

| Moment | Estimated H | VDD |
|---|---|---|
| Ramp-down, last reading (00:07:07.9) | **3.02 V** | 2.006 V |
| SWD lost (00:07:08.9) | — | — |
| POR boot (00:08:04); first measurement (00:08:09) | **3.31 V** | 2.001 V |
| End | 5.99 V | 2.000 V |

- **VDD = 2.00 V fixed down to 3.02 V and abrupt shutdown**, without a gradual drop. It is
  consistent with an undervoltage cutoff at the battery input, but it is not
  identified.
- It agrees with what the owner reports: the LED flashes on boot,
  near 3 V when ramping up, and batteries at ≈2.3 V did not make the board work.
- Earlier attempt lost: the BLE reader did not reconnect and the connection dropped
  at 23:49:40, before the first step. That is why `--duration` with
  reconnection was added to `scripts/ble_sensors.py`. `mac-curve-cancelled-6v/` is a
  cancelled recording at 6 V. Without recorded setpoints, this curve does not
  recalibrate the r20 fit.

## E3/E4 as power input (H/F, C and the Pico disconnected)

| E3 | VDD | Source |
|---|---|---|
| 5.0 V | **4.58 V** (owner's multimeter, C/F); SAADC saturated at 3.60 V | `mac-e3-5v/` |
| 3.7 V | **3.42 V** (SAADC) | `mac-e3-3v7/` |

- With 5 V on E3 the nRF52832 exceeds its absolute maximum (3.9 V). The
  E3→VDD drop is ≈0.3–0.4 V: it looks like a diode, not a regulator (hypothesis).
- AIN3 ≈ 0.04–0.08 V: E3 does not feed the H divider path.
- Assignment consistent with the Location Beacon article provided by the
  owner (GND, Vcc IN, GPIO0 = RX, GPIO1 = TX): E4 = GND, E3 = Vcc IN,
  E2 = RX (P0.12), E1 = TX (P0.13). That article states 5 V, but this unit,
  with custom firmware, measures 4.58 V VDD with 5 V.
- **Test at 5 V with the Pico connected (decided by the owner):** the UART
  upload worked in both directions. The Pico transmits at 3.3 V to an nRF with
  VDD ≈ 4.6 V, below the nominal threshold 0.7·VDD ≈ 3.2 V, and it still received.
  E1 delivered ≈4.6 V to GP5 of the RP2040, whose absolute maximum is ≈3.8 V. That
  it works does not show that it is within specification: there may be latent
  damage in the nRF or the Pico.
- **Recommended use: E3 ≈ 3.6–3.9 V**, or an external regulator if starting from
  5 V. With 3.7 V the UART runs at ≈3.4 V, compatible with the Pico without
  adapters.
- Unexplained observation: after the cold boot, AIN3 read 0.27–0.28 V with
  H unconnected (before, 0.04 V).

## Current (owner's multimeter in series with H, power supply at 6 V, Pico disconnected)

Application r45c-uart3, which measures every 1 s. 2 mA range. Owner's
readings, instrument model not recorded; the Mac confirmed each state over BLE:

| State | BLE check | Reading |
|---|---|---|
| Boot (≈2 s: bootloader UART window and the app's 1 s wait with the CPU active) | — | ≈4 mA and then ≈3.7 mA (20 mA range) |
| A: advertising every 1 s and measuring every 1 s, no connection | — | **≈0.15 mA**, sometimes 0, peaks the instrument cannot follow |
| B: connected, notification every 1 s (00:57:52–00:58:40, 48 samples, no restarts) | `current-B-connected/` | ≈0.15–0.5 mA, mean slightly higher than A |
| C: bootloader `AdaDFU` (00:59:20; 67 advertisements, RSSI −61 dBm) | `current-C-adadfu*/` | **> 2 mA** (overload); bootloader LED blinking via PWM |

- With the LED on, the 2 mA range overflows: the LED draws more than
  2 mA. In the app it only flashes for 50 ms on boot and on connection.
- The app sleeps between events (`sd_app_evt_wait`). The idle mean is on the
  order of 0.1–0.5 mA. A multimeter averages millisecond radio peaks poorly,
  so this is an estimate, not a measurement of average consumption.
- Order of magnitude, not verified: with 4 × CR2477 in 2S2P (≈2000 mAh at 6 V,
  nominal figure), 0.15 mA ≈ 1.5 years and 0.3 mA ≈ 9 months.

## Final setup

After the current measurements, the owner cut and restored power and
the app came back (`mac-back-app/`). Then the **release
version 1.0.0** (r45c code; `ota-release-1.0.0/`, `mac-release-1.0.0/`) was loaded over BLE OTA: it advertises
`1.0.0`, battery 97 %, all sensors valid. Setup at closure: power supply at 6 V
on H/F; E3/E4 and the Pico disconnected.
