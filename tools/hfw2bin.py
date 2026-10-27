#!/usr/bin/env python3
"""Extract the app image from an official Harmony 650 firmware update.

    hfw2bin.py harmony_650_firmware_0_4.hfw region2.bin
    hfw2bin.py Region_2.EZUpgrade region2.bin

The .hfw file is a zip; its Region_2.EZUpgrade is XML whose <DATA> elements
hold the image as hex text. The result can be flashed with
`concordance --write-arch14-fw=region2.bin --commit` (e.g. to recover from
custom firmware). The header marker and checksum are checked.
"""
import io
import re
import sys
import zipfile


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    data = open(sys.argv[1], 'rb').read()
    if data[:2] == b'PK':
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next((n for n in z.namelist() if n.endswith('Region_2.EZUpgrade')), None)
            if not name:
                sys.exit('no Region_2.EZUpgrade in %s' % sys.argv[1])
            data = z.read(name)
    chunks = re.findall(rb'<DATA>\s*([0-9A-Fa-f\s]+?)\s*</DATA>', data)
    if not chunks:
        sys.exit('no <DATA> elements found')
    img = bytes.fromhex(b''.join(re.sub(rb'\s', b'', c) for c in chunks).decode())

    if img[8:10] != b'HG':
        sys.exit('no "HG" header marker; not an arch 14 app image')
    size = int.from_bytes(img[4:7], 'little') + 8
    a, b = 0x21, 0x43
    for i in range(4, size, 2):
        a ^= img[i]
        b ^= img[i + 1]
    if img[0:2] != bytes([a, b]):
        sys.exit('header checksum mismatch')
    open(sys.argv[2], 'wb').write(img)
    print('0x%X bytes, header checksum %02X%02X OK' % (len(img), a, b))


if __name__ == '__main__':
    main()
