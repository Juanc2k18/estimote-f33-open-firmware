"""Push-pull SCL on an indeterminate node (GPIO17) with a virtual RTC on SDA18/SCL17."""
from pathlib import Path
import random
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
import board_diagnostics as bd
import i2c_pushpull_scl as pp
import rail_survey as rs
from test_board_diagnostics import SlaveLines
from test_rail_survey import FakeNRF

P=rs.P


class RtcBoard(FakeNRF):
    """17 floats at mid voltage unless driven; the slave sees SDA=18, SCL=17."""
    def __init__(self,data=(0x45,)*8):
        super().__init__(directional=True);self.slave=SlaveLines(data);self.rng=random.Random(1)
    def host_level(self,p):
        c=self.cnf[p]
        if c&1:return self.out>>p&1
        if p==17:return None                      # not driven: the slave sees no edge
        return 1                                  # SDA released: pull-up
    def sync(self):
        for p,k in ((18,2),(17,8)):
            v=self.host_level(p)
            if v is not None and self.slave.host[k]!=v:self.slave.change(k,v)
    def level(self,p):
        if p==17:
            if self.cnf[17]&1:return self.out>>17&1
            return 0                              # intermediate node: the pull-up does not raise it (r32)
        if p==18:
            host=self.out>>18&1 if self.cnf[18]&1 else 1
            return host&self.slave.drive
        return super().level(p)
    def write32(self,a,v):
        super().write32(a,v)
        if a in (P+0x508,P+0x50c,P+0x518,P+0x51c) or P+0x700<=a<P+0x780:self.sync()


class PushPullTests(unittest.TestCase):
    def test_od_rejects_noisy_scl_but_push_pull_finds_rtc(self):
        t=RtcBoard();events=[]
        with rs.RailBoard(t,lambda **e:events.append(e),sleep=lambda s:None) as b:
            ok_od=bd.scan_i2c(b,[(18,17)],[0x68],lambda **e:events.append(dict(mode='od',**e)),bd.Deadline(30))
            with pp.pushpull_lines():
                ok_pp=bd.scan_i2c(b,[(18,17)],[0x68],lambda **e:events.append(dict(mode='pp',**e)),bd.Deadline(30))
        od=[e for e in events if e.get('mode')=='od' and e['kind']=='i2c_electrical'][0]
        self.assertFalse(od['valid'])
        cand=[e for e in events if e.get('mode')=='pp' and e['kind']=='i2c_candidate']
        self.assertEqual([c['address'] for c in cand],[0x68],[e for e in events if e.get('mode')=='pp'][:4])
        self.assertTrue(ok_pp)
        self.assertIs(bd.SWDLines.__name__,'SWDLines')

    def test_pairs_and_cli_guards(self):
        self.assertEqual(len(pp.pairs_for([16,17,18,20])),12)
        self.assertNotIn(17,pp.NEIGHBOURS)
        self.assertEqual(pp.main(['--plan']),0)
        for bad in (['--pins','16,17'],['--pins','17,3'],['--pins','17,12'],['--pins','17,19'],['--states','all']):
            with self.assertRaises(SystemExit):pp.main(['--plan',*bad])


if __name__=='__main__':unittest.main()
