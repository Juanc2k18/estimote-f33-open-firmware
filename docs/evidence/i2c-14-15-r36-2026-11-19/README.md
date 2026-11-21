# r36 · I²C bus located: SDA=P0.14, SCL=P0.15 · 2026

Run by the agent, at the owner's request, of `scripts/i2c_rail_bus.py`.
Declared setup: owner's power supply at 3.3 V on C/F; Pico SWD on A/B/F.
A read-only check was done first: PART 52832/AAB0, APPROTECT
FFFFFFFF, PC in bootloader. Status `complete`. Valid closure: PC 0x75108,
bootloader and UICR hashes identical and CNF19=0. From RAM; **I²C reads only,
no writes to the devices** and no changes to flash or UICR.

## Result

**SDA=P0.14 (pin 17) and SCL=P0.15 (pin 18)**, as reported by the
owner from continuity. The reverse orientation (SDA15/SCL14) gives no ACK.

| Address | ACK | Identification (repeated read) | Model |
| --- | --- | --- | --- |
| 0x19 | validated 3× with controls | WHO_AM_I 0x0F = **0x33** (×3) | **LIS2DH12** (or LIS3DH-compatible), SA0=1 |
| 0x1E | validated | WHO_AM_I 0x0F = **0x3D** | **LIS3MDL**, magnetometer, SA1=1 |
| 0x4A | validated | no ID register; map consistent with MAX44009: config 0x02, lux 0x3F/0x0B (≈90 lx), thresholds 0xEF/0x00, timer 0xFF | **MAX44009 probable**, light sensor |
| 0x68 | validated | calendar advancing; flags 0x0F = **0x04 (OF=1)** | **M41T62**, RTC |
| 0x77 | validated | chip_id 0xD0 = **0x58** (×3) | **BMP280**, SDO=1 |

No response at 0x50–0x57: there is no EEPROM on this bus.

### M41T62 RTC

In three runs, the hundredths and seconds advance **1.80–1.81 s** over
measured windows of **1.807 s**. The oscillator works and the count is exact.
The calendar has non-BCD values (minutes 0x76/0x77, hour 0x3F, date 0x9D…),
that is, the time was never set after power was lost. **OF=1** is the
oscillator-fail *flag*, consistent with the "clock error" in the original
telemetry. SQWE=1 and RS=0001: SQW outputs 32.768 kHz on pad 2, but its destination
has not been seen on any free GPIO. The tool classified it as
`invalid_clock_data` because of the reserved bits; that is a limitation of the criterion,
not an RTC fault.

### Role of P0.06/P0.07

- **Rail 6+7 on:** the bus is valid in open drain and in push-pull.
- **Rail off:** open drain is electrically invalid (idle 0/0),
  but with SCL in push-pull and the internal pull-up on SDA all five devices
  respond and identify the same way.

Conclusion: **P0.06/P0.07 power the bus pull-ups** (pull-ups switched
by GPIO to save energy), and the sensors have their own supply (VDD).
That explains why 14/15 high raise {6,7} through the pull-ups. It remains
not fully explained that, in r31, {6,7} did not raise 14/15 with pull-down; it is
compatible with a VIH threshold of 0.7·VDD against a pull-up/pull-down divider.

## Why it was not found earlier

Since r16, 14/15 were treated as "enables" and were always left out of
the I²C pairs. With the rail off and no pull-ups, the bus looks dead in
open drain. The decisive clue was the physical continuity RTC1→17 and RTC8→18.

`id-reads.json` holds the later identification reads (0x1E, 0x4A,
RTC registers 0x08–0x0F, 0x19 and 0x77), also with a valid closure.
