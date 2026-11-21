#ifndef F33_EXAMPLE_PACKET_H
#define F33_EXAMPLE_PACKET_H
#include <stddef.h>
#include <stdint.h>

struct F33Packet {
  uint8_t version, flags;
  uint16_t seq;
  int16_t acc[3], mag[3], temp;
  uint32_t pressQ8, mlux;
  uint16_t vdd, ain3;
  uint8_t rtc;
};

inline uint16_t f33U16(const uint8_t *p) {
  return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
}
inline int16_t f33I16(const uint8_t *p) {
  const uint16_t v = f33U16(p);
  return v < 0x8000 ? int16_t(v) : int16_t(int32_t(v) - 65536);
}
inline uint32_t f33U32(const uint8_t *p) {
  return uint32_t(f33U16(p)) | (uint32_t(f33U16(p + 2)) << 16);
}
inline bool decodeF33(const uint8_t *data, size_t size, F33Packet &p) {
  if (!data || size != 31 || data[0] != 1) return false;
  p.version = data[0];
  p.flags = data[1];
  p.seq = f33U16(data + 2);
  for (unsigned i = 0; i < 3; ++i) {
    p.acc[i] = f33I16(data + 4 + 2 * i);
    p.mag[i] = f33I16(data + 10 + 2 * i);
  }
  p.temp = f33I16(data + 16);
  p.pressQ8 = f33U32(data + 18);
  p.mlux = f33U32(data + 22);
  p.vdd = f33U16(data + 26);
  p.ain3 = f33U16(data + 28);
  p.rtc = data[30];
  return true;
}
#endif
