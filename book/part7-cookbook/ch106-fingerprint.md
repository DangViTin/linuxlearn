---
chapter: 106
title: Fingerprint sensors (R503, FPM10A, AS608, GT-521F)
part: VII — Device cookbook
estimated_pages: 12
status: draft
---

# Chapter 106 — Fingerprint sensors

> **What:** **standalone fingerprint modules** that do the imaging + matching internally and expose a UART command protocol. **Grow R503** (capacitive, ring-LED indicator, the modern favorite), **FPM10A / AS608** (optical, classic, cheap), **GT-521F** (capacitive, larger sensor area). This chapter also covers the libfprint path for USB fingerprint scanners — the laptop-style readers. On the i.MX6ULL we wire R503 to UART, walk the proprietary 9-byte command framing protocol, enroll a template, perform a 1:N match, store templates in flash, and integrate with PAM for "password + fingerprint" 2-factor login.
>
> **Why:** Fingerprint is the dominant biometric for low-friction access control. Face recognition has privacy and enrolment problems; iris is expensive. UART modules are *self-contained matchers* — you don't deal with raw image processing, template extraction, or the messy algorithms. You enroll, you match, you get a yes/no + template ID. Common applications: smart locks, time-and-attendance kiosks, equipment-checkout terminals, secure-area entry. On Linux, plug the module's UART into the i.MX6ULL, write a 300-line driver, and you have biometric auth.
>
> **Focus:** modules are stateful — they remember which template ID is enrolled in which slot, and protocol commands operate on that state. Enrollment is a three-step sequence: capture image 1, capture image 2, combine into template, store at chosen ID. Matching is one command: capture, compare to all stored, return ID + score. The framing protocol is trivial (header + length + cmd + data + checksum), but the **state model** (which template is at slot N, what happens if you re-enroll into an occupied slot, how power-cycle affects state) is where most integrations fail.
>
> **Tooling.** This chapter uses Just a UART terminal (`picocom`); the PAM 2FA lab needs `libpam-dev` to build a custom PAM module.
> - **Ubuntu-base (target):** `apt install picocom libpam0g-dev`
> - **Buildroot:** `BR2_PACKAGE_PICOCOM=y BR2_PACKAGE_LINUX_PAM=y`
> - Full per-tool reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).

## 106.1  Module comparison

| | Grow R503 | FPM10A / AS608 | GT-521F32 |
|---|---|---|---|
| Sensor type | capacitive | optical | capacitive |
| Sensor area | 21.5 mm dia | 14 × 18 mm | 16 × 16 mm |
| Resolution | 508 DPI | 508 DPI | 450 DPI |
| Template storage | 200 templates | 162 (FPM10A) / 1000 (AS608) | 200 |
| Match time | ~1.2 s | ~1.0 s | ~1.5 s |
| FAR (false accept) | < 0.001 % | < 0.001 % | < 0.001 % |
| FRR (false reject) | < 1 % | < 2 % | < 1 % |
| Interface | UART (TTL 3.3 V) | UART (TTL 3.3 V or 5 V) | UART |
| LED ring | yes (RGB, programmable) | no | no |
| Cost (module) | $25–35 | $10–18 | $20–30 |
| Form factor | round button | flat sensor + PCB | flat module |

**Pick guide:**
- **R503** — for any consumer-facing product. The capacitive sensor is dirt/wet-tolerant; the LED ring gives user feedback (red = denied, green = approved, blue = scanning). Choose the R503 when the product needs a polished user experience.
- **AS608** — when BOM matters and the form factor allows an optical sensor (which can't get wet). Bigger storage (1000 templates) than R503.
- **GT-521F** — for cases where you need a flat panel sensor (door reader behind a 1 mm glass).

## 106.2  Wiring an R503 to the i.MX6ULL

R503 has a 6-wire cable: VCC, GND, TX, RX, IRQ, 3V3_TOUCH_OUT.

```
       ┌────────┐                              ┌──────────┐
i.MX  ─┤ TXD    ├──────────────────────────────┤ RX       │
UART5  │ RXD    ├──────────────────────────────┤ TX       │  R503
GPIO  ─┤ IRQ in ├──────────────────────────────┤ IRQ out  │  (asserts when finger touched)
       │        │   3.3 V ──────────────────── ┤ VCC      │
       │        │   GND ──────────────────────  ┤ GND      │
       │        │   3.3 V ──────────────────── ┤ 3V3_TOUCH│  (LED ring power)
       └────────┘                              └──────────┘
```

The IRQ pin (active high) goes high when a finger touches the sensor. Wire to a GPIO and you can wake the i.MX6ULL from sleep on touch — critical for battery-powered locks.

## 106.3  The packet framing protocol

All commands use the same frame:

```
   [Header MSB] [Header LSB] [Address 4 bytes] [Packet ID] [Length MSB] [Length LSB] [Data...] [Sum MSB] [Sum LSB]
       0xEF         0x01     0xFF 0xFF 0xFF 0xFF     ID         N             N         payload    checksum
```

- **Header** — fixed `0xEF01`.
- **Address** — module address; default `0xFFFFFFFF` (broadcast); can be changed.
- **Packet ID** — frame type:
  - `0x01` = command
  - `0x02` = data (multi-part follow-up)
  - `0x07` = ack/response from module
  - `0x08` = end-of-data
- **Length** — payload + checksum length in bytes.
- **Data** — first byte is the command code; rest is command-specific payload.
- **Checksum** — sum of bytes from Packet ID to last data byte, modulo 65536.

Example: `GetImg` command (capture an image of the finger on the sensor):

```
  EF 01  FF FF FF FF  01  00 03  01  00 05
   ↑       ↑           ↑     ↑    ↑    ↑
  hdr   address       cmd  len=3 GetImg checksum
```

Response (success):

```
  EF 01  FF FF FF FF  07  00 03  00  00 0B
                       ↑     ↑    ↑    ↑
                     ack  len=3 OK   checksum
```

Confirmation codes:
- `0x00` = success
- `0x01` = packet error
- `0x02` = no finger
- `0x03` = failed to enroll
- `0x07` = template generation fail (too few features)
- `0x09` = no match (1:1 verify)
- `0x0A` = no template found (1:N search)

Key commands:

| Hex | Name | Purpose |
|---|---|---|
| 0x01 | GetImg | capture image from sensor |
| 0x02 | GenChar | extract feature template from image, into char buffer 1 or 2 |
| 0x05 | RegModel | combine char buffers 1+2 into a template |
| 0x06 | Store | store template in flash at PageID |
| 0x07 | LoadChar | load template from flash into char buffer |
| 0x04 | Search | match char buffer against all stored, return PageID + score |
| 0x1A | Match | compare char buffers 1 and 2 (1:1 verify) |
| 0x35 | AuraLedConfig | R503-only: configure LED ring (color, mode) |
| 0x17 | ReadTemplateIndex | bitmap of which slots have stored templates |
| 0x0C | DeleteChar | delete templates in a range |
| 0x0D | Empty | wipe all templates |

## 106.4  Enrollment — the 3-step dance

```
   1. GetImg                  ← user puts finger on sensor
   2. GenChar(buffer=1)       ← extract features → char buffer 1
   3. (user lifts finger, AT-LEAST-200-MS-pause, presses again)
   4. GetImg                  ← capture again
   5. GenChar(buffer=2)       ← extract features → char buffer 2
   6. RegModel                ← combine buffers 1+2 into a robust template
   7. Store(slot=N)           ← persist to flash at slot N
```

Double-capture improves robustness. Fingerprints do not sample identically each time, so the union of two captures gives better matching tolerance. Some implementations capture 3 times for even better quality (look for FPM10A's `Enroll` shortcut command that does it all in one).

If GenChar returns "too few features," the user's finger was wet, dirty, or off-center; retry.

## 106.5  Matching — 1:N search

```
   1. GetImg                  ← user puts finger
   2. GenChar(buffer=1)
   3. Search(buffer=1, start=0, count=200)
       → returns PageID (slot) + Score, or "no match"
```

Score is 0..2000 (higher = better match); the chip's threshold is typically 50 — above that, declare a match. Tune for FAR/FRR trade-off.

## 106.6  From scratch — R503 driver in C

r503.c (compressed):

```c
/* Minimal R503 fingerprint driver.
 * Commands: enroll, search, delete, list.
 */
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <termios.h>
#include <unistd.h>

static int uart_fd;

static int send_pkt(uint8_t pid, const uint8_t *data, int n) {
    uint8_t hdr[9] = {
        0xEF, 0x01,                                  /* header */
        0xFF, 0xFF, 0xFF, 0xFF,                      /* address */
        pid,                                          /* packet id */
        (n + 2) >> 8, (n + 2) & 0xFF,                /* length */
    };
    uint16_t sum = pid + ((n + 2) >> 8) + ((n + 2) & 0xFF);
    for (int i = 0; i < n; i++) sum += data[i];
    write(uart_fd, hdr, 9);
    write(uart_fd, data, n);
    uint8_t tail[2] = { sum >> 8, sum & 0xFF };
    return write(uart_fd, tail, 2);
}

static int recv_pkt(uint8_t *data_out, int maxlen) {
    uint8_t hdr[9];
    /* Read until we have a valid header */
    for (int i = 0; i < 9; ) {
        int n = read(uart_fd, &hdr[i], 9 - i);
        if (n <= 0) return -1;
        i += n;
    }
    if (hdr[0] != 0xEF || hdr[1] != 0x01) return -2;
    uint16_t len = (hdr[7] << 8) | hdr[8];
    if (len < 2 || len > maxlen + 2) return -3;
    uint8_t payload[256];
    for (int i = 0; i < len; ) {
        int n = read(uart_fd, &payload[i], len - i);
        if (n <= 0) return -4;
        i += n;
    }
    /* Verify checksum (skipped for brevity in this listing) */
    memcpy(data_out, payload, len - 2);
    return len - 2;        /* returns payload (incl confirm byte) */
}

static int cmd(uint8_t op, const uint8_t *args, int argc, uint8_t *resp, int max) {
    uint8_t buf[256];
    buf[0] = op;
    if (args) memcpy(&buf[1], args, argc);
    send_pkt(0x01, buf, argc + 1);
    return recv_pkt(resp, max);
}

/* High-level operations */
static int get_img(void) {
    uint8_t r[16];
    return (cmd(0x01, NULL, 0, r, sizeof r) > 0) ? r[0] : -1;
}
static int gen_char(int buf_num) {
    uint8_t a = buf_num, r[16];
    return (cmd(0x02, &a, 1, r, sizeof r) > 0) ? r[0] : -1;
}
static int reg_model(void) {
    uint8_t r[16];
    return (cmd(0x05, NULL, 0, r, sizeof r) > 0) ? r[0] : -1;
}
static int store(int slot) {
    uint8_t a[3] = { 0x01, slot >> 8, slot & 0xFF }, r[16];
    return (cmd(0x06, a, 3, r, sizeof r) > 0) ? r[0] : -1;
}
static int search(int *out_slot, int *out_score) {
    uint8_t a[5] = { 0x01, 0x00, 0x00, 0x00, 0xC8 }, r[16];   /* buf=1, start=0, count=200 */
    int n = cmd(0x04, a, 5, r, sizeof r);
    if (n < 5) return -1;
    if (r[0] != 0x00) return r[0];
    *out_slot = (r[1] << 8) | r[2];
    *out_score = (r[3] << 8) | r[4];
    return 0;
}

static int enroll(int slot) {
    printf("Place finger...\n");
    while (get_img() != 0) usleep(100000);
    if (gen_char(1) != 0) return -1;
    printf("Lift finger, place again...\n");
    sleep(1);
    while (get_img() != 0) usleep(100000);
    if (gen_char(2) != 0) return -1;
    if (reg_model() != 0) return -1;
    return store(slot);
}

int main(int argc, char **argv) {
    uart_fd = open("/dev/ttymxc4", O_RDWR | O_NOCTTY);
    struct termios tio;
    tcgetattr(uart_fd, &tio);
    cfsetspeed(&tio, B57600);
    cfmakeraw(&tio);
    tcsetattr(uart_fd, TCSANOW, &tio);

    if (argc > 1 && strcmp(argv[1], "enroll") == 0) {
        int slot = atoi(argv[2]);
        if (enroll(slot) == 0) printf("Enrolled at slot %d\n", slot);
        else printf("Enroll failed\n");
    } else {
        printf("Place finger to identify...\n");
        for (;;) {
            if (get_img() != 0) { usleep(100000); continue; }
            if (gen_char(1) != 0) { printf("Bad image, retry\n"); sleep(1); continue; }
            int slot, score;
            int r = search(&slot, &score);
            if (r == 0) printf("Match: slot=%d score=%d\n", slot, score);
            else printf("No match\n");
            sleep(2);
        }
    }
}
```

What this exposes:

- The framing protocol's checksum, length, header — easy to get wrong with no error messages.
- The two-stage capture for enrollment.
- The 0x0X confirmation codes that distinguish "no finger" from "too few features" from "match found."
- Why the matching is *fast* (the chip's internal DSP does the convolution) but *async* (a 1.2 s wall-clock for capture + extract + search).

## 106.7  PAM integration — 2-factor login

For "password + fingerprint" 2FA, write a small PAM module that calls into your R503 driver:

```c
/* /lib/security/pam_r503.so */
PAM_EXTERN int pam_sm_authenticate(pam_handle_t *pamh, int flags, ...) {
    /* Open R503, capture, search */
    int slot, score, rc = r503_authenticate(&slot, &score);
    if (rc != 0 || score < 50) return PAM_AUTH_ERR;
    /* Check slot is allowed for this user */
    const char *user;
    pam_get_user(pamh, &user, NULL);
    if (!is_user_authorized(user, slot)) return PAM_AUTH_ERR;
    return PAM_SUCCESS;
}
```

`/etc/pam.d/sshd`:

```
auth required pam_unix.so       try_first_pass
auth required pam_r503.so
account required pam_unix.so
```

Now SSH (or any PAM-using service) requires password + fingerprint.

## 106.8  libfprint — for USB fingerprint scanners

If you have a laptop-style USB fingerprint reader (Validity, Synaptics, Goodix), the kernel side is `libusb` user-space; `libfprint` provides the protocol drivers. Used by `fprintd` daemon and GNOME/KDE settings.

```sh
apt install fprintd libfprint-2-2
fprintd-enroll username
fprintd-verify username
```

This is a different ecosystem from the embedded UART modules. Choose based on form factor and integration needs.

## 106.9  Lab

1. **R503 UART up.** Wire to UART; baud 57600 default. Send `AT+VFY-PWD` (system-handshake; alias for "command 0x13 verify password" with default `0x00000000`). Verify ACK.
2. **Enroll 3 fingers.** Slots 1, 2, 3 — different real fingers (or same finger from different angles).
3. **1:N search.** Touch a finger; should match its enrolled slot with score > 100.
4. **Try unenrolled finger.** Should return "no match."
5. **LED feedback.** Configure aura LED via `AuraLedConfig`: red=denied, green=approved, blue=scanning. Tie into your matching loop.
6. **Touch-interrupt wake.** Wire the R503's IRQ to a GPIO. Sleep the i.MX6ULL; touch the sensor; verify wake-from-suspend.
7. **Template export/import.** Use `UpChar` and `DownChar` commands to upload a template to the host and back. Stores templates per-user in `/var/lib/myapp/`.
8. **PAM 2FA (stretch).** Write `pam_r503.so`; configure `sshd` to require fingerprint after password. Test SSH login from another machine.
9. **Hostile re-enroll detection.** What happens if an attacker tries to enroll their finger over your slot 0? The chip will replace it silently. Add a server-side flag that requires admin re-confirmation for any enroll/delete operation.

## 106.10  Pitfalls

- **Wrong baud rate.** Default 57600 on R503; some clones default to 9600. Try both; some modules persist whatever was last set.
- **First-scan warmup.** Optical sensors (FPM10A) need ~500 ms warmup after power-on; the first 2–3 scans may give "no finger detected" even when present.
- **Wet fingers on optical.** Optical sensors fail with wet, dirty, or smudged fingers; capacitive (R503) is much more tolerant. If your product deploys outdoors, choose capacitive.
- **Sensor surface scratched.** A single deep scratch on the optical sensor's prism creates a permanent "fake fingerprint" everyone matches. Replace the module.
- **Power supply noise.** Some modules are picky about VCC ripple > 50 mV; add an LC filter on the supply.
- **Template format incompatibility.** R503 templates are not interchangeable with FPM10A; each vendor's algorithm produces a different template format. Don't try to migrate.
- **Slot overwrite on re-enroll.** `Store(slot=N)` silently overwrites the previous template at slot N. Use `ReadTemplateIndex` first to check.
- **Score threshold tuning.** Default 50; too low = false accepts, too high = false rejects. Tune for your application's FAR/FRR balance.
- **Privacy / GDPR.** Fingerprint templates are biometric PII in many jurisdictions. Store encrypted; allow deletion; document the retention policy.
- **Aging.** Skin changes with age; templates may need re-enrollment every ~5 years for older users.

## 106.11  Going deeper

- **Grow R503 User Manual** — protocol spec, all commands, error codes.
- **AS608 User Manual** — slightly different command set but similar architecture.
- **`libfprint`** + **`fprintd`** for USB scanners.
- **PAM Programming Guide** for writing custom auth modules.
- **ISO/IEC 19794-2** — fingerprint template interchange format (if you need cross-vendor portability).
- **NIST Fingerprint Image Quality (NFIQ)** — the standard quality score; some R503 firmware versions expose it.
- **Ch 105 (RFID)** — RFID + fingerprint is the classic 2-factor combination for high-security access control.

---

> Next chapter: **Chapter 107 — GPS/GNSS + PPS time sync** — u-blox + gpsd + chrony for sub-µs NTP.
