# F3.3 diagnostics

Status: **complete**.

## Recorded tests

- parameters: 1
- baseline: 1
- active_start: 1
- counter_control: 2
- rail_topology: 1
- phase: 1
- frequency: 23
- lfclk: 1
- analog: 1
- gpio_probe: 21
- matrix: 1
- skipped: 1
- closure: 1

## Findings

No identifiers or clock validated under the tested conditions.

A NACK does not prove absence. This does not physically locate D or pins without continuity.
See events.jsonl for frames, electrical states and closure.

## Rail, frequency and LFCLK

- Topology: single node=False; idle with pull-down {6: 0, 7: 0, 14: 0, 15: 0}
- Counter control GPIO19: 0/20 valid=False
- Counter control GPIO18: 20/20 valid=True
- LFCLK rail_off: consistent with a passive crystal: no edges on XL1 and bypass without 32 kHz
- Edges rail_off GPIO17: 9 (~35.3 Hz)
