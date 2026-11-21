# Unit photos · r22 · 2026

Historical photo analysis from the owner's ZIP. The former README photograph
and the four source JPEGs are no longer distributed. The current three cropped,
metadata-free photographs are in [board photos](../board-photos-2026/README.md).
The observations below describe the earlier r22 session; use the consolidated
guide for current component assignments.

## Observation and identification

The owner proposes the marking «66110-11». In 20261119_015439.jpg the
20-contact module next to the antenna has a marking consistent with SKY66110-11.
Position, package and marking give a strong visual identification, not an electronic
ID reading. [Manufacturer Skyworks](https://www.skyworksinc.com/-/media/715E2FFC8FE542D9951B1906A56DA4FF.pdf):
2.4 GHz Bluetooth FEM with amplifier and TX/RX switching. It is not a sensor nor an
I2C/SPI peripheral. Pin14=VCC, pin17=CRX, pin19=CTX, pin4=TR, pin11=ANT.
Do not carry this numbering over to the nRF nor assign GPIOs without continuity.

Implication: CTX/CRX must be mapped for a future BLE application with normal
range. Do not assume the generic bootloader drives the FEM. The manufacturer forbids
CTX=CRX=1; do not yet link those controls to GPIO14/15: there is no continuity.
The earlier interpretation «14/15 power the sensors» remains a hypothesis.

Metal can with a hole, below and slightly to the right of the nRF with the
antenna up: **strong candidate for a pressure sensor because of its construction**.
The package resembles MEMS barometers, but that is not enough to identify a BMP280,
LPS or another model. The small black chips around the nRF still have no
legible ID. Do not assign accelerometer/magnetometer/EEPROM by position alone.
The elongated metal package to the right of the nRF is not identified either
as a crystal or a sensor without reading its marking/measuring connections.

The photos allow locating components and some surface traces, but
not demonstrating complete continuity to a GPIO. Several traces end in vias and there are
areas covered by the connector/tape. Keep the pin map already measured.

## Next targeted test

On the pressure candidate, first identify ground and supply on its
neighboring capacitors with a multimeter (do not inject voltage into an unknown pin).
Then, with no power and no Pico USB, measure continuity from its contacts
to nRF pins to obtain the real bus. Document ohms and positions with a
photo before assigning sensor pin names. Accessible vias/pads may
serve as test points once continuity is confirmed.

No connections, power, flash or beacon configuration were changed
during this photo analysis. The last reported setup remains H/F at 6 V,
C without power supply, Pico connected and G free after the reset test.
