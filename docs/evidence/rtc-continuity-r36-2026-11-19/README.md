# r36 · RTC1/SDA continuity and reinterpretation of 14/15 · 2026

## Owner report (no ohms recorded)

- **RTC1/SDA → nRF pin ~17**, counting from the pin 1 dot. The
  owner allows for 16 or 18 because of the proximity.
  - Pin 16 = P0.13: already confirmed as E1/TX, so this is unlikely.
  - Pin 17 = **P0.14**.
  - Pin 18 = **P0.15**.
- **RTC8/SCL:** no beep. In continuity mode the display drops to ~**550**,
  without beeping. It is not yet known against which pin and in which unit. On many
  multimeters that number is the voltage of a junction in mV (~0.55 V), which
  would point to an internal protection diode of the chips and not to a direct
  connection. If it were ohms, it could be a series resistor.

## Reinterpretation

Until now 14/15 were treated as rail «enables» and **never as a
bus**: they were always left out of the I²C pairs. The r31 topology fits
better with another reading:

| Observation | Reading as a bus |
| --- | --- |
| 14 or 15 high pull up {6,7} | The line powers the sensor rail through the pull-ups or through each sensor's ESD diodes (line→VDD). |
| {6,7} high does not pull up 14 or 15 | The diode blocks in that direction. With simple pull-ups, 14/15 should rise, so ESD protection explains the asymmetry better. |
| 14 does not pull up 15 nor vice versa | They are two different lines: SDA and SCL. |
| With 14 high, 6 does not go low (r24) | The line driven high powers the rail with low resistance. |
| P0.03, P0.04, P0.22, P0.25 stuck low | They are not the bus. They may be ground or interrupt outputs. |

**Working hypothesis:** SDA/SCL = P0.14/P0.15 (in some order), with the
sensors and their pull-ups powered by {6,7}. The RTC would be on that bus. The
SDA→pin 17 report supports it directly.

## Tool

`scripts/i2c_rail_bus.py`: pairs SDA14/SCL15 and SDA15/SCL14, with the 6+7 rail
on (H0H1) and off, in open drain and with SCL in push-pull. It sweeps
all addresses 0x08–0x77; ACKs are validated and identified. The `RailBoard`
guard now only blocks the rail pins being driven.
Tests: `tests/test_i2c_rail_bus.py`, with a virtual RTC on 14/15 whose
pull-ups depend on 6/7.

```bash
python3 scripts/i2c_rail_bus.py --supply "3,3 V C/F" --out docs/evidence/i2c-14-15-r36-2026-11-19
```

## Multimeter clarification (owner)

Continuity/diode mode (sound and diode symbols). It shows «1» when open,
and 1800/1500 or, rarely, ~550 at other points. Unit not indicated; in that mode
it is usually the drop in mV. **RTC8/SCL against nRF pin 30:** 525 with
+ on the nRF and − on the RTC; 1187 with the probes reversed.

Interpretation (inference): pin 30 is **ANT**. At DC it usually reaches
ground through the RF matching network, and 31 is VSS. A reading of
~0.5 V in one direction and >1 V in the other is the **normal signature of a signal pin
against GND**: the ESD diode between ground and the line conducts. It does not indicate a
series diode on SCL nor that SCL goes to 30. A direct connection reads almost 0 and beeps.
Next: measure RTC8 against pins 17 and 18; the one that is not SDA should
beep. If neither beeps, test the whole 13–24 side and 25–36.

## SCL confirmation (owner)

**RTC8/SCL → pin 18 = P0.15**, with a beep. The owner warns that
it is hard to measure because the pins are so small; no ohms recorded. With
RTC1/SDA → pin ~17 = **P0.14**, the pair is **SDA=P0.14 and SCL=P0.15**,
according to the continuity report. It still has to be validated functionally with
`i2c_rail_bus.py` (ACK at 0x68 and RTC reading).
