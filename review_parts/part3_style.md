# Part III — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining is the dominant AI tic across all 7 chapters.** Almost every long sentence has an em-dash splice ("X — Y" where Y elaborates or contrasts). Many can be periods or simple commas. Suggest a global pass.
- **Semicolons used as soft periods** ("X; Y." where Y is an independent clause). Same fix: period.
- **"Productized" / "productize"** is a buzzword the author repeats ("Ch 14 productized", "your Chapter 14 work, productized"). It sounds marketing-speak. Replace with "the production version of" or "the real-world version of".
- **Royal "we" overuse**: "We will use...", "We use mainline...", "We did it.", "We dissect it in Ch 20 §20.7." Engineer-voice can drop most of these.
- **Dramatic single-sentence paragraphs** ("That's it.", "Pattern 2 is what mainline does.", "Read it.", "We did it.", "Painful.") — used so often it becomes a rhetorical tic.
- **"This is the most..." / "the cleanest..." / "the entire point" superlatives** appear in nearly every chapter (Ch19 §19.7, Ch20 §20.5, Ch21 §21.4). Tone them down.
- **Triplet rhythm** appears in pitch-style paragraphs (Ch19 intro: "what makes it different from full U-Boot, what fits in 64 KB of OCRAM, and how it loads its successor"; Ch24: "edit on host, network-boot on target, no SD-card reflashing"). Acceptable once per chapter, not three times.
- **Sledgehammer "not X — Y"** constructions: "SPL does not run the kernel. SPL does not handle networking. SPL does not have a command prompt." (Ch20 §20.2) Effective once; becomes mannered after the second time in a chapter.
- **Hedging openers** mostly avoided — good. But "Notice:" / "Notice that" appears often and reads pedagogical-stiff.
- **Buzzword count is low** (no delve/leverage/seamless/comprehensive). Author has good baseline discipline. The remaining offenders are mostly em-dashes and the "productized"/superlative tic.

---

## Ch19 — U-Boot from source

### AI wording / sledgehammer / buzzwords

- > "From here on the question is no longer 'can we?' but 'what does the professional version of this work look like?' U-Boot is that version. Reading its source is the most concentrated lesson in real-world embedded-Linux engineering available."
  - Rewrite: "From here on the question is what the professional version looks like. U-Boot is that version. Its source is one of the best embedded-Linux codebases to read."
- > "Three structs and one function call. Inside `mx6_ddr3_cfg` ... you will find ~600 lines that do *exactly* what your Chapter 14 `ddr_init` does — pad config, MMDC core registers, MR loads, ZQ cal, write-leveling — but parameterized, table-driven, and validated across every Micron / Nanya / ISSI DDR3 part NXP supports."
  - Rewrite: "Three structs and one function call. Inside `mx6_ddr3_cfg`, you'll find ~600 lines doing the same job as your Chapter 14 `ddr_init`: pad config, MMDC core registers, MR loads, ZQ cal, write-leveling. The difference is that it is table-driven and validated across every Micron, Nanya, and ISSI DDR3 part NXP supports."
- > "Read it. It is the cleanest production-grade DDR3 init code in any open-source project. The fact that it does not look magical to you is the entire point of Chapter 14."
  - Rewrite: "Read it. After Chapter 14, none of it should look magical. That is the point."
- > "The productized version of your Chapter 14 MMDC bring-up — mainline's `arch/arm/mach-imx/mx6/ddr.c` is a ~1500-line table-driven engine that wraps the same MMDC register dance, hardened across thousands of boards."
  - Rewrite: "The production version of your Chapter 14 MMDC bring-up. Mainline's `arch/arm/mach-imx/mx6/ddr.c` is a ~1500-line table-driven driver that wraps the same MMDC sequence, hardened across thousands of boards."
- > "DRAM works. Same DRAM we configured by hand in Chapter 14, but the SPL did it for us this time."
  - Rewrite: "DRAM works. Same DRAM as Chapter 14, but SPL configured it this time."
- > "Pause. Read the boot log a third time."
  - Rewrite: "Read the boot log again, slowly." (Drop the dramatic "Pause.")
- > "If you press a key before the autoboot counts down, you land at the `=>` prompt. We did it."
  - Rewrite: "If you press a key during autoboot, you land at the `=>` prompt."
- > "Disk is cheap; we keep history."
  - Rewrite: "Disk is cheap. Keep the history."

### ESL readability

- > "Older systems may need an explicit `--depth=1` to avoid pulling ~50 MB of git history."
  - Rewrite: "On slow connections, add `--depth=1` to skip ~50 MB of git history."
- > "A few interesting moments scroll past:"
  - Rewrite: "A few interesting lines scroll past:"
- > "When `make` returns to the prompt without errors, the build artefacts are:"
  - Rewrite: "When `make` finishes without errors, the build produces these files:"
- > "Actually, for the SD-boot case the SPL is what carries the IVT, and the SPL loads `u-boot-dtb.imx` (or `u-boot.img`) from a later offset on the card."
  - Rewrite: "For the SD-boot case, SPL carries the IVT. SPL then loads `u-boot-dtb.imx` (or `u-boot.img`) from a later offset on the card."
  - Note: "Actually," is a hedge opener; drop it.
- > "A more pleasant alternative: `uuu` can do the whole thing over USB-OTG without an SD card."
  - Rewrite: "A nicer alternative: `uuu` does the whole thing over USB-OTG, no SD card needed."

### Needs more explanation

- §19.5 "Loading Environment from MMC...": the env subsystem is introduced in one bullet ("U-Boot tries to read its persistent env from the SD card"). For a first-time U-Boot reader, expand: what is the env, what storage backend, where on the SD card, what `CONFIG_ENV_OFFSET` means. (You do cover it in Ch21 §21.6 — add a forward reference.)
- §19.5 "relocaddr = 0x9ff37000. This is the actual address U-Boot is running from right now": relocation is one of the hardest U-Boot concepts and gets a one-line mention here. Add 2-3 sentences on *why* (kernel landing zone) with a forward reference to Ch21 §21.4.
- §19.3 "`u-boot.imx` ... the file to flash for SD-boot when no SPL is needed": the SPL vs no-SPL decision is dropped on the reader in one cell. Add a short paragraph: when does U-Boot fit in OCRAM, why i.MX6ULL needs SPL, where this is configured.
- §19.6 `bdinfo`: `fdt_blob = 0x9ed3d2c0` and the explanation "It will pass this address to the kernel via `r2` when it eventually `bootz`'s Linux" — for an MCU engineer who hasn't seen Linux boot ABI, the `r2 = DTB` convention deserves a sidebar (ARM boot protocol: r0=0, r1=machine type, r2=ATAGs/DTB pointer).

---

## Ch20 — U-Boot SPL

### AI wording / sledgehammer / buzzwords

- > "the i.MX6ULL OCRAM is 128 KB total at `0x00900000`, but the Boot ROM reserves the bottom of it (`0x00900000–0x00906FFF`, ~28 KB) for its own working area + scatter buffers. That leaves a **~68 KB practical window** for an SPL image (`0x00907000–0x0091FFFF`). Full U-Boot is ~600 KB and can't fit; SPL bridges that gap — a small first-stage program that initializes DRAM, loads full U-Boot into DRAM, and jumps to it. Mechanically, SPL is your Chapter 11–14 work, productized."
  - Rewrite: "The i.MX6ULL OCRAM is 128 KB at `0x00900000`. The Boot ROM reserves the bottom ~28 KB (`0x00900000–0x00906FFF`) for its own scratch space. That leaves a ~68 KB window for SPL (`0x00907000–0x0091FFFF`). Full U-Boot is ~600 KB and does not fit. SPL is the small first-stage program that bridges the gap: it brings up DRAM, loads full U-Boot into DRAM, and jumps to it. Mechanically, SPL is the production version of Chapters 11–14."
- > "**This is the modern pattern.**"
  - Rewrite: drop the bold, drop the sentence; the paragraph already says "Mainline does this."
- > "Two stages, one for setup, one for the main job. The pattern repeats further up the stack: U-Boot then loads Linux, and Linux loads `/sbin/init`. Each stage knows more than the previous and runs from more resources."
  - Rewrite: "Two stages: one to set up, one to do the real job. The same pattern repeats higher up. U-Boot loads Linux. Linux loads `/sbin/init`. Each stage has more resources than the one before."
- > "That is it. SPL does not run the kernel. SPL does not handle networking. SPL does not have a command prompt. SPL is the smallest program that can do exactly the seven things above on this hardware."
  - Rewrite: "That is the whole list. SPL does not run the kernel, handle networking, or offer a command prompt. It is the smallest program that can do the seven steps above on this hardware."
- > "The headroom is real; the discipline is mandatory."
  - Rewrite: "The headroom exists, but the discipline is mandatory." (Or drop the line — the paragraph already makes the point.)
- > "You can read each of these files in under 10 minutes per file. Together they are the cleanest reference implementation of a bootloader's first stage available in open source."
  - Rewrite: "Each file reads in under 10 minutes. Together they are a clean reference for a bootloader's first stage."
- > "The structural shape is identical to ours. Production U-Boot adds the safety nets and SoC-family abstractions that we skipped because we only had one SoC."
  - Rewrite: "The structure matches ours. Production U-Boot adds the safety nets and SoC-family abstractions we skipped because we targeted only one SoC."
- > "After this function returns... no, it doesn't return. `board_init_r` is a tail-call: it never returns, the SPL keeps running, the SPL never exits."
  - Rewrite: "`board_init_f` does not return. It tail-calls `board_init_r`, which also never returns. SPL keeps running until it jumps to U-Boot."
- > "That's the entire handoff: cast the load address to a function pointer and call it."
  - Rewrite: "The handoff is one C statement: cast the load address to a function pointer and call it."

### ESL readability

- > "Patten 2 is what mainline does. Two stages, one for setup, one for the main job. The pattern repeats further up the stack..."
  - Rewrite (combined): "Mainline uses Pattern 2: two stages, one for setup, one for the main work. The same pattern repeats up the stack — U-Boot loads Linux, Linux loads `/sbin/init`."
- > "If `text + data + bss > CONFIG_SPL_MAX_SIZE` (~64 KB on the EVK defconfig), the build emits a warning — but not always under every linker configuration, so verify with `size` after every change. Exceed the practical OCRAM window and the ROM will silently refuse the image."
  - Rewrite: "If `text + data + bss > CONFIG_SPL_MAX_SIZE` (~64 KB on the EVK defconfig), the build usually warns. The warning is not reliable under every linker config, so always check with `size` after a change. If SPL exceeds the OCRAM window, the ROM silently refuses to load it."
- > "Compare your specific SPL's DCD content against the EVK board's `.cfg` file (`board/freescale/mx6ull_14x14_evk/mx6ull_14x14_evk.cfg`) to confirm what's actually there."
  - Rewrite: "Compare your SPL's DCD against the EVK board's `.cfg` file (`board/freescale/mx6ull_14x14_evk/mx6ull_14x14_evk.cfg`) to see what is actually written."

### Needs more explanation

- §20.6 `board_init_f`: "The 'f' stands for 'flash' (historical — back when U-Boot ran first from flash, before it relocated itself to RAM)." Good — keep. But the "five calls, each is a chapter from Part II" line is too brief. List which Part-II chapter each call corresponds to (you do this implicitly in §20.2 but not here).
- §20.8 "Does SPL have a DCD?": the DCD concept is treated as if the reader knows it cold. ESL readers will benefit from a one-line refresher: "Recall: DCD is a small register-write script the Boot ROM executes before handing control to the loaded image (Ch 7 §7.X)." Add the back-reference.
- §20.9 SPL-to-U-Boot handshake: the four-bullet list ("Full U-Boot's code is at..., DRAM is alive, cache is in a known state, stack...") is dense. Each item is non-obvious for a newcomer. Expand "the cache is in a known state" — what does "known" mean here? I-cache disabled, D-cache flushed, MMU off. Be explicit.
- §20.3 "every feature pays for itself in bytes": this is the most important framing in the chapter but only appears in the §20 banner. Pull it forward and give one concrete example: "Enabling `CONFIG_SPL_NET` adds ~12 KB. On a 64 KB budget, that is 19%. That is why SPL never has networking."

---

## Ch21 — U-Boot internals

### AI wording / sledgehammer / buzzwords

- > "Each step has a name we can grep for. Each step is < 200 lines. Total reading time, all of it, end-to-end, ~3 hours. Do it once and the bootloader stops being a black box."
  - Rewrite: "Each step has a name you can grep for. Each is under 200 lines. End-to-end reading takes about 3 hours. Do it once and U-Boot is no longer a black box."
- > "This is the most surprising design choice in U-Boot for a newcomer. Let's pin it down."
  - Rewrite: "Relocation is the most confusing U-Boot design for a newcomer. Here is how it works."
- > "The post-copy `bx lr` is the **single most important instruction** in this entire chapter."
  - Rewrite: "The post-copy `bx lr` is the key instruction. Before it, the CPU runs the original U-Boot in low DRAM. After it, the CPU runs the relocated copy in high DRAM."
- > "That's the relocation handshake. Every detail matters."
  - Rewrite: "That is the relocation handshake." (Drop the "every detail matters" — empty emphasis.)
- > "Conceptually identical to Linux's `struct device` + `struct driver`, but much smaller."
  - Rewrite: "Same idea as Linux's `struct device` + `struct driver`, but much smaller."
- > "You write a Linux driver later in Chapter 39 and the structure will look almost identical. That is not a coincidence — DM was deliberately modeled on the Linux driver model."
  - Rewrite: "You will write a Linux driver in Chapter 39 with almost the same structure. DM was modeled on the Linux driver model on purpose."
- > "Now you can also predict, with high confidence, where to look in the source if any of those lines reports an error."
  - Rewrite: "If any of those lines reports an error, you now know which source file to open."
- > "Eight lines of code, one Makefile line. You have just shipped a U-Boot patch — a tiny one, but a real one. This is the discipline pattern for everything in `cmd/`."
  - Rewrite: "Eight lines of code, one Makefile line. That is a real U-Boot patch, small but complete. Every command in `cmd/` follows this pattern."

### ESL readability

- > "When U-Boot was originally built for embedded systems running from flash, relocation made sense: 'copy yourself from slow XIP flash to fast RAM, fix pointers, run from RAM.' On a modern i.MX6ULL booting from SD via SPL, U-Boot is already in RAM. So why relocate?"
  - Rewrite (good as is, but split): "Originally U-Boot ran from flash. Relocation meant: copy yourself from slow XIP flash to fast RAM, fix pointers, run from RAM. On a modern i.MX6ULL booting from SD via SPL, U-Boot is already in RAM. So why relocate?"
- > "Two stages, one for setup, one for the main job." (cross-reference to Ch20; recurring phrasing pattern)
- > "After this, the original U-Boot in low DRAM is reusable memory — the kernel can land there."
  - Rewrite: "After the jump, the old copy in low DRAM is free memory. The kernel can be loaded there."
- > "Read that list top to bottom. **It is the entire pre-relocation boot.** Each entry is a small function in the same file (or in `arch/`, `lib/`, etc.). Each is < 50 lines. The architecture is: *one giant array of function pointers, walked in order, halt on the first non-zero return.*"
  - Rewrite: "Read the list top to bottom. That is the entire pre-relocation boot. Each entry is a small function (< 50 lines) in the same file or in `arch/` / `lib/`. The design is simple: one array of function pointers, walked in order, stop on the first non-zero return."
- > "Most 'my env change didn't stick' bug reports are this."
  - Rewrite: "Most 'my env change didn't stick' bugs are this."
- > "The fact that it does not look magical to you..." (recurring tic, also in Ch19)

### Needs more explanation

- §21.4 "U-Boot is built with **position-independent code** (`-fpic` / `-fpie`) and a **relocation table** in `.rel.dyn`": for an MCU engineer who has never built PIC code, this needs 3-4 lines on what PIC actually means (no fixed absolute addresses in instructions; jumps are PC-relative; data references go through a table). The current explanation assumes the reader has seen dynamic linking before, which an MCU engineer often hasn't.
- §21.5 command system: the `__attribute__((section(...)))` + linker-collected-array trick is the most "magical" pattern in U-Boot. Expand: what is a linker section, how does the linker collect `.u_boot_list_2_cmd_*` patterns, how `__u_boot_list_2_cmd_start` / `__u_boot_list_2_cmd_end` get defined (in the linker script). One paragraph would unlock the next 50 chapters.
- §21.6 env persistence: the section says "stored on the boot medium" and lists offsets, but does not explain the **redundant env** pattern (`CONFIG_ENV_OFFSET_REDUND`) — many production boards use two env copies with sequence numbers for power-fail safety. Mention it, even briefly, since the user listed env persistence as a hard concept.
- §21.7 DM probe: the lifecycle (bind → probe → remove → unbind) is glossed; "DM matches the device to a driver in its uclass and calls the driver's `probe()`" skips the *bind* phase entirely. For a reader who will write DM drivers in Ch22 and Linux drivers in Ch39, the bind-vs-probe distinction matters.
- §21.3 `gd_t`: introduced as "single structure that holds pointers and state used everywhere" and never expanded. List the 5-6 most important fields (`flags`, `bd`, `env_addr`, `relocaddr`, `ram_size`, `fdt_blob`). Without this, the later `[r9, #GD_START_ADDR_SP]` reads as magic.

---

## Ch22 — U-Boot board port

### AI wording / sledgehammer / buzzwords

- > "in real product work, you almost never ship the vendor reference board. You ship a custom PCB that resembles the reference but has different pads, different I/O, different DRAM. The port is the *deliverable*. This chapter is how you produce it."
  - Rewrite: "In real product work, you rarely ship the vendor reference board. The custom PCB looks similar but has different pads, different I/O, different DRAM. The port is the deliverable."
- > "Once you have done one port, every subsequent one is a copy-and-modify of the same five files."
  - Rewrite: "After the first port, every later one is a copy-and-modify of the same five files."
- > "This is the part you cannot fake."
  - Rewrite: "This part you cannot fake." (Or simply: "There is no shortcut for DDR.")
- > "That single call performs every register write Chapter 14 documented."
  - Rewrite: "That one call performs every register write from Chapter 14."
- > "If any fails, the per-line section above tells you which file to revisit."
  - Rewrite: "If any check fails, go back to the section that introduced that peripheral and check the file mentioned there."

### ESL readability

- > "Closer to variant but with DDR and pinmux changes."
  - Rewrite: "It is mostly a variant port plus DDR and pinmux work."
- > "The 90 % of the port lives in `spl.c` (DDR config) and the DTS."
  - Rewrite: "About 90% of the work is in `spl.c` (DDR config) and the DTS."
- > "Add overrides as needed for `board_late_init` (env defaults), `board_phy_config` (RGMII PHY tweaks), `board_eth_init` (PHY address override)."
  - Rewrite: "Add overrides if you need them: `board_late_init` for env defaults, `board_phy_config` for RGMII PHY tweaks, `board_eth_init` for PHY-address overrides."
  - Note: original is a triplet rhythm glued together.
- > "The macros `MX6_PAD_UART1_TX_DATA__UART1_DCE_TX` etc. are generated from the i.MX6ULL IOMUX tables; they encode pad, mux mode, and SELECT_INPUT in one constant."
  - Rewrite: "These macros come from the i.MX6ULL IOMUX tables. Each one encodes the pad, the mux mode, and the SELECT_INPUT value in a single constant."
  - Note: semicolon → period.

### Needs more explanation

- §22.5 device tree: the chapter says "This is the *U-Boot* device tree (used to inform U-Boot of its own board's hardware)" but a reader who hasn't reached Part IV may not yet know U-Boot has its own DT separate from Linux's. A 3-sentence sidebar would help: U-Boot's DT is embedded in the U-Boot binary; SPL has a stripped subset; the kernel's DT is a separate file passed via `r2`. (You mention this in passing in Ch20 §20.7 and Ch22 §22.5 but never connect the three.)
- §22.6 DDR config: the structs are dropped on the reader with brief field comments. For someone who did Ch14, names like `cs_density`, `rtt_nom`, `walat`, `ralat`, `mif3_mode` still need one-line meanings. At least cross-reference the Ch 14 register where each field ends up.
- §22.4 `CONFIG_SYS_TEXT_BASE = 0x87800000`: introduced as a value without explaining why this specific address. Reference Ch21 §21.1a which does explain it, or repeat the explanation briefly here.
- §22.3 Kconfig changes: a reader who has never edited a Kconfig file will be lost on `imply CMD_DM`, `select BOARD_LATE_INIT`. A two-sentence note on `select` vs `imply` semantics would unblock them.

---

## Ch23 — bootcmd, bootargs, FIT

### AI wording / sledgehammer / buzzwords

- > "these three things are the difference between 'U-Boot works' and 'Linux boots.' They are also where most 'the kernel won't start' bugs live. Master them and you can diagnose boot failures from the boot log alone."
  - Rewrite: "These three things sit between 'U-Boot works' and 'Linux boots.' Most 'the kernel won't start' bugs live here. Once you understand them, you can diagnose boot failures from the boot log alone."
- > "After `bootz`, U-Boot is gone. The kernel runs."
  - Rewrite (good — keep as is; this short form actually works for the engineer voice).
- > "It's verbose but the pattern is universal:"
  - Rewrite: "The script is verbose, but the pattern is common to most boards:"
- > "One `setenv bootcmd '...'; saveenv` and the board boots over the network on every power-up. Fast iteration; we use this in Chapter 24."
  - Rewrite: "One `setenv bootcmd '...'; saveenv` and the board network-boots on every power-up. Chapter 24 builds on this."
- > "Understand which knobs are kernel-side and which are U-Boot-side and you stop chasing ghosts."
  - Rewrite: "Know which knobs are kernel-side and which are U-Boot-side, and you stop chasing the wrong file."

### ESL readability

- > "Three commands, very similar names, different jobs."
  - Rewrite: "Three commands with similar names but different jobs."
- > "All three take the same arguments after the address: `[initrd-addr] [dtb-addr]`. The `-` in `bootz 0x82000000 - 0x83000000` means 'no initrd, DTB at the next address.'"
  - Rewrite: "All three take the same arguments after the address: `[initrd-addr] [dtb-addr]`. The `-` in `bootz 0x82000000 - 0x83000000` means 'no initrd; DTB is at the next argument.'"
- > "Mostly useful for distros. For development, edit `bootcmd` directly."
  - Rewrite: "Boot scripts are mostly for distros. For development work, just edit `bootcmd`."
- > "A FIT can carry **multiple DTBs and multiple configurations**."
  - Rewrite: "A FIT can hold several DTBs and several configurations."

### Needs more explanation

- §23.2 bootargs → DT chosen node: this is a critical "contract" but the mechanism gets 3 lines. Expand: at `bootm`/`bootz` time, U-Boot finds the `/chosen` node in the in-memory DT, sets `bootargs` property to the env var's value, *then* passes the DT pointer to the kernel in `r2`. The kernel's early init reads `/chosen/bootargs` to populate `boot_command_line`. Without this sequence diagram, the reader cannot debug an `earlycon` problem.
- §23.5 FIT: "FIT is a single binary container that holds one or more *images*..." — the actual on-disk format is not described. Add 2-3 lines: a FIT is a DTB (compiled with `mkimage`) where each /images/* subnode holds the binary blob plus metadata. The configurations subnodes are pointers. Without this, the `.its` syntax looks magical.
- §23.5 FIT signing: "**Signed boot.** The FIT can have an attached signature." Two sentences for the most security-critical feature in the chapter. Either expand to a paragraph (with forward reference to Ch 62) or remove from this chapter and leave it for Ch 62 only.
- §23.3 `bootm` vs `bootz` vs `booti`: the table says "U-Boot image (legacy uImage)" for `bootm`. But `bootm` also handles **FIT images**, which is what §23.5 builds. Reconcile — `bootm` is actually the universal entry point and the table is misleading.

---

## Ch23A — Multi-variant FIT

### AI wording / sledgehammer / buzzwords

- > "real products ship in revisions. Rev A has a 4.3" display; Rev B has a 7" display and a fan controller; Rev C drops the display and adds a Wi-Fi module. Shipping three separate images means three separate OTA targets and three release-engineering pipelines. **Shipping one image** means one OTA stream and one set of QA artifacts."
  - Rewrite: "Real products ship in revisions. Rev A has a 4.3-inch display, Rev B has a 7-inch display and a fan, Rev C drops the display and adds Wi-Fi. Three separate images means three OTA targets and three release pipelines. One image means one OTA stream and one QA artifact set."
- > "The kernel is included *once*, regardless of how many configurations reference it. Same for the rootfs. FIT does not duplicate."
  - Rewrite: "The kernel is stored once, no matter how many configurations reference it. Same for the rootfs. FIT does not duplicate payloads."
- > "When you receive a unit, you don't ask 'which rev is this?' The unit answers itself."
  - Rewrite: "When you receive a unit, you don't have to ask which rev it is. The unit identifies itself at boot."
- > "For a dev board with ~5 variants, separate DTBs are simpler. For a product line with ~50 variants, overlays scale better."
  - Rewrite: keep — direct, good engineer voice.

### ESL readability

- > "Two pins encode four states. The strapping resistors are set during PCB assembly; software reads them on every boot."
  - Rewrite: "Two pins encode four states. PCB assembly populates the strap resistors. Software reads them on every boot."
- > "One-time programmable; uncopiable; tamper-resistant. Used in production for the security-conscious. Expensive to undo if you make a mistake — the fuse cannot be cleared."
  - Rewrite: "One-time programmable, hard to copy, tamper-resistant. Used in security-critical production. If you burn the wrong value, you cannot clear it."
  - Note: triplet rhythm + em-dash, both in two short lines.
- > "Advantages over strap pins: 256 possible IDs, easy to reprogram in the field, no extra pads needed if you already have an I²C EEPROM for serial number / MAC address."
  - Rewrite: "Advantages over strap pins: 256 possible IDs, you can reprogram in the field, and no extra pads if you already have an EEPROM for serial number or MAC address."

### Needs more explanation

- §23A.5 DT overlays: `fdt apply` is shown but the mechanics are hand-waved. For someone who has never seen DT overlays, explain: an overlay is a DTB with a special `__fixups__` and `__local_fixups__` table (created by `dtc -@`) that tells the merger how to resolve label references in the base. Without this, "U-Boot's `fdt apply` merges the overlay into the base" sounds like magic.
- §23A.3 `bootm` flow: step 6 "Branch to the kernel `entry=` with the DTB address in `r2`" — this is the ARM Linux boot ABI mentioned again. Define it once (best place: here or Ch23 §23.2) and back-reference everywhere else.
- §23A.4 Pattern C eFuse: `fuse_read(BOARD_ID_BANK, BOARD_ID_WORD, &board_id)` — the OCOTP layout (banks, words) is mentioned but not explained. For ESL readers, a one-line "OCOTP is organized in banks of 8 words; pick an unused bank for board ID" would prevent confusion.

---

## Ch24 — Workflows TFTP / NFS / USB-OTG

### AI wording / sledgehammer / buzzwords

- > "an embedded engineer's productivity is bounded by how fast they iterate. Reflash-via-SD takes 1–2 minutes per change. TFTP-and-NFS takes 5–10 seconds. Multiplied across hundreds of kernel builds in Parts IV–VI, that's days of saved time. The Linux-host CLI workflow in this chapter is the one this book uses for all subsequent development."
  - Rewrite: "Iteration speed bounds productivity. SD-reflash takes 1–2 minutes per cycle. TFTP+NFS takes 5–10 seconds. Across hundreds of kernel builds in Parts IV–VI, that adds up to days. The workflow in this chapter is what the rest of the book assumes."
- > "the **single mental loop** — edit a file on the host; the target sees it instantly. That loop is what makes embedded Linux feel like embedded development rather than embedded compilation."
  - Rewrite: "the single mental loop: edit a file on the host, the target sees it immediately. That loop is what turns embedded Linux from a build-and-flash cycle into real development."
- > "**You can't iterate this fast any other way on this hardware.**"
  - Rewrite: "No other workflow on this hardware iterates this fast."
- > "Now the boot sequence is: power on → ROM → SPL → U-Boot → TFTP → kernel. No SD-card writes, ever."
  - Rewrite (good — keep as is; clear and engineer-voice).
- > "Faster than `dd`-then-eject-then-insert-then-boot."
  - Rewrite: "Faster than `dd`, eject, insert, boot."
- > "That's the goal."
  - Rewrite: drop the sentence.

### ESL readability

- > "A common boot-time hang is 'NFS mount timed out.' Almost always: server-side firewall blocking, wrong export options, or wrong kernel cmdline path."
  - Rewrite: "A common boot-time hang is 'NFS mount timed out.' Almost always the cause is a server-side firewall, wrong export options, or a wrong kernel cmdline path."
- > "Each colon-separated field is positional."
  - Rewrite: "Each field is positional (separated by colons)."
- > "`uuu` enumerates the i.MX6ULL Boot ROM, pushes SPL, runs it, the SPL hands off to U-Boot in RAM, U-Boot enables Fastboot, `uuu` then drives `fastboot` commands to flash the persistent storage."
  - Rewrite: "`uuu` enumerates the i.MX6ULL Boot ROM and pushes SPL. SPL runs and hands off to U-Boot in RAM. U-Boot enables Fastboot. `uuu` then issues `fastboot` commands to flash persistent storage."
  - Note: original is six clauses glued with commas. Hard to parse for ESL.
- > "Modules loaded by `modprobe` come from `/lib/modules/...` on the rootfs, which *is* NFS — that works."
  - Rewrite: "`modprobe` loads modules from `/lib/modules/...` on the rootfs, which is NFS. That works fine."

### Needs more explanation

- §24.2 TFTP: protocol is used but never described. One paragraph: TFTP is UDP-based, very simple, block-by-block ACK, port 69; that's why it's slow but reliable for bootloader use. For an MCU engineer, the why-TFTP question is real.
- §24.3 `nfsroot` and `ip=` cmdline format: the `ip=client::gateway:netmask::interface:autoconf` token has 7 fields and the explanation is one line. Show all fields explicitly with a labeled example. The current text only labels four.
- §24.4 `uuu` recipe DSL: `SDP:`, `SDPU:`, `FB:` prefixes appear with no explanation. For a first reader, these protocol names are opaque. Add: `SDP` = Serial Download Protocol (NXP's ROM-mode protocol), `SDPU` = SDP-over-USB-after-U-Boot-jump, `FB` = Fastboot (Android-derived). One sentence each.
- §24.4 "U-Boot enables Fastboot" — Fastboot is mentioned without introduction. For an MCU engineer who doesn't come from Android, define: Fastboot is a USB protocol for sending images and commands to a bootloader. It originated with Android but U-Boot supports it. Then `uuu` makes more sense.
