# F3.3 application (BLE + UART with a host) · version 1.0.0

Release build: `release/f33-ble-sensors-1.0.0.hex` and `.zip` (DFU package),
with `release/SHA256SUMS`. Version history and the full guide in
[docs/guide-f33.md](../../docs/guide-f33.md).

C on top of the S132 6.1.1 SoftDevice API, without the Nordic SDK. It is loaded at
0x26000 below the Adafruit r46 bootloader (r43 in earlier tests). Designs: internal design notes for
BLE and for UART (not published).

| File | Purpose |
|---|---|
| `main.c` | SoftDevice, GATT, RTC1 (counts seconds up to the interval), UART commands, DFU |
| `sensors.c`, `twim.c` | The five sensors over I²C, and SAADC |
| `f33_math.c` | Conversions, battery and BLE packet (pure, tested on the Mac) |
| `f33_uart.c` | JSON line, line assembly and commands (pure, tested on the Mac) |
| `uart.c` | UART0 on E1/E2, host detection on E2 and TX ring buffer |

Start-up uses Nordic's `Reset_Handler` (`-nostartfiles -D__START=main
-D__STARTUP_CLEAR_BSS`), without the newlib CRT, and links with `--fatal-warnings`.

## Build and flash

For a new environment, first follow the [build instructions](../../docs/build.md).
They prepare `tools/bootloader-build/` (Arm 15.2.rel1 compiler and the pinned
bootloader clone with the S132, nrfx/mdk and CMSIS headers) and explain path overrides.

```bash
make -C firmware/ble-sensors
```

```bash
pyocd flash -t nrf52 -u E660C0D1C75C942F firmware/ble-sensors/build/f33-ble-sensors.hex
```

It only erases the application sectors. The bootloader accepts it without a DFU
package (settings page 0x7F000 erased and valid vectors). After a DFU upload
that page is left written: it is best to erase it before flashing over SWD again.

### Without SWD (r45)

`make zip` (optionally `FW_REV=r45-x OUT=build/x`) generates the DFU package with
`adafruit-nrfutil` from `.venv`:

```bash
make -C firmware/ble-sensors zip
```

Over BLE (terminal tab; if it finds `F33`, it first switches it to `AdaDFU`):

```bash
.venv/bin/python scripts/ble_dfu.py firmware/ble-sensors/build/f33-ble-sensors.zip
```

Over UART on E1/E2 (Pico GP4→E2, GP5←E1, GND→E4; VDD ≥ 3 V). The script waits for
the boot: cut and restore the power, or send `ble_sensors.py --serial-dfu`.

```bash
.venv/bin/python scripts/uart_dfu.py firmware/ble-sensors/build/f33-ble-sensors.zip
```

With the 1.0.0 app and a host connected, without cutting anything (UART command `dfu`):

```bash
python3 scripts/uart_dfu.py --command --port /dev/cu.usbmodem21102 firmware/ble-sensors/build/f33-ble-sensors.zip
```

## UART with a host (E1–E4)

E3 at 3.3 V, E4 GND, host TX → E2 and RX ← E1, 115200 8N1. The UART
turns itself on if E2 is high, because the host TX is idle. One
JSON line per measurement and the commands `read`, `int N`, `ver`, `dfu` and `ota`. Format
and command table in the [guide](../../docs/guide-f33.md#5b-use-with-a-host-on-e1e4-version-100).
Reader: `python3 scripts/uart_sensors.py --port <port>`.

## BLE

- `F33` advertisement, connectable, every 1 s.
- Service `239d0001-86eb-4a92-8ec1-0e38f13e0817`:
  - `…0002` data: read and notification every 1 s (since r45c it also measures
    without a connection; 31 bytes, see `f33_math.h` and `scripts/f33_packet.py`).
  - `…0003` control: `0x01` restarts into DFU OTA (`AdaDFU`); `0x02` into DFU over
    UART (E1/E2) for 3 s.
- Battery Service `0x180F`: level `0x2A19` (%), with two cells in series and a
  provisional table (`f33_battery_percent`).
- Device Information `0x180A`: revision `0x2A26` = `FW_REV`.
- RAM `f33_status` (marker "F33S"): `scripts/swd_monitor.py` reads it over SWD.
  Since 1.0.0 it also carries `uart_dropped` at the end (lines not sent for lack
  of space).

From the Mac, in a terminal tab (`--duration S` records with reconnection):

```bash
python scripts/ble_sensors.py --count 15 --out docs/evidence/<folder>
```

## Power

H/F (batteries, two in series): VDD = 2.0 V; works from ≈3.0 V (boots at
≈3.3 V). E3/E4: **do not use 5 V** (VDD 4.58 V, above the nRF maximum);
use 3.3 V on E3 (VDD ≈3.0 V), checking host logic-level margin as described in the guide.

## Pins

P0.14/P0.15 = SDA/SCL with internal pull-up, P0.06/P0.07 high with high drive
(probable sensor power supply), P0.17 = LED, P0.05 = AIN3 and P0.12/13 =
UART with a host (without a host, E2 with pull-down and E1 in high impedance). It does not touch
P0.19 (RTC IRQ) or P0.21 (reset).

## Tests

```bash
python3 -m unittest tests.test_ble_firmware
python3 -m unittest discover -s tests -p 'test_*uart*.py'
```

They compile `f33_math.c` and `f33_uart.c` on the Mac. They are checked against the
example from the BMP280 datasheet, the Python decoder and the UART reader.
