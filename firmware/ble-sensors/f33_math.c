#include "f33_math.h"

static uint16_t u16le(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }

void bmp280_cal_parse(const uint8_t raw[24], bmp280_cal_t *c) {
  c->T1 = u16le(raw);               c->T2 = (int16_t)u16le(raw + 2);  c->T3 = (int16_t)u16le(raw + 4);
  c->P1 = u16le(raw + 6);           c->P2 = (int16_t)u16le(raw + 8);  c->P3 = (int16_t)u16le(raw + 10);
  c->P4 = (int16_t)u16le(raw + 12); c->P5 = (int16_t)u16le(raw + 14); c->P6 = (int16_t)u16le(raw + 16);
  c->P7 = (int16_t)u16le(raw + 18); c->P8 = (int16_t)u16le(raw + 20); c->P9 = (int16_t)u16le(raw + 22);
}

// Integer formulas from the BMP280 datasheet (section 3.11.3).
int32_t bmp280_temp_centi(const bmp280_cal_t *c, int32_t adc_t, int32_t *t_fine) {
  int32_t v1 = ((((adc_t >> 3) - ((int32_t)c->T1 << 1))) * (int32_t)c->T2) >> 11;
  int32_t d = (adc_t >> 4) - (int32_t)c->T1;
  int32_t v2 = (((d * d) >> 12) * (int32_t)c->T3) >> 14;
  *t_fine = v1 + v2;
  return (*t_fine * 5 + 128) >> 8;
}

uint32_t bmp280_press_q24_8(const bmp280_cal_t *c, int32_t adc_p, int32_t t_fine) {
  int64_t v1 = (int64_t)t_fine - 128000;
  int64_t v2 = v1 * v1 * c->P6;
  v2 += (v1 * c->P5) * ((int64_t)1 << 17);
  v2 += (int64_t)c->P4 * ((int64_t)1 << 35);
  v1 = ((v1 * v1 * c->P3) >> 8) + (v1 * c->P2 * ((int64_t)1 << 12));
  v1 = ((((int64_t)1 << 47) + v1) * c->P1) >> 33;
  if (v1 == 0) return 0;
  int64_t p = 1048576 - adc_p;
  p = (((p * ((int64_t)1 << 31)) - v2) * 3125) / v1;
  v1 = ((int64_t)c->P9 * (p >> 13) * (p >> 13)) >> 25;
  v2 = ((int64_t)c->P8 * p) >> 19;
  p = ((p + v1 + v2) >> 8) + ((int64_t)c->P7 << 4);
  return (uint32_t)p;
}

// lux = 2^exponent * mantissa * 0.045 → thousandths: (mantissa << exponent) * 45.
uint32_t max44009_millilux(uint8_t hi, uint8_t lo) {
  uint8_t e = hi >> 4;
  uint32_t m = (uint32_t)((hi & 0x0F) << 4 | (lo & 0x0F));
  if (e > 14) return UINT32_MAX;   // 15 = overrange according to the datasheet
  return (m << e) * 45u;
}

uint8_t bcd_to_bin(uint8_t bcd) { return (uint8_t)((bcd >> 4) * 10 + (bcd & 0x0F)); }

// Normal mode (10 bits, left-aligned), ±2 g: 4 mg per count.
int16_t lis2dh12_mg(uint8_t lo, uint8_t hi) { return (int16_t)(((int16_t)(hi << 8 | lo) >> 6) * 4); }

// ±4 G: 6842 counts per gauss.
int16_t lis3mdl_mgauss(uint8_t lo, uint8_t hi) {
  int32_t raw = (int16_t)(hi << 8 | lo);
  return (int16_t)(raw * 1000 / 6842);
}

// Gain 1/6 and internal 0.6 V reference → 3.6 V at 12-bit full scale.
uint16_t saadc_mv(int16_t raw) { return raw <= 0 ? 0 : (uint16_t)(((int32_t)raw * 3600 + 2048) / 4096); }

// r20: V(H) ≈ 5.825·AIN3 + 0.122 V (power supply set points, no metrology).
uint16_t f33_battery_mv(uint16_t ain3_mv) {
  if (ain3_mv < 100) return 0;
  return (uint16_t)((uint32_t)ain3_mv * 5825u / 1000u + 122u);
}

// Typical lithium-manganese cell discharge (plateau ~2.9–3.0 V, final drop).
static const struct { uint16_t mv; uint8_t pct; } CELL[] = {
  {3000, 100}, {2950, 90}, {2900, 80}, {2800, 60}, {2700, 40}, {2600, 20}, {2400, 5}, {2000, 0}};

uint8_t f33_battery_percent(uint16_t battery_mv) {
  uint32_t cell = battery_mv / 2u;   // 2S
  if (cell >= CELL[0].mv) return 100;
  for (size_t i = 1; i < sizeof CELL / sizeof CELL[0]; i++)
    if (cell >= CELL[i].mv) {
      uint32_t span = CELL[i - 1].mv - CELL[i].mv, dp = CELL[i - 1].pct - CELL[i].pct;
      return (uint8_t)(CELL[i].pct + (cell - CELL[i].mv) * dp / span);
    }
  return 0;
}

static uint8_t *put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); return p + 2; }
static uint8_t *put32(uint8_t *p, uint32_t v) { p = put16(p, (uint16_t)v); return put16(p, (uint16_t)(v >> 16)); }

size_t f33_pack(const f33_sample_t *s, uint8_t out[F33_PACKET_LEN]) {
  uint8_t *p = out;
  *p++ = F33_PACKET_VERSION;
  *p++ = s->flags;
  p = put16(p, s->seq);
  for (int i = 0; i < 3; i++) p = put16(p, (uint16_t)s->acc_mg[i]);
  for (int i = 0; i < 3; i++) p = put16(p, (uint16_t)s->mag_mgauss[i]);
  p = put16(p, (uint16_t)s->temp_centi);
  p = put32(p, s->press_q24_8);
  p = put32(p, s->millilux);
  p = put16(p, s->vdd_mv);
  p = put16(p, s->ain3_mv);
  *p++ = s->rtc_seconds;
  return (size_t)(p - out);
}
