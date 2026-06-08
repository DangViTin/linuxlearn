---
chapter: 42
title: Sleeping, waiting, polling
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 42 — Sleeping, waiting, polling

> **What:** **wait queues** (`wait_queue_head_t`, `wait_event_interruptible`, `wake_up`), the `.poll` file_operations callback, and the `O_NONBLOCK` machinery. Together these let a `read(2)` or `write(2)` syscall block until data is ready, wake exactly the right process when it is, and integrate with `select(2)` / `poll(2)` / `epoll`.
>
> **Why:** drivers that produce data on their own schedule (UART, keyboard, sensor, network) need a way to make a reader wait without polling. Without wait queues, your `read` callback either returns "no data, try again" (caller burns CPU spinning) or blocks the CPU itself (kernel hangs). Wait queues are how Linux makes blocking I/O efficient. The thread sleeps. The scheduler runs something else. An interrupt or timer wakes the thread when its data is ready.
>
> **Focus:** **the sleep/wake protocol**. The reader registers itself on a wait queue, checks a condition, and sleeps if not met. The producer modifies state then calls `wake_up`. The kernel guarantees no missed wakeups via a careful prepare-and-check sequence. Get the sequence right and your driver's blocking I/O is correct. Get it wrong and reads sometimes hang forever.


## 42.1  The two ways to wait

Two patterns exist in user-space:

1. **Blocking read.** `read(fd, buf, n)` doesn't return until data is available. The kernel puts the caller to sleep and wakes it when data arrives.
2. **Polling / `select`.** The caller registers interest in `fd` becoming readable/writable, then sleeps in `select(fds, ...)` until *any* registered fd is ready. The same `fd` may be one of many.

Both eventually rest on the same kernel primitive: a **wait queue**. The driver maintains a `wait_queue_head_t` per logical "thing to wait for." Threads add themselves and sleep. producers wake everyone who's waiting.

## 42.2  Wait queue API

`#include <linux/wait.h>`

```c
wait_queue_head_t my_wq;
init_waitqueue_head(&my_wq);
/* or: */
DECLARE_WAIT_QUEUE_HEAD(my_wq);

/* Wait until a condition is true */
wait_event_interruptible(my_wq, condition);

/* Wake everyone waiting on this queue */
wake_up_interruptible(&my_wq);
```

`condition` is **evaluated multiple times** inside `wait_event_interruptible`. The macro:

1. Adds the current task to the wait queue.
2. Sets state to `TASK_INTERRUPTIBLE`.
3. Checks `condition`. If true, removes the task and returns.
4. If false, calls `schedule()` — the task sleeps.
5. On wake, jumps back to step 3.

This loop is what prevents the "lost wakeup" race: the producer might `wake_up` between our check of `condition` and our `schedule()`. The wait_event_* macros handle the atomicity carefully.

### Variants

| Macro | What |
|-------|------|
| `wait_event(wq, cond)` | Uninterruptible — task can't be killed |
| `wait_event_interruptible(wq, cond)` | Killable; returns `-ERESTARTSYS` on signal |
| `wait_event_timeout(wq, cond, t)` | Times out after `t` jiffies; returns remaining time |
| `wait_event_interruptible_timeout(...)` | Both interruptible and timeout |
| `wait_event_killable(wq, cond)` | Like interruptible, but only fatal signals interrupt |

For driver `read`/`write` callbacks: **use `wait_event_interruptible` or `wait_event_interruptible_timeout`**. Never use the uninterruptible variants. A stuck driver with uninterruptible waiters is the classic D-state hang — the user cannot kill the process. only a reboot fixes it.

### Wake variants

| Function | What |
|----------|------|
| `wake_up(&wq)` | Wakes one or more, sets `TASK_RUNNING` |
| `wake_up_interruptible(&wq)` | Wakes one or more that are in `TASK_INTERRUPTIBLE` |
| `wake_up_all(&wq)` | Wakes everyone |
| `wake_up_interruptible_all(&wq)` | Wakes everyone in `TASK_INTERRUPTIBLE` |

For driver code, match the variant to your wait: if you `wait_event_interruptible`, you `wake_up_interruptible`. Mismatch isn't broken per se — wake_up wakes everyone — but the pairing is conventional and clear.

## 42.3  A blocking read example

Extend the misc-device driver from Chapter 40 with a kernel-thread "producer" and a blocking `read` that waits for data.

```c
#include <linux/wait.h>
#include <linux/kthread.h>
#include <linux/delay.h>

static char data_buf[64];
static int  data_len;
static DECLARE_WAIT_QUEUE_HEAD(read_wq);
static struct mutex data_lock;
static struct task_struct *producer;

/* Producer kernel thread: every 2 seconds, generate data and wake readers */
static int producer_fn(void *arg)
{
    int counter = 0;
    while (!kthread_should_stop()) {
        msleep(2000);
        mutex_lock(&data_lock);
        data_len = snprintf(data_buf, sizeof(data_buf),
                            "event %d\n", counter++);
        mutex_unlock(&data_lock);
        wake_up_interruptible(&read_wq);
    }
    return 0;
}

static ssize_t my_read(struct file *filp, char __user *ubuf,
                       size_t count, loff_t *ppos)
{
    ssize_t ret;

    /* Block until data_len > 0; respect O_NONBLOCK */
    if (filp->f_flags & O_NONBLOCK) {
        if (data_len == 0)
            return -EAGAIN;
    } else {
        if (wait_event_interruptible(read_wq, data_len > 0))
            return -ERESTARTSYS;
    }

    mutex_lock(&data_lock);
    if (count > data_len)
        count = data_len;
    if (copy_to_user(ubuf, data_buf, count)) {
        ret = -EFAULT;
        goto out;
    }
    data_len = 0;   /* consumed */
    ret = count;
out:
    mutex_unlock(&data_lock);
    return ret;
}
```

Test:

```
[root@pa-mini:~]# insmod waiting.ko
[root@pa-mini:~]# cat /dev/waiting
event 0       ← appears after ~2 seconds, blocks here
event 1
event 2
...
```

The read blocks. The producer thread wakes the wait queue every 2 seconds. The reader wakes, returns one event's worth of data, then re-enters the wait if `cat` continues.

### O_NONBLOCK

```c
if (filp->f_flags & O_NONBLOCK) {
    if (data_len == 0)
        return -EAGAIN;
}
```

If the user opened the device with `O_NONBLOCK`, we *never* sleep — we return `-EAGAIN` (= "would block. try again later") immediately if no data. This is what `epoll` and similar event loops want.

`O_NONBLOCK` is a per-open flag. The user can change it later via `fcntl(fd, F_SETFL, O_NONBLOCK)`. Always check it.

## 42.4  poll / select / epoll

`select(2)` and friends let user-space block on multiple fds at once. To support them, your driver implements a `.poll` callback in `file_operations`:

```c
static __poll_t my_poll(struct file *filp, poll_table *wait)
{
    __poll_t mask = 0;

    /* Register our wait queue with the poll system */
    poll_wait(filp, &read_wq, wait);

    /* Report current readability/writability */
    if (data_len > 0)
        mask |= EPOLLIN | EPOLLRDNORM;

    /* If we had writable state, we'd also: */
    /* if (have_space) mask |= EPOLLOUT | EPOLLWRNORM; */

    return mask;
}
```

Add to `file_operations`:

```c
static const struct file_operations my_fops = {
    .owner   = THIS_MODULE,
    .read    = my_read,
    .poll    = my_poll,
    /* ... */
};
```

The `poll_wait` call **doesn't block**. It just registers our wait queue with the kernel's poll machinery — if the caller's `select` decides to sleep, it'll be woken whenever any of the queues it registered with is woken.

After registering, we **immediately** report current readability. If data is available, `EPOLLIN | EPOLLRDNORM` says "this fd is readable now."

The flow from user-space:

```
   user: select({read=fd}, ..., timeout=10s)
            │
            ▼
   kernel: dispatches to my_poll(filp, &poll_table)
            │
            ▼
   my_poll: poll_wait(filp, &read_wq, &poll_table)
            return mask
            │
            ▼
   kernel: if mask != 0, return immediately
            else, sleep on the registered wait queues
            │
            ▼
   producer: wake_up_interruptible(&read_wq)
            │
            ▼
   kernel: woken; rerun all the poll callbacks
            if any returns non-zero mask, return to user-space
```

The `wake_up_interruptible(&read_wq)` does double duty: it wakes blocking `read()` callers *and* triggers a recheck for `select` callers. One wait queue, two consumers — exactly what we want.

### Testing with `select`

User-space test (`test_poll.c`):

```c
#include <sys/select.h>
#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>

int main(void)
{
    int fd = open("/dev/waiting", O_RDONLY | O_NONBLOCK);
    char buf[64];
    fd_set rfds;
    struct timeval tv;

    while (1) {
        FD_ZERO(&rfds);
        FD_SET(fd, &rfds);
        tv.tv_sec = 5;
        tv.tv_usec = 0;
        int r = select(fd + 1, &rfds, NULL, NULL, &tv);
        if (r == 0) {
            printf("[timeout]\n");
        } else if (r > 0 && FD_ISSET(fd, &rfds)) {
            int n = read(fd, buf, sizeof(buf) - 1);
            buf[n] = 0;
            printf("[%d bytes] %s", n, buf);
        }
    }
}
```

Build for ARM and run on target:

```
[root@pa-mini:~]# ./test_poll
[64 bytes] event 0
[64 bytes] event 1
[timeout]      ← if no events for 5 seconds
...
```

`select` correctly sleeps and wakes only when our driver signals data ready.

## 42.5  msleep, msleep_interruptible, schedule_timeout

Driver code sometimes needs to "wait N milliseconds." The options:

```c
msleep(100);                  /* sleep 100 ms; uninterruptible */
msleep_interruptible(100);    /* sleep 100 ms; signal can wake */
ssleep(2);                    /* sleep 2 seconds */
udelay(50);                   /* busy-wait 50 µs (cannot sleep) */
mdelay(2);                    /* busy-wait 2 ms (cannot sleep) */
usleep_range(50, 100);        /* sleep ~50–100 µs, can sleep */
schedule_timeout(jiffies);    /* low-level; you set the task state first */
```

Quick guide:

- **Process context, can sleep, exact delay not critical:** `msleep`.
- **Process context, can sleep, want to be killable:** `msleep_interruptible`.
- **Process context, sleeping but short:** `usleep_range`. Kernel may bundle short sleeps to reduce wake-ups.
- **Atomic context (IRQ handler, spinlock held):** `udelay` or `mdelay` only — these busy-wait. Do not `mdelay` more than ~10 ms — you stall every other task on a single-core system.
MCU bridge: Think of an IRQ like an EXTI/NVIC interrupt path, except Linux splits the hard interrupt from deferred work and must share lines across drivers.
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
- **Need to wait for a condition with a timeout:** `wait_event_interruptible_timeout`.

## 42.6  Tasks state machine

Quick sidebar on what "sleep" means.

A task in Linux has a state:

- `TASK_RUNNING` — on a CPU or in a runqueue waiting for one.
- `TASK_INTERRUPTIBLE` — sleeping. can be woken by a signal.
- `TASK_UNINTERRUPTIBLE` — sleeping. only the thing it's waiting for can wake it. (This is the dreaded "D state" you see in `ps`.)
- `TASK_KILLABLE` — uninterruptible but fatal signals (SIGKILL) wake it. Compromise between INT and UNINT.
- `TASK_STOPPED` — paused by SIGSTOP.
- `TASK_TRACED` — paused by ptrace.

`wait_event_interruptible` sets state to `TASK_INTERRUPTIBLE`. `wait_event` (no _interruptible) sets `TASK_UNINTERRUPTIBLE`. **Avoid `TASK_UNINTERRUPTIBLE`** for driver-level waits — if your driver bugs out, the user can't kill the stuck process. The system feels unresponsive, `kill -9` doesn't help, only reboot does.

Times where `TASK_UNINTERRUPTIBLE` is appropriate:
- Waiting for filesystem I/O.
- Waiting for a hardware operation that *must* complete (DMA finish, etc.).
MCU bridge: Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
- Holding important locks that signals could destabilize.

For chardev `read`/`write`, always use interruptible.

## 42.7  Lab

1. **Build and run the producer/waiting-read example.** Confirm blocking `read` waits 2 seconds for each event.
2. **Test `O_NONBLOCK`.** Open with `O_NONBLOCK | O_RDONLY`. verify `read` returns `-EAGAIN` immediately when no data.
3. **Implement and test `.poll`.** Write the `test_poll.c` from §42.4. Verify `select` correctly times out and wakes on events.
4. **Test signal handling.** Run `cat /dev/waiting` in a foreground process. While blocked, hit `Ctrl-C`. Confirm the process exits (returns `-ERESTARTSYS`, which `cat` translates to "interrupted").
5. **Replace `wait_event_interruptible` with `wait_event` (the uninterruptible variant).** Confirm Ctrl-C *doesn't* kill the reader. Use Ctrl-Z, then `kill -9 %1`. The process is unkillable. (This is the bug pattern. restore interruptible afterwards.)
6. **Add a writeable path.** Implement `.poll`'s `EPOLLOUT` for a fictional state ("buffer empty enough to accept more writes"). Test with `select` watching for writability.

## 42.8  Pitfalls

- **Race: condition check vs schedule.** If you write the pattern by hand instead of using `wait_event_interruptible`, you may have a window where the producer sets the condition, calls wake, and you fall asleep *after* the wake — sleeping forever. **Always use the `wait_event_*` macros.** They handle this race correctly.
- **Forgetting to wake.** Producer changes state but never calls `wake_up`. Reader sleeps forever. Symptom: works once (initial check passes), hangs after.
- **`wait_event` instead of `wait_event_interruptible` in `read`/`write` callbacks.** Process becomes unkillable when stuck. Always use interruptible variants in fops.
- **Returning `-EINTR` instead of `-ERESTARTSYS`.** Both are valid responses to a signal during a sleep, but `-ERESTARTSYS` causes the kernel to re-execute the syscall after the signal handler returns (if the signal handler permits). `-EINTR` returns the error directly to user-space, requiring the app to retry. Prefer `-ERESTARTSYS`. It's friendlier.
- **`poll_wait` called after returning the mask.** Order matters: register the wait first, then return the mask. Reverse it and the kernel may register no wait, so `select` busy-loops.
- **Calling `msleep` in an IRQ handler.** IRQ handlers are atomic. Use `udelay` or `mdelay` (busy-wait, no sleep), or schedule a workqueue/tasklet to do the sleeping work.
- **Memory-barrier wishful thinking.** Producer writes data buffer, then wakes. reader is woken, then reads buffer. The `wake_up` family has implicit barriers — wake_up implies a full barrier, and the woken task's resumption implies a barrier too. You usually don't need explicit `smp_wmb()`/`smp_rmb()`. But if you're doing fancy lockless work, double-check `Documentation/memory-barriers.txt`.

## 42.9  Going deeper

- **`Documentation/scheduler/sched-domains.rst`** — how the scheduler picks which CPU to wake a task on.
- **`Documentation/filesystems/poll.rst`** — the kernel's poll subsystem and how user-space `epoll` is implemented in terms of it.
- **`drivers/tty/`** — UART and TTY drivers. Real-world examples of mixed blocking-read + poll + ioctl driver code.
- **`drivers/input/evdev.c`** — the input-event chardev. Read it as a reference for poll-based event delivery.
- **LDD3 Chapter 6** — blocking I/O, still mostly accurate after all these years.

> Next chapter: **Chapter 43 — Interrupts.** With locking and waiting in place, we wire actual hardware events into the driver: `request_irq`, top-half/bottom-half split, tasklets, workqueues, threaded IRQs.
