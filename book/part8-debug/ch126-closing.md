---
chapter: 126
title: Closing — what to read next
part: VIII — Debug, production, advanced
estimated_pages: 6
status: draft
---

# Chapter 126 — Closing: what to read next

> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


> In 125 chapters you've gone from MCU engineer to someone who can bring up a custom i.MX6ULL board with mainline U-Boot, Linux, a hand-built rootfs, drivers, secure boot, CI, and OTA. That's a lot of ground. This chapter points to what to read and do next.
> MCU bridge: Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> MCU bridge: Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
> **U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.


## 126.1  The next-step canon

Five books and sites that pick up where this book ends:

### 1. **Linux Device Drivers, 3rd Ed. (LDD3)** — Corbet, Rubini, Kroah-Hartman

The canonical kernel-driver book. Written for kernel 2.6 (so the specific APIs are dated), but the *concepts* are timeless — char devices, blocks, networking drivers, USB drivers, PCI, sleeping primitives, kernel memory management. The mental model it gives you is correct. just check current APIs in the kernel source when implementing.

Free online: https://lwn.net/Kernel/LDD3/

### 2. **Bootlin's "Embedded Linux" training material**

Bootlin (formerly Free Electrons) is a French embedded-Linux training + consulting company. Their training slides + labs are free, comprehensive, current, and license-permissive. Topics: kernel internals, Yocto, Buildroot, audio, video, real-time, security.
**Yocto** - a metadata-driven build system for producing custom Linux distributions.
**Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.

https://bootlin.com/training/

Probably the best free online resource for further study.

### 3. **`kernelnewbies.org`**

Wiki + mailing list for new kernel contributors. Hosts:
- A "first patch" tutorial.
- Release notes for every kernel version since 2.6 — read these to track what's changing.
- "KernelHacking" tutorials.

http://kernelnewbies.org

The most welcoming community for first-time kernel contributors. Mailing-list lurkers welcome.

### 4. **LWN.net**

The professional-grade kernel-development periodical. A paid subscription ($10/month) is worth it if you work with Linux full-time. Coverage:
- Weekly summaries of LKML threads.
- Deep dives on new kernel features (eBPF, io_uring, sched_ext).
- Conference reports (Linux Plumbers, Kernel Summit, Open Source Summit).
- Subsystem maintainer profiles.

Reading LWN weekly is one of the most reliable ways to absorb kernel-development culture and stay current.

https://lwn.net/

### 5. **`Documentation/process/`** in the Linux source tree

The kernel ships its own onboarding documentation. Read in order:
- `1.Intro.rst` — "the kernel project is huge"
- `2.Process.rst` — "how the release cycle works"
- `3.Early-stage.rst` — "what to do before sending a patch"
- `4.Coding.rst` — "the code style and norms"
- `5.Posting.rst` — "how to send patches (Ch 120A's bible)"
- `6.Followthrough.rst` — "how to respond to reviews"
- `7.AdvancedTopics.rst` — "everything else"

200 pages total. every new contributor should read it once.

## 126.2  Communities and conferences

- **Linux Plumbers Conference** (annual. ~Sep–Oct) — the developer's conference. Streamed talks free.
- **Embedded Linux Conference** (Linux Foundation. spring + fall) — embedded-specific.
- **FOSDEM** (Brussels, Feb) — free, sprawling, every open-source project under one roof.
- **Open Source Summit** (Linux Foundation, multiple cities) — broader open-source.
- **DebConf** (annual) — Debian-specific. many embedded developers attend.

Local: search for "Linux meetup" or "embedded systems meetup" in your city. Bring questions. The community is welcoming.

## 126.3  Mailing lists

Subscribe (digest mode if volume is too high):

- **linux-kernel@vger.kernel.org** — the firehose. ~500 mails/day. lurk.
- **linux-arm-kernel@lists.infradead.org** — ARM-specific. ~50/day. relevant to you.
- **linux-imx@nxp.com** — NXP-imx-specific (moderated). ~5/day. very relevant.
- **devicetree@vger.kernel.org** — DT bindings discussions.
- **stable@vger.kernel.org** — stable-kernel patch announcements.
- **kernelnewbies@kernelnewbies.org** — beginner Q&A.

Lurk for a month before posting. Read the patches you can understand. ignore the rest. Slowly your understanding accretes.

## 126.4  Three further specializations

Depending on your interests:

### Path A — Kernel hacker
Goal: become a subsystem maintainer.
- Pick a subsystem (e.g., IIO sensors, GPIO, regulators).
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**IIO** - Industrial I/O, Linux's subsystem for sensors, ADCs, DACs, and buffered sampled data.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
- Read every patch on that subsystem's mailing list for 6 months.
- Submit small fixes. build reputation.
- Eventually: maintain a driver, then a subsystem.

### Path B — Product engineer
Goal: ship great embedded products.
- Master one BSP family deeply (i.MX, STM32MP, TI Sitara, RPi).
**BSP** - Board Support Package: vendor patches, configs, bootloader files, and scripts needed to boot one board.
- Build the CI/release/OTA infrastructure (Ch 121A, 125).
- Develop soft skills: talking to product managers, defending engineering trade-offs.
- Eventually: tech lead on a product team.

### Path C — Embedded security
Goal: build trustworthy embedded systems.
- Deepen on TrustZone + OP-TEE.
- Study secure boot in depth across multiple SoCs.
- Learn cryptography (Boneh's online course is excellent).
- Eventually: security architect. review designs across products.

## 126.5  Skills outside Linux you'll still need

- **C and C++** — kernel is C. many embedded apps are C++.
- **Python** — for tooling, build scripts, test automation.
- **Rust** — increasingly relevant. learn it for new kernel contributions and for high-reliability user-space.
- **Git** — beyond `add/commit/push`. Understand rebase, bisect, blame, format-patch, send-email.
- **Make + CMake + Meson** — build system fluency saves hours.
- **Networking** — TCP/IP at the implementation level, not just usage. RFC 793 / 1122.
- **Shell scripting** — `bash`, `awk`, `sed`. Indispensable.
- **Schematic / PCB reading** — you may never design boards, but you'll read thousands.
- **Public speaking and writing** — explaining technical decisions to non-engineers is a force multiplier.

## 126.6  A short list of "if you remember nothing else"

1. **The kernel-userspace split is the most important concept in this book.** Every confusion ultimately reduces to "I forgot which side that runs on."
2. **Driver-binding is via DT `compatible` strings.** Add your chip's compatible to the driver's table. DT enables it. The kernel binds.
3. **A/B partitioning + rollback is mandatory for OTA.** Without it, one bad update bricks your fleet.
4. **`printk` is the universal Linux debugger.** When in doubt, add a printk. trust dmesg.
5. **Mainline first. fork only when you must.** Vendor BSPs cost more over the product's life than the engineering to use mainline.
6. **Secure boot, key ceremony, and OTA together — not individually — is what makes a product secure.** Each in isolation is theatrical.
7. **The community is your colleague.** Lurk lists. ask after lurking. help others. submit patches. Embedded Linux is built by humans. be a good human.

## 126.7  Acknowledgements

(Reserved for the book author's final acknowledgements: the people who made the journey possible, the colleagues who reviewed early drafts, the readers who reported errors, the maintainers whose code makes this possible at all.)

## 126.8  Errata + feedback

(Reserved: URL of the book's errata page. an email or GitHub issues tracker for reader-submitted corrections.)

---

> **End of the book.**

> You started with a question: *"How do I become an embedded-Linux engineer when my background is microcontrollers and bare-metal?"*

> Now you have an answer: *"By understanding every layer from the reset vector to the systemd target, having built each by hand once, and knowing where to look up the rest when you need it."*

> Most importantly, you now have the vocabulary to read kernel source, the frameworks to think about new problems, the debugging instincts to solve them, and the community connections to learn faster than alone.

> Build something. Ship it. Watch a customer use it for years. That is embedded Linux.

> Good luck. Send your first patch.
