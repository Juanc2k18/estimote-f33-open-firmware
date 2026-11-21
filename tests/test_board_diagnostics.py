"""Diagnostics tests: virtual electrical I2C slave and target limits."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import sensor_identification as sensors


class SlaveLines:
    """I2C slave: receives bytes, generates ACK and delivers data on real edges."""
    def __init__(self,data=(0x58,),nack_at=None):
        self.host={2:1,8:1};self.drive=1;self.mode='idle';self.bits=0
        self.byte=0;self.received=[];self.starts=0;self.stops=0
        self.data=list(data);self.index=0;self.bit=0;self.master_acks=[]
        self.nack_at=nack_at;self.address=True
    def sample(self):return {2:self.host[2]&self.drive,8:self.host[8]}
    def low(self,p):self.change(p,0)
    def release(self,p):self.change(p,1)
    def change(self,p,value):
        old=self.host[p];self.host[p]=value
        if p==2 and self.host[8] and old!=value:
            if value==0:
                self.starts+=1;self.mode='receive';self.address=True
                self.bits=self.byte=0;self.drive=1
            else:self.stops+=1;self.mode='idle';self.drive=1
        if p!=8 or old==value:return
        if value:
            if self.mode=='receive':
                self.byte=(self.byte<<1)|self.host[2];self.bits+=1
                if self.bits==8:
                    self.received.append(self.byte);self.mode='ack_pending'
            elif self.mode=='ack':self.mode='ack_done'
            elif self.mode=='send':self.mode='send_done'
            elif self.mode=='master_ack':
                self.master_acks.append(self.host[2]);self.mode='master_ack_done'
        else:
            if self.mode=='ack_pending':
                self.drive=int(len(self.received)-1==self.nack_at);self.mode='ack'
            elif self.mode=='ack_done':
                reading=self.address and bool(self.byte&1)
                self.address=False;self.drive=1;self.bits=self.byte=0
                if reading:self.mode='send';self.bit=0;self.prepare()
                else:self.mode='receive'
            elif self.mode=='send_done':
                self.bit+=1
                if self.bit==8:self.mode='master_ack';self.drive=1
                else:self.mode='send';self.prepare()
            elif self.mode=='master_ack_done':
                self.index+=1;self.bit=0
                self.mode='send' if not self.master_acks[-1] else 'idle'
                self.prepare() if self.mode=='send' else None
    def prepare(self):self.drive=(self.data[self.index%len(self.data)]>>(7-self.bit))&1


class RegisterTests(unittest.TestCase):
    def test_register_repeated_start_and_final_nack(self):
        io=SlaveLines((0x12,0x34))
        r=sensors.RegisterProbe(io,2,8,timeout=.001,delay=0).read_register(0x68,0,2)
        self.assertEqual(r['status'],'ok',r)
        self.assertEqual(r['data'],[0x12,0x34])
        self.assertEqual(io.received,[0xd0,0,0xd1])
        self.assertEqual(io.starts,2)
        self.assertEqual(io.master_acks,[0,1])
        self.assertEqual(io.stops,1)

    def test_nack_at_each_stage_returns_no_data(self):
        for index in range(3):
            io=SlaveLines(nack_at=index)
            r=sensors.RegisterProbe(io,2,8,timeout=.001,delay=0).read_register(0x76,0xd0,1)
            self.assertEqual(r['status'],'nack',r)
            self.assertEqual(r['data'],[])
            self.assertEqual(len(io.received),index+1)
            self.assertEqual(io.stops,1)

    def test_stuck_bus_not_reported_as_nack(self):
        class Stuck(SlaveLines):
            def sample(self):return {2:1,8:0}
        r=sensors.RegisterProbe(Stuck(),2,8,timeout=.001,delay=0).read_register(0x68,0,8)
        self.assertEqual(r['status'],'bus_busy')
        self.assertEqual(r['data'],[])


class ClassificationTests(unittest.TestCase):
    def test_sensor_ids_require_repeated_matching_reads(self):
        self.assertEqual(sensors.sensor_model(0x76,[0x58,0x58]),'BMP280')
        self.assertEqual(sensors.sensor_model(0x77,[0x60,0x60]),'BME280')
        self.assertEqual(sensors.sensor_model(0x18,[0x33,0x33]),'LIS3DH/LIS2DH12 compatible')
        for values in ([0x58,0x00],[0x58],[0,0],[255,255]):
            self.assertIsNone(sensors.sensor_model(0x76,values))
        self.assertIsNone(sensors.sensor_model(0x68,[0x58,0x58]))

    def test_rtc_bcd_and_rollover(self):
        first=[0,0x59,0x59,0x23,1,0x31,0x12,0x26]
        second=[0,0,0,0,2,1,1,0x27]
        r=sensors.rtc_evidence(first,second,1.1)
        self.assertEqual(r['status'],'clock_advancing',r)
        self.assertEqual(r['advance_seconds'],1)
        self.assertFalse(r['exact_model_verified'])

    def test_rtc_stopped_and_invalid_not_identified(self):
        good=[0,0x10,0x20,0x12,1,0x19,0x11,0x26]
        self.assertEqual(sensors.rtc_evidence(good,good,1.1)['status'],'no_advance')
        stopped=good.copy();stopped[1]|=0x80
        self.assertEqual(sensors.rtc_evidence(stopped,stopped,1.1)['status'],'oscillator_stopped')
        for bad in ([255]*8,good[:7],[0,0x7a,0,0,1,1,1,0]):
            self.assertEqual(sensors.rtc_evidence(bad,good,1.1)['status'],'invalid_clock_data')

import board_diagnostics as board
from unittest.mock import patch
import tempfile
import json


class FakeTarget:
    def __init__(self):
        self.writes=[];self.calls=[];self.fail_on_radio=False
        self.mem={0x10000100:0x52832,0x10001200:21,0x10001204:21,0x40001550:0}
    def read32(self,address):return self.mem.get(address,0)
    def write32(self,address,value):
        self.writes.append((address,value));self.mem[address]=value
        if address==0x40001010 and self.fail_on_radio:raise OSError('SWD lost')
    def read_memory_block8(self,address,length):return [0]*length
    def write_memory_block8(self,address,data):self.writes.append((address,list(data)))
    def write_core_register(self,name,value):self.calls.append(('reg',name,value))
    def read_core_register(self,name):return 0x75000
    def halt(self):self.calls.append('halt')
    def resume(self):self.calls.append('resume')
    def reset(self):self.calls.append('reset')


class BoardTests(unittest.TestCase):
    def test_baseline_reads_gpio_without_writing_or_halting(self):
        t=FakeTarget();t.mem[0x50000510]=1<<13
        snapshot=board.snapshot(t)
        self.assertEqual(snapshot['part'],0x52832)
        self.assertEqual(snapshot['gpio'][13]['level'],1)
        self.assertEqual(t.writes,[]);self.assertEqual(t.calls,[])

    def test_active_cleanup_after_failure_keeps_irq_input(self):
        t=FakeTarget();events=[]
        with self.assertRaisesRegex(RuntimeError,'experiment'):
            with board.ActiveBoard(t,lambda **event:events.append(event),sleep=lambda _:None):
                raise RuntimeError('experiment')
        self.assertIn('reset',t.calls)
        self.assertEqual(t.mem[0x50000700+19*4],0)
        self.assertIn('resume',t.calls)
        self.assertTrue(events[-1]['unchanged'])
        self.assertFalse(any(0<=addr<0x80000 or 0x10001000<=addr<0x10002000 for addr,value in t.writes))

    def test_cleanup_also_runs_when_preparation_fails(self):
        t=FakeTarget();t.fail_on_radio=True;events=[]
        with self.assertRaises(OSError):
            with board.ActiveBoard(t,lambda **event:events.append(event),sleep=lambda _:None):pass
        self.assertIn('reset',t.calls)
        self.assertEqual(t.mem[0x50000700+19*4],0)

    def test_pin_selection_rejects_reserved_and_duplicates(self):
        for value in ('0,2','11,8','12,13','19,8','21,8','3,4','2,2','32','14,8'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):board.parse_pins(value)
        self.assertEqual(board.parse_pins('2,8,16'),[2,8,16])
        self.assertTrue({0,1,9,10,11,12,13,19,21,3,4,22,25,14,15}.isdisjoint(board.DEFAULT_PINS))

    def test_deadline_expires_as_incomplete(self):
        clock=iter([10,10.5,11.1])
        deadline=board.Deadline(1,clock=lambda:next(clock))
        deadline.check()
        with self.assertRaises(TimeoutError):deadline.check()

    def test_uart_audit_detects_false_positive(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'uart.jsonl'
            tx='c0 d1 4e 00 e1 7f 00 00 00 aa a8 c0'
            rows=[dict(time='2026-11-19T00:00:00-05:00',sequence=1,result='ack',tx_hex=tx,rx_hex='c0 10 00 00 f0 c0',ack_number=2,port='/dev/test',baud=115200),
                  dict(time='2026-11-19T00:00:05-05:00',sequence=1,result='ack',tx_hex=tx,rx_hex=tx,ack_number=2,port='/dev/test',baud=115200)]
            path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
            result=board.audit_uart_log(path)
            self.assertEqual(result['counts'],{'ack':2})
            self.assertEqual(result['invalid_ack_lines'],[2])
            self.assertFalse(result['valid'])


class SPIIO:
    def __init__(self,stuck=False):self.level={};self.stuck=stuck;self.bit=0
    def set(self,p,v):self.level[p]=v
    def input(self,p):pass
    def pause(self):pass
    def sample(self,p):
        if p==8 and self.stuck:return 0
        if p==17:
            value=(0x33>>(7-self.bit%8))&1;self.bit+=1;return value
        return self.level.get(p,1)


class SPITests(unittest.TestCase):
    def test_spi_reads_id_in_both_modes(self):
        for mode in (0,3):
            io=SPIIO();r=sensors.DirectedSPI(io,2,8,16,17).read_id(0x8f,mode)
            self.assertEqual(r,{'status':'ok','value':0x33})
            self.assertEqual(io.level[2],1)
    def test_stuck_clock_is_electrical_failure_not_zero_id(self):
        r=sensors.DirectedSPI(SPIIO(stuck=True),2,8,16,17).read_id(0x8f)
        self.assertEqual(r['status'],'sck_not_toggle');self.assertIsNone(r['value'])


class ReviewRegressions(unittest.TestCase):
    def test_rtc_control_bits_are_not_bcd_or_reserved(self):
        first=[0,0x10,0xa0,0x12,0xf1,0x19,0x11,0x26]
        second=first.copy();second[1]=0x11
        self.assertEqual(sensors.rtc_evidence(first,second,1.1)['status'],'clock_advancing')

    def test_slow_rtc_transactions_use_observation_window(self):
        a=[0,0,0,0,1,1,1,0x26];b=a.copy();b[1]=0x04
        self.assertEqual(sensors.rtc_evidence(a,b,6,window=(2,6))['status'],'clock_advancing')

    def test_cleanup_reset_attempted_even_if_hash_read_fails(self):
        class ClosingFailure(FakeTarget):
            def __init__(self):super().__init__();self.reads=0
            def read_memory_block8(self,address,length):
                self.reads+=1
                if self.reads==3:raise OSError('transient hash')
                return [0]*length
        t=ClosingFailure();events=[]
        with self.assertRaises(RuntimeError):
            with board.ActiveBoard(t,lambda **e:events.append(e),sleep=lambda _:None):pass
        self.assertIn('reset',t.calls)
        self.assertEqual(t.mem[0x50000700+19*4],0)
        self.assertIn('resume',t.calls)
        self.assertFalse(events[-1]['valid'])

    def test_disconnected_input_is_not_a_physical_low(self):
        t=FakeTarget();t.mem[0x50000700+2*4]=2
        gpio=board.snapshot(t)['gpio'][2]
        self.assertIsNone(gpio['level']);self.assertEqual(gpio['raw_in_bit'],0)
        self.assertFalse(gpio['input_connected'])

    def test_gpio_records_neighbor_changes_during_od(self):
        class Neighbor(FakeTarget):
            def read32(self,address):
                if address==0x50000510:return (1<<2|1<<8) if not self.mem.get(0x50000518) else 0
                return super().read32(address)
        t=Neighbor();events=[]
        with board.ActiveBoard(t,lambda **e:events.append(e),sleep=lambda _:None) as active:
            board.gpio_survey(active,[2],lambda **e:events.append(e),board.Deadline(5))
        probe=next(e for e in events if e['kind']=='gpio_probe')
        self.assertEqual(probe['od_low_raw']>>8&1,0)

    def test_baseline_disconnect_does_not_force_resume(self):
        self.assertFalse(board.session_options('baseline',100000)['resume_on_disconnect'])

    def test_audit_rejects_empty_bad_tx_bad_ack_field_and_sequence_jump(self):
        tx='c0 d1 4e 00 e1 7f 00 00 00 aa a8 c0'
        good=dict(time='2026-11-19T00:00:00-05:00',sequence=1,result='ack',tx_hex=tx,
                  rx_hex='c0 10 00 00 f0 c0',ack_number=2,port='/dev/test',baud=115200)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'log.jsonl'
            p.write_text('');self.assertFalse(board.audit_uart_log(p)['valid'])
            for change in (dict(tx_hex=''),dict(ack_number=7),dict(baud=0),dict(time='bad')):
                p.write_text(json.dumps(dict(good,**change))+'\n')
                self.assertFalse(board.audit_uart_log(p)['valid'],change)
            p.write_text(json.dumps(good)+'\n'+json.dumps(dict(good,sequence=3))+'\n')
            self.assertFalse(board.audit_uart_log(p)['valid'])

    def test_spi_checks_mosi_before_command_clock(self):
        class StuckMOSI(SPIIO):
            def sample(self,p):return 0 if p==16 else super().sample(p)
        r=sensors.DirectedSPI(StuckMOSI(),2,8,16,17).read_id(0x8f)
        self.assertEqual(r['status'],'mosi_not_level')

    def test_i2c_fault_is_not_a_complete_pair(self):
        class FakeBus:
            def __init__(self,*args,**kwargs):pass
            def electrical(self):return dict(valid=True)
            def address(self,address,read):return dict(address=address,status='clock_not_high')
        events=[];active=type('Active',(),{'release':lambda self:None})()
        with patch.object(board,'SWDLines',return_value=None),patch.object(board,'RegisterProbe',FakeBus):
            complete=board.scan_i2c(active,[(2,8)],[0x68,0x76],lambda **e:events.append(e),board.Deadline(5))
        self.assertFalse(complete)
        self.assertEqual(next(e for e in events if e['kind']=='i2c_pair_incomplete')['unprobed'],[0x76])

    def test_adjacent_devices_can_reach_identification(self):
        class FakeBus:
            def __init__(self,*args,**kwargs):pass
            def electrical(self):return dict(valid=True)
            def address(self,address,read):return dict(address=address,status='ack' if address in (0x18,0x19) else 'nack')
        identified=[];active=type('Active',(),{'release':lambda self:None})()
        def identify(bus,address,*args):identified.append(address);return True
        with patch.object(board,'SWDLines',return_value=None),patch.object(board,'RegisterProbe',FakeBus),patch.object(board,'identify_i2c',side_effect=identify):
            board.scan_i2c(active,[(2,8)],[0x18,0x19],lambda **e:None,board.Deadline(5))
        self.assertEqual(identified,[0x18,0x19])


class FinalBoundaryTests(unittest.TestCase):
    def test_register_bus_fault_propagates_incomplete(self):
        bus=type('Bus',(),{'read_register':lambda self,*args:dict(status='clock_not_high',data=[])})()
        events=[]
        result=board.identify_i2c(bus,0x76,lambda **e:events.append(e),board.Deadline(5),dict(sda=2,scl=8))
        self.assertFalse(result)
        self.assertEqual(events[-1]['status'],'incomplete')

    def test_failed_reset_leaves_ram_core_halted(self):
        class ResetFailure(FakeTarget):
            def reset(self):self.calls.append('reset_failed');raise OSError('reset without response')
        t=ResetFailure()
        with self.assertRaises(RuntimeError):
            with board.ActiveBoard(t,lambda **e:None,sleep=lambda _:None):pass
        self.assertEqual(t.calls[-1],'halt')
        self.assertEqual(t.calls.count('resume'),1)


if __name__=='__main__':unittest.main()
