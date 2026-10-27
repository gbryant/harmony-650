# Dumping your remote's bootloader and flash

Before flashing anything, make a full backup of your own remote. The
bootloader is the one part that keeps the remote recoverable, so it's worth
having a copy of it (and knowing its version) even though nothing here ever
writes it.

All reads below are read-only. They use the patched Concordance
(`--dump-flash`, see the README) and work with the remote running
**Logitech's firmware** (normal mode); that is how they were tested. Our
custom firmware does not speak Concordance's protocol, so if your remote
runs it, put the stock firmware back first (see "Safety and recovery" in
the README).

## What is where

| Concordance address | Contents | Size |
|---|---|---|
| `0x000000`–`0x1FFFFF` | external SPI flash (EN25F16): app image, Region 3, config | 2 MiB |
| `0xFE0000`–`0xFFFFFF` | the PIC18F67J50's **internal** flash, read through a window | 128 KiB |

Inside the internal flash:

| Internal address | Contents |
|---|---|
| `0x00000`–`0x08FFF` | **bootloader** (Safe mode, firmware install) |
| `0x09000`–`0x1EBFF` | installed app (a copy of the image the bootloader last installed) |
| `0x1EC00`–`0x1FFF7` | app tables and parameter block |
| `0x1FFF8`–`0x1FFFF` | configuration words (oscillator, watchdog, XINST, …) |

## 1. Dump the internal flash (twice)

    concordance --dump-flash=internal_a.bin --flash-addr=0xFE0000 --flash-len=0x20000
    concordance --dump-flash=internal_b.bin --flash-addr=0xFE0000 --flash-len=0x20000
    cmp internal_a.bin internal_b.bin && echo identical

Two reads that match rule out a bad USB transfer. Each file should be
exactly 131072 bytes.

## 2. Cut out the bootloader and check it

    head -c 36864 internal_a.bin > bootloader.bin      # 0x9000 bytes
    shasum -a 256 bootloader.bin
    tail -c 8 internal_a.bin | xxd                     # configuration words

Reference values from the remote this project was developed on
(bootloader 0.2.0, as reported in Safe mode: "Harmony Remote 4-0.2.0"):

| | |
|---|---|
| `bootloader.bin` SHA-256 | `27a5f27bd3a55d4dcb9999a8042c7e6f536dffe2efcb0cea6d0cc6c05d01132d` |
| configuration words | `8e f5 05 fb f8 f8 ff ff` |

A different hash isn't necessarily a problem: other production runs may
have other bootloader versions. If yours differs, please open an issue with
the hash, the Safe mode version string and your remote's firmware version,
so the notes can say which bootloaders are known to work. **Don't post the
dump itself**; it's Logitech's code.

## 3. Dump the external flash and the config

    concordance --dump-flash=extflash.bin --flash-addr=0 --flash-len=0x200000
    concordance --dump-config config.EZHex

`extflash.bin` (2 MiB) holds the installed app image at 0x0, Region 3 at
0x20000 and your config at 0x30000. Keep `config.EZHex`: it's your device
setup, and Concordance can write it back with `--write-config`.

## Restoring

- **App firmware:** restorable at any time from Safe mode with
  `--write-arch14-fw` (the official image comes from `tools/hfw2bin.py`).
- **Config:** `concordance --write-config config.EZHex`.
- **Bootloader:** *not* restorable with these tools, and it never needs to
  be: no command in this project writes internal flash. Writing through the
  `0xFE0000` window would overwrite the bootloader itself, which is why
  `--write-arch14-fw` only ever writes external flash at 0x0. The bootloader
  dump is a record (version, hash, a reference for analysis), not a restore
  image. Restoring a damaged bootloader would need a PIC programmer wired to
  the chip's programming pins (ICSP); this project hasn't looked at the
  board for those.
