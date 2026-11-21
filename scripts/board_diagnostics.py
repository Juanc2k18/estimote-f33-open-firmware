#!/usr/bin/env python3
"""F3.3 diagnostics over SWD: GPIO, SAADC, I2C/RTC and targeted SPI.

Not a UART bootloader command. Requires A/B/F connected to the Pico.
"""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import time

from bus_probe import I2CProbe
from dfu_ping import SlipDecoder, ack_number, hci_packet
from sensor_identification import RegisterProbe, DirectedSPI, sensor_model, rtc_evidence

P=0x50000000
RESERVED={0,1,3,4,9,10,11,12,13,14,15,19,21,22,25}
DEFAULT_PINS=[p for p in range(32) if p not in RESERVED and p!=5]
DEFAULT_ADDRESSES=[0x18,0x19,0x29,0x39,0x50,0x68,0x76,0x77]


def parse_pins(text):
    pins=[int(x,0) for x in text.split(',')]
    if not pins or len(set(pins))!=len(pins) or any(not 0<=p<32 or p in RESERVED for p in pins):
        raise ValueError('GPIO duplicated, out of range or reserved; use --plan to see the exclusions')
    return pins


class Deadline:
    def __init__(self,seconds,clock=time.monotonic):
        self.clock=clock;self.end=clock()+seconds
    def check(self):
        if self.clock()>=self.end:raise TimeoutError('global deadline reached; test incomplete')


def snapshot(target):
    raw=target.read32(P+0x510);gpio=[]
    for pin in range(32):
        cnf=target.read32(P+0x700+4*pin);connected=not bool(cnf&2)
        gpio.append(dict(pin=pin,level=(raw>>pin)&1 if connected else None,
                         raw_in_bit=(raw>>pin)&1,input_connected=connected,
                         cnf=cnf,reserved=pin in RESERVED))
    return dict(part=target.read32(0x10000100),gpio=gpio,
        dir=target.read32(P+0x514),out=target.read32(P+0x504),
        resetpins=[target.read32(x) for x in (0x10001200,0x10001204)],
        uart=dict(enable=target.read32(0x40002500),tx=target.read32(0x4000250c),rx=target.read32(0x40002514)),
        radio=target.read32(0x40001550))


class ActiveBoard:
    """Temporarily takes over RAM; closes down even if the preparation fails."""
    def __init__(self,target,emit,sleep=time.sleep):
        self.t=target;self.emit=emit;self.sleep=sleep;self.started=False;self.pins=set()
    def hashes(self):
        return {name:hashlib.sha256(bytes(self.t.read_memory_block8(addr,size))).hexdigest()
                for name,addr,size in [('bootloader',0x74000,0xc000),('uicr',0x10001000,0x400)]}
    def __enter__(self):
        try:
            if self.t.read32(0x10000100)!=0x52832:raise RuntimeError('the target is not an nRF52832')
            self.before=self.hashes()
            self.t.halt();self.started=True
            self.t.write32(P+0x700+19*4,0)
            self.t.write_memory_block8(0x20000000,[0x72,0xb6,0xfe,0xe7])
            for reg,value in [('pc',0x20000000),('sp',0x20010000),('xpsr',1<<24)]:
                self.t.write_core_register(reg,value)
            self.t.resume()
            self.t.write32(0x40001308,0xffffffff)
            self.t.write32(0x40001010,1);self.sleep(.02)
            if self.t.read32(0x40001550)!=0:raise RuntimeError('RADIO still active')
            for address in (0x40003500,0x40004500):self.t.write32(address,0)
            self.configure(14,0);self.configure(15,0)
            self.emit(kind='active_start',hashes=self.before,radio=0,irq19='input without pull')
            return self
        except BaseException:
            self.close();raise
    def configure(self,pin,value):
        if pin in RESERVED and pin not in (14,15):raise ValueError('reserved GPIO')
        self.pins.add(pin);self.t.write32(P+0x700+4*pin,value)
    def release(self):
        for pin in sorted(self.pins-{14,15}):self.t.write32(P+0x700+pin*4,0)
    def enable(self,pin):
        if pin not in (None,14,15):raise ValueError('state only 14 or 15, never both')
        if pin is not None:
            self.t.write32(P+0x508,1<<pin);self.configure(pin,1);self.sleep(.2)
            self.emit(kind='enable_state',pin=pin,interpretation='experimental state, not an identified enable')
    def close(self):
        if not self.started:return True
        self.started=False;errors=[]
        def attempt(label,operation):
            try:return operation()
            except BaseException as exc:errors.append(dict(step=label,error=repr(exc)));return None
        attempt('halt',self.t.halt)
        for pin in sorted(self.pins|{14,15}):
            attempt(f'release_{pin}',lambda pin=pin:self.t.write32(P+0x700+pin*4,0))
        after=attempt('hashes',self.hashes)
        # Independent recovery: a hash/release failure does not prevent the reset.
        reset_ok=attempt('reset',lambda:(self.t.reset(),True)[1])
        pc=cnf19=None
        if reset_ok:
            self.sleep(.4);attempt('halt_after_reset',self.t.halt)
            pc=attempt('pc',lambda:self.t.read_core_register('pc'))
            attempt('irq19_input',lambda:self.t.write32(P+0x700+19*4,0))
            cnf19=attempt('irq19_verify',lambda:self.t.read32(P+0x700+19*4))
            attempt('resume_bootloader',self.t.resume)
        else:
            # Do not resume the RAM loop if the reset did not complete.
            attempt('halt_after_failed_reset',self.t.halt)
        bootloader=pc is not None and 0x74000<=pc<0x80000
        okay=not errors and after==self.before and bootloader and cnf19==0
        self.emit(kind='closure',unchanged=after==self.before,hashes=after,
                  bootloader=bootloader,pc=pc,cnf19=cnf19,errors=errors,valid=okay)
        return okay
    def __exit__(self,exc_type,exc,tb):
        okay=self.close()
        if not okay and exc is None:raise RuntimeError('closure not verified; check events.jsonl')


class SWDLines:
    def __init__(self,active,pins):
        self.a=active;self.t=active.t;self.pins=pins
        for p in pins:active.configure(p,12)
        self.t.write32(P+0x50c,sum(1<<p for p in pins))
    def low(self,p):self.t.write32(P+0x518,1<<p)
    def release(self,p):self.t.write32(P+0x51c,1<<p)
    def sample(self):
        value=self.t.read32(P+0x510)
        return {p:(value>>p)&1 for p in self.pins}


class SPIIO:
    def __init__(self,active):self.a=active;self.t=active.t
    def set(self,p,value):
        self.t.write32(P+(0x508 if value else 0x50c),1<<p)
        self.a.configure(p,1)
    def input(self,p):self.a.configure(p,12)
    def sample(self,p):return (self.t.read32(P+0x510)>>p)&1
    def pause(self):time.sleep(.0002)


def gpio_survey(active,pins,emit,deadline):
    eligible=[]
    for pin in pins:active.configure(pin,0)
    for pin in pins:
        deadline.check();active.release();states={}
        for name,cnf in [('floating',0),('pull_down',4),('pull_up',12)]:
            active.configure(pin,cnf);time.sleep(.01)
            states[name]=active.t.read32(P+0x510)
        active.t.write32(P+0x50c,1<<pin);active.t.write32(P+0x518,1<<pin)
        time.sleep(.005);low_raw=active.t.read32(P+0x510);low=(low_raw>>pin)&1
        active.t.write32(P+0x51c,1<<pin);time.sleep(.01)
        high_raw=active.t.read32(P+0x510);high=(high_raw>>pin)&1
        okay=low==0 and high==1
        if okay:eligible.append(pin)
        emit(kind='gpio_probe',pin=pin,raw_states=states,can_low=low==0,can_high=high==1,eligible=okay,od_low_raw=low_raw,released_raw=high_raw)
        active.configure(pin,0)
    return eligible


def analog_survey(active,emit,deadline):
    t=active.t;adc=0x40007000
    def wait(offset):
        end=time.monotonic()+.3
        while time.monotonic()<end:
            deadline.check()
            if t.read32(adc+offset):return
        raise TimeoutError('SAADC without event; test incomplete')
    try:
        for channel in range(8):
            t.write32(adc+0x510+16*channel,0);t.write32(adc+0x514+16*channel,0)
        t.write32(adc+0x518,5<<16);t.write32(adc+0x5f0,2);t.write32(adc+0x500,1)
        t.write32(adc+0x110,0);t.write32(adc+0xc,1);wait(0x110)
        for ain,pin in [(1,2),(4,5),(5,28),(6,29),(7,30),(8,31),(9,None)]:
            if pin is not None:active.configure(pin,0)
            t.write32(adc+0x510,ain);values=[]
            for _ in range(4):
                deadline.check();t.write32(adc+0x62c,0x20005000);t.write32(adc+0x630,1)
                t.write32(adc+0x100,0);t.write32(adc+0x104,0);t.write32(adc,1);wait(0x100)
                t.write32(adc+4,1);wait(0x104)
                raw=int.from_bytes(bytes(t.read_memory_block8(0x20005000,2)),'little',signed=True)
                values.append(raw)
                t.write32(adc+0x114,0);t.write32(adc+8,1);wait(0x114)
            emit(kind='analog',pin=pin,source='VDD' if pin is None else f'AIN{ain-1}',
                 raw=values,millivolts=[round(v*3600/4096,2) for v in values],
                 interpretation='voltage; does not identify a sensor or provide metrological calibration')
    finally:t.write32(adc+0x500,0)


def identify_i2c(bus,address,emit,deadline,label):
    if address in (0x18,0x19,0x76,0x77):
        register=0x0f if address in (0x18,0x19) else 0xd0
        readings=[]
        for _ in range(3):
            deadline.check();result=bus.read_register(address,register,1)
            emit(kind='register_read',**label,**result)
            if result['status'] not in ('ok','nack'):
                emit(kind='identification',**label,address=address,model=None,status='incomplete',reason=result['status'])
                return False
            if result['status']=='nack':break
            readings.append(result['data'][0])
        model=sensor_model(address,readings)
        emit(kind='identification',**label,address=address,model=model,readings=readings,
             status='id_repeated' if model else 'unidentified')
    elif address==0x68:
        deadline.check();start=time.monotonic();first=bus.read_register(address,0,8)
        first_end=time.monotonic()
        emit(kind='register_read',**label,**first)
        if first['status']!='ok':
            emit(kind='rtc',**label,address=address,status='read_unavailable',reason=first['status'])
            return first['status']=='nack'
        time.sleep(1.2);deadline.check();second_start=time.monotonic()
        second=bus.read_register(address,0,8);second_end=time.monotonic()
        elapsed=(second_start+second_end-start-first_end)/2
        emit(kind='register_read',**label,**second)
        if second['status']=='ok':
            emit(kind='rtc',**label,address=address,**rtc_evidence(first['data'],second['data'],elapsed,
                                   window=(second_start-first_end,second_end-start)))
        elif second['status']!='nack':
            emit(kind='rtc',**label,address=address,status='incomplete',reason=second['status'])
            return False
    deadline.check()
    return True


def scan_i2c(active,pairs,addresses,emit,deadline):
    complete=True
    for index,(sda,scl) in enumerate(pairs,1):
        deadline.check();active.release();label=dict(sda=sda,scl=scl)
        bus=RegisterProbe(SWDLines(active,(sda,scl)),sda,scl,timeout=.015,delay=.0002)
        electrical=bus.electrical();emit(kind='i2c_electrical',**label,**electrical)
        if not electrical['valid']:
            print(f'I2C {index}/{len(pairs)} SDA{sda}/SCL{scl}: electrically invalid',flush=True)
            continue
        candidates=[];fault=False
        for position,address in enumerate(addresses):
            deadline.check();result=bus.address(address,False);deadline.check()
            emit(kind='i2c_address',**label,**result)
            if result['status']=='ack':candidates.append(address)
            elif result['status']!='nack':
                complete=False;fault=True
                emit(kind='i2c_pair_incomplete',**label,status=result['status'],unprobed=addresses[position+1:])
                break
        if fault:continue
        for address in candidates:
            repeats=[]
            for _ in range(3):
                for read in (False,True):
                    deadline.check();result=bus.address(address,read);deadline.check()
                    repeats.append(result['status']);emit(kind='i2c_repeat',**label,**result)
            # A legitimate neighbouring device is not a negative control.
            controls=[x for x in (address-1,address+1,address-2,address+2,8,0x40,0x70)
                      if 8<=x<120 and x not in candidates]
            controls=list(dict.fromkeys(controls))[:3];negative=[]
            for control in controls:
                deadline.check();result=bus.address(control,False);deadline.check()
                negative.append(result['status']);emit(kind='i2c_control',**label,**result)
            electrical_fault=any(x not in ('ack','nack') for x in repeats+negative)
            if electrical_fault:
                complete=False;emit(kind='i2c_pair_incomplete',**label,status='validation_bus_fault',unprobed=[])
            validated=all(x=='ack' for x in repeats) and bool(negative) and all(x=='nack' for x in negative)
            emit(kind='i2c_candidate',**label,address=address,
                 status='validated_address' if validated else 'ambiguous_address')
            if validated:
                identified=identify_i2c(bus,address,emit,deadline,label)
                if identified is False:complete=False
        print(f'I2C {index}/{len(pairs)} SDA{sda}/SCL{scl}: ACK {[hex(x) for x in candidates]}',flush=True)
    active.release();deadline.check()
    return complete


def scan_spi(active,pins,emit,deadline):
    spi=DirectedSPI(SPIIO(active),*pins);complete=True
    for mode in (0,3):
        for command,address in ((0x8f,0x18),(0xd0,0x76)):
            values=[];control=None
            for selected in (True,True,False):
                deadline.check();result=spi.read_id(command,mode,selected)
                emit(kind='spi_read',pins=pins,mode=mode,command=command,selected=selected,**result)
                deadline.check()
                if result['status']!='ok':
                    complete=False
                    emit(kind='spi_incomplete',pins=pins,mode=mode,command=command,status=result['status'])
                    break
                if selected:values.append(result['value'])
                else:control=result['value']
            model=sensor_model(address,values) if control is not None and control not in values else None
            emit(kind='spi_identification',pins=pins,mode=mode,command=command,model=model,
                 readings=values,control=control,status='id_with_cs_control' if model else 'unidentified')
    active.release();deadline.check()
    return complete


def audit_uart_log(path):
    counts=Counter();rows=[];invalid=[];errors=[];issues=[];expected_sequence=1
    allowed={'ack','resync','echo','invalid','silence','port_absent','access_error','interrupted'}
    for index,line in enumerate(Path(path).read_text().splitlines(),1):
        try:
            row=json.loads(line);counts[row['result']]+=1;rows.append(row)
            seq=row['sequence'];result=row['result']
            if type(seq) is not int or not 0<=seq<8:raise ValueError('sequence out of range')
            if result not in allowed:raise ValueError('unknown result')
            stamp=datetime.fromisoformat(row['time'])
            if stamp.utcoffset() is None:raise ValueError('time without time zone')
            if not isinstance(row['port'],str) or not row['port'] or row['baud']<=0:
                raise ValueError('invalid port/baud rate')
            if seq!=expected_sequence:issues.append(dict(line=index,reason='sequence_transition',expected=expected_sequence,actual=seq))
            tx=bytes.fromhex(row['tx_hex']);rx=bytes.fromhex(row['rx_hex'])
            if result not in ('port_absent','access_error','interrupted') and tx!=hci_packet(seq,b'\x7f\x00\x00\x00'):
                issues.append(dict(line=index,reason='invalid_request'))
            numbers=[n for frame in SlipDecoder().feed(rx) if (n:=ack_number(frame)) is not None]
            if result=='ack':
                number=(seq+1)%8
                if number not in numbers:invalid.append(index)
                if row.get('ack_number')!=number:issues.append(dict(line=index,reason='ack_metadata'))
                expected_sequence=number
            elif result=='resync':
                number=row.get('ack_number')
                if type(number) is not int or number not in numbers or number==(seq+1)%8:
                    issues.append(dict(line=index,reason='invalid_resync'))
                else:expected_sequence=number
            else:expected_sequence=seq
        except (ValueError,KeyError,TypeError,AttributeError) as exc:errors.append(dict(line=index,error=str(exc)))
    duration=None
    if rows:
        try:duration=(datetime.fromisoformat(rows[-1]['time'])-datetime.fromisoformat(rows[0]['time'])).total_seconds()
        except (KeyError,ValueError,TypeError):pass
    return dict(path=str(Path(path).resolve()),attempts=len(rows),counts=dict(counts),
                duration_seconds=duration,invalid_ack_lines=invalid,parse_errors=errors,issues=issues,
                valid=bool(rows) and not invalid and not errors and not issues)


class Journal:
    def __init__(self,path):
        self.path=path;path.mkdir(parents=True,exist_ok=False)
        self.file=(path/'events.jsonl').open('x');self.events=[]
    def emit(self,**event):
        event=dict(time=datetime.now().astimezone().isoformat(),**event)
        self.events.append(event);self.file.write(json.dumps(event,ensure_ascii=False)+'\n');self.file.flush()
    def finish(self,status):
        counts=dict(Counter(event['kind'] for event in self.events))
        hits=[e for e in self.events if e['kind'] in ('identification','rtc','spi_identification')]
        summary=dict(status=status,counts=counts,findings=hits,
                     limitation='A NACK does not prove absence. Does not physically locate D or pins without continuity.')
        (self.path/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        text=f'# F3.3 diagnostics\n\nStatus: **{status}**.\n\n'
        text+='## Logged tests\n\n'+''.join(f'- {kind}: {count}\n' for kind,count in counts.items())
        text+='\n## Findings\n\n'
        text+=''.join('- `'+json.dumps(hit,ensure_ascii=False)+'`\n' for hit in hits) or 'No identifiers or clock validated under the tested conditions.\n'
        text+='\n'+summary['limitation']+'\nSee events.jsonl for frames, electrical states and closure.\n'
        (self.path/'report.md').write_text(text);self.file.close()
        return summary


def session_options(profile,frequency):
    # baseline keeps a halted core; active profiles do their own closure.
    return dict(target_override='nrf52832',frequency=frequency,auto_unlock=False,
                connect_mode='attach',halt_on_connect=False,resume_on_disconnect=False)


def parser():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''Examples:
  python3 scripts/board_diagnostics.py --plan --profile auto
  python3 scripts/board_diagnostics.py --profile baseline --out NEW_PATH
  python3 scripts/board_diagnostics.py --profile auto --max-seconds 600 --out NEW_PATH
  python3 scripts/board_diagnostics.py --profile i2c --i2c 6:7 --out NEW_PATH
  python3 scripts/board_diagnostics.py --profile spi --spi CS:SCK:MOSI:MISO --out NEW_PATH

The numbers are nRF GPIOs, NOT pads A-H or Pico GPIOs.
Stop dfu_ping with Ctrl-C. Confirmed power supply 3.3 V C/F; H/E3/batteries removed.
Does not change UART12/13 or SWD; their wires do not need to be moved for the auto profile.
The baseline profile only reads. The active profiles take over RAM and reset on close;
GPIO19 stays an input without pull in RAM only; a later reset restores the LED.
Exit code: 0 suite completed (does not imply a sensor was found), 1 incomplete, 2 CLI, 130 Ctrl-C.
''')
    ap.add_argument('--profile',choices=['baseline','gpio','adc','i2c','spi','auto'],default='baseline')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--pins',default=','.join(map(str,DEFAULT_PINS)))
    ap.add_argument('--i2c',action='append',metavar='SDA:SCL',help='repeatable targeted pairs; without the option it searches candidate pairs')
    ap.add_argument('--spi',metavar='CS:SCK:MOSI:MISO',help='traced pins only; there is no bulk SPI sweep')
    ap.add_argument('--addresses',default=','.join(hex(x) for x in DEFAULT_ADDRESSES))
    ap.add_argument('--enable',type=int,choices=(14,15),help='experimental state: one GPIO high, the other an input; none by default')
    ap.add_argument('--max-seconds',type=float,default=600)
    ap.add_argument('--max-pairs',type=int,default=0,help='0: all candidate pairs within the deadline')
    ap.add_argument('--frequency',type=int,default=100000)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--uart-port',default='/dev/cu.usbmodem21202',help='path used to check concurrent access; it is not opened and nothing is transmitted')
    ap.add_argument('--uart-log',type=Path,help='audit an existing UART log; does not need the board')
    ap.add_argument('--plan',action='store_true',help='show the selection and exclusions without connecting to the target')
    return ap


def main(argv=None):
    ap=parser();a=ap.parse_args(argv)
    try:
        pins=parse_pins(a.pins)
        pairs=[parse_pins(text.replace(':',',')) for text in a.i2c or []]
        if any(len(pair)!=2 for pair in pairs):raise ValueError('--i2c requires two different GPIOs')
        spi=parse_pins(a.spi.replace(':',',')) if a.spi else None
        if spi is not None and len(spi)!=4:raise ValueError('--spi requires four different GPIOs')
        if a.profile=='spi' and spi is None:raise ValueError('--profile spi requires --spi with traced pins')
        addresses=[int(x,0) for x in a.addresses.split(',')]
        if not addresses or len(set(addresses))!=len(addresses) or any(not 8<=x<120 for x in addresses):
            raise ValueError('unique addresses in range 0x08..0x77')
        if not math.isfinite(a.max_seconds) or a.max_seconds<=0 or a.max_pairs<0 or a.frequency<=0:
            raise ValueError('deadline/frequency positive and finite, and max-pairs >=0')
    except ValueError as exc:ap.error(str(exc))
    plan=dict(profile=a.profile,pins=pins,excluded=sorted(RESERVED),pairs=pairs or 'permutations of GPIOs with a valid OD matrix',
              spi=spi or 'skipped: traced pins missing',addresses=addresses,enable=a.enable,
              max_seconds=a.max_seconds,max_pairs=a.max_pairs,uart_gpio_reserved=[12,13],probe=a.probe)
    if a.plan:print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    out=a.out or Path('docs/evidence')/('board-diagnostics-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f%z'))
    try:journal=Journal(out)
    except OSError as exc:ap.error(f'cannot create new directory: {exc}')
    status='incomplete';exit_code=1
    try:
        journal.emit(kind='parameters',**plan)
        if a.uart_log:
            audit=audit_uart_log(a.uart_log);journal.emit(kind='uart_audit',**audit)
            status='complete' if audit['valid'] else 'incomplete';exit_code=0 if audit['valid'] else 1
            return exit_code
        busy=subprocess.run(['lsof','-t',a.uart_port,a.uart_port.replace('/cu.','/tty.')],capture_output=True,text=True)
        if busy.stdout.strip():raise RuntimeError('UART busy; stop the monitor with Ctrl-C before the diagnostics')
        from pyocd.core.helpers import ConnectHelper
        options=session_options(a.profile,a.frequency)
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=options) as session:
            if session is None:raise RuntimeError('selected Pico not available')
            target=session.target;journal.emit(kind='baseline',**snapshot(target))
            if a.profile!='baseline':
                deadline=Deadline(a.max_seconds)
                complete=True
                with ActiveBoard(target,journal.emit) as active:
                    active.enable(a.enable)
                    eligible=pins
                    if a.profile in ('gpio','auto') or (a.profile=='i2c' and not pairs):
                        eligible=gpio_survey(active,pins,journal.emit,deadline)
                    if a.profile in ('adc','auto'):analog_survey(active,journal.emit,deadline)
                    if a.profile in ('i2c','auto'):
                        selected=pairs or list(itertools.permutations(eligible,2))
                        if a.max_pairs:selected=selected[:a.max_pairs]
                        journal.emit(kind='i2c_selection',pairs=selected,eligible=eligible)
                        complete=scan_i2c(active,selected,addresses,journal.emit,deadline) and complete
                    if a.profile in ('spi','auto'):
                        if spi:complete=scan_spi(active,spi,journal.emit,deadline) and complete
                        else:journal.emit(kind='skipped',test='spi',reason='CS/SCK/MOSI/MISO not traced')
                    deadline.check()
                if not complete:raise RuntimeError('electrical tests incomplete; check the log')
            status='complete';exit_code=0
    except KeyboardInterrupt:
        journal.emit(kind='interrupted');status='interrupted';exit_code=130
    except Exception as exc:
        journal.emit(kind='error',error=repr(exc));print(str(exc),file=sys.stderr)
    finally:
        summary=journal.finish(status)
        print(json.dumps(dict(output=str(out.resolve()),status=status,counts=summary['counts']),ensure_ascii=False),flush=True)
    return exit_code


if __name__=='__main__':raise SystemExit(main())
