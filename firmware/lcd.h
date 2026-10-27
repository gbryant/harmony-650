#ifndef LCD_H
#define LCD_H

void delay_ms(unsigned int ms);
void lcd_reset(void);
unsigned char lcd_read_id(unsigned char command);
void lcd_init(void);
void lcd_window(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1);
void lcd_pixels(const unsigned char __data *data, unsigned char n);
void lcd_runs(const unsigned char __data *data, unsigned char runs);
void lcd_fill(unsigned char x0, unsigned char y0, unsigned char x1, unsigned char y1,
              unsigned int color);

#define RGB565(r, g, b) ((((r) & 0xF8u) << 8) | (((g) & 0xFCu) << 3) | ((unsigned)(b) >> 3))

#endif
