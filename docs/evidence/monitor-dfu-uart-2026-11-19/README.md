# UART DFU monitor · 2026

**Later update:** with the r15 setup confirmed, the unit was validated: one
ping and 20/20 ACK from the monitor, with no failures. See [unit-20261119T113146-0500](unit-20261119T113146-0500/README.md).
The pending-setup sections below describe the initial software phase.

Objective: periodically observe the UART transport of the Adafruit bootloader
0.11.0 with requests of unknown type `0x7f`, without loading an application.
Implementation: `scripts/dfu_ping.py`, Python 3 and the standard library.

## Physical state and scope

**The real UART was not opened or transmitted to in this run.** The Pico is
present: USB `Debugprobe on Pico (CMSIS-DAP)`, serial `E660C0D1C75C942F`,
observed port `/dev/cu.usbmodem21102` (different from the historical r15 one).
USB enumeration is a host measurement; it does not attest to electrical connections.

The last setup documented in AGENTS.md/r26 has E/SWO→GP5/pin 7,
E1/E2 removed and GP4/pin 6 free; the documented power supply remains at 6 V H/F,
C without supply and C/F around 2 V (earlier report and SAADC, not a new measurement).
It does not match r15. Confirmation of the current setup was requested from the owner;
without confirmation or a new measurement, transmission is postponed.

Pending physical action, **with power removed**:

1. Remove E/SWO→GP5. Connect GP4/pin 6 TX→E2/RX of the beacon and
   GP5/pin 7 RX←E1/TX of the beacon. Keep common GND F.
2. Disconnect H, E3 and batteries; use a single regulated 3.3 V power supply on C/F.
   H is not VDD. Verify C/F with an instrument and check E1/E2 idle
   before transmitting. The script's 50 ms listen does not measure voltage.
3. Confirm setup and bootloader in serial DFU. No monitor reset is needed;
   an external reset reconfigures P0.19 as an output via the r29 binary.

Flash, UICR, GPIO, reset and power supply were not altered. There is no new
beacon log; `software-pty.jsonl` corresponds exclusively to a PTY emulation.

## Software validation

The false success of the echo in the original script was reproduced via the real CLI; the
positive fixture is the literal r15 capture:

- TX `c0 d1 4e 00 e1 7f 00 00 00 aa a8 c0`
- RX `c0 10 00 00 f0 c0`

`red-task1.txt`: 6 assertion failures (5 methods, with subcases), including echo.
`green-task1.txt`: 5 methods pass after validating complete ACKs.
`red-task2.txt`: 6 tests fail before implementing continuous mode.
`green-task2.txt`: 12 methods pass. The final suite is kept in `software-tests.txt`: **21 Python methods, 0 failures**
(14 for the monitor and 7 existing).

Checked: fragmentation, echo+ACK, checksum/type/flags/length/sequence,
truncation, silence, invalid SLIP escape and frame overflow; wrap-around
7→0, duplicate ACKs, lost ACK, previous session, counting, missing port,
disconnection/reappearance on the same path and Ctrl-C with an attempt in flight.
`software-pty.jsonl` keeps 20 attempts and 20 simulated ACKs; its console is in
`software-pty-console.txt`. It does not demonstrate operation of the real wiring.
The existing C test `tests/spi_classification.c` also compiles and runs
with exit 0. `hardware-enumeration.json` stores the USB enumeration without opening
the port. The independent review found two important issues:
B0 accepted and ACK overwritten by a disconnection during the wait. Both were
reproduced (`red-review.txt`) and fixed (`green-review.txt`), with
additional regressions; baud rates <=0 are rejected before opening the device.

## Transport and log contract

Checked against the local checkout of the bootloader, HEAD
`c67f0bcf0fa8e841426335b1bbde91cda6ca1f50`, used in r14:

- [hci_transport.c](https://github.com/adafruit/Adafruit_nRF52_Bootloader/blob/c67f0bcf0fa8e841426335b1bbde91cda6ca1f50/lib/sdk/components/libraries/hci/hci_transport.c):
  `ack_transmit`, `rx_vendor_specific_pkt_type_handle`, `packet_number_expected_inc`.
- [dfu_transport_serial.c](https://github.com/adafruit/Adafruit_nRF52_Bootloader/blob/c67f0bcf0fa8e841426335b1bbde91cda6ca1f50/lib/sdk11/components/libraries/bootloader_dfu/dfu_transport_serial.c):
  unknown type with no implementation, release of the processed element.

ACK: exactly four decoded bytes, type 0, length 0, the ACK's flags and
TX sequence zero, header sum modulo 256 equal to zero.
The advertised number is the next expected sequence. An ACK matching
`(sequence+1)%8` confirms the transport; another structurally valid ACK
produces `resync` and prepares the advertised sequence for the next attempt.
`resync` does not count as success. On silence the same sequence is retransmitted.
An ACK of a retransmission may confirm a previously accepted request;
this 3-bit protocol does not attest new execution nor allow distinguishing an
arbitrarily late ACK after a full wrap-around. The bytes
received before each TX are kept separately in `idle_rx_hex`, without using them to confirm samples.

A single open descriptor and a single request in flight are kept. Timeouts use a
monotonic clock; `--interval` is the pause after each attempt (the cadence
includes an initial 50 ms listen and up to `--timeout`, 1 s by default).
The parser keeps fragments between reads during the attempt, limits each
frame to 4096 bytes and discards fragments from before the next TX.

Each JSONL line has local ISO time with zone, port, baud rate, sequence,
TX/RX hex, prior listen, result, decoded events and latency of the
first matching ACK if any. Results: `ack`, `resync`, `echo`, `invalid`,
`silence`, `port_absent`, `access_error`, `interrupted`.
The file is written and flushed after each attempt, even on failure or Ctrl-C.
The summary counts those same lines. After processing a block with a matching
ACK, the sample ends; a later disconnection is observed on the
next attempt, without erasing the confirmed ACK. A device error closes the descriptor;
only the chosen path is reopened, without searching for another port. If macOS renumbers the Pico,
stop and consciously select the new path.

`--log` creates an exclusive file and its parent directories; reusing
an existing log is rejected before opening the port. Without `--log`, there is only the console.
Exit: 0 if there was at least one ACK, 1 if there was no ACK, 2 invalid arguments/log,
130 on interruption. An exit 0 does not imply absence of losses:
check the summary and the failure lines.

## Commands after confirming r15

From the project root, set the real path and use new logs:

```sh
PUERTO=/dev/cu.usbmodem21102
python3 scripts/dfu_ping.py "$PUERTO" 115200
python3 scripts/dfu_ping.py "$PUERTO" 115200 --watch --interval 5 --count 20 \
  --log docs/evidence/monitor-dfu-uart-2026-11-19/beacon-bounded.jsonl
python3 scripts/dfu_ping.py "$PUERTO" 115200 --watch --interval 5 \
  --log docs/evidence/monitor-dfu-uart-2026-11-19/beacon-live.jsonl
```

The last command stays in the foreground until Ctrl-C. **Not run on the unit**;
the `beacon-*.jsonl` files are proposed destinations, not yet existing.

To repeat the software without hardware:

```sh
python3 -m unittest discover -s tests -p test_dfu_ping.py -v
python3 -m unittest discover -s tests -v
clang -Wall -Wextra -Werror -o /tmp/estimote-monitor-spi-test tests/spi_classification.c
/tmp/estimote-monitor-spi-test
```
