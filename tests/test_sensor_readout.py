"""sensor_readout with a simulated register bus and bit-by-bit writes."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import sensor_readout as sr
from test_board_diagnostics import SlaveLines

# Example from the BMP280 datasheet (section 8.2): 25.08 °C, 100653.27 Pa.
CAL=(27504,26435,-1000,36477,-10685,3024,2855,140,-7,15500,-14600,6000)


class FakeBus:
    def __init__(self):
        self.regs={a:{} for a in (sr.ACC,sr.MAG,sr.LUX,sr.RTC,sr.BARO)};self.tick=0
        r=self.regs
        r[sr.ACC].update({0x20:0x07,0x23:0x00,0x27:0x08});r[sr.MAG].update({0x20:0x10,0x21:0,0x22:0x03,0x27:0x08})
        r[sr.LUX].update({0x02:0x03,0x03:0x35,0x04:0x02});r[sr.RTC][0x01]=0x42
        for i,b in enumerate(struct.pack('<HhhHhhhhhhhh',*CAL)):r[sr.BARO][0x88+i]=b
        adc_p,adc_t=415148,519888
        for i,b in enumerate([adc_p>>12,(adc_p>>4)&0xff,(adc_p&0xf)<<4,adc_t>>12,(adc_t>>4)&0xff,(adc_t&0xf)<<4]):
            r[sr.BARO][0xF7+i]=b
        self.writes=[]
    def refresh(self):
        self.tick+=1;r=self.regs
        on=r[sr.ACC][0x20]&0x07==0x07 and r[sr.ACC][0x20]>>4
        z=(250+self.tick%3)<<6 if on else 0
        for i,b in enumerate(struct.pack('<hhh',0,0,z)):r[sr.ACC][0x28+i]=b
        on=r[sr.MAG][0x22]&3==0
        x=(2000+self.tick%3) if on else 0
        for i,b in enumerate(struct.pack('<hhhh',x,0,1000,0)+struct.pack('<h',-8)):r[sr.MAG][0x28+i]=b
    def read_register(self,address,register,length):
        self.refresh();reg=register&0x7F if address in (sr.ACC,sr.MAG) else register
        return dict(address=address,register=register,status='ok',data=[self.regs[address].get(reg+i,0) for i in range(length)])
    def write_register(self,address,register,data):
        self.writes.append((address,register,data[0]));self.regs[address][register]=data[0]
        return dict(address=address,register=register,written=data,status='ok')


class ReadoutTests(unittest.TestCase):
    def test_bmp280_datasheet_example(self):
        t,p=sr.bmp280_compensate(CAL,519888,415148)
        self.assertAlmostEqual(t,25.08,places=2);self.assertAlmostEqual(p,100653.27,delta=0.1)

    def test_max44009_lux(self):
        self.assertAlmostEqual(sr.max44009_lux(0x35,0x02),8*0x52*0.045)

    def test_run_reads_measures_and_restores(self):
        bus=FakeBus();events=[]
        rows,result=sr.run(sr.Sensors(bus,lambda **e:events.append(e),sleep=lambda s:None),
                           lambda **e:events.append(e),3,0,sleep=lambda s:None,show=lambda *a,**k:None)
        self.assertEqual({k:v['status'] for k,v in result.items()},
                         {'accel':'ok','magnet':'ok','baro':'check','light':'check'})  # baro/light fixed in the fake
        self.assertAlmostEqual(rows[0]['accel']['norm_g'],1.0,delta=.02)
        self.assertAlmostEqual(rows[0]['baro']['pressure_hpa'],1006.53,delta=.01)
        self.assertEqual(rows[0]['rtc_seconds']['seconds'],42)
        # Restore to the original values.
        self.assertEqual(bus.regs[sr.ACC][0x20],0x07);self.assertEqual(bus.regs[sr.MAG][0x22],0x03)
        self.assertTrue([e for e in events if e['kind']=='restore'][0]['ok'])
        # The MAX44009 and the RTC are never written.
        self.assertFalse([w for w in bus.writes if w[0] in (sr.LUX,sr.RTC)])

    def test_failed_write_still_restores(self):
        bus=FakeBus();events=[]
        bus.regs[sr.BARO][0x88]=0;bus.regs[sr.BARO][0x89]=0
        with self.assertRaises(sr.SensorError):
            sr.run(sr.Sensors(bus,lambda **e:events.append(e),sleep=lambda s:None),
                   lambda **e:events.append(e),1,0,sleep=lambda s:None,show=lambda *a,**k:None)
        # Calibration fails after powering LIS2DH12/LIS3MDL: they are restored anyway.
        self.assertEqual(bus.regs[sr.ACC][0x20],0x07);self.assertEqual(bus.regs[sr.MAG][0x22],0x03)

    def test_write_register_bit_level(self):
        io=SlaveLines((0,))
        r=sr.SensorBus(io,2,8,timeout=.001,delay=0).write_register(0x19,0x20,[0x57])
        self.assertEqual(r['status'],'ok',r);self.assertEqual(io.received,[0x32,0x20,0x57])
        self.assertEqual((io.starts,io.stops),(1,1))

    def test_guided_prompts_before_each_round(self):
        bus=FakeBus();events=[];lines=[]
        rows,_=sr.run(sr.Sensors(bus,lambda **e:events.append(e),sleep=lambda s:None),lambda **e:events.append(e),
                      99,0,sleep=lambda s:None,show=lambda *a,**k:lines.append(a[0]),guide=sr.GUIDE[:3])
        self.assertEqual(len(rows),3);self.assertEqual(rows[1]['stimulus'],sr.GUIDE[1])
        self.assertIn('Round 1/3',lines[0])

    def test_only_magnet(self):
        bus=FakeBus()
        rows,res=sr.run(sr.Sensors(bus,lambda **e:None,sleep=lambda s:None),lambda **e:None,2,0,
                        sleep=lambda s:None,show=lambda *a,**k:None,only=('magnet',))
        self.assertEqual(set(rows[0])-{'round','stimulus','local_time'},{'magnet'})
        self.assertEqual(res['accel']['status'],'no_data')

    def test_plan(self):
        self.assertEqual(sr.main(['--plan']),0)
        with self.assertRaises(SystemExit):sr.main(['--plan','--rounds','0'])


if __name__=='__main__':unittest.main()
