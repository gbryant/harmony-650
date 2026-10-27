"""Talk to the Harmony 650 custom firmware: draw on its LCD, read buttons.

    from harmony import Remote
    r = Remote()
    r.show(pil_image)          # 128x128, only changed pixels are sent
    for name, pressed in r.events(): ...

Display commands go out as 64-byte HID output reports (see firmware/main.c).
"""
import ctypes
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from keyreader import load_hidapi, VID, PID, REPORT_SIZE  # noqa: E402

WIDTH = HEIGHT = 128
CMD_WINDOW, CMD_PIXELS, CMD_FILL, CMD_BACKLIGHT, CMD_RUNS = 1, 2, 3, 4, 5
RAW_PIXELS = 31           # 62 bytes of RGB565 per PIXELS packet
MAX_RUNS = 20             # (count, hi, lo) triples per RUNS packet
BAND_GAP = 4              # merge changed-row bands closer than this

# our key code -> button name (firmware/KEYMAP.md)
BUTTONS = {
    0x00: 'movie', 0x01: 'screen_right_top', 0x02: 'help', 0x03: 'activities',
    0x04: 'tv', 0x05: 'off', 0x06: 'music', 0x07: 'screen_left_top',
    0x08: 'screen_left_bottom', 0x09: 'menu', 0x0A: 'screen_below_left', 0x0B: 'exit',
    0x0C: 'red', 0x0D: 'vol_up', 0x0E: 'vol_down', 0x0F: 'mute',
    0x10: '4', 0x11: '7', 0x12: '+', 0x13: '0',
    0x14: 'skip_back', 0x15: 'rewind', 0x16: 'record', 0x17: '1',
    0x18: 'screen_below_middle', 0x19: 'up', 0x1A: 'down', 0x1B: 'yellow',
    0x1C: 'blue', 0x1D: 'fast_forward', 0x1E: 'ch_up', 0x1F: 'ch_down',
    0x20: 'guide', 0x21: 'screen_right_bottom', 0x22: 'screen_below_right', 0x23: 'info',
    0x24: '6', 0x25: 'skip_forward', 0x26: '3', 0x27: 'stop',
    0x28: 'dpad_right', 0x29: 'dpad_down', 0x2A: 'back', 0x2B: 'play',
    0x2C: '9', 0x2D: 'pause', 0x2E: '2', 0x2F: '5',
    0x30: 'green', 0x31: 'dpad_up', 0x32: 'ok', 0x33: 'dpad_left',
    0x34: '8', 0x35: 'E',
}


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def encode(colors):
    """Pack RGB565 pixels into PIXELS / RUNS packets. Each packet is whichever
    of the two covers more pixels from the current position."""
    packets = []
    i, n = 0, len(colors)
    while i < n:
        runs, j = [], i
        while j < n and len(runs) < MAX_RUNS:
            k = j + 1
            while k < n and colors[k] == colors[j] and k - j < 256:
                k += 1
            runs.append((k - j, colors[j]))
            j = k
        if j - i > RAW_PIXELS or j == n:
            body = bytearray([CMD_RUNS, len(runs)])
            for count, c in runs:
                body += bytes((count & 0xFF, c >> 8, c & 0xFF))
            packets.append(bytes(body))
            i = j
        else:
            chunk = colors[i:i + RAW_PIXELS]
            body = bytearray([CMD_PIXELS, len(chunk) * 2])
            for c in chunk:
                body += bytes((c >> 8, c & 0xFF))
            packets.append(bytes(body))
            i += len(chunk)
    return packets


class Remote:
    def __init__(self, wait=True):
        self.hid = load_hidapi()
        self.hid.hid_write.restype = ctypes.c_int
        self.hid.hid_write.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        self.hid.hid_set_nonblocking.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.hid.hid_read.restype = ctypes.c_int
        self.hid.hid_read.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        self.hid.hid_init()
        self.dev = None
        self._buf = ctypes.create_string_buffer(REPORT_SIZE)
        self._open(wait)

    def _open(self, wait):
        while not self.dev:
            self.dev = self.hid.hid_open(VID, PID, None)
            if not self.dev:
                if not wait:
                    raise IOError('remote %04x:%04x not found' % (VID, PID))
                time.sleep(0.5)
        self.hid.hid_set_nonblocking(self.dev, 1)
        self.frame = None           # last image sent, as RGB bytes; None = unknown

    def reconnect(self):
        """Wait for the remote to come back (e.g. after a replug). The screen
        content is unknown afterwards, so the next show() sends a full frame."""
        self.close()
        self._open(wait=True)

    def close(self):
        if self.dev:
            self.hid.hid_close(self.dev)
            self.dev = None

    def _send(self, payload):
        report = b'\x00' + bytes(payload) + b'\x00' * (64 - len(payload))
        if self.hid.hid_write(self.dev, report, 65) < 0:
            raise IOError('write to remote failed')

    def backlight(self, lcd=True, keys=False):
        self._send([CMD_BACKLIGHT, (1 if lcd else 0) | (2 if keys else 0)])

    def fill(self, x0, y0, x1, y1, color):
        c = rgb565(*color)
        self._send([CMD_FILL, x0, y0, x1, y1, c >> 8, c & 0xFF])
        self.frame = None

    def blit(self, image, x0, y0, x1, y1):
        """Send the rectangle (inclusive) of a 128x128 RGB image."""
        px = image.crop((x0, y0, x1 + 1, y1 + 1)).tobytes()
        colors = [((px[i] & 0xF8) << 8) | ((px[i + 1] & 0xFC) << 3) | (px[i + 2] >> 3)
                  for i in range(0, len(px), 3)]
        self._send([CMD_WINDOW, x0, y0, x1, y1])
        for packet in encode(colors):
            self._send(packet)

    def show(self, image):
        """Draw a 128x128 image, sending only the bands of rows that changed."""
        image = image.convert('RGB')
        new = image.tobytes()
        row = WIDTH * 3
        if self.frame is None:
            boxes = [(0, 0, WIDTH - 1, HEIGHT - 1)]
        else:
            changed = [y for y in range(HEIGHT)
                       if new[y * row:(y + 1) * row] != self.frame[y * row:(y + 1) * row]]
            bands = []
            for y in changed:
                if bands and y - bands[-1][1] <= BAND_GAP:
                    bands[-1][1] = y
                else:
                    bands.append([y, y])
            boxes = []
            for top, bottom in bands:
                cols = [x for x in range(WIDTH)
                        if any(new[y * row + x * 3:y * row + x * 3 + 3] !=
                               self.frame[y * row + x * 3:y * row + x * 3 + 3]
                               for y in range(top, bottom + 1))]
                boxes.append((cols[0], top, cols[-1], bottom))
        for box in boxes:
            self.blit(image, *box)
        self.frame = new

    def events(self):
        """Button events since the last call: list of (name, pressed)."""
        out = []
        while True:
            n = self.hid.hid_read(self.dev, self._buf, REPORT_SIZE)
            if n < 0:
                raise IOError('read from remote failed')
            if n == 0:
                return out
            pressed, col, row, code = self._buf.raw[:4]
            if pressed == 0x80:
                continue            # info report
            out.append((BUTTONS.get(code, 'code_%02x' % code), bool(pressed)))
