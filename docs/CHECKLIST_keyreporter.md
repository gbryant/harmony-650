# Custom firmware: button-code reporter

Goal: a C firmware that enumerates as a vendor-defined HID device
(usage page 0xFF00) and sends one report per button press/release with
the keypad column/row, plus a Mac script that prints those reports.

- [x] 1. Linker script + startup (header, vectors, stack)
- [x] 2. Build script: sdcc -> gpasm -> gplink -> hex2img -> fixhdr
- [x] 3. hex2img.py: Intel HEX -> app image at 0x9000 (range/size checks)
- [x] 4. Port init in C (copied from stock 0x1B3D0)
- [x] 5. Keypad scan in C (14 columns x PORTB4-7, debounce)
- [x] 6. USB descriptors (device, config, interface, HID, report, strings)
- [x] 7. USB EP0 control transfers (enumeration)
- [x] 8. USB EP1 IN reports (press/release events)
- [x] 9. Full build + Concordance dry run
- [x] 10. Mac reader script (hidapi via ctypes)
- [x] 11. Flash, press every button, record the map
- [x] 12. Write results into NOTES.md
