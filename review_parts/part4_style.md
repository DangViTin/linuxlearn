# Part IV — Style/ESL Review

## Cross-cutting patterns
- **Em-dash chaining** is the dominant AI tic across all eight chapters. Almost every paragraph has at least one `—` clause-joiner. Most should be periods or commas. ESL readers parse periods much faster than em-dashes.
- **"navigate"** used metaphorically multiple times ("source-tree structure you will navigate", "navigate to"). Use plain "find", "go to", "read".
- **"crucial / essential / paramount" family** — "the prerequisite for every chapter", "the single most important architectural decision", "the deliverable of this chapter". Tone down or be specific.
- **Royal "we"** is heavy in chapter intros ("we walk", "we open", "we build", "we trace"). For an engineer-at-whiteboard tone, mix in "you" or drop the pronoun.
- **Sledgehammer "Not X — but Y"** appears in chapter intros and conclusions ("not to *do* the bring-up", "not the *what*", "it's not X. It's Y."). Rewrite with one clear positive statement.
- **Hedging/intensifier openers** — "Notably,", "Worth pinning:", "Worth a skim if". OK once a chapter; currently several per chapter.
- **Bullet-list-as-prose**: many sections (esp. Ch25 §25.5, Ch28 §28.4, Ch30A §30A.5) walk a process as a numbered list when 2-3 short sentences would read better.
- **Triplet rhythm** ("smaller flash, PREEMPT_RT for real-time, debug options on engineering builds"; "what, why, how"; "the cpu, the gic, on-chip ram, ..."). Pleasing in moderation; overdone here.
- **Underexplained kernel concepts**: bootargs/`/chosen`, ATAGs, decompressor stub, `__init` sections, vmlinux↔zImage, MIDR, MMU bring-up in head.S, slab/SLUB, `paging_init`, devm_, `of_node` lifecycle. All stated in one sentence then used as if known.

## Ch25 — Building mainline Linux
### AI wording / sledgehammer / buzzwords
- > "The build itself is mechanical, but the artefacts it produces — and the source-tree structure you will navigate for the next several Parts — are the first thing that needs to be at your fingertips."
  - Rewrite: "The build is mechanical. What matters is the artefacts it produces and the source-tree layout you will use in every later chapter."
- > "The hierarchy is consistent: **subsystem at top → vendor at the second level → SoC/board at the third**."
  - Rewrite: drop the arrows; "Every subsystem follows the same layout: top-level is the subsystem, next level is the vendor, and the lowest level is the SoC or board."
- > "One config builds for all of them; a single `zImage` boots on any board with a matching DT. This is mainline's preferred organisation."
  - Rewrite: Semicolon → period. "One config builds for all of them. A single `zImage` boots on any board that has a matching DT. This is the mainline style."
- > "Forgetting `ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-`. The `make` will try to build a host x86-64 kernel and fail with cryptic errors deep in the architecture-specific code."
  - Rewrite: drop "cryptic"; "`make` will build a host x86-64 kernel and fail somewhere deep in arch code."

### ESL readability
- > "Greg KH applies bugfix backports to each mainline release for ~6 weeks after it. Tagged `6.6.1`, `6.6.2`, etc."
  - Rewrite: "Greg KH backports bug fixes to each mainline release for about 6 weeks. Tags look like `6.6.1`, `6.6.2`, and so on."
- > "Re-run `make imx_v6_v7_defconfig && make -j$(nproc) zImage` and observe that the second build is essentially as fast as the first incremental build — `ccache` is the reason if you have it installed; otherwise the same speed."
  - Rewrite: split sentence. "Re-run the defconfig and the build. The second build is almost as fast as an incremental build. If you have `ccache` installed, that is why. If not, it is still about the same."
- > "On a 4-core / 8-thread modern host, expect 5–8 minutes for a fresh full build, < 30 s for an incremental change."
  - Rewrite: "On a modern 4-core / 8-thread host, expect 5-8 minutes for a fresh build and under 30 seconds for an incremental change."

### Needs more explanation
- §25.4 "vmlinux vs Image vs zImage": one-paragraph table, then used as fact. Expand: what an ELF binary is in this context, why ARM32 uses `zImage` while AArch64 uses `Image`, what "decompressor stub" actually means in assembly terms. The §25.5 sketch helps but should come first.
- §25.5 "decompressor": "the kernel image carries its own decompressor" — say *where* the decompressor source lives (`arch/arm/boot/compressed/`), what runs it (the first instructions of `zImage`), and that it self-relocates so it doesn't get overwritten.
- §25.4 "modules.dep, modules.alias": named but not defined. One sentence each: what `modprobe` does with them.

## Ch26 — Booting the kernel from U-Boot
### AI wording / sledgehammer / buzzwords
- > "this is the moment your work as a *Linux* engineer begins. Up to here we have done bare-metal, bootloader, and pre-Linux infrastructure. From here on, Linux is running and we are reading its output, not writing the words it prints."
  - Rewrite: drop the dramatic frame. "From here on, Linux is running. Your job changes from writing the boot code to reading what the kernel prints."
- > "Get `r2` right and the kernel boots ~95 % of the time. Get it wrong and you stare at silence."
  - Rewrite: poetic. "If `r2` is correct, the kernel almost always boots. If `r2` is wrong, you see nothing on the UART."
- > "This is the magic line: U-Boot sets `r2 = 0x83000000`, hands off, and disappears."
  - Rewrite: "magic line" is buzzword. "This is the key step. U-Boot sets `r2 = 0x83000000`, jumps to the kernel, and is done."
- > "VFS panic ... Symptom is loud and clear; fix `root=` cmdline."
  - Rewrite: idiom + semicolon. "The panic message is clear. Fix the `root=` argument."

### ESL readability
- > "If you accidentally typed `bootz 0x82000000 0x83000000` (no `-`), U-Boot interprets `0x83000000` as the initrd address and there's no DTB."
  - Rewrite: "If you type `bootz 0x82000000 0x83000000` (no `-`), U-Boot reads `0x83000000` as the initrd address. The kernel then gets no DTB."
- > "Without `earlycon`, the first ~10 boot lines are buffered and you only see them once the regular console comes up."
  - Rewrite: "Without `earlycon`, the first ~10 boot lines stay in a buffer. You see them only when the regular console driver loads."
- > "Common culprit: PMIC over I²C — if I²C is broken, voltage regulators don't come up, devices don't enumerate, kernel hangs."
  - Rewrite (triplet rhythm): "A common cause is the PMIC on I²C. If I²C is broken, the regulators stay off. Devices fail to enumerate, and the kernel hangs."

### Needs more explanation
- §26.1 "ATAGS path": named in the table but never defined. One line: "ATAGS were the pre-DT way to pass boot info from bootloader to kernel; legacy only."
- §26.3 "`earlycon`": "tiny inline UART driver" appears in §26.6 but the cmdline parameter is used in §26.3 without an explanation. Move a one-sentence definition forward.
- §26.4 table "MIDR (Main ID Register) of the core. `0x410FC075` decodes as: implementer `0x41` (ARM), variant `0xF`, architecture `0xC`, primary part `0xC07` (Cortex-A7)" — good content but no pointer to ARM ARM section that defines this register. Add "see ARM ARM, B6.1.107".
- §26.4 "Contiguous Memory Allocator": one-line definition needed ("a kernel allocator that reserves a physically-contiguous region at boot, mainly for DMA that cannot scatter-gather").

## Ch27 — Device Tree
### AI wording / sledgehammer / buzzwords
- > "the Device Tree is the single biggest mental shift for an MCU engineer moving to Linux. There is no `arch/arm/mach-mx6/board-mx6ull.c` with hand-written platform device tables anymore."
  - Rewrite: tone down "single biggest mental shift" (repeated in §27.11). "DT is the biggest mental shift in this chapter. There is no longer a hand-written `board-*.c` with platform device tables."
- > "Internalise this and the rest of DT is grammar."
  - Rewrite: "Internalise" is buzzword. "Once you have this, the rest of DT is just grammar."
- > "By 2010 the ARM `arch/` tree held thousands of such files and Linus Torvalds publicly complained that ARM was \"a fucking pain in the ass\". The community's response was to adopt the **Device Tree**, which had been used on PowerPC since the early 2000s — borrowed in turn from Open Firmware on Sun and Apple machines."
  - Rewrite: drop em-dash chain. Two sentences. "...which had been used on PowerPC since the early 2000s. PowerPC in turn borrowed it from Open Firmware on Sun and Apple machines."
- > "The kernel binary is now genuinely generic across the ARM ecosystem."
  - Rewrite: drop "genuinely" and "ecosystem". "One ARM kernel binary now works across many boards."
- > "*This is how the kernel finds drivers for hardware.*"
  - Rewrite: italic emphasis is fine, but the phrasing is over-condensed. "This is how the kernel matches drivers to hardware at boot."
- > "You did not recompile the kernel. You did not touch the rootfs. You added a hardware description and the kernel did the rest. This is the model that justifies the DT's existence."
  - Rewrite: triplet + sledgehammer. "You did not recompile the kernel or touch the rootfs. You added a hardware description and the kernel handled the rest. This is why DT exists."
- > "Internalise it and Part VI is dramatically easier."
  - Rewrite: "Internalise" again. "Once this clicks, Part VI is much easier."

### ESL readability
- > "Each `pinctrl-N` references a pin-configuration node. `pinctrl-names` gives a symbolic name per state. The driver activates a state with `pinctrl_select_state(p, \"default\")`."
  - Rewrite: link the sentences. "Each `pinctrl-N` points to a pin-configuration node, and `pinctrl-names` gives each one a symbolic name. The driver picks a state with `pinctrl_select_state(p, \"default\")`."
- > "References — the angle-bracket form combined with the `&label` shortcut — get richer:"
  - Rewrite: em-dash chain. "References use the angle-bracket form together with the `&label` shortcut. They can be richer:"
- > "Reads as: \"two clock entries; each is (a reference to the `clks` node, plus an integer index).\" The clock provider — the node labelled `clks` — interprets the integer."
  - Rewrite: "This says: two clock entries. Each entry is a reference to the `clks` node plus an integer index. The clock provider (the node labelled `clks`) decides what that integer means."

### Needs more explanation
- §27.6 "`/chosen`": properties listed (bootargs, stdout-path, linux,initrd-start, kaslr-seed) but no explanation of *why* `/chosen` exists as a separate node and how it differs from hardware nodes. Add one sentence: "The `chosen` node is *not* hardware. It is a place for the bootloader to pass runtime arguments to the kernel."
- §27.6 "phandle": the word is used in §27.4 "phandle/reference target" and again in §27.10 "Look up a phandle (a &label reference)". A standalone one-paragraph definition early on: "A phandle is the numeric ID assigned by `dtc` when you write `&label`. The DTB stores it as an integer; the kernel uses it to find the target node."
- §27.7 "`simple-bus` ... is the magic that tells the kernel to *automatically* recurse into child nodes and probe them" — explain *how*: `drivers/of/platform.c::of_platform_default_populate` walks each `simple-bus` parent and creates a platform_device for each child. Otherwise the reader sees "magic" with no mechanism.
- §27.9 "ConfigFS overlay": shown in two commands but ConfigFS itself is not introduced. One sentence: "ConfigFS is a virtual filesystem that lets user space create kernel objects by `mkdir`."
- §27.5 "cell": good definition, but immediately after, `<&clks IMX6UL_CLK_UART1_IPG>` mixes a phandle and an enum constant inside `<>`. Add one line: "Inside angle brackets, anything can be a 32-bit value: a literal number, a `&label` (resolved to a phandle), or a `#include`-d constant like `IMX6UL_CLK_UART1_IPG`."

## Ch27A — DT bindings YAML
### AI wording / sledgehammer / buzzwords
- > "Master one binding YAML and you can read or write any of them."
  - Rewrite: "Master" is grandiose. "Read one binding YAML carefully and the rest follow the same pattern."
- > "This single file replaces what used to be ~30 lines of free-form English, and it's machine-verifiable."
  - Rewrite: minor. "This one file replaces ~30 lines of English prose, and it can be checked by tools."
- > "Schema is necessary, not sufficient."
  - Rewrite: classic sledgehammer ("Not X — but Y" cousin). "The schema catches some bugs but not all. You still need to test on real hardware."
- > "Run `dt_binding_check` against your own binding *first*; only then propose it upstream."
  - Rewrite: semicolon. "Run `dt_binding_check` against your own binding first. Only then propose it upstream."

### ESL readability
- > "(a) Just `fsl,imx1-uart` or `fsl,imx21-uart` alone. (b) `fsl,imx25-uart` (or one of several others) followed by a fallback to `fsl,imx21-uart`. (c) A three-string list ending in `fsl,imx21-uart`. Anything else is rejected."
  - Rewrite: list-as-prose. "Three legal forms: just `fsl,imx1-uart` or `fsl,imx21-uart`; a SoC string followed by `fsl,imx21-uart` as fallback; or a three-string list ending in `fsl,imx21-uart`."
- > "`maxItems: 1` says \"up to one entry, of any type\". `items: [- description: foo]` says \"exactly one entry, described as foo\". Different. Use the latter when you want to document semantics."
  - Rewrite: choppy. "`maxItems: 1` means up to one entry of any type. `items: [- description: foo]` means exactly one entry, described as foo. These are different — use the second form when you want the description to appear in the docs."

### Needs more explanation
- §27A.2 "$ref: serial.yaml#" inheritance: shown in the example, mentioned briefly. Expand: where does `serial.yaml` live, what does it contribute, and why every UART binding pulls it in. Two sentences.
- §27A.6 inheritance: "These parents define standard properties common to the *class*" — give an example of what `i2c-controller.yaml` actually adds (`#address-cells`, `#size-cells`, `clock-frequency`, child node validation). Otherwise the section is abstract.
- §27A.2 `unevaluatedProperties: false` vs `additionalProperties: false` — pitfalls section mentions the difference but `unevaluatedProperties` is introduced in the example with no prior explanation. Define both in §27A.2.

## Ch28 — Kernel startup, traced
### AI wording / sledgehammer / buzzwords
- > "the kernel boot path is large but knowable. Every line you trace is something you no longer fear when it goes wrong."
  - Rewrite: dramatic. "The boot path is long but readable. Each line you trace becomes one less thing that surprises you when something breaks."
- > "the boss function"
  - Rewrite (referring to `start_kernel()`): "the main C entry point" or "the function that runs every init step".
- > "After this point, the kernel is in steady-state. User-space processes run; the kernel responds to syscalls and interrupts. We have completed the boot."
  - Rewrite: semicolon + summary cliché. "After this point, the kernel is in steady state. User-space processes run. The kernel responds to syscalls and interrupts. The boot is done."
- > "That table is the deliverable of this chapter. After Chapter 28 you can grep the kernel for any boot-log string and find where it came from in under 60 seconds."
  - Rewrite: "deliverable" is buzzword. "That table is the goal of this chapter. After it, you can grep the kernel for any boot-log line and find its source in under a minute."
- > "Worth pinning:"
  - Rewrite: hedging opener. Drop or replace with "Four points worth noting:" → "Four points to keep in mind:"

### ESL readability
- > "Walks roughly:"
  - Rewrite: too compressed. "It does roughly the following:" or "The main steps are:"
- > "The kernel reaches user-space when it prints..."
  - Rewrite: OK on its own, but the surrounding paragraph chains a long sentence with semicolons in §28.4 console_init line. Split: "Until this point, all `printk` output went to one of two places. Either it sat in the `printk` ring buffer for `dmesg` to read later, or it was pushed to the UART by `earlycon` if the bootloader configured that. After `console_init()`, every later `printk` reaches the UART in real time."
- > "(Why a separate task? Because creating kthreads requires holding certain locks, and the boot thread can't easily acquire them.)"
  - Rewrite: in-line parenthetical breaks the flow. "There is a separate task for this because creating kthreads needs certain locks that the boot thread cannot easily take."

### Needs more explanation
- §28.2 "`__create_page_tables` builds a flat identity-mapped 1-MiB-section page table" — for an MCU reader this is dense. Explain: identity-mapped means VA==PA; 1-MiB section means using ARMv7 short-descriptor format with first-level only (no L2 tables); "just big enough" means a few entries covering kernel image plus the DT.
- §28.2 "`__enable_mmu` sets `SCTLR.M=1`. The next instruction it executes is via virtual addresses; the jump-via-`r13` lands at `__mmap_switched`" — explain what's at risk: the PC has to remain valid across the MMU switch, so the page table makes the kernel's physical address also valid as a virtual address (identity map). This is critical to understanding.
- §28.4 "`mm_core_init()` brings up ... the page allocator (`buddy`), the slab allocator (`SLUB`)..." — buddy and SLUB are named, not explained. One paragraph: buddy allocator hands out power-of-two page blocks; SLUB sits on top, hands out smaller objects from caches. Both feed `kmalloc`.
- §28.5 "PID 0 (the idle task) doesn't show in `ps` because it's a kernel-internal thread" — say *why* a "task" can be the idle loop. The boot CPU's task_struct continues to exist; after `rest_init`, that task's job is to run `do_idle()`.
- §28.6 "On a successful `exec`, the calling task's image is replaced — `kernel_init()`'s code is unmapped, the new program runs." — this is the most important sentence in Ch28 and is given two clauses. Expand: explain that `kernel_execve` does the same work as a user-space `execve` syscall; what gets unmapped (the kernel `.init.text` containing `kernel_init`), what gets mapped (the ELF image of `/sbin/init`), and how PID 1 stays the same while everything else changes.

## Ch29 — Initramfs from scratch
### AI wording / sledgehammer / buzzwords
- > "the cpio archive as a filesystem image that the kernel unpacks into the initial tmpfs. Once that mental model is solid, the rest is mechanics."
  - Rewrite: "Once that mental model is solid, the rest is mechanics" is a sledgehammer. "Once that model is clear, the rest is just commands."
- > "That's it. The smallest user space that boots Linux on this hardware. **30 KB compiled. Two lines of effort.**"
  - Rewrite: triplet + emphasis. "That is the smallest user space that boots Linux on this board: 30 KB compiled."
- > "`hello` is a curiosity. A practical embedded initramfs has a shell, some utilities, and an init system."
  - Rewrite: triplet rhythm. "`hello` is just a demo. A practical initramfs has a shell and some utilities, plus an init system."
- > "Once you've done it once, everything else in Part V (Buildroot, Ubuntu-base, overlayfs) is \"the same plus features.\""
  - Rewrite: vague. "Once you have done it once, Buildroot and Ubuntu-base in Part V build on the same idea, just with more pieces."

### ESL readability
- > "BusyBox packs all of those into one ~600 KB statically-linked binary that exposes hundreds of applets (every Unix utility you remember and several you forgot)."
  - Rewrite: idiom "you remember/forgot". "BusyBox packs all of these into one statically-linked binary of about 600 KB. It exposes hundreds of applets — most of the common Unix utilities."
- > "Option 1 is simpler for tiny one-binary images. Option 2 is more flexible (you can change the rootfs without rebuilding the kernel) and is the standard choice for any non-trivial image."
  - Rewrite: parenthetical breaks flow. "Option 1 is simpler for tiny images. Option 2 is more flexible — you can change the rootfs without rebuilding the kernel — and is the standard choice for anything bigger."
- > "Trailing slash on `find .`. `find . | cpio ...` produces relative paths starting with `./` — that's what cpio expects. `find /home/you/initramfs | cpio ...` produces absolute paths, which give you a `/home/you/initramfs/init` inside the archive — and the kernel doesn't find `/init`. Always `cd` into the rootfs first."
  - Rewrite: long, em-dash chain. "Trailing slash on `find .`. `find .` gives relative paths like `./init`, which is what cpio wants. `find /home/you/initramfs` gives absolute paths, so the archive ends up with `/home/you/initramfs/init` and the kernel cannot find `/init`. Always `cd` into the rootfs first."

### Needs more explanation
- §29.1 "tmpfs": named once, never defined. One sentence: "tmpfs is a RAM-backed filesystem; files written to it live only in memory."
- §29.1 "cpio archive": mention the on-disk layout briefly — header per file with mode/uid/gid/path, then file contents, terminated by a special `TRAILER!!!` entry. Otherwise it is treated as a black box.
- §29.2 "MUST be named \"init\" at the root" — explain *why*: in §29.6 the search order is described, but here the reader meets the requirement first. One line: "The kernel's `kernel_init` calls `/init` first by default (see §28.6); other names need `init=` or `rdinit=`."
- §29.3 "`bootz 0x82000000 0x84000000 0x83000000` — the second argument is now the initrd address (no longer `-`). U-Boot writes both `linux,initrd-start` and `linux,initrd-end` into the DT." — explain the DT path: under `/chosen`, two properties hold the address range; the kernel's `early_init_dt_scan_chosen` reads them. This ties back to Ch27's `/chosen` discussion.
- §29.4 "busybox knows to run as init when called this way" — one sentence on argv[0] dispatch in BusyBox.

## Ch30 — Kernel configuration deep-dive
### AI wording / sledgehammer / buzzwords
- > "Knowing where each knob lives and what it does is the difference between \"Linux works\" and \"Linux works the way *we* need it to.\""
  - Rewrite: classic "Not X but Y". "Knowing where each knob lives lets you build a kernel that fits your product, not just one that boots."
- > "**`.config` is the source of truth.** Every other interface (`menuconfig`, `xconfig`, etc.) is just a UI on top. Read it, edit it carefully, regenerate, repeat."
  - Rewrite: triplet + buzzword. "`.config` is the canonical file. `menuconfig`, `xconfig`, and the others are just UIs that edit it. Read it, edit through the UI, and rebuild."
- > "You can read every help text in `menuconfig` and learn nothing useful for hours."
  - Rewrite: dismissive opening. "Reading every help text in `menuconfig` takes hours and is not the fastest way to learn what matters. Here are the dozen options that matter most on the path from `defconfig` to an i.MX6ULL image:"
- > "Disabling `CONFIG_PREEMPT_VOLUNTARY` to \"make it faster\". What you actually get is `CONFIG_PREEMPT_NONE`..."
  - Rewrite: "What you actually get" sneer. "If you turn off `CONFIG_PREEMPT_VOLUNTARY`, the build falls back to `CONFIG_PREEMPT_NONE`, which is the server profile (higher latency, higher throughput). On an interactive system this is a regression."

### ESL readability
- > "the entire state lives in **`.config`** at the kernel-tree root. It's a plain text file — every line is either `CONFIG_FOO=y`, `CONFIG_FOO=m`, `CONFIG_FOO=\"string\"`, `CONFIG_FOO=10`, or `# CONFIG_FOO is not set`."
  - Rewrite: long em-dash sentence. "The entire state lives in `.config` at the kernel-tree root. It is plain text. Each line is one of: `CONFIG_FOO=y`, `CONFIG_FOO=m`, `CONFIG_FOO=\"string\"`, `CONFIG_FOO=10`, or `# CONFIG_FOO is not set`."
- > "Two commands; the second engineer has the same kernel."
  - Rewrite: semicolon, choppy. "With those two commands, the second engineer has the same kernel."
- > "**PREEMPT_RT** turns the kernel into a low, bounded-latency real-time kernel"
  - Rewrite: "low, bounded-latency" is awkward. "`PREEMPT_RT` turns the kernel into a real-time kernel with bounded, low latency."

### Needs more explanation
- §30.1 "Kconfig": the *language* is never explained. A Kconfig file defines symbols with `config FOO`, default values, dependencies (`depends on`), and selects (`select`). Without this, the reader cannot answer "where does this option come from?". Add a 6-line example.
- §30.4 "*minimum* set of options that, applied on top of the architecture's defaults, reproduces your `.config`" — explain what "architecture defaults" means concretely: every `config FOO` symbol's `default y/n` clause in every Kconfig file under `arch/arm/`. `savedefconfig` only writes lines that differ from those defaults.
- §30.5 `CONFIG_PREEMPT_*` — the four modes are listed and described, but the reader has no model of *what preemption is*. One paragraph: kernel preemption means the scheduler is allowed to take the CPU away from kernel code (not just user code) when a higher-priority task wakes up. Each level decides where in kernel code that is allowed.
- §30.5 `CONFIG_NO_HZ_*` — "stop the tick" needs one more sentence about which timer (the periodic scheduler tick at HZ), and why stopping it saves power (the CPU can stay in WFI longer).

## Ch30A — Kernel lifecycle
### AI wording / sledgehammer / buzzwords
- > "the single most consequential architectural choice in any Linux-based product"
  - Rewrite: superlative. "one of the most important architectural choices in any Linux-based product".
- > "Get it right and the product ships updates effortlessly; get it wrong and three years from now you're trying to backport six years of CVEs onto a fork no one upstream cares about."
  - Rewrite: dramatic + semicolon. "If you choose well, updates ship easily for years. If you choose poorly, three years from now you are backporting six years of CVEs onto a fork no one upstream maintains."
- > "Whatever you pick, you commit to *maintaining* — or paying someone to maintain — the gap between it and whatever the world is doing next."
  - Rewrite: em-dash chain. "Whatever you pick, you commit to maintaining the gap between it and what the world ships next. If you cannot maintain it yourself, you pay someone who will."
- > "5.4 ends in Dec 2025. Forever is shorter than you think."
  - Rewrite: poetic. "5.4 ends in Dec 2025. That is not forever."
- > "the field-life of the product, multiplied by the security-tolerance of the application, determines the kernel track."
  - Rewrite: clean enough, but "multiplied by" reads as math when it isn't. "The product's field life and the security level required together determine the kernel track."
- > "Mainline drift. Every quarter, the vendor's tree diverges further from mainline. Any patch you write against the vendor BSP is not directly applicable to mainline. Your work has half-life."
  - Rewrite: "Your work has half-life" is buzzword-poetry. "Every quarter, the vendor's tree drifts further from mainline. Any patch you write against the BSP needs porting before it works against mainline. The longer you wait, the harder that port becomes."
- > "**Plug it in, it works.**"
  - Rewrite: minor; the bold "**The upside**" already labels it. Drop the bold sentence and just say "Every peripheral on the vendor's reference board has a working driver."

### ESL readability
- > "A common scenario: you find an existing vendor BSP pinned to Linux 4.1.15 (NXP's i.MX BSP from 2017). The hardware works. The board boots. You're tempted to ship it."
  - Rewrite: choppy triplet. "Here is a common scenario. You inherit a vendor BSP pinned to Linux 4.1.15 (NXP's i.MX BSP from 2017). The hardware works and the board boots, so you are tempted to ship it."
- > "What you're really shipping:"
  - Rewrite: sales-tone. "What you would actually be shipping:"
- > "**\"We don't need security fixes; the device isn't on the internet.\"** Increasingly false. Even isolated devices get USB sticks. Even airgapped devices get supply-chain attacks. Apply security fixes."
  - Rewrite: triplet + sermon. "\"We don't need security fixes; the device isn't on the internet.\" This is less and less true. Even isolated devices receive USB sticks. Even airgapped devices face supply-chain attacks. Apply the fixes."

### Needs more explanation
- §30A.1 table mentions **Yocto / Buildroot kernel** and **Distribution kernel** but the chapter never returns to them. Either give a one-sentence rationale ("we revisit Yocto kernel curation in Part X") or drop those rows.
- §30A.4 "extended LTS (CIP)" — Civil Infrastructure Platform is mentioned without saying what it actually is (a Linux Foundation project specifically for industrial systems, funded by Toshiba/Siemens/Renesas, providing 10+ year security backports for selected LTS branches). Add two lines.
- §30A.5 "vendor patches. Thousands." — give one concrete example of *what kind* of patch (e.g., NXP's i.MX VPU driver, or their power-domain refactor that never went upstream). Otherwise "thousands" is hand-wavy.
- §30A.7 "4.1.15 doesn't build with modern gcc (>= 11) without patches" — say *why*: gcc 11 added stricter checks (`-Wno-error` defaults changed), and the 4.1 kernel uses constructs (variable-length arrays in structs, some K&R-isms) that newer gcc warns or errors on by default.

Done.
