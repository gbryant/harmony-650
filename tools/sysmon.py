#!/usr/bin/env python3
"""System monitor on the Harmony 650 screen.

    .venv/bin/python tools/sysmon.py

D-pad left/right: change page (overview, CPU, network, colour bars,
spectrum, buttons, about).  All Off: LCD backlight.  Red: button
backlight.  Stop it with Ctrl-C (no remote button quits, so it can't be
stopped by accident).
"""
import collections
import colorsys
import os
import sys
import time

import psutil
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from harmony import Remote  # noqa: E402

W = H = 128
FONT = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 10)
BIG = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 16)
BG, FG, DIM = (0, 0, 0), (230, 230, 230), (110, 110, 110)
CPU_C, MEM_C, DISK_C, UP_C, DOWN_C = (80, 200, 255), (120, 255, 120), (255, 200, 80), (255, 120, 120), (120, 160, 255)
HISTORY = W - 4
# macOS: / is the sealed system volume; user data lives on the Data volume
DISK = '/System/Volumes/Data' if os.path.ismount('/System/Volumes/Data') else '/'


def human_rate(n):
    for unit in ('B', 'K', 'M', 'G'):
        if n < 1024 or unit == 'G':
            return ('%.0f%s' if n >= 10 or unit == 'B' else '%.1f%s') % (n, unit)
        n /= 1024.0


def graph(d, top, bottom, series, color, peak=None):
    peak = peak or max(max(series, default=0), 1e-9)
    h = bottom - top
    pts = [(2 + i, bottom - int(h * min(v / peak, 1.0))) for i, v in enumerate(series)]
    if len(pts) > 1:
        d.line(pts, fill=color)


def page_overview(img, d, s, hist, ui):
    d.text((2, 0), time.strftime('%H:%M:%S'), font=BIG, fill=FG)
    d.text((86, 4), time.strftime('%a'), font=FONT, fill=DIM)
    y = 22
    for label, frac, color, text in (
            ('CPU', s['cpu'] / 100, CPU_C, '%d%%' % s['cpu']),
            ('MEM', s['mem'] / 100, MEM_C, '%d%%' % s['mem']),
            ('DSK', s['disk'] / 100, DISK_C, '%d%%' % s['disk'])):
        d.text((2, y), label, font=FONT, fill=DIM)
        d.rectangle((26, y + 2, 98, y + 10), outline=(60, 60, 60))
        d.rectangle((27, y + 3, 27 + int(70 * max(0.0, min(1.0, frac))), y + 9), fill=color)
        d.text((102, y), text, font=FONT, fill=FG)
        y += 15
    d.text((2, y), 'UP', font=FONT, fill=DIM)
    d.text((26, y), human_rate(s['up']) + '/s', font=FONT, fill=UP_C)
    y += 13
    d.text((2, y), 'DN', font=FONT, fill=DIM)
    d.text((26, y), human_rate(s['down']) + '/s', font=FONT, fill=DOWN_C)
    y += 13
    d.text((2, y), 'LD', font=FONT, fill=DIM)
    d.text((26, y), '%.2f %.2f %.2f' % s['load'], font=FONT, fill=FG)
    d.text((2, 116), 'up ' + s['uptime'], font=FONT, fill=DIM)


def page_cpu(img, d, s, hist, ui):
    d.text((2, 0), 'CPU %d%%' % s['cpu'], font=BIG, fill=CPU_C)
    d.rectangle((1, 22, 126, 70), outline=(50, 50, 50))
    graph(d, 23, 69, list(hist['cpu']), CPU_C, peak=100)
    cores = s['cores']
    n = len(cores)
    bw = max(1, (124 // max(n, 1)) - 1)
    for i, c in enumerate(cores):
        x = 2 + i * (bw + 1)
        d.rectangle((x, 124 - int(46 * c / 100), x + bw - 1, 124), fill=CPU_C)
    d.text((2, 74), '%d cores' % n, font=FONT, fill=DIM)


def page_net(img, d, s, hist, ui):
    d.text((2, 0), 'Network', font=BIG, fill=FG)
    peak = max(max(hist['up'], default=0), max(hist['down'], default=0), 1024)
    d.rectangle((1, 22, 126, 100), outline=(50, 50, 50))
    graph(d, 23, 99, list(hist['down']), DOWN_C, peak)
    graph(d, 23, 99, list(hist['up']), UP_C, peak)
    d.text((2, 104), 'DN ' + human_rate(s['down']) + '/s', font=FONT, fill=DOWN_C)
    d.text((66, 104), 'UP ' + human_rate(s['up']) + '/s', font=FONT, fill=UP_C)
    d.text((2, 116), 'peak ' + human_rate(peak) + '/s', font=FONT, fill=DIM)


def page_colors(img, d, s, hist, ui):
    """SMPTE-style bars, a grey ramp and RGB ramps: a test card for photos."""
    bars = [(192, 192, 192), (192, 192, 0), (0, 192, 192), (0, 192, 0),
            (192, 0, 192), (192, 0, 0), (0, 0, 192)]
    for i, c in enumerate(bars):
        d.rectangle((i * 128 // 7, 0, (i + 1) * 128 // 7 - 1, 69), fill=c)
    for i, c in enumerate([(0, 0, 192), (0, 0, 0), (192, 0, 192), (0, 0, 0),
                           (0, 192, 192), (0, 0, 0), (192, 192, 192)]):
        d.rectangle((i * 128 // 7, 70, (i + 1) * 128 // 7 - 1, 79), fill=c)
    for x in range(128):
        v = x * 255 // 127
        d.line((x, 80, x, 93), fill=(v, v, v))
        d.line((x, 94, x, 103), fill=(v, 0, 0))
        d.line((x, 104, x, 113), fill=(0, v, 0))
        d.line((x, 114, x, 127), fill=(0, 0, v))


def page_spectrum(img, d, s, hist, ui):
    """Hue across, brightness down: shows the panel's full colour range."""
    px = img.load()
    for y in range(128):
        for x in range(128):
            r, g, b = colorsys.hsv_to_rgb(x / 128.0, 1.0 if y < 64 else 1.0 - (y - 64) / 64.0,
                                          y / 64.0 if y < 64 else 1.0)
            px[x, y] = (int(r * 255), int(g * 255), int(b * 255))


def page_buttons(img, d, s, hist, ui):
    """Shows the last button pressed, to demo the input side."""
    d.text((2, 0), 'Buttons', font=BIG, fill=FG)
    d.text((2, 22), 'press any button', font=FONT, fill=DIM)
    name = ui.get('last_button')
    if name:
        label = name.replace('_', ' ')
        font = BIG if d.textlength(label, font=BIG) <= 108 else FONT
        w = d.textlength(label, font=font)
        d.rounded_rectangle((4, 50, 123, 86), radius=8, outline=CPU_C, width=2)
        d.text(((128 - w) / 2, 60 if font is BIG else 63), label, font=font, fill=FG)
        d.text((2, 100), '%d presses' % ui.get('presses', 0), font=FONT, fill=DIM)
    d.text((2, 116), '54 buttons, USB HID', font=FONT, fill=DIM)


def page_about(img, d, s, hist, ui):
    for i, c in enumerate([(255, 80, 80), (255, 200, 80), (120, 255, 120), (80, 200, 255)]):
        d.ellipse((6 + i * 14, 6, 18 + i * 14, 18), fill=c)
    d.text((2, 26), 'Harmony 650', font=BIG, fill=FG)
    d.text((2, 46), 'Status Monitor', font=FONT, fill=CPU_C)
    lines = ['custom firmware in C', 'PIC18F67J50 @ 16 MHz', '128x128 ST7637 LCD',
             'drawn over USB HID', 'github: harmony-650']
    for i, line in enumerate(lines):
        d.text((2, 66 + i * 12), line, font=FONT, fill=DIM if i < 4 else FG)


PAGES = [page_overview, page_cpu, page_net, page_colors, page_spectrum, page_buttons, page_about]


def reconnect(r, lcd, keys):
    """The remote went away (unplugged, reflashed): wait for it, restore the
    backlights. Returns no events; the caller redraws the page."""
    print('remote disconnected; waiting for it to come back', flush=True)
    r.reconnect()
    r.backlight(lcd, keys)
    print('reconnected', flush=True)
    return []


def send(r, action, lcd, keys):
    """Run a display action, reconnecting and retrying once if it fails."""
    try:
        action()
    except IOError:
        reconnect(r, lcd, keys)
        action()


def main():
    r = Remote()
    print('sysmon started', time.strftime('%Y-%m-%d %H:%M:%S'), flush=True)
    r.backlight(lcd=True, keys=False)
    page, lcd, keys = 0, True, False
    ui = {'last_button': None, 'presses': 0}
    hist = {k: collections.deque(maxlen=HISTORY) for k in ('cpu', 'up', 'down')}
    psutil.cpu_percent(percpu=True)
    net = psutil.net_io_counters()
    t_net = time.time()
    next_sample = 0
    s = None
    while True:
        now = time.time()
        if now >= next_sample:
            next_sample = now + 1
            n2 = psutil.net_io_counters()
            dt = max(now - t_net, 1e-3)
            cores = psutil.cpu_percent(percpu=True)
            up_s = int(now - psutil.boot_time())
            s = {
                'cpu': sum(cores) / len(cores), 'cores': cores,
                'mem': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage(DISK).percent,
                'up': (n2.bytes_sent - net.bytes_sent) / dt,
                'down': (n2.bytes_recv - net.bytes_recv) / dt,
                'load': os.getloadavg(),
                'uptime': '%dd %02d:%02d' % (up_s // 86400, up_s // 3600 % 24, up_s // 60 % 60),
            }
            net, t_net = n2, now
            hist['cpu'].append(s['cpu'])
            hist['up'].append(s['up'])
            hist['down'].append(s['down'])
            dirty = True
        else:
            dirty = False

        try:
            events = r.events()
        except IOError:
            events = reconnect(r, lcd, keys)
            dirty = True
        for name, pressed in events:
            if not pressed:
                continue
            ui['last_button'] = name
            ui['presses'] += 1
            if name == 'dpad_right':
                page = (page + 1) % len(PAGES)
            elif name == 'dpad_left':
                page = (page - 1) % len(PAGES)
            elif name == 'off':
                lcd = not lcd
                send(r, lambda: r.backlight(lcd, keys), lcd, keys)
            elif name == 'red':
                keys = not keys
                send(r, lambda: r.backlight(lcd, keys), lcd, keys)
            dirty = True

        if dirty and s:
            img = Image.new('RGB', (W, H), BG)
            d = ImageDraw.Draw(img)
            PAGES[page](img, d, s, hist, ui)
            # page dots, except on the full-screen test pages
            if PAGES[page] not in (page_colors, page_spectrum):
                x0 = 126 - len(PAGES) * 5
                for i in range(len(PAGES)):
                    d.ellipse((x0 + i * 5, 118, x0 + i * 5 + 2, 120), fill=FG if i == page else (60, 60, 60))
            send(r, lambda: r.show(img), lcd, keys)
        time.sleep(0.02)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print('sysmon stopped', time.strftime('%Y-%m-%d %H:%M:%S'), flush=True)
