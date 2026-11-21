# F3.3 diagnostics

Status: **incomplete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- counter_control: 2
- rail_topology: 1
- phase: 4
- frequency: 92
- slow_pull: 8
- analog: 4
- gpio_probe: 84
- matrix: 4
- rail_on: 3
- matrix_diff: 3
- rail_check_end: 3
- rail_off: 3
- i2c_electrical: 30
- i2c_address: 2
- i2c_pair_incomplete: 2
- skipped: 1
- closure: 1
- error: 1

## Findings

No identifiers or clock validated under the tested conditions.

A NACK does not prove absence. This does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.

## Rail, frequency and LFCLK

- Topology: single node=False; idle with pull-down {6: 0, 7: 0, 14: 0, 15: 0}
- Counter control GPIO19: 0/20 valid=False
- Counter control GPIO18: 20/20 valid=True
- Edges rail_off GPIO17: 9 (~35.4 Hz)
- Edges rail_14 GPIO17: 9 (~35.5 Hz)
- Edges rail_15 GPIO10: 1 (~3.9 Hz)
- Edges rail_15 GPIO17: 9 (~35.4 Hz)
- Edges rail_67 GPIO17: 9 (~35.4 Hz)
- Slow pull rail_off GPIO17: up [0, 0, 0] down [0, 0, 0]
- Slow pull rail_off GPIO19: up [0, 0, 0] down [0, 0, 0]
- Slow pull rail_14 GPIO17: up [0, 1, 0] down [1, 0, 0]
- Slow pull rail_14 GPIO19: up [0, 0, 0] down [0, 0, 0]
- Slow pull rail_15 GPIO17: up [0, 0, 0] down [1, 0, 0]
- Slow pull rail_15 GPIO19: up [0, 0, 0] down [0, 0, 0]
- Slow pull rail_67 GPIO17: up [1, 0, 1] down [0, 0, 0]
- Slow pull rail_67 GPIO19: up [0, 0, 0] down [0, 0, 0]
- Matrix rail_14: new with rail []; lost []; pairs 0
- Matrix rail_15: new with rail [17]; lost []; pairs 30
- Matrix rail_67: new with rail []; lost []; pairs 0
