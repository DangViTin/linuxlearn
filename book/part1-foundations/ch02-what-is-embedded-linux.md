# Chapter 2: What "Embedded Linux" actually is

> **What:** a mental model of an embedded Linux system, expressed in terms a microcontroller engineer already understands.
>
> **Why:** every later chapter assumes this vocabulary. If a term is still unclear at the end, review it before continuing.
>
> **Focus:** the **user/kernel split**. Once you understand it, most Linux behavior becomes easier to explain.


## 2.1  The system you already understand

Picture the firmware you wrote last year for a Cortex-M. At reset, the CPU obtains an initial stack pointer and reset-handler address from the device's reset vector arrangement; the vector table is data, not code to execute. The reset mapping depends on the device. The reset handler initializes RAM, clears `.bss`, copies `.data`, and calls `main()`. Your application then loops or starts an RTOS scheduler, often priority-based with optional round-robin scheduling between equal-priority tasks.

The system has the following properties:

- **One address space.** Every task, ISR, and variable shares one flat physical address space. A pointer contains an address in that shared map.
- **One privilege level in most projects.** Cortex-M has Thread mode and Handler mode, plus privileged and unprivileged execution. However, many MCU projects run all application code with privilege, so any task can access a peripheral register.
- **Cooperative or preemptive scheduling.** Tasks commonly share an address space even when an RTOS manages their execution.
- **A filesystem may already exist.** FatFS and littlefs provide real file abstractions. Linux's difference is not the invention of files, but process isolation and a kernel-controlled common resource model.
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
   │  select device, find image header, load bootloader           │
   │  (immutable, lives inside the SoC)                           │
   ├──────────────────────────────────────────────────────────────┤
   │  Layer 0: Hardware  (i.MX6ULL + DDR + peripherals)           │
   └──────────────────────────────────────────────────────────────┘
```

A few things to notice immediately.

**Layer 1 is not your code.** The Boot ROM is a small mask-programmed firmware that NXP burned into the silicon when the chip was fabricated. You cannot change it. You can only obey its expectations: present a boot image at the right offset, with the right signature header, on the boot device it is configured to read from. Chapter 7 is entirely about Layer 1.

**Layer 2 is the closest analogue to "your firmware" from the MCU world.** U-Boot is a small bare-metal C program. It runs without an MMU at first. It does its own clock and DDR setup. Its SD card and Ethernet drivers look much like the ones you wrote on the MCU. The difference is that U-Boot's job is to load and start Layer 3, not to *be* the application.

**Layer 3 is the kernel.** After the usual U-Boot handoff, Linux controls scheduling, memory mappings, and hardware access. An allocator may serve `malloc()` from memory already obtained, without a syscall for each allocation. Similarly, a driver may map a device or buffer into a process; subsequent loads and stores use that mapping without a syscall for each access.

**Layer 4 is "user space".** Applications, shells, and daemons normally ask drivers for services through system calls. They do not automatically have peripheral registers mapped into their address spaces. The kernel decides which interfaces and mappings a process may use.

The split between Layer 3 and Layer 4 is the most important idea in this chapter. Everything in Parts V and VI builds on it.

## 2.3  The user/kernel split, made concrete

Many MCU projects run all application code privileged, though Cortex-M and some RTOS designs support unprivileged tasks. For this introduction, distinguish Linux user execution from privileged kernel execution:

- **Kernel execution:** privileged ARMv7-A modes, including SVC and IRQ, with access to system-control operations and kernel mappings. AArch64's EL1 is comparison terminology, not a mode on this board.
- **User mode** ("EL0", "USR mode" on ARMv7-A): cannot access kernel memory, cannot execute privileged instructions, cannot read or write peripheral registers directly.

This is not only a software convention. The CPU enforces it. If a user-mode instruction attempts to write to a protected kernel address, the CPU raises a hardware exception. The kernel handles the exception and normally terminates the offending process.

**Root is not kernel mode.** `sudo picocom` gives a user-space process root credentials so it can open a restricted serial device. Its ordinary instructions still run in user mode. A syscall enters the kernel temporarily; `sudo` does not turn the program into kernel code. Whether a device needs `sudo` depends on Linux permissions, not an inherent requirement of hardware.

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

A **process** contains one or more **threads**. Each thread has its own registers, stack, and execution state. Threads in one process share its virtual address space and file descriptors. Linux represents each schedulable thread as a task with a `struct task_struct`; a multithreaded process is still a process.

What about ISRs? A Linux **hard interrupt handler** runs in kernel interrupt context and must not sleep or make blocking allocations. Its stack arrangement depends on architecture and configuration. A threaded interrupt handler has different rules because it runs in a schedulable kernel thread. Chapter 43 explains that distinction.

## 2.6  Vocabulary you must internalize

The following terms recur in every later chapter. Bookmark this section.

### File descriptor (fd)

A small non-negative integer identifying an open kernel object. `open()`, `socket()`, and `eventfd()` return descriptors; `pipe()` fills an array with two descriptors. Many operations on an already-open object take its fd as their first argument. Each process has an fd table mapping numbers to objects such as files, sockets, pipes, and devices.

By convention, fd 0 is stdin, 1 is stdout, 2 is stderr. After that, the kernel hands out the lowest free number.

> **Why this is important:** Linux uses file descriptors as a common handle for regular files, serial ports, GPIO devices, network sockets, pipes, and many other kernel objects. The phrase "everything is a file" is approximate, but many interfaces use the same `read()`, `write()`, and `ioctl()` model.

### inode

The kernel's representation of a filesystem object, including metadata such as type, permissions, and owner. How it locates content depends on the filesystem; a procfs entry need not have disk blocks. Directory entries map names to inodes, and hard links can give one inode multiple names. An open *file object* additionally records state such as the current offset; an fd refers to that open object.

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

This is a simplified path when stdout is a UART terminal. Buffering and the selected libc can change the calls. The libc and kernel implementations are available as source; Chapter 28 follows kernel startup, while the driver chapters explain device operations.

### Process tree, init

When the kernel starts user space, it runs the selected init program: commonly `/sbin/init` on a mounted root filesystem, or `/init` in an initramfs. This is PID 1, the root of the ordinary user-space process tree, not the ancestor of kernel threads. If the system's PID 1 exits, the kernel panics. BusyBox init and systemd are two possible implementations. In Chapter 29, a small statically-linked PID 1 prints a message and deliberately reboots rather than returning normally.

### Kernel module (LKM)

A `.ko` file contains object code that can be loaded into a running kernel to add drivers or features. Load it with `insmod foo.ko` and unload it with `rmmod foo`. Module code runs in **kernel mode** with full privileges. It is kernel code stored in a separate object file, not user-space code. Chapters 36 onward cover kernel modules.

## 2.7  Linux storage and memory use

Linux has a reputation for being heavy. Let's quantify it for our target.

These are example ranges, not measured requirements for every kernel configuration. Storage means file size; RAM means runtime use.

| Component | Resource | Approximate size |
|----------|----------|------------------|
| `zImage` (compressed kernel) | Storage | 5-8 MB |
| Decompressed kernel | RAM | 12-20 MB |
| Device tree blob | Storage | 50 KB |
| Statically-linked BusyBox | Storage | 800 KB |
| musl libc shared object | Storage | 600 KB |
| glibc shared object | Storage | 2.0 MB |
| Small Buildroot rootfs (BusyBox + musl + utilities) | Storage | 4-8 MB |
| Kernel data and allocations | RAM | 30-60 MB |

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
- **User/kernel split**: applications normally use driver interfaces through syscalls. The kernel controls permissions and mappings; mapped buffers or devices can then be accessed with memory instructions.
- **Virtual memory**: every process has its own address space. Physical and virtual are not the same. The MMU translates.
- **File descriptors**: the unified handle for everything I/O.
- **syscall, not function call**: the API between Layer 4 and Layer 3 is `svc`, not `bl`.

If any of those five points is still unclear, review the relevant section before moving to Chapter 3. The later labs assume this vocabulary.

## 2.10  Lab

This chapter is conceptual, so the lab is a short review. Answer the following questions in your own words without looking at the chapter:

1. Why can't a user-space program write directly to a GPIO register?
2. What does U-Boot do that the Boot ROM does not?
3. Which principal file-I/O operations let `cat /etc/hostname` copy a file to stdout? Ignore loader and process-startup calls.
4. Sketch a minimal Linux system whose PID 1 prints "hello" on the UART and stays alive or deliberately reboots. Why must it not just return from `main()`?
5. How does a user-space NULL-pointer fault differ from a kernel-module fault? Why can the module fault not be promised harmless? Do not deliberately crash your host to investigate.

### Answer checks

1. A physical register address is not automatically mapped into the process. The kernel must authorize a driver interface or mapping.
2. U-Boot provides board initialization and loading facilities beyond the ROM's device/image contract: for example, loading Linux and passing its device tree and command line.
3. Open the input, read bytes, write bytes to stdout, then close the input. Exact syscall names and startup calls depend on the binary and libc.
4. Hardware, a suitable bootloader, kernel, and a root filesystem/initramfs containing PID 1 are enough for this demonstration. PID 1 must remain alive or request a deliberate shutdown/reboot; an ordinary exit causes a panic.
5. A user fault is normally contained to that process. A kernel fault may produce an *oops* (a kernel fault report), terminate the current task, or cause a *panic* that stops the system, depending on context and policy. Corrupted kernel state can affect other work even when execution continues.

## 2.11  Pitfalls

- **Confusing "embedded Linux" with "Linux on small hardware."** The kernel is the same. The kernel does not have an embedded mode. What differs is *user space*, leaner libc, fewer daemons, less storage, perhaps a read-only root. The kernel does not know your target is "embedded."
- **Assuming the bootloader and the kernel cooperate after handoff.** They do not. The bootloader stops running at `bootz`. The kernel does not call back into U-Boot. A few data values from U-Boot may remain in memory, but U-Boot code is no longer in control.
- **Believing `/proc/cpuinfo` always reflects physical hardware.** It reports what the kernel detected or was told through the device tree. A virtual machine such as QEMU may report virtual hardware instead.
- **Trying to debug user-space problems with kernel tools and vice versa.** Each layer has its own toolset. First identify which layer contains the bug, then choose tools for that layer.

## 2.12  Going deeper

- *The Design of the Unix Operating System*, Maurice Bach (1986). Old, but the chapters on the process model and VFS are still the cleanest explanation in print.
- *Linux Kernel Development*, Robert Love (3rd ed., 2010). Outdated in detail. Correct in spirit. Best high-level kernel tour.
- The "Anatomy of a Program" series on LWN.net.
- Start with `man 2 intro`, `man 2 open`, `man 2 read`, `man 2 mmap`, and `man 7 pthreads`. See [mmap(2)](https://man7.org/linux/man-pages/man2/mmap.2.html) and [pthreads(7)](https://man7.org/linux/man-pages/man7/pthreads.7.html) for the mapping and shared-resource distinctions above.
- The Linux source tree's `Documentation/admin-guide/` and `Documentation/process/`.

> Next chapter: **Chapter 3: Host environment setup.** We prepare the build and debugging tools used by the rest of the book.
