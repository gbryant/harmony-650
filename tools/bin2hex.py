#!/usr/bin/env python3
"""Write a binary as Intel HEX (INHX32) at a load address: bin2hex.py in.bin out.hex base [len]"""
import sys

def rec(addr, typ, data):
    b = [len(data), (addr >> 8) & 0xFF, addr & 0xFF, typ] + list(data)
    return ':' + ''.join('%02X' % x for x in b) + '%02X\n' % ((-sum(b)) & 0xFF)

src, dst, base = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
data = open(src, 'rb').read()
if len(sys.argv) > 4:
    data = data[:int(sys.argv[4], 0)]
with open(dst, 'w') as out:
    hi = None
    for off in range(0, len(data), 16):
        a = base + off
        if a >> 16 != hi:
            hi = a >> 16
            out.write(rec(0, 4, [hi >> 8, hi & 0xFF]))
        out.write(rec(a & 0xFFFF, 0, data[off:off + 16]))
    out.write(rec(0, 1, []))
