# r32 · Rail states 14 / 15 / 6+7 · 2026

Run by the owner of `rail_survey.py` r31b with `--no-lfclk`. Declared
supply: 3.3 V on C/F; H/E3 loose. Status `incomplete`, only because of the two
I²C pairs with `bus_busy` on GPIO17. Valid closure: PC 0x75102, bootloader
and UICR hashes equal, CNF19=0. From RAM; no changes to flash or UICR.

## Wiring reported in this turn: check

Owner: E1→pin 8, E2→pin 7, A→pin 4, B→pin 5, C→3.3 V, F→pin 3.
If these are **Pico physical pins**, pin 8 is **GND**: E1 (beacon TX,
P0.13) is **shorted to ground**. When the bootloader is active, its TX, idle
high, is continuously discharged into GND. Pin 7 (GP5) is a Pico input
and E2 is also an input: there is no communication. Previously validated
setup: **E1→pin 7/GP5 and E2→pin 6/GP4**. A→4/GP2, B→5/GP3 and F→3/GND
are correct. The r32 test does not touch 12/13, so this wiring does not affect
the data, but it does affect the risk to P0.13 while the bootloader runs.

## Results

| State (H0H1) | {6,7} | New pins | Notes |
| --- | --- | --- | --- |
| off | 0/0 | — | Valid: 2, 8, 9, 10, 16, 18, 20, 23, 24, 26–31 |
| 14 only | 1/1 | none | At the end, 15 read 1 (at the start, 0) |
| 15 only | 1/1 | 17 (false) | 30 pairs with 17: invalid or `bus_busy` |
| 6+7 | 1/1 | none | — |

- **3, 4, 5, 22 and 25 do not recover the high level in any state.** P0.03 and P0.04
  read between −5 and +3 mV by SAADC in all four states, consistent with ground or
  with a low-impedance output driven low. **The hypothesis «SDA/SCL on 3/4
  powered by {6,7}» is left without support** under these conditions. P0.05
  stays at ~470 mV (battery divider, with H loose).
- **GPIO17: a stable ~35.4 Hz** in all four states (9 edges per 0.25 s), and
  its readings with pulls are inconsistent. A periodic signal of its own, independent
  of the rail and of the nRF's pulls, explains its one-off passing of the
  matrix in state 15 and the `bus_busy` results. **It is not an I²C candidate.** Hypothesis:
  a frequency or PWM output from a component (for example, a
  light→frequency light sensor or an oscillator). This is checked with `pin_frequency_watch.py`
  while changing the light.
- **GPIO19 low in all states and waits** (5/50/300 ms, even with
  pull-up), whereas in r29 it followed the pulls. Something is actively driving it
  low. If RTC6→P0.19 is correct, this is consistent with an **active M41T62
  IRQ/OUT**: the RTC would be powered and with an active *flag*, consistent with the
  «clock error» in the telemetry of 18 Nov. This still needs checking by reading the RTC.
- **P0.02/AIN0** goes from ~94 mV with the rail off to ~240 mV with any
  state on. It is a weak coupling to the rail; no interpretation.

## Next

1. **Fix E1/E2** (or confirm what «pin 8» refers to).
2. Light test on GPIO17, 60 s, alternating covered and flashlight every ~10 s:

```bash
python3 scripts/pin_frequency_watch.py --pin 17 --seconds 60 --gate 1 --supply "3,3 V C/F" --out docs/evidence/gpio17-light-r33-2026-11-19
```

   Repeat with `--rail 15` if it does not change.
3. The bus still does not appear on the accessible pins. The decisive step is
   **continuity of RTC1/SDA and RTC8/SCL** to the nRF pins.
