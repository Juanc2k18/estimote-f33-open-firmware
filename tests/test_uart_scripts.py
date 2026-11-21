"""UART host scripts: line reader, conversion and the dfu command."""
from pathlib import Path
import os
import threading
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import uart_sensors as us
import uart_dfu as ud


class Reader(unittest.TestCase):
    def test_splits_partial_chunks(self):
        r=us.LineReader()
        self.assertEqual(r.feed(b'{"seq":1}\n{"se'),['{"seq":1}'])
        self.assertEqual(r.feed(b'q":2}\r\n\n'),['{"seq":2}'])

    def test_drops_invalid_utf8_and_overflow(self):
        r=us.LineReader(limit=16)
        self.assertEqual(r.feed(b'\xff\xfe\n{"ok":"ver"}\n'),['{"ok":"ver"}'])
        r.feed(b'x'*40);self.assertEqual(r.feed(b'\n{"seq":3}\n'),['{"seq":3}'])


class Convert(unittest.TestCase):
    def test_only_present_sensors(self):
        d=us.to_decoded({'seq':7,'mlux':1000})
        self.assertEqual(d,{'version':1,'seq':7,'valid':dict(accel=False,magnet=False,baro=False,light=True,
                                                             rtc=False,adc=False),'light':{'lux':1.0}})


class RequestDfu(unittest.TestCase):
    def pty(self):
        m,s=os.openpty();self.addCleanup(os.close,m);self.addCleanup(os.close,s)
        return m,os.ttyname(s)

    def test_sends_dfu_and_waits_for_ok(self):
        m,name=self.pty();got=bytearray()
        def board():
            while b'dfu\n' not in got:got.extend(os.read(m,64))
            os.write(m,b'{"seq":1}\n{"ok":"dfu"}\n')
        th=threading.Thread(target=board,daemon=True);th.start()
        events=[];ud.request_dfu(name,115200,lambda **k:events.append(k));th.join(2)
        self.assertTrue(got.startswith(b'\ndfu\n'));self.assertEqual(events[-1]['kind'],'dfu_command_ok')

    def test_accepts_ok_after_stale_fragment(self):
        # When the port opens, the rest of an old line may arrive, without '\n', stuck to the reply.
        m,name=self.pty();got=bytearray()
        def board():
            while b'dfu\n' not in got:got.extend(os.read(m,64))
            os.write(m,b'{"seq":35,"acc_mg":[-4,{"ok":"dfu"}\n')
        th=threading.Thread(target=board,daemon=True);th.start()
        events=[];ud.request_dfu(name,115200,lambda **k:events.append(k));th.join(2)
        self.assertEqual(events[-1]['kind'],'dfu_command_ok')

    def test_timeout_without_reply(self):
        m,name=self.pty()
        with self.assertRaises(TimeoutError):ud.request_dfu(name,115200,lambda **k:None,timeout=0.3)


if __name__=='__main__':unittest.main()
