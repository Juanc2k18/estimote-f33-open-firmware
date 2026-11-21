# F3.3 diagnostics

Status: **incomplete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- gpio_probe: 16
- analog: 7
- i2c_selection: 1
- i2c_electrical: 24
- i2c_address: 177
- i2c_pair_incomplete: 1
- skipped: 1
- closure: 1
- error: 1

## Findings

No identifiers or clock validated under the tested conditions.

NACK does not prove absence. Does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.
