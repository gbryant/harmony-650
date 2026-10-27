; Startup for custom Harmony 650 application firmware.
;
; Image layout expected by the bootloader (offsets from 0x9000):
;   0-1  checksum      (filled in by tools/fixhdr.py)
;   2-3  0xFFFF
;   4-6  payload size  (filled in by tools/fixhdr.py)
;   7    version byte
;   8-9  "HG" marker
;   A-D  goto entry    (the bootloader jumps to 0x900A)
; Interrupts are never enabled; the vectors just return.

        processor p18f67j50
        include "p18f67j50.inc"

        extern  _main
        extern  _stack_end
        global  _entry

HDR     CODE    0x9000
        db      0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x01, 'H', 'G'
        goto    _entry

HIVEC   CODE    0x9400
        retfie  FAST

LOVEC   CODE    0x9800
        retfie

ENTRY   CODE
_entry:
        clrf    INTCON              ; no interrupts
        lfsr    1, _stack_end       ; SDCC software stack (FSR1) and frame (FSR2)
        lfsr    2, _stack_end
        clrf    TBLPTRU
        call    _main
hang:
        bra     hang

        end
