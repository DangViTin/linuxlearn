---
chapter: 2
title: What "Embedded Linux" actually is
part: I — Foundations
estimated_pages: 14
status: draft
---

# Chapter 2: What "Embedded Linux" actually is

> **What:** a mental model of an embedded Linux system, expressed in terms a microcontroller engineer already understands.
>
> **Why:** every later chapter assumes this vocabulary. If a word from this chapter is fuzzy at the end, the rest of the book will be twice as hard.
>
> **Focus:** the **user/kernel split**. Once you have it, most of Linux stops looking strange.


## 2.1  The system you already understand

Picture the firmware you wrote last year for a Cortex-M. After reset, the CPU jumps to the vector table at address `0x0`. The reset handler initializes RAM, clears `.bss`, copies `.data`, and calls `main()`. Inside `main()`, you set up clocks, peripherals, and an interrupt or two, then either spin in a `while(1)` loop or hand control to an RTOS scheduler that round-robins your tasks.

The system has the following properties:

- **One address space.** Every task, every ISR, every variable shares one flat physical address space. A pointer is just an integer. whatever it points at is what you get.
- **One privilege level (effectively).** Cortex-M has Thread mode and Handler mode, and Privileged vs Unprivileged execution, but most projects run everything privileged. If a task wanted to poke a peripheral register, it just did. The hardware did not stop it.
- **Cooperative or preemptive scheduling, but you wrote the scheduler** (or your RTOS vendor did) and you can read its source in an afternoon.
- **No filesystems**, or at most a thin layer over a flash translation library. "Open a file" was, in practice, "DMA a sector from this offset on the SD card".
- **Drivers were function calls.** `i2c_read(addr, buf, len)` resolved directly to bit-banging or writing to an I²C peripheral register.
- **The whole image was one ELF**, statically linked at link time, flashed once, runs forever.

Hold that picture in mind. The rest of this chapter is a careful walk through which of those properties survive into embedded Linux and which do not.

## 2.2  The four layers

An embedded Linux system, viewed from boot, is a chain of four programs that run one after the other, each handing control to the next:

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Layer 4 — User space                                        │
   │  shell, applications, daemons, your code                     │
   │  (lives in /bin, /sbin, /usr/bin, ...)                       │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 3 — Linux kernel                                      │
   │  scheduler, MM, FS, drivers, network stack                   │
   │  (vmlinux, zImage)                                           │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 2 — Bootloader  (U-Boot)                              │
   │  initialize DRAM, load kernel from SD/eMMC/network,          │
   │  pass control + device tree + cmdline                        │
   │  (u-boot.imx)                                                │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 1 — Boot ROM  (on-chip mask ROM)                      │
   │  pin-strapping, read first sector, jump to bootloader        │
   │  (immutable; lives inside the SoC)                           │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 0 — Hardware  (i.MX6ULL + DDR + peripherals)          │
   └──────────────────────────────────────────────────────────────┘
```

A few things to notice immediately.

**Layer 1 is not your code.** The Boot ROM is a small mask-programmed firmware that NXP burned into the silicon when the chip was fabricated. You cannot change it. You can only obey its expectations: present a boot image at the right offset, with the right magic header, on the boot device it is configured to read from. Chapter 7 is entirely about Layer 1.

**Layer 2 is the closest analogue to "your firmware" from the MCU world.** U-Boot is a small bare-metal C program. It runs without an MMU at first. It does its own clock and DDR setup. its SD card and Ethernet drivers look much like the ones you wrote on the MCU. The difference is that U-Boot's job is to load and start Layer 3, not to *be* the application.

**Layer 3 is the kernel.** Once U-Boot transfers control, the kernel never returns. From that point on, it owns the hardware. Every interrupt now goes through the kernel. every memory allocation goes through the kernel. every peripheral access from anywhere outside the kernel goes through the kernel.

**Layer 4 is "user space".** This is where your application code, the shell, and the daemons live. From Layer 4's point of view, the hardware does not exist. You cannot, from a user-space program, write directly to a GPIO register and expect anything to happen. You ask the kernel.

The split between Layer 3 and Layer 4 is the most important idea in this chapter. Everything in Parts V and VI builds on it.

## 2.3  The user/kernel split, made concrete

In the MCU world, all code is privileged. In Linux, code runs in one of two modes:

- **Kernel mode** (also "supervisor", "EL1" on AArch64, "SVC mode" on ARMv7-A): full access to every peripheral, every memory address, every CPU instruction.
- **User mode** ("EL0", "USR mode" on ARMv7-A): cannot access kernel memory, cannot execute privileged instructions, cannot read or write peripheral registers directly.

This is not a software convention, the CPU enforces it. If a user-mode instruction attempts to write to a kernel address, the CPU raises a fault, a real hardware exception, indistinguishable from a Cortex-M MemManage fault and the kernel's exception handler kills the offending process.

How then does a user-mode program ever ask for I/O? Through a **system call**, a controlled transition from user mode to kernel mode. On ARMv7-A, the `svc` instruction (formerly `swi`) raises an SVC exception. The CPU switches to SVC mode, jumps to the exception handler, and the kernel decides what to do based on the syscall number in `r7` and arguments in `r0`–`r6`.

```
    user-space process            kernel
    ───────────────────────       ──────────────────────────
    fd = open("/dev/i2c-0",..)
        ↓ glibc wrapper builds
        ↓ syscall args
        svc #0        ────────►   exception handler
                                  → sys_openat()
                                  → kernel parses path
                                  → finds i2c_dev driver
                                  → driver's .open() runs
                                  → returns fd
                       ◄────────  return from exception
    fd in r0, back in user mode
```

Every interaction between an application and the kernel takes this shape, no exceptions. Reading a file uses `read()`. Allocating memory uses `brk()` or `mmap()`. Sleeping uses `nanosleep()`. All are syscalls. Writing to the LED? You may use `write()` against a sysfs file, or `ioctl()` against a device node, or `mmap()` a memory region, but each is a syscall.

In your MCU firmware, there were perhaps 50 functions in your driver library and you called them directly. In Linux, the **syscall is the interface** and there are roughly 400 of them. They are documented and you can run `man 2 <name>` on any Linux host to see it.

### Why the split exists

In an MCU system with one programmer and one application, the user/kernel split would only get in your way. So why does Linux insist on it?

Three reasons:

1. **Robustness.** A bug in a user-space process cannot scribble over kernel data structures or another process's memory. The process crashes. The system survives.
2. **Multi-tasking with multi-trust.** You can run code you do not fully trust, third-party binaries, scripts, even a network service exposed to the internet without it being able to compromise the rest of the system.
3. **Resource arbitration.** Many processes want the I²C bus, the CPU, the network. Someone must serialize and schedule. The kernel is that someone.

You will hear engineers occasionally argue that on a *fully controlled* embedded device, the split is overkill. They are not wrong in principle, Zephyr and FreeRTOS exist for exactly that case. But once you adopt Linux, you adopt the split, and embracing it makes the rest of the system easier, not harder.

## 2.4  Virtual memory, in one section

On an MCU, an address is usually simple:

```c
*(volatile uint32_t *)0x020E0000 = value;
```

If the reference manual says the IOMUXC register is at `0x020E0000`, your firmware writes to `0x020E0000`. The CPU puts that address on the bus. The peripheral responds.

Linux changes this model.

With the MMU enabled, a user-space pointer is usually a **virtual address**, not a direct physical bus address. Before the CPU can load or store memory, the MMU translates:

```text
virtual address used by the program
        |
        v
MMU looks in the current process page table
        |
        v
physical address in RAM or in a device register block
```

The important part is "current process". Each process has its own address map. The same virtual address can mean different physical memory in different processes.

```
Process A:
  virtual 0x00010000  -> physical RAM for process A's code
  virtual 0x000B0000  -> physical RAM for process A's data
  virtual 0xBE000000  -> physical RAM for process A's stack

Process B:
  virtual 0x00010000  -> physical RAM for process B's code
  virtual 0x000A0000  -> physical RAM for process B's data
  virtual 0xBE000000  -> physical RAM for process B's stack
```

Both processes may use a pointer like `0x00010000`, but they are not touching the same bytes. The MMU uses the page table for the currently running process, so `0x00010000` in process A and `0x00010000` in process B can translate to different physical pages.

The **page table** is the data structure that describes this translation. You can think of it as a map owned by the kernel:

```text
For process A:
  virtual page X -> physical page Y, readable and executable
  virtual page Z -> physical page W, readable and writable
  some pages     -> not mapped at all
```

If a process touches a virtual address that is not mapped, the MMU raises a **page fault**. A page fault does not always mean a crash. It means "the MMU could not complete this translation; kernel, please decide what to do."

The kernel may decide:

- This address is valid but not loaded yet, so allocate RAM and continue.
- This address belongs to a memory-mapped file, so read the needed file page and continue.
- This address is illegal for this process, so kill the process with a segmentation fault.

This is why Linux can give each process the illusion that it owns a private, large address space. Physical RAM is assigned only when needed, and only through mappings the kernel permits.

You do not need to know the Linux APIs yet, but this one mechanism explains several features you will meet later:

- **Process isolation.** Process A cannot write into process B's memory because process A's page table does not contain process B's private pages.
- **Memory-mapped files.** `mmap()` is a syscall that makes a file look like memory. Instead of calling `read()` into a buffer, the program gets a pointer. When it touches that pointer, the kernel loads the needed part of the file.
- **fork().** `fork()` is a syscall that creates a new process by copying the current one. At first, Linux does not copy every RAM page. Parent and child share the same physical pages until one process writes. That delayed copy is called **copy-on-write**.
- **Shared libraries.** A library such as `libc.so` contains common code used by many programs. Linux can map the same physical code pages into many processes, while each process still has its own private stack and heap.
- **Swap.** Swap means the kernel can move idle memory pages out of RAM and onto storage, then bring them back later. Embedded systems often disable swap, but it uses the same page-table and page-fault machinery.

Now return to the i.MX6ULL IOMUXC register block at physical address `0x020E0000`. A normal user process does not automatically have that physical address in its page table. If the process tries to treat `0x020E0000` as a pointer, the MMU interprets it as a virtual address. Unless the kernel deliberately mapped that virtual page for the process, the access faults.

That is why a Linux application normally cannot write directly to GPIO, IOMUX, UART, or clock registers. The kernel owns those mappings. User space asks the kernel through a driver, a device node, sysfs, ioctl, or another syscall-based interface. The driver then performs the register access from kernel space.

You will spend Chapter 17 building, by hand, a minimal first-level page table on bare metal. After that the MMU stops being a black box.

## 2.5  Processes, threads, and where they live

An RTOS task is, mechanically, a function pointer plus a stack. The scheduler context-switches between tasks by saving and restoring registers and stack pointers.

A Linux **process** is much more. Each process owns:

- A unique **PID** (process ID).
- A **virtual address space** (its own page table).
- A set of **open file descriptors** (more on these in a moment).
- A **current working directory**, a **uid/gid**, a **set of signal handlers**, a **resource-limits table**, and roughly fifty other things you can `cat` from `/proc/<pid>/`.

A **thread** is a unit of scheduling inside a process. Multiple threads of the same process share its virtual address space and file descriptors. Linux implements threads as "tasks", internally, the kernel does not strongly distinguish processes and threads. both are `struct task_struct`. A process is the special case where the task has no thread-group siblings.

What about ISRs? In your MCU firmware, an ISR was a function whose stack might be the thread that was running when the interrupt fired, or a dedicated stack. In Linux, interrupts run in a **kernel-only context** with a small dedicated stack and very strict rules about what they may do (no sleeping, no blocking allocations, no calling functions that might sleep). Chapter 43 is entirely about this.

## 2.6  Vocabulary you must internalize

The following terms recur in every later chapter. Bookmark this section.

### File descriptor (fd)

A small non-negative integer returned by `open()`, `socket()`, `pipe()`, `eventfd()`, and friends. Every I/O syscall takes an fd as its first argument. Each process has its own fd table, mapping fd numbers to kernel objects (file, socket, pipe, device).

By convention, fd 0 is stdin, 1 is stdout, 2 is stderr. After that, the kernel hands out the lowest free number.

> **Why this is important:** in Linux, *almost everything*, a regular file, a serial port, a GPIO chip, a network socket, a kernel-event source, is accessed through a file descriptor. "Everything is a file" is the slogan. The slogan is approximate, but the operational truth is "everything is reachable through a uniform API that takes an fd."

### inode

The kernel's internal representation of a file. A directory entry maps a name to an inode. an inode holds the metadata (size, permissions, owner) and pointers to data blocks. A file may have multiple names (hard links) but only one inode. When you `open()` a path, the kernel resolves the path to an inode, then to a *file object*, then returns an fd that points at the file object.

### Virtual filesystem (VFS)

The kernel's abstraction layer that lets `read()` and `write()` work the same way on ext4, on FAT, on tmpfs, on procfs, and on devtmpfs. Each concrete filesystem implements a set of operations the VFS calls. Drivers also plug into VFS by exposing character or block devices.

### syscall, libc, glibc, musl

A **syscall** is the kernel entry point: an integer + arguments, invoked via `svc`. **libc** is the user-space C library that wraps syscalls into ordinary C functions. glibc and musl are two implementations of libc. embedded systems often prefer musl for size and licensing reasons. We will use both at different points.

When you call `printf()` from a C program, the path is roughly:

```
printf("hi\n")
   → glibc formats the string into a buffer
   → glibc calls write(1, buf, 3)
       → glibc's write() wrapper places 1, buf, 3 into registers
       → executes svc #0 with syscall number for write
           → kernel exception handler
               → sys_write()
                   → VFS layer
                       → tty driver's write callback
                           → UART register access
```

Eight layers between your `printf` and the UART register, and every one of them is auditable source code in Linux. We will read through this stack in Chapter 28.

### Process tree, init

When the kernel finishes booting, it runs `/sbin/init` (or whatever you pass as `init=` in the cmdline). That process has PID 1 and is the ancestor of every other process. If it dies, the kernel panics. In the simplest embedded Linux systems, `init` is a BusyBox binary running a shell script in `/etc/init.d/rcS`. In systemd-based systems, it is the systemd PID-1 daemon. In our Chapter 29 initramfs experiments, it is a single statically-linked binary that prints "hello" and reboots.

### Kernel module (LKM)

> **Privilege boundary:** $ means normal user. # or sudo means root and can change host or target state.
> After a privileged command, verify the expected device, service, or file appears before continuing. Roll back by undoing the config change or stopping the service you just enabled.


A `.ko` file: object code that can be loaded into the running kernel at runtime to add drivers or features. Loading is `insmod foo.ko`. unloading is `rmmod foo`. The module's code runs in **kernel mode** with full privileges. It is not "user-space code that the kernel runs", it is genuinely a piece of kernel code that happens to live in a separate object file. Chapter 36 onwards are all about LKMs.

## 2.7  How big Linux is, and where the size hides

Linux has a reputation for being heavy. Let's quantify it for our target.

| Component | Approx. size on disk |
|----------|----------------------|
| `zImage` (compressed kernel) | 5–8 MB |
| Decompressed kernel in RAM | 12–20 MB |
| Device tree blob | 50 KB |
| Statically-linked BusyBox | 800 KB |
| musl libc shared object | 600 KB |
| glibc shared object | 2.0 MB |
| A "minimal" Buildroot rootfs (BusyBox + musl + a few utilities) | 4–8 MB |
| Memory the kernel uses for its own data | 30–60 MB |

A workable single-purpose embedded Linux system can fit, comfortably, in 64 MB of RAM and 32 MB of flash. The Point Atom MINI's 512 MB of DRAM is luxurious by these standards. By the time we get to Chapter 29 we will boot, log in, and run commands with most of the RAM unused.

The size that surprises people is *not* the kernel. It is the user-space libraries (especially glibc and the C++ runtime if pulled in) and any high-level frameworks (Qt, Python). The kernel itself is small. This is why Yocto and Buildroot spend most of their effort on user space: that is where the bytes go.

## 2.8  What the rest of this book builds, in order

To anchor the next 62 chapters, here is the rough trajectory and where each artifact lives in the four-layer model.

| Chapter range | Layer | Artifact |
|--------------|-------|----------|
| 3–8 | host / 0 / 1 | Workspace; understanding of Boot ROM and IVT/DCD |
| 9–17 | **own bare-metal** at Layer 2 substitute | LED → DDR → MMU; you become the bootloader |
| 18 | optional | bare-metal I²C/SPI/LCD |
| 19–24 | Layer 2 | U-Boot from source, ported, understood |
| 25–30 | Layer 3 | Linux kernel built from source, booted, traced |
| 31–35 | Layer 4 | Root filesystem and user space, hand-built and then Buildroot-built |
| 36–55 | Layer 3 | Drivers, the whole catalog |
| 56–58 | all | Debugging at every layer |
| 59 | all | Capstone: your own board |
| 60–63 | tools | Toolchain, Yocto, secure boot, OTA |
| 64 | — | What to read next |

If you only remember one diagram from this book, remember the four-layer stack from Section 2.2. Everything we do is somewhere on that stack, and the most common cause of confusion when an embedded Linux system misbehaves is mistakenly looking for the bug at the wrong layer.

## 2.9  Focus: re-read this if nothing else

- **Four layers**: Boot ROM, bootloader, kernel, user space. Memorize this stack.
- **User/kernel split**: every interaction between an application and the hardware passes through a syscall and runs, briefly, in kernel mode.
- **Virtual memory**: every process has its own address space. physical and virtual are not the same. The MMU translates.
- **File descriptors**: the unified handle for everything I/O.
- **syscall, not function call**: the API between Layer 4 and Layer 3 is `svc`, not `bl`.

If any of those five bullets is still cloudy after this chapter, re-read the relevant section before moving to Chapter 3. The labs from Chapter 8 onward assume all five.

## 2.10  Lab

This chapter has no lab, it is conceptual. The "lab" is that you should now be able to answer the following, in your own words, without looking anything up:

1. Why can't a user-space program write directly to a GPIO register?
2. What does U-Boot do that the Boot ROM does not?
3. If you `cat /etc/hostname` on the target, list every syscall that probably happens.
4. What is the smallest possible Linux system that can print "hello" on the UART and exit? Sketch its components.
5. If you `insmod my_driver.ko` and the module dereferences a NULL pointer, does the whole system crash, the calling process crash, or neither?

Compare your answers against the chapter text and the references below.

## 2.11  Pitfalls

- **Confusing "embedded Linux" with "Linux on small hardware."** The kernel is the same. The kernel does not have an embedded mode. What differs is *user space*, leaner libc, fewer daemons, less storage, perhaps a read-only root. The kernel does not know your target is "embedded."
- **Assuming the bootloader and the kernel cooperate after handoff.** They do not. The bootloader vanishes at `bootz`. The kernel does not call back into U-Boot, except as a curiosity (`bdinfo` data lives on, but that is all).
- **Believing `/proc/cpuinfo` reflects hardware reality.** It reflects what the kernel was *told* (via DT and detection). Lies are possible, and useful, for QEMU.
- **Trying to debug user-space problems with kernel tools and vice versa.** Each layer has its own toolset (Chapter 56–58). Knowing which layer your bug lives in is half the battle.

## 2.12  Going deeper

- *The Design of the Unix Operating System*, Maurice Bach (1986). Old, but the chapters on the process model and VFS are still the cleanest explanation in print.
- *Linux Kernel Development*, Robert Love (3rd ed., 2010). Outdated in detail. correct in spirit. Best high-level kernel tour.
- The "Anatomy of a Program" series on LWN.net.
- `man 2 intro`, `man 7 inode`, `man 7 fanotify`, `man 7 namespaces` — Linux's man pages are excellent.
- The Linux source tree's `Documentation/admin-guide/` and `Documentation/process/`.

> Next chapter: **Chapter 3 — Host environment setup.** We stop philosophizing and start installing packages.
