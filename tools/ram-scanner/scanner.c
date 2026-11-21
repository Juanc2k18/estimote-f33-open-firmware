// Sensor bus scanner for the nRF52832 of the Estimote F3.3.
// Loaded into RAM over SWD and run without touching flash (see run_scanner.py).
// Tests bit-banged SPI (4-wire and 3-wire, modes 0 and 3) with CS on P0.06/P0.07
// reading typical WHO_AM_I registers, and I2C on any pair of pins with pull-up.
#include <stdint.h>

#define REG(a) (*(volatile uint32_t *)(a))
#define P0_OUTSET REG(0x50000508)
#define P0_OUTCLR REG(0x5000050C)
#define P0_IN     REG(0x50000510)
#define PIN_CNF(p) REG(0x50000700 + 4 * (p))

#define CNF_OUT      0x1  // output, input buffer connected
#define CNF_IN_PU    0xC  // input, pull-up
#define CNF_IN       0x0  // input without pull
#define CNF_DEFAULT  0x2  // reset state (input disconnected)

typedef struct {
    uint8_t kind, cs, sck, mosi, miso, mode, reg, val;
} hit_t;

typedef struct {
    volatile uint32_t magic, done, count, progress;
    uint32_t power_mask;           // pins set HIGH before scanning
    uint32_t sck_mask, miso_mask;  // candidates
    uint32_t cs_mask;
    uint32_t i2c_mask;
    hit_t hits[120];
} results_t;

results_t res __attribute__((section(".results")));

static void delay(volatile uint32_t n) { while (n--) __asm volatile("nop"); }
static inline void set(int p, int v) { if (v) P0_OUTSET = 1u << p; else P0_OUTCLR = 1u << p; }
static inline int get(int p) { return (P0_IN >> p) & 1; }

static void add(int kind, int cs, int sck, int mosi, int miso, int mode, int reg, int val) {
    if (res.count < sizeof(res.hits) / sizeof(res.hits[0])) {
        hit_t *h = &res.hits[res.count];
        h->kind = kind; h->cs = cs; h->sck = sck; h->mosi = mosi;
        h->miso = miso; h->mode = mode; h->reg = reg; h->val = val;
    }
    res.count++;
}

static int spi_read(int cs, int sck, int mosi, int miso, int mode, uint8_t cmd) {
    int cpol = mode == 3;
    PIN_CNF(cs) = CNF_OUT; set(cs, 1);
    PIN_CNF(sck) = CNF_OUT; set(sck, cpol);
    PIN_CNF(mosi) = CNF_OUT; set(mosi, 0);
    if (miso != mosi) PIN_CNF(miso) = CNF_IN_PU;
    delay(20);
    set(cs, 0); delay(20);
    for (int i = 7; i >= 0; i--) {
        set(mosi, (cmd >> i) & 1);
        if (mode == 3) { set(sck, 0); delay(5); set(sck, 1); delay(5); }
        else { delay(5); set(sck, 1); delay(5); set(sck, 0); }
    }
    if (miso == mosi) PIN_CNF(miso) = CNF_IN_PU;
    int v = 0;
    for (int i = 0; i < 8; i++) {
        if (mode == 3) { set(sck, 0); delay(5); set(sck, 1); delay(3); v = (v << 1) | get(miso); delay(2); }
        else { delay(5); set(sck, 1); delay(3); v = (v << 1) | get(miso); delay(2); set(sck, 0); }
    }
    set(cs, 1); delay(20);
    PIN_CNF(sck) = CNF_DEFAULT; PIN_CNF(mosi) = CNF_DEFAULT; PIN_CNF(miso) = CNF_DEFAULT;
    return v;
}

// I2C with emulated open drain (OUT=0, the direction is toggled).
static int sda_p, scl_p;
static void lo(int p) { PIN_CNF(p) = CNF_OUT; }
static void hi(int p) { PIN_CNF(p) = CNF_IN; }
static void i2c_start(void) { hi(sda_p); hi(scl_p); delay(50); lo(sda_p); delay(50); lo(scl_p); delay(50); }
static void i2c_stop(void) { lo(sda_p); delay(50); hi(scl_p); delay(50); hi(sda_p); delay(50); }
static int i2c_wb(uint8_t b) {
    for (int i = 7; i >= 0; i--) {
        if ((b >> i) & 1) hi(sda_p); else lo(sda_p);
        delay(30); hi(scl_p); delay(50); lo(scl_p); delay(30);
    }
    hi(sda_p); delay(30); hi(scl_p); delay(50);
    int ack = !get(sda_p);
    lo(scl_p); delay(30);
    return ack;
}
static int i2c_rb(int ack) {
    int v = 0;
    hi(sda_p);
    for (int i = 0; i < 8; i++) { delay(30); hi(scl_p); delay(50); v = (v << 1) | get(sda_p); lo(scl_p); }
    if (ack) lo(sda_p); else hi(sda_p);
    delay(30); hi(scl_p); delay(50); lo(scl_p); hi(sda_p); delay(30);
    return v;
}

static const uint8_t spi_cmds[] = {0x8F, 0xCF, 0xD0, 0x80, 0x92};

int main(void) {
    res.count = 0; res.done = 0; res.progress = 0;
    for (int p = 0; p < 32; p++)
        if ((res.power_mask >> p) & 1) { P0_OUTSET = 1u << p; PIN_CNF(p) = CNF_OUT; }
    P0_OUTCLR = ~res.power_mask;
    delay(2000000);  // sensor start-up (~100 ms)

    // SPI
    for (int cs = 0; cs < 32; cs++) {
        if (!((res.cs_mask >> cs) & 1)) continue;
        for (int sck = 0; sck < 32; sck++) {
            if (!((res.sck_mask >> sck) & 1) || sck == cs) continue;
            for (int mosi = 0; mosi < 32; mosi++) {
                if (!((res.sck_mask >> mosi) & 1) || mosi == sck || mosi == cs) continue;
                for (int miso = 0; miso < 32; miso++) {
                    if (!((res.miso_mask >> miso) & 1) || miso == sck || miso == cs) continue;
                    res.progress++;
                    for (int mode = 0; mode <= 3; mode += 3)
                        for (unsigned c = 0; c < sizeof(spi_cmds); c++) {
                            int v = spi_read(cs, sck, mosi, miso, mode, spi_cmds[c]);
                            if (v != 0xFF && v != 0x00) add(1, cs, sck, mosi, miso, mode, spi_cmds[c], v);
                        }
                }
            }
        }
    }
    // I2C: any pair of candidate pins
    for (int a = 0; a < 32; a++) {
        if (!((res.i2c_mask >> a) & 1)) continue;
        for (int b = 0; b < 32; b++) {
            if (!((res.i2c_mask >> b) & 1) || a == b) continue;
            sda_p = a; scl_p = b;
            P0_OUTCLR = (1u << a) | (1u << b);
            // With the internal pull-down they only stay high if there are real external pull-ups.
            PIN_CNF(a) = 0x4; PIN_CNF(b) = 0x4; delay(2000);
            int pu = get(a) && get(b);
            hi(a); hi(b); delay(100);
            if (!pu) { PIN_CNF(a) = CNF_DEFAULT; PIN_CNF(b) = CNF_DEFAULT; continue; }
            for (int addr = 0x08; addr < 0x78; addr++) {
                i2c_start();
                int ack = i2c_wb((uint8_t)(addr << 1 | 1));
                int v = ack ? i2c_rb(0) : 0;
                i2c_stop();
                if (ack) add(2, 0, scl_p, sda_p, 0, 0, addr, v);
            }
            PIN_CNF(a) = CNF_DEFAULT; PIN_CNF(b) = CNF_DEFAULT;
        }
    }
    res.done = 1;
    res.magic = 0x5CA22E12;
    for (;;) __asm volatile("bkpt #0");
}

__attribute__((naked, noreturn, section(".entry"))) void _start(void) {
    __asm volatile("ldr r0, =0x20010000\n mov sp, r0\n bl main\n b .");
}
