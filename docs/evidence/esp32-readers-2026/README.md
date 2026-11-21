# ESP32 DevKit V1 UART and BLE readers · hardware results · 2026

Goal: confirm that the two Arduino examples can read the F3.3 sensor data on a
real ESP32, beyond the earlier compilation and decoder tests.

## Setup and tools

Owner report: ESP32 DevKit V1; both sketches work. The preceding setup request
specified E1–E4 only, with the F3.3 powered at 3.3 V on E3.
The UART sketch shown selects GPIO16 as RX from E1 and GPIO17 as TX to E2,
115200 baud, 8N1. The documented wiring has common GND on E4, H/C disconnected.
The physical wires and source of the 3.3 V supply are not visible in the images;
this record does not establish use of the ESP32's own 3V3 regulator pin.

Both screenshots show Arduino IDE **2.3.11**, the **ESP32 Dev Module** board
profile and serial monitor on `/dev/cu.usbserial-0001` (an example port, not a
portable identifier). The example sources target Arduino-ESP32 3.3.10; the
screenshots do not independently establish the installed core version or the
flashed binary hash. Both ESP32 Dev Module and DOIT ESP32 DEVKIT V1 profiles
were compiled in the offline checks.

Operations: the owner uploaded `f33_uart_reader.ino` and
`f33_ble_reader.ino` separately and observed their serial output. No additional
hardware operations were performed by the agent for this record. For the
repeatable example instructions, see [ESP32 readers](../../../examples/esp32/README.md).

## Observations from the screenshots

| Reader | Visible result |
|---|---|
| UART | 16 JSON lines, sequences 182–197; all five sensor fields plus ADC present; RTC seconds 21–36. |
| BLE | F33 discovered at `eb:46:d9:38:11:cb`, connection message, 13 displayed GATT reads, sequences 4–17 with 7 absent; every row has `valid=0x3f`. |
| UART VDD | Software ADC values 2.963–2.979 V. |
| BLE VDD | Software ADC values 2.939–2.976 V. |

The BLE sequence gap is consistent with polling the latest value once per
second; the screenshot does not establish lossless delivery. The reader uses
GATT reads, not notifications. Sensor values change and RTC seconds advance.
These are separate recordings; they do not establish simultaneous UART/BLE
sample equality. A zero battery estimate with E3 power does not indicate a
battery was connected or depleted.

Conclusion: **basic UART sensor reception and BLE discovery, connection and
sensor reads work on the owner's ESP32 DevKit V1**, supported by the owner's
report and screenshots. S3/C3 retain compilation-only status. Reconnection after
an induced disconnect, extended operation, commands, notifications and DFU on
ESP32 are outside this validation.

This functional result does not measure host TX levels or prove electrical
margin for every 3.3 V host. Retain the guide's level checks against target VDD.

## Evidence

- `uart-reader.png` and `ble-reader.png`: byte-identical copies of the owner attachments.
- `result.json`: observations transcribed from the screenshots, separated from owner report.
- `SHA256SUMS`: hashes of this record.
