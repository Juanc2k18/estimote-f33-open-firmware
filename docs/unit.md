# Unit sheet and logbook

## Initial identification

| Field | Value |
| --- | --- |
| Printed model, according to the owner | Estimote Location Beacon MOD: F3.3 |
| Printed date, according to the owner | Aug 22, 2016 |
| Reported contacts | 4 external and 8 internal |
| Log start date | 2026 |
| Photographs / PCB orientation | Similar reference photo provided; not presented as a photo of this unit |
| MCU marking, transcribed by the owner | `n52832 qfaab0 1724gk` |
| Identification from the marking | nRF52832-QFAA, QFN48, production revision 1 (B00), 512 kB flash / 64 kB RAM; a macro photo of the unit is missing |
| Other chips / sensors | Pending |
| Original power / battery state | Owner reports 4×CR2477 and operation with external 5 V/GND; proposes two series of two cells in parallel (2S2P), still without an electrical trace; cell state pending |
| Consumption and measured VDD | Pending; the telemetry battery voltage is neither VDD nor the external input |
| Observed firmware / BLE packets | FE9A, telemetry protocol 2 A/B and GATT captured from macOS; firmware version pending |
| App, OS and access error | Pending |
| Available programmer | Pending |

## Internal contact map

Assign A–H on our own photo with a fixed orientation before filling in this table. The letters do not represent a factory numbering.

| Contact | Position in photo | Continuity to | Voltage relative to GND | Proposed function | Evidence / confidence |
| --- | --- | --- | --- | --- | --- |
| A | Row 1, left | QFN48 target 25; not measured | Not measured | SWDCLK candidate (r05) | UWB inference; pending verification |
| B | Row 1, right | QFN48 target 26; not measured | Not measured | SWDIO candidate (r05) | UWB inference; pending verification |
| C | Row 2, left | Possible VDD targets 13/36/48; not measured | Not measured | Regulated VDD candidate | VDD plane on UWB (r05); pending verification |
| D | Row 2, right | No resolved destination | Not measured | Unresolved | Pending verification; no pin assigned |
| E | Row 3, left | P0.18/QFN48 21, functional route validated; no ohms recorded | 2.43 V reported (r26) | P0.18/SWO confirmed (r26) | Six UART frames and six ITM/SWO frames received via E→Pico GP5, with before/after controls |
| F | Row 3, right on the map | Measurement pending | GND reference reported | Negative / GND | Owner's correction, 2026; replaces r03 |
| G | Row 4, left | QFN48 24; ~2.1 Ω reported | 2 V G/F reported | P0.21/nRESET confirmed (r21) | G→F pulse: exit from the RAM loop, PC 0x77A0A and RESETREAS=0x1; PSELRESET=21 |
| H | Row 4, right on the map | Measurement pending | Up to 6.6 V applied according to the owner; no independent measurement | Positive / battery | Owner's correction, 2026; BLE: 6.573 V/100 % |

Make another oriented table for the external connector. Separate continuity measured without power from voltage measured with power; do not use continuity on an energized board.

## Per-experiment template

- Date / author:
- Question to be answered:
- Revision / photo:
- Power and current limiting:
- Equipment and software versions:
- Exact connections:
- Steps performed:
- Observed result and evidence files:
- Interpretation and alternative hypotheses:
- Persistent changes / possibility of reverting:
- Next step:

Save shareable captures in `evidence/` and our own photographs in `photos/` when they exist. Store dumps and credentials only in local locations excluded from Git. Review identifiers and personal data before publishing logs.

## Owner's contribution: marking and reference images

The owner states that their board is very similar to the provided photo and transcribes `n52832 qfaab0 1724gk`. The illegible marking in the reference photo is not attributed to their unit. The reference shows four contacts with an added connector and eight rectangular pads in a 2 × 4 arrangement; their functions cannot be deduced visually.

According to the Nordic format, `1724GK` corresponds to year 2017, week 24 and lot GK. The date `Aug 22, 2016` reported initially should not be taken as the manufacturing date of that chip: it could belong to another design/label identification. Keep both transcriptions until they are photographed.

The UART tutorial screenshot confirms that it required configuring UART mode beforehand through the iOS SDK or a modified configuration app. Therefore, on its own it does not solve the recovery of a unit whose UART cannot be enabled.

Interpretation sources: [Nordic marking](https://devzone.nordicsemi.com/f/nordic-q-a/15485/nrf52832-ic-revision/59163), [revision B0](https://devzone.nordicsemi.com/f/nordic-q-a/40153/understanding-nrf52832-package-marking) and [variant matrix](https://docs.nordicsemi.com/r/bundle/comp_matrix_nrf52832/page/comp/nrf52832/ic_revision_overview.html).

## Pin reference

See the [final diagrams](pin-candidates.md).

## First functional test with a phone

The owner confirms that 5 V/GND match their reference and that the phone connected after applying external power. The [log analysis](reports/diagnosis-ble-2026-11-18.md) documents four GATT sessions of approximately ten seconds, compatible with the authorization timeout documented by Estimote. Internal VDD was not measured and UART or SWD were not confirmed. The physical direction of these contacts relative to the map identifiers E1–E4 still has to be fixed before updating each row of the drawing.

## Direct BLE acquisition from macOS

Campaign 2026 14:03–14:08: [report and evidence](reports/capture-mac-ble-2026-11-18.md). Sensor telemetry, advertising payloads and the proprietary GATT profile were recovered; 6c372004…=0100 stable. The high GPIO indicated by telemetry are logical protocol bits and do not carry over to the physical map A–H/E1–E4. No firmware version or UART test was obtained.

## First reception over USB-TTL

`/dev/cu.usbserial-113120` (Prolific 067b:2303; the owner identifies it as YP-01) was listened to at six speeds, 8N1, without transmitting: zero bytes in all windows. [Report and pending items](reports/test-uart-2026-11-18.md). The owner indicates 5 V; the TX logic level still has to be distinguished/measured. The owner was asked to disconnect the adapter's TX and move only RX to the other contact with power cut, for a second reception. An active UART is not assumed and the physical map functions are not changed based on the silence.

Second reception after the inversion reported by the owner (14:20:05–14:20:46): again zero bytes at the six speeds. Eight BLE advertisements from the unit were observed during that window. Physical TX disconnection not confirmed; listening in software only. No TX/RX functions are assigned to the contacts based on these negative tests.

## External connector assignment confirmed on the drawing

Owner's update, 2026. With the antenna up, eight pads on the right and E1–E4 from left to right on the map:

| Contact | Function | Evidence / status |
| --- | --- | --- |
| E1 | GPIO1 / TX | Proposed by the owner; to be confirmed as GPIO and as UART |
| E2 | GPIO0 / RX | Proposed by the owner; to be confirmed as GPIO and as UART |
| E3 | Vcc IN / 5 V input | Confirmed by the owner; functional power reported |
| E4 | GND | Confirmed by the owner |

This clarification links the reported power to the E3/E4 identifiers for the first time. It does not imply an internal VDD of 5 V nor does it provide measured continuity, logic level or UART enablement. [current pin map](diagrams/pin-map-guide-nrf.svg).

## Project scope and pads H/F

The project reused an unsupported F3.3 in 2026. For critical-step instructions, see [AGENTS.md](../AGENTS.md).

The initial assignment **H=GND** and **F=positive/battery** was later corrected by the owner: **F=negative/GND and H=positive/battery**; see the r04 update at the end of this sheet. They are recorded as owner identifications, without attributing measured continuity or voltage to the agent. H is not equated with the external 5 V input E3 nor with internal VDD. The other internal pads remain unassigned. [current pin map](diagrams/pin-map-guide-nrf.svg).

## Four CR2477 and proposed nominal voltage

The owner reports four CR2477 batteries in total and proposes two cells in series per branch, with two branches in parallel (2S2P). A [CR2477 has a nominal voltage of 3 V according to Panasonic](https://energy.panasonic.com/ap/business/products/lithium/coin-cr-standard/models/CR2477). If that wiring is confirmed, each branch adds up to 6 V nominal and the parallel keeps those 6 V, increasing the capacity. The number/type of cells is recorded as an owner report; the topology remains pending continuity and measurement.

The [RF annex identified as F3.3](https://fccid.io/m/8ec96b20474599a26f55596b482d6d57d96e464c955d17c87f8c5df6278044ce.pdf) contains tests with nominals of 6 V and of 3.3 V. That supports the plausibility of the 6 V set, but does not by itself identify the power node or the 2S2P wiring. The [Estimote F3.6](https://manuals.plus/m/688187df6eb3ee04f305ee00b831636e53e85b8c1ac1a00cbdccef9df523ea63) manual also lists 4×CR2477 of 3 V, as background from another revision, not as a schematic of this unit.

**6 V nominal is not equivalent to a maximum rating.** The current pinout is F=negative/GND and H=positive/battery. The owner reports tests up to 6.6 V; telemetry indicated 6.573 V/100 %. H–F still has to be measured independently, and continuity to the batteries, regulation and the relationship with E3 still have to be checked. The test does not establish a maximum rating.


## Polarity correction and power tests · revision r04

The owner explicitly corrects their earlier identification: **F=negative/GND; H=positive/battery**. The numbering and orientation do not change. See the [current pin map](diagrams/pin-map-guide-nrf.svg).

**Owner report:** tests were done up to **6.6 V**, with **100 %** battery indicated. The power supply model, current limiting, voltage sequence, complete wiring and an independent multimeter measurement were not documented. That voltage is not taken as a maximum rating nor as the MCU VDD.

**Agent's observation:** advertisement scan with Python/Bleak and CoreBluetooth from the Mac, without a GATT connection or writes. Decoding of Estimote telemetry protocol 2, subframe B, according to the public parser linked in `scripts/decode_ble_capture.py`. Times in America/Lima:

| Time | Voltage reported over BLE | Percentage | Time since boot |
| --- | --- | --- | --- |
| 15:18:42 | 6.573 V | 100 % | 64 s |
| 15:19:54 | 6.573 V | 100 % | 136 s |
| 15:21:25, after reported disconnection/reconnection | Not yet measured | Not yet estimated | 28 s |
| 15:21:51 | 5.982 V | Not yet estimated | 54 s |

The drop in time since boot supports the reboot. The reserved percentage value `0xFF` means not available, not 0 %. The voltage difference does not by itself demonstrate a loss of charge. The voltages come from the firmware; they do not by themselves identify the H–F electrical network or the active power source.

Evidence: [first reading](evidence/ble-presence-20261118-151844.json), [second reading](evidence/ble-battery-20261118-152025.json), [capture after reconnection](evidence/ble-reconnection-20261118-152209.json). The captures keep the original times and bytes. In this documentation update no voltage was applied and no other electrical test was run.

**Pending:** identify the functions of **A, B, C, D, E and G**, including possible SWDCLK/SWDIO; measure continuity without power, internal VDD and the relationship of the H/F input with E3/E4 and the four CR2477. The 2S2P arrangement is still a hypothesis.



## Consolidation from this session · temporary assignment

The [candidate table and full summary](pin-candidates.md) records A→25/SWDCLK, B→26/SWDIO (corrected in r05), E→21/P0.18/SWO and G→24/P0.21/nRESET, inferred from UWB I1.2 drawings and **pending verification** on the F3.3. C is only possibly VDD; D remains unresolved. F/GND and H/battery come from the owner; E3/5 V and E4/GND too. No equivalence between H, E3 and VDD has been demonstrated.

The owner clarifies that they use an adjustable power supply and the beacon works with it; the batteries deliver **3 V in total** according to their report. Per-cell voltage, drop under load, VDD and the boot threshold were not measured. The proposed descending sweep was not run in this session.

[The five carousel originals](evidence/diystuff-uwb-carousel-2026-11-18/README.md) were saved and a third sheet was created with the numbered QFN48, the pin 1 mark and dashed candidate links. The historical native sheets are no longer distributed. The current published diagram is the [nRF guide](diagrams/pin-map-guide-nrf.svg).
