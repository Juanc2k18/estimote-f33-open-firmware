#!/usr/bin/env python3
"""Compares over SWD the application at 0x26000 with the .bin of a DFU package and reads the 0x7F000 settings.

Read-only; does not halt the CPU. Used to confirm which image a DFU upload left
(UART or BLE) and what the bootloader wrote to its settings page.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

APP=0x26000;SETTINGS=0x7F000


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('zip',type=Path)
    ap.add_argument('--probe',default='E660C0D1C75C942F')
    ap.add_argument('--out',type=Path)
    a=ap.parse_args(argv)
    with zipfile.ZipFile(a.zip) as z:
        app=json.loads(z.read('manifest.json'))['manifest']['application'];image=z.read(app['bin_file'])
    from pyocd.core.helpers import ConnectHelper
    with ConnectHelper.session_with_chosen_probe(unique_id=a.probe,options={'target_override':'nrf52','connect_mode':'attach','resume_on_disconnect':True}) as s:
        t=s.target
        flash=bytes(t.read_memory_block8(APP,len(image)))
        after=bytes(t.read_memory_block8(APP+len(image),64))
        settings=[t.read32(SETTINGS+4*i) for i in range(8)]
    r=dict(zip=str(a.zip),bin_len=len(image),bin_sha256=hashlib.sha256(image).hexdigest(),
           flash_sha256=hashlib.sha256(flash).hexdigest(),match=flash==image,
           first_diff=next((i for i,(x,y) in enumerate(zip(flash,image)) if x!=y),None),
           after_image_erased=all(b==0xFF for b in after),settings_words=[f'0x{w:08x}' for w in settings])
    print(json.dumps(r,indent=1))
    if a.out:a.out.write_text(json.dumps(r,indent=1))
    return 0 if r['match'] else 1


if __name__=='__main__':raise SystemExit(main())
