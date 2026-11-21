# 1.0.0 · UART with a host on E1–E4 · 2026

Goal: validate on the board the 1.0.0 application with UART on E1/E2. The
checks cover the JSON data, the commands, host detection through E2, the
upload via the `dfu` command and the rescue by cutting E3, and that use without a host does not
draw more current.

Design: specification and plan for the UART host, 2026 (internal planning
notes, not published). Tasks 1–4 were
implemented by Codex. Here they were audited and five risks were fixed (see
"Audit").

## Firmware

`firmware/ble-sensors/release/`, built from `build/`, and the same package in
all tests:

| File | SHA-256 |
|---|---|
| `f33-ble-sensores-1.0.0.hex` | `26469daa5f3896900c521b5fcf9b11f9131f35baa50cea1eeb0b23f31e727d14` |
| `f33-ble-sensores-1.0.0.zip` | `0c084ae8c5a8e940f72ba05de5810f964f75518620832797142cf66aaabaf01a` |

On 2026 the build target was renamed to `f33-ble-sensors` and rebuilt from the
English-commented sources. The `.hex` is byte-identical (same SHA-256 as above) and the
DFU package carries the same `.bin`/`.dat`; only file names inside the `.zip` changed, so
the published `f33-ble-sensors-1.0.0.zip` has SHA-256
`1ba16459435ccb8dda05547bfb4f829e173989ecb2a2dd057497a4778e2b0045`. The firmware on the
board does not need reflashing.

The application size is 9244 B: text 9160, data 60, bss 952. It replaces
the 1.0.0 without UART from commit `406e0e1`, which was never published.

## Setups (reported by the owner)

- **Without host:** power supply at 6 V on H/F and Pico disconnected.
- **With host**, from step 3:
  - H disconnected;
  - power supply at **3.7 V** on E3 (+) and E4 (−);
  - Pico debugprobe as a UART bridge: GP4 (pin 6) → E2, GP5 (pin 7) ← E1 and
    GND → E4;
  - Pico on `/dev/cu.usbmodem21102` (yesterday it was `…1131202`).

## Results

| Step | Test | Result | Folder |
|---|---|---|---|
| 1 | BLE OTA of the new 1.0.0 (without host) | 9244 B in 10.0 s (1012 B/s); advertises `1.0.0`; six valid sensors; boots with the new `Reset_Handler` (`__START=main`) | `ota-1.0.0/`, `mac-after-ota/` |
| 2 | Current without host, multimeter in series with H | See "Current draw" | — |
| 4 | Data over UART, 20 s | 21 lines, one per second; VDD 3.357–3.389 V; light ≈106.6 lx (daytime; at night, 0 lx) | `uart-data/` |
| 4 | UART and BLE simultaneously | 10 common samples (#22–#31): identical except for pressure, 0.01 hPa in 5 of them, because the JSON gives it in whole Pa (anticipated in the design). The extra measurement #20 is the one from the BLE connection, which now also goes out over UART. | `mac-simultaneous/` |
| 5 | Commands | `ver` → `{"ok":"ver","fw":"1.0.0"}`; `read` → `ok` and an extra measurement 30 ms later; `int 0` → `{"err":"range"}`; `int 5` → no measurements for 4 s; `int 1` → every 1 s again. Responses in ≈4 ms. | `uart-commands/` |
| 6 | Disconnection: the owner releases GP4→E2 for ≈20 s and reconnects it | Last line #219 (12:19:09); first after reconnecting #240 (12:19:30). The board kept measuring (continuous seq) and came back in ≤1 s, with no garbage. | `uart-disconnect/` |
| 7 | `uart_dfu.py --command` (without cutting power) | 1st attempt: the board received `dfu` and restarted, but the script did not recognize the ACK (see "Issues"). 2nd attempt, with the fixed script: ACK in 13 ms, bootloader caught at the first packet, nrfutil 3.1 s, `status: ok`; the app came back | `uart-dfu-command-fail-ack/`, `uart-dfu-command/`, `uart-after-dfu-command/` |
| 8 | Rescue: the owner cuts and restores E3 with `uart_dfu.py` waiting | Caught at power-up (696 attempts in 23.4 s of waiting); nrfutil 3.0 s; `status: ok`; the app came back | `uart-rescue/`, `uart-after-rescue/` |

| 9 | **E3 at 3.3 V** (lab power supply; the owner set it, the rest of the setup unchanged) | VDD **2.985–3.001 V**; 26 lines with all six sensors valid; `ver` and `read` OK; simultaneous BLE with version `1.0.0`; upload via `dfu` with the `.zip` from `release/`: caught at the first packet, nrfutil 3.0 s, `status: ok`, the app came back | `uart-e3-3v3/`, `mac-e3-3v3/`, `uart-dfu-command-e3-3v3/`, `uart-after-dfu-e3-3v3/` |

With E3 at 3.3 V, VDD ≈ 3.0 V, so the E3→VDD drop is ≈0.3 V, the same
as at 3.7 V. The Pico transmits at 3.3 V, right at the nRF's VDD + 0.3 V limit,
and its RX receives ≈3.0 V, above its high threshold. It was tested with a lab
power supply, not with a host's 3.3 V pin. A pin like that has to supply the
boot peak, ≈4 mA, and the LED, more than 2 mA, with margin.

The UART uploads were not verified byte for byte over SWD, because A/B were
disconnected. Both images are the same 1.0.0, so the advertised version
does not distinguish them. The evidence is `nrfutil` with exit code 0 and the app coming back.

## Current draw without host (owner reading, same multimeter as in r45)

| State | Yesterday, 1.0.0 without UART (r45, state A) | Today, 1.0.0 with UART |
|---|---|---|
| Boot, 20 mA range | ≈4 mA and then ≈3.7 mA | 4.2 mA and then 3.2 mA |
| Idle advertising, 2 mA range | ≈0.15 mA, sometimes 0 | **0.17–0.45 mA**, fluctuating |

Conclusion: there is no **increase detectable with a multimeter**. The minimum is
equivalent and no added fixed current appears. The fluctuation comes from
the radio peaks and the measurement every 1 s, which the instrument does not average
well. Separating differences of tenths of a mA would require an average current
meter, for example a PPK2. **It is not a measurement of equality.**

## Audit of Codex's work (before the board)

- **Accepted:** booting with `-nostartfiles -D__START=main
  -D__STARTUP_CLEAR_BSS` and `--fatal-warnings`. It is the documented option in
  `gcc_startup_nrf52.S`: it copies `.data`, clears `.bss` and calls `SystemInit` and
  `main`. Step 1 confirms that it boots.
- **Fixed:**
  1. An empty line (the `\n` the scripts prepend) took the only RX
     slot and could cause `dfu` to be lost. It is now ignored; there is a new test.
  2. With `int 3600`, reconnection took up to an hour to be detected. Now
     E2 is checked every second.
  3. With the TX full, `{"ok":"dfu"}` could be lost. Now the TX is drained before
     responding to `dfu` and `ota`.
  4. A pending command survived disconnection. Now `uart_stop`
     discards it.
  5. The measurement on BLE connection did not go out over UART. Now any measurement
     goes out over UART if there is a host.

## Issues

- **Line remnant when opening the port.** When opening `/dev/cu.usbmodem…` a piece
  of an old line, without `\n`, from when the port was closed, sometimes
  arrives. It sticks to the first new line. In `uart_sensors.py` it only produces
  an initial `not_json`, which is discarded. In `uart_dfu.py --command` it caused
  `{"ok":"dfu"}` not to be recognized. Fixed with `endswith` and a test
  (`test_accepts_ok_after_stale_fragment`).
- The disconnection recording (240 s) was stopped with Ctrl-C after reconnection,
  at 150 s. `result.json` was written.

## Setup at closure

According to the owner, the board is left **with host**: power supply at **3.3 V** on E3/E4
(last test), Pico on GP4/GP5/GND and H disconnected.
