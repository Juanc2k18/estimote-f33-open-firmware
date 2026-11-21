// F3.3 I²C sensors (r36–r39) and SAADC (VDD, AIN3).
#ifndef SENSORS_H
#define SENSORS_H
#include "f33_math.h"

void sensors_power_on(void);   // P0.06/P0.07 high (H0H1): probable sensor power supply
void sensors_init(void);       // after ~1 s of power; retries on every reading if it failed
void sensors_read(f33_sample_t *s);   // fills in fields and flags; does not touch seq
void delay_us(uint32_t us);

#endif
