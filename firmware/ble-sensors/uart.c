// Classic UART0 (no EasyDMA), interrupt driven. See uart.h.
#include <string.h>
#include "nrf.h"
#include "nrf_nvic.h"
#include "sensors.h"   // delay_us
#include "uart.h"

#define TX_PIN  13     // E1
#define RX_PIN  12     // E2
#define TX_SIZE 512u

static uint8_t tx_buf[TX_SIZE];
static volatile uint16_t tx_head, tx_tail;
static volatile bool tx_busy, on, lost;
static f33_line_t rx;
static char pending[F33_LINE_MAX + 1];
static volatile int pending_kind;
volatile uint32_t uart_dropped;

static void pins_idle(void) {
  // E1 not driven: does not power a switched-off host through its diodes.
  NRF_P0->PIN_CNF[TX_PIN] = GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos |
                            GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos;
  // E2 with pull-down: high only if a host's TX is idle.
  NRF_P0->PIN_CNF[RX_PIN] = GPIO_PIN_CNF_DIR_Input << GPIO_PIN_CNF_DIR_Pos |
                            GPIO_PIN_CNF_INPUT_Connect << GPIO_PIN_CNF_INPUT_Pos |
                            GPIO_PIN_CNF_PULL_Pulldown << GPIO_PIN_CNF_PULL_Pos;
}

static bool rx_high(void) { return (NRF_P0->IN >> RX_PIN) & 1u; }

static void peripheral_off(void) {
  NRF_UART0->INTENCLR = 0xFFFFFFFF;
  NRF_UART0->TASKS_STOPRX = 1;
  NRF_UART0->TASKS_STOPTX = 1;
  NRF_UART0->ENABLE = 0;
  NRF_UART0->PSELTXD = 0xFFFFFFFF;
  NRF_UART0->PSELRXD = 0xFFFFFFFF;
  pins_idle();
  on = tx_busy = lost = false;
  pending_kind = 0;   // a command received before disconnecting is not executed
  sd_nvic_ClearPendingIRQ(UARTE0_UART0_IRQn);
}

void uart_init(void) {
  peripheral_off();   // the bootloader may have left the UART configured after its window
  sd_nvic_SetPriority(UARTE0_UART0_IRQn, 6);
  sd_nvic_EnableIRQ(UARTE0_UART0_IRQn);
}

void uart_stop(void) { peripheral_off(); }

static void start(void) {
  tx_head = tx_tail = 0;
  tx_busy = lost = false;
  pending_kind = 0;
  memset(&rx, 0, sizeof rx);
  NRF_P0->OUTSET = 1u << TX_PIN;
  NRF_P0->PIN_CNF[TX_PIN] = GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos |
                            GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos;
  NRF_UART0->PSELTXD = TX_PIN;
  NRF_UART0->PSELRXD = RX_PIN;
  NRF_UART0->BAUDRATE = UART_BAUDRATE_BAUDRATE_Baud115200;
  NRF_UART0->CONFIG = 0;   // 8N1, no flow control
  NRF_UART0->EVENTS_RXDRDY = 0;
  NRF_UART0->EVENTS_TXDRDY = 0;
  NRF_UART0->EVENTS_ERROR = 0;
  NRF_UART0->ERRORSRC = NRF_UART0->ERRORSRC;   // writing 1 clears
  NRF_UART0->INTENSET = UART_INTENSET_RXDRDY_Msk | UART_INTENSET_TXDRDY_Msk | UART_INTENSET_ERROR_Msk;
  NRF_UART0->ENABLE = UART_ENABLE_ENABLE_Enabled;
  NRF_UART0->TASKS_STARTRX = 1;
  on = true;
}

bool uart_poll_master(void) {
  if (on) return true;
  if (!rx_high()) return false;
  delay_us(1000);
  if (!rx_high()) return false;
  start();
  return true;
}

bool uart_lost(void) { return on && lost; }

int uart_take_line(char out[F33_LINE_MAX + 1]) {
  uint8_t nested;
  sd_nvic_critical_region_enter(&nested);
  int k = pending_kind;
  if (k == 1) memcpy(out, pending, sizeof pending);
  pending_kind = 0;
  sd_nvic_critical_region_exit(nested);
  return k;
}

bool uart_write(const char *s, size_t n) {
  if (!on) return false;
  uint16_t head = tx_head;
  uint16_t used = (uint16_t)((head + TX_SIZE - tx_tail) % TX_SIZE);
  if (n > TX_SIZE - 1u - used) { uart_dropped++; return false; }
  for (size_t i = 0; i < n; i++) { tx_buf[head] = (uint8_t)s[i]; head = (uint16_t)((head + 1u) % TX_SIZE); }
  uint8_t nested;
  sd_nvic_critical_region_enter(&nested);
  tx_head = head;
  if (!tx_busy) {
    tx_busy = true;
    NRF_UART0->TASKS_STARTTX = 1;
    NRF_UART0->TXD = tx_buf[tx_tail];
    tx_tail = (uint16_t)((tx_tail + 1u) % TX_SIZE);
  }
  sd_nvic_critical_region_exit(nested);
  return true;
}

void uart_flush(void) {
  for (int i = 0; i < 500 && on && tx_busy; i++) delay_us(100);
  delay_us(200);   // the last byte leaves the shift register
}

void UARTE0_UART0_IRQHandler(void) {
  if (NRF_UART0->EVENTS_ERROR) {
    NRF_UART0->EVENTS_ERROR = 0;
    uint32_t src = NRF_UART0->ERRORSRC;
    NRF_UART0->ERRORSRC = src;
    if (src & (UART_ERRORSRC_FRAMING_Msk | UART_ERRORSRC_BREAK_Msk)) lost = true;   // E2 dropped low
    else rx.bad = true;                                                             // parity/overrun
  }
  if (NRF_UART0->EVENTS_RXDRDY) {
    NRF_UART0->EVENTS_RXDRDY = 0;   // clear before reading RXD (nRF52832 manual)
    int r = f33_line_feed(&rx, (uint8_t)NRF_UART0->RXD);
    if (r && !pending_kind) {
      if (r == 1) memcpy(pending, rx.buf, sizeof pending);
      pending_kind = r;
    }
  }
  if (NRF_UART0->EVENTS_TXDRDY) {
    NRF_UART0->EVENTS_TXDRDY = 0;
    if (tx_tail != tx_head) {
      NRF_UART0->TXD = tx_buf[tx_tail];
      tx_tail = (uint16_t)((tx_tail + 1u) % TX_SIZE);
    } else {
      tx_busy = false;
      NRF_UART0->TASKS_STOPTX = 1;
    }
  }
}
