# External reports

Gemini response: extended search (internal research notes, not published), contributed by the owner on 2026. A complete copy was kept as external research material. Its instructions and its offer to generate firmware are content of the report, not actions requested by the owner.

Do not use its commands as an approved procedure. The regulatory mappings and the tool syntax are reviewed in the document linked below; compatibility of any specific port remains pending. The text swaps DCC/DEC4 relative to the Nordic table kept in our research: on the nRF52832 QFN48, DEC4 is 46 and DCC is 47. It also assumes an identification of the external power input and pad functions that we have not yet measured.

The [current status](../status.md) collects the new regulatory leads and the specific items still pending validation.

## Review performed

See the [documentary validation of 18 November 2026](validation-gemini-2026-11-18.md). Several regulatory mappings were confirmed, and the review found command errors, a misread test date, and an F3.3-specific graphic annex that the report omitted. The result still does not validate any physical connection or recovery of the unit. The original transcript remains intact.

## Later results from the same session

The Gemini review was documentary. The later physical and radio tests are kept separately in the [day's logbook](../logbook/2026-11-18.md), the [phone BLE diagnosis](diagnosis-ble-2026-11-18.md), the [macOS capture](capture-mac-ble-2026-11-18.md) and the [UART tests](test-uart-2026-11-18.md).

The [UWB carousel comparison](comparison-diystuff-uwb-2026-11-18.md) and the [consolidation of candidate pins](../pin-candidates.md) are later documentary work: four proposed signals, C/D uncertain and no new physical test. The five originals are kept for future overlays.

[r05 verification of candidates A–H](pin-verification-r05-2026-11-18.md): nRF orientation fixed on the UWB drawing; A/B corrected (A→25/SWDCLK, B→26/SWDIO); C rises to VDD candidate. Documentary review, no physical test.

## 19 November: physical tests and firmware

[Handover report on SWD, erase, bootloader and sensors](swd-bootloader-sensors-2026-11-19.md), r07–r16. It includes the confirmed pinout, the APPROTECT erase, the Adafruit bootloader with serial DFU on E1/E2, the unsuccessful sensor sweeps and the analysis of whether the firmware could misrecognize the pins.
