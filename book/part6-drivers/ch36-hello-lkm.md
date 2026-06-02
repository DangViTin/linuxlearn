---
chapter: 36
title: Your first kernel module
part: VI — Driver development
estimated_pages: 16
status: draft
---

# Chapter 36 — Your first kernel module

> **What:** the smallest possible Linux kernel module — a `.ko` file with an entry point, an exit point, and a license tag — and the build system (`Kbuild`) that turns C source into it. By the end you can `insmod hello.ko`, see your `printk` in `dmesg`, and `rmmod` it without rebooting.
>
> **Why:** every driver you'll ever write — character, block, network, platform, I²C, SPI, sound — is a kernel module at its core. The wrapper around the interesting code is the same: module_init / module_exit / MODULE_LICENSE. Master the trivial case once and the only thing left to learn for each subsystem is its own API.
>
> **Focus:** **what gets linked into what, and when**. `hello.ko` is a relocatable ELF that the kernel loader patches into the kernel's address space at insmod time. Understanding that — that there is no fresh process, no separate memory, just dynamic linking into the running kernel — explains 80 % of "why is this allowed?" and "why is that not?" questions.

## 36.1  The driver mindset shift

If your last decade was MCU work, the first thing to internalise is this:

| MCU firmware | Linux kernel module |
|--------------|---------------------|
| `main()` runs from reset | No `main()`; you register callbacks |
| Your code owns the CPU | Your code is invoked when the kernel decides |
| Stack is whatever you allocate | Stack is ~16 KB and shared with whoever called you |
| Memory is whatever flash holds | Memory comes from `kmalloc()` / `vmalloc()` |
| You print to a UART you set up | You call `printk` and it routes itself |
| Crash → board resets | Crash → kernel panics → user is unhappy |

A kernel module is a library that the kernel dynamically links into itself. The kernel calls your `module_init` once when loaded, and your `module_exit` once when unloaded. In between, your code waits, then runs when something calls into it — a system call, an interrupt, a work queue, a kthread, or whichever subsystem registered it.

This is more than a coding-style change. The failure modes change too. A wild pointer in firmware corrupts your `.bss`. A wild pointer in a kernel module corrupts the kernel itself. That can mean kernel threads, other drivers, or the scheduler — whatever happens to be running. A bug that would have been a crashed loop is now an unbootable system.

## 36.2  The smallest module that compiles

`hello.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/kernel.h>

static int __init hello_init(void)
{
    pr_info("hello: loaded\n");
    return 0;
}

static void __exit hello_exit(void)
{
    pr_info("hello: unloaded\n");
}

module_init(hello_init);
module_exit(hello_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("you@example.com");
MODULE_DESCRIPTION("Smallest possible kernel module");
MODULE_VERSION("0.1");
```

About twenty lines. Walk through each.

**Headers.**
- `<linux/init.h>` — defines `__init` and `__exit` macros, plus `module_init` and `module_exit`.
- `<linux/module.h>` — defines the `MODULE_*` metadata macros and ties into the module-loading infrastructure.
- `<linux/kernel.h>` — pulls in `printk`, `pr_info`, and friends.

Note **none** of these are `<stdio.h>` or `<stdlib.h>`. **The kernel has no libc.** `printf`, `malloc`, `strcmp` — all unavailable. The kernel provides its own versions, sometimes with the same name (`strcmp`), sometimes renamed (`kmalloc` instead of `malloc`, `printk` instead of `printf`).

**`__init` annotation.** `hello_init` is the function that runs when the module loads. Marking it `__init` tells the linker to put it in a special section (`.init.text`) that the kernel can **free** after the module has loaded. For a built-in module (statically linked into the kernel image), this means ~10 KB of init code is reclaimed once the system boots. For a `.ko`, the section is freed after `module_init` returns. **Implication:** code in `__init` functions can call other `__init` functions but not be called from runtime code. The linker warns if you violate this.

**Return value.** `hello_init` returns `int`. Returning 0 means "module loaded successfully." A negative `errno` (e.g., `-ENODEV`, `-EINVAL`) means "load failed" — the kernel unloads the module and `insmod` reports the error.

**`__exit` annotation.** Similar to `__init`: `.exit.text` is freed in the built-in case (since a built-in module is never unloaded). For a `.ko`, `module_exit` runs when `rmmod` is called.

**`module_init(hello_init)`.** This isn't a function call — it's a macro that expands to a special section entry telling the loader: "the entry point is `hello_init`." Without it, the loader can't find your code.

**`MODULE_LICENSE("GPL")`.** Without this, two things happen: the kernel taints itself (sets a "this kernel has loaded non-GPL code" flag visible in `dmesg` and `/proc/sys/kernel/tainted`), and **many GPL-only exported symbols become unavailable to your module.** If you try to call `gpiod_get` (which is `EXPORT_SYMBOL_GPL`) from a non-GPL module, you get `Unknown symbol gpiod_get`. There is no way around this short of using a GPL license tag. Other accepted strings: `"GPL v2"`, `"GPL and additional rights"`, `"Dual BSD/GPL"`, `"Dual MIT/GPL"`, `"Dual MPL/GPL"`, `"Proprietary"`.

**The rest of the `MODULE_*` macros** are just metadata. `modinfo hello.ko` displays them. They're not load-time gates (except `MODULE_LICENSE`).

## 36.3  The `Kbuild` Makefile

You don't compile a kernel module with `arm-linux-gnueabihf-gcc hello.c -o hello.ko`. Kbuild does a lot of work for you. It generates per-module ELF sections, applies the kernel's own `CFLAGS` (including `-fno-stack-protector` and many others), and dynamically discovers the right `vmlinux` symbols. You build out-of-tree modules by *invoking the kernel's own Makefile* and pointing at your source.

`Makefile`:

```makefile
obj-m += hello.o

# Path to the kernel source (must match the kernel we'll run on)
KDIR ?= /home/$(USER)/linux-imx6ull/build

# Architecture and cross-compiler for the target
ARCH         ?= arm
CROSS_COMPILE ?= arm-linux-gnueabihf-

all:
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(PWD) clean
```

Run:

```
$ make
make -C /home/you/linux-imx6ull/build M=/home/you/hello modules
  CC [M]  /home/you/hello/hello.o
  MODPOST /home/you/hello/Module.symvers
  CC [M]  /home/you/hello/hello.mod.o
  LD [M]  /home/you/hello/hello.ko
```

Five lines of `make` output. What happened:

1. **`CC [M] hello.o`** — your `hello.c` compiled to `hello.o`. Standard so far.
2. **`MODPOST`** — Module post-processing. This scans `hello.o` for **undefined symbols** (functions you call but didn't define — `printk`, in our case) and looks them up in the kernel's exported symbol table (`Module.symvers` from the kernel build). For each symbol it finds, it records the symbol's hash. If a symbol is **not** exported, modpost emits a warning. If a symbol is `EXPORT_SYMBOL_GPL` and you're not GPL, modpost emits a warning.
3. **`CC [M] hello.mod.o`** — modpost generates a small `hello.mod.c` containing version magic, module metadata, and symbol-version records. This compiles to `hello.mod.o`.
4. **`LD [M] hello.ko`** — final link. `hello.o` + `hello.mod.o` → `hello.ko`. The `.ko` is a **relocatable ELF**, not a shared object. The kernel does the relocations itself at load time.

Inspect the output:

```
$ file hello.ko
hello.ko: ELF 32-bit LSB relocatable, ARM, EABI5 version 1 (SYSV), ...

$ arm-linux-gnueabihf-readelf -h hello.ko | head -5
  Class:                             ELF32
  Data:                              2's complement, little endian
  Type:                              REL (Relocatable file)
  Machine:                           ARM

$ modinfo hello.ko
filename:       /home/you/hello/hello.ko
version:        0.1
description:    Smallest possible kernel module
author:         you@example.com
license:        GPL
srcversion:     ABCD1234EF567890
depends:
vermagic:       6.6.0 SMP mod_unload modversions ARMv7
```

The **`vermagic`** is critical. It encodes the exact kernel version (`6.6.0`) and the config options that affect binary compatibility (`SMP`, `mod_unload`, etc.). When you `insmod hello.ko`, the kernel compares `hello.ko`'s vermagic to its own. If they differ, the load is refused. You can't take a module built against 6.6.0 and load it on 6.6.1, even if the API is identical. This is a feature, not a bug — it prevents subtle ABI breakage.

## 36.4  Loading and unloading

Copy `hello.ko` to the target. Then on the target:

```
[root@pa-mini:~]# insmod hello.ko
[root@pa-mini:~]# dmesg | tail -1
[   42.123456] hello: loaded

[root@pa-mini:~]# lsmod
Module                  Size  Used by
hello                  16384  0

[root@pa-mini:~]# rmmod hello
[root@pa-mini:~]# dmesg | tail -1
[   50.234567] hello: unloaded
```

That's the whole loop. The module is now part of the kernel's address space; its code is reachable via the symbol table.

**`/sys/module/hello/`** exposes runtime information:

```
[root@pa-mini:~]# ls /sys/module/hello/
coresize      holders       initsize    refcnt    srcversion    uevent
initsize      initstate     notes/      sections/ taint         version
```

- `refcnt` — how many other things use this module. As long as it's > 0, `rmmod` refuses.
- `srcversion` — hash of the source; useful for detecting "did I actually copy the new build?"
- `sections/` — load address of each section. Useful when debugging crashes; you need the section addresses to symbolicate addresses in the `dmesg` backtrace.
- `taint` — does this module taint the kernel?

**`/proc/modules`** has the same info but flatter, suitable for scripting.

## 36.5  Module parameters

Hardcoding settings is fine for "hello world" but real drivers need to be tunable. Linux gives you `module_param`:

```c
#include <linux/moduleparam.h>

static int howmany = 1;
static char *whom = "world";

module_param(howmany, int, 0644);
MODULE_PARM_DESC(howmany, "Number of greetings");

module_param(whom, charp, 0644);
MODULE_PARM_DESC(whom, "Who to greet");

static int __init hello_init(void)
{
    int i;
    for (i = 0; i < howmany; i++)
        pr_info("hello, %s\n", whom);
    return 0;
}
```

The third argument to `module_param` is the **permission** for the sysfs file at `/sys/module/hello/parameters/howmany`. `0644` means readable by all, writable by root. `0` means not exposed in sysfs at all.

Use at load time:

```
[root@pa-mini:~]# insmod hello.ko howmany=3 whom=earth
[root@pa-mini:~]# dmesg | tail -3
[  ... ] hello, earth
[  ... ] hello, earth
[  ... ] hello, earth
```

Or change at runtime via sysfs:

```
[root@pa-mini:~]# cat /sys/module/hello/parameters/whom
earth
[root@pa-mini:~]# echo mars > /sys/module/hello/parameters/whom
[root@pa-mini:~]# cat /sys/module/hello/parameters/whom
mars
```

Note: writing to the sysfs file **does not re-run `hello_init`.** It just updates the variable. Your driver's runtime code needs to read the variable each time to see the new value.

Supported types: `bool`, `byte`, `short`, `ushort`, `int`, `uint`, `long`, `ulong`, `charp` (a `char *`), and arrays via `module_param_array`.

## 36.6  `printk` and its message levels

`printk` is `printf`'s kernel cousin. The signature is the same; the difference is that the first character of the format string (a special `KERN_*` byte) sets the **message level**. There are eight levels:

| Macro | Value | Used for |
|-------|-------|----------|
| `KERN_EMERG` | 0 | System is unusable, panic imminent |
| `KERN_ALERT` | 1 | Action must be taken immediately |
| `KERN_CRIT` | 2 | Critical conditions (e.g., hard hardware errors) |
| `KERN_ERR` | 3 | Error conditions (driver init failed, etc.) |
| `KERN_WARNING` | 4 | Warnings (the default — unmarked `printk` uses this) |
| `KERN_NOTICE` | 5 | Normal but significant |
| `KERN_INFO` | 6 | Informational (load/unload, link up, etc.) |
| `KERN_DEBUG` | 7 | Debug noise |

Modern code uses the convenience wrappers, which are clearer:

```c
pr_emerg("...");      // KERN_EMERG
pr_alert("...");      // KERN_ALERT
pr_crit("...");
pr_err("...");
pr_warn("...");
pr_notice("...");
pr_info("...");
pr_debug("...");
```

`pr_debug` is special: it expands to a `printk` only if `DEBUG` is defined when the file is compiled, **or** if dynamic debug (`CONFIG_DYNAMIC_DEBUG`) is enabled and the user has turned this site on at runtime. We use it heavily; dynamic debug is one of the most underused gems of kernel development.

What you see in `dmesg` depends on the **console log level**. Read it:

```
[root@pa-mini:~]# cat /proc/sys/kernel/printk
4    4    1    7
```

Four numbers: current console log level, default for unmarked messages, minimum allowed, boot default. The console shows messages with priority **lower than or equal to** the first number — so `4` means levels `0`–`3` print to console, levels `4`–`7` only go to the ring buffer. Raise it:

```
[root@pa-mini:~]# echo 8 > /proc/sys/kernel/printk
```

Now everything prints to console. Useful for debugging. Noisy in production.

## 36.7  Lab

1. **Build and load `hello.ko`** on the target. Verify in `dmesg` and `/sys/module/hello/`.
2. **Add a module parameter** named `name` (string) defaulting to `"world"`. Load with `insmod hello.ko name=mainline`. Verify it prints.
3. **Tweak the parameter at runtime** via `/sys/module/hello/parameters/name`. Note that the value changes but `hello_init` is not re-run.
4. **Add `pr_debug` calls** and enable dynamic debug for your module:
   ```sh
   echo "module hello +p" > /sys/kernel/debug/dynamic_debug/control
   ```
   Confirm your debug messages now print, without rebuilding.
5. **Crash the kernel intentionally** (don't do this on a production system). Add `*(int *)0 = 0;` to `hello_init`. Build, load, observe the `Oops`. Note: this is recoverable on i.MX6ULL — the module fails to load, kernel reports the BUG, but the system continues. (On other archs and with `CONFIG_PANIC_ON_OOPS=y`, the kernel will panic.)
6. **Decode the Oops trace.** Look at the PC register and the symbol-section addresses in `/sys/module/hello/sections/`. Confirm the crash address falls inside your module.

## 36.8  Pitfalls

- **`vermagic` mismatch.** "Module hello: version magic '...' should be '...'" The two strings are right there — diff them. Usually you built against the wrong kernel tree, or the running kernel was updated and you haven't rebuilt.
- **`Unknown symbol foo (err -2)`.** A function you reference isn't exported by the running kernel. `nm hello.ko | grep " U "` shows your undefined references; `cat /proc/kallsyms | grep foo` shows what the kernel has. The fix is usually: GPL-license the module, or pick a different API.
- **`__init` data referenced at runtime.** Compile warning: "section mismatch." Your `__init` function called by something that lives in `.text` (runtime). Either drop the `__init` annotation or restructure so the call only happens during init.
- **Forgetting `MODULE_LICENSE`.** Build succeeds; modpost warns "missing MODULE_LICENSE"; load fails with "taints kernel" and many APIs unavailable. Always include it.
- **Out-of-tree modules and kernel upgrades.** Your `hello.ko` is tied to one exact kernel build. Plan for either rebuilding the module each time you rebuild the kernel, or adopt **DKMS** (Dynamic Kernel Module Support) which rebuilds automatically on kernel upgrade. For an embedded product with a fixed kernel, just build once and ship the `.ko` alongside `zImage`.
- **`rmmod` says "Resource busy".** Something is using your module. The `refcnt` in `/sys/module/<name>/refcnt` tells you how many; the `holders/` directory inside lists which other modules reference yours. You can't unload until they all go away.
- **`insmod` says nothing, but `dmesg` does.** `insmod` only reports errors to stderr. The success or failure detail (and any `printk` calls from your init function) go to the kernel log. Always check `dmesg` after every load.

## 36.9  Going deeper

- **`Documentation/kbuild/modules.rst`** — the canonical reference for the out-of-tree module build system.
- **`Documentation/admin-guide/dynamic-debug-howto.rst`** — turn `pr_debug` calls on and off at runtime, by module, file, line, or function. Indispensable.
- **`Linux Device Drivers, 3rd edition`** (LDD3, Corbet/Rubini/Kroah-Hartman) — old but still the best long-form introduction to kernel modules. Chapters 2 and 3 cover modules and char devices.
- **`Documentation/process/submitting-patches.rst`** — when your driver is good enough to upstream.
- **`scripts/checkpatch.pl`** — run it on every change. Catches whitespace, style, and many common bugs.

> Next chapter: **Chapter 37 — A character driver, by hand.** With a module that loads, we add the `file_operations` plumbing so user-space can `open`, `read`, `write`, and `close` `/dev/hello`.
