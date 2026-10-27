#!/usr/bin/env python3
"""Annotate a gpdasm PIC18F67J50 listing with SFR names.

    sfrnames.py p18f67j50.inc in.lst > out.lst

Access-bank operands (a=0, 0x60-0xFF) map to 0xF60-0xFFF. Banked operands
(a=1) map to BSR*0x100 + f, with BSR tracked from the last movlb in straight-
line order (an approximation across branches). movff operands are absolute.
"""
import re
import sys

sfr = {}
for line in open(sys.argv[1]):
    m = re.match(r"^(\w+)\s+EQU\s+H'0?([0-9A-Fa-f]{3,4})'", line)
    if m:
        a = int(m.group(2), 16)
        if a >= 0xF40 and a not in sfr:
            sfr[a] = m.group(1)

bsr = None
for line in open(sys.argv[2]):
    line = line.rstrip('\n')
    m = re.match(r'^([0-9a-f]{6}):  [0-9a-f]{4}  (\w+)\s+(.*)$', line)
    note = ''
    if m:
        op, args = m.group(2), m.group(3)
        if op == 'movlb':
            bsr = int(args, 16)
        elif op == 'movff':
            names = [sfr.get(int(x, 16)) for x in re.findall(r'0x([0-9a-f]+)', args)]
            note = ', '.join(n or '-' for n in names) if any(names) else ''
        else:
            fm = re.match(r'0x([0-9a-f]+)(?:, 0x[0-9a-f])?, 0x([01])$', args)
            if fm:
                f, a = int(fm.group(1), 16), fm.group(2)
                addr = (0xF00 + f if f >= 0x60 else None) if a == '0' else \
                    (bsr * 0x100 + f if bsr is not None else None)
                if addr in sfr:
                    note = sfr[addr]
    print(line + ('    ; ' + note if note else ''))
