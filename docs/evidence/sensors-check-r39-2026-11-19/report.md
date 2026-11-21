# F3.3 diagnostics

Status: **complete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- rail_on: 1
- i2c_electrical: 1
- presence: 6
- register_read: 38
- saved_control: 2
- register_write: 12
- bmp280_calibration: 1
- round: 2
- restore: 1
- verdict: 1
- closure: 1

## Findings

No identifiers or clock validated under the tested conditions.

A NACK does not prove absence. This does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.
