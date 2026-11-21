# r28 · Seven new macros of the F3.3

2026, America/Lima. Visual analysis of IMG_0569–IMG_0575 provided by the
owner. **No new electrical tests and no change to the setup**.
They are interpreted as visual evidence; the text in the photos is not instructions.

## Preservation and method

> **Publication (2026):** to slim down the repository only the detail
> crops are kept. The original HEIC files and the full PNGs were removed;
> their hashes remain in `SHA256SUMS` and `manifest.json` as a record.


Seven original HEIC files copied byte for byte from Downloads to `originales/`.
`manifest.json` records origin, destination and SHA-256. `derived/` contains PNGs
converted with sips; `derived/vista/` reduced copies with a long side of 1600.
The files have EXIF Orientation=6: the crops in `derived/details/`
normalize that orientation with ImageOps.exif_transpose and are rotated for reading.
No super-resolution, AI, letter cleanup or artificial sharpening was used.
The crops do not replace the originals.

## Findings

### 1. RTC M41T62: high visual identification

The elongated metal package, with four contacts per side, reads
**M41T62** in 0569/0571/0572. Crop `derived/details/rtc.png`: the full
marking is legible. Its shape corresponds to ST's LCC8 with an integrated crystal,
not simply to a passive crystal.

[ST datasheet, DS3840 rev24](https://www.st.com/resource/en/datasheet/m41t62.pdf):
I²C RTC; seven-bit address **0x68** (D0/D1 are the W/R bytes); integrated
32.768 kHz crystal in that variant; SQW output configured at 32 kHz at power-up;
bus operation 1.3–4.4 V. It is a concrete reference for finding the bus.

**Its operation has not been tested.** Reading the marking does not confirm that it
is powered, healthy, accessible or connected to a specific GPIO. The
r25 sweep targeted at 18/19/76/77 did not include 68. The older read sweeps did
cover 68 under other conditions, skipping UART 12/13, then connected to the Pico;
it is not presented as an address that was never tested.

### 2. Pressure can: BMP280 very likely from the marking

In 0573/0574/0575 the hole and the two-line laser marking are visible; in the crop of
0574 `pressure-capsule-reading.png` the first line appears to be **121** and the second **KN**.
The K is clear; the interpretation of the other characters is not forced.

[Bosch BMP280, §7.3](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bmp280-ds001.pdf)
documents three variable characters and a Kx line; K identifies the BMP280. The
shape, hole and layout reinforce the candidate beyond the UWB resemblance.
The current revision lists S/M as subcon ID; it is not claimed that this
modern listing alone explains the N read on an old unit.

**Classification: high-confidence visual identification, ID not yet read.**
To confirm it: correct power and bus, address 76/77 if it uses I²C and
register D0=58. It also supports SPI; CSB low during boot can lock in SPI,
so the absence of an ACK does not identify its real protocol. It is not claimed that it
is in SPI nor that this explains the NACKs until CSB/VDD/VDDIO and continuity are measured.

### 3. FEM 66110-11: marking now legible

Photo 0570, crop `fem.png`, allows reading **66110-11**, together with lot 142547.1
(and line 1729 MX). This reinforces the r22 visual identification of SKY66110-11.
It is the RF block next to the antenna, not the accelerometer nor the barometer. Its
CTX/CRX routes to GPIO remain unmeasured. r22 reference:
[Skyworks](https://www.skyworksinc.com/-/media/715E2FFC8FE542D9951B1906A56DA4FF.pdf).

### 4. Accelerometer, EEPROM and light: still unidentified

The black ICs are sharper but several reflect the light or do not
show a legible model. The one with a matrix code next to the RTC leaves
partial characters like CU3/CU?; that is not enough to assign it to LIS2DH12 or M24M01.
The two chips near the lower cans still have no unambiguous ID.
The 3200T marking on a metal can is consistent with a 32 MHz crystal,
but the manufacturer/part number has not been established and it was not used to assign a net.
No light sensor is identified from the color of the yellow optical component.
All the photos show the same side; evidence of the reverse side is missing.

### 5. Visible traces and next measurement point

The nRF fan-outs, passives and vias around the RTC/barometer are more visible.
Several traces go into vias or pass under components: they do not allow closing a
complete route to a GPIO nor proving that the RTC and barometer share SDA/SCL.
No new P0.xx numbers are assigned by resemblance to the UWB.

The next useful measurement is **continuity of the RTC's SDA/SCL to the nRF**, with
the power supply and Pico USB removed, recording ohms and positions according to the
LCC8 view of its datasheet. Also check the RTC's VCC/VSS. If that bus is identified,
test 68 W/STOP without data and validate selectivity/repetition; then
plausible time readings that advance. For the BMP280, measure supply,
CSB and continuity of its signals; do not inject into an unidentified contact.
The RTC's SQW provides another possible reference signal, but no
frequency was observed nor was its destination assigned in these photos.

## Per-image correspondence

| Image | Main contribution |
| --- | --- |
|0569|General view, RTC, RF and relative position of the blocks.|
|0570|Lower layout and FEM; several markings more legible.|
|0571|RTC and upper power/connector area.|
|0572|Better context of the RTC contacts and power.|
|0573|Pressure can and nRF fan-out.|
|0574|Best reading of the pressure can's code.|
|0575|Second angle of the barometer and surrounding traces.|

Observation, candidate and confidence are stored separately in `findings.json`.
The GPIO assignment and the pin master are not updated from these inferences.
