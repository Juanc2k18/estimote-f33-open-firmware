#include <assert.h>
#include <stdint.h>
static uint32_t regs[1024];
static int levels[32], stuck_cs, stuck_sck;
static uint32_t *reg_addr(uint32_t addr){return &regs[(addr&0xfff)/4];}
static void test_set(int p,int v){levels[p]=v;}
static int test_get(int p){if(p==2&&stuck_cs)return 1;if(p==8&&stuck_sck)return stuck_sck==2;return levels[p];}
#define REG(a) (*reg_addr(a))
#define TEST_GPIO
#define main scanner_main
#include "../tools/ram-scanner/scanner-r24-spi.c"
#undef main
int main(void){
 assert(__builtin_offsetof(results_t,cs_not_low)==996);
 stuck_cs=1;assert(spi_read(2,8,16,17,0,0x8f,1)==-1);
 stuck_cs=0;stuck_sck=1;assert(spi_read(2,8,16,17,0,0x8f,1)==-2);
 stuck_sck=0;assert(spi_read(2,8,16,17,0,0x8f,1)==0);
 assert(res.cs_not_low==1 && res.sck_not_toggle==1 && res.completed==1);
 assert(spi_read(2,8,16,17,3,0x8f,1)==0);
 assert(res.completed==2);
 stuck_sck=2;assert(spi_read(2,8,16,17,3,0x8f,1)==-2);
 stuck_sck=0;
 res.power_mask=res.i2c_mask=0;res.cs_mask=1u<<2;
 res.sck_mask=1u<<8;res.magic=1u<<16;res.miso_mask=1u<<17;
 scanner_main();
 assert(res.progress==1 && res.completed==10 && res.no_signature==10);
 assert(res.cs_not_low==0 && res.sck_not_toggle==0 && res.signatures==0);
 res.magic=1u<<16;stuck_cs=1;scanner_main();
 assert(res.progress==1 && res.cs_not_low==10 && res.completed==0 && res.no_signature==0);
 stuck_cs=0;stuck_sck=1;res.magic=1u<<16;scanner_main();
 assert(res.sck_not_toggle==10 && res.completed==0 && res.no_signature==0);
 return 0;
}
