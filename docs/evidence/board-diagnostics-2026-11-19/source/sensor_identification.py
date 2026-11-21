"""Identification readings; no pyOCD dependency and no data writes."""
from datetime import datetime
import math
from bus_probe import BusFault, I2CProbe


class RegisterProbe(I2CProbe):
    def start(self):
        self.release(self.sda)
        self.release(self.scl)
        self.wait({self.sda:1,self.scl:1},'bus_busy')
        self.low(self.sda)
        self.low(self.scl)

    def write_byte(self,value):
        for bit in range(7,-1,-1):
            (self.release if value>>bit&1 else self.low)(self.sda)
            self.high_clock()
            self.low(self.scl)
        self.release(self.sda)
        ack=self.high_clock()[self.sda]==0
        self.low(self.scl)
        return ack

    def read_byte(self,ack):
        self.release(self.sda)
        value=0
        for _ in range(8):
            value=value*2+self.high_clock()[self.sda]
            self.low(self.scl)
        (self.low if ack else self.release)(self.sda)
        self.high_clock()
        self.low(self.scl)
        self.release(self.sda)
        return value

    def read_register(self,address,register,length):
        if not 8<=address<120 or not 0<=register<=255 or not 1<=length<=32:
            raise ValueError('invalid address, register or length')
        result=dict(address=address,register=register,data=[],status='ok',stage='start')
        try:
            self.start()
            for stage,value in (('address_write',address*2),('register',register),
                                ('address_read',address*2+1)):
                result['stage']=stage
                if stage=='address_read':self.start()
                if not self.write_byte(value):
                    result['status']='nack'
                    break
            else:
                result['stage']='data'
                result['data']=[self.read_byte(i<length-1) for i in range(length)]
        except BusFault as exc:
            result.update(status=exc.status,data=[])
        finally:
            if result['status']=='bus_busy':
                self.release(self.sda);self.release(self.scl)
            else:
                try:result['post_stop']=self.stop()
                except BusFault as exc:result.update(status=exc.status,data=[])
        return result


def sensor_model(address,values):
    if len(values)<2 or len(set(values))!=1:return None
    value=values[0]
    if address in (0x18,0x19) and value==0x33:return 'LIS3DH/LIS2DH12 compatible'
    if address in (0x76,0x77):return {0x58:'BMP280',0x60:'BME280'}.get(value)
    return None


def decode_clock(raw):
    if len(raw)!=8 or any(not 0<=x<=255 for x in raw):raise ValueError('RTC length/range')
    def bcd(value,maximum,minimum=0):
        if value&15>9 or value>>4>9:raise ValueError('invalid BCD')
        number=(value>>4)*10+(value&15)
        if not minimum<=number<=maximum:raise ValueError('BCD out of range')
        return number
    if raw[3]&0xc0 or raw[4]&0x08 or raw[5]&0xc0 or raw[6]&0x20:
        raise ValueError('RTC reserved bits')
    hundredths=bcd(raw[0],99)
    seconds=bcd(raw[1]&0x7f,59);minutes=bcd(raw[2]&0x7f,59)
    hours=bcd(raw[3],23);day=bcd(raw[5],31,1);month=bcd(raw[6]&0x1f,12,1)
    weekday=raw[4]&7
    if not 1<=weekday<=7:raise ValueError('RTC weekday')
    year=2000+(raw[6]>>6)*100+bcd(raw[7],99)
    stamp=datetime(year,month,day,hours,minutes,seconds,hundredths*10000)
    return stamp,bool(raw[1]&0x80)


def rtc_evidence(first,second,elapsed,window=None):
    result=dict(first=first,second=second,elapsed_seconds=elapsed,
                exact_model_verified=False,advance_seconds=None)
    try:
        if not math.isfinite(elapsed) or elapsed<=0:raise ValueError('RTC interval')
        a,st1=decode_clock(first);b,st2=decode_clock(second)
    except (ValueError,TypeError) as exc:
        return dict(result,status='invalid_clock_data',reason=str(exc))
    delta=(b-a).total_seconds()
    result.update(first_decoded=a.isoformat(),second_decoded=b.isoformat(),advance_seconds=delta)
    if st1 or st2:return dict(result,status='oscillator_stopped')
    if delta==0:return dict(result,status='no_advance')
    lower,upper=window if window is not None else (max(.01,elapsed-1.5),elapsed+1.5)
    return dict(result,status='clock_advancing' if 0<delta and lower-.03<=delta<=upper+.03
                else 'inconsistent_advance',observation_window=[lower,upper])


class DirectedSPI:
    """IO provides set(pin,value), input(pin), sample(pin) and pause()."""
    def __init__(self,io,cs,sck,mosi,miso):
        self.io=io;self.cs=cs;self.sck=sck;self.mosi=mosi;self.miso=miso
    def clock(self,value):
        self.io.set(self.sck,value);self.io.pause()
        if self.io.sample(self.sck)!=value:raise BusFault('sck_not_toggle')
    def read_id(self,command,mode=0,selected=True):
        cpol=int(mode==3)
        try:
            self.io.set(self.cs,1);self.io.set(self.sck,cpol)
            self.io.set(self.mosi,0);self.io.input(self.miso)
            self.io.set(self.cs,int(not selected));self.io.pause()
            if self.io.sample(self.cs)!=int(not selected):raise BusFault('cs_not_level')
            self.clock(cpol)
            for bit in range(7,-1,-1):
                level=(command>>bit)&1
                self.io.set(self.mosi,level);self.io.pause()
                if self.io.sample(self.mosi)!=level:raise BusFault('mosi_not_level')
                self.clock(1-cpol);self.clock(cpol)
            value=0
            for _ in range(8):
                self.clock(1-cpol)
                if mode==0:value=value*2+self.io.sample(self.miso)
                self.clock(cpol)
                if mode==3:value=value*2+self.io.sample(self.miso)
            return dict(status='ok',value=value)
        except BusFault as exc:return dict(status=exc.status,value=None)
        finally:self.io.set(self.cs,1)
