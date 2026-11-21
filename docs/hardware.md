# Hardware identification

**There is a partial pinout reported by the owner:** F=negative/GND, H=positive/battery; E4=GND and E3=external 5 V input. E2/GPIO0-RX and E1/GPIO1-TX are provisional. Tests up to 6.6 V and 100 % over BLE are reported; internal VDD still has to be measured and SWD located; there is no complete validated pinout.

## Three different things

| Interface | Function | Condition |
| --- | --- | --- |
| External GPIO/UART | Inputs/outputs or messages to the original firmware | Mode configured and compatible protocol |
| SWD | Programming and debugging of the candidate ARM MCU | Signals identified, correct voltage and access available |
| BLE | Radio advertisements and, separately, connection services | Receiving advertisements is not equivalent to write authorization |

Case [S1](research.md) describes a four-contact connector with GND, Vcc IN, GPIO0 and GPIO1. Only in UART mode does GPIO0 become RX and GPIO1 TX. On the oriented map, the owner fixes E4=GND, E3=5 V, E2=GPIO0/RX (to be confirmed) and E1=GPIO1/TX (to be confirmed). See the [unit sheet](unit.md).

F and H are identified by the owner as negative/GND and positive/battery, respectively (correction after r03). H has not been identified as the MCU VDD nor as the 5 V input. The other six contacts could include manufacturing or debug signals; do not label them as SWD because of their number.

## Before powering or soldering

1. Photograph both sides and references without sanding or removing components.
2. Disconnect every power source to measure continuity. Identify GND through several points and visible connections.
3. Read the MCU marking and confirm the package against its datasheet.
4. Follow traces from the pads to the MCU, using continuity where accessible. Document the orientation and evidence for each assignment.
5. Separate the regulated input, battery terminals and MCU VDD. Do not assume they accept the same voltage.
6. With known original power, measure voltages relative to GND without bridging adjacent pads. If there is no known and safe power, stop that test until the circuit is identified.

Primary batteries are not rechargeable. Do not connect an external power supply in parallel with them without knowing the board's topology and isolation.

## nRF52832 identified by the reported marking

Its specification states a VDD of 1.7–3.6 V; **5 V is not a valid voltage for VDD**. Also respect the input limits of each signal. SWD uses SWDIO and SWDCLK; a practical setup also needs GND and the target's voltage reference. Reset may be needed depending on the tool. [S8–S9](research.md).

Conceptual diagram, without pad numbering:

```text
SWD probe              Identified board
GND           -------- confirmed GND
VTref/sense   -------- measured VDD (per the probe manual)
SWDIO         -------- confirmed SWDIO
SWCLK         -------- confirmed SWDCLK
RESET         -------- Reset, if identified and needed
```

VTref does not imply that the probe powers the target. Check the manual of the chosen probe and use a single documented power strategy.

A conventional Arduino Uno is not on its own an SWD probe for this chip; Arduino ISP is not the SWD protocol either. Do not connect its 5 V outputs to signals of the reported nRF52. Emulating a probe with additional hardware and firmware would be another, unvalidated project.

## Required material by stage

- BLE diagnosis: phone or BLE receiver and verified original power.
- Electrical identification: multimeter, magnification/camera, fine probes; regulated power supply with current limiting only after identifying the input.
- SWD: probe compatible with the MCU and its levels, short wiring or pogo pins, software that supports the target. A compatible J-Link probe or the debug-out of a Nordic DK are options to evaluate according to their manuals; no purchase has been selected yet for this board.

When preparing custom firmware, also identify the clock, sensors, buses, power enables and any RF amplifier/switch. That the core boots does not guarantee that the radio or the sensors work with a generic board definition.

## Continuity targets with the QFAAB0 marking

The owner's transcription corresponds to nRF52832-QFAA, QFN48, revision 1; a macro photo is still needed to corroborate it. Use Nordic's **top view** diagram, first locate the package's pin 1 mark and follow its numbering. Do not orient the chip by the board's text nor by the photo of another device. On our unit, the owner sees the pin 1 dot at the bottom left with the antenna up (r07).

| Signal to look for | QFN48 package pin |
| --- | --- |
| SWDCLK | 25 |
| SWDIO | 26 |
| P0.21 / configurable nRESET | 24 |
| VDD | 13, 36, 48 |
| VSS | 31, 45 and bottom pad |

Source: [Nordic, nRF52832 pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html). **These are chip pin numbers, not numbers of the eight Estimote pads.** Look for continuity with the board unpowered, without bridging pins; if they are not accessible, follow traces or test points under magnification. There is no need to desolder the MCU for this initial research.

The original firmware's UART configuration does not by itself enable or disable SWD access: they are different interfaces. SWD may have its own access protection. Identifying both debug contacts would allow investigating programming without depending on the external RX/TX, subject to the protection state and a possible erase.

Documentation update from this session: [full candidates and QFN48 visual guide](pin-candidates.md). A→25/SWDCLK, B→26/SWDIO (corrected in r05), E→21/SWO and G→24/nRESET are proposals derived from a UWB I1.2; **pending verification** by continuity on the F3.3. C possibly VDD and D unresolved. The consolidated master distinguishes continuity targets from connections already measured.

## Hypothesis of power from four CR2477

The owner reports four CR2477 and proposes two parallel branches of two cells in series (2S2P). Since each cell is nominally 3 V, that arrangement would be **6 V nominal**, without adding voltage between parallel branches. The [unit sheet](unit.md) gathers sources and limits: the F3.3 regulatory annex tests at a nominal 6 V, but no schematic is available that unambiguously links that power to pad H. The owner reports tests up to 6.6 V with 100 % over BLE; 6.573 V/100 % was captured and, after reconnection, 5.982 V with no percentage available. These are firmware readings, not an independent H–F measurement. Neither a maximum rating nor an equivalence with the MCU VDD has been established.
