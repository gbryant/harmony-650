#!/usr/bin/env python3
"""Rebuild the arch 14 firmware header of a (modified) image, like Logitech's
getValidFirmware: size field, FFFF, "HG" marker, checksum.

    fixhdr.py in.bin out.bin
"""
import sys

img = bytearray(open(sys.argv[1], 'rb').read())
if len(img) % 2:
    img.append(0xFF)
size = len(img) - 8
img[2:4] = b'\xff\xff'
img[4:7] = size.to_bytes(3, 'little')
img[8:10] = b'HG'
a, b = 0x21, 0x43
for i in range(4, len(img), 2):
    a ^= img[i]
    b ^= img[i + 1]
img[0:2] = bytes([a, b])
open(sys.argv[2], 'wb').write(img)
print('0x%X bytes, checksum %02X%02X' % (len(img), a, b))
