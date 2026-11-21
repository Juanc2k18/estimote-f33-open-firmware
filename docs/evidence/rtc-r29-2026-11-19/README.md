# r29 · Reported RTC→P0.19 continuity and search for 0x68

2026. **RTC still without a validated I²C response.** New information:
the owner reports M41T62 contact 6 (counterclockwise from its dot) with continuity
to physical pin 22 of the nRF52832, that is **P0.19**. It is not GPIO P0.22.
Ohms, range and instrument not recorded. According to ST LCC8, contact 6 is
**IRQ/OUT**, not SDA/SCL. The function is derived from the pinout and the reported count;
it was not tested by generating an alarm. The continuity alone does not locate the bus.

## Setup and preparation

The owner confirmed the Pico/power supply reconnected and E1/E2 removed. The
usual SWD/GND setup and previous power supply setting on H/F are kept, C without power supply,
G free. Last reported setting: 6 V; no new H/F or C/F measurement. E→Pico GP5
was the last r26 setup; whether it is still in place was not explicitly reconfirmed.
Nothing was transmitted from the Pico and no connection to unknown contacts was added.

The question about the RTC's VCC (pin 5 relative to pin 3) remained **indeterminate**:
the owner could not distinguish 0 V from lack of contact on small pads.
Do not record it as zero nor as confirmed power. Ground on RTC pin 3
is not demonstrated by software either. This is a central limitation of the results.

Tools reused: r25 OD matrix and bus_probe/i2c_candidates. Added
filters `--exclude`, `--anchor`/role and a single state `--power-pin14|15`; the reported
IRQ line 19 was not used as SDA/SCL nor driven high as an enable. Radio
STATE=0 on entering RAM; CPU in a loop with CPSID i, without programming flash/UICR.

## First matrix: incomplete at GPIO11

The inherited r25 revision attempted 29 GPIOs, excluding 0/1/21. It saved 2–10
complete and failed with FAULT ACK when reading GPIO.IN after requesting OD low on 11. The
`finally` also failed when halting the core. **There is no valid reading of 11
nor a normal closure of that batch**; it is not equivalent to a NACK or to absence of a device.
It never got to test 19. Raw data and traceback are preserved in `matrix/`, `matrix.log`.
`pyocd reset -t nrf52832 -f10000` ended with exit 0; subsequent connection recovered.
The repetition excluded 11 (repeated failures) and 19 (reported IRQ), and ended without failure.

Repeated matrix: 27 GPIOs. The 19 that go low and recover high with the internal pull-up:
**2,8,9,10,12,13,16,17,18,20,23,24,25,26,27,28,29,30,31**.
3,4,5,6,7,14,15,22 did not recover high in that condition and were not probed as a
bus. 0/1 reserved for the crystal, 21 for nRESET. This does not universally rule out
any GPIO as a connection; it only limits the current electrical test.

## I²C search targeted at the RTC

All 342 pair orientations among those 19 GPIOs, for each state:

| State 14/15 | Valid orientations | ACK W | NACK W | ACK R | NACK R |
| --- | --- | --- | --- | --- | --- |
| Z/Z |340|0|340|0|340|
| H/Z |340|0|340|0|340|
| Z/H |340|0|340|0|340|

Z=input without pull; H=output high. Never both 14/15 as outputs. The high
state is configured after the negative control and kept across pairs,
initial wait 1 s. CNF14/15=1/0 or 0/1 is verified. No other enable is tested.
Each pair uses internal pull-ups only on SDA/SCL, OUT=0 and DIR for OD.
Prior validation of idle, independent lows and recovery within 50 ms.
9/10 and 10/9 are electrically invalid because of coupling; they are not addressed.
SCL is read high on each pulse, including the ninth, and idle is required after STOP.
W transmits address/W and STOP, with no register/data. R would read one byte only on ACK.

**Total 2,040 NACKs**, with no ACK, stuck clock, busy bus or timeout on the
valid probes. Prior controls SDA2/SCL8: 2 NACKs per run, 6 additional.
There was no candidate to repeat nor reason to read registers/calendar.
A known device for a physical positive control is still missing.

**Scope:** no response at 0x68 with those pairs and three states. It does not demonstrate
a faulty RTC, lack of power, a different address or absence of I²C. VCC not
measured, SDA/SCL not traced, other GPIOs/enables not covered. No
SPI was done and 11/19 were not used as a clock during the search.

## P0.19: input observation and configuration conflict

The generic bootloader's header defines LED_SECONDARY_PIN=19. The earlier
reading confirmed **CNF19=3, DIR19=1**: output with the input buffer disconnected.
Therefore, IN19=0 in that configuration does not measure the physical level. If the
RTC6→P0.19 continuity is correct, its use as an LED needs review; this does not prove there is
an LED connected nor that it is compatible with the RTC's IRQ line.

`rtc_irq_input_r29.py` left P0.19 exclusively as an input during its test:

| Configuration | High samples /64 | DIR19 |
| --- | --- | --- |
| No pull |0|0|
| Pull-up |64|0|
| Pull-down |0|0|
| No pull again |0|0|

The line follows the pulls in this sampling. Consistent with a released IRQ/OUT,
a high-impedance connection or another situation; it does not prove a powered RTC, a functional
alarm, a frequency nor an open connection. Without alarm programming or
flag reading, the interrupt function is not validated. The slow sampling
may miss brief pulses.

At closure the bootloader was restored and CNF19 was replaced **only in RAM**
by 0 (input without pull), read as 0 twice after resuming. **This change is lost
on reset/power-cycle**, because the flashed binary still configures 19 as an LED.
The persistent firmware was not changed and this adjustment is not presented as a repair.

## Closure

Bootloader running: **PC=0x77a06**, P0.19 input without pull. Each
search and the repeated matrix completed reset/hash; the first attempt at 11 was
recovered. Bootloader/UICR hashes equal to those at the start:

- Bootloader: `589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`
- UICR: `82ea7e308fcc09c6dd9dee4d9686e9e261f4848d49d6c540f9b1ea670dbc7ad7`

There were no changes to power supply, flash or UICR. GPIO14/15 released at the end of their
tests. E1/E2 remain removed per report. There is no validated RTC/bus candidate.

## Next concrete measurement

With power supply and USB removed, locate **RTC pin 1/SDA** and **RTC pin 8/SCL** according to
the LCC8 and find their nRF pins; note the ohms. Confirming RTC pin 3↔F helps
validate orientation and reference. For VCC the neighboring capacitor can be used
**only after confirming** which end joins RTC pin 5 and which joins F; then measure
at its ends, without assigning polarity by appearance. This avoids insisting with the
probes on tiny contacts and distinguishes power from bus configuration.

## Files/versions

`owner-report.json`, `matrix*/`, `i2c-68*/probes.jsonl`, `summary.json`,
`irq19/events.json`, logs and `verification.json` store data and closures.
`source/` keeps the sources: the baseline search started before the state
options were added; the later saved revision keeps the same baseline
path with power-pin omitted. The actual parameters of each run are in its
first record. The first matrix attempt used the archived r25 revision;
the repetition uses the revision with exclusion. There are no commits; versions and data
are identified by SHA-256. The ST consultation was on the web; local downloads
failed, according to `references/README.md`. No incomplete PDF is kept.
