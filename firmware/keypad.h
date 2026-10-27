#ifndef KEYPAD_H
#define KEYPAD_H

#define KEY_COLUMNS 14

/* One debounced change: column 0-13, row 0-3 (PORTB4-7), pressed 1/0. */
struct key_event {
    unsigned char column;
    unsigned char row;
    unsigned char pressed;
};

void keypad_init(void);
void keypad_scan(void);                       /* call about once per ms */
unsigned char keypad_get(struct key_event __data *ev);   /* 1 if an event was taken */

#endif
