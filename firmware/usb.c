/* Minimal polled USB device: EP0 control + EP1 interrupt IN.
 * Buffer descriptors at 0x400 (no ping-pong), as in the stock firmware. */
#include "hw.h"
#include "usb.h"
#include "usb_desc.h"

/* UCON */
#define PKTDIS  0x10
#define USBEN   0x08
/* UIR */
#define STALLIF 0x20
#define IDLEIF  0x10
#define TRNIF   0x08
#define ACTVIF  0x04
#define URSTIF  0x01
/* UCFG: on-chip pull-up, full speed, on-chip transceiver */
#define UCFG_VALUE 0x14
/* UEPn */
#define EP_CTRL 0x16    /* handshake, OUT, IN */
#define EP_INOUT 0x1E   /* handshake, no SETUP, IN and OUT */
/* BD STAT */
#define UOWN    0x80
#define DTS     0x40
#define DTSEN   0x08
#define BSTALL  0x04
#define PID_SETUP 0x0D

/* BDT entries: STAT, CNT, ADRL, ADRH */
#define BD_EP0_OUT 0
#define BD_EP0_IN  4
#define BD_EP1_OUT 8
#define BD_EP1_IN  12
volatile __at(0x400) unsigned char bdt[16];
volatile __at(0x500) unsigned char ep0_out[EP0_SIZE];
volatile __at(0x540) unsigned char ep0_in[EP0_SIZE];
volatile __at(0x580) unsigned char ep1_in[REPORT_SIZE];
/* two EP1 OUT buffers used in turn: one receives while the other is drawn */
volatile __at(0x5C0) unsigned char ep1_out_a[OUT_REPORT_SIZE];
volatile __at(0x600) unsigned char ep1_out_b[OUT_REPORT_SIZE];

static unsigned char setup[8];
static unsigned char pending_address;
static unsigned char configuration;
static unsigned char ep1_toggle;
static unsigned char ep1_out_toggle;
static unsigned char ep1_out_which;     /* buffer the BD points at: 0 = a, 1 = b */
static unsigned char ep1_out_full;      /* a received packet is waiting */

static void arm_ep0_out(void)
{
    bdt[BD_EP0_OUT + 1] = EP0_SIZE;
    bdt[BD_EP0_OUT + 2] = 0x00;
    bdt[BD_EP0_OUT + 3] = 0x05;
    bdt[BD_EP0_OUT] = UOWN;     /* accept either data toggle */
}

/* Data or status stage of a control transfer, always DATA1. */
static void ep0_send(unsigned char len)
{
    bdt[BD_EP0_IN + 1] = len;
    bdt[BD_EP0_IN + 2] = 0x40;
    bdt[BD_EP0_IN + 3] = 0x05;
    bdt[BD_EP0_IN] = UOWN | DTS | DTSEN;
}

static void ep0_send_code(__code const unsigned char *src, unsigned char len)
{
    unsigned char i;
    if (len > setup[6] && setup[7] == 0)
        len = setup[6];         /* wLength */
    for (i = 0; i < len; i++)
        ep0_in[i] = src[i];
    ep0_send(len);
}

static void ep0_send_zeros(unsigned char len)
{
    unsigned char i;
    for (i = 0; i < len; i++)
        ep0_in[i] = 0;
    ep0_send(len);
}

static void arm_ep1_out(void)
{
    bdt[BD_EP1_OUT + 1] = OUT_REPORT_SIZE;
    bdt[BD_EP1_OUT + 2] = ep1_out_which ? 0x00 : 0xC0;
    bdt[BD_EP1_OUT + 3] = ep1_out_which ? 0x06 : 0x05;
    bdt[BD_EP1_OUT] = UOWN | DTSEN | (ep1_out_toggle ? DTS : 0);
}

static void ep0_stall(void)
{
    bdt[BD_EP0_IN] = UOWN | BSTALL;
}

static void reset_endpoints(void)
{
    UEP1 = 0;
    UADDR = 0;
    pending_address = 0;
    configuration = 0;
    bdt[BD_EP0_IN] = 0;
    bdt[BD_EP1_IN] = 0;
    bdt[BD_EP1_OUT] = 0;
    arm_ep0_out();
    UEP0 = EP_CTRL;
}

static void handle_setup(void)
{
    __code const unsigned char * __data desc;
    unsigned char i, len;

    for (i = 0; i < 8; i++)
        setup[i] = ep0_out[i];
    bdt[BD_EP0_IN] = 0;         /* take back IN in case it was stalled */
    arm_ep0_out();

    switch (setup[0]) {
    case 0x80:                  /* standard, device-to-host, device */
    case 0x81:                  /* standard, device-to-host, interface */
    case 0x82:                  /* standard, device-to-host, endpoint */
        if (setup[1] == 0x06) {                 /* GET_DESCRIPTOR */
            len = usb_descriptor(setup[3], setup[2], &desc);
            if (len)
                ep0_send_code(desc, len);
            else
                ep0_stall();
        } else if (setup[1] == 0x00) {          /* GET_STATUS */
            ep0_send_zeros(2);
        } else if (setup[1] == 0x08) {          /* GET_CONFIGURATION */
            ep0_in[0] = configuration;
            ep0_send(1);
        } else if (setup[1] == 0x0A) {          /* GET_INTERFACE */
            ep0_send_zeros(1);
        } else {
            ep0_stall();
        }
        break;

    case 0x00:                  /* standard, host-to-device, device */
        if (setup[1] == 0x05) {                 /* SET_ADDRESS */
            pending_address = setup[2];
            ep0_send(0);
        } else if (setup[1] == 0x09) {          /* SET_CONFIGURATION */
            configuration = setup[2];
            bdt[BD_EP1_IN] = 0;
            ep1_toggle = 0;
            ep1_out_toggle = 0;
            ep1_out_which = 0;
            ep1_out_full = 0;
            UEP1 = configuration ? EP_INOUT : 0;
            if (configuration)
                arm_ep1_out();
            ep0_send(0);
        } else if (setup[1] == 0x01 || setup[1] == 0x03) {  /* features */
            ep0_send(0);
        } else {
            ep0_stall();
        }
        break;

    case 0x02:                  /* standard, host-to-device, endpoint */
        /* CLEAR_FEATURE(ENDPOINT_HALT) resets the endpoint's data toggle on
         * the host (macOS does this when a program opens the device), so
         * ours must follow, or the next OUT packet is dropped as a repeat. */
        if (setup[1] == 0x01 && setup[2] == 0) {
            if (setup[4] == 0x01) {
                if (bdt[BD_EP1_OUT] & UOWN) {
                    ep1_out_toggle = 0;
                    arm_ep1_out();
                } else {
                    ep1_out_toggle = 1;     /* usb_out_available() flips it */
                }
            } else if (setup[4] == 0x81) {
                ep1_toggle = 0;
            }
        }
        ep0_send(0);
        break;

    case 0x01:                  /* standard, host-to-device, interface */
        ep0_send(0);            /* SET_INTERFACE 0, CLEAR/SET_FEATURE */
        break;

    case 0x21:                  /* class, host-to-device, interface */
        if (setup[1] == 0x0A || setup[1] == 0x0B)   /* SET_IDLE, SET_PROTOCOL */
            ep0_send(0);
        else
            ep0_stall();
        break;

    case 0xA1:                  /* class, device-to-host, interface */
        if (setup[1] == 0x01)                   /* GET_REPORT */
            ep0_send_zeros(REPORT_SIZE);
        else if (setup[1] == 0x02 || setup[1] == 0x03)  /* GET_IDLE, GET_PROTOCOL */
            ep0_send_zeros(1);
        else
            ep0_stall();
        break;

    default:
        ep0_stall();
    }

    UCON &= ~PKTDIS;            /* SIE halts packet processing after SETUP */
}

static void handle_transaction(unsigned char ustat)
{
    unsigned char endpoint = (ustat >> 3) & 0x0F;
    unsigned char in = ustat & 0x04;

    if (endpoint != 0)
        return;                 /* EP1: main loop checks UOWN on the BDs */

    if (!in) {
        if (((bdt[BD_EP0_OUT] >> 2) & 0x0F) == PID_SETUP)
            handle_setup();
        else
            arm_ep0_out();      /* status stage of a control read */
    } else if (pending_address) {
        UADDR = pending_address;    /* takes effect after the status stage */
        pending_address = 0;
    }
}

void usb_init(void)
{
    volatile unsigned int wait;

    UCON = 0;                   /* detach so the host sees a fresh device */
    UIE = 0;
    UEIE = 0;
    for (wait = 0; wait < 0xFFFF; wait++)
        ;

    UCFG = UCFG_VALUE;
    UEIR = 0;
    UIR = 0;
    reset_endpoints();
    UCON = USBEN;
}

void usb_poll(void)
{
    unsigned char i;

    if (UIR & URSTIF) {
        for (i = 0; i < 4; i++)
            UIR &= ~TRNIF;      /* flush the USTAT FIFO */
        reset_endpoints();
        UIR &= ~URSTIF;
    }
    if (UIR & STALLIF) {
        UEP0 &= ~0x01;          /* EPSTALL */
        UIR &= ~STALLIF;
    }
    if (UIR & (IDLEIF | ACTVIF))
        UIR &= ~(IDLEIF | ACTVIF);
    if (UEIR)
        UEIR = 0;

    while (UIR & TRNIF) {
        i = USTAT;
        UIR &= ~TRNIF;
        handle_transaction(i);
    }
}

unsigned char usb_configured(void)
{
    return configuration != 0;
}

unsigned char usb_report_ready(void)
{
    return configuration && !(bdt[BD_EP1_IN] & UOWN);
}

void usb_send_report(const unsigned char __data *report)
{
    unsigned char i;
    for (i = 0; i < REPORT_SIZE; i++)
        ep1_in[i] = report[i];
    bdt[BD_EP1_IN + 1] = REPORT_SIZE;
    bdt[BD_EP1_IN + 2] = 0x80;
    bdt[BD_EP1_IN + 3] = 0x05;
    bdt[BD_EP1_IN] = UOWN | DTSEN | (ep1_toggle ? DTS : 0);
    ep1_toggle ^= 1;
}

/* A packet has arrived when the SIE gives the BD back. It is then re-armed
 * at once on the other buffer, unless the caller still holds that one. */
unsigned char usb_out_available(void)
{
    if (!configuration || ep1_out_full || (bdt[BD_EP1_OUT] & UOWN))
        return ep1_out_full;
    ep1_out_full = 1;
    ep1_out_which ^= 1;
    ep1_out_toggle ^= 1;
    arm_ep1_out();
    return 1;
}

/* The buffer holding the received packet (the one the BD no longer uses). */
const unsigned char __data *usb_out_buffer(void)
{
    return ep1_out_which ? (const unsigned char __data *)ep1_out_a
                         : (const unsigned char __data *)ep1_out_b;
}

void usb_out_release(void)
{
    ep1_out_full = 0;
}
