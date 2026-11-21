#include "twim.h"
#include "nrf.h"

#define PIN_SDA 14
#define PIN_SCL 15
#define TIMEOUT_LOOPS 200000u   // ~ several ms at 64 MHz; one byte at 100 kHz takes 90 µs

static uint8_t tx_buf[8];

void twim_init(void) {
  // r44: with P0.06/P0.07 high and no internal pull, SDA/SCL read as 0. The software I²C
  // that worked (r36–r39) used the internal pull-up: it is used here as well.
  uint32_t cnf = (GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos) |
                 (GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos) |
                 (GPIO_PIN_CNF_PULL_Pullup << GPIO_PIN_CNF_PULL_Pos) |
                 (GPIO_PIN_CNF_DRIVE_S0D1 << GPIO_PIN_CNF_DRIVE_Pos);
  NRF_P0->PIN_CNF[PIN_SDA] = cnf;
  NRF_P0->PIN_CNF[PIN_SCL] = cnf;
  NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Disabled;
  NRF_TWIM0->PSEL.SDA = PIN_SDA;
  NRF_TWIM0->PSEL.SCL = PIN_SCL;
  NRF_TWIM0->FREQUENCY = TWIM_FREQUENCY_FREQUENCY_K100;
  NRF_TWIM0->ENABLE = TWIM_ENABLE_ENABLE_Enabled;
}

static bool run(uint32_t shorts, bool start_rx) {
  NRF_TWIM0->EVENTS_STOPPED = 0;
  NRF_TWIM0->EVENTS_ERROR = 0;
  NRF_TWIM0->ERRORSRC = NRF_TWIM0->ERRORSRC;   // cleared by writing 1
  NRF_TWIM0->SHORTS = shorts;
  if (start_rx) NRF_TWIM0->TASKS_STARTRX = 1; else NRF_TWIM0->TASKS_STARTTX = 1;
  uint32_t n = 0;
  while (!NRF_TWIM0->EVENTS_STOPPED && !NRF_TWIM0->EVENTS_ERROR && ++n < TIMEOUT_LOOPS) {}
  if (!NRF_TWIM0->EVENTS_STOPPED) {
    NRF_TWIM0->TASKS_STOP = 1;   // NACK or hung bus: release the bus
    n = 0;
    while (!NRF_TWIM0->EVENTS_STOPPED && ++n < TIMEOUT_LOOPS) {}
    NRF_TWIM0->EVENTS_STOPPED = 0;
    return false;
  }
  NRF_TWIM0->EVENTS_STOPPED = 0;
  return NRF_TWIM0->ERRORSRC == 0;
}

bool twim_write(uint8_t addr, const uint8_t *data, size_t len) {
  if (len > sizeof tx_buf) return false;
  for (size_t i = 0; i < len; i++) tx_buf[i] = data[i];   // EasyDMA only reads from RAM
  NRF_TWIM0->ADDRESS = addr;
  NRF_TWIM0->TXD.PTR = (uint32_t)tx_buf;
  NRF_TWIM0->TXD.MAXCNT = len;
  return run(TWIM_SHORTS_LASTTX_STOP_Msk, false);
}

bool twim_write_reg(uint8_t addr, uint8_t reg, uint8_t value) {
  uint8_t d[2] = {reg, value};
  return twim_write(addr, d, 2);
}

bool twim_read(uint8_t addr, uint8_t reg, uint8_t *data, size_t len) {
  tx_buf[0] = reg;
  NRF_TWIM0->ADDRESS = addr;
  NRF_TWIM0->TXD.PTR = (uint32_t)tx_buf;
  NRF_TWIM0->TXD.MAXCNT = 1;
  NRF_TWIM0->RXD.PTR = (uint32_t)data;
  NRF_TWIM0->RXD.MAXCNT = len;
  return run(TWIM_SHORTS_LASTTX_STARTRX_Msk | TWIM_SHORTS_LASTRX_STOP_Msk, false);
}
