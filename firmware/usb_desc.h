#ifndef USB_DESC_H
#define USB_DESC_H

#define EP0_SIZE    64
#define REPORT_SIZE 8
#define OUT_REPORT_SIZE 64

/* Finds descriptor (type, index) for GET_DESCRIPTOR. Returns its length,
 * or 0 if there is none, and sets *where. */
unsigned char usb_descriptor(unsigned char type, unsigned char index,
                             __code const unsigned char * __data *where);

#endif
