"""Regression tests through the real CLI and a PTY; independent r15 fixtures."""
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import threading
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'dfu_ping.py'
REQUEST = bytes.fromhex('c0 d1 4e 00 e1 7f 00 00 00 aa a8 c0')
ACK = bytes.fromhex('c0 10 00 00 f0 c0')


class CLITests(unittest.TestCase):
    def run_peer(self, reply):
        master, slave = pty.openpty()
        stop = threading.Event()
        seen = []
        def peer():
            buf = b''
            while not stop.is_set():
                ready, _, _ = select.select([master], [], [], .02)
                if not ready:
                    continue
                data = os.read(master, 4096)
                buf += data
                while b'\xc0' in buf:
                    start = buf.find(b'\xc0')
                    end = buf.find(b'\xc0', start + 1)
                    if end < 0:
                        buf = buf[start:]
                        break
                    packet, buf = buf[start:end+1], buf[end+1:]
                    if len(packet) > 2:
                        seen.append(packet)
                        for part in reply(packet):
                            os.write(master, part)
                            time.sleep(.01)
        thread = threading.Thread(target=peer)
        thread.start()
        try:
            result = subprocess.run([sys.executable, str(SCRIPT), os.ttyname(slave)],
                                    capture_output=True, text=True, timeout=6)
            return result, seen
        finally:
            stop.set()
            thread.join()
            os.close(master)
            os.close(slave)

    def test_echo_is_not_ack(self):
        result, seen = self.run_peer(lambda packet: [packet])
        self.assertTrue(seen)
        self.assertEqual(result.returncode, 1, result.stdout)

    def test_r15_ack_and_request(self):
        result, seen = self.run_peer(lambda packet: [ACK])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(seen[0], REQUEST)

    def test_fragmented_ack(self):
        result, _ = self.run_peer(lambda packet: [ACK[:2], ACK[2:4], ACK[4:]])
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_echo_then_ack(self):
        result, _ = self.run_peer(lambda packet: [packet, ACK])
        self.assertEqual(result.returncode, 0)

    def test_bad_frames_and_silence_fail(self):
        for data in (b'', ACK[:-1], bytes.fromhex('c0 10 00 00 f1 c0'),
                     bytes.fromhex('c0 38 00 00 c8 c0'),
                     bytes.fromhex('c0 50 00 00 b0 c0'),
                     bytes.fromhex('c0 10 01 00 ef c0'),
                     bytes.fromhex('c0 10 10 00 e0 c0')):
            with self.subTest(data=data.hex()):
                result, _ = self.run_peer(lambda packet: [data] if data else [])
                self.assertEqual(result.returncode, 1, result.stdout)

# These tests detect sequences that do not advance, loss of evidence,
# reopening on every sample and disconnections that end the monitor.
import contextlib
import importlib.util
import json
import signal
import tempfile


@contextlib.contextmanager
def monitor_peer(reply, count=20, extra=()):
    master, slave = pty.openpty()
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / 'run.jsonl'
        proc = subprocess.Popen([sys.executable, str(SCRIPT), os.ttyname(slave),
                                 '--watch', '--interval', '.01', '--timeout', '.07',
                                 '--count', str(count), '--log', str(log), *extra],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        seen = []
        try:
            deadline = time.monotonic() + 8
            buf = b''
            while proc.poll() is None and time.monotonic() < deadline:
                if not select.select([master], [], [], .01)[0]:
                    continue
                buf += os.read(master, 4096)
                while len(buf) > 1:
                    start = buf.find(b'\xc0')
                    end = buf.find(b'\xc0', start+1)
                    if start < 0 or end < 0:
                        break
                    packet, buf = buf[start:end+1], buf[end+1:]
                    if len(packet) > 2:
                        seen.append(packet)
                        response = reply(packet, len(seen))
                        if response:
                            os.write(master, response)
            out, err = proc.communicate(timeout=2)
            rows = [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []
            yield proc.returncode, out, err, rows, seen
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.communicate()
            os.close(master)
            os.close(slave)


def wire_ack(number):
    # Independent of the production builder: ACK format from ack_transmit.
    return bytes([0xC0, number*8, 0, 0, (-number*8) & 255, 0xC0])


class WatchTests(unittest.TestCase):
    def test_wrap_duplicates_and_log_summary(self):
        def reply(packet, index):
            seq = packet[1] & 7
            return wire_ack(seq) + wire_ack((seq+1) % 8)*2
        with monitor_peer(reply) as (code, out, err, rows, seen):
            self.assertEqual(code, 0, err)
            self.assertEqual(len(rows), 20)
            self.assertEqual([row['sequence'] for row in rows], [1,2,3,4,5,6,7,0]*2+[1,2,3,4])
            self.assertTrue(all(row['result'] == 'ack' for row in rows))
            self.assertIn('"ack": 20', out)
            self.assertIn('"attempts": 20', out)
            for row in rows:
                self.assertRegex(row['time'], r'[+-]\d\d:\d\d$')
                self.assertTrue(row['tx_hex'].startswith('c0 '))
                self.assertTrue(row['rx_hex'].endswith(' c0'))
                self.assertIsNotNone(row['latency_ms'])
                self.assertEqual(row['baud'], 115200)

    def test_lost_ack_retries_same_sequence(self):
        def reply(packet, index):
            return b'' if index == 2 else wire_ack(((packet[1] & 7)+1) % 8)
        with monitor_peer(reply, count=4) as (code, out, err, rows, seen):
            self.assertEqual(code, 0, err)
            self.assertEqual([r['sequence'] for r in rows], [1,2,2,3])
            self.assertEqual([r['result'] for r in rows], ['ack','silence','ack','ack'])

    def test_previous_session_resynchronizes_without_counting_ack(self):
        def reply(packet, index):
            return wire_ack(6) if index == 1 else wire_ack(((packet[1] & 7)+1) % 8)
        with monitor_peer(reply, count=3) as (code, out, err, rows, seen):
            self.assertEqual(code, 0, err)
            self.assertEqual([r['sequence'] for r in rows], [1,6,7])
            self.assertEqual([r['result'] for r in rows], ['resync','ack','ack'])
            self.assertIn('"ack": 2', out)

    def test_missing_port_and_bad_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp)/'missing.jsonl'
            proc = subprocess.run([sys.executable, str(SCRIPT), str(Path(tmp)/'absent'),
                                   '--watch','--interval','.01','--count','2','--log',str(log)],
                                  capture_output=True, text=True, timeout=2)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            rows = [json.loads(x) for x in log.read_text().splitlines()]
            self.assertEqual([r['result'] for r in rows], ['port_absent']*2)
            for flag, value in (('--interval','0'),('--interval','nan'),('--interval','inf'),
                                ('--count','0'),('--count','-1'),('--timeout','0')):
                result = subprocess.run([sys.executable, str(SCRIPT), '/absent', flag, value], capture_output=True)
                self.assertEqual(result.returncode, 2)

    def test_ctrl_c_flushes_inflight_attempt(self):
        master, slave = pty.openpty()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                log = Path(tmp)/'interrupt.jsonl'
                proc = subprocess.Popen([sys.executable,str(SCRIPT),os.ttyname(slave),
                    '--watch','--log',str(log)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                try:
                    self.assertTrue(select.select([master],[],[],2)[0])
                    self.assertTrue(os.read(master,4096))
                    proc.send_signal(signal.SIGINT)
                    out, err = proc.communicate(timeout=2)
                    self.assertEqual(proc.returncode,130,err)
                    rows = [json.loads(x) for x in log.read_text().splitlines()]
                    self.assertEqual(len(rows),1)
                    self.assertEqual(rows[0]['result'],'interrupted')
                    self.assertTrue(rows[0]['tx_hex'])
                    self.assertIn('"attempts": 1',out)
                finally:
                    if proc.poll() is None:
                        proc.kill(); proc.communicate()
        finally:
            os.close(master); os.close(slave)

    def test_disconnect_and_reappearance_selected_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            port, log = Path(tmp)/'selected', Path(tmp)/'reconnect.jsonl'
            master, slave = pty.openpty()
            port.symlink_to(os.ttyname(slave))
            proc = subprocess.Popen([sys.executable,str(SCRIPT),str(port),'--watch',
                '--interval','.05','--timeout','.08','--count','6','--log',str(log)],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertTrue(select.select([master],[],[],2)[0])
                os.read(master,4096)
                os.close(master); os.close(slave)
                master = slave = None
                port.unlink()
                deadline = time.monotonic()+2
                while time.monotonic()<deadline:
                    rows = [json.loads(x) for x in log.read_text().splitlines()]
                    if any(r['result']=='port_absent' for r in rows):
                        break
                    time.sleep(.01)
                self.assertTrue(any(r['result']=='port_absent' for r in rows))
                master, slave = pty.openpty()
                port.symlink_to(os.ttyname(slave))
                deadline = time.monotonic()+3
                while proc.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],.02)[0]:
                        packet = os.read(master,4096)
                        if len(packet)>2:
                            os.write(master,wire_ack(((packet[1]&7)+1)%8))
                out, err = proc.communicate(timeout=2)
                rows = [json.loads(x) for x in log.read_text().splitlines()]
                self.assertEqual(len(rows),6)
                self.assertEqual(rows[-1]['result'],'ack',err)
                self.assertTrue(any(r['result']=='access_error' for r in rows))
                self.assertTrue(all(r['port']==str(port) for r in rows))
            finally:
                if proc.poll() is None:
                    proc.kill();proc.communicate()
                if master is not None: os.close(master)
                if slave is not None: os.close(slave)


class DecoderTests(unittest.TestCase):
    def test_fragment_escape_and_bounded_overflow(self):
        spec = importlib.util.spec_from_file_location('dfu_ping',SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        decoder = module.SlipDecoder(limit=8)
        self.assertEqual(decoder.feed(b'noise\xc0\xdb'),[])
        self.assertEqual(decoder.feed(b'\xdc\xdb\xdd\xc0'),[b'\xc0\xdb'])
        self.assertEqual(decoder.feed(b'x'*10000+b'\xc0'+ACK),[None,bytes.fromhex('10 00 00 f0')])
        self.assertLessEqual(len(decoder.buffer),8)
        self.assertEqual(decoder.feed(b'\xdb\x00\xc0'),[None])


class ReviewRegressionTests(unittest.TestCase):
    def test_zero_baud_rejected_before_port_open(self):
        result = subprocess.run([sys.executable,str(SCRIPT),'/no-such-port','0'],capture_output=True)
        self.assertEqual(result.returncode,2)

    def test_ack_remains_confirmed_when_peer_disconnects(self):
        master, slave = pty.openpty()
        proc = subprocess.Popen([sys.executable,str(SCRIPT),os.ttyname(slave)],
                                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            self.assertTrue(select.select([master],[],[],2)[0])
            os.read(master,4096)
            os.write(master,ACK)
            time.sleep(.05)
            os.close(master); master = None
            out, err = proc.communicate(timeout=2)
            self.assertEqual(proc.returncode,0,out+err)
            self.assertIn('"ack": 1',out)
        finally:
            if proc.poll() is None:
                proc.kill();proc.communicate()
            if master is not None: os.close(master)
            os.close(slave)


if __name__ == '__main__':
    unittest.main()
