# Research and background

Consulted: **2026**. “Documented” means that a public source describes it; “verified on our unit” requires a local test. For now there are no local tests.

## Cases and primary sources

| ID | Source | What it provides | What it does not demonstrate |
| --- | --- | --- | --- |
| S1 | [Michał Łusiak: Broadcasting custom packages on Estimote Location Beacons with Raspberry Pi, 2017](https://mlusiak.com/estimoge-uart-raspberry-pi/) | Direct experience: UART configured via iOS and custom BLE messages from a Raspberry Pi; identifies GPIO0 as RX and GPIO1 as TX | Custom firmware, current success or an unambiguous F3.3 revision |
| S2 | [Marco van Nieuwenhoven: Estimote UWB Location Beacon Teardown, 2018](https://diystuff.nl/embedded/estimote-uwb-location-beacon-teardown/) | Reverse engineering of a UWB board, components and connections; intention to create open firmware | A finished and reproducible port for the 2016 F3.3 |
| S3 | [Estimote: Telemetry](https://d3lgd0yxjqbzck.cloudfront.net/sensors/estimote-telemetry/) | Packets with sensors and status; mentions pressure on F3.x and I and differences between versions | That our unit is emitting them |
| S4 | [Estimote: estimote-specs](https://github.com/estimote/estimote-specs) | Public Nearable and Telemetry parsers in JavaScript; repository archived on 2025-07-28 | That its old dependencies work today without adaptation |
| S5 | [Estimote: iOS Fleet Management SDK](https://github.com/Estimote/iOS-Fleet-Management-SDK) | Configuration, access modes and examples; F family identified as Location Beacon | That the cloud service or the app are usable with this account/unit |
| S6 | [Estimote: Connecting to Beacons](https://d3lgd0yxjqbzck.cloudfront.net/managing-beacons/connecting-to-beacons/) | Distinguishes BLE advertisements and authenticated connection; explains the dependency on authorization | That a generic BLE scanner can unlock GPIO |
| S7 | [Estimote: Mesh networking](https://d3lgd0yxjqbzck.cloudfront.net/managing-beacons/mesh/) | Identifies F3.3 as Long Range Location Beacon, with mesh from firmware 4.10.0 | Presence of a UWB radio or compatibility with any mesh stack |
| S8 | [Nordic: nRF52832 Product Specification v1.9](https://docs-be.nordicsemi.com/bundle/nRF52832_PS_v1.9/raw/resource/enus/nRF52832_PS_v1.9.pdf) | Power, GPIO, SWD, memory and protection of the candidate MCU | That this is the chip of this unit or how its pads are distributed |
| S9 | [Nordic: Debug and trace](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/dif.html) | Describes APPROTECT and erasing via CTRL-AP; differences by revision | That access is open or that we can save the protected firmware |
| S10 | [Nordic: nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile) | Tool for exploring BLE advertisements, RSSI and services | Authorization to modify the proprietary Estimote configuration |
| S11 | [Estimote: Robotics Indoor SDK](https://d3lgd0yxjqbzck.cloudfront.net/robotics/) | Official UART case with a Raspberry Pi on a UWB variant; stated power of 3.3 V | That its voltage or numbering apply to the F3.3 |
| S12 | [Nordic: S132](https://www.nordicsemi.com/Products/Development-software/s132) | nRF5 SDK and SoftDevice in maintenance; recommends nRF Connect SDK for new projects | A ready-to-build Estimote board support package |

S1 describes a 5 V Vcc IN; S11 uses 3.3 V on a UWB variant. These are different contexts: **do not resolve that difference by applying a voltage by trial and error**. The unit's circuit still has to be identified.

## Bounded conclusions

There is evidence of functional reuse with Estimote firmware and UART, as well as reverse engineering on another variant. **No located evidence is sufficient to state that anyone has turned this specific F3.3 into a development board with a complete recipe.** That does not demonstrate impossibility.

Update: the owner transcribed `n52832 qfaab0 1724gk`, compatible with nRF52832-QFAA revision 1, 512 kB flash / 64 kB RAM according to Nordic; photographic corroboration of the unit is missing. Do not confuse references to old nRF51 beacons or later nRF52840 products with this board.

It was also not verified that the app has disappeared from all platforms or that all Estimote infrastructure is shut down. The access problem reported by the owner should be recorded with platform, error and date.

## Reproducible search and limits

Combinations of `Estimote F3.3 reprogram SWD`, `Estimote SWDIO`, `Estimote custom firmware`, `Estimote openocd`, `Estimote J-Link`, `Estimote 8-pin` and `Estimote Arduino reprogram` were searched, in addition to official documentation and indexed GitHub. Search results are not exhaustive; unindexed code, vanished pages and closed forums may hide other cases.

The S1 site returned a verification barrier when opening one of its routes; the indexed text of its archive was consulted. Its examples were not run and its dependencies were not audited. S2 had intermittent responses; the available description is not enough to state that firmware was delivered.

## How to accept a case as a reproduction of the F3.3

Require photos and an identifiable revision, a pinout with orientation, voltages, a legible MCU, programmer and software/versions, source code and build steps, a programming log and a functional test. An announced purpose, a video without connections or a binary without provenance do not complete that evidence.

## Provided article: Reverse Engineering the Estimote

[Alasdair Allan, Make: Reverse Engineering the Estimote](https://makezine.com/article/technology/computers-mobile/reverse-engineering-the-estimote/) analyzes an earlier Developer Preview Kit, based on the **nRF51822**, and studies advertisements and GATT configuration using Bluetooth tools and an SDK. It is relevant direct research, but it does not demonstrate alternative firmware or a pinout of the F3.3 with nRF52832. Its mechanisms and characteristic addresses should not be carried over to another firmware generation.

New primary sources for the reported unit:

- [Nordic: SoC revisions and variants](https://docs.nordicsemi.com/r/bundle/comp_matrix_nrf52832/page/comp/nrf52832/ic_revision_overview.html): QF/AA/Bx0, QFN48, revision 1 and memory.
- [Nordic: Understanding nRF52832 package marking](https://devzone.nordicsemi.com/f/nordic-q-a/40153/understanding-nrf52832-package-marking): `QFAAB0` represents production B00, revision 1; not Engineering B.
- [Nordic: IC revision and date/lot](https://devzone.nordicsemi.com/f/nordic-q-a/15485/nrf52832-ic-revision/59163): year, week, lot format.
- [Nordic: Pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html): SWD pins of the package; no correspondence with the Estimote pads.

The S1 UART case requires enabling that mode beforehand. It is evidence of a possible use with accessible configuration, **not a demonstrated solution to the configuration lock reported here**.

## Assessment of the two provided UWB links

### Android-Estimote-UWB-SDK

[Official repository](https://github.com/Estimote/Android-Estimote-UWB-SDK). Its README requires Android 14/API 34 and describes BLE discovery and ranging with UWB phones. The application imports `com.estimote:uwb-sdk:1.0.0-rc5` from an external Maven repository. It is phone software; it does not provide a recipe for alternative firmware, an SWD pinout or UART enablement for the F3.3. Compatibility with this unit has not been tested or established.

The absence of authentication mentioned by the README refers to the UWB kits described there; it does not demonstrate free access to the original F3.3 firmware. Nor does it demonstrate compatibility with the 2018 UWB hardware of the other link.

### DIY Stuff teardown: manufacturing lead

The board is explicitly identified as **I1.2**, with nRF52832 and a separate **DW1000** UWB radio. Sharing an MCU does not imply sharing a PCB or pinout. In the GPIO section, the author attributes firmware-update capability to the pogo contact pads; this is a manufacturing-interface lead worth investigating. It does not identify the eight F3.3 pads there nor demonstrate a reproducible custom flashing. The nRF–DW1000 connection table is for the bus between chips, not an SWD pinout.

Consequence for our research: prioritize continuity between the unit's pads and SWDCLK/SWDIO of the nRF52832. Do not assume UWB because of having that MCU, nor interpret the word firmware as evidence that RX/TX are enabled.

## Critical review of the external report provided by the owner

The Gemini report was checked against Nordic documentation. Its conclusions are considered leads, not measurements of the board.

### Verified electrical corrections

For the **nRF52832 QFN48**, the correct order is **25 = SWDCLK, 26 = SWDIO**. **P0.21/nRESET is on physical pin 24**, not 21. **The center pad is VSS/GND**, never VDD; VDD is on 13, 36 and 48. The report swaps the SWD signals and confuses GPIO number with physical pin. Do not use its list for wiring. [Nordic source](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html).

### Recovery: chip capability versus board result

Nordic documents that on build codes Fxx and earlier, which include B00, CTRL-AP ERASEALL disables APPROTECT when erasing flash, UICR and RAM. That supports a path for reusing the silicon, but does not prove continuity to the eight pads nor operation of the radio, sensors or power with custom firmware. The firmware can re-enable the protection; do not describe the unlock as permanent and irreversible. [Nordic source, hardware section](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/dif.html).

The [improved APPROTECT article from 2022](https://devzone.nordicsemi.com/nordic/nordic-blog/b/blog/posts/working-with-the-nrf52-series-improved-approtect) mainly covers new revisions, including Gxx/revision 3 of the nRF52832; for B00 use the explicit distinction by build code in the specification.

Do not skip the backup attempt if access allows it. Do not erase before identifying the board, pins and voltage and having suitable minimal firmware available. Do not assume that erasing via CTRL-AP removes external EEPROM or FICR factory calibration; distinguish those memories from flash/UICR.

### Claims not yet demonstrated

- That the remaining pads are NFC or specific UART GPIO.
- That mapping them takes less than two minutes or that all have accessible direct continuity.
- That the F3.3 carries exactly the SKY66112-11 or that its range with a generic firmware is centimeters.
- That the crystal and configuration of a DK apply directly to this PCB.
- That there is no public documentation at all: we can only state that a sufficient recipe has not been located.

### Regulatory leads kept

[FCC EST0116](https://fccid.io/2ABP2-EST0116) lists internal photos from 2016 and [FCC EST0117](https://fccid.io/2ABP2-EST0117) lists internal photos from 2017. They are candidates for comparison; equivalence with the unit's revision has not yet been established. The link to the EST0117 internal photos returned HTTP 403 during this review. They are not incorporated as a confirmed pinout.

## Update: extended validation of 2026

The [later review](reports/validation-gemini-2026-11-18.md) resolves the earlier regulatory leads: the EST0116 and EST0117 annexes identify F1.3d and G1.12, respectively. A Japanese annex with assembly drawings identified as F3.3 and the inscription Aug. 22, 2016 was also located. That specific reference improves the physical comparison, but does not identify nets or SWD pads. The review also documents the command errors of the second report; it does not modify the corrections attributed to the first report.
