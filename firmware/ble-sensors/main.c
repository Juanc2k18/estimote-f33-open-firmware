// F3.3 application, version 1.0.0: sensors over BLE (r44), battery, version and serial DFU (r45), continuous
// measurement and RAM status for SWD (r45c) and UART with a host on E1/E2 (1.0.0). Designs:
// internal design notes (not published).
#include <stdbool.h>
#include <string.h>
#include "nrf.h"
#include "nrf_sdm.h"
#include "nrf_soc.h"
#include "nrf_nvic.h"
#include "ble.h"
#include "sensors.h"
#include "uart.h"

#define LED_PIN        17          // r42: transistor, active high
#define APP_CONN_TAG   1
#define ATT_MTU        64
#define DFU_MAGIC_OTA  0xA8        // Adafruit bootloader: DFU over BLE ("AdaDFU")
#define DFU_MAGIC_UART 0x4E        // Adafruit bootloader: DFU over UART (E1/E2), 3 s without traffic
#ifndef FW_REV
#define FW_REV         "1.0.0"
#endif
#define DEVICE_NAME    "F33"

// 239dXXXX-86eb-4a92-8ec1-0e38f13e0817, in little-endian order.
static const ble_uuid128_t BASE_UUID = {{0x17, 0x08, 0x3e, 0xf1, 0x38, 0x0e, 0xc1, 0x8e,
                                         0x92, 0x4a, 0xeb, 0x86, 0x00, 0x00, 0x9d, 0x23}};
enum { UUID_SERVICE = 0x0001, UUID_DATA = 0x0002, UUID_CONTROL = 0x0003 };

extern uint32_t __data_start__;   // start of the application RAM (linker)
nrf_nvic_state_t nrf_nvic_state;   // required by nrf_nvic.h

static uint16_t conn = BLE_CONN_HANDLE_INVALID;
static uint8_t adv_handle = BLE_GAP_ADV_SET_HANDLE_NOT_SET;
static uint8_t adv_buf[BLE_GAP_ADV_SET_DATA_SIZE_MAX], srsp_buf[BLE_GAP_ADV_SET_DATA_SIZE_MAX];
static ble_gatts_char_handles_t data_char, ctrl_char, batt_char, rev_char;
static uint8_t battery_pct;
static uint8_t packet[F33_PACKET_LEN];
// Status for reading over SWD without halting the CPU (scripts/swd_monitor.py). `count` changes
// after the packet is copied: the reader discards the copy if it changed while reading.
typedef struct { uint32_t magic, resetreas, count; uint8_t packet[F33_PACKET_LEN]; uint32_t uart_dropped; } swd_status_t;
volatile swd_status_t f33_status __attribute__((used)) = {.magic = 0x53333346};   // "F33S"
static f33_sample_t sample;
static bool notify_on, batt_notify_on;
static volatile bool tick, second;
static volatile uint32_t period_s = 1, elapsed;   // measurement interval (UART command `int N`)
static uint32_t evt_buf[(sizeof(ble_evt_t) + ATT_MTU + 3) / 4];

// An unrecoverable error resets; the bootloader keeps its UART DFU window.
static void check(uint32_t err) { if (err != NRF_SUCCESS) NVIC_SystemReset(); }
static void fault(uint32_t id, uint32_t pc, uint32_t info) { (void)id; (void)pc; (void)info; NVIC_SystemReset(); }

void SWI2_EGU2_IRQHandler(void) {}   // only wakes up sd_app_evt_wait

// The RTC interrupts every 1 s and counts up to period_s: a single comparator cannot reach 3600 s
// (24 bits at 32768 Hz overflow after 512 s).
void RTC1_IRQHandler(void) {
  NRF_RTC1->EVENTS_COMPARE[0] = 0;
  NRF_RTC1->CC[0] = (NRF_RTC1->COUNTER + 32768u) & 0xFFFFFF;
  second = true;   // host detection every second, whatever the interval
  if (++elapsed >= period_s) { elapsed = 0; tick = true; }
}

static void led(bool on) { if (on) NRF_P0->OUTSET = 1u << LED_PIN; else NRF_P0->OUTCLR = 1u << LED_PIN; }
static void flash(void) { led(true); delay_us(50000); led(false); }

static void timer_start(void) {
  NRF_RTC1->TASKS_STOP = 1;
  NRF_RTC1->PRESCALER = 0;
  NRF_RTC1->TASKS_CLEAR = 1;
  NRF_RTC1->CC[0] = 32768u;
  NRF_RTC1->EVENTS_COMPARE[0] = 0;
  NRF_RTC1->EVTENSET = RTC_EVTEN_COMPARE0_Msk;
  NRF_RTC1->INTENSET = RTC_INTENSET_COMPARE0_Msk;
  check(sd_nvic_SetPriority(RTC1_IRQn, 6));
  check(sd_nvic_EnableIRQ(RTC1_IRQn));
  NRF_RTC1->TASKS_START = 1;
}


static void stack_init(void) {
  nrf_clock_lf_cfg_t clk = {.source = NRF_CLOCK_LF_SRC_RC, .rc_ctiv = 16, .rc_temp_ctiv = 2,
                            .accuracy = NRF_CLOCK_LF_ACCURACY_500_PPM};   // same as the bootloader
  check(sd_softdevice_enable(&clk, fault));
  check(sd_nvic_EnableIRQ(SD_EVT_IRQn));

  uint32_t ram = (uint32_t)&__data_start__;
  ble_cfg_t cfg;
  memset(&cfg, 0, sizeof cfg);
  cfg.conn_cfg.conn_cfg_tag = APP_CONN_TAG;
  cfg.conn_cfg.params.gap_conn_cfg.conn_count = 1;
  cfg.conn_cfg.params.gap_conn_cfg.event_length = BLE_GAP_EVENT_LENGTH_DEFAULT;
  check(sd_ble_cfg_set(BLE_CONN_CFG_GAP, &cfg, ram));
  memset(&cfg, 0, sizeof cfg);
  cfg.conn_cfg.conn_cfg_tag = APP_CONN_TAG;
  cfg.conn_cfg.params.gatt_conn_cfg.att_mtu = ATT_MTU;
  check(sd_ble_cfg_set(BLE_CONN_CFG_GATT, &cfg, ram));
  memset(&cfg, 0, sizeof cfg);
  cfg.gap_cfg.role_count_cfg.adv_set_count = 1;
  cfg.gap_cfg.role_count_cfg.periph_role_count = 1;
  check(sd_ble_cfg_set(BLE_GAP_CFG_ROLE_COUNT, &cfg, ram));
  memset(&cfg, 0, sizeof cfg);
  cfg.common_cfg.vs_uuid_cfg.vs_uuid_count = 1;
  check(sd_ble_cfg_set(BLE_COMMON_CFG_VS_UUID, &cfg, ram));
  check(sd_ble_enable(&ram));   // NO_MEM if the application RAM starts too low
}

static void gap_init(void) {
  ble_gap_conn_sec_mode_t open;
  BLE_GAP_CONN_SEC_MODE_SET_OPEN(&open);
  check(sd_ble_gap_device_name_set(&open, (const uint8_t *)DEVICE_NAME, sizeof DEVICE_NAME - 1));
  ble_gap_conn_params_t pp = {.min_conn_interval = 80, .max_conn_interval = 160,   // 100–200 ms
                              .slave_latency = 0, .conn_sup_timeout = 400};         // 4 s
  check(sd_ble_gap_ppcp_set(&pp));
}

static void add_char(uint16_t svc, uint16_t uuid16, uint8_t type, bool readable, bool notify,
                     bool writable, uint8_t *init, uint16_t len, ble_gatts_char_handles_t *h) {
  ble_gatts_char_md_t md = {0};
  ble_gatts_attr_md_t cccd = {0}, attr_md = {0};
  md.char_props.read = readable;
  md.char_props.notify = notify;
  md.char_props.write = writable;
  if (notify) {
    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd.read_perm);
    BLE_GAP_CONN_SEC_MODE_SET_OPEN(&cccd.write_perm);
    cccd.vloc = BLE_GATTS_VLOC_STACK;
    md.p_cccd_md = &cccd;
  }
  if (readable) BLE_GAP_CONN_SEC_MODE_SET_OPEN(&attr_md.read_perm);
  if (writable) BLE_GAP_CONN_SEC_MODE_SET_OPEN(&attr_md.write_perm);
  attr_md.vloc = BLE_GATTS_VLOC_STACK;
  ble_uuid_t uuid = {.uuid = uuid16, .type = type};
  ble_gatts_attr_t attr = {.p_uuid = &uuid, .p_attr_md = &attr_md, .init_len = len, .max_len = len,
                           .p_value = init};
  check(sd_ble_gatts_characteristic_add(svc, &md, &attr, h));
}

static uint8_t uuid_type;

static void gatt_init(void) {
  check(sd_ble_uuid_vs_add(&BASE_UUID, &uuid_type));
  ble_uuid_t svc_uuid = {.uuid = UUID_SERVICE, .type = uuid_type};
  uint16_t svc;
  check(sd_ble_gatts_service_add(BLE_GATTS_SRVC_TYPE_PRIMARY, &svc_uuid, &svc));
  f33_pack(&sample, packet);
  add_char(svc, UUID_DATA, uuid_type, true, true, false, packet, F33_PACKET_LEN, &data_char);
  uint8_t zero = 0;
  add_char(svc, UUID_CONTROL, uuid_type, false, false, true, &zero, 1, &ctrl_char);

  ble_uuid_t bas = {.uuid = 0x180F, .type = BLE_UUID_TYPE_BLE};   // Battery Service
  check(sd_ble_gatts_service_add(BLE_GATTS_SRVC_TYPE_PRIMARY, &bas, &svc));
  add_char(svc, 0x2A19, BLE_UUID_TYPE_BLE, true, true, false, &battery_pct, 1, &batt_char);
  ble_uuid_t dis = {.uuid = 0x180A, .type = BLE_UUID_TYPE_BLE};   // Device Information
  check(sd_ble_gatts_service_add(BLE_GATTS_SRVC_TYPE_PRIMARY, &dis, &svc));
  add_char(svc, 0x2A26, BLE_UUID_TYPE_BLE, true, false, false, (uint8_t *)FW_REV, sizeof FW_REV - 1, &rev_char);
}

static void adv_init(void) {
  uint8_t *p = adv_buf;
  *p++ = 2; *p++ = BLE_GAP_AD_TYPE_FLAGS; *p++ = BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE;
  *p++ = sizeof DEVICE_NAME; *p++ = BLE_GAP_AD_TYPE_COMPLETE_LOCAL_NAME;
  memcpy(p, DEVICE_NAME, sizeof DEVICE_NAME - 1); p += sizeof DEVICE_NAME - 1;
  uint8_t *s = srsp_buf;
  *s++ = 17; *s++ = BLE_GAP_AD_TYPE_128BIT_SERVICE_UUID_COMPLETE;
  memcpy(s, BASE_UUID.uuid128, 16); s[12] = UUID_SERVICE & 0xFF; s[13] = UUID_SERVICE >> 8; s += 16;
  static ble_gap_adv_data_t data;
  data.adv_data.p_data = adv_buf; data.adv_data.len = (uint16_t)(p - adv_buf);
  data.scan_rsp_data.p_data = srsp_buf; data.scan_rsp_data.len = (uint16_t)(s - srsp_buf);
  ble_gap_adv_params_t prm = {0};
  prm.properties.type = BLE_GAP_ADV_TYPE_CONNECTABLE_SCANNABLE_UNDIRECTED;
  prm.interval = 1600;   // 1 s in units of 0.625 ms
  prm.duration = BLE_GAP_ADV_TIMEOUT_GENERAL_UNLIMITED;
  prm.filter_policy = BLE_GAP_ADV_FP_ANY;
  prm.primary_phy = BLE_GAP_PHY_1MBPS;
  check(sd_ble_gap_adv_set_configure(&adv_handle, &data, &prm));
}

static void adv_start(void) { check(sd_ble_gap_adv_start(adv_handle, APP_CONN_TAG)); }

static void send_sample(void) {
  char line[F33_JSON_MAX];
  size_t n = f33_json_line(&sample, line, sizeof line);
  if (n) uart_write(line, n);   // without a host, uart_write does nothing
}

// Every measurement (tick, `read` command or BLE connection) goes out over BLE and, if a host is present, over UART.
static void measure_and_publish(void) {
  sample.seq++;
  sensors_read(&sample);
  f33_pack(&sample, packet);
  for (unsigned i = 0; i < F33_PACKET_LEN; i++) f33_status.packet[i] = packet[i];
  f33_status.count++;
  ble_gatts_value_t v = {.len = F33_PACKET_LEN, .offset = 0, .p_value = packet};
  sd_ble_gatts_value_set(conn, data_char.value_handle, &v);
  if (notify_on && conn != BLE_CONN_HANDLE_INVALID) {
    uint16_t len = F33_PACKET_LEN;
    ble_gatts_hvx_params_t hvx = {.handle = data_char.value_handle, .type = BLE_GATT_HVX_NOTIFICATION,
                                  .p_len = &len, .p_data = packet};
    sd_ble_gatts_hvx(conn, &hvx);   // queue full or short MTU: this sample is lost, not fatal
  }
  uint8_t pct = (sample.flags & F33_ADC) ? f33_battery_percent(f33_battery_mv(sample.ain3_mv)) : 0;
  ble_gatts_value_t bv = {.len = 1, .offset = 0, .p_value = &pct};
  sd_ble_gatts_value_set(conn, batt_char.value_handle, &bv);
  if (batt_notify_on && conn != BLE_CONN_HANDLE_INVALID && pct != battery_pct) {
    uint16_t len = 1;
    ble_gatts_hvx_params_t hvx = {.handle = batt_char.value_handle, .type = BLE_GATT_HVX_NOTIFICATION,
                                  .p_len = &len, .p_data = &pct};
    sd_ble_gatts_hvx(conn, &hvx);
  }
  battery_pct = pct;
  send_sample();
}

static void enter_dfu(uint8_t magic) {
  sd_power_gpregret_clr(0, 0xFF);
  sd_power_gpregret_set(0, magic);
  NVIC_SystemReset();
}

static void set_period(uint32_t s) {
  uint8_t nested;
  sd_nvic_critical_region_enter(&nested);
  period_s = s;
  elapsed = 0;
  sd_nvic_critical_region_exit(nested);
}

// Host commands on E2. See the command table in the design.
static void uart_service(void) {
  if (uart_lost()) { uart_stop(); return; }   // detected again in the next second
  char line[F33_LINE_MAX + 1];
  int k = uart_take_line(line);
  if (!k) return;
  uint32_t arg = 0;
  f33_cmd_t c = k == 1 ? f33_parse_cmd(line, &arg) : k == -1 ? F33_CMD_ERR_LONG : F33_CMD_ERR_CMD;
  if (c == F33_CMD_DFU || c == F33_CMD_OTA) uart_flush();   // make room for the ACK: the host waits for it
  char out[48];
  size_t n = f33_reply(c, arg, FW_REV, out, sizeof out);
  if (n) uart_write(out, n);
  switch (c) {
  case F33_CMD_READ: measure_and_publish(); break;
  case F33_CMD_INT:  set_period(arg); break;
  case F33_CMD_DFU:  uart_flush(); enter_dfu(DFU_MAGIC_UART); break;
  case F33_CMD_OTA:  uart_flush(); enter_dfu(DFU_MAGIC_OTA); break;
  default: break;
  }
}

static void on_ble(const ble_evt_t *e) {
  switch (e->header.evt_id) {
  case BLE_GAP_EVT_CONNECTED:
    conn = e->evt.gap_evt.conn_handle;
    notify_on = batt_notify_on = false;
    flash();
    measure_and_publish();
    break;
  case BLE_GAP_EVT_DISCONNECTED:
    conn = BLE_CONN_HANDLE_INVALID;
    adv_start();
    break;
  case BLE_GAP_EVT_PHY_UPDATE_REQUEST: {
    ble_gap_phys_t phys = {.tx_phys = BLE_GAP_PHY_AUTO, .rx_phys = BLE_GAP_PHY_AUTO};
    sd_ble_gap_phy_update(e->evt.gap_evt.conn_handle, &phys);
    break;
  }
  case BLE_GAP_EVT_DATA_LENGTH_UPDATE_REQUEST:
    sd_ble_gap_data_length_update(e->evt.gap_evt.conn_handle, NULL, NULL);
    break;
  case BLE_GAP_EVT_SEC_PARAMS_REQUEST:
    sd_ble_gap_sec_params_reply(e->evt.gap_evt.conn_handle, BLE_GAP_SEC_STATUS_PAIRING_NOT_SUPP, NULL, NULL);
    break;
  case BLE_GATTS_EVT_SYS_ATTR_MISSING:
    sd_ble_gatts_sys_attr_set(e->evt.gatts_evt.conn_handle, NULL, 0, 0);
    break;
  case BLE_GATTS_EVT_EXCHANGE_MTU_REQUEST:
    sd_ble_gatts_exchange_mtu_reply(e->evt.gatts_evt.conn_handle, ATT_MTU);
    break;
  case BLE_GATTS_EVT_WRITE: {
    const ble_gatts_evt_write_t *w = &e->evt.gatts_evt.params.write;
    if (w->handle == data_char.cccd_handle && w->len == 2)
      notify_on = w->data[0] & BLE_GATT_HVX_NOTIFICATION;
    else if (w->handle == batt_char.cccd_handle && w->len == 2)
      batt_notify_on = w->data[0] & BLE_GATT_HVX_NOTIFICATION;
    else if (w->handle == ctrl_char.value_handle && w->len == 1 && w->data[0] == 0x01)
      enter_dfu(DFU_MAGIC_OTA);
    else if (w->handle == ctrl_char.value_handle && w->len == 1 && w->data[0] == 0x02)
      enter_dfu(DFU_MAGIC_UART);
    break;
  }
  case BLE_GATTS_EVT_TIMEOUT:
  case BLE_GATTC_EVT_TIMEOUT:
    sd_ble_gap_disconnect(conn, BLE_HCI_REMOTE_USER_TERMINATED_CONNECTION);
    break;
  default:
    break;
  }
}

int main(void) {
  f33_status.resetreas = NRF_POWER->RESETREAS;   // boot cause (POR = 0, RESETPIN, SREQ…)
  NRF_POWER->RESETREAS = 0xFFFFFFFF;
  NRF_P0->OUTCLR = 1u << LED_PIN;
  NRF_P0->PIN_CNF[LED_PIN] = GPIO_PIN_CNF_DIR_Output << GPIO_PIN_CNF_DIR_Pos |
                             GPIO_PIN_CNF_INPUT_Disconnect << GPIO_PIN_CNF_INPUT_Pos;
  sensors_power_on();
  delay_us(1000000);   // r37: the sensors respond ~1 s after P0.06/P0.07 go high
  sensors_init();
  flash();
  stack_init();
  gap_init();
  gatt_init();
  adv_init();
  adv_start();
  uart_init();
  uart_poll_master();
  timer_start();
  for (;;) {
    for (;;) {
      uint16_t len = sizeof evt_buf;
      if (sd_ble_evt_get((uint8_t *)evt_buf, &len) != NRF_SUCCESS) break;
      on_ble((const ble_evt_t *)evt_buf);
    }
    uint32_t soc_evt;
    while (sd_evt_get(&soc_evt) == NRF_SUCCESS) {}
    if (second) {
      second = false;
      uart_poll_master();
      f33_status.uart_dropped = uart_dropped;
    }
    if (tick) { tick = false; measure_and_publish(); }   // r45c: also without a connection
    uart_service();
    sd_app_evt_wait();
  }
}
