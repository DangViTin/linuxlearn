---
chapter: 51A
title: Watchdog
part: VI — Driver development (supplementary v1.2)
estimated_pages: 12
status: draft
---

# Chapter 51A — Watchdog

> **What:** the **watchdog subsystem** — `/dev/watchdog`, the `watchdog_device` framework, and the user-space pattern (`systemd-watchdog` or a hand-written keepalive daemon) that reset the hardware timer periodically. If the timer ever expires, the SoC's watchdog peripheral resets the system. By the end you have a system that recovers automatically from any kernel hang or stuck application.
> **Why:** every product shipped to a customer needs this. A kernel oops on an unrelated subsystem, a deadlock in your driver, a CPU stuck in a tight infinite loop in user-space — without a watchdog, that's a brick that needs a power-cycle by hand. With one, the device reboots within seconds, logs the event, and is back in service. Watchdog handling is the difference between "this product is reliable" and "this product is not."
> **Focus:** **the keepalive contract**. Some user-space process *must* write to `/dev/watchdog` (or call the right ioctl) before the timer expires, forever. If that process dies, hangs, or gets stuck on disk I/O, the watchdog fires and the system resets. Picking *which* process should hold this responsibility — and what "alive" means to it — is the design decision.

## 51A.1  Hardware vs software watchdog

Two kinds exist:

**Hardware watchdog** — a SoC peripheral or external IC. Independent of the CPU. Counts down a register; on zero, asserts the system's RESET signal. Survives kernel hangs because it's not running kernel code. i.MX6ULL has two: WDOG1 and WDOG2 (in SNVS). External ICs like TPS3823, MAX6369 provide an even more independent watchdog (someone else's silicon, on a separate power rail).

**Software watchdog** (`softdog` module) — a kernel timer-based watchdog. Useful for testing but useless against a kernel that's truly stuck (the timer is part of the kernel that hung). Don't ship products with only softdog.

**Always use a hardware watchdog in production.** Use softdog only for dev-host testing.

## 51A.2  Enable WDOG1 in DT

```dts
&wdog1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_wdog>;
    fsl,ext-reset-output;
    status = "okay";
};
```

`fsl,ext-reset-output` exports the WDOG_B pin so an external chip (PMIC) can react to the reset. Required if your PMIC supplies CPU power and needs an explicit reset signal.

The driver is `imx2_wdt` (mainline). Once enabled, `/dev/watchdog` appears (also `/dev/watchdog0`).

## 51A.3  The user-space ioctl interface

`/dev/watchdog` follows the legacy "any write keeps it alive" convention plus a richer ioctl interface:

```c
#include <linux/watchdog.h>

int fd = open("/dev/watchdog", O_WRONLY);

/* Configure timeout */
int timeout = 30;
ioctl(fd, WDIOC_SETTIMEOUT, &timeout);

/* Get current timeout */
ioctl(fd, WDIOC_GETTIMEOUT, &timeout);

/* Keepalive */
ioctl(fd, WDIOC_KEEPALIVE, NULL);
/* equivalently: */
write(fd, "x", 1);

/* Disarm (gracefully — driver-dependent) */
ioctl(fd, WDIOC_SETOPTIONS, &(int){ WDIOS_DISABLECARD });

/* On close: by default, the watchdog stays armed → reset after timeout
 * unless your kernel is built with CONFIG_WATCHDOG_NOWAYOUT=n and you write "V" */
write(fd, "V", 1);    /* "magic close" — disable watchdog on close */
close(fd);
```

**Magic close**: if `CONFIG_WATCHDOG_NOWAYOUT=y` (default on most distros), once `/dev/watchdog` is opened, it cannot be safely closed — closing without the magic "V" character first leaves it armed; closing with "V" disables it. This prevents a buggy daemon from accidentally disabling the watchdog by exiting.

For production builds, leave `NOWAYOUT=y` — your keepalive process is supposed to live forever; if it dies, you *want* the watchdog to fire.

## 51A.4  Picking a keepalive process

Three common patterns:

### Pattern A — systemd's built-in watchdog

If you use systemd, the simplest answer is `WatchdogSec` in your unit files. The PID 1 systemd opens `/dev/watchdog`, sets the timeout, and the kernel resets unless systemd itself keeps writing.

```ini
[Service]
ExecStart=/usr/bin/my-app
WatchdogSec=30s
Restart=always
```

The unit becomes responsible: it must call `sd_notify(0, "WATCHDOG=1")` periodically; if it doesn't, systemd assumes the unit is hung and restarts it. systemd as a whole is hung → kernel resets.

Layered watchdog: hardware → systemd → application. Each layer protects the layer above.

### Pattern B — busybox `watchdog` daemon

For non-systemd setups, BusyBox has a `watchdog` command:

```sh
# In /etc/init.d/rcS or equivalent:
/sbin/watchdog -t 5 /dev/watchdog
```

`-t 5` says "feed every 5 seconds." It runs forever, writing to `/dev/watchdog`. Simple but dumb — it only checks if `watchdog` itself is running; it can't tell if the application is hung.

### Pattern C — application-aware feeder

Better: a tiny daemon that periodically checks the application is healthy, then feeds the watchdog. "Healthy" might mean: pings reachable, /proc/<pid>/status is "S" not "D", a heartbeat counter in shared memory advances.

```c
while (1) {
    if (app_is_healthy()) {
        write(wdfd, "x", 1);
    }
    sleep(5);
}
```

This catches the case where the application is *running* but stuck — perhaps in a deadlock or infinite loop — which dumb keepalive misses.

## 51A.5  What to do with watchdog reset events

A reset by watchdog should be **observable** so you can debug. Two mechanisms:

1. **Boot-reason register.** Most SoCs (including i.MX6ULL via SRC_SRSR) record why the system reset. On boot, `imx2_wdt` reads this and reports via `dmesg` / `/proc/sys/kernel/last_reboot_reason` if available.
2. **Persistent log on reset.** Use a `pstore` / `ramoops` region — a small chunk of DRAM marked "preserved across warm reset" — to save kernel oops and console buffer. On the next boot, the recovered data lives in `/sys/fs/pstore/`.

```dts
reserved-memory {
    #address-cells = <1>;
    #size-cells = <1>;
    ranges;

    ramoops@9c000000 {
        compatible = "ramoops";
        reg = <0x9c000000 0x100000>;     /* 1 MB */
        record-size  = <0x4000>;
        console-size = <0x4000>;
        ftrace-size  = <0x0>;
    };
};
```

After a watchdog reset, `ls /sys/fs/pstore/` shows `dmesg-ramoops-N`, `console-ramoops-N` — the last KB of dmesg before the hang. Worth its weight in gold for debugging field failures.

## 51A.6  Writing a watchdog driver (for completeness)

If you ever needed to support a chip not in mainline:

```c
#include <linux/watchdog.h>

static int my_wdt_start(struct watchdog_device *wdd) { /* enable HW */ }
static int my_wdt_stop(struct watchdog_device *wdd)  { /* disable HW */ }
static int my_wdt_ping(struct watchdog_device *wdd)  { /* feed timer */ }
static int my_wdt_set_timeout(struct watchdog_device *wdd, unsigned int t) { /* program timeout */ }

static const struct watchdog_ops my_wdt_ops = {
    .owner = THIS_MODULE,
    .start = my_wdt_start,
    .stop  = my_wdt_stop,
    .ping  = my_wdt_ping,
    .set_timeout = my_wdt_set_timeout,
};

static const struct watchdog_info my_wdt_info = {
    .options = WDIOF_SETTIMEOUT | WDIOF_KEEPALIVEPING | WDIOF_MAGICCLOSE,
    .identity = "my watchdog",
};

/* In probe: */
struct watchdog_device *wdd = devm_kzalloc(...);
wdd->ops = &my_wdt_ops;
wdd->info = &my_wdt_info;
wdd->min_timeout = 1;
wdd->max_timeout = 128;
wdd->timeout = 30;
watchdog_set_drvdata(wdd, priv);

return devm_watchdog_register_device(&pdev->dev, wdd);
```

The core handles `/dev/watchdog`, ioctls, and sysfs. You just implement the four ops.

## 51A.7  Lab

1. **Enable the i.MX2 watchdog in your DT.** Verify `/dev/watchdog` exists; `cat /sys/class/watchdog/watchdog0/status`.
2. **Write a minimal keepalive daemon.** Open `/dev/watchdog`, set 10 s timeout, `WDIOC_KEEPALIVE` every 5 s. Then `kill -9` the daemon; verify the system resets 10 s later.
3. **Set up ramoops.** Reserve memory, enable the `ramoops` driver. After a forced watchdog reset, find the saved dmesg in `/sys/fs/pstore/`.
4. **Application-aware feeder.** Write a feeder that watches a "heartbeat file" updated by your app every 2 s. If the file is stale by > 30 s, stop feeding the watchdog (and let the system reset).
5. **systemd integration.** Convert the feeder to a systemd unit with `WatchdogSec=`. Use `sd_notify(0, "WATCHDOG=1")` from your code.
6. **External watchdog IC.** Optional — wire up a TPS3823 with a GPIO output as the reset trigger; feed it from your driver. Compare against the on-chip watchdog.

## 51A.8  Pitfalls

- **`CONFIG_WATCHDOG_NOWAYOUT=n` in production.** A buggy daemon `close()`s the device → watchdog disabled → product hangs forever. Always `=y` in shipped kernels.
- **Forgetting to feed during heavy I/O.** If your keepalive process gets stuck on disk I/O (D state), it can't feed. Worst case: watchdog fires during normal operation. Tune timeout to be longer than longest expected I/O burst.
- **Pre-init watchdog**. The bootloader (U-Boot) can start the watchdog before the kernel boots. If the kernel takes longer to boot than the timeout, watchdog fires during boot. Either U-Boot disables it before jumping, or kernel takes over fast.
- **Multiple processes opening `/dev/watchdog`.** First open arms it; later opens get -EBUSY (in most drivers). Stick to one feeder process.
- **Watchdog during suspend.** Suspended kernel can't feed. Most watchdog drivers stop the timer on suspend automatically; verify your specific driver's behavior.
- **Pretty short timeouts.** A 2-second timeout has no slack for slow user-space ops. 30 seconds is a saner default. Some products use 5–10 minutes (high-availability gear with long expected blocking ops).
- **Forgetting ramoops region from kernel cmdline.** `mem=...` cuts off the reserved area. Tune carefully so ramoops's physical address is *inside* the visible-to-kernel memory map.

## 51A.9  Going deeper

- **`Documentation/watchdog/`** — the watchdog subsystem documentation.
- **`drivers/watchdog/imx2_wdt.c`** — i.MX2/3/5/6/7 watchdog driver. ~300 lines.
- **`Documentation/admin-guide/ramoops.rst`** — ramoops setup and usage.
- **`Documentation/admin-guide/pstore-blk.rst`** — pstore on block devices for systems with non-volatile storage but no preserved RAM.
- **`man systemd.service` → `WatchdogSec`** — the systemd-watchdog integration.

> Next chapter: **Chapter 51B — Power management.** Runtime PM, DVFS, suspend/resume. Watchdog + PM interact: a suspended system isn't feeding the watchdog, so PM must coordinate the watchdog driver's behavior.
