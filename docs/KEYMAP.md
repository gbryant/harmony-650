# Harmony 650 keypad map

Recorded with the key reporter firmware (tools/keyreader.py). Column is
the driven column (0-6 PORTE0-6, 7-9 PORTA3-5, 10-13 PORTD0-3), row is
PORTB4-7 as 0-3, code = column*4 + row.

The stock firmware (fw 0.4, scan at 0x18EF0-0x19076) numbers columns 1-14
and rows 1-4 and forms key code (col-1)*4 + row, so **stock code = our
code + 1**. The bootloader's safe-mode codes 0x06/0x33/0x2C are therefore
our 0x05 (All Off/power), 0x32 (OK) and 0x2B (Play), all confirmed by
pressing.

No button-name table exists offline: the config only names skin 72 and
the desktop app fetched layouts from Logitech's servers, so names come
from pressing buttons.

| Code | Stock | Col | Row | Button (symbol) |
|------|-------|-----|-----|-----------------|
| 0x00 | 0x01 | 0 | 0 | Watch a Movie (movie) |
| 0x01 | 0x02 | 0 | 1 | Screen: right side, top |
| 0x02 | 0x03 | 0 | 2 | Help (help) |
| 0x03 | 0x04 | 0 | 3 | More Activities (star) |
| 0x04 | 0x05 | 1 | 0 | Watch TV (TV) |
| 0x05 | 0x06 | 1 | 1 | All Off (power, safe-mode key) |
| 0x06 | 0x07 | 1 | 2 | Listen to Music (music) |
| 0x07 | 0x08 | 1 | 3 | Screen: left side, top |
| 0x08 | 0x09 | 2 | 0 | Screen: left side, bottom |
| 0x09 | 0x0A | 2 | 1 | Menu |
| 0x0A | 0x0B | 2 | 2 | Screen: below, left |
| 0x0B | 0x0C | 2 | 3 | Exit |
| 0x0C | 0x0D | 3 | 0 | Red |
| 0x0D | 0x0E | 3 | 1 | Volume up |
| 0x0E | 0x0F | 3 | 2 | Volume down |
| 0x0F | 0x10 | 3 | 3 | Mute |
| 0x10 | 0x11 | 4 | 0 | 4 |
| 0x11 | 0x12 | 4 | 1 | 7 |
| 0x12 | 0x13 | 4 | 2 | + |
| 0x13 | 0x14 | 4 | 3 | 0 |
| 0x14 | 0x15 | 5 | 0 | Skip back |
| 0x15 | 0x16 | 5 | 1 | Rewind |
| 0x16 | 0x17 | 5 | 2 | Record |
| 0x17 | 0x18 | 5 | 3 | 1 |
| 0x18 | 0x19 | 6 | 0 | Screen: below, middle |
| 0x19 | 0x1A | 6 | 1 | Up (separate from the D-pad) |
| 0x1A | 0x1B | 6 | 2 | Down (separate from the D-pad) |
| 0x1B | 0x1C | 6 | 3 | Yellow |
| 0x1C | 0x1D | 7 | 0 | Blue |
| 0x1D | 0x1E | 7 | 1 | Fast forward |
| 0x1E | 0x1F | 7 | 2 | Channel up |
| 0x1F | 0x20 | 7 | 3 | Channel down |
| 0x20 | 0x21 | 8 | 0 | Guide |
| 0x21 | 0x22 | 8 | 1 | Screen: right side, bottom |
| 0x22 | 0x23 | 8 | 2 | Screen: below, right |
| 0x23 | 0x24 | 8 | 3 | Info |
| 0x24 | 0x25 | 9 | 0 | 6 |
| 0x25 | 0x26 | 9 | 1 | Skip forward |
| 0x26 | 0x27 | 9 | 2 | 3 |
| 0x27 | 0x28 | 9 | 3 | Stop |
| 0x28 | 0x29 | 10 | 0 | D-pad right |
| 0x29 | 0x2A | 10 | 1 | D-pad down |
| 0x2A | 0x2B | 10 | 2 | Back |
| 0x2B | 0x2C | 10 | 3 | Play (safe-mode key) |
| 0x2C | 0x2D | 11 | 0 | 9 |
| 0x2D | 0x2E | 11 | 1 | Pause |
| 0x2E | 0x2F | 11 | 2 | 2 |
| 0x2F | 0x30 | 11 | 3 | 5 |
| 0x30 | 0x31 | 12 | 0 | Green |
| 0x31 | 0x32 | 12 | 1 | D-pad up |
| 0x32 | 0x33 | 12 | 2 | OK (safe-mode key) |
| 0x33 | 0x34 | 12 | 3 | D-pad left |
| 0x34 | 0x35 | 13 | 0 | 8 |
| 0x35 | 0x36 | 13 | 1 | E |
