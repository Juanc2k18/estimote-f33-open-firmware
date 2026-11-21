# r38 · Guided reading with stimuli · 2026

`scripts/sensor_readout.py --guided --interval 8 --supply "3,3 V C/F"`. Before
each round the tool showed an instruction in the terminal tab,
gave 8 s to carry it out and then read the sensors. Setup and method as in r37.
**Owner report (afterwards):** they did not see any instruction (the terminal
tab was not in view). They alternated strong and dim light by hand and stopped
doing so at the end; they moved the board slightly, without defined orientations; they did not
rotate it deliberately. The "Instruction" column is only what the tool
showed, **not the stimulus applied**.

| R | Instruction | Accel. X/Y/Z (g) | Mag. X/Y/Z (G) | Light (lx) |
|---|---|---|---|---|
| 1 | still, horizontal | 0.07 / −0.08 / 1.12 | 1.30 / 0.86 / 0.19 | 33 |
| 2 | rotate 90° in the plane | 0.23 / 0.06 / 1.04 | 1.31 / 0.91 / 0.23 | 29 |
| 3 | 180° | 0.14 / 0.04 / 1.08 | 1.29 / 0.91 / 0.20 | **1060** |
| 4 | 270° | 0.15 / 0.00 / 1.08 | 1.31 / 0.91 / 0.19 | **1031** |
| 5 | initial position | 0.21 / −0.03 / 1.05 | 1.31 / 0.90 / 0.21 | 78 |
| 6 | on its edge | 0.16 / 0.06 / 1.04 | 1.28 / 0.89 / 0.19 | 25 |
| 7 | upside down | 0.04 / 0.05 / 1.05 | 1.32 / 0.90 / 0.20 | 23 |
| 8 | cover the light | 0.04 / **−0.40 / 0.83** | 1.29 / 0.93 / 0.17 | 26 |
| 9 | flashlight | 0.15 / −0.12 / **0.74** | 1.30 / 0.93 / 0.19 | 26 |
| 10 | still | 0.20 / 0.01 / 1.07 | 1.27 / 0.92 / 0.14 | 22 |

Pressure 1006.56–1006.65 hPa in all rounds.

## Reading of the data (measurement + owner report)

- **MAX44009: responds to light.** 22 → 1060 lx (×45) in R3–R4, then 78 and
  22 lx; this matches the reported strong/dim alternation and the end without
  stimulus.
- **LIS2DH12: responds to movement.** Up to Y=−0.40 / Z=0.83 g (R8) and |a|=0.77 g
  while moving (R9); this matches the reported slight movement. The automatic
  "review" verdict is due to R9 (outside 0.8–1.2 g because of the dynamics).
- **LIS3MDL: no conclusion.** Variation < 0.06 G, but the board was not rotated
  deliberately; a slight tilt changes the field little. It is neither a
  validation nor a failure. Pending: a slow 360° rotation in the plane, away from magnets.
- **BMP280:** stable, as expected.

Tool defect: the instructions were only shown in a terminal tab
the owner could not see. For the next test they are given in the chat.

## Closure

The registers were restored. Bootloader `589c61bd…` and UICR `82ea7e30…`
unchanged, PC in the bootloader and CNF19=0. The first presence attempt at 0x19
again gave a NACK and the second, an ACK, as in r37.

Files: `events.jsonl`, `summary.json`, `report.md`; hashes in `SHA256SUMS`.
