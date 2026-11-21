// Arduino-ESP32 3.3.10. USB serial monitor: 115200 baud.
// E3: regulated 3.3 V; E4: common GND. H and C disconnected.
// Check the README and your ESP32 board before wiring these example GPIOs.
#include <Arduino.h>

#if CONFIG_IDF_TARGET_ESP32
constexpr int F33_RX_PIN = 16;  // ESP32 RX <- F3.3 E1 (TX)
constexpr int F33_TX_PIN = 17;  // ESP32 TX -> F3.3 E2 (RX)
#elif CONFIG_IDF_TARGET_ESP32S3
constexpr int F33_RX_PIN = 18;
constexpr int F33_TX_PIN = 17;
#elif CONFIG_IDF_TARGET_ESP32C3
constexpr int F33_RX_PIN = 4;
constexpr int F33_TX_PIN = 5;
#else
#error "Choose available RX/TX GPIOs for your board before using this example."
#endif

HardwareSerial f33(1);
char line[256];
size_t used = 0;
bool overflow = false;

void setup() {
  Serial.begin(115200);
  f33.begin(115200, SERIAL_8N1, F33_RX_PIN, F33_TX_PIN);
  // TX stays idle high, enabling the F3.3 UART. No commands are transmitted.
  Serial.println("# F33 UART reader; JSON lines below (115200 8N1)");
}

void loop() {
  while (f33.available()) {
    const char c = static_cast<char>(f33.read());
    if (c == '\r') continue;
    if (c == '\n') {
      line[used] = '\0';
      if (overflow) Serial.println("# UART line too long; discarded");
      else if (used && line[0] == '{') Serial.println(line);
      used = 0;
      overflow = false;
    } else if (!overflow) {
      if (used < sizeof(line) - 1) line[used++] = c;
      else overflow = true;  // Discard until newline, then recover.
    }
  }
  delay(1);
}
