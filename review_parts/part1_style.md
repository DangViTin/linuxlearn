# Part I — Style/ESL Review

## Cross-cutting patterns

- **Em-dash overload.** Almost every page glues a clause onto another with " — ". It reads as the book's signature tic. Many of these should be a period or a comma. Pick a quota (say, one em-dash per ~5 paragraphs) and break the rest into two sentences.
- **Semicolon-glued clauses.** The author often joins two full clauses with `;` instead of `.`. A non-native reader has to re-parse; a period would just work. Examples flagged per chapter.
- **Sledgehammer "not X — but Y" / "It's not X, it's Y" cadence.** Used for emphasis but blunts when repeated. Trim aggressively in Ch01, Ch02, Ch07.
- **AI-buzzword hits**: `robust`, `crucial`, `essential`, `comprehensive`, `realm`, `harness`, `pivotal`, `landscape`, `seamless`, `navigate` appear sporadically. Quote-and-fix per chapter.
- **Long compound sentences with parenthetical asides.** ESL-hostile. Many sentences run 35–60 words with em-dash interjections mid-clause. Break into 2–3 short sentences.
- **Royal "we" overuse.** "We will write…", "We will build…", "We will configure…" three in a row reads like a marketing deck. Vary with "you" or imperative.

## Ch01 — Preface

### AI wording / sledgehammer / buzzwords
- > "If anything breaks — a different DRAM chip, a custom IOMUX, a peripheral the BSP doesn't know about — you have no foothold to debug from."
  - Rewrite: "If anything breaks, like a different DRAM chip or a custom IOMUX, you have no foothold to debug from."
- > "We will build, by hand, every layer between *power-on-reset* and a running multi-process Linux system on the i.MX6ULL. We will write the boot image bytewise. We will configure the DDR controller register-by-register against the JEDEC sequence. We will hand-write the linker script, the page table, the device tree. We will compile U-Boot…"
  - Rewrite: Break this five-sentence "We will…" chain. Keep two, drop three. "You will build every layer between power-on-reset and a running Linux system on the i.MX6ULL by hand. That means writing the boot image bytewise, setting DDR registers against the JEDEC sequence, hand-writing the linker script, page table, and device tree, then compiling U-Boot from source."
- > "By that point, the tools will feel like productivity wins rather than magic."
  - Rewrite: "By then the tools will feel like time-savers, not magic." ("productivity wins" is corporate.)
- > "The cost is patience. The reward is that no future bug in any of those tools can hide from you."
  - Rewrite: "It takes patience. The payoff is that no bug in those tools can hide from you later." (Drops the parallel "cost/reward" rhetoric.)
- > "If 'register' means 'bank teller window' — the bare-metal chapters in Part II will feel cruel."
  - Rewrite: "If 'register' makes you think of a bank teller's window, Part II will feel cruel." (Em-dash glue.)
- > "This discipline is the entire point of the book. Skip it at your own risk."
  - Rewrite: "This discipline is the point of the book. Skip it and you lose the point." ("at your own risk" is cliché.)
- > "Five items, ten minutes, every new peripheral. This habit, more than anything else, is what separates engineers who can bring up a custom board from engineers who can only operate on someone else's eval kit."
  - Rewrite: "Five items, ten minutes, every new peripheral. That habit is what separates engineers who can bring up a custom board from engineers who can only run someone else's eval kit." (Triplet rhythm + "more than anything else" filler.)
- > "A subscription is among the best dollars per byte in technical journalism."
  - Rewrite: "A subscription is one of the best deals in technical writing." (Cute phrasing; ESL-opaque.)

### ESL readability (long/choppy/idiomatic)
- > "The trouble is that you have learned almost nothing. The vendor BSP brought up your DDR. Yocto cross-compiled your toolchain. U-Boot's `defconfig` set every register on your behalf. The kernel's `imx_v7_defconfig` enabled the right drivers because someone, somewhere, already did the work."
  - Rewrite: Tighten the four parallel sentences into a list or two sentences. "The trouble is that you learned almost nothing. The BSP set up the DDR, Yocto built your toolchain, U-Boot's defconfig set every register, and the kernel's `imx_v7_defconfig` enabled the drivers — all because someone else had done the work."
- > "You have stared at an oscilloscope at 3 a.m. wondering why an interrupt isn't firing."
  - Idiomatic but harmless; keep.
- > "If you cannot regenerate the artifact, the chapter is not finished."
  - Fine; keep.
- > "Bare-metal Part II (Chapters 9–18) is the only part the impatient reader can skip without losing the thread. But: *you should not skip it*."
  - Rewrite: "Part II (Chapters 9–18) is the only part an impatient reader can skip without losing the thread. You should not skip it anyway." (The "But:" with colon reads weird in print.)
- > "It is where this book differs from every other embedded-Linux book on the shelf, and it is the part that will save you, six months from now, when a bring-up problem traces all the way back to a misconfigured AHB clock."
  - Rewrite: Split. "It is where this book differs from every other embedded-Linux book on the shelf. It is also the part that will save you six months from now, when some bring-up problem traces back to a misconfigured AHB clock." (45-word sentence with two mid-clause inserts.)

### Needs more explanation
- §1.7 "Code listings": jumps from "all code is inline" to "licensed MIT; kernel-module excerpts that quote GPL kernel sources inherit GPL-2.0-only per the kernel's license." A reader new to FOSS won't know what "inherit GPL-2.0-only" means in practice. One extra sentence on why GPL applies to derived kernel code would help.

## Ch02 — What "Embedded Linux" actually is

### AI wording / sledgehammer / buzzwords
- > "Once you internalize it, ninety percent of Linux's surface stops looking strange."
  - Rewrite: "Once you have it, most of Linux stops looking strange." ("internalize" + "surface" is jargon.)
- > "The conceptual split between Layer 3 and Layer 4 is the single most important idea in this chapter and the foundation for everything in Parts V and VI."
  - Rewrite: "The split between Layer 3 and Layer 4 is the most important idea in this chapter. Everything in Parts V and VI builds on it." (Avoids "conceptual… single most important… foundation for everything" pile-on.)
- > "This is not a software convention. It is enforced by the CPU."
  - Two-sentence dramatic reveal pattern. Rewrite: "This is not a software convention — the CPU enforces it." Or keep as two but drop the rhetorical setup elsewhere.
- > "Every interaction between application code and the kernel takes this shape. There is no exception."
  - Rewrite: "Every interaction between an application and the kernel takes this shape — no exceptions." ("There is no exception" sounds like a press release.)
- > "Reading a file? `read()` is a syscall. Allocating memory? `brk()` or `mmap()` is a syscall. Sleeping? `nanosleep()` is a syscall."
  - Triplet rhetorical questions. Fine once, but reads like AI when stacked. Rewrite: "Reading a file uses `read()`. Allocating memory uses `brk()` or `mmap()`. Sleeping uses `nanosleep()`. All are syscalls."
- > "They are not wrong in principle, and Zephyr/FreeRTOS exist for that argument."
  - Rewrite: "They are not wrong in principle — Zephyr and FreeRTOS exist for exactly that case."
- > "From the process's point of view, the memory was always there."
  - Fine.
- > "After that, the MMU stops being magical."
  - "Magical" is mild AI-flavor. Rewrite: "After that the MMU stops being a black box."
- > "Pin this section."
  - Rewrite: "Bookmark this section." ("Pin" is jargon from chat apps.)

### ESL readability (long/choppy/idiomatic)
- > "Picture the firmware you wrote last year for a Cortex-M. After reset, the CPU jumps to the vector table at address `0x0`, your reset handler initializes RAM, clears `.bss`, copies `.data`, and calls `main()`."
  - 35-word run-on with five verbs glued by commas. Break: "After reset, the CPU jumps to the vector table at address `0x0`. The reset handler initializes RAM, clears `.bss`, copies `.data`, and calls `main()`."
- > "U-Boot is, in every meaningful sense, a small bare-metal C program."
  - Rewrite: "U-Boot is a small bare-metal C program." ("in every meaningful sense" is filler.)
- > "It has drivers for SD cards and Ethernet that look not unlike your MCU drivers."
  - Double-negative "not unlike" is ESL-hostile. Rewrite: "Its SD card and Ethernet drivers look much like the ones you wrote on the MCU."
- > "Once U-Boot transfers control, the kernel never returns. It owns the hardware forever."
  - "Forever" is dramatic. Rewrite: "Once U-Boot transfers control, the kernel never returns. From that point on, it owns the hardware."
- > "By Chapter 30, you will."
  - Inverted, abrupt. Fine in English; ESL readers may stumble. Keep but acceptable.

### Needs more explanation
- §2.3 "How then does a user-mode program ever ask for I/O? Through a system call, a controlled transition from user mode to kernel mode. On ARMv7-A, the `svc` instruction (formerly `swi`) raises an SVC exception; the CPU switches to SVC mode, jumps to the exception handler, and the kernel decides what to do based on the syscall number in `r7` and arguments in `r0`–`r6`."
  - Too dense for first-time readers. The reader has never seen `svc`, never seen "SVC mode" vs "USR mode" on ARMv7-A, and the register convention (`r7` for number) is dropped without justification. Add a paragraph: what physically happens at the `svc` instruction (banked registers swap, mode bits in CPSR change, PC vectors to a known address), and why `r7` is used (Linux ABI choice).
- §2.4 "Virtual memory, in one section": the page-table walk is condensed into one sentence. A reader who hasn't seen an MMU has only the vaguest picture. The first-level/second-level structure, the TLB, and what "the MMU walks" physically means should each get one sentence — even if Ch17 builds it for real.
- §2.6 "inode": defined in two sentences but used in the next subsection without a recap. ESL readers will lose the link between "file object" and "inode". One extra sentence tying inode → directory entry → fd would help.

## Ch03 — Host environment setup

### AI wording / sledgehammer / buzzwords
- > "A flaky host is the single most common time-sink in embedded Linux work — far more than buggy code."
  - Rewrite: "A flaky host wastes more of your time than any bug in your code." (Sledgehammer "single most common… far more than".)
- > "By the end of this chapter, 'change a source file, see the change run on the board' must take under thirty seconds. If it takes longer, you will quietly stop iterating, and you will stop learning."
  - Rewrite: "By the end of this chapter, the loop 'change a file, see it run on the board' must take under thirty seconds. If it is slower, you will iterate less, and you will learn less." (Drops "quietly".)
- > "Other options work but cost you time in ways that vary from 'annoying' to 'showstopper'."
  - Cute phrasing. Rewrite: "Other options work but cost you time, sometimes a lot."
- > "Two opinions about this layout, both load-bearing for the rest of the book"
  - "Load-bearing" is metaphor jargon, ESL-opaque. Rewrite: "Two rules about this layout. Both matter for the rest of the book."
- > "This is the central iteration trick of embedded Linux."
  - Fine — keep.
- > "What each pulls in, briefly"
  - Fine.
- > "The first surprise for many people is that the *kernel* uses OpenSSL during build (for module signing)."
  - Rewrite: "Surprise: the kernel needs OpenSSL during build (for module signing)." (Drops "for many people".)
- > "If you wipe the wrong block device you will lose your operating system. Look at the size. Look at the mount points. Then look again."
  - Triplet ("Look. Look. Then look again.") is rhetorical. Reads dramatic. Rewrite: "If you wipe the wrong block device you will lose your operating system. Check the size and the mount points twice before running `dd`."
- > "That regex on `/dev/sd[b-z]` is the seatbelt: it refuses to write to `/dev/sda`, which is almost always your host's root disk."
  - Fine — "seatbelt" is a clear, common metaphor. Keep.
- > "Every embedded engineer has done this once."
  - Idiomatic but harmless.

### ESL readability (long/choppy/idiomatic)
- > "If you are running Windows or macOS, the fastest path is to put Ubuntu on a USB-3 NVMe enclosure and boot from it. Dual-booting your daily-driver machine is the obvious alternative; the only thing that matters is that, at the end, when you plug the board into a USB port, `lsusb` on your host sees it without ceremony."
  - 45-word sentence with three commas and a semicolon-glue. Break: "Dual-booting your daily machine is the obvious alternative. What matters is that when you plug the board into a USB port, `lsusb` sees it without trouble." (Drops "without ceremony" idiom.)
- > "A common source of confusion: people use the `linux-gnueabihf` toolchain for bare metal and get baffled when their build pulls in libc. Use the right tool for the job."
  - "Get baffled" + "right tool for the job" are both idiomatic. Rewrite: "A common mistake: people use the `linux-gnueabihf` toolchain for bare metal and are surprised when libc gets pulled in. Use the bare-metal toolchain for bare metal."
- > "Quit with **Ctrl-A Ctrl-X**. Send Ctrl-C with **Ctrl-A Ctrl-C** (the leader sequence catches things picocom would otherwise intercept)."
  - The parenthetical is jargon-dense for ESL. Rewrite: "Quit with Ctrl-A Ctrl-X. To send a real Ctrl-C to the board, press Ctrl-A then Ctrl-C — picocom uses Ctrl-A as its escape key."
- > "Booting a kernel over NFS-root on Wi-Fi works but is brittle. If you see 'VFS: Unable to mount root fs', it is almost always NFS timing out, not a real kernel bug. Use wired."
  - "Brittle" is fine. "Use wired" is a sentence fragment; keep for punch.

### Semicolons / em-dashes to break
- > "Pros: newer GCC, often better optimization. Cons: triplet is `arm-none-linux-gnueabihf`, not `arm-linux-gnueabihf`. We accommodate both throughout the book."
  - Fine; this is list-style.
- > "Source Insight 4 (`sourceinsight.com`, commercial Windows) — extremely fast indexer, instant 'Go to Definition,' visual call graphs. Read-only for our purposes; popular in Chinese-language embedded communities."
  - Semicolon glue. Rewrite: "...visual call graphs. Read-only for our purposes. It is popular in Chinese-language embedded communities."

### Needs more explanation
- §3.4 "Decoding the triplet": the `eabi` entry says "Embedded ABI v5" with no further word — ESL reader still doesn't know what an ABI is. One sentence: "An ABI fixes how functions pass arguments, return values, and use the stack so that code from different compilers can link together."
- §3.8 "USB-OTG flashing tools": "When you strap the boot pins to 'USB' or no SD/eMMC is present, the chip enumerates as a USB device". The reader has never seen "strap the boot pins" before — this is Ch07 vocabulary. A one-line forward reference ("the boot pins are physical pins read by the chip at reset; Ch07 covers them") would help.

## Ch04 — ARMv7-A for MCU engineer

### AI wording / sledgehammer / buzzwords
- > "the three concepts that justify the entire kernel — **privilege levels**, **the MMU**, and **banked registers / exception modes**. Internalize these and most kernel design choices follow."
  - Rewrite: "the three concepts that justify the entire kernel: privilege levels, the MMU, and banked registers / exception modes. Get these and most kernel design choices follow." (Em-dash glue + "internalize".)
- > "Every row above explains *something* about Linux. The MMU exists so multiple processes can have private address spaces. Banked registers exist so taking an exception does not corrupt user-space state. The generic timer exists so the kernel does not have to argue with the bootloader over who programs the tick source. NEON exists so glibc's `memcpy` is fast. And so on."
  - Triplet+ rhythm and "And so on" tagline. Rewrite: "Every row above explains something about Linux. The MMU gives each process a private address space. Banked registers stop an exception from trashing user-mode state. The generic timer means the kernel does not fight the bootloader over the tick source. NEON makes glibc's `memcpy` fast." (Drop the "exists so" parallel and the closer.)
- > "The Cortex-M equivalent is nothing — the hardware did it for you. The A-profile design trades hardware simplicity (cheaper silicon) for software complexity (more careful entry/exit code). Linux's `entry-armv.S` is one large fortress of code dedicated to exactly this."
  - "Fortress of code" is purple. Rewrite: "The Cortex-M equivalent is nothing — the hardware did it for you. A-profile trades cheaper silicon for trickier entry/exit code. Linux's `entry-armv.S` is the file that handles all of it."
- > "When you read in a Linux kernel book that 'syscall switches to kernel mode', what that *means*, on this hardware, is: an `svc` instruction triggered a Supervisor Call exception, which moved the CPU from USR mode (PL0) to SVC mode (PL1), banked LR and SP swapped to their SVC-mode copies, and the exception handler began running with full privileges. There is nothing magical about it. It is a normal exception, same family as IRQ."
  - 60-word run-on plus "There is nothing magical about it" two-sentence reveal. Rewrite: Break into three sentences. "When a Linux kernel book says 'syscall switches to kernel mode', here is what happens on this hardware. An `svc` instruction triggers a Supervisor Call exception. The CPU moves from USR mode (PL0) to SVC mode (PL1). LR and SP swap to their SVC-mode copies, and the handler runs with full privileges. It is a normal exception, same family as IRQ."
- > "Just like Cortex-M, but unlike Cortex-M, you cannot easily run usefully fast without them."
  - "Just like X, but unlike X" is a stylistic trip. Rewrite: "Caches are off at reset, same as Cortex-M. The difference is that on A-profile you cannot get useful performance without them."
- > "Once you have done that exercise, every kernel memory-management bug will be ten times easier to think about."
  - "Ten times easier" is hand-wave. Rewrite: "Once you have done that exercise, kernel memory bugs are much easier to read."
- > "The bible."
  - "The bible" is overused. Rewrite: "The reference of last resort."
- > "By the standards of 2026, a slow core."
  - Fine but reads slightly dramatic. Keep.

### ESL readability
- > "The i.MX6ULL contains a single **Cortex-A7** core, which implements **ARMv7-A** with the **VFPv4** floating-point unit and **NEON** SIMD. There is also a small **Cortex-M4** companion on i.MX6 *SoloX* and bigger family members — there is **no Cortex-M4** on i.MX6ULL. The single A7 is alone."
  - "The single A7 is alone" is poetic and confusing. Rewrite: "The i.MX6ULL has one Cortex-A7 core with VFPv4 and NEON. Bigger i.MX6 parts (e.g. SoloX) also carry a Cortex-M4 companion. The i.MX6ULL does not — it is A7 only."
- > "Cortex-A7 is, by the standards of 2026, a slow core. It is in-order, dual-issue, with a short pipeline (8 stages). Its strength is power efficiency, silicon area, and *price*. It is also, for our purposes, **simpler to reason about** than its big-core siblings (A53/A72/A76), which is why we picked it."
  - "It is also, for our purposes," + parenthetical is a mid-sentence detour. Rewrite: "By 2026 standards Cortex-A7 is a slow core: in-order, dual-issue, 8-stage pipeline. Its strengths are power, area, and price. For our purposes it is also easier to reason about than the bigger A53/A72/A76 cores, which is why we picked it."
- > "In Cortex-A (ARMv7-A), there is no auto-stacking. Instead, the CPU has **nine processor modes**, each with its own banked copies of certain registers. When an exception fires, the CPU switches to the appropriate mode; the new mode's banked registers shadow the user-mode ones; *your handler is responsible* for saving anything else it wants to preserve."
  - Two semicolon-joined clauses inside one sentence. Rewrite: "In Cortex-A (ARMv7-A) there is no auto-stacking. The CPU has nine processor modes, each with its own banked copies of certain registers. When an exception fires, the CPU switches to the right mode. The new mode's banked registers shadow the user-mode ones. Your handler must save anything else it wants to keep."
- > "When an IRQ fires, the CPU does not push anything; it simply switches to IRQ mode, and now `SP` refers to a different physical register than it did a microsecond ago."
  - Semicolon glue + "a microsecond ago" idiom. Rewrite: "When an IRQ fires, the CPU does not push anything. It just switches to IRQ mode, and `SP` now points to a different physical register than it did one cycle earlier."
- > "Cortex-M has the same instructions; the surprise on A-profile is that you must also use the right barrier afterwards if you need ordering against unrelated memory."
  - Semicolon glue. Rewrite: "Cortex-M has the same instructions. The surprise on A-profile is that you also need the right barrier afterwards if you want ordering against unrelated memory."
- > "For user space, NEON is just there — `libc`'s `memcpy`, `memset`, `strcmp` use it. You will see it in `objdump -d` of any glibc binary."
  - "Just there" is colloquial. Rewrite: "For user space, NEON is always available. `libc`'s `memcpy`, `memset`, and `strcmp` use it, and you will see it in any glibc `objdump -d`."
- > "Symptom: code 'should work' but doesn't, until you add an unrelated `printk` (which happens to insert a barrier)."
  - Fine; keep.

### Needs more explanation
- §4.3 "The nine modes": the table lists 9 modes and `M[4:0]` encodings, then jumps into a banked-register diagram. ESL readers will struggle with what "banked" physically means. Add one paragraph: "Banked" means there are several physical registers that all carry the same name (e.g. R13). Which one you actually access depends on the M[4:0] bits in CPSR. A mode switch does not move data; it just changes which physical register the name R13 resolves to. That single fact explains every later line in the diagram.
- §4.3 IRQ-entry asm listing: the reader has never seen `srsdb`, `cpsid if, #0x13`, or `rfeia` before. Two lines per instruction would help: `srsdb sp!, #0x12` = "store return state (LR+SPSR) onto the IRQ-mode stack and decrement SP"; `cpsid if, #0x13` = "disable IRQ+FIQ and change to SVC mode (0x13)"; `rfeia sp!` = "return from exception, popping LR and SPSR off SP".
- §4.4 "CPSR/SPSR": the layout diagram lists Q, IT, J, GE, E, A, I, F, T, M without explaining *why* there are two instruction-set bits (J and T). One sentence on the historical layering (ARM/Thumb/ThumbEE/Jazelle, with Jazelle being effectively dead in our era) would tie it together.
- §4.5 "Translation table formats": the short-descriptor walk diagram uses 12 / 8 / 12 bit field widths but the labels say "Level-1 index 31:20" (12 bits), "Level-2 idx 19:12" (8 bits). State explicitly: "L1 index is 12 bits → 4096 entries, each covering 1 MB; L2 index is 8 bits → 256 entries, each covering 4 KB." Right now the reader has to count bits in their head.
- §4.6 caches: the chapter says "PIPT means no virtual-address aliasing for normal cache lines". The reader who has never seen VIPT cannot judge what "aliasing" means in this context. Add one sentence: "With a virtually indexed cache (VIPT), two different virtual addresses that map to the same physical page can hit two different cache lines, so the kernel must work to keep them consistent. PIPT avoids the problem entirely."

## Ch05 — i.MX6ULL tour

### AI wording / sledgehammer / buzzwords
- > "every later chapter will name a peripheral. You should be able to find that peripheral on the die-block diagram, locate its register base, identify its clock root and gate bit, and learn what pin it appears on — within minutes."
  - Four-verb chain plus em-dash tag. Rewrite: "Every later chapter will name a peripheral. For each one you should be able to find it on the block diagram, locate its register base, find its clock root and gate bit, and know what pin it lands on. All of that in a few minutes."
- > "These three structures repeat across every NXP i.MX SoC; the names change, the shapes do not."
  - Aphorism. Acceptable, but the semicolon should be a period. Rewrite: "These three structures repeat across every NXP i.MX SoC. The names change, the shapes do not."
- > "Memorize this table — it is the geography of the chip."
  - "Geography of the chip" is fine, but the em-dash glue can be a period. Rewrite: "Memorize this table. It is the geography of the chip."
- > "Print that table and tape it to the wall."
  - Fine; engineer voice. Keep.
- > "The most useful 128 KB on the chip"
  - Appears twice (§5.1 and §5.3). Drop one. Possessive judgement reads like AI hype the second time.
- > "Pitfall #1 of all NXP work"
  - Hyperbole. Rewrite: "The most common NXP bring-up pitfall: forgetting to enable a peripheral's clock gate."
- > "IOMUX setup is the second-most common bring-up bug after 'forgot the clock gate.'"
  - Ranked claim with no source. Rewrite: "IOMUX setup is the next most common bring-up bug after a missing clock gate."
- > "You will not read them all. You *will* spend a lot of time grep-ping them for a pin you care about."
  - Italic emphasis + future-tense lecture. Fine but reads pep-talky. Keep.
- > "is a waste of life"
  - Idiomatic; minor. Keep.
- > "The 'Programming Guide' in each peripheral chapter is usually wrong about something."
  - Sweeping. Rewrite: "The 'Programming Guide' at the front of each peripheral chapter often gets one detail wrong. When in doubt, trust the register descriptions — those are machine-generated from the silicon."

### ESL readability
- > "NXP positions the i.MX6ULL ('Ultra-Low-Layer') at the bottom of the i.MX6 family: single Cortex-A7 core, no GPU, no VPU, no PCIe — but full peripheral set (Ethernet, USB, LCD, CSI camera, SAI audio, eMMC, NAND, QSPI, plus 8 UARTs and 4 I²C/SPI). It targets cost-sensitive Linux applications: industrial HMI, point-of-sale, smart metering, simple gateway boxes."
  - 50+ word run-on with two parentheticals. Break: "NXP positions the i.MX6ULL ('Ultra-Low-Layer') at the bottom of the i.MX6 family. One Cortex-A7 core, no GPU, no VPU, no PCIe. The peripheral set is still full: Ethernet, USB, LCD, CSI camera, SAI audio, eMMC, NAND, QSPI, 8 UARTs, and 4 I²C/SPI. It is aimed at cost-sensitive Linux applications such as industrial HMI, point-of-sale, smart metering, and simple gateways."
- > "On-chip memory: 128 KB **OCRAM** at `0x00900000` (the most useful 128 KB on the chip) + a separate 96 KB **Boot ROM** at `0x00000000` (mask-programmed by NXP). There is **no TCM** — TCM is a Cortex-M / Cortex-R concept; A-profile cores rely on L1/L2 caches instead."
  - Em-dash + semicolon stack. Rewrite: "On-chip memory: 128 KB OCRAM at `0x00900000` plus a separate 96 KB Boot ROM at `0x00000000` (mask-programmed by NXP). There is no TCM. TCM is a Cortex-M / Cortex-R concept; A-profile cores use L1/L2 caches instead." (Or drop the semicolon there too.)
- > "Of the 128 KB OCRAM at `0x00900000`–`0x0091FFFF`, the Boot ROM uses a portion **while executing the boot sequence** for its own working area (exception vectors at the low end; MMU table, stack, and bookkeeping near the top)."
  - 40 words with nested parenthetical. Rewrite: "The Boot ROM uses part of OCRAM (`0x00900000`–`0x0091FFFF`) while it is running the boot sequence. The low end holds exception vectors; the top end holds the MMU table, stack, and ROM bookkeeping."
- > "i.MX6ULL's 128 KB L2 is integrated in the MPCore block, not a separate PL310"
  - Fine but the row label "External PL310 L2 controller / (absent)" reads strangely. Add a parenthetical for the new reader: "(present on bigger i.MX6 parts; absent here)".
- > "The DRAM aperture begins at `0x80000000`. Every U-Boot script you will read sets `loadaddr=0x80800000` or similar. That magic number is 'DRAM base + 8 MB'. The kernel by convention loads ~8 MB into DRAM so its decompressed image (which lives below the load address) has somewhere to go."
  - Last sentence is murky. ESL reader will not catch that the *compressed* image is loaded high and *decompresses downward*. Rewrite: "The DRAM aperture starts at `0x80000000`. Every U-Boot script you will read sets `loadaddr=0x80800000` or similar. That is just 'DRAM base + 8 MB'. The kernel image is loaded at that offset because the compressed image decompresses downward into the space below it."
- > "the *peripheral* must say which pin to listen to — a 'daisy chain', in NXP's language"
  - "Daisy chain" is misleading here; NXP actually calls these "daisy chain" but the metaphor is opaque to ESL readers. Add one extra sentence: "NXP calls this a 'daisy chain' because the input signal arrives via a chain of pad → pin mux → peripheral input selector."

### Needs more explanation
- §5.5 "Clock tree": four layers are listed but the reader has never seen what a PFD is on a PLL. The line "PLL2 and PLL3 expose PFDs (Phase Fractional Dividers): four per PLL" is dense. Add: "A PFD takes the PLL's VCO output and divides it by a fractional value (typically 18/N where N=12..35), giving four extra clock outputs per PLL without adding hardware multipliers. PLL2_PFD2 at 396 MHz, for instance, is PLL2's 528 MHz × 18/24."
- §5.5 CCGR encoding `00/01/11`: where is `10`? One line — "Encoding `10` is reserved" — would close the loop.
- §5.6 IOMUX: the example "ALT5: GPIO1_IO04 (same as ALT0; sometimes the GPIO appears in two ALTs)" is confusing. Why would the same function appear twice? Add a footnote: "Some pads expose the GPIO function in two ALT slots so that NXP's pin-mux tool can route conflict-free in either case."
- §5.6 The constant `0xB0B1`: promised "we will decode every bit in Chapter 9" but a one-table sketch here (drive strength = bits 5:3, slew = bit 0, pull-up = bits 13:12, etc.) would let an MCU engineer who hits IOMUX before reading Ch9 still make progress.
- §5.7 Power domains: "SNVS — Secure Non-Volatile Storage: a tiny always-on domain with its own oscillator, RTC, and 24 bytes of SRAM." A reader new to the part will not know whether "always-on" means "while VDD_SOC is on" or "while a coin-cell battery is connected." Clarify: "SNVS stays powered from a coin-cell on VBAT even when the main 3V3 is off. That is why the RTC keeps time across reboots."

## Ch06 — Toolchain

### AI wording / sledgehammer / buzzwords
- > "every later chapter ends with 'now build it.' If 'build' is a black box, every failure will be too."
  - Aphorism. Fine; keep.
- > "the ABI is a contract between every function call across your program"
  - "Contract between every function call" is awkward. Rewrite: "the ABI is the contract that every function call in your program follows."
- > "You can read your own machine code. This is non-negotiable for embedded work."
  - "Non-negotiable" is corporate. Rewrite: "You can read your own machine code. For embedded work, that skill is mandatory."
- > "*That* is what runs first when the kernel `exec`'s this file; only after it finishes loading shared libraries does control reach `main`."
  - Italic emphasis + semicolon. Rewrite: "That is what runs first when the kernel `exec`s this file. Only after the dynamic linker finishes loading shared libraries does control reach `main`."
- > "This is liberating once you accept it."
  - "Liberating" is hippie. Rewrite: "Once you accept that, working without libc is straightforward."
- > "the tool of record"
  - Journalese. Rewrite: "the tool you will use."
- > "this section is longer than it might first seem because every later chapter references it; once you have it, you do not need it again"
  - Semicolon glue + meta-commentary. Rewrite: "This section is longer than it looks. Every later chapter references it, but once you have it down, you do not need to revisit it."
- > "the first time you cut-and-paste a rule, this bites everyone"
  - "Bites everyone" is idiomatic. Rewrite: "Every engineer hits this the first time they cut-and-paste a rule."
- > "mostly a footgun"
  - Jargon. Rewrite: "mostly a trap."
- > "Every flag in `CFLAGS` is load-bearing"
  - Metaphor jargon. Rewrite: "Every flag in `CFLAGS` matters."
- > "is the same reason we are doing this book"
  - Cute reference. Rewrite: "is the same reason we wrote this book."

### ESL readability
- > "…six programs run in sequence. `gcc` is a **driver**: it parses the command line, decides which sub-tools to invoke, builds their argument lists, and chains their I/O."
  - Fine. Keep.
- > "For embedded work, the steps that bite are #1 (include path mismatches), #5 (linker script and wrong sysroot), and the boundary between #3 and #5 (relocation types)."
  - Triple parenthetical. Rewrite: "For embedded work, the steps that bite are: step 1 (include path mismatches), step 5 (linker script and sysroot problems), and the boundary between step 3 and step 5 (wrong relocation types)."
- > "VMA of `.data` = somewhere in RAM (where the variables live at runtime). LMA of `.data` = somewhere in Flash (where the *initial values* are stored persistently). Your startup code copies LMA → VMA before `main()`."
  - Fine — already broken up cleanly. Keep.
- > "Use `:=` everywhere by default. The `=` form is occasionally necessary (recursive expansion of generated variables) but mostly a footgun."
  - "Mostly a footgun" — see above. Otherwise the sentence is fine after that swap.
- > "We will mostly use glibc (because the Ubuntu toolchain ships it) and switch to musl for one comparison build in Chapter 34."
  - Long parenthetical mid-sentence. Rewrite: "We will mostly use glibc because the Ubuntu toolchain ships it. In Chapter 34 we switch to musl once for comparison."
- > "Compare sizes:" followed by two `ls -l` commands and "You will see something like 8 KB dynamic vs 600 KB static (glibc). With musl, static is ~30 KB."
  - "Something like" is filler. Rewrite: "Expect roughly 8 KB dynamic vs 600 KB static with glibc, or ~30 KB static with musl."

### Needs more explanation
- §6.5 AAPCS: the table lists registers and roles but never explains "caller-saved" vs "callee-saved" in plain language. ESL readers see the terms but cannot tell who is responsible. Add: "Caller-saved means the calling function must spill the register to the stack if it wants the value after the call. Callee-saved means the called function must restore the register before returning. The compiler enforces both for you, but in hand-written assembly you must do it yourself."
- §6.5 r9 "platform register" — mentioned ("see §6.6") but §6.6 does not actually explain it. One sentence: "On Linux ARMv7-A hard-float, r9 is the **TLS register** — it points to the current thread's TLS block. Touch it only if you know what you are doing." would close the loop.
- §6.6 libc inventory: musl listed at "~30 KB". For a reader who has never built a static hello-world, add one line: "A static glibc binary pulls in name-service, locale, and dynamic-linker machinery even when you don't use them; musl strips that down to almost nothing."
- §6.7.2 `:=` vs `=`: the worked example is great. Add a one-line summary table after it: "`=` → expand later (variable lookups happen when the rule runs); `:=` → expand now (variable lookups happen at definition time)."
- §6.9 ELF: "The startup code (or the kernel) zeroes it." Add the *why* in one sentence: "ELF stores `.bss` as a size only (no bytes) so the file stays small; the loader allocates real RAM and zeroes it at load time."

## Ch07 — Boot ROM, IVT, DCD

### AI wording / sledgehammer / buzzwords
- > "the worst kind of bug, because there is no log to read"
  - Aphorism, fine. Keep.
- > "These three structures, all under 100 bytes, are the contract."
  - "Are the contract" — fine. Keep.
- > "It runs first, at every power-on and every reset, on every i.MX6ULL ever made."
  - Triplet rhythm. Rewrite: "It runs first at every power-on and every reset, on every i.MX6ULL ever shipped."
- > "This is the cleverest, least-documented, and most useful part of i.MX boot."
  - Superlative pile-up. Rewrite: "The DCD is one of the more clever and least-documented parts of i.MX boot."
- > "Sixteen bytes of data, four bytes of overhead."
  - Fine. Keep.
- > "Burn the procedure into muscle memory: a board that boots into SDP mode is **not bricked**, no matter what is on its flash."
  - "Burn into muscle memory" is idiomatic. Rewrite: "Drill this procedure until it is automatic. A board that boots into SDP mode is not bricked, whatever is on its flash."
- > "**This is the most important sentence in this chapter.**"
  - Bold, dramatic. Acceptable for a single emphasis but reads sledgehammer. Consider lowercasing or trimming to: "Remember this — it is the most important sentence in the chapter."
- > "The point of doing it ourselves once is the same as the point of the whole book."
  - Aphorism callback. Acceptable; keep.
- > "Getting `self` wrong is the #1 way to brick an otherwise correct image."
  - Ranked claim. Rewrite: "Getting `self` wrong is the most common way to brick an otherwise correct image."

### ESL readability
- > "From POR_B rising to your `_start` executing, the i.MX6ULL Boot ROM performs roughly the following:"
  - Fine. Keep.
- > "**Read `OCOTP_CFG5[BT_FUSE_SEL]`. If set, the boot device comes from fuses (`OCOTP_CFG4`). If clear, it comes from the **BOOT_MODE[1:0]** pins (`BOOT_MODE0`, `BOOT_MODE1`) and the **BOOT_CFG** pins.**"
  - Bold formatting in a sub-bullet is dense. Rewrite plain: "The ROM reads `OCOTP_CFG5[BT_FUSE_SEL]`. If that bit is set, the boot device is taken from the fuses in `OCOTP_CFG4`. If clear, it comes from the BOOT_MODE[1:0] pins together with the BOOT_CFG pins."
- > "Read `BootData.length` bytes from the boot device into `BootData.start` (the destination address)."
  - Fine. Keep.
- > "The whole sequence takes 10–100 ms depending on boot media and image size. The Boot ROM's `printf`-equivalent goes nowhere — there is no UART output unless you build in your own as soon as you take control."
  - Fine. Keep.
- > "Wait — those don't make sense together. Actually they do: this is a U-Boot image meant to be loaded to `0x80700000` (DRAM), and the byte order is little-endian."
  - The "Wait — actually they do" reads chatty/AI-blog. Rewrite: "These look inconsistent at first glance. They aren't, once you remember that the byte order is little-endian and the image is meant to be loaded at `0x80700000` in DRAM."
- > "A DCD entry is a small instruction in a tiny one-byte-opcode language:"
  - "Tiny" + "instruction in a … language" is a bit clumsy. Rewrite: "Each DCD entry is one instruction in a small, one-byte-opcode language:"
- > "The ROM cannot load into DRAM unless DDR is initialized. The ROM cannot initialize DDR unless someone tells it what values to write. The DCD is how you tell it."
  - Triple-sentence cascade. Acceptable as deliberate emphasis but reads AI. Rewrite: "The ROM can only load into DRAM after DDR is initialized, and the ROM cannot initialize DDR on its own. The DCD is the script you hand it that does that initialization."

### Needs more explanation
- §7.2 step 3 boot modes: BOOT_MODE = 0b00 is labelled "Boot from fuses (rare on dev boards)". A reader who has not seen IMX boot before will not know what "boot from fuses" means physically. Add: "When BOOT_MODE = 00, the boot-device selection comes from the burned OCOTP fuses (`BOOT_CFG[1..4]`) rather than from the package pins. Factories use this so end-user boards can't be re-routed to SDP."
- §7.3 IVT magic: the byte sequence `0xD1 0x00 0x20 0x40` is "header: tag, length BE, version". Spell it out once: "Byte 0 = `0xD1` (tag, identifies an IVT). Bytes 1–2 = `0x00 0x20` = 0x0020 = 32, big-endian (IVT length in bytes). Byte 3 = `0x40` or `0x41` (HAB version)."
- §7.5 DCD WRITE format: the `flags:1-byte` byte is described as "bits 3:2 select byte/halfword/word writes, bits 1:0 select write/set/clear semantics". State the actual encoding: "bits 3:2 = `00` byte, `01` halfword, `10` word; bits 1:0 = `00` plain write, `01` set bits, `11` clear bits." Right now the reader cannot turn that into a real value without the RM open.
- §7.6 SDP "command set": each opcode is listed but the reader does not know how the command is framed on the wire. One paragraph: "SDP frames every command as a 16-byte report descriptor over USB HID. The first 2 bytes are the opcode (e.g. `0x0404` for WRITE_FILE), followed by the target address, byte count, and a small payload header. `uuu` builds these frames for you; if you ever need to read its wire log, this is what you're seeing."
- §7.7 .imx file layout: "(1 KB of padding, sometimes contains partition table or zero)" — clarify "partition table" means MBR/GPT, not anything i.MX-specific. ESL readers may think this is part of the IVT.
- §7.9 IVT decoding example: the worked example claims `00 14 78 80` → self = `0x80781400`. That looks wrong — little-endian `00 14 78 80` is `0x80781400`, which doesn't match "loaded to `0x80700000`". Either the example is intentionally inconsistent (and the next paragraph fixes it) or the bytes need to be `00 04 70 80` → `0x80700400`. Re-check the example before publication.

## Ch08 — Hardware bring-up

### AI wording / sledgehammer / buzzwords
- > "the cheapest place to discover a flaky cable or a wrong jumper is *now*, not at 1 a.m. in Chapter 14 when you cannot tell whether your DDR init or your wiring is the problem"
  - Long single sentence with italic and time-of-night anecdote. Acceptable engineer voice; keep but split. Rewrite: "The cheapest time to discover a flaky cable or wrong jumper is now. Not at 1 a.m. in Chapter 14, when you can't tell whether the DDR init or the wiring is broken."
- > "Until you have done it once with a deliberately broken SD card, you will not believe it."
  - Mild dramatic flourish. Keep.
- > "If you are a hardware engineer this is reflex. If you are not, do it once and the habit will save you later."
  - Fine.
- > "**This is the most important sentence in this chapter.**"
  - Same pattern as Ch07. Trim or drop the bold. Rewrite: "That line is the most important confirmation in this chapter — keep it."
- > "Once you've done this, no boot-flash mishap can scare you. You always have a path back."
  - Aphorism. Acceptable; keep.
- > "Burn the procedure into muscle memory"
  - Already flagged for Ch07 — same idiom appears here implicitly with "do it now, with a working board, so you know how to do it under pressure when a board is genuinely stuck." Acceptable in moderation.
- > "The cheapest hardware upgrade you can buy yourself for this book."
  - Mild marketing. Rewrite: "The cheapest hardware investment for this book."
- > "Trust the serial output, not LEDs."
  - Fine. Keep.

### ESL readability
- > "The Point Atom MINI has, at minimum: a microUSB or USB-C **power + OTG** port, an Ethernet RJ45, a microSD slot, a 40-pin expansion header, an LCD ribbon connector, a JTAG header, and a 4-pin debug-UART header. Locate each."
  - 35-word list-as-sentence. Fine for a connector inventory; consider rendering as a real bullet list to make scanning easier for ESL readers.
- > "Do not connect VCC — your CP2102 / CH340 dongle is powered over USB, and double-feeding the rail can damage the board."
  - Fine. Keep.
- > "If the SD card is empty or absent, you should see nothing — but the serial console should still be alive (just idle)."
  - Em-dash + parenthetical. Rewrite: "If the SD card is empty or absent, you should see nothing on the console. The console itself is still alive, just idle."
- > "To prove the serial is alive *without* anything booting on the board, short the dongle's TX to its RX (no board) and type — you should see your keystrokes echo. That confirms the host side."
  - Long sentence + em-dash glue. Rewrite: "To prove the host side works without the board, short the dongle's TX to its RX (no board attached) and type. You should see your keystrokes echo back."
- > "Almost always one of three causes:"
  - Fine.
- > "Push a known-good image to RAM and jump to it:"
  - Fine.
- > "On Point Atom MINI, this is the 'OTG' labelled port."
  - Awkward word order. Rewrite: "On the Point Atom MINI, this is the port labelled 'OTG'."
- > "(some revisions only sample boot pins at POR)"
  - Acronym POR is reintroduced from Ch07 here but unexplained inline. Add a parenthetical: "(POR = power-on reset; some board revisions only sample the boot pins at that moment)."
- > "Part II begins with the most fun chapter in the book: a blinking LED, in pure ARM assembly, on a Cortex-A7."
  - "Most fun" is fine engineer voice. Keep.

### Needs more explanation
- §8.4 Boot-mode selector: the chapter says "Flip the switch to SDP **once now** to confirm it works" but the previous chapter (Ch07 §7.2) described BOOT_MODE = 0b01 as one of several pin states. A one-line cross-reference would help — "(Mechanically, the switch drives BOOT_MODE[1:0] to the values described in Ch 7 §7.2: 0b01 = SDP, 0b10 = internal boot.)"
- §8.6 Recovery drill: the example uses `uuu -b spl u-boot-dtb.imx`. The `-b spl` script is opaque to a first-time reader. One sentence: "`uuu -b <script>` runs a built-in script. `spl` means 'load this image as an SPL via SDP, then let it boot'; later we'll write our own `.uuu` script files."
- §8.6a uuu vs MfgTool: the table maps MfgTool concepts to `uuu` equivalents but uses the word "manufacturing profile" without context. Add one sentence: "MfgTool's 'profile' is an XML file describing the flash layout and the per-step commands. `uuu_script.uuu` is the plain-text equivalent — one line per WRITE_FILE / JUMP_ADDRESS."
- §8.7 JTAG: pin list is given but signal names (TMS, TCK, TDI, TDO, nTRST) are not explained. ESL readers from a Cortex-M background may know SWD better. Add: "If you have only used SWD on Cortex-M, JTAG is the older four-wire-plus-reset version: TCK is the clock, TMS selects the state machine, TDI/TDO carry data, nTRST is an optional reset."
- §8.9 End-of-chapter checklist: good. No expansion needed.

