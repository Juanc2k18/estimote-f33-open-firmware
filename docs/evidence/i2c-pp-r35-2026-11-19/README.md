# r35 · I²C with SCL in push-pull on the neighbours of P0.19 · 2026

Run by the owner of `scripts/i2c_pushpull_scl.py`: pairs of 16/17/18/20,
rail states off/15/14, addresses 0x68, 0x18, 0x19, 0x50, 0x76 and 0x77.
Setup: 3.3 V on C/F. Status `incomplete` because of three pairs with GPIO17. Valid
closure: PC 0x750FE, identical hashes and CNF19=0. From RAM; no flash or UICR.

## Result

- **108 NACK and no ACK** on the electrically valid pairs of 16, 18 and 20
  (6 per state; in 14 the pair SDA20/SCL17 was added). On those three GPIOs
  neither the RTC nor any candidate sensor responds, in any rail state.
- **GPIO17 drives poorly even in push-pull H0H1.** Driven high as SCL,
  it read 0 in 6 of 9 idle samples. There were `clock_not_high` (it did not reach
  high within 15 ms), `timeout` and `bus_busy`. To read low with a strong high
  *driver*, the pin has to be below ~0.3·VDD. That implies a
  **second low-impedance external *driver* on 17 or a load almost to ground**,
  not an LED with a resistor nor a pull-up. With the edge bursts of r33,
  the most consistent explanation is that **17 is an output of another chip** (INT/OUT), and not SDA/SCL.
- **Recommendation:** do not drive 17 as an output again. Doing so may create
  contention with that other chip. It stays input-only in future tests.

## Situation

Over SWD the accessible pins have already been covered in all reasonable
variants: OD, push-pull, rail off/14/15/6+7 and 6 V/3.3 V. No pair
responds at 0x68. The bus is not on the pins the nRF can drive
normally, or the devices do not respond in this state. **The next
data point has to be physical:** continuity of RTC1/RTC8 (or their vias) to the
nRF pins, and also of RTC6 to confirm pin 22.
