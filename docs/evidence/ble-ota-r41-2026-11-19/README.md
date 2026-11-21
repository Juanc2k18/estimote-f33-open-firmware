# r41 · First BLE test: bootloader in DFU OTA ("AdaDFU") · 2026

**Objective:** check whether the RF chain (nRF, SKY66110 amplifier and
antenna) transmits and receives without knowing the amplifier control pins and without
new firmware.

**Setup:** power supply on H/F (≈3.25 V estimated; VDD 2.0 V). Pico SWD on A/B.

## Method

`scripts/ble_ota_advert.py`:
1. Writes GPREGRET=0xA8 (DFU_MAGIC_OTA_RESET of the Adafruit bootloader).
2. Performs a SYSRESETREQ reset.
3. Reads registers without halting the CPU.

It does not write to flash or UICR. The first attempt (`../ble-ota-r41a-error-2026-11-19/`)
failed before the reset because of a reset type name that does not exist in pyOCD 0.46.

## Results

**SWD (measurement)**
- Before: RADIO off in 225 of 225 samples.
- After: GPREGRET consumed (0x00) and RADIO active in 5.8 % of 1198
  samples: Tx, TxRu, Rx and RxRu.
- FREQUENCY 2 and 80 (channels 37 and 39; 38 did not show up in the sampling) and
  TXPOWER 0 dBm.

**Owner's phone** (nRF Connect, capture `nrfconnect-mobile-adadfu.png`)
- `AdaDFU` appears and **accepts a connection**.
- Services: Device Information 0x180A, GAP, GATT and Nordic Legacy DFU
  `00001530-1212-EFDE-1523-785FEABCD123`.
- The owner reports that **the BLE address is the same as that of the
  original firmware**. This fits with the address coming from FICR DEVICEADDR,
  which the erase does not change.

**Mac** (`scripts/ble_scan_read.py` with bleak 3.1.0 and CoreBluetooth; data in
`../ble-mac-r41-2026-11-19/`)
- 80 valid advertisements in 10 s; RSSI from −69 to −53 dBm, median −59 dBm.
  Distance not stated; 2 values of 127 ("not available" marker) were discarded.
- Connection succeeded and Device Information was read:
  - manufacturer "Estimote F3.3 (reutilizado)"
  - model "Estimote F3.3"
  - firmware "0.11.0 s132 6.1.1"
- From the agent process, Python aborts (code 134) because it has no
  Bluetooth permission. From the terminal tab it works.

## Interpretation

- **The radio transmits and receives through the antenna** without controlling the
  amplifier. With nothing on its control pins, the SKY66110 passes the
  signal through: it sits in a mode that works (probably bypass, not yet
  identified). Until range is measured it is unknown whether power is lost.
- **LED:** the owner sees an LED blinking fast in this mode. The
  bootloader drives it via **PWM0 with PSEL.OUT[0] = P0.17 and PSEL.OUT[1] = P0.19**,
  so the OUT register stays at 0 even though IN toggles. Hypothesis, not
  confirmed: the LED is on **P0.17**. That would explain the r35 reading (17
  stays at 0 even though it is driven high at VDD = 3.1 V): an LED to GND clamps the
  pin voltage below the "1" threshold. With VDD = 2 V, IN17 does reach 1. P0.19 is
  the RTC IRQ (open drain, inactive with OUT = 1). It remains to be determined which of the
  two pins lights the LED.

**State at the end:** the bootloader keeps advertising `AdaDFU` until the next
reset or power-off. After that it returns to UART DFU.
