/* F3.3 r44: application on top of S132 6.1.1, below the Adafruit bootloader (0x74000). */
SEARCH_DIR(.)
GROUP(-lgcc -lc)

MEMORY
{
  FLASH (rx) : ORIGIN = 0x26000, LENGTH = 0x74000 - 0x26000
  RAM (rwx) :  ORIGIN = 0x20003000, LENGTH = 0x20010000 - 0x20003000
}

INCLUDE "nrf_common.ld"
