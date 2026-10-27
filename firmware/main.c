/* Harmony 650 custom firmware: report keypad button codes over USB. */
#pragma stack 0xE00 0x100

#include "hw.h"
#include "keypad.h"
#include "lcd.h"
#include "usb.h"
#include "usb_desc.h"

/* Same pin setup as the stock firmware (0x1B3D0). The bootloader has
 * already set up the oscillator and PLL, so the clock isn't touched. */
static void init_ports(void)
{
    ADCON0 = 0;
    ADCON1 = 0x86;
    WDTCON |= ADSHR;
    ANCON0 = 0xF8;
    ANCON1 = 0xFF;
    WDTCON &= ~ADSHR;

    LATA = 0;    TRISA = 0x07;
    LATB = 0xF6; TRISB = 0xF6;
    INTCON2 |= RBPU;
    LATC = 0x28; TRISC = 0x93;
    LATD = 0xD0; TRISD = 0;
    LATE = 0;    TRISE = 0x80;
    LATF = 0xE0; TRISF = 0x04;
    LATG = 0x09; TRISG = 0;

    LATD = 0;    TRISD = 0;
    LATD |= 0x01;
}

/* Report layout (REPORT_SIZE bytes):
 *   0  1 = pressed, 0 = released
 *   1  column 0-13
 *   2  row 0-3
 *   3  code = column * 4 + row
 *   4  sequence number, to spot dropped reports
 * Info report (sent once at start and whenever Help is pressed):
 *   0  0x80
 *   1  LCD ID3 (command 0xDC), 2  LCD ID1 (command 0xDA)
 *   3  Timer0 ticks per 1 ms USB frame, low byte; 5  high byte
 *   4  sequence number
 *   6  LATG (G4 = LCD backlight, G0 low = button backlight)
 *   7  display packets processed, low byte (to check for dropped packets)
 */
#define INFO_REPORT 0x80
#define HELP_CODE   0x02
#define SCAN_FRAMES 4       /* keypad scan interval, 1 ms USB frames */

#define BACKLIGHT_LCD   0x10    /* LATG4, high = on */
#define BACKLIGHT_KEYS  0x01    /* LATG0, low = on */

/* Output reports from the Mac (64 bytes), byte 0 = command:
 *   1 WINDOW x0 y0 x1 y1          set the drawing window, start writing
 *   2 PIXELS n data[n]            n <= 62 bytes of RGB565, high byte first
 *   3 FILL x0 y0 x1 y1 hi lo      fill a rectangle with one colour
 *   4 BACKLIGHT flags             bit 0 LCD on, bit 1 buttons on
 *   5 RUNS n (count hi lo)[n]     n <= 20 runs of one colour, count 0 = 256
 *   6 INFO                        send an info report */
static unsigned char info_pending;

static void display_command(const unsigned char __data *b)
{
    switch (b[0]) {
    case 1:
        lcd_window(b[1], b[2], b[3], b[4]);
        break;
    case 2:
        lcd_pixels(b + 2, b[1] > 62 ? 62 : b[1]);
        break;
    case 3:
        lcd_fill(b[1], b[2], b[3], b[4], ((unsigned int)b[5] << 8) | b[6]);
        break;
    case 5:
        lcd_runs(b + 2, b[1] > 20 ? 20 : b[1]);
        break;
    case 6:
        info_pending = 1;
        break;
    case 4:
        if (b[1] & 1)
            LATG |= BACKLIGHT_LCD;
        else
            LATG &= ~BACKLIGHT_LCD;
        if (b[1] & 2)
            LATG &= ~BACKLIGHT_KEYS;
        else
            LATG |= BACKLIGHT_KEYS;
        break;
    }
}

/* Timer0 ticks (Fosc/4) between two USB start-of-frame counts, 1 ms apart. */
static unsigned int ticks_per_ms(void)
{
    unsigned char f, lo, hi;
    T0CON = 0x88;
    f = UFRML;
    while (UFRML == f)
        usb_poll();
    TMR0H = 0;
    TMR0L = 0;
    f = UFRML;
    while (UFRML == f)
        ;
    lo = TMR0L;
    hi = TMR0H;
    return ((unsigned int)hi << 8) | lo;
}
void main(void)
{
    static unsigned char report[REPORT_SIZE];
    static struct key_event ev;
    unsigned char i, frame, seq, id1, id3, packets;
    unsigned int ticks;

    WDTCON &= ~0x01;            /* SWDTEN off, in case the bootloader set it */
    init_ports();
    keypad_init();

    lcd_reset();
    id3 = lcd_read_id(0xDC);    /* stock reads each ID twice, keeps the second */
    id3 = lcd_read_id(0xDC);
    id1 = lcd_read_id(0xDA);
    id1 = lcd_read_id(0xDA);
    lcd_init();
    /* ST7637 RAM is up to 132x132: clear all of it, then a dark blue
     * screen until the Mac draws something */
    lcd_fill(0, 0, 131, 131, RGB565(0, 0, 0));
    lcd_fill(0, 0, 127, 127, RGB565(0, 0, 64));
    LATG |= BACKLIGHT_LCD;

    usb_init();

    for (i = 0; i < REPORT_SIZE; i++)
        report[i] = 0;
    seq = 0;
    packets = 0;
    ticks = 0;
    info_pending = 1;
    while (!usb_configured())
        usb_poll();
    ticks = ticks_per_ms();
    frame = UFRML;

    for (;;) {
        usb_poll();
        if (!usb_configured())
            continue;

        if (usb_out_available()) {
            display_command(usb_out_buffer());
            usb_out_release();
            packets++;
        }

        if (((UFRML - frame) & 0xFF) >= SCAN_FRAMES) {   /* scan every 4 ms */
            frame = UFRML;
            keypad_scan();
        }

        if (info_pending && usb_report_ready()) {
            report[0] = INFO_REPORT;
            report[1] = id3;
            report[2] = id1;
            report[3] = ticks & 0xFF;
            report[4] = seq++;
            report[5] = ticks >> 8;
            report[6] = LATG;
            report[7] = packets;
            usb_send_report(report);
            report[5] = 0;
            report[6] = 0;
            report[7] = 0;
            info_pending = 0;
            continue;
        }

        if (usb_report_ready() && keypad_get(&ev)) {
            if (ev.pressed && ev.column == 0 && ev.row == HELP_CODE)
                info_pending = 1;

            report[0] = ev.pressed;
            report[1] = ev.column;
            report[2] = ev.row;
            report[3] = (ev.column << 2) | ev.row;
            report[4] = seq++;
            usb_send_report(report);
        }
    }
}
