# r44 · BLE sensor application · 2026

First custom application on S132 6.1.1, running under the r43 bootloader. Code in
`firmware/ble-sensors/`; design in internal planning notes (not published).

## Setup

Power supply on H/F (unchanged since r40), C without supply; VDD measured by SAADC ≈2.00 V.
Pico SWD on A/B; E1/E2 connected to the Pico (UART DFU, not used in this test).
Mac with bleak 3.1.0 in a terminal tab.

## Result

| Step | Result | File |
|---|---|---|
| SWD flashing (0x26000, 2 sectors) | correct (r44a; r44b the same, no log saved) | `flash.log` |
| r44a boot | PC in the application, radio on advertising channels | `swd-check-r44a.json` |
| Mac, r44a | 10/10 notifications, MTU 64, **only ADC valid**: all five I²C chips fail | `mac-rest/` |
| Diagnosis | SDA/SCL at 0 with P0.06/07 high and TWIM off; they rise to 1 with the internal pull-up | — |
| Mac, r44b | 10/10 notifications, **all six fields valid** | `mac-rest-b/` |
| Control `0x01` | the board restarts as `AdaDFU` (79 advertisements, RSSI −69/−65/−59 dBm) | `mac-dfu-adadfu/` |
| Back to the app | SWD reset with GPREGRET=0: PC in the app, advertising | `swd-check-final.json` |

r44b values at rest (measurement): acceleration (−0.02; 0.32; 0.98) g, |B| ≈1.55 G
(includes the hard-iron offset from r39), 1006.6 hPa, 26.2 °C, 31.7 lx,
VDD 2.00 V, AIN3 ≈0.54 V, RTC seconds advancing in steps of 2. Consistent with
r37–r40. The first sample (#1) is taken on connection, before notifications are
enabled; that is why the series starts at #2.

## Finding: bus pull-ups

In r44a the TWIM was configured without internal pull, assuming external pull-ups
powered by P0.06/P0.07 (interpretation from r36). With P0.06/07 high
(S0S1 and then H0H1) and the TWIM off, P0.14/P0.15 read 0. The software I²C
of r36–r39 used the nRF internal pull-up (PIN_CNF=12). With
PULL=Pullup the lines rise and all five chips respond. **Provisional
conclusion:** there are no effective external pull-ups on 14/15; P0.06/07 would be the
sensors' power supply (no continuity or current measurement to
confirm it). r44b leaves P0.06/07 at H0H1 and the internal pull-up on 14/15.

## Notes

- The `0x01` write ends in a disconnection before the response, because the
  firmware restarts on receiving it; `ble_sensors.py` records it as such.
- The linker warns about unimplemented `_close/_lseek/_read/_write` (newlib
  nosys); they are not used.
- `f33-ble-sensors.hex` corresponded to r44b; withdrawn from publication on 2026: only version 1.0.0 is distributed; the hashes are kept as a record in `SHA256SUMS`.

## r44c · Timed stimuli (22:54:00–22:56:20)

The owner followed seven 20 s phases by the clock, given in the chat:
still, covered, flashlight, rotation on the table, on edge, face down and still. The
Mac received **75 of 75 notifications** (seq 2–76, no gaps), all with the
six fields valid. Transitions arrive between 2 and 6 s after the nominal
time. Data in `mac-stimuli/`.

| Phase | Measurement |
|---|---|
| Still | (0.00; 0.05; 1.04) g, 56.9 lx, 1006.6 hPa, 26.8 °C |
| Covered | light 57 → **0.135 lx**; BMP280 temperature rises 26.7 → 31.0 °C (heat from the hand, interpretation) |
| Flashlight | light up to **11 382 lx**; magnetometer z 0.22 → 0.47 G with the phone on top (phone magnets, interpretation) |
| Rotation | the field angle relative to the r39 hard-iron centre (1.08; 0.75) G sweeps ≈+21° → −173° → +140° with radius 0.23–0.29 G: more than half a turn; the rest overlaps with the next phase |
| On edge | **x ≈ +1.08 g** |
| Face down | **z ≈ −1.03 g**, light ≈4.8 lx |
| Final still | z ≈ +1.05 g, light ≈46 lx, temperature 28.1 °C and falling |

Pressure stays at 1006.5–1006.7 hPa in all phases. The gravity
magnitude, ≈1.04–1.08 g, matches r37 (possible gain error
of ≈5 %, not calibrated).

## r44d · Hair dryer (23:02:00–23:03:50)

Phases given in the chat: reference, air in short passes at 20–30 cm from
23:02:20 to 23:02:50, and cool-down. A hair dryer was used instead of a heat
gun, so as not to damage wires, Pico or solder joints. **70 of 70 notifications**
(seq 78–147, no gaps), all valid. Data in `mac-hairdryer/`.

- BMP280 temperature: 26.8 °C stable; starts rising at 23:02:24 and
  reaches **43.7 °C** at 23:02:38. It falls exponentially
  (τ ≈ 67 s, fit from 23:02:50) to 31.5 °C at 23:04:02.
- Pressure: mean of 1006.70 hPa before the air and 1006.44–1006.47 hPa after.
  That 0.25 hPa drop does not recover on cooling, so it is not attributed to
  temperature. It remains unexplained; it is within the chip's absolute accuracy
  (±1 hPa).
- Light ≈81–84 lx, with a momentary dip to 60 lx (shadow, interpretation).
  Magnetometer stable (|B| 1.19–1.21 G): the dryer motor does not disturb it at
  that distance. |g| fluctuates up to 1.095 during the air (handling or
  vibration).
