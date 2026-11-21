"""Virtual RTC on SDA14/SCL15 with pull-ups powered by the 6/7 rail."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd
import i2c_rail_bus as rb
import rail_survey as rs
from test_board_diagnostics import SlaveLines
from test_rail_survey import FakeNRF

P=rs.P


class RailBusBoard(FakeNRF):
    def __init__(self):
        super().__init__(directional=True);self.slave=SlaveLines((0x10,)*8)
    def rail67(self):return all(self.cnf[p]&1 and self.out>>p&1 for p in (6,7))
    def line(self,p,k):
        if self.cnf[p]&1:return self.out>>p&1
        pulled=self.rail67() or (self.cnf[p]>>2)&3==3
        if not pulled:return 0
        return self.slave.drive if k==2 else 1
    def level(self,p):
        if p==14:return self.line(14,2)
        if p==15:return self.line(15,8)
        return super().level(p)
    def write32(self,a,v):
        super().write32(a,v)
        for p,k in ((14,2),(15,8)):
            host=self.out>>p&1 if self.cnf[p]&1 else 1
            if self.slave.host[k]!=host:self.slave.change(k,host)


class RailBusTests(unittest.TestCase):
    def test_finds_rtc_on_14_15_with_rail(self):
        t=RailBusBoard();events=[]
        with rs.RailBoard(t,lambda **e:events.append(e),sleep=lambda s:None) as b:
            ok=rb.run(b,lambda **e:events.append(e),bd.Deadline(60),['67'],['od'],[0x50,0x68])
        cands=[e for e in events if e['kind']=='i2c_candidate']
        self.assertTrue(any(c['address']==0x68 and (c['sda'],c['scl'])==(14,15) for c in cands),cands)
        self.assertTrue(ok)

    def test_rail_guard_allows_bus_pins(self):
        t=FakeNRF(directional=True)
        with rs.RailBoard(t,lambda **e:None,sleep=lambda s:None) as b:
            b.rail_set(True,pins=(6,7));b.configure(14,rs.CNF_PU)
            with self.assertRaises(ValueError):b.configure(6,0)

    def test_plan(self):
        self.assertEqual(rb.main(['--plan']),0)
        with self.assertRaises(SystemExit):rb.main(['--plan','--states','14'])


if __name__=='__main__':unittest.main()
