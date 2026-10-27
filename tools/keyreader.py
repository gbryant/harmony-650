#!/usr/bin/env python3
"""Print button events from the custom Harmony 650 key reporter firmware.

    keyreader.py [--log FILE]

Each 8-byte HID input report is: pressed, column, row, code, sequence.
The stock firmware's key code for the same button is code + 1.
A report with byte 0 = 0x80 is device info (LCD IDs, clock).
Uses Homebrew's hidapi (brew install hidapi) through ctypes.
"""
import argparse
import ctypes
import ctypes.util
import sys
import time

VID, PID = 0x1209, 0x0001
REPORT_SIZE = 8


def load_hidapi():
    for name in ('/opt/homebrew/lib/libhidapi.dylib', ctypes.util.find_library('hidapi')):
        if name:
            try:
                lib = ctypes.CDLL(name)
                break
            except OSError:
                pass
    else:
        sys.exit('hidapi not found; brew install hidapi')
    lib.hid_init.restype = ctypes.c_int
    lib.hid_open.restype = ctypes.c_void_p
    lib.hid_open.argtypes = [ctypes.c_ushort, ctypes.c_ushort, ctypes.c_wchar_p]
    lib.hid_read_timeout.restype = ctypes.c_int
    lib.hid_read_timeout.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_int]
    lib.hid_close.argtypes = [ctypes.c_void_p]
    lib.hid_exit.restype = ctypes.c_int
    return lib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--log', help='also append events to this file')
    args = ap.parse_args()

    hid = load_hidapi()
    hid.hid_init()
    print('waiting for %04x:%04x ...' % (VID, PID))
    dev = None
    while not dev:
        dev = hid.hid_open(VID, PID, None)
        if not dev:
            time.sleep(0.5)
    print('connected; press buttons (Ctrl-C to stop)')

    log = open(args.log, 'a') if args.log else None
    buf = ctypes.create_string_buffer(REPORT_SIZE)
    last_seq = None
    try:
        while True:
            n = hid.hid_read_timeout(dev, buf, REPORT_SIZE, 500)
            if n < 0:
                sys.exit('device disconnected')
            if n == 0:
                continue
            pressed, col, row, code, seq = buf.raw[:5]
            if pressed == 0x80:
                ticks = code | buf.raw[5] << 8
                line = 'info    LCD ID3 0x%02X ID1 0x%02X, %d Timer0 ticks/ms (CPU ~%.1f MHz), LATG 0x%02X' % (
                    col, row, ticks, ticks * 4 / 1000.0, buf.raw[6])
                print(line)
                if log:
                    log.write(line + '\n')
                    log.flush()
                last_seq = seq
                continue
            gap = '' if last_seq is None or seq == (last_seq + 1) & 0xFF else '  (missed reports)'
            last_seq = seq
            line = '%s col %2d row %d code 0x%02X (stock 0x%02X)%s' % (
                'press  ' if pressed else 'release', col, row, code, code + 1, gap)
            print(line)
            if log:
                log.write(line + '\n')
                log.flush()
    except KeyboardInterrupt:
        pass
    finally:
        hid.hid_close(dev)
        hid.hid_exit()


if __name__ == '__main__':
    main()
