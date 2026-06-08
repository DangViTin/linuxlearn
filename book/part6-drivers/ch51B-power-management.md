---
chapter: 51B
title: Power management
part: VI — Driver development (supplementary v1.2)
estimated_pages: 18
status: draft
---

# Chapter 51B — Power management
**regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.
MCU bridge: Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.

> **What:** Linux's three power-management layers — **runtime PM** (drivers autonomously gate clocks and rails when idle), **DVFS** (CPU frequency-and-voltage scaling under load) and **system sleep** (suspend-to-RAM / standby / hibernation). By the end your driver participates in runtime PM, the system suspends to RAM cleanly, and the CPU clocks down when idle.
>
> **Why:** On battery-powered products, PM tuning is a large fraction of the work. Saving 50 mA in idle means 5× battery life on a 1 Ah cell. For mains-powered embedded, it's still meaningful: less heat, smaller heatsinks, lower fan noise. Linux's PM framework is rich and *opt-in* — drivers that don't implement it don't suspend. The whole device fails to enter suspend until you fix them.
>
> **Focus:** **the three layers are mostly independent**. Runtime PM is "this peripheral is idle. gate its clock now." DVFS is "the CPU isn't busy. scale to 396 MHz." System sleep is "the user pressed the suspend button. stop everything safely, resume on a wake source." Implement them one at a time. don't tangle them up.


## 51B.1  Runtime PM

Runtime PM is the kernel's automatic per-device idle/active state machine. Each device has an idle and an active state. The framework counts users with a refcount. When the refcount hits zero it calls `runtime_suspend`. When it goes from zero to one it calls `runtime_resume`.

```c
#include <linux/pm_runtime.h>

static int my_runtime_suspend(struct device *dev)
{
    struct my_priv *p = dev_get_drvdata(dev);
    clk_disable_unprepare(p->clk);    /* gate the clock */
    regulator_disable(p->vcc);         /* drop the rail */
    return 0;
}

static int my_runtime_resume(struct device *dev)
{
    struct my_priv *p = dev_get_drvdata(dev);
    int err = regulator_enable(p->vcc);
    if (err) return err;
    return clk_prepare_enable(p->clk);
}

static const struct dev_pm_ops my_pm_ops = {
    SET_RUNTIME_PM_OPS(my_runtime_suspend, my_runtime_resume, NULL)
};

static struct platform_driver my_driver = {
    .driver = {
        .name = "my-driver",
        .pm   = &my_pm_ops,
    },
    /* ... */
};

/* In probe: */
pm_runtime_set_autosuspend_delay(&pdev->dev, 1000);  /* 1 s after last use */
pm_runtime_use_autosuspend(&pdev->dev);
pm_runtime_enable(&pdev->dev);

/* In your hot path (read/write/IRQ handler entry): */
pm_runtime_get_sync(&pdev->dev);     /* wakes if suspended; bumps refcount */
do_the_work();
pm_runtime_mark_last_busy(&pdev->dev);
pm_runtime_put_autosuspend(&pdev->dev);
```

Sequence:

1. Driver calls `pm_runtime_get_sync` before using the device. If already runtime-active, this just bumps the refcount. If suspended, it calls `runtime_resume` first, then bumps.
2. Driver does work.
3. Driver calls `pm_runtime_mark_last_busy` + `pm_runtime_put_autosuspend`. The refcount drops. When it hits zero, after the autosuspend delay (1 s here), `runtime_suspend` runs.

The result: between bursts of use, the device's clock is gated and rail is dropped, automatically. No user-space involvement.

Inspect from sysfs:
**sysfs** - a kernel-generated filesystem under /sys that exposes devices, drivers, and attributes.

```
[root@pa-mini:~]# cat /sys/devices/platform/.../power/runtime_status
suspended
[root@pa-mini:~]# cat /sys/devices/platform/.../power/runtime_active_time
12345
[root@pa-mini:~]# cat /sys/devices/platform/.../power/runtime_suspended_time
876543
```

## 51B.2  DVFS — CPU frequency scaling

The i.MX6ULL CPU can run at 396, 528, or 696 MHz. Higher frequency = more performance + more power. lower = the reverse. **DVFS** (Dynamic Voltage and Frequency Scaling) picks the frequency dynamically based on load.

CPU operating points in DT:

```dts
&cpu0 {
    operating-points-v2 = <&cpu0_opp_table>;
    cpu-supply = <&reg_arm>;
};

cpu0_opp_table: opp-table {
    compatible = "operating-points-v2";

    opp-396000000 {
        opp-hz = /bits/ 64 <396000000>;
        opp-microvolt = <1125000>;
    };
    opp-528000000 {
        opp-hz = /bits/ 64 <528000000>;
        opp-microvolt = <1175000>;
    };
    opp-696000000 {
        opp-hz = /bits/ 64 <696000000>;
        opp-microvolt = <1275000>;
    };
};
```

Each OPP is a frequency + the voltage required to run at that frequency. The DVFS framework reads this table, picks an OPP, and applies the change. When raising the clock, the regulator goes up first, then the clock. when lowering, the reverse. This ensures the CPU is always supplied with enough voltage for its current speed.

User-space pick the **governor** (the algorithm that decides when to scale):

```
[root@pa-mini:~]# cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors
performance powersave userspace ondemand conservative schedutil

[root@pa-mini:~]# cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
schedutil

[root@pa-mini:~]# echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
[root@pa-mini:~]# cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
696000
```

Governors:
- **performance** — always max frequency. Lowest latency.
- **powersave** — always min frequency. Lowest power.
- **schedutil** — modern default. uses scheduler hints (utilisation) to scale.
- **ondemand** — older. reacts to CPU load.
- **conservative** — slower-reacting version of ondemand.

For embedded products, `schedutil` is almost always right. Performance for benchmarks, powersave for "device is on standby waiting for an event."

## 51B.3  System sleep — suspend-to-RAM

Three system-level sleep states (described in `/sys/power/state`):

- **freeze** — userspace frozen, devices left running. Lowest latency wake (microseconds), modest power savings.
- **standby** — devices suspended, CPU clock gated. Medium savings.
- **mem** — full suspend-to-RAM. RAM in self-refresh, CPU off, only PMIC and SoC suspend domain active. Lowest power, ~1–2 second wake latency.
MCU bridge: Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
**PMIC** - Power Management IC, a chip that sequences and regulates the board's voltage rails.

Trigger:

```
[root@pa-mini:~]# echo mem > /sys/power/state
```

The kernel:
1. Freezes all userspace processes (sends SIGSTOP-equivalent).
2. For each device (in topological order — leaves first), calls `pm_ops.suspend`. Drivers save state, gate clocks, idle hardware.
3. The CPU is parked. only the wakeup-capable peripherals remain powered.
4. A wakeup event fires (RTC alarm, GPIO IRQ, etc.).
MCU bridge: Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
5. Resume in reverse order: devices first, then userspace thaws.

For your driver to participate:

```c
static int my_suspend(struct device *dev)
{
    struct my_priv *p = dev_get_drvdata(dev);
    /* save any state that won't survive (chip registers via regmap_mark_dirty);
       gate clocks; tell the chip to enter low-power mode */
    return 0;
}

static int my_resume(struct device *dev)
{
    struct my_priv *p = dev_get_drvdata(dev);
    /* restore — typically by re-running probe-like init or regcache_sync(p->regmap) */
    return 0;
}

static const struct dev_pm_ops my_pm_ops = {
    SET_SYSTEM_SLEEP_PM_OPS(my_suspend, my_resume)
    SET_RUNTIME_PM_OPS(my_runtime_suspend, my_runtime_resume, NULL)
};
```

System-suspend callbacks run when user-space writes `mem` to `/sys/power/state`. Runtime-suspend callbacks run automatically when the device goes idle.

### Wakeup sources

For the system to wake from `mem`, *something* must be allowed to fire an IRQ in the suspended state. Configure via DT (`wakeup-source` boolean) and userspace:

```sh
[root@pa-mini:~]# echo enabled > /sys/class/wakeup/.../wakeup
[root@pa-mini:~]# cat /sys/power/wakeup_count    ← bumps each wake
```

Common wakeup sources: RTC alarm, USB plug, GPIO from button or sensor data-ready, network wake-on-LAN.

Set an RTC alarm wake:

```sh
[root@pa-mini:~]# echo $(($(date +%s) + 30)) > /sys/class/rtc/rtc0/wakealarm
[root@pa-mini:~]# echo mem > /sys/power/state
# … 30 s later, system wakes ...
```

## 51B.4  Measuring impact

You changed something to save power. how do you measure?

**External**: a USB current meter (e.g., USB Type-A inline meter) or a benchtop power analyzer at the SoC supply. Best for absolute numbers.

**Internal**: `/sys/class/power_supply/`, `INA226` driver readouts (Ch 75), or `powertop`:

```
[root@pa-mini:~]# powertop --time=10
Summary: 23.4 wakeups/second
       Usage    Events/s   Category   Description
        5.4%        0.0    Process    /usr/bin/myapp
        ...
```

`powertop` shows which userspace process is keeping the CPU awake. Goal: idle the device under test → see "kernel sleep" at 95%+. Wakeups should be < 10/sec at idle.

## 51B.5  The full optimisation playbook

The order of operations for "make this product 3× longer-lasting":

1. **Measure idle current.** Get a baseline number.
2. **Use `powertop`** to find spurious wakeups. Disable / tune.
3. **Enable runtime PM in all peripheral drivers.** Each one off saves a few mA.
4. **Configure DVFS to powersave when idle.** Or schedutil — let scheduler decide.
5. **Use `mem` suspend during long idle periods.** A few seconds of wake-up latency for a battery-life multiplier.
6. **Set wakeup-only inputs.** Don't poll sensors. let them IRQ on data-ready.
7. **Drop USB/Ethernet PHY power when unused.** `ip link set eth0 down` actually drops the PHY's clock.
**PHY** - physical-layer block or chip that converts digital MAC signals to electrical or radio signals.
**MAC** - Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.
8. **Compile out unused subsystems.** A smaller kernel boots faster, holds less in cache.

Each step saves a few mA. Together they take a 1 Ah cell from 4 hours to 4 days.

## 51B.6  Lab

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


1. **Add runtime PM to a driver.** Take your fastadc / I²C / SPI driver. Implement `runtime_suspend`/`resume`. Verify `/sys/.../power/runtime_status` shows `suspended` between accesses.
2. **DVFS sweep.** Run a CPU-heavy workload at each governor (`performance`, `powersave`, `schedutil`). Time the run and measure current. Build the trade-off curve.
3. **System suspend.** `echo mem > /sys/power/state` from console. wake via `wakealarm` set for 30 s. Verify devices come back up correctly.
4. **Catch a suspend failure.** Deliberately omit `regcache_sync` in resume. observe that the chip's config is wrong after wake. Add it back.
5. **`powertop` baseline.** Get powertop output at idle. Tune until wake-ups are < 5/s.
6. **Measure absolute current.** With a USB meter or INA219, record current at: 696 MHz busy, 396 MHz idle, suspended. Compare.

## 51B.7  Pitfalls

- **`pm_runtime_get_sync` from atomic context.** It may sleep waiting for resume. Use `pm_runtime_get` (async. Check status) instead.
- **Forgetting to enable runtime PM.** `pm_runtime_enable(dev)` must be called once at probe. Without it, all the get/put calls are no-ops.
- **Driver that never calls `pm_runtime_get/put`.** The device is permanently "active" from PM's view. runtime suspend never runs.
- **System suspend on a driver without suspend ops.** Kernel logs "noop_suspend" and proceeds, but your peripheral may be left in a bad state on resume. Always provide ops or use `pm_ptr` to inherit reasonable defaults.
- **Clock left enabled across suspend.** PMIC may try to drop rails while clock is still toggling, which can violate the chip's spec sheet. Order: gate clock first, then drop rail, on the way down. reverse on resume.
- **DVFS without proper regulator support.** If `cpu-supply` is wrong, the kernel may raise the clock before voltage settles. Execution becomes unreliable. Always specify `operating-points-v2` with matched microvolt entries.
- **Wakeup source enabled but `IRQ_TYPE_LEVEL_HIGH` instead of `IRQ_TYPE_EDGE`.** Some SoCs only wake on edge IRQs from certain banks. Confirm against datasheet.
- **`wakealarm` set in the past.** Kernel ignores. system suspends indefinitely. Always compute as `$(date +%s) + N`.

## 51B.8  Going deeper

- **`Documentation/power/`** — the entire PM kernel documentation.
- **`Documentation/power/runtime_pm.rst`** — runtime PM in depth.
- **`Documentation/admin-guide/pm/cpufreq.rst`** — CPU frequency scaling.
- **`drivers/cpufreq/imx6q-cpufreq.c`** — i.MX6 cpufreq driver.
- **`drivers/regulator/anatop-regulator.c`** — Anatop regulator driver used for CPU voltage on i.MX.
- **`powertop` source** — kernel.org. Read for inspiration on how to measure.
- **`Documentation/power/states.rst`** — sleep state semantics.

> Next chapter: **Chapter 52 — Network driver (FEC + KSZ8081 PHY).** With PM understood, we tackle a real-world driver: i.MX6ULL's FEC Ethernet MAC and the KSZ8081 PHY that completes the gigabit Ethernet stack on Point Atom boards.
