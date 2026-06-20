# Chapter 2: What "Embedded Linux" actually is

> **What:** a mental model of an embedded Linux system, expressed in terms a microcontroller engineer already understands.
>
> **Why:** every later chapter assumes this vocabulary. If a term is still unclear at the end, review it before continuing.
>
> **Focus:** the **user/kernel split**. Once you understand it, most Linux behavior becomes easier to explain.


## 2.1  The system you already understand

Picture the firmware you wrote last year for a Cortex-M. After reset, the CPU jumps to the vector table at address `0x0`. The reset handler initializes RAM, clears `.bss`, copies `.data`, and calls `main()`. Inside `main()`, you set up clocks, peripherals, and an interrupt or two, then either spin in a `while(1)` loop or hand control to an RTOS scheduler that round-robins your tasks.

The system has the following properties:

- **One address space.** Every task, ISR, and variable shares one flat physical address space. A pointer contains an address in that shared map.
- **One privilege level in most projects.** Cortex-M has Thread mode and Handler mode, plus privileged and unprivileged execution. However, many MCU projects run all application code with privilege, so any task can access a peripheral register.
- **Cooperative or preemptive scheduling, but you wrote the scheduler** (or your RTOS vendor did) and you can read its source in an afternoon.
- **No filesystems**, or at most a thin layer over a flash translation library. "Open a file" was, in practice, "DMA a sector from this offset on the SD card".
- **Drivers were function calls.** `i2c_read(addr, buf, len)` resolved directly to bit-banging or writing to an I²C peripheral register.
- **The whole image was one ELF**, statically linked at link time, flashed once, runs forever.

Keep that picture in mind. The rest of this chapter compares which of those properties survive into embedded Linux and which do not.

## 2.2  The four layers

An embedded Linux system can be viewed as four software layers above the hardware. During boot, control moves from the Boot ROM to the bootloader, then to the kernel, which starts user-space programs:

```
   ┌──────────────────────────────────────────────────────────────┐
   │  Layer 4: User space                                         │
   │  shell, applications, daemons, your code                     │
   │  (lives in /bin, /sbin, /usr/bin, ...)                       │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 3: Linux kernel                                       │
   │  scheduler, MM, FS, drivers, network stack                   │
   │  (vmlinux, zImage)                                           │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 2: Bootloader  (U-Boot)                               │
   │  initialize DRAM, load kernel from SD/eMMC/network,          │
   │  pass control + device tree + cmdline                        │
   │  (u-boot.imx)                                                │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 1: Boot ROM  (on-chip mask ROM)                       │
   │  pin-strapping, read first sector, jump to bootloader        │
   │  (immutable, lives inside the SoC)                           │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 0: Hardware  (i.MX6ULL + DDR + peripherals)           │
   └──────────────────────────────────────────────────────────────┘
```

A few things to notice immediately.

**Layer 1 is not your code.** The Boot ROM is a small mask-programmed firmware that NXP burned into the silicon when the chip was fabricated. You cannot change it. You can only obey its expectations: present a boot image at the right offset, with the right signature header, on the boot device it is configured to read from. Chapter 7 is entirely about Layer 1.

**Layer 2 is the closest analogue to "your firmware" from the MCU world.** U-Boot is a small bare-metal C program. It runs without an MMU at first. It does its own clock and DDR setup. Its SD card and Ethernet drivers look much like the ones you wrote on the MCU. The difference is that U-Boot's job is to load and start Layer 3, not to *be* the application.

**Layer 3 is the kernel.** Once U-Boot transfers control, the kernel never returns. From that point on, it controls the hardware. Every interrupt now goes through the kernel. Every memory allocation goes through the kernel. Every peripheral access from anywhere outside the kernel goes through the kernel.

**Layer 4 is "user space".** This is where your application code, the shell, and the daemons live. From Layer 4's point of view, the hardware does not exist. You cannot, from a user-space program, write directly to a GPIO register and expect anything to happen. You ask the kernel.

The split between Layer 3 and Layer 4 is the most important idea in this chapter. Everything in Parts V and VI builds on it.

## 2.3  The user/kernel split, made concrete

In the MCU world, all code is privileged. In Linux, code runs in one of two modes:

- **Kernel mode** (also "supervisor", "EL1" on AArch64, "SVC mode" on ARMv7-A): full access to every peripheral, every memory address, every CPU instruction.
- **User mode** ("EL0", "USR mode" on ARMv7-A): cannot access kernel memory, cannot execute privileged instructions, cannot read or write peripheral registers directly.

This is not only a software convention. The CPU enforces it. If a user-mode instruction attempts to write to a protected kernel address, the CPU raises a hardware exception. The kernel handles the exception and normally terminates the offending process.

How does a user-mode program request I/O? It makes a **system call**, which is a controlled transition from user mode to kernel mode. On ARMv7-A, the `svc` instruction raises an SVC exception. The CPU switches to SVC mode and enters the kernel's exception handler. The kernel reads the syscall number from `r7` and the arguments from `r0`-`r6`.

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

Most application requests to the kernel take this shape. Reading a file uses `read()`. Allocating memory may use `brk()` or `mmap()`. Sleeping may use `nanosleep()`. To control an LED, an application may call `write()` on a device interface or use `ioctl()` on a device node. These operations cross the user/kernel boundary through syscalls.

In your MCU firmware, there were perhaps 50 functions in your driver library and you called them directly. In Linux, the **syscall is the interface** and there are roughly 400 of them. They are documented and you can run `man 2 <name>` on any Linux host to see it.

### Why the split exists

In an MCU system with one programmer and one application, the user/kernel split would only get in your way. So why does Linux insist on it?

Three reasons:

1. **Robustness.** A bug in a user-space process cannot scribble over kernel data structures or another process's memory. The process crashes. The system survives.
2. **Isolation between programs.** A fault or unauthorized access in one user-space process is less likely to damage the kernel or another process.
3. **Resource arbitration.** Many processes want the I²C bus, the CPU, the network. Someone must serialize and schedule. The kernel is that someone.

On a fully controlled embedded device, this separation may not always be necessary. Systems such as Zephyr and FreeRTOS serve that type of design. Linux uses the user/kernel split, so understanding it is necessary for working with Linux.

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

If a process touches a virtual address that is not mapped, the MMU raises a **page fault**. A page fault does not always mean a crash. It means the MMU could not complete the translation, so the kernel must decide how to handle the access.

The kernel may decide:

- This address is valid but not loaded yet, so allocate RAM and continue.
- This address belongs to a memory-mapped file, so read the needed file page and continue.
- This address is illegal for this process, so kill the process with a segmentation fault.

This is why each Linux process appears to have its own private, large address space. Physical RAM is assigned only when needed, and only through mappings the kernel permits.

You do not need to know the Linux APIs yet, but this one mechanism explains several features you will meet later:

- **Process isolation.** Process A cannot write into process B's memory because process A's page table does not contain process B's private pages.
- **Memory-mapped files.** `mmap()` is a syscall that makes a file look like memory. Instead of calling `read()` into a buffer, the program gets a pointer. When it touches that pointer, the kernel loads the needed part of the file.
- **fork().** `fork()` is a syscall that creates a new process by copying the current one. At first, Linux does not copy every RAM page. Parent and child share the same physical pages until one process writes. That delayed copy is called **copy-on-write**.
- **Shared libraries.** A library such as `libc.so` contains common code used by many programs. Linux can map the same physical code pages into many processes, while each process still has its own private stack and heap.
- **Swap.** Swap means the kernel can move idle memory pages out of RAM and onto storage, then bring them back later. Embedded systems often disable swap, but it uses the same page-table and page-fault machinery.

Now return to the i.MX6ULL IOMUXC register block at physical address `0x020E0000`. A normal user process does not automatically have that physical address in its page table. If the process tries to treat `0x020E0000` as a pointer, the MMU interprets it as a virtual address. Unless the kernel deliberately mapped that virtual page for the process, the access faults.

That is why a Linux application normally cannot write directly to GPIO, IOMUX, UART, or clock registers. The kernel owns those mappings. User space asks the kernel through a driver, a device node, sysfs, ioctl, or another syscall-based interface. The driver then performs the register access from kernel space.

You will spend Chapter 17 building, by hand, a minimal first-level page table on bare metal. After that, MMU behavior becomes much easier to reason about.

## 2.5  Processes, threads, and where they live

At minimum, an RTOS task is a function pointer plus a stack. The scheduler context-switches between tasks by saving and restoring registers and stack pointers.

A Linux **process** is much more. Each process owns:

- A unique **PID** (process ID).
- A **virtual address space** (its own page table).
- A set of **open file descriptors** (more on these in a moment).
- A **current working directory**, a user ID and group ID (**UID/GID**), signal handlers, resource limits, and other state visible under `/proc/<pid>/`.

A **thread** is a unit of scheduling inside a process. Multiple threads of the same process share its virtual address space and file descriptors. Linux implements threads as "tasks." Inside the kernel, processes and threads are both represented by `struct task_struct`. A process is the special case where the task has no thread-group siblings.

What about ISRs? In your MCU firmware, an ISR was a function whose stack might be the thread that was running when the interrupt fired, or a dedicated stack. In Linux, interrupts run in a **kernel-only context** with a small dedicated stack and very strict rules about what they may do (no sleeping, no blocking allocations, no calling functions that might sleep). Chapter 43 is entirely about this.

## 2.6  Vocabulary you must internalize

The following terms recur in every later chapter. Bookmark this section.

### File descriptor (fd)

A small non-negative integer returned by `open()`, `socket()`, `pipe()`, `eventfd()`, and friends. Every I/O syscall takes an fd as its first argument. Each process has its own fd table, mapping fd numbers to kernel objects (file, socket, pipe, device).

By convention, fd 0 is stdin, 1 is stdout, 2 is stderr. After that, the kernel hands out the lowest free number.

> **Why this is important:** Linux uses file descriptors as a common handle for regular files, serial ports, GPIO devices, network sockets, pipes, and many other kernel objects. The phrase "everything is a file" is approximate, but many interfaces use the same `read()`, `write()`, and `ioctl()` model.

### inode

The kernel's internal representation of a file. A directory entry maps a name to an inode. An inode holds the metadata (size, permissions, owner) and pointers to data blocks. A file may have multiple names (hard links) but only one inode. When you `open()` a path, the kernel resolves the path to an inode, then to a *file object*, then returns an fd that points at the file object.

### Virtual filesystem (VFS)

The kernel's abstraction layer that lets `read()` and `write()` work the same way on ext4, on FAT, on tmpfs, on procfs, and on devtmpfs. Each concrete filesystem implements a set of operations the VFS calls. Drivers also plug into VFS by exposing character or block devices.

### syscall, libc, glibc, musl

A **syscall** is a numbered kernel operation with arguments. On ARMv7-A, user space invokes it through `svc`. **libc** is the user-space C library that wraps syscalls in ordinary C functions. Two common libc implementations are glibc and musl. Embedded systems often use musl when a smaller runtime is useful. We will use both at different points.

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
> After a privileged command, verify that the expected device, service, or file appears before continuing. Roll back by undoing the configuration change or stopping the service enabled in the previous step.


A `.ko` file contains object code that can be loaded into a running kernel to add drivers or features. Load it with `insmod foo.ko` and unload it with `rmmod foo`. Module code runs in **kernel mode** with full privileges. It is kernel code stored in a separate object file, not user-space code. Chapters 36 onward cover kernel modules.

## 2.7  Linux storage and memory use

Linux has a reputation for being heavy. Let's quantify it for our target.

| Component | Approx. size on disk |
|----------|----------------------|
| `zImage` (compressed kernel) | 5-8 MB |
| Decompressed kernel in RAM | 12-20 MB |
| Device tree blob | 50 KB |
| Statically-linked BusyBox | 800 KB |
| musl libc shared object | 600 KB |
| glibc shared object | 2.0 MB |
| A "minimal" Buildroot rootfs (BusyBox + musl + a few utilities) | 4-8 MB |
| Memory the kernel uses for its own data | 30-60 MB |

A single-purpose embedded Linux system can fit in 64 MB of RAM and 32 MB of flash. The Point Atom MINI's 512 MB of DRAM is sufficient for the systems built in this book.

User-space libraries and frameworks can use more storage than the kernel. Common examples are glibc, the C++ runtime, Qt, and Python. This is why Yocto and Buildroot spend much of their work selecting and packaging user-space components.

## 2.8  What the rest of this book builds, in order

The following table shows the first major stages of the book and where each artifact belongs in the four-layer model.

| Chapter range | Layer | Artifact |
|--------------|-------|----------|
| 3-8 | host / 0 / 1 | Workspace and understanding of Boot ROM and IVT/DCD |
| 9-17 | **our bare-metal code** as a Layer 2 substitute | LED, DDR, and MMU. Your code performs the bootloader's early work. |
| 18 | optional | bare-metal I²C/SPI/LCD |
| 19-24 | Layer 2 | U-Boot from source, ported and understood |
| 25-30 | Layer 3 | Linux kernel built from source, booted and traced |
| 31-35 | Layer 4 | Root filesystem and user space, first by hand and then with Buildroot |
| 36-55 | Layer 3 | Device drivers and kernel subsystems |
| Later parts | all | Debugging, product development, build systems, security, and advanced topics |

If you only remember one diagram from this book, remember the four-layer stack from Section 2.2. Everything we do is somewhere on that stack, and the most common cause of confusion when an embedded Linux system misbehaves is mistakenly looking for the bug at the wrong layer.

## 2.9  Focus: re-read this if nothing else

- **Four layers**: Boot ROM, bootloader, kernel, user space. Memorize this stack.
- **User/kernel split**: every interaction between an application and the hardware passes through a syscall and runs, briefly, in kernel mode.
- **Virtual memory**: every process has its own address space. Physical and virtual are not the same. The MMU translates.
- **File descriptors**: the unified handle for everything I/O.
- **syscall, not function call**: the API between Layer 4 and Layer 3 is `svc`, not `bl`.

If any of those five points is still unclear, review the relevant section before moving to Chapter 3. The later labs assume this vocabulary.

## 2.10  Lab

This chapter is conceptual, so the lab is a short review. Answer the following questions in your own words without looking at the chapter:

1. Why can't a user-space program write directly to a GPIO register?
2. What does U-Boot do that the Boot ROM does not?
3. If you `cat /etc/hostname` on the target, list every syscall that probably happens.
4. What is the smallest possible Linux system that can print "hello" on the UART and exit? Sketch its components.
5. If you `insmod my_driver.ko` and the module dereferences a NULL pointer, does the whole system crash, the calling process crash, or neither?

Compare your answers against the chapter text and the references below.

## 2.11  Pitfalls

- **Confusing "embedded Linux" with "Linux on small hardware."** The kernel is the same. The kernel does not have an embedded mode. What differs is *user space*, leaner libc, fewer daemons, less storage, perhaps a read-only root. The kernel does not know your target is "embedded."
- **Assuming the bootloader and the kernel cooperate after handoff.** They do not. The bootloader stops running at `bootz`. The kernel does not call back into U-Boot. A few data values from U-Boot may remain in memory, but U-Boot code is no longer in control.
- **Believing `/proc/cpuinfo` always reflects physical hardware.** It reports what the kernel detected or was told through the device tree. A virtual machine such as QEMU may report virtual hardware instead.
- **Trying to debug user-space problems with kernel tools and vice versa.** Each layer has its own toolset. First identify which layer contains the bug, then choose tools for that layer.

## 2.12  Going deeper

- *The Design of the Unix Operating System*, Maurice Bach (1986). Old, but the chapters on the process model and VFS are still the cleanest explanation in print.
- *Linux Kernel Development*, Robert Love (3rd ed., 2010). Outdated in detail. Correct in spirit. Best high-level kernel tour.
- The "Anatomy of a Program" series on LWN.net.
- `man 2 intro`, `man 7 inode`, `man 7 fanotify`, `man 7 namespaces`. These manual pages explain the user-space interfaces.
- The Linux source tree's `Documentation/admin-guide/` and `Documentation/process/`.

> Next chapter: **Chapter 3: Host environment setup.** We prepare the build and debugging tools used by the rest of the book.
