"""Data packet format of the F3.3 BLE application (version 1, 31 bytes).

Must match `firmware/ble-sensors/f33_math.c` (`f33_pack`).
"""
import math
import struct

LAYOUT=struct.Struct('<BBH3h3hhIIHHB')
FLAGS=('accel','magnet','baro','light','rtc','adc')
# Battery on H: same as the firmware's f33_battery_mv/f33_battery_percent (r45, provisional).
CELL=((3000,100),(2950,90),(2900,80),(2800,60),(2700,40),(2600,20),(2400,5),(2000,0))


def battery_mv(ain3_mv:int)->int:
    return 0 if ain3_mv<100 else ain3_mv*5825//1000+122


def battery_percent(mv:int)->int:
    cell=mv//2   # 2S
    if cell>=CELL[0][0]:return 100
    for (hi,php),(lo,plo) in zip(CELL,CELL[1:]):
        if cell>=lo:return plo+(cell-lo)*(php-plo)//(hi-lo)
    return 0


def decode(data:bytes)->dict:
    if len(data)!=LAYOUT.size:raise ValueError(f'expected {LAYOUT.size} bytes, got {len(data)}')
    (version,flags,seq,ax,ay,az,mx,my,mz,temp,press,mlux,vdd,ain3,rtc)=LAYOUT.unpack(data)
    if version!=1:raise ValueError(f'unknown packet version: {version}')
    ok={name:bool(flags>>i&1) for i,name in enumerate(FLAGS)}
    out=dict(version=version,seq=seq,valid=ok)
    if ok['accel']:
        g=[v/1000 for v in (ax,ay,az)];out['accel']=dict(g=g,norm_g=round(math.hypot(*g),3))
    if ok['magnet']:
        gs=[v/1000 for v in (mx,my,mz)];out['magnet']=dict(gauss=gs,norm_gauss=round(math.hypot(*gs),3))
    if ok['baro']:out['baro']=dict(temp_c=temp/100,pressure_hpa=round(press/256/100,2))
    if ok['light']:out['light']=dict(lux=mlux/1000)
    if ok['rtc']:out['rtc_seconds']=rtc
    if ok['adc']:out['adc']=dict(vdd_v=vdd/1000,ain3_v=ain3/1000,battery_v_estimate=battery_mv(ain3)/1000,
                     battery_percent=battery_percent(battery_mv(ain3)))
    return out
