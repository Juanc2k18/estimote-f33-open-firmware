#!/usr/bin/env python3
"""Exports the published nRF pin guide SVG using VectorCraft.

Only the nRF SVG is published; native masters and PNG exports are not saved.
Do not run after manual annotations without first incorporating them here.
"""
import base64
import hashlib
import json
import subprocess
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / 'docs/diagrams'
RTC_PHOTO = PROJECT / 'docs/evidence/photos-rtc-r30-2026-11-19/derived/rtc-reading.png'
RTC_PINOUT = {1: 'SDA', 2: 'SQW', 3: 'VSS / GND', 4: 'NC', 5: 'VCC', 6: 'IRQ/OUT', 7: 'NC', 8: 'SCL'}
RTC_PHOTO_CONTACTS = {1:(345,748),2:(464,718),3:(591,691),4:(704,665),5:(634,433),6:(518,459),7:(397,485),8:(279,512)}
W, H = 1800, 1200
INK, MUTED, BG = '#18322F', '#60736D', '#F6F8F3'
LINE, TEAL, AMBER = '#D6E0D9', '#28776E', '#A36A16'
COLORS = {'A': '#2864AE', 'B': '#C66D21', 'E': '#8252A1', 'G': '#387C55', 'E1': '#B23A64', 'E2': '#6D4C41'}
VERIFIED = {'A', 'B', 'E', 'G'}  # A/B/G: continuity; E: functional UART + SWO validation
PINS = [
    ('A', 'SWDCLK confirmed', '25', 'Continuity + SWD (r10–r12)', 'Pico GP2 · physical pin 4'),
    ('B', 'SWDIO confirmed', '26', 'Continuity + SWD (r10–r12)', 'Pico GP3 · physical pin 5'),
    ('C', 'VDD confirmed', '13 / 36 / 48 *', 'Owner + SAADC (r09/r25)', 'VDD ~1.992 V; currently no power supply on C'),
    ('D', 'Unresolved', 'Unassigned', 'Reported voltage (r23)', 'Owner: D/F = 0.94 V; MCU connection unresolved'),
    ('E', 'P0.18 / SWO confirmed', '21', 'UART + ITM/SWO (r26)', 'Functional validation; no ohmic measurement'),
    ('F', 'Negative / GND', 'VSS 31 / 45 / EP *', 'Owner + SWD setup', 'Common ground with the Pico; do not confuse with H'),
    ('G', 'P0.21 / nRESET confirmed', '24', '~2.1 Ω + physical reset (r21)', 'PSELRESET=21; G→F pulse validated'),
    ('H', 'Positive / battery', 'Regulator input', 'Owner + curve (r20)', 'Battery input; VDD regulated to 2.0 V'),
    ('E1', 'Beacon UART TX', '16 · P0.13', 'Continuity + DFU (r08/r15)', 'To host RX / Pico GP5'),
    ('E2', 'Beacon UART RX', '15 · P0.12', 'Continuity + DFU (r08/r15)', 'From host TX / Pico GP4'),
    ('E3', 'External power input', 'Not the MCU VDD', 'Owner', 'Use 3.3 V; 5 V exceeds the nRF VDD limit'),
    ('E4', 'External GND', 'Ground net', 'Owner', 'Internal route without a recorded measurement'),
]


class VC:
    def __init__(self):
        self.p = subprocess.Popen([
            str(Path.home() / '.cargo/bin/vectorcraft-cli'), 'mcp',
            '--automation-read-root', str(PROJECT),
            '--automation-write-root', str(PROJECT),
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.n = 0
        self.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {},
                               'clientInfo': {'name': 'estimote-pin-map', 'version': '1'}})
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})

    def send(self, obj):
        self.p.stdin.write(json.dumps(obj) + '\n')
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.n += 1
        self.send({'jsonrpc': '2.0', 'id': self.n, 'method': method, 'params': params})
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError('The CLI ended without a response')
            result = json.loads(line)
            if result.get('id') == self.n:
                if 'error' in result:
                    raise RuntimeError(result['error'])
                return result['result']

    def raw(self, tool_name, **arguments):
        result = self.rpc('tools/call', {'name': tool_name, 'arguments': arguments})
        if result.get('isError'):
            raise RuntimeError(result)
        return result

    def tool(self, tool_name, **arguments):
        result = self.raw(tool_name, **arguments)
        content = ''.join(c.get('text', '') for c in result.get('content', []) if c['type'] == 'text')
        try:
            return json.loads(content)
        except ValueError:
            return content

    def cmd(self, command, **params):
        return self.tool('command_run', id=command, params=params)

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=20)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    v = VC()
    text_count = 0

    def layer(name):
        v.cmd('layer.new', name=name)

    def rect(x, y, w, h, fill, stroke='none', radius=0, sw=1, name=''):
        return v.tool('draw_shape', shape='rectangle', x=x, y=y, width=w, height=h,
                      fill=fill, stroke=stroke, strokeWidth=sw, radius=radius, name=name)

    def text(s, x, y, size=16, color=INK, center=False):
        nonlocal text_count
        r = v.tool('add_text', text=s, x=x, y=y, size=size, font='Helvetica', color=color,
                   justify='center' if center else 'left')
        if isinstance(r, dict) and r.get('overflow'):
            raise RuntimeError(f'Text overflow: {s}')
        text_count += 1
        return r

    def path(d, color=LINE, sw=1, fill='none', dash=None, name=''):
        args = dict(d=d, stroke=color, strokeWidth=sw, fill=fill, name=name)
        if dash:
            args['dash'] = dash
        return v.tool('draw_path', **args)

    def line(x, y, xx, yy, color=LINE, sw=1, dash=None):
        return path(f'M{x} {y} L{xx} {yy}', color, sw, dash=dash)

    def circle(x, y, r, fill, stroke='none'):
        return v.tool('draw_shape', shape='ellipse', x=x-r, y=y-r, width=2*r,
                      height=2*r, fill=fill, stroke=stroke, strokeWidth=1)

    def header(off, number, title, sub, notice=None):
        rect(off, 0, W, H, BG)
        text('ESTIMOTE F3.3 / PIN REFERENCE', off+48, 48, 14, TEAL)
        text(title, off+48, 99, 34)
        text(sub, off+48, 135, 17, MUTED)
        rect(off+48, 158, W-96, 48, '#FFF0D5', radius=6)
        text(notice or 'SWD · UART · SWO · nRESET verified on this unit · Pad D unresolved', off+66, 189, 17, AMBER)
        line(off+48, 1132, off+W-48, 1132)
        text('2026 · Owner reports and measurements identified separately. Not to scale.', off+48, 1164, 14, MUTED)
        text(f'{number} / 3', off+W-95, 1164, 14, MUTED)

    v.cmd('file.new', width=W, height=H)
    layer('01 · Pinout r26 and evidence table')
    header(0, 1, 'F3.3 pin map', 'Antenna up · eight pads on the right · E1–E4 left to right · not to scale')
    text('WORKING POSITIONS', 48, 250, 15, TEAL)
    path('M80 635 C56 466 130 367 293 310 L355 276 C445 232 538 266 626 321 L740 391 C840 454 886 574 835 701 C777 822 572 867 342 836 C173 813 92 761 80 635 Z', INK, 2, '#FFFFFF')
    path('M336 321 Q434 266 540 320', TEAL, 5)
    text('ANTENNA / LOGO UP', 438, 350, 13, TEAL, True)
    rect(240, 465, 145, 145, INK, radius=5)
    text('nRF52832', 312, 520, 18, '#FFFFFF', True)
    text('QFN48 · approximate', 312, 550, 13, '#FFFFFF', True)
    text('position', 312, 573, 13, '#FFFFFF', True)
    rect(475, 415, 34, 76, '#D8DBCF', MUTED, 3, 1, 'RTC M41T62 · approximate location')
    circle(502, 484, 3, AMBER)
    text('RTC', 492, 450, 11, INK, True)
    text('Sheet 3', 525, 477, 12, TEAL)
    # Pin 1 dot observed by the owner: bottom-left corner.
    circle(254, 596, 7, '#FFFFFF', AMBER)
    text('Pin 1 dot: bottom left (owner)', 160, 634, 12, AMBER)
    path('M624 420 L642 420 L624 438 Z', MUTED, 1, dash=[3, 3], name='Triangle mark · not observed on this unit')
    text('Triangle: not seen on this unit', 404, 433, 12, MUTED)
    for row in range(4):
        for col in range(2):
            p = chr(65+2*row+col)
            x, y = 646+col*90, 440+row*76
            c = COLORS.get(p, TEAL if p in 'FH' else AMBER)
            rect(x, y, 68, 58, '#FFFFFF', c, 5, 2, f'Pad {p} · temporary')
            text(p, x+34, y+38, 25, c, True)
    for i in range(4):
        rect(450+i*60, 756, 20, 45, '#D6A944', radius=2)
    rect(424, 786, 266, 66, INK, radius=5)
    for i in range(4):
        text(f'E{i+1}', 460+i*60, 827, 17, '#FFFFFF', True)
    text('The letters A–H are ours, not the manufacturer\'s.', 80, 903, 16, MUTED)
    text('I²C: SDA P0.14 · SCL P0.15 · internal pull-ups.', 80, 932, 16, MUTED)
    text('Enable P0.06/P0.07 high; wait about 1 second.', 80, 961, 16, MUTED)
    text('Battery divider: P0.05 / AIN3 (~1:6). LED: P0.17.', 80, 990, 16, AMBER)
    text('UART: power E3 at 3.3 V; disconnect H.', 80, 1019, 16, AMBER)
    # Wide, two-line rows preserve both evidence source and pending action.
    rect(904, 230, 848, 840, '#FFFFFF', LINE, 8)
    for x, s in [(924, 'ID'), (986, 'FUNCTION / STATUS'), (1248, 'PIN / TARGET'), (1494, 'EVIDENCE / PENDING')]:
        text(s, x, 265, 12, TEAL)
    line(920, 282, 1735, 282)
    for i, (p, func, pin, source, pending) in enumerate(PINS):
        y = 313+i*60
        c = COLORS.get(p, INK)
        text(p, 924, y, 19, c)
        text(func, 986, y, 15, c)
        text(pin, 1248, y, 14, MUTED)
        text(source, 1494, y, 13, MUTED)
        text(pending, 986, y+22, 12, AMBER)
        line(920, y+32, 1735, y+32)
    text('* VDD/VSS: chip references; no complete ohmic trace.', 924, 1052, 13, MUTED)
    text('Never power H and E3 together. Do not supply C while either input is powered.', 48, 1101, 15, MUTED)

    # Integrated guide: keep the outline, MCU on the left, pads on the right and connector at the bottom.
    off = 1900
    qfn_off = off
    v.cmd('artboard.new', x=off, y=0, width=W, height=H, name='QFN48 guide and validated links')
    layer('03 · QFN48 and validated links r26')
    header(off, 2, 'Visual guide on the board · nRF52832-QFAA', 'Reference outline and layout kept · MCU on the left · pads on the right · external connector at the bottom')
    text('SAME BOARD / SAME CONTACT LAYOUT', off+60, 260, 15, TEAL)
    text('Solid = validated link; the method is shown on the right. These are guides, not physical traces.', off+60, 291, 15, AMBER)
    # Board outline and placement references, without claiming a physical trace.
    path(f'M{off+90} 710 C{off+64} 560 {off+180} 464 {off+360} 415 L{off+480} 350 C{off+590} 285 {off+730} 310 {off+860} 388 L{off+1090} 488 C{off+1250} 550 {off+1340} 680 {off+1260} 820 C{off+1190} 950 {off+920} 985 {off+640} 980 C{off+320} 975 {off+130} 900 {off+90} 710 Z', INK, 2, '#FFFFFF')
    path(f'M{off+500} 368 Q{off+650} 300 {off+800} 372', TEAL, 5)
    text('ANTENNA / LOGO UP', off+650, 395, 14, TEAL, True)
    for x, y in [(620,438),(710,438),(600,916),(700,924)]:
        circle(off+x,y,13,'#E2E7E1',MUTED)
    for x,y,w,h in [(820,453,45,40),(884,478,54,54),(900,570,45,48),(720,555,45,40),(746,630,34,48),(234,660,34,42),(200,800,34,40)]:
        rect(off+x,y,w,h,'#DBE1DA',radius=3)
    for i in range(4):
        rect(off+821+i*59,882,18,43,'#D6A944',radius=2)
    rect(off+795,909,257,62,INK,radius=5)
    for i in range(4):
        text(f'E{i+1}',off+830+i*59,948,16,'#FFFFFF',True)
    text('E1 TX / E2 RX · E3 3.3 V / E4 GND',off+780,999,13,MUTED)
    bx, by, side = off+330, 520, 300
    spacing = side/13
    pin_points = {}
    # Pin 1 dot observed at the bottom left: package rotated 90° counter-clockwise
    # relative to the standard view. Counter-clockwise numbering seen from above.
    for i in range(12):
        pin_points[1+i] = (bx+(i+1)*spacing, by+side+18, 'bottom')
        pin_points[13+i] = (bx+side+18, by+side-(i+1)*spacing, 'right')
        pin_points[25+i] = (bx+side-(i+1)*spacing, by-18, 'top')
        pin_points[37+i] = (bx-18, by+(i+1)*spacing, 'left')
    pad_centers = {}
    for row in range(4):
        for col in range(2):
            p = chr(65+2*row+col)
            x, y = off+960+col*90, 520+row*80
            pad_centers[p] = (x+74, y+27)
            c = COLORS.get(p, TEAL if p in 'FH' else AMBER)
            rect(x, y, 74, 54, '#FFFFFF', c, 4, 2)
            text(p, x+37, y+36, 24, c, True)
    text('A/B SWD · E SWO · G nRESET: validated', off+960, 426, 13, AMBER)
    path(f'M{off+938} 502 L{off+956} 502 L{off+938} 520 Z', MUTED, 1, dash=[3, 3], name='Triangle mark · not observed on this unit')
    connections = {'A': 25, 'B': 26, 'E': 21, 'G': 24}
    for p, pin in connections.items():
        sx, sy = pad_centers[p]
        tx, ty, edge = pin_points[pin]
        cx = sx-37  # horizontal centre of the pad
        if p == 'A':
            # Leaves from the top and enters 25 from above.
            d=f'M{cx} {sy-27} L{cx} 482 L{tx} 482 L{tx} {ty}'
        elif p == 'B':
            # Outer lane above A's: they do not cross.
            d=f'M{cx} {sy-27} L{cx} 464 L{tx} 464 L{tx} {ty}'
        else:
            # E/G leave from the left towards the right side of the nRF.
            # E→21 and G→24 cross once: the order of pads and pins is reversed.
            elbow=off+{'E':800,'G':724}[p]
            d=f'M{sx-74} {sy} L{elbow} {sy} L{elbow} {ty} L{tx} {ty}'
        verified = p in VERIFIED
        path(d, COLORS[p], 3, dash=None if verified else [9, 5],
             name=f'{p} to pin {pin} · ' + ('functional UART + SWO r26' if p == 'E' else 'continuity + reset r21' if p == 'G' else 'continuity + SWD r12'))
    # E1/E2: continuity measured by the owner (r08) → solid line.
    # They cross once: E1 (left) goes to the higher pin.
    for p, pin, px, low, vx in [('E1', 16, off+830, 874, off+698), ('E2', 15, off+889, 862, off+710)]:
        tx, ty, edge = pin_points[pin]
        d=f'M{px} 882 L{px} {low} L{vx} {low} L{vx} {ty} L{tx} {ty}'
        path(d, COLORS[p], 3, name=f'{p} to pin {pin} · continuity reported by the owner')
    rect(bx, by, side, side, '#FFFFFF', INK, 7, 2)
    circle(bx+20, by+side-20, 6, AMBER)
    text('Pin 1 dot · observed (owner)', bx+34, by+side-15, 11, AMBER)
    text('nRF52832',bx+side/2,by+100,24,INK,True)
    text('QFAA / QFN48',bx+side/2,by+134,18,INK,True)
    text('Top view · rotated 90°',bx+side/2,by+170,13,TEAL,True)
    text('Pin 1 at the bottom left.',bx+side/2,by+195,12,MUTED,True)
    rect(bx+112,by+210,76,40,'#E5ECE7',LINE,3)
    text('EP / VSS',bx+150,by+236,12,TEAL,True)
    special = {25: 'A', 26: 'B', 21: 'E', 24: 'G', 16: 'E1', 15: 'E2'}
    for pin, (x, y, edge) in pin_points.items():
        color = COLORS[special[pin]] if pin in special else TEAL if pin in (31,45) else AMBER if pin in (13,36,48) else '#AEBBB3'
        if edge in ('left', 'right'):
            rect(x-12, y-8, 24, 16, color, radius=2, name=f'QFN48 pin {pin}')
            label_x = x-37 if edge == 'left' else x+27
            if pin in (15, 16):
                label_x = x-46  # inside the package: there are vertical routes outside
            # The routes leave horizontally to the right: the number goes above.
            label_y = y-6 if pin in special else y+4
            text(str(pin), label_x, label_y, 11, color)
        else:
            rect(x-8, y-12, 16, 24, color, radius=2, name=f'QFN48 pin {pin}')
            # 25/26 receive routes from above: their number goes inside the package.
            label_y = (y+35 if pin in special else y-23) if edge == 'top' else y-55
            text(str(pin), x, label_y, 11, color, True)
    for i, (p, pin, func) in enumerate([('A',25,'SWDCLK'),('B',26,'SWDIO'),('E',21,'P0.18 / SWO'),('G',24,'P0.21 / nRESET')]):
        y = 384+i*70
        text(f'{p} → {pin}', off+1470, y, 21, COLORS[p])
        text(func, off+1470, y+26, 16, COLORS[p])
        text({'A': 'Continuity + SWD (r10–r12)', 'B': 'Continuity + SWD (r10–r12)', 'E': 'Functional: UART + ITM/SWO (r26)', 'G': '~2.1 Ω + physical reset (r21)'}[p], off+1470, y+47, 12, TEAL)
    text('F → VSS 31 / 45 / EP', off+1470, 708, 16, TEAL)
    text('GND reported; continuity pending.', off+1470, 733, 12, MUTED)
    text('C → VDD 13 / 36 / 48', off+1470, 783, 16, AMBER)
    text('C/F ~2 V; supply on H/F, not on C.', off+1470, 808, 12, MUTED)
    text('E1 → 16 · P0.13', off+1470, 858, 16, COLORS['E1'])
    text('E2 → 15 · P0.12', off+1470, 884, 16, COLORS['E2'])
    text('Continuity r08 + UART DFU r15. UWB differs.', off+1470, 908, 12, MUTED)
    text('E → Pico GP5 / physical pin 7: SWO RX.', off+1470, 950, 13, TEAL)
    text('Pin 1 and absence of NFC: owner report.', off+1470, 974, 13, MUTED)
    # Explicit non-connections prevent interpreting H as a voltage-reference pin.
    for i, (title, body) in enumerate([
        ('C · VDD confirmed', 'SAADC r25: ~1.992 V. C without supply.'),
        ('D · unresolved', 'Owner: D/F=0.94 V; connection unresolved.'),
        ('H · battery +', '6 V set on H/F; not a maximum rating.'),
    ]):
        x, y = off+70+i*560, 1010
        rect(x, y, 520, 80, '#FFFFFF', LINE, 6)
        text(title, x+18, y+30, 18, AMBER)
        text(body, x+18, y+58, 15, MUTED)
    text('E validated functionally, no ohms recorded. G validated with continuity and reset. UWB routes are not copied.', off+70, 1114, 13, MUTED)
    # RTC locator on the plate; numbering is shown separately at enlarged scale.
    rect(off+827, 505, 48, 106, '#D8DBCF', MUTED, 3, 1, 'RTC M41T62 · approximate location, see sheet 4')
    circle(off+866, 602, 4, AMBER)  # Bottom-right dot in the board view, indicated by the owner.
    text('RTC', off+851, 548, 11, INK, True)
    text('M41T62', off+851, 568, 10, INK, True)
    text('Sheet 3', off+851, 592, 10, TEAL, True)

    # Fourth artboard: native labels over actual owner photo and a top-view key.
    off = 3800
    v.cmd('artboard.new', x=off, y=0, width=W, height=H, name='RTC M41T62 · LCC8 contacts')
    layer('04 · RTC on our own macro and documented top-view numbering')
    header(off, 3, 'RTC M41T62 · numbering of the eight contacts',
           'Owner photo · rotated 180° · top view, not mirrored',
           'LCC8 pin numbering · dot is a visual reference; package orientation is not continuity-verified')
    rect(off+48, 225, 1000, 869, '#FFFFFF', LINE, 8)
    text('REAL PHOTO / MARKED CONTACTS', off+68, 257, 15, TEAL)
    photo_x, photo_y, photo_w, photo_h = off+48, 275, 1000, 1000*832/1058
    v.cmd('file.place', path=str(RTC_PHOTO), link=False, rect=[photo_x, photo_y, photo_w, photo_h])
    scale = photo_w/1058
    rtc_colors = {1:TEAL,8:TEAL,3:'#2864AE',5:AMBER,6:'#8252A1',2:INK,4:MUTED,7:MUTED}
    rtc_centers = {}
    for pin,(px,py) in RTC_PHOTO_CONTACTS.items():
        ax,ay = photo_x+px*scale,photo_y+py*scale
        rtc_centers[pin]=(ax,ay)
        lx,ly = ax,(1028 if pin<=4 else 565)
        col=rtc_colors[pin]
        # Thin leaders end on solder, rather than obscuring the contact with a badge.
        line(ax,ay,lx,ly-15 if pin<=4 else ly+28,col,2)
        circle(ax,ay,5,'none',col)
        rect(lx-48,ly-20,96,53,'#FFFFFF',col,5)
        text(str(pin),lx,ly+1,20,col,True)
        text(RTC_PINOUT[pin],lx,ly+23,12,col,True)
    # The visible round mark is a photographic reference, not a new ohmic proof.
    dx,dy=photo_x+330*scale,photo_y+650*scale
    circle(dx,dy,15,'none',AMBER)
    line(off+255,900,dx-16,dy,AMBER,2)
    rect(off+66,873,190,52,'#FFFFFF',AMBER,5)
    text('Dot used to',off+78,894,13,AMBER)
    text('start counting',off+78,913,13,AMBER)
    text('Bottom: 1 → 2 → 3 → 4. Top, right to left: 5 → 6 → 7 → 8.',off+65,1080,13,MUTED)

    rect(off+1080,225,672,869,'#FFFFFF',LINE,8)
    text('LCC8 REFERENCE / TOP VIEW',off+1104,267,17,TEAL)
    bx,by,bw,bh=off+1210,350,400,180
    rect(bx,by,bw,bh,'#D8DBCF',INK,8,2)
    text('M41T62',bx+bw/2,by+66,28,INK,True)
    text('Upright text · marked face',bx+bw/2,by+102,15,MUTED,True)
    circle(bx+32,by+bh-28,9,AMBER)
    text('Dot reference',bx+54,by+bh-23,12,AMBER)
    for pin in range(1,9):
        i=pin-1 if pin<=4 else 8-pin
        x=bx+50+100*i
        y=by+bh+12 if pin<=4 else by-12
        col=rtc_colors[pin]
        rect(x-24,y-12,48,24,col,radius=2)
        text(str(pin),x,y+6,18,'#FFFFFF',True)
        text(RTC_PINOUT[pin],x,y+39 if pin<=4 else y-25,13,col,True)
    line(off+1104,606,off+1728,606)
    notes={1:'SDA → P0.14 (I²C validated)',2:'Clock output; not measured',3:'Check continuity with F',4:'No internal connection (NC)',5:'Voltage still undetermined',6:'Reported to nRF22 / P0.19',7:'No internal connection (NC)',8:'SCL → P0.15 (I²C validated)'}
    for i in range(8):
        pin=i+1;y=641+i*31;col=rtc_colors[pin]
        text(str(pin),off+1110,y,17,col)
        text(RTC_PINOUT[pin],off+1150,y,16,col)
        text(notes[pin],off+1320,y,14,MUTED)
    rect(off+1104,908,624,148,'#F8F1FC','#8252A1',6)
    text('6 / IRQ-OUT → nRF terminal 22 / P0.19',off+1120,940,20,'#8252A1')
    text('Continuity reported by you in r29; no ohms recorded.',off+1120,969,14,MUTED)
    text('The IRQ function was not validated with an alarm.',off+1120,994,14,MUTED)
    text('Do not confuse this 6 with pin 6 of the Pico.',off+1120,1019,14,MUTED)
    text('P0.19 is the RTC IRQ; the LED uses P0.17.',off+1120,1043,13,AMBER)
    text('Source: ST M41T62, LCC8 (Fig. 4 of DS3840). The pad drawing at the bottom of the mechanical sheet is a bottom view.',off+65,1112,13,MUTED)

    # Export only the selected public guide; do not recreate retired artifacts.
    v.cmd('select.set', ids=[])
    print('EXPORT', v.tool('export', path=str(OUT/'pin-map-guide-nrf.svg'),
                           artboard=1, outlineText=False), flush=True)
    result = v.raw('render_preview', max_side=W, artboard=1)
    for block in result.get('content', []):
        if block['type'] == 'image':
            (Path('/tmp')/'f33-preview-guide-nrf.png').write_bytes(base64.b64decode(block['data']))
    inspection = v.tool('doc_inspect', depth=3, childLimit=150)
    (Path('/tmp')/'f33-diagram-inspection.json').write_text(json.dumps(inspection, ensure_ascii=False, indent=2))
    (PROJECT/'docs/pin-candidates.json').write_text(json.dumps({
        'date': '2026', 'status': 'Current pinout; RTC package orientation not continuity-verified',
        'diagram': 'docs/diagrams/pin-map-guide-nrf.svg', 'candidate_connections': {},
        'confirmed_connections': connections,
        'connection_evidence': {'A': 'Continuity r10 + SWD r12', 'B': 'Continuity r10 + SWD r12', 'E': 'Functional UART + SWO/ITM r26; no ohms recorded', 'G': 'Continuity ~2.1 Ω and physical reset r21'},
        'pin1_corner': 'bottom left, antenna up (visual observation by the owner)',
        'qfn48_orientation': 'bottom 1-12 left→right; right 13-24 bottom→top; top 25-36 right→left; left 37-48 top→bottom',
        'triangle_mark': 'not observed on this unit (owner)',
        'nfc': 'no NFC coil (owner)',
        'pins': [dict(zip(['pad','function','target','evidence','pending'], p)) for p in PINS],
        'qfn48_positions': {str(p): [x-qfn_off,y,edge] for p,(x,y,edge) in pin_points.items()},
        'rtc': {'model': 'M41T62', 'identification': 'visual r28/r30', 'package': 'LCC8', 'pin_functions': RTC_PINOUT, 'photo': str(RTC_PHOTO.relative_to(PROJECT)), 'photo_view': 'top; rotated 180 degrees; dot at bottom left', 'photo_contacts': {str(p):list(xy) for p,xy in RTC_PHOTO_CONTACTS.items()}, 'orientation_electrically_confirmed': False, 'reported_connection': {'rtc_pin':6, 'nrf_terminal':22, 'nrf_gpio':19, 'source':'owner r29; no ohms recorded'}},
        'text_objects_created': text_count,
    }, ensure_ascii=False, indent=2)+'\n')
    files = [OUT/'pin-map-guide-nrf.svg']
    (OUT/'SHA256SUMS').write_text(''.join(
        f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n' for p in files))
    v.close()
    print('DONE · published nRF SVG only ·', text_count, 'scene texts', flush=True)


if __name__ == '__main__':
    main()
