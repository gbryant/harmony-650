#!/usr/bin/env python3
"""Print gpdasm listing lines in [start, end): lstrange.py file.lst 0x1400 0x1480"""
import re, sys
lst, start, end = sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16)
for line in open(lst):
    m = re.match(r'^([0-9a-f]{6}):  [0-9a-f]{4}(  .*)?$', line.rstrip('\n'))
    if m and start <= int(m.group(1), 16) < end and m.group(2):
        print(line, end='')
