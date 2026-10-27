#!/usr/bin/env python3
"""Check that no display packets are dropped, across several device opens.

Each round opens the remote, reads the firmware's processed-packet counter
(info report byte 7), sends N no-op packets plus raw and run packets, reads
the counter again and compares.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from harmony import Remote  # noqa: E402

CMD_INFO = 6


def counter(r):
    r._send([CMD_INFO])
    deadline = time.time() + 2
    while time.time() < deadline:
        n = r.hid.hid_read(r.dev, r._buf, 8)
        if n > 0 and r._buf.raw[0] == 0x80:
            return r._buf.raw[7]
        time.sleep(0.005)
    raise IOError('no info report')


ok = True
for round_ in range(5):
    r = Remote()
    c0 = counter(r)
    sent = 0
    r._send([1, 0, 0, 127, 127])
    sent += 1
    for i in range(100):
        r._send([0])
        r._send(bytes([2, 62]) + bytes(62))
        r._send(bytes([5, 1, 1, 0, 0]))
        sent += 3
    c1 = counter(r)
    got = (c1 - c0 - 1) & 0xFF     # minus the INFO request itself
    print('round %d: sent %d, firmware processed %d%s' % (
        round_, sent, got if got else 256, '' if got == sent & 0xFF else '  <-- MISMATCH'))
    ok &= got == sent & 0xFF
    r.close()
print('PASS' if ok else 'FAIL')
