// UART format with a host (application 1.0.0). See f33_uart.h.
#include "f33_uart.h"

typedef struct { char *p; size_t len, pos; bool ok; } wr_t;

static void put_s(wr_t *w, const char *s) {
  for (; *s; s++) {
    if (w->pos + 1 >= w->len) { w->ok = false; return; }
    w->p[w->pos++] = *s;
  }
}

static void put_u(wr_t *w, uint32_t v) {
  char t[10];
  int n = 0;
  do { t[n++] = (char)('0' + v % 10); v /= 10; } while (v);
  char c[2] = {0, 0};
  while (n) { c[0] = t[--n]; put_s(w, c); }
}

static void put_i(wr_t *w, int32_t v) {
  if (v < 0) { put_s(w, "-"); put_u(w, 0u - (uint32_t)v); }
  else put_u(w, (uint32_t)v);
}

static void put_v3(wr_t *w, const int16_t v[3]) {
  put_s(w, "["); put_i(w, v[0]); put_s(w, ","); put_i(w, v[1]); put_s(w, ","); put_i(w, v[2]); put_s(w, "]");
}

static size_t finish(wr_t *w) {
  if (!w->ok) { if (w->len) w->p[0] = 0; return 0; }
  w->p[w->pos] = 0;
  return w->pos;
}

size_t f33_json_line(const f33_sample_t *s, char *buf, size_t len) {
  wr_t w = {buf, len, 0, len > 0};
  put_s(&w, "{\"seq\":"); put_u(&w, s->seq);
  if (s->flags & F33_ACC) { put_s(&w, ",\"acc_mg\":"); put_v3(&w, s->acc_mg); }
  if (s->flags & F33_MAG) { put_s(&w, ",\"mag_mg\":"); put_v3(&w, s->mag_mgauss); }
  if (s->flags & F33_BARO) {
    put_s(&w, ",\"temp_cc\":"); put_i(&w, s->temp_centi);
    put_s(&w, ",\"press_pa\":"); put_u(&w, s->press_q24_8 / 256);
  }
  if (s->flags & F33_LIGHT) { put_s(&w, ",\"mlux\":"); put_u(&w, s->millilux); }
  if (s->flags & F33_RTC) { put_s(&w, ",\"rtc_s\":"); put_u(&w, s->rtc_seconds); }
  if (s->flags & F33_ADC) {
    uint16_t mv = f33_battery_mv(s->ain3_mv);
    put_s(&w, ",\"vdd_mv\":"); put_u(&w, s->vdd_mv);
    put_s(&w, ",\"ain3_mv\":"); put_u(&w, s->ain3_mv);
    put_s(&w, ",\"bat_mv\":"); put_u(&w, mv);
    put_s(&w, ",\"bat_pct\":"); put_u(&w, f33_battery_percent(mv));
  }
  put_s(&w, "}\n");
  return finish(&w);
}

int f33_line_feed(f33_line_t *l, uint8_t b) {
  if (b == '\r') return 0;
  if (b == '\n') {
    int r = l->bad ? -2 : l->overflow ? -1 : l->len ? 1 : 0;   // empty line: nothing
    l->buf[l->len] = 0;
    l->len = 0;
    l->bad = l->overflow = false;
    return r;
  }
  if (b < 0x20 || b > 0x7E) { l->bad = true; return 0; }
  if (l->len >= F33_LINE_MAX) { l->overflow = true; return 0; }
  l->buf[l->len++] = (char)b;
  return 0;
}

static char lower(char c) { return (c >= 'A' && c <= 'Z') ? (char)(c - 'A' + 'a') : c; }
static const char *skip(const char *s) { while (*s == ' ') s++; return s; }

// If `s` starts with the word `w` followed by a space or the end, returns what follows; otherwise NULL.
static const char *word(const char *s, const char *w) {
  for (; *w; s++, w++)
    if (lower(*s) != *w) return NULL;
  return (*s == ' ' || *s == 0) ? s : NULL;
}

f33_cmd_t f33_parse_cmd(const char *line, uint32_t *arg) {
  const char *s = skip(line), *r;
  if (!*s) return F33_CMD_NONE;
  if ((r = word(s, "read")) && !*skip(r)) return F33_CMD_READ;
  if ((r = word(s, "ver")) && !*skip(r)) return F33_CMD_VER;
  if ((r = word(s, "dfu")) && !*skip(r)) return F33_CMD_DFU;
  if ((r = word(s, "ota")) && !*skip(r)) return F33_CMD_OTA;
  if ((r = word(s, "int"))) {
    r = skip(r);
    uint32_t v = 0;
    int digits = 0;
    for (; *r >= '0' && *r <= '9'; r++, digits++)
      if (v < 100000) v = v * 10 + (uint32_t)(*r - '0');   // cap: avoids overflow with long numbers
    if (!digits || *skip(r)) return F33_CMD_ERR_CMD;
    if (v < F33_PERIOD_MIN || v > F33_PERIOD_MAX) return F33_CMD_ERR_RANGE;
    *arg = v;
    return F33_CMD_INT;
  }
  return F33_CMD_ERR_CMD;
}

size_t f33_reply(f33_cmd_t c, uint32_t arg, const char *fw, char *buf, size_t len) {
  wr_t w = {buf, len, 0, len > 0};
  switch (c) {
  case F33_CMD_READ:      put_s(&w, "{\"ok\":\"read\"}"); break;
  case F33_CMD_INT:       put_s(&w, "{\"ok\":\"int\",\"s\":"); put_u(&w, arg); put_s(&w, "}"); break;
  case F33_CMD_VER:       put_s(&w, "{\"ok\":\"ver\",\"fw\":\""); put_s(&w, fw); put_s(&w, "\"}"); break;
  case F33_CMD_DFU:       put_s(&w, "{\"ok\":\"dfu\"}"); break;
  case F33_CMD_OTA:       put_s(&w, "{\"ok\":\"ota\"}"); break;
  case F33_CMD_ERR_CMD:   put_s(&w, "{\"err\":\"cmd\"}"); break;
  case F33_CMD_ERR_RANGE: put_s(&w, "{\"err\":\"range\"}"); break;
  case F33_CMD_ERR_LONG:  put_s(&w, "{\"err\":\"long\"}"); break;
  default:                if (len) buf[0] = 0; return 0;   // F33_CMD_NONE: no reply
  }
  put_s(&w, "\n");
  return finish(&w);
}
