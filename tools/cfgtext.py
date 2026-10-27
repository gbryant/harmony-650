#!/usr/bin/env python3
"""Replace on-screen text in a Harmony 650 config (.EZHex) and fix both
checksums, producing a file Concordance can --write-config.

    cfgtext.py in.EZHex out.EZHex "Remote Assistant" "New Text"

Text uses the config's own character codes (CHARMAP below, recovered from
the strings in this remote's config). The new text must be no longer than
the old; shorter text is ended with 0x00 and padded with 0x00. Every match
is replaced; use --index N to replace only the Nth (0-based).

Checksums:
  - inside the config: XOR of 16-bit words seeded 0x21,0x43 over
    [0, end-2), stored at end-2 (end = 24-bit LE at offset 4, minus
    the config base 0x30000), followed by "PTYY"
  - file: <CHECKSUM> = 0x69 XOR every byte of the binary part
"""
import argparse
import re
import sys

CONFIG_BASE = 0x030000

# code -> character, verified against words in the config text
CHARMAP = {
    0x01: 'H', 0x02: 'y', 0x05: ' ', 0x07: 's', 0x08: 'e', 0x09: 'c',
    0x15: 'a', 0x16: 'U', 0x17: 't', 0x18: 'h', 0x19: 'r', 0x1A: 'm',
    0x1B: 'o', 0x1C: 'n', 0x1D: 'u', 0x1E: 'p', 0x1F: 'f', 0x20: 'w',
    0x21: 'd', 0x22: 'A', 0x23: 'i', 0x24: 'v', 0x25: 'b', 0x28: 'S',
    0x29: 'B', 0x2A: 'C', 0x2B: 'L', 0x2C: 'I', 0x2D: 'l', 0x2E: 'g',
    0x2F: 'R', 0x31: 'G', 0x34: 'k', 0x36: 'P', 0x38: 'M',
}
ENCODE = {ch: code for code, ch in CHARMAP.items()}


def encode(text):
    missing = sorted(set(c for c in text if c not in ENCODE))
    if missing:
        sys.exit('No known code for: %s\nAvailable: %s' % (
            ' '.join(repr(c) for c in missing), ''.join(sorted(ENCODE))))
    return bytes(ENCODE[c] for c in text)


def xor_words(data, a=0x21, b=0x43):
    for i in range(0, len(data) - 1, 2):
        a ^= data[i]
        b ^= data[i + 1]
    return bytes([a, b])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('infile')
    ap.add_argument('outfile')
    ap.add_argument('old')
    ap.add_argument('new')
    ap.add_argument('--index', type=int)
    args = ap.parse_args()

    f = open(args.infile, 'rb').read()
    size = int(re.search(rb'<BINARYDATASIZE>(\d+)</BINARYDATASIZE>', f).group(1))
    xml, cfg = f[:-size], bytearray(f[-size:])
    if cfg[:4] != b'GSPM':
        sys.exit('Config binary does not start with GSPM')

    end = int.from_bytes(cfg[4:7], 'little') - CONFIG_BASE
    if cfg[end:end + 4] != b'PTYY' or xor_words(cfg[:end - 2]) != cfg[end - 2:end]:
        sys.exit('Input config checksum/terminator not as expected; refusing')

    old, new = encode(args.old), encode(args.new)
    if len(new) > len(old):
        sys.exit('New text is %d characters; must be at most %d' % (len(new), len(old)))
    new = new + b'\x00' * (len(old) - len(new))

    # Match whole strings: preceded by any byte, followed by the 0x00 terminator
    hits = [m.start() for m in re.finditer(re.escape(old) + b'(?=\x00)', bytes(cfg[:end]))]
    if not hits:
        sys.exit('Text not found')
    if args.index is not None:
        hits = [hits[args.index]]
    for at in hits:
        cfg[at:at + len(old)] = new
        print('replaced at config offset 0x%X (flash 0x%X)' % (at, CONFIG_BASE + at))

    cfg[end - 2:end] = xor_words(cfg[:end - 2])
    file_sum = 0x69
    for c in cfg:
        file_sum ^= c
    xml = re.sub(rb'<CHECKSUM>\d+</CHECKSUM>', b'<CHECKSUM>%d</CHECKSUM>' % file_sum, xml, count=1)

    open(args.outfile, 'wb').write(xml + bytes(cfg))
    print('config checksum %s, file checksum %d' % (cfg[end - 2:end].hex().upper(), file_sum))


if __name__ == '__main__':
    main()
