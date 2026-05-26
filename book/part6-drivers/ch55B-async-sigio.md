---
chapter: 55B
title: Async notification (SIGIO / fasync)
part: VI — Driver development (supplementary v1.1)
estimated_pages: 8
status: draft
---

# Chapter 55B — Async notification (SIGIO)

> **What:** the **fasync / SIGIO** mechanism — a driver tells its user-space process "data is ready" by sending it a Unix signal, instead of the process polling or blocking on read. The driver implements `.fasync` in `file_operations`; user-space arms it with `fcntl(fd, F_SETOWN, getpid()); fcntl(fd, F_SETFL, O_ASYNC);`.
> **Why:** for very rare events ("button pressed" or "thermal alarm"), forcing user-space to `poll()` continuously or block on `read()` is wasteful. SIGIO lets the application do other things; the signal arrives when something happens. Linux's input layer doesn't use it (poll/epoll is preferred), but legacy POSIX-style apps and some custom devices do.
> **Focus:** **registers a process for delivery; driver triggers**. The driver maintains a `fasync_struct`; when an event happens, it calls `kill_fasync` and the kernel sends the registered process a SIGIO.

## 55B.1  Driver side

Add `.fasync` to your `file_operations`:

```c
#include <linux/fs.h>

struct my_priv {
    struct fasync_struct *fasync;
    /* ... */
};

static int my_fasync(int fd, struct file *filp, int mode)
{
    struct my_priv *p = filp->private_data;
    return fasync_helper(fd, filp, mode, &p->fasync);
}

static const struct file_operations my_fops = {
    .owner   = THIS_MODULE,
    /* ... */
    .fasync  = my_fasync,
};

/* When an event occurs (e.g., IRQ → data ready): */
static void notify_userspace(struct my_priv *p)
{
    if (p->fasync)
        kill_fasync(&p->fasync, SIGIO, POLL_IN);
}

/* In release(): */
static int my_release(struct inode *inode, struct file *filp)
{
    my_fasync(-1, filp, 0);    /* clean up the fasync registration */
    return 0;
}
```

`fasync_helper(fd, filp, mode, &list)` manages the list of registered processes. `kill_fasync(&list, signal, band)` sends the signal to every registered process.

## 55B.2  User-space side

```c
#include <fcntl.h>
#include <signal.h>
#include <unistd.h>

static volatile sig_atomic_t got_event;

static void on_sigio(int sig)
{
    got_event = 1;
}

int main(void)
{
    int fd = open("/dev/myevent", O_RDONLY);

    /* Register our signal handler */
    struct sigaction sa = {0};
    sa.sa_handler = on_sigio;
    sigaction(SIGIO, &sa, NULL);

    /* Tell the kernel: send signals to *this* process */
    fcntl(fd, F_SETOWN, getpid());

    /* Enable async notification */
    int flags = fcntl(fd, F_GETFL);
    fcntl(fd, F_SETFL, flags | O_ASYNC);

    while (1) {
        pause();    /* sleep until any signal arrives */
        if (got_event) {
            char buf[64];
            int n = read(fd, buf, sizeof(buf) - 1);
            buf[n] = 0;
            printf("event: %s\n", buf);
            got_event = 0;
        }
    }
}
```

Three steps: install signal handler → `F_SETOWN` declares who gets the signal → `F_SETFL | O_ASYNC` enables it.

## 55B.3  When to use SIGIO (and when not to)

**Use when**:
- The event is rare (≤ a few per second).
- The application is already signal-handling (legacy code).
- Polling overhead would be wasteful.

**Don't use when**:
- Events come at > ~100 Hz (signal delivery is expensive).
- You can use `poll()` / `select()` / `epoll` instead — those are more efficient and don't have signal-handler restrictions.
- You need to know *which* fd fired (SIGIO carries the band but not the fd unless you use `F_SETSIG` for realtime signals with `siginfo`).

For modern code, `poll()` / `epoll` are preferred for everything. SIGIO is a "good to know it exists" mechanism more than a "use this often" mechanism.

## 55B.4  Lab

1. **Add SIGIO** to the button driver from Ch 45. Confirm a user-space process receives SIGIO when the button is pressed.
2. **Compare against poll().** Write two equivalent programs — one with SIGIO, one with `poll()`. Profile CPU and latency.
3. **F_SETSIG for SI_FD.** Use a realtime signal (`SIGRTMIN+1`) with `F_SETSIG`; receive `siginfo->si_fd` to know which fd fired.

Commit code to `code/ch55B-sigio/`.

## 55B.5  Pitfalls

- **Signal handler doing too much.** Signal handlers run in arbitrary context; only async-signal-safe functions allowed. Set a flag; do real work in the main loop.
- **Forgetting `F_SETOWN`.** Without it, the kernel doesn't know who to signal.
- **Race: signal arrives before sigaction installed.** Install handler before opening the device.
- **Signal merging.** If your driver fires SIGIO twice before user-space handles either, only one delivery happens. User-space must drain whatever was queued, not just respond to "one event."
- **`fasync_helper(-1, ...)` not called in release.** Stale fasync entry; later signals go to a dead pid.

## 55B.6  Going deeper

- **`Documentation/admin-guide/cgroup-v2.rst`** (no, just kidding) — the relevant kernel docs are sparse; use LDD3 Chapter 6 and `man 2 fcntl`.
- **`drivers/char/`** — many older char drivers use SIGIO.
- **`kernel/signal.c`**, **`fs/fcntl.c`** — implementation.

> Next chapter: **Chapter 55C — CAN + FlexCAN.** SocketCAN, kernel framework, FlexCAN driver, transceivers.
