#!/usr/bin/env python3
"""HCI/SLIP monitor for the Adafruit 0.11.0 bootloader; standard library."""
import argparse
from collections import Counter
from datetime import datetime
import errno
import json
import math
import os
import select
import termios
import time


def crc16(data, crc=0xFFFF):
    for b in data:
        crc = ((crc >> 8) & 0x00FF) | ((crc << 8) & 0xFF00)
        crc ^= b
        crc ^= (crc & 0x00FF) >> 4
        crc ^= (crc << 8) << 4
        crc ^= ((crc & 0x00FF) << 4) << 1
        crc &= 0xFFFF
    return crc


def hci_packet(seq, payload):
    h = [seq | (((seq + 1) % 8) << 3) | 0xC0,
         14 | ((len(payload) & 0x0F) << 4), len(payload) >> 4]
    h.append(-sum(h) & 0xFF)
    body = bytes(h) + payload
    body += crc16(body).to_bytes(2, 'little')
    return b'\xc0' + body.replace(b'\xdb', b'\xdb\xdd').replace(b'\xc0', b'\xdb\xdc') + b'\xc0'


class SlipDecoder:
    """Complete delimited frames; overflow discards until END."""
    def __init__(self, limit=4096):
        self.limit = limit
        self.buffer = bytearray()
        self.started = False
        self.escape = False
        self.bad = False

    def feed(self, data):
        frames = []
        for b in data:
            if b == 0xC0:
                if self.started and (self.buffer or self.bad or self.escape):
                    frames.append(None if self.bad or self.escape else bytes(self.buffer))
                self.started = True
                self.buffer.clear()
                self.escape = self.bad = False
            elif self.started and not self.bad:
                if self.escape:
                    self.escape = False
                    if b not in (0xDC, 0xDD):
                        self.bad = True
                        continue
                    b = 0xC0 if b == 0xDC else 0xDB
                elif b == 0xDB:
                    self.escape = True
                    continue
                self.buffer.append(b)
                if len(self.buffer) > self.limit:
                    self.buffer.clear()
                    self.bad = True
        return frames


def ack_number(frame):
    """Exact ACK emitted by ack_transmit() in c67f0bc, without CRC/payload."""
    if (frame is None or len(frame) != 4 or frame[0] & 0xC7
            or frame[1:3] != b'\x00\x00' or sum(frame) & 0xFF):
        return None
    return (frame[0] >> 3) & 7


def open_port(port, baud):
    fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        attrs = termios.tcgetattr(fd)
        attrs[0] = attrs[1] = attrs[3] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[4] = attrs[5] = getattr(termios, f'B{baud}')
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, attrs)
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_available(fd, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
        return b''
    data = os.read(fd, 4096)
    if not data:
        raise OSError('port disconnected (EOF)')
    return data


def probe(fd, seq, timeout=1.0, record=None):
    # Listen before transmitting and separate earlier bytes from the reply.
    if record is None:
        record = {}
    record.update(sequence=seq, tx_hex='', rx_hex='', idle_rx_hex='',
                  result='silence', latency_ms=None, ack_number=None, events=[])
    idle = bytearray()
    deadline = time.monotonic() + .05
    while time.monotonic() < deadline:
        idle.extend(read_available(fd, deadline))
        record['idle_rx_hex'] = idle.hex(' ')
    tx = hci_packet(seq, b'\x7f\x00\x00\x00')
    started = time.monotonic()
    deadline = started + timeout
    sent = 0
    while sent < len(tx):
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([], [fd], [], remaining)[1]:
            raise OSError('write timeout')
        sent += os.write(fd, tx[sent:])
        record['tx_hex'] = tx[:sent].hex(' ')
    decoder = SlipDecoder()
    request_frame = SlipDecoder().feed(tx)[0]
    rx = bytearray()
    echo = False
    invalid = False
    candidate = None
    while time.monotonic() < deadline:
        data = read_available(fd, deadline)
        rx.extend(data)
        record['rx_hex'] = rx.hex(' ')
        for frame in decoder.feed(data):
            number = ack_number(frame)
            if number is not None:
                record['events'].append(dict(kind='ack', number=number))
                if number == (seq + 1) % 8:
                    if record['result'] != 'ack':
                        record.update(result='ack', ack_number=number,
                                      latency_ms=round((time.monotonic()-started)*1000, 3))
                else:
                    candidate = number
            elif frame == request_frame:
                echo = True
                record['events'].append(dict(kind='echo'))
            else:
                invalid = True
                record['events'].append(dict(kind='invalid'))
        # Parse the whole block (duplicates included) and close the confirmed
        # sample: a later incident belongs to the next attempt.
        if record['result'] == 'ack':
            break
    record['rx_hex'] = rx.hex(' ')
    if record['result'] != 'ack':
        if candidate is not None:
            record.update(result='resync', ack_number=candidate)
        elif invalid or decoder.buffer or decoder.bad or decoder.escape:
            record['result'] = 'invalid'
        elif echo:
            record['result'] = 'echo'
        elif rx:
            record['result'] = 'invalid'
    return record


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('must be a positive finite number')
    return number


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python3 scripts/dfu_ping.py /dev/cu.usbmodemXXXX 115200
  python3 scripts/dfu_ping.py /dev/cu.usbmodemXXXX --watch --interval 5 --log monitor.jsonl

Use only with the r15 wiring and power checked (see AGENTS.md).
Listens 50 ms before each TX; does not reset the beacon or control DTR/RTS.
An ACK proves the transport; it does not prove a DFU application or new execution.
An out-of-sequence ACK resynchronises the next sample, without counting as success.
--interval is the pause between finished attempts. Ctrl-C closes and summarises.
Exit: 0 if there was an ACK, 1 if not, 2 invalid arguments/log, 130 Ctrl-C.
The log is created exclusively: choose a new file for every run.
""")
    parser.add_argument('port', help='exact path; no other device is ever selected')
    parser.add_argument('baud', nargs='?', type=int, default=115200)
    parser.add_argument('--watch', action='store_true', help='repeat without limit unless --count')
    parser.add_argument('--interval', type=positive_float, default=5.0, metavar='SECONDS')
    parser.add_argument('--timeout', type=positive_float, default=1.0, metavar='SECONDS')
    parser.add_argument('--count', type=positive_int, metavar='N', help='attempt limit in --watch')
    parser.add_argument('--log', metavar='PATH.jsonl', help='new file; creates parent directories')
    args = parser.parse_args(argv)
    if args.baud <= 0 or not hasattr(termios, f'B{args.baud}'):
        parser.error('baud rate not supported by termios')
    if args.count is not None and not args.watch:
        parser.error('--count requires --watch')
    log = None
    if args.log:
        try:
            from pathlib import Path
            path = Path(args.log)
            path.parent.mkdir(parents=True, exist_ok=True)
            log = path.open('x', encoding='utf-8')
        except OSError as exc:
            parser.error(f'cannot create log: {exc}')
    counts = Counter()
    attempts = 0
    fd = None
    seq = 1
    interrupted = False
    try:
        while True:
            record = dict(time=datetime.now().astimezone().isoformat(), port=args.port,
                          baud=args.baud, sequence=seq, tx_hex='', rx_hex='',
                          idle_rx_hex='', result='silence', latency_ms=None,
                          ack_number=None, events=[])
            try:
                if fd is None:
                    fd = open_port(args.port, args.baud)
                probe(fd, seq, args.timeout, record)
                if record['result'] == 'ack':
                    seq = (seq + 1) % 8
                elif record['result'] == 'resync':
                    seq = record['ack_number']
            except (OSError, termios.error) as exc:
                record['result'] = ('port_absent' if getattr(exc, 'errno', None) in
                                    (errno.ENOENT, errno.ENXIO, errno.ENODEV) else 'access_error')
                record['error'] = str(exc)
                if fd is not None:
                    os.close(fd)
                    fd = None
            except KeyboardInterrupt:
                record['result'] = 'interrupted'
                interrupted = True
            finally:
                attempts += 1
                counts[record['result']] += 1
                if log:
                    log.write(json.dumps(record, ensure_ascii=False) + '\n')
                    log.flush()
                print('TX', record['tx_hex'] or '(not sent)', flush=True)
                print('RX', record['rx_hex'] or '(nothing)', flush=True)
                print(f"{record['time']} seq={record['sequence']} {record['result']}", flush=True)
            if interrupted or not args.watch or (args.count and attempts >= args.count):
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        if fd is not None:
            os.close(fd)
        if log:
            log.close()
    print('SUMMARY ' + json.dumps(dict(attempts=attempts, **counts), sort_keys=True), flush=True)
    if counts['ack']:
        print('UART LINK OK', flush=True)
    return 130 if interrupted else (0 if counts['ack'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
