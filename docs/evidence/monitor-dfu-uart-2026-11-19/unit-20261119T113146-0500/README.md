# UART DFU physical validation · 2026

Goal: check the bootloader's UART transport and the monitor's continuous mode.

## Connections and power

Owner confirmation: single 3.3 V power supply on C/F; H, E3 and batteries
disconnected. GP4/physical pin 6→E2, GP5/physical pin 7←E1 and common GND F.
Pad E/SWO removed. The owner indicates A→4 and B→5; according to the physical
contacts of the documented r12/r15 setup, these correspond to GP2/SWCLK and GP3/SWDIO.
Those SWD wires were to be left in place; GP4/GP5 are not used for A/B.
The voltage was not measured again with a host instrument; power is as
reported by the owner, the UART response was measured by software.

Port selected in this session: `/dev/cu.usbmodem21202`, Pico Debugprobe
serial `E660C0D1C75C942F` (enumerated in the prior check). 115200 baud,
8N1, no flow control. `scripts/dfu_ping.py`, Python 3 standard library only.
50 ms of prior listening. 1 s timeout. No reset, SWD, GPIO changes,
flash or UICR were performed by this test.

## Single sample

Record: `single.jsonl`; console: `single.console.txt`.
Exit 0, one sample and one matching ACK:

- TX: `c0 d1 4e 00 e1 7f 00 00 00 aa a8 c0`
- RX: `c0 10 00 00 f0 c0`
- Sequence 1, next expected ACK 2; latency 3.226 ms.

The TX/RX pair matches r15 exactly. It attests the UART DFU transport,
not an application upload nor restoration of the original firmware.

## Bounded run

Command: `python3 scripts/dfu_ping.py /dev/cu.usbmodem21202 115200 --watch --interval 5 --count 20 --log bounded.jsonl`
(the run used the absolute path of the record in this directory).
Record `bounded.jsonl` and console `bounded.console.txt`; final result in
`verification.json`, written after finishing and cross-checking the frames.

The script starts each process at sequence 1. The first ACK of a new session
may correspond to a retransmission; the transport does not attest a new
execution of the request. The only DFU type sent is 0x7f.

Final result: **20 attempts, 20 ACKs, 0 failures and 0 resynchronizations**.
All 20 raw responses match the expected ACKs; sequences 7→0
and JSONL summary verified. Min/mean/max latency: 3.104/3.918/4.54 ms.
The run ended normally; no continuous monitor is left open.
