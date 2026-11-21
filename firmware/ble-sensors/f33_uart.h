// UART format with a host (application 1.0.0): JSON lines and text commands.
// Pure: no registers; also compiled on the Mac (tests/test_uart_firmware.py).
// Design: internal design notes (not published).
#ifndef F33_UART_H
#define F33_UART_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "f33_math.h"

#define F33_LINE_MAX   32     // longest accepted command, without '\n'
#define F33_JSON_MAX   224    // buffer large enough for f33_json_line (worst case ≈205 with NUL)
#define F33_PERIOD_MIN 1
#define F33_PERIOD_MAX 3600

typedef enum { F33_CMD_NONE, F33_CMD_READ, F33_CMD_INT, F33_CMD_VER, F33_CMD_DFU, F33_CMD_OTA,
               F33_CMD_ERR_CMD, F33_CMD_ERR_RANGE, F33_CMD_ERR_LONG } f33_cmd_t;

typedef struct { char buf[F33_LINE_MAX + 1]; uint8_t len; bool overflow, bad; } f33_line_t;

// JSON line terminated by '\n' and NUL; returns its length without the NUL, or 0 if it does not fit.
size_t    f33_json_line(const f33_sample_t *s, char *buf, size_t len);
// One received byte: 0 continue (or empty line), 1 line ready in l->buf, -1 too long, -2 non-printable bytes.
int       f33_line_feed(f33_line_t *l, uint8_t byte);
// Line without '\n'. With F33_CMD_INT it leaves the interval in *arg.
f33_cmd_t f33_parse_cmd(const char *line, uint32_t *arg);
// JSON reply terminated by '\n'; 0 for F33_CMD_NONE or if it does not fit.
size_t    f33_reply(f33_cmd_t c, uint32_t arg, const char *fw, char *buf, size_t len);

#endif
