#!/usr/bin/env python3
"""System monitor on the Harmony 650 screen.

    .venv/bin/python tools/sysmon.py

D-pad left/right: change page.  All Off: LCD backlight.  Red: button
backlight.  Exit: quit.
"""
import collections
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


def page_overview(d, s):
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


def page_cpu(d, s, hist):
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


def page_net(d, s, hist):
    d.text((2, 0), 'Network', font=BIG, fill=FG)
    peak = max(max(hist['up'], default=0), max(hist['down'], default=0), 1024)
    d.rectangle((1, 22, 126, 100), outline=(50, 50, 50))
    graph(d, 23, 99, list(hist['down']), DOWN_C, peak)
    graph(d, 23, 99, list(hist['up']), UP_C, peak)
    d.text((2, 104), 'DN ' + human_rate(s['down']) + '/s', font=FONT, fill=DOWN_C)
    d.text((66, 104), 'UP ' + human_rate(s['up']) + '/s', font=FONT, fill=UP_C)
    d.text((2, 116), 'peak ' + human_rate(peak) + '/s', font=FONT, fill=DIM)


PAGES = [page_overview, page_cpu, page_net]


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
    r.backlight(lcd=True, keys=False)
    page, lcd, keys = 0, True, False
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
            elif name == 'exit':
                r.close()
                return
            dirty = True

        if dirty and s:
            img = Image.new('RGB', (W, H), BG)
            d = ImageDraw.Draw(img)
            fn = PAGES[page]
            if fn is page_overview:
                fn(d, s)
            else:
                fn(d, s, hist)
            # page dots
            for i in range(len(PAGES)):
                d.ellipse((112 + i * 5, 118, 114 + i * 5, 120), fill=FG if i == page else (60, 60, 60))
            send(r, lambda: r.show(img), lcd, keys)
        time.sleep(0.02)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
