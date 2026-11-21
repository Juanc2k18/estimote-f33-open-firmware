# r25 · GPIO extension: tests resumed and closure verified

**Later closure:** SWD reconnected; 29 GPIOs checked, 378 valid I²C
orientations with no ACK at 0x18/19/76/77, one GPIO11-high test incomplete
with recovery without erase. [Full results](RESULTS.md).
The text below preserves the initial preparation and diagnosis.

2026. Pico USB E660C0D1C75C942F available. The nRF did not respond
at the start of the matrix at 100 kHz. pyOCD connection at 50/10 kHz and direct DP
read at 100/10 kHz also gave No ACK. No code was loaded into RAM and
no nRF GPIOs were configured; its current boot cannot be verified.

The owner clarified that he first removed physical contacts 4/5 of the Pico and
later the wires to E1/E2. The former are GP2/GP3, SWCLK/SWDIO:
this plausibly explains the missing link, pending reconnection and measurement.
Reconnect physical pin 4/GP2→A, physical 5/GP3→B, keep GND→F. Physical UART
6/GP4→E2 and 7/GP5←E1 must stay disconnected to test GPIO12/13.
Power supply: keep its previous setting and connection, with no supply on C or G.
Do not confuse this Pico with the 2×20 header of a Raspberry Pi SBC.

## Exclusions and scope

| GPIO | Actual state |
| --- | --- |
| 0/1 | 32 kHz crystal observed; excluded from driving in this campaign, not ruled out as a possible route under another configuration. |
| 12/13 | Previously reserved for the physical UART to the Pico; included in r25 only after removing E1/E2 and reconnecting SWD. |
| 21 | nRESET confirmed, UICR=21; not reconfigured here. Earlier test r18 temporarily released reset, with no I²C finding. |
| 3/4/11/22/25 | Persistently low under earlier conditions; attempts as SPI clock incomplete due to SWD loss, not negatives. Passive/OD testing is allowed, without using them as SPI clock. |
| 6/7 | r24: electrically invalid for I²C only in ZZ/HZ/ZH with/without pull; does not rule out a sensor or other conditions. |
| 9/10 | Electrical coupling observed; not excluded individually. The pair must pass independence before I²C. |
| 14/15 | Unknown function; do not assign sensor or FEM enable without continuity. They may be tested individually as bus GPIOs. Both are not driven high. |
| Rest | No confirmed sensor model; previous sweeps only rule out the specific configurations/transactions completed. |

TX/RX correction: the connector assignment changed to GPIO12/13. The scripts
use direct P0.xx registers, without Arduino translation. This does not show that the
silicon GPIO numbers are shifted; it does invalidate carrying over UWB routes.

## Preparation and resumption

`gpio_bus_matrix_r25.py`: 29 GPIOs if UART disconnected; each pin separately
without pull/pull-down/pull-up, OD low and recovery. Logs GPIO.IN, CNF,
DIR and OUT. The rest as input without pull; radio disabled; reset and hashes at
closure. No high driving and no flash/UICR. Hardware not yet run.

`i2c_candidates_r25.py`: takes the full matrix with a valid closure; tests ordered
pairs of GPIOs able to go low/high, validates independence and recovery,
and tests W/R at 0x18/0x19/0x76/0x77. Prior 2/8 control. Repeats ACK and neighbouring addresses
three times, without attempting ID automatically. No forced enables. Skips
the 14/15 pair so as not to raise both via pulls. Not yet run.

Sources copied and hashes kept. Syntax compilation of both scripts
and seven existing probe tests passed; this does not physically validate the new
scripts nor replace a known ACK control.

After reconnecting SWD and confirming E1/E2 removed:

```bash
python3 scripts/gpio_bus_matrix_r25.py --uart-disconnected --out docs/evidence/buses-r25-2026-11-19/resume
python3 scripts/i2c_candidates_r25.py --uart-disconnected --matrix docs/evidence/buses-r25-2026-11-19/resume/matrix.json --out docs/evidence/buses-r25-2026-11-19/i2c
```
