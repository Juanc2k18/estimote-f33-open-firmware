/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2018 Ha Thach for Adafruit Industries
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#ifndef _ESTIMOTE_F33_H
#define _ESTIMOTE_F33_H

/*------------------------------------------------------------------*/
/* LED
 *------------------------------------------------------------------*/
// r42: single LED on P0.17 (pin 20) via a transistor, active high.
// P0.19 (pin 22) is the IRQ/OUT of the M41T62 RTC: not used as an LED.
#define LEDS_NUMBER       1
#define LED_PRIMARY_PIN   17
#define LED_STATE_ON      1

/*------------------------------------------------------------------*/
/* BUTTON
 *------------------------------------------------------------------*/
// The board has no buttons. P0.22 is held low by an external circuit and
// P0.20 is unknown: if they were defined, a low level at boot would force
// DFU. Entering DFU: 1 s UART window after reset, GPREGRET (0xA8 = OTA,
// 0x4E = serial only) from the application or SWD.

/*------------------------------------------------------------------*/
/* UART (only used by nRF52832)
 *------------------------------------------------------------------*/
#define RX_PIN_NUMBER  12 // E2, QFN48 pin 15 (continuity r08)
#define TX_PIN_NUMBER  13 // E1, QFN48 pin 16 (continuity r08)
#define CTS_PIN_NUMBER 0
#define RTS_PIN_NUMBER 0
#define HWFC           false

//--------------------------------------------------------------------+
// BLE OTA
//--------------------------------------------------------------------+
#define BLEDIS_MANUFACTURER "Estimote F3.3 (repurposed)"
#define BLEDIS_MODEL        "Estimote F3.3 r46"

#define UF2_PRODUCT_NAME    "Estimote F3.3 nRF52832"
#define UF2_INDEX_URL       "https://www.adafruit.com/product/3406"

#endif // _ESTIMOTE_F33_H
