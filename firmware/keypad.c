/* Keypad matrix scan. Columns are driven low one at a time (idle high) and
 * the four rows are read on PORTB4-7, which read low when a key in the
 * driven column is down. Column order follows the stock firmware:
 *   0-6   PORTE0-6
 *   7-9   PORTA3-5
 *   10-13 PORTD0-3
 */
#include "hw.h"
#include "keypad.h"

#define COLS_E  0x7F
#define COLS_A  0x38
#define COLS_D  0x0F
#define DEBOUNCE_SCANS 4    /* scans are 4 ms apart: ~16 ms debounce */
#define QUEUE_LEN 16        /* power of two */

static unsigned char raw[KEY_COLUMNS];      /* last scan */
static unsigned char stable[KEY_COLUMNS];   /* debounced */
static unsigned char same[KEY_COLUMNS];     /* scans raw has been unchanged */

static struct key_event queue[QUEUE_LEN];
static unsigned char q_head, q_tail;

static void columns_idle(void)
{
    LATE |= COLS_E;
    LATA |= COLS_A;
    LATD |= COLS_D;
}

static void column_drive(unsigned char c)
{
    if (c < 7)
        LATE &= ~(1 << c);
    else if (c < 10)
        LATA &= ~(1 << (c - 7 + 3));
    else
        LATD &= ~(1 << (c - 10));
}

static void settle(void)
{
    volatile unsigned char i;
    for (i = 0; i < 4; i++)
        ;
}

static void push(unsigned char column, unsigned char row, unsigned char pressed)
{
    unsigned char next = (q_head + 1) & (QUEUE_LEN - 1);
    if (next == q_tail)
        return;                 /* full: drop the event */
    queue[q_head].column = column;
    queue[q_head].row = row;
    queue[q_head].pressed = pressed;
    q_head = next;
}

void keypad_init(void)
{
    unsigned char c;
    for (c = 0; c < KEY_COLUMNS; c++) {
        raw[c] = 0;
        stable[c] = 0;
        same[c] = 0;
    }
    q_head = 0;
    q_tail = 0;
    columns_idle();
}

void keypad_scan(void)
{
    unsigned char c, r, rows, changed;

    for (c = 0; c < KEY_COLUMNS; c++) {
        column_drive(c);
        settle();
        rows = (~PORTB >> 4) & 0x0F;
        columns_idle();

        if (rows != raw[c]) {
            raw[c] = rows;
            same[c] = 0;
            continue;
        }
        if (same[c] < DEBOUNCE_SCANS) {
            same[c]++;
            continue;
        }
        changed = rows ^ stable[c];
        if (!changed)
            continue;
        for (r = 0; r < 4; r++)
            if (changed & (1 << r))
                push(c, r, (rows >> r) & 1);
        stable[c] = rows;
    }
}

unsigned char keypad_get(struct key_event __data *ev)
{
    if (q_tail == q_head)
        return 0;
    ev->column = queue[q_tail].column;
    ev->row = queue[q_tail].row;
    ev->pressed = queue[q_tail].pressed;
    q_tail = (q_tail + 1) & (QUEUE_LEN - 1);
    return 1;
}
