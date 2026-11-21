#include "sensors.h"
#include "nrf.h"
#include "twim.h"

#define ACC  0x19   // LIS2DH12
#define MAG  0x1E   // LIS3MDL
#define LUX  0x4A   // MAX44009 (probable)
#define RTC  0x68   // M41T62
#define BARO 0x77   // BMP280
#define AUTO_INC 0x80

static bmp280_cal_t cal;
static uint8_t ready;   // F33_* flags of the configured chips

void delay_us(uint32_t us) {
  // ~4 cycles per iteration at 64 MHz; precision does not matter here.
  for (volatile uint32_t n = us * 16u; n; n--) {}
}

void sensors_power_on(void) {
  for (int pin = 6; pin <= 7; pin++) {
    NRF_P0->OUTSET = 1u << pin;
    // High drive (H0H1), as rail_survey.py in r36–r39: probable sensor power supply.
    NRF_P0->PIN_CNF[pin] = GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos |
                           GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos |
                           GPIO_PIN_CNF_DRIVE_H0H1 << GPIO_PIN_CNF_DRIVE_Pos;
  }
}

static bool write_retry(uint8_t addr, uint8_t reg, uint8_t value) {
  for (int i = 0; i < 5; i++) {   // r37: 0x19 does not respond on the first attempt
    if (twim_write_reg(addr, reg, value)) return true;
    delay_us(2000);
  }
  return false;
}

static bool id_is(uint8_t addr, uint8_t reg, uint8_t expect) {
  uint8_t v = 0;
  for (int i = 0; i < 3; i++) {
    if (twim_read(addr, reg, &v, 1)) return v == expect;
    delay_us(2000);
  }
  return false;
}

static void init_missing(void) {
  if (!(ready & F33_ACC) && id_is(ACC, 0x0F, 0x33) &&
      write_retry(ACC, 0x20, 0x27) && write_retry(ACC, 0x23, 0x80))   // 10 Hz normal; BDU, ±2 g
    ready |= F33_ACC;
  if (!(ready & F33_MAG) && id_is(MAG, 0x0F, 0x3D) &&
      write_retry(MAG, 0x20, 0x10) && write_retry(MAG, 0x21, 0x00) &&   // 10 Hz low power; ±4 G
      write_retry(MAG, 0x22, 0x03))                                     // powered down between readings
    ready |= F33_MAG;
  if (!(ready & F33_BARO) && id_is(BARO, 0xD0, 0x58)) {
    uint8_t raw[24];
    if (twim_read(BARO, 0x88, raw, sizeof raw) && write_retry(BARO, 0xF5, 0x00)) {
      bmp280_cal_parse(raw, &cal);
      ready |= F33_BARO;
    }
  }
  ready |= F33_LIGHT | F33_RTC;   // no configuration: validated on every reading
}

void sensors_init(void) {
  twim_init();
  NRF_SAADC->RESOLUTION = SAADC_RESOLUTION_VAL_12bit;
  uint32_t cfg = SAADC_CH_CONFIG_GAIN_Gain1_6 << SAADC_CH_CONFIG_GAIN_Pos |
                 SAADC_CH_CONFIG_REFSEL_Internal << SAADC_CH_CONFIG_REFSEL_Pos |
                 SAADC_CH_CONFIG_TACQ_10us << SAADC_CH_CONFIG_TACQ_Pos;
  NRF_SAADC->CH[0].CONFIG = cfg;
  NRF_SAADC->CH[0].PSELP = SAADC_CH_PSELP_PSELP_VDD;
  NRF_SAADC->CH[1].CONFIG = cfg;
  NRF_SAADC->CH[1].PSELP = SAADC_CH_PSELP_PSELP_AnalogInput3;   // P0.05
  NRF_SAADC->ENABLE = 1;
  NRF_SAADC->EVENTS_CALIBRATEDONE = 0;
  NRF_SAADC->TASKS_CALIBRATEOFFSET = 1;
  for (uint32_t n = 0; !NRF_SAADC->EVENTS_CALIBRATEDONE && n < 100000; n++) {}
  NRF_SAADC->ENABLE = 0;
  init_missing();
}

static bool read_adc(f33_sample_t *s) {
  static volatile int16_t res[2];
  NRF_SAADC->ENABLE = 1;
  NRF_SAADC->RESULT.PTR = (uint32_t)res;
  NRF_SAADC->RESULT.MAXCNT = 2;
  NRF_SAADC->EVENTS_STARTED = NRF_SAADC->EVENTS_END = NRF_SAADC->EVENTS_STOPPED = 0;
  NRF_SAADC->TASKS_START = 1;
  uint32_t n = 0;
  while (!NRF_SAADC->EVENTS_STARTED && ++n < 100000) {}
  NRF_SAADC->TASKS_SAMPLE = 1;   // scan mode: both channels
  while (!NRF_SAADC->EVENTS_END && ++n < 200000) {}
  bool ok = NRF_SAADC->EVENTS_END;
  NRF_SAADC->TASKS_STOP = 1;
  while (!NRF_SAADC->EVENTS_STOPPED && ++n < 300000) {}
  NRF_SAADC->ENABLE = 0;
  s->vdd_mv = saadc_mv(res[0]);
  s->ain3_mv = saadc_mv(res[1]);
  return ok;
}

static bool read_acc(f33_sample_t *s) {
  uint8_t d[6];
  if (!twim_read(ACC, 0x28 | AUTO_INC, d, 6)) return false;
  for (int i = 0; i < 3; i++) s->acc_mg[i] = lis2dh12_mg(d[2 * i], d[2 * i + 1]);
  return true;
}

static bool read_mag(f33_sample_t *s) {
  uint8_t st = 0, d[6];
  if (!twim_write_reg(MAG, 0x22, 0x01)) return false;   // single conversion
  for (int i = 0; i < 50 && !(st & 0x08); i++) {        // ZYXDA, up to ~50 ms
    delay_us(1000);
    if (!twim_read(MAG, 0x27, &st, 1)) return false;
  }
  if (!(st & 0x08) || !twim_read(MAG, 0x28 | AUTO_INC, d, 6)) return false;
  for (int i = 0; i < 3; i++) s->mag_mgauss[i] = lis3mdl_mgauss(d[2 * i], d[2 * i + 1]);
  return true;
}

static bool read_baro(f33_sample_t *s) {
  uint8_t st = 0x08, d[6];
  if (!twim_write_reg(BARO, 0xF4, 0x25)) return false;  // forced, ×1/×1
  for (int i = 0; i < 20 && (st & 0x08); i++) {         // measuring
    delay_us(2000);
    if (!twim_read(BARO, 0xF3, &st, 1)) return false;
  }
  if ((st & 0x08) || !twim_read(BARO, 0xF7, d, 6)) return false;
  int32_t adc_p = (int32_t)(d[0] << 12 | d[1] << 4 | d[2] >> 4);
  int32_t adc_t = (int32_t)(d[3] << 12 | d[4] << 4 | d[5] >> 4);
  int32_t fine;
  s->temp_centi = (int16_t)bmp280_temp_centi(&cal, adc_t, &fine);
  s->press_q24_8 = bmp280_press_q24_8(&cal, adc_p, fine);
  return true;
}

static bool read_light(f33_sample_t *s) {
  uint8_t hi, lo;
  if (!twim_read(LUX, 0x03, &hi, 1) || !twim_read(LUX, 0x04, &lo, 1)) return false;
  s->millilux = max44009_millilux(hi, lo);
  return true;
}

static bool read_rtc(f33_sample_t *s) {
  uint8_t v;
  if (!twim_read(RTC, 0x01, &v, 1)) return false;
  s->rtc_seconds = bcd_to_bin(v & 0x7F);
  return true;
}

void sensors_read(f33_sample_t *s) {
  init_missing();
  uint8_t ok = 0;
  if ((ready & F33_ACC) && read_acc(s)) ok |= F33_ACC;
  if ((ready & F33_MAG) && read_mag(s)) ok |= F33_MAG;
  if ((ready & F33_BARO) && read_baro(s)) ok |= F33_BARO;
  if (read_light(s)) ok |= F33_LIGHT;
  if (read_rtc(s)) ok |= F33_RTC;
  if (read_adc(s)) ok |= F33_ADC;
  // A chip that stops responding is configured again on the next reading.
  ready &= (uint8_t)(ok | F33_LIGHT | F33_RTC);
  s->flags = ok;
}
