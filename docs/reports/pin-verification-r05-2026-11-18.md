# Documentary verification of candidates A–H · r05

Date: 2026, America/Lima. Image review, **no electrical measurements and no connections to the beacon**. Its goal is to check whether the provisional assignments of the eight pads derived from the UWB I1.2 teardown were read correctly. It also looks at what indicates that the pad block follows the same layout on the F3.3.

## Tools and method

- Unmodified carousel originals: `docs/evidence/diystuff-uwb-carousel-2026-11-18/` (hashes in `manifest.json`).
- F3.3 reference photo from the internet (2594×1884), not included in the repository. It is not a measured photo of our unit.
- Crops with `scripts/crop_layer.py` (Pillow 12.3, `python3`). Transparent background composited over white, without rotating or mirroring. Crops saved in [uwb-route-verification-2026](../evidence/uwb-route-verification-2026-11-18/) with `SHA256SUMS`.
- Color sampling in rings of 35/50/70 px around each via, on all four layers, to distinguish a via **joined** to a plane (no white separation ring) from one that **passes through it isolated**.

Coordinates in pixels of the original 6816×3878 layers.

## 1. Package orientation in the UWB drawing: confirmed by five independent indicators

The previous analysis assigned pins without recording the rotation of the nRF in the drawing. It is now fixed as follows, in the top view of `1Top.png`:

| QFN48 side in the drawing | Pins |
| --- | --- |
| Left, top to bottom | 25 → 36 |
| Bottom, left to right | 37 → 48 |
| Right, bottom to top | 1 → 12 |
| Top, right to left | 13 → 24 |

This is the standard counter-clockwise numbering, rotated 180°: pin 1 ends up in the bottom-right corner. Indicators:

1. **ANT/VSS.** Sixth pin on the left side: trace towards the matching network and the antenna RF switch (= 30, ANT). The seventh joins the exposed pad with a blue trace (= 31, VSS).
2. **VSS 45.** The ninth pin on the bottom side is blue (ground) → 37+8 = 45.
3. **NFC.** The two top pins on the right side have orange traces towards the NFC coil visible in `4Bot.png` (= 11/12, P0.09/P0.10 NFC1/NFC2).
4. **VDD 13.** The right end of the top side goes to a capacitor and to a via joined to the red bottom plane, the same plane as C (see §3).
5. **Marking.** In `1TopComponents.png`, the text `N52832 QFAAB0 1701FG` reads upside down; the chip is rotated 180°, consistent with pin 1 at the bottom right.

If the direction is reversed, indicators 1–3 no longer hold. Confidence **high**, for the UWB drawing.

## 2. A and B were swapped

Tracing of the top layer (`1Top-pads-mcu.png`, `1Top-ab-pins.png`). The original block `B D F H / A C E G` rotated 90° clockwise is kept:

- **A** (bottom left in the original): the trace leaves from the bottom edge, runs down diagonally and enters the **first top pin on the left side** = **25, SWDCLK**.
- **B** (top left in the original): the trace leaves from the left edge, goes around the outside of the block and enters the **second** pin = **26, SWDIO**.
- The two traces do not cross. 25 is the corner neighbor of 24, where G ends; this gives an internal confirmation.

**Correction:** A→**SWDCLK/25** and B→**SWDIO/26**. This replaces A→SWDIO/26 and B→SWDCLK/25 from the previous consolidation.

## 3. Remaining pads in the UWB drawing

| Pad | Observed route | r05 result | Confidence on the UWB |
| --- | --- | --- | --- |
| C | Via with no trace on inner layers 1 and 2 (isolated from the ground plane in 3Inner). In `4Bot` it is **joined to the red plane**, which also receives the decoupling via of VDD 13 | **Regulated VDD** (plane) | Medium-high; rises from «weak hypothesis» to candidate |
| D | Via → first inner layer, thin red trace towards the lower power/RTC area | Unresolved | No change |
| E | Via under the pad → short link in 2Inner → via → fourth pin on the top side from the left | **P0.18 / SWO, 21** | High (confirmed) |
| F | Grey-blue ground area; via **joined** to the ground plane of 3Inner | **GND/VSS** | High (confirmed) |
| G | Top trace to the pin in the top-left corner; also a trace to a nearby component (possible pull-up/capacitor) | **P0.21 / nRESET, 24** | High (confirmed) |
| H | Dark red pad; via → thick dark red trace in 2Inner, the same color as the battery pads in `4Bot` | **Battery +** | High (confirmed) |

The block matches a complete programming connector: **VDD, GND, SWDIO, SWDCLK, nRESET, SWO, battery + and D**.

## 4. Does the F3.3 share the same layout?

Indicators in the F3.3 reference photo (crop removed from the publication because it is an internet image):

- Same block of 2×4 rectangular pads with the same spacing, rotated 90° relative to the UWB.
- **Triangular mark next to a corner of the block** on both boards: on the UWB, next to the original pad A (bottom left); on the F3.3, top left, next to our A. The 90° clockwise rotation takes one mark to the other. **This independently confirms the geometric correspondence**, which previously rested only on the shape of the block.
- The owner identified F=GND and H=battery on the F3.3. These are the same functions the UWB gives those pads after the rotation.

Differences that prevent carrying over the **routes**: the F3.3 has a different layout (block on the right, MCU center-left, no DW1000 and a different connector). What carries over is the **test connector assignment**, plausible as a standard Estimote factory fixture. The traces do not. In the F3.3 photo, the nRF marking and pin 1 dot are not legible; 12 pins per side are counted (QFN48).

Conclusion: it is **likely** that the F3.3 uses the same factory assignment. It is the best estimate available, but only continuity proves it.

## 5. Changes applied

- See the [final diagrams](../pin-candidates.md) for the current map and editable master.
- `pin-candidates.json/.md`, `AGENTS.md`, `status.md`, `unit.md`, `hardware.md`, comparison report and logbook updated.

## 6. Recommended cold check (in order)

No batteries and no power supply. Multimeter in continuity/diode mode, fine probes:

1. F ↔ E4 and F ↔ battery negative terminal (confirms GND). H ↔ battery positive.
2. **C ↔ VDD**: with power applied, C should measure around the regulator output (≈1.8–3.3 V), not the battery voltage. First, cold, C ↔ decoupling capacitors next to the nRF.
3. Locate pin 1 of the nRF on the F3.3 under magnification, and measure A ↔ 25 and B ↔ 26. If A shows no continuity with 25, try 26: this detects whether the F3.3 swaps the pair.
4. E ↔ 21 and G ↔ 24.
5. If 1–4 check out, the A/B/C/F/G block is enough to connect an SWD probe: SWDCLK, SWDIO, VTref, GND and reset.

## 7. r06 extension: external connector E1–E4 on the UWB

Owner's question: do the reference images mark a tentative destination for E1/E2 on the nRF? Yes: the UWB drawing allows them to be traced. Crops: `1Top-connector-gpio.png`, `1Top-gpio-resistors.png`, `2Inner-gpio-segment.png` and `1Top-gpio-pins-8-9.png`.

The UWB connector (08 in the photo) has four pads in the same view as our F3.3, with the pins facing up.

| UWB pad, left to right | Observed route | F3.3 equivalent | Tentative destination |
| --- | --- | --- | --- |
| 1 | Top trace → **series resistor** → via → 2Inner → via → right-side pin no. 8 | **E1** (GPIO1/TX?) | **8 · P0.06** |
| 2 | Via next to the pad → short segment in 2Inner → parallel top trace → **series resistor** → via → 2Inner → via → pin no. 9 | **E2** (GPIO0/RX?) | **9 · P0.07** |
| 3 | Wide red power trace | E3 (5 V, owner) | Power input |
| 4 | Blue ground pad | E4 (GND, owner) | GND |

The pin numbering follows the orientation fixed in §1: pins 8 and 9 are on the 1–12 side, next to the NFC pins 11/12 and the 32 kHz crystal pins 2/3. Pads 3/4 match the owner's E3=5 V and E4=GND. This supports the connector equivalence having the same order. Confidence **medium**: the UWB route is clear, but the F3.3 is a different board.

Consequences for measuring:
- With a series resistor, E1↔8 continuity will not "beep": it is measured in **ohms**, and the reading is the resistor value (record it).
- In diode mode, E1/E2 relative to E4 add the resistance to the protection diode drop. The reading may exceed 0.7 V without meaning it is open.
- P0.06/P0.07 are normal GPIOs. They are usable for UART or a serial bootloader, never for SWD.

## 8. Recorded owner answers

- **Raspberry at 5 V in external guides:** on a Raspberry Pi, the 5 V pin is power. Its GPIO/TX/RX work at **3.3 V** and are not 5 V tolerant. A guide that connects a Pi probably takes 5 V to Vcc IN (E3) and the UART at 3.3 V. That suggests 3.3 V logic on the beacon, but it has not been measured. A 5 V Arduino is not equivalent.
- **Listen before transmitting:** validated by the owner as a rule of the method.
- **Automatic baud rate detection with a microcontroller:** just an idea; proposed for later.
- **Diode-mode test E1/E2–E4:** pending.
- **Continuity E1↔8 / E2↔9:** pending, with the tentative targets of this section.

## 9. r07 extension: rotation of the nRF on the F3.3

Owner report, from visual observation of their unit (no measurement):

- **Pin 1 dot** in the **bottom-left** corner of the nRF, with the antenna at the top and the pads on the right. The guide previously drew it at the top left (standard view), so the chip is **rotated 90° counter-clockwise**.
- **Triangular mark** next to the block: not seen on this unit. The one on the UWB and in the reference photo no longer counts as support for our board.
- **NFC:** the unit has no NFC coil.

Resulting numbering, viewed from above:

| Side | Pins |
| --- | --- |
| Bottom, left to right | 1 → 12 |
| Right, bottom to top | 13 → 24 |
| Top, right to left | 25 → 36 |
| Left, top to bottom | 37 → 48 |

Consistencies that are not electrical proof, but support the reading:

- 21 (SWO), 24 (nRESET), 25 (SWDCLK) and 26 (SWDIO) end up together in the **top-right corner**, the one closest to the A–H block.
- ANT (30) and VSS (31) end up on the top side, **towards the antenna**.
- 8/9 (P0.06/P0.07), tentative destinations of E1/E2, end up on the bottom side, **towards the external connector**.
- 13 (VDD) ends up at the bottom end of the right side, in the bottom-right corner, next to 12.

Changes: sheet 3 rotates the 48 pins and redraws the routes. A and B enter 25/26 from above without crossing. E→21 and G→24 cross once, because the order of the pads and of the pins is reversed; it is a guide line, not a trace. Sheets 1 and 2 mark the dot at the bottom left and the triangle in grey as «not seen». `pin-candidates.json` includes `pin1_corner`, `qfn48_orientation`, `triangle_mark` and `nfc`.

Next step: cold continuity A↔25, B↔26, E↔21, G↔24, E1↔8 and E2↔9 with this numbering. If it fails, first check the count from the dot before assuming a different assignment.

## 10. r08: E1/E2 continuity measured by the owner

First physical measurement of the series. Owner report: **E1 ↔ pin 16** and **E2 ↔ pin 15**, counting from the pin 1 dot at the bottom left (§9).

| Contact | Pin | nRF52832 QFN48 signal | UWB prediction (r06) |
| --- | --- | --- | --- |
| E1 (GPIO1 / TX?) | 16 | P0.13 | 8 · P0.06 |
| E2 (GPIO0 / RX?) | 15 | P0.12 | 9 · P0.07 |

Not recorded: multimeter, range, reading (beep or ohms) and whether there is a series resistor.

Consequences:

- **The UWB trace does not carry over to the F3.3.** The connectors have the same shape and E3/E4 match, but the data lines go to other GPIOs. This reinforces caution with A–H: the UWB assignment is a candidate, not a proven standard.
- P0.12 and P0.13 are normal GPIOs with no fixed function. They are usable for software UART or UARTE (configurable pins on the nRF52), or for a serial bootloader, **not for SWD**.
- The measurement depends on counting from the pin 1 dot. 15 and 16 are on the right side, 3rd and 4th from the bottom. Counting from another corner would change the assignment, not the continuity.
- Whether there is an active UART on those pins with the original firmware remains undemonstrated.

On the master, E1/E2 become solid lines (reported continuity); the rest remain dashed (hypothesis).

## 11. r09: C confirmed as VDD

Owner report: **C is VDD** and the unit is powered with **3.3 V on C and GND on F**. This is within the nRF52832 range (1.7–3.6 V).

Not recorded: confirmation method (continuity with 13/36/48 or other), voltage on C with the original power, current drawn, power supply current limit and whether the batteries were removed.

Precautions when powering via C:
- No batteries and nothing on H or E3, so as not to back-feed the regulator towards the battery.
- Power supply with current limit.
- For SWD, the probe's VTref to C and common ground on F. A single power supply.

## 12. r10: A and B continuity

Owner report: **A ↔ 25 (SWDCLK)** and **B ↔ 26 (SWDIO)** with continuity, counting from pin 1 at the bottom left. This confirms the r05 correction (A/B are not swapped). C was also validated by continuity (r09).

With A, B, C (VDD) and F (GND, to be confirmed by continuity to E4/VSS), the minimum for an SWD probe is now available: SWDCLK, SWDIO, VTref and GND. G (nRESET, 24) is optional for SWD on the nRF52, which can connect under reset via software.

Pending: reading and range; continuity E↔21, G↔24 and F↔E4; first SWD connection (read `APPROTECT`/identification before erasing).
