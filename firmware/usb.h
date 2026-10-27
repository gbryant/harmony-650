#ifndef USB_H
#define USB_H

void usb_init(void);
void usb_poll(void);                    /* call continuously from main */
unsigned char usb_configured(void);
unsigned char usb_report_ready(void);   /* EP1 IN buffer free */
void usb_send_report(const unsigned char __data *report);   /* REPORT_SIZE bytes */

/* EP1 OUT, double-buffered: once usb_out_available() returns 1 the packet
 * stays in usb_out_buffer() until usb_out_release(), while the next packet
 * is received into the other buffer. */
unsigned char usb_out_available(void);
const unsigned char __data *usb_out_buffer(void);
void usb_out_release(void);

#endif
