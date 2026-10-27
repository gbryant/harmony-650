# Harmony 650 firmware notes

Remote: Harmony 650, arch 14 ("Molson"), skin 72 ("MOLSON_M2"), PIC18F67J50, 2 MiB external flash (EON EN25F16; Concordance wrongly says 4 MiB).
Installed firmware: 0.3. Update file `orig/harmony_650_firmware_0_4.hfw` is 0.4.

## Files
In this repository:
- `firmware/` – the custom firmware (C, SDCC + gputils); `firmware/build.sh` builds `firmware/build/fw.bin`
- `tools/hex2img.py`, `tools/fixhdr.py` – linker HEX → app image, rebuild an image's header (size, marker, checksum; reproduces both official headers)
- `tools/harmony.py`, `tools/sysmon.py`, `tools/display_test.py`, `tools/packet_test.py`, `tools/keyreader.py` – Mac side (hidapi via ctypes, Pillow, psutil)
- `tools/cfgtext.py` / `tools/cfgpatch.py` – edit config text / bytes and fix both config checksums; `tools/charmap_solve.py` recovers the config's character codes
- `tools/lcdseq.py`, `tools/sfrnames.py`, `tools/lstrange.py`, `tools/bin2hex.py` – helpers for reading `gpdasm` listings of the stock firmware
- `concordance-patches/` – Concordance changes (`--dump-flash`, `--write-arch14-fw`)
- `docs/KEYMAP.md` – all 54 buttons

Not included (Logitech's copyrighted files, or personal data), referred to below by their local names:
- `hfw/` – the unzipped official 0.4 update; `hfw/region2.bin` = the decoded 0.4 app image, used for recovery
- `backup/` – full dumps of the external flash, the PIC's internal flash (bootloader included), the installed 0.3 image and the config
- `winapp/` – Logitech Harmony Remote 7.7.0 (Windows) and decompiled sources; `disasm/` – `gpdasm -p p18f67j50` listings of the bootloader and both firmware images
- `mods/` – built images and modified configs

## External flash layout (Concordance read address space)
| Address | Contents |
|---|---|
| 0x00000–~0x12100 | Application firmware image (Region 2) |
| 0x20000–0x21BCA | Region 3 (`GSPM` cookie); identical in 0.3 and 0.4 |
| 0x30000– | User config |

## Firmware image header (offsets in the image)
| Off | 0.3 | 0.4 | Meaning |
|---|---|---|---|
| 0–1 | 1B0B | CA88 | Checksum, see below |
| 2–3 | FFFF | FFFF | Blank |
| 4–6 | 782001 | 782601 | Payload size, 24-bit LE = image size − 8 |
| 7 | 03 | 04 | Version |
| 8–9 | 4847 | 4847 | Fixed marker "HG" |
| A–D | goto | goto | Reset entry (`goto` main C startup) |

Checksum: a=0x21, b=0x43; for i from 4 to end of image (exact length, no padding) step 2: a^=img[i], b^=img[i+1]. Same as Logitech `getValidFirmware` (word XOR, seed 0x4321). Verified on 0.3 and 0.4.

## Internal (PIC) memory
- Step-by-step dump and check of your own bootloader: [BOOTLOADER_DUMP.md](BOOTLOADER_DUMP.md). Bootloader 0.2.0 (internal 0x0000–0x8FFF) SHA-256 `27a5f27bd3a55d4dcb9999a8042c7e6f536dffe2efcb0cea6d0cc6c05d01132d`.
- Readable through Concordance's flash read at 0xFE0000–0xFFFFFF (internal 0x00000–0x1FFFF); Logitech's flash map has 128 × 1 KiB blocks there.
- Bootloader at 0x0000–~0x7000. Its vectors: 0x0008 → `goto 0x9400`, 0x0018 → `goto 0x9800`.
- Internal 0x9000.. holds an exact copy of the external image (header included): the bootloader copies external → internal.
- Fixed entry points (same in 0.3 and 0.4): reset `goto` at 0x900A, high ISR 0x9400, low ISR 0x9800. Modified builds must keep them.
- Bootloader checks the "HG" marker of the installed app (reads 0xFE9008, ~0x10F0) and has a 0x21/0x43-seeded XOR checksum loop (~0x1420). Not fully traced.
- The app never reads its own header (no table reads at 0x9000).
- The app reads a table at internal 0x1EC00 and writes single words in a parameter block at internal 0x1F440–0x1F7C0 (same addresses in both versions). No flash writes target the bootloader region.
- 0x1F6C0 bit 0: read at boot, cleared (written 0xFFFE) by the app – possibly a "first boot after update" / boot-confirm flag. Unconfirmed.

## Logitech update sequence (arch 14, from the Windows app)
Data.xml order: Region 3, then Region 2, then reset. Region 2 (`UpdateHidService.writeApplicationFirmware`, case 14):
1. Unless in safe mode (fw type 4): `startConfiguration(9, 0)` = `A3 0A 09 00` (Concordance `WriteMiscByte(9, RESTART_CONFIG, 0)`)
2. RAM[0] = 0, read back (`A3 06 00 00`)
3. Invalidate flash (`A1 02`), erase 64K blocks, write image at external 0x0, read back and compare
4. RAM[0] = 2, read back
5. Reset
Region 3: invalidate embedded flash, write at the embedded config address.
Implemented as `concordance --write-arch14-fw=<image> [--commit] [--no-reset]` (dry run without `--commit`).

## Bootloader behaviour (traced in `disasm/boot.lst`)
Reset → 0x0EFC → init 0xD80 → boot sequence 0x1038, which in order:
1. **0x1A80 install update.** Reads the update flag (RAM 0x100 = Logitech's "RAM[0]", via 0x6890; 4→2, 7→6). Only if it is 2 or 6: read the size field from external 0x000004, add 8, cap at 0x15C00; erase internal 0x9000.. in 1 KiB blocks (0x66DC); copy external 0x0.. into internal 0x9000.. in 64-byte blocks (0x66F8/0x670E); clear the flag (0x689C). **The copy does not check the checksum.**
2. **0x1096 key check.** A value from 0x6114 equal to 0x06, 0x33 or 0x2C (probably held buttons, i.e. the Safe mode combination) → stay in the bootloader.
3. **0x17AA app check.** Stored checksum (internal 0x9000, via 0x4220) must equal the XOR-word checksum recomputed over the installed app (0x4290; size from the header, max 0x15C00). Pass → load PC with 0x00900A (0x10B8). Fail → stay in the bootloader (0x10C6, mode 5).
- 0x10E0–0x1400 is a status report (app checksum and version byte, plus an image at internal 0x1000), likely the Safe mode screen.
- The bootloader's USB flash commands reach internal flash through the 0xFE0000 window: **writes there would overwrite the bootloader.** Our tool only writes external 0x000000.

What this means for modified firmware:
- **Bad header/checksum:** the copy still happens, the app check fails, and the remote stays in the bootloader, which can be reflashed over USB with a good image (expected; untested).
- **Good checksum but broken code:** the app is started. Recovery then depends on the Safe mode key combination at boot: codes 0x06/0x33/0x2C are All Off, OK and Play (identified with the key reporter; only OK tested).
- Images must be ≤ 0x15C00 bytes (enforced in `--write-arch14-fw`).

## Wake sources / possible motion sensor (firmware 0.4)
- No accelerometer support in Logitech's app for arch 14 (the "accelerator" hardware-feature query, `B3 0C 00 00`, is only sent to arch 12 / Harmony One). No sign of an accelerometer bus in the firmware; the ADC is used in one module only.
- Low-priority ISR (0x9800): Timer0 → 0x12CBA; PORTB change (RB4–RB7) → 0x18EAE (likely keypad); **INT1 (RB1): flag cleared, no handler** – a pure wake-from-sleep line, enabled at init (0x1B3EC, rising edge); UART RX.
- Idle routine 0x1A782: arms modules (0x12EB0, 0x1300C, 0x136FE, 0x17038), `sleep`, then polls each module for the wake reason (0x12EBA, 0x1300E, 0x13700, 0x14A94, 0x1703C).
- **INT2 (RB2) module, 0x12EB0–0x12FA4: a hardware wake input gated by a user setting.** Before sleep it enables INT2 (0x12EB0). After wake, or polled from the main loop (0x12F28 via 0x16096), an INT2 edge triggers a settings lookup (0x12DC0): section 0x0F of the GSPM pointer table (pointer at 4·i+0x0C) must be type 9, and slot 7 must point at a byte equal to 1. If so, event 0x0D/1 is posted (0x10A3E); otherwise 0xF1A = 10 and 0x14A12 run. The setting is 1 in Region 3 (default, 0x021B9E) and in the config (0x08C482). **Hypothesis: the motion/tilt switch with an "enable motion wake" setting.** Test: `mods/config_claude_code_motion_off.EZHex` sets 0x08C482 = 0.
- The ADC routines (0x12E08 sample, 0x12E58 64-sample average) are a separate module, called from 0xCCDA, 0x130FC and 0x13792 – probably battery measurement.
- Config/Region 3 table reads go through 0x10B72 (TBLPTRU 3 = config at 0x030000, 2 = Region 3 at 0x020000, chosen by flag 0x8E bit 4) and 0x18B70/0x18B94 (read external flash).
- INT1 (wake-only, no handler) remains unidentified: keypad "any key" line, USB sense, or a second sensor.
- 0x11700–0x11830 is data, apparently small font bitmaps (false `sleep` hits in the listing).

## Open questions
- Which buttons are key codes 0x06, 0x33, 0x2C. (Safe mode entry itself is known, see below.)
- Exact behaviour of the 0x1F6C0 flag.

## Concordance changes (branch `dump-flash` in `concordance/`)
For sharing upstream. All tested only on one Harmony 650 (arch 14, skin 72).
- `--dump-flash[=file] [--flash-addr=N] [--flash-len=N]`: read-only raw flash read (`read_flash_range_from_remote`). Default 0x0–0x30000. Arch 14 accepts external 0x000000–0x1FFFFF and the internal-flash window 0xFE0000–0xFFFFFF; reads at 0x200000+ are refused by the remote.
- `--write-arch14-fw=<image> [--commit] [--no-reset]` (`write_arch14_firmware`): Logitech's region 2 sequence above. Dry run (header checks only) unless `--commit`.
- `CRemote::EraseSector`, `CRemote::RestartConfig`: small public helpers used by the above.
- Existing `--dump-firmware`/`--write-firmware` and arch 14's `TArchInfo` are unchanged, so `--write-firmware` still refuses arch 14.

### Upstream bugs found
- **`EraseFlash` never erases the first sector.** The sector tables list sector *ends* (no 0 entry) and the loop starts at `sectors[n-1]`, so an erase starting at `flash_base` begins at the first boundary, and an unaligned start skips its partial sector. No supported path hits it (config and firmware erases always start on a boundary above `flash_base`); `erase_safemode()` would, but the CLI never calls it. Arch 14's firmware area starts at 0, hence `EraseSector`.
- **Arch 14 flash size.** The `0x15:0x1C EON F16-100HIP` entry says 4096 KiB; the part is 16 Mbit (2 MiB). Logitech's `FlashMemoryFactory` (manufacturer 21 "MOLSON_2M") also uses 32 × 64 KiB. This makes "Config Flash Used" report out of 3904 KiB instead of ~1856 KiB.
- **`-R` short option** is documented but missing from the `getopt_long` option string; `--no-reset` works.
- `ReadFlash` can copy up to a packet past `len`; `_read_fw_from_remote` allocates exactly `size`.

## Test log
- **2026-10-26, test 1: official 0.4 over 0.3.** `concordance --write-arch14-fw=hfw/region2.bin --commit` → written, verified, reset. Afterwards the remote reports 0.4 (USB product "Harmony Remote 0-0.4.0"), fw type 0. External 0x0 and internal 0x9000 both equal the 0.4 image; bootloader, internal 0x1B680–0x1FFFF, Region 3 and config unchanged; config still valid. Log and post-update dumps in `logs/`.
- **2026-10-26, mod 1: "Remote Assistant" → "Claude Code" (config, not firmware).** `tools/cfgtext.py backup/config.EZHex mods/config_claude_code.EZHex "Remote Assistant" "Claude Code"`, then `concordance --no-web --write-config=mods/config_claude_code.EZHex`. Flash read-back equals the file; only the string and the config checksum changed. Restore with `--write-config=backup/config.EZHex`.

## Config format (0x30000–, from `--dump-config` / `.EZHex`)
- `.EZHex` = XML header, then the raw binary (`<BINARYDATASIZE>` bytes), identical to flash at 0x30000.
- Binary: `GSPM` cookie, 24-bit LE end address at offset 4 (flash address). At end−2: XOR-of-words checksum seeded 0x21,0x43 over [0, end−2); then `PTYY`.
- File `<CHECKSUM>` = 0x69 XOR every binary byte. Updating the internal checksum after an edit leaves this unchanged (the two changes cancel).
- On-screen text is 0x00-terminated, with no length prefix, in a custom character code. Known codes are in `tools/cfgtext.py` (`CHARMAP`); several low codes (03, 04, 0B, 0C, 10, 3D…) are formatting, not letters. "Remote Assistant" is at config 0x19658; "Assistant" alone at 0x196B9.
- The character table was recovered from this config's text (`tools/charmap_solve.py`, then checked by hand); it may be specific to this config's font.
- **2026-10-26, mod 1 confirmed:** "Claude Code" shows on the remote's screen in place of "Remote Assistant".
- **2026-10-26, mod 2: INT2 setting off.** `concordance --no-web --write-config=mods/config_claude_code_motion_off.EZHex` (0x08C482 = 0). Read-back: only 0x08C482 and the checksum byte at 0xF65C0 changed. Result: **picking the remote up still lit the screen**, so this setting does not control motion wake (RB2's role still unknown). Restored with `mods/config_claude_code.EZHex`. Undo: `--write-config=mods/config_claude_code.EZHex`.
- **2026-10-26, firmware mod 1: USB product name.** `mods/fw04_usbname.bin` = official 0.4 with the second USB string descriptor (image 0x12371, cpu 0x1B371) changed to "Claude Code Remote 0.4" (same length, 22 UTF-16 chars, bLength 0x30), header rebuilt by `tools/fixhdr.py` (checksum CA88 → CAF2). Flashed with `--write-arch14-fw --commit`. The remote enumerates as product "Claude Code Remote 0.4", reports fw 0.4 type 0, config intact; internal 0x9000 == image; bootloader unchanged. **First modified firmware accepted and running.**
  - USB string descriptors: image 0x1233F = manufacturer, 0x1236F = product (each `30 03` + 22 UTF-16 chars + NUL).
  - Changing both strings identically leaves the checksum unchanged (XOR of words, edits 0x30 apart), which is why only one was changed for this test.

## Safe mode (bootloader)
- **Entered by removing a battery, holding OK, and reinserting it** (tested). The bootloader's safe-mode key codes 0x06/0x33/0x2C are stock codes for All Off (power), OK and Play (see `firmware/KEYMAP.md`); only OK has been tested. Exit: remove/reinsert a battery without holding anything.
- **Also entered by holding OK while plugging in USB** (tested 2026-10-26, battery out). On USB power alone the remote stays on and the key reporter firmware runs with no battery, so re-seating the battery only restarts it when USB is unplugged.
- USB identity in safe mode: manufacturer/product "Harmony Remote 4-0.2.0"; Concordance reports firmware 0.2, **type 4**, same skin/arch/flash/serial; config still readable.
- The first `concordance -i` right after plugging in failed ("failed to requesting identity"); every retry succeeded. Retry once if it fails.
- `--write-arch14-fw` dry run passes in safe mode (type 4 is allowed; the restart-config step is skipped, as in Logitech's updater).
- **2026-10-26, recovery test: official 0.4 flashed from safe mode** (entered with OK). Written, verified, reset → normal mode, fw 0.4 type 0; internal 0x9000 == official 0.4; bootloader unchanged. Recovery path tested end to end.
  - Right after that reset the manufacturer string read as empty (Concordance and macOS); after a USB replug it read correctly again. Enumeration glitch, not firmware.

## Custom firmware: key reporter (`firmware/`)
- C firmware built with SDCC 4.6.0 + gputils (`firmware/build.sh` → `firmware/build/fw.bin`; copy in `mods/fw_keyreporter.bin`). Pieces:
  - `harmony650.lkr`: code only in 0x9000–0x1EBFF; header, 0x9400 and 0x9800 vectors reserved; RAM bank 0x100 (bootloader update flag) and USB RAM 0x400–0x7FF kept out of the allocator.
  - `startup.asm`: image header (filled in by `tools/fixhdr.py`), `goto` at 0x900A, return-only vectors, stack setup; `tools/hex2img.py` turns the linker's HEX into the image and refuses anything outside the app area.
  - `main.c` (stock port init from 0x1B3D0), `keypad.c` (matrix scan, 4-scan debounce), `usb.c` + `usb_desc.c` (polled USB, EP0 control + EP1 interrupt IN, BDT at 0x400 without ping-pong), `hw.h`/`regs.c` (registers by address, no device headers).
- Enumerates as vendor-defined HID (usage page 0xFF00), VID:PID 1209:0001 (pid.codes test), "harmony-hack" / "Harmony 650 Key Reporter" (renamed "Harmony 650 Status Monitor" for the first release). 8-byte input report: pressed, column, row, code (column·4+row), sequence number.
- `tools/keyreader.py [--log FILE]` (hidapi via ctypes) prints events; no macOS Input Monitoring permission needed.
- No screen, IR or sleep: the firmware only reports buttons, so it runs the battery down; recover with Safe mode (OK) + `hfw/region2.bin`.
- SDCC notes: no crt0 is linked (`--no-crt`), so globals are initialized in code; struct assignment needs `memcpy` and generic pointers need library helpers, so use field copies and `__data`/`__code` pointers.
- **2026-10-26, flashed and working.** `--write-arch14-fw=mods/fw_keyreporter.bin --commit` wrote and verified the image; Concordance then waited forever on "Rebooting" (it expects the stock firmware back), which is harmless. The remote enumerated on the first try and reported every button cleanly, with no repeats or dropped reports.
- **All 54 buttons mapped**, in `firmware/KEYMAP.md`. The stock firmware forms key code (col−1)·4 + row with 1-based column/row (fw 0.4, 0x18EF0–0x19076), so **stock code = our code + 1**. 54 of the 56 matrix slots are used; 0x36 and 0x37 (column 13, rows 2–3) have no button.
- No button-name table exists offline: the config names only skin 72 and the desktop app fetched layouts from Logitech's servers.

## LCD (traced in fw 0.4, confirmed with custom firmware)
- Controller: Sitronix ST7637 family (init at 0xD400: 01 reset, D7 9F, E0 00, E3, E1, 28, 11, then power/gamma, 36 48, 3A 05 = RGB565, B0 7F, 29). 4-wire SPI on MSSP2: RD4 SDA (SDO2), RD6 SCL (SCK2), RD7 CS (low), RB3 D/C (low = command), RF6 RESET (low 10 ms, then 120 ms). SSP2STAT = 0, SSP2CON1 = 0x30 (master, clock idle high, Fosc/4).
- Panel detection (0xDD1A): bit-banged 3-wire reads of 0xDC (ID3) and 0xDA (ID1), each twice. ID3 ≠ 0 selects a second controller family (init 0xD9C2, 16-bit window addresses with +1/+2 offsets); otherwise ID1 = 1 / 2 / other selects one of three ST7637 variants. **This remote reads ID3 = 0, ID1 = 0 → variant 3 (0xD7E0).**
- Window (ST7637 path): `2A x0 x1`, `2B y0 y1` (8-bit, no offset), `2C`, then RGB565 pixels high byte first. CS is held low by the caller for a whole batch; the byte routine (0xE054 → 0x1B4E0) doesn't touch it.
- **Backlights:** LATG4 high = LCD backlight on. LATG0 low = **button backlight** on (the stock firmware software-PWMs G0 around 0x1B128). G2/G3 showed no visible effect. Stock port init leaves G4 low and G0 high, so both are off until the firmware turns them on.
- **CPU clock is 16 MHz** (Timer0 at Fosc/4 counts ~3960 per 1 ms USB frame), i.e. config CPDIV = /3 of the 48 MHz PLL.
- **2026-10-26:** `mods/fw_lcdid.bin` (ID read + clock) and `mods/fw_lcdtest.bin` (variant-3 init, colour bars; colour buttons toggle G0/G2/G3/G4) flashed from safe mode. Red/green/blue/white bars shown once G4 was set.

## Display firmware + Mac system monitor
- `mods/fw_display.bin` (`firmware/`): key reporter + LCD. At boot: LCD reset, ID read, variant-3 init, dark blue screen, LCD backlight on. CS stays low after init (the LCD is the only device on MSSP2), so a memory write can span USB packets.
- USB: same vendor HID (1209:0001) plus **EP1 OUT**, 64-byte output reports (interval 1 ms). Byte 0 = command: `1` WINDOW x0 y0 x1 y1 (2A/2B/2C), `2` PIXELS n + n ≤ 62 bytes RGB565 high byte first, `3` FILL x0 y0 x1 y1 hi lo, `4` BACKLIGHT (bit 0 LCD, bit 1 buttons). Input reports unchanged (button events; 0x80 = info: LCD IDs, ticks/ms, LATG).
- **Visible area is 128×128 at (0,0)** with MADCTL 0x48: a border at 0..127 shows on all sides, nothing of RAM 128..131 is visible, text is upright and not mirrored.
- No open-source ST7637 driver exists; the ST7735 shares the drawing commands (2A/2B/2C/36/3A) and libraries like luma.lcd target it, but porting a graphics library to the PIC isn't worth it. Drawing is done on the Mac with Pillow instead; the remote is a framebuffer.
- Mac side (Pillow + psutil in `.venv/`): `tools/harmony.py` (Remote: `show()` sends only the changed bounding box, `fill()`, `backlight()`, `events()` with button names from KEYMAP.md), `tools/display_test.py`, `tools/sysmon.py` (7 pages: overview / CPU graph + per-core bars / network graph / colour bars / spectrum / last button pressed / about; D-pad ◀▶ pages, All Off = LCD backlight on/off, Red = button backlight on/off; no button quits, Ctrl-C stops it).
- Full-frame redraw measured 1.65 s (32 KB in ~530 packets); the monitor mostly sends small regions (the clock) each second.
- macOS: `psutil.disk_usage('/')` is the sealed system volume (2%); use `/System/Volumes/Data`.
- **2026-10-26:** flashed from safe mode; test pattern correct, `sysmon.py` running on the remote.

## Drawing speed and fixes (fw_display2–4)
- Measured cost per HID OUT packet on macOS: 1.47 ms with no work on the remote, 2.25 ms with 62 pixel bytes (fw_display). Python RGB565 conversion is 10 ms per frame, not a factor.
- **fw_display2:** pixel/fill loops write SSP2BUF directly and wait on SSP2STAT.BF (no call per byte); new command `5` RUNS: up to 20 × (count, hi, lo), count 0 = 256. The Mac encoder (`harmony.encode`) picks RUNS or PIXELS per packet, whichever covers more pixels; `show()` sends separate bands of changed rows. Monitor pages: 529 → 85–124 packets.
- **fw_display3:** the keypad scan (14 columns, 20-step settle) took ~0.7 ms of every 1 ms frame. Now every 4 frames with a 4-step settle (debounce still 4 scans, ~16 ms). EP1 OUT double-buffered (0x5C0 / 0x600): the BD is re-armed on the other buffer as soon as a packet arrives, no copy. Result: **1.00 ms per packet** (one per USB frame, the HID limit).
- Final timings: typical UI frame 0.31 s (was 1.65 s), random noise (worst case) 0.53 s, flat colour 0.13 s (SPI-limited, ~250 KB/s). Faster would need a bulk endpoint (libusb) instead of HID.
- **Bug (fixed in fw_display4): dropped packet after reopening.** macOS sends CLEAR_FEATURE(ENDPOINT_HALT), which resets the host's data toggle; the firmware didn't reset its own, so the next OUT packet was silently dropped as a repeat and the pixel stream shifted ("partial erase"). Now EP1 OUT/IN toggles reset on that request. Info report byte 7 counts processed OUT packets and OUT command `6` requests an info report; `tools/packet_test.py` checks no packets are lost across 5 opens (PASS).
- **Bug (Mac side): no reconnect.** `Remote.reconnect()` and `sysmon.py` now recover from unplugging/replugging; tested.
- Buttons still register reliably with the shorter keypad settle (checked with page switching).
