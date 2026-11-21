# r25 · Extended GPIOs, targeted I²C and enable tests

2026, America/Lima. **Physical tests resumed and closed**. GPIO12/13 are
included after removing the Pico UART; there is no new sensor candidate.
No GPIO is universally ruled out as a sensor connection by these tests.

## Setup and check

The owner confirmed reconnection of the Pico's physical contacts 4/GP2→A and
5/GP3→B, keeping GND→F, and removal of UART E1/E2 (physical contacts
6/GP4 and 7/GP5). This restored SWD after the initial No ACKs.
The power supply report is still 6 V H/F, C without supply and G free; its
setting and wiring were not changed by software. There was no independent H/F measurement.

SWD at 100 kHz responded: PART=0x52832, NFCPINS=FFFFFFFE, PSELRESET=[21,21],
initial PC=0x750EC in the bootloader. A RAM loop was run with interrupts and
radio disabled, without programming flash/UICR. The final ADC reused
`sensor_diagnostics.py` (its SWD configured at 4 MHz): VDD=1.992480 V and
P0.05/AIN3 without pull=1.005029 V mean, four samples after calibration.
Internal reference and gain 1/6: these are nRF estimates, not a measurement of H/F.

## 1. Individual matrix: 29 GPIOs

Each GPIO separately without pull, with pull-down and with pull-up; then OUT=0 and
DIR output for 10 ms, release to input with pull-up for 50 ms.
The other test GPIOs remained as inputs without pull. The full GPIO.IN,
PIN_CNF, DIR and OUT were saved; in all 29 records OUT[p]=0,
DIR[p]=1 during the low and DIR[p]=0 on release were checked. The reading comes from IN and not
only from the OUT latch. No high was forced in this phase.

| GPIO | No pull / PD / PU | OD low | Recovers high | Selection for I²C r25 |
| --- | --- | --- | --- | --- |
| P0.02 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.03 | 0/0/0 | yes | no | not under this condition |
| P0.04 | 0/0/0 | yes | no | not under this condition |
| P0.05 | 1/1/0 | yes | no | not under this condition |
| P0.06 | 0/0/0 | yes | no | not under this condition |
| P0.07 | 0/0/0 | yes | no | not under this condition |
| P0.08 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.09 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.10 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.11 | 0/0/0 | yes | no | not under this condition |
| P0.12 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.13 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.14 | 0/0/0 | yes | no | not under this condition |
| P0.15 | 0/0/0 | yes | no | not under this condition |
| P0.16 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.17 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.18 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.19 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.20 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.22 | 0/0/0 | yes | no | not under this condition |
| P0.23 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.24 | 1/0/1 | yes | yes | yes, pending pair validity |
| P0.25 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.26 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.27 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.28 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.29 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.30 | 0/0/1 | yes | yes | yes, pending pair validity |
| P0.31 | 0/0/1 | yes | yes | yes, pending pair validity |

**20 pins allow low and individual high recovery:**
2,8,9,10,12,13,16,17,18,19,20,23,24,25,26,27,28,29,30,31.
The other nine (3,4,5,6,7,11,14,15,22) did not recover high with the internal
pull-up in this configuration. They are not interpreted as absent sensors nor
as direct connections to ground. **25 recovers high**, correcting any
reading of "stuck low" as a universal property of that pin.

0/1 were left undriven because of the observed 32 kHz crystal; 21 was kept
as nRESET (UICR was not changed). These are reservations of this test, not an
identification of sensor routes. 12/13 were not skipped because of the bootloader
header, nor 17/19/20/22 because of their LED/button names in that header.

## 2. I²C W and R in 380 orientations

All ordered pairs among the 20 pins above were tested:
380 orientations. Internal pull-ups only on SDA/SCL; all other GPIOs
as inputs without pull, no forced enables. Radio STATE=0 checked at the
start. Before each pair, high idle, individual low with the other
line high and recovery of both high were verified; limit 50 ms. The 9/10 pair failed
in both directions due to dragging of the other line; **378 valid orientations**.

On each valid pair, 0x18/0x19 (LIS2DH12 candidate) and 0x76/0x77
(BMP280 candidate) were probed with W and R. W=START+address/W+ninth pulse+STOP, with no
register or data. Each SCL high is validated via IN, including the ACK sampling;
after STOP, high idle is required. R would only have read a byte if it had received ACK.

| Address | W | R |
| --- | --- | --- |
| 0x18 | 378 NACK | 378 NACK |
| 0x19 | 378 NACK | 378 NACK |
| 0x76 | 378 NACK | 378 NACK |
| 0x77 | 378 NACK | 378 NACK |

**3,024 NACK**, 0 ACK, 0 clock stuck, 0 bus busy and 0 timeout in the
probes of valid pairs. Initial control SDA2/SCL8: electrical validity and eight
additional NACKs (four addresses × W/R), valid STOP. There was no address
that justified repeating ACK or attempting an ID read. **A known physical positive
control is missing**; the seven software tests include simulated
ACK, which does not replace that device.

**Scope:** there was no response at those four addresses, with these 20 GPIOs,
pulls and state of the other GPIOs. It was not a sweep of all addresses.
It does not cover other power/enable conditions, addresses or protocols and does not
show that LIS2DH12/BMP280 are absent. It includes, for the first time in this
campaign, driving GPIO12/13 with the Pico UART removed. P0.xx is used
directly through registers, without Arduino numbering or carrying over UWB routes.

No SPI was performed and 3/4/11/22/25 were not reused as **SPI clocks**. GPIO25
did pass the individual/pair validation and took part in the r25 I²C probes.

## 3. A single GPIO high: partial result and limited repetition

`gpio_enable_matrix_r25.py`: all other GPIOs as inputs without pull,
one output high at a time; minimum wait 10 ms plus SWD latencies and 50 ms after
release. Logging of IN, CNF, DIR and OUT. 14/15 were not driven simultaneously
as outputs; the DIR readings confirm it in all complete records.

First sequence, first pass: nine complete tests were saved, GPIO
2,3,4,5,6,7,8,9,10. **3 and 4 reached a high logic reading when driven**,
even though the pull-up did not raise them: they should not be treated as impossible to
drive high nor as confirmed ground. When 6 was driven high, 7 went from 0 to 1;
when 9 was driven high, 10 went from 0 to 1. No functions are assigned from those effects.

The next operation attempted GPIO11 high: the GPIO.IN read failed with
Unexpected ACK 0 / No ACK. The last complete test is GPIO10. The actual
level of 11 was not confirmed and the cause of the loss is not demonstrated. The
`finally` also failed when trying to halt the core. **Incomplete sequence**, not a negative
nor a repeatable test of 11. GPIO22/25 were not reached in that sequence.

Recovery: `pyocd reset -t nrf52832 -f 10000` ended with exit 0. Afterwards,
read DP IDR=2BA01477, CTRL-AP IDR=02880000, APPROTECTSTATUS=1 and a pulse only
of CTRL-AP RESET, without ERASEALL. Later reading: PC=0x779FC, P11.CNF=2,
RESETREAS=4, bootloader/UICR with the same hashes. There is no evidence of erase.

A second sequence was completed with **51 tests**, three passes of the 17
remaining selected GPIOs: 12,13,14,15,16,17,18,19,20,23,24,26,27,28,29,30,31.
No SWD loss; radio disabled and normal closure. 11 was not retried and
22/25 were not included as high outputs in this continuation. The changes in 12/13
were neither selective nor constant between passes. Several lines were already high
in the baseline sample or retained charge/level after release; that persistence
**limits** the comparisons and does not allow claiming that a GPIO is not an enable.
No new enable with a selective and reproducible effect was identified.

## 4. Final 6/7 control and closure

`i2c_trial_r24.py` was reused in full after these tests and the ADC.
Control 2/8: **112 NACK W and 112 NACK R**. In the twelve 6/7 cases (ZZ, HZ, ZH;
both orientations; without/with internal pull-up), all electrically invalid:
ZZ=0/0 without recovery; HZ/ZH=1/1 and they cannot be pulled low individually.
Same result as r24. No addresses were tested on the invalid 6/7.
Full table and raw trace in `post-enables-6-7/`.

GPIOs of that test released as input without pull before the reset. Final
closure: PC **0x779fc** inside the bootloader, radio=0, PSELRESET=[21,21],
core resumed. Bootloader and UICR with SHA-256 equal to the start:

- Bootloader: `589c61bd3a2cbecdf8aaa765991510c9dca5f1a279c7b8d85877321f049fcedc`
- UICR: `82ea7e308fcc09c6dd9dee4d9686e9e261f4848d49d6c540f9b1ea670dbc7ad7`

UART E1/E2 remains removed according to the confirmed setup. Power supply unmodified.
There are no validated sensor candidates. The first high-output matrix remains
incomplete on reaching 11, recovered afterwards; the other tests
listed completed their closure. Continuity and actual power of the chips still need
to be characterized to choose bus/CS/clock without assuming the UWB schematic.

## Evidence and reproduction

- `resume/matrix.json`: raw data of the 29 GPIOs and closure.
- `resume/matrix-summary.json`, `matrix-table.md`, `parameters.json`, `source/`.
- `i2c/probes.jsonl`, `i2c/summary.json`: probes and controls per pair/address.
- `enables/enable.jsonl`, `enables.log`: incomplete first sequence and traceback.
- `recovery-*.json/log`, `after-recovery.json`: recovery without erase.
- `remaining-enables/`: three complete passes and closure.
- `adc-final.log`, `post-enables-6-7/`, `final.json`: final controls and closure.
- `verification.json`, `SHA256SUMS`: verification and code versions without commits.

The source copies identify the code that was run. There is no external waveform
capture; the readings are GPIO.IN and nRF registers. The final r24
SWD trace is in `post-enables-6-7/gpio-trace.jsonl`.
