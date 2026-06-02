---
chapter: 37
title: A character driver, by hand
part: VI — Driver development
estimated_pages: 20
status: draft
---

# Chapter 37 — A character driver, by hand

> **What:** a character device driver — the kind that backs `/dev/ttyS0`, `/dev/i2c-1`, `/dev/hidraw0`, and most other "stream of bytes you read and write" device files in `/dev/`. We'll build one from scratch: allocate a device number, register a `cdev`, hook up `open`/`read`/`write`/`release`, and copy data safely between user-space and kernel.
>
> **Why:** character drivers are how the vast majority of embedded peripheral drivers expose themselves to user-space. UARTs, GPIO chips, I²C/SPI controllers, sensors, fingerprint readers, sound cards' control interfaces — almost all are character devices under the hood. The pattern is identical every time; what changes is the body of `open` / `read` / `write`. Master the pattern in this chapter; everything in Part VI is variations on it.
>
> **Focus:** **the user/kernel boundary**. The single most common bug class in driver code is dereferencing a user-space pointer directly. `copy_to_user` and `copy_from_user` are not just safer — they are *correct*; a direct dereference will fault, silently corrupt, or be a security hole. By the end of this chapter the `__user` annotation should feel like a load-bearing part of every function signature.

## 37.1  The picture

When a process does `fd = open("/dev/hello", O_RDWR)` and then `write(fd, "hi", 2)`, this chain of events happens:

```
   user-space                kernel-space
   ──────────                ────────────
   write(fd, "hi", 2)
        │
        │  glibc wraps it,
        │  invokes SVC                 sys_write(fd, ...)
        │                                    │
        │                              VFS:  lookup file*
        │                                    │
        │                              dispatch to f_op->write
        │                                    │
        │                              your_driver_write(filp, buf, 2, &pos)
        │                                    │
        │                              copy_from_user(kbuf, buf, 2)
        │                                    │
        │                              do something useful
        │                                    │
        │                              return 2 (bytes written)
   2  ←───────────────────────────────  return up the stack
```

Your driver provides a **`file_operations`** struct. The kernel's VFS layer looks up the right `file_operations` for a given device number, then calls your function pointers. Everything else is plumbing.

What the user thinks is "writing to a file" is whatever your `write` callback decides to do — send UART bytes, toggle GPIOs, fill a buffer for next read. The "file" is a façade. You decide what's behind it.

## 37.2  Device numbers

A device file in `/dev/` has a **major** and **minor** number:

```
[root@pa-mini:~]# ls -l /dev/null /dev/ttymxc0 /dev/i2c-0
crw-rw-rw- 1 root root  1, 3 May 24  2026 /dev/null
crw--w---- 1 root tty 207, 0 May 24  2026 /dev/ttymxc0
crw-rw---- 1 root i2c  89, 0 May 24  2026 /dev/i2c-0
```

The two numbers after the size (`1, 3`, `207, 0`, `89, 0`) are *major, minor*. The kernel uses the major number to dispatch to the right driver; the driver uses the minor number to distinguish among devices that share the driver (e.g., `i2c-0`, `i2c-1`, `i2c-2`).

On Linux, the combined number is a 32-bit `dev_t`: 12 bits major, 20 bits minor. The split is opaque to most code; use the macros:

```c
dev_t devid = MKDEV(major, minor);
unsigned int maj = MAJOR(devid);
unsigned int min = MINOR(devid);
```

### Picking a major number — don't

The old way was to pick an unused major from a documented list (`Documentation/admin-guide/devices.txt`, the list of all officially registered major numbers). The modern way is to ask the kernel for one:

```c
dev_t devid;
int err = alloc_chrdev_region(&devid, 0, 1, "hello");
//                              ▲      ▲  ▲   ▲
//                              │      │  │   name shown in /proc/devices
//                              │      │  count of consecutive minors
//                              │      base minor (almost always 0)
//                              out: assigned dev_t
```

The kernel finds an unused major and returns the `dev_t` to you. Always prefer this for new drivers. Hard-coding majors is a 1990s pattern. Don't do it.

After `alloc_chrdev_region`, you'll see your device in `/proc/devices`:

```
[root@pa-mini:~]# cat /proc/devices
Character devices:
...
240 hello
...
```

When you unload the driver, balance this with `unregister_chrdev_region(devid, 1)`.

## 37.3  The `cdev` structure

A `cdev` is the kernel's representation of a character device. You build one in your driver and register it:

```c
#include <linux/cdev.h>

struct cdev mycdev;

cdev_init(&mycdev, &my_fops);   /* attach file_operations */
mycdev.owner = THIS_MODULE;
err = cdev_add(&mycdev, devid, 1);   /* register; now reachable */
```

After `cdev_add`, opening `/dev/hello` (assuming the device file exists with the right major/minor) routes through your `my_fops`. `cdev_init` and `cdev_add` are really one logical step. The kernel splits them so it can tell apart initialization from registration. Treat them as two lines next to each other.

To remove: `cdev_del(&mycdev)`.

## 37.4  The full structure of a chardev driver

Here's the canonical layout. Save as `hello_chrdev.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

#define HELLO_BUFSIZE  256

struct hello_dev {
    struct cdev cdev;
    dev_t devid;
    char *buffer;
    size_t buf_len;
    struct mutex lock;
};

static struct hello_dev *hd;

/* ─────────────────────────── file_operations ────────────────────────── */

static int hello_open(struct inode *inode, struct file *filp)
{
    struct hello_dev *dev = container_of(inode->i_cdev,
                                          struct hello_dev, cdev);
    filp->private_data = dev;
    pr_info("hello: open\n");
    return 0;
}

static int hello_release(struct inode *inode, struct file *filp)
{
    pr_info("hello: release\n");
    return 0;
}

static ssize_t hello_read(struct file *filp, char __user *ubuf,
                          size_t count, loff_t *ppos)
{
    struct hello_dev *dev = filp->private_data;
    ssize_t ret;

    if (mutex_lock_interruptible(&dev->lock))
        return -ERESTARTSYS;

    if (*ppos >= dev->buf_len) {
        ret = 0;   /* EOF */
        goto out;
    }
    if (*ppos + count > dev->buf_len)
        count = dev->buf_len - *ppos;

    if (copy_to_user(ubuf, dev->buffer + *ppos, count)) {
        ret = -EFAULT;
        goto out;
    }
    *ppos += count;
    ret = count;

out:
    mutex_unlock(&dev->lock);
    return ret;
}

static ssize_t hello_write(struct file *filp, const char __user *ubuf,
                           size_t count, loff_t *ppos)
{
    struct hello_dev *dev = filp->private_data;
    ssize_t ret;

    if (mutex_lock_interruptible(&dev->lock))
        return -ERESTARTSYS;

    if (count > HELLO_BUFSIZE)
        count = HELLO_BUFSIZE;

    if (copy_from_user(dev->buffer, ubuf, count)) {
        ret = -EFAULT;
        goto out;
    }
    dev->buf_len = count;
    *ppos = count;
    ret = count;

out:
    mutex_unlock(&dev->lock);
    return ret;
}

static const struct file_operations hello_fops = {
    .owner   = THIS_MODULE,
    .open    = hello_open,
    .release = hello_release,
    .read    = hello_read,
    .write   = hello_write,
};

/* ─────────────────────────── init / exit ────────────────────────────── */

static int __init hello_init(void)
{
    int err;

    hd = kzalloc(sizeof(*hd), GFP_KERNEL);
    if (!hd)
        return -ENOMEM;

    hd->buffer = kzalloc(HELLO_BUFSIZE, GFP_KERNEL);
    if (!hd->buffer) {
        err = -ENOMEM;
        goto free_dev;
    }
    mutex_init(&hd->lock);

    err = alloc_chrdev_region(&hd->devid, 0, 1, "hello");
    if (err)
        goto free_buf;

    cdev_init(&hd->cdev, &hello_fops);
    hd->cdev.owner = THIS_MODULE;

    err = cdev_add(&hd->cdev, hd->devid, 1);
    if (err)
        goto unreg_region;

    pr_info("hello: major=%d minor=%d  (mknod /dev/hello c %d 0)\n",
            MAJOR(hd->devid), MINOR(hd->devid), MAJOR(hd->devid));
    return 0;

unreg_region:
    unregister_chrdev_region(hd->devid, 1);
free_buf:
    kfree(hd->buffer);
free_dev:
    kfree(hd);
    return err;
}

static void __exit hello_exit(void)
{
    cdev_del(&hd->cdev);
    unregister_chrdev_region(hd->devid, 1);
    kfree(hd->buffer);
    kfree(hd);
    pr_info("hello: unloaded\n");
}

module_init(hello_init);
module_exit(hello_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hello character device");
```

That's 100-some lines. Let's pull out the four ideas that matter.

### Idea 1: `container_of` and `private_data`

```c
struct hello_dev *dev = container_of(inode->i_cdev, struct hello_dev, cdev);
filp->private_data = dev;
```

The inode passed to `open` knows it has a `cdev` inside it (`inode->i_cdev`). But what we *want* is the enclosing `hello_dev` struct that has all our state. `container_of` is the kernel's "given a pointer to a struct member, recover the pointer to the containing struct" macro. It's a compile-time trick — no runtime cost.

We stash the `hello_dev *` in `filp->private_data` so subsequent `read`/`write`/`release` calls can find it without redoing the lookup. **`filp->private_data` is the standard idiom** for per-open state.

### Idea 2: `__user` and copy_to/from_user

```c
static ssize_t hello_read(..., char __user *ubuf, ...)
{
    if (copy_to_user(ubuf, dev->buffer + *ppos, count))
        return -EFAULT;
}
```

The `__user` annotation on `ubuf` is a marker for `sparse` (a static analyzer) saying "this pointer is in user-space's address space; do not dereference it directly." On i.MX6ULL there is no MMU domain protection, so a direct dereference might *appear* to work. But it only works when the user buffer is paged in and reachable from kernel mode — not always the case. On systems with **PAN** (Privileged Access Never, an ARMv8 feature; not on i.MX6ULL but on many newer SoCs) a direct dereference faults immediately.

`copy_to_user` (and its sibling `copy_from_user`) do three things:
1. **Validate the address** is within user-space (`access_ok`).
2. **Handle page faults gracefully** — if the user-space page is paged out, the function brings it in.
3. **Return the number of bytes NOT copied**. Zero = success. Nonzero = partial copy. **Most drivers convert any nonzero result to `-EFAULT`.**

Don't bypass `copy_to/from_user`. If you find yourself thinking "I just need to peek at one byte," use `get_user(byte, p)` (single byte) or `put_user(byte, p)` (single write). Same safety guarantees, smaller code.

### Idea 3: Locking

```c
if (mutex_lock_interruptible(&dev->lock))
    return -ERESTARTSYS;
```

Multiple processes can have your device open at the same time. Two threads doing `write()` concurrently can race on `dev->buffer`. A `mutex` serializes them.

We use `mutex_lock_interruptible` rather than `mutex_lock`. The difference: if a signal is pending while we wait for the lock, `_interruptible` returns `-ERESTARTSYS` and the kernel rolls back the syscall so it can restart after the signal handler. `mutex_lock` (uninterruptible) can leave a process unkillable if the lock is held by a buggy other path.

`-ERESTARTSYS` is the conventional return code for "signal pending; please restart me." The VFS handles it correctly.

### Idea 4: Goto-based unwind

```c
err = alloc_chrdev_region(...);
if (err)
    goto free_buf;
err = cdev_add(...);
if (err)
    goto unreg_region;
...
unreg_region:
    unregister_chrdev_region(...);
free_buf:
    kfree(hd->buffer);
free_dev:
    kfree(hd);
    return err;
```

This `goto` cascade is **idiomatic kernel C**. Each label cleans up *exactly* what's been allocated up to that point. It is the kernel's idiomatic error-path style. After a dozen drivers it becomes natural. Read it carefully: each error-path target only does the cleanup for resources that were successfully acquired *before* this point.

## 37.5  Building, loading, testing

```sh
$ make
$ scp hello_chrdev.ko target:~
```

On the target:

```
[root@pa-mini:~]# insmod hello_chrdev.ko
[root@pa-mini:~]# dmesg | tail -1
hello: major=240 minor=0  (mknod /dev/hello c 240 0)

[root@pa-mini:~]# mknod /dev/hello c 240 0
[root@pa-mini:~]# echo "ping" > /dev/hello
[root@pa-mini:~]# cat /dev/hello
ping
```

It works. We wrote "ping" into the kernel buffer; `cat` read it back.

A few things to notice:

- The major number (240) is **whatever the kernel picked**. It's not stable across reboots. Next chapter, we'll automate device-file creation with udev/mdev so you don't have to `mknod` by hand.
- `echo "ping"` writes 5 bytes (4 + newline). `cat` reads all of them. Our buffer correctly tracks `buf_len`.
- Each new `cat` invocation gets a fresh open, so `*ppos` resets to 0. Within one `cat`, the first `read` returns 5 bytes and the second returns 0 (EOF).

## 37.6  Testing edge cases

| Test | Expected | Why |
|------|----------|-----|
| `dd if=/dev/zero of=/dev/hello bs=1M count=1` | Truncates to 256 bytes | Our `count > HELLO_BUFSIZE` clamp |
| `dd if=/dev/hello of=/dev/null bs=1` (after write) | Reads exactly `buf_len` bytes | Our `*ppos + count > buf_len` clamp |
| Two `cat /dev/hello > x &` in parallel | Both succeed, neither corrupts | Mutex serializes |
| Kill a stuck read with Ctrl-C | Returns immediately | `mutex_lock_interruptible` |
| `rmmod hello_chrdev` while a process has it open | "Resource busy" | `THIS_MODULE` owner causes refcount > 0 |

The last one is worth elaborating. Set `cdev.owner = THIS_MODULE`. The kernel auto-increments your module's reference count for every `open` on a device file under your `cdev`. As long as one process has `/dev/hello` open, `rmmod` refuses. This is the safety mechanism that prevents "user has fd open → driver unloaded → user's next read crashes" bugs.

## 37.7  `mknod` and why it's temporary

Notice we manually `mknod /dev/hello c 240 0` to create the device file. That's tedious and fragile:

- The major number is dynamic — pick by `alloc_chrdev_region` — but `mknod` requires you to know it.
- Reboots may renumber.
- On a tmpfs `/dev` (almost always true now; see Ch 32), the manually-`mknod`'d node disappears at reboot — you'd have to recreate it each boot.

Chapter 38 fixes this entirely: with `class_create` + `device_create`, the kernel **broadcasts a hot-plug event** when your driver loads, and udev (or mdev) creates the right file in `/dev/` automatically. Same when you unload: the file disappears.

For now, `mknod` is fine. Just know it's a stopgap.

## 37.8  Lab

1. **Build and load `hello_chrdev.ko`.** Confirm the buffer survives writes and reads as expected.
2. **Concurrency test.** Open two terminal sessions on the target. In each, run `while true; do echo "from-A" > /dev/hello; cat /dev/hello; done` (varying the strings). Watch for any garbled reads. Then remove the mutex from the code and rerun: garbled output now occurs.
3. **Bad pointer.** Pass a bogus pointer:
   ```c
   read(fd, (void *)0xFFFFFFFF, 100);
   ```
   Confirm that `copy_to_user` returns `-EFAULT` and the kernel doesn't crash.
4. **Static buffer size.** Try writing 300 bytes (more than `HELLO_BUFSIZE`). Confirm it truncates to 256 and `write` returns 256.
5. **Open with `O_RDONLY`.** Now try to `write`. What happens?
   - The VFS layer rejects it before reaching your driver. You can verify by `strace cat /dev/hello`: no `write()` syscall on a read-only fd would reach you anyway, but understanding *where* the rejection happens is useful.
6. **Inspect with `lsof`.** `lsof /dev/hello` lists all processes holding it open. Stop one such process; observe the open count drop.

## 37.9  Pitfalls

- **Forgetting `THIS_MODULE` in `cdev.owner` or `file_operations.owner`.** The kernel won't increment your module's refcount on open. `rmmod` while a process has the device open → kernel crashes when it tries to call into freed code. Always set both.
- **Calling user-space functions inside the kernel.** Kernel code does not have access to glibc. No `printf`, no `malloc`, no `memcpy_s`. Use `printk`/`pr_*`, `kmalloc`/`kfree`, `memcpy` (which exists in the kernel, slightly different optimisation profile).
- **Stack overflow.** Kernel stacks are **8 KB on ARM32 i.MX6ULL** (16 KB on x86_64 / arm64). Don't put large arrays on the stack. If you need a 4 KB scratch buffer, use `kmalloc(4096, GFP_KERNEL)` and free it at the end of the function.
- **Allocating with the wrong flag.** `kmalloc(..., GFP_KERNEL)` may sleep — fine in syscall context, not fine in interrupt context. In an IRQ handler, use `GFP_ATOMIC`. We'll cover this in Ch 43.
- **Returning the wrong type.** `read` and `write` return `ssize_t`. Don't return `int` (compile warning), don't return `size_t` (may hide negative values), and don't return success when you mean count.
- **Holding a mutex across `copy_to_user`.** `copy_to_user` can sleep (it may need to page in user memory). Sleeping while holding a mutex is fine in principle, but if you hold the mutex too long, every other reader/writer is blocked. For most chardevs this is acceptable.
- **Not handling `*ppos` correctly.** A misbehaving driver that ignores `*ppos` reads the buffer-from-the-start every read, leading `cat` into an infinite loop. Always advance `*ppos` by the number of bytes you returned.

## 37.10  Going deeper

- **`Documentation/filesystems/vfs.rst`** — how the VFS dispatches operations.
- **`Documentation/process/coding-style.rst`** — the kernel's coding standards; `checkpatch.pl` enforces them.
- **`drivers/char/mem.c`** — `/dev/null`, `/dev/zero`, `/dev/random`. Real chardev implementations in canonical style.
- **`drivers/char/misc.c`** — the misc device framework (next chapter — Ch 40); useful to read once you understand chardev basics.
- **LDD3 Chapter 3** — much more on the chardev driver model.

> Next chapter: **Chapter 38 — Auto-creating `/dev/` nodes.** With udev/mdev hot-plug, you stop calling `mknod` by hand. We add `class_create` and `device_create` to the driver.
