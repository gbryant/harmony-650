/* LCD access, following the stock firmware (fw 0.4):
 *   RD4 SDA (SDO2; input while reading)   RD6 SCL (SCK2)   RD7 CS
 *   RB3 D/C (low = command)               RF6 RESET (low = reset)
 * Writes use MSSP2; ID reads bit-bang 3-wire SPI on the same pins with
 * MSSP2 off (stock 0xDD1A-0xDE4C). */
#include "hw.h"
#include "lcd.h"

#define SSPEN 0x20
#define BF 0x01             /* SSP2STAT: receive buffer full = byte done */

static unsigned char spi_dummy;

/* Timer0 free-running at Fosc/4 with no prescaler. The CPU runs at 16 MHz
 * (measured against USB frames), so 4000 ticks per ms; this waits 4096. */
void delay_ms(unsigned int ms)
{
    unsigned char lo, hi;
    T0CON = 0x88;               /* on, 16-bit, prescaler bypassed */
    while (ms--) {
        TMR0H = 0;
        TMR0L = 0;
        do {
            lo = TMR0L;         /* reading TMR0L latches TMR0H */
            hi = TMR0H;
        } while (hi < 16);
    }
}

void lcd_reset(void)
{
    LATD |= 0x80;               /* CS high */
    LATF &= ~0x40;
    delay_ms(10);
    LATF |= 0x40;
    delay_ms(120);
}

static void bit_delay(void)
{
    __asm
        nop
        nop
    __endasm;
}

unsigned char lcd_read_id(unsigned char command)
{
    unsigned char i, value = 0;

    SSP2CON1 &= ~SSPEN;         /* pins back to plain I/O */
    TRISD &= ~0x50;             /* RD4, RD6 outputs */
    LATD &= ~0x10;
    LATD &= ~0x80;              /* CS low */
    LATB &= ~0x08;              /* command */

    for (i = 0; i < 8; i++) {
        LATD &= ~0x40;          /* SCL low */
        if (command & 0x80)
            LATD |= 0x10;
        else
            LATD &= ~0x10;
        command <<= 1;
        bit_delay();
        LATD |= 0x40;           /* SCL high: LCD samples */
        bit_delay();
    }

    LATB |= 0x08;               /* data */
    TRISD |= 0x10;              /* RD4 input */
    for (i = 0; i < 8; i++) {
        LATD &= ~0x40;
        bit_delay();
        LATD |= 0x40;
        bit_delay();
        value <<= 1;
        if (PORTD & 0x10)
            value |= 1;
    }

    LATD |= 0x80;               /* CS high */
    TRISD &= ~0x10;
    LATD &= ~0x10;
    return value;
}

/* Init sequence for the ST7637 path with ID1 not 1 or 2 (stock 0xD400,
 * variant at 0xD7E0, shared tail at 0xD91E). Pairs of (kind, value). */
#define C 0     /* command */
#define D 1     /* data */
#define W 2     /* wait, ms */
#define END 3
static __code const unsigned char init_seq[] = {
    C,0x01, W,150,
    C,0xD7, D,0x9F,
    C,0xE0, D,0x00, W,20,
    C,0xE3, W,20,
    C,0xE1,
    C,0x28,
    C,0x11, W,50,
    C,0xC0, D,0xF3, D,0x00,
    C,0x25, D,0x48,
    C,0xC5, D,0x01,
    C,0xB5, D,0x89,
    C,0xBD, D,0x02,
    C,0xF0, D,0x06, D,0x0B, D,0x0D, D,0x15,
    C,0xF9, D,0x00, D,0x03, D,0x05, D,0x07, D,0x09, D,0x0B, D,0x0D, D,0x0F,
            D,0x11, D,0x13, D,0x15, D,0x17, D,0x19, D,0x1B, D,0x1D, D,0x1F,
    C,0xC3, D,0x00,
    C,0xC4, D,0x07,
    C,0x20,
    C,0xCB, D,0x01,
    C,0x36, D,0x48,
    C,0xD0, D,0x1D,
    C,0x3A, D,0x05,         /* 16-bit RGB565 */
    C,0xB0, D,0x7F,
    C,0x29,                 /* display on */
    END
};

/* MSSP2 as in stock 0x1B4A8: SPI master, clock idle high, Fosc/4. */
static void spi_on(void)
{
    SSP2CON1 &= ~SSPEN;
    TRISD &= ~0x70;             /* RD4 SDO2, RD5, RD6 SCK2 outputs */
    LATD |= 0x50;
    LATD &= ~0x20;
    SSP2STAT = 0;
    SSP2CON1 = 0x30;
    spi_dummy = SSP2BUF;        /* clear BF */
}

/* Every transfer reads SSP2BUF back, so BF is clear before the next one. */
static void spi_byte(unsigned char b)
{
    SSP2BUF = b;
    while (!(SSP2STAT & BF))
        ;
    spi_dummy = SSP2BUF;
}

static void lcd_command(unsigned char c)
{
    LATB &= ~0x08;
    spi_byte(c);
    LATB |= 0x08;
}

void lcd_init(void)
{
    unsigned char i, kind, value;

    spi_on();
    LATD &= ~0x80;              /* CS low for the whole sequence, as stock */
    for (i = 0; ; i += 2) {
        kind = init_seq[i];
        value = init_seq[i + 1];
        if (kind == END)
            break;
        if (kind == C)
            lcd_command(value);
        else if (kind == D)
            spi_byte(value);
        else
            delay_ms(value);
    }
    /* CS stays low from here on: the LCD is the only device on MSSP2, and a
     * memory write can then span several USB packets. */
}

void lcd_window(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1)
{
    lcd_command(0x2A); spi_byte(x0); spi_byte(x1);
    lcd_command(0x2B); spi_byte(y0); spi_byte(y1);
    lcd_command(0x2C);
}

/* The pixel loops write SSP2BUF directly instead of calling spi_byte():
 * at 16 MHz the call overhead was most of the per-byte time. */
void lcd_pixels(const unsigned char __data *data, unsigned char n)
{
    while (n--) {
        SSP2BUF = *data++;
        while (!(SSP2STAT & BF))
            ;
        spi_dummy = SSP2BUF;
    }
}

/* Runs of (count, high, low); count 0 means 256. */
void lcd_runs(const unsigned char __data *data, unsigned char runs)
{
    unsigned char count, hi, lo;

    while (runs--) {
        count = *data++;
        hi = *data++;
        lo = *data++;
        do {
            SSP2BUF = hi;
            while (!(SSP2STAT & BF))
                ;
            spi_dummy = SSP2BUF;
            SSP2BUF = lo;
            while (!(SSP2STAT & BF))
                ;
            spi_dummy = SSP2BUF;
        } while (--count);
    }
}

void lcd_fill(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1,
              unsigned int color)
{
    unsigned char x, y;
    unsigned char hi = color >> 8, lo = color & 0xFF;

    lcd_window(x0, y0, x1, y1);
    for (y = y0; ; y++) {
        for (x = x0; ; x++) {
            SSP2BUF = hi;
            while (!(SSP2STAT & BF))
                ;
            spi_dummy = SSP2BUF;
            SSP2BUF = lo;
            while (!(SSP2STAT & BF))
                ;
            spi_dummy = SSP2BUF;
            if (x == x1)
                break;
        }
        if (y == y1)
            break;
    }
}
