#include <stdint.h>
#define REG(a) (*(volatile uint32_t *)(a))
int main(void) {
    volatile uint32_t *len=(uint32_t *)0x20005400;
    volatile uint32_t *done=(uint32_t *)0x20005404;
    volatile uint32_t *sent=(uint32_t *)0x20005408;
    volatile uint8_t *data=(uint8_t *)0x20005000;
    *done=0; *sent=0;
    if (*len>400) { *done=3; for (;;) __asm volatile("nop"); }
    for (uint32_t i=0;i<*len;i++) {
        uint32_t limit=1000000;
        while (!(REG(0xE0000000)&1) && --limit) __asm volatile("nop");
        if (!limit) { *done=2; for (;;) __asm volatile("nop"); }
        *(volatile uint8_t *)0xE0000000=data[i];
        *sent=i+1;
        for (volatile unsigned d=0;d<30000;d++) __asm volatile("nop");
    }
    *done=1;
    for (;;) __asm volatile("nop");
}
__attribute__((naked,noreturn,section(".entry"))) void _start(void) {
    __asm volatile("cpsid i\n ldr r0, =0x20010000\n mov sp, r0\n bl main\n b .");
}
