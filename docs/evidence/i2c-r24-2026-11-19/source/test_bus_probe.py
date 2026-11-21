import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
 from bus_probe import I2CProbe
except ImportError:
 I2CProbe=None

class Wires:
 """Electrical model: receiver without data, configurable ACK on the ninth clock."""
 def __init__(self,ack=False,stuck=None,coupled=False):
  self.level={2:1,8:1}; self.ack=ack; self.stuck=stuck; self.coupled=coupled
  self.edges=[];self.active=False;self.bits=[];self.n=0
 def low(self,p):
  if p==2 and self.level[8] and self.level[2]:self.active=True;self.n=0;self.bits=[]
  self.level[p]=0
 def release(self,p):
  old=self.level[p];self.level[p]=1
  if p==8 and not old and self.active:
   self.n+=1
   if self.n<=8:self.bits.append(self.level[2])
   self.edges.append((self.n,self.level[2]))
  if p==2 and self.level[8] and not old:self.active=False
 def sample(self):
  d=dict(self.level)
  if self.ack and self.active and self.n==9 and d[8]:d[2]=0
  if self.stuck is not None:d[self.stuck]=0
  if self.coupled and not all(d.values()):d={2:0,8:0}
  return d

class ProbeTests(unittest.TestCase):
 def probe(self,w):
  self.assertIsNotNone(I2CProbe,'verifiable probe missing')
  return I2CProbe(w,2,8,timeout=.001,delay=0)
 def test_write_nack_is_address_only(self):
  w=Wires();r=self.probe(w).address(0x46,False)
  self.assertEqual(r['status'],'nack');self.assertEqual(r['byte'],0x8c)
  self.assertEqual([n for n,_ in w.edges if n<=9],list(range(1,10)))
  self.assertEqual(r['post_stop'],{2:1,8:1})
  self.assertEqual(w.bits,[1,0,0,0,1,1,0,0])
 def test_ack_with_scl_high_and_read_bit(self):
  w=Wires(ack=True);r=self.probe(w).address(0x46,True)
  self.assertEqual(r['status'],'ack');self.assertEqual(r['byte'],0x8d)
  self.assertEqual(r['ack_sample'][8],1)
 def test_stuck_clock_is_not_nack(self):
  w=Wires();p=self.probe(w);w.stuck=8
  self.assertEqual(p.address(0x46,False)['status'],'bus_busy')
 def test_clock_blocked_on_ack_is_not_ack_or_nack(self):
  class BlockNinth(Wires):
   def sample(self):
    v=super().sample()
    if self.active and self.n==9:v[8]=0
    return v
  r=self.probe(BlockNinth(ack=True)).address(0x46,False)
  self.assertEqual(r['status'],'clock_not_high')
 def test_stop_timeout_is_not_valid_ack(self):
  class HoldAfterAck(Wires):
   def sample(self):
    v=super().sample()
    if self.n>=10:v[2]=0
    return v
  r=self.probe(HoldAfterAck(ack=True)).address(0x46,False)
  self.assertEqual(r['status'],'timeout');self.assertEqual(r['stop_error'],'timeout')
 def test_electrical_coupling_rejected(self):
  w=Wires(coupled=True);r=self.probe(w).electrical()
  self.assertFalse(r['valid']);self.assertEqual(len(r['lines']),2)
 def test_electrical_independent_lines(self):
  self.assertTrue(self.probe(Wires()).electrical()['valid'])

if __name__=='__main__':unittest.main()
