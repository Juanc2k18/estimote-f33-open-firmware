# Visual comparison with the DIY Stuff UWB teardown

Date: 2026, America/Lima. Documentary inspection from Chrome; no equipment was connected and no electrical measurements were made.

## Goal and sources

Assess whether the block of eight pads in [Marco van Nieuwenhoven's teardown](https://diystuff.nl/embedded/estimote-uwb-location-beacon-teardown/) can guide the identification of the pads on our F3.3. The carousel was paused and its drawings were opened individually:

- [Top with traces](https://diystuff.nl/wp-content/uploads/2018/02/1Top.png).
- [First inner layer](https://diystuff.nl/wp-content/uploads/2018/02/2Inner.png).
- [Second inner layer](https://diystuff.nl/wp-content/uploads/2018/02/3Inner.png).
- [Bottom](https://diystuff.nl/wp-content/uploads/2018/02/4Bot.png).
- [Placement and numbered components](https://diystuff.nl/wp-content/uploads/2018/02/0TopComponentsText_TP.png).
- [Author's nRF schematic](https://diystuff.nl/wp-content/uploads/2018/02/nRF.png).

## Observations and interpretation

The article identifies its hardware as **UWB I1.2**, with nRF52832, DW1000 and three CR123A. Our unit is recorded as **F3.3**, with four CR2477 reported by the owner. They are not the same revision/model; sharing a manufacturer does not prove identical nets or voltages.

The carousel includes renderings of different copper layers of the same board, in addition to the photo with components. Opening them separately avoids mistaking a transition/overlay for a connection between layers. Lines crossing in projection do not prove an electrical connection: the vias and their destinations must be followed.

To compare the block of eight pads with our letters, rotate the article's image **90 degrees clockwise**, keeping the same side and without mirroring it. In the article's ORIGINAL orientation, the proposed geometric correspondence is:

```text
Fila superior: B  D  F  H
Fila inferior: A  C  E  G
```

(Top row: B D F H; bottom row: A C E G.)

In `1Top.png`, the third pad of the top row (equivalent F) visually belongs to the grey-blue plane, consistent with ground when compared with the ground areas of other components. The fourth (equivalent H) appears brown and is linked by a via to the brown power net of the layers. This **is consistent with F−/H+ from r04**, but it remains an inference from the author's drawing, not measured continuity on our unit.

The first inspection did not assign the other six functions. The extended tracing, documented below, made it possible to propose four signal links; C/D were not resolved with certainty. The nRF schematic alone does not provide an A–H table for our F3.3.

## Conclusion and next check

It is plausible that both revisions share a factory test interface, and the geometric match of ground/power strengthens that hypothesis. It does not prove that all eight contacts are identical.

To test it, with batteries and power supply disconnected: first check ground and power against identified nodes on our board; then look for continuity from the remaining pads to the MCU's SWDCLK/SWDIO pins and other destinations. Distinguish UWB reference, F3.3 candidate and measurement on our unit. Later, at the owner's request, the [single consolidated master and QFN48 guide](../pin-candidates.md) was created; it replaced the earlier native files and shows all assignments as provisional where applicable.

## Route tracing: candidates to check

Later extended inspection of the originals `1Top.png`, `2Inner.png` and `4Bot.png`, comparing vias at the same coordinates. Package numbering checked against [Nordic, QFN48](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html). The following are documentary inferences, not measurements on the F3.3:

| Pad on our map | Proposed route in the UWB drawing | QFN48 pin / status |
| --- | --- | --- |
| A | SWDCLK | 25; direct top trace (corrected in [r05](pin-verification-r05-2026-11-18.md); 26 had been recorded) |
| B | SWDIO | 26; direct top trace (corrected in r05; 25 had been recorded) |
| C | Via joined to the bottom VDD plane (r05) | Candidate regulated VDD; no individual pin verified |
| D | Inner route towards the RTC/power area | Functional destination unresolved; no nRF pin assigned |
| E | P0.18 / TRACEDATA[0] / SWO | 21; via under the pad, short link on the first inner layer and return to a via of the top trace of the fourth pin on that side |
| F | GND | VSS net; nRF pins 31, 45 and exposed pad as continuity targets |
| G | P0.21 / configurable nRESET | 24; top trace running around the vias under the block |
| H | Battery power | Not identified with the nRF's direct VDD |

The alternative SWO/reset function of a pin does not prove that the firmware enabled it. C and D need more evidence; do not fill in their names by resemblance to another debug connector. The QFN48 package keeps its numbering across units if the same nRF52832-QFAA is confirmed, but the PCB may connect the pads differently.

## Recent owner reports

The owner clarifies in this chat that they have an adjustable power supply and have been using it for the tests with correct operation. They report 3 V in total on the batteries and currently no BLE detection with them; there is no per-cell voltage, voltage drop under load or measurement of the boot threshold. This is not presented as a new test run by the agent.


## Sensor baseline after r24 · 2026

At the owner's request, the UWB I1.2 teardown is used as a **list of candidate
components**, without carrying its GPIOs over to the F3.3. Based on the
article and manufacturer datasheets; no new access to the hardware.

| Function | Evidence in the UWB article | Use on our F3.3 |
| --- | --- | --- |
| Acceleration | Component 77 identified by the author as LIS2DH12 | Priority candidate, marking/ID/continuity not yet confirmed on our unit. |
| Pressure | Component 84: the text proposes BMP280 based on the matching pinout; the table keeps TBD | BMP280 as a hypothesis to check against the metal package, not a firm identification even in the article. |
| Light | Component 03, model TBD | No model that would allow choosing an address or driver; do not assume a digital interface. |
| Temperature | The author does not locate a dedicated component | Do not assume a fourth chip: LIS2DH12 includes temperature and BMP280 measures temperature; the source of the original telemetry remains undetermined. |

Primary references:
- [Author's teardown](https://diystuff.nl/embedded/estimote-uwb-location-beacon-teardown/).
- [ST LIS2DH12, DocID025056 Rev 6](https://www.st.com/resource/en/datasheet/lis2dh12.pdf):
  I²C/SPI, 2×2 mm LGA-12; 7-bit I²C addresses 0x18/0x19,
  WHO_AM_I at 0x0F=0x33. The ID alone does not distinguish all compatible
  parts in the family; also check marking/package. CS high enables I²C,
  CS low selects SPI. Do not confuse the bytes 0x30/0x31/0x32/0x33 in the
  transaction table with the 7-bit addresses.
- [Bosch BMP280, BST-BMP280-DS001-26](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf):
  I²C/SPI, metal 8-contact LGA, 2×2.5 mm; basis for comparing the
  package and determining power/CSB/SCK/SDI/SDO before testing the chip.

The M24M01 EEPROM and the M41T62 RTC from the article are further candidates when
looking for a possible shared bus, but they are not confirmed on the F3.3 either. The
article's FEM is SKY66112-11; the marking proposed for our board is SKY66110-11
(r22), an additional difference that prevents copying its control scheme.

**Practical consequence:** prioritize LIS2DH12 and BMP280 when comparing package markings and
measuring continuity of their bus and select contacts. Once the bus has been validated
electrically, test selective, reproducible W (write) addresses before reading the ID. The
previous sweeps already included the SPI commands 0x8F (read of 0x0F) and 0xD0;
knowing these candidates does not by itself solve the electrical problem or the lack
of CS/SCK. r24 did not find a valid bus on 6/7 in ZZ/HZ/ZH, with/without internal
pulls: repeating ID reads there without changing that condition is not warranted.

No new SWD tests were run, power was not modified and firmware/UICR were not
changed in this documentary review.
