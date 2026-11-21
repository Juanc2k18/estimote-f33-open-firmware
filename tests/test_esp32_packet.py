"""Compile the ESP32 example decoder on the host and compare protocol fixtures."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('c++'), 'C++ compiler required')
class Esp32Packet(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        source = Path(cls.tmp.name) / 'decode.cpp'
        source.write_text(r'''
#include "f33_packet.h"
#include <cstdio>
int main() {
  uint8_t data[64]; unsigned value; size_t n = 0;
  while (n < sizeof data && scanf("%x", &value) == 1) data[n++] = value;
  F33Packet p;
  if (!decodeF33(data, n, p)) return 2;
  printf("%u %u %u %d %d %d %d %d %d %d %lu %lu %u %u %u\n",
    p.version, p.flags, p.seq, p.acc[0], p.acc[1], p.acc[2],
    p.mag[0], p.mag[1], p.mag[2], p.temp,
    (unsigned long)p.pressQ8, (unsigned long)p.mlux, p.vdd, p.ain3, p.rtc);
}
''')
        cls.exe = Path(cls.tmp.name) / 'decode'
        subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                        '-I', str(ROOT / 'examples/esp32/f33_ble_reader'),
                        str(source), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_packet(self, data):
        return subprocess.run([str(self.exe)], input=data.hex(' '),
                              text=True, capture_output=True)

    def test_matches_existing_wire_layout(self):
        fields = (1, 63, 513, 12, -30, 1040, 1080, 750, -200,
                  2810, 100660 * 256, 22500, 1998, 1009, 42)
        result = self.run_packet(struct.pack('<BBH3h3hhIIHHB', *fields))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tuple(map(int, result.stdout.split())), fields)

    def test_signed_unsigned_boundaries_and_absent_sensors(self):
        fields = (1, 0, 65535, -32768, 32767, 0, -1, 1, -32768,
                  -32768, 0xffffffff, 0xffffffff, 65535, 0, 59)
        result = self.run_packet(struct.pack('<BBH3h3hhIIHHB', *fields))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(tuple(map(int, result.stdout.split())), fields)

    def test_rejects_incomplete_oversized_and_unknown_packets(self):
        for data in (b'', b'\x01' * 30, b'\x01' * 32, b'\x02' + bytes(30)):
            with self.subTest(length=len(data)):
                self.assertEqual(self.run_packet(data).returncode, 2)
