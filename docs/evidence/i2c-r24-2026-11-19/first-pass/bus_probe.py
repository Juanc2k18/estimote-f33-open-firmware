"""r24 I2C probe; OD primitives derived from i2c_bitbang_swd.py.
No register/data on W. R reads one byte and returns NACK if the address responds.
Every high level is validated through IN; monotonic limits, no aggressive recovery.
"""
import time

class BusFault(Exception):
 def __init__(self,status):self.status=status

class I2CProbe:
 def __init__(self,io,sda,scl,timeout=.05,delay=.001):
  self.io,self.sda,self.scl=io,sda,scl
  self.timeout,self.delay=timeout,delay
 def pause(self):
  if self.delay:time.sleep(self.delay)
 def levels(self):return self.io.sample()
 def wait(self,expected,status):
  end=time.monotonic()+self.timeout
  while True:
   v=self.levels()
   if all(v[p]==x for p,x in expected.items()):return v
   if time.monotonic()>=end:raise BusFault(status)
   self.pause()
 def low(self,p):self.io.low(p);self.pause()
 def release(self,p):self.io.release(p);self.pause()
 def high_clock(self):
  self.release(self.scl)
  return self.wait({self.scl:1},'clock_not_high')
 def electrical(self):
  self.release(self.sda);self.release(self.scl)
  result={'idle':self.levels(),'lines':[],'valid':True}
  for p,other in ((self.sda,self.scl),(self.scl,self.sda)):
   self.low(p);low=self.levels()
   self.release(p)
   try:released=self.wait({self.sda:1,self.scl:1},'timeout');recovered=True
   except BusFault:released=self.levels();recovered=False
   ok=low[p]==0 and low[other]==1 and recovered
   result['lines'].append({'driven':p,'low':low,'released':released,'recovered':recovered,'valid':ok})
   result['valid'] &= ok
  result['valid'] &= all(result['idle'].values())
  return result
 def stop(self):
  self.low(self.scl);self.low(self.sda)
  self.high_clock();self.release(self.sda)
  return self.wait({self.sda:1,self.scl:1},'timeout')
 def address(self,addr,read=False):
  r={'address':addr,'rw':'R' if read else 'W','byte':addr*2+int(read)}
  try:
   self.release(self.sda);self.release(self.scl)
   try:self.wait({self.sda:1,self.scl:1},'bus_busy')
   except BusFault:raise
   self.low(self.sda);self.low(self.scl)
   for bit in range(7,-1,-1):
    (self.release if r['byte']>>bit&1 else self.low)(self.sda)
    self.high_clock();self.low(self.scl)
   self.release(self.sda);r['ack_sample']=self.high_clock()
   ack=r['ack_sample'][self.sda]==0
   self.low(self.scl)
   if ack and read:
    v=0
    for _ in range(8):
     v=v*2+self.high_clock()[self.sda];self.low(self.scl)
    self.release(self.sda);self.high_clock();self.low(self.scl)
    r['read_byte']=v
   r['status']='ack' if ack else 'nack'
  except BusFault as e:r['status']=e.status
  finally:
   # Bus busy before START: release it without inventing a STOP.
   if r.get('status')=='bus_busy':
    self.release(self.sda);self.release(self.scl);r['post_stop']=self.levels()
   else:
    try:r['post_stop']=self.stop()
    except BusFault as e:
     r['stop_error']=e.status
     if r.get('status') in ('ack','nack'):r['status']=e.status
     self.release(self.sda);self.release(self.scl);r['post_stop']=self.levels()
  return r
