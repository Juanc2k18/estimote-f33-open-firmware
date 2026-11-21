#!/usr/bin/env python3
"""Real reading of the sensors on the SDA=P0.14 / SCL=P0.15 bus (r37).

Goal: show that each sensor **measures**, not just that it answers with its ID.
They are powered up by writing only volatile configuration registers
(lost when power is removed) and N rounds are read so that the
owner can tilt, rotate or cover the board between rounds.

- LIS2DH12 0x19: CTRL_REG1=0x57 (100 Hz, XYZ), CTRL_REG4=0x80 (BDU, ±2 g).
  Expected at rest: |a| ≈ 1 g.
- LIS3MDL 0x1E: CTRL_REG1=0x90 (temperature + 10 Hz), CTRL_REG2=0 (±4 G),
  CTRL_REG3=0 (continuous). Earth's field ≈ 0.25–0.65 G.
- BMP280 0x77: calibration 0x88..0xA1 and forced measurement (ctrl_meas=0x25).
- MAX44009 0x4A (probable): lux from 0x03/0x04; no writes.
- M41T62 0x68: seconds read only (the time is not set).

When finished, the control registers read at the start are restored.
From RAM (RailBoard), no flash/UICR; reset on close. P0.06/P0.07 high
power the pull-ups. 12/13/17/21 are not touched.
"""
import argparse
from datetime import datetime
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd
from bus_probe import BusFault
import rail_survey as rs
from sensor_identification import RegisterProbe

SDA,SCL=14,15
ACC,MAG,LUX,RTC,BARO=0x19,0x1E,0x4A,0x68,0x77
AUTO_INC=0x80   # LIS2DH12/LIS3MDL: bit 7 of the sub-address = auto-increment


class SensorBus(RegisterProbe):
    """RegisterProbe with register writes (START, addr+W, reg, data, STOP)."""
    def write_register(self,address,register,data):
        data=list(data)
        if not 8<=address<120 or not 0<=register<=255 or not 1<=len(data)<=8:
            raise ValueError('invalid address, register or length')
        result=dict(address=address,register=register,written=data,status='ok')
        try:
            self.start()
            for value in [address*2,register]+data:
                if not self.write_byte(value):result['status']='nack';break
        except BusFault as exc:result['status']=exc.status
        finally:
            if result['status']=='bus_busy':self.release(self.sda);self.release(self.scl)
            else:
                try:self.stop()
                except BusFault as exc:result['status']=exc.status
        return result


class SensorError(RuntimeError):pass


class Sensors:
    """Per-sensor operations on a bus with read_register/write_register."""
    def __init__(self,bus,emit,sleep=time.sleep):
        self.bus=bus;self.emit=emit;self.sleep=sleep;self.saved={}
        self.calibration=None

    def read(self,address,register,length):
        r=self.bus.read_register(address,register,length)
        self.emit(kind='register_read',**{k:v for k,v in r.items() if k!='post_stop'})
        if r['status']!='ok':raise SensorError(f'{hex(address)}@{hex(register)}: {r["status"]}')
        return r['data']

    def write(self,address,register,value,verify=True):
        r=self.bus.write_register(address,register,[value])
        self.emit(kind='register_write',**r)
        if r['status']!='ok':raise SensorError(f'write {hex(address)}@{hex(register)}: {r["status"]}')
        if verify:
            back=self.read(address,register,1)[0]
            if back!=value:raise SensorError(f'{hex(address)}@{hex(register)} reads back {hex(back)} ≠ {hex(value)}')

    def wait_ready(self,address,status_reg,mask,timeout=.6):
        end=time.monotonic()+timeout
        while True:
            if self.read(address,status_reg,1)[0]&mask:return True
            if time.monotonic()>=end:return False
            self.sleep(.02)

    # --- configuration and restore ---
    SETUP={ACC:((0x20,0x57),(0x23,0x80)),MAG:((0x20,0x90),(0x21,0x00),(0x22,0x00))}

    def setup(self,address):
        regs=self.SETUP[address]
        self.saved[address]=[(reg,self.read(address,reg,1)[0]) for reg,_ in regs]
        self.emit(kind='saved_control',address=address,registers=self.saved[address])
        for reg,value in regs:self.write(address,reg,value)

    def restore(self):
        failures=[]
        for address,regs in self.saved.items():
            # LIS3MDL: CTRL_REG3 (mode) first, to power down before the rest.
            for reg,value in sorted(regs,key=lambda x:x[0]!=0x22):
                try:self.write(address,reg,value)
                except SensorError as exc:failures.append(str(exc))
        self.emit(kind='restore',ok=not failures,failures=failures)
        return not failures

    # --- readings ---
    def accel(self):
        ready=self.wait_ready(ACC,0x27,0x08)
        raw=struct.unpack('<hhh',bytes(self.read(ACC,0x28|AUTO_INC,6)))
        g=[(v>>6)*0.004 for v in raw]          # normal mode 10 bits, 4 mg/digit
        return dict(ready=ready,raw=raw,g=[round(x,3) for x in g],norm_g=round(math.sqrt(sum(x*x for x in g)),3))

    def magnet(self):
        ready=self.wait_ready(MAG,0x27,0x08)
        raw=struct.unpack('<hhh',bytes(self.read(MAG,0x28|AUTO_INC,6)))
        gauss=[v/6842 for v in raw]            # ±4 G
        temp=struct.unpack('<h',bytes(self.read(MAG,0x2E|AUTO_INC,2)))[0]/8+25
        return dict(ready=ready,raw=raw,gauss=[round(x,4) for x in gauss],
                    norm_gauss=round(math.sqrt(sum(x*x for x in gauss)),4),temp_c_rel=round(temp,1))

    def baro_calibration(self):
        data=self.read(BARO,0x88,24)
        self.calibration=struct.unpack('<HhhHhhhhhhhh',bytes(data))
        self.emit(kind='bmp280_calibration',values=self.calibration)
        if self.calibration[0]==0 or self.calibration[3]==0:raise SensorError('empty BMP280 calibration')
        return self.calibration

    def baro(self):
        if self.calibration is None:self.baro_calibration()
        self.write(BARO,0xF4,0x25,verify=False)   # forced, osrs_t=1, osrs_p=1
        self.sleep(.01)
        end=time.monotonic()+.2
        while self.read(BARO,0xF3,1)[0]&0x08 and time.monotonic()<end:self.sleep(.005)
        d=self.read(BARO,0xF7,6)
        adc_p=d[0]<<12|d[1]<<4|d[2]>>4;adc_t=d[3]<<12|d[4]<<4|d[5]>>4
        t,p=bmp280_compensate(self.calibration,adc_t,adc_p)
        return dict(adc_t=adc_t,adc_p=adc_p,temp_c=round(t,2),pressure_hpa=round(p/100,2))

    def light(self):
        hi=self.read(LUX,0x03,1)[0];lo=self.read(LUX,0x04,1)[0]
        return dict(raw=[hi,lo],lux=round(max44009_lux(hi,lo),2),config=self.read(LUX,0x02,1)[0])

    def rtc_seconds(self):
        s=self.read(RTC,0x01,1)[0]&0x7F
        return dict(raw=s,seconds=(s>>4)*10+(s&0x0F))


def bmp280_compensate(c,adc_t,adc_p):
    T1,T2,T3,P1,P2,P3,P4,P5,P6,P7,P8,P9=c
    v1=(adc_t/16384-T1/1024)*T2
    v2=(adc_t/131072-T1/8192)**2*T3
    fine=v1+v2;temp=fine/5120
    v1=fine/2-64000
    v2=v1*v1*P6/32768+v1*P5*2
    v2=v2/4+P4*65536
    v1=(P3*v1*v1/524288+P2*v1)/524288
    v1=(1+v1/32768)*P1
    if v1==0:return temp,0.0
    p=(1048576-adc_p-v2/4096)*6250/v1
    p+=(P9*p*p/2147483648+p*P8/32768+P7)/16
    return temp,p


def max44009_lux(hi,lo):
    exponent=hi>>4;mantissa=(hi&0x0F)<<4|(lo&0x0F)
    return (1<<exponent)*mantissa*0.045


CHECKS={
    'accel':lambda r:0.8<=r['norm_g']<=1.2,
    'magnet':lambda r:0.1<=r['norm_gauss']<=1.0,
    'baro':lambda r:700<=r['pressure_hpa']<=1100 and -10<=r['temp_c']<=60,
    'light':lambda r:0<=r['lux']<=188000,
}
KEYS={'accel':'g','magnet':'gauss','baro':'pressure_hpa','light':'lux'}


def verdict(rows):
    """Plausibility per round and variation between rounds (not blocking)."""
    out={}
    for name,check in CHECKS.items():
        values=[r[name] for r in rows if isinstance(r.get(name),dict)]
        if not values:out[name]=dict(status='no_data');continue
        plausible=sum(bool(check(v)) for v in values)
        series=[json.dumps(v[KEYS[name]]) for v in values]
        out[name]=dict(rounds=len(values),plausible=plausible,distinct=len(set(series)),
                       status='ok' if plausible==len(values) and (len(values)<2 or len(set(series))>1)
                       else 'check')
    return out


GUIDE=['still, horizontal (reference)',
       'rotate 90° on the table, without lifting it',
       'rotate another 90° (180° in total)',
       'rotate another 90° (270° in total)',
       'return to the starting position',
       'stand it on its edge (one long side down)',
       'face down',
       'horizontal and cover the light sensor with your hand',
       'horizontal with the phone flashlight on top',
       'still, uncovered (final reference)']


READINGS=('accel','magnet','baro','light','rtc_seconds')


def run(sensors,emit,rounds,interval,sleep=time.sleep,show=print,guide=None,only=READINGS):
    rows=[]
    if guide:rounds=len(guide)
    try:
        for address in (ACC,MAG):sensors.setup(address)
        sensors.baro_calibration()
        sleep(.2)
        for n in range(1,rounds+1):
            if guide:
                show(f'\n>>> Round {n}/{rounds}: {guide[n-1].upper()} — you have {interval:g} s',flush=True)
                emit(kind='stimulus',round=n,instruction=guide[n-1]);sleep(interval)
            row=dict(round=n,stimulus=guide[n-1] if guide else None,local_time=datetime.now().astimezone().isoformat(timespec='seconds'))
            for name in only:
                try:row[name]=getattr(sensors,name)()
                except SensorError as exc:row[name]=dict(error=str(exc))
            emit(kind='round',**row);rows.append(row)
            show(summary_line(row),flush=True)
            if n<rounds and not guide:sleep(interval)
    finally:
        sensors.restore()
    result=verdict(rows);emit(kind='verdict',**result)
    return rows,result


def summary_line(row):
    def get(name,fmt):
        v=row.get(name)
        if v is None:return '-'
        return 'ERR' if 'error' in v else fmt(v)
    a=get('accel',lambda v:f"{v['g']} |{v['norm_g']}| g")
    m=get('magnet',lambda v:f"|{v['norm_gauss']}| G")
    b=get('baro',lambda v:f"{v['pressure_hpa']} hPa {v['temp_c']} °C")
    l=get('light',lambda v:f"{v['lux']} lx")
    r=get('rtc_seconds',lambda v:f"{v['seconds']} s")
    return f"[{row['round']}] accel {a}  mag {m}  baro {b}  light {l}  rtc {r}"


def presence(bus,emit,sleep,tries=5):
    """Address ACK per sensor before configuring; logs every attempt."""
    missing=[]
    for address in (ACC,MAG,LUX,RTC,BARO):
        for attempt in range(1,tries+1):
            r=bus.address(address,False);emit(kind='presence',attempt=attempt,**r)
            if r['status']=='ack':break
            sleep(.1)
        else:missing.append(address)
    return missing


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Example:\n  python3 scripts/sensor_readout.py --rounds 8 --interval 3 --supply "3,3 V C/F" --out docs/evidence/sensors-reading-r37-2026-11-19')
    ap.add_argument('--rounds',type=int,default=6)
    ap.add_argument('--interval',type=float,default=3.0,help='seconds between rounds (to move/cover)')
    ap.add_argument('--guided',action='store_true',help='guided sequence of 10 stimuli (ignores --rounds)')
    ap.add_argument('--only',default=','.join(READINGS),help='readings per round: '+','.join(READINGS))
    ap.add_argument('--settle',type=float,default=1.0,help='wait after raising 6/7 (s)')
    ap.add_argument('--supply',default='not stated')
    ap.add_argument('--out',type=Path)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--frequency',type=int,default=100000)
    ap.add_argument('--uart-port',default='/dev/cu.usbmodem21202')
    ap.add_argument('--plan',action='store_true')
    a=ap.parse_args(argv)
    if not 1<=a.rounds<=100 or not (math.isfinite(a.interval) and 0<=a.interval<=60):
        ap.error('rounds 1–100, interval 0–60 s')
    only=tuple(x.strip() for x in a.only.split(','))
    if not only or set(only)-set(READINGS):ap.error('--only: '+','.join(READINGS))
    plan=dict(tool='sensor_readout',supply=a.supply,sda=SDA,scl=SCL,rail=(6,7),settle=a.settle,rounds=a.rounds,interval=a.interval,guided=GUIDE if a.guided else None,only=only,
              writes={hex(k):[(hex(r),hex(v)) for r,v in regs] for k,regs in Sensors.SETUP.items()}|{'0x77':[('0xf4','0x25')]},
              restore='original control registers when finished')
    if a.plan:print(json.dumps(plan,indent=2,ensure_ascii=False));return 0
    out=a.out or Path('docs/evidence')/('sensors-reading-'+datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z'))
    journal=bd.Journal(out);status='incomplete';code=1;result=None
    try:
        journal.emit(kind='parameters',**plan)
        busy=subprocess.run(['lsof','-t',a.uart_port,a.uart_port.replace('/cu.','/tty.')],capture_output=True,text=True)
        if busy.stdout.strip():raise RuntimeError('UART busy; stop the monitor first')
        from pyocd.core.helpers import ConnectHelper
        with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options=bd.session_options('auto',a.frequency)) as s:
            if s is None:raise RuntimeError('Pico not available')
            journal.emit(kind='baseline',**bd.snapshot(s.target))
            with rs.RailBoard(s.target,journal.emit) as board:
                levels=board.rail_set(True,pins=(6,7));board.sleep(.3)
                journal.emit(kind='rail_on',levels=levels)
                if not (levels[6] and levels[7]):raise RuntimeError(f'rail 6/7 does not reach high: {levels}')
                bus=SensorBus(bd.SWDLines(board,(SDA,SCL)),SDA,SCL,timeout=.015,delay=.0002)
                electrical=bus.electrical();journal.emit(kind='i2c_electrical',**electrical)
                if not electrical['valid']:raise RuntimeError('bus 14/15 electrically invalid')
                board.sleep(a.settle)
                missing=presence(bus,journal.emit,board.sleep)
                if missing:raise RuntimeError(f'no ACK after retries: {[hex(x) for x in missing]}')
                _,result=run(Sensors(bus,journal.emit),journal.emit,a.rounds,a.interval,guide=GUIDE if a.guided else None,only=only)
                board.release();board.rail_set(False)
        status='complete';code=0
    except KeyboardInterrupt:journal.emit(kind='interrupted');status='interrupted';code=130
    except Exception as exc:journal.emit(kind='error',error=repr(exc));print(exc,file=sys.stderr)
    finally:
        summary=journal.finish(status)
        print(json.dumps(dict(output=str(out.resolve()),status=status,veredicto=result,counts=summary['counts']),ensure_ascii=False))
    return code


if __name__=='__main__':raise SystemExit(main())
