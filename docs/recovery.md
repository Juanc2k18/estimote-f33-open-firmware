# Staged diagnosis and recovery

Staged guide. **BLE observation already has local evidence**, with sensors received from macOS; two UART listening sessions without bytes were also done. Authenticated configuration, UART activation, SWD, backup and flashing have not been carried out yet. See the [logbook for 2026](logbook/2026-11-18.md). The instructions below are still proposals except where a result is linked. Numbered references in [research](research.md).

## Before critical steps

Explain the gains and losses, permanent factory-firmware erasure and the risk of irreversible damage from wiring, voltage or programming errors. Obtain explicit authorization for the specific critical step before proceeding; see [AGENTS.md](../AGENTS.md). Historical tests are not standing authorization.

## A. Observe the existing firmware

1. Complete the identification and photographs in [the unit sheet](unit.md).
2. If it still has working original power, scan with [nRF Connect for Mobile](https://www.nordicsemi.com/Products/Development-tools/nRF-Connect-for-mobile). Record phone, OS, version, permissions and date. Start without connecting or writing characteristics.
3. Save name, observed identifier, service UUIDs, manufacturer data, service data and raw bytes. Record for at least one minute and repeat after gently moving/reorienting the device. If it does not appear, check power, permissions and possible conditional advertising before concluding it is faulty.
4. Look for iBeacon/Eddystone/Estimote advertisements without assuming they are all enabled. Compare possible Telemetry frames with [the official parser](https://github.com/estimote/estimote-specs/blob/master/estimote-telemetry.js). Record the protocol version; do not interpret offsets from another version.
5. Note which readings are actually observed and which only appear in documentation. A connectivity packet does not guarantee that telemetry is enabled.

A receiver can use open advertisements without logging in to Estimote; that does not enable access to configuration. MAC-based identification may vary or look different across platforms: also keep the content of the advertisements.

### Proximity and distance

Recording RSSI is useful for presence and for comparing closeness. RSSI changes with orientation, the human body, walls and multipath; it is not a direct measurement of meters. As an experiment, measure series at known distances with the same receiver and orientation, using median and spread; choose thresholds with hysteresis. If a propagation model is tried, calibrate it locally and publish its errors. A single beacon and its RSSI do not determine a unique 2D position. These are experiment design criteria, not measured performance of this device.

**Output of A:** raw capture and list of functions usable now. If there is telemetry, a possible second life as a BLE sensor without flashing already exists.

## B. Evaluate the original configuration

1. Record the exact error of the available app and check whether the unit belongs to an accessible account.
2. Review the [official SDK](https://github.com/Estimote/iOS-Fleet-Management-SDK), GPIO examples and access mode of that version. Record actual build and connection compatibility; historical documentation is not equivalent to current operation.
3. Distinguish Development mode (access policy) from GPIO/UART mode (function of the contacts). They are not the same.
4. If it is possible to authenticate and configure, save the original settings before changing a single parameter. Rescan and compare.
5. Try UART only with confirmed pins, power and levels. Background case S1 uses EstiUART, a proprietary protocol; there is no evidence of a text command console nor of a firmware loader over that port.

No recipe is offered to “activate the pins” with nRF Connect: being able to discover services does not replace Estimote's protocol or authorization. The presence of DFU in a tool does not prove compatibility with the original bootloader either.

**Output of B:** connection/configuration result with evidence, or a concrete blocker (account, service, firmware or compatibility).

## C. Investigate custom firmware over SWD

Applicable only after identifying the MCU and completing [hardware](hardware.md).

1. Document probe, versions, voltages and connections with photos; check for short circuits without power.
2. Establish a debug session using the connection procedure of the chosen tool. Even connecting a probe can halt or reset the MCU: record that effect. Identify whether the scripts recover or erase and run them only as part of a defined test; obtain explicit authorization before any critical action.
3. Read identifiers and protection state if the tool and the chip allow it. Save logs. A connection failure can also be wiring or power; it does not demonstrate protection.
4. If reading is allowed and useful, attempt a flash/UICR backup and record SHA-256. It is optional and does not block reuse if not possible. Two matching readings verify consistency; they do not guarantee restoration.
5. If APPROTECT is present, document the lock. On the nRF52832 the recovery mechanism via erase can remove flash, UICR and RAM; **it is not a backup and does not recover the original firmware**. The reference unit was protected and was subsequently erased; it no longer contains the factory firmware.
6. Before erasing, define whether the goal is to diagnose recovery or to load firmware, and document the goal, tool and connections. Explain that erasure permanently removes the factory firmware and configuration, identify the intended replacement and its limitations, and wait for explicit authorization. Do not assume restoration from the cloud.
7. For a future port, choose a pinned toolchain version and a custom board definition. Nordic recommends nRF Connect SDK for new projects; nRF5 SDK/S132 is a historical alternative in maintenance [S12]. Do not flash a DK image expecting pin equivalence.
8. Validate boot and consumption; then BLE advertisements and, separately, each sensor. Add the pinout, code, exact commands and results to the repository when a real reproduction exists.

This phase contains no erase or flash commands: photographic corroboration of the MCU, a confirmed board pinout and a confirmed tool are missing for them to be executable without inventing parameters.

## Success criterion

- Recovery without flashing: repeatable reception of presence or useful readings, with captures and conditions recorded.
- Recovery with custom firmware: build from sources, repeatable programming on the F3.3 and a documented functional test, with known consumption and limitations.
- Publication: our own photos, checked links, pinned versions and steps distinguished between tested and proposed.
