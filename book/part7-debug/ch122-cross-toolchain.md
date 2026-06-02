---
chapter: 122
title: Build your own cross-toolchain (crosstool-NG)
part: VIII — Debug, production, advanced
estimated_pages: 24
status: draft
---

# Chapter 122 — Build your own cross-toolchain

> **What:** building a complete **cross-compiling toolchain** — binutils + gcc + glibc (or musl/uClibc-ng) + gdb — from upstream sources, using **crosstool-NG** (the canonical tool) and, as a one-time exercise, by hand. We resolve the bootstrap puzzle: "gcc needs libc to compile programs, libc needs gcc to compile itself, gcc needs binutils, …". The output: an `arm-linux-gnueabihf-*` toolchain in `/opt/x-tools/`. We compare it size-for-size and behavior-for-behavior against a pre-built Linaro / Bootlin / Yocto SDK toolchain.
>
> **Why:** for most users, `apt install gcc-arm-linux-gnueabihf` is fine. Build your own when one of these matters:
> 1. **Pinning** — the apt version updates with Ubuntu; your build might silently change behavior. Your own toolchain is reproducible across teams and time.
> 2. **Custom libc / configuration** — you need `glibc` 2.34 specifically; or you want musl for size; or you want a hardened gcc with stack protector defaults.
> 3. **Understanding** — every "weird linker error" makes sense once you've built the linker. It also teaches what every flag and stage actually does.
>
> **Focus:** a multi-stage build solves the chicken-and-egg problem. Stage 1 gcc has no libc and can only compile freestanding code. It builds the kernel headers, then glibc. Stage 2 gcc is then built against the new glibc and has a full C++/pthread runtime. Each stage knows where to find the previous; the directories, prefix, and `--with-sysroot` flags must agree. Get any of these wrong and the linker can't find libc, or gcc looks in `/usr/lib` instead of the cross sysroot. crosstool-NG hides this complexity in menuconfig + sequenced builds.

## 122.1  What's in a toolchain

A cross-toolchain has 4 parts:

| Component | What it does | Source |
|---|---|---|
| **binutils** | assembler (`as`), linker (`ld`), object tools (`objcopy`, `objdump`, `nm`, `readelf`, `strip`, `ar`) | https://ftp.gnu.org/gnu/binutils |
| **gcc** | the C/C++ compiler driver + frontends + middle-end + backend | https://ftp.gnu.org/gnu/gcc |
| **libc** | C runtime library + dynamic linker (glibc, musl, uClibc-ng, newlib) | https://ftp.gnu.org/gnu/glibc, https://musl.libc.org |
| **gdb** | the debugger (host-side; gdbserver runs on target) | https://ftp.gnu.org/gnu/gdb |

Plus optional:
- **gcc support libraries**: libgcc, libstdc++, libgfortran, libgomp, libitm, libsanitizer.
- **kernel headers** — the userspace-visible kernel API headers (`asm/`, `linux/`, `mtd/`) — needed for glibc to compile syscall wrappers.
- **linker scripts, sysroot layout, multilib variants**.

The full prefix-namespace convention:
```
   /opt/x-tools/arm-unknown-linux-gnueabihf/
   ├── bin/
   │   ├── arm-unknown-linux-gnueabihf-gcc      ← compiler driver
   │   ├── arm-unknown-linux-gnueabihf-ld
   │   ├── arm-unknown-linux-gnueabihf-objdump
   │   └── ...
   ├── arm-unknown-linux-gnueabihf/             ← "target" subtree
   │   ├── lib/        crt*.o, libc.so, libpthread.so
   │   ├── sys-root/
   │   │   ├── usr/include/    headers
   │   │   ├── usr/lib/         libraries
   │   │   └── lib/             dynamic linker
   │   └── ...
   ├── lib/
   │   └── gcc/arm-unknown-linux-gnueabihf/<gcc-ver>/
   │       ├── libgcc.a
   │       ├── include/         (gcc's own headers — stddef.h, stdarg.h)
   │       └── ...
   └── share/
```

The "triple" `arm-unknown-linux-gnueabihf` encodes: arch (arm), vendor (unknown — generic), OS (linux), ABI (gnueabihf = GNU C library + ARM EABI + hard-float).

## 122.2  The bootstrap problem

You want to build gcc. gcc needs glibc to compile programs. glibc needs gcc to compile itself. Circular.

Resolution — **multi-stage build**:

```
   1. binutils (assembler + linker)                   ┐
                                                      │ Self-contained
   2. Kernel headers (NOT compiled — just installed   │ — no libc needed
       from linux source)                              ┘

   3. gcc "stage 1" (a.k.a. bootstrap gcc):
      - configured with --disable-shared, --disable-libssp, etc.
      - links nothing, just compiles
      - has libgcc.a (the gcc support library, freestanding)
      - this gcc can compile glibc's source but cannot link an app

   4. glibc:
      - configured to use stage-1 gcc + binutils + kernel headers
      - builds libc.so, libpthread.so, crt0.o, etc.

   5. gcc "stage 2" (the final gcc):
      - configured with --enable-shared, --enable-threads, etc.
      - linked against the freshly-built glibc
      - now full C++ runtime, full pthreads, full sanitizers
```

Each stage produces artifacts the next stage consumes. crosstool-NG sequences this automatically.

## 122.3  crosstool-NG — the standard tool

```sh
# Get crosstool-NG
git clone https://github.com/crosstool-ng/crosstool-ng.git
cd crosstool-ng
./bootstrap                  # autoconf/automake; one-time
./configure --enable-local   # build in current dir
make
PATH=$PWD:$PATH              # use local ct-ng

# Configuration
mkdir ../crosstool-build && cd ../crosstool-build
ct-ng menuconfig
```

The menuconfig is structured similarly to kernel menuconfig:

```
   Target options
     → Target Architecture: arm
     → Endianness: Little endian
     → Bitness: 32 bit
     → Architecture level: armv7-a
     → CPU: cortex-a7
     → Tune: cortex-a7
     → Floating point: hardware (FPU)
     → FPU: vfpv3-d16

   Toolchain options
     → Tuple's vendor string: yourvendor
     → Tuple's alias: arm-yourvendor-linux-gnueabihf

   Operating System
     → Target OS: linux
     → Linux kernel version: 6.6.x (the headers version)

   C compiler
     → gcc version: 13.2.0
     → C++ + Fortran on/off
     → Enable Link Time Optimization

   C library
     → glibc 2.38   (or musl, or uClibc-ng)

   Binutils
     → binutils version: 2.41

   Debug facilities
     → gdb: enabled (for cross-debug)
     → ltrace, strace: enabled
```

Save the config. Build:

```sh
ct-ng build
# Downloads sources (binutils, gcc, glibc, kernel, gdb)
# Builds binutils
# Installs kernel headers
# Builds gcc stage 1
# Builds glibc
# Builds gcc stage 2
# Builds gdb cross
# Installs to ~/x-tools/arm-yourvendor-linux-gnueabihf/
# Takes 30–90 minutes on a fast machine; longer on a Pi
```

After:

```sh
export PATH=~/x-tools/arm-yourvendor-linux-gnueabihf/bin:$PATH
arm-yourvendor-linux-gnueabihf-gcc --version
# gcc (crosstool-NG 1.27.0) 13.2.0
arm-yourvendor-linux-gnueabihf-gcc -o hello hello.c
file hello
# hello: ELF 32-bit LSB pie executable, ARM, EABI5 version 1 (SYSV), dynamically linked, interpreter /lib/ld-linux-armhf.so.3, ...
```

Your own toolchain, pinned to specific versions, reproducible.

## 122.4  Manual mini-build — for the masochist (and the educated)

For one-time understanding, build it by hand. Compressed (a full tutorial is 30+ pages; here's the skeleton):

```sh
TARGET=arm-mine-linux-gnueabihf
PREFIX=/opt/x-tools/$TARGET
SYSROOT=$PREFIX/$TARGET/sysroot
JOBS=$(nproc)

mkdir -p $SYSROOT
export PATH=$PREFIX/bin:$PATH

# 1. binutils
tar xf binutils-2.41.tar.xz
cd binutils-2.41
mkdir build && cd build
../configure --prefix=$PREFIX --target=$TARGET --with-sysroot=$SYSROOT \
             --disable-nls --disable-werror
make -j$JOBS && make install
cd ../..

# 2. Kernel headers (no compilation)
tar xf linux-6.6.tar.xz
cd linux-6.6
make ARCH=arm INSTALL_HDR_PATH=$SYSROOT/usr headers_install
cd ..

# 3. gcc stage 1 (compiler only, no libc yet)
tar xf gcc-13.2.0.tar.xz
cd gcc-13.2.0
./contrib/download_prerequisites           # downloads mpfr, gmp, mpc
mkdir build && cd build
../configure --prefix=$PREFIX --target=$TARGET --with-sysroot=$SYSROOT \
             --disable-multilib --disable-shared --disable-threads \
             --disable-libatomic --disable-libgomp --disable-libquadmath \
             --disable-libssp --disable-libvtv --disable-libstdcxx \
             --enable-languages=c
make -j$JOBS all-gcc all-target-libgcc
make install-gcc install-target-libgcc
cd ../..

# 4. glibc
tar xf glibc-2.38.tar.xz
cd glibc-2.38
mkdir build && cd build
../configure --prefix=/usr --host=$TARGET --target=$TARGET \
             --with-headers=$SYSROOT/usr/include \
             --disable-multilib --disable-werror libc_cv_forced_unwind=yes
make -j$JOBS
make install DESTDIR=$SYSROOT
cd ../..

# 5. gcc stage 2 (full C/C++ with glibc)
cd gcc-13.2.0/build
rm -rf *
../configure --prefix=$PREFIX --target=$TARGET --with-sysroot=$SYSROOT \
             --disable-multilib --enable-shared --enable-threads=posix \
             --enable-languages=c,c++
make -j$JOBS
make install
cd ../..

# Verify
$TARGET-gcc -o hello hello.c
file hello
```

Each `configure` line is a tour of GNU autoconf flags. The `--with-sysroot=$SYSROOT` is the key glue: gcc looks here for `usr/include/` (headers) and `usr/lib/` (libraries). Get the path wrong and gcc happily uses your host's headers — your binaries get built but link against the wrong libc.

## 122.5  glibc vs musl — the C library choice

| | glibc | musl | uClibc-ng | newlib |
|---|---|---|---|---|
| Size (static helloworld) | 800 KB | 8 KB | 30 KB | 30 KB |
| Compatibility | extreme | high (mostly POSIX) | medium | bare-metal/embedded |
| Performance | best (NPTL threads, vectorized memcpy, ...) | OK | OK | n/a |
| License | LGPL | MIT | LGPL | BSD |
| dlopen support | yes | yes | yes | partial |
| Locale + i18n | full | limited | limited | minimal |
| Use case | desktop, server, full systems | static linking, containers, small Linux | older embedded | bare-metal RTOS |

**Pick guide:**
- **glibc** — default for any system that has > 64 MB RAM and runs a real distribution.
- **musl** — when you statically link (Alpine-style images, single-binary apps) or want < 50 MB rootfs.
- **uClibc-ng** — legacy embedded; mostly being replaced by musl.
- **newlib** — bare-metal Cortex-M; not for Linux.

The toolchain is built around the libc choice; you can't easily swap later. Pick at the start.

## 122.6  ABI and the "hf" suffix

`arm-linux-gnueabihf` decoded:
- **arm**: 32-bit ARM
- **linux**: Linux kernel target
- **gnueabi**: GNU C library + ARM EABI calling convention
- **hf**: hardware float — uses FPU registers for argument passing in floating-point calls

Vs `arm-linux-gnueabi` (soft-float — passes float args in integer registers; works on any ARM but slower):

- **hf binaries cannot run on soft-float systems** and vice versa.
- The dynamic linker name differs: `/lib/ld-linux-armhf.so.3` vs `/lib/ld-linux.so.3`.
- The i.MX6ULL Cortex-A7 has VFPv3 (hardware float); use **hf**.

`gcc -mfloat-abi=hard` is required at compile time; the toolchain has it as the default.

## 122.7  Multilib — multiple variants in one toolchain

A single gcc can produce binaries for multiple ABIs (e.g., both soft-float and hard-float, both armv7-a and armv5te). Enable with `--enable-multilib`. Costs: longer build time, more disk space.

For most embedded projects: pick one ABI; disable multilib for clarity. crosstool-NG's `--disable-multilib` is the default.

## 122.8  Sysroot vs prefix vs target

These three concepts confuse first-time toolchain builders:

- **prefix** — where the toolchain binaries (gcc, ld, etc.) install: `/opt/x-tools/<triple>/`
- **target** — the system the toolchain produces code for: `arm-linux-gnueabihf`
- **sysroot** — the target's logical "/" — where gcc/ld look for target headers and libraries. Often `<prefix>/<target>/sysroot/`

When compiling for the target:
```
gcc                 reads .c source
  → gcc preprocessor   includes <stdio.h> from sysroot/usr/include/
  → cc1               compiles to assembly
  → as                assembles to .o
  → ld                links against sysroot/usr/lib/libc.so
```

A "sysroot" is essentially the target filesystem layout, available on the host for cross-build. Buildroot, Yocto, and even crosstool-NG produce one.

For application development, you often want the sysroot to also contain libraries from your rootfs (libcurl, libssl, ...). Buildroot's "Per-package directories" + SDK export gives this.

## 122.9  Comparing your toolchain to pre-built ones

```sh
# Yours
$TARGET-gcc --version

# Linaro
wget https://snapshots.linaro.org/.../gcc-linaro-...-linux-gnueabihf.tar.xz

# Bootlin
wget https://toolchains.bootlin.com/.../arm-buildroot-linux-gnueabihf.tar.bz2

# Yocto SDK (after building an image; produces a self-extracting installer)
./poky-glibc-x86_64-core-image-...-toolchain-....sh
```

Compare:
- **Binary sizes** (size of "hello world" with each)
- **Default options** (`gcc -dumpspecs` shows the spec file)
- **glibc version**: `strings $SYSROOT/lib/libc.so.6 | grep version`
- **Compatibility**: does code built with yours run on the target built with theirs?

In practice they're all similar (all build from the same upstream). Differences:
- Yocto/Buildroot SDKs are tied to a specific rootfs; yours is generic.
- Linaro toolchains often include experimental optimizations.
- Your own toolchain has your chosen versions + flags.

## 122.10  Lab

1. **Install crosstool-NG.** Follow the build. Verify `ct-ng version`.
2. **Configure for i.MX6ULL.** menuconfig → select Cortex-A7, hard-float, glibc, gcc 13.x. Save config.
3. **Build the toolchain.** Run `ct-ng build`. Watch each stage complete. ~1 hour.
4. **Test the toolchain.** Compile a simple program; run it on the target (NFS root); confirm it works.
5. **Compare with apt's gcc.** `arm-linux-gnueabihf-gcc -dumpversion` (apt) vs your custom; differences?
6. **musl variant.** Reconfigure crosstool-NG with musl libc; rebuild; compile `hello world`; compare static-link sizes.
7. **Manual stage 1.** Following §122.4, build binutils + kernel headers + gcc stage 1 by hand. Stop after stage 1; verify it can produce object files.
8. **Pinning.** Write a script that downloads a specific version of binutils + gcc + glibc, builds, and produces a tarball your team can extract anywhere.
9. **Cross-debug.** Build your gdb cross (part of crosstool-NG). Use it to debug a target program via gdbserver.
10. **Yocto SDK comparison.** If you've done a Yocto build (Ch 123A): export an SDK; compare against your hand-built toolchain.

## 122.11  Pitfalls

- **Build out of order.** Build glibc before stage 1 gcc → fails. Always sequence binutils → headers → gcc1 → glibc → gcc2.
- **Wrong sysroot path.** gcc looks in `/usr/include` instead of `$SYSROOT/usr/include`; uses host headers; ABI mismatch on target. Verify `gcc -print-sysroot`.
- **Missing kernel headers.** glibc build complains about missing `linux/...` headers. Install them first via `make headers_install`.
- **Host-tool versions too old.** Building gcc 13 needs autoconf 2.69+, makeinfo, modern bison/flex. Use Ubuntu 22.04+.
- **gcc bootstrap requires C++ compiler.** Stage 1 gcc compiles with the host gcc; host must support C++14+.
- **Out-of-tree build required.** Most GNU sources don't support in-source builds. Always `mkdir build && cd build && ../configure ...`.
- **Static glibc.** Linking statically against glibc bloats binaries; static linking glibc *also* breaks dlopen and getaddrinfo. Use musl for static.
- **Multiple toolchains in PATH.** Two `arm-linux-gnueabihf-gcc` binaries → wrong one picked. Always explicit full path or curate PATH.
- **PIE vs PIC defaults.** Modern gcc defaults to `-fPIE -pie`; older code expecting non-PIE may break (especially if your kernel doesn't support PIE binaries, which is rare).
- **Locale ate the build.** glibc builds depend on `LC_ALL=C`; if your locale is set weirdly, configure scripts misbehave.
- **`-march=armv7-a` vs `-mcpu=cortex-a7` confusion.** Both work; cortex-a7 is more specific (enables errata). Pick one and stay consistent.
- **Cross-gdb missing python.** crosstool-NG's gdb may lack Python support → no `lx-symbols`. Enable `--with-python` for gdb.

## 122.12  Going deeper

- **`crosstool-NG documentation`** — `docs/`; well-written.
- **Bootlin's "Toolchains for Embedded Linux"** training material — gold-standard.
- **`Linux From Scratch` (LFS)** — manual-build instructions; not embedded but the bootstrap chapter is the canonical reference.
- **GNU binutils, gcc, glibc manuals** — long but the truth.
- **musl libc documentation** — much shorter than glibc, good intro.
- **Yocto's `meta-toolchain` recipe** — for understanding how Yocto produces SDKs.
- **Bootlin's pre-built toolchains** (https://toolchains.bootlin.com) — to compare against your own.
- **GCC's "internals" docs** — for deep understanding of stages, passes, register allocation.
- **Ch 6** — the original toolchain chapter (consumer-side).
- **Ch 123** — Yocto vs Buildroot; both use cross-toolchains.

---

> Next chapter: **Chapter 122A — BSP → mainline migration playbook**.
