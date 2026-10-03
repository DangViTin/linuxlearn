# Chapter 2: What "Embedded Linux" actually is

Suppose you want to turn on an LED. In a familiar MCU project, your application calls a GPIO function, and that function writes a register. On Linux, an application normally asks a driver to do the job. The register is still there, and someone still writes it, but the route from your C code to that register has changed.

Why put more software in the way of such a small operation? To answer that, we need to look at what Linux is responsible for. We will start with the firmware model you know, then follow the changes that let several independent programs share one board.

## 2.1  The system you already understand

Think back to the startup code in a Cortex-M project. At reset, the CPU obtains its initial stack pointer and reset-handler address from the device's vector arrangement. The vector table contains those values; it is not itself a sequence of instructions. The reset handler prepares RAM, copies `.data`, clears `.bss`, and calls `main()`. Your program then enters its main loop or starts an RTOS scheduler.

In a typical project, the application, its drivers, and the RTOS are linked into one image. Tasks may have different stacks and priorities, but they commonly share one physical address space. If a task passes a buffer pointer to an I2C driver, both use the same address to reach the same bytes.

Most such projects also let application code access peripheral registers directly. Cortex-M does support privileged and unprivileged execution, and an MPU can add protection on parts that have one, but many projects do not use that separation. A call such as `i2c_read(addr, buf, len)` goes straight into the driver's code.

You may already have a filesystem through FatFS or littlefs, a network stack, and several RTOS tasks. Linux does not make those ideas new. The larger change is how it separates programs and controls their access to shared resources. Keep the shared MCU address space in mind as we examine that change.

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

Read the diagram from the bottom upward. Each stage prepares enough of the machine for the next one to run.

**The Boot ROM runs first.** NXP puts this small firmware inside the chip during manufacture. We cannot replace it, so our first image must use the header and placement it expects. Chapter 7 explains that format and how the ROM finds our code.

**The bootloader prepares and loads the system.** We use U-Boot. Its early code configures clocks and DDR, and its drivers can fetch files from storage or the network. Much of this will look familiar from MCU work. Its destination, however, is another program: the Linux kernel. In Part II, our own small bare-metal programs temporarily occupy this place in the boot sequence.

**The kernel manages the running system.** Once U-Boot hands over control, Linux schedules work, manages memory, and controls access to devices. Drivers are part of this layer. They turn requests such as "send these bytes" into the register operations needed by a particular UART or network controller.

**User space is where applications run.** It includes your program, the shell, and background services, often called *daemons*. These programs use interfaces provided by the kernel rather than assuming that every peripheral register is available to them.

Boot ROM, bootloader, kernel, and user space are separate pieces, even when a vendor distributes them in one image. For the LED question at the start of the chapter, the boundary we care about is the last one: how does an application ask a kernel driver to act?

## 2.3  The user/kernel split, made concrete

On our Linux system, application instructions and kernel instructions run with different CPU privileges. The Cortex-A7 calls ordinary application execution **USR mode**. Kernel exception handlers use privileged modes such as **SVC** and **IRQ**; Chapter 4 explains those names in detail.

- **Kernel execution** can use privileged system-control operations and kernel memory mappings.
- **User execution** cannot use privileged instructions or access protected kernel memory. An application also has no automatic mapping of peripheral registers; the kernel decides which interfaces or mappings it may use.

The CPU enforces this distinction. A user instruction that tries to write to protected kernel memory causes an exception, rather than completing the write. The kernel handles that exception and normally terminates the offending process. We will meet processes shortly; for now, think of one as a running application with its own resources.

There are two different meanings of privilege here. **Root** is a Linux user identity, while **kernel mode** describes CPU execution. Later, `sudo picocom` gives the serial-terminal program root credentials so it can open a restricted device. The program still runs in user mode. Its credentials are checked when it asks the kernel for access; `sudo` does not turn it into a driver. This is also why the need for `sudo` comes from device permissions, not from a rule that hardware always needs root.

An application requests a kernel service through a **system call**, usually shortened to *syscall*. On ARMv7-A, the `svc` instruction raises a Supervisor Call exception. The CPU enters the kernel handler in SVC mode, where Linux reads the syscall number from `r7` and its arguments from `r0`-`r6`. After handling the request, the kernel returns a result to the application.

Here is a simplified path for opening an I2C device. The application sees an ordinary C function; the library wrapper performs the transition into the kernel:

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

Not every C function needs a syscall every time it runs. `malloc()` can reuse memory the library already obtained, for example. If a driver authorizes a memory mapping, later loads and stores through that mapping do not each require a syscall. The kernel sets up and controls the access; it does not have to execute every instruction on the application's behalf.

Linux documents its syscall interfaces in section 2 of the manual. On a Linux host, `man 2 read` opens the description of `read()`. You do not need to learn the syscall list now. First understand the request, the transition into the kernel, and the return to the caller.

### Why the split exists

For one tightly controlled firmware image, direct calls may be exactly what you want. Linux is designed to run independent programs on the same machine. A shell, a network service, and your application may all want CPU time, memory, and access to a device. Separation gives the kernel a way to manage that situation:

1. **Robustness.** A bad pointer in an ordinary application is normally contained by its mappings and permissions, rather than overwriting kernel data or another program's private memory.
2. **Isolation between programs.** A fault or unauthorized access in one user-space process is less likely to damage the kernel or another process.
3. **Resource arbitration.** Many processes want the I²C bus, the CPU, the network. Someone must serialize and schedule. The kernel is that someone.

There are good reasons to choose a smaller RTOS for a controlled application. Our subject here is Linux, so we need to understand the separation it uses rather than treating it as an extra driver-library call.

## 2.4  Virtual memory, in one section

On an MCU, an address is usually simple:

```c
*(volatile uint32_t *)0x020E0000 = value;
```

If the reference manual says the IOMUXC register is at `0x020E0000`, your firmware writes to `0x020E0000`. The CPU puts that address on the bus. The peripheral responds.

Now try to carry that same pointer into a Linux application. What does the number mean there?

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

The important detail is the current process. Each process has its own address map, so two applications can use the same pointer value without reaching the same physical bytes. The following addresses are illustrative, not a required Linux memory layout:

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

When process A is running, its mapping gives `0x00010000` one meaning. When process B runs, its mapping can give that number another meaning. This is how each application can work with its own code, globals, and stack without calculating where every other application lives in physical RAM.

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

This also separates an address range from the RAM currently backing it. A process can have a valid range for which physical pages are supplied as needed. The kernel decides whether a fault can be resolved or whether the access must be rejected.

Several later Linux features build on this mechanism. Treat the names below as examples of where the idea leads, not as APIs to memorize before Chapter 3:

- **Process isolation.** Process A cannot write into process B's memory because process A's page table does not contain process B's private pages.
- **Memory-mapped files.** `mmap()` is a syscall that makes a file look like memory. Instead of calling `read()` into a buffer, the program gets a pointer. When it touches that pointer, the kernel loads the needed part of the file.
- **fork().** `fork()` is a syscall that creates a new process by copying the current one. At first, Linux does not copy every RAM page. Parent and child share the same physical pages until one process writes. That delayed copy is called **copy-on-write**.
- **Shared libraries.** A library such as `libc.so` contains common code used by many programs. Linux can map the same physical code pages into many processes, while each process still has its own private stack and heap.
- **Swap.** Swap means the kernel can move idle memory pages out of RAM and onto storage, then bring them back later. Embedded systems often disable swap, but it uses the same page-table and page-fault machinery.

Now return to the i.MX6ULL IOMUXC register block at physical address `0x020E0000`. A normal user process does not automatically have that physical address in its page table. If the process tries to treat `0x020E0000` as a pointer, the MMU interprets it as a virtual address. Unless the kernel deliberately mapped that virtual page for the process, the access faults.

So the physical GPIO or UART address from the manual is not automatically a usable application pointer. The normal route is through a driver interface. The application asks for an operation, and the driver uses the mappings and register access appropriate to the hardware. That answers the LED question without making the GPIO itself any less familiar.

You will spend Chapter 17 building, by hand, a minimal first-level page table on bare metal. After that, MMU behavior becomes much easier to reason about.

## 2.5  Processes, threads, and where they live

An RTOS task gives you a familiar starting point: execution needs registers, a stack, and scheduler state. In Linux, that execution is a **thread**. A **process** groups one or more threads together with the resources they share.

A process has:

- A unique **PID** (process ID).
- A **virtual address space** (its own page table).
- A set of **open file descriptors** (more on these in a moment).
- A **current working directory**, a user ID and group ID (**UID/GID**), signal handlers, resource limits, and other state visible under `/proc/<pid>/`.

Threads within the process share its address space and file descriptors, but each has its own registers, stack, and execution state. Linux represents a schedulable thread as a task with a `struct task_struct`. The distinction is useful: two threads in one application can share a global variable directly, while two independent processes need an agreed sharing mechanism.

What about ISRs? A Linux **hard interrupt handler** runs in kernel interrupt context and must not sleep or make blocking allocations. Its stack arrangement depends on architecture and configuration. A threaded interrupt handler has different rules because it runs in a schedulable kernel thread. Chapter 43 explains that distinction.

## 2.6  Names you will meet in the next chapters

We now have a place for the remaining names: some describe the handles applications use, some describe the kernel's internal objects, and some describe the files we build. You can return to this section when a name appears in a later lab.

### File descriptor (fd)

When an application opens a file or a device, it needs a way to refer to that open object in later requests. Linux gives it a **file descriptor**, a small non-negative integer. The descriptor belongs to the process's fd table; it is not the device's register address.

`open()`, `socket()`, and `eventfd()` return descriptors, while `pipe()` fills an array with two of them. Later calls such as `read(fd, ...)` tell the kernel which open object to use. That object may be a regular file, a socket, a pipe, or a device.

By convention, fd 0 is stdin, 1 is stdout, 2 is stderr. After that, the kernel hands out the lowest free number.

This common handle explains the phrase "everything is a file." The phrase is not literally true, but many interfaces use the same `read()`, `write()`, and `ioctl()` model. A serial port and a text file behave differently, yet an application can refer to each through an fd.

### inode

A filename is how we look something up. An **inode** is the kernel's representation of the filesystem object, including its type, permissions, and owner. Directory entries connect names to inodes, and hard links allow several names to refer to one inode.

Keep this separate from an open file. An open *file object* records state such as the current offset, and an fd refers to that open object. How an inode locates content depends on the filesystem; a procfs entry, for instance, need not correspond to blocks on a disk.

### Virtual filesystem (VFS)

An application should not need a different read function for every filesystem. The **VFS** provides the common kernel interface above ext4, FAT, tmpfs, procfs, and devtmpfs. Each filesystem supplies operations that the VFS calls. Character and block devices also connect to this framework, which is why a device can appear in a file-oriented interface.

### syscall, libc, glibc, musl

The C functions in your application are not the kernel itself. **libc**, the user-space C library, implements standard C facilities and wraps many syscalls in ordinary function calls. Glibc and musl are two implementations we will encounter. The syscall underneath is the numbered kernel operation invoked through `svc` on this board.

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

Who starts the first application? The kernel runs the selected **init** program, commonly `/sbin/init` on a mounted root filesystem or `/init` in an initramfs. It becomes PID 1 and starts the ordinary user-space process tree. Kernel threads have a different origin.

BusyBox init and systemd are two possible init implementations, but the first experiment can be much smaller. In Chapter 29, our statically-linked PID 1 prints a message and deliberately reboots. It must not simply return from `main()`: the system's PID 1 exiting causes a kernel panic.

### Kernel module (LKM)

A driver does not always have to be built into the kernel image. A **kernel module** stores kernel code in a separate `.ko` file that can be loaded while the system is running. `insmod foo.ko` loads it; `rmmod foo` unloads it when unloading is permitted.

Loading a module does not make it an application. Its code runs inside the kernel with kernel privileges, so a faulty module can damage the whole system. We begin working with modules in Chapter 36.

## 2.7  Linux storage and memory use

You may now be wondering how much memory all these layers need. A desktop installation includes many programs we do not need on the board. A small embedded system selects only the kernel features, libraries, and applications required for its job.

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

A carefully selected single-purpose system can fit in 64 MB of RAM and 32 MB of flash. That is an example of what is possible, not a budget for every kernel or application. A MINI core with 512 MB of DRAM gives us considerably more room for the systems built here.

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

Return to the four-layer diagram when a later experiment fails. If the Boot ROM has not loaded a valid image, changing an application cannot help. If Linux is running but a device cannot be opened, the image header is probably not the first place to look. The diagram gives us a way to choose the next question.

## 2.9  Before we move on

We started with an LED and found two changes to the MCU model. First, an application's pointer belongs to its virtual address space; a physical register address is not automatically mapped there. Second, the application normally asks a driver for an operation through a kernel interface. A C library function can make that request through a syscall, and an fd can identify the open device.

The hardware operation at the end is still a register access. Linux adds control over who may request it and how it is shared. If you can explain that route in your own words, you have the main idea needed for the following chapters. The less familiar filesystem and process terms will become more concrete as we use them.

## 2.10  Lab

Before setting up the host, try these questions in your own words. You do not need a running board for them. Use the answer checks afterward to find anything worth rereading:

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

- **Looking for an "embedded mode" in Linux.** We configure the kernel for the target and choose a suitable userspace: perhaps fewer daemons, a smaller libc, and a read-only root. There is no single switch that turns a desktop distribution into the system our board needs.
- **Assuming the bootloader and the kernel cooperate after handoff.** They do not. The bootloader stops running at `bootz`. The kernel does not call back into U-Boot. A few data values from U-Boot may remain in memory, but U-Boot code is no longer in control.
- **Believing `/proc/cpuinfo` always reflects physical hardware.** It reports what the kernel detected or was told through the device tree. A virtual machine such as QEMU may report virtual hardware instead.
- **Trying to debug user-space problems with kernel tools and vice versa.** Each layer has its own toolset. First identify which layer contains the bug, then choose tools for that layer.

## 2.12  Going deeper

- *The Design of the Unix Operating System*, Maurice Bach (1986), for historical background on Unix processes and filesystem design. Its implementation details are not current Linux behavior.
- *Linux Kernel Development*, Robert Love (3rd ed., 2010), for a high-level kernel tour. Compare implementation details with the selected Linux source version.
- The "Anatomy of a Program" series on LWN.net.
- Start with `man 2 intro`, `man 2 open`, `man 2 read`, `man 2 mmap`, and `man 7 pthreads`. See [mmap(2)](https://man7.org/linux/man-pages/man2/mmap.2.html) and [pthreads(7)](https://man7.org/linux/man-pages/man7/pthreads.7.html) for the mapping and shared-resource distinctions above.
- The Linux source tree's `Documentation/admin-guide/` and `Documentation/process/`.

We have separated the software that runs on the board into layers. Next we prepare the computer that builds and inspects those pieces. Chapter 3 sets up the host without hiding compiler selection in global shell configuration.
