# r42 · LED on P0.17 confirmed · 2026

**Continuity (owner report):** nRF pin 20 (P0.17) goes to
a three-legged component, probably a transistor, and from there to a
resistor and the LED. Ohms and the instrument were not recorded.

**Test:** `scripts/led_blink_probe.py --delay 10`, with the power supply on H/F and
VDD = 2.0 V.
1. Halts the CPU and disables PWM0, which the bootloader uses on 17 and 19.
2. Leaves 17 and 19 low (outputs) for 10 s.
3. P0.17: three pulses of 2 s high and 2 s low.
4. 5 s pause.
5. P0.19: the same pattern.
6. SYSRESETREQ reset.

It does not write to flash or UICR. Over SWD, IN followed OUT on both pins.

**Owner's observation:** he saw only 3 flashes, then the LED off for a
while and then the bootloader's "breathing". From the order, the flashes
were those of P0.17: the P0.19 group and the pause form the dark stretch before
the reset.

**Result:** the **LED is on P0.17 and is active high** (it lights with the
pin high and was off with the pin low), through a transistor.
**P0.19 has no LED.**
- `LED_PRIMARY_PIN 17` and `LED_STATE_ON 1` are confirmed correct.
- `LED_SECONDARY_PIN 19` is wrong: that is the RTC IRQ.

**Reinterpretation of r33–r35:** GPIO17 does not have an external *driver*. It drives
the base or gate of a transistor. If it is an NPN with a low base resistance, the
pin stays near 0.7–0.9 V; that is why at VDD = 3.1 V it read 0 even when
driven high. At VDD = 2.0 V the input does read 1. Driving 17 is safe: the
bootloader does it on every boot. The "do not drive 17" restriction is withdrawn.

The first run (`../led-r42a-ambiguous-2026-11-19/`) used a 1 Hz blink
on 17 and 4 Hz on 19 without first stopping the bootloader LED. The owner's
observation turned out ambiguous.
