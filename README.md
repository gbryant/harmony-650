# harmony-650

Custom firmware for the Logitech Harmony 650 universal remote, written from
scratch in C. With Logitech's Harmony service shut down, this turns the
remote into a USB display and 54-button input device for a computer. The
included demo is a system monitor (CPU, memory, disk, network) on the
remote's colour screen, with the remote's buttons switching pages.

**Status: proof of concept.** Tested on one Harmony 650 (firmware 0.3/0.4,
bootloader 0.2.0) with a Mac. Not affiliated with or endorsed by Logitech.

## What works
- Builds with free tools (SDCC + gputils) into an image the stock bootloader
  accepts; flashed with a patched [Concordance](https://github.com/jaymzh/concordance).
- USB: enumerates as a vendor-defined HID device (VID:PID `1209:0001`, the
  pid.codes test ID), no driver needed.
- All 54 buttons report press/release ([docs/KEYMAP.md](docs/KEYMAP.md)).
- The 128×128 colour LCD (Sitronix ST7637) and both backlights (screen and
  buttons). The computer draws: `tools/harmony.py` renders with Pillow and
  sends only changed regions, run-length encoded where it helps.
  A typical full screen takes ~0.3 s, a small update a few ms.

Not (yet) supported: infrared, sleep/power saving (the firmware runs flat
out, so keep the remote on USB), the motion sensor, standalone operation
without the computer.

## Safety and recovery
The bootloader (0x0000–0x8FFF) is never written: images are limited to the
app area, and the bootloader only copies a new image after it is fully
written and verified. If anything goes wrong:

1. **Enter Safe mode:** hold **OK** while inserting the battery, or while
   plugging in USB with the battery out. The bootloader stays in control and
   Concordance can talk to it (it reports firmware 0.2).
2. **Flash the official firmware** (you need Logitech's update file,
   `harmony_650_firmware_0_4.hfw`, which is not included here):

       tools/hfw2bin.py harmony_650_firmware_0_4.hfw region2.bin
       concordance --write-arch14-fw=region2.bin --commit

Back up your remote first (see below). Your config is not touched by
firmware updates, but keep a copy anyway. **Use at your own risk.**

## Requirements (macOS, Homebrew)

    brew install sdcc gputils hidapi pkgconfig autoconf automake libtool libzip

Tested with SDCC 4.6.0, gputils 1.5.2, hidapi 0.15.0, Python 3 with Pillow
and psutil:

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

## 1. Build Concordance with firmware support
Upstream Concordance can't write firmware to this remote. The patches in
[concordance-patches/](concordance-patches/) add `--dump-flash` (read-only
backup of any flash range) and `--write-arch14-fw` (follows Logitech's own
update sequence; dry run unless `--commit`).

    git clone https://github.com/jaymzh/concordance
    cd concordance
    git checkout 041324c5f2d13e486facad78ddb17ad951d7881a
    git am ../concordance-patches/*.patch
    P=$PWD/../build
    export CPPFLAGS="-I$P/include -I/opt/homebrew/include" LDFLAGS="-L$P/lib -L/opt/homebrew/lib"
    (cd libconcord && autoreconf --install && ./configure --prefix=$P && make && make install)
    (cd concordance && autoreconf --install && ./configure --prefix=$P && make && make install)

The binary is `build/bin/concordance`.

## 2. Back up the remote

    concordance --dump-config config.EZHex
    concordance --dump-flash=extflash.bin --flash-addr=0 --flash-len=0x200000
    concordance --dump-flash=internal.bin --flash-addr=0xFE0000 --flash-len=0x20000

## 3. Build and flash the firmware

    firmware/build.sh                                       # -> firmware/build/fw.bin
    concordance --write-arch14-fw=firmware/build/fw.bin     # dry run: checks only
    concordance --write-arch14-fw=firmware/build/fw.bin --commit

After the reset Concordance keeps waiting for the stock firmware to come
back ("Rebooting remote"); press Ctrl-C. The remote now shows a dark blue
screen and appears as "Harmony 650 Key Reporter". To flash again later,
enter Safe mode first.

## 4. Use it

    .venv/bin/python tools/sysmon.py        # system monitor
    .venv/bin/python tools/display_test.py  # alignment pattern + speed benchmark
    .venv/bin/python tools/keyreader.py     # print raw button events
    .venv/bin/python tools/packet_test.py   # check no display packets are lost

In the monitor: D-pad ◀ ▶ change pages, All Off toggles the screen
backlight, Red toggles the button backlight, Exit quits. It reconnects by
itself if the remote is unplugged.

From your own code:

```python
from harmony import Remote
from PIL import Image, ImageDraw
r = Remote()
img = Image.new('RGB', (128, 128))
ImageDraw.Draw(img).text((10, 10), 'hello', fill='white')
r.show(img)
for name, pressed in r.events():
    print(name, pressed)
```

## USB protocol
Input reports (8 bytes), remote → computer:
`pressed, column, row, code, sequence`. A report with byte 0 = `0x80` is
device info (LCD IDs, clock, backlight state, packets processed).

Output reports (64 bytes), computer → remote, byte 0 = command:

| Cmd | Name | Arguments |
|---|---|---|
| 1 | WINDOW | x0 y0 x1 y1 — set the drawing window |
| 2 | PIXELS | n, then n ≤ 62 bytes of RGB565 (high byte first) |
| 3 | FILL | x0 y0 x1 y1 hi lo |
| 4 | BACKLIGHT | bit 0 screen, bit 1 buttons |
| 5 | RUNS | n ≤ 20 × (count, hi, lo); count 0 = 256 |
| 6 | INFO | send an info report |

## How it works
[docs/NOTES.md](docs/NOTES.md) has the full write-up: flash layout, image
header and checksum, bootloader behaviour and Safe mode, Logitech's update
sequence, the config format, the keypad matrix, the LCD (pins, controller
detection, init sequence), the clock (16 MHz CPU), and how the drawing
speed was tuned. Hardware summary:

| Part | Detail |
|---|---|
| MCU | PIC18F67J50, 128 KB flash; bootloader 0x0000–0x8FFF, app from 0x9000 |
| External flash | 2 MiB SPI (EON EN25F16) |
| Keypad | 14 columns (PORTE0–6, PORTA3–5, PORTD0–3) × 4 rows (PORTB4–7) |
| LCD | ST7637, 128×128 RGB565, SPI on MSSP2 (RD4/RD6/RD7, D/C RB3, reset RF6) |
| Backlights | screen: RG4 high; buttons: RG0 low |

## License
GPLv3 (see [LICENSE](LICENSE)). The Concordance patches are GPLv3 like
Concordance itself.
