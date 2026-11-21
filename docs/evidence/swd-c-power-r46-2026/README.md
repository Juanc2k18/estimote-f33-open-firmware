# Bootloader r46 installation and validation on C/F at 3.3 V · 2026

Goal: document the final planned direct-VDD session before validating bootloader
r46. The record covers the read-only preflight, SWD installation, image verification, application BLE data and bootloader BLE identity.

## Setup (owner report)

The owner confirmed the preceding setup and reported powering the board at
3.3 V on C. The requested setup was: regulated supply + to C and - to F;
Pico GP2 (physical pin 4) to A/SWDCLK, GP3 (physical pin 5) to B/SWDIO,
Pico GND to F; H and E3 disconnected, UART/SWO/reset disconnected.
No new multimeter reading was supplied. 3.3 V is the reported supply setpoint,
not an independent voltage measurement by the software.

## Tools and method

- Raspberry Pi Pico debugprobe, probe ID `E660C0D1C75C942F`.
- pyOCD 0.46.1, Python 3.10.14; installed outside the repository `.venv`.
- `pyocd list` identified one probe.
- `ConnectHelper.session_with_chosen_probe`, target `nrf52`, SWD 1000000 Hz,
  `connect_mode=attach`, `auto_unlock=False`, `resume_on_disconnect=False`.
- Read FICR, UICR, the 9244 application bytes at 0x26000 and bootloader region
  0x74000–0x7DFFF. Compared the application with the BIN in the published
  `firmware/ble-sensors/release/f33-ble-sensors-1.0.0.zip`.
- No core halt/reset, erase, UICR programming or firmware upload was requested.

## Preflight result (before programming)

SWD attach and memory reads succeeded. FICR identifies nRF52832/AAB0,
64 KiB RAM and 512 KiB flash. The CPU was observed sleeping.
The installed application's 9244 bytes match the published DFU payload exactly,
SHA-256 `9af7e77a74cb0ec9e0a9ea84436ec48631492cd9b4ee0ad8cb963c7c0f506dae`.
UICR bootloader address is 0x74000 and both reset assignments are P0.21.
The bootloader contains the r43 model string; the r46 model string is absent.
Details: `preflight.json`.

This confirms communication and image identity under the reported C/F setup.
At this stage it did not validate r46. Neither this session nor its software readings establish compatibility of 3.3 V SWD signals with a target running at VDD=2.0 V.

## Future power and validation scope

The owner requests future operation on the previously validated 6 V H/F input
and no further direct-C power sessions after this one. Prior H/F measurements
are documented in the r20/r45 evidence: the battery input regulates VDD to
approximately 2.0 V. This 6 V input validation applies to H/F only, not E3 or C.
UART/SWD interfaces must still be compatible with the resulting VDD; this
preflight makes no new claim about SWD on H/F.

## Programming and verification

The two commands in `planned-commands.txt` were subsequently executed in order:
full-chip erase and the published r46 combined HEX (bootloader, S132 and UICR),
then a sector-based write of the published 1.0.0 application. Both returned 0.
The exact executed commands, hashes and relative durations are recorded in
`flash-result.json`; tool output is in the two `*-flash.log` files.

All populated segments of both published HEX images match SWD readback byte for
byte, including the combined image's UICR words. See `postflash.json`.
The settings page was erased. Application status at 0x20003004 advanced from
55 to 57 over approximately 2 s, with flags 0x3F (five sensors plus ADC).
Software VDD was 3.230 V in that sample; this is not a multimeter reading.
AIN3 was 0.498 V despite H being reported disconnected; the inferred battery
value is not a measurement of an attached battery.

The first runtime check searched all RAM and found a stale `F33S` copy at
0x200023E4. Its zero counter caused the check to fail. The existing monitor and
linker place application RAM at 0x20003000; restricting the search to that
region found the live structure. `postflash-initial.json` preserves the first
attempt; `runtime.json` records the corrected check. No firmware change was
needed.

## Bluetooth checks

Agent-process scans did not discover F33 or AdaDFU. Scans/readout from Terminal,
which has Bluetooth access in this setup, succeeded:

- `scripts/ble_sensors.py --count 3 --scan 8`: F33, firmware 1.0.0, MTU 64,
  three notifications with all six validity flags true (`ble-app-terminal/`).
- Read-only radio sampling over SWD observed advertising frequencies 2/26/80
  MHz offset (`app-radio.json`).
- Requested BLE DFU on the exact SWD target via GPREGRET=0xA8 followed by
  SYSRESETREQ; no further flash was written (`enter-ble-dfu.json`).
- `scripts/ble_scan_read.py --name AdaDFU --seconds 5`: 37 advertisements;
  DIS manufacturer `Estimote F3.3 (repurposed)`, model `Estimote F3.3 r46`,
  firmware `0.11.0 s132 6.1.1` (`ble-bootloader-terminal/`).
- Reset back to the application: the runtime counter advanced from 1 to 2, flags 0x3F (`final-state.json`); Terminal received three further BLE notifications, version 1.0.0 and MTU 64 (`ble-final-terminal/`).

Current claim: r46 SWD installation, exact image readback, application boot and
BLE data, and bootloader BLE identification are validated on this unit.
BLE/UART uploads were validated previously with r43; no DFU payload upload was
repeated during this r46 session. UART E1/E2 was disconnected.
Calendar metadata in published JSON/JSONL is replaced by relative seconds.
The supply remains as reported for this session: 3.3 V on C/F, H/E3 disconnected.
