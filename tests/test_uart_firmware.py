"""JSON format and UART commands of the F3.3 firmware (f33_uart.c), compiled on the Mac."""
import ctypes
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_ble_firmware import FW,Sample,fp
import uart_sensors as us

READ,INT,VER,DFU,OTA,ERR_CMD,ERR_RANGE,ERR_LONG=range(1,9)


class Line(ctypes.Structure):
    _fields_=[('buf',ctypes.c_char*33),('len',ctypes.c_uint8),('overflow',ctypes.c_bool),('bad',ctypes.c_bool)]


def full_sample():
    return Sample(flags=0x3F,seq=513,acc_mg=(12,-30,1040),mag_mgauss=(1080,750,-200),temp_centi=2810,
                  press_q24_8=100660*256+200,millilux=22500,vdd_mv=1998,ain3_mv=1009,rtc_seconds=42)


@unittest.skipUnless(shutil.which('cc'),'no C compiler on the Mac')
class UartFormat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();lib=Path(cls.tmp.name)/'libf33uart.so'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','-fPIC','-o',lib,
                        FW/'f33_uart.c',FW/'f33_math.c'],check=True)
        cls.lib=L=ctypes.CDLL(str(lib))
        L.f33_pack.restype=ctypes.c_size_t
        L.f33_pack.argtypes=[ctypes.POINTER(Sample),ctypes.c_char_p]
        L.f33_json_line.restype=ctypes.c_size_t
        L.f33_json_line.argtypes=[ctypes.POINTER(Sample),ctypes.c_char_p,ctypes.c_size_t]
        L.f33_parse_cmd.restype=ctypes.c_int
        L.f33_parse_cmd.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_uint32)]
        L.f33_line_feed.restype=ctypes.c_int
        L.f33_line_feed.argtypes=[ctypes.POINTER(Line),ctypes.c_uint8]
        L.f33_reply.restype=ctypes.c_size_t
        L.f33_reply.argtypes=[ctypes.c_int,ctypes.c_uint32,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_size_t]

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def json_line(self,s,size=224):
        buf=ctypes.create_string_buffer(size);n=self.lib.f33_json_line(ctypes.byref(s),buf,size)
        return n,buf.value.decode()

    def parse(self,text):
        arg=ctypes.c_uint32(0);c=self.lib.f33_parse_cmd(text.encode(),ctypes.byref(arg));return c,arg.value

    def reply(self,cmd,arg=0):
        buf=ctypes.create_string_buffer(64);n=self.lib.f33_reply(cmd,arg,b'1.0.0',buf,64)
        return n,buf.value.decode()

    def test_json_full_line(self):
        n,line=self.json_line(full_sample())
        self.assertEqual(line,'{"seq":513,"acc_mg":[12,-30,1040],"mag_mg":[1080,750,-200],"temp_cc":2810,'
                              '"press_pa":100660,"mlux":22500,"rtc_s":42,"vdd_mv":1998,"ain3_mv":1009,'
                              '"bat_mv":5999,"bat_pct":99}\n')
        self.assertEqual(n,len(line));json.loads(line)

    def test_json_omits_invalid_sensors(self):
        s=full_sample();s.flags=1<<3   # light only
        self.assertEqual(json.loads(self.json_line(s)[1]),{'seq':513,'mlux':22500})

    def test_json_worst_case_fits_and_overflow_returns_zero(self):
        s=Sample(flags=0x3F,seq=65535,acc_mg=(-32768,)*3,mag_mgauss=(-32768,)*3,temp_centi=-32768,
                 press_q24_8=0xFFFFFFFF,millilux=0xFFFFFFFF,vdd_mv=65535,ain3_mv=65535,rtc_seconds=255)
        n,line=self.json_line(s)
        self.assertGreater(n,0);self.assertLess(n,224);json.loads(line)
        self.assertEqual(self.json_line(s,100),(0,''))

    def test_parse_commands(self):
        cases={'read':(READ,0),'READ':(READ,0),'  read  ':(READ,0),'ver':(VER,0),'dfu':(DFU,0),'ota':(OTA,0),
               'int 5':(INT,5),'INT 3600':(INT,3600),'int 1':(INT,1),'int   7 ':(INT,7),
               'int 0':(ERR_RANGE,0),'int 3601':(ERR_RANGE,0),'int 99999999':(ERR_RANGE,0),
               'int':(ERR_CMD,0),'int x':(ERR_CMD,0),'int 5x':(ERR_CMD,0),'reads':(ERR_CMD,0),
               'dfux':(ERR_CMD,0),'hello':(ERR_CMD,0),'':(0,0),'   ':(0,0)}
        for text,want in cases.items():
            with self.subTest(text=text):self.assertEqual(self.parse(text),want)

    def test_line_feed(self):
        line=Line();feed=lambda data:[self.lib.f33_line_feed(ctypes.byref(line),b) for b in data]
        self.assertEqual(feed(b'read\r\n'),[0,0,0,0,0,1]);self.assertEqual(line.buf,b'read')
        self.assertEqual(feed(b'a'*40+b'\n')[-1],-1)
        self.assertEqual(feed(b'\xc0ab\n')[-1],-2)
        self.assertEqual(feed(b'ver\n')[-1],1);self.assertEqual(line.buf,b'ver')   # clean state after errors
        # Empty line (the scripts prepend '\n'): does not take the slot of the next command.
        self.assertEqual(feed(b'\n\r\n'),[0,0,0]);self.assertEqual(feed(b'\ndfu\n'),[0,0,0,0,1])

    def test_replies(self):
        self.assertEqual(self.reply(READ)[1],'{"ok":"read"}\n')
        self.assertEqual(self.reply(INT,5)[1],'{"ok":"int","s":5}\n')
        self.assertEqual(self.reply(VER)[1],'{"ok":"ver","fw":"1.0.0"}\n')
        self.assertEqual(self.reply(DFU)[1],'{"ok":"dfu"}\n')
        self.assertEqual(self.reply(OTA)[1],'{"ok":"ota"}\n')
        self.assertEqual(self.reply(ERR_CMD)[1],'{"err":"cmd"}\n')
        self.assertEqual(self.reply(ERR_RANGE)[1],'{"err":"range"}\n')
        self.assertEqual(self.reply(ERR_LONG)[1],'{"err":"long"}\n')
        self.assertEqual(self.reply(0),(0,''))

    def test_uart_reader_matches_ble_decoder(self):
        s=full_sample();s.press_q24_8=100660*256   # exact Pa: the JSON rounds to Pa
        pkt=ctypes.create_string_buffer(fp.LAYOUT.size)
        self.lib.f33_pack(ctypes.byref(s),pkt)
        self.assertEqual(us.to_decoded(json.loads(self.json_line(s)[1])),fp.decode(pkt.raw))


if __name__=='__main__':unittest.main()
