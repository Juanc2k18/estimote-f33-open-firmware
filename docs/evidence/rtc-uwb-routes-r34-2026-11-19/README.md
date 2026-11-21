# r34 · Background: M41T62 routes on the Estimote UWB I1.2 · 2026

Owner's question: on other Estimotes, does the RTC's I²C go straight to the
nRF or through an intermediary? On the F3.3 there is no visual continuity from RTC1
and RTC8.

## Source and method

Top layer `1Top.png` from the DIY Stuff teardown, stored without
transformation in `../diystuff-uwb-carousel-2026-11-18/`, under the author's
CC BY-NC-SA 4.0 license. nRF orientation fixed in r05: pin 1 at the bottom
right and 37–48 on the lower side from left to right. Pin 45
(VSS) is blue and serves as a check. On the LCC8 RTC, the third lower pad
is blue (ground), which matches the F3.3's r30 numbering: bottom
1 SDA/2 SQW/3 VSS/4 NC; top 8 SCL/7 NC/6 IRQ/5 VCC. Pad 7 (NC) has no
trace, another match.

Visual inspection and region filling by copper color (red and
purple) on the original image are combined. Each net was associated with the via or test
point it touches. `uwb-1top-rtc-annotated.png` is a ×2 enlarged crop with
added labels.

## Result on the UWB I1.2

| RTC | Route on the top layer | nRF52832 |
| --- | --- | --- |
| 1 SDA | trace → via shared with the trace of pin 41; another via and a branch to the left (other devices) | **41 · P0.29** |
| 8 SCL | trace → via shared with the trace of pin 42; another via to an internal layer | **42 · P0.30** |
| 6 IRQ | trace → green test point → pin 43 | **43 · P0.31** |
| 2 SQW | direct via to an internal layer | not followed |
| 5 VCC | decoupling capacitor to ground | — |

**There is no intermediate component** (series resistor, MOSFET or translator) between
the RTC and the nRF on the UWB. There are only vias and test points. The only
level translators on that board (TXB0104/TXS0101) are for the DW1000. SDA and
SCL **jump straight to internal layers** and from there continue to other
devices on the bus: that is why, on the visible side, the route cannot be followed
end to end. The pull-ups are not on these segments.

Confidence: high in the topology (direct, through vias) and medium-high in the
41/42 assignment. The association by shared via was obtained both by
inspection and by color filling, with a 3-pixel margin.

## What carries over to the F3.3 and what does not

- **The GPIOs do not carry over:** on the F3.3, IRQ goes to pin 22/P0.19 according to the
  owner, not to 43. The layout is different.
- **The pattern does carry over:** direct connection through hidden vias, with SDA/SCL/IRQ
  on **adjacent pins** of the nRF. That is why not seeing it with the naked eye is
  to be expected, not a sign of an intermediary.
- **Hypothesis for the F3.3:** SDA/SCL next to pin 22. The neighbors are 20
  (P0.17), 21 (P0.18/SWO, pad E), 23 (P0.20) and 24 (P0.21/nRESET). P0.17 is the
  most striking candidate:
  - in r29, at 6 V H/F, it was valid;
  - at 3.3 V C/F it sits at an intermediate voltage and does not rise with the pull-up;
  - with state 15 it becomes valid, and as SCL it gives `bus_busy` after STOP (it does not return high).

  That fits an I²C line whose pull-ups hang off a rail that depends
  on how the board is powered.

## Recommended measurement

With power supply and USB disconnected, three pins per pad:
**RTC1 and RTC8 against nRF pins 20, 23 and 21** (counting from the
pin 1 dot, as in r08). Note the ohms. 0–10 Ω indicates a direct connection;
1 to 10 kΩ, that the measurement is going through a shared pull-up. If a
pad reads kΩ against all of them, measure it against C (VDD), 6/7 and 14/15 to locate the
pull-up.

## Follow-up: probe with SCL in push-pull (prepared, not run)

The r32 readings of GPIO17 in the electrical validation change from 0 to 1 under the
same condition: the node is at an intermediate voltage. All previous
probes required **both** lines to be valid OD, so an SCL like that
was never addressed. The M41T62, LIS2DH12 and BMP280 do not stretch the clock, so
the host can drive SCL in push-pull.
`scripts/i2c_pushpull_scl.py` does that: it drives SCL in H0H1, leaves SDA in OD
with the internal pull-up and validates only SDA. It tests the 12 pairs of 16/17/18/20 in
the rail states off, 15 and 14, with addresses 0x68, 0x18, 0x19, 0x50,
0x76 and 0x77. `tests/test_i2c_pushpull.py` checks that the OD validation
rejects a virtual RTC with SCL on an intermediate node and that push-pull mode
finds it at 0x68.

E (P0.18) must not be connected to the Pico during the test.

```bash
python3 scripts/i2c_pushpull_scl.py --supply "3,3 V C/F" --out docs/evidence/i2c-pp-r35-2026-11-19
```

If nothing appears, `--wide` widens the candidates to 16 GPIOs (240 pairs per
state; use `--states off,15`).

## Review of the owner's photos in light of the UWB

The 13 HEIC files the owner attached again (IMG_0569–0581) are
**byte-for-byte identical** to those already archived in r28 (0569–0575) and r30
(0576–0581), checked by SHA-256. They were not duplicated.

`f33-0579-rtc-vias-annotated.png` (IMG_0579 cropped; r30 numbering, rotated 90°
because the text is vertical, with the dot next to 1/SDA):

- Next to **1/SDA** and **8/SCL** there is a **via covered by the solder mask**, and no
  surface trace leaves those pads towards the nRF. It is the same pattern as on the
  UWB: the signal goes straight to an internal layer. That is why no continuity is visible
  to the naked eye.
- Next to **6/IRQ** there is also a via, consistent with the 6→P0.19 continuity
  reported by the owner.
- **5/VCC** has a decoupling capacitor beside it, as on the UWB.
- Next to the RTC there is a black LGA chip with a matrix code (partial reading
  «9EAJ/CEAJ»). In that position, on the UWB, were the bus sensors. It still
  has no model.

The vias are marked with «?»: they are visual deductions from a photo, not
measured continuity. **To measure, there is no need to follow the trace:** it is enough to
put one probe on pad 1 or 8 of the RTC (or on its via) and the other on each
candidate nRF pin.
