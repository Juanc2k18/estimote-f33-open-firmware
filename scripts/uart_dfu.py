#!/usr/bin/env python3
"""Uploads an application over UART (E1/E2) to the Adafruit bootloader, catching its boot window.

On the nRF52832 the bootloader opens 1 s of serial DFU at every boot and closes it if
it receives no valid traffic. This script:

1. Sends a reliable HCI packet (sequence 1) every 30 ms with a DFU type that the
   bootloader ignores (0x06), until it receives its ACK. Receiving a valid packet
   marks activity and leaves the bootloader waiting for the upload with no deadline.
2. Completes the round of sequence numbers (2…7, 0) so that the bootloader
   expects sequence 1 again, which is the one adafruit-nrfutil starts with.
3. Launches `adafruit-nrfutil dfu serial` with the package.

Usage: start the script and then boot the board (cut power and restore
it, or `ble_sensors.py --serial-dfu`). With `--command`, the script itself
sends the UART command `dfu` to the 1.0.0 application and nothing needs to be
cut. `--wait` is the maximum waiting time. 3.3 V logic: E3 at 3.3 V (verify logic-level margin against measured VDD).
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
from dfu_ping import SlipDecoder, ack_number, hci_packet, open_port, read_available
from uart_sensors import LineReader

IGNORED_TYPE=(6).to_bytes(4,'little')   # not INIT, START, DATA or STOP: the bootloader discards it
NRFUTIL=Path(__file__).resolve().parents[1]/'.venv'/'bin'/'adafruit-nrfutil'


def now():return datetime.now().astimezone().isoformat(timespec='milliseconds')


def wait_ack(fd,dec,want,deadline):
    while time.monotonic()<deadline:
        for frame in dec.feed(read_available(fd,min(deadline,time.monotonic()+0.03))):
            if ack_number(frame)==want:return True
    return False


def request_dfu(port,baud,log,timeout=1.5):
    """Asks the 1.0.0 application (UART on) to restart into UART DFU: command `dfu`."""
    fd=open_port(port,baud);rd=LineReader()
    try:
        os.write(fd,b'\ndfu\n');end=time.monotonic()+timeout
        while time.monotonic()<end:
            for line in rd.feed(read_available(fd,min(end,time.monotonic()+0.05))):
                # endswith: the first line may carry an old leftover without '\n' in front (seen in r1.0.0).
                if line.endswith('{"ok":"dfu"}'):log(kind='dfu_command_ok');return
        raise TimeoutError('the application did not reply {"ok":"dfu"}: UART off or E2 not connected?')
    finally:os.close(fd)


def catch(port,baud,wait,log):
    fd=os.open(port,os.O_RDONLY|os.O_NONBLOCK);os.close(fd)   # fails early if the port does not exist
    fd=open_port(port,baud);dec=SlipDecoder()
    try:
        end=time.monotonic()+wait;sent=0;t0=time.monotonic()
        while True:
            if time.monotonic()>end:raise TimeoutError(f'no response from the bootloader in {wait:g} s')
            os.write(fd,hci_packet(1,IGNORED_TYPE));sent+=1
            if wait_ack(fd,dec,2,time.monotonic()+0.03):break
        log(kind='caught',attempts=sent,after_s=round(time.monotonic()-t0,2))
        for seq in (2,3,4,5,6,7,0):   # full round: the bootloader expects 1 again
            for attempt in range(5):
                os.write(fd,hci_packet(seq,IGNORED_TYPE))
                if wait_ack(fd,dec,(seq+1)%8,time.monotonic()+0.3):break
            else:raise RuntimeError(f'no ACK for sequence {seq}')
        log(kind='sequence_wrapped')
    finally:os.close(fd)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('zip',type=Path)
    ap.add_argument('--port',default='/dev/cu.usbmodem1131202')
    ap.add_argument('--baud',type=int,default=115200)
    ap.add_argument('--wait',type=float,default=60,help='seconds waiting for the board to boot')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--command',action='store_true',
                    help='send the UART command `dfu` to the 1.0.0 application instead of waiting for an E3 power cut')
    a=ap.parse_args(argv)
    events=[]
    def log(**kw):
        kw={'t':now()}|kw;events.append(kw);print(json.dumps(kw,ensure_ascii=False),flush=True)
    status='error'
    try:
        log(kind='waiting',port=a.port,wait_s=a.wait,zip=str(a.zip))
        if a.command:request_dfu(a.port,a.baud,log)
        catch(a.port,a.baud,a.wait,log)
        t0=time.monotonic()
        p=subprocess.run([str(NRFUTIL),'--verbose','dfu','serial','-pkg',str(a.zip),'-p',a.port,'-b',str(a.baud)],
                         capture_output=True,text=True)
        print(p.stdout[-3000:],p.stderr[-3000:],sep='\n')
        log(kind='nrfutil_done',returncode=p.returncode,seconds=round(time.monotonic()-t0,2),
            stdout_tail=p.stdout[-1500:],stderr_tail=p.stderr[-1500:])
        status='ok' if p.returncode==0 else 'error'
    except Exception as exc:log(kind='error',error=repr(exc))
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/'events.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events))
        (a.out/'result.json').write_text(json.dumps(dict(tool='uart_dfu',zip=str(a.zip),status=status),indent=1))
    return 0 if status=='ok' else 1


if __name__=='__main__':raise SystemExit(main())
