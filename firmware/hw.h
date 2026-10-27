/* PIC18F67J50 special function registers used by this firmware.
 * SDCC's non-free device headers aren't installed, so registers are
 * declared directly by address. */
#ifndef HW_H
#define HW_H

/* regs.c defines HW_DEFINE_SFRS to emit the symbols once. */
#ifdef HW_DEFINE_SFRS
#define SFR(name, addr) volatile __at(addr) unsigned char name
#else
#define SFR(name, addr) extern volatile __at(addr) unsigned char name
#endif

/* Ports */
SFR(PORTA, 0xF80); SFR(PORTB, 0xF81); SFR(PORTC, 0xF82); SFR(PORTD, 0xF83);
SFR(PORTE, 0xF84); SFR(PORTF, 0xF85); SFR(PORTG, 0xF86);
SFR(LATA, 0xF89);  SFR(LATB, 0xF8A);  SFR(LATC, 0xF8B);  SFR(LATD, 0xF8C);
SFR(LATE, 0xF8D);  SFR(LATF, 0xF8E);  SFR(LATG, 0xF8F);
SFR(TRISA, 0xF92); SFR(TRISB, 0xF93); SFR(TRISC, 0xF94); SFR(TRISD, 0xF95);
SFR(TRISE, 0xF96); SFR(TRISF, 0xF97); SFR(TRISG, 0xF98);

/* Core / analog. ANCON0/ANCON1 share addresses with ADCON1/ADCON0 and are
 * reached by setting WDTCON.ADSHR (bit 4). */
SFR(INTCON, 0xFF2); SFR(INTCON2, 0xFF1); SFR(INTCON3, 0xFF0);
SFR(ADCON0, 0xFC2); SFR(ADCON1, 0xFC1);
SFR(ANCON1, 0xFC2); SFR(ANCON0, 0xFC1);
SFR(WDTCON, 0xFC0);
SFR(PIE1, 0xF9D);   SFR(PIE2, 0xFA0);

/* Timer0 */
SFR(T0CON, 0xFD5); SFR(TMR0L, 0xFD6); SFR(TMR0H, 0xFD7);

/* MSSP2 (LCD SPI) */
SFR(SSP2BUF, 0xF6F); SFR(SSP2STAT, 0xF6D); SFR(SSP2CON1, 0xF6C);
SFR(PIR3, 0xFA4);

/* USB */
SFR(UCON, 0xF65);  SFR(USTAT, 0xF64); SFR(UEIR, 0xF63); SFR(UIR, 0xF62);
SFR(UFRMH, 0xF61); SFR(UFRML, 0xF60); SFR(UCFG, 0xF5F); SFR(UADDR, 0xF5E);
SFR(UEIE, 0xF5D);  SFR(UIE, 0xF5C);
SFR(UEP0, 0xF4C);  SFR(UEP1, 0xF4D);  SFR(UEP2, 0xF4E);

#define ADSHR   0x10
#define RBPU    0x80

#endif
