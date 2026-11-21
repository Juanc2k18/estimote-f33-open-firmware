# F3.3 diagnostics

Status: **incomplete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- rail_on: 1
- i2c_electrical: 1
- register_read: 1
- restore: 1
- closure: 1
- error: 1

## Findings

No identifiers or clock validated under the tested conditions.

A NACK does not prove absence. This does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.
