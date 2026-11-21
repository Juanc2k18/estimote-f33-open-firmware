# F3.3 diagnostics

Status: **incomplete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- rail_topology: 1
- pp_phase: 3
- i2c_electrical: 36
- i2c_address: 111
- i2c_pair_incomplete: 3
- rail_on: 2
- rail_off: 2
- closure: 1
- error: 1

## Findings

No identifiers or clock validated under the tested conditions.

NACK does not prove absence. Does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.
