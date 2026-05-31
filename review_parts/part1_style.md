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
