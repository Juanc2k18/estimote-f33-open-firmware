# F3.3 diagnostics

Status: **complete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- gpio_probe: 16
- analog: 7
- i2c_selection: 1
- i2c_electrical: 156
- i2c_address: 1248
- skipped: 1
- closure: 1

## Findings

No identifiers or clock validated under the tested conditions.

A NACK does not prove absence. This does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.

## Post-run validation of the record

summary.json and every line of events.jsonl were cross-checked. Duration:
2 min 3.345 s, including closure. 16 GPIOs were examined; 13 passed the OD
matrix and their 156 oriented pairs were swept. GPIO6, GPIO7 and GPIO17 did not
pass it in this run and did not take part in the sweep.

All 156 pairs passed the electrical checks. 1,248 W NACKs are verified: eight
addresses per pair (0x18, 0x19, 0x29, 0x39, 0x50, 0x68, 0x76, 0x77), with SCL
high at sampling and SDA/SCL high after STOP. 156 of them are NACKs at 0x68;
the RTC was never read and its advance was not checked. There were no ACK
candidates and no identifiers. SPI was skipped for lack of traced pins.

VDD estimated by SAADC: 3.170–3.175 V. Six other analog sources were sampled;
those voltages do not identify sensors.

Valid closure: bootloader active, bootloader/UICR hashes equal and P0.19 as an
input without pull, temporarily in RAM. A reset restores the binary's LED19 define.
The complete status attests coverage of the selection, not discovery of sensors
nor absence of components that do not respond. Details and the record hash are
in validation.json. GND/VCC and the RTC SDA/SCL routes are still pending targeted
physical confirmation.
