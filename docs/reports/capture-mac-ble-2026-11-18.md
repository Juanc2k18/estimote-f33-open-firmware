# Direct BLE capture from the Mac

2026, America/Lima. Main campaign: 14:03:46–14:08:11. Tests run from this Mac against the Estimote. Python 3.12.12, Bleak 3.0.1 and CoreBluetooth; system authorization granted. The owner confirmed that they closed the phone scanner and brought the beacon closer.

**Result: telemetry received and decoded; three successful GATT connections. No authenticated configuration, firmware, UART or SWD access was obtained.**

## Evidence and scope

106 advertisement events filtered to Estimote FE9A and 12 distinct payloads were saved, with RSSI from −77 to −45 dBm. The data are the fields exposed by CoreBluetooth, not complete HCI packets or an exact measurement of the advertising rate.

- [Evidence index and reproduction](../evidence/mac-ble-2026-11-18/README.md).
- [Computed summary](../evidence/mac-ble-2026-11-18/summary.json).
- [Initial events](../evidence/mac-ble-2026-11-18/capture.jsonl) and [corrected GATT sessions](../evidence/mac-ble-2026-11-18/capture-gatt.jsonl).
- [Decoded telemetry](../evidence/mac-ble-2026-11-18/telemetry-decoded.json) and [CSV](../evidence/mac-ble-2026-11-18/telemetry.csv).

## Identification and connectability

The advertisements share the identifier prefix `bb6b7d16b94a4e26`; the long frames contain `bb6b7d16b94a4e265cb6b304024bd423`. Their data and the GATT profile were correlated with the phone evidence. The physical unit was not power-cycled as an additional identity test.

macOS presents different identifiers for the observed advertisements. The first target detected mainly emitted non-connectable frames: three attempts ended in a 12 s timeout. Inspecting `kCBAdvDataIsConnectable` distinguished:

| Observed CoreBluetooth identifier | FE9A frame | Connectable |
| --- | --- | --- |
| 1EFECAEF-655D-D8F8-CF40-BB95DC87DD0F | 0x11… | No |
| DD75C07D-F9F6-C8A8-415E-8820F04DF5EB | 0x22… | No |
| 98864573-BACF-56A9-85C1-88958FA96AC9 | 0x00… | Yes |

The corrected round selected the connectable advertisement by content and metadata, not by proximity or by a fixed UUID. The macOS UUIDs are not the MACs that Android sees. [Bleak: macOS backend](https://bleak.readthedocs.io/en/latest/backends/macos.html).

Examples of retained payloads:

```text
00bb6b7d16b94a4e265cb6b304024bd423946440
11bb6b7d16b94a4e265cb6b304024bd423c203
22bb6b7d16b94a4e260005fe42004af899428801
22bb6b7d16b94a4e26010000005ea78290f00401
```

The final fields of the 0x00/0x11 frames are not interpreted by guesswork, and no firmware version is attributed to those bytes.

## GATT reads and subscriptions

In the three successful connections, CoreBluetooth exposed two proprietary services and five characteristics, matching the proprietary subset observed on Android:

| Service | Characteristic | Properties |
| --- | --- | --- |
| 6c372000… | 6c372001… | Write Without Response |
| 6c372000… | 6c372002… | Write, Notify |
| 6c372000… | 6c372004… | Read |
| 6c371000… | 6c371002… | Notify |
| 6c371000… | 6c371001… | Write, Write Without Response |

Base: `xxxxxxxx-d2cc-11e4-9a1f-0002a5d5c51b`. Observed MTU: 23. In this campaign macOS did not expose the standard 0x1800/0x1801 services that do appear on Android; this is not interpreted as absence in the firmware. Their earlier readings remain in the [phone diagnosis](diagnosis-ble-2026-11-18.md).

- `6c372004…`: three successful reads, always **`01 00`**. Meaning not identified; it does not show firmware 1.0 or an active UART.
- Client descriptors 0x2902, handles 17 and 23: `0000` in the first and third sessions.
- Second session: both subscriptions accepted; **zero notifications received** during the observed window. No application payloads were written to request responses.

| Session | Services ready | Observed disconnection | Time since services ready |
| --- | --- | --- | --- |
| 1, reads | 14:06:33.954 | 14:06:42.807 | 8.853 s |
| 2, reads and subscriptions | 14:07:00.685 | 14:07:09.660 | 8.975 s |
| 3, reads | 14:07:26.215 | 14:07:35.193 | 8.978 s |

These times start after link establishment and service discovery; they are not the full link duration. The callback does not include the HCI reason here. The disconnection remains consistent with the documented Estimote authorization deadline, and subscribing did not prevent it. [Official Estimote explanation](https://d3lgd0yxjqbzck.cloudfront.net/managing-beacons/connecting-to-beacons/).

## Telemetry available without connecting

Interpretation according to the [public Estimote format](https://github.com/Estimote/estimote-specs/blob/master/estimote-telemetry.js), protocol 2, subframes A/B. These are reported fields, without independent calibration:

| Field | Observed values |
| --- | --- |
| Temperature | 36.125–37.8125 °C |
| Absolute pressure | 100411.93–100422.09 Pa, approximately 1004.12–1004.22 hPa |
| Light | 322.56–345.60 lx |
| Acceleration, first sample X/Y/Z | +0.079 / −0.031 / +1.039 g |
| Activity, B subframes | 679–855 seconds |
| Normalized magnetic field | 0 / 0 / 0 |
| Reported battery | 316 mV and 1 % |
| Flags, first A subframe | No firmware error; clock error indicated |
| GPIO, first A subframe | Four bits reported high |

The GPIO bits do not identify physical pins or confirm UART. The battery field does not measure the 5 V input; with external power, its relevance requires checking the circuit. The magnetic zeros do not show a missing sensor. Nor does the clock flag allow diagnosing a faulty component.

## Changes and limits

Only the temporary subscription of the two client descriptors was enabled, in addition to scanning/connecting/reading. No proprietary characteristics were written, no authentication was attempted, no firmware was changed and no memory was erased. The third session read both descriptors again as `0000`. At the end all sessions were disconnected and scans stopped.

The presence and sensor path via advertisements already has local evidence. Configuring GPIO/UART or recovering protected data still requires Estimote authorization or physical SWD work. The list of recovered data is limited to what was broadcast and to the accessible reads; it is not a dump of the device's entire memory or configuration.
