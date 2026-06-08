---
chapter: 43
title: Interrupts
part: VI — Driver development
estimated_pages: 22
status: draft
---

# Chapter 43 — Interrupts

> **What:** **`request_irq`**, the **top-half / bottom-half split**, and the four standard bottom halves — softirqs, tasklets, work queues, and threaded IRQs. By the end you'll have a driver that owns a hardware IRQ, acknowledges it in nanoseconds in the top half, and processes the event without blocking the rest of the kernel.
> **IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
>
> **Why:** interrupts are how hardware tells the kernel something happened: data arrived, DMA finished, a button was pressed, a timer expired. Get the IRQ-handler design wrong and you hit one of two failures: *missed interrupts* (handler too slow or wrong polarity) or *IRQ storms* (handler does not acknowledge, hardware re-asserts continuously, system hangs). The rules below give you the right design every time.
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
> **DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
>
> **Focus:** **the IRQ contract is "fast, atomic, and minimal."** Your top-half runs with interrupts disabled, in atomic context (no sleeping, no `kmalloc(GFP_KERNEL)`, no `copy_to_user`). Anything that takes more than a few microseconds *must* be deferred to a bottom half. Once you accept this constraint, the API choices below follow naturally.


## 43.1  How the i.MX6ULL gets an interrupt to your code

The chain, end to end:

```
   hardware peripheral (e.g., GPIO pin transition)
        │
        ▼
   peripheral IRQ output line
        │
        ▼
   GIC (Generic Interrupt Controller — Cortex-A IRQ multiplexer)
        │ assigns IRQ number (e.g., 99)
        ▼
   CPU's IRQ exception vector
        │
        ▼
   kernel's gic_handle_irq → generic_handle_irq(virq)
        │
        ▼
   IRQ domain mapping (DT-based) → your handler
        │
        ▼
   your_irq_handler(irq, dev_id) — runs with IRQ off
```

Two things to notice:

1. **IRQ numbers in DT and `request_irq` are virtual.** The DT line `interrupts = <0 99 IRQ_TYPE_LEVEL_HIGH>` carries the GIC hardware number. At boot, the kernel maps it to a virtual IRQ (a *virq*). Your `request_irq` uses this virq. You usually do not see the mapping happen — the framework hands you the virq.
2. **GIC is the multiplexer.** The CPU has one IRQ line. The GIC has up to ~160 inputs (i.MX6ULL specific) and figures out which is firing. The kernel's GIC driver demultiplexes and routes to your handler.

## 43.2  The top half

Your top half is the function the kernel calls when the IRQ fires. The contract:

- **It runs in atomic context.** No sleeping. No `kmalloc(GFP_KERNEL)`. No `mutex_lock`. No `copy_to_user`. No `printk` with `KERN_INFO` (well, `printk` works but is rate-limited. minimize).
- **It runs with that IRQ disabled.** The GIC won't re-fire the same IRQ on the same CPU until you return. (Other CPUs *can* see it. that's how SMP works.)
- **It runs with kernel preemption off.** No context switch until you return.
- **It returns `IRQ_HANDLED`** if it processed the IRQ, `IRQ_NONE` if not (used in shared-IRQ scenarios — "this wasn't mine").
- **It must acknowledge the hardware.** Otherwise the IRQ line stays asserted and the IRQ fires again immediately ⇒ IRQ storm ⇒ system hang.

A canonical top-half:

```c
static irqreturn_t my_irq_handler(int irq, void *dev_id)
{
    struct my_dev *dev = dev_id;
    u32 status;

    /* 1. Read status; figure out what fired */
    status = readl(dev->base + STATUS_REG);
    if (!(status & MY_IRQ_FLAG))
        return IRQ_NONE;          /* not for us — shared IRQ */

    /* 2. Acknowledge the hardware (write-1-clear pattern) */
    writel(MY_IRQ_FLAG, dev->base + STATUS_REG);

    /* 3. Capture minimal data; defer the rest */
    dev->raw_value = readl(dev->base + DATA_REG);
    dev->irq_count++;

    /* 4. Wake the bottom half (workqueue, tasklet, or wait queue) */
    queue_work(dev->wq, &dev->work);

    return IRQ_HANDLED;
}
```

Five lines of real work. Read status, ack, snapshot, defer, return. Under 1 µs on i.MX6ULL.

If your top-half is doing anything more than this — parsing protocol bytes, looking up tables, doing math — it's too long. Move it to a bottom half.

## 43.3  Requesting an IRQ

`#include <linux/interrupt.h>`

```c
int request_irq(unsigned int irq, irq_handler_t handler,
                unsigned long flags, const char *name, void *dev);

void free_irq(unsigned int irq, void *dev);
```

For platform drivers, the `irq` number comes from the DT via `platform_get_irq()`:

```c
int virq = platform_get_irq(pdev, 0);
if (virq < 0)
    return virq;

err = devm_request_irq(&pdev->dev, virq, my_irq_handler,
                        IRQF_TRIGGER_RISING | IRQF_ONESHOT,
                        "myhw", priv);
```

The `devm_request_irq` variant auto-frees on driver-unbind. Always prefer it.

### Flags

| Flag | Meaning |
|------|---------|
| `IRQF_TRIGGER_RISING` | Edge-triggered, rising edge |
| `IRQF_TRIGGER_FALLING` | Edge-triggered, falling edge |
| `IRQF_TRIGGER_HIGH` | Level-triggered, active high |
| `IRQF_TRIGGER_LOW` | Level-triggered, active low |
| `IRQF_SHARED` | Multiple handlers may share this IRQ line |
| `IRQF_ONESHOT` | Don't re-enable IRQ until threaded handler completes |
| `IRQF_NO_THREAD` | Force top-half-only (don't run as kernel thread) |

The trigger flag is **usually omitted** for platform drivers because the DT specifies it (in the `interrupts` property's third cell). The kernel's IRQ subsystem reads from DT.

## 43.4  Bottom halves — four choices

Top half done. Now you need to do the real work outside the atomic constraints. Four options, in order of "easiest" to "most flexible":

### 1. Threaded IRQ — the modern default

`request_threaded_irq` is the cleanest pattern: the kernel calls your *primary* (top-half) function with IRQs off, then schedules your *threaded* function as a kernel thread that runs with normal kernel context — can sleep, take mutexes, do `copy_to_user`, everything.

```c
static irqreturn_t my_primary(int irq, void *dev_id)
{
    struct my_dev *dev = dev_id;
    /* Read status, ack hw — atomic context */
    writel(...);
    return IRQ_WAKE_THREAD;
}

static irqreturn_t my_threaded(int irq, void *dev_id)
{
    struct my_dev *dev = dev_id;
    /* Process at leisure — full kernel context */
    mutex_lock(&dev->lock);
    /* ... */
    mutex_unlock(&dev->lock);
    wake_up(&dev->wq);
    return IRQ_HANDLED;
}

/* In probe: */
err = devm_request_threaded_irq(&pdev->dev, virq,
                                 my_primary, my_threaded,
                                 IRQF_TRIGGER_RISING | IRQF_ONESHOT,
                                 "myhw", priv);
```

The `IRQF_ONESHOT` flag is important: it keeps the IRQ masked from when the primary returns `IRQ_WAKE_THREAD` until the threaded handler completes. Without it, the IRQ could re-fire and re-schedule before you've finished processing.

You can pass `NULL` for the primary, in which case the kernel installs a default that just returns `IRQ_WAKE_THREAD`. Then your threaded handler is the only thing you wrote.

**Use threaded IRQ for ~80% of new driver code.** It's the cleanest model.

### 2. Work queues — explicit deferral

A work queue is a kernel thread that processes a queue of work items. Schedule a work item from your top-half. The work runs later in a normal kernel thread.

```c
#include <linux/workqueue.h>

static struct workqueue_struct *my_wq;
static struct work_struct my_work;

static void my_work_fn(struct work_struct *w)
{
    /* Runs in process context. Can sleep. */
    struct my_dev *dev = container_of(w, struct my_dev, work);
    /* Process accumulated data */
}

static irqreturn_t my_irq(int irq, void *dev_id)
{
    /* Top half */
    queue_work(my_wq, &my_work);
    return IRQ_HANDLED;
}

/* In probe */
my_wq = alloc_workqueue("myhw", WQ_UNBOUND, 0);
INIT_WORK(&my_work, my_work_fn);
```

For most drivers, the shared system workqueue is fine and you don't need to allocate your own:

```c
INIT_WORK(&my_work, my_work_fn);
/* In IRQ: */
schedule_work(&my_work);
```

**When to use work queues** over threaded IRQs:
- You want to *coalesce* multiple IRQs into one bottom-half execution (work is idempotent. queueing it again is a no-op if already queued).
- You don't want a dedicated kthread per IRQ.
- You're piggy-backing on existing workqueue infrastructure.

### 3. Tasklets — legacy

A tasklet runs in **softirq context** (atomic, can't sleep, but with all IRQs enabled). It's faster to schedule than a workqueue but lives in atomic context.

```c
#include <linux/interrupt.h>

/* Modern form (since v5.9): DECLARE_TASKLET(name, fn) where fn takes (struct tasklet_struct *).
 * DECLARE_TASKLET_OLD is the backward-compat macro for the legacy (unsigned long) callback shown
 * here. New drivers should prefer DECLARE_TASKLET — but better still, prefer workqueues
 * (tasklets are being phased out across the tree). */
static DECLARE_TASKLET_OLD(my_tasklet, my_tasklet_fn);

static void my_tasklet_fn(unsigned long data)
{
    /* Softirq context. Can't sleep. */
}

static irqreturn_t my_irq(int irq, void *dev_id)
{
    tasklet_schedule(&my_tasklet);
    return IRQ_HANDLED;
}
```

Tasklets are **discouraged** in new code. The kernel is migrating away from them — they're an obstacle for `PREEMPT_RT` (real-time kernel. Ch 52A). Use threaded IRQs unless you have a strong reason for atomic-context bottom-half processing.
**PREEMPT_RT** - the Linux real-time patch set that makes more kernel paths preemptible and reduces latency.

### 4. Softirqs — kernel-internal only

Softirqs are the lowest-level deferred mechanism. Used internally for networking, timers, and block-I/O completion. **Driver authors don't write softirqs**. We use tasklets/workqueues/threaded IRQs which are built on top of softirq machinery.

### Picking among them — table

| Bottom half | Context | Can sleep? | Coalesces? | Scheduling cost | When to use |
|-------------|---------|-----------|------------|-----------------|-------------|
| Threaded IRQ | Process (kthread) | Yes | No | ~10 µs (wake kthread) | Default modern choice |
| Workqueue (shared) | Process (kthread) | Yes | Yes (if queued) | ~10 µs | Coalescing multi-IRQ |
| Workqueue (dedicated) | Process (kthread) | Yes | Yes | ~10 µs | Want isolation |
| Tasklet | Softirq | No | Yes | < 1 µs | Legacy; latency-sensitive |

## 43.5  GPIO interrupts — the everyday case

The most common reason embedded drivers want IRQs is to react to a GPIO transition (button press, sensor data-ready, etc.). The mechanics:
> **MCU bridge:** Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

### DT side

```dts
my_button {
    compatible = "linuxlearn,button";
    interrupt-parent = <&gpio4>;
    interrupts = <14 IRQ_TYPE_EDGE_FALLING>;
    button-gpios = <&gpio4 14 GPIO_ACTIVE_LOW>;
};
```

The `interrupts` property names the GPIO bank (via `interrupt-parent`) and the pin within that bank. `IRQ_TYPE_EDGE_FALLING` says trigger on the high-to-low transition.

### Driver side

```c
static int button_probe(struct platform_device *pdev)
{
    struct gpio_desc *gpio;
    int virq, err;

    gpio = devm_gpiod_get(&pdev->dev, "button", GPIOD_IN);
    if (IS_ERR(gpio))
        return PTR_ERR(gpio);

    virq = gpiod_to_irq(gpio);
    if (virq < 0)
        return virq;

    err = devm_request_threaded_irq(&pdev->dev, virq, NULL, button_thread,
                                     IRQF_TRIGGER_FALLING | IRQF_ONESHOT,
                                     "button", priv);
    return err;
}

static irqreturn_t button_thread(int irq, void *dev_id)
{
    /* Button pressed; do something in process context */
    pr_info("button: pressed\n");
    return IRQ_HANDLED;
}
```

Two new things:

- **`gpiod_to_irq`** converts a GPIO descriptor into a virq we can pass to `request_irq`. This is the bridge.
- **NULL primary handler** in `request_threaded_irq` — when you don't have any atomic-context work to do, pass NULL and the kernel installs a default that just returns `IRQ_WAKE_THREAD`.

That's it. The threaded handler runs whenever the button is pressed. Sleep, mutex, copy_to_user — all fine.

## 43.6  Shared IRQs

Multiple devices can share one IRQ line on some hardware (PCI is the canonical case. some SoC peripherals also support it). To handle:

```c
err = request_irq(virq, my_handler, IRQF_SHARED, "myhw", priv);
```

Each handler examines hardware status to see if *its* device fired. Returns `IRQ_HANDLED` if so, `IRQ_NONE` if not. The kernel calls all registered handlers in turn until one returns `IRQ_HANDLED` (or all return `IRQ_NONE`, in which case it's a spurious IRQ).

On i.MX6ULL, GPIO interrupts naturally share (all 32 pins of a bank share one GIC line), so the kernel's GPIO IRQ controller multiplexes for you. You don't need `IRQF_SHARED` for those — the GPIO subsystem handles demuxing.

## 43.7  IRQ-related debug

When IRQs misbehave:

```
[root@pa-mini:~]# cat /proc/interrupts
            CPU0
  17:          0     GIC-0  29 Edge      ...
  19:        842     GIC-0  30 Edge      arch_timer
  21:         12     GIC-0  31 Edge      arch_timer
  29:       4221     GIC-0  68 Level     2020000.serial
  46:          0  gpio-mxc  14 Falling   button
...
```

`/proc/interrupts` shows every active IRQ, total count, controller, hardware number, trigger type, and owner. Look for:

- **Count stuck at 0**: IRQ never fires — wrong trigger polarity, hardware not configured, line not wired up.
- **Count exploding**: IRQ storm — handler not acknowledging hardware properly.
- **"None" in the owner column**: someone requested it then `free_irq`'d but didn't claim ownership. usually a bug.

To debug timing:

```sh
$ echo function > /sys/kernel/debug/tracing/current_tracer
$ echo my_irq_handler my_threaded > /sys/kernel/debug/tracing/set_ftrace_filter
$ echo 1 > /sys/kernel/debug/tracing/tracing_on
... trigger IRQs ...
$ cat /sys/kernel/debug/tracing/trace
```

You'll see timestamps for every entry/exit of your handler, in microseconds. Chapter 119 covers ftrace properly.

## 43.8  Lab

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


1. **Write a GPIO-button driver.** Use the user button on the Point Atom MINI. Threaded IRQ, prints to dmesg on press.
2. **Measure IRQ latency.** Use ftrace to time from a button press (capture in the GPIO bank IRQ) to your threaded handler running. Compare against running the same work in a tasklet.
3. **Add bouncing handling.** Add a 20 ms debounce: ignore further IRQs that fire within 20 ms of the previous (use `jiffies` and `time_after`). Test by pressing and holding. observe a single event in dmesg.
4. **Force an IRQ storm.** Set the trigger type to LEVEL but don't acknowledge the hardware. Observe `/proc/interrupts` count exploding. recover with `rmmod`. *(Note: do this on a non-critical system. If you don't recover quickly, the kernel may detect the storm and disable the IRQ.)*
5. **Convert from threaded to workqueue.** Rewrite #1 using `schedule_work` from a non-threaded `request_irq`. Compare code complexity. observe equivalent behavior.
6. **Shared-IRQ experiment.** On a real shared IRQ (or fake one), register two handlers and verify the kernel calls both. Confirm `IRQ_NONE` is the right return when *your* device didn't fire.

## 43.9  Pitfalls

- **Sleeping in a top-half.** `kmalloc(GFP_KERNEL)`, `mutex_lock`, `copy_to_user` — all forbidden. `CONFIG_DEBUG_ATOMIC_SLEEP=y` catches at the call site. Use `GFP_ATOMIC` if you really must allocate from IRQ context. otherwise pre-allocate.
- **Forgetting to ack.** Level-triggered IRQ + no acknowledge = continuous re-fire = lockup. The kernel will eventually detect the storm and disable the IRQ, printing "spurious IRQ disabled" to dmesg.
- **Wrong trigger polarity in DT.** Symptom: IRQ never fires. Always cross-check the device's datasheet against the DT's `IRQ_TYPE_*` value.
- **Returning `IRQ_NONE` from a non-shared handler.** The kernel treats this as a spurious IRQ. After enough of these, the IRQ is disabled.
- **Calling `request_irq` then `free_irq` with mismatched `dev` pointers.** `free_irq` is keyed on the cookie. Mismatch ⇒ silently fails to free the right handler.
- **Not using `IRQF_ONESHOT` with threaded IRQs.** The hardware can re-fire while the thread is still running, causing a queue of pending threaded calls. Almost always you want `IRQF_ONESHOT`.
- **Wrong context for memory allocation.** In an IRQ handler, `kmalloc(GFP_KERNEL)` may sleep waiting for memory reclaim. Use `GFP_ATOMIC` in top-halves and bottom-halves running in softirq context. Top tip: pre-allocate at probe time so you never alloc in IRQ context.
- **Forgetting `dev_id` parameter.** `request_irq` takes a cookie. You can pass a pointer to your private state. **Don't pass NULL** even if you don't need it — the kernel won't free the handler later, because the cookie is part of the identity for `free_irq`.
- **Not handling shared IRQ correctly.** If you register with `IRQF_SHARED` but always return `IRQ_HANDLED`, other handlers on the same line are starved. Inspect *your* hardware status before claiming the IRQ.

## 43.10  Going deeper

- **`Documentation/core-api/genericirq.rst`** — the kernel's generic IRQ framework.
- **`Documentation/devicetree/bindings/interrupt-controller/`** — the binding for declaring IRQ controllers in DT.
- **`Documentation/locking/lockdep-design.rst`** — IRQ-context vs process-context locking rules (important once you have shared state).
- **`drivers/gpio/gpio-mxc.c`** — the i.MX GPIO driver. Shows how a chained IRQ controller works: the GPIO bank handler demuxes 32 pin events into per-pin virqs.
- **`Documentation/PCI/MSI-HOWTO.rst`** — PCI Message Signaled Interrupts. Different mechanism, same API on the receiving side.
- **`drivers/spi/spi-imx.c`** — a real i.MX driver using threaded IRQ + DMA.

---

> **End of foundation chapters (Ch 36–43).** You now have the full kernel-module driver vocabulary: load/unload, chardev, hot-plug, platform binding, locking, blocking I/O, and interrupts. The chapters that follow (44–51 + insertions) take this vocabulary and apply it to specific subsystems: GPIO, input, I²C, SPI, PWM/RTC, IIO, regmap, DMA, network, sound, LCD/DRM. Each chapter follows the same pattern — the subsystem provides a registration API, you fill in callbacks, the framework handles the rest.
> **MCU bridge:** Think of Linux PWM like an MCU timer output channel, except the driver exposes period, duty cycle, polarity, and enable state through a subsystem.
> **MCU bridge:** Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
> **PWM** - Pulse-Width Modulation, a timer output whose duty cycle controls average power or encodes timing.
> **IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
> **regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.

> Next chapter: **Chapter 44 — GPIO subsystem.** The `gpiod_*` API and how character drivers integrate with the GPIO framework.
