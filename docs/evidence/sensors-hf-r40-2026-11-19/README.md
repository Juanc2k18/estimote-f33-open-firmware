# r40 · SWD and sensors powered through H/F · 2026

**Setup** (owner report): the power supply moves from C to **H/F**; value not
stated. C is left without power supply. SWD (A/B) and GND wires checked after r39.

**Measurement:**
- **Pico detected.** SWD connects; valid closure in both runs:
  bootloader `589c61bd…`, UICR `82ea7e30…` and PC in the bootloader.
- **VDD by SAADC: 1.994–1.998 V**, the same regulated ~2 V as r17–r20.
- AIN3 (battery divider candidate) reads 0.538 V. With the r20 curve
  (0.494 V at 3 V and 0.668 V at 4 V) this points to **H ≈ 3.25 V**; it is an estimate,
  not a direct measurement.
- **All five devices respond with VDD = 2 V**. In the presence check, 0x19 gave a
  NACK on the first attempt, as always. Readings at rest:

| Sensor | Reading |
|---|---|
| Accelerometer | −0.09 / 0.10 / 1.02 g (\|a\| = 1.03 g) |
| Magnetometer | 1.55 G (offset from r39) |
| BMP280 | 1006.5 hPa, 27.3 °C |
| Light | 37 lx |
| RTC | advancing |

  Registers restored.

**Note:** at 2 V VDD, the Pico's 3.3 V SWD signals are above the nRF's
VDD + 0.3 V. It works, but it is out of specification; ~1 kΩ series
resistors are advisable.

VDD/AIN evidence: `../vdd-hf-r40-2026-11-19/`.
