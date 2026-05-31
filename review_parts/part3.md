# Part III — U-Boot: Review

## Cross-cutting observations

- **No "U-Boot vs. your bare-metal blob" framing chapter or opening section.** The MCU reader's biggest gap going into Part III is conceptual: *they have never used an interactive bootloader.* On MCUs, the engineer flashes a single blob and the chip runs it. U-Boot is a separate program that loads *another* program and provides a CLI in between. Ch19's "Why" sentence ("From here on the question is no longer 'can we?' but 'what does the professional version of this work look like?'") does some of this work, but it does not explicitly say: "U-Boot is a program. Linux is a separate program. U-Boot's only job is to find Linux, prepare RAM/peripherals, and call it. Then U-Boot is gone." A two-paragraph framing at the top of Ch19 (or as a brand-new §III.0 page) before §19.1 would save the reader an hour of confusion when they first see `bootcmd`, `bootargs`, and `bootm` and wonder why a bootloader has a *shell*.
- **The environment as "persistent NVRAM your CLI can edit" is never explicitly bridged.** MCU engineers may know "EEPROM-backed config blob" but not "shell variables that persist." `setenv` / `saveenv` / `printenv` show up across Ch19, Ch21, Ch23, Ch24 with the assumption that the reader already knows what an env var is in a bootloader. Add to Ch19 §19.6 (`printenv`) or as a fresh sub-section: "Concept break: U-Boot's environment is a key/value store stored in a known sector of the boot medium. Think of it as one I²C-EEPROM-backed `struct config` whose fields you can edit from a shell. `setenv` modifies the in-RAM copy; `saveenv` writes it to flash. Reboot loses anything you didn't `saveenv`."
- **`source.denx.de` vs `git.denx.de` slash naming.** Several places use `https://source.denx.de/u-boot/u-boot.git`; the canonical project URL has shifted over the years and the directive page now is `https://source.denx.de/u-boot/u-boot.git` (correct as written in Ch19) but the parenthetical "(a.k.a. `git.denx.de`)" is no longer accurate as a current alias. Either drop or rephrase as "(historically `git.denx.de`)".
- **No ASCII figure of "where is what at each boot stage."** Part III would benefit enormously from one canonical "stage chart" that the reader can flip back to from any chapter: at stage 0 (ROM) PC is in iROM, what is in OCRAM; at stage 1 (SPL) what code is at what address, what stack is where; at stage 2 (U-Boot pre-relocation); stage 3 (U-Boot post-relocation, kernel about to be loaded); stage 4 (kernel running). Ch20 §20.4 has a partial flow chart but it is verb-oriented, not address-oriented. Add an address-oriented diagram once, reuse across Ch20, Ch21, Ch24.
- **OCRAM/SPL size budget mismatch with the reference manual.** Ch20 §20.3 says "the Boot ROM's effective load window for SPL is **~100 KB** within OCRAM." The IMX6ULL reference manual (page ~260 in our extract, the ROM/RAM memory-map figure) shows OCRAM = 128 KB total, with the **free area = 68 KB** (0x00907000-0x00917FF0) — the rest is reserved for ROM stack, MMU table, log buffer, RAM exception vectors. NXP's `CONFIG_SPL_MAX_SIZE` on `mx6ull_14x14_evk` is typically set near 64 KB for exactly this reason. Either cite the 68 KB free figure directly, or rephrase as "~64 KB practical SPL budget within 128 KB OCRAM (the ROM reserves the rest for its own MMU table / stack / log buffer)". The current "~100 KB" overstates the budget by ~50 %.
- **Mainline EVK board-name string check.** Ch19 §19.5 boot log shows `Model: Freescale i.MX6 UltraLiteLite 14x14 EVK Board`. That double-"Lite" looks like a typo and a reader would assume the book made an error. In mainline U-Boot the actual board file at `board/freescale/mx6ull_14x14_evk/mx6ull_14x14_evk.c` historically uses "i.MX6 UltraLite/ULL" or "i.MX6ULL 14x14 EVK Board". If the "UltraLiteLite" string is reproduced verbatim from a real boot log, leave it but add a brief footnote ("yes, this odd double-Lite is in NXP's source verbatim — `UltraLite` + `Lite` for ULL"). If not, fix to `i.MX6 ULL 14x14 EVK Board`. Either way, the reader needs the cue.
- **Chapter cross-references use chapter numbers in a way that may be brittle.** Examples: Ch19 "Chapter 14 §14.6", Ch20 "Chapter 11 §20.1's Pattern 1", Ch21 "Chapter 14's tRP/tRAS/tRC/tWR setting", Ch22 "Chapter 14 §14.13", Ch23 "Chapter 28", Ch23A "Chapter 62", Ch24 "Chapter 3 §3.6/3.7/3.8/3.10", "Chapter 55E". This is fine if the TOC is locked, but section numbers are easy to drift. Consider a final-pass automated cross-ref check before publication.
- **The two-IMX-fork story (mainline vs. NXP `imx_v2016.03_4.1.15_2.0.0_ga`) is mentioned only in Ch19 §19.1 and is not picked up again.** A reader following a *Chinese-language guide or a vendor BSP* (e.g., Point Atom uses the 2016 NXP fork) will get confused when source paths diverge — e.g., NXP fork has `arch/arm/cpu/armv7/mx6/...` legacy layout while mainline has `arch/arm/mach-imx/mx6/`. Add a short callout near §19.1 or as a sidebar: "If a tutorial or AN you're following references a file path that doesn't exist in your tree, you're probably reading NXP-fork docs. Mainline's `mach-imx` layout was introduced in 2016+."
- **"Bare-metal" → "U-Boot mapping" cross-reference table missing.** Each chapter references "Chapter X" frequently, but a single table at the start of Part III ("Chapter 10's startup.S = U-Boot's `arch/arm/cpu/armv7/start.S`; Chapter 14's `ddr_init` = `arch/arm/mach-imx/mx6/ddr.c`; Chapter 12's UART init = `drivers/serial/serial_mxc.c`; Chapter 11's `mkimx.py` = `tools/mkimage` + `imximage` plugin") would crystallize the "U-Boot is our Part II, productized" message that the book keeps making prose-only.

## Ch19 — U-Boot from source

### Readability
- §19.3 sentence: "The first build takes 1–2 minutes on a modern host. A few interesting moments scroll past:" — "A few interesting moments scroll past" is awkward and slightly poetic. Suggest: "Watch for these lines as the build scrolls past:". The same goes for §19.5 "Pause. Read the boot log a third time. Notice:" — fine for English speakers but the imperative repetition feels off. Suggest: "Re-read the boot log a third time, paying attention to each of these lines:".
- §19.1 last sentence reads: "The boards are close enough that the EVK config boots on the MINI with only minor DT changes for IOMUX and DDR timings." DDR timing changes are *not* minor on hardware that differs (different DRAM chip, different trace lengths, different number of chips). The whole point of Ch22 §22.6 is "this part you cannot fake." Either soften to "...with EVK config as a starting point — DDR timings need fresh stress-tool values for the MINI; IOMUX needs per-pad updates," or move the qualifier here.
- §19.3 table: `MLO` row says "Symbolic link / copy of the SPL image used by some SoCs (TI / OMAP heritage)". On i.MX6ULL this is irrelevant. Either remove the row, or add: "(not used on i.MX6ULL — ignore)" to spare the reader looking it up.

### MCU-engineer friendliness
- §19.2 directory layout: the comment `cmd/  # one .c per U-Boot command` is the first hint that U-Boot *has* commands. The reader doesn't know yet what "U-Boot commands" means. Add a parenthetical: "(`cmd/md.c` is the `md` 'memory display' command you'll type at the `=>` prompt in §19.6.)" — pre-bridges the discovery in §19.6.
- §19.5 — first sight of the `=>` prompt. This is *the* moment the MCU reader meets an interactive bootloader. Add a paragraph immediately after the boot-log block: "If you've only ever worked with MCUs, this is the new concept of Part III. The chip is *not* yet running Linux. It is running a small program (U-Boot) that gives you a shell, a memory editor, drivers for SD/USB/Ethernet, and the ability to load and start another program (Linux). For the next four chapters we'll live at this prompt."
- §19.4 SD-card flash table: the reader who hand-flashed in Part II knows the IVT offset. But they don't know why SPL goes to LBA 2 (1 KiB offset) *and* U-Boot goes to LBA 138 (69 KiB offset). One sentence: "The 1 KiB offset is what the ROM expects (Ch 7). The 69 KiB offset is where SPL is *configured* to look for its second-stage image — a U-Boot Kconfig choice (`CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR`), not a hardware constraint." This makes the magic numbers stop being magic.
- §19.6 `printenv`: the sample output has `bootcmd=run findfdt; mmc dev ${mmcdev}; mmc rescan; ...` — that `...` is doing a lot of work. The MCU reader has no analog for a shell-script-stored-in-a-variable. Add a one-line annotation: "`${mmcdev}` is variable substitution like Bash. `run findfdt` evaluates the variable `findfdt` as a sequence of commands. Chapter 23 covers this DSL in detail."
- §19.6 `bdinfo`: `relocaddr = 0x9ff37000` and "U-Boot started executing somewhere lower in DRAM, then *relocated itself* to high DRAM" — relocation is a deep concept and Ch21 covers it, but the *first* mention here for an MCU reader who has only ever written XIP-from-flash MCU code is jarring. One extra sentence: "MCU engineers: think of this as the equivalent of `memcpy(0x9ff37000, 0x80800000, image_size); jmp 0x9ff37000;` — but with the linker's pointer fix-ups also adjusted by the offset. Trust this for now; Ch21 explains."

### Missing examples / figures
- After §19.5 add an ASCII diagram showing: ROM → reads SPL from SD LBA 2 → SPL in OCRAM @ 0x907400 → SPL DDR init → SPL reads u-boot.imx from SD LBA 138 → u-boot.bin in DRAM @ 0x87800000 → SPL jumps to it → U-Boot relocates to high DRAM (~0x9ff37000) → `=>` prompt. This is the canonical "Part III mental model" diagram and the reader will refer back to it from Ch20 and Ch21.
- §19.6 `bdinfo`: include an annotated diagram of the DRAM map at the moment of `=>`: low DRAM unused (0x80000000-?), reloc target (0x9ff37000) U-Boot code, stack growing down from somewhere above, env load buffer somewhere, fdt blob @ 0x9ed3d2c0. The numbers are all in the bdinfo output — link them visually.

### Technical errors
- §19.3 table: `MLO` description is TI/OMAP. On i.MX6ULL `MLO` is unused and the file may not even exist for the EVK defconfig. Drop or qualify.
- §19.4 says `bs=1k seek=1` writes at LBA 2 — correct, since LBA 2 = byte offset 1024. But the offset table above it says `1 (= LBA 2)` and labels the column "Offset (KiB)" — a reader could read "offset 1 KiB = LBA 2" as a contradiction with "LBA 2 = byte 1024 = 1 KiB". Clarify or just say "byte offset 0x400".
- §19.4 the offset `8192` "Reserved for partitions" — actually `8192 KiB = 8 MiB` and the EVK convention is partitions start at `8 MiB` (= LBA 16384, sector 512). Spell out "8192 KiB = 8 MiB" so the reader doesn't read it as sectors.
- §19.5 boot log: "CPU: i.MX6ULL rev1.1 at 396 MHz" — the EVK config does run at 396 MHz initially (from the ROM's default PLL1 setting, see RM Table 8-4). But later it ramps to 528 or 696 MHz under Linux. State this once so the reader doesn't conclude "U-Boot caps the EVK at 396 MHz."
- §19.5 "DRAM: 512 MiB — SPL's DDR setup worked. The same 100-line MMDC dance as our Chapter 14". The mainline `arch/arm/mach-imx/mx6/ddr.c` is closer to 1500 lines, not 100, and even the board-specific spl.c is several hundred. The "100-line" claim under-sells the production code by an order of magnitude. The chapter already does this better in §19.7 ("~600 lines"). Make §19.5 say "the productized MMDC bring-up you wrote 100 lines of in Ch 14; in U-Boot it's a 600-line table-driven engine."

### Knowledge prerequisites missing
- §19.3 references `make distclean` for the first time in Pitfalls but uses `make mx6ull_14x14_evk_defconfig` without explaining that it generates a `.config` file. An MCU engineer using Make may not know the Linux-kernel-Kconfig convention. One sentence: "`make foo_defconfig` reads `configs/foo_defconfig` and writes the resulting `.config` (a Kconfig artefact) to the build root. `make` then reads `.config` and the per-CONFIG `Makefile`s to decide what to build."
- §19.6 mentions `bootz` only via the prose "bootcmd ... tries to find a kernel and chain-boot Linux." But the actual command `bootz` is introduced cleanly only in Ch23. A forward-reference link would help: "(`bootz` is the kernel-launch command; we cover it in Ch 23.)"
- §19.7 — `arch/arm/include/asm/arch-mx6/...` paths and the macro `MX6_PAD_*` are referenced but the cross-tree DT-vs-source-header file structure is not yet introduced. Forward-reference Ch22 explicitly.

### Other
- §19.10 "Going deeper" lists `https://docs.u-boot.org/` — the actual URL is `https://docs.u-boot.org/en/latest/` for the modern Sphinx-built docs site. Minor but worth correcting.
- The "DENX's Bootloader_with_U-Boot article series (free)" reference is vague; the canonical thing is "U-Boot manual" on docs.u-boot.org. Consider replacing.

## Ch20 — U-Boot SPL: the missing link

### Readability
- §20.1 "Pattern 3 ... Has been done. Painful." — fragments. Either expand ("This pattern was used historically — strip features until the binary fits in 100 KB OCRAM. It works but the resulting U-Boot is too feature-thin for any real product."), or accept as deliberate. Currently feels half-finished.
- §20.8 has a confused, self-correcting passage: `"Hmm. Let me re-check. The entry for an SPL is *inside OCRAM*, not DRAM..."` and later `"...wait no, that's not right either, because SPL is what initializes DDR. The answer is subtle and worth pinning..."`. **This reads as if the author was reasoning live in the chapter and didn't clean up.** For a book aimed at a non-native English MCU engineer, this is highly confusing — the reader can't tell which statement is correct. Rewrite §20.8 as a single clean explanation: (1) SPL's `.imx` may or may not have a DCD; (2) if present, the DCD does pad/clock setup needed *before SPL's C code runs* — but **not** DDR init; (3) DDR init is SPL's C code's job; (4) compare to the EVK's `.cfg` file. Remove all the "wait" / "hmm" / "actually" hedging.
- §20.9 "Full U-Boot's `_main` then proceeds with *its* `board_init_f` → relocation → `board_init_r` → main loop." — Bare-minimum sentence but missing a connective. "We trace this in Chapter 21." → consider expanding to: "The full-U-Boot init flow runs `board_init_f`, relocates to high DRAM, then `board_init_r`, then the main loop. Chapter 21 walks each step."

### MCU-engineer friendliness
- §20.1 "Three possible solutions" is great for an engineer who already knows the constraint. But it dives into Pattern 1/2/3 before reminding the reader *why* the constraint exists. One sentence at the very top: "The i.MX6ULL Boot ROM, when loading from SD/eMMC, reads at most 4 KiB initially (see Ch 7's IVT-Initial-Load-Region) and ultimately loads what fits into OCRAM (~68 KB free). Full U-Boot doesn't fit. SPL exists to bridge that gap."
- §20.2 "What SPL is responsible for" — the seven-step list is excellent, but the closing paragraph ("SPL is the smallest program that can do exactly the seven things above on this hardware") should be picked up *visually* as a hand-off contract diagram: SPL's exit conditions = the world full U-Boot expects to inherit. Otherwise the seven items feel like a list and not a contract.
- §20.6 "The 'f' stands for 'flash' (historical — back when U-Boot ran first from flash...)". MCU engineer reads "U-Boot ran first from flash" and thinks "wait, you said it doesn't fit in OCRAM, so how did it run from flash directly?" — the answer is that this is *legacy CPU-NOR-flash XIP era*, distinct from our SD-boot-into-DRAM flow. Add one clarifying sentence: "Historically (i.MX1/2/3 era), the bootloader was small enough to execute in place (XIP) from parallel NOR flash. The `_f` / `_r` distinction is a vestige of that."

### Missing examples / figures
- Add to §20.3 a real `size spl/u-boot-spl` output annotated with what fits where in OCRAM. Currently the budget is abstract; an image of "39204 bytes text + 1872 data + 8112 bss = 49188 bytes, free OCRAM after SPL = 68KB - 49KB = ~19KB headroom" would crystallize the constraint.
- §20.4 has a great ASCII flow but no *address* annotations. Add: "SPL @ 0x00907400, stack @ ~0x0091FE00, gd_t @ ~0x0091FE08, U-Boot loaded to DRAM @ 0x87800000" — same skeleton as the Ch21 §21.2 SP-arithmetic walk, but for SPL.
- §20.7 — when `_main` is shown, it includes `ldr sp, =(CONFIG_SYS_INIT_SP_ADDR)` but does not show what that value is *in SPL*. For SPL on i.MX6ULL EVK this is also near the top of OCRAM. Add a one-line annotation.

### Technical errors
- §20.3 "the Boot ROM's effective load window for SPL is ~100 KB within OCRAM" — see cross-cutting note; per RM the free area is 68 KB. Fix.
- §20.4 ASCII diagram says "loads SPL (~40 KB) into OCRAM @ 0x00907400". 0x907400 is correct for typical EVK; pinpoint it correctly. But the diagram also implies the ROM does the load *after* IVT parsing — it does, and the load address is what the IVT `self` field declares (see Ch 11 §11.x), not a hard-coded ROM constant. State this.
- §20.4 — `arch/arm/cpu/armv7/start.S` is shared between SPL and full U-Boot; `lowlevel_init.S` is **not** at `arch/arm/cpu/armv7/lowlevel_init.S` in modern mainline (varies by SoC; on i.MX it's in `arch/arm/mach-imx/`). Double-check paths.
- §20.5 `cpu_init_crit` description "very-early board-critical init (memory remapping, system control register tweaks)" — on ARMv7 `cpu_init_crit` mostly invalidates caches and TLBs and sets up the SCTLR; it doesn't do "memory remapping" in any general sense. Tighten.
- §20.6 The pseudo-`board_init_f` is shown as 5 explicit calls (`arch_cpu_init`, `timer_init`, `preloader_console_init`, `spl_dram_init`, `memset`...). In reality SPL's `board_init_f` may directly include this sequence on i.MX, but the *generic* SPL framework uses `spl_board_init_f` or the init-sequence pattern from `common/spl/spl.c`. Make clear this is the i.MX SPL flavor, not the generic SPL framework's flow.
- §20.7 mentions `spl_load_image(BOOT_DEVICE_MMC1, &spl_image)` — modern SPL has the framework call `spl_load_image_method` and choose the loader from a list. The simplified pseudocode is fine but could note: "Reality is `spl_load_image` runs a list of registered `spl_image_loader` methods, this is a simplification."
- §20.7 "spl_mmc_load_image → reads `u-boot.imx` from SD card LBA 138 (= seek=69 in 1 KB blocks)". 69 KiB / 0.5 KiB-per-LBA = 138 LBAs from start — correct, but worth stating once: 1 LBA = 512 bytes, so 69 KiB = 138 LBAs.

### Knowledge prerequisites missing
- §20.4 introduces `board_init_f` / `board_init_r` for the first time without defining the `f`/`r` convention. §20.6 then defines it. Reorder so the definition comes before first use, or define at first use.
- §20.7 introduces `gd_t` (struct global_data) without explanation. Define it once with: "`gd_t` is U-Boot's per-CPU 'global data' — a single struct holding pre-relocation state, DRAM detection results, console pointers, env state, etc. It's allocated on the stack early and pointed to by a fixed register (r9 on ARM) so any code can reach it without passing pointers around."
- §20.8 references `mx6ull_14x14_evk.cfg` (a `.cfg` file). MCU readers won't know that NXP's U-Boot uses `.cfg` files to feed `mkimage` for IVT/DCD generation. Brief explanation: "the `.cfg` file is a small text file specifying IVT entry, DCD entries, etc. `mkimage`'s `imximage` plugin reads it. The same logic as your Ch 11 `mkimx.py`'s args."

### Other
- §20.11 Pitfall "Out-of-bounds OCRAM access. SPL has ~100 KB of OCRAM" — same 100KB error.
- §20.11 Pitfall "Calling SPL functions from full U-Boot. They don't exist there — different binary, different memory map." — this is a very real trap for a beginner. Add an example: "If you write `spl_load_image()` in your full-U-Boot code, the build fails because that symbol is gated by `#ifdef CONFIG_SPL_BUILD`."

## Ch21 — U-Boot internals

### Readability
- §21.1 — the 9-step list is excellent. But each step lacks a one-line "what to grep for". Add: "1. `_start` (file: `arch/arm/cpu/armv7/start.S`, ~50 lines)". Most steps already have file refs; complete them all consistently and add LOC estimates so the reader knows what they're committing to.
- §21.1a — "the linker script `u-boot.lds` (generated at the top of the source tree only **after** a successful build — pre-build there's only the unprocessed `arch/arm/cpu/u-boot.lds`)" — the parenthetical is too dense. Split: "The linker script `u-boot.lds` is generated during build from the per-arch template `arch/arm/cpu/u-boot.lds`. Until you've built once, only the template exists at the source root."
- §21.3 lists the `init_sequence_f` array. The closing line "After `board_init_f` returns, control falls back into `_main`" is followed by ASM. The transition between "here's the C list" and "now here's the ASM after the return" needs a connective sentence: "Control returns to `_main` after the C list executes. The ASM that runs next is the relocation handshake — every line below is critical."
- §21.4 — "This is the most surprising design choice in U-Boot for a newcomer." Good hook, but the explanation jumps between abstract ("Why relocate at all") and concrete ("How relocation works mechanically") quickly. Add a clearer transition: "With *why* clear, here's *how* in three steps."
- §21.4 "The post-copy `bx lr` is the **single most important instruction** in this entire chapter." Excellent line — keep it. Consider boxing it as a callout.

### MCU-engineer friendliness
- §21.2 SP-arithmetic walk is one of the strongest passages in the part. **Keep it as is**, and consider doing similar walks for one or two other "what address holds what" moments (e.g., `relocaddr` calculation, env-load-buffer placement).
- §21.4 — when introducing position-independent code, an MCU engineer who hasn't dealt with PIC will not have the mental model. Add one paragraph: "Position-independent code is compiled so all internal jumps and data references are *relative* to the program counter, not absolute. The cost is a few extra instructions per non-local reference. The benefit is that the same binary works at any load address. U-Boot uses `-fpic` to get this, and `.rel.dyn` to track which absolute references remain (string literals, function pointers in tables, etc.) so relocation can patch them."
- §21.5 — the `cmd_tbl_t` linker-section trick. MCU readers know `__attribute__((section))` for ISR vector tables in MCU startup code. Make the analogy explicit: "If you've ever placed an ISR vector or initcall via `__attribute__((section(".isr_vector")))` and let the linker assemble all entries into a contiguous range, this is the same trick. U-Boot's `cmd/Makefile` doesn't need a central registry; each `.c` file self-registers via the section attribute."
- §21.6 — the env subsystem. The "Where it lives" passage is good. The MCU equivalent: "If you've ever stored config in a chip-internal EEPROM or a reserved flash sector with a CRC and a magic word, U-Boot's env is the same idea, but with a userspace API (`fw_setenv`) and a shell."
- §21.7 (Driver Model) — "Conceptually identical to Linux's `struct device` + `struct driver`, but much smaller." Good. Now add: "If you've used HAL APIs on STM32 (HAL_UART_Init etc.), DM is the same idea but with a runtime registry of (device, driver) pairs instead of a static `huart1` global. The DT tells DM what devices exist; DM walks the device list and binds each to a matching driver."

### Missing examples / figures
- §21.4 — add a 4-quadrant before/after memory layout diagram for relocation: LEFT = "U-Boot at load addr 0x80800000 in low DRAM, stack in OCRAM" → RIGHT = "U-Boot at 0x9ff37000 in high DRAM, stack in high DRAM, low DRAM free for kernel/DTB". Even a 6-line ASCII box would lock the concept.
- §21.5 — add the actual disassembly of `find_cmd` (10 lines) so the reader sees the section-walk pattern in code. Currently we describe it but never show it.
- §21.6 — show a real `fw_printenv` invocation from Linux user-space with annotated output. Currently the Linux-side env access is mentioned in one paragraph but never demonstrated.
- §21.7 — add a `dm tree` output sample with a 5-line tree. Lab item 7 asks the reader to run `dm tree` but doesn't preview what they'll see.
- §21.8 boot-log walk: this is the best section in the chapter. Consider adding the *file path* for each subsystem-init call so the reader can grep directly: `MMC: ...` ← `drivers/mmc/mmc.c:mmc_init` (etc.).

### Technical errors
- §21.1a table: `relocaddr = 0x9ff37000` in Ch19's `bdinfo` matches "near the top of 512 MiB DRAM" — 0x80000000 + 512 MiB = 0xa0000000, so 0x9ff37000 is 0xc9000 (812 KiB) below the top. Sanity-check that the linker script's `__bss_end = 0x878A8E74` is *pre-relocation*, not the final runtime location — these are the linker's view, not the post-reloc view. The text says "Sample value" and "for our ... build" — make explicit that these are the *linked* addresses, which the relocation engine then offsets by `reloc_off`.
- §21.2 ASCII memory map: shows `0x0091FFFF` as "top of OCRAM (128 KB)". But OCRAM ends at `0x0091FFFF` only if base is `0x00900000` and size is `0x20000` = 128 KiB. The arithmetic is fine, but `0x00900000 + 0x20000 - 1 = 0x0091FFFF`, OK. Then the ASM says SP = 0x0091FF00, leaving 256 bytes above SP — confirm this aligns with `GENERATED_GBL_DATA_SIZE = 256`. The text says GD_SIZE = 248 but reserves 256. Clarify: "256 = round-up of 248 to 16-byte alignment".
- §21.3 — `setup_spl_handoff` exists in the init sequence list. This is only relevant for boards using the SPL→U-Boot handoff data passing (added in 2019). Not all i.MX boards use it. Either qualify or note "may or may not appear depending on CONFIG_SPL_HANDOFF".
- §21.4 — `relocate_code` snippet shows `ldmia r1!, {r10-r11}` / `stmia r0!, {r10-r11}`. That's a 2-register copy loop (8 bytes per iteration). Modern mainline uses `ldmia r1!, {r10-r11}` exactly, so this is correct. But the relocation fix-up loop uses different register conventions; double-check `r0/r1/r2/r3/r4/r6` assignments against the current `arch/arm/lib/relocate.S` rather than older versions.
- §21.4 "U-Boot was built linked for an address of approximately `0x80800000`" — actually the EVK's `CONFIG_SYS_TEXT_BASE = 0x87800000` (per Ch22 §22.4's defconfig). The text in Ch21 §21.1a also uses `0x87800000`. Fix §21.4 to be consistent.
- §21.6 "stored on the boot medium — for our SD-card workflow, in a fixed-offset sector of the SD card (`CONFIG_ENV_OFFSET`, often 0x100000 = 1 MiB)". On the mainline `mx6ull_14x14_evk_defconfig` the env offset is actually a different value (often `0xC0000` = 768 KiB or `0x100000` depending on version). Verify with `grep CONFIG_ENV_OFFSET configs/mx6ull_14x14_evk_defconfig`.

### Knowledge prerequisites missing
- §21.3 references `init_fnc_t` typedef without defining it. One line: "`typedef int (*init_fnc_t)(void)` — a function returning 0 on success, non-zero on fatal init failure."
- §21.5 references `cmd_tbl_t` but the actual modern name in mainline is `struct cmd_tbl`. Either explain the `_t` suffix is historical / shorthand, or update to current naming.
- §21.7 — `dm_serial_ops`, `udevice`, `uclass_get`, `device_probe` are all introduced in code but never defined as types. Add a quick "DM types you'll see" box: `struct udevice` (instance), `struct driver` (code), `struct uclass` (category), `struct udevice_id` (DT compat match table).
- §21.7 — `compatible = "fsl,my-uart"` syntax. The reader hasn't yet seen DT compatibility strings (Part IV introduces DT). Forward-reference: "DT compatible strings come up in detail in Ch 27; for now just know that a string in DT lets DM match a device to a driver."

### Other
- §21.5 — the `U_BOOT_CMD` macro expansion is shown but the field meanings are not all explained: `md, 3, 1, do_mem_md, ...` — what does the `3` mean? (max argc). What does the `1` mean? (repeatable on Enter). Add a comment line.
- §21.9 Lab item 4: `arm-linux-gnueabihf-readelf -r u-boot | head -30` — fine. But add expected output: "you should see hundreds of R_ARM_RELATIVE entries, each one a pointer in U-Boot's image that gets fixed up at relocation."
- §21.10 Pitfall "Two `U_BOOT_CMD` macros with the same name. Last-defined wins, silently." — actually with the linker-section approach, *both* are present and the lookup order depends on link order. Could be "first wins" or "last wins" depending on linker behavior; either way it's surprising. Verify and reword.

## Ch22 — Porting U-Boot to a custom board

### Readability
- §22.1 "Three categories of port" — the third bullet ("**Real port** ... New defconfig + new DT + new DDR config + new board.c. The Point Atom MINI vs the NXP EVK is approximately this. Closer to variant but with DDR and pinmux changes.") is contradictory — first says "real port", then "closer to variant". Pick one description and stick with it.
- §22.7 — "The macros `MX6_PAD_UART1_TX_DATA__UART1_DCE_TX` etc. are generated from the i.MX6ULL IOMUX tables; they encode pad, mux mode, and SELECT_INPUT in one constant." Good. Then "See `arch/arm/include/asm/arch-mx6/mx6ul_pins.h`." — note the i.MX6ULL pin header is sometimes split between `mx6ul_pins.h` and `mx6ull_pins.h`; double-check which mainline uses in 2025.

### MCU-engineer friendliness
- §22.2 "the per-board content lives in:" — the layout is fine. Add a sentence noting which of these files exist on the MCU bare-metal side (none): "Compare to your Ch11 setup where you had a single `board.c` and a `Makefile`. In U-Boot, the same conceptual 'board' is split across six locations: build config (`defconfig`), source tree (`include/configs/`), board folder (with Kconfig + sources), DT, and a per-arch DT-Makefile entry. The split is mostly to play well with mainline's build system."
- §22.3 — `git mv mx6ull_14x14_evk.c mx6ull_pa_mini.c` while files are in a *copied* (not added) directory. `git mv` on uncommitted files is `mv + git add` effectively, but the reader may be confused. Add: "These files are not in git yet; `git mv` here is equivalent to `mv + git add`. If you've staged the copy first, `git mv` preserves history."
- §22.6 "This is the part you cannot fake." — Excellent emphasis. Keep.
- §22.7 — for an MCU engineer who has done IOMUX register-by-register, the U-Boot abstraction `imx_iomux_v3_setup_multiple_pads(array, ARRAY_SIZE(array))` is just a thin wrapper around writing the same registers. Explicitly say so: "Compare to Ch11 §X where you wrote IOMUXC_SW_MUX_CTL_PAD_xxx directly. U-Boot's helper just writes the same registers from a table; the macros pre-compute the register address + value pair from the pad name."

### Missing examples / figures
- §22.3 — add a "before vs after" tree-diff after the `cp -r` and `git mv` commands so the reader can verify their working tree matches.
- §22.5 — the DT snippet is good but the reader has not yet seen DT in Part IV. Add a one-line note: "If `&fec1`, `pinctrl-0`, `phy-handle` syntax is unfamiliar, skim Ch 27 first. For now, treat it as 'JSON-ish hardware description'."
- §22.6 — the three structs are introduced but `mx6_dram_cfg(&ddr_sysinfo, &mx6_mmdc_calib, &mt41k128m16jt_125)` at the bottom uses *different argument order* than the EVK's `mx6_ddr3_cfg(&sysinfo, &mx6_mmcd_calib, &mt41k128m16jt_125)` in Ch19 §19.7. Make sure the function name is consistent (`mx6_dram_cfg` vs `mx6_ddr3_cfg`). In modern mainline it's `mx6_dram_cfg`.
- §22.9 Verify per-peripheral: add an explicit "if the MAC PHY doesn't link, here's what to check" sub-troubleshooting list. Currently only `ping` failure is noted at high level.

### Technical errors
- §22.3 — `board/myorg/mx6ull_pa_mini/` — mainline U-Boot does not have a `board/myorg/` directory; you're creating one. State explicitly: "We're inventing a new vendor namespace `myorg`. You'll also need to create `board/myorg/Kconfig`." That bit is in §22.3 but the chronology is "make Kconfig if it doesn't exist" — clarify it definitely doesn't exist if you're forking your own.
- §22.3 — `source "board/myorg/mx6ull_pa_mini/Kconfig"` from `board/myorg/Kconfig` — that's fine, but you also need `board/myorg/Kconfig` to be `source`d from `arch/arm/mach-imx/mx6/Kconfig` or similar. The chapter says "in `arch/arm/mach-imx/mx6/Kconfig`, add ..." — but doesn't explicitly say to *also* source the new myorg/Kconfig from there. Check this; the reader will hit a build error if missed.
- §22.4 — `CONFIG_SYS_PROMPT="=> "` → `"pa-mini=> "`. In modern U-Boot, `CONFIG_SYS_PROMPT` may be a Kconfig string rather than a `defconfig` literal; check whether `=` syntax works directly.
- §22.5 — `pwms = <&pwm0 0 50000>;` — i.MX6ULL has 4 PWM controllers numbered `pwm1`-`pwm4`, not `pwm0`. Check DT label.
- §22.6 — `static struct mx6_ddr3_cfg mt41k128m16jt_125 = { ... .density = 2, /* Gb */ ...}` for an MT41K128M16 part. MT41K128M16 is 2 Gb (128 M × 16). Correct. But `.trcd = 1310, .trcmin = 4875, .trasmin = 3500` — these are timing values in units that vary. The U-Boot ddr.h convention is typically in tenths of nanoseconds; double-check the units (1310 = 13.10 ns tRCD-on?). The reader will copy these blindly without that knowledge.
- §22.6 — `.refsel = 1, /* refresh = 32 kHz / 64 */` — `refsel = 1` selects 32 kHz / something; the comment "32 kHz / 64" needs verification against the MMDC register doc.
- §22.10 — `MAINTAINERS` block uses tabs (M:\t, S:\t, F:\t). Make sure the rendered code block preserves tabs vs spaces; this is checked by `scripts/get_maintainer.pl`.

### Knowledge prerequisites missing
- §22.5 — DT syntax (`compatible`, `#address-cells`, `phandle`, `&label`) is used throughout but DT is not introduced until Ch 27. Add a forward-reference paragraph at the top of §22.5: "We use device-tree syntax extensively below. If unfamiliar, this is a good moment to skim Ch 27 §27.1-§27.3, then come back. For now: `compatible` is what DM/Linux uses to match driver↔device; `&label` is a phandle reference."
- §22.6 — the *DDR Stress Tool* (Ch14 §14.13) is referenced but the reader may have skipped or forgotten Ch14's stress-tool section. Add a 2-line reminder: "NXP's `mx6ull_ddr_stress_tester` is a Windows app that drives the i.MX6ULL via UART/USB while you tweak MMDC parameters live. It produces the six calibration values you copy into `mx6_mmdc_calib`. See Ch14 §14.13 for setup."

### Other
- §22.10 — for non-mainline-submission cases, the MAINTAINERS file is optional. State this: "If you're shipping an internal-only port, skip this; the file is only required for upstream submission."
- §22.11 Lab item 5 "Pick something the EVK doesn't have — for instance, the BEEP GPIO toggling once on boot from `board_late_init`." Good idea, but `board_late_init` selection (`select BOARD_LATE_INIT`) is in §22.3's Kconfig and `BOARD_LATE_INIT` itself is not explained. One line: "`BOARD_LATE_INIT` Kconfig enables U-Boot to call your `board_late_init()` after the main DM init — it's the standard hook for board-specific env tweaks or hardware initialization that needs full DM up."

## Ch23 — bootcmd, bootargs, FIT images

### Readability
- §23.1 — first sentence "`bootcmd` is one environment variable whose value is treated as a sequence of U-Boot commands, evaluated automatically after `CONFIG_BOOTDELAY` seconds if no key is pressed." Excellent. Keep verbatim — clean and complete.
- §23.1 "EVK's default `bootcmd` (cleaned up)" — the multi-line bootcmd is wrapped for readability but the chapter doesn't say so. Add: "In the real env this is one logical line (`;`-separated). I've line-wrapped here for reading."
- §23.5 "Why FIT" bullet list is good. The "Signed boot" bullet says "U-Boot's HAB- or FIT-signature-verifying boot path is what `bootm` invokes for `-c` (signed configs)." But Ch23 has not introduced `-c` syntax. Either show the `bootm <addr>#<config>` and `bootm <addr> -c <config>` syntax once, or drop the `-c` reference.
- §23.7 — table column "Likely cause" works well. Consider adding a 4th column "Where to look in dmesg" for each row.

### MCU-engineer friendliness
- §23.1 — first encounter with the embedded DSL idea ("run findfdt; if; then ...; else ...; fi"). Add a "Concept break" callout: "U-Boot has its own mini-shell language: variables, command substitution (`${var}`), `;`-chained commands, `if`/`else`/`fi`, `run var`. It's a Bash subset, optimized for embedded boot logic. Most env entries are 'one liners' in this DSL."
- §23.2 — `bootargs` is *the* kernel command line. Excellent emphasis. Now add the MCU-engineer-friendly framing: "On an MCU you compile-time configure your firmware via macros. On Linux, the kernel is generic — the cmdline tells it at boot what role to play. Same kernel, different cmdline → different system. `bootargs` is the chief lever."
- §23.3 table — `bootm` / `bootz` / `booti`. For our board, `bootz`. Make this explicit: "**For everything in this book on i.MX6ULL, use `bootz`.** `bootm` and `booti` are documented here for completeness."
- §23.5 — FIT vs uImage vs zImage distinction. The MCU engineer's mental model is "a flash image is a flat binary blob". FIT — a structured container — is a new concept. Add: "FIT is to flash images what `zip` is to a folder. Multiple files, optional compression, optional signatures, a manifest. The 'manifest' (the FIT header) tells U-Boot where each file lives within the FIT."
- §23.5 — `data = /incbin/("./zImage");` syntax is FDT/DTS-specific. Reader who hasn't done DT-yet won't know this. Add: "`/incbin/` is a DTS directive that includes the *binary contents* of a file. The `mkimage -f` driver compiles the .its (DTS-like source) → .itb (binary FIT)."

### Missing examples / figures
- §23.1 — add a real `printenv bootcmd` from the EVK on first boot, *unwrapped*, then show the same with line-wrapping for the chapter. This gives the reader the "this is really one line" mental model.
- §23.2 — add an annotated diagram of: "Where does `bootargs` flow?" Showing: env → `bootcmd` runs → kernel image loaded → `bootm`/`bootz` writes `bootargs` into DT `chosen.bootargs` → kernel reads it during `start_kernel()`. The arrow from env to DT is the key insight.
- §23.5 — add a `mkimage -l boot.itb` output showing the FIT's structure (hashes, sizes, configurations). This is the "look inside the box" demo.
- §23.7 — add a real "boot hangs at 'Uncompressing Linux...'" UART log sample so the reader recognizes the pattern when they see it.

### Technical errors
- §23.3 table: "`bootm` ... 'U-Boot image' (legacy uImage)" — `bootm` also handles FIT images (so it's not just legacy uImage). Add: "`bootm` handles both legacy uImage *and* FIT (.itb) images — the format is auto-detected from the header."
- §23.3 — `bootz <addr> [<initrd>] [<fdt>]` — the addr is the *zImage* address. Some readers will pass the kernel.bin address instead. Clarify.
- §23.5 — the .its example uses `compression = "none";` for the kernel but `zImage` is *already self-decompressing* (the `z` in zImage). Note this: "`zImage` is self-extracting, so we tell FIT `compression=none` even though the kernel content is compressed. If you instead use `Image` (raw kernel) you'd specify `compression=gzip` and pre-gzip the file."
- §23.5 — `load = <0x82000000>; entry = <0x82000000>;` — for zImage these can be the same. But for an Image (arm64) they differ. Note the constraint.
- §23.5 — `arch = "arm";` for kernel/ramdisk — correct. But `os = "linux";` is missing on the `fdt-1` block. Inconsistent — `flat_dt` doesn't need `os`, but the absence may confuse the reader. Add a one-line comment.
- §23.5 — `mkimage -f boot.its boot.itb` doesn't always pick the right output type; modern usage is `mkimage -f boot.its -E boot.itb` for external data, or just `mkimage -f boot.its boot.itb` for embedded. Verify your default flow.
- §23.6 — `setenv bootargs ${bootargs} earlycon ignore_loglevel` — note this *appends* to the existing bootargs in place. Some U-Boots do not expand `${bootargs}` when reassigning to itself; double-check syntax.

### Knowledge prerequisites missing
- §23.2 — `KEY_HOME` and other Linux input codes from `linux,code = <KEY_HOME>` (introduced in Ch22 §22.5's DT) are *Linux kernel* constants, not visible to U-Boot. The DT processed by U-Boot is *passed* to the kernel for those nodes. Worth noting that U-Boot doesn't act on `gpio-keys` nodes — they're for Linux.
- §23.2 `console=ttymxc0,115200` — `ttymxc0` is the Linux tty name for `uart1` on i.MX6. The Linux-side mapping is `imx_uart_dev[0]` → `ttymxc0`. State this: "Linux names i.MX6 UARTs as `ttymxc0`, `ttymxc1`, ... corresponding to the i.MX UART instance number minus one (`UART1` → `ttymxc0`)."
- §23.2 `earlycon=ec_imx6q,0x02020000` — `ec_imx6q` is a Linux earlycon driver name. Reader has not seen earlycon yet. Brief note: "earlycon is Linux's very-earliest console driver, before the full UART subsystem comes up. The 'ec_imx6q' parser knows the i.MX6 UART register layout; the address is UART1's MMIO base (Ch12)."
- §23.4 `mkimage -A arm -O linux -T script -C none -d boot.cmd boot.scr` — `-T script` is a specific image type. Reader hasn't seen the `-T` taxonomy. List `kernel`, `ramdisk`, `script`, `flat_dt` as the common values.

### Other
- §23.8 Lab item 6: "Break it on purpose. Pass `root=/dev/nonsense` and watch the panic." — good. But the recovery instruction says "Then add `init=/bin/sh` and recover." — `init=/bin/sh` won't help if `/dev/nonsense` makes root un-mountable; the kernel won't reach the init step. Reword: "When the kernel panics on root, your only recovery is to re-edit `bootargs` in U-Boot and retry. Practice doing this."

## Ch23A — Multi-variant FIT images and DT overlays

### Readability
- §23A.4 Pattern B EEPROM code: `i2c_read(0x50, 0xFF, 1, &id, 1)` — legacy i2c API. The fourth arg is the buffer, fifth is length. Reading 1 byte from address `0xFF` of chip 0x50. The reader will not know U-Boot's `i2c_read()` signature; add a comment annotating each arg.
- §23A.5 "DT overlays — the alternative" — first sentence is "Instead of N full DTBs, you can have **one base DTB** and **N overlay files** that patch it." Good and clear. Keep.
- §23A.6 — embedded `bootcmd` script with `if/elif/else/fi`. Reader from Ch23 §23.1's intro will see this and recognize the DSL. Now ensure §23.1 actually introduces `elif` syntax — it doesn't currently. Either backfill in Ch23 or add a note in §23A.6: "`elif` is U-Boot's else-if; standard hush syntax."

### MCU-engineer friendliness
- §23A.1 — Three hardware revs scenario is excellent and very real. Keep.
- §23A.4 Pattern A — Strap pin — explain WHY a strap pin: "On MCUs you'd compile different firmware per board variant. On Linux you ship one binary and detect the variant at runtime. Strap pins (resistor-populated GPIOs) are the cheapest detection mechanism: $0.01 BOM, 1 ms boot-time read, instantly identifiable in software." This justifies the pattern instead of presenting it as a given.
- §23A.5 — "DT overlays" — for an MCU reader this is new vocabulary. Add: "An overlay is a small DT 'patch file'. It says 'add these nodes, change these properties' relative to a base DT. U-Boot (or the kernel) merges them in memory. Conceptually identical to a `git diff` of two DT files." 

### Missing examples / figures
- §23A.2 — `mkimage -f multi.its multi.itb` output should show the build's hash-verification step so the reader sees that the hashes were computed.
- §23A.3 — show actual `bootm 0x82000000#conf-rev-b` output (the lines: "Loading kernel from FIT Image at 82000000 ... Verifying Hash Integrity ... OK ... Loading fdt from FIT Image ..."). Reader needs to know what success looks like.
- §23A.5 — show the resulting merged DT after `fdt apply`. A `fdt print /` excerpt would show "the base I²C2 node + the overlay's gt911@5d node combined". Without seeing the result, the reader has no mental verification.
- §23A.6 — the inline `bootcmd` script is large and complex. Add a small flow diagram: "i2c probe → read byte → switch → setenv variant → bootm with variant".

### Technical errors
- §23A.4 Pattern A — `gpio_get_value(IMX_GPIO_NR(1, 9))` — the `IMX_GPIO_NR(bank, offset)` macro encodes a GPIO descriptor; check it's the U-Boot API (some versions use `gpio_request` first). Add a note that you may need `gpio_request(IMX_GPIO_NR(1, 9), "rev_pin")` before `gpio_get_value`.
- §23A.4 Pattern B — `i2c_set_bus_num(0)` then `i2c_read(0x50, 0xFF, 1, &id, 1)`. The address `0xFF` of a 24C04 is at end of bank 0 (24C04 is 512 bytes total, 256 per bank with the bank chosen via the I²C slave address LSB). For a 24C04 the high half (256-511) is accessed at chip address 0x51. So reading "byte 0xFF" via chip 0x50 reads byte 255 of the lower bank, which is fine — but if the manufacturing pipeline writes the ID byte at offset 0xFF of the *upper* bank, the code reads the wrong byte. Note the assumption.
- §23A.5 — `fdt resize 8192` — the syntax is `fdt resize <size_in_bytes>`. 8192 = 8 KiB additional space. The reader will see "8192" and might read it as KiB; specify "8192 bytes (= 8 KiB) extra".
- §23A.5 trade-offs table — "Tooling support" row for overlays says ">= 2020.07". That's accurate for some features (e.g., `fdt apply` with symbol resolution) but `fdt apply` itself has been around longer. Tighten: "`fdt apply` works in any modern U-Boot; symbol-based overlay support requires `dtc -@` and U-Boot ≥ 2020.07."
- §23A.6 — `i2c read 0x50 0xFF 1 0x82000000` reads 1 byte from chip 0x50 offset 0xFF into DRAM address 0x82000000. The `setexpr.l id *0x82000000` then assigns env var `id` from the loaded byte. This works *only if* the byte is at the lowest address of the loaded buffer (little-endian read of a 4-byte value where only the low byte matters). For 1-byte reads use `setexpr.b` if available, or carefully comment.

### Knowledge prerequisites missing
- §23A.4 Pattern C — eFuse — `BOARD_ID_BANK, BOARD_ID_WORD` are placeholder symbols; the reader will not know which bank/word to use. Either give a real example (e.g., NXP commonly uses GP1[0:7] for board ID) or state "you choose bank/word per project; verify with `imx_efuse_blow_helper` (Ch9 reference) which fuses are available".
- §23A.5 — DT overlay syntax (`/plugin/`, `&label`) is new. Reader hasn't yet read Ch 27. Forward-reference.
- §23A.5 — `dtc -@ -O dtb` — the `-@` flag generates a `__symbols__` node in the compiled DTB so overlays can resolve labels. Explain once.

### Other
- §23A.8 Pitfall "Strap pin floats" — good. Add a corollary: "Use the i.MX6ULL internal pull-up/pull-down if you don't have an external pull. Configure via IOMUX PAD_CTL (Ch12)."
- §23A.7 Lab item 5: "Read U-Boot's `fdt apply` source." — fine, but the suggested path `cmd/fdt.c` and `common/fdt_support.c` — the actual `fdt apply` implementation in modern mainline lives in `boot/fdt_support.c` (not `common/`). Verify.

## Ch24 — Workflows: TFTP, NFS, USB-OTG

### Readability
- §24.1 introduction: "stop reflashing the SD card." Strong opener. Keep.
- §24.4 `flash_all.uuu` script: "(Real recipes are more involved; this is the structure.)" — this disclaimer undermines the example. Either provide a real, working recipe, or remove the disclaimer and explain that this is an illustration. As-is the reader is left wondering what's wrong with the example.
- §24.5 ASCII flow diagram is excellent. Possibly the best diagram in Part III. Keep verbatim.

### MCU-engineer friendliness
- §24.1 — the table mapping transport → job is great. Add a line acknowledging this is *very* alien to MCU engineers: "MCU engineers: this workflow has no equivalent in MCU dev. On an STM32 you flash and run; on embedded Linux you can have the kernel come from a TFTP server, the rootfs from an NFS mount, and the bootloader from SD — three transports, three lifecycles. The next sections set each up."
- §24.2 "Stage layout on the host" — using `ln -s` to symlink `/srv/tftp/zImage` to the kernel build tree's output is *the* pro tip. Currently it's stated cleanly. Keep. Add: "MCU engineers used to copy-then-flash workflows: this symlink eliminates the copy step entirely. `make zImage` immediately publishes a new kernel."
- §24.3 — NFS root explanation. MCU engineers may not know NFS at all. Add: "NFS is 'mount a directory on the host as a directory on the target over the network'. The target sees `/srv/nfs/rootfs/etc/passwd` as if it were a local file; reads are RPCs. For development this is magical: edit on host, change visible on target in milliseconds."
- §24.4 `uuu` — `uuu` is a high-level scripting tool. MCU engineers will see "fastboot" + "SDP" + "uucmd" and feel lost. Brief glossary: "**SDP** (Serial Download Protocol) is the i.MX BootROM's USB interface — Ch9. **Fastboot** is an Android-derived protocol U-Boot can speak to expose 'flash my eMMC' commands over USB. **uuu** is a script driver that combines both."

### Missing examples / figures
- §24.2 — add a wireshark / `tcpdump -i eth0 port 69` snippet showing TFTP packet flow. Or at least show "after `tftp ${loadaddr} zImage`, on the host you'll see one UDP request packet to port 69, then ~6000 data packets." Helps reader debug when TFTP doesn't work.
- §24.3 — add an example `/etc/exports` line *plus* the `showmount -e localhost` verification. Currently the reader sets exports once and hopes; show how to verify.
- §24.4 — provide a real, working `uuu` recipe for first-time flashing of the MINI. The current placeholder script is non-functional. Reference NXP's `imx_uart` or `imx_usb_loader` if there's a simpler tool.
- §24.6 — the env helpers block is great. Add a "save this to a file `dev-env.txt` and load via `env import -t 0x82000000 <size>`" tip — so the reader can version-control their dev env.

### Technical errors
- §24.2 — TFTP speed: "TFTP runs at ~1 MB/s on 10/100 Ethernet (UDP, small windows). A 6 MB `zImage` arrives in ~6 seconds." On modern U-Boot with `CONFIG_TFTP_BLOCKSIZE=1468` and `CONFIG_TFTP_WINDOWSIZE=8` (RFC 7440 windowsize), TFTP can run at 5-10 MB/s. The 1 MB/s figure is for default block size 512. Either cite the conservative default or mention the tunables.
- §24.3 — `nfsroot=192.168.7.1:/home/you/imx6ull/rootfs,vers=3,nolock,tcp` — `tcp` here is implicit for NFSv3 in many distros but not all. Verify the exact tokens accepted by the kernel's nfsroot parser (`Documentation/admin-guide/nfs/nfsroot.rst`).
- §24.3 — kernel boot log sample shows "`[ 7.812345] Sending DHCP requests . OK`" but the `ip=` cmdline shown earlier sets a static IP, not DHCP. Inconsistent. Either change cmdline to `ip=dhcp` or change the log to not mention DHCP.
- §24.4 — `uuu` script: `SDP: boot -f SPL` then `SDPU: write -f u-boot-dtb.imx`. `SDPU` is the SDP-mode-as-a-USB-device-after-boot subset. The order is plausible but the actual NXP recipe is `SDP: boot -f flash.bin` (combined SPL+U-Boot) or `SDP: boot -f SPL` + `SDPU: write -f u-boot.imx`. The variant in this chapter doesn't match the most common form; check against the latest `uuu` documentation.
- §24.4 — `FB: ucmd mmc write ${fastboot_buffer} 0x2000 0x6000` writes 0x6000 sectors (24576 sectors = 12 MiB) starting at sector 0x2000 (= 4 MiB). A 6 MiB zImage wouldn't need 12 MiB. Numbers don't quite match the comment "write zImage to MMC".
- §24.6 — `console=${console}` env var is referenced but never set. Add `setenv console ttymxc0,115200` to the prerequisites.

### Knowledge prerequisites missing
- §24.3 — `ip=` cmdline format: `client::gateway:netmask::interface:autoconf`. The number of colons is critical. Show with each field labeled:
  ```
  ip=192.168.7.2 : : 192.168.7.1 : 255.255.255.0 : : eth0 : off
       client      server-ip     gateway          netmask     hostname  interface  autoconf
  ```
  The empty fields (`::`) are critical and easy to miscount.
- §24.3 — `nfs.callback_tcpport=0` and `CONFIG_NFS_DEBUG` — these are kernel-side knobs the reader has not yet encountered. Forward-reference Ch28/Ch29.
- §24.4 — `udev` rule from Ch3 §3.8 — refresh the reader's memory: "the `udev` rule lets non-root users access /dev/uuu* devices; without it `uuu` needs sudo."
- §24.6 — `bootargs` substitution with `${var}` — the reader has seen this in Ch23, but the `nfsroot_args` here is a 2-line continuation with `\`. U-Boot env values can't contain literal newlines; the `\` continuation is a *display* convenience in this chapter, not actual env syntax. Add: "(These are formatted across lines for readability; in the actual env they're one logical line.)"

### Other
- §24.4 — "**Automated production line** — `uuu` can flash N boards in parallel; standard NXP practice for factory programming." — true and useful. Consider expanding into a short subsection or forward-reference to Ch63 (production / OTA).
- §24.7 Lab item 5: "Practice the `uuu` recovery. Deliberately wipe the SD card's first MB" — this is genuinely scary for a beginner. Add a safety note: "Be triple-certain `/dev/sdX` is your SD card and not your host's hard disk before running `dd if=/dev/zero`. `lsblk` before any `dd` operation."
- §24.8 — Pitfall "Slow Ethernet PHY auto-negotiation. Some PHYs take 2-3 seconds to come up." — useful. Add: "Symptom: `tftp` says 'no link' on first try, works on second. Either pre-bring-up the link with `mii info` then wait, or use `setenv autoload no; dhcp` to force link establishment before TFTP."
- End-of-Part-III box: "Everything from here on assumes you can boot to a U-Boot prompt, network-boot a kernel, and NFS-mount a rootfs." — Strong closer. Keep.
