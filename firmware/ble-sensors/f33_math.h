// Pure calculations of the F3.3 BLE application: no registers, also compiled on the Mac.
#ifndef F33_MATH_H
#define F33_MATH_H
#include <stddef.h>
#include <stdint.h>

#define F33_PACKET_VERSION 1
#define F33_PACKET_LEN     31

enum { F33_ACC = 1u << 0, F33_MAG = 1u << 1, F33_BARO = 1u << 2,
       F33_LIGHT = 1u << 3, F33_RTC = 1u << 4, F33_ADC = 1u << 5 };

typedef struct {
  uint16_t T1; int16_t T2, T3;
  uint16_t P1; int16_t P2, P3, P4, P5, P6, P7, P8, P9;
} bmp280_cal_t;

typedef struct {
  uint8_t  flags;
  uint16_t seq;
  int16_t  acc_mg[3];
  int16_t  mag_mgauss[3];
  int16_t  temp_centi;
  uint32_t press_q24_8;
  uint32_t millilux;
  uint16_t vdd_mv;
  uint16_t ain3_mv;
  uint8_t  rtc_seconds;
} f33_sample_t;

void     bmp280_cal_parse(const uint8_t raw[24], bmp280_cal_t *c);
int32_t  bmp280_temp_centi(const bmp280_cal_t *c, int32_t adc_t, int32_t *t_fine);
uint32_t bmp280_press_q24_8(const bmp280_cal_t *c, int32_t adc_p, int32_t t_fine);
uint32_t max44009_millilux(uint8_t hi, uint8_t lo);
uint8_t  bcd_to_bin(uint8_t bcd);
int16_t  lis2dh12_mg(uint8_t lo, uint8_t hi);
int16_t  lis3mdl_mgauss(uint8_t lo, uint8_t hi);
uint16_t saadc_mv(int16_t raw);
// Battery on H/F (r45, provisional): linear fit of the r20 curve and a per-cell table for a
// CR-type lithium cell, with two cells in series (owner: the original firmware only showed
// 100 % between 6 and 6.5 V, and less at 3.3 V).
uint16_t f33_battery_mv(uint16_t ain3_mv);
uint8_t  f33_battery_percent(uint16_t battery_mv);
size_t   f33_pack(const f33_sample_t *s, uint8_t out[F33_PACKET_LEN]);

#endif
