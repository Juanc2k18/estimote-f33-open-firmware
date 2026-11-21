"""rail_survey tests with an nRF52832 simulated at register level.

Model: 6/7/14/15 are one node; 3/4 are SDA/SCL with an external pull-up to the rail
(low with the rail off); 9 follows pulls; 19 follows pulls; XL1 optionally receives
a 32768 Hz square wave.
"""
from pathlib import Path
import sys
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import rail_survey as rs

P=rs.P;CLK=rs.CLOCK


class FakeNRF:
    def __init__(self,sqw_on_xl1=False,crystal=True,rail_single=True,directional=False):
        self.directional=directional
        self.mem={};self.cnf=[0]*32;self.out=0;self.sqw=sqw_on_xl1;self.crystal=crystal
        self.rail_single=rail_single;self.timer_count=0;self.timer_running=False;self.t_start=None
        self.lf_running=False;self.lf_src=0;self.lf_started_event=0;self.rtc_start=None;self.rtc_base=0
        self.pc=0x75000
    # --- electrical model ---
    def dir(self):return sum((c&1)<<i for i,c in enumerate(self.cnf))
    def rail_powered(self):
        pins=rs.RAIL if self.rail_single or self.directional else (6,7)
        return any(self.cnf[p]&1 and self.out>>p&1 for p in pins)
    def level(self,p):
        c=self.cnf[p]
        if c&1:return self.out>>p&1
        if p in (14,15) and self.directional:return 1 if (c>>2)&3==3 else 0
        if p in rs.RAIL and (self.rail_single or self.directional or p in (6,7)):return int(self.rail_powered())
        if p in (3,4):return int(self.rail_powered())
        pull=(c>>2)&3
        return 1 if pull==3 else 0
    def gpio_in(self):return sum(self.level(p)<<p for p in range(32))
    def freq(self,p):
        if p==0 and self.sqw:return 32768
        return 0
    # --- pyOCD interface ---
    def read32(self,a):
        if a==0x10000100:return 0x52832
        if a==0x40001550:return 0
        if a==P+0x510:return self.gpio_in()
        if a==P+0x514:return self.dir()
        if a==P+0x504:return self.out
        if P+0x700<=a<P+0x780:return self.cnf[(a-P-0x700)//4]
        if a==rs.TIMER1+0x540:return self.mem.get(a,0)
        if a==CLK+0x418:return (int(self.lf_running)<<16)|self.lf_src&3
        if a==CLK+0x104:return self.lf_started_event
        if a==CLK+0x518:return self.mem.get(a,0)
        if a==rs.RTC2+0x504:
            if not self.rtc_start or not self.lf_ok():return self.rtc_base
            return int((time.monotonic()-self.rtc_start)*32768)&0xffffff
        if 0x40007100<=a<0x40007120:return 1
        return self.mem.get(a,0)
    def lf_ok(self):
        src=self.mem.get(CLK+0x518,0)
        if src&(1<<17):return self.sqw
        if src&3==1:return self.crystal or self.sqw
        return True
    def set_cnf(self,p,v):
        old=self.level(p);self.cnf[p]=v;self.edge(p,old)
    def edge(self,p,old):
        cfg=self.mem.get(rs.GPIOTE+0x510,0)
        if cfg&3==1 and (cfg>>8)&31==p and self.mem.get(rs.PPI+0x500,0)&1 and self.timer_running:
            if old==0 and self.level(p)==1:self.timer_count+=1
    def write32(self,a,v):
        self.mem[a]=v
        if a==P+0x508:self.out|=v
        elif a==P+0x50c:self.out&=~v
        elif a==P+0x518 or a==P+0x51c:
            for p in range(32):
                if v>>p&1:
                    old=self.level(p)
                    self.cnf[p]=(self.cnf[p]|1) if a==P+0x518 else (self.cnf[p]&~1);self.edge(p,old)
        elif P+0x700<=a<P+0x780:self.set_cnf((a-P-0x700)//4,v)
        elif a==rs.PPI+0x504:self.mem[rs.PPI+0x500]=self.mem.get(rs.PPI+0x500,0)|v
        elif a==rs.PPI+0x508:self.mem[rs.PPI+0x500]=self.mem.get(rs.PPI+0x500,0)&~v
        elif a==rs.TIMER1:self.timer_running=True;self.t_start=time.monotonic()
        elif a==rs.TIMER1+0x004:self.timer_running=False
        elif a==rs.TIMER1+0x00c:self.timer_count=0;self.t_start=time.monotonic()
        elif a==rs.TIMER1+0x040:
            cfg=self.mem.get(rs.GPIOTE+0x510,0);extra=0
            if cfg&3==1 and self.timer_running:extra=int(self.freq((cfg>>8)&31)*(time.monotonic()-self.t_start))
            self.mem[rs.TIMER1+0x540]=self.timer_count+extra
        elif a==CLK+0x008:
            self.lf_running=self.lf_ok();self.lf_started_event=int(self.lf_running);self.lf_src=self.mem.get(CLK+0x518,0)
        elif a==CLK+0x00c:self.lf_running=False
        elif a==rs.RTC2:self.rtc_start=time.monotonic()
        elif a==rs.RTC2+0x004:self.rtc_start=None
    def read_memory_block8(self,a,n):return [0]*n
    def write_memory_block8(self,a,data):pass
    def halt(self):pass
    def resume(self):pass
    def reset(self):self.cnf=[0]*32;self.out=0
    def write_core_register(self,r,v):pass
    def read_core_register(self,r):return self.pc


def collect():
    events=[]
    return events,lambda **e:events.append(e)


class RailTests(unittest.TestCase):
    def board(self,real_sleep=False,**kw):
        self.t=FakeNRF(**kw);self.events,emit=collect()
        return rs.RailBoard(self.t,emit,sleep=time.sleep if real_sleep else (lambda s:None))
    def lf_event(self):return [e for e in self.events if e.get('kind')=='lfclk'][-1]

    def test_topology_single_node(self):
        with self.board() as b:self.assertTrue(rs.state_allowed('all',rs.rail_topology(b,lambda **e:self.events.append(e))))
        self.assertTrue([e for e in self.events if e.get('kind')=='rail_topology'][0]['single_node'])

    def test_topology_split_blocks_rail(self):
        with self.board(rail_single=False) as b:topo=rs.rail_topology(b,lambda **e:None)
        self.assertFalse(rs.state_allowed('all',topo));self.assertFalse(rs.state_allowed('14',topo))
        self.assertTrue(rs.state_allowed('67',topo))

    def test_directional_topology_allows_single_sources(self):
        with self.board(directional=True) as b:topo=rs.rail_topology(b,lambda **e:None)
        self.assertEqual(topo[14],{6:1,7:1,15:0})
        self.assertEqual([n for n in rs.STATES if rs.state_allowed(n,topo)],['14','15','67'])

    def test_directional_state_powers_bus(self):
        dl=rs.Deadline(30)
        with self.board(directional=True) as b:
            c=rs.EdgeCounter(b);matrix,freq=rs.selection(False)
            off,_=rs.run_phase(b,c,lambda **e:None,dl,'rail_off',matrix,freq,.02,False)
            levels=b.rail_set(True,pins=(14,))
            self.assertEqual((levels[6],levels[7],levels[15]),(1,1,0))
            on,_=rs.run_phase(b,c,lambda **e:None,dl,'rail_14',matrix,freq,.02,False)
        self.assertEqual(rs.choose_pairs(off,on,False)[1],[3,4])

    def test_guards(self):
        with self.board() as b:
            for pin in (12,13,21):
                with self.assertRaises(ValueError):b.configure(pin,0)
            for pin in (0,1,19,11):
                with self.assertRaises(ValueError):b.configure(pin,rs.CNF_OUT)
                b.configure(pin,rs.CNF_IN)
            b.rail_set(True)
            with self.assertRaises(ValueError):b.configure(6,0)
            b.release();self.assertEqual(self.t.cnf[6],rs.CNF_OUT_H0H1)

    def test_counter_control_counts_pull_toggles(self):
        with self.board() as b:
            r=rs.EdgeCounter(b).control_pull_toggle(19,toggles=7)
        self.assertEqual(r['rising_edges'],7);self.assertTrue(r['valid'])

    def test_matrix_gains_bus_pins_with_rail(self):
        dl=rs.Deadline(30)
        with self.board() as b:
            c=rs.EdgeCounter(b);matrix,freq=rs.selection(False)
            off,_=rs.run_phase(b,c,lambda **e:None,dl,'rail_off',matrix,freq,.02,False)
            levels=b.rail_set(True);self.assertTrue(all(levels.values()))
            on,_=rs.run_phase(b,c,lambda **e:None,dl,'rail_on',matrix,freq,.02,False)
        self.assertNotIn(3,off);self.assertNotIn(4,off);self.assertIn(3,on);self.assertIn(4,on)
        pairs,new=rs.choose_pairs(off,on,False)
        self.assertEqual(sorted(new),[3,4]);self.assertIn((3,4),pairs)
        self.assertTrue(all(a in new or b in new for a,b in pairs))
        self.assertEqual(self.t.cnf[6],0)   # closure releases the rail

    def test_i2c_on_new_pair_reports_nack_not_fault(self):
        with self.board() as b:
            b.rail_set(True)
            ok=rs.scan_i2c(b,[(3,4)],[0x68],lambda **e:self.events.append(e),rs.Deadline(30))
        self.assertTrue(ok)
        self.assertEqual([e['status'] for e in self.events if e['kind']=='i2c_address'],['nack'])

    def test_lfclk_external_square_wave(self):
        with self.board(real_sleep=True,sqw_on_xl1=True,crystal=False) as b:
            ok=rs.lfclk_probe(b,rs.EdgeCounter(b),lambda **e:self.events.append(e),'rail_off',.05)
        self.assertTrue(ok);e=self.lf_event()
        self.assertIn('external ~32 kHz',e['verdict']);self.assertGreater(e['xl_as_gpio'][0]['rising_edges'],0)

    def test_lfclk_passive_crystal(self):
        with self.board(real_sleep=True,sqw_on_xl1=False,crystal=True) as b:
            rs.lfclk_probe(b,rs.EdgeCounter(b),lambda **e:self.events.append(e),'rail_off',.05)
        e=self.lf_event()
        self.assertIn('passive crystal',e['verdict']);self.assertEqual(e['xl_as_gpio'][0]['rising_edges'],0)

    def test_plan_cli(self):
        self.assertEqual(rs.main(['--plan']),0)
        with self.assertRaises(SystemExit):rs.main(['--plan','--control-pins','12'])
        with self.assertRaises(SystemExit):rs.main(['--plan','--states','14,14'])


class WatchTests(unittest.TestCase):
    def test_watch_counts_signal_and_restores_rail(self):
        import pin_frequency_watch as w
        t=FakeNRF(directional=True);t.freq=lambda p:100 if p==17 else 0;events=[]
        with rs.RailBoard(t,lambda **e:events.append(e)) as b:
            s=w.watch(b,rs.EdgeCounter(b),lambda **e:events.append(e),17,.3,.1,'14')
            self.assertEqual(t.cnf[14],rs.CNF_PD)
        self.assertGreaterEqual(s['windows'],2);self.assertGreater(s['hz_min'],50)


if __name__=='__main__':unittest.main()
