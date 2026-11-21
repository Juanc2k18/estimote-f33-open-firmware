# r37 · Real sensor reading on SDA=P0.14 / SCL=P0.15 · 2026

Run by the agent, at the owner's request ("let's go with test 1"), of
`scripts/sensor_readout.py --rounds 6 --interval 2 --supply "3,3 V C/F"`.

**Goal:** check that each sensor measures, not just answers with its ID.

**Setup:** according to the owner, 3.3 V on C/F and Pico SWD (A/B). No wiring
change since r36. The board stayed still on the table; nobody moved or covered it
between rounds.

**Method:** from RAM (RailBoard), with P0.06/P0.07 high (H0H1). Bit-bang bus
in open drain with internal pull-up, electrically validated. Before
configuring, the address ACK of all five devices was checked.

Writes, all to volatile registers and read back to verify them:

| Sensor | Registers written | Restored at the end to |
|---|---|---|
| LIS2DH12 0x19 | CTRL_REG1 0x20=0x57, CTRL_REG4 0x23=0x80 | 0x07 / 0x00 |
| LIS3MDL 0x1E | CTRL_REG1 0x20=0x90, CTRL_REG2 0x21=0x00, CTRL_REG3 0x22=0x00 | 0x18 / 0x00 / 0x03 |
| BMP280 0x77 | ctrl_meas 0xF4=0x25 (forced measurement; returns to sleep by itself) | — |

No writes to the MAX44009 (0x4A) or the RTC (0x68).

## Result (measurement)

| Round | Acceleration (g) | Magnetometer, magnitude | BMP280 | Light | RTC seconds |
|---|---|---|---|---|---|
| 1 | 0.028 / 0.036 / 1.036 | 1.613 G | 1006.63 hPa · 28.41 °C | 22.1 lx | 24 |
| 3 | 0.036 / 0.040 / 1.048 | 1.611 G | 1006.68 hPa · 28.47 °C | 22.0 lx | 36 |
| 6 | 0.040 / 0.032 / 1.040 | 1.607 G | 1006.65 hPa · 28.27 °C | 22.0 lx | 53 |

- **The LIS2DH12 measures.** |a| = 1.04 g with Z vertical (board horizontal). There is noise
  between rounds. Scale error ≈ +4 %, normal without calibration.
- **The BMP280 measures.** Its factory calibration is consistent. Pressure ≈ 1006.6 hPa,
  plausible near sea level, and temperature ≈ 28.4 °C, with noise.
- **The MAX44009 (probable) measures.** 22 lx; it was ≈ 90 lx in r36, with different light and a
  different time (21:12 local). The response to covering or illuminating has not been seen yet.
- **M41T62:** advances ~6 s per round (2 s interval plus the reading time).
- **The LIS3MDL responds with live data**, with noise and DRDY active, but its magnitude
  of 1.61 G is outside the Earth's range (0.25–0.65 G), especially on X/Y
  (1.33 / 0.90 / 0.17 G). It is constant, so it looks like a hard-iron offset:
  magnetized parts of the board, battery clips or a magnet or tool on
  the table. Assumed scale ±4 G (6842 LSB/G), confirmed by CTRL_REG2=0. To
  validate it: rotate the board in its plane and see that X/Y trace an offset
  circle.
- The LIS3MDL's internal temperature (~27 °C) is relative, with no factory offset.

## Earlier runs on the same day

- `../sensors-reading-r37a-nack-2026-11-19/`: the first reading of 0x19 gave a
  NACK about 0.4 s after raising 6/7. That is why a 1 s wait and
  the presence check with retries were added. In r37, 0x19 answered NACK on the
  first attempt and ACK on the second; the others answered on the first.
  Hypothesis not demonstrated: 6/7 power something more than the pull-ups, or the first
  transaction after power-up is lost.
- `../sensors-reading-r37b-field-2026-11-19/`: configuration and calibration
  correct. It aborted because of a tool error (duplicate `time` field in the
  record), since fixed. The sensors were restored.

## Closure

Registers restored (`restore ok`). Bootloader `589c61bd…` and UICR `82ea7e30…`
unchanged, PC in the bootloader (0x750F2) and CNF19=0. Reset performed.

Files: `events.jsonl`, `summary.json`, `report.md`; hashes in `SHA256SUMS`.
