# ESP32 readers implementation plan · 2026

Goal: two small Arduino examples for the existing F3.3 application: UART JSON
passthrough and BLE GATT reads, displayed on the USB serial monitor.

Architecture: independent sketch folders under `examples/esp32/`; BLE has a
portable, explicitly little-endian packet decoder. No DFU or configuration writes.
Arduino-ESP32 3.3.10 is installed locally and is the compilation target.

Constraints: user specifies E1–E4 only and 3.3 V on E3. The ESP32 model is not
yet known. UART pins are configurable and GPIO16/17 are examples for a classic
ESP32 board with those pins available, not confirmed wiring for the owner's board.
No hardware connections or uploads are performed. Other repository edits remain.

- [x] Test the BLE decoder against existing Python packet fixtures, signed and
  unsigned boundaries, bad length/version and absent validity bits; observe failure.
- [x] Implement UART bounded line forwarding with overflow recovery and active TX.
- [x] Implement BLE active scanning, ambiguity rejection or MAC selection, periodic
  reads, packet validation and reconnect. Use no unbounded client allocation.
- [x] Compile both sketches for classic ESP32, S3 and C3; run decoder tests.
- [x] Document wiring prerequisites, units and untested hardware status; update
  the consolidated guide and checksums.

Review focus: split/truncated UART lines; partial BLE packets; invalid sensor
fields; multiple beacons; disconnect/reconnect; unsupported chips/pins; electrical
margin when E3=3.3 V gives VDD near 3.0 V.

Verification: six chip/sketch compilations passed; decoder tests 3/3; full suite 97 cases, 96 passed and one historical skip. Independent review found no important issues. Physical tests remain pending; no board upload or wiring operation performed.

Follow-up: owner identifies ESP32 DevKit V1. Keep classic UART GPIO16 RX / GPIO17 TX; select FQBN esp32:esp32:esp32doit-devkit-v1. Hardware testing and uploads remain pending.

Hardware follow-up (2026): owner reports both sketches working on DevKit V1; screenshots show UART JSON and BLE valid=0x3f with Arduino IDE ESP32 Dev Module profile. See docs/evidence/esp32-readers-2026/README.md. No new agent hardware operation performed.

Test cleanup (2026): removed tests/test_board_observe.py at the owner's request because scripts/board_observe.py is absent. The remaining 96 tests pass with no omissions; this does not establish what firmware the obsolete test originally targeted.
