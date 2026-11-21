// UART0 on E1 (TX, P0.13) and E2 (RX, P0.12) with host detection on E2 (application 1.0.0).
// Design: internal design notes (not published).
#ifndef UART_H
#define UART_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "f33_uart.h"

void uart_init(void);          // after enabling the SoftDevice: peripheral off and pins idle
bool uart_poll_master(void);   // if it is off and E2 is high, turns it on; returns whether it is on
void uart_stop(void);          // turns the peripheral off; E1 high impedance, E2 with pull-down
bool uart_lost(void);          // framing error or break: the host disconnected
int  uart_take_line(char out[F33_LINE_MAX + 1]);   // 0 nothing, 1 line, -1 too long, -2 invalid
bool uart_write(const char *s, size_t n);          // false if it is off or does not fit (discarded whole)
void uart_flush(void);         // waits until all TX has gone out, up to ≈50 ms

extern volatile uint32_t uart_dropped;   // lines discarded for lack of TX space

#endif
