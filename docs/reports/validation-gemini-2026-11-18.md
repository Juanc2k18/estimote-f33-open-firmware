# Validation of Gemini's extended report

Documentary review: 2026. Subject: original transcript (internal research notes, not published), kept unmodified. No hardware was connected or programmed. The corrected commands were checked against their manuals but were not run: this environment does not have `JLinkExe` or `nrfjprog` available in PATH.

**Verdict: partially correct; do not use it as a recovery recipe.** It gets several regulatory mappings and the chip's SWD pins right, but it contains command errors and presents hypotheses about the board as certainties.

## 1. New finding: there is assembly documentation for the F3.3

The Japanese certificate 001-A13797 links two public annexes. Both were downloaded, and the three pages of the first and the test tables of the second were visually inspected. They are regulatory documents hosted on a mirror; the direct link to the MIC portal provided by Gemini could not be opened. It was not checked whether its parameter `ATF=3978002` corresponds to the recovered annex.

- [Graphic annex, 3 pages](https://fccid.io/m/7b38b84adb9ede3898e271998da0572251661f332fb5e6688269a01996afc347.pdf): assembly perspective and label position on p. 1; top drawing on p. 2; bottom drawing on p. 3. The drawings identify revision F3.3, initial BOM rev. 1.0. The bottom side carries MOD: F3.3 and the date Aug. 22, 2016, matching what the owner reported. The four external contacts and eight internal pads are visible. It is a mechanical and component-placement reference; it provides no net names and no SWD pinout.
- [RF annex, 8 pages](https://fccid.io/m/8ec96b20474599a26f55596b482d6d57d96e464c955d17c87f8c5df6278044ce.pdf): identifies F3.3/Sample 01 and BLE tests at 2402, 2442 and 2480 MHz, with nominal voltages of 6.00 V and 3.30 V. The tables on pp. 1 and 5 place the tests between 13 and 25 June 2018. 16 May appears as the instrument calibration date, not as the test date. The test voltages do not identify where to power our board.

Therefore, the report omits a relevant annex and attributes an incorrect date to the test. Nor is it correct to describe those drawings as microscopic photographs of the PCB or as an electrical schematic.

SHA-256 fingerprints of the inspected files: the hexadecimal name in each URL matches the fingerprint computed from the downloaded PDF. The working copies were kept outside the repository; the originals are linked here and their description is kept.

## 2. Regulatory mappings

| Claim | Result and evidence |
| --- | --- |
| EST0116 = F1.3d, report 15-0291, 2016-01-07 | Confirmed on the cover extracted from the [US Tech PDF](https://fccid.io/m/bad41e9316bb163f94d2052a96b476b66f285b9265869ea282011bc09e196090.pdf). |
| EST0117 = G1.12, report 17-0142, 2017-06-21 | Confirmed on the cover of the [US Tech internal annex](https://fccid.io/m/acb7a7573a6ade5b9bb5ae922718dbde71effd4cc72f34a271706ad7876f97ef.pdf). The IC ending in EST0217 appears that way in the document; it was not corrected by inference. |
| EST0216 = H1.7, report 16-0265, 2016-11-18 | Confirmed on the cover of the [US Tech external annex](https://fccid.io/m/5512d27e1f52f753647774c7f040ada215f2eb6db28a722ed56b67899c2c662c.pdf). |
| EST0317 = F3.6, report 17-0528, 2017-12-14 | Confirmed in the headers of the [US Tech external annex](https://fccid.io/2ABP2-EST0317/External-Photos/External-Photos-3685477.pdf). That does not prove UWB, electrical equivalence with the F3.3, or that it is the closest physical reference. |
| EST0217 = Sticker, report 17-0238 | Matches the document title in the [filing index](https://fccid.io/2ABP2-EST0217/Test-Report/Test-Report-Part-15-3493249); the full PDF was not reviewed. |
| F3.3 with Estimote OS 4.13.2 | Confirmed as a user report in [official issue #43](https://github.com/Estimote/Android-Proximity-SDK/issues/43), not as proof about our unit. |

The confirmed mappings make it possible to rule out those annexes as documentation explicitly identified as F3.3. They do not show that every possible regulatory filing for the family has been exhausted, nor that no other filing exists.

## 3. Command errors

### J-Link Commander

`ReadAP 1 0x0C` does not follow the documented Commander syntax. [SEGGER](https://kb.segger.com/J-Link_Commander) specifies a register index and selects the AP via DP SELECT. The equivalent sequence, once the SWD session has been correctly established, is:

```text
WriteDP 2 0x01000000
ReadAP 3
```

It selects AP 1/bank 0 and reads index 3, equivalent to offset 0x0C. Writing SELECT changes the debug selection; it is not an erase command. [Nordic](https://docs.nordicsemi.com/r/bundle/nwp_027/page/wp/nwp_027/nwp_027_approtect.html) confirms AP 1 and the meaning of bit 0: 0 protected, 1 no access protection.

This corrects the syntax; **it does not validate a complete session free of side effects**. The J-Link version, probe, configuration and log are missing. Detecting an SWD-DP shows communication with a debug port, but its ID does not by itself identify the nRF52832, does not validate the eight pads and does not guarantee stability or flash readout. Reject any unlock proposal involving an erase if the goal is to preserve the firmware.

### Backup with nrfjprog

The report combines two file names in a single invocation. [Nordic's manual](https://docs.nordicsemi.com/r/bundle/ug_nrf_cltools/page/ug/cltools/nrf_nrfjprogexe_reference.html) allows combining reads, but only one of them takes a file name. For separate files, the documented form is:

```bash
nrfjprog -f nrf52 --readcode backup_flash.hex
nrfjprog -f nrf52 --readuicr backup_uicr.hex
```

It depends on access being allowed, the target being correctly selected and a compatible tool. Obtaining both files does not yet prove a complete, restorable backup of the whole board: the content and any external memory would still need to be checked. `--recover` is a destructive operation, not a diagnostic step. It was not run.

## 4. Chip and board: what can be stated

| Point | Validation |
| --- | --- |
| QFAAB0 = production revision 1 | Correct; also calling it Engineering B is incorrect. [Nordic's answer on package marking](https://devzone.nordicsemi.com/f/nordic-q-a/40153/understanding-nrf52832-package-marking) distinguishes B00 from the engineering revisions. |
| SWDCLK 25, SWDIO 26, P0.21/nRESET 24 | Correct for QFN48. Reset is a configurable function. These are chip pins, not Estimote pad numbers. |
| VDD 13/36/48; VSS 31/45/bottom pad | Correct for that package. |
| DCC 46 and DEC4 47 | Swapped: **DEC4 = 46; DCC = 47**. Source for these three rows: [Nordic pin assignments](https://docs.nordicsemi.com/r/bundle/ps_nrf52832/page/pin.html). |
| Four external contacts already identified and SWD pads with guaranteed continuity | Not demonstrated. The local record contains no measurements. Resistance, direct connection, reset or the function of each pad cannot be asserted from its appearance. |
| 3.0–3.3 V on external contacts called VDD | Not a validated instruction for this board. The power input, the batteries and the MCU's VDD must be kept separate. |
| Generic firmware receivable at −70/−85 dBm through an unknown FEM | Prediction without evidence for this board. Do not use the absence or presence of advertisements as the only proof of execution. |
| No public F3.3 pinout or support exists | A universal claim not demonstrated through indexed searches. The defensible result is that no reproducible pinout is available yet. |

## 5. SDK and first firmware

[Zephyr documents nrf52dk/nrf52832](https://docs.zephyrproject.org/latest/boards/nordic/nrf52dk/doc/index.html), with two crystals and peripherals specific to that DK. That is not equivalent to support for an Estimote board. Its [defconfig](https://raw.githubusercontent.com/zephyrproject-rtos/zephyr/main/boards/nordic/nrf52dk/nrf52dk_nrf52832_defconfig) enables a UART console: even a simple example requires reviewing the inherited GPIOs.

No specific Zephyr/NCS/BLE controller combination for B00 was validated, nor the exact nRF5 SDK 17.1.0 archive and all its errata. The claims of full compatibility and of a minimal overlay remain pending. LFRC and LDO are options to study; they do not replace identifying the high-frequency clock, RF and power. Nor is there any basis to guarantee that LDO will make any board work.

As a review criterion, do not include GPIO/I2C/SPI sweeps or toggling of unknown contacts in the first test: they generate electrical activity on nets not yet identified. An execution test with known connections must be defined first.

## 6. Practical consequence

The research does move forward: there are now F3.3-specific drawings to guide photographs and measurements. There is still no pinout of its eight pads, no local SWD test, no backup and no reproducible alternative firmware. The next step is still to compare the real board with the drawing, record the original power supply and measure continuity without power. Only then can an SWD session be prepared with specific tools and versions.

SHA-256 fingerprint of the preserved transcript: `c3e5b532993935e52c1fe21a33c0793abbba3d0d01bda81482a5db0cc83ceaaf`.
