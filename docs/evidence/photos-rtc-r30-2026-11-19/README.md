# r30 · Macro photographs and numbered RTC

> **Publication (2026):** to slim down the repository only the detail
> crops are kept. The original HEIC files and the full PNGs were removed;
> their hashes remain in `SHA256SUMS` and `manifest.json` as a record.


The owner's six photographs IMG_0576–0581 were reviewed. The original
HEIC files were kept byte for byte; `manifest.json` records provenance and SHA-256.
The reference PNGs only convert format/orientation; the crops have no
generative reconstruction. `rtc-reading.png` comes from IMG_0579 and is rotated 180° to
read the text. The coordinates of its contacts are stored in the pin JSON.

They provide a clearer view of the eight contacts, solder joints and vias near
the already identified M41T62 RTC. They do not show a complete SDA/SCL route to the
nRF nor allow another model to be assigned to the black chips with certainty. There are
no new GPIO assignments nor demonstration of a shared bus from these images.

## Drawing numbering

Top view, M41T62 text upright and the dot used by the owner at the bottom
left; not mirrored. Bottom, left to right: 1 SDA, 2 SQW, 3 VSS/GND,
4 NC. Top, left to right: 8 SCL, 7 NC, 6 IRQ/OUT, 5 VCC.
The orientation is documentary and must be checked by 3→F continuity;
the visible circular mark does not replace that validation. The earlier report
6→nRF physical pin 22/P0.19 is kept as a report without recorded ohms;
it is not an identification of SDA/SCL nor an alarm test. VCC not measured.

Source: ST M41T62 datasheet, DocID10397 Rev16, figure 4/page 8 (LCC8 connections).
Mechanical figure 29/page 38 shows the pads from BELOW and must not be copied
as a top view. ST PDF archived from the mirror
https://www.100y.com.tw/pdf_file/34-ST-M41T62-65.pdf ; official source:
https://www.st.com/resource/en/datasheet/m41t62.pdf .
The ST PDF, its text and the rendered pages were removed from publication
(2026) because of ST's copyright; consult the datasheet at the official link.
The hashes remain in `SHA256SUMS` as a record.

## Diagrams

See the [final pin reference](../../pin-candidates.md) for the editable master and three English diagram sheets. No physical tests were performed for this documentation update.
