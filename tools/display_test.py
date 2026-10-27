#!/usr/bin/env python3
"""Check the LCD's visible area and draw speed.

White 1-pixel border at 0..127, red in the controller RAM beyond it
(128..131). Seeing all four white edges and no red means 128x128 at 0,0.
"""
import os
import sys
import time

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
from harmony import Remote  # noqa: E402

r = Remote()
r.fill(0, 0, 131, 131, (255, 0, 0))     # whole RAM red
img = Image.new('RGB', (128, 128), (0, 0, 48))
d = ImageDraw.Draw(img)
d.rectangle((0, 0, 127, 127), outline=(255, 255, 255))
font = ImageFont.truetype('/System/Library/Fonts/Menlo.ttc', 11)
d.text((6, 8), 'Harmony 650', font=font, fill=(255, 255, 255))
d.text((6, 24), 'custom firmware', font=font, fill=(120, 200, 255))
for i, (name, c) in enumerate([('red', (255, 0, 0)), ('green', (0, 255, 0)), ('blue', (0, 0, 255))]):
    d.rectangle((6 + i * 40, 50, 6 + i * 40 + 34, 70), fill=c)
d.text((6, 80), 'top-left: (0,0)', font=font, fill=(255, 255, 0))
t = time.time()
r.show(img)
full = time.time() - t
d.text((6, 100), 'full frame %.2fs' % full, font=font, fill=(200, 200, 200))
r.show(img)
print('full frame took %.2f s' % full)
r.close()

# Benchmark: worst case (noise), flat colour, and a typical UI frame
import random  # noqa: E402

r = Remote()
noise = Image.frombytes('RGB', (128, 128), bytes(random.randrange(256) for _ in range(128 * 128 * 3)))
flat = Image.new('RGB', (128, 128), (0, 80, 0))
for name, im in (('noise (worst case)', noise), ('flat colour', flat), ('test pattern', img)):
    r.frame = None
    t = time.time()
    r.show(im)
    print('%-20s %.2f s' % (name, time.time() - t))
r.close()
