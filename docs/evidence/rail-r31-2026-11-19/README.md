# r31 · Rail topology, edge counting and LFCLK · 2026

Run by the owner of `scripts/rail_survey.py` (first version). Setup
declared in `--supply`: **3.3 V on C/F; H/E3 loose**. Status `complete`. Valid
closure: bootloader PC 0x750EC, bootloader and UICR hashes equal, CNF19=0.
From RAM; no changes to flash or UICR. Since the topology was not a single node,
**the rail was not switched on** and there was no I²C. `source/rail_survey-r31b.py` is the
later version, already with separate states; the one run is the earlier one. Its
measurement logic is the same.

## Results (measurement by SWD; GPIO.IN register, no oscilloscope)

**1. Topology 6/7/14/15: directed, not a single node.**

| Pin driven high (S0H1) | 6 | 7 | 14 | 15 |
| --- | --- | --- | --- | --- |
| 6 | — | 1 | 0 | 0 |
| 7 | 1 | — | 0 | 0 |
| 14 | 1 | 1 | — | 0 |
| 15 | 1 | 1 | 0 | — |

At rest, with pull-down, all four read 0. 6 and 7 are joined in both
directions. 14 and 15 each pull up the {6,7} node, but the node does not pull them up
and neither pulls up the other. With a ~13 kΩ pull-down, a low resistance would make
14/15 rise when 6 is driven. That is why the 14/15→{6,7} path is **unidirectional**:
a diode OR or the enable input of a load switch or MOSFET,
whose output is {6,7}. Together with r24 (with 14 high, 6 does not go low), the second
option, a stiff output switched by 14 or 15, is the most consistent.
**Hypothesis:** {6,7} is a switched power output, and 14/15 are
independent enables or an OR. This can be confirmed with continuity or with
the photo of the SOT-23s.

**2. Counter.** The control with GPIO19 gave 0/20: **19 no longer follows the pull-up at
3 ms**, unlike r29 (64/64 with slow sampling). The control with GPIO18
gave 20/20, valid. It may be an active-low RTC IRQ (in that case the RTC
would be powered and with an active *flag*) or a slow RC. Version r31b adds
`slow_pull` on 17/19 (5/50/300 ms) to tell them apart.

**3. Edges with the rail off.** No GPIO has ~32 kHz. Only **GPIO17:
9 rising edges in 0.25 s (~35 Hz)**, with inconsistent readings (high when floating, low
with pull-up and does not go low with OD). It is consistent with a floating node with noise or
with a slow signal. It must be repeated with a longer window before giving it
an interpretation. The bootloader's *define* assigns it the red LED.

**4. LFCLK: its own passive crystal.** With LFCLK stopped, XL1/XL2 give no edges.
In crystal mode it starts in 0.318 s and RTC2 reads **32 760 Hz** against the host
clock (the error is within the method's uncertainty). In
BYPASS+EXTERNAL it does not start. Therefore, **the M41T62's SQW does not reach XL1**. The
nRF's 32 kHz comes from a discrete crystal, as on the UWB (3215). The RTC's SQW
still has no known destination; it was not seen on any free GPIO. This does not prove that the
RTC is unpowered: its SQW may be disabled by the previous configuration,
or hang off a switched-off {6,7}.

**5. SAADC** (input disconnected, no pull): VDD 3.120 V; P0.05/AIN3 468 mV,
with H loose; AIN1/P0.03 9 mV and AIN2/P0.04 6 mV, effectively grounded;
AIN0 92 mV and AIN4–7 116–247 mV, floating.

**6. OD matrix with the rail off.** Valid: 2, 8, 9, 10, 16, 18, 20, 23, 24,
26–31. Stuck low with pull-up: **3, 4, 5, 22, 25**. 17 is anomalous. Matches
r16.

## Next run

Version r31b tests the states separately, in the order `--states 14,15,67,all`:
**14 only**, **15 only** and **6+7**, each in H0H1 and checking that {6,7}
goes high. `all` still requires a single node, so with this topology it
will be skipped. 14 and 15 are never driven high at the same time.

```bash
python3 scripts/rail_survey.py --no-lfclk --supply "3,3 V C/F; H/E3 sueltos" --out docs/evidence/rail-r32-2026-11-19
```

`--no-lfclk` avoids repeating what has already been settled.
