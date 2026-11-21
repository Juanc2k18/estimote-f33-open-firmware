// Sensor bus scanner for the nRF52832 of the Estimote F3.3.
// Loaded into RAM over SWD and run without touching flash (see run_scanner.py).
// r24: targeted SPI only, modes 0/3. Separate counters per transaction.
// Requires CS/SCK continuity before running. Do not use a bulk sweep.
#include <stdint.h>

#ifndef REG
#define REG(a) (*(volatile uint32_t *)(a))
#endif
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
    volatile uint32_t cs_not_low, sck_not_toggle, completed;
    volatile uint32_t no_signature, signatures, validation_incomplete, cs_not_high;
} results_t;

#ifdef TEST_GPIO
results_t res;
#else
results_t res __attribute__((section(".results")));
#endif

static void delay(volatile uint32_t n) { while (n--) __asm volatile("nop"); }
#ifdef TEST_GPIO
#define set test_set
#define get test_get
#else
static inline void set(int p, int v) { if (v) P0_OUTSET = 1u << p; else P0_OUTCLR = 1u << p; }
static inline int get(int p) { return (P0_IN >> p) & 1; }
#endif
static int clock_level(int p, int level) { set(p, level); delay(5); return get(p) == level; }

static void add(int kind, int cs, int sck, int mosi, int miso, int mode, int reg, int val) {
    if (res.count < sizeof(res.hits) / sizeof(res.hits[0])) {
        hit_t *h = &res.hits[res.count];
        h->kind = kind; h->cs = cs; h->sck = sck; h->mosi = mosi;
        h->miso = miso; h->mode = mode; h->reg = reg; h->val = val;
    }
    res.count++;
}

static int spi_read(int cs, int sck, int mosi, int miso, int mode, uint8_t cmd, int selected) {
    int cpol = mode == 3;
    set(cs, 1); PIN_CNF(cs) = CNF_OUT;
    set(sck, cpol); PIN_CNF(sck) = CNF_OUT;
    set(mosi, 0); PIN_CNF(mosi) = CNF_OUT;
    if (miso != mosi) PIN_CNF(miso) = CNF_IN_PU;
    delay(20);
    set(cs, !selected); delay(20);
    int v = 0;
    if (selected && get(cs)) { res.cs_not_low++; v = -1; goto cleanup; }
    if (!selected && !get(cs)) { res.cs_not_high++; v = -3; goto cleanup; }
    if (get(sck) != cpol) goto bad_clock;
    for (int i = 7; i >= 0; i--) {
        set(mosi, (cmd >> i) & 1);
        if (!clock_level(sck, !cpol) || !clock_level(sck, cpol)) goto bad_clock;
    }
    if (miso == mosi) PIN_CNF(miso) = CNF_IN_PU;
    for (int i = 0; i < 8; i++) {
        if (!clock_level(sck, !cpol)) goto bad_clock;
        if (mode == 0) v = (v << 1) | get(miso);
        if (!clock_level(sck, cpol)) goto bad_clock;
        if (mode == 3) v = (v << 1) | get(miso);
    }
    res.completed++;
    goto cleanup;
bad_clock:
    res.sck_not_toggle++; v = -2;
cleanup:
    set(cs, 1); delay(20);
    PIN_CNF(cs) = CNF_DEFAULT; PIN_CNF(sck) = CNF_DEFAULT;
    PIN_CNF(mosi) = CNF_DEFAULT; PIN_CNF(miso) = CNF_DEFAULT;
    return v;
}

static const uint8_t spi_cmds[] = {0x8F, 0xCF, 0xD0, 0x80, 0x92};

int main(void) {
    res.count = 0; res.done = 0; res.progress = 0;
    res.cs_not_low = res.sck_not_toggle = res.completed = 0;
    res.no_signature = res.signatures = res.validation_incomplete = res.cs_not_high = 0;
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
                if (!(((res.magic ? res.magic : res.sck_mask) >> mosi) & 1) || mosi == sck || mosi == cs) continue;
                for (int miso = 0; miso < 32; miso++) {
                    if (!((res.miso_mask >> miso) & 1) || miso == sck || miso == cs) continue;
                    res.progress++;
                    for (int mode = 0; mode <= 3; mode += 3)
                        for (unsigned c = 0; c < sizeof(spi_cmds); c++) {
                            int v = spi_read(cs, sck, mosi, miso, mode, spi_cmds[c], 1);
                            if (v < 0) continue;
                            if (v == 0xFF || v == 0x00) { res.no_signature++; continue; }
                            int repeat = spi_read(cs, sck, mosi, miso, mode, spi_cmds[c], 1);
                            int control = spi_read(cs, sck, mosi, miso, mode, spi_cmds[c], 0);
                            if (repeat < 0 || control < 0) { res.validation_incomplete++; continue; }
                            if (v == repeat && v != control) {
                                res.signatures++; add(1, cs, sck, mosi, miso, mode, spi_cmds[c], v);
                            } else res.no_signature++;
                        }
                }
            }
        }
    }
    res.done = 1;
    res.magic = 0x5CA22E12;
    #ifndef TEST_GPIO
    for (;;) __asm volatile("bkpt #0");
#else
    return 0;
#endif
}

#ifndef TEST_GPIO
__attribute__((naked, noreturn, section(".entry"))) void _start(void) {
    __asm volatile("cpsid i\n ldr r0, =0x20010000\n mov sp, r0\n bl main\n b .");
}

#endif
