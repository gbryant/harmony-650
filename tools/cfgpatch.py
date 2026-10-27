#!/usr/bin/env python3
"""Patch bytes in a Harmony 650 config (.EZHex) and fix both checksums.

    cfgpatch.py in.EZHex out.EZHex FLASH_ADDR=HEXBYTES [...]

FLASH_ADDR is the external flash address (config starts at 0x030000),
e.g. 0x08C482=00. The old byte values are printed so a patch can be undone.
"""
import sys

sys.path.insert(0, __import__('os').path.dirname(__file__))
from cfgtext import CONFIG_BASE, xor_words  # noqa: E402
import re  # noqa: E402


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    f = open(sys.argv[1], 'rb').read()
    size = int(re.search(rb'<BINARYDATASIZE>(\d+)</BINARYDATASIZE>', f).group(1))
    xml, cfg = f[:-size], bytearray(f[-size:])
    end = int.from_bytes(cfg[4:7], 'little') - CONFIG_BASE
    if cfg[:4] != b'GSPM' or cfg[end:end + 4] != b'PTYY' \
            or xor_words(cfg[:end - 2]) != cfg[end - 2:end]:
        sys.exit('Input config checksum/terminator not as expected; refusing')

    for arg in sys.argv[3:]:
        addr, data = arg.split('=')
        off = int(addr, 0) - CONFIG_BASE
        new = bytes.fromhex(data)
        if off < 8 or off + len(new) > end - 2:
            sys.exit('%s is outside the config body' % addr)
        print('0x%06X: %s -> %s' % (off + CONFIG_BASE, cfg[off:off + len(new)].hex(), new.hex()))
        cfg[off:off + len(new)] = new

    cfg[end - 2:end] = xor_words(cfg[:end - 2])
    file_sum = 0x69
    for c in cfg:
        file_sum ^= c
    xml = re.sub(rb'<CHECKSUM>\d+</CHECKSUM>', b'<CHECKSUM>%d</CHECKSUM>' % file_sum, xml, count=1)
    open(sys.argv[2], 'wb').write(xml + bytes(cfg))
    print('config checksum %s, file checksum %d' % (cfg[end - 2:end].hex().upper(), file_sum))


if __name__ == '__main__':
    main()
