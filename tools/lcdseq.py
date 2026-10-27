#!/usr/bin/env python3
"""Extract the LCD command/data sequence from a stock firmware routine.

    lcdseq.py disasm/fw04_sfr.lst START [END]

Follows straight-line code from START: LATB3 low = command, high = data;
movlw X + movwf 0x90 (bank 2) + call 0xE07A sends X; movlw X + movwf 0xE7
(bank 1) + call 0x19F90 is a delay of X ms. Other calls/branches/SFR writes
are printed as they are, so the output is a guide, not a full emulation.
"""
import re
import sys

lines = open(sys.argv[1]).read().splitlines()
start = int(sys.argv[2], 16)
end = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
code = []
for l in lines:
    m = re.match(r'^([0-9a-f]{6}):  [0-9a-f]{4}  (\w+)\s*(.*)$', l)
    if m:
        code.append((int(m.group(1), 16), m.group(2), m.group(3)))
i = next(k for k, c in enumerate(code) if c[0] == start)
w = None
dc = '?'
out = []
while i < len(code):
    a, op, args = code[i]
    if end and a >= end:
        break
    if op == 'movlw':
        w = int(args, 16)
    elif op == 'movf' or op == 'movff':
        w = None
        out.append('  [%06x %s %s]' % (a, op, args))
    elif op == 'clrf' and args.startswith('0x90'):
        out.append('%s 0x00' % ('CMD ' if dc == 'C' else 'data'))
        w = None
    elif op in ('bcf', 'bsf') and args.startswith('0x8a, 0x3'):
        dc = 'C' if op == 'bcf' else 'D'
    elif op in ('call', 'rcall') and args.startswith('0x00e07a') and w is not None:
        out.append('%s 0x%02X' % ('CMD ' if dc == 'C' else 'data', w))
    elif op == 'call' and args.startswith('0x019f90'):
        out.append('delay %d ms' % w)
    elif op == 'return':
        out.append('return @%06x' % a)
        break
    elif op in ('call', 'rcall', 'goto', 'bra') or op.startswith('b') and op not in ('bcf', 'bsf'):
        out.append('  [%06x %s %s]' % (a, op, args))
    elif op in ('bcf', 'bsf', 'movwf', 'clrf', 'setf') and ';' in args and 'LAT' in args:
        out.append('  [%06x %s %s]' % (a, op, args))
    i += 1
print('\n'.join(out))
