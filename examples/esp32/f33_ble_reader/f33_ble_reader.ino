// Arduino-ESP32 3.3.10; built-in BLE library. No external libraries required.
// Reads sensor data only. Does not write control commands or upload firmware.
#include <Arduino.h>
#include <soc/soc_caps.h>
#if !SOC_BLE_SUPPORTED
#error "This ESP32 chip has no native Bluetooth LE support."
#endif
#include <BLEDevice.h>
#include "f33_packet.h"

// Optional ESP32-visible MAC, e.g. "aa:bb:cc:dd:ee:ff" (not a macOS UUID).
// Empty: connect only when exactly one F33 is found in the scan.
const char *TARGET_MAC = "";
const BLEUUID SERVICE("239d0001-86eb-4a92-8ec1-0e38f13e0817");
const BLEUUID DATA("239d0002-86eb-4a92-8ec1-0e38f13e0817");
BLEClient *client = nullptr;
BLERemoteCharacteristic *dataCharacteristic = nullptr;
uint8_t badReads = 0;

void printSample(const F33Packet &p) {
  Serial.printf("seq=%u valid=0x%02x", p.seq, p.flags);
  if (p.flags & 1) Serial.printf(" acc_g=[%.3f,%.3f,%.3f]", p.acc[0]/1000.0, p.acc[1]/1000.0, p.acc[2]/1000.0);
  if (p.flags & 2) Serial.printf(" mag_G=[%.3f,%.3f,%.3f]", p.mag[0]/1000.0, p.mag[1]/1000.0, p.mag[2]/1000.0);
  if (p.flags & 4) Serial.printf(" temp_C=%.2f pressure_hPa=%.2f", p.temp/100.0, p.pressQ8/25600.0);
  if (p.flags & 8) Serial.printf(" light_lux=%.3f", p.mlux/1000.0);
  if (p.flags & 16) Serial.printf(" rtc_s=%u", p.rtc);
  if (p.flags & 32) Serial.printf(" vdd_mV=%u ain3_mV=%u", p.vdd, p.ain3);
  Serial.println();
}

bool connectF33() {
  BLEScan *scan = BLEDevice::getScan();
  Serial.println("# Scanning for F33...");
  BLEScanResults *results = scan->start(4, false);
  if (!results) return false;
  int selected = -1, matches = 0;
  for (int i = 0; i < results->getCount(); ++i) {
    BLEAdvertisedDevice peer = results->getDevice(i);
    if (!peer.haveName() || peer.getName() != "F33") continue;
    String address = peer.getAddress().toString();
    Serial.printf("# F33: %s\n", address.c_str());
    if (*TARGET_MAC && !address.equalsIgnoreCase(TARGET_MAC)) continue;
    selected = i;
    ++matches;
  }
  if (matches != 1) {
    Serial.println(matches ? "# Multiple F33 devices; set TARGET_MAC" : "# Target not found");
    scan->clearResults();
    return false;
  }
  BLEAdvertisedDevice peer = results->getDevice(selected);
  const bool connected = client->connect(&peer);
  scan->clearResults();
  if (!connected) return false;
  client->setMTU(64);  // Request room for all 31 bytes; length is checked below.
  client->getServices();  // Refresh cached handles after each reconnection.
  BLERemoteService *service = client->getService(SERVICE);
  dataCharacteristic = service ? service->getCharacteristic(DATA) : nullptr;
  if (!dataCharacteristic || !dataCharacteristic->canRead()) {
    Serial.println("# F33 data characteristic unavailable");
    dataCharacteristic = nullptr;
    client->disconnect();
    return false;
  }
  badReads = 0;
  Serial.println("# Connected; reading once per second");
  return true;
}

void setup() {
  Serial.begin(115200);
  BLEDevice::init("F33-reader");
  client = BLEDevice::createClient();  // One client reused across reconnections.
  BLEDevice::getScan()->setActiveScan(true);  // Service UUID is in scan response.
}

void loop() {
  if (!client->isConnected()) {
    dataCharacteristic = nullptr;
    connectF33();
    delay(1000);
    return;
  }
  if (!dataCharacteristic) {
    client->disconnect();
    delay(1000);
    return;
  }
  String raw = dataCharacteristic->readValue();
  F33Packet packet;
  if (decodeF33(reinterpret_cast<const uint8_t *>(raw.c_str()), raw.length(), packet)) {
    printSample(packet);
    badReads = 0;
  } else {
    Serial.printf("# Invalid packet: length=%u; expected 31 bytes, version 1\n", unsigned(raw.length()));
    if (++badReads >= 3) {
      dataCharacteristic = nullptr;
      client->disconnect();
    }
  }
  delay(1000);
}
