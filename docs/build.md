# Build the F3.3 firmware from a fresh checkout

These instructions are for a user or AI agent preparing a build environment.
They generate files locally; no beacon, ESP32 or programmer needs to be connected.
Use the commands when you want to rebuild, rather than assuming the ignored
`tools/bootloader-build/` directory is already available.

The reference build used macOS Apple Silicon, Python 3.12 and Arm GNU Toolchain
15.2.rel1. The shell commands below are for macOS/Linux; other hosts require
adapted installation and paths. Linux/Windows builds have not been validated
by this project.

## 1. Get the project and Python tools

Install Git, GNU Make, Python 3.12 with venv/pip, and an archive extractor.
For the optional host tests, also install a C/C++ compiler. Start in a new
directory; do not overwrite an existing checkout or build environment.

```bash
git clone https://github.com/Juanc2k18/estimote-f33-open-firmware.git
cd estimote-f33-open-firmware
F33_ROOT="$(pwd)"
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install intelhex==2.3.0
```

Keep using this shell so that `F33_ROOT` remains defined. For an existing
checkout, start at its root and set `F33_ROOT` there; reuse or deliberately
prepare its environment instead of repeating `git clone`.

## 2. Prepare the pinned Adafruit source and board definition

The application uses the SoftDevice, nrfx and CMSIS headers from this tree.
The bootloader also uses its submodules. Check out the full pinned commit
before initializing submodules so their revisions match that source.

```bash
mkdir -p tools/bootloader-build
git clone https://github.com/adafruit/Adafruit_nRF52_Bootloader.git tools/bootloader-build/src
git -C tools/bootloader-build/src checkout --detach c67f0bcf0fa8e841426335b1bbde91cda6ca1f50
git -C tools/bootloader-build/src submodule update --init --recursive
mkdir -p tools/bootloader-build/src/src/boards/estimote_f33
cp firmware/adafruit-bootloader/board.h firmware/adafruit-bootloader/board.mk tools/bootloader-build/src/src/boards/estimote_f33/
```

The repeated `src/src` is intentional: the clone is named `src`, and Adafruit
keeps board definitions in its own `src/boards` directory. This dependency tree
is ignored by this project's Git configuration.

## 3. Install the compiler for your host

Download **Arm GNU Toolchain 15.2.rel1**, target **arm-none-eabi**, from
[Arm's downloads](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads).
Choose the archive for your computer's OS and CPU and compare its SHA-256 with
the checksum provided by Arm before extracting it. Do not choose an
`aarch64-none-elf` or Linux-target compiler: the beacon uses Cortex-M4.
See [Arm's installation guide](https://learn.arm.com/install-guides/gcc/arm-gnu/).

For the macOS Apple Silicon archive, replace the archive path below with your
download's actual location:

```bash
F33_ARCHIVE="/absolute/path/to/arm-gnu-toolchain-15.2.rel1-darwin-arm64-arm-none-eabi.tar.xz"
shasum -a 256 "$F33_ARCHIVE"
# Compare the printed digest with Arm's published checksum before continuing.
tar -xf "$F33_ARCHIVE" -C "$F33_ROOT/tools/bootloader-build"
F33_TOOLCHAIN="$F33_ROOT/tools/bootloader-build/arm-gnu-toolchain-15.2.rel1-darwin-arm64-arm-none-eabi/bin"
"$F33_TOOLCHAIN/arm-none-eabi-gcc" --version
```

For another host or an existing installation, set `F33_TOOLCHAIN` to the
absolute directory containing `arm-none-eabi-gcc`, `arm-none-eabi-objcopy` and
`arm-none-eabi-size`. The version output must correspond to the chosen
15.2.rel1 release. The application Makefile's default path is for macOS ARM64;
the commands below override it explicitly.

## 4. Build application 1.0.0

Run from the project root:

```bash
make -C firmware/ble-sensors zip \
  SDK_ROOT="$F33_ROOT/tools/bootloader-build/src" \
  TOOLCHAIN="$F33_TOOLCHAIN" \
  NRFUTIL="$F33_ROOT/.venv/bin/adafruit-nrfutil"
```

Outputs: `firmware/ble-sensors/build/f33-ble-sensors.hex` and
`firmware/ble-sensors/build/f33-ble-sensors.zip` (application-only DFU package).
The default firmware revision is 1.0.0. To create a distinguishable test build,
add `FW_REV=your-test-revision OUT=build/your-test-revision` to the command.

## 5. Build bootloader r46 with S132 6.1.1

The copied `board.h` provides the r46 BLE strings and F3.3 pins. Explicit
version parameters avoid differences in tag discovery and macOS `sed` behavior.

```bash
make -C "$F33_ROOT/tools/bootloader-build/src" \
  BOARD=estimote_f33 \
  PYTHON="$F33_ROOT/.venv/bin/python" \
  CROSS_COMPILE="$F33_TOOLCHAIN/arm-none-eabi-" \
  NRFUTIL="$F33_ROOT/.venv/bin/adafruit-nrfutil" \
  GIT_VERSION=0.11.0 _VER3="0 11 0" all
```

Outputs are under `tools/bootloader-build/src/_build/build-estimote_f33/`:

- `estimote_f33_bootloader-0.11.0_s132_6.1.1.hex`: combined bootloader,
  SoftDevice and UICR, corresponding to the published r46 combined image.
- `estimote_f33_bootloader-0.11.0_nosd.hex`: the published r46 nosd variant.
- The upstream `all` target also creates local UF2/ZIP artifacts. Those are not
  the application's DFU package and are not the project's published install path.

## 6. Compare with the published artifacts

For unchanged sources and the reference toolchain, the following `cmp`
commands are expected to exit 0 with no output. A difference needs investigation
before claiming the build reproduces the published HEX.

```bash
cmp firmware/ble-sensors/build/f33-ble-sensors.hex firmware/ble-sensors/release/f33-ble-sensors-1.0.0.hex
cmp tools/bootloader-build/src/_build/build-estimote_f33/estimote_f33_bootloader-0.11.0_s132_6.1.1.hex firmware/adafruit-bootloader/estimote_f33_bootloader-0.11.0_s132_6.1.1-r46.hex
cmp tools/bootloader-build/src/_build/build-estimote_f33/estimote_f33_bootloader-0.11.0_nosd.hex firmware/adafruit-bootloader/estimote_f33_bootloader-0.11.0_nosd-r46.hex
```

ZIP container timestamps can differ. Compare the decompressed application BIN,
DAT and manifest rather than requiring an identical ZIP hash:

```bash
.venv/bin/python - <<'PY'
from zipfile import ZipFile
with ZipFile('firmware/ble-sensors/build/f33-ble-sensors.zip') as built, \
     ZipFile('firmware/ble-sensors/release/f33-ble-sensors-1.0.0.zip') as published:
    for name in published.namelist():
        assert built.read(name) == published.read(name), name
print('Application DFU contents match')
PY
```

Optional software tests, without hardware:

```bash
python3.12 -m unittest discover -s tests
```

Compiling and comparing files does not install them. Programming is a separate
operation covered by the [guide](guide-f33.md#6-reprogramming), with its own
target, wiring, power and authorization requirements.
