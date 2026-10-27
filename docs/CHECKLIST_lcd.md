# Custom firmware: drive the LCD

Goal: show our own text/graphics on the screen, then stream content from
the Mac over USB (system monitor).

- [x] 1. Find the LCD interface in stock fw 0.4 (pins, bus, peripheral)
- [x] 2. Find the controller init sequence and identify the controller (ST7637 path, ID3=0 ID1=0 -> variant 3)
- [x] 3. Backlights: G4 high = LCD backlight on; G0 low = button backlight on (stock PWMs G0). G2/G3 no visible effect
- [x] 4. Find how pixels are written (window/address commands, pixel format)
- [x] 5. lcd.c: init + fill (fw_lcdid: IDs 00/00, CPU 16 MHz; fw_lcdtest: variant-3 init + colour bars)
- [x] 6. Flash, check the screen changes (red/green/blue/white bars shown once G4 set)
- [x] 7. Text: rendered on the Mac with Pillow (tools/harmony.py), not on the PIC
- [x] 8. USB OUT reports: EP1 OUT 64-byte reports, WINDOW/PIXELS/FILL/BACKLIGHT (mods/fw_display.bin)
- [x] 9. Mac script: tools/sysmon.py (3 pages, running on the remote)
- [x] 10. Write results into NOTES.md
