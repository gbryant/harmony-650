/* USB descriptors: one vendor-defined HID interface with interrupt IN
 * (button events) and interrupt OUT (display commands) endpoints. Every descriptor fits in a single 64-byte EP0 packet. */
#include "usb_desc.h"

/* pid.codes test VID/PID, so nothing mistakes this for the stock firmware */
#define VID 0x1209
#define PID 0x0001

static __code const unsigned char device_desc[] = {
    18, 0x01,               /* bLength, DEVICE */
    0x00, 0x02,             /* USB 2.0 */
    0x00, 0x00, 0x00,       /* class in interface */
    EP0_SIZE,
    VID & 0xFF, VID >> 8,
    PID & 0xFF, PID >> 8,
    0x00, 0x01,             /* bcdDevice 1.00 */
    1, 2, 0,                /* manufacturer, product, no serial */
    1,                      /* one configuration */
};

static __code const unsigned char report_desc[] = {
    0x06, 0x00, 0xFF,       /* Usage Page (Vendor 0xFF00) */
    0x09, 0x01,             /* Usage (1) */
    0xA1, 0x01,             /* Collection (Application) */
    0x15, 0x00,             /*   Logical Minimum (0) */
    0x26, 0xFF, 0x00,       /*   Logical Maximum (255) */
    0x75, 0x08,             /*   Report Size (8) */
    0x95, REPORT_SIZE,      /*   Report Count */
    0x09, 0x01,             /*   Usage (1) */
    0x81, 0x02,             /*   Input (Data, Var, Abs) */
    0x95, OUT_REPORT_SIZE,  /*   Report Count */
    0x09, 0x02,             /*   Usage (2) */
    0x91, 0x02,             /*   Output (Data, Var, Abs) */
    0xC0,                   /* End Collection */
};

static __code const unsigned char config_desc[] = {
    9, 0x02, 41, 0,         /* CONFIGURATION, total length 41 */
    1, 1, 0,                /* 1 interface, value 1, no string */
    0x80, 50,               /* bus powered, 100 mA */

    9, 0x04, 0, 0, 2,       /* INTERFACE 0, 2 endpoints */
    0x03, 0x00, 0x00, 0,    /* HID, no subclass/protocol */

    9, 0x21, 0x11, 0x01,    /* HID 1.11 */
    0, 1, 0x22,             /* no country, 1 descriptor: report */
    sizeof(report_desc), 0,

    7, 0x05, 0x81, 0x03,    /* ENDPOINT 1 IN, interrupt */
    REPORT_SIZE, 0, 10,     /* 8 bytes, 10 ms */

    7, 0x05, 0x01, 0x03,    /* ENDPOINT 1 OUT, interrupt */
    OUT_REPORT_SIZE, 0, 1,  /* 64 bytes, 1 ms */
};

static __code const unsigned char string0[] = { 4, 0x03, 0x09, 0x04 };

static __code const unsigned char string1[] = {
    2 + 2 * 12, 0x03,
    'h',0, 'a',0, 'r',0, 'm',0, 'o',0, 'n',0, 'y',0, '-',0, 'h',0, 'a',0, 'c',0, 'k',0,
};

static __code const unsigned char string2[] = {
    2 + 2 * 26, 0x03,
    'H',0, 'a',0, 'r',0, 'm',0, 'o',0, 'n',0, 'y',0, ' ',0, '6',0, '5',0, '0',0, ' ',0,
    'S',0, 't',0, 'a',0, 't',0, 'u',0, 's',0, ' ',0, 'M',0, 'o',0, 'n',0, 'i',0, 't',0,
    'o',0, 'r',0,
};

unsigned char usb_descriptor(unsigned char type, unsigned char index,
                             __code const unsigned char * __data *where)
{
    switch (type) {
    case 0x01:
        *where = device_desc;
        return sizeof(device_desc);
    case 0x02:
        *where = config_desc;
        return sizeof(config_desc);
    case 0x03:
        if (index == 0) { *where = string0; return sizeof(string0); }
        if (index == 1) { *where = string1; return sizeof(string1); }
        if (index == 2) { *where = string2; return sizeof(string2); }
        return 0;
    case 0x21:
        *where = config_desc + 18;
        return 9;
    case 0x22:
        *where = report_desc;
        return sizeof(report_desc);
    }
    return 0;
}
