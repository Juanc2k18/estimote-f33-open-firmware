# Evidence of the macOS capture

Test of 18 November 2026, America/Lima. JSONL files: one event per line, with date and monotonic clock where applicable.

- `capture.jsonl`: first round; advertisements and three exhausted attempts against a non-connectable advertisement. Kept to show the initial selection error.
- `capture-gatt.jsonl`: corrected round, selecting the connectable advertisement by content and macOS metadata; three GATT sessions, reads and a subscription test.
- `estimote-connectability.jsonl`: native connectability metadata, filtered to FE9A.
- `run.log` and `run-gatt.log`: console output of both rounds; they do not duplicate the advertisements.
- `telemetry-decoded.json`: interpreted values and unique original telemetry bytes.
- `telemetry.csv`: the same fields for tabular analysis.
- `summary.json`: counts, times and computed ranges of this campaign.

The advertisements are the data exposed by CoreBluetooth/Bleak, which may group/cache fields and omit repetitions; they are not a full HCI capture nor an exact measurement of the transmission rate. The first general scan of nearby devices remained only in `dumps/`, excluded from Git.

To repeat from the project root:

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python bleak==3.0.1
.venv/bin/python scripts/capture_ble.py
.venv/bin/python scripts/decode_ble_capture.py
```

The script targets the observed identifier of this unit and appends events to the files. For a new campaign, change its output directory; do not mix sessions from different dates. The decoder reads both captures and rebuilds the interpreted JSON. These are experimental acquisition instruments, not a configuration tool.

No proprietary characteristics were written and no authentication, update or erase was attempted. In the second, corrected session, subscriptions were enabled via the client descriptors; no notifications were received, and in the third session the descriptors read back as `0000`.
