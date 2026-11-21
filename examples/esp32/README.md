# ESP32 master–slave application examples · F3.3 1.0.0

The ESP32 acts as the **master application / host** and the F3.3 as the
**slave sensor node**. Two independent Arduino sketches demonstrate sensor
reading over UART or Bluetooth LE. Over BLE, the precise roles are ESP32
central/GATT client and F3.3 peripheral/GATT server. Over UART, the F3.3 sends
JSON automatically; UART itself does not define a master/slave bus protocol.

Choose one sketch per connection method:

| Sketch | Behavior |
|---|---|
| `f33_uart_reader/f33_uart_reader.ino` | Receives E1/E2 JSON lines and forwards them to the USB serial monitor. |
| `f33_ble_reader/f33_ble_reader.ino` | Finds F33, reads the sensor characteristic once per second, decodes the packet and prints values. Reconnects after disconnection. |

Open one `.ino` in Arduino IDE. For the reported DevKit V1 select
**Tools → Board → esp32 → ESP32 Dev Module** (the profile shown in the
owner's successful tests). DOIT ESP32 DEVKIT V1 also compiles. Use
**esp32 by Espressif Systems 3.3.10**, with its built-in BLE library. No external
Arduino libraries are needed. Open the serial monitor at **115200 baud**.
Keep `f33_packet.h` beside the BLE sketch.

**Basic UART reception and BLE sensor reads were validated on the owner's
ESP32 DevKit V1 in 2026**, supported by the owner's report and screenshots.
See the [hardware results](../../docs/evidence/esp32-readers-2026/README.md).
ESP32-S3/C3 have compilation checks only. Other development boards still need
pin and electrical checks.
No upload or hardware connection is performed by the compilation commands below.

## E1–E4 and power

The requested setup uses only the external connector, with **3.3 V on E3**:

| F3.3 pad | UART example | BLE example |
|---|---|---|
| E1 (nRF TX) | ESP32 RX, chosen below | Unconnected |
| E2 (nRF RX) | ESP32 TX, chosen below | Unconnected |
| E3 | Regulated 3.3 V supply + | Regulated 3.3 V supply + |
| E4 | Supply ground and ESP32 GND | Supply ground |

H/batteries and C must be disconnected when powering E3. When leaving the SWD
setup, power down before changing connections and disconnect the Pico signals.
For BLE the two devices communicate wirelessly; no signal wires or common
ground between boards are needed. Each still needs its own suitable power source.

The earlier 3.3 V E3 path was tested with a laboratory supply. The ESP32
screenshots do not show the source of the reported 3.3 V input.
If you want to power E3 from an ESP32 board's 3V3 pin, verify its regulator's
available current and startup behavior first. Do not use its 5V/VIN pin.

**UART voltage margin:** E3=3.3 V gave VDD near 3.0 V, with recorded samples
down to 2.985 V in the earlier Pico test; the ESP32 UART screenshot shows
2.963–2.979 V (software ADC). Measure actual host TX and target VDD before connecting TX to
E2; nominal 3.3 V TX has little or no margin against the nRF's VDD+0.3 V limit.
Use suitable level translation if necessary. This working setup does not make
all 3.3 V hosts electrically compatible. See the [power guide](../../docs/guide-f33.md#3-power).
The firmware enables UART when E2 is idle high; connecting only E1 to RX will
not enable the application UART reliably.

For the reported classic DevKit V1, use **GPIO16/RX2 from E1** and
**GPIO17/TX2 to E2**, as already selected by the UART sketch. The numbers are
ESP32 GPIO numbers, not physical pin numbers. Other chips use these examples:

| Chip | `F33_RX_PIN` (from E1) | `F33_TX_PIN` (to E2) |
|---|---|---|
| ESP32 classic | GPIO16 | GPIO17 |
| ESP32-S3 | GPIO18 | GPIO17 |
| ESP32-C3 | GPIO4 | GPIO5 |

For example, some classic ESP32 boards with PSRAM reserve GPIO16/17. Confirm
available pins and change the two constants before wiring your board. Other
chips deliberately produce a compile error until pin selection is added.

## UART output

UART is 115200 baud, 8N1. The sketch leaves TX idle high and sends no commands.
It forwards lines starting with `{`, skips other boot fragments, and discards
overlong lines through the next newline. It does not parse or validate JSON.
Lines beginning with `#` are reader diagnostics, not sensor JSON.

```json
{"seq":123,"acc_mg":[12,-30,1035],"mag_mg":[1080,750,-210],"temp_cc":2810,"press_pa":100660,"mlux":22000,"rtc_s":41,"vdd_mv":3000,"ain3_mv":40,"bat_mv":0,"bat_pct":0}
```

Units: acceleration mg, magnetic field mG, temperature 0.01 °C, pressure Pa,
light 0.001 lux, RTC seconds, ADC/battery mV. Fields for invalid sensors are
omitted by the F3.3 firmware. With E3 power and H disconnected, `bat_mv` and
`bat_pct` do not describe an attached battery.

## BLE output

Requires an ESP32 chip with native BLE, for example ESP32 classic, S3 or C3.
ESP32-S2 cannot run this BLE example. No pairing or control commands are used.
The F3.3 allows one BLE connection: disconnect other readers before testing.

The sketch uses active scanning. By default it connects only if exactly one
device named `F33` is found during the scan. With multiple units, set
`TARGET_MAC` to the address printed by the ESP32. A macOS peripheral UUID is
not an ESP32 BLE address. Scan visibility is not a guarantee of device identity;
use a specific address when selecting among units.

The reader requests MTU 64 and performs **GATT reads**, rather than subscribing
to notifications. Every read must return exactly 31 bytes with packet version
1; malformed reads are reported and three consecutive failures trigger a
reconnection. Only sensor fields marked valid are printed. This does not test
notification delivery on the ESP32. The request is not proof that MTU 64 was
negotiated; packet-length validation detects incomplete reads.

```text
seq=123 valid=0x3f acc_g=[0.012,-0.030,1.035] mag_G=[1.080,0.750,-0.210] temp_C=28.10 pressure_hPa=1006.60 light_lux=22.000 rtc_s=41 vdd_mV=3000 ain3_mV=40
```

`valid=0x3f` means all five sensors plus ADC are valid. Acceleration is in g,
magnetic field in gauss, pressure hPa and light lux. The magnetometer remains
uncalibrated. ADC values are printed without interpreting a battery on E3.
Polling can repeat a sequence or skip samples; this is a latest-value reader,
not a lossless recorder. Firmware interval settings affect how often data changes.

## Offline checks

Compilation passed in 2026 for both sketches on classic ESP32, S3 and C3
with Arduino-ESP32 3.3.10, using default application partitions. Both also
compile for the specific DOIT ESP32 DEVKIT V1 profile: UART 281,476 bytes, BLE
1,099,139 bytes, each within its 1,310,720-byte limit. The generic classic
ESP32 BLE sketch uses 1,099,107 of 1,310,720 available flash bytes.
The three native decoder tests passed; the current repository suite passes all 96 tests,
with no skipped tests after removing the obsolete observation test. Details are in
`software-checks.json`. Physical DevKit V1 operation is documented separately
in the hardware results; these compilation checks alone do not establish it.

Host protocol tests:

```bash
python3 -m unittest discover -s tests -p test_esp32_packet.py
```

Compile from the repository root with Arduino CLI and core 3.3.10 installed:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 examples/esp32/f33_uart_reader
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 examples/esp32/f33_ble_reader
```

If your chosen partition layout is too small for the BLE stack, choose a larger
application partition such as **Huge APP**. Compilation profiles for
ESP32-S3 and C3 are `esp32:esp32:esp32s3` and `esp32:esp32:esp32c3`.
Board selection and USB serial options for uploading must match your actual board.

References: [Espressif's BLE client example](https://github.com/espressif/arduino-esp32/blob/3.3.10/libraries/BLE/examples/Client/Client.ino),
[UART API](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/uart.html),
and the project's [31-byte packet layout](../../docs/guide-f33.md#5-ble-interface-version-100).
