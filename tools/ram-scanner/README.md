# RAM bus scanner (nRF52832)

`scanner.c` is compiled for RAM, loaded over SWD and run without touching flash: the bootloader comes back after the final reset.

It tests:
- **Bit-banged SPI:** 4-wire and 3-wire, modes 0 and 3, with active-low CS on the given pins. Reads typical WHO_AM_I registers (commands `0x8F`, `0xCF`, `0xD0`, `0x80`, `0x92`).
- **I2C:** every pair of candidate pins with a real external pull-up, checked with the internal pull-down.

Build (Arm GNU Toolchain 15.2.rel1):
```bash
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -Os -ffreestanding -nostdlib -T ram.ld -Wl,--gc-sections,--no-warn-rwx-segments -o scanner.elf scanner.c
arm-none-eabi-objcopy -O binary --only-section=.text --only-section=.data scanner.elf scanner.bin
```

Run:
```bash
python3 tools/ram-scanner/run_scanner.py --power 14,15 --cs 6,7
```

With only one of P0.14/P0.15 high, I2C on P0.06/P0.07 gives an ACK at every address. This is a false positive: the line rises too slowly with a weak pull-up.

## Experimental r17 variant

`scanner-r17.c` keeps the original SPI, allows I2C with internal pull-ups,
checks SCL when sampling the ACK and requires a high idle level after STOP. It starts with
interrupts disabled. Build it the same way as the original, replacing the
source file name. Results from the two variants are not mixed: state which one was used.
`run_scanner.py --low 14,15 --power ''` keeps those GPIOs low during the test.
Do not include UART P0.12/P0.13 while the Pico is still connected, nor the crystal P0.00/01
or nRESET P0.21. The output adds PC/xPSR and CFSR/HFSR to check execution.

Evidence and limitations: [r17 campaign](../../docs/evidence/sensors-r17-2026-11-19/README.md).

## r18 variants

- `scanner-r18.c`: allows limiting I2C to pairs that include a given pin with
  `run_scanner.py --image scanner-r18.bin --require-pin N --cs '' ...`.
- `scanner-r18-spi.c`: requires an effective low CS, a repeatable reading and a response
  that differs from the control with CS deasserted. `--mosi list` allows MOSI
  candidates different from `--sck`; this argument only has that meaning with this
  variant. For SPI only, use `--i2c ''`. The header mask `magic`
  serves as an I2C filter in r18 or as a MOSI mask in the SPI variant.
- `scripts/sensor_reset_pin_trial.py`: test of P0.21 temporarily released from
  reset; reprograms UICR, saves the defined fields and restores them in `finally`.
  Checks the SHA-256 of the bootloader block before/after. It is not read-only.
- The loader accepts `--image`, `--frequency` and resets in `finally`.

## r24 variant: SPI electrical classification (not run on the board)

`scanner-r24-spi.c` derives from r18, is SPI only and requires choosing pins by
continuity on this unit. Do not use it as a new bulk sweep. `progress` still
counts combinations, while the block at offset 996 counts SPI calls:
CS that does not go low, SCK that does not reach both levels, completed calls,
primary probes completed without a signature, signatures, incomplete validations and
CS control that does not go high. Electrical errors return negative values,
kept apart from any 00–FF byte. SCK is physically read back on every transition.

Load with `run_scanner.py --image tools/ram-scanner/scanner-r24-spi.bin
--spi-stats` with explicit targeted masks, `--i2c ''` and `--power ''` (or a
single justified enable). The loader rejects 14/15 high at the same time and
SCK3/4/11/22/25 when using `--spi-stats`. No physical mask is provided
for this unit because CS/SCK are still unidentified.

Host validation: `clang -Wall -Wextra -Werror -o /tmp/estimote-spi-test
tests/spi_classification.c` and run `/tmp/estimote-spi-test`.
Build for ARM the same way as r18, replacing the name with scanner-r24-spi.
Targeted I²C test with a negative control and independent electrical validation:
`python3 scripts/i2c_trial_r24.py --out docs/evidence/i2c-r24-repeticion`.
Results and versioned sources in [r24](../../docs/evidence/i2c-r24-2026-11-19/README.md).
