#!/bin/sh
# Build the custom Harmony 650 app image: build/fw.bin (header fixed,
# ready for concordance --write-arch14-fw).
set -e
cd "$(dirname "$0")"
TOOLS=../tools
LIBSDCC=/opt/homebrew/share/sdcc/lib/pic16/libsdcc.lib
mkdir -p build

OBJS=build/startup.o
gpasm -c -o build/startup.o startup.asm
for src in *.c; do
    obj=build/${src%.c}.o
    sdcc -mpic16 -p18f67j50 --no-crt --no-warn-non-free -c -o "$obj" "$src"
    OBJS="$OBJS $obj"
done

gplink -m -s harmony650.lkr -o build/fw.hex $OBJS "$LIBSDCC"
python3 $TOOLS/hex2img.py build/fw.hex build/fw_raw.bin
python3 $TOOLS/fixhdr.py build/fw_raw.bin build/fw.bin
