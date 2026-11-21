# F3.3 application 1.0.0 (BLE + UART with host). `make` produces build/f33-ble-sensors.hex.
# Default version 1.0.0; `make FW_REV=x` changes the string (Device Information 0x2A26).
ROOT      := ../..
SDK_ROOT  ?= $(ROOT)/tools/bootloader-build/src
TOOLCHAIN ?= $(ROOT)/tools/bootloader-build/arm-gnu-toolchain-15.2.rel1-darwin-arm64-arm-none-eabi/bin
CC        := $(TOOLCHAIN)/arm-none-eabi-gcc
OBJCOPY   := $(TOOLCHAIN)/arm-none-eabi-objcopy
SIZE      := $(TOOLCHAIN)/arm-none-eabi-size
SD_API    := $(SDK_ROOT)/lib/softdevice/s132_nrf52_6.1.1/s132_nrf52_6.1.1_API/include
MDK       := $(SDK_ROOT)/lib/nrfx/mdk
OUT       ?= build
NRFUTIL   ?= $(ROOT)/.venv/bin/adafruit-nrfutil
SD_FWID   := 0x00B7   # S132 6.1.1, read at 0x300C over SWD (r45)
NAME      := f33-ble-sensors
FW_REV    ?= 1.0.0

SRC  := main.c sensors.c twim.c f33_math.c f33_uart.c uart.c $(MDK)/system_nrf52.c
ASM  := $(MDK)/gcc_startup_nrf52.S
CPU  := -mcpu=cortex-m4 -mthumb -mabi=aapcs -mfloat-abi=hard -mfpu=fpv4-sp-d16
DEFS := -DNRF52832_XXAA -DNRF52 -DS132 -DSOFTDEVICE_PRESENT -DNRF_SD_BLE_API_VERSION=6 \
        -D__HEAP_SIZE=0 -D__STACK_SIZE=4096 -D__START=main -D__STARTUP_CLEAR_BSS -DFW_REV='"$(FW_REV)"'
INC  := -I. -isystem $(SD_API) -isystem $(SD_API)/nrf52 -isystem $(MDK) -isystem $(SDK_ROOT)/src/cmsis/include
CFLAGS  := $(CPU) $(DEFS) $(INC) -std=c11 -Os -g3 -Wall -Wextra -Werror \
           -ffunction-sections -fdata-sections -fno-strict-aliasing -fno-builtin -fshort-enums
# Nordic Reset_Handler initializes data/BSS and calls main; no newlib CRT/exit/syscalls.
LDFLAGS := $(CPU) -nostartfiles -L$(MDK) -Tapp.ld -Wl,--gc-sections -Wl,--fatal-warnings -Wl,-Map=$(OUT)/$(NAME).map --specs=nano.specs --specs=nosys.specs

all: $(OUT)/$(NAME).hex

# DFU package (legacy, SDK 11) for UART (adafruit-nrfutil) and BLE (scripts/ble_dfu.py).
zip: $(OUT)/$(NAME).zip

$(OUT)/$(NAME).zip: $(OUT)/$(NAME).hex
	$(NRFUTIL) dfu genpkg --dev-type 0x0052 --sd-req $(SD_FWID) --application $< $@

$(OUT)/$(NAME).elf: $(SRC) $(ASM) app.ld *.h | $(OUT)
	$(CC) $(CFLAGS) $(LDFLAGS) $(SRC) $(ASM) -o $@
	$(SIZE) $@

$(OUT)/$(NAME).hex: $(OUT)/$(NAME).elf
	$(OBJCOPY) -O ihex $< $@

$(OUT):
	mkdir -p $@

clean:
	rm -rf $(OUT)

.PHONY: all zip clean
