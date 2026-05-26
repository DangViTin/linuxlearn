---
chapter: 52A
title: PREEMPT_RT — Linux as a real-time OS
part: VI — Driver development (supplementary v1.2)
estimated_pages: 14
status: draft
---

# Chapter 52A — PREEMPT_RT

> **What:** the **PREEMPT_RT** patch set (now largely merged into mainline 6.x) — the kernel configuration that turns Linux into a hard-real-time OS, where worst-case interrupt-to-thread latency is measured in tens of microseconds on a Cortex-A7 instead of milliseconds. We cover the four core changes (preemptible spinlocks, threaded IRQs by default, priority inheritance, high-resolution timers), how to enable it on the i.MX6ULL, and how to measure latency with `cyclictest`.
> **Why:** standard Linux has a few-millisecond worst-case scheduling latency under load. That's fine for general computing but disqualifies it from motor control, audio processing, industrial PLCs, and anything that needs deterministic response. PREEMPT_RT bridges that gap. Many shipping industrial products (CNCs, robotic arms, real-time camera ML inference) run PREEMPT_RT Linux today.
> **Focus:** **the deterministic-latency contract**. PREEMPT_RT promises that a high-priority thread will run within a bounded time after its waking event, regardless of what lower-priority threads or kernel code are doing. Internalising what "bounded" really means — and what defeats it — is the whole game.

## 52A.1  What "real-time" means here

"Real-time" doesn't mean "fast." It means "*deterministic*." A standard Linux kernel might run your callback in 100 µs on average — but every 1000th time, it takes 5 ms because some other kernel code held a non-preemptible lock. For audio sampling at 48 kHz (20.8 µs/sample) or a motor control loop at 5 kHz (200 µs/sample), that worst case is fatal.

PREEMPT_RT trades a few percent of throughput for bounded worst case. With it enabled and tuned on i.MX6ULL Cortex-A7, you can expect:

- **Standard kernel under load**: ~100 µs typical, 5–10 ms worst case.
- **PREEMPT_RT under load**: ~30 µs typical, ~150 µs worst case.

The 30× improvement in the long tail makes hard-RT applications viable.

## 52A.2  What PREEMPT_RT changes

Four big changes:

### 1. Preemptible spinlocks

In standard Linux, holding a `spin_lock` *disables preemption*. A higher-priority task can't run until the lock is released. PREEMPT_RT converts most spinlocks to "rt_mutex" — sleeping locks that *can be preempted*. A high-priority task can interrupt a lower-priority task even mid-lock.

The exception: `raw_spinlock` — the few critical locks that genuinely need to disable preemption (the scheduler's own lock, IRQ disable code). These stay non-preemptible. PREEMPT_RT's correctness depends on the kernel using `raw_spinlock_t` *only* where strictly required, and `spinlock_t` (now preemptible) everywhere else. The conversion has been mostly upstreamed; what remains is a small bounded set.

### 2. Threaded interrupts by default

Standard Linux runs IRQ handlers in IRQ context — atomic, fast, but blocking other IRQs of the same priority. PREEMPT_RT runs *all* IRQ handlers as kernel threads, schedulable like any other thread. A real-time thread can preempt an IRQ handler thread; SCHED_FIFO priorities determine order.

You already use `request_threaded_irq` (Ch 43); PREEMPT_RT extends this to *every* IRQ, even ones registered with `request_irq`. The primary handler becomes vestigial.

### 3. Priority inheritance for all mutexes

Without priority inheritance: low-priority task A holds mutex M. High-priority task B wants M, blocks. Medium-priority task C runs (preempts A). B is now blocked indefinitely by C — *priority inversion*. PREEMPT_RT's mutexes implement PI: when B blocks on M, the kernel temporarily boosts A's priority to B's. A runs through to release M, B unblocks, normal priorities restored.

This single feature avoids the Mars Pathfinder bug.

### 4. High-resolution timers everywhere

The `hrtimer` framework gives ns-resolution timers (Ch 55A). PREEMPT_RT makes all kernel-internal timers use hrtimer-class timing, so scheduling decisions happen with µs precision.

## 52A.3  Enabling PREEMPT_RT

For 6.x kernels, PREEMPT_RT is partially in mainline. Check:

```
[host]$ make menuconfig
General setup --->
    Preemption Model
        ( ) No Forced Preemption (Server)
        ( ) Voluntary Kernel Preemption (Desktop)
        ( ) Preemptible Kernel (Low-Latency Desktop)
        (X) Fully Preemptible Kernel (Real-Time)
```

If "Fully Preemptible Kernel (Real-Time)" is missing, you need the out-of-tree PREEMPT_RT patch:

```sh
$ wget https://cdn.kernel.org/pub/linux/kernel/projects/rt/6.6/older/patch-6.6.20-rt19.patch.gz
$ zcat patch-6.6.20-rt19.patch.gz | patch -p1
$ make ARCH=arm imx_v6_v7_defconfig
$ make menuconfig    # enable Full Preemption
$ make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- zImage modules dtbs -j8
```

Boot the new kernel; `uname -a` will show `PREEMPT_RT` in the version string.

## 52A.4  Measuring latency with cyclictest

`cyclictest` is the standard benchmark — it spawns a high-priority thread that sleeps for a fixed interval and measures actual wake-time deviation.

```
[root@pa-mini:~]# cyclictest -t1 -p99 -i1000 -l100000
# /dev/cpu_dma_latency set to 0us
policy: fifo: loadavg: 0.21 0.06 0.02 1/53 230

T: 0 (  223) P:99 I:1000 C: 100000 Min:      6 Act:    8 Avg:    12 Max:      85
```

What this means:
- **T: 0** — thread 0.
- **P:99** — priority 99 (highest FIFO).
- **I:1000** — wakeup interval = 1000 µs (1 ms).
- **C: 100000** — 100,000 wake-ups completed.
- **Min: 6 µs** — fastest measured wake.
- **Max: 85 µs** — worst case.
- **Avg: 12 µs** — average.

For PREEMPT_RT on i.MX6ULL Cortex-A7, a tuned configuration typically gets:
- Max < 100 µs.
- Avg < 20 µs.

Standard kernel on the same hardware: max often > 5000 µs (5 ms).

Run cyclictest with system load:

```
[root@pa-mini:~]# (stress-ng --cpu 1 --io 4 --vm 1 --vm-bytes 50M --timeout 60s &) ; cyclictest -t1 -p99 -i1000 -l60000
```

This is the test that matters — latency *under load*, not at idle.

## 52A.5  Configuration tuning

PREEMPT_RT alone isn't enough. Tune:

### Kernel config

- `CONFIG_HZ=1000` (already default). Higher HZ = finer scheduler granularity.
- `CONFIG_NO_HZ_FULL` for tickless operation on dedicated CPUs (more relevant for multi-core).
- Disable everything non-essential. Each enabled debug option costs latency.

### Kernel cmdline

- **`isolcpus=`** (multi-core only) — reserve specific CPUs for RT threads. i.MX6ULL is single-core, so not applicable.
- **`nohz_full=`** — disable timer ticks on specified CPUs.
- **`mce=off`** — disable machine-check exceptions.
- **`processor.max_cstate=0`** — disable CPU C-states (lower latency, higher idle power).

### Userspace

- **Set RT priority** for your real-time thread: `pthread_setschedparam(SCHED_FIFO, prio=80)`.
- **Lock memory**: `mlockall(MCL_CURRENT | MCL_FUTURE)` to prevent page-fault latency.
- **Pre-fault pages**: write to every page of your stack at startup.

```c
#include <sys/mman.h>
#include <pthread.h>
#include <sched.h>

int main(void) {
    struct sched_param p = { .sched_priority = 80 };
    pthread_setschedparam(pthread_self(), SCHED_FIFO, &p);
    mlockall(MCL_CURRENT | MCL_FUTURE);

    /* Pre-fault 256 KB of stack */
    char stack[256 * 1024];
    memset(stack, 0, sizeof(stack));

    /* Now the RT loop */
    while (1) { ... }
}
```

## 52A.6  Pitfalls

- **Mixing SCHED_FIFO at priority 99 with the kernel's own RT threads.** Your code can starve kernel watchdogs / scheduler maintenance. Cap user RT priorities below 90.
- **Driver still has a raw_spinlock with too much code inside it.** A long raw_spinlock critical section blocks RT. Mostly upstream code is clean; out-of-tree drivers are the usual culprits.
- **`IRQF_NO_THREAD` flag on `request_irq`.** Forces top-half-only handling. Don't use unless absolutely necessary.
- **`spin_lock` in code that calls `kmalloc(GFP_KERNEL)`.** Works under standard Linux (kmalloc tries not to sleep); under PREEMPT_RT, the kmalloc *can* sleep, causing weirdness. Always use `GFP_ATOMIC` in critical sections.
- **VFS / page fault latency on first access.** Read a file, the kernel may fault pages from storage. mlockall + warmup avoids this.
- **Hardware quirks.** Some i.MX6ULL peripherals (SDMA, USB) introduce latency. Profile with `ftrace` to find the culprit.

## 52A.7  Lab

1. **Build PREEMPT_RT kernel** for i.MX6ULL. Boot, verify `uname -a` shows PREEMPT_RT.
2. **Run cyclictest at idle.** Get a baseline Max latency.
3. **Run cyclictest under load.** `stress-ng` + cyclictest in parallel; record worst case.
4. **Tune.** Try `isolcpus` (no-op single-core), `processor.max_cstate=0`, mlockall in cyclictest source. Measure improvement.
5. **Compare with standard kernel.** Build same kernel with `CONFIG_PREEMPT_NONE`; run cyclictest under same load. Note the 30–100× worse worst case.
6. **Real workload.** Run a 1 kHz GPIO toggle from a SCHED_FIFO thread; scope the period jitter. Tune until jitter is < 50 µs.

Commit results and config diffs to `code/ch52A-preempt-rt/`.

## 52A.8  Going deeper

- **`Documentation/locking/`** — preemptible locks under PREEMPT_RT.
- **<https://wiki.linuxfoundation.org/realtime/start>** — the canonical real-time Linux community wiki.
- **`Documentation/admin-guide/sysctl/kernel.rst`** — RT-throttling and related sysctls.
- **`tools/rt-tests/`** — cyclictest, oslat, hackbench source.
- **Open Source Automation Development Lab (OSADL) latency archives** — long-running latency plots across many hardware platforms.

> Next chapter: **Chapter 53 — Sound (ALSA + ASoC).** Ethernet behind us, audio next: the most architecturally complex subsystem in the kernel, with three drivers (machine, codec, CPU-DAI) cooperating to make a single `aplay` work.
