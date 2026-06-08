---
chapter: 41
title: Concurrency in the kernel
part: VI — Driver development
estimated_pages: 20
status: draft
---

# Chapter 41 — Concurrency in the kernel

> **What:** the kernel synchronization toolbox — `atomic_t`, `spinlock_t`, `mutex`, `rwlock_t`, `semaphore`, RCU, and the per-CPU and memory-barrier primitives that back them. By the end you can answer "what lock should I use?" by asking three questions.
>
> **Why:** every driver that touches shared state in two contexts (a process and an interrupt; a process and a timer; two processes via `open(2)`) has a race. Pick the wrong primitive and you hit one of two failure modes: a silent data-corruption race, or a lockup so deep that `dmesg` cannot tell you what happened.
>
> **Focus:** **the three questions** — *who else can be running this code at the same time?* (process, softirq, hardirq, multiple CPUs); *is the critical section allowed to sleep?* (mutex if yes, spinlock if no); *is the access read-mostly?* (RCU if yes). Get these three answers right and the API choice is mechanical.

## 41.1  Why the kernel is concurrent

Unlike a single-core MCU running a single firmware loop, the kernel is concurrent on multiple axes:

1. **Multi-CPU (SMP).** The i.MX6ULL is single-core, but the kernel is built `CONFIG_SMP=y` and *behaves* as if it were SMP. Your driver may run on different CPUs at different times.
2. **Preemption.** A process running your driver code can be preempted by a higher-priority process. Your local variables are safe; your shared variables aren't.
3. **Interrupts.** A hardware interrupt can preempt your driver mid-instruction. If both your driver and its interrupt handler touch the same variable, you have a race.
4. **Softirqs and tasklets.** A "bottom half" — softirq, tasklet, or work queue — can run on the same CPU as your driver, interleaving at quantum boundaries.
5. **Multiple syscalls.** Two processes both calling `read(fd)` on your device file are racing inside your driver simultaneously.

Concurrency is the default. Every shared variable needs a plan. Every variable that's read or written from more than one of the contexts above needs locking, atomics, or one of the lock-free patterns we'll get to.

## 41.2  The decision tree

Three questions. Answer them and you've picked your primitive.

### Question 1: What contexts can access the data?

- **Process only** (no IRQ handler, no softirq) → mutex or semaphore.
- **Process + IRQ** → spinlock (and the IRQ variant — `spin_lock_irqsave`).
- **Process + softirq/tasklet** → spinlock with `_bh` variant.
- **IRQ only**, single CPU → no lock needed (interrupts are serialized on one CPU). With SMP, still need a spinlock.

### Question 2: Is the critical section allowed to sleep?

- **Yes** (calls `kmalloc(GFP_KERNEL)`, `copy_to_user`, anything else that can block) → must be mutex (or other sleeping lock). Spinlocks forbid sleeping while held.
- **No** (just arithmetic, register read/write) → spinlock is fine.

### Question 3: Is the access read-mostly?

- **Yes** (e.g., a list updated rarely but read in every IRQ) → consider RCU.
- **No** → standard lock is fine.

That's it. Three questions, one primitive. Let's see them in action.

### Context cheat sheet — what may sleep, what may not

This is *the* table to memorize. Every later driver chapter (i2c, SPI, IIO, regmap, DMA, USB, etc.) assumes you know it; we will not repeat it.

| Context | Examples | May sleep? | Locks you may take | Locks you must avoid |
|---|---|---|---|---|
| **Process** (syscall, `probe()`, file_operations) | `read`, `write`, `ioctl`, `open` | **yes** | `mutex_lock`, `spin_lock`, `down`, `wait_event`, `i2c_smbus_*`, `spi_sync`, `kmalloc(GFP_KERNEL)` | — |
| **Threaded IRQ** (`request_threaded_irq` bottom half) | the `_threaded_fn` argument | **yes** | same as process context | — |
| **Workqueue** (`schedule_work`, `delayed_work`) | `INIT_WORK` handlers | **yes** | same as process context | — |
| **Softirq / tasklet / timer** | `softirq` callbacks, `mod_timer` callbacks | **no** | `spin_lock`, `atomic_*`, `mutex_trylock` (only) | `mutex_lock`, `i2c_smbus_*`, `msleep`, `kmalloc(GFP_KERNEL)` |
| **Hard IRQ** (top half of `request_irq`) | the `_handler` argument when there's no threaded fn | **no — strictly atomic** | `spin_lock_irqsave`, `atomic_*` | everything that may sleep, including i2c/spi transfers, `printk` with KERN_DEBUG at high rate |
| **Holding a spinlock** | inside `spin_lock` … `spin_unlock` | **no** | nested spinlocks (different order rule) | everything that may sleep |

**Rule of thumb for sensor / bus drivers:** if you need to do an `i2c_smbus_*` or `spi_sync` (both can block on bus contention), you must be in **process context** or a **threaded IRQ** — never in a hard IRQ handler or under a spinlock. Use `request_threaded_irq` and put the bus access in the threaded half.

We refer back to this table from many places. When a later chapter says "this runs in atomic context," consult the rows above.

## 41.3  Atomic operations

Sometimes you just want to increment a counter from multiple contexts. A lock is overkill; the kernel exposes **atomic types** that compile to a single bus-locked instruction.

```c
#include <linux/atomic.h>

atomic_t counter = ATOMIC_INIT(0);

atomic_inc(&counter);
atomic_dec(&counter);
atomic_add(7, &counter);
int n = atomic_read(&counter);

/* Test-and-modify */
if (atomic_dec_and_test(&counter)) {
    /* counter just hit zero */
}

/* Compare and swap */
int old = atomic_cmpxchg(&counter, 0, 1);
if (old == 0) {
    /* we set 0 → 1, exclusive use */
}
```

Atomics are signed 32-bit (`atomic_t`) or signed 64-bit (`atomic64_t`). They're guaranteed atomic against all contexts, all CPUs. They don't take a lock; they use the CPU's atomic-instruction support (ldrex/strex on ARM).

Use atomics for:
- Reference counts.
- Statistics counters (e.g., packets transmitted).
- Simple flags (one bit at a time — but `set_bit/clear_bit/test_bit` are a better API for that).

Don't use atomics for:
- Anything that requires multi-step consistency (e.g., "increment `a` and decrement `b`" — you need a lock).
- Pointers that need ordering with respect to other writes (use RCU instead).

### Bit operations

For single-bit flags:

```c
unsigned long flags = 0;

set_bit(BIT_RUNNING, &flags);
clear_bit(BIT_RUNNING, &flags);
if (test_bit(BIT_RUNNING, &flags)) ...

/* Atomic test-and-set; returns the OLD value */
if (!test_and_set_bit(BIT_BUSY, &flags))
    /* we got the lock */
```

These compile to the same atomic instructions as `atomic_t`. They're idiomatic for "a small set of independent state bits."

## 41.4  Spinlocks

A spinlock is the simplest lock: a CPU that can't acquire it *spins* (busy-loops) until it can. No sleeping, no scheduling — perfect for protecting state shared with IRQ handlers.

```c
#include <linux/spinlock.h>

static DEFINE_SPINLOCK(my_lock);    /* static initializer */

spin_lock(&my_lock);
shared_data = new_value;
spin_unlock(&my_lock);
```

Three rules for spinlocks:

1. **Hold time must be short.** While you hold a spinlock, the kernel will not preempt the current task. In the IRQ-safe variant, IRQs are disabled on the holding CPU too. Other CPUs trying to grab the lock burn cycles. "Short" means microseconds, not milliseconds.
2. **No sleeping while held.** Don't call `kmalloc(GFP_KERNEL)`, `copy_to_user`, `mutex_lock`, or anything that might sleep. Kernel debug builds (`CONFIG_DEBUG_ATOMIC_SLEEP=y`) will catch and shame you for these.
3. **Don't reschedule.** Don't call `schedule()`, don't call `cond_resched()`, don't call user-space syscalls.

### Variants

```c
spin_lock(&lock);          spin_unlock(&lock);          /* base */
spin_lock_bh(&lock);       spin_unlock_bh(&lock);       /* disable softirqs */
spin_lock_irq(&lock);      spin_unlock_irq(&lock);      /* disable IRQs */
spin_lock_irqsave(&lock, flags);  spin_unlock_irqrestore(&lock, flags);
```

When to use which:

- **Process context only**: `spin_lock` is enough.
- **Process + softirq/tasklet**: `spin_lock_bh`. Otherwise a softirq can fire between your lock and unlock and try to grab the same lock — deadlock.
- **Process + IRQ**: `spin_lock_irqsave`. The `_save` variant preserves the previous IRQ state, which matters because you might already be in an IRQ-disabled context (nested locks).

The IRQ variants must be matched: `spin_lock_irqsave` ↔ `spin_unlock_irqrestore`, never mix.

### Example: protecting a shared counter

```c
static DEFINE_SPINLOCK(stats_lock);
static u64 packets;

/* From process context (driver write callback) */
void user_send(void)
{
    unsigned long flags;
    spin_lock_irqsave(&stats_lock, flags);
    packets++;
    spin_unlock_irqrestore(&stats_lock, flags);
}

/* From IRQ handler */
irqreturn_t my_irq(int irq, void *dev)
{
    spin_lock(&stats_lock);   /* IRQs already off in IRQ handler */
    packets++;
    spin_unlock(&stats_lock);
    return IRQ_HANDLED;
}
```

(In practice, `atomic64_t` would be simpler for a single counter. Spinlocks shine when there's more than one variable to keep consistent.)

## 41.5  Mutexes

A mutex is a **sleeping** lock. If the lock is unavailable, the requesting task is put to sleep and woken when the lock is released. This makes them perfect for protecting longer critical sections — anything that calls `kmalloc(GFP_KERNEL)`, `copy_to_user`, etc.

```c
#include <linux/mutex.h>

static DEFINE_MUTEX(my_mutex);

mutex_lock(&my_mutex);
/* may sleep */
do_long_work();
mutex_unlock(&my_mutex);
```

Variants:

```c
mutex_lock(&m);              /* uninterruptible — can't be killed */
mutex_lock_interruptible(&m); /* returns -EINTR on signal; preferred */
mutex_lock_killable(&m);     /* only fatal signals interrupt */
mutex_trylock(&m);           /* nonblocking; returns 1 if got it, 0 if not */
```

**Use `mutex_lock_interruptible` in driver fops** so a stuck process can be killed with `Ctrl-C` instead of being unkillable.

Mutexes have one nice property over semaphores: the kernel tracks *who* holds them. Lockdep (Linux's lock-debug subsystem, `CONFIG_PROVE_LOCKING=y`) uses this for deadlock detection — if you ever take lock A while holding B in one place and B while holding A elsewhere, lockdep prints a screaming warning to dmesg with both stack traces.

## 41.6  Read-write locks

When a resource is **read often, written rarely**, a read-write lock lets multiple readers share access while writers get exclusive ownership.

```c
#include <linux/rwlock.h>

static DEFINE_RWLOCK(my_rwlock);

/* Readers */
read_lock(&my_rwlock);
/* read shared data */
read_unlock(&my_rwlock);

/* Writers */
write_lock(&my_rwlock);
/* modify shared data */
write_unlock(&my_rwlock);
```

Same _irq, _bh, _irqsave variants as spinlocks apply. Also exists as sleeping variant: `rwsem` (`down_read`/`down_write` API).

The catch: rwlocks have a famously bad performance profile on heavily contended scenarios — readers are cheap, writers are expensive, and starvation is possible. For most "many-read, rare-write" cases, **RCU is the better choice**.

## 41.7  RCU — the read-mostly secret weapon

Read-Copy-Update is the kernel's read-mostly trick: readers pay zero synchronization cost — no atomic operations, no lock acquisition, no memory barriers in the fast path. Writers copy, modify, and publish atomically. Old readers see the old version until they finish; new readers see the new.

```c
#include <linux/rcupdate.h>

struct config {
    int speed;
    int mode;
};

static struct config __rcu *cur_config;

/* Reader */
void some_read_path(void)
{
    struct config *c;
    rcu_read_lock();
    c = rcu_dereference(cur_config);
    if (c)
        do_something(c->speed, c->mode);
    rcu_read_unlock();
}

/* Writer */
void update_config(int s, int m)
{
    struct config *old, *new;
    new = kmalloc(sizeof(*new), GFP_KERNEL);
    new->speed = s;
    new->mode = m;
    old = rcu_dereference_protected(cur_config, lockdep_is_held(&write_lock));
    rcu_assign_pointer(cur_config, new);
    synchronize_rcu();      /* wait for all readers to finish with `old` */
    kfree(old);
}
```

`rcu_read_lock()`/`rcu_read_unlock()` are basically free — they expand to nothing on most kernel configurations (`CONFIG_PREEMPT_NONE`) or to a per-CPU counter increment (`CONFIG_PREEMPT_RCU`). No spinning, no atomics in the read path.

The catch: writes are expensive (`synchronize_rcu()` can take milliseconds) and you can only protect *pointer* updates this way. RCU is heavy machinery — not for a simple counter. But for "lookup-then-use" data on every packet, it is dramatically faster than any lock — that's why almost every networking-fast-path data structure in the kernel is RCU-protected.

We won't go deeper here. If you find yourself wanting RCU, read `Documentation/RCU/whatisRCU.rst` and the references; it has subtleties.

## 41.8  Per-CPU data — the lock-free shortcut

Sometimes you can sidestep locking entirely by *splitting* the data. If you have a "packets sent" counter, instead of one shared `atomic64_t`, have **per-CPU counters**. Each CPU increments its own (no contention); read combines them.

```c
#include <linux/percpu.h>

static DEFINE_PER_CPU(u64, packets);

/* Increment on this CPU (no atomic needed if preemption disabled) */
void incr_local(void)
{
    preempt_disable();
    this_cpu_inc(packets);
    preempt_enable();
}

/* Sum across all CPUs */
u64 sum_all(void)
{
    u64 total = 0;
    int cpu;
    for_each_possible_cpu(cpu)
        total += per_cpu(packets, cpu);
    return total;
}
```

Per-CPU data works well when reads are rare relative to writes (the opposite of RCU's case). Linux's `getrusage` accounting, networking statistics, scheduler runqueue load — all use per-CPU.

On a single-core CPU (the i.MX6ULL), the per-CPU array has one slot and `this_cpu_inc` is just a normal increment. Still useful, because you've written code that scales to multi-core too.

## 41.9  Lockdep — your friend

Build the kernel with `CONFIG_PROVE_LOCKING=y`. (It costs ~20% performance, so disable in production, but enable during development.) Lockdep watches every lock acquisition and:

- Detects A-B-B-A deadlocks across all CPUs and contexts.
- Catches "sleeping while atomic" violations.
- Flags forgotten unlocks.
- Highlights wait-context mismatches (RT, IRQ context, etc.).

When it triggers, you get a wall of dmesg output. Two stack traces, one per lock acquisition path, and a verdict like "deadlock possible." Read it carefully — it tells you which locks, in which order, from which functions.

Turn it on during development. Disable for production.

## 41.10  A worked example: thread-safe ring buffer

Let's solidify with a small example — a ring buffer that a process writes to from `write(2)` and a tasklet reads from. Two contexts (process, softirq), shared state.

```c
#include <linux/spinlock.h>

#define RBUF_SIZE 4096

struct rbuf {
    char data[RBUF_SIZE];
    size_t head, tail;
    spinlock_t lock;
};

static struct rbuf rb;

void rb_init(void) { spin_lock_init(&rb.lock); }

/* Producer: from write() */
ssize_t rb_put(const char __user *u, size_t n)
{
    unsigned long flags;
    char buf[RBUF_SIZE];
    if (n > RBUF_SIZE) n = RBUF_SIZE;
    if (copy_from_user(buf, u, n)) return -EFAULT;

    spin_lock_irqsave(&rb.lock, flags);   /* lock for shared structure access */
    for (size_t i = 0; i < n; i++) {
        size_t next = (rb.head + 1) % RBUF_SIZE;
        if (next == rb.tail) break;       /* full */
        rb.data[rb.head] = buf[i];
        rb.head = next;
    }
    spin_unlock_irqrestore(&rb.lock, flags);
    return n;
}

/* Consumer: from a tasklet (softirq context) */
size_t rb_consume(char *out, size_t max)
{
    unsigned long flags;
    size_t i;
    spin_lock_irqsave(&rb.lock, flags);
    for (i = 0; i < max && rb.head != rb.tail; i++) {
        out[i] = rb.data[rb.tail];
        rb.tail = (rb.tail + 1) % RBUF_SIZE;
    }
    spin_unlock_irqrestore(&rb.lock, flags);
    return i;
}
```

Things to notice:

- We `copy_from_user` *outside* the lock — because `copy_from_user` can sleep. With the lock, that would be illegal.
- The shared-state access (the actual put/consume) is short and under spinlock.
- We use `spin_lock_irqsave` because the consumer runs in softirq context.

This pattern — copy outside, lock around the structure mutation only — is fundamental. Locks should protect the **minimum** of code that needs protection.

## 41.11  Lab

1. **Build and run the ring buffer above.** Test single-threaded, then with parallel producers.
2. **Add a stress test.** Have a kthread (`kthread_run`) consume in a tight loop while `write(2)` is hammered from user space. Verify no crashes, no corrupt data, no deadlocks.
3. **Provoke a deadlock.** Take lock A then lock B in one path; take B then A in another. Build with `CONFIG_PROVE_LOCKING=y`. Watch lockdep's dmesg report when both paths actually run.
4. **Convert `packets` to per-CPU.** Compare overhead vs an `atomic64_t`. (Spoiler: per-CPU is faster on multi-core but the test is harder to write on a single-core i.MX6ULL.)
5. **RCU experiment.** Implement a simple read-mostly config lookup with RCU. Use `ftrace` (Chapter 119) to measure the read-side overhead. Confirm it's zero in `CONFIG_PREEMPT_NONE`.

## 41.12  Pitfalls

- **Sleeping inside a spinlock.** The kernel may not crash immediately; it may deadlock minutes or hours later when the *other* CPU tries to take the same lock. `CONFIG_DEBUG_ATOMIC_SLEEP=y` catches this immediately at the offending call site.
- **Forgetting `spin_lock_irqsave` when sharing with an IRQ.** Process takes lock → IRQ fires on same CPU → IRQ tries lock → deadlock. Use `_irqsave` whenever IRQ context can hit the same lock.
- **Recursive locking.** Linux mutexes are **not recursive**. Taking the same mutex twice from the same task = deadlock (or BUG with debug enabled). Use `mutex_trylock` if you might already hold it, or restructure to never re-enter.
- **`mutex_lock` in `read`/`write` instead of `mutex_lock_interruptible`.** A process holding your mutex becomes unkillable. Always use interruptible in syscall context.
- **Long-held mutexes.** `mutex_lock` doesn't sleep-spin — it actually puts the thread to sleep. For very short critical sections (<a few hundred cycles), a spinlock is faster than the schedule overhead. For long ones, mutex is far better. Profile if unsure; the dividing line is ~tens of cycles vs ~microseconds.
- **Mixing atomic and locked access.** `atomic_inc(&x); spin_lock(&l); some_other_code(); spin_unlock(&l);` — what consistency are you trying to maintain? If `x` is only consistent with the lock, use the lock everywhere. Mixed access usually means a bug.
- **Using `volatile`.** `volatile` is almost always wrong in kernel code. Use atomics or memory barriers. The kernel coding style explicitly bans `volatile` except for compile-time-known special cases. See `Documentation/process/volatile-considered-harmful.rst`.

## 41.13  Going deeper

- **`Documentation/locking/`** — the kernel's lock-by-lock documentation. Read `mutex-design.rst` and `rt-mutex-design.rst`.
- **`Documentation/locking/lockdep-design.rst`** — what lockdep watches for and how to read its reports.
- **`Documentation/RCU/whatisRCU.rst`** — the friendly RCU intro.
- **`Documentation/memory-barriers.txt`** — when you absolutely need to think about memory ordering. (Almost never in driver code; usually only in lock primitives themselves.)
- **`Is Parallel Programming Hard, And, If So, What Can You Do About It?`** by Paul McKenney — the definitive textbook on kernel concurrency, free PDF online.

> Next chapter: **Chapter 42 — Sleeping, waiting, polling.** With locking understood, we add the missing piece for blocking I/O: wait queues, `wait_event_interruptible`, and the `poll`/`select` integration.
