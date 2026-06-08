---
chapter: 55I
title: Rust for Linux
part: VI — Driver development (supplementary v1.2)
estimated_pages: 14
status: draft
---

# Chapter 55I — Rust for Linux

> **What:** the **Rust-for-Linux** project — Rust as a second supported language inside the kernel since Linux 6.1. We cover the toolchain setup (rustc + bindgen + a specific Rust edition), what kernel APIs are *exposed* to Rust today, what kind of drivers can already be written, and how to compile a "hello world" kernel module in Rust.
>
> **Why:** Rust's memory-safety guarantees apply at compile time. A whole class of C kernel bugs becomes impossible to write in safe Rust: use-after-free, double-free, data races on shared memory, integer overflows. The kernel community has accepted this as worth integrating because these bug classes account for a large share of kernel CVEs. As of 2026, Rust is still small in the kernel (drivers, no core subsystems) but growing.
>
> **Focus:** **the borrow checker, applied to kernel code**. The trade-off: more compile errors, fewer runtime errors. For a chapter on i.MX6ULL device drivers, the value is "you can do it for new drivers if you want, with caveats."


## 55I.1  Status as of late 2025 / early 2026

- **In mainline**: since 6.1 (October 2022).
- **Supported architectures**: x86_64, arm64, RISC-V, LoongArch64. **ARM32 (i.MX6ULL's architecture) is NOT yet supported.**
- **What's written in Rust**: a small handful of drivers (NVMe, GPU, etc.). Adoption is slow.
- **What it takes**: nightly-ish Rust toolchain, bindgen, `CONFIG_RUST=y`.

**On the i.MX6ULL specifically**, Rust is not usable yet — ARM32 is not supported. This chapter is about *the model*. You'd apply it on a different SoC (i.MX8M, Raspberry Pi 4, etc.) where Rust-for-Linux works today.

## 55I.2  Toolchain

```sh
# A specific Rust version that matches the kernel's expectation
$ rustup toolchain install 1.74.0
$ rustup default 1.74.0
$ rustup component add rust-src

# bindgen for generating Rust bindings from C headers
$ cargo install --locked --version 0.65.1 bindgen-cli
```

The kernel's `Documentation/rust/quick-start.rst` lists the exact versions required for a given kernel. Mismatch = build fails.

Check the kernel supports it:

```sh
$ cd linux/
$ make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- LLVM=1 rustavailable
Rust is available!
```

If not, the message tells you what's missing.

Enable in `.config`:

```
General setup --->
    [*] Rust support
```

## 55I.3  Hello world in Rust

`rust_hello.rs`:

```rust
// SPDX-License-Identifier: GPL-2.0

//! A trivial Rust kernel module.

use kernel::prelude::*;

module! {
    type: RustHello,
    name: "rust_hello",
    author: "LinuxLearn",
    description: "Hello world from Rust",
    license: "GPL",
}

struct RustHello;

impl kernel::Module for RustHello {
    fn init(_module: &'static ThisModule) -> Result<Self> {
        pr_info!("Hello from Rust!\n");
        Ok(RustHello)
    }
}

impl Drop for RustHello {
    fn drop(&mut self) {
        pr_info!("Goodbye from Rust!\n");
    }
}
```

`Makefile`:

```makefile
obj-m += rust_hello.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
```

Build, load:

```
$ make
  CC [M] rust_hello.o
  ...

# insmod rust_hello.ko
# dmesg | tail -1
[ ... ] Hello from Rust!

# rmmod rust_hello
# dmesg | tail -1
[ ... ] Goodbye from Rust!
```

That's it. The `module!` macro expands to all the C boilerplate (module_init, MODULE_LICENSE, etc.) under the hood.

## 55I.4  What Rust gets you

**Memory safety at compile time:**
- Use-after-free: caught by the borrow checker.
- Double-free: caught by ownership rules.
- Data races on shared mutable state: caught by the borrow checker + `Send`/`Sync` traits.

**Type-state programming:** force certain sequences of operations via the type system. Example — a "driver" that *must* be initialised before any I/O:

```rust
struct Uninit;
struct Init;

struct MyDevice<S> { _state: PhantomData<S>, ... }

impl MyDevice<Uninit> {
    fn new() -> Self { ... }
    fn init(self) -> MyDevice<Init> { ... }   /* consumes; returns initialised */
}

impl MyDevice<Init> {
    fn read(&self) -> u32 { ... }   /* only callable on initialised */
}
```

The compiler refuses to compile a call to `.read()` on an uninitialised device. The "did you forget to init?" bug class is no longer expressible.

**Error handling via `Result`**:

```rust
fn read_register(reg: u32) -> Result<u32> {
    if reg > MAX_REG {
        return Err(EINVAL);
    }
    Ok(unsafe { read_volatile(... as *const u32) })
}

let val = read_register(0x40)?;     // `?` propagates errors automatically
```

You cannot silently ignore an error — the compiler will not let you.

## 55I.5  What's *exposed* today (the limits)

Kernel APIs are exposed to Rust as Rust modules under `kernel::`. Currently available:

- `kernel::pr_info!`, `pr_err!`, etc. (printk).
- `kernel::sync::{Mutex, SpinLock, ...}` — locks.
- `kernel::workqueue::Work` — workqueues.
- `kernel::time::Ktime` — time.
- `kernel::error::{Result, Error}` — error handling.
- `kernel::miscdev::Registration` — misc device chardev.
- `kernel::file` — file_operations bindings.
- `kernel::pci::Driver`, `kernel::platform::Driver` — bus drivers.

**Not yet exposed (as of early 2026)**:
- Most subsystem-specific APIs (input, sound, drm, networking).
- Lots of platform-specific helpers.

The list grows monthly. Check `rust/kernel/` in mainline.

## 55I.6  Trade-offs

**Pros**:
- Memory safety classes of bug eliminated.
- Type-driven API design.
- Better build-time errors.

**Cons**:
- Smaller community inside the kernel.
- Tooling churn — Rust version requirements change with each kernel.
- Toolchain disk cost (rustc + bindgen ~1.5 GB).
- C interop requires `unsafe { }` blocks where you cross the boundary. Within those blocks, all the same C bugs are possible — Rust safety depends on the `unsafe` blocks being correct. Bugs inside `unsafe` are no different from C bugs.
- More upfront design for the type system.

**For an embedded project**: if you're writing a new driver for a chip that doesn't exist in mainline, and you control the build environment, Rust is worth considering on Rust-supported architectures. For maintaining 4.1 BSP code or anything on ARM32, not yet.
**BSP** - Board Support Package: vendor patches, configs, bootloader files, and scripts needed to boot one board.

## 55I.7  Lab

1. **Check rustavailable**. On a Rust-supported arch + recent kernel, verify `make rustavailable` says yes.
2. **Build rust_hello**. Use the example above. load it. verify dmesg output.
3. **Add a module parameter**. Look up `kernel::module_param!` usage.
4. **Convert a small chardev to Rust**. Use `kernel::miscdev::Registration`.
5. **Provoke a compile error**. Pass a moved value somewhere. Note the borrow-check diagnostic.

## 55I.8  Pitfalls

- **Toolchain version mismatch.** Each kernel pins specific rustc/bindgen versions. Use exactly what `Documentation/rust/quick-start.rst` says.
- **`unsafe` overuse.** Wrapping every C call in `unsafe { }` defeats the safety goal. Write thin safe wrappers around C APIs.
- **Trying to use std**. Kernel Rust is `#![no_std]`. Heap allocations go through specific kernel allocators.
- **Long compile times.** First build of a Rust module is slow (~30 s). incremental is fast.
- **Linking issues with mixed C/Rust modules.** Currently uncommon. If you need it, follow the kernel maintainers' examples.

## 55I.9  Going deeper

> **Driver choice:** Use the in-tree, maintained driver first.
> Use out-of-tree, spidev, or custom-driver paths only after you accept the kernel-version maintenance cost and document who owns updates.


- **`Documentation/rust/`** — the Rust-for-Linux documentation.
- **`rust/kernel/`** — the in-kernel Rust support crate.
- **<https://github.com/Rust-for-Linux>** — historical out-of-tree work.
- **"Rust for Linux" talks from Linux Plumbers, Open Source Summit** — videos online.
- **Asahi Linux's Apple-GPU driver** — large real-world Rust kernel code.

---

> **End of Part VI — Driver Development.** From the smallest kernel module (Ch 36) to Rust-for-Linux (Ch 55I), you now have the full vocabulary: load/unload, chardev, hot-plug, platform binding, locking, blocking I/O, interrupts, GPIO, input, I²C, SPI, PWM/RTC, IIO, regmap, DMA, watchdog, PM, network, RT, audio, LCD, MTD/UBI, V4L2, USB, timers, async, CAN, block, WiFi, cellular, multi-touch, HDMI, Rust.
> MCU bridge: Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
> MCU bridge: Think of Linux PWM like an MCU timer output channel, except the driver exposes period, duty cycle, polarity, and enable state through a subsystem.
> MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
> MCU bridge: Think of regmap like a typed wrapper around your read_reg() and write_reg() helpers, with caching, locking, and bus differences handled centrally.
> **DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.
> **PWM** - Pulse-Width Modulation, a timer output whose duty cycle controls average power or encodes timing.
> **IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
> **UBI** - Unsorted Block Images, a flash-management layer over raw NAND that handles wear leveling and bad blocks.
> **MTD** - Memory Technology Device, Linux's raw flash subsystem for eraseblock-based storage.
> **GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
> **regmap** - a kernel helper that wraps register reads and writes over I2C, SPI, or MMIO.
>
> The next Part is the **Device Cookbook (Part VII)** — Ch 64 onwards — where these subsystem chapters get applied to real chips: 2–3 representative chips per category, with schematics, DT, drivers, labs, and pitfalls per chip.

> Next chapter: **Chapter 64 — QSPI NOR flash** (Winbond W25Q128 / Macronix MX25L256 / Micron MT25Q).
