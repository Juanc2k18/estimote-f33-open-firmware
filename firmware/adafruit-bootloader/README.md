# Adafruit nRF52 bootloader for the Estimote F3.3

Own build of [adafruit/Adafruit_nRF52_Bootloader](https://github.com/adafruit/Adafruit_nRF52_Bootloader) **0.11.0** (commit `c67f0bc`), board `estimote_f33` derived from `feather_nrf52832`. Flashed on 2026 (logbook r14).

| Parameter | Value |
| --- | --- |
| UART DFU | **TX = P0.13 (E1, pin 16)**, **RX = P0.12 (E2, pin 15)**, 115200 baud, no flow control |
| LED | **r43/r46:** P0.17 only (confirmed in r42; transistor, active high). r14 also used P0.19, which is the RTC IRQ |
| Buttons | **r43/r46: none.** r14 had P0.20/P0.22 with pull-up; P0.22 is held low and P0.20 is unknown |
| Entering DFU with an application | 1 s UART window after every reset; GPREGRET 0xA8 (BLE OTA) or 0x4E (serial only) from the application or over SWD |
| BLE manufacturer / model (DIS) | **r46:** `Estimote F3.3 (repurposed)` / `Estimote F3.3 r46`. r43: `Estimote F3.3 (reutilizado)` / `Estimote F3.3 r43`. r14: model `Estimote F3.3` |
| SoftDevice | S132 6.1.1 |
| Boot | without a valid application it stays in DFU; with an application, 1 s of serial DFU after every reset |

Files:
- `estimote_f33_bootloader-0.11.0_s132_6.1.1-r46.hex`: bootloader, SoftDevice and UICR (r46).
- `estimote_f33_bootloader-0.11.0_nosd-r46.hex`: bootloader only (r46).
- **r46 vs r43:** r46 (2026) only changes the two BLE Device Information strings to English
  (manufacturer `Estimote F3.3 (repurposed)`, model `Estimote F3.3 r46`). A byte-level diff against
  r43 shows 47 changed bytes: those strings plus three pointer offsets that shift by one byte; the
  SoftDevice, UICR and layout are identical. **r46 was installed and verified on the reference board in 2026**: all
  populated HEX segments match SWD readback, including SoftDevice and UICR;
  BLE DIS identifies r46 and app 1.0.0 boots with valid BLE sensor data.
  BLE/UART DFU uploads were not repeated with r46; earlier upload tests used r43.
  See the [validation record](../../docs/evidence/swd-c-power-r46-2026/README.md). The r43 and r14 images are no
  longer distributed; historical hashes remain in the evidence, and r43 can be rebuilt from this
  `board.h` by restoring those two strings.
- `board.h`, `board.mk`: board definition (copy to `src/boards/estimote_f33/` in the Adafruit repository).
- `SHA256SUMS`.
- `licenses/`: Adafruit MIT license and the Nordic license for the S132 SoftDevice included in the combined `.hex` (it may only be used with Nordic circuits).

## Rebuilding

Follow the [fresh-checkout build instructions](../../docs/build.md) to install
the compiler and Python tools, clone the pinned Adafruit source and submodules,
copy the board definition and generate the r46 HEX images. The instructions
include the explicit version parameters, `intelhex` dependency and artifact
comparisons; the `tools/bootloader-build/` directory is created locally and is
not distributed with this repository.

## Flashing over SWD (Pico debugprobe)

```bash
python3 -m pyocd flash -t nrf52832 -f 1000000 -O auto_unlock=false -e chip estimote_f33_bootloader-0.11.0_s132_6.1.1-r46.hex
```


## LED assignment

The published r46 `board.h` uses P0.17 as its only LED. P0.19 is the M41T62
RTC IRQ and is not configured as a secondary LED. The r29 notes describe an
earlier bootloader, not the current board definition.
