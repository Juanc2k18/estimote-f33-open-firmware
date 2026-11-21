# Third-party material

The [MIT](LICENSE) license covers only this project's original content. The
following files keep their authors' licenses.

| Files | Author | License | Notes |
|---|---|---|---|
| `firmware/adafruit-bootloader/*.hex` (bootloader part), `board.h`, `board.mk` | Adafruit Industries and contributors ([Adafruit_nRF52_Bootloader](https://github.com/adafruit/Adafruit_nRF52_Bootloader)) | MIT — [text](firmware/adafruit-bootloader/licenses/LICENSE-adafruit-bootloader.txt) | Own build of version 0.11.0 (commit `c67f0bc`) with a new board definition. |
| S132 6.1.1 SoftDevice and MBR inside `estimote_f33_bootloader-0.11.0_s132_6.1.1-r46.hex` | Nordic Semiconductor ASA | Nordic 5-clause license — [text](firmware/adafruit-bootloader/licenses/LICENSE-nordic-s132.txt) | May only be used with Nordic integrated circuits. The binary must not be decompiled or modified. |
| `docs/evidence/diystuff-uwb-carousel-2026-11-18/*.png` and derived crops/annotations in `docs/evidence/uwb-route-verification-2026-11-18/1Top-*.png`, `2Inner-*.png`, `4Bot-*.png` and `docs/evidence/rtc-uwb-routes-r34-2026-11-19/uwb-1top-rtc-annotated.png` | Marco van Nieuwenhoven / [DIY Stuff](https://diystuff.nl/embedded/estimote-uwb-location-beacon-teardown/) | [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) | Non-commercial use with attribution; derivatives are shared under the same license. They show the UWB variant, not the F3.3. |

Photos of the board are the project's own. A reference photo from the internet
used early on is not included. Datasheets (ST M41T62, Nordic nRF52832, etc.)
are not included; they are linked to the official source. Estimote is a
trademark of Estimote, Inc.; this project is not affiliated with or endorsed by
the company.
