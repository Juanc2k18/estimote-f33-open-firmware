"""BLE firmware calculations (compiled on the Mac with ctypes) and the Python decoder."""
import ctypes
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import f33_packet as fp

FW=ROOT/'firmware'/'ble-sensors'
# Example from the BMP280 datasheet (section 8.2): 25.08 °C, 100653.27 Pa.
CAL=(27504,26435,-1000,36477,-10685,3024,2855,140,-7,15500,-14600,6000)


class Sample(ctypes.Structure):
    _fields_=[('flags',ctypes.c_uint8),('seq',ctypes.c_uint16),('acc_mg',ctypes.c_int16*3),
              ('mag_mgauss',ctypes.c_int16*3),('temp_centi',ctypes.c_int16),('press_q24_8',ctypes.c_uint32),
              ('millilux',ctypes.c_uint32),('vdd_mv',ctypes.c_uint16),('ain3_mv',ctypes.c_uint16),
              ('rtc_seconds',ctypes.c_uint8)]


@unittest.skipUnless(shutil.which('cc'),'no C compiler on the Mac')
class FirmwareMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();lib=Path(cls.tmp.name)/'libf33.so'
        subprocess.run(['cc','-std=c11','-Wall','-Werror','-O2','-shared','-fPIC','-o',lib,FW/'f33_math.c'],check=True)
        cls.lib=L=ctypes.CDLL(str(lib))
        L.bmp280_temp_centi.restype=ctypes.c_int32
        L.bmp280_temp_centi.argtypes=[ctypes.c_void_p,ctypes.c_int32,ctypes.POINTER(ctypes.c_int32)]
        L.bmp280_press_q24_8.restype=ctypes.c_uint32
        L.bmp280_press_q24_8.argtypes=[ctypes.c_void_p,ctypes.c_int32,ctypes.c_int32]
        for name,res,args in (('max44009_millilux',ctypes.c_uint32,[ctypes.c_uint8]*2),
                              ('bcd_to_bin',ctypes.c_uint8,[ctypes.c_uint8]),
                              ('lis2dh12_mg',ctypes.c_int16,[ctypes.c_uint8]*2),
                              ('lis3mdl_mgauss',ctypes.c_int16,[ctypes.c_uint8]*2),
                              ('saadc_mv',ctypes.c_uint16,[ctypes.c_int16]),
                              ('f33_battery_mv',ctypes.c_uint16,[ctypes.c_uint16]),
                              ('f33_battery_percent',ctypes.c_uint8,[ctypes.c_uint16]),
                              ('f33_pack',ctypes.c_size_t,[ctypes.POINTER(Sample),ctypes.c_char_p])):
            f=getattr(L,name);f.restype=res;f.argtypes=args

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_bmp280_datasheet_example(self):
        raw=struct.pack('<HhhHhhhhhhhh',*CAL);cal=ctypes.create_string_buffer(64)
        self.lib.bmp280_cal_parse(raw,cal)
        fine=ctypes.c_int32()
        self.assertEqual(self.lib.bmp280_temp_centi(cal,519888,ctypes.byref(fine)),2508)
        self.assertAlmostEqual(self.lib.bmp280_press_q24_8(cal,415148,fine.value)/256,100653.27,delta=1)

    def test_conversions(self):
        L=self.lib
        self.assertEqual(L.max44009_millilux(0x00,0x01),45)
        self.assertEqual(L.max44009_millilux(0x3F,0x0F),255*8*45)
        self.assertEqual(L.max44009_millilux(0xEF,0x0F),255*(1<<14)*45)
        self.assertEqual(L.max44009_millilux(0xF0,0x00),0xFFFFFFFF)
        self.assertEqual(L.bcd_to_bin(0x59),59)
        self.assertEqual(L.lis2dh12_mg(0x00,0x40),1024)       # 0x4000>>6 = 256 counts
        self.assertEqual(L.lis2dh12_mg(0xC0,0xFF),-4)
        self.assertEqual(L.lis3mdl_mgauss(0xBA,0x1A),1000)    # 6842 = 0x1ABA
        self.assertEqual(L.saadc_mv(4096),3600);self.assertEqual(L.saadc_mv(-3),0)

    def test_pack_matches_python_decoder(self):
        s=Sample(flags=0x3F,seq=513,acc_mg=(12,-30,1040),mag_mgauss=(1080,750,-200),temp_centi=2810,
                 press_q24_8=int(100660*256),millilux=22500,vdd_mv=1998,ain3_mv=1009,rtc_seconds=42)
        buf=ctypes.create_string_buffer(fp.LAYOUT.size)
        self.assertEqual(self.lib.f33_pack(ctypes.byref(s),buf),fp.LAYOUT.size)
        d=fp.decode(buf.raw)
        self.assertEqual(d['seq'],513);self.assertEqual(d['accel']['g'],[0.012,-0.03,1.04])
        self.assertEqual(d['magnet']['gauss'],[1.08,0.75,-0.2])
        self.assertEqual(d['baro'],dict(temp_c=28.1,pressure_hpa=1006.6))
        self.assertEqual(d['light']['lux'],22.5);self.assertEqual(d['rtc_seconds'],42)
        self.assertEqual(d['adc']['battery_v_estimate'],5.999)
        self.assertEqual(d['adc']['battery_percent'],99)

    def test_battery_fit_matches_r20_curve(self):
        # r20: H/F set to 3/4/5/6 V → AIN3 0.494/0.668/0.838/1.009 V.
        for ain3,volts in ((494,3),(668,4),(838,5),(1009,6)):
            self.assertAlmostEqual(self.lib.f33_battery_mv(ain3)/1000,volts,delta=0.03)
        self.assertEqual(self.lib.f33_battery_mv(50),0)        # AIN3 almost 0: no battery on H

    def test_battery_percent(self):
        P=self.lib.f33_battery_percent
        self.assertEqual(P(6000),100);self.assertEqual(P(6573),100)   # 2S, 3.0 V per cell
        self.assertEqual(P(5800),80);self.assertEqual(P(5600),60)     # 2S, 2.9 and 2.8 V
        self.assertEqual(P(5400),40);self.assertEqual(P(4800),5)
        self.assertEqual(P(3300),0);self.assertEqual(P(0),0)          # 3.3 V = 1.65 V/cell: depleted

    def test_python_battery_matches_c(self):
        for ain3 in range(0,1200,7):
            mv=self.lib.f33_battery_mv(ain3)
            self.assertEqual(fp.battery_mv(ain3),mv)
            self.assertEqual(fp.battery_percent(mv),self.lib.f33_battery_percent(mv))


class Decoder(unittest.TestCase):
    def test_invalid_sensors_are_omitted(self):
        data=fp.LAYOUT.pack(1,0b001000,7,0,0,0,0,0,0,0,0,1000,0,0,0)
        d=fp.decode(data)
        self.assertEqual(set(d)-{'version','seq','valid'},{'light'});self.assertFalse(d['valid']['accel'])

    def test_rejects_bad_length_and_version(self):
        with self.assertRaises(ValueError):fp.decode(b'\x01'*10)
        with self.assertRaises(ValueError):fp.decode(fp.LAYOUT.pack(2,*([0]*14)))


if __name__=='__main__':unittest.main()
