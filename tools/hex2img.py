#!/usr/bin/env python3
"""Convert a gplink Intel HEX file into a Harmony 650 app image.

    hex2img.py in.hex out.bin

The image starts at 0x9000 (where the bootloader copies it) and may be at
most 0x15C00 bytes. Any data outside 0x9000-0x1EBFF is an error, since it
would mean the linker placed something over the bootloader or config words.
Gaps are filled with 0xFF. Run tools/fixhdr.py on the result.
"""
import sys

BASE, MAX = 0x9000, 0x15C00

mem = {}
upper = 0
for n, line in enumerate(open(sys.argv[1]), 1):
    line = line.strip()
    if not line:
        continue
    if line[0] != ':':
        sys.exit('line %d: not Intel HEX' % n)
    rec = bytes.fromhex(line[1:])
    if sum(rec) & 0xFF:
        sys.exit('line %d: bad record checksum' % n)
    count, addr, kind, data = rec[0], int.from_bytes(rec[1:3], 'big'), rec[3], rec[4:-1]
    if len(data) != count:
        sys.exit('line %d: bad record length' % n)
    if kind == 0:
        for i, b in enumerate(data):
            mem[(upper << 16) + addr + i] = b
    elif kind == 1:
        break
    elif kind == 4:
        upper = int.from_bytes(data, 'big')
    else:
        sys.exit('line %d: unsupported record type %d' % (n, kind))

outside = sorted(a for a in mem if not BASE <= a < BASE + MAX)
if outside:
    sys.exit('data outside 0x%X-0x%X, first at 0x%X; refusing' % (BASE, BASE + MAX - 1, outside[0]))
if mem.get(BASE + 8) != ord('H') or mem.get(BASE + 9) != ord('G'):
    sys.exit('no "HG" header at 0x%X; is startup.o linked?' % BASE)

end = max(mem) + 1
img = bytearray(b'\xff' * (end - BASE))
for a, b in mem.items():
    img[a - BASE] = b
open(sys.argv[2], 'wb').write(img)
print('0x%X bytes (0x%X-0x%X)' % (len(img), BASE, end - 1))
