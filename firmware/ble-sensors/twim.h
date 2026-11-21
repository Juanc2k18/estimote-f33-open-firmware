// I²C master on TWIM0 on the sensor bus (SDA=P0.14, SCL=P0.15).
#ifndef TWIM_H
#define TWIM_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

void twim_init(void);
bool twim_write(uint8_t addr, const uint8_t *data, size_t len);
// Writes `reg` and reads `len` bytes with a repeated START.
bool twim_read(uint8_t addr, uint8_t reg, uint8_t *data, size_t len);
bool twim_write_reg(uint8_t addr, uint8_t reg, uint8_t value);

#endif
