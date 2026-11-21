# r33 · GPIO17 with light: it is not a frequency · 2026

`pin_frequency_watch.py --pin 17 --seconds 60 --gate 1`, at 3.3 V on C/F and without
rail. The owner applied strong light and reports that he noticed no changes. GPIO18
counter control: 20/20. Valid closure, identical hashes and CNF19=0.

## Result

59 windows of 1 s: **8–9 edges per window**, unrelated to the light.
In r31 and r32, with 0.25 s windows, **9 edges** came out. Since the number of
edges does not depend on the window length, **it is not a periodic signal**.
The "~35 Hz" of r31/r32 was an artefact of dividing that fixed burst by a
short window. This is now corrected.

What is consistent is a **burst of ~9 edges when the pin is configured as an input**:
the voltage crosses the input threshold slowly and noise generates bounces. This fits
the inconsistent readings of 17 with pulls (r31/r32) and a node that sits
**near the threshold**. For example, an LED from 17 to ground clamps the pin at its
forward voltage (~1.6–1.9 V) against the internal pull-up, and that falls in the
indeterminate zone between VIL and VIH at 3.1 V. The bootloader *define* assigns the red
LED to 17, and the owner saw an LED blinking in DFU mode. **Hypothesis: 17 is
the LED**, not a sensor. To confirm it: with the bootloader active, see whether the blinking
LED goes off when 17 is touched, or turn 17 on as an output and observe it.

Lesson for the tool: a count that does not scale with the window indicates a
burst or artefact, not a frequency. To claim a frequency you have to measure with
two different windows.
