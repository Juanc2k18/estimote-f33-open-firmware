# r39 · LIS3MDL magnetometer rotation · 2026

**Prior check** (`../sensors-check-r39-2026-11-19/`, after the
owner's rearrangement to rotate the board): Pico `E660C0D1C75C942F`
detected; SWD, bus 14/15 and all five devices respond; valid closure.

**Test:** `sensor_readout.py --only magnet,accel --rounds 40 --interval 0`.
Instructions given in the chat: still for 5 s, one slow 360° turn in the plane
of the table over about 30 s, still at the end, away from tools and magnets.
34 rounds were obtained, one every ~1.8 s, between 21:32:10 and 21:33:10.

## Result (measurement)

- **Accelerometer:** Z ≈ 1.04 g in all rounds. The rotation was in the plane,
  without tilting the board.
- **Magnetometer:** X between 0.80 and 1.34 G, Y between 0.52 and 0.96 G, Z between 0.05 and
  0.18 G. Circle fit to X/Y:
  - **centre (1.076; 0.754) G**, magnitude 1.31 G
  - **radius 0.251 G**, with RMS residual of 0.024 G
- The angle relative to the centre sweeps about 300° and then goes back a little.
  Interpretation: the rotation was not in a single direction.

## Interpretation

- **The LIS3MDL measures.** The 0.25 G radius matches in order of magnitude the
  horizontal component of the Earth's field. The circle of points indicates that the
  vector rotates with the board.
- **The constant field of ≈1.3 G is attached to the board** (hard-iron offset):
  something magnetized on the PCB or next to it, such as the battery holder, clips or
  shields. It is not an object on the table: if it were, it would not add up as a
  fixed vector in the sensor's frame. An application would have to calibrate it,
  subtracting the centre, before using the sensor as a compass.

## Closure: invalid

In round 35 SWD was lost (`Unexpected ACK 0` and then `Target not
detected`); most likely the wires moved during the rotation. Therefore:
- the LIS2DH12 and LIS3MDL registers **were not restored**, and they keep
  measuring until the board is powered off;
- the hashes were not verified;
- the SWD reset failed.

There were no writes to flash or UICR in this tool. To recover:
check the A/B/F wires, power C off and on, and re-verify.
