# r43 · Bootloader reflashed with the board fixes · 2026

**Reason:** `board.h` inherited from the Feather an LED on P0.19, which is the
RTC IRQ (r29/r42), and buttons on P0.20/P0.22, P0.22 being a pin stuck low.

**Changes in `firmware/adafruit-bootloader/board.h`:**
- `LEDS_NUMBER 1`, only with P0.17.
- No `BUTTON_DFU` or `BUTTON_DFU_OTA`.
- DIS model `Estimote F3.3 r43`.

**Build:**
- Adafruit_nRF52_Bootloader `c67f0bc` with Arm GNU Toolchain 15.2.rel1
  darwin-arm64. The toolchain SHA-256 matches the one published by Arm
  (`1938a84b…`).
- Prior control: the build without changes reproduced the r14 hex **bit for bit**
  (`9094ca7a…`).
- r43 usage: 20 992 B of flash and 16 024 B of RAM.

**Flashing:** `pyocd flash -e chip -f 1000000`, 181 248 B and 45 pages
(`flash.log`). Power supply on H/F.

**SWD verification** (`verify.txt`):
- Flash identical to the hex in all three segments.
- SHA-256 of region 0x74000–0x7E000: `8e6f23cb…`. This is the new reference
  value for closures; previously it was `589c61bd…`.
- UICR:
  - BOOTLOADERADDR 0x74000
  - MBR params 0x7E000
  - **PSELRESET[0:1] = 0x15 (P0.21)**
  - APPROTECT 0xFFFFFFFF
- After reset: PC 0x77960, inside the bootloader.
- Peripherals:
  - **PWM0 only on P0.17**
  - CNF19/20/22 = 0x2 (disconnected)
  - UART enabled with TX13/RX12

**BLE** (`ble-ota/`, `ble-mac/`): with GPREGRET=0xA8 and reset, the radio transmits
on channels 37 and 39. From the Mac: 59 advertisements, median RSSI −59 dBm.
Device Information returns **model "Estimote F3.3 r43"**, manufacturer
"Estimote F3.3 (reutilizado)" and firmware "0.11.0 s132 6.1.1".

**UART DFU:**
- First attempt (`dfu-ping.jsonl`): 5 pings with no response. E1/E2 were not
  connected to the Pico.
- Afterwards the owner confirmed E1/E2 ↔ GP5/GP4. With GPREGRET=0 and an SWD reset
  (serial mode), `dfu-ping-2.jsonl` gave **10 of 10 ACK** via
  `/dev/cu.usbmodem1131202`.
- Note: in BLE OTA mode the bootloader does not service the UART.
