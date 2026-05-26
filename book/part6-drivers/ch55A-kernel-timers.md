---
chapter: 55A
title: Kernel timers and hrtimers
part: VI — Driver development (supplementary v1.1)
estimated_pages: 12
status: draft
---

# Chapter 55A — Kernel timers and hrtimers

> **What:** the kernel's two timer families — **timer_list** (jiffies-granular, ~1 ms on i.MX6ULL with HZ=1000) and **hrtimer** (high-resolution, nanosecond-granular). Used for "do X in N ms" patterns inside drivers — debouncing buttons, polling status, scheduling periodic samples.
> **Why:** `msleep` and `mdelay` block the calling thread. Sometimes you need "fire a callback in 50 ms without blocking" — that's what these timers are for. They're foundational to many driver patterns: timeouts, periodic polling, throttling, scheduled deferred work.
> **Focus:** **timer_list for ms granularity, hrtimer for µs/ns**. Pick the right one and the API choices follow.

## 55A.1  timer_list

The classic jiffies-based timer:

```c
#include <linux/timer.h>

struct timer_list my_timer;

static void my_timer_cb(struct timer_list *t)
{
    /* runs in softirq context — no sleeping! */
    pr_info("timer fired\n");
}

/* In probe: */
timer_setup(&my_timer, my_timer_cb, 0);

/* Schedule: fire 100 ms from now */
mod_timer(&my_timer, jiffies + msecs_to_jiffies(100));

/* Cancel: */
del_timer_sync(&my_timer);
```

- **Granularity**: 1 jiffy ≈ 1 ms (HZ=1000).
- **Context**: callback runs in softirq context (atomic). No sleeping, no `mutex_lock`, no `kmalloc(GFP_KERNEL)`.
- **`mod_timer`**: re-schedules an existing timer to a new expiry; if not active, arms it.
- **`del_timer_sync`**: deletes and waits for any in-flight callback to finish. Use in `remove`.

Typical pattern — button debounce (Ch 45 lab):

```c
static void debounce_cb(struct timer_list *t)
{
    struct my_button *b = from_timer(b, t, debounce_timer);
    int val = gpiod_get_value(b->gpio);
    input_report_key(b->input, KEY_ENTER, val);
    input_sync(b->input);
}

static irqreturn_t button_irq(int irq, void *dev_id)
{
    struct my_button *b = dev_id;
    mod_timer(&b->debounce_timer, jiffies + msecs_to_jiffies(20));
    return IRQ_HANDLED;
}
```

Each press triggers an IRQ, which re-arms the timer. If the button bounces, every bounce resets the timer; only after 20 ms of silence does the timer fire and report the press.

## 55A.2  hrtimer

When you need µs precision:

```c
#include <linux/hrtimer.h>

struct hrtimer my_hrtimer;

static enum hrtimer_restart my_hr_cb(struct hrtimer *t)
{
    /* still softirq context */
    pr_info("hrtimer fired\n");
    /* For periodic: */
    hrtimer_forward_now(t, ms_to_ktime(100));
    return HRTIMER_RESTART;
    /* For one-shot: return HRTIMER_NORESTART; */
}

/* In probe: */
hrtimer_init(&my_hrtimer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
my_hrtimer.function = my_hr_cb;

/* Arm: fire 500 µs from now */
hrtimer_start(&my_hrtimer, us_to_ktime(500), HRTIMER_MODE_REL);

/* Cancel: */
hrtimer_cancel(&my_hrtimer);
```

- **Granularity**: nanoseconds, limited by hardware (i.MX6ULL's GPT has ~30 ns resolution).
- **Context**: same — softirq, no sleeping.
- **Periodic loops**: return `HRTIMER_RESTART` after `hrtimer_forward_now`. Drifts less than re-arming manually.

Common pattern — periodic sampling at 1 kHz:

```c
hrtimer_init(&p->hr, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
p->hr.function = sample_cb;
hrtimer_start(&p->hr, ms_to_ktime(1), HRTIMER_MODE_REL);
```

Each callback: do the work, then `hrtimer_forward_now(t, ms_to_ktime(1)); return HRTIMER_RESTART;`. The forwarding (vs. recomputing now+1ms) keeps the schedule cumulative without drift.

## 55A.3  Workqueue vs timer

Both are deferred mechanisms but in different contexts:

| | timer/hrtimer | workqueue |
|---|---|---|
| Callback context | softirq (atomic) | process (sleeping OK) |
| Precision | high | low (~1 ms typical, more under load) |
| Use for | timeouts, fast polling | longer work that may sleep |

Combine them: timer fires (atomic), schedules a workqueue (process context for the heavy work).

```c
static void my_timer_cb(struct timer_list *t)
{
    struct my_priv *p = from_timer(p, t, timer);
    schedule_work(&p->work);
    mod_timer(&p->timer, jiffies + msecs_to_jiffies(100));  /* re-arm */
}

static void my_work_fn(struct work_struct *w)
{
    struct my_priv *p = container_of(w, struct my_priv, work);
    /* heavy work, can sleep */
}
```

## 55A.4  Delayed work — a workqueue with built-in timer

For the common "do this in N ms, in process context" pattern:

```c
#include <linux/workqueue.h>

struct delayed_work my_dwork;

static void my_dwork_fn(struct work_struct *w)
{
    /* process context — can sleep */
}

INIT_DELAYED_WORK(&my_dwork, my_dwork_fn);

schedule_delayed_work(&my_dwork, msecs_to_jiffies(100));
cancel_delayed_work_sync(&my_dwork);
```

`delayed_work` combines a timer + workqueue. Most "do this later" use cases want this rather than raw timers.

## 55A.5  Lab

1. **Add a software heartbeat.** A `timer_list` that prints `dmesg` every 5 seconds. Verify it fires regularly.
2. **Hrtimer for jitter measurement.** Fire an hrtimer every 1 ms; in the callback, log the actual time delta. With PREEMPT_RT, compare jitter against standard kernel.
3. **Debounce button.** Use `timer_list` for 20 ms debounce on a GPIO key.
4. **Periodic GPIO toggle.** Use hrtimer + GPIO output to generate a 1 kHz square wave; scope it; observe jitter.
5. **Combine timer + workqueue.** A timer that schedules work; the work does `msleep(50)`; verify the system stays responsive.

Commit code to `code/ch55A-timers/`.

## 55A.6  Pitfalls

- **Sleeping in a timer callback.** Softirq context — `kmalloc(GFP_KERNEL)`, `mutex_lock` are forbidden. Use workqueue if you need to sleep.
- **`del_timer` without `_sync` in remove.** Race: timer fires during cleanup. Always use `del_timer_sync`.
- **Forgetting to re-arm a periodic timer.** It fires once and stops. Either `mod_timer` in the callback or use `delayed_work`.
- **hrtimer drift with manual re-arming.** `hrtimer_start(t, now + 1ms)` drifts because of callback latency. `hrtimer_forward_now(t, 1ms)` doesn't.
- **Timer fires after device is unregistered.** Without `del_timer_sync`, the callback can run after probe-cleanup, touching freed memory. Synchronize cleanup.
- **Too many timers in flight.** Each adds to the kernel timer wheel; thousands cost CPU. For mass-scheduled events, consider a single timer + a list of work items.

## 55A.7  Going deeper

- **`Documentation/timers/`** — kernel timer documentation.
- **`include/linux/timer.h`** and **`hrtimer.h`** — APIs.
- **`kernel/time/`** — implementation. `hrtimer.c`, `timer.c`.
- **LDD3 Chapter 7** — timers and workqueues in depth.

> Next chapter: **Chapter 55B — Async notification via SIGIO.** A "signal me when data is ready" mechanism that's useful for legacy POSIX-style apps that don't use poll/epoll.
