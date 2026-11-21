# F3.3 diagnostics

Status: **incomplete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- rail_on: 1
- i2c_electrical: 1
- presence: 6
- register_read: 182
- saved_control: 2
- register_write: 5
- bmp280_calibration: 1
- round: 34
- closure: 1
- error: 1

## Findings

No identifiers or clock validated under the tested conditions.

NACK does not prove absence. Does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.
