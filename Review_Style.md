# Review (Style/ESL pass) — Embedded Linux on i.MX6ULL (book/)

> **Reviewer brief.** Each Part below was reviewed for AI-sounding wording, ESL readability, and concept-depth gaps. Reviewers flagged: em-dashes (—) used to glue clauses, semicolons used as connectives, "not X — but Y" sledgehammers, AI buzzwords (delve, leverage, robust, seamless, intricate, navigate, tapestry, underscore, elevate, plethora, myriad, paramount, pivotal, vital, embark, harness, foster, realm, landscape), hedging openers ("It's worth noting", "Notably,", "Crucially,"), triplet rhythm, bullet-list-as-prose, poetic phrasing, royal "we'll"/"let's" overuse, "In conclusion/Moreover/Furthermore" transitions, "This isn't X. This is Y." dramatic reveals, long compound sentences with 3+ clauses, idioms that won't translate, and choppy fragments that should be combined. They also called out hard concepts introduced in one or two sentences without enough explanation for an MCU engineer.

> **How to use this.** Each Part has a *Cross-cutting patterns* block at the top listing wording habits that recur across chapters. Below that are per-chapter sections with quoted text and suggested rewrites. The rewrites aim for SHORTER or EQUAL length, plain English, engineer-at-a-whiteboard tone. Subheadings inside a chapter are only present when the reviewer found something to say.

---
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


---

# Part II — Style/ESL Review

## Cross-cutting patterns
- Em-dash use is heavy throughout, often chaining 2 or 3 clauses. Most can become periods. Several chapters open each section with em-dash-glued sentences ("X — and Y — but Z").
- "Royal we" ("we'll", "let's", "we are about to", "we graduate") appears in nearly every section header. Trim by half.
- The closing-line dramatic flourish (Ch9 §9.7 "you driving electrons through silicon you wrote a contract with"; Ch11 §11.5 "60 lines of Python and 50 lines of C"; Ch12 "force multiplier") is an AI tic. One per chapter is fine; multiple per chapter feels staged.
- "Worth noting / Worth pointing out / Notably" hedges appear in Ch9, Ch11, Ch12. Cut.
- The pattern "X. *Without* X." or "Without it, ..." as a punchline is overused (Ch9, Ch10, Ch11). Vary the construction.
- Triplet rhythm: "No bootloader. No kernel. No OS." (Ch9); "No `mkimage`. No NXP tools. No magic." (Ch11); "No `.data`, no `.bss`, no `main`." (Ch9) — each chapter has at least one.
- Aphoristic one-liners ("habit is cheap, and bugs from 'we will never need this' are expensive"; "once you own the image format, you own boot") feel like AI mottoes. ESL reader will read past them but they don't sound like a working engineer.
- Idiom load is moderate — "let it ride", "earns its salary", "belt-and-braces", "in the void", "force multiplier", "hand-place", "throws away". For ESL readers, prefer plain phrasing.

## Ch09 — ASM LED
### AI wording / sledgehammer / buzzwords
- > "this is your 'I own this chip' moment. Every layer above bare-metal exists to make hard things easier, and you cannot tell whether they are doing it well unless you have once done it the hard way."
  - Rewrite: "This is the moment you really own the chip. Higher layers exist to make hard things easy, but you can only judge them if you have done it the hard way once."
- > "Internalize it; we use it for every peripheral, forever."
  - Rewrite: "Memorize it. We use it for every peripheral in the book."
- > "loaded into OCRAM by the Boot ROM over USB-OTG."
  - Fine, but later: "Boot ROM transfers control. The LED blinks." — three back-to-back fragments. Combine the last two: "The Boot ROM transfers control and the LED blinks."
- > "Hanging off the end of an asm program is not a thing on bare-metal"
  - Rewrite: "An assembly program has no caller to return to; you must explicitly loop forever."
- > "The LED blinks. The blink is, in the most literal sense, you driving electrons through silicon you wrote a contract with."
  - Rewrite: "The LED blinks. You wrote every instruction the CPU executed to get here." (Cut the "contract with silicon" line — it's poetic AI tone.)
- > "There is nothing between your code and the chip. No bootloader. No kernel. No OS. This is, more than any other moment in this book, embedded *Linux* — because you understand now what the next 50 chapters are *adding* to this picture."
  - Rewrite: "Nothing sits between your code and the chip. The next 50 chapters add layers on top of what you just built." (Drops the dramatic triplet plus the italicized reveal.)
- > "We will not use a linker script in this chapter — the program is small enough that we hand-place it."
  - Rewrite: "No linker script this chapter. The program is small enough to hand-place." (em-dash → period; trims "we".)

### ESL readability
- > "On both Point Atom ALPHA and MINI, the user LED ('LED0', marked **D1** on the silkscreen) drives **GPIO1_IO03** active-LOW (the GPIO pulls the cathode side of the LED low to turn it on, with the anode tied to the 3.3 V rail through a current-limiting resistor). Both boards use the same pin."
  - Rewrite: "On both Point Atom ALPHA and MINI, the user LED (D1 on the silkscreen) is on **GPIO1_IO03**. The wiring is active-low: the anode goes to 3.3 V through a current-limiting resistor; the GPIO pulls the cathode low to turn the LED on." (Splits the dense parenthetical.)
- > "Because we are merely *toggling* the bit in this chapter, the active-low wiring is invisible to the program (the LED just blinks opposite-phase from what you might naively expect)."
  - Rewrite: "Because we only toggle the bit, active-low wiring does not change our code. The LED just blinks with inverted phase."
- > "These addresses, for our case (GPIO1_IO03), from the i.MX6ULL Reference Manual:"
  - Rewrite: "Addresses for GPIO1_IO03, from the Reference Manual:"
- > "for a learning exercise the OR-in form is cleaner."
  - Add: "Learning exercise → use the OR form, which leaves the other gates unchanged."
- > "**`ldr r0, =0x...`** is GNU assembler syntax for 'load-pc-relative pool constant'. The assembler generates a literal pool somewhere after the function and the `ldr` becomes a load from that pool. Cortex-A7 cannot encode arbitrary 32-bit immediates in a single instruction; this pseudo-form is the standard idiom."
  - Use periods, not semicolons: "Cortex-A7 cannot encode arbitrary 32-bit immediates in one instruction. This pseudo-form is the standard idiom."

### Needs more explanation
- §9.3 "CPSR.I=1 from reset" is dropped in passing without explaining what CPSR is or what the I bit does. For an MCU engineer coming from Cortex-M (where CPSR doesn't exist by that name; PRIMASK/FAULTMASK do), this needs 3-4 sentences. Mention: CPSR = Current Program Status Register on Cortex-A; I bit masks IRQ, F bit masks FIQ; reset state.
- §9.3 ".syntax unified" — the prose says "modern ARM/Thumb-unified mnemonics" but doesn't explain what the *old* (divided) mnemonics looked like. Either drop the explanation or expand by one line.
- §9.5 "BootData immediately follows IVT (offset +0x20)" — the python heredoc has comments but no prose around why the 0x1000 padding. State plainly: "ROM expects the entry point at offset 0x1000 from the load address. Pad to that."

## Ch10 — C + startup.S + linker script
### AI wording / sledgehammer / buzzwords
- > "you cannot tell whether they are doing it well unless you have once done it the hard way." (Ch9, repeated in Ch10 spirit: "lay them down so the next eight chapters do not have to.")
  - Rewrite: "set these up once so the next eight chapters can ignore them."
- > "When you can answer 'where does the initial value of a global live, and how does it get to RAM?', you understand startup."
  - Rewrite: "If you can answer where the initial value of a global lives and how it reaches RAM, you understand startup."
- > "Whoever drops us at our load address has done all they will do."
  - Rewrite: "Whoever loaded us is done. The rest is on us."
- > "the first function-call instruction in C destroys the world."
  - Rewrite: "the first C function call crashes." (No "destroys the world" theatrics.)
- > "Three things in this script are easy to get wrong; all three you only get wrong once."
  - Rewrite: "Three things in this script are easy to get wrong. Each one bites only once."
- > "habit is cheap, and bugs from 'we will never need this' are expensive."
  - AI mottoism. Cut, or rewrite: "The cost of the loop is zero. The cost of debugging missing init values is high."
- > "the day we move .data to DRAM it earns its salary."
  - Rewrite: "We will use it for real when .data moves to DRAM."
- > "**`bl main`** is a *branched-and-link*"
  - Typo / odd phrasing: should be "branch-and-link" (verb form). Rewrite: "**`bl main`** is *branch-and-link*: it sets LR to the return address before branching."
- > "which is at minimum polite."
  - Rewrite: "which is at least polite to the power budget." or just drop it.
- > "We are now running compiled C on bare metal."
  - Fine, but precedes too many curtain-falls in this chapter.
- > "Macroize it once (as we did with `REG()`) and stop thinking about it."
  - Fine; this is good engineer voice. Keep.
- > "This bug has happened to every embedded engineer at least once."
  - Cliché. Rewrite: "Most embedded engineers hit this bug once. Avoid it by reflex."
- > "Optional but informative."
  - Mild hedge — fine.

### ESL readability
- > "But the moment you write code like: [...] without `volatile`, the compiler can decide the read of `UART_STATUS` is invariant inside the loop, hoist it out, and produce an infinite spin."
  - Triplet "decide, hoist, produce" reads AI-smooth. Rewrite as one shorter chain: "Without `volatile`, the compiler treats `UART_STATUS` as constant inside the loop, reads it once before the loop, and spins forever."
- > "Two `int foo;` declarations in two `.c` files silently collide. Sometimes works, sometimes corrupts."
  - Fragments. Rewrite: "Two `int foo;` declarations in two `.c` files silently merge into one symbol. Sometimes the result works, sometimes it corrupts memory."
- > "Your AAPCS requires SP to be 8-byte aligned at every public function entry. Our `_stack_top = ORIGIN + LENGTH` aligns naturally because LENGTH is a multiple of 8 — but if you change LENGTH to an odd value, expect baffling crashes inside libgcc helpers."
  - Long compound. Split: "AAPCS requires SP to be 8-byte aligned at every public function entry. `_stack_top = ORIGIN + LENGTH` aligns naturally as long as LENGTH is a multiple of 8. Change LENGTH to an odd value and expect crashes inside libgcc helpers."

### Needs more explanation
- §10.3 "We are entered in SVC mode with IRQ/FIQ masked." Cortex-A modes are NOT obvious to an MCU dev. Add a short paragraph or sidebar listing the Cortex-A modes (USR, FIQ, IRQ, SVC, MON, ABT, UND, SYS, HYP), why each exists, what banked registers each has, and *why we want SVC for startup*. Currently the chapter just announces "SVC is what we want" and moves on.
- §10.3 `cpsid if, #0x13` — explain CPSR mode bits (`0x13` = SVC, lowest 5 bits). The `if` suffix means "mask IRQ and FIQ" but that is not stated explicitly. Add one sentence.
- §10.3 `strlo r2, [r0], #4` — conditional execution is a Cortex-A trait that's unusual for ESL reader from M-class. Briefly: "ARM (not Thumb-2) lets most instructions carry a 4-bit condition code in the opcode. `strlo` = store if the previous compare set the LO (unsigned less-than) flag."
- §10.6 `_stack_top = ORIGIN + LENGTH` aligned naturally — fine, but the link between AAPCS 8-byte alignment and "down-growing stack" is implicit. Add: "ARM stacks grow downward (`SP` decrements on push), so the *initial* SP value sits at the top of the region."

## Ch11 — Hand-building a Boot ROM image
### AI wording / sledgehammer / buzzwords
- > "the kind of code you cannot edit with confidence. Owning the tool means owning the image format. Once you own the image format, you own boot."
  - Triple-cadence AI mottoism. Rewrite: "You cannot edit that script with confidence. Owning the tool means owning the format, and owning the format means owning boot."
  - Actually still mottoey. Try: "You will edit this tool again. A 60-line Python script you understand beats a 3-line shell command you don't."
- > "The conclusion writes itself: `dd if=led.imx of=/dev/sdX bs=1k seek=1`."
  - Rewrite: "So: `dd if=led.imx of=/dev/sdX bs=1k seek=1`."
- > "*Without* U-Boot. *Without* mkimage. *Without* Yocto. With 60 lines of Python and 50 lines of C and assembly."
  - Sledgehammer triplet. Rewrite: "No U-Boot, no mkimage, no Yocto. Just 60 lines of Python and 50 lines of C/asm."
- > "the **byte-for-byte layout** of the `.imx` file"
  - Fine.
- > "Worth pointing out:"
  - Hedging opener. Cut: just present the bullets.
- > "Two boot paths, one image, one IVT."
  - Triplet, slightly poetic. Acceptable as a callout title, but the prose under it has another triplet ("SDP, ... SD boot, ... eMMC boot"). Tighten.
- > "the simpler view is that `dcd_addr` is the *post-load* address of the DCD bytes."
  - "Simpler view" hedging. Rewrite: "`dcd_addr` is the address of the DCD *after the image is loaded into RAM*."

### ESL readability
- > "When `uuu` pushes this file in SDP mode, it strips the first `0x400` of pad (it's the leading 1 KB the ROM never reads on USB-SDP) and uploads from `0x0400` onward into RAM, addressed to `BootData.start`."
  - One long sentence with a parenthetical and a participle. Break: "In SDP mode, `uuu` skips the first `0x400` bytes of the file (the ROM never reads them on USB-SDP). It uploads everything from offset `0x0400` onward to the RAM address in `BootData.start`."
- > "Yes, this is two `dd` invocations conceptually — we don't write the first 1 KB. That's intentional."
  - Confusing — only one `dd` is shown. Rewrite: "The `seek=1` means we do not write the first 1 KB. That's intentional: the ROM never reads it."
- > "On the i.MX6ULL with `BOOT_CFG` set for SD card, the ROM reads from **LBA 2** of the boot device — that is, **byte offset `0x400`** — looking for an IVT."
  - Em-dash double-clause. Rewrite: "On the i.MX6ULL with `BOOT_CFG` set for SD card, the ROM reads from **LBA 2** (byte offset `0x400`) of the boot device, looking for an IVT."
- > "This is a U-Boot image that loads to DRAM at `0x8077C000`. It must have a DCD that initialized DDR, otherwise the ROM cannot load it. That DCD lives at `0x8077042C`, which means it lives inside the image at file offset `0x42C - 0x77C000 + ...` — actually, the simpler view is that..."
  - Stops mid-arithmetic and pivots. Reads like the author thought out loud. Rewrite cleanly: "This U-Boot image loads to DRAM at `0x8077C000`. It must include a DCD, because DDR is not initialized when the ROM starts loading. The DCD lives at address `0x8077042C` *after* the image is loaded. (We will dissect DCD contents in Chapter 14.)"

### Needs more explanation
- §11.1 IVT field-by-field table is great, but the *purpose* of each field — what the ROM does with it — is not laid out anywhere. Add a paragraph: "The ROM uses `self` to know where to expect itself in memory; `boot_data` points it at start+length so it knows how much to copy; `dcd` (if non-zero) tells it to run DDR init scripts first; `entry` is the jump target after load. `csf` is the HAB signature."
- §11.2 "**`csf_addr = 0`** disables **HAB**" — HAB has been mentioned but not defined for the MCU dev. One sentence: "HAB is NXP's secure-boot mechanism. With csf_addr=0, the ROM skips signature verification and runs anything."
- §11.5 "BOOT_CFG set for SD card" — for the first-time reader, point to where these pins/fuses live. One line: "BOOT_CFG comes from the boot-mode switch on Point Atom; on production parts it can be fused via OCOTP."

## Ch12 — UART driver and printf
### AI wording / sledgehammer / buzzwords
- > "Adding the first textual output channel is a force multiplier — every later chapter in Part II spends `printf` budget freely."
  - "Force multiplier" is corporate. Rewrite: "Adding text output changes everything. Every later chapter in Part II uses `printf` freely."
- > "Both repeat across every UART implementation in the world; once you see them on i.MX6ULL, you have seen them everywhere."
  - Hyperbole + AI rhythm. Rewrite: "Both repeat across most UART implementations. After this chapter you will recognize them anywhere."
- > "The thing to read repeatedly is `uart_init()`. Every line is documented in the RM and every line is the result of someone's wasted afternoon when they skipped it."
  - Rewrite: "Read `uart_init()` carefully. Each line is in the RM, and each line costs someone an afternoon when it is skipped."
- > "**`UCR3.RXDMUXSEL = 1`** is the errata fix that I lost an afternoon to once."
  - Personal anecdote is good engineer voice. Keep.
- > "We could use a third-party tiny printf (`mpaland/printf` is excellent), and you should in real projects. For the book, we write our own minimal one — just enough to be useful, ~120 lines."
  - Em-dash. Rewrite: "You should use a third-party printf (`mpaland/printf` is excellent) in real projects. For the book we write our own, ~120 lines."
- > "After you do it once, the interrupt version is just 'the same thing, but the FIFO threshold triggers an ISR.'"
  - Fine.
- > "we have a console."
  - Fine.

### ESL readability
- > "On the Point Atom MINI these are routed to pads **UART1_TX_DATA** and **UART1_RX_DATA** in their default mux — but in i.MX naming, those pad names are aliases for specific physical pads. Per the schematic, this is the pair on the 4-pin debug header you wired up."
  - Confusing because pad name = signal name causes apparent circular wording. Rewrite: "On the Point Atom MINI these signals come out on the pads literally named UART1_TX_DATA and UART1_RX_DATA, in their reset mux (ALT0). The 4-pin debug header from Chapter 8 brings them out."
- > "Mismatched baud manifests as garbage characters that resemble valid ASCII but aren't."
  - Rewrite: "A mismatched baud rate shows up as garbage characters that look like ASCII but are not."
- > "**`UCR2.SRST`** (bit 0) — software reset; **active-low**, so we clear it to assert reset, set it to release. (Yes, polarity is confusing; per RM.)"
  - Semicolon-chained, parenthetical hedge. Rewrite: "**`UCR2.SRST`** (bit 0) — software reset, **active-low**. Clear the bit to *assert* reset; set it to release. (Yes, the polarity is unusual. That is what the RM says.)"
- > "**`UCR2.TXEN | UCR2.RXEN`** (bits 2, 1) — TX and RX enables."
  - Fine, but the bullet list mixes `|` (OR of bits) with comma-list. Either say "bits 1 and 2" or list them separately.

### Needs more explanation
- §12.2 "There's a fractional adjustment (`UFCR.RFDIV` field) that further divides f_uart_clk by 1 / 2 / 4 / etc.; we leave it at 'divide by 1' for now." — semicolon chain. Also: explain the formula one more time at the bottom with chosen values, so reader can plug-and-check: `baud = 80,000,000 / 16 * 71 / 3083 = 115,205`. Currently the chapter does the math in two steps but never writes the final verification line.
- §12.4 "UBIR must be written before UBMR. The order matters; the controller's internal divider is latched on the UBMR write. Reverse and you'll get baud rates 6.8% off..." — this is great but compressed. Add: explain what "latched" means in this context (the divider hardware samples both registers when UBMR is written; if UBIR is stale, it uses old numerator).
- §12.5 `va_arg` paragraph — "AAPCS promotes `unsigned short` and `unsigned char` to `unsigned int` when passing to a variadic function" is dropped without context. For someone who hasn't internalized varargs ABI, give one extra sentence: "Variadic args go through default argument promotion. Anything smaller than `int` is widened to `int`, and `float` is widened to `double`. So `unsigned char x; printf("%u", x);` actually passes an `unsigned int`."


---

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


---

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


---

# Part V — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining** is the dominant AI tic across every chapter. Many sentences chain two or three clauses with `—`. Half of them should be periods; some can use commas. Often two em-dashes in one sentence ("first the X — the Y — the Z").
- **"Not X — but Y" / "Not X. Y." sledgehammer** appears in chapter intros and pitfall sections (Ch31 §31.10 ld-linux gotcha, Ch33 §33.1 "That's it"). Soften.
- **Royal "we"** is heavy in Why/Focus blockquotes and chapter handoffs ("we look at", "we adopt", "we'll meet"). Reduce by 50%.
- **Numbered triplet rhythm** ("Three things X is good at: 1... 2... 3..." / "Three subdirectories you'll visit"). Used five times in Ch35 alone.
- **Buzzword "indispensable"** (Ch32 intro), "irresistible" (Ch35A), "canonical" (everywhere — fine as a technical word for `man` pages, overused as praise). "Real" / "real choice" / "real product" used as emphasis filler.
- **"For 80% of...", "For most readers' real products..."** opinion-as-fact framing is repeated. Once per chapter is enough; the book is opinionated, the reader knows.
- **Footprint number tables** in Ch33/Ch34/Ch35/Ch35A repeat the same trick. Fine, but the surrounding prose ("The cost is footprint", "The killer cost") leans on the same phrasing each time.
- **Hard concepts in the chapter intro** are stated in one breathless sentence and never revisited at depth. The Focus block is supposed to point at *the* hard idea; often it does, but the chapter body then races past it.

---

## Ch31 — Rootfs by hand

### AI wording / sledgehammer / buzzwords
- > "Chapter 29's BusyBox initramfs was a toy — one cpio file, no persistence, no real /etc."
  - Rewrite: "Chapter 29's BusyBox initramfs was a toy. One cpio file, no persistence, no real /etc."
- > "The same machinery becomes a *real* rootfs the moment you (a) populate `/etc/` with config, (b) include shared libraries so dynamically-linked tools work, (c) host it on NFS so you can iterate on user space without reflashing."
  - Rewrite: split into three sentences. The bullet-as-prose plus the inline (a)(b)(c) makes one long sentence carry too much. "It becomes a real rootfs once three things are in place. First, `/etc/` holds config. Second, the shared libraries dynamically-linked tools need are present. Third, NFS exports it so you can iterate user space without reflashing."
- > "Master these and every higher-level rootfs system (Buildroot, Yocto, Ubuntu-base) becomes "the same content, generated by tools.""
  - Rewrite: "Once you know these files, Buildroot, Yocto, and Ubuntu-base look like the same content generated by tools."
- > "This is the iteration speed that makes embedded Linux feel reasonable."
  - Rewrite: drop the bold + sledgehammer. "This is what makes embedded Linux iteration feel reasonable."
- > "**The `chmod +x` is mandatory.** Without execute permission, BusyBox init silently skips the script and you get a system with no `/proc`, no `/sys`, no `/dev/pts`. This is the #1 first-time-rootfs bug."
  - Rewrite: drop the "#1" superlative. "**The `chmod +x` matters.** Without execute permission, BusyBox init skips the script silently. No `/proc`, no `/sys`, no `/dev/pts`. This is the most common first-time-rootfs bug."

### ESL readability
- > "what can't do is real DNS over the network. If you need network DNS lookups on the target, build BusyBox *dynamically* and copy the toolchain's libraries into `~/imx6ull/rootfs/lib/`. We do both in this chapter — static for the first boot to keep things simple, then dynamic in §31.7 to enable DNS."
  - Rewrite: the §31.10 reference is wrong (text says §31.7). And the long sentence stacks two ideas. "If you need real DNS, build BusyBox dynamically and copy the toolchain libraries into the rootfs. This chapter does both: static for the first boot, dynamic in §31.10."
- > "The dynamic linker itself MUST be the real file, not a symlink."
  - Rewrite: shouting is fine once. The whole §31.10 list item using bold + caps + "dance" reads like marketing. Tone down: "The dynamic linker itself must be the real file, not a symlink."
- > "Most `.so.N` files are symlinks to `.so.N.M`. Without `-d`, `cp` follows the symlink and copies the target — making both files identical full copies. With `-d`, the symlink stays a symlink and you save space."
  - Rewrite: fine, but the em-dash should be a comma or period. "Without `-d`, `cp` follows the symlink and copies the target. Both files end up as identical full copies."

### Needs more explanation
- §31.5 inittab format: the `<id>:<runlevels>:<action>:<process>` is stated once. "For BusyBox, `<id>` is the controlling tty (empty for 'use the system default console')" — expand with one example showing how `console::respawn:-/bin/sh` parses field-by-field, and explain *what BusyBox does with the empty id vs `tty1`*. A 6 YOE MCU reader needs to picture how PID 1 picks a tty.
- §31.5 "The leading `-` on `-/bin/sh` makes it a login shell" — say *which* /etc files a login shell reads vs an interactive non-login shell, and why that matters here (PS1, PATH). One paragraph.
- §31.10 NSS: "NSS modules are dlopen'd at runtime even for 'static' binaries" — this is the hard concept. Define NSS (one line: "Name Service Switch — the glibc plug-in layer that turns `gethostbyname` / `getpwuid` into a dispatch through configurable backends like `files`, `dns`, `nis`"), show `/etc/nsswitch.conf`, point out that the `libnss_*.so` files have to exist on the target even when the program is "static".
- §31.10 INTERP: "the path the ELF binaries' INTERP section points to" — INTERP is mentioned in passing. Show one `readelf -l` snippet here, so the reader sees the actual `[Requesting program interpreter: /lib/ld-linux-armhf.so.3]` line. (Ch34 does this, but Ch31 stands alone for a reader who jumps in.)
- §31.6 devtmpfs vs mdev vs udev: the script wires both `mount -t devtmpfs` and `mdev`. The relationship isn't explained until Ch32. One sentence here: "devtmpfs creates device *nodes*; mdev handles permissions, symlinks, and hotplug rules on top."

---

## Ch32 — /proc, /sys, devtmpfs

### AI wording / sledgehammer / buzzwords
- > "Each is RAM-backed, kernel-populated, and indispensable."
  - Rewrite: drop "indispensable". "Each is RAM-backed and populated by the kernel."
- > "Knowing *which* virtual filesystem holds what, and what its file-format conventions are, is what separates "I can read tutorials" from "I can solve a problem nobody has solved before.""
  - Rewrite: cut the marketing line. "Knowing which virtual filesystem holds what is what makes the difference between following a tutorial and debugging an unfamiliar problem."
- > "Master this idiom and you can debug things without writing any code."
  - Rewrite: tone down. "Once you know this idiom, a lot of debugging needs no code."
- > "`/proc` was originally a way for `ps` to list processes."
  - Fine, but the section header "the process FS that grew" is a touch cute. Optional: "/proc — process info, plus a lot more."
- > "Diagnostic gold for "is my IRQ firing?""
  - Rewrite: drop "gold". "Useful for `is my IRQ firing?`"
- > "No code; one `cat`."
  - Sledgehammer. Either drop or use once per chapter. Here it's fine because it's earned, but the pattern (`No X; just Y.`) repeats — watch it.

### ESL readability
- > "Inside a process directory:" followed by a 12-row table where each row is "a clause". The two-column table is a list-as-prose. Fine to keep as table, but a one-sentence summary before it would help: "Each per-PID directory contains symlinks to live process state plus a handful of text files."
- > "every entry you see corresponds to *some* in-kernel data structure. Writing to a file usually invokes a kernel callback that interprets the bytes."
  - Rewrite: "Every entry corresponds to a kernel data structure. Writing to a file usually calls a kernel callback that parses the bytes."
- > "Sysfs path stability assumptions. A path like `/sys/devices/platform/2020000.serial/tty/ttymxc0/` may rename when kernel versions change. Prefer `/sys/class/tty/ttymxc0/` (the class-based view) for scripts."
  - Rewrite: combine. "Don't hard-code paths under `/sys/devices/`; they rename across kernel versions. Use `/sys/class/...` in scripts."

### Needs more explanation
- §32.4 devtmpfs vs udev vs mdev: the chapter introduces all three but only sketches the differences. Spell out the actual division of labor: kernel creates the device node (devtmpfs), userspace daemon adjusts ownership/permissions and creates symlinks (udev/mdev), userspace also fires hotplug scripts. A small diagram or three-line summary at the top of §32.4 would land it.
- §32.3 sysfs vs the device model: "every `struct device`, `struct device_driver`, `struct bus_type`, `struct class`" is listed in one sentence. For a reader who hasn't met the Linux driver model, this is opaque. Two sentences explaining what a `device` and a `driver` are in kernel terms, with the bind/probe story sketched, makes the rest of the chapter land.
- §32.2 `/proc/sys/` and sysctl: "sysctl adds value-validation and persistence support via `/etc/sysctl.conf`." Expand by one paragraph: show a `/etc/sysctl.d/` example and explain that the file is parsed at boot by either an initscript or systemd-sysctl.

---

## Ch33 — Init systems

### AI wording / sledgehammer / buzzwords
- > "PID 1 is special. The kernel will panic if it dies. Everything else that runs on your system is, ultimately, started or supervised by PID 1."
  - Rewrite: triplet-rhythm three short sentences. Keep one. "PID 1 is special: the kernel panics if it dies, and every other process on the system descends from it."
- > "the **trade-off triangle**: simplicity, capability, and footprint. BusyBox wins simplicity and footprint; systemd wins capability; sysvinit is the historical middle."
  - The triangle metaphor is fine. Semicolons should be periods: "BusyBox wins on simplicity and footprint. Systemd wins on capability. Sysvinit is the historical middle."
- > "The 600-pound gorilla."
  - Idiom. Possibly unclear to ESL. Replace: "Systemd is the giant in the room."
- > "For 80 % of i.MX6ULL-class embedded products, this is the right answer."
  - Rewrite: drop the number. "For most i.MX6ULL-class embedded products, this is the right answer."
- > "There's little niche left for sysvinit on a new design."
  - "niche left for X" is fine but slightly poetic. "Sysvinit has little reason to exist in a new design."
- > "Lennart Poettering's "Rethinking PID 1" blog post — the original systemd design rationale. Worth reading for context."
  - Fine. The "Worth reading" hedge is common across the book; consider trimming.

### ESL readability
- > "If your `respawn` lines aren't actually being reaped, you may have processes that double-fork and detach. The grandchildren get reparented to PID 1; if PID 1's `wait()` loop is correct, they're reaped automatically. BusyBox init handles this correctly out of the box. Custom PID-1 binaries often *don't*; symptom: `ps` shows growing list of `<defunct>` processes."
  - Long compound. Break: "Some daemons double-fork and detach. The grandchild then gets reparented to PID 1. If PID 1's `wait()` loop is correct, the kernel hands it the SIGCHLD and the child is reaped. BusyBox init does this correctly. Custom PID-1 binaries often forget the `wait()` loop; the symptom is `<defunct>` processes piling up in `ps`."
- > "Estimate the boot-time difference. Boot your BusyBox rootfs and note the time from `kernel_init` to login prompt (the kernel timestamps in `dmesg` are your clock). Compare with the same hardware running Ubuntu-base (Ch 35A); typical: 2-second BusyBox vs 8-second Ubuntu-base, almost all the difference being systemd."
  - Two sentences with parens and a semicolon. Break: "Boot your BusyBox rootfs and note the time from `kernel_init` to the login prompt. The `dmesg` timestamps are your clock. Now do the same on the Ubuntu-base rootfs (Ch 35A). Typical figures: ~2 s BusyBox vs ~8 s Ubuntu-base. Most of the gap is systemd."

### Needs more explanation
- §33.1 zombie reaping: "When *those* children eventually exit, PID 1 must `wait()` for them or they become zombies forever." For an ESL MCU reader, "zombie" needs a one-line explanation: "A zombie is a process that has exited but whose exit status no parent has collected yet; the kernel keeps its PID and `task_struct` alive until someone calls `wait()`."
- §33.4 cgroups: "Per-service resource limits via cgroups: `CPUQuota=`, `MemoryMax=`, `IOWeight=`." Cgroups are referenced again in Ch35C. One sentence here defining the concept (kernel feature that groups processes and applies CPU/memory/IO limits) would prevent the reader from arriving at Ch35C cold.
- §33.4 systemd targets: `multi-user.target`, `network.target` appear in the unit file with no explanation. One paragraph on what a *target* is (a synchronization point, replacing runlevels) clears up the unit example.
- §33.6 "no init at all": the kernel cmdline `init=` mechanism is mentioned but not how the kernel finds `/sbin/init` by default. Show the search order (`/sbin/init`, `/etc/init`, `/bin/init`, `/bin/sh`).

---

## Ch34 — libc, dynamic linking, and the loader

### AI wording / sledgehammer / buzzwords
- > "Embedded Linux gives you a real choice of C library, unlike a typical desktop where you get glibc and that's it."
  - Rewrite: "Embedded Linux lets you pick the C library. On a desktop you get glibc and nothing else."
- > "For embedded Linux **musl is increasingly the default**."
  - Fine claim. "Increasingly" is hedge-padding; cut.
- > "When it works it's invisible; when it breaks you get "No such file or directory" on a file that obviously exists."
  - Semicolon-as-period; idiom. "When it works it's invisible. When it breaks you get `No such file or directory` on a file that does exist."
- > "Once you've traced this sequence you can debug any "libfoo.so.X: cannot open shared object file" problem."
  - "any" is too strong. "...you can debug most `libfoo.so.X: cannot open shared object file` problems."
- > "Far more useful than guessing."
  - Cut. "Use `LD_DEBUG=libs` before guessing."

### ESL readability
- > "Mixed glibc and musl on one rootfs. glibc's SONAME is `libc.so.6` with loader `/lib/ld-linux-armhf.so.3`; musl's loader is `/lib/ld-musl-armhf.so.1` with its own libc — they have different SONAMEs and can technically coexist in separate prefixes. The real failure mode is when both expect to *own* the same `/lib/libc.so.6` symlink. Either pick one libc per rootfs, or place musl binaries under their own prefix with their own loader path baked in via `RPATH`."
  - Long. Break: "Mixing glibc and musl on one rootfs is possible but easy to get wrong. Glibc uses SONAME `libc.so.6` and loader `/lib/ld-linux-armhf.so.3`. Musl uses its own loader `/lib/ld-musl-armhf.so.1` and its own libc. They can live in separate prefixes. The failure mode is when both want to own the same `/lib/libc.so.6` symlink. Pick one libc per rootfs, or put musl binaries under their own prefix with the loader path baked in via `RPATH`."
- > "The two tables that make dynamic linking efficient."
  - Choppy fragment after a heading. Make it a full sentence: "The PLT and GOT are the two tables that make dynamic linking efficient."

### Needs more explanation
- §34.2 lazy binding: "**Subsequent calls** go directly via the GOT — fast." The mechanism is described but a reader who hasn't seen PLT/GOT before still wonders *who writes the GOT entry* on the first call. Spell out: "The first call to `puts` lands in the PLT stub. The stub jumps to a resolver routine inside ld-linux. The resolver looks `puts` up in libc's symbol table, writes the real address into the GOT slot, then jumps to `puts`. Every subsequent call reads the now-populated GOT slot directly. The PLT becomes a one-instruction jump table."
- §34.4 SONAME / `libc.so.6` vs `libc-2.31.so`: "The "6" is the ABI version; "2.31" is the implementation version." Expand: explain that `.so.6` is the SONAME the linker records in the binary at build time, that `ldconfig` builds the symlinks from real file to SONAME, and what an "ABI version bump" actually means (incompatible symbol changes, library renamed to `.so.7`).
- §34.1 static linking and glibc: the table claims static glibc "doesn't really work". Expand the *why* with the NSS mechanism: "When you write a glibc program that calls `gethostbyname`, glibc does not statically link the DNS resolver. It opens `libnss_dns.so` at runtime via `dlopen`. A statically linked glibc binary therefore needs the NSS plug-ins on disk anyway, defeating the purpose of static linking." (Ch31 hints at this; Ch34 should land it.)
- §34.6 `$ORIGIN`: explain it's a *literal string* token expanded by ld-linux, not by the shell. The pitfall already says this; the body should too.

---

## Ch35 — Buildroot

### AI wording / sledgehammer / buzzwords
- > "Buildroot does the same in 20 minutes of compile time and one menuconfig session, and on top of that adds 3000+ optional packages (Qt, alsa-utils, openssh, mosquitto, nodejs, ...)."
  - Em-dash-clause + "on top of that". Rewrite: "Buildroot does the same in twenty minutes of compile time and one menuconfig session. On top of that it offers 3000+ optional packages (Qt, alsa-utils, openssh, mosquitto, nodejs, ...)."
- > "We did Ch 31 first so you know what Buildroot is doing under the hood; now we let the tool save time."
  - Royal we + "let the tool save time". "Chapter 31 was for understanding; this chapter is for speed."
- > "Once you can navigate `output/`, debugging build failures becomes a directed search rather than a hunt."
  - "navigate" (metaphor) is on the buzzword list. "Once you know `output/`, debugging a failed build is a directed search instead of a hunt."
- > "Three things Buildroot is *good* at:" ... "Three things Buildroot is *not* good at:"
  - Triplet rhythm + matched pair. Fine once, but the chapter does it again with "Three subdirectories you'll visit" — feels formulaic.
- > "For *learning* and for *single-purpose products with simple package needs*, Buildroot is the right tool. For *commercial product lines with many variants*, Yocto is. Most engineers learn Buildroot first."
  - Italics-as-shouting plus a triplet. "Buildroot is the right tool for learning, and for single-purpose products with simple package needs. Yocto is the right tool for commercial product lines with many variants. Most engineers learn Buildroot first."
- > "The hand-built path was for *understanding*. Buildroot is for *production work*. From this chapter on, we use Buildroot."
  - "This isn't X. This is Y." pattern. "The hand-built path taught the structure. Buildroot is what you ship. The rest of the book uses Buildroot."

### ESL readability
- > "The defconfig also enabled `BR2_TARGET_UBOOT` and `BR2_LINUX_KERNEL`, which we'll often turn off if we want to build only the rootfs."
  - "if we want to" is wordy. "The defconfig enables `BR2_TARGET_UBOOT` and `BR2_LINUX_KERNEL`. Turn both off when you only need the rootfs."
- > "Modifying files under `output/target/` directly. They will be overwritten the next time `make` runs. Use overlay or post-build scripts."
  - The fragment "Modifying files under `output/target/` directly." is a pitfall header style. ESL-fine; consistent with the rest of the pitfall list. Leave it but be aware the whole pitfalls section uses noun-phrase headers + explanation, which reads less naturally than full-sentence pitfalls.

### Needs more explanation
- §35.1 Kconfig: "One Kconfig tree describes ~3000 packages." Kconfig is mentioned without explanation. A reader who hasn't built a kernel might not know what Kconfig *is*. One sentence: "Kconfig is the same configuration system Linux uses — a declarative language for `bool/string/int` options with dependencies."
- §35.7 `BR2_ROOTFS_OVERLAY`: explain that "overlay" here is *not* overlayfs (the kernel feature of Ch35B). It's a build-time file copy. The terminology collision is confusing.
- §35.7 the custom package's `$(eval $(generic-package))`: this is the heart of Buildroot's package system but is presented as one magic line. One paragraph on the rule template would help. (Acknowledge that the full story is in `docs/manual/`.)
- §35.6 cross-compile: the user types `make` and a cross-compile happens. Worth one sentence explaining that Buildroot builds its own toolchain to `output/host/` and uses *that* for every package — so the host's gcc doesn't matter.

---

## Ch35A — Ubuntu-base

### AI wording / sledgehammer / buzzwords
- > "Not Ubuntu-the-distro with GNOME — that's too heavy. We use **Ubuntu-base**..."
  - "Not X — Y" sledgehammer. Rewrite: "Ubuntu-the-distro with GNOME is too heavy. We use **Ubuntu-base** instead..."
- > "The killer feature: **`apt install <anything>`**..."
  - "killer feature" / "killer cost" pair. ESL-borderline (gamer/marketing idiom). "The headline feature is `apt install <anything>`...". "The headline cost is..."
- > "The trick is invisible to `apt-get` and makes the whole workflow possible."
  - "the whole workflow possible" is sledgehammer. "Apt-get doesn't notice and the workflow works."
- > "Engineers who use `apt-get install` daily on their dev machines get the same workflow on the target."
  - Fine, but the *whole intro* is selling the choice. Trim one sentence.
- > "A full Ubuntu shell. `apt install` works ... `python3` is there. Every command you're used to is there."
  - Triplet rhythm of short declarative sentences. Keep one or two: "A full Ubuntu shell. `apt install` works, `python3` is there, every command you're used to is there."

### ESL readability
- > "`qemu-user-static` is a CPU emulator that runs *one ARM binary at a time* on your x86_64 host. `binfmt-support` registers it with the kernel so that when the kernel sees `exec("/usr/bin/ls")` and `ls` is an ARM binary, it transparently runs `qemu-arm-static /usr/bin/ls` instead."
  - Long; the second sentence has three clauses. Break: "`qemu-user-static` runs one ARM binary at a time on your x86_64 host. `binfmt-support` registers it with the kernel via `binfmt_misc`. When the kernel sees `exec` of an ARM ELF, it transparently invokes `qemu-arm-static` to run it."
- > "For users in China who find the official mirrors slow, the Tsinghua or USTC mirror is much faster:"
  - Fine. Reader-targeted; keep.

### Needs more explanation
- §35A.3 `binfmt_misc`: the mechanism is referenced but not named. Worth one paragraph: `/proc/sys/fs/binfmt_misc/` is a kernel feature that registers a magic-bytes pattern to an interpreter. `binfmt-support` writes entries for every QEMU userland binary. The reader who has never met `binfmt_misc` is the one who later debugs "I copied qemu but exec still says Exec format error."
- §35A.5 systemd inside chroot: "`systemctl` here just creates a symlink — it doesn't actually start anything (we're in a chroot)." Why doesn't it work? Two-line explanation: systemctl talks to systemd over dbus; in a chroot systemd isn't running, so it falls back to filesystem-only operations (enable creates the wants/ symlink, start would fail).
- §35A.2 LTS support windows: the dates are stated as fact. A line about *what* ESM (Extended Security Maintenance) actually is — a paid Ubuntu Pro subscription, free for personal use — clarifies whether the dates apply.

---

## Ch35B — Read-only rootfs + overlayfs

### AI wording / sledgehammer / buzzwords
- > "End result: the system can lose power at any instant without corrupting its rootfs."
  - "End result" is a writer's tic. "The result: power can drop at any instant without corrupting the rootfs."
- > "the **three-tier model** — `lowerdir` (immutable rootfs), `upperdir` (where changes accumulate), `workdir` (overlay's scratch space). Once you understand those three, every overlayfs setup follows the same shape."
  - Fine. Em-dash is acceptable here (definition list). Maybe drop "the same shape" cliché.
- > "Anyone who has shipped a product in the field has stories about devices that came back from customers with corrupted rootfs after a power glitch."
  - Slightly anecdotal-marketing. Tighten: "Every team that has shipped a product has at least one corrupted-rootfs story from a power glitch in the field."
- > "Trivially defeats everything. Always verify with `mount | head -1` after boot."
  - Fragment + sledgehammer. "Without `ro` in `bootargs` the whole scheme is defeated. Verify with `mount | head -1` after boot."

### ESL readability
- > "If power dies between the buffer-add and the flush, you have:"
  - "buffer-add" is jargon and an unusual compound. "If power drops between the page-cache write and the disk flush, you can end up with:"
- > "Over 1000 power cycles, the difference is overwhelming."
  - "overwhelming" is rhetorical. "Over a thousand power cycles, the difference is large enough to count."

### Needs more explanation
- §35B.1 page cache: "The kernel buffers writes in its page cache and flushes them to disk lazily." For a reader who hasn't met the page cache, expand by one paragraph: writes hit the page cache immediately, are marked dirty, and a background `writeback` thread flushes them later. `sync(2)` forces it. Mention that ext4's journal protects metadata, not data, by default — this is precisely why partial data writes can happen.
- §35B.4 overlay copy-up: "overlayfs copies `/etc/hostname` from `lowerdir` to `upperdir` ("copy-up"), then applies the write." Explain that copy-up is *per-file*, so the upper grows file-by-file rather than mirroring the whole lower; mention the cost of copying a large file just to change one byte.
- §35B.4 pivot_root: the script uses `pivot_root` but the kernel mechanism isn't explained. One paragraph: `pivot_root(new_root, put_old)` swaps the kernel's idea of `/`; the old root becomes a regular mount; init then runs in the new root. Compare with `chroot` (only changes the calling process's view; PID 1 still sees the original root).
- §35B.4 the bind-mount + pivot dance: this script is the most complex in Part V. A small diagram showing "before pivot" vs "after pivot" trees would land it.

---

## Ch35C — Containers on embedded

### AI wording / sledgehammer / buzzwords
- > "Modern embedded products increasingly separate "the base system" ... from "the application" ..."
  - "increasingly" is hedge filler.
- > "the benefit is a deployment story that scales from one device to one million."
  - "from one to one million" is marketing prose. "...one device or a fleet of a million."
- > "**the three kernel features that make containers work** — namespaces (process isolation), cgroups (resource limits), and overlayfs (storage). All three are in mainline Linux for years; you just need them turned on in `.config`."
  - Triplet + semicolon. "Three kernel features make containers work: namespaces (process isolation), cgroups (resource limits), and overlayfs (storage). All three have been in mainline Linux for years. You just need them turned on in `.config`."
- > "That's it. There is no "container runtime" magic — just a process with namespaces, cgroups, and a careful mount setup. **Docker, Podman, containerd, and CRI-O all do the same thing**; they differ in UI, daemons (or lack of), and ecosystem."
  - "That's it" + bold all-caps-energy. Tone down: "There is no container-runtime magic. A container is a process with namespaces, cgroups, and a careful mount setup. Docker, Podman, containerd, and CRI-O all do the same thing. They differ in UI, daemons, and ecosystem."
- > "For dynamic product lines that update frequently, containers earn their cost."
  - "earn their cost" is fine but the whole "When *not* to use" section is rhetorical pair-up. Cut one sentence.

### ESL readability
- > "A "container" is just a Linux process group with three things layered on:"
  - "layered on" + the triplet that follows. Acceptable but mark the pattern.
- > "The container thinks it's a complete Alpine system."
  - Anthropomorphism. ESL-borderline. "From inside, it looks like a complete Alpine system."

### Needs more explanation
- §35C.2 namespaces: each type is listed in one breath ("PID, network, mount, UTS, IPC, user, cgroup"). A reader who has never used `unshare` needs the picture. For each, one line: "PID namespace: the container's first process is PID 1 inside, even though the host sees it as PID 14523. Mount namespace: mount/unmount inside the container does not affect the host." A small table would do.
- §35C.2 cgroups v1 vs v2: pitfalls section mentions both. The body should say what cgroup v2 is (unified hierarchy, replacing the per-controller mount points of v1), why it matters (Podman 4.x assumes v2), and how to tell which one is in use (`mount | grep cgroup`).
- §35C.2 user namespace + UID mapping: the pitfalls section says "the correct fix is `--user 0:0` plus careful capability grants" but the body never explains what subuid/subgid maps are. A short paragraph: "Rootless Podman uses a range of subordinate UIDs (listed in `/etc/subuid`) that the kernel maps to a different range inside the user namespace. UID 0 inside the container is UID 100000 on the host, etc."
- §35C.3 `CONFIG_OVERLAY_FS`: link back to Ch35B explicitly. A reader who skipped Ch35B will think overlayfs is unique to containers.


---

# Part VIa — Style/ESL Review

## Cross-cutting patterns

- **Em-dash overload, still the book's signature tic.** Driver chapters lean on " — " to glue clauses, often three times per paragraph. Many should be periods (a few examples flagged per chapter; the pattern is everywhere).
- **Semicolon-glued clauses.** Less than Parts II–V but still frequent in `Pitfalls` bullets ("X happens; Y is the fix"). Period reads better for ESL.
- **"Not X — but Y" / "Not X, it's Y" cadence.** Ch36, Ch37, Ch41, Ch46 all reach for it. Trim.
- **AI-buzzword hits**: `crucial`, `essential`, `comprehensive` are mostly absent (good), but `internalise/internalize`, `mechanical` (used as praise: "the API choice is mechanical"), `canonical`, and `idiomatic` appear over and over. Vary or drop.
- **Triplet rhythm.** "Sleep, mutex, copy_to_user — all fine." / "Three players:" / "Three questions, one primitive." Rhythmic but reads AI-generated when repeated within one chapter.
- **Royal "we'll/let's" overuse.** "Let's pull apart the four interesting pieces." / "Let's see them in action." / "Let's write the world's simplest..." Replace half with imperative ("Walk through the four interesting pieces.") or drop.
- **"That's it." / "That's the whole pattern." / "That's the whole API."** Used as a sentence at least once per chapter. Pick one or two per part, drop the rest.
- **Cliché phrases.** "the workhorse bus of embedded" (Ch46), "the kernel's cleverest tricks" (Ch41), "the right starting point" (Ch40), "a masterclass" (Ch48). All marketing-flavor; cut.

## Ch36 — Your first kernel module

### AI wording / sledgehammer / buzzwords
- > "A kernel module isn't a program. It's a **library that the kernel dynamically links into itself.**"
  - "Not X. It's Y." sledgehammer. Rewrite: "A kernel module is a library that the kernel dynamically links into itself."
- > "This isn't merely a coding-style change. It changes the failure modes too."
  - Same pattern, paragraph later. Rewrite: "This is more than a coding-style change. The failure modes change too."
- > "Twenty-some lines. Let's go through each."
  - "Twenty-some" is informal English and odd for ESL. Rewrite: "About twenty lines. Walk through each."
- > "The kernel build system (Kbuild) is invasive — it generates per-module ELF sections, applies the kernel's own `CFLAGS`..."
  - "Invasive" has negative tone. Em-dash glue. Rewrite: "Kbuild does a lot of work for you. It generates per-module ELF sections, applies the kernel's own `CFLAGS`..."
- > "**Mismatch = refused load.**"
  - Cute but parses oddly for ESL. Rewrite: "If they differ, the load is refused."
- > "Crank it up:"
  - Idiomatic. Rewrite: "Raise it:"
- > "Useful for debugging; spammy in production."
  - Semicolon glue + "spammy" is slang. Rewrite: "Useful for debugging. Noisy in production."

### ESL readability
- > "Your code is sitting passive — invoked from system calls, interrupts, work queues, kthreads, whatever subsystem you've hooked into."
  - "Sitting passive" is awkward English; "whatever subsystem you've hooked into" is idiomatic. Rewrite: "Your code waits, then runs when something calls into it — a system call, an interrupt, a work queue, a kthread, or whichever subsystem registered it."
- > "A wild pointer in firmware corrupts your `.bss`. A wild pointer in a kernel module corrupts *the kernel*, and the kernel is whatever is currently running — kernel threads, other drivers, the scheduler."
  - 36-word sentence with em-dash mid-clause. Break: "A wild pointer in firmware corrupts your `.bss`. A wild pointer in a kernel module corrupts the kernel itself. That can mean kernel threads, other drivers, or the scheduler — whatever happens to be running."
- > "Without it, the loader can't find your code."
  - Fine; keep.

### Needs more depth
- §36.2 `GFP_KERNEL` / `GFP_ATOMIC` are referenced under `kmalloc` in the MCU table without explanation. The first time `GFP_KERNEL` actually appears in code (Ch37) it is also not explained. Add one paragraph here or in Ch37 §37.4 introducing the flag family: "`GFP_*` flags tell the allocator how hard it can work. `GFP_KERNEL` may sleep waiting for memory reclaim — fine in process context. `GFP_ATOMIC` never sleeps but may fail when memory is tight — required in IRQ context. There are a dozen more; these two cover 95% of driver code."

## Ch37 — A character driver, by hand

### AI wording / sledgehammer / buzzwords
- > "What the user *thinks* they're doing — 'writing to a file' — is whatever your `write` callback chooses to do. Send bytes over UART. Set GPIO pins. Allocate buffers. Cache and return on next read."
  - Triplet-plus-bonus rhythm reads AI. Trim to: "What the user thinks is 'writing to a file' is whatever your `write` callback decides to do — send UART bytes, toggle GPIOs, fill a buffer for next read."
- > "The 'file' abstraction is a façade; you decide what's behind it."
  - "Façade" is poetic; semicolon glue. Rewrite: "The 'file' is a façade. You decide what's behind it." (Or drop "façade" entirely: "The 'file' is just an interface — you decide what's behind it.")
- > "Years ago you'd pick 'an unused major'... Now we ask the kernel:"
  - "Years ago / Now we" rhetorical setup. Rewrite: "The old way was to pick an unused major from a documented list. The modern way is to ask the kernel for one:"
- > "Hard-coding majors was a 1990s pattern and is now actively discouraged."
  - "Actively discouraged" is corporate. Rewrite: "Hard-coding majors is a 1990s pattern. Don't do it."
- > "It's the most readable way to handle error paths in C — far better than nested `if`s. New kernel-module authors find it strange for an afternoon, then can't imagine writing it any other way."
  - Preachy. Rewrite: "It is the kernel's idiomatic error-path style. After a dozen drivers it becomes natural."
- > "There's never a reason to bypass `copy_to/from_user`."
  - Absolute. Rewrite: "Don't bypass `copy_to/from_user`."

### ESL readability
- > "On i.MX6ULL with no MMU domain protection it might *appear* to work — but only when the user buffer happens to be paged in and accessible from kernel mode, which is not always the case."
  - 35 words, two clauses. Break: "On i.MX6ULL there is no MMU domain protection, so a direct dereference might *appear* to work. But it only works when the user buffer is paged in and reachable from kernel mode — not always the case."
- > "Multiple `cat`s in a row read the same 5 bytes each time — because our `read` checks `*ppos >= buf_len` and signals EOF appropriately, then `cat` reopens and starts from `*ppos = 0` next time."
  - 35-word run-on; tense slippage between "next time" and "in a row." Rewrite: "Each new `cat` invocation gets a fresh open, so `*ppos` resets to 0. Within one `cat`, the first `read` returns 5 bytes and the second returns 0 (EOF)."
- > "The pair `cdev_init` + `cdev_add` is conceptually one step that the kernel splits to make initialization-time vs. registration-time allocation distinguishable; you treat it as two lines next to each other."
  - 30-word sentence, semicolon glue, dense vocabulary ("distinguishable"). Rewrite: "`cdev_init` and `cdev_add` are really one logical step. The kernel splits them so it can tell apart initialization from registration. Treat them as two lines next to each other."

### Needs more depth
- §37.4 Idea 1 (`container_of`): explained as "a compile-time trick — no runtime cost." For an MCU reader who has never seen `offsetof`-based parent recovery, this is too thin. Add a 4-line diagram showing the struct layout, the inner cdev pointer, and the pointer-subtract that recovers the outer `hello_dev *`.
- §37.4 Idea 2 (`__user`): the section explains *what* `copy_to_user` does (validate, fault-handle, return uncopied count) but does not explain *why* it cannot be a memcpy. For an MCU reader with no MMU experience, add one sentence: "User-space lives in a separate virtual address space, and the page may not be mapped right now — `copy_to_user` brings it in if needed."
- §37.4 Idea 3 (`mutex_lock_interruptible`): "if a signal is pending while we wait for the lock, `_interruptible` returns `-ERESTARTSYS`" — first mention of signals in driver context for an MCU reader. Add one sentence linking to a familiar idea: "Linux signals are roughly the user-space equivalent of IRQ-driven async events; `Ctrl-C` from the terminal sends SIGINT to the foreground process. `_interruptible` means our wait can be aborted by such a signal."

## Ch38 — Auto-creating /dev nodes

### AI wording / sledgehammer / buzzwords
- > "This is profoundly different from how you might imagine it."
  - "Profoundly" is overdone. Rewrite: "This is different from how you might imagine it."
- > "The kernel does **not** maintain `/dev/`. The kernel publishes events; user-space chooses what to do with them."
  - Sledgehammer + semicolon. Rewrite: "The kernel does not maintain `/dev/`. It publishes events. User-space decides what to do with them."
- > "Take the driver from Chapter 37 and add three lines."
  - It is actually more than three lines (struct fields, init lines, exit lines, cleanup labels). Rewrite: "Take the Ch 37 driver and add a class, a device, and matching cleanup — about a dozen lines."
- > "No `mknod` step. The file appears at load and disappears at unload."
  - Two-sentence reveal; fine, keep.
- > "(`echo add > uevent` re-triggers — useful for replaying events on a system that booted before udev was running.)"
  - Useful info buried in parentheses. Move out: "Writing `echo add > uevent` re-triggers the event. This is useful for replaying events on a system that booted before udev was running."

### ESL readability
- > "Conceptually, a *class* is a group of devices that share a role (LED, RTC, GPIO chip, network interface, sound card). The class directory becomes a namespace under which individual devices live."
  - "Becomes a namespace under which X live" is dense. Rewrite: "A *class* is a group of devices that share a role — LED, RTC, GPIO chip, network interface, sound card. The class directory holds one entry per device in that group."
- > "Drivers that *do* fit (an LED driver belongs in `leds`, an RTC in `rtc`) skip class creation and register with the **subsystem** framework instead (Ch 44–48 cover those frameworks one by one)."
  - 32-word sentence, two parentheticals. Break: "Drivers that fit an existing class skip `class_create` and register with the subsystem framework directly. For example, an LED driver belongs in `leds` and an RTC in `rtc`. Ch 44–48 cover these subsystems."

### Needs more depth
- §38.3 first sentence on `class_create` describes its function but never explains *why* the kernel has both classes (a sysfs hierarchy) and bus types (`platform`, `i2c`, `spi`). For the MCU reader this is the first hint of the device-model split. One sentence: "Classes group devices by *role*; buses group them by *how the CPU reaches them*. A single device belongs to one bus and one class."
- §38.6 `sysfs_emit` — introduced in passing ("bounds-checked since 5.10; prefer over sprintf") with no explanation of *why* a custom sprintf exists at all. One sentence: "`sysfs_emit` is `sprintf` for sysfs callbacks; it checks that you don't write past PAGE_SIZE, which is the kernel's hard cap for any sysfs read."

## Ch39 — Platform drivers + device tree

### AI wording / sledgehammer / buzzwords
- > "Almost everything on an i.MX6ULL is platform: GPIO blocks, UARTs, I²C controllers (the controllers themselves; the *devices on them* are I²C-bus children), SPI controllers, PWM, ADC, timers, FlexCAN, Ethernet MAC, USB OTG controllers, LCDIF, eCSPI, etc."
  - 42-word bulleted-as-prose sentence. Rewrite: "Almost everything on i.MX6ULL is a platform device: GPIO blocks, UARTs, I²C/SPI/eCSPI controllers, PWM, ADC, timers, FlexCAN, Ethernet MAC, USB OTG, LCDIF. (The devices on an I²C bus are I²C-bus children, not platform devices.)"
- > "That's the whole template. Let's pull apart the four interesting pieces."
  - "That's the whole" cliché + "let's" royal we. Rewrite: "That is the full template. Look at the four pieces that matter."
- > "This is the biggest stylistic win in modern kernel code."
  - "Stylistic win" is corporate. Rewrite: "`devm_*` is the biggest readability gain in modern kernel code."
- > "Always prefer it to `dev_err(...) + return -EINVAL;`."
  - Fine; keep.
- > "Useful in development: re-probe a device after fixing a hardware glitch, without rebooting. Also useful in production for power-saving (unbind unused hardware to drop its clocks)."
  - Two "Useful X:" fragments back to back. Rewrite: "Useful in development for re-probing a device after a hardware glitch, without a reboot. Also useful in production: unbind unused hardware to drop its clocks."

### ESL readability
- > "It exists solely to give the driver/device model something to attach to. When the kernel parses the DT at boot, every node whose parent has no `compatible` for a real bus (i.e., everything directly under the SoC node) becomes a platform device."
  - The "every node whose parent has no `compatible` for a real bus" clause is heavy. Break: "It exists only to give the device model something to attach to. At boot, every DT node whose parent does not name a real bus becomes a platform device. In practice that means everything directly under the SoC node."

### Needs more depth
- §39.3 Piece A: `MODULE_DEVICE_TABLE(of, ...)` is explained as "exposes the table to depmod" but the reader has not yet seen what `depmod` does. One sentence: "`depmod` is the tool (run at module-install time) that scans every `.ko` for its `MODULE_DEVICE_TABLE` entries and writes them to `/lib/modules/*/modules.alias`. `modprobe` consults this alias file to find which `.ko` matches a given DT compatible."
- §39.7 `EPROBE_DEFER` mechanism is mentioned but never explained at a system level — the reader might wonder how the kernel knows when to retry. One paragraph: "The kernel keeps a list of devices whose probe returned `-EPROBE_DEFER`. Every time a *new* device successfully probes (which may have provided the missing resource), the kernel re-tries the deferred list. After a few seconds with no progress, deferral times out and the device is logged as never-bound."
- §39.7 shutdown vs remove: "shutdown() runs in atomic context — keep it short." Surprising claim for someone new to PM; deserves a sentence about why ("system is on the way down; scheduler may not be available; you have milliseconds before power is cut").

## Ch40 — The misc framework

### AI wording / sledgehammer / buzzwords
- > "For simple character devices that don't fit a standard subsystem, this is the right starting point."
  - "The right starting point" is consultant-speak. Rewrite: "Use it for simple character devices that don't fit a standard subsystem."
- > "Knowing when to reach for it saves real effort."
  - Idiomatic ("reach for it") and vague ("real effort"). Rewrite: "Knowing when to use it saves you the chardev boilerplate."
- > "For the in-between cases — 'simple chardev, one or two instances, no existing framework' — misc is perfect."
  - "Perfect" is marketing. Rewrite: "For these in-between cases — simple chardev, one or two instances, no matching framework — misc fits."
- > "Two functions. That's the whole API."
  - "That's the whole API" again. Rewrite: "Two functions. The full API."
- > "Six lines to register, one to deregister."
  - Fine; keep.

### ESL readability
- > "**`miscdevice` struct must outlive the registration.** Don't put it on the stack of `init()`. Make it `static` (as in the example) or allocate it from `kmalloc`. The misc layer holds a pointer to your struct."
  - Four sentences for one idea. Tighten: "**`miscdevice` must outlive the registration**, because the misc layer holds a pointer to it. Don't put it on the stack of `init()` — make it `static` or allocate it with `kmalloc`."

### Needs more depth
- §40.1 first bullet "you need a chardev for a single device (or a small fixed number)" without quantifying. The reader is left wondering "what's small." Add one sentence: "Misc has a finite pool of dynamic minors (~150); for hundreds of instances, use a chardev with your own major."

## Ch41 — Concurrency in the kernel

### AI wording / sledgehammer / buzzwords
- > "Pick the wrong primitive and you get the wrong of two failure modes: a silent data-corruption race, or a lockup so deep that `dmesg` can't tell you what happened."
  - "The wrong of two failure modes" is awkward phrasing. Rewrite: "Pick the wrong primitive and you hit one of two failure modes: a silent data-corruption race, or a lockup so deep that `dmesg` cannot tell you what happened."
- > "Concurrency is the rule, not the exception."
  - Cliché. Rewrite: "Concurrency is the default. Every shared variable needs a plan."
- > "Three questions. Answer them and you've picked your primitive."
  - Triplet-rhythm reveal. Fine once; trim sibling triplets nearby.
- > "Read-Copy-Update is one of the kernel's cleverest tricks."
  - "Cleverest tricks" is fan-prose. Rewrite: "Read-Copy-Update is the kernel's read-mostly trick: readers pay zero synchronization cost."
- > "RCU is heavy machinery; you wouldn't use it for a simple counter. But for 'lookup-then-use' data structures read on every packet, it's revolutionary..."
  - "Revolutionary" is marketing. Rewrite: "RCU is heavy machinery — not for a simple counter. But for 'lookup-then-use' data on every packet, it is dramatically faster than any lock."
- > "Per-CPU data is brilliant when reads are rare relative to writes (the opposite of RCU's sweet spot)."
  - "Brilliant" + "sweet spot" both idiomatic. Rewrite: "Per-CPU data works well when reads are rare relative to writes (the opposite of RCU's case)."
- > "Worth turning on. Worth keeping on through development. Then disable for production."
  - Triplet. Rewrite: "Turn it on during development. Disable for production."

### ESL readability
- > "While you hold a spinlock, the holding CPU has IRQs disabled (in the IRQ-safe variant) and the kernel won't preempt the current task."
  - "The holding CPU has IRQs disabled (in the IRQ-safe variant) and..." reads as a parenthetical mid-clause. Rewrite: "While you hold a spinlock, the kernel will not preempt the current task. In the IRQ-safe variant, IRQs are disabled on the holding CPU too."
- > "When it triggers, you get a wall of dmesg output with two stack traces (acquire path 1 vs acquire path 2) and a verdict like 'deadlock possible.' Read it carefully — it tells you exactly which locks, in which order, and from which functions."
  - 40-word sentence. Break: "When it triggers, you get a wall of dmesg output. Two stack traces, one per lock acquisition path, and a verdict like 'deadlock possible.' Read it carefully — it tells you which locks, in which order, from which functions."

### Needs more depth
- §41.4 "the CPU's atomic-instruction support (ldrex/strex on ARM)" — most MCU devs have never used `ldrex/strex`. One sentence: "These are ARM's load-exclusive / store-exclusive instructions: load with a reservation, store only if the reservation is still intact. Failure means another CPU touched the address; retry."
- §41.7 RCU section: the example uses `rcu_dereference_protected` with `lockdep_is_held(&write_lock)` but `write_lock` is never defined. The reader sees a magic identifier. Either define it inline or note that writers must also serialize among themselves via some other lock.

## Ch42 — Sleeping, waiting, polling

### AI wording / sledgehammer / buzzwords
- > "Every driver that produces data on its own schedule — UART, keyboard, sensor, network — needs a way to make a reader wait without polling."
  - Bullet-as-prose. Rewrite: "Drivers that produce data on their own schedule (UART, keyboard, sensor, network) need a way to make a reader wait without polling."
- > "Wait queues are how Linux makes blocking I/O efficient: the thread sleeps, the scheduler runs something else, and an interrupt or timer wakes the thread exactly when its data is ready."
  - 35-word run-on. Break: "Wait queues are how Linux makes blocking I/O efficient. The thread sleeps. The scheduler runs something else. An interrupt or timer wakes the thread when its data is ready."
- > "Get this dance right and your driver's blocking I/O is correct; get it wrong and you have a 'sometimes the read just hangs forever' bug."
  - "Get this dance right" idiom + semicolon glue. Rewrite: "Get the sequence right and your driver's blocking I/O is correct. Get it wrong and reads sometimes hang forever."
- > "Never use the uninterruptible variants — a stuck driver with uninterruptible waiters is the classic D-state hang that takes the system down with it."
  - "Takes the system down with it" is informal. Rewrite: "Never use the uninterruptible variants. A stuck driver with uninterruptible waiters is the classic D-state hang — the user cannot kill the process; only a reboot fixes it."
- > "`O_NONBLOCK` is a per-open flag. The user can also flip it later via `fcntl(fd, F_SETFL, O_NONBLOCK)`. Always honor it."
  - "Flip it" + "honor it" both idiomatic. Rewrite: "`O_NONBLOCK` is a per-open flag. The user can change it later via `fcntl(fd, F_SETFL, O_NONBLOCK)`. Always check it."

### ESL readability
- > "`poll_wait` after returning the mask. The order is: register first (`poll_wait`), then return the mask. Reverse it and the kernel may register no wait at all, leading to busy-looping in `select`."
  - Pitfall headline reads backwards from the explanation. Rewrite the headline: "**`poll_wait` called after returning the mask.** Order matters: register the wait first, then return the mask. Reverse it and the kernel may register no wait, so `select` busy-loops."

### Needs more depth
- §42.2 "This loop is what prevents the 'lost wakeup' race" — names the race but does not explain it. For someone seeing wait queues for the first time, this is a real conceptual gap. Add a small race diagram: producer sets condition → wake_up → meanwhile reader checks condition (false, racing) → reader sleeps → no future wake → forever. Then show how `wait_event_*` sequencing avoids it (set state TASK_INTERRUPTIBLE *before* the final check, so any wake sets us runnable even if we are about to schedule).
- §42.6 task states list is dense. Add a sentence on `TASK_RUNNING` to clarify: "`TASK_RUNNING` does not mean 'on a CPU right now'; it means 'eligible to run.' The scheduler picks one runnable task per CPU at a time."

## Ch43 — Interrupts

### AI wording / sledgehammer / buzzwords
- > "Get the IRQ-handler design wrong and you cause one of two failures — *missed interrupts* (handler too slow or wrong polarity) or *IRQ storms* (handler doesn't acknowledge, hardware re-asserts continuously, system locks up). The right design is mechanical once you know the rules."
  - "The right design is mechanical" again. Rewrite: "Get the IRQ-handler design wrong and you hit one of two failures: *missed interrupts* (handler too slow or wrong polarity) or *IRQ storms* (handler does not acknowledge, hardware re-asserts continuously, system hangs). The rules below give you the right design every time."
- > "Internalise this constraint and the API choices for the rest of this chapter make obvious sense."
  - "Internalise" + "make obvious sense" both AI-flavored. Rewrite: "Once you accept this constraint, the API choices below follow naturally."
- > "Five lines of real work. Read status, ack, snapshot, defer, return. Under 1 µs on i.MX6ULL."
  - Triplet + fragment. Fine for emphasis once, but the next paragraph also opens with a triplet — vary.
- > "**Use threaded IRQ for ~80% of new driver code.** It's the cleanest model."
  - "Cleanest model" is marketing. Rewrite: "**Use threaded IRQ for most new driver code.** It is the simplest correct pattern."

### ESL readability
- > "The DT says `interrupts = <0 99 IRQ_TYPE_LEVEL_HIGH>` — that's the GIC's hardware number. The kernel maps it to a virtual IRQ (`virq`) at boot time, then your `request_irq` uses the virq. You usually don't see the conversion — the framework hands you the virq directly."
  - Three sentences with two em-dash chains. Rewrite: "The DT line `interrupts = <0 99 IRQ_TYPE_LEVEL_HIGH>` carries the GIC hardware number. At boot, the kernel maps it to a virtual IRQ (a *virq*). Your `request_irq` uses this virq. You usually do not see the mapping happen — the framework hands you the virq."
- > "The `IRQF_ONESHOT` flag is important: it keeps the IRQ masked from when the primary returns `IRQ_WAKE_THREAD` until the threaded handler completes. Without it, the IRQ could re-fire and re-schedule before you've finished processing."
  - Two long sentences with technical content. Keep but split the first: "`IRQF_ONESHOT` is important. It keeps the IRQ masked from when the primary returns `IRQ_WAKE_THREAD` until the threaded handler finishes. Without it, the IRQ can re-fire and re-schedule before you have finished processing."
- > "Don't `mdelay` more than ~10 ms; that's bad on a single-core system."
  - "That's bad" is vague. Rewrite: "Do not `mdelay` more than ~10 ms — you stall every other task on a single-core system."

### Needs more depth
- §43.2 top-half contract bullet "It runs with kernel preemption off" — first mention of kernel preemption in any handler context. One sentence: "Preemption is the kernel's right to swap out a running task for a higher-priority one; while it is off, your code keeps the CPU until it voluntarily yields."
- §43.4.1 threaded IRQ: the section says the threaded fn "runs as a kernel thread that runs with normal kernel context — can sleep." The reader needs to know that this kthread is dedicated to *this IRQ* — its name appears in `ps` as `irq/<n>-<name>`. One sentence helps debugging later.
- §43.6 shared IRQs example references a `dev_id` cookie that has not been re-introduced since §43.3. One sentence: "Remember `dev_id` is the void-pointer cookie you passed to `request_irq`; each handler on a shared line gets it back as its second argument and uses it to find its private state."

## Ch44 — GPIO subsystem + pinctrl

### AI wording / sledgehammer / buzzwords
- > "Once you internalise that — and stop thinking in 'GPIO numbers' — every GPIO-using driver in Linux reads the same way."
  - "Internalise" again. Rewrite: "Once you accept that — and stop thinking in 'GPIO numbers' — every GPIO-using driver in Linux looks the same."
- > "The two-step model is a Linux invariant"
  - "Linux invariant" sounds formal/jargon. Rewrite: "The two-step model is fixed across Linux."
- > "Build, load. Press the button: LED toggles. ~90 lines of driver, zero MMIO writes, fully portable to any SoC with a `compatible` Linux GPIO controller."
  - Marketing pitch. Rewrite: "Build, load, press the button: the LED toggles. About 90 lines, zero MMIO writes, portable to any SoC with a Linux GPIO driver."
- > "If you forget step 1 — leave the pin in its default UART function — step 2 reads garbage and your driver thinks the button is always pressed."
  - Em-dash glue. Fine; keep — useful concrete example.

### ESL readability
- > "Pin is still in its default mux (e.g., UART). `gpiod_get` succeeds (the GPIO controller doesn't know the pin is muxed elsewhere) but the GPIO seems 'stuck' — because reads/writes hit the GPIO register, but the IOMUX routes the pin to UART."
  - 40-word sentence with two parentheticals and an em-dash. Break: "Pin is still in its default mux (for example, UART). `gpiod_get` succeeds — the GPIO controller has no idea the pin is muxed elsewhere. But the GPIO seems 'stuck': reads and writes hit the GPIO register, while the IOMUX routes the pin to UART."
- > "Don't hog a pin that a driver will claim; the driver's `pinctrl_select_state` will fail. Hog only 'ownerless' pins."
  - Semicolon glue. Rewrite: "Don't hog a pin that a driver will claim. The driver's `pinctrl_select_state` will fail. Hog only ownerless pins."

### Needs more depth
- §44.2 the `0x17059` magic value is mentioned and decoded ("pull-up enabled, fast speed, drive strength = 40 Ω, etc.") but the *bit layout* of that 32-bit word is never shown. The MCU reader is used to "bit 5 = pull-up, bits 6-7 = drive strength" tables and will want one. A small ASCII table of the IOMUXC_SW_PAD_CTL_PAD bits would land well — even just for the four most common fields.
- §44.4 the difference between `gpiod_set_value` and `gpiod_set_value_cansleep` is given correctly, but the *reason* the plain version is "atomic-safe" is left implicit. One sentence: "The plain version takes a spinlock around the GPIO register write; `_cansleep` may take a mutex (the bus driver does its I/O while holding it). Mutex in atomic context = BUG."

## Ch45 — Input subsystem

### AI wording / sledgehammer / buzzwords
- > "Every keyboard, mouse, touchscreen, joystick, accelerometer-as-tilt-sensor, rotary encoder, and IR remote control on a Linux box flows through the same input subsystem."
  - Bullet-as-prose. Rewrite: "Every input device on a Linux box — keyboard, mouse, touchscreen, joystick, IR remote — goes through the input subsystem."
- > "Once that triple makes sense (`EV_KEY` + `KEY_ENTER` + `1` = 'Enter key was just pressed'), every input subsystem capability you'll meet — abs axes, relative motion, multi-touch slot protocol — is just a different combination of type/code/value."
  - 40-word sentence with parenthetical example *and* em-dash list. Break: "Once that triple makes sense — `EV_KEY` + `KEY_ENTER` + `1` means 'Enter was pressed' — the rest of the input subsystem (abs axes, relative motion, multi-touch slots) is just different combinations of type/code/value."
- > "Your driver is upstream of the type/code/value protocol; user-space is downstream. You don't talk to user-space directly."
  - "Upstream / downstream" metaphor + semicolon. Rewrite: "Your driver feeds events into the type/code/value protocol; the input core delivers them to user-space. You never talk to user-space directly."

### ESL readability
- > "**Allocating with `input_allocate_device` and registering separately, but the alloc/register can fail in different ways.** Standard `goto` cleanup applies."
  - Pitfall headline is a sentence fragment; the explanation is too short. Rewrite: "**Mixing `input_allocate_device` with separate `input_register_device`.** Both can fail, at different points. Use standard `goto` cleanup, or just use `devm_input_allocate_device` to avoid the problem."
- > "Done. Button is a real keyboard key."
  - Fine; keep.

### Needs more depth
- §45.4 `bd->input->id.bustype = BUS_HOST;` appears without explanation. ESL reader does not know what `BUS_HOST` means versus `BUS_USB`, `BUS_I2C`, `BUS_PCI`. One sentence: "`bustype` tells user-space what bus this device came from; `BUS_HOST` is the catch-all for 'on the board, no real bus.' Use `BUS_USB` for USB-HID, `BUS_I2C` for an I²C touch controller, etc."
- §45.5 autorepeat is named but not shown. For an MCU reader who has handled button repeat in firmware before, one paragraph on what `EV_REP` registration looks like (and how the user can set period via sysfs) would be valuable.

## Ch46 — I²C drivers

### AI wording / sledgehammer / buzzwords
- > "I²C is the workhorse bus of embedded"
  - Cliché. Rewrite: "I²C is the most common slow bus in embedded systems."
- > "Master this primitive and you can drive *any* I²C chip — write-then-read, repeated-start, 10-bit addressing, SMBus quirks."
  - "Master this" + triplet+quirks. Rewrite: "Get this primitive right and you can talk to any I²C chip: write-then-read, repeated-start, 10-bit addressing, SMBus quirks."
- > "Modern systems use DT, but the i2c_device_id is the historical fallback; you include both for forward/backward portability."
  - Semicolon. Rewrite: "Modern systems use DT. The `i2c_device_id` is the historical fallback. Include both for portability."
- > "Caveat: if a kernel driver has *bound* to a device, i2c-tools won't let you talk to it (you'd race with the driver). Use `-y -f` to force, but only for known-safe testing."
  - Fine, but "Caveat:" reads like a slide bullet. Rewrite: "If a kernel driver has already bound to the device, `i2c-tools` will refuse to touch it (you would race the driver). Pass `-y -f` to override — only for known-safe testing."

### ESL readability
- > "When the kernel parses DT, it sees: ... and creates an `i2c_client` with `addr = 0x76`, `name = 'bme280'`. When your `i2c_driver` registers, the I²C core walks all clients on all adapters, matches `compatible` to your `of_match_table`, and calls your `probe()`."
  - The second sentence is 28 words across three clauses. Break: "When your `i2c_driver` registers, the I²C core walks every client on every adapter. For each one whose `compatible` is in your `of_match_table`, it calls your `probe()`."
- > "Stress-test page alignment. Write 256 bytes starting at offset 3. Verify the driver correctly handles the page boundaries at 8, 16, 24, …"
  - Fine.

### Needs more depth
- §46.4 SMBus API: the section describes the API but never says what makes "SMBus" different from raw I²C at the protocol level. Three sentences: "SMBus is a subset of I²C used originally for PC motherboard management. It adds strict timing (10–100 kHz only), packet-error checking, and timeouts. In Linux, the SMBus helper functions also work on plain I²C — the kernel adapter advertises which protocol it supports, and the helper falls through to raw I²C when needed."
- §46.5 `i2c_transfer` returns "the number of messages successfully transferred" — easy to miss. The example checks `ret != 2`. Add one sentence: "On success `i2c_transfer` returns the number of messages it sent. So `if (ret != ARRAY_SIZE(msgs))` is the right error check; the code below converts a partial result to `-EIO`."

### Technical note (style-relevant)
- §46.3 driver template uses `static int mychip_probe(struct i2c_client *client)` — the modern single-argument form. Good — but the prose in §46.1 says the kernel calls `probe()` with no signature shown. Add one line: "Modern kernels (≥6.3) pass a single `struct i2c_client *`; older kernels passed a second `const struct i2c_device_id *` argument as well."

## Ch47 — SPI drivers

### AI wording / sledgehammer / buzzwords
- > "Same shape as I²C but with full-duplex transactions and per-CS independent configuration"
  - Fine in the *What* header. In §47.1 the table does the work; cut the redundant prose intro.
- > "Mirror image of the I²C driver from Ch 46. Same idioms: `module_spi_driver`, two match tables, `devm_kzalloc`, `dev_err_probe`."
  - Bullet-as-prose. Rewrite: "Mirror image of the I²C driver from Ch 46 — same idioms: `module_spi_driver`, two match tables, `devm_kzalloc`, `dev_err_probe`."
- > "Why `rohm,dh2228fv`? Because the kernel maintainers refuse to add `'spidev'` as a magic generic compatible (it's not a chip; it's a hack)."
  - Editorialising. Rewrite: "Why `rohm,dh2228fv`? The kernel maintainers will not accept `'spidev'` as a generic compatible — spidev is not a chip, just a user-space access mechanism."
- > "Useful for bring-up. Production code should be a real `spi_driver`."
  - Fine; keep.

### ESL readability
- > "The `len` is the SPI clock count; you need at least that many bytes in `rx_buf`."
  - Semicolon. Rewrite: "The `len` field is the SPI clock count, so you need at least that many bytes in `rx_buf`."
- > "The i.MX eCSPI native CS asserts/deasserts for each `spi_transfer`. If you need CS held across multiple `spi_transfer`s, either build them into one `spi_message` or use GPIO-CS via `cs-gpios` (which is held by software for the whole message)."
  - Long sentence with two options. Break: "The i.MX eCSPI native CS asserts and deasserts for *each* `spi_transfer`. To hold CS across multiple transfers, either (a) put them all in one `spi_message`, or (b) use GPIO-based CS via `cs-gpios` — software holds GPIO-CS for the whole message."

### Needs more depth
- §47.4 "CS asserts before the first transfer, deasserts after the last (unless overridden)." The "unless overridden" is the *whole point* of the `cs_change` field that the next paragraph mentions. Rewrite to make the link explicit: "CS asserts before the first transfer and deasserts after the last. To deassert between transfers in the same `spi_message`, set `cs_change = 1` on the transfer *before* the desired CS toggle."
- §47.4 `spi_async` example: introduces `spi_message_init`, `spi_message_add_tail`, and the `complete`/`context` callback fields without explaining the lifetime contract (who owns the `spi_message`, who must keep it alive until the callback fires). One sentence: "The `spi_message` and its transfers must remain valid until your `complete` callback runs — typical pattern is to embed them in your private struct, not on the stack."

## Ch48 — PWM and RTC subsystems

### AI wording / sledgehammer / buzzwords
- > "two short and orthogonal subsystems combined here because each is small enough on its own and the patterns reinforce each other"
  - "Orthogonal" is jargon. Rewrite: "two short, unrelated subsystems combined here — each is small enough on its own, and the patterns reinforce each other."
- > "You almost always write *consumers*; the SoC vendor wrote the producers."
  - Semicolon. Rewrite: "You almost always write *consumers*. The SoC vendor wrote the producers."
- > "A masterclass in handling chip-family variants."
  - "Masterclass" is fan-prose. Rewrite: "A good reference for handling chip-family variants."

### ESL readability
- > "For a fleet product, you almost certainly want `chrony` or `systemd-timesyncd` running to sync system time to NTP, then write the RTC periodically (`-11` hook or systemd's `systemd-time-sync-target`)."
  - 35-word sentence with parenthetical jargon (`-11 hook`). Break: "For a fleet product, run `chrony` or `systemd-timesyncd` to sync system time to NTP. Then write the RTC periodically — via systemd's `systemd-time-sync-target`, or an init `-11` hook."
- > "Wire up a CR2032; if you can't, accept the limitation and sync via NTP at boot."
  - Semicolon glue. Rewrite: "Wire up a CR2032. If you cannot, accept the limit and sync via NTP at boot."

### Needs more depth
- §48.1.2 the `pwms = <&pwm1 0 5000000 0>` line is decoded inline, which is good. But the broader concept of "DT phandle cells" — where the count of cells (`#pwm-cells`) is set by the provider — is never named. One sentence at the end of the inline comment: "The number of cells after the phandle (here, 3) is set by the controller's `#pwm-cells` property; check the binding doc for what each cell means."
- §48.2.1 *two RTCs* sidebar is excellent, but does not explain the practical consequence of `CONFIG_RTC_HCTOSYS_DEVICE`. Add: "If both register, the kernel reads `/dev/rtc0` at boot to set system time. Whoever registers first wins the `rtc0` name — and on many BSPs that is the SoC internal RTC, even when the external chip is more accurate. Pin the right one via kernel config or a udev rule."

## Ch49 — IIO subsystem (ADC, sensors)

### AI wording / sledgehammer / buzzwords
- > "Every chip in Part VII's sensor cookbook is an IIO driver."
  - Fine; useful forward reference. Keep.
- > "Get these three concepts right and IIO clicks."
  - "Clicks" is informal. Rewrite: "Get those three concepts right and the rest of IIO follows."
- > "Drivers declare a list of `iio_chan_spec` (channel specifications) and provide `read_raw` / `write_raw` callbacks. The core handles user-space exposure."
  - Fine; concise.
- > "We'll meet triggers and buffers again in Ch 70/71 (IMUs) where they really earn their keep."
  - "Earn their keep" is idiomatic English. Rewrite: "We come back to triggers and buffers in Ch 70/71 (IMUs), where they become essential."

### ESL readability
- > "before IIO (~2011), every sensor driver invented its own sysfs layout. Reading an ADXL345 was completely different from reading an LIS3DH despite both being 3-axis accelerometers. IIO standardised the interface: every accelerometer reports `in_accel_x_raw` in the same units after `_scale` is applied."
  - Three sentences flow fine; keep.
- > "`devm_iio_device_alloc(&client->dev, sizeof(*p))` allocates both the `iio_dev` and your private struct in one block. `iio_priv(idev)` recovers the priv pointer."
  - Good; keep.
- > "User-space writes to `scan_elements/in_*_en` to enable channels."
  - "scan_elements/in_*_en" — wildcard inside a path is confusing for ESL. Rewrite: "User-space writes `1` to `scan_elements/in_<channel>_en` for each channel to enable (e.g., `in_accel_x_en`, `in_accel_y_en`)."

### Needs more depth
- §49.3 the return-value table for `read_raw` (`IIO_VAL_INT`, `IIO_VAL_INT_PLUS_MICRO`, `IIO_VAL_FRACTIONAL_LOG2`) lists meaning but does not show what user-space sees. One worked example: "For a scale of 1/4096, return `IIO_VAL_FRACTIONAL_LOG2` with `*val=1, *val2=12`; user-space sees `0.000244` in the sysfs file."
- §49.6 buffered capture pipeline is fast and dense. The phrase "the driver's trigger handler reads a coordinated set of samples and pushes them" deserves a name (`iio_trigger_handler` / `iio_push_to_buffers`) so the reader can grep for it. One sentence with the actual function names would land well.

## Ch50 — regmap

### AI wording / sledgehammer / buzzwords
- > "Get the config right and the rest is mechanical."
  - "Mechanical" again — appears in Ch41, Ch43, here. Rewrite: "Get the config right and the rest is bookkeeping."
- > "That's a hundred lines of identical-feeling code. Regmap factors it all out. You declare *what your chip looks like*; regmap handles *how to talk to it*."
  - Triplet + semicolon. Rewrite: "That is a hundred lines of identical-looking code. Regmap factors it out: declare *what your chip looks like*, and regmap handles *how to talk to it*."
- > "The driver becomes bus-agnostic."
  - "Agnostic" is jargon. Rewrite: "The driver no longer cares which bus it sits on."
- > "Maybe 200 lines total. The same chip, hand-written without regmap and without IIO, would be 600+. The frameworks are leverage."
  - "Frameworks are leverage" is consultant-speak. Rewrite: "Around 200 lines total. The same chip without regmap or IIO would be 600+. The frameworks save you that code."
- > "For interactive driver debugging during bring-up, this is invaluable."
  - "Invaluable" is marketing. Rewrite: "This is the tool you reach for during bring-up."

### ESL readability
- > "With `cache_type = REGCACHE_RBTREE`, regmap caches all non-volatile, non-read-only registers in a red-black tree. A `regmap_read` of a cached register returns the cached value instantly; only volatile registers hit the bus. A `regmap_write` updates the cache *and* the bus; if power is restored after suspend, `regcache_sync(regmap)` flushes the cache back to the chip."
  - Three semicolon-spliced sentences. Break: "With `cache_type = REGCACHE_RBTREE`, regmap caches every non-volatile, non-read-only register in a red-black tree. A `regmap_read` of a cached register returns the cached value instantly. Only volatile registers hit the bus. A `regmap_write` updates both the cache and the bus. After resume from suspend, `regcache_sync(regmap)` flushes the cache back to the chip."
- > "Endianness mismatch. Chip is big-endian, driver assumes little-endian. Symptom: 16-bit values appear byte-swapped. Set `reg_format_endian = REGMAP_ENDIAN_BIG` in config."
  - Fragments fine for a pitfall bullet; keep.

### Needs more depth
- §50.3 the *volatile* concept is named ("ID registers are read-only; status registers change without you writing") but the *consequence* of marking a register volatile is left implicit. One sentence: "Marking a register volatile tells regmap: never cache this — always read the bus. Forget to mark a status register volatile and your driver sees the stale cached value."
- §50.5 the worked example ties regmap + IIO + IRQ together, which is great — but the IRQ handler comment "read data, push to buffer" hides the regmap → IIO call sequence that the rest of the chapter has been building toward. Either expand the comment to actual `regmap_bulk_read` + `iio_push_to_buffers` calls, or cross-link to Ch49 §49.6.


---

# Part VIb — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining** dominates almost every chapter intro and "Focus" line. The pattern "X — Y — Z" appears so often it has become invisible to the author but is jarring for an ESL reader. Replace with periods or commas.
- **"Not X — but Y" / "isn't X. It's Y"** sledgehammer used in chapter intros (esp. Ch 52A, Ch 53). Just state what it is.
- **Triplet rhythms** in "Focus:" lines ("what, why, how", "request, configure, prepare, submit"). Cut one.
- **Buzzwords cluster**: "seamless" (Ch 53), "deterministic" (Ch 52A — used correctly here but reused as marketing), "robust", "critical/crucial" (Ch 51A, 52A), "invaluable" (Ch 51B). Drop or replace with concrete numbers.
- **Royal "we'll / let's"** in section transitions and "Next chapter" boxes. Fine in moderation but appears in every chapter's closing line — vary or drop.
- **Hedging interjections** ("Worth its weight in gold", "Subtle.", "Better:") litter the text. Strip; the engineer reader does not need editorial nudges.
- **Bullet-list-as-prose**: short clauses bolded with "**Term.** Sentence." Used so consistently in Pitfalls/Tradeoffs sections that it becomes monotone. Mix in full sentences.
- **Long compound sentences** with three to four clauses joined by em-dashes and parentheticals are the dominant readability problem for ESL. Almost every paragraph has one.

## Ch51 — DMA

### AI wording / sledgehammer / buzzwords

- > "the CPU is a terrible bulk-data mover. Sustained 10 Mbps of SPI traffic eats a chunk of i.MX6ULL's CPU when each byte requires an IRQ; the SDMA controller does it at zero CPU cost."
  - Rewrite: "The CPU is bad at bulk data moves. At 10 Mbps SPI, one IRQ per byte burns a large fraction of the i.MX6ULL CPU. SDMA does the same job at zero CPU cost."
- > "turns 'this driver is incomprehensible' into 'this driver is a textbook dmaengine consumer.'"
  - Rewrite: "Once you know the consumer API, most DMA-using drivers read the same way."
- > "the four-step ritual"
  - Rewrite: "the four standard steps" (used four times across the chapter; "ritual" is decorative)
- > "Once you can mentally walk those four steps for any peripheral, every DMA driver in the kernel looks like a variation on one theme."
  - Rewrite: "Once you know these four steps, most DMA drivers look the same."
- > "the trap that catches everyone"
  - Rewrite: "A common bug:" (the "trap" framing is dramatic)
- > "the cache dance"
  - Rewrite: "the cache flush/invalidate sequence"

### ESL readability

- > "Setup cost. Configuring an SDMA transfer costs ~1 µs. For 4-byte transfers, PIO is faster."
  - Rewrite: keep as is — already short. But the surrounding `Memory pinning` bullet has too much packed in. Split: "DMA needs physically-contiguous, cache-coherent buffers. Use `dma_alloc_coherent` (slower, smaller pool) or `dma_map_single` (faster, manages cache). The MMU/cache material from Ch 4 matters here."
- > "you populate a buffer in user-space, give the kernel pointer to your driver, your driver DMAs from it — and DMA reads stale data because the CPU's recent writes are still in L1 cache."
  - Rewrite: "User-space fills a buffer. The driver hands the kernel pointer to DMA. DMA reads stale data — the CPU's recent writes are still in L1 cache."
- > "the kernel handles this for you *if you use the APIs correctly*. If you cast a pointer to `dma_addr_t` and skip the map call, you'll get sporadic data corruption that depends on whether the cache line happened to be evicted between operations."
  - Rewrite: "The kernel handles cache coherency for you, but only if you use the APIs. If you cast a pointer to `dma_addr_t` and skip `dma_map_*`, you get random data corruption. Whether it appears depends on whether the cache line was evicted between operations."

### Needs more explanation

- §51.3 "Step 3 — Prepare a descriptor": scatter-gather gets one line. Add 10 lines: what `struct scatterlist` is, why peripherals stream into multiple discontiguous pages (user-space buffers crossing page boundaries), the `sg_init_table` / `sg_set_buf` / `dma_map_sg` flow, and what the engine actually does (chain of descriptors, one per SG entry). This is the hard part of the dmaengine API and the chapter waves at it.
- §51.5 "Cyclic transfers": mention the relationship between `period` count, total ring size, and the residue API (`dmaengine_tx_status` returning the in-period offset) — that's how ALSA computes the hardware pointer.
- §51.7 "Cache coherency": the explanation conflates ARMv7 cache ops with the Linux DMA API. Add a sentence: "ARMv7 has separate inner/outer caches (PL310 L2). The DMA API takes care of both. `dma_alloc_coherent` returns memory that's mapped non-cacheable in the page tables, so no flushes are ever needed."
- A short paragraph on **dma-buf** is missing entirely. Even if not covered here, name it and forward-reference where it lives (camera / DRM zero-copy). The reader will hit it in Ch 54B and have no anchor.

---

## Ch51A — Watchdog

### AI wording / sledgehammer / buzzwords

- > "every product shipped to a customer needs this."
  - Rewrite: "Most shipping products need this." (avoid absolute marketing tone)
- > "Watchdog handling is the difference between 'this product is reliable' and 'this product is not.'"
  - Rewrite: drop the sentence. The previous line already made the point.
- > "Worth its weight in gold for debugging field failures."
  - Rewrite: "Very useful for debugging field failures." or drop.
- > "**Pretty short timeouts.**"
  - Rewrite: "**Short timeouts.**" ("Pretty" is filler.)
- > "Layered watchdog: hardware → systemd → application. Each layer protects the layer above."
  - Rewrite: leave the diagram, but the trailing "Each layer protects the layer above" is filler — the diagram says it.

### ESL readability

- > "A kernel oops on an unrelated subsystem, a deadlock in your driver, a CPU stuck in a tight infinite loop in user-space — without a watchdog, that's a brick that needs a power-cycle by hand."
  - Rewrite: "A kernel oops in some other subsystem. A deadlock in your driver. A user-space process stuck in an infinite loop. Without a watchdog, the device becomes a brick that needs a manual power-cycle."
- > "if `CONFIG_WATCHDOG_NOWAYOUT=y` (default on most distros), once `/dev/watchdog` is opened, it cannot be safely closed — closing without the magic 'V' character first leaves it armed; closing with 'V' disables it."
  - Rewrite: "With `CONFIG_WATCHDOG_NOWAYOUT=y` (the usual default), once `/dev/watchdog` is opened, it cannot be safely closed. To disable it on close, write a `'V'` first. Closing without the `'V'` leaves it armed."

### Needs more explanation

- §51A.5 "boot-reason register": SRC_SRSR is named but not decoded. Show the actual bit layout (POR, WDOG, WARM, JTAG) and how to read it from user-space (`cat /sys/...` path) so the reader can actually use it.
- §51A.6 "Writing a watchdog driver" feels too thin given the chapter's depth requirement. Add: what the core does for you (the `dev_t` allocation, the `/dev/watchdogN` node, the IOCTL multiplex), and *why* you usually do not need to write one (because chips are usually wired through GPIO + a kthread, see external IC pattern).
- pstore/ramoops: name `pstore_blk` and `pstore-zone`. Reader hitting eMMC-only boards needs to know there is a path without preserved RAM.

---

## Ch51B — Power management

### AI wording / sledgehammer / buzzwords

- > "Runtime PM is the kernel's autonomic nervous system."
  - Rewrite: "Runtime PM is the kernel's automatic per-device idle/active state machine." (the biology metaphor is a tell.)
- > "DVFS — the 'voltage before frequency' / 'frequency before voltage' dance"
  - Rewrite: "DVFS — when raising clock, the regulator goes up first, then the clock; when lowering, the reverse."
- > "`powertop` is invaluable for finding which userspace process is keeping the CPU awake."
  - Rewrite: "`powertop` shows which userspace process is keeping the CPU awake."
- > "Each step is small (~mA). Together they go from '1 Ah lasts 4 hours' to '1 Ah lasts 4 days.'"
  - Rewrite: "Each step saves a few mA. Together they take a 1 Ah cell from 4 hours to 4 days." (the quoted-string framing is theatrical.)
- > "for any battery-powered product, this is half the engineering work."
  - Rewrite: "On battery-powered products, PM tuning is a large fraction of the work."

### ESL readability

- > "Each device declares idle and active states; the framework reference-counts usage and runs `runtime_suspend` / `runtime_resume` callbacks when the count crosses zero."
  - Rewrite: "Each device has an idle and an active state. The framework counts users with a refcount. When the refcount hits zero it calls `runtime_suspend`. When it goes from zero to one it calls `runtime_resume`."
- > "the kernel calls system-suspend callbacks during `echo mem > /sys/power/state` and runtime-suspend callbacks autonomously."
  - Rewrite: "System-suspend callbacks run when user-space writes `mem` to `/sys/power/state`. Runtime-suspend callbacks run automatically when the device goes idle."
- > "If `cpu-supply` is wrong, raising the frequency before voltage stabilises = unreliable execution."
  - Rewrite: "If `cpu-supply` is wrong, the kernel may raise the clock before voltage settles. Execution becomes unreliable."

### Needs more explanation

- §51B.1 "Runtime PM" — runtime PM has subtle interaction with **system suspend**, parent/child device PM, and `dev_pm_domain`. Add a few lines on: parent must be active before child can resume; PM domains (genpd) on i.MX gate whole IP blocks; what "no_callbacks" devices mean.
- §51B.3 "System sleep" — add a paragraph on the difference between `suspend`, `suspend_late`, `suspend_noirq` callbacks. This is the part of system PM that bites everyone: ordering across the device tree matters, and the three callback phases are exactly that ordering.
- §51B.2 DVFS: the OPP table is shown but the **regulator coupling** is not explained. Mention that on i.MX6ULL the ANATOP arm regulator and the SOC/PU regulators are coupled, and getting that wrong is the most common DVFS bring-up bug.
- Missing entirely: **CPU idle** (`cpuidle`) — distinct from cpufreq. WFI vs deeper idle states. On i.MX6ULL there are only WAIT and STOP idle modes, but the reader should know they exist and how the framework picks them.

---

## Ch52 — Network (FEC + KSZ8081)

### AI wording / sledgehammer / buzzwords

- > "Ethernet is the most-debugged peripheral on any embedded board."
  - Rewrite: "Ethernet is one of the most-debugged peripherals on any embedded board." (the absolute is unprovable and reads like marketing.)
- > "the full anatomy of 'Linux has eth0 working.'"
  - Rewrite: "the full path from MAC to `eth0`."
- > "Get the four layers right and packets flow."
  - Rewrite: drop (sledgehammer). The diagram already says it.
- > "**This is the biggest bring-up gotcha**"
  - Rewrite: "This is the most common bring-up bug on i.MX6ULL boards."
- > "Half the 'FEC not working' reports turn out to be a bent CAT5e or a dead RJ45 jack."
  - Rewrite: keep — this one is funny and accurate.

### ESL readability

- > "i.MX6ULL has **two FEC instances**, FEC1 and FEC2. Some boards wire both (giving dual Ethernet). Point Atom MINI typically has one wired, ALPHA may have two."
  - Rewrite: already short and clear. No change.
- > "NAPI batches RX interrupts to reduce the IRQ rate at high packet rates — instead of one IRQ per packet, the driver gets one IRQ, then polls until the RX queue is empty, then re-arms IRQ."
  - Rewrite: "NAPI batches RX interrupts. The driver gets one IRQ, then polls until the RX queue is empty, then re-arms the IRQ. This avoids one IRQ per packet at high rates."
- > "Wrong direction = no link, no MDIO communication, mysterious failures."
  - Rewrite: "If the clock direction is wrong, you get no link, no MDIO communication, and confusing symptoms."

### Needs more explanation

- §52.3 "netdev framework" — `sk_buff` is the central object and is not mentioned. Add 10 lines: an `sk_buff` is what `ndo_start_xmit` receives and what NAPI hands up the stack; data is in a headroom/data/tailroom layout; skb_pull/skb_push manipulate headers. Without this, the reader cannot read `fec_main.c` meaningfully.
- §52.4 "phylib" — explain the **link state machine**. The PHY library has its own kthread (`phy_state_machine`) that polls PHY status registers and invokes the MAC driver's `adjust_link` callback. The reader should know why "no link" sometimes means "phylib has not polled yet."
- §52.6 "RMII pinmux": the `0x1b0b0` pad value is repeated 9 times with no decode. Spend 5 lines decoding the conf_reg bits (PUS, PUE, HYS, SPEED, DSE, SRE) so the reader knows what they are setting.
- Missing: a quick word on **`xdp`** and where it sits relative to NAPI. Even if not implemented for FEC, name it; the reader will encounter it.

---

## Ch52A — PREEMPT_RT

### AI wording / sledgehammer / buzzwords

- > "Many shipping industrial products (CNCs, robotic arms, real-time camera ML inference) run PREEMPT_RT Linux today."
  - Rewrite: "Many industrial products run PREEMPT_RT Linux today — CNCs, robotic arms, real-time camera inference."
- > "Internalising what 'bounded' really means — and what defeats it — is the whole game."
  - Rewrite: "What 'bounded' actually means, and what breaks it, is the main thing to learn."
- > "The 30× improvement in the long tail makes hard-RT applications viable."
  - Rewrite: "A 30× drop in the worst case makes hard-RT applications viable."
- > "This single feature avoids the Mars Pathfinder bug."
  - Rewrite: keep — this is genuinely informative. Could be expanded with two lines on what the Pathfinder bug actually was, since ESL readers will not know.
- > "PREEMPT_RT alone isn't enough. Tune:"
  - Rewrite: "PREEMPT_RT alone is not enough. You also need to tune the kernel, the cmdline, and userspace:" (the colon-as-section-header is a tic that appears in several chapters.)

### ESL readability

- > "A standard Linux kernel might run your callback in 100 µs on average — but every 1000th time, it takes 5 ms because some other kernel code held a non-preemptible lock."
  - Rewrite: "On a standard kernel, your callback runs in about 100 µs on average. But every 1000th time, it takes 5 ms because some other kernel code held a non-preemptible lock."
- > "Standard Linux runs IRQ handlers in IRQ context — atomic, fast, but blocking other IRQs of the same priority. PREEMPT_RT runs *all* IRQ handlers as kernel threads, schedulable like any other thread."
  - Rewrite: "Standard Linux runs IRQ handlers in IRQ context: atomic, fast, but blocking other IRQs at the same priority. PREEMPT_RT runs every IRQ handler as a kernel thread. The scheduler treats them like any other thread."
- > "Without priority inheritance: low-priority task A holds mutex M. High-priority task B wants M, blocks. Medium-priority task C runs (preempts A). B is now blocked indefinitely by C — *priority inversion*."
  - Rewrite: "Without priority inheritance, priority inversion happens. Low-priority task A holds mutex M. High-priority task B wants M and blocks. Medium-priority task C runs and preempts A. B now waits behind C indefinitely."

### Needs more explanation

- §52A.2.1 "Preemptible spinlocks" — the conversion from `spinlock_t` to sleeping lock is the most important RT idea and only gets two sentences. Add: this is why some code is wrong under RT (calling `spin_lock` then `kmalloc(GFP_ATOMIC)` is fine on mainline but the lock is sleepable on RT, so the rules for what you can do inside it change). The reader from MCU-RTOS world needs this contrast.
- §52A.4 `cyclictest`: explain *what cyclictest actually measures* — it is the gap between the `nanosleep(target)` expected wake time and the moment the user-space thread actually runs. So the number is (kernel timer jitter) + (IRQ-to-thread wake) + (scheduler latency). Many readers think it measures hardware IRQ latency directly.
- Missing entirely: **what threaded IRQs look like to a driver writer**. Two paragraphs on `IRQF_ONESHOT`, the primary/threaded split, and `IRQF_NO_AUTOEN`. This is the day-to-day mechanic of writing RT-safe drivers.
- The relationship to **`runtime PM`** (Ch 51B): runtime suspend can add 100+ µs to wake-from-idle. A real RT chapter should at least name this trade-off.

---

## Ch53 — Sound (ALSA / ASoC)

### AI wording / sledgehammer / buzzwords

- > "audio is one of the most stressful real-time loops in any system."
  - Rewrite: "audio is one of the tightest real-time loops in any embedded system."
- > "the most architecturally complex subsystem in the kernel"
  - Rewrite: "one of the most layered subsystems in the kernel"
- > "a magnificent hack" (in Ch 54 about panel-simple)
  - Rewrite: "a useful shortcut" (the "magnificent hack" framing is cute but not informative.)
- > "as long as user-space writes fast enough that the buffer doesn't underrun, sound plays seamlessly."
  - Rewrite: "if user-space writes fast enough to avoid an underrun, playback continues without glitches."
- > "Once you grok this binding pattern, every ASoC driver in the kernel becomes legible."
  - Rewrite: "Once you understand this binding, ASoC drivers become readable."

### ESL readability

- > "ASoC splits an audio chain into three driver pieces: **CPU-DAI** (the SoC's I²S/SAI controller), **codec** (the analog chip, e.g., WM8960 or SGTL5000), and **machine** (the glue that wires them together for one specific board)."
  - Rewrite: "ASoC splits an audio chain into three drivers. The **CPU-DAI** is the SoC's I²S/SAI controller. The **codec** is the analog chip (WM8960, SGTL5000). The **machine driver** wires them together for one specific board."
- > "Every period (typically 1024 samples = ~21 ms at 48 kHz), the DMA fires an IRQ; ALSA refills that period from the user-space buffer; the cycle continues."
  - Rewrite: "DMA fires an IRQ every period (typically 1024 samples, about 21 ms at 48 kHz). ALSA refills that period from the user-space buffer. The cycle continues."

### Needs more explanation

- §53.1 should at least name **DAPM** (Dynamic Audio Power Management) as a concept before §53.7 references it. DAPM is the second-hardest ASoC concept (after the three-driver split) and is currently introduced sideways via the DT routing example. Two paragraphs: each codec block (HP_L, MIC, etc.) is a DAPM widget; the routing graph decides which blocks are powered; user-space mixer changes propagate through the graph and gate power.
- §53.4 "Writing a machine driver": the example does not show the `dai_fmt` constants in detail. ESL reader sees `SND_SOC_DAIFMT_CBS_CFS` and has no chance — decode: "Codec is Bit-clock Slave, Frame-clock Slave (CBS_CFS). The SoC is master."
- The cyclic DMA path is the same as Ch 51's cyclic transfer, but the **residue-based hardware-pointer** computation that ALSA does is not shown. This is the bridge between Ch 51.5 and Ch 53; a one-paragraph diagram would close the loop.
- Missing: **ALSA's PCM substream states** (OPEN → SETUP → PREPARED → RUNNING → XRUN → DRAINING). The pcm_ops callbacks fire on these transitions; without the state machine the callbacks are random functions.

---

## Ch54 — LCD / DRM

### AI wording / sledgehammer / buzzwords

- > "panel-simple + DT timings == working display"
  - Rewrite: "For most boards, panel-simple plus correct DT timings is enough." (the `==` is cute but reads as code where the prose should not.)
- > "is a magnificent hack"
  - Rewrite: "is a database-driven panel driver" (matter-of-fact)
- > "**Pixel clock too high.** PCLK > ~80 MHz on i.MX6ULL LCDIF → silent failure."
  - Rewrite: "**Pixel clock too high.** Above about 80 MHz the LCDIF gives no output."
- > "Always test with daylight first."
  - Rewrite: "Always check in good ambient light first." (slight ESL clarity — "test with daylight" is unusual English.)
- > "drm.debug=15 on kernel cmdline floods dmesg with DRM info; invaluable for chasing modeset issues."
  - Rewrite: "`drm.debug=15` on the kernel cmdline fills dmesg with DRM trace output. Very useful for modeset bugs."

### ESL readability

- > "For embedded HMI with one panel and a single fullscreen Qt app, fbdev still works. For anything with multiple outputs, GPU acceleration, or Wayland, DRM is the only option."
  - Rewrite: clear already; no change.
- > "**Both are present** on modern kernels; fbdev is emulated on top of DRM via `fbdev_emulation`. Your fullscreen Qt app sees `/dev/fb0`; under the hood DRM is doing the work."
  - Rewrite: "Both APIs are present on modern kernels. fbdev is emulated on top of DRM (`fbdev_emulation`). A fullscreen Qt app opens `/dev/fb0`, but DRM is doing the work underneath."
- > "Off-by-one in front-porch is the most common error."
  - Rewrite: keep — already crisp.

### Needs more explanation

- §54.1 (fbdev vs DRM table) — the four central DRM objects (**CRTC, plane, encoder, connector**) appear in the table but are not defined. For an ESL reader coming from MCU framebuffer drivers, this is the single biggest leap. One short section is essential:
  - CRTC = the scan-out engine (the LCDIF instance).
  - plane = a layer that the CRTC composites (overlay, cursor, primary).
  - encoder = the bridge between pixel data and a physical interface (DPI, HDMI, MIPI).
  - connector = the physical output port and its EDID/state.
  Without this the entire chapter is opaque.
- §54.3 — `panel-timing` is shown with 12 fields and no diagram. Add a small ASCII diagram of a video frame showing where each porch / sync lives. The MCU reader has seen this on a CRT controller but the naming differs.
- §54.5 "DRM style" introduces `modetest` then says "atomic mode-setting" only in the table. Add a paragraph: the atomic ioctl bundles all CRTC + plane + connector state into one ioctl that either all succeeds or all fails. This is the API that DRM clients (Weston, Qt EGLFS) actually use; `modetest` exposes it through `-P`/`-s`.
- **dma-buf** is absent again. DRM is where dma-buf truly matters: any zero-copy from V4L2 to DRM (Ch 54B → Ch 54) goes through dma-buf. Either name it here or in Ch 54B and cross-reference.

---

## Ch54A — MTD / UBI

### AI wording / sledgehammer / buzzwords

- > "raw NAND is everywhere in industrial embedded"
  - Rewrite: "Raw NAND is common in industrial embedded."
- > "Used by every shipping NAND-based product on Linux."
  - Rewrite: drop. The previous sentence makes the point.
- > "**Don't confuse them**; each solves a distinct problem."
  - Rewrite: "Keep them separate in your head — each solves a different problem."
- > "**Wear test.** Write a script that writes a 1 MB file in a loop"
  - Rewrite: keep, but "Wear test" as section header is fine.

### ESL readability

- > "But NAND is *not* a block device: it has erase blocks (~128 KB), pages (~2 KB), bad-blocks that grow over the lifetime, and limited erase cycles."
  - Rewrite: "But NAND is not a block device. It has erase blocks (about 128 KB) and pages (about 2 KB). Bad blocks appear over the device's lifetime. Erase cycles are limited."
- > "UBIFS atop a block layer that's atop NAND is double-translation."
  - Rewrite: "If you put a block-device emulation on top of NAND, then a filesystem on top of that, you pay for two translation layers."

### Needs more explanation

- §54A.1 should mention **MTD-on-SPI-NOR** (m25p80) as the other common MTD use case. The chapter is NAND-only by title, but readers with SPI-NOR boot devices need to know MTD is the same framework.
- §54A.4 "UBI on top" — UBI's **fastmap** feature is a real win on large NANDs (cuts attach time from seconds to ~100 ms) and is missing. One paragraph: `ubi.fm_autoconvert=1` or DT `linux,ubi-fastmap`.
- §54A.6 "Wear levelling" — the chapter does not explain **why** UBI works the way it does. Two paragraphs on the algorithm: UBI keeps each LEB's erase counter; when free LEBs are needed, it picks ones with low counters; periodically it migrates static data off low-counter PEBs to even things out. Without this the `ubinfo` output is just numbers.
- Missing: **UBI block driver** (`ubiblock`) for read-only mounting of squashfs over UBI — a common pattern for /usr on industrial products. Worth a short subsection.
- Power-loss safety is asserted ("UBIFS handles this well") but not explained. Add a sentence: UBIFS uses a journal and the UBI layer guarantees that an LEB is either erased or fully written; partial writes are detected and discarded on attach.

---

## Ch54B — V4L2 / GStreamer

### AI wording / sledgehammer / buzzwords

- > "Mastering the pipeline mental model unlocks the entire imaging stack."
  - Rewrite: "Once the pipeline model clicks, the rest of the imaging stack reads easily."
- > "Everything else is image processing."
  - Rewrite: "After that, the rest is image processing."
- > "100 lines for a complete capture loop. Tedious but predictable."
  - Rewrite: keep — already plain.
- > "GStreamer 30 seconds"
  - Rewrite: "GStreamer in 30 seconds" (small ESL correction)
- > "Auto-exposure / auto-white-balance work surprisingly well for general use."
  - Rewrite: "Auto-exposure and auto-white-balance are good enough for general use."

### ESL readability

- > "A V4L2 *device* is what user-space opens (`/dev/video0`). It's connected to *sub-devices* — the sensor (OV5640) and the CSI bridge (i.MX CSI/ISI) — via a **media graph**. The user-space configures both the format (resolution, pixelformat) at the video device and the format at each subdev."
  - Rewrite: "A V4L2 *device* is what user-space opens (`/dev/video0`). It connects to *sub-devices* — the sensor and the CSI bridge — through a **media graph**. User-space sets the format on both the video device and on each subdev."
- > "i.MX6ULL has no GPU/VPU, so video encoding is software (slow). Useful up to ~5–10 fps at QVGA. For higher framerates and resolutions you need a different SoC."
  - Rewrite: clear; no change.
- > "5 MP at 30 fps requires ~140 MB/s memory bandwidth — pushes i.MX6ULL hard."
  - Rewrite: "5 MP at 30 fps needs about 140 MB/s of memory bandwidth. This is close to the i.MX6ULL's practical limit."

### Needs more explanation

- §54B.1 — the media graph is named but not shown. Add the actual `media-ctl -p` output (or at least a sketch of one) with the link directions and the active/inactive markers. The reader cannot understand `media-ctl --set-v4l2` without seeing what the graph looks like.
- §54B.3 — the `videobuf2` (vb2) layer behind V4L2's buffer ioctls deserves a paragraph. vb2 is the kernel-side machinery that backs `REQBUFS` / `QBUF` / `DQBUF` with three queue types (MMAP, USERPTR, DMABUF). This is where **dma-buf** finally appears in the book — name it here and forward to where it crosses into DRM.
- §54B.5 — the **control framework** (`v4l2_ctrl`) deserves a short subsection. Sensors expose dozens of controls; the framework provides per-control min/max/step, change notifications, and a "control event" subscription mechanism. Without this paragraph the reader hits `v4l2-ctl --list-ctrls` and has no idea what's behind it.
- The i.MX6ULL has **CSI parallel** but the chapter mentions MIPI lanes (`data-lanes = <1>`) which is wrong for parallel CSI (parallel uses an 8-bit bus, not lanes). Either the DT snippet is for a MIPI-CSI variant or it is a bug. Worth a clarifying note: "On i.MX6ULL, CSI is 8-bit parallel; the `data-lanes` syntax is only valid if you have a CSI-2 bridge."

---

## Ch55 — USB gadget

### AI wording / sledgehammer / buzzwords

- > "the modern way to compose a USB gadget"
  - Rewrite: "The current way to compose a USB gadget." (lower-key)
- > "every Android phone, Raspberry Pi Zero in USB-Pi mode, smart-meter that exposes its data via USB-serial — all run USB gadget."
  - Rewrite: "USB gadget runs on Android phones, Raspberry Pi Zero in USB-Pi mode, smart meters that expose data over USB-serial, and many other devices."
- > "**Two gadgets bound to one UDC.** Only one bind per UDC at a time."
  - Rewrite: keep — already crisp.

### ESL readability

- > "Last line: writing the UDC name binds the gadget. Now plug a USB cable from the i.MX6ULL's OTG port to a PC; the PC sees a composite USB device with serial + Ethernet + mass storage."
  - Rewrite: "The last line binds the gadget by writing the UDC name. Plug a USB cable from the i.MX6ULL's OTG port into a PC. The PC sees a composite USB device with serial, Ethernet, and mass storage."
- > "ConfigFS is a *filesystem*: `mkdir` a function, `echo` settings into its files, then bind to a UDC. No kernel code."
  - Rewrite: short already.
- > "Windows needs an `.inf` driver hint for CDC-ACM."
  - Rewrite: "Windows needs a `.inf` driver file before it will bind to CDC-ACM."

### Needs more explanation

- §55.2 ConfigFS overview — the chapter shows the steps but does not say **why** the design is this way. One paragraph: pre-ConfigFS, every gadget composition required a kernel module (`g_serial.ko`, `g_ether.ko`); ConfigFS lets a single user-space init script change the composition at runtime. The "function" / "configuration" / "UDC" tree mirrors the actual USB device tree (one device → one or more configurations → one or more interfaces).
- §55.5 "Custom function": **FunctionFS** is named but the model is not explained. Two paragraphs: FunctionFS exposes raw endpoint files (`ep1`, `ep2`, ...) to user-space; you write descriptors into `ep0` then read/write data on the other endpoints. This is the equivalent of "raw USB device" for testing or proprietary protocols.
- Missing: **USB gadget composite vs OS Descriptors** for Windows. The chapter mentions Windows needs `.inf` but does not mention that gadgets can ship OS Descriptors (MS_OS_20) inside the device itself to make Windows auto-bind WinUSB — this is the modern Windows-compatible path.
- §55.1 OTG: the ID-pin detection mechanism (the extcon framework, `usb_role_switch`) is missing. Even a one-line forward reference would help.

---

## Ch55A — Kernel timers / hrtimers

### AI wording / sledgehammer / buzzwords

- > "They're foundational to many driver patterns: timeouts, periodic polling, throttling, scheduled deferred work."
  - Rewrite: "Common driver patterns use them: timeouts, periodic polling, rate limiting, deferred work."
- > "Pick the right one and the API choices follow."
  - Rewrite: drop. The next section explains both APIs anyway.
- > "Drifts less than re-arming manually."
  - Rewrite: "It drifts less than recomputing `now + 1ms` each time."

### ESL readability

- > "`mod_timer`: re-schedules an existing timer to a new expiry; if not active, arms it."
  - Rewrite: "`mod_timer`: re-schedules a running timer to a new expiry. If the timer is not active, it arms it."
- > "Each press triggers an IRQ, which re-arms the timer. If the button bounces, every bounce resets the timer; only after 20 ms of silence does the timer fire and report the press."
  - Rewrite: "Each press triggers an IRQ that re-arms the timer. If the button bounces, every bounce resets the timer. Only after 20 ms of silence does the timer fire and report the press."
- > "Granularity: nanoseconds, limited by hardware (i.MX6ULL's GPT has ~30 ns resolution)."
  - Rewrite: clear; no change.

### Needs more explanation

- The chapter does not explain **what runs the callback**. timer_list runs in the timer softirq (`TIMER_SOFTIRQ`); hrtimer can run in either softirq or hardirq context depending on the mode (`HRTIMER_MODE_REL_HARD` etc.). For RT users this is the key difference. One paragraph.
- §55A.2 hrtimer modes: `HRTIMER_MODE_REL`, `_ABS`, `_PINNED`, `_HARD` — the chapter only shows `_REL`. ESL reader will hit driver code with `_PINNED` and wonder what it does (pin to the CPU it was started on, useful for per-CPU timers).
- §55A.3 workqueue table is fine but `kthread_worker` (a private workqueue for one kthread) is the RT-preferred alternative and not mentioned. RT drivers prefer kthread_worker because regular workqueue can starve.
- The relationship to **NAPI** (Ch 52) is implicit and not stated: NAPI is also a softirq context, sharing the same constraints as timer callbacks. Cross-reference would help.

---

## Ch55B — Async / SIGIO

### AI wording / sledgehammer / buzzwords

- > "Linux's input layer doesn't use it (poll/epoll is preferred), but legacy POSIX-style apps and some custom devices do."
  - Rewrite: clear; no change.
- > "SIGIO is a 'good to know it exists' mechanism more than a 'use this often' mechanism."
  - Rewrite: "SIGIO is worth knowing about, but rarely the right tool today."
- > "`Documentation/admin-guide/cgroup-v2.rst` (no, just kidding) — the relevant kernel docs are sparse"
  - Rewrite: drop the joke. "The relevant kernel docs are sparse — see LDD3 Chapter 6 and `man 2 fcntl` instead." (The parenthetical is a Claude-ism.)

### ESL readability

- > "Three steps: install signal handler → `F_SETOWN` declares who gets the signal → `F_SETFL | O_ASYNC` enables it."
  - Rewrite: "Three steps. First, install the signal handler. Second, `F_SETOWN` tells the kernel which process gets the signal. Third, `F_SETFL | O_ASYNC` enables delivery."
- > "User-space must drain whatever was queued, not just respond to 'one event.'"
  - Rewrite: "User-space must drain everything that was queued, not just handle one event."

### Needs more explanation

- The chapter is short and that is fine, but it should at least name the **modern alternatives one more time at the end** with a one-line "use poll/epoll/io_uring instead" verdict so an ESL reader does not walk away thinking SIGIO is a good default.
- `F_SETSIG` is referenced in Pitfalls but never explained. Either show a code snippet or drop the reference.
- Missing: **how SIGIO interacts with threads**. `F_SETOWN` to a pid signals the process; signaling a specific thread requires `F_SETOWN_EX`. This bites people moving from single-threaded prototypes.

---

## Ch55C — CAN / FlexCAN

### AI wording / sledgehammer / buzzwords

- > "Linux's elegant abstraction"
  - Rewrite: "Linux's clean abstraction" or just "Linux's abstraction." ("Elegant" is a tell.)
- > "**CAN-as-network-device**"
  - Rewrite: "CAN looks like a network device."
- > "Indispensable."
  - Rewrite: "Required." or drop. (One-word emphatic sentences are a Claude pattern.)
- > "the most common embedded case"
  - Rewrite: "a common embedded case"

### ESL readability

- > "The kernel filters in software (or hardware where possible — FlexCAN has MB filtering). High-throughput receivers should always set filters; otherwise every frame on the bus arrives at every socket."
  - Rewrite: "The kernel filters in software, or in hardware where the controller supports it. FlexCAN has message-buffer (MB) filtering. High-throughput receivers should always set filters. Otherwise, every frame on the bus is delivered to every socket."
- > "Without 60 Ω at each end, signal integrity collapses. Single-node bench setups: just stick a single 120 Ω resistor across CAN_H/CAN_L and live with reduced robustness."
  - Rewrite: "Without 120 Ω termination at each end of the bus (60 Ω total), signal integrity collapses. For a single-node bench setup, put one 120 Ω resistor across CAN_H/CAN_L. Robustness is lower but it works." (Original conflates 60 Ω each-end with 60 Ω total — this is a *technical* error worth flagging: standard CAN termination is 120 Ω at each end, which forms 60 Ω parallel as the bus impedance.)

### Needs more explanation

- §55C.3 "Bringing up the interface" — the **bit-timing** segment registers (`tq`, `prop_seg`, `phase_seg1`, `phase_seg2`, `sjw`, `sample-point`) are skipped entirely. For real CAN bring-up these matter when you cannot use the default bitrate calculator. One paragraph showing how `ip link set canX type can bitrate 500000 sample-point 0.875` works, and a sentence on why CiA recommends 87.5 %.
- §55C.4 — **CAN-FD** is in DT and in the cmdline but not in the C example. Add a short C snippet using `canfd_frame` and the `CAN_RAW_FD_FRAMES` socket option.
- §55C.5 — the **BCM (Broadcast Manager)** is named in one line and never demonstrated. This is the one CAN-specific socket feature that *no other socket family has* and that is genuinely powerful (kernel-side cyclic TX, content-change RX filter). Two paragraphs with a code sketch.
- **Error handling** is the practical hard part of CAN drivers. The chapter mentions `CAN_ERR_BUSOFF` but does not explain TEC/REC (Transmit/Receive Error Counters) and the warning/passive/bus-off transitions. One small diagram of the state machine.

---

## Ch55D — Block device drivers

### AI wording / sledgehammer / buzzwords

- > "Userspace's `read(fd, ..., 4096)` becomes one or more `struct bio`s queued to a `gendisk`."
  - Rewrite: "A user-space `read(fd, ..., 4096)` becomes one or more `struct bio`s submitted to a `gendisk`."
- > "A real RAM-backed block device, mountable like any disk."
  - Rewrite: drop the editorial closing line. The code listing already showed what it did.
- > "The minimal ramdisk skips many features."
  - Rewrite: "The ramdisk above is minimal. Production block drivers add:"

### ESL readability

- > "Drivers can either process bio-at-a-time or convert to hardware-native request structures."
  - Rewrite: "Drivers can process bios one at a time, or convert them to hardware-native request structures."
- > "Modern kernels require sector-aligned bios; smaller-than-sector requests get split."
  - Rewrite: "Modern kernels require sector-aligned bios. Requests smaller than a sector get split."
- > "Block layer expects fast queue_rq returns. Defer long work to a workqueue."
  - Rewrite: "`queue_rq` is expected to return quickly. Defer long work to a workqueue."

### Needs more explanation

- §55D.1 The path from `read()` — `pagecache` is invisible in the diagram. For an MCU engineer this is a major gap: most reads do not reach the block layer because page cache catches them. One paragraph: VFS first checks page cache; on miss, the filesystem builds a bio; the bio goes through blk-mq.
- §55D.2 The ramdisk example uses `blk_mq_alloc_disk` which is the modern (5.14+) API. The chapter should say so and contrast with the pre-5.14 `blk_alloc_queue` + `alloc_disk` pattern that older code still uses, so reading older drivers in the kernel does not confuse the reader.
- The **request lifecycle** is missing: `queue_rq` → `blk_mq_start_request` → driver does work → `blk_mq_end_request` (or `blk_mq_requeue_request` on transient errors). The chapter shows the calls but does not name the lifecycle states.
- Missing entirely: **`bio_chain` and `bio_split`** — how the kernel handles bios that exceed the driver's max transfer size, and how zoned and DM (device-mapper) layers stack on top. Even a forward reference would help.

---

## Ch55E — WiFi / wpa_supplicant

### AI wording / sledgehammer / buzzwords

- > "Get any layer wrong and 'nothing works.'"
  - Rewrite: "If any layer is wrong, nothing works."
- > "from a multi-day mystery into a methodical bring-up."
  - Rewrite: "from a multi-day debug into a methodical bring-up."
- > "Most BCM/Realtek modules need a 32 KHz LPO clock; if not wired/provided, sleep modes fail or chip is unreliable."
  - Rewrite: "Most BCM and Realtek modules need a 32 kHz LPO clock. Without it, sleep modes fail and the chip becomes unreliable."

### ESL readability

- > "Without the nvram, the driver probes but WiFi doesn't enumerate channels correctly (or at all). The nvram is *per-board* — copying from a different board's image gives wrong antenna config, wrong regulatory, broken behavior. Always get the matching nvram from your board vendor."
  - Rewrite: "Without the nvram, the driver probes but channels do not enumerate correctly (or at all). The nvram is per-board. Copying from another board gives the wrong antenna config, the wrong regulatory domain, and broken behavior. Always get the matching nvram from your board vendor."
- > "Three things:"
  - Rewrite: "Three things to notice:" (standalone "Three things:" is a Claude pattern.)

### Needs more explanation

- §55E.1 The stack — there is no discussion of **firmware-loading mechanics**. The reader sees "firmware blob loaded" but does not know that `request_firmware()` walks `/lib/firmware/` and that systemd/udev hooks can re-trigger probe after firmware lands. This is a real source of bring-up bugs (firmware shipped in initramfs vs rootfs).
- §55E.2 — **SDIO** itself deserves a short paragraph. The reader has not seen SDIO before. It is MMC-like with a function-based protocol. WiFi modules implement SDIO function 1 (BCM) or function 2 (others). The `wifi@1` reg matches the function number. Without this the DT snippet is opaque.
- §55E.5 — **regulatory** is one bullet in Pitfalls but is actually a separable subsystem (`CRDA` historically, `wireless-regdb` now). Worth a short subsection: the kernel sets a country code via `iw reg set XX` or via 802.11d/h beacons; this gates which channels/powers are allowed.
- Missing: **mac80211 hwsim** for development on a host without WiFi hardware. The chapter mentions it in "Going deeper" only; a sentence in the body about using it for testing wpa_supplicant configs would help.
- The **power management** angle is missing. WiFi modules have `WoWLAN` (Wake-on-WLAN), `keep-power-in-suspend` is in DT but not explained. One paragraph linking back to Ch 51B.

---

## Ch55F — Cellular modems

### AI wording / sledgehammer / buzzwords

- > "Bringing one up correctly the first time saves weeks of customer-side debugging."
  - Rewrite: "Getting the bring-up right early avoids weeks of customer-side debugging."
- > "QMI is the modern industry-standard for Linux; default to that unless you have a specific reason."
  - Rewrite: "QMI is the standard mode for Linux today. Use it unless you have a specific reason not to."
- > "Manual is fragile. ModemManager is the way."
  - Rewrite: "Manual setup is fragile. Use ModemManager when you can."
- > "PPP is slow (~10 Mbit/s max) and adds latency. Use only for old modems without USB."
  - Rewrite: keep — already plain.

### ESL readability

- > "Bench testing failures are almost always power."
  - Rewrite: "Most bench-test failures are power-related."
- > "EC25 alone exposes 4 USB modes (RNDIS, ECM, QMI, MBIM) — pick wrong and nothing works."
  - Rewrite: "The EC25 alone exposes four USB modes: RNDIS, ECM, QMI, MBIM. The wrong choice produces no working interface."
- > "Cost: ~$0.05."
  - Rewrite: "(SMS cost is around $0.05 per message on most carriers.)"

### Needs more explanation

- §55F.2 — the **`qmi_wwan` driver** is named but the role of the kernel vs user-space is not explained. The kernel handles data-path packet shuttling between `wwan0` and the USB control endpoints; ModemManager handles the QMI session setup on `/dev/cdc-wdm0`. The reader should know which side does what.
- §55F.4 "raw-ip mode": one of the most common bring-up bugs is QMI default = `802.3-ethernet` mode but newer modems require `raw-ip`. The chapter mentions it but does not explain the *symptom* (you get an interface, get an IP via DHCP, then no traffic flows because the modem is stripping/adding Ethernet headers the kernel does not). Spell it out.
- Missing: **MBIM** is named but never demonstrated. MBIM is the USB-CDC-standardised alternative to QMI, especially for Windows-friendly modems. One paragraph.
- §55F.5 PPP — the `pppd` chat-script flow needs at least one line on what PPP actually is (HDLC framing over serial, IPCP for IP negotiation). Otherwise it looks like magic init strings.
- **eSIM / iSIM** — modern modems may not have a removable SIM. Worth a single sentence forward reference.

---

## Ch55G — Multi-touch (GT911)

### AI wording / sledgehammer / buzzwords

- > "the **ubiquitous** Goodix GT911"
  - Rewrite: "the common Goodix GT911"
- > "Old code uses MT-A (sliding-window protocol); new code uses MT-B (cleaner, easier)."
  - Rewrite: "Older code uses MT-A. Current code uses MT-B."
- > "the touch's reported value isn't linearly mapped to display pixels."
  - Rewrite: "the touch values are not linearly mapped to display pixels."

### ESL readability

- > "**`reg = <0x5d>` or `<0x14>`** — GT911 has two I²C addresses; the IRQ pin level at reset selects. 0x5d when IRQ low, 0x14 when high."
  - Rewrite: "**`reg = <0x5d>` or `<0x14>`** — the GT911 has two I²C addresses. The IRQ pin level at reset selects which: 0x5d when IRQ is low, 0x14 when IRQ is high."
- > "The order of bringing up RST and INT *during reset* selects the I²C address. The driver handles this dance."
  - Rewrite: "The driver bring-up sequence for RST and INT selects the I²C address. The driver handles this for you."

### Needs more explanation

- §55G.1 MT-B vs MT-A — `ABS_MT_TRACKING_ID` is shown in the event sequence but never explained: it is a per-contact persistent ID that user-space uses to track "the same finger" across frames. The driver assigns it; releasing the finger sets it to -1. This is the *core* of MT-B and the chapter shows it without naming it.
- Missing entirely: the **input subsystem stack** — `evdev` (/dev/input/eventN), `libinput` (the user-space library that consumes evdev), the kernel input core, the device class. The chapter sits on top of all of these without naming them. One paragraph would orient an ESL reader.
- **Palm rejection** and **touch tuning** (`touchscreen-fuzz-x/y`, `touchscreen-fuzz-pressure`) are common GT911 properties. Worth a line.
- The **rotation interaction with DRM** is missing. If the display is rotated 90 degrees via DRM, touch coordinates need the same rotation. This is currently done in libinput or in the compositor, not in DT. Forward-reference Ch 54.

---

## Ch55H — RGB-to-HDMI bridge (SiI902x)

### AI wording / sledgehammer / buzzwords

- > "Drops onto any i.MX6ULL board."
  - Rewrite: "It works on any i.MX6ULL board with LCDIF pinmux available."
- > "Three nodes form the graph: LCDIF → SiI902x → HDMI-connector. DRM bridge chain wires them."
  - Rewrite: "Three DT nodes form the graph: LCDIF, SiI902x, and the HDMI connector. The DRM bridge chain wires them together."
- > "But: i.MX6ULL's LCDIF clocks ceilings at ~80 MHz pixel clock."
  - Rewrite: "However, the i.MX6ULL LCDIF tops out at about 80 MHz pixel clock." ("clocks ceilings at" is awkward.)
- > "tiny, ~$2 chip"
  - Rewrite: "small, low-cost (~$2) chip"

### ESL readability

- > "Linux's DRM framework chains bridges automatically; you describe the chain in DT and the driver activates appropriately."
  - Rewrite: "DRM chains bridges automatically. You describe the chain in DT and the driver does the rest."
- > "**Output looks blank but kernel says 'modeset OK.'** Often the HDMI receiver is using a different format than the bridge is sending."
  - Rewrite: "**Modeset reports OK but the screen stays blank.** Often the HDMI sink is expecting a different pixel format than the bridge sends."

### Needs more explanation

- §55H.3 — **EDID** is mentioned twice but never explained. EDID is a 128/256 byte block the sink exposes over the DDC I²C lines. It lists supported modes and timings. The bridge driver reads it and feeds it into DRM's mode list. Without this paragraph, the term is opaque.
- The **bridge chain** is the key DRM concept this chapter is teaching but it gets one sentence. Expand: a "bridge" is a DRM object that sits between the CRTC and the connector and transforms the signal. Chains can be multiple bridges (e.g., RGB → LVDS bridge → LVDS → HDMI bridge → HDMI). Each bridge has `.attach`, `.mode_set`, `.enable`, `.disable` callbacks. The DRM core calls them in order on modeset.
- **HPD handling** deserves a paragraph. The chapter mentions the IRQ but does not show what the kernel does on the IRQ: schedule `drm_kms_helper_hotplug_event`, which re-reads EDID and triggers a userspace uevent that compositors listen for. This is how plugging a monitor "just works" in Wayland.
- The **DRM "bridge vs panel vs encoder vs connector"** distinction is the single confusion point. The same chip can be modeled three ways depending on the era of the driver. One paragraph clarifying which the SiI902x driver actually does (a bridge that also implements a connector).

---

## Ch55I — Rust for Linux

### AI wording / sledgehammer / buzzwords

- > "Rust as a second-class citizen language inside the kernel"
  - Rewrite: "Rust as a second supported language inside the kernel" ("second-class citizen" is loaded and a little dismissive.)
- > "the security cost of these bug classes is colossal"
  - Rewrite: "these bug classes account for a large share of kernel CVEs"
- > "Classes of 'did you forget to init?' bugs vanish."
  - Rewrite: "The 'did you forget to init?' bug class is no longer expressible."
- > "No more 'did I forget to check this errno?' — the compiler insists."
  - Rewrite: "You cannot silently ignore an error — the compiler will not let you."
- > "Not a wave."
  - Rewrite: "Adoption is slow." (Short editorial fragments like "Not a wave." are a Claude tic.)
- > "**For the i.MX6ULL specifically**: Rust isn't usable yet (ARM32 not supported)."
  - Rewrite: "**On the i.MX6ULL specifically**, Rust is not usable yet — ARM32 is not supported."

### ESL readability

- > "A whole class of C kernel bugs — use-after-free, double-free, data races on shared memory, integer overflows — become *unrepresentable* in safe Rust."
  - Rewrite: "A whole class of C kernel bugs becomes impossible to write in safe Rust: use-after-free, double-free, data races on shared memory, integer overflows."
- > "Rust safety is contingent on *correctly written* unsafe code."
  - Rewrite: "Rust safety depends on the `unsafe` blocks being correct. Bugs inside `unsafe` are no different from C bugs."
- > "The compiler refuses to call `.read()` on an uninitialised device."
  - Rewrite: "The compiler refuses to compile a call to `.read()` on an uninitialised device." (Compilers do not call; they accept or reject.)

### Needs more explanation

- §55I.1 should also note the **distinction between `kernel::` safe wrappers and `bindings::` raw C bindings**. Most beginners try to call C from Rust directly and end up writing huge `unsafe` blocks; the design point is that the kernel team writes the safe wrapper once, then drivers use only safe APIs.
- §55I.4 type-state example: the example uses `PhantomData<S>` but does not explain it. ESL reader has no chance. One sentence: "`PhantomData` is a zero-size marker that tells the compiler 'this type behaves as if it owned an S' for the borrow checker. It generates no code at runtime."
- §55I.5 the **`pin-init`** crate is one of the biggest practical hurdles in current kernel-Rust (because most kernel objects must be initialised in place, not moved). A paragraph would help readers who try to write a driver and immediately hit `Pin<&mut T>`.
- The chapter does not contrast Rust **module signing / kbuild integration** with C modules. Rust modules still produce a `.ko` with the same module loader interface; the only difference is the build path. Worth one line so readers do not think Rust modules need a separate loader.
- **GPL compatibility** is mentioned ("license: 'GPL'") but not explained: the kernel only links GPL-licensed Rust modules to its GPL-only symbols. A non-GPL Rust module is restricted to a smaller API. Same as C, but worth noting.



---

# Part VIIa — Style/ESL Review (Ch 64–81 Cookbook)

## Cross-cutting patterns

- **Em-dash chaining is the dominant tic.** Every chapter uses " — " two or three times per paragraph to glue clauses. Often this should be a period. Examples flagged below per chapter; the pattern is everywhere.
- **Semicolons gluing two clauses.** Less than Parts II–V but still common, particularly in `Pitfalls` bullets ("X happens; Y is the fix"). Period reads better for an ESL reader.
- **"Not X — Y" / "Not X. It's Y." sledgehammer.** Recurring in chapter intros, "why" boxes, and physics explanations (Ch 69 "wrong by design", Ch 71 "this isn't X. It's Y.").
- **AI buzzwords that survived past Part VI**: `internalise`, `mechanical` (used as praise), `canonical`, `idiomatic`, `magic`, `magical`, `proper`, `genuinely`, `essentially`, `effectively`. Several chapters also use `traceable`, `non-trivial`, `radically different`, `clarifying`. Cull on a pass.
- **Cliché phrases.** "the workhorse bus" (Ch 64/65/70), "the right starting point" (Ch 67), "the magic" / "where the magic happens" (Ch 67, 73, 78), "a masterclass", "the heart of the framework" (Ch 64). All marketing-flavor.
- **Royal "we / let's"** still leaks in: "Let's prove we understand…" (Ch 65, 67), "Let's walk…" (Ch 64), "we'll write" (most chapters). Replace half with an imperative or just drop.
- **Triplet rhythm in lab/pitfall bullets.** "X. Y. Z." constructs (e.g. Ch 67 "you understand the chip"; Ch 76 "Measure, log, alert."). Once per chapter is fine; multiple is AI cadence.
- **"That's it." / "That's the whole protocol." / "That's the whole game."** Used at the end of subsections all over Ch 64–69. Pick one per chapter, drop the rest.
- **Editorialising tone slips in** ("wrong by design", "honest pedagogy", "marketing", "placebo", "fan-prose", "honestly", "don't experiment with…"). Some is fine for personality but it appears too often and reads opinionated rather than instructional. Cut where the technical point stands without it.
- **Bullet-as-prose sentences.** Particularly in intros ("Why" boxes) — long sentences listing 4–6 items separated by commas. Break or bullet.
- **"Build, load, exercise:" / "Build, load, test:" header.** Repeated verbatim in every from-scratch chapter (Ch 64, 65, 67, 68, 69, 70…). Vary: "Build and load." / "Bring it up." / "Try it."

## Ch64 — QSPI NOR flash

### AI wording / sledgehammer / buzzwords
- > "The mainline driver wraps this in regmap-like abstractions and parameter databases, but the wire protocol is dead simple."
  - "Dead simple" is informal English. Rewrite: "The mainline driver wraps this in abstractions and a parameter database, but the wire protocol itself is small."
- > "That's basically the entire interface."
  - "Basically" + cliché. Rewrite: "That is the full interface."
- > "If you ever encounter a chip that *isn't* in the database, you'll know how to add it (or replace the framework entirely with 200 lines)."
  - Boastful. Rewrite: "If you encounter a chip that is not in the database, you can add an entry — or replace the framework with about 200 lines of your own."
- > "**a NOR flash is a state machine driven by single-byte commands**. `0x9F` = read JEDEC ID. ..."
  - The triplet/quartet of `0x..` = X lines reads as a slogan. Keep the lead sentence; collapse the examples into a single line: "Common commands: `0x9F` JEDEC ID, `0x06` write-enable, `0x20` sector erase, `0x02` page program, `0x03` read."
- > "This is the heart of the framework: a polling loop that yields the CPU between checks."
  - "Heart of the framework" is cliché. Rewrite: "This polling loop is what makes the framework work on Linux: it yields the CPU between checks."
- > "Pedagogically, ordinary SPI is the right choice for this from-scratch driver."
  - "Pedagogically" is academic. Rewrite: "For this teaching example, ordinary SPI is the right choice."

### ESL readability
- > "QSPI NOR fits when storage need is < 32 MB, you want fast/deterministic boot, you want a soldered theft-resistant device, and you're not storing much user data."
  - 33-word bullet-as-prose, mixed comma grammar. Break: "QSPI NOR fits when your storage need is under 32 MB, when you want a fast, deterministic boot, when you want a soldered device that resists theft, and when there is little user data to store."
- > "(so they're HIGH while still in 1-bit / single-IO mode at boot — quad mode hasn't been enabled yet, IO2 acts as /WP, IO3 as /HOLD; both active-low, so pulled HIGH means 'not asserted')."
  - 38-word parenthetical with two em-dashes and a semicolon. Break out of the parenthesis: "These pull-ups keep IO2 and IO3 HIGH while the chip is still in single-IO mode at boot. Quad mode is not enabled yet, so IO2 acts as /WP and IO3 as /HOLD. Both are active-low, so 'HIGH' means 'not asserted.'"
- > "The page-boundary clamp in step 1 is critical — NOR chips wrap *within a page*: programming with an address of 0xFE and 4 bytes of data writes the last 2 bytes at 0xFE, 0xFF, then the next 2 bytes back at 0x00 and 0x01. Silent corruption."
  - Good content but dense. Rewrite: "Step 1's page-boundary clamp matters because NOR chips wrap *within a page*. If you program at address 0xFE with 4 bytes of data, the last 2 bytes go to 0xFE and 0xFF, then the next 2 bytes wrap back to 0x00 and 0x01 of the same page. Silent corruption."

### Needs more depth
- §64.6 mentions `spi_mem_op` and `spi_mem_exec_op` as "translating into whatever the underlying SPI/QSPI controller wants" — but the reader has not seen `spi_mem` before. One paragraph: `spi_mem` is the kernel's abstraction for "memory-mapped-style flash commands" (cmd + addr + dummy + data). On a plain SPI controller it falls through to `spi_message`s; on a dedicated QSPI controller it programs the controller's LUT. The mainline `spi-nor` is written against `spi_mem` so a single driver works on both.
- §64.8 MTD partitioning interacts with the U-Boot environment partition, but the chapter never explains *what U-Boot does with these partitions at boot* before showing the partition table. Add one sentence linking `partition@100000` ("u-boot-env") to the `fw_setenv` step in §64.10: "U-Boot reads its environment from this region at startup via raw `sf read`; Linux uses `fw_setenv` to update it from user-space. Both sides must agree on the offset — that is what `fw_env.config` is for."
- §64.9 XIP: "instruction-cache misses are expensive" is named but the *why* is not explained for an MCU reader who has seen XIP on Cortex-M before. One sentence: "On Cortex-A, an I-cache miss that hits QSPI stalls the pipeline for the chip's read latency — tens of ns at 80 MHz QSPI, versus single-digit ns from DDR3. A loop that misses cache repeatedly is the bottleneck."

## Ch65 — I²C / SPI EEPROM

### AI wording / sledgehammer / buzzwords
- > "The protocol is *trivial*; writing your own driver in 100 lines is genuinely possible and clarifying."
  - "Genuinely", "clarifying" both AI-flavored; semicolon. Rewrite: "The protocol is small. Writing your own driver in 100 lines is realistic and worth the time."
- > "Master those and the rest is byte arithmetic."
  - "Master those" is consultant-speak. Rewrite: "Get those two right and the rest is byte arithmetic."
- > "EEPROM is the 'metadata anchor' of an embedded board"
  - "Metadata anchor" is a coined phrase. Rewrite: "EEPROM is the place embedded boards store small permanent facts about themselves — MAC address, board serial, calibration."
- > "After this chapter the kernel's `at24.c` will look like ordinary plumbing, not magic."
  - "Magic" again. Rewrite: "After this chapter the kernel's `at24.c` will read as ordinary code, not a mystery."
- > "That's the whole driver. ~50 lines of meaningful code; the rest is parameter tables, DT plumbing, and edge-case handling…"
  - "That's the whole driver" + semicolon. Rewrite: "That is the whole driver. Around 50 lines of real code. The rest is parameter tables, DT plumbing, and edge cases (multi-address chips, write-protect GPIOs)."
- > "Same chip, more features."
  - Fragment-as-tagline. Rewrite: "Same chip, more features available." Or drop entirely.
- > "the production pattern — own it."
  - "Own it" is idiomatic American English. Rewrite: "this is the production pattern — get familiar with it." Or just: "This is the production pattern."

### ESL readability
- > "Then the chip enters **internal write cycle** for ~5 ms. During this time it **NACKs every I²C transaction**. The host polls (issues address-write, sees NACK, retries) until it gets an ACK — that's 'ACK polling,' the standard way to know the write finished."
  - "ACK polling" is named at the end of a 60-word block. Rewrite leading with the name: "After the data bytes, the chip starts an *internal write cycle* of about 5 ms. During this time it NACKs every I²C transaction. The host keeps issuing address-write transactions; each NACK means 'still writing,' and the first ACK means 'done.' This is called **ACK polling**."
- > "Multiple EEPROMs on one bus. Strap each chip's A0/A1/A2 differently to give unique addresses (0x50–0x57). If two chips share an address, neither responds correctly."
  - Three sentences fine; keep.
- > "Reads return all-0xFF forever; writes silently fail. Tie WP low, or wire to a GPIO with default-low."
  - Semicolon + idiom ("default-low"). Rewrite: "Reads return all-0xFF and writes silently fail. Tie WP low, or wire it to a GPIO that defaults to low."

### Needs more depth
- §65.4 page-boundary explanation: the bytes "indexed 0x08" wrap back to "0x00" — but the *underlying mechanism* (each chip's write buffer is page-sized; the chip's address counter is only `log2(page_size)` bits wide) is not stated. One sentence: "The chip latches incoming bytes into a one-page RAM buffer; the buffer's address pointer is only as wide as `log2(page_size)` bits. After the last page byte, the pointer rolls over inside the page, not into the next page. The full byte address is only loaded once at the start of the transaction."
- §65.7 the **nvmem** subsystem is introduced as "an nvmem provider" without saying *what nvmem is*. Add a one-paragraph aside: "nvmem (Non-Volatile MEMory) is a tiny subsystem that lets one driver (the EEPROM, in this case) publish typed byte-regions called 'cells', and another driver (the Ethernet MAC) consume them at probe. The DT `nvmem-cells` / `nvmem-cell-names` properties on the consumer side wire them together. This decouples the MAC driver from where the MAC address physically lives — could be EEPROM, eFuse, or an OTP region."

## Ch66 — SD card and eMMC

### AI wording / sledgehammer / buzzwords
- > "**Writing one from scratch in a chapter is not honest pedagogy.**"
  - "Honest pedagogy" is academic. Rewrite: "Writing one from scratch in a single chapter is not realistic."
- > "What we *can* do — and what's productive — is **trace a single `read()` through the layers**"
  - Em-dash insertion + "productive" feels like a slide. Rewrite: "What we *can* do is trace a single `read()` through the layers."
- > "Dooms you to field failures or wasted engineering."
  - Overdramatic. Rewrite: "Picking wrong leads to field failures or wasted engineering effort."
- > "SD cards die. Often. In ways that surprise engineers used to flash chips:"
  - Triplet-fragment style, very common AI cadence. Rewrite: "SD cards fail often, in ways that surprise engineers used to flash chips."
- > "Make the engineering call early."
  - Consultant tagline. Rewrite: "Decide between SD and eMMC at schematic time, not after the first field unit fails."
- > "**That's the abstraction**."
  - Slogan. Rewrite: "That is the abstraction." Or drop and keep the next sentence.
- > "(soldered eMMC at HS200, 5-year industrial life)"
  - "5-year industrial life" is marketing claim and bare. Rewrite: "rated for 5+ years of continuous service in industrial-grade parts."

### ESL readability
- > "Card-detect ignored; system keeps trying after card removal."
  - Telegraphic. Rewrite: "The card-detect signal is ignored, so the system keeps trying to talk to the slot after the card is removed."
- > "eMMC `fsync` does a real flush-to-flash cycle (10s–100s of ms). If your app fsyncs after every write, performance tanks. Batch writes."
  - "Tanks" + fragment. Rewrite: "eMMC `fsync` does a real flush-to-flash, which takes 10 to 100 ms. If your application calls `fsync` after every write, throughput drops sharply. Batch your writes."
- > "A power loss can corrupt a *bigger area than you wrote*. Industrial eMMCs (Micron e.MMC, KIOXIA) have PFAIL protection; consumer ones don't."
  - Semicolon. Rewrite: "A power loss can corrupt a wider area than you actually wrote. Industrial eMMCs (Micron, KIOXIA) include PFAIL protection. Consumer parts do not."

### Needs more depth
- §66.3 speed-mode table mentions "UHS-I voltage switch" for SDR104 without explaining it. One paragraph: "Before SDR104, the bus runs at 3.3 V. To enter SDR104 the host issues CMD11 (SWITCH_VOLTAGE), the card pulls DAT0 low to confirm, the host re-clocks at 1.8 V on the VQMMC rail. The `vqmmc-supply` regulator must be able to make this 3.3 V → 1.8 V switch under software control; a fixed 3.3 V regulator leaves the controller stuck at slower modes."
- §66.4 the `pinctrl-1` / `pinctrl-2` mechanism is mentioned ("different pin slew rates at higher speeds") but the *Linux concept of multiple pinctrl states* is hidden. For someone who has only seen `pinctrl-0` it deserves one sentence: "`pinctrl-names = \"default\", \"state_100mhz\", \"state_200mhz\"` defines three named pin states. The driver switches between them via `pinctrl_select_state(p, state)` as the bus clock changes; faster modes need lower drive strength and tighter slew." (Then cross-link to Ch 44.)
- §66.7 EXT_CSD output reads as if `mmc extcsd read` is built in. Add one sentence: "`mmc` is from the `mmc-utils` package — not installed by default on most distros. Build from `git://git.kernel.org/pub/scm/linux/kernel/git/cjb/mmc-utils.git`."

## Ch67 — Temperature / humidity / pressure

### AI wording / sledgehammer / buzzwords
- > "By writing one from scratch you internalise both the chip and IIO."
  - "Internalise" again. Rewrite: "Writing one from scratch teaches you both the chip and IIO at the same time."
- > "Understanding this — and that the formula is in the *driver*, not the *chip* — is the whole game."
  - "The whole game" cliché. Rewrite: "Understanding this — that the compensation formula lives in the *driver*, not the *chip* — is the key insight."
- > "It's *not* an approximation we made up. It's lifted byte-for-byte from the Bosch datasheet's pseudocode, page 25."
  - Defensive tone. Rewrite: "These formulas are not approximations. They are lifted byte-for-byte from page 25 of the BME280 datasheet."
- > "Those are framework concerns, not 'do you understand the chip' concerns. You understand the chip."
  - Two-fragment slogan ending. Rewrite: "Those are framework features, not chip-understanding features. The chip is what we set out to teach."
- > "A working IIO driver that exposes temp + humidity + pressure"
  - Triplet-as-spec; fine, keep.
- > "Sensirion's philosophy: less state in the chip, more in the host."
  - "Philosophy" is grand. Rewrite: "Sensirion's design choice: keep state in the host, not the chip."
- > "The 'everyone's hobbyist humidity sensor.'"
  - Idiomatic English. Rewrite: "The default cheap humidity sensor on hobbyist boards."

### ESL readability
- > "User-space reads `/sys/bus/iio/devices/iio:device0/in_temp_input` → driver issues 'forced measurement,' waits ~8 ms, reads the 8 raw bytes, applies the compensation formula, returns '23420' (mC)."
  - Bullet-as-prose with arrow notation. Break: "When user-space reads `/sys/bus/iio/devices/iio:device0/in_temp_input`, the driver issues a 'forced measurement,' waits about 8 ms, reads the 8 raw bytes, applies the compensation formula, and returns `23420` (millidegrees Celsius)."
- > "The H and T raw values are 20-bit, packed across 5 bytes with a nibble split at byte 3."
  - "Nibble split" is jargon-y for ESL. Rewrite: "The H and T raw values are 20 bits each. They share a middle byte: the top 4 bits go to H, the bottom 4 bits to T."
- > "Ten minutes of work once you've done BME280."
  - Marketing claim. Rewrite: "After the BME280 driver, converting to AHT20 is mostly mechanical command-table substitution."

### Needs more depth
- §67.4 mentions "regmap" prominently as the abstraction but the BME280 mainline glue (`bmp280-i2c.c`) creating a regmap is treated as a one-liner. For the reader to understand why this is a win, one sentence: "The same `bmp280_common_probe` is called from `bmp280-spi.c` with a regmap built via `devm_regmap_init_spi` instead — and not a single line in the chip logic changes. That is the bus-decoupling regmap buys you."
- §67.4 compensation formulas with `t_fine` — the *reason* `t_fine` is a 32-bit "intermediate temperature value" tied to pressure/humidity compensation is mathematical (temperature affects gas density which affects pressure, and the saturation-vapor curve depends on T). One sentence helps the reader trust the cross-coupling: "The chip's sensors are physically affected by die temperature, so the pressure and humidity formulas use the temperature result via the shared `t_fine` intermediate. Always compute temperature first."
- §67.6 SHT3x "clock-stretching" appears once in the protocol table; no explanation of what clock-stretching is for an MCU reader who only knows fast I²C. One sentence: "Clock stretching is the slave holding SCL low to make the master wait — typically because the slave is busy with an internal measurement. The master's controller must tolerate SCL low for tens of ms. Some controllers time out; i.MX6ULL handles it correctly."

## Ch68 — Light & color sensors

### AI wording / sledgehammer / buzzwords
- > "After this chapter you can pick a sensor by understanding the trade-offs, and write your own driver for any of them."
  - Marketing. Rewrite: "After this chapter you can pick a sensor by its trade-offs, and write a driver for any of them."
- > "Internalise this hierarchy and you'll never trust an 'eCO₂' reading on its face again."
  - "Internalise" + idiom ("on its face"). Rewrite: "Once you see this hierarchy, you stop trusting 'eCO₂' as if it were a CO₂ reading." (This sentence is actually from Ch 69 — flag in that chapter; remove the duplicate critique here.)
- > "Light is non-trivial."
  - "Non-trivial" is overused. Rewrite: "Measuring light is harder than it looks."
- > "**Integration time governs both noise and saturation**."
  - Bold-as-slogan. Keep but soften the sentence around it: "Integration time controls both noise floor and saturation point."
- > "The 'right' integration time depends on what you're trying to measure."
  - Hedge ("the right"). Rewrite: "Pick integration time for the range you care about."
- > "The user never sees the lambdaweighting; it's all hidden."
  - Typo ("lambdaweighting") *and* semicolon *and* "magic" subtext. Rewrite: "The user never sees the wavelength weighting; the driver does it. Just `cat in_illuminance_input` gives lux."
- > "(BH1750 is unusual: it has no register map.) ... That's it. Two bytes on the wire, one division."
  - "That's it" + fragment. Rewrite: "Two bytes on the wire and one division — that is the whole protocol."

### ESL readability
- > "Different sensors solve this differently — BH1750 uses an analog filter, TSL2561 measures broad+IR and subtracts, VEML7700 uses an integrated correction."
  - Bullet-as-prose with three options. Bullet for real or rewrite: "Different sensors solve this differently. BH1750 uses an analog filter. TSL2561 measures a broadband channel and an IR channel and subtracts. VEML7700 uses an integrated correction."
- > "**Optical filter** (BH1750, VEML7700, TCS34725 clear channel): a colored glass cover on the die that approximates the photopic curve. Cheap, fixed."
  - Fragment ("Cheap, fixed.") for emphasis is fine once; this construction repeats three times in this list. Vary the third one.
- > "Bouncing between integration times causes flicker in the lux reading."
  - Idiomatic ("bouncing"). Rewrite: "Switching back and forth between integration times causes flicker in the reported lux."

### Needs more depth
- §68.2 the **CIE photopic curve** is named but never shown or described in numbers. A 4-line table — wavelength vs. relative response at 400 / 450 / 500 / 555 / 600 / 650 / 700 nm — anchors the abstract idea. ESL reader will benefit hugely.
- §68.4 the BH1750 mainline driver exposes raw + scale, not `_processed`. For an ESL reader new to IIO, the *difference* between `_raw + _scale + _offset` and `_processed` is worth one explicit sentence: "`_raw` is the chip's count. `_scale` is the conversion factor. `_processed = raw * scale + offset`, already in the unit named by the channel. Drivers expose one or the other; mainline `bh1750` exposes raw+scale (more flexible), the from-scratch one exposes processed (simpler)." Then mention `_offset` for completeness.

## Ch69 — Air quality / gas / PM

### AI wording / sledgehammer / buzzwords
- > "**NDIR is physics; metal-oxide is correlation; laser scatter is counting**."
  - Triplet with semicolons. Strong slogan but reads AI. Rewrite: "NDIR measures physics directly. Metal-oxide infers from a correlation. Laser scatter counts particles. Three very different things wearing the label 'air quality sensor.'"
- > "Internalise this hierarchy and you'll never trust an 'eCO₂' reading on its face again."
  - Already flagged: "internalise" + idiomatic "on its face". Rewrite: "Once you see this hierarchy, an 'eCO₂' reading reads as 'rough VOC trend that someone scaled into CO₂-looking numbers,' not as a CO₂ measurement."
- > "Expensive but honest."
  - Editorialising fragment. Rewrite: "Expensive but accurate."
- > "If your product advertises 'CO₂ sensor,' use SCD30, not CCS811."
  - Fine; keep. Useful concrete rule.
- > "Don't claim 'this is CO₂.'"
  - Fragment as caution. Rewrite: "Don't label CCS811 output as 'CO₂' to end users."
- > "Wrong by design when you have non-human VOC sources (cooking, cleaning, painting)."
  - "Wrong by design" is editorial. Rewrite: "Inaccurate by construction whenever a VOC source other than human breath is present — cooking, cleaning, painting all corrupt it."
- > "The whole protocol is a state machine over a UART stream."
  - Trailing slogan. Trim or keep as one sentence per chapter — already there in 64, 65.

### ESL readability
- > "Most products have a 'fan power' pin; cycle it."
  - "Cycle it" idiom + semicolon. Rewrite: "Most products bring out a 'fan power' pin. Toggle it off and on to reset the fan."
- > "(Skipping the CRC bytes at indices 2 and 5; check them and retry on mismatch.)"
  - Parenthetical instruction with semicolon. Rewrite: "Indices 2 and 5 are CRC bytes — skipped here for the value extraction, but check them and retry on mismatch."
- > "Particulate matter ... is calibrated against standard EPA reference. Use that one. The 'standard' column is uncalibrated."
  - Two-sentence pitfall with confusing naming ("standard" column is the uncalibrated one). Add a clarifying parenthetical: "In the frame, the columns labelled *atmospheric* are calibrated against EPA reference — use those. The columns labelled *standard* are uncalibrated (Plantower's chosen naming, not a quality statement)."

### Needs more depth
- §69.3 the chapter mentions "**I²C clock stretching**" with a one-line warning about Raspberry Pi. The MCU reader knows clock stretching as "slave drags SCL low" but may not know how the kernel host driver actually handles it. One sentence: "On i.MX6ULL the uSDHC's I²C blocks support clock-stretching natively — the controller just waits while SCL is held low, no driver intervention needed. The Pi's BCM2835 had a hardware bug where clock-stretching past a few µs broke; Sensirion's SCD30 stretches for tens of ms, which is why this is a recurring gotcha."
- §69.5 **SerDev** appears as a critical concept (the whole from-scratch driver depends on it) and is explained at the end of the chapter (§69.5 last subsection). Move that explanation *before* the code, not after — the reader needs to know what `serdev_device_driver` and `receive_buf` are before reading 100 lines that use them.
- §69.4 CCS811's "ENV_DATA register" cross-coupling with BME280 is mentioned ("feed it temperature and humidity from your BME280, and the chip adjusts its baseline"). Briefly say *what the chip does with it*: "MOX-film resistance is strongly temperature- and humidity-dependent. The driver writing T and H into ENV_DATA lets the chip apply a correction polynomial internally before computing eCO₂/TVOC — it does not change what the film measures, but it cancels the largest systematic error."

## Ch70 — I²C IMUs

### AI wording / sledgehammer / buzzwords
- > "and once you understand it you can use it for any high-rate sensor."
  - Marketing. Rewrite: "Once you understand it, the same pattern works for any high-rate sensor."
- > "**trigger + buffer is the path to thousands of samples per second**."
  - Slogan with "path to". Rewrite: "**Trigger + buffer is how IIO scales to thousands of samples per second.**"
- > "Untenable."
  - One-word fragment for impact; reads AI-emphatic. Rewrite: "Not workable."
- > "invaluable for time-aligned analysis."
  - "Invaluable" again. Rewrite: "essential when you need to time-align across sensors."
- > "The driver doesn't care whether the trigger came from a timer or from the chip's own data-ready IRQ — same handler either way."
  - Fine; keep.
- > "5000 atomic samples — accel + gyro + 64-bit timestamp — captured in 5 seconds. User-space can FFT for vibration analysis, or feed to a Madgwick filter for real-time orientation."
  - Two-sentence brag. Rewrite: "Five thousand atomic samples — accel, gyro, and 64-bit timestamp — captured in 5 seconds. From here, user-space can FFT for vibration analysis or feed a Madgwick filter for orientation."
- > "This is *user-space* math, not driver math. The driver's job is to deliver clean samples; the application owns the fusion."
  - "Owns the fusion" idiomatic; semicolon. Rewrite: "Fusion belongs in user-space, not in the driver. The driver delivers clean samples; the application turns them into orientation."

### ESL readability
- > "For a 1 kHz IMU, a one-sample-per-sysfs-read loop hits the syscall path 1000 times per second per axis. That's ~30 µs per sysfs read × 6 axes × 1000 Hz = 18 % of one CPU just on the syscall overhead."
  - The math line "× 6 × 1000 = 18 %" is dense but clear; keep. The "hits the syscall path" idiom should change: "crosses the syscall boundary 1000 times per second per axis."
- > "Adding a magnetometer gives an Earth-field reference: the chip measures the geomagnetic vector (~50 µT, pointing roughly north + downward). Combined with the accel's gravity vector, the fusion algorithm can pin all three rotational axes."
  - "Pin all three rotational axes" is technical idiom. Rewrite: "Combined with the accel's gravity vector, the fusion algorithm can lock down all three rotation angles — roll, pitch, *and* yaw."
- > "So even at 1 kHz, the CPU only wakes once per sample — and only briefly. Compare to `read()` polling: 30 µs per syscall × 6 channels = 180 µs of CPU per sample (18 %). With trigger+buffer: maybe 5 µs per sample (0.5 %)."
  - "Only briefly" + telegraphic comparison; rewrite to a normal sentence: "At 1 kHz the CPU wakes once per sample for a few microseconds. Compare to `read()` polling, which is 30 µs per syscall and 6 channels = 180 µs per sample, or 18 % of one CPU. Trigger+buffer is closer to 5 µs per sample, around 0.5 %."

### Needs more depth
- §70.4 IIO buffered mode is the main topic of the chapter and explained well, but a few essential terms are unnamed:
  - `scan_elements/*_en` is shown as user-space writes "1" to enable a channel — but the chapter never says "the IIO buffer's *scan mask* is the bitfield of enabled channels." Add one sentence so the reader can grep for `scan_mask` in driver code.
  - `iio_pollfunc_store_time` is named in the probe as the "pre-handler" but never explained. One sentence: "`iio_pollfunc_store_time` is a stock pre-handler that runs in the trigger's hardirq context and timestamps the trigger event. The main handler runs later, in thread context. The pair is the standard top-half / bottom-half split for IIO triggers."
  - `scan_index` and `scan_type` are used in the channel macro but the *layout in the buffer* is left implicit. One sentence: "Each enabled channel's `scan_type` (storagebits) defines how many bytes it consumes in the sample; channels are packed in ascending `scan_index` order; `IIO_CHAN_SOFT_TIMESTAMP(N)` always sits at the end at an 8-byte aligned offset." Important because user-space parsers rely on this contract.
- §70.5 "Two-stage IRQ path" subsection mentions SCHED_FIFO and `IRQ_WAKE_THREAD` but does not cross-link to Ch 43's threaded IRQ discussion. One sentence: "See Ch 43 §43.4.1 for how threaded IRQs work in general; the IIO trigger path is a specialisation of that pattern."
- §70.10 Madgwick — fine to keep at a high level, but the `quat_mul`, `compute_gradient`, `normalize` functions are referenced as if defined elsewhere. Either add one paragraph noting "these are standard quaternion ops; reference implementation at https://x-io.co.uk", or drop the code snippet and just describe the algorithm.

## Ch71 — SPI IMUs

### AI wording / sledgehammer / buzzwords
- > "**the FIFO + watermark IRQ pattern**. Instead of getting an IRQ per sample (8000/s = unacceptable), configure the chip's internal FIFO with a watermark threshold."
  - "= unacceptable" reads as a slide annotation. Rewrite: "Instead of taking one IRQ per sample (8000/s, far too many), configure the chip's internal FIFO with a watermark threshold."
- > "making multi-IMU systems easy."
  - "Easy" is marketing. Rewrite: "which makes multi-IMU systems straightforward to wire."
- > "Distinguishing feature: **two SPI ports**"
  - Slide-bullet fragment. Rewrite: "Its distinguishing feature is two SPI ports."
- > "If you need them, the LSM6DSO is irreplaceable."
  - "Irreplaceable" is dramatic. Rewrite: "When you need FSM or MLC, no other current-production part offers the same."
- > "Beyond ~400 Hz per axis, I²C's 400 kHz × ~10 bits-per-byte budget is exhausted."
  - "Budget is exhausted" idiom for ESL. Rewrite: "Beyond ~400 Hz per axis, you run out of I²C bandwidth: 400 kHz divided by ~10 bits per byte does not leave room for many channels."
- > "CPU load drops 16-fold; data is identical."
  - Semicolon + slogan. Rewrite: "CPU load drops 16-fold, and the captured data is the same."

### ESL readability
- > "The chip IRQs only when N samples have accumulated; the driver drains them all in one SPI burst."
  - "IRQs" as verb + semicolon. Rewrite: "The chip raises its IRQ only when N samples have accumulated. The driver then drains them in a single SPI burst."
- > "ADXL345 outputs *little-endian*; MPU6050 outputs *big-endian*. Easy to swap by accident."
  - Semicolon. Rewrite: "ADXL345 puts data out little-endian. MPU6050 puts it out big-endian. Easy to swap by accident."
- > "Some boards leave /CS floating during SoC reset; chip enters undefined state. Tie /CS HIGH at idle (10 kΩ to VCC or controller-default)."
  - Semicolon + telegraphic. Rewrite: "Some boards leave /CS floating during SoC reset. The chip then sits in an undefined state. Tie /CS HIGH at idle — 10 kΩ to VCC, or rely on the SPI controller's default."

### Needs more depth
- §71.4 the regmap config trick `read_flag_mask = 0x80 | 0x40` is shown without enough context. The MCU reader has seen R/W bit at MSB before, but the *regmap mechanism* (regmap OR's `read_flag_mask` into the register address on every read) is new. One sentence: "Regmap OR's `read_flag_mask` into the register byte for every read, and `write_flag_mask` for every write. Setting both is how you encode the chip's R/W + multi-byte protocol once and forget about it."
- §71.5 the watermark IRQ handler reads the FIFO sample-by-sample in a loop: `for (i=0; i<entries; i++) ma_read(m, REG_DATAX0, sample, 6);`. Each call is one SPI transaction. The mainline driver does a single bulk read of all `entries*6` bytes. Explicitly mention this as a follow-up improvement: "The mainline driver does a single `regmap_noinc_read` of all `entries × 6` bytes in one SPI transaction, instead of one transaction per sample. At 800 Hz × 16-sample watermark, that is one SPI burst vs 16 — measurable CPU saving."
- §71.6 LSM6DSO FSM/MLC mentioned with intriguing examples ("doorbell pressed", "drone has crashed") but no concrete pointer to *how to compile a program for them*. One sentence: "ST's UNICO-GUI tool (`st.com/en/embedded-software/unico-gui.html`) converts a labelled motion dataset to the binary blob the chip executes; the IIO config interface uploads it at runtime via firmware-loader."

## Ch72 — Distance & proximity

### AI wording / sledgehammer / buzzwords
- > "the bane of Linux's preemption"
  - Cute but slangy for ESL. Rewrite: "famously hard to time accurately under Linux."
- > "promise customers ranging accuracy you can't deliver."
  - "Customers" is unusual register; consultant-speak. Rewrite: "promising users a ranging accuracy you cannot actually deliver."
- > "**time-of-flight is electronics; ultrasonic is physics; IR is photometry**."
  - Three-way semicolon triplet. Rewrite: "Time-of-flight measures with electronics. Ultrasonic measures with sound. IR measures with reflected brightness. Three different physics."
- > "The 'magic' of the driver is mostly the tuning-blob loop."
  - "Magic" again. Rewrite: "What looks complex in the driver is mostly the tuning-blob loop."
- > "VL53L0X is *the chip with a firmware blob*."
  - Slide-tagline. Rewrite: "VL53L0X is unusual: it needs a long initial register-write sequence — effectively a firmware blob — uploaded at every probe."
- > "**Bottom line:** don't ship HC-SR04 connected to Linux GPIO."
  - "Bottom line" is corporate-English. Rewrite: "In short: do not ship products with HC-SR04 wired directly to Linux GPIO."
- > "an honest discussion of why HC-SR04 is hard on Linux."
  - "Honest discussion" is editorial. Rewrite: "a clear-eyed look at why HC-SR04 is hard on Linux."
- > "Each driver's complexity reflects this hierarchy."
  - Tidy slogan; harmless once but combined with everything above reads polished. Trim: "Each driver's complexity tracks the physics."

### ESL readability
- > "The chip's own emitter reflects off the inner glass surface; 'or '0 mm' reading forever. Mount with a recessed window or angled cover."
  - Semicolon + jargon-y "recessed window". Rewrite: "The chip's emitter reflects off the inner surface of the glass, and you read 0 mm forever. Use a recessed window or tilt the cover slightly."
- > "Note the **two busy-wait loops** in the kernel. This burns a CPU during the ~25 ms measurement."
  - "Burns a CPU" idiomatic. Rewrite: "The kernel busy-waits in two loops here. That keeps one CPU pinned for the full ~25 ms measurement."
- > "Range = 2 m at indoor light, drops to ~0.6 m in direct sunlight (940 nm ambient noise dominates). Accurate, fast, but more complex than the alternatives."
  - Fragment ending. Rewrite: "Range is 2 m in indoor light. In direct sunlight it drops to ~0.6 m because 940 nm ambient noise dominates. The chip is accurate and fast, but more complex than the alternatives."
- > "User-space converts voltage to mm via the datasheet's piecewise table or polynomial."
  - Fine; keep.

### Needs more depth
- §72.3 the VL53L0X tuning blob is described as "STMicro's IP", not documented. For an ESL/MCU reader, the *practical consequence* of this for the kernel driver is worth one sentence: "The tuning blob is reverse-engineerable from STMicro's open-source `STSW-IMG005` C SDK, which the kernel driver imports. Treat it as a vendor-provided initialization script."
- §72.6 the four options for HC-SR04 timing — PREEMPT_RT, capture-input timer, MCU helper, PRU — are listed but none gets a sense of *which is realistic for a Linux beginner*. Add one ranking sentence: "For learning: PREEMPT_RT + threaded IRQ (option 1) is the lowest-effort path. For production: a $1 MCU helper (option 3) is the standard solution and the one shipped in actual products."
- §72.7 the GP2Y0A's non-linear curve is mentioned but not shown. A small table (5 points: 100 mm, 200 mm, 400 mm, 600 mm, 800 mm → V) gives the MCU reader a concrete sense of "how non-linear" and lets them write the polynomial fit immediately.

## Ch73 — Magnetometer / compass

### AI wording / sledgehammer / buzzwords
- > "Most engineers ship without calibration and wonder why their bearing is off — sometimes they blame the IMU."
  - Editorial swipe. Rewrite: "Many products ship without calibration; their compass is off by 10–30°, and the IMU often gets blamed."
- > "**calibration happens in user-space, but the driver must enable it**."
  - Bold-as-tagline. Slim the surrounding paragraph: "Calibration runs in user-space; the driver's job is to deliver raw X/Y/Z in stable, scaled units."
- > "the most important non-driver content of the chapter"
  - Self-referential. Rewrite: "Most of this chapter is not driver code. It is calibration."
- > "the part everyone skips"
  - Slogan in subsection title. Keep — actually a fine ESL signal that this matters. But change "everyone" to "most products": "Calibration — the part most products skip."
- > "**Trap**: HMC5883L's name is on every $1 eBay 'HMC5883L' breakout. Those modules are *QMC5883L*."
  - Fine; the lead "Trap:" reads like a slide bullet. Rewrite: "Watch for this: every $1 eBay 'HMC5883L' breakout is actually a QMC5883L."
- > "completely unusable for navigation."
  - "Completely unusable" is dramatic. Rewrite: "Heading is wrong enough to be useless for navigation."
- > "**You cannot drive a QMC5883L with HMC5883L code; the chip will appear inert.**"
  - Bold + semicolon. Rewrite: "HMC5883L code does not work on a QMC5883L — the chip will simply not respond."

### ESL readability
- > "The samples will fit on an ellipsoid; you compute: 1. The **offset** ... 2. The **3x3 matrix** to rotate-and-scale the ellipsoid into a sphere — soft-iron correction."
  - The introductory sentence has a semicolon and ends with a colon into a numbered list. Rewrite the lead: "The samples fall on an ellipsoid. From the ellipsoid you compute two things:"
- > "Tilt unaccounted for. XY-only heading assumes the sensor is level. For real attitude-aware compass, use tilt-compensation: combine with accel to project the magnetic vector onto the horizontal plane."
  - Two-fragment lead + colon + jargon. Rewrite: "**XY-only heading assumes the sensor is held level.** If the device can tilt, combine the magnetometer with the accelerometer and project the magnetic vector onto the horizontal plane. This is 'tilt compensation' and it is mandatory for any device a user holds in their hand."
- > "the killer differences"
  - Idiom. Rewrite: "the breaking differences" or just "the differences that matter."

### Needs more depth
- §73.7 the "proper" ellipsoid fit (10 parameters via least-squares) is named but never broken down. For the engineer-at-whiteboard reader, *one* paragraph describing the algorithm at a high level is worth more than the literature pointer: "The full method: collect ~1000 samples spanning all orientations; assemble a 10×N design matrix from each sample's `(x²,y²,z²,xy,xz,yz,x,y,z,1)`; solve the generalised eigenvalue problem to get the ellipsoid's quadratic form; decompose into center (hard-iron offset) and 3×3 symmetric matrix (soft-iron). The matrix's Cholesky factor is the linear map that turns ellipsoid into sphere."
- §73.5 mainline drivers expose `sampling_frequency` etc. but the *relationship between sampling rate and noise floor* for a magnetometer is left out. One sentence: "Higher sampling rate widens the noise bandwidth (noise floor ∝ √Hz). For a stationary compass, ~10 Hz is plenty and gives the lowest noise; for fast-moving gimbals, 100 Hz or higher trades noise for latency."
- §73.10 "Slow rotation during calibration" pitfall — would be much more useful with a *concrete cadence*: "Aim for ~2 full rotations per axis over 30 seconds; faster and you skip arcs of the sphere, slower and bias drift creeps in."

## Ch74 — Hall-effect & rotary position

### AI wording / sledgehammer / buzzwords
- > "**the magnet matters as much as the chip**."
  - Bold tagline. Rewrite: "**The magnet matters as much as the chip — get it wrong and the chip reads garbage.**"
- > "Most 'AS5048 doesn't work' reports trace to magnet selection."
  - Editorial. Rewrite: "Most 'AS5048 doesn't work' threads online trace back to the wrong magnet."
- > "Hall-on-magnet replaces optical encoders for lower cost, infinite life (no slip-rings or photo-emitter aging), and tolerance to oil/dust."
  - 26-word bullet-as-prose. Break: "Hall-on-magnet sensors replace optical encoders. They cost less, last longer (no slip-rings, no aging photo-emitters), and tolerate oil and dust."
- > "Buy a small (6 mm × 2.5 mm) **diametrically-magnetised** disc-magnet separately."
  - Fine; keep.
- > "Default choice."
  - Slogan fragment. Rewrite: "The general-purpose choice." Or just attach to previous sentence.
- > "The 14-bit absolute angle is now in IIO, ready for any consumer."
  - "Ready for any consumer" is consultant-speak. Rewrite: "The 14-bit absolute angle is in IIO, ready for any application that needs it."

### ESL readability
- > "Each SPI frame is 16 bits: ... You send a *command frame* this transaction; the *response* comes in the *next* transaction."
  - "This transaction" / "next transaction" reads awkwardly without articles. Rewrite: "You send a *command frame* in the current transaction. The matching *response* arrives in the next transaction."
- > "Datasheet specifies 1–3 mm typical."
  - Telegraphic. Rewrite: "The datasheet specifies a typical air gap of 1–3 mm."
- > "Hot-plug/start-up race."
  - Pitfall heading fragment. Rewrite: "**Hot-plug / start-up race.** The chip needs about 10 ms after VCC rises. A read earlier returns junk. The mainline driver handles this delay; the from-scratch driver must too."

### Needs more depth
- §74.3 the "two-frame protocol" (command this frame, result next frame) is a real conceptual hurdle for someone used to register-read-returns-value chips. The chapter mentions it but does not say *why* the chip is designed this way. One sentence: "AS5048 returns whatever it has staged in its output register on the *current* SPI clock cycle, while latching the new command for the *next* cycle. The first transaction's response is therefore stale (or zero on the first read after power-up). Always issue a 'priming' read and discard, or expect to ignore the first answer."
- §74.4 the from-scratch driver uses one 4-byte `spi_transfer` to issue command + read response. The mainline `as5048.c` uses two separate `spi_message`s. Worth a sentence: "Combining both frames in a single `spi_transfer` keeps /CS asserted the whole time, which is *not* what AS5048 specifies. Some chips tolerate it; some do not. For correctness, use two separate `spi_message`s with their own CS toggle, or set `cs_change=1` on the first transfer."
- §74.6 TLE5012 "SSC protocol" is named but not explained. One sentence: "SSC is a 3-wire SPI variant where MOSI and MISO share one bidirectional line. The chip drives it during the response phase. This saves a pin but requires the SoC's SPI controller to support tri-state SDI/SDO — i.MX6ULL eCSPI can with extra GPIO management, not natively."

## Ch75 — Current & power monitoring

### AI wording / sledgehammer / buzzwords
- > "the *calibration register* that everyone gets wrong"
  - "Everyone gets wrong" editorial. Rewrite: "the *calibration register* that is the most common bug."
- > "**the shunt converts current to voltage; the chip converts voltage to digital, then divides by shunt to recover current**."
  - Triplet with semicolons. Rewrite: "The shunt converts current to voltage. The chip's ADC converts voltage to a count. The calibration register tells the chip the shunt's value, so the chip can report current directly."
- > "Forget the calibration register and you read garbage scaled by an unknown factor."
  - "Garbage scaled by an unknown factor" is informal. Rewrite: "Without the calibration register, the Current and Power registers read zero (or numbers in unknown units, depending on the chip)."
- > "the part everyone gets wrong"
  - Tagline repeated. Rewrite: "the part most people miss on the first try."
- > "This is the part everyone gets wrong."
  - Same. Pick one and drop the repeated framing.
- > "**Current monitors → hwmon**. IMUs, ADCs, environmental sensors → IIO. Some chips have both drivers (legacy + modern). Don't enable both."
  - Slide-fragment style. Rewrite: "Current monitors live in hwmon. IMUs, ADCs, and environmental sensors live in IIO. A few chips have both drivers — pick one in your kernel config and disable the other."

### ESL readability
- > "The chip's internal `Current` register doesn't measure current directly. It computes: `Current_register = (Shunt_voltage × Calibration_register) / 4096`"
  - Fine; keep.
- > "Where: `Current_LSB` is the unit you want ... `R_shunt` is in ohms."
  - "Where:" is mathematical English. Fine for an engineer.
- > "Common-mode voltage limit. Both INA pins must be within the chip's input range. For a high-side shunt on a 24 V rail, V+ and V− are both around 24 V — INA219 spec'd to 26 V, fine."
  - "Spec'd" idiomatic; em-dash. Rewrite: "Common-mode voltage limit. Both INA pins must sit within the chip's input range. On a high-side shunt at 24 V, V+ and V- are both close to 24 V. INA219 is rated up to 26 V, so that is fine."
- > "Common-mode voltage" is named but not defined for an MCU reader who may not have analog-IC vocabulary. One sentence: "Common-mode voltage is the absolute voltage of both inputs above ground (not the difference between them). High-side shunts have a high common-mode (~VBUS); low-side shunts have a low common-mode (~0 V)."

### Needs more depth
- §75.3 the LSB constants `4096`, `0.04096`, `2048` are called "physical constants of the chip's design" but never traced to a derivation. For a curious reader: "The 4096 divisor in `Current = Shunt × Cal / 4096` comes from the chip's internal 12-bit fixed-point format. The 0.04096 in the calibration formula falls out of `4096 × Current_LSB × R_shunt` after solving for Cal — it carries the constant scaling between the chip's internal counts and SI units of A·Ω."
- §75.6 the hwmon/IIO table is good. Add one row: **"Per-sample timestamp"** — hwmon has none; IIO buffers do. Reinforces the buffering distinction.
- §75.4 the driver writes the calibration as `cal = data->config->calibration_value * 1000000 / data->shunt_uohms`. The DT property `shunt-resistor` is in *micro-ohms*. Worth one sentence in the prose: "The DT binding takes the shunt value in micro-ohms (`shunt-resistor-micro-ohms`). Putting it in micro-units keeps the math integer-only in the kernel and matches Linux convention for sub-SI scaled DT properties."

## Ch76 — Battery fuel gauge + charger

### AI wording / sledgehammer / buzzwords
- > "report 'percent full' to the user *honestly*."
  - "Honestly" editorial. Rewrite: "report 'percent full' to the user accurately."
- > "**`power_supply_class` is how kernel and user-space cooperate on battery state**."
  - Slogan. Rewrite: "The kernel exposes battery state to user-space through `power_supply_class`, the same framework used by laptops, phones, and embedded boards."
- > "ModelGauge's claim to fame"
  - Marketing English. Rewrite: "MAX17048's main selling point" — or drop and just state the facts.
- > "The right choice for a real product."
  - "Real product" is editorial. Rewrite: "The standard choice for production-grade hardware."
- > "**Use BQ24074 for**: any product where the user expects the device to power up immediately when plugged in (and the battery isn't presumed alive)."
  - "Bold-then-colon" slide pattern + nested parenthetical. Rewrite: "Pick BQ24074 for any product that must come up the moment a USB cable is plugged in, regardless of whether the battery is alive."
- > "Standardised. Phones, laptops, IoT — all use this."
  - Fragment tagline. Rewrite: "The naming is standardised across phones, laptops, and embedded boards."
- > "Slow but charming"
  - Editorial. (This is in Ch 77's preview line.) Leave for Ch 77.

### ESL readability
- > "MAX17048's claim to fame: 23 µA standby, no shunt, factory-loaded 'typical Li-ion' model, 'good enough for most products' SoC."
  - Bullet-as-prose with quoted-as-aside. Rewrite: "MAX17048's main selling point: 23 µA standby current, no shunt resistor required, a factory-loaded 'typical Li-ion' model, and SoC accurate enough for most consumer products."
- > "The middle plateau is flat — a small voltage range covers most of the capacity."
  - Fine; keep.
- > "Read at the wrong moment, you tell the user 60 % when actual is 65 %."
  - "Read at the wrong moment" telegraphic. Rewrite: "If you read while a high-current load is active, you may tell the user 60 % when the resting SoC is actually 65 %."
- > "instantaneous readings can wobble ±1 % under varying load."
  - "Wobble" colloquial. Rewrite: "instantaneous readings vary by ±1 % when the load is unsteady."

### Needs more depth
- §76.2 ModelGauge is described as "build an internal model of the cell's V/I/T/SoC relationship". This is the chapter's deep concept and deserves a small diagram (or table) showing how SoC is *not* a function of just V. A 5-row table with (V_cell, load_current, true_SoC) showing the same voltage giving two different SoCs under different loads would land the point much better than the current prose alone.
- §76.4 `power_supply_class` is introduced via the enum and a sysfs example. Missing: *how driver and user-space stay in sync when state changes*. One paragraph: "When the driver detects a state change (charger plugged in, capacity dropped past a threshold), it calls `power_supply_changed(psy)`. The framework sends a uevent on the device; user-space daemons (UPower, systemd) react. This is how 'battery low' notifications appear without any polling on the user-space side. A from-scratch driver should call `power_supply_changed` from an interrupt handler or a polling thread that compares the new reading to the cached old one."
- §76.5 the from-scratch driver returns `POWER_SUPPLY_STATUS_UNKNOWN` for STATUS — but the chapter never wires up the CRATE register to make it real. Either add the 10-line CRATE read + sign-check in the example code, or move that hint into a dedicated "exercise for the reader" pitfall.
- §76.6 TP4056 limitation about "no power-path" is well stated, but the *symptom* on Linux ("boot loops on a deeply-discharged battery") is named without explanation. One sentence: "On TP4056, the SoC's input rail sags as soon as it draws current, because the battery voltage at 2.7 V cannot sustain the load. The SoC resets, releases the load, voltage recovers, the SoC tries again — classic crowbar boot loop. With a power-path charger (BQ24074), the USB input takes over instantly and the SoC sees a stable 5 V regardless of cell state."
- §76.10 "Quick-start without justification" — say *what quick-start does internally* in one line: "Quick-start zeroes the internal accumulators and recomputes SoC from the next ~30 seconds of V/dV samples. Useful right after a fresh cell; harmful in normal operation because it discards the model's learning."

## Ch77 — 1-Wire sensors

### AI wording / sledgehammer / buzzwords
- > "Slow but charming"
  - Editorial. Rewrite: "Slow but easy to wire" — or just drop the adjective and lead with the technical fact.
- > "a brutally honest 'Linux is the wrong host' discussion"
  - "Brutally honest" is editorial. Rewrite: "a clear-eyed look at why DHT22 is a poor fit for Linux."
- > "Get the master right and slaves are trivial."
  - "Trivial" minimizes. Rewrite: "Once the master is reliable, writing a slave driver is short — the w1 core does the work."
- > "**Bottom line: if you see DHT22 in someone's product schematic, suggest a swap to SHT3x.**"
  - "Bottom line" idiom. Rewrite: "**Verdict: if you see DHT22 on someone's product schematic, replace it with SHT3x.**"
- > "**a digital MEMS mic is 'an I²S DAI with no control interface'**"
  - (This belongs to Ch 78.) Same pattern; covered there.
- > "Once you can wire SAI → mic in DT via `simple-audio-card` and capture with `arecord`, you have a working audio-input pipeline."
  - "Once you can…, you have…" reads as a marketing tagline. Rewrite: "Wire SAI to the mic in DT via `simple-audio-card`, then `arecord` captures the audio. That is the whole audio-input pipeline." (Belongs to Ch 78.)
- > "the pretender"
  - Slangy. Rewrite: "the lookalike."
- > "DHT22 borrows the wire and the parasitic power but invented its own timing"
  - "Borrows" / "invented its own timing" is editorial. Rewrite: "DHT22 uses the same physical wiring (one signal line plus ground, with parasitic power) but a different, incompatible bit-framing scheme."

### ESL readability
- > "**edge detection is not the same as edge timing**. The host must drive transitions with ±5 µs accuracy."
  - Strong distinction; keep — but soften the bold-as-slogan style: "Detecting that an edge happened is not the same as knowing *when* it happened. The host must drive transitions with about ±5 µs accuracy."
- > "Once one bit is misread, the whole frame is corrupt (no resync)."
  - "Resync" is jargon; fine but rephrase: "Once one bit is misread, the whole 40-bit frame is wrong — there is no resync point until the next measurement starts."
- > "Acceptable for 'read every 5 seconds'; not acceptable for thousands of reads per second."
  - Semicolon. Rewrite: "Fine for 'read every 5 seconds.' Not fine for thousands of reads per second."

### Needs more depth
- §77.1 the *parasitic-power* concept is mentioned in §77.3 only briefly. For an MCU reader, it deserves one paragraph here: "1-Wire supports a 3-pin mode where VDD is tied to GND at the slave, and the slave draws power from the bus's pull-up during 'high' periods, charging an internal capacitor. This works at low duty cycles. During long operations like a temperature conversion, the master must drive the line *actively high* (not just pull-up) for tens of ms — this is the 'strong pull-up' the chapter mentions in pitfalls."
- §77.3 `w1_reset_select_slave`, `w1_write_block`, `w1_read_block` are listed but the *kthread that calls them* is not explained. The MCU reader, after Ch 41–42, is primed for "what context does my slave driver run in?". One sentence: "The w1 core runs a kthread per master. All slave driver callbacks (sysfs attribute show/store, etc.) run in process context on user-space's request, taking `master->bus_mutex` to serialize with the enumeration kthread."
- §77.6 the four options for DHT22 are listed but for the engineer-reader, one concrete latency number per option would clinch it: "PREEMPT_RT + threaded IRQ: 20 µs typical, 150 µs worst case → ~95 % success rate. Hardware capture timer: ~10 ns resolution → 100 %. MCU helper via I²C: zero Linux timing concern → 100 %. PRU: nanoseconds → 100 %."

## Ch78 — MEMS microphones

### AI wording / sledgehammer / buzzwords
- > "**a digital MEMS mic is 'an I²S DAI with no control interface'**"
  - Bold tagline. Rewrite: "A digital MEMS mic is, from Linux's view, an I²S DAI without any control interface — clocks in, samples out."
- > "From Linux's perspective it's just a slave of the SAI."
  - "From X's perspective" tic. Rewrite: "To the SAI driver, the mic is just an I²S slave."
- > "**don't write this**"
  - Slogan. Rewrite: "Most projects do not need a custom machine driver. Use `simple-audio-card`."
- > "Plays back in stereo on the host."
  - Telegraphic. Rewrite: "The captured file plays back in stereo on the host."
- > "This is the part worth understanding even when you don't write the drivers"
  - Slide-tagline. Rewrite: "Worth understanding even when you do not write the drivers yourself."
- > "70 lines — same shape as Ch 53's WM8960 machine driver but simpler"
  - Editorial brevity. Rewrite: "Roughly 70 lines. Same shape as Ch 53's WM8960 machine driver, only without the codec controls, DAPM widgets, and jack-detection."

### ESL readability
- > "There's no I²C control — the mic has no registers. The wires alone (BCLK, LRCLK, SD, LR-select strap) determine its behavior."
  - Good; keep.
- > "the 24 bits go in the upper bits of the 32-bit container"
  - "Container" is OK but could be clearer: "the 24 audio bits sit in the high 24 bits of the 32-bit slot; the bottom 8 bits are zero."
- > "Configure for S32_LE in ALSA; the 24 bits go in the upper bits of the 32-bit container."
  - Semicolon. Rewrite per above.

### Needs more depth
- §78.4 the `dmic-codec` "fake codec" is a key conceptual hurdle. The chapter says it has no registers but does not say *what its role* in ASoC is. One paragraph: "ASoC's machine driver requires a CPU DAI and a codec DAI; the framework expects both. `dmic-codec` is a stub codec driver that satisfies this requirement without doing anything — it has no register accesses, no DAPM widgets, no controls. Its only purpose is to be the 'other end' of the SAI ↔ codec link in the ASoC framework. A real codec driver would handle volume, jack detection, etc.; here those are all hard-wired in the mic hardware itself."
- §78.5 the SDMA data path is mentioned ("Zero CPU between mic and SDMA; one memcpy per `read()`."). For the MCU reader who learned about DMA in Ch 51, this deserves a cross-link: "See Ch 51.5 for how the SDMA ring buffer between SAI and DDR is built. The audio ALSA pipeline reuses the same generic DMA-coherent ring pattern."
- §78.9 "S32_LE vs S24_LE" — the chapter says "S24_LE *may* work depending on ASoC version" but does not say what to actually do. One sentence: "Set ALSA's format to S32_LE unconditionally; the mainline ASoC core handles the 24-in-32 packing. S24_LE is technically '24 bits in 24 bits' (no padding), which the SAI's TDM-slot config does not support on i.MX6ULL — so use S32_LE."

## Ch79 — Health sensors (PPG)

### AI wording / sledgehammer / buzzwords
- > "**the chip captures light intensity, you compute physiology**."
  - Slogan with bold. Rewrite: "The chip delivers light-intensity samples. Your code turns those samples into heart rate and SpO₂ — the chip cannot do this for you."
- > "Without good signal processing, the readings are garbage — and the chip can't fix bad processing."
  - "Garbage" colloquial. Rewrite: "Without good signal processing, the readings are unreliable. The chip cannot compensate for bad code on the host."
- > "the principle elegant — but the *signal processing* is where the real work lives"
  - "Where the real work lives" idiom. Rewrite: "the principle is simple, but the work is in the signal processing on the host side."
- > "real production systems add: motion artifact rejection ..., auto-gain ..., finger-detection ..."
  - Bullet list fine; the lead "real production systems add" is editorial. Rewrite: "Production systems add motion-artifact rejection (using accelerometer cross-correlation to gate readings during movement), auto-gain (adjusting LED current to keep DC in range), and finger-detection (treating low DC as 'no finger')."
- > "Don't claim 'medical-grade SpO₂' without proper calibration against a reference oximeter."
  - Editorial caution; fine and useful, keep.

### ESL readability
- > "Some of it gets absorbed by blood; the rest reflects/scatters back to a photodiode."
  - Semicolon + slash. Rewrite: "Some of it is absorbed by blood. The rest reflects or scatters back to a photodiode."
- > "The signal is tiny — ~1 % of the DC level. The bulk of what hits the photodiode is the constant amount that gets through tissue."
  - "The bulk of" idiomatic. Rewrite: "The pulsatile signal is small — about 1 % of the DC level. Most of the light hitting the photodiode is the constant amount that passes through tissue without modulation."
- > "Compute: ... 110 − 25·R (empirical for fingertip PPG; calibration-dependent)"
  - Parenthetical with semicolon. Rewrite: "Compute `SpO₂ ≈ 110 − 25 × R`. This linear formula is empirical for fingertip PPG and depends on the specific chip's geometry."
- > "The bulk of what hits the photodiode is the constant amount that gets through tissue. The pulsatile 'AC' component is the interesting bit."
  - "Interesting bit" idiom. Rewrite: "The pulsatile AC component is the signal we actually want."

### Needs more depth
- §79.2 SpO₂ formula `110 − 25·R` is presented with one parenthetical "empirical for fingertip PPG; calibration-dependent." For a chapter that aims at depth, *why* this formula form (linear) versus a polynomial fit deserves one sentence: "The linear approximation is the first-order term of the Beer-Lambert relationship between R-ratio and oxygen saturation, valid in the SpO₂ 70–100 % range. Below 70 %, the curve becomes noticeably nonlinear; pulse oximeters that report low values use a piecewise table instead."
- §79.4 says mainline IIO drivers exist (`max30100.c`, `max30102.c`) but never explains what they expose — only that they leave DSP to user-space. Add one sentence: "The mainline drivers register `IIO_INTENSITY` channels with `IIO_MOD_LIGHT_RED` / `IIO_MOD_LIGHT_IR` and a soft-timestamp channel; the chip's data-ready IRQ drives a triggered buffer. User-space reads `/dev/iio:device0` at the configured sample rate and applies the HR/SpO₂ DSP described in §79.6."
- §79.5 the driver's `mh_read_raw` for `INFO_RAW` returns "the latest" by draining all but one. This is a debatable design choice — sysfs reads should usually return *one* sample, not "whatever is freshest after discarding queued data." Mention the trade-off: "This implementation drains the FIFO down to its last sample on each sysfs read so the user always sees recent data. The alternative (return the next-queued sample) means stale readings during slow polling. Buffered mode is the correct path for high-rate logging — sysfs is meant for the occasional one-shot."

## Ch80 — External ADCs

### AI wording / sledgehammer / buzzwords
- > "saves you from chasing noise in a design that was doomed at the silicon level."
  - "Doomed" dramatic. Rewrite: "saves you from chasing noise that the silicon will never let you remove."
- > "**bits, speed, channels, and simultaneity are independent axes**."
  - Slogan. Trim: "Bits, speed, channels, and simultaneity are independent design axes."
- > "ADS1115 = high-bit, slow, multiplexed. MCP3008 = low-bit, medium-speed, cheap. ADS1256 = very-high-bit, low-noise, slow. AD7606 = high-bit, fast, *simultaneous*."
  - Slide-bullet `=` style. Rewrite as a sentence or a proper bullet list with verbs: "**ADS1115** is high-bit, slow, and multiplexed. **MCP3008** is low-bit, medium-speed, and cheap. **ADS1256** is very-high-bit, low-noise, and slow. **AD7606** is high-bit, fast, and *simultaneous*."
- > "An external ADC ... transforms what's measurable."
  - "Transforms what's measurable" reads like marketing. Rewrite: "An external ADC with a clean reference, a PGA, and more bits lets you see signals the SoC's internal ADC cannot."
- > "the everyday precision choice."
  - Marketing. Rewrite: "the standard precision choice."
- > "beautiful trick"
  - Editorial. Rewrite: "useful trick."
- > "Pick by which axis your application stresses."
  - "Stresses" odd word. Rewrite: "Pick by which axis matters most for your application."

### ESL readability
- > "Each register is 16-bit, **big-endian** on the wire. The MUX field selects which input pair; you re-write Config to switch channels (one conversion at a time — it's multiplexed)."
  - Semicolon + parenthetical. Rewrite: "Each register is 16 bits, big-endian on the wire. The MUX field selects which input pair. To switch channels you re-write Config — the chip handles one conversion at a time, since it is multiplexed."
- > "The Vexc *cancels*. Any noise or drift in the excitation voltage cancels too — the reading depends only on the load, not on the absolute excitation."
  - Em-dash chain. Rewrite: "The Vexc *cancels*. Any noise or drift in the excitation voltage also cancels. The reading depends only on the load, not on the absolute excitation."
- > "A 12-bit ADC with a clean reference, a PGA, and more bits"
  - Fine; keep.
- > "Easy to get backwards. Check the datasheet's 'Operational Status' description carefully (it's counterintuitive)."
  - Two-fragment + parenthetical. Rewrite: "Easy to get backwards. The datasheet's 'Operational Status' description is counterintuitive — read it carefully."

### Needs more depth
- §80.3 the ADS1115 OS-bit semantics are flagged in pitfalls but never resolved in the protocol section. The chapter's own from-scratch driver has a comment "note: OS reads 1 when conversion is DONE in single-shot; check datasheet" — which is exactly the wrong place to leave the reader. Fix in §80.3 with one clear sentence: "In single-shot mode, **writing OS=1** triggers a conversion. **Reading OS** then returns 0 while the conversion is in progress, and 1 once it completes. So your poll loop reads Config and waits for OS to flip back to 1."
- §80.4 ENOB (effective number of bits) appears in the comparison table without definition. For the engineer who has heard 'ENOB' but never quite pinned down: "ENOB is the resolution after subtracting the chip's noise floor. A nominal 24-bit ADC with ~22 ENOB means 2 bits at the bottom are noise — the meaningful range is 22 bits."
- §80.9 ratiometric measurement is well explained, but the *reverse* point — when *not* to use ratiometric — deserves one sentence: "Ratiometric measurement requires the sensor's excitation and the ADC's reference to be the same node. If the sensor is excited by a constant-current source (4-20 mA loops, thermocouples with cold-junction comp ICs), use an absolute reference instead — the ADC measures the actual voltage, not a ratio."

## Ch81 — External DACs + clock generators

### AI wording / sledgehammer / buzzwords
- > "**a DAC is an IIO channel that flows the other way; a clock generator is a clk provider**."
  - Bold-with-semicolon slogan. Rewrite: "A DAC is an IIO channel that flows out instead of in. A clock generator is a `clk` provider."
- > "These three chips fill the gap, and they introduce two frameworks we haven't used: IIO's *output* channels and the kernel's *clk provider* model."
  - "Fill the gap" idiom. Rewrite: "These three chips cover the common cases, and they introduce two new frameworks: IIO's output channels and the kernel's `clk` provider model."
- > "this is one of the cases where 'understand the existing driver, don't replace it' is the right call."
  - "Right call" idiom. Rewrite: "Reimplementing Si5351's PLL math is not a productive exercise — read the existing driver instead."
- > "Two different frameworks, both worth knowing."
  - Trailing tagline. Drop or fold: "These are two different frameworks; both are useful."
- > "the inverse of Chapter 80"
  - Fine; keep.

### ESL readability
- > "MCP4725 can source/sink only ~a few mA. Driving a low-impedance load directly causes the voltage to sag."
  - "Sag" colloquial. Rewrite: "MCP4725 can source or sink only a few mA. Driving a low-impedance load directly causes the output voltage to drop."
- > "Each PLL must run 600–900 MHz internally. Output dividers are 4–2048. Not every frequency is achievable on every output; the driver's solver picks the closest."
  - Semicolon. Rewrite: "Each PLL must run between 600 and 900 MHz internally. The output dividers are 4 to 2048. Not every target frequency is achievable on every output. The driver's solver picks the closest valid combination."
- > "The mainline driver does it."
  - Telegraphic. Rewrite: "The mainline driver implements the solver for you."

### Needs more depth
- §81.3 the IIO output-channel concept is explained at the channel-spec level (`.output = 1`) but the *user-space write semantics* are not pinned down: does writing `out_voltage0_raw` block until the chip has settled? Is there a `write_*_available` for valid range? One sentence: "Writing `out_voltage0_raw` calls the driver's `write_raw` synchronously. For an I²C DAC this returns after the bus transaction completes (~100 µs at 400 kHz); for SPI it is faster. There is no settling-time wait in the framework — the driver should add `udelay` if the chip needs it before the next write."
- §81.6 the **clk framework provider role** is the harder concept of this chapter; the explanation is good but ends abruptly. Add one paragraph naming the three required `clk_ops`: "A clk provider must implement at least `recalc_rate` (report current rate when the framework asks), `set_rate` (program the hardware to a requested rate), and `round_rate` (compute the closest achievable rate without programming). Optional ops include `prepare`/`unprepare` (gate the clock on/off), `enable`/`disable` (the atomic equivalents), and `set_parent` (switch input source). For a simple frequency-synthesizer chip, just `recalc_rate` + `set_rate` + `round_rate` is enough."
- §81.6 `clock-frequency = <100000000>;` in DT — the chapter does not explain *when* the frequency takes effect. One sentence: "`clock-frequency` is a soft hint, applied when the consumer driver enables the clock. If no consumer enables it, the clock stays at the chip's reset default."
- §81.5 AD5663 is mentioned but its actual driver is `ad5446.c`. For someone hunting the source, the name mismatch is a stumbling block. Add: "Confusingly, the mainline driver file is `ad5446.c`, named after the original chip in the family. The probe table inside the file lists every variant — including AD5663 — that shares the same SPI command framing."


---

# Part VIIb — Style/ESL Review (Ch 82–97: displays, touch, cameras, audio, Wi-Fi, Bluetooth)

## Cross-cutting patterns

- **Em-dash overload.** Driver chapters in this batch use " — " several times per paragraph, including triple em-dashes within one sentence. The first two pages of Ch 87, Ch 89, Ch 91 are especially heavy. Convert at least one em-dash per paragraph to a period.
- **Semicolon-glued clauses in `Pitfalls`.** "X happens; Y is the cure." reads AI-flavored. Use a period.
- **"Not X, it's Y" / "Not X — Y" sledgehammer.** Frequent in chapter intros and the "Why" callouts (Ch 82 §82.2, Ch 85 §85.6, Ch 87, Ch 91, Ch 95). Trim.
- **Buzzwords still present.** `crucial`, `essential`, `mandatory` (used 6+ times across Ch 85/87/89/95), `seamless`, `comprehensive` are mostly absent (good). But `landscape`, `realm`, `pivotal` show up in the Wi-Fi/BT chapters' intros. `internalize` / `mental model` is overused throughout this batch.
- **Triplet rhythm.** "X, Y, Z — all from one DT node." / "Three buffers, two pipelines, one mux." / "Pixel, plane, port." Rhythmic but reads AI when stacked.
- **Royal "we'll/let's" overuse.** Common in §X.4 "from scratch" sections ("Let's wire up the codec_dai"). Replace half with imperative.
- **"That's it." / "That's the whole pattern."** Drop most.
- **Cliché phrasing.** "the bread-and-butter HMI display interface" (Ch 82), "the cheapest possible 'real display'" (Ch 85), "alphabet soup of layers" (Ch 91 §91.2), "the kernel's most opinionated subsystem" (Ch 89). All flagged below in their chapters.
- **Bullet-list-as-prose inside §X.0 callouts.** The `> **What:** ...` blockquotes routinely run 60+ words with multiple em-dashes. Break into 2–3 short sentences.
- **Marketing tone on chip pricing.** "$3–6," "$1.50–3," "$5–15" appear in comparison tables and also as ad-copy in prose ("a $2 128×64 OLED"). Keep in tables, drop from prose.

---

## Ch 82 — RGB parallel LCD on LCDIF

### AI wording / sledgehammer / buzzwords
- > "**pixel clock + 6 porch numbers + 3 polarities = a working panel**."
  - Cute formula, but `Focus:` callout reads marketing. Rewrite: "A working panel needs a pixel clock, six porch numbers, and three polarities. That is the entire job."
- > "Get the timings right and the panel works; get one porch wrong and you see a rolling, torn, or blank screen."
  - Semicolon glue + triplet ("rolling, torn, or blank"). Rewrite: "Get the timings right and the panel works. Get one porch wrong and the image rolls, tears, or stays blank."
- > "Transcribing them is the entire job."
  - Bolded sledgehammer (second time in the chapter). Drop the bold, keep the sentence once.
- > "parallel-RGB is the bread-and-butter HMI display interface for i.MX6ULL."
  - Cliché. Rewrite: "Parallel-RGB is the standard HMI display interface for i.MX6ULL."
- > "Unlike a smart SPI panel (Ch 83), a parallel panel has no frame buffer of its own — the SoC continuously streams pixels at the pixel clock, refreshing 60× per second."
  - 31-word em-dash sentence. Rewrite: "A parallel panel has no frame buffer. The SoC streams pixels at the pixel clock and refreshes the glass 60 times a second."
- > "There is no 'smart' negotiation — the numbers must match the glass."
  - Em-dash glue. Rewrite: "There is no negotiation. The numbers must match the glass."
- > "The 'porches' are blanking intervals — legacy from CRT days (the electron beam needed time to fly back), but LCDs still use the timing model."
  - Em-dash + parenthetical + "but" clause = three clauses in one line. Rewrite: "The 'porches' are blanking intervals. They are a CRT legacy — the electron beam needed time to fly back. LCDs kept the timing model."
- > "The conversion is mechanical but easy to fumble."
  - "Mechanical but easy to fumble" is a stock Claude line (seen often in Parts II/V). Rewrite: "The conversion is simple but easy to get wrong."

### ESL readability
- > "ATK10261 (71 MHz) is at the edge — works but marginal, sometimes needs reducing to a lower-refresh timing."
  - "At the edge" idiomatic; "works but marginal" fragment. Rewrite: "ATK10261 at 71 MHz is at the limit. It usually works but you may need to drop to a lower refresh rate."
- > "For a panel needing custom power sequencing or init commands (rare for dumb RGB panels, common for panels with an init-controller), write a `drm_panel` driver:"
  - 28-word sentence with two parentheticals. Rewrite: "Some panels need custom power sequencing or init commands. This is rare for dumb RGB panels but common for panels with an init controller. For those, write a `drm_panel` driver."
- > "~120 lines. It registers a `drm_panel` with the timing and power sequencing; the LCDIF DRM driver finds it via the of_graph link and uses its mode."
  - Semicolon glue + dense vocabulary. Rewrite: "About 120 lines. It registers a `drm_panel` with the timing and power sequencing. The LCDIF DRM driver finds the panel through the of_graph link and uses its mode."

### Needs more depth
- §82.4 The DRM CRTC/encoder/connector/panel split is invoked ("The LCDIF DRM driver is the **CRTC + encoder**; the panel is the **connector's** mode source.") without ever explaining the four-role model. An MCU reader meets these terms first here. Add a 6–8 line paragraph: "DRM splits the display pipeline into four roles. The **CRTC** scans pixels out of memory at the right timing. The **encoder** translates the parallel pixel stream into a transport-level signal (parallel RGB, LVDS, HDMI, DSI). The **connector** is the physical port (or in our case, the panel input). The **panel/bridge** is the device hanging off the connector. On i.MX6ULL with parallel RGB the encoder is trivial (just wires) and the connector is the panel itself."
- §82.4 Atomic vs legacy KMS is never mentioned. The `myst7789.c` driver in Ch 83 uses `DRIVER_ATOMIC`, but it is never explained what atomic modesetting is or why it matters. Add one paragraph here in §82.4: "Modern DRM drivers use **atomic modeset**: every state change (mode, plane, cursor, format) is packaged into one transaction that the hardware applies on the next vblank, atomically. The legacy KMS path applied changes one at a time and could leave you with a half-configured display for a frame. All new drivers must be atomic; the helpers in this chapter assume it."
- §82.5 Approach 3 introduces `panel-bridge` indirectly (the driver is a `drm_panel`, not a `drm_bridge`). The bridge model is the natural follow-on (LVDS bridges, DSI-to-HDMI bridges) and is invoked offhand in later chapters. Add 4 lines: "Between the encoder and the panel sometimes sits a **bridge** — a chip that converts one signal type to another (parallel RGB → LVDS, DSI → HDMI). `drm_bridge` is the kernel object for it. A driver chain of bridges + a final panel is common on bigger SoCs. On i.MX6ULL with a direct-attached parallel panel, there is no bridge."

---

## Ch 83 — SPI LCD (ST7789 / ILI9341)

### AI wording / sledgehammer / buzzwords
- > "Unlike the dumb parallel panels of Ch 82, these have their own RAM — you send an init sequence + pixel data over SPI, and the controller refreshes the glass itself."
  - 28-word em-dash sentence + comma splice into "and the controller refreshes." Rewrite: "Unlike the dumb parallel panels in Ch 82, these have their own RAM. You send an init sequence and pixel data over SPI. The controller refreshes the glass on its own."
- > "SPI LCDs are cheap ($3–8), need only 4–5 wires (vs 28 for parallel), and are everywhere — smartwatches, thermostats, handheld instruments, hobbyist gadgets."
  - Marketing-flavor list, em-dash glue. Rewrite: "SPI LCDs are cheap and small. They need 4–5 wires versus 28 for parallel, and they appear in smartwatches, thermostats, handheld instruments, and hobby gadgets."
- > "**the MIPI-DBI command/data model + partial updates**"
  - Bolded equation-style heading in `Focus:`. Restate plainly.
- > "Only sending the *changed* rectangle (partial update) is the key to acceptable performance."
  - "The key to" cliché. Rewrite: "Send only the changed rectangle. That keeps refresh fast enough."
- > "What we got, ~200 lines:"
  - Informal contraction "What we got". Rewrite: "About 200 lines. We now have:"
- > "What *we* provided: the init sequence (the chip-specific magic) and the pixel dimensions."
  - "Magic" overused throughout the book. Rewrite: "We provided two things: the chip-specific init sequence and the pixel dimensions."
- > "What we'd add for production: rotation handling (MADCTL variations), power management (sleep on disable), and using the mainline `panel-mipi-dbi` generic driver instead of a custom one."
  - 28-word run-on with three parentheticals. Break into a bulleted list or three sentences: "For production: handle rotation through MADCTL. Add sleep on disable for power management. Better still, switch to the mainline `panel-mipi-dbi` generic driver and skip the custom code entirely."

### ESL readability
- > "the trade-off: SPI bandwidth limits refresh rate (a 240×240 16-bit frame is 115 KB; at 40 MHz SPI that's ~23 ms = ~40 fps max for a full refresh). For static or partial-update UIs, that's plenty."
  - Long parenthetical with semicolon glue inside. Break: "The trade-off is bandwidth. A 240×240 16-bit frame is 115 KB. At 40 MHz SPI that takes ~23 ms — about 40 fps for a full refresh. For static or partial-update UIs, that is plenty."
- > "Note: 3-wire mode (no DC pin; the D/C bit is embedded as a 9th bit per byte) exists but is awkward on most SPI controllers — 4-wire (separate DC GPIO) is standard."
  - 30-word sentence, three clauses, semicolon glue inside parenthetical. Rewrite: "A 3-wire mode also exists. The D/C bit becomes a 9th bit per byte, so there is no DC pin. Most SPI controllers cannot generate the 9-bit frame, so 4-wire (a separate DC GPIO) is the standard."
- > "Did the CASET/RASET/RAMWR command sequence per flush."
  - Bullet starts with past-tense verb in a list of "What the helper did for us." Awkward English for ESL. Rewrite all bullets in parallel form: "Tracked dirty rectangles..." → "It tracked dirty rectangles..." for each.

### Needs more depth
- §83.3 The DRM "tiny" framework and the `drm_simple_display_pipe` abstraction are introduced without context. An MCU reader has not seen DRM's full pipeline yet (CRTC + plane + connector). Add a 4–5 line paragraph: "A full DRM driver wires four objects together: a CRTC for timing, a plane for the source buffer, a connector for the output port, and an encoder for the signal conversion. For tiny displays this is overkill. `drm_simple_display_pipe` collapses CRTC + plane + encoder into one object with one set of callbacks. You only fill in `.enable`, `.disable`, and `.update`; the helpers handle the rest."
- §83.4 The `DRIVER_ATOMIC` flag appears with no introduction. Forward-reference or inline one sentence: "All modern DRM drivers must support atomic modeset — see Ch 82 §82.4."
- §83.6 Vsync / tearing handling ("No tearing if you respect the vblank") deserves 3 lines. For an MCU reader who has not seen vblank in a CPU-driven panel context: "Tearing happens when the SPI flush overlaps the controller's own refresh of the glass. Some panels expose a **TE (tearing effect)** pin that pulses at the start of each refresh cycle; route it to a GPIO IRQ and start each flush just after the TE pulse to land the data outside the controller's scan window."

---

## Ch 84 — QSPI LCD

### AI wording / sledgehammer / buzzwords
- > "QSPI quadruples the data rate: ~13 ms = ~75 fps. For round watch faces and animated UIs, QSPI is the difference between 'smooth' and 'slideshow.'"
  - "The difference between X and Y" cliché; quoted contrast is marketing. Rewrite: "Quad-SPI quadruples the data rate to about 13 ms per frame, or 75 fps. That is the difference between smooth animation and a slideshow."
- > "This is a newer, less-common interface — fewer mainline drivers, more chance you'll write your own."
  - Em-dash list-as-prose. Rewrite: "QSPI is newer and less common. Fewer mainline drivers exist, so you are more likely to write your own."
- > "**Honest assessment**: the i.MX6ULL is *not* a great host for QSPI displays. Its QSPI is flash-centric."
  - Bolded editorial header. Drop the bold, keep the content.
- > "We cover the topic because the *displays* are increasingly common, and you may meet them on a more capable SoC."
  - "You may meet them" is awkward English (you may encounter them). Rewrite: "We still cover the topic. The displays are increasingly common, and you will likely meet them on a more capable SoC."

### ESL readability
- > "The exact framing is controller-specific."
  - Fine; keep.
- > "On SoCs whose SPI controller exposes `spi_mem` with quad support, the `mipi_dbi` helper can issue quad transfers."
  - "On SoCs whose..." is grammatically dense for ESL. Rewrite: "Some SPI controllers expose `spi_mem` with quad support. On those SoCs, the `mipi_dbi` helper can issue quad transfers."
- > "We won't reproduce the full driver — it's Ch 83's driver with the data phase changed to quad, *and* it only works on an SoC whose controller supports quad `spi_mem` writes (not stock i.MX6ULL)."
  - 36-word sentence with em-dash + italic "and" + parenthetical. Rewrite: "We do not reproduce the full driver. It is the Ch 83 driver with the data phase changed to quad. It only works on an SoC whose controller supports quad `spi_mem` writes — stock i.MX6ULL does not."

### Needs more depth
- §84.3 The "QSPI controller is designed for flash" claim is correct but unmotivated. One paragraph explaining the LUT model: "The i.MX6ULL QSPI controller does not have a generic 'send N bytes on 4 lanes' command. Instead, it programs a 16-entry **LUT** (look-up table) where each entry is a phase descriptor (CMD/ADDR/DUMMY/DATA), and a transfer is built by selecting a sequence of LUT entries. For NOR flash, this matches the JEDEC command set perfectly. For displays, the framing (single-lane command marker → quad-lane pixel stream) does not map cleanly onto the LUT phases, and the driver `fsl-quadspi.c` never exposes a non-flash data path."

(Short chapter, only 3-4 worst offenders flagged. §84.4–§84.6 are clean enough.)

---

## Ch 85 — OLED & e-paper

### AI wording / sledgehammer / buzzwords
- > "**OLED is a page-addressed bitmap; e-paper is a two-buffer LUT-driven waveform machine**."
  - Bolded "X is A; Y is B" parallelism in `Focus:`. Rewrite: "OLED uses a page-addressed bitmap. E-paper uses a two-buffer waveform replay driven by a LUT. They need very different driver code."
- > "OLEDs are the cheapest possible 'real display' — a $2 128×64 OLED gives you a crisp status screen with no backlight, perfect contrast, ~20 mA."
  - "The cheapest possible 'real display'" cliché + triplet ("crisp..., perfect..., ~20 mA"). Rewrite: "OLEDs are the cheapest 'real display' you can buy. A 128×64 OLED costs around $2, draws ~20 mA, and has perfect contrast without a backlight."
- > "E-paper is the opposite extreme: zero idle power (the image persists with no power), sunlight-readable, but slow to update."
  - Triplet rhythm. Rewrite: "E-paper is the opposite. Zero idle power — the image persists with no power. Sunlight-readable. But slow to update."
- > "Both show up constantly in IoT status displays, instruments, smart-home panels, electronic shelf labels."
  - List-as-prose. Keep as is or break the sentence into "Both show up in IoT status displays: instruments, smart-home panels, electronic shelf labels."
- > "The `0x8D 0x14` (charge pump enable) is the #1 gotcha — the OLED needs an internal boost converter for the ~7 V it requires; forget this command and the screen never lights."
  - 28-word sentence, em-dash + semicolon. Rewrite: "The `0x8D 0x14` (charge pump enable) is the #1 gotcha. The OLED needs an internal boost converter for the ~7 V it requires. Forget this command and the screen stays black."
- > "A normal framebuffer driver assumes 'write pixel, see it.' E-paper assumes 'write image, trigger a 2-second update, then see it.'"
  - "X assumes Y. Y assumes Z." parallel sledgehammer. Keep, but trim quotes: "A normal framebuffer is 'write pixel, see it.' E-paper is 'write image, trigger update, wait 2 seconds, see it.'"

### ESL readability
- > "Within a page, *each byte is a vertical column of 8 pixels* (bit 0 = top, bit 7 = bottom):"
  - Fine; the diagram below clarifies. Keep.
- > "The mainline `ssd130x` driver has a `col_offset` field set from DT for exactly this."
  - "set from DT for exactly this" is dense for ESL. Rewrite: "The mainline `ssd130x` driver reads a `col_offset` value from DT to handle this case."
- > "To adapt the from-scratch driver: change `ms_cmd(m, 0x21); ms_cmd(m, 0); ms_cmd(m, 127);` to `ms_cmd(m, 0x21); ms_cmd(m, 2); ms_cmd(m, 129);`. (Or — SH1106 doesn't support horizontal addressing mode at all in some variants; you set page + column manually per page.)"
  - 40+ word sentence with parenthetical. Rewrite: "For SH1106, change the column window from 0–127 to 2–129. Some SH1106 variants do not support horizontal addressing mode at all — for those, set the page and column manually for each page."
- > "Below ~0 °C, e-paper refreshes very slowly or not at all. The waveform LUT is temperature-dependent; good modules have a temperature sensor + multiple LUTs."
  - Semicolon glue + "+" used as conjunction. Rewrite: "Below ~0 °C, e-paper refreshes very slowly or not at all. The waveform LUT is temperature-dependent. Good modules include a temperature sensor and ship multiple LUTs for the controller to switch between."

### Needs more depth
- §85.6 The e-paper waveform LUT is described but the *electrochemistry* is hand-waved. One paragraph: "Each e-ink pixel is a microcapsule of black and white pigment particles, each pigment with the opposite charge. A positive pulse at the top electrode attracts white particles up (pixel appears white). The waveform LUT is a per-pixel sequence of voltage levels over time that *moves* the particles from their current position to the target. Why the multi-second flicker? The particles must be pushed all the way to one extreme, then the other, then the target — to break free of mechanical sticking ('hysteresis'). Skipping the bounce gives partial-refresh: faster, but particles do not fully detach, leaving the ghost of the old image."

---

## Ch 86 — Touch input ICs

### AI wording / sledgehammer / buzzwords
- > "a display without touch is a monitor; with touch it's an interface."
  - Semicolon glue + "X is A; X is B" cliché. Rewrite: "A display without touch is a monitor. Add touch and it becomes an interface."
- > "**capacitive = threshold detection, resistive = ADC + calibration**."
  - Equation-style `Focus:` heading. Rewrite into prose: "Capacitive touch is threshold detection — a digital touched/not-touched. Resistive touch is two ADC readings plus a calibration step."
- > "A cap button outputs a clean digital 'touched'; you wire it to `gpio-keys` and you're done."
  - Semicolon glue. Rewrite: "A capacitive button outputs a clean digital 'touched' signal. Wire it to `gpio-keys` and you are done."
- > "Resistive touch gives you two ADC readings (X, Y position) that map non-linearly to screen pixels — calibration (the `tslib` / `xinput_calibrator` step) turns raw ADC counts into pixel coordinates."
  - 30-word em-dash sentence with parenthetical-inside-parenthetical. Rewrite: "Resistive touch gives you two ADC readings, X and Y, that do not map directly to screen pixels. A calibration step (using `tslib` or `xinput_calibrator`) converts raw ADC counts into pixel coordinates."
- > "Touching the pad generates a `KEY_POWER` / `KEY_MENU` input event. `evtest /dev/input/eventN` shows them. Done — zero driver code."
  - "Done — zero driver code." trim-and-mic-drop pattern. Rewrite: "Touching the pad generates a `KEY_POWER` or `KEY_MENU` input event, which `evtest /dev/input/eventN` will show. No driver code needed."
- > "These are *hardware* straps, not software — set them on the PCB."
  - Em-dash glue. Rewrite: "These are hardware straps, not software-configurable. Set them on the PCB."
- > "Raw ADC ≠ pixels."
  - Cute but math-notation-in-prose is unusual. Rewrite: "Raw ADC values are not pixel coordinates."

### ESL readability
- > "Each electrode's capacitance rises when a finger approaches (the finger adds capacitance to ground). The chip tracks a per-electrode baseline and reports 'touched' when capacitance exceeds a threshold."
  - Two parentheticals, but readable. Keep.
- > "Sampling toggles the panel layers, which can spuriously trigger PENIRQ."
  - "Spuriously trigger" is technical English. For ESL: "Sampling toggles the panel layers, and that can trigger PENIRQ even when no one is touching."
- > "The mainline driver masks PENIRQ during sampling. Our simple driver polls the GPIO instead — works but less clean."
  - "works but less clean" fragment. Rewrite: "The mainline driver masks PENIRQ during sampling. Our simple driver polls the GPIO instead — it works, but the mainline approach is cleaner."

### Needs more depth
- §86.6 Calibration: the 3×2 affine matrix is presented as a formula without explaining *why* an affine works. For an MCU reader: "Why an affine? A 3×2 affine handles four real-world distortions in one matrix: (1) origin offset (touchscreen edge not aligned with LCD edge), (2) per-axis scale (raw ADC range smaller than the panel), (3) X/Y swap, and (4) small rotation if the touch overlay was glued slightly off-square. It does not handle non-linear distortion (corners pulling inward), but resistive panels have very little of that — affine is good enough in practice."
- §86.4 ADC differential mode is mentioned in the protocol table ("SER/DFR (0 = differential — better noise rejection)") but not explained. One line: "Differential mode reads the touch-point voltage against the drive layer's far rail in one conversion, canceling supply noise that would otherwise creep into the single-ended reading."
- §86.4 The mainline `ads7846.c` driver uses a *hardware* settle-time and interleaved sample sequences ("X-+ X-- Y-+ Y-- Z-+ Z--") that the from-scratch driver skips. Mention this trade-off explicitly in §86.5's "what we skipped" list: "The mainline driver runs each axis in both polarities and averages — cancels switch-charge artifacts in the resistive layers. We just median-filter five same-polarity samples, which is simpler but noisier under EMI."

---

## Ch 87 — Parallel CSI cameras

### AI wording / sledgehammer / buzzwords
- > "Three sensors compared: **OmniVision OV5640** (5 MP, the workhorse), **OV7725** (0.3 MP VGA, simple), **GalaxyCore GC2145** (2 MP, cheap)."
  - "Workhorse" cliché. Rewrite: "Three sensors compared: OmniVision OV5640 (5 MP, the common default), OV7725 (0.3 MP VGA, simple), GalaxyCore GC2145 (2 MP, budget)."
- > "any i.MX6ULL product with a camera — a smart doorbell, a barcode scanner, a machine-vision sensor — uses parallel CSI (the i.MX6ULL has *no* MIPI-CSI)."
  - Double em-dash interjection + parenthetical. Rewrite: "Any i.MX6ULL product with a camera uses parallel CSI. The i.MX6ULL has no MIPI-CSI. Smart doorbells, barcode scanners, and machine-vision sensors all run through this interface."
- > "The driver model is the most elaborate in the kernel: a *sensor* sub-device feeds a *CSI bridge* sub-device feeds a *video* device, all wired via the media controller."
  - "Most elaborate in the kernel" is editorial. "Feeds a X feeds a Y" reads like a chain. Rewrite: "The driver model has more moving parts than most subsystems. A *sensor* sub-device feeds a *CSI bridge* sub-device, which feeds a *video* device. The media controller wires them all together."
- > "Understanding this graph is the key that unlocks all of V4L2."
  - "The key that unlocks" cliché. Rewrite: "Understand this graph and the rest of V4L2 falls into place."
- > "**a camera sensor is two devices in one — an I²C control interface and a parallel pixel stream — modeled as a V4L2 sub-device**."
  - Bolded `Focus:` with triple em-dashes. Rewrite: "A camera sensor is two devices in one. It has an I²C control interface and a parallel pixel stream. V4L2 models the combination as a sub-device."
- > "This indirection (separate subdevs, explicit format propagation) seems heavyweight for one camera, but it's what lets V4L2 handle complex pipelines (multiple sensors, ISP stages, scalers) uniformly."
  - 31-word sentence, two parentheticals. Rewrite: "All this indirection — separate subdevs, explicit format propagation — feels heavy for one camera. It is what lets V4L2 handle complex pipelines (multiple sensors, ISP stages, scalers) with the same code paths."
- > "These come from OmniVision's reference code. They configure the sensor's internal ISP, PLL, timing, and pixel pipeline. Like the BME280 compensation formulas (Ch 67) or the VL53L0X tuning blob (Ch 72), these are vendor IP transcribed verbatim — you don't derive them, you apply them."
  - Triplet ("ISP, PLL, timing, and pixel pipeline" is fine; the second triplet "you don't derive them, you apply them" reads AI). Rewrite the last sentence: "Like the BME280 compensation formulas (Ch 67) or the VL53L0X tuning blob (Ch 72), these are vendor IP. You copy them in, you do not derive them."

### ESL readability
- > "The sensor needs its MCLK running *before* I²C communication works (the sensor's logic is clocked by MCLK). This is a common bring-up gotcha."
  - Fine, but "gotcha" is idiomatic. Rewrite: "The sensor's logic runs off MCLK. Until MCLK is running, the sensor will not even ACK on I²C. This catches many people."
- > "**MCLK not running before I²C.** The sensor's logic is clocked by MCLK; no MCLK = no I²C ACK. Enable the xclk in power-on *before* the chip-id read."
  - Equation-as-prose ("no MCLK = no I²C ACK"). Rewrite: "Without MCLK, the sensor cannot ACK on I²C. Enable the xclk in `power_on()` before any I²C read."
- > "The bridge + sensor must agree on format: if the sensor emits YUYV8_2X8 640×480, the CSI captures that. `media-ctl --set-v4l2` can override pad formats during bring-up debugging."
  - "+" used as conjunction. Rewrite: "The bridge and the sensor must agree on format. If the sensor emits YUYV8_2X8 at 640×480, the CSI must capture that. During bring-up, `media-ctl --set-v4l2` can override pad formats for debugging."

### Needs more depth
- §87.3 The V4L2 subdev pipeline is the chapter's core concept but is described only at the "boxes and arrows" level. An MCU reader has not seen async subdev registration, pad format propagation, or the media-controller link semantics. Add a 12-line block after the diagram explaining:
  - **Async subdev registration.** "Sensors and CSI bridges probe independently and at unknown times — the I²C bus enumerates separately from the platform bus. `v4l2_async_register_subdev_sensor` says 'I am ready, find me.' The CSI bridge driver registers a *notifier* with a list of of_graph endpoints it expects. The async core matches them and calls `bound` when both sides are present. This is why your `/dev/video0` may not appear if the of_graph link in DT is wrong — the bridge waits forever."
  - **Pad format propagation.** "Each pad has its own current format. The format does *not* automatically flow through links — you set it on each pad with `VIDIOC_SUBDEV_S_FMT` (via `media-ctl --set-v4l2`). All pads in a chain must match; if the sensor emits YUYV but the CSI is configured for RGB565, the pipeline refuses to start or you get garbage."
  - **V4L2 controls vs subdev controls.** "Sensor controls (exposure, gain, AWB) live on the sensor subdev, not on `/dev/video0`. `v4l2-ctl --device /dev/v4l-subdev0 --list-ctrls` for the sensor's controls. The video node only owns frame-buffer-level controls."

---

## Ch 88 — USB UVC cameras

### AI wording / sledgehammer / buzzwords
- > "Unlike the parallel-CSI sensors of Ch 87 (which need a custom driver per sensor), a UVC camera is class-compliant: plug it in, `/dev/video0` appears, no driver work."
  - 28-word sentence with parenthetical + colon + comma triplet. Rewrite: "Unlike the parallel-CSI sensors in Ch 87, a UVC camera is class-compliant. Plug it in, `/dev/video0` appears, and there is no driver to write."
- > "**UVC is a class driver — the protocol is standardized, so one driver handles all cameras**."
  - Bolded sledgehammer. Rewrite: "UVC is a class driver. The protocol is standardized, so one kernel driver covers every UVC camera."
- > "The complexity isn't in a per-device driver (there isn't one); it's in *bandwidth budgeting* and *format selection*."
  - "Not X — it's Y" sledgehammer + semicolon glue. Rewrite: "The hard part is no longer per-device driver code. It is bandwidth budgeting and format selection."
- > "Understanding this is the whole game."
  - Cliché. Drop or rewrite: "Get the bandwidth math right and the rest is easy."
- > "The killer advantage of UVC: **the camera does the compression**."
  - "Killer advantage" idiom. Rewrite: "The big advantage of UVC: the camera does the compression."
- > "This makes UVC *better* than CSI for the i.MX6ULL in many cases — the webcam's silicon encodes, the SoC just receives compressed frames."
  - Em-dash glue with comma splice. Rewrite: "For the i.MX6ULL, this often makes UVC the better choice. The webcam's silicon does the encoding, and the SoC only has to receive the compressed bytes."
- > "From the application's view, a UVC camera and a CSI camera are *identical* (both V4L2 video devices); only the bring-up differs."
  - Semicolon glue. Rewrite: "From the application's view, a UVC camera and a CSI camera are identical. Both are V4L2 video devices. Only the bring-up differs."

### ESL readability
- > "UVC streams video over USB **isochronous** transfers — guaranteed bandwidth, no retransmission (a dropped frame is just dropped)."
  - 19 words but stacked qualifications. Rewrite: "UVC video runs over USB **isochronous** transfers. These guarantee bandwidth but never retransmit — a dropped microframe is simply lost."
- > "MJPEG isn't a video codec. It's per-frame JPEG — no inter-frame compression. 10:1 typical, not the 100:1 of H.264. For bandwidth-critical streaming, prefer an H.264 UVC camera."
  - Choppy fragments ("10:1 typical, not the 100:1 of H.264"). Rewrite: "MJPEG is not a true video codec. It is per-frame JPEG with no compression between frames. Typical ratio is 10:1, against H.264's 100:1. For bandwidth-critical streams, pick an H.264 UVC camera."

### Needs more depth
- §88.2 Isochronous vs bulk USB transfers: an MCU reader who has only seen USB-CDC or HID may not have a mental model of isochronous. Add one short paragraph: "USB transfers come in four flavors. **Bulk** is best-effort with retransmission — used for mass-storage and most data. **Interrupt** is small, low-latency polled — keyboards, mice. **Control** is the setup channel. **Isochronous** reserves a fixed slice of every 125 µs microframe and never retransmits — used for audio and video where a late packet is worthless. The host scheduler allocates isochronous bandwidth at enumeration; if it cannot fit the camera's request, the device fails to start."
- §88.2 UVC descriptors and their parsing: one sentence describing what a descriptor *is* in USB terms: "USB descriptors are small fixed-format read-only blocks the device exposes during enumeration. UVC adds a class-specific descriptor tree under the standard Configuration descriptor — VS Format/Frame/Frame-Interval tables that enumerate every (format, resolution, frame-rate) combination the camera supports. `uvcvideo` walks this tree and turns each combination into a V4L2 enum entry."

---

## Ch 89 — I²S audio codecs

### AI wording / sledgehammer / buzzwords
- > "the analog-front-end chips that give the i.MX6ULL real audio — DAC for playback, ADC for capture, headphone/speaker drivers, mic preamps."
  - Triplet-plus list-as-prose. Rewrite: "These are the analog-front-end chips that give the i.MX6ULL real audio: DAC for playback, ADC for capture, headphone and speaker drivers, mic preamps."
- > "the i.MX6ULL's SAI is just a digital I²S serializer — it has no analog audio."
  - Em-dash glue. Rewrite: "The i.MX6ULL's SAI is a digital I²S serializer only. It has no analog audio."
- > "**a codec driver is regmap + DAPM widgets + DAI ops**."
  - Equation-as-prose bolded `Focus:`. Rewrite: "A codec driver has three parts: a regmap for register access, DAPM widgets and routes for the analog graph, and DAI ops for I²S format negotiation."
- > "Master these three and any codec driver reads the same."
  - "Master these three" is cliché. Rewrite: "Once you understand these three, every codec driver looks familiar."
- > "The single most important codec concept."
  - Hype line. Drop and let the section title carry it, or rewrite: "DAPM is the central concept in ASoC codec design."
- > "DAPM is why a well-written codec driver consumes µA at idle and doesn't click — and why a *badly* written one pops on every play/stop."
  - "Not X — and why Y" parallel sledgehammer. Rewrite: "DAPM is the reason a well-written codec driver draws µA at idle and stays silent between tracks. A badly-written one pops on every play and stop."
- > "Getting the routes and power-sequencing right is the bulk of codec-driver effort."
  - Fine, but "the bulk of effort" is cliché. Rewrite: "Getting the routes and power-sequence right is most of the work in a codec driver."
- > "That's the whole codec driver shape: regmap + DAI ops + component (controls + DAPM)."
  - Equation-as-prose. Rewrite: "Those four pieces — regmap, DAI ops, component (controls + DAPM) — are the whole codec driver."
- > "Real codecs are bigger, but the *structure* is identical."
  - Stock Claude line. Keep, but trim italics.

### ESL readability
- > "The DAPM graph models the analog signal paths (DAC → mixer → headphone-amp → jack) and powers each block only when it's in an active route — saving power and clicks."
  - 28-word sentence with parenthetical + em-dash + double benefit. Rewrite: "The DAPM graph models the analog signal paths: DAC → mixer → headphone amp → jack. Each block is powered up only when it lies on an active route, which saves power and avoids switching clicks."
- > "When you play audio: the stream activates 'Left DAC'; DAPM walks the graph forward — DAC → mixer → PGA → Headphone Jack — and powers on each widget in that path."
  - Colon + semicolon + em-dashes in 30 words. Rewrite: "When you play audio, the stream activates the 'Left DAC' widget. DAPM walks the graph forward: DAC → mixer → PGA → Headphone Jack. It powers on each widget along the way."
- > "Codecs need MCLK = a specific multiple of the sample rate (e.g., 256× or 512× fs). For 48 kHz: 12.288 MHz or 24.576 MHz."
  - Equation glyph in prose. Rewrite: "A codec needs MCLK to be a specific multiple of the sample rate, typically 256× or 512× fs. For 48 kHz that means 12.288 MHz or 24.576 MHz."

### Needs more depth — IMPORTANT for ESL/MCU reader, ASoC is hard
- §89.4 The three-driver ASoC split (machine/CPU-DAI/codec) is referenced ("Ch 53 showed the three-driver ASoC split (CPU-DAI + codec + machine) with WM8960") but never recapped in this chapter. The reader landing here without re-reading Ch 53 has no map. Add a 6-line recap at the start of §89.4:
  - "Three drivers cooperate to make ALSA audio work:
    1. **CPU-DAI driver** — owns the SAI (or SSI/I²S) peripheral. Knows how to push samples into the I²S serializer. Lives in `sound/soc/fsl/fsl_sai.c`. You do not write this for i.MX6ULL.
    2. **Codec driver** — owns the codec chip over I²C. Knows the codec's registers, DAPM graph, and DAI format constraints. This chapter is about writing one of these.
    3. **Machine driver** — the glue. Says 'connect the SAI's playback DAI to the WM8960's hifi DAI, in I²S format, with the WM8960 as clock slave.' Lives in either a custom `imx-audmux-wm8960.c` or, more commonly, the generic `simple-audio-card` driver consuming a DT description."
- §89.3 DAPM widget-vs-control-vs-route trio is dense. Add a 4-line example clarifying widget power bits: "A widget like `SND_SOC_DAPM_DAC('DAC', 'Playback', REG_POWER, 0, 0)` says: 'There is a DAC named DAC. Its DMA stream binding name is Playback. To power it on, set bit 0 of REG_POWER. The fifth argument (`0`) means active-high — write 1 to enable.' When DAPM decides this widget should be on, it does `update_bits(REG_POWER, 1<<0, 1<<0)` for you. You never set the bit by hand — DAPM owns it."
- §89.4 Regmap *write-only* register handling is mentioned correctly but the implication is buried. Add one sentence: "Write-only chips appear often in audio. Without `reg_defaults` and a cache, every read returns the cached zero, and `update_bits` (read-modify-write) silently corrupts state. The regmap cache is not optional — it is the only correct way to handle these chips."

---

## Ch 90 — Digital class-D amplifiers

### AI wording / sledgehammer / buzzwords
- > "'audio output without a codec' — chips that take I²S directly and drive a speaker (class-D amp) or headphones (DAC), with no ADC, no mic, no analog input mixing."
  - Triplet "no ADC, no mic, no analog input mixing" + em-dash chain. Rewrite: "These chips take I²S directly and drive a speaker (class-D amp) or headphones (DAC). They have no ADC, no mic input, and no input mixer — just a digital-in, analog-out path."
- > "(the MAX98357A is almost comically simple; the TAS5805M shows DSP-coefficient loading)."
  - "Almost comically simple" reads as editorial. Rewrite: "The MAX98357A driver is extremely short. The TAS5805M shows DSP-coefficient loading."
- > "you don't need a full codec (Ch 89). You need to turn I²S into sound."
  - "Not X. Y." sledgehammer. Rewrite: "A full codec (Ch 89) is overkill for playback-only products. All you need is to turn I²S into sound."
- > "The MAX98357A in particular needs *zero* configuration — wire I²S, pick L/R/mono via a resistor, done."
  - "Done." trim-and-stop pattern. Rewrite: "The MAX98357A needs zero configuration. Wire I²S, pick L/R/mono with a resistor, and it plays."
- > "**an amp-without-control is the simplest ASoC component possible**."
  - Bolded sledgehammer. Rewrite: "An amp without a control bus is the simplest ASoC component you can write."
- > "The spectrum from 'dumb amp' to 'smart DSP amp' maps cleanly to driver complexity."
  - Marketing-flavor. Rewrite: "Driver complexity tracks chip capability — dumb amp short, DSP amp long."
- > "The MAX98357A is the minimalist's dream."
  - Cliché. Rewrite: "The MAX98357A is as simple as it gets."
- > "That's it. No register access because there are no registers."
  - "That's it." pattern. Rewrite: "There is no register access in the driver because the chip has no registers."
- > "This is the *simplest possible ASoC component*."
  - Italic superlative. Rewrite: "This is the floor of ASoC complexity."
- > "The TAS5805M is the opposite extreme: a 2×23 W stereo class-D amp with an **on-chip DSP** offering:"
  - "The opposite extreme" cliché. Rewrite: "The TAS5805M sits at the other end. It is a 2×23 W stereo class-D amp with an on-chip DSP that provides:"
- > "a $5 speaker can sound like a $50 one with good DSP tuning. This is why class-D DSP amps dominate smart speakers."
  - Marketing. Rewrite: "Good DSP tuning makes a $5 speaker sound much better than its physical parts deserve. This is why DSP class-D amps are standard in smart speakers."
- > "The driver replays this blob at probe — like the camera (Ch 87) and ToF (Ch 72) register blobs."
  - Reasonable cross-reference. Keep.
- > "This is the canonical 'amp without a codec' use case."
  - "Canonical" overused. Rewrite: "This is the standard 'amp without a codec' product pattern."

### ESL readability
- > "Wire I²S (BCLK, LRCLK, DIN), power, speaker — and it plays."
  - List + dash + verb-without-subject. Rewrite: "Wire up I²S (BCLK, LRCLK, DIN), power, and a speaker. It plays."
- > "The DAPM `OUT_DRV_E` widget's event callback toggles the SD_MODE GPIO when the route activates (amp on during playback, off when idle — saving power)."
  - 24-word sentence with parenthetical-em-dash chain. Rewrite: "The `OUT_DRV_E` widget's event callback toggles the SD_MODE GPIO with the route. The amp is on during playback and off when idle, saving power."
- > "All configured over I²C. The DSP runs a *coefficient set* — you compute biquad coefficients (e.g., from a target frequency response) and load them into the chip's coefficient RAM."
  - Fragment "All configured over I²C." starts a paragraph. Rewrite: "All of this is configured over I²C. The DSP runs a *coefficient set*. You compute biquad coefficients (for example, from a target frequency response) and load them into the chip's coefficient RAM."

### Needs more depth
- §90.3 The DAPM `OUT_DRV_E` event mechanism is shown but the *event types* (`PRE_PMU`/`POST_PMU`/`PRE_PMD`/`POST_PMD`) are barely explained. An MCU reader who has not absorbed Ch 89's DAPM detail needs one sentence: "DAPM fires the event callback four times around any power transition — `PRE_PMU` before powering up, `POST_PMU` after, `PRE_PMD` before powering down, `POST_PMD` after. Class-D amps need `PRE_PMU` (settle the enable before the DAC drives signal) and `POST_PMD` (clear the GPIO after the DAC stops, to avoid pop)."
- §90.5 TAS5805M book/page register paging is unique enough to deserve a short example. Add 4 lines: "Selecting a coefficient page on the TAS5805M looks like: `write(0x00, 0x00); write(0x7F, 0x8C); write(0x00, 0x18);` — that is page 0x00, book 0x8C, page 0x18. Now register addresses 0x08..0xFF on this page are the biquad coefficients for filter slot 0. Forget the sequence and you write to whatever page was last selected — a different filter, the DRC config, or the device-id register."

---

## Ch 91 — SDIO WiFi

### AI wording / sledgehammer / buzzwords
- > "But it's also the hardest peripheral to bring up on a new board — the SDIO transport, the power sequence, the 32 kHz clock, the per-board NVRAM, and the firmware blob all have to be exactly right, and the failure mode is usually 'nothing in dmesg.'"
  - 44-word sentence with five-item list-as-prose. Rewrite: "SDIO WiFi is also the hardest peripheral to bring up on a new board. Five things must be exactly right: the SDIO transport, the power sequence, the 32 kHz clock, the per-board NVRAM, and the firmware blob. When any one is wrong, the symptom is usually 'nothing in dmesg.'"
- > "This chapter is mostly about the bring-up sequence and debugging."
  - Fine; keep.
- > "**the WiFi chip is a full-MAC co-processor; the driver is a firmware-loader + a SDIO-packet shuttle**."
  - Bolded sledgehammer with semicolon glue + equation-style "+". Rewrite: "The WiFi chip is a full-MAC co-processor. The Linux driver does two things only: it loads firmware, and it shuttles SDIO packets."
- > "Bring-up = getting the SDIO bus working + getting the right firmware + NVRAM. After that, the chip does the WiFi."
  - Equation-as-prose. Rewrite: "Bring-up is two jobs: get the SDIO bus working, then supply the right firmware and NVRAM. After that, the chip handles the actual WiFi."
- > "Miss any one and you get silence in dmesg."
  - Sledgehammer one-liner. Keep, but consider: "Miss any one of these and dmesg is silent."
- > "**Strongly prefer modules with in-tree drivers** (AP6212/brcmfmac, SD8801/mwifiex)."
  - Bolded recommendation followed by a parenthetical. Rewrite: "Strongly prefer modules with in-tree drivers — AP6212 with brcmfmac, SD8801 with mwifiex."
- > "The $0.50 you save on an RTL8189 vs an AP6212 is dwarfed by the engineering cost of maintaining an out-of-tree driver across an 8-year product life."
  - "Dwarfed by" cliché. Rewrite: "Saving $0.50 on an RTL8189 versus an AP6212 is nothing compared to the engineering cost of maintaining an out-of-tree driver for an 8-year product life."
- > "So brcmfmac is fundamentally: a firmware loader + an SDIO packet shuttle + a cfg80211↔Broadcom-command translator. ~15000 lines, but conceptually those three jobs."
  - Equation-as-prose + sentence-fragment "~15000 lines, but conceptually those three jobs." Rewrite: "So brcmfmac is three things: a firmware loader, an SDIO packet shuttle, and a cfg80211-to-Broadcom command translator. The source is ~15000 lines, but conceptually it is those three jobs."

### ESL readability
- > "SDIO uses the same physical bus and protocol as an SD card (Ch 66), but instead of 'read/write blocks of storage,' the device exposes **I/O functions** — registers and an interrupt."
  - 30-word sentence with embedded quote + em-dash. Rewrite: "SDIO uses the same physical bus and protocol as an SD card (Ch 66). Instead of reading and writing storage blocks, the device exposes **I/O functions** — a set of registers and an interrupt line."
- > "The progression:"
  - Fine.
- > "The Linux side stops at 'write bytes to SDIO FIFO.' Everything 802.11 happens in the chip's firmware."
  - Two short sentences with embedded quote — keep.
- > "For a *product*, **don't use RTL8188EUS** unless you need its AP/monitor features."
  - "For a *product*" italic stress. Keep, but the bold is unnecessary; the imperative is clear.

### Needs more depth — important, the wpa_supplicant/nl80211/cfg80211 stack is hard
- §91.3 The cfg80211 / nl80211 / mac80211 / mac-driver layering is dense. The current §91.3 diagram lists boxes but does not explain *which* layer does what. An MCU reader needs a clear breakdown — this is one of the hardest concepts in Linux networking. Add a 12-line block:
  - "**nl80211** is a kernel-internal netlink protocol — the wire format wpa_supplicant uses to talk to the kernel WiFi stack. Think of it as 'WiFi's ioctl, but on a netlink socket.' Userspace tools (`iw`, `wpa_supplicant`, NetworkManager) all speak nl80211.
  - **cfg80211** is the kernel-side server for nl80211. It receives nl80211 messages (scan, connect, set-key) and calls per-driver callbacks. Every WiFi driver registers cfg80211 ops. cfg80211 also enforces the regulatory database (what channels are allowed in what country) and tracks scan results.
  - **mac80211** is an optional middleware layer between cfg80211 and the chip driver. It implements the 802.11 MAC state machine (authentication, association, rate selection, encryption) in software, for chips that are 'soft-MAC' — i.e., where the chip is just a radio and Linux runs the MAC. RT5370 (Ch 92), MT7601, and most Atheros chips use mac80211.
  - **Full-MAC chips** (BCM43438, Marvell SD8801, Realtek RTW88 family) run the 802.11 MAC inside the chip's firmware. Their Linux drivers skip mac80211 and implement cfg80211 ops directly. brcmfmac is full-MAC.
  - From wpa_supplicant's view, the layering is transparent — it sends nl80211 'connect' and the kernel handles the rest. Knowing which layer your chip uses tells you where to read the kernel source when something goes wrong."

---

## Ch 92 — USB WiFi

### AI wording / sledgehammer / buzzwords
- > "USB WiFi dongles — the plug-in alternative to soldered SDIO WiFi (Ch 91)."
  - Fine.
- > "The defining theme: the **in-tree vs out-of-tree driver saga** — which dongles 'just work' and which require a DKMS nightmare."
  - "Saga," "nightmare" — both loaded. Rewrite: "The big theme here is in-tree versus out-of-tree drivers. Some dongles just work. Others need a constantly-rebuilt DKMS module."
- > "**the chip you buy determines whether WiFi is a 5-minute job or a 5-day ordeal**."
  - Bolded marketing. Rewrite: "The chip you buy determines whether bringing up WiFi takes five minutes or five days."
- > "Choosing the right chip is the entire game."
  - Cliché. Rewrite: "Chip choice is most of the work."
- > "**If you want zero hassle, buy an RT5370 dongle.**"
  - Bolded conversational instruction. Rewrite: "For the lowest-hassle path, buy an RT5370 dongle."
- > "The most *common* dongle, the most *painful* driver."
  - Stylized rhetorical balance. Rewrite: "The most common dongle, but the most painful driver."
- > "Total bring-up: insert dongle, copy firmware (if not present), connect. Five minutes."
  - List-as-prose with mic-drop "Five minutes." Rewrite: "Total bring-up is three steps. Insert the dongle. Copy the firmware if it is not present. Connect. About five minutes."
- > "**RT5370 / MT7601 use mac80211** (soft-MAC) — the kernel does the 802.11 MAC, the chip is a radio. This is why they integrate so cleanly: mac80211 + cfg80211 handle everything; the chip driver is a thin USB+radio shim."
  - 30 words with em-dash + semicolon + "+". Rewrite: "RT5370 and MT7601 are *soft-MAC* chips. They use mac80211: the kernel does the 802.11 MAC, the chip is just a radio. This is why integration is clean. mac80211 and cfg80211 handle the protocol work, and the chip driver is a thin USB-to-radio shim."

### ESL readability
- > "But it's out-of-tree:"
  - Fragment to introduce a code block. Acceptable.
- > "Each kernel bump may require patching the driver."
  - Fine.
- > "Pin the kernel or use DKMS — or pick an in-tree module."
  - Double em-dash. Rewrite: "Pin the kernel, use DKMS, or — better — pick an in-tree module."
- > "Some 'USB WiFi' is a soldered module (not a dongle) — same driver story, but now you can't swap the chip if the driver is bad."
  - "Same driver story" idiom. Rewrite: "Some 'USB WiFi' is a soldered-on module, not a removable dongle. The driver situation is the same, but now you cannot swap the chip if the driver turns out to be bad."

### Needs more depth
- §92.2 The mac80211 path is good, but the mention is one parenthetical. Forward-link to Ch 91's added cfg80211/mac80211 explanation, or recap two lines: "RT5370 is a *soft-MAC* chip. Its driver implements mac80211 ops (transmit a single frame, receive, set-channel) and mac80211 handles the rest of 802.11. Compare to AP6212 (Ch 91), where the chip firmware runs the MAC and Linux's mac80211 is bypassed entirely."
- §92.5 USB-2.0 isochronous bandwidth and how WiFi reservations interact with cameras (Ch 88) — the chapter mentions "compete" but never names *isochronous bandwidth reservation* as the mechanism. One sentence: "USB WiFi uses bulk transfers, not isochronous, so it cannot 'reserve' bandwidth. UVC cameras (Ch 88) do reserve isochronous bandwidth. The net effect: a high-res webcam can starve the WiFi dongle's bulk endpoint, but rarely the reverse."

(Short chapter — kept findings to top-5 highest impact.)

---

## Ch 93 — Hosted WiFi via ESP32 / ESP8266

### AI wording / sledgehammer / buzzwords
- > "**two fundamentally different offload models**."
  - Bolded "fundamentally." Rewrite: "Two very different offload models."
- > "esp-hosted: the ESP is a *dumb radio* — Linux runs the IP stack, the ESP just moves 802.11 frames (Linux sees `wlan0`, runs wpa_supplicant, full control). AT-command: the ESP is a *smart modem* — it runs its own TCP/IP, Linux sends `AT+CIPSTART` and gets a socket-like abstraction (simple, but limited and non-standard)."
  - 55-word two-sentence pair with double em-dashes and parentheticals. Break into four sentences: "esp-hosted treats the ESP as a *dumb radio*. Linux runs the IP stack and just sends 802.11 frames through the ESP. From Linux's view there is a normal `wlan0` with wpa_supplicant on top. AT-command treats the ESP as a *smart modem*. The ESP runs its own TCP/IP stack and Linux speaks `AT+CIPSTART` to open sockets. Simple, but limited and non-standard."
- > "Picking between them shapes everything."
  - Cliché. Rewrite: "The choice between them shapes the rest of the design."
- > "The last point is underrated:"
  - Editorial. Rewrite: "One often-missed advantage:"
- > "an ESP32 *module* (not bare chip) ships with FCC/CE/IC modular certification. Bolt it on, and your product inherits the RF certification — no expensive antenna-certification of your own design. This alone justifies hosted WiFi for low-volume products."
  - 41-word run with em-dash and editorial "alone justifies." Rewrite: "An ESP32 *module* (not the bare chip) ships with FCC/CE/IC modular certification. If you mount the module without changing the antenna, your product inherits the certification. You skip an expensive antenna-certification step. For low-volume products, this alone can justify hosted WiFi."
- > "And you maintain the ESP firmware in addition to the Linux side."
  - "And you maintain" sentence-starter. Rewrite: "You also maintain the ESP firmware on top of the Linux side."
- > "Linux talks to the ESP like a dial-up modem:"
  - Fine; keep.
- > "The right choice for a real product. Requires the esp-hosted firmware + the Linux driver."
  - Two fragments. Rewrite: "It is the right choice for production. You need both the esp-hosted firmware on the ESP and the matching Linux driver."
- > "Common in quick prototypes and MCU-style code. Avoid for anything that needs the Linux network ecosystem."
  - Two fragments. Rewrite: "AT-command mode is common in quick prototypes and in MCU-style code. Avoid it for any product that needs Linux's network ecosystem (sockets, TLS, multiple connections, NetworkManager)."

### ESL readability
- > "esp-hosted also relays Bluetooth (HCI over the same transport) — so one ESP32 gives Linux both `wlan0` and an `hci0`."
  - Em-dash glue. Rewrite: "esp-hosted also relays Bluetooth, sending HCI over the same transport. So one ESP32 gives Linux both `wlan0` and `hci0`."
- > "The ESP's transport protocol multiplexes: WiFi-STA frames, WiFi-AP frames, BT-HCI packets, and control commands all flow over the same SPI link, distinguished by an `if_type` field in the header."
  - 31-word colon-introducing run-on. Rewrite: "The ESP's transport protocol multiplexes several streams over the same SPI link: WiFi-STA frames, WiFi-AP frames, BT-HCI packets, and control commands. An `if_type` field in the header distinguishes them."
- > "Same shape as brcmfmac (Ch 91), but the transport is the esp-hosted SPI protocol instead of SDIO."
  - "Same shape" idiom. Keep, but rewrite: "The structure mirrors brcmfmac (Ch 91). Only the transport changes — the esp-hosted SPI protocol instead of SDIO."
- > "For a kernel-integrated AT-mode (making it look like a network interface), `drivers/net/ppp/` + a chat script can layer PPP over the AT link — but esp-hosted is the better path if you want a real `wlan0`."
  - 38-word sentence with parenthetical-as-clarifier + em-dash. Rewrite: "If you want AT-mode to look like a network interface, the kernel's PPP driver (`drivers/net/ppp/`) plus a chat script can layer PPP over the AT link. esp-hosted is still the better choice for a real `wlan0`, though."

### Needs more depth
- §93.4 The "control packet" path (cfg80211 op → protobuf-encoded control request → ESP firmware → response) is described in one sentence but is the most interesting part. Add 6 lines: "On the control side, esp-hosted defines a small protobuf-based RPC. cfg80211 ops on the Linux side (`.scan`, `.connect`, `.set_key`) build a protobuf request, prepend the same `if_type` framing as data packets but with `if_type=CTRL`, and send it over the SPI link. The ESP firmware deserializes the protobuf, calls Espressif's `esp_wifi_*` APIs in its own RTOS, and returns the result framed the same way. This RPC pattern is how a single transport carries data and control without ambiguity — the same model FlexCAN, slcan, and many radio modems use."
- §93.5 The AT-command "you'll need a TLS-capable firmware" caveat is one parenthetical. Worth a sentence: "Espressif's AT firmware ships in two variants: bare TCP and a larger TLS-capable build with mbedTLS. The TLS variant is bigger and slower on the ESP, but it lets a small Linux host avoid bringing in OpenSSL. Pick at firmware-flash time."

---

## Ch 94 — WiFi+BT combo modules

### AI wording / sledgehammer / buzzwords
- > "modules that pack WiFi *and* Bluetooth into one chip sharing one 2.4 GHz antenna"
  - "Pack X and Y" idiom. Rewrite: "Modules that combine WiFi and Bluetooth on one chip, sharing one 2.4 GHz antenna."
- > "The defining challenges: bringing up *two* radios on *one* chip over *two* different buses, and the **coexistence** problem — both radios fighting over the same 2.4 GHz band and the same antenna."
  - 32 words, italics, em-dash, "fighting over" metaphor. Rewrite: "Two challenges define the topic. First, you must bring up two radios on one chip over two different buses. Second, the coexistence problem: both radios share the same 2.4 GHz band and the same antenna."
- > "But bringing up both halves — WiFi on SDIO (Ch 91) *and* BT on UART — and getting them to coexist is more than twice the work of either alone."
  - 26-word run-on with double em-dash. Rewrite: "Bringing up both halves takes more than twice the effort of either alone — WiFi on SDIO (Ch 91), BT on UART, then making them coexist."
- > "**one chip, two buses, two subsystems, one antenna**."
  - Bolded four-item triplet (quadruplet) `Focus:`. Keep but un-bold or rewrite as prose: "One chip carries two radios on two buses. They share one antenna and are managed by two independent kernel subsystems."
- > "They're independent driver stacks that happen to share silicon."
  - "Happen to share" idiom. Rewrite: "The two stacks are independent. They share silicon, but nothing else in software."
- > "Nothing new. The combo module's WiFi is just an AP6212-WiFi as in Ch 91."
  - Two-fragment dismissal. Acceptable in context (it's recapping). Could merge: "Nothing new — the combo module's WiFi is exactly the AP6212 case from Ch 91."
- > "Common mistake: getting WiFi working, declaring victory, shipping — then discovering BT was never wired up correctly. Test both, separately and together."
  - "Declaring victory" idiom + em-dash sting. Rewrite: "A common mistake is to get WiFi working and assume the job is done. Then a field unit fails because the BT side was never wired correctly. Test both, separately and together."

### ESL readability
- > "WiFi throughput craters, BT audio stutters."
  - "Craters" is informal English. Rewrite: "WiFi throughput collapses and BT audio stutters."
- > "The chip solves this internally with **PTA** (Packet Traffic Arbitration, also called coexistence or 'coex'): a hardware arbiter that time-slices the radio between WiFi and BT, prioritizing based on packet type (BT audio is latency-sensitive → high priority; WiFi bulk data → can wait a few ms)."
  - 47-word colon-introducing run-on with arrow and parenthetical. Break: "The chip solves this internally with **PTA** (Packet Traffic Arbitration, also called coexistence or 'coex'). PTA is a hardware arbiter that time-slices the radio between WiFi and BT, prioritising by packet type. BT audio is latency-sensitive and gets high priority. WiFi bulk data can wait a few ms."
- > "The drop is the 'cost' of coexistence — typically 10–30 % WiFi throughput reduction during active BT."
  - Fragment-quoted "cost" + em-dash. Rewrite: "This drop is the cost of coexistence — typically 10 to 30 percent less WiFi throughput while BT is active."
- > "(declare it once, reference from both pwrseq and the BT node)"
  - Concise; keep.

### Needs more depth
- §94.4 The HCI layering (BlueZ daemon → kernel BT subsystem → hci_uart line discipline → controller) is one diagram with no explanation of what each layer does. For an MCU reader meeting Bluetooth here, add 6 lines:
  - "**bluetoothd** is the BlueZ user-space daemon. It owns GAP (advertising/scanning), GATT (services and characteristics), SMP (pairing), and the higher profiles (A2DP audio, HID keyboards). Applications talk to it over D-Bus.
  - **The kernel BT subsystem** (`net/bluetooth/`) exposes a socket family (`AF_BLUETOOTH`) and implements HCI transport, L2CAP, and the lower stack. bluetoothd opens an HCI socket and sends commands through this layer.
  - **hci_uart line discipline** turns a UART into an HCI transport. It frames H4 packets (one type byte + payload) on the wire and presents `hci0` to the kernel. `hci_bcm` is a vendor-glue module that loads the Broadcom firmware patch and handles the baud-rate switch."
- §94.5 Coexistence: the "three-wire coex" between separate WiFi and BT chips is mentioned in one sentence but never named in standard form. Add: "When WiFi and BT live on separate chips, they negotiate over a three-wire PTA bus: BT_PRIORITY (BT says 'I am about to transmit, importance is X'), BT_ACTIVE (BT is transmitting now), and WLAN_ACTIVE (WiFi is transmitting now). Each chip uses the other's signals to defer or steal the radio. Combo modules collapse this into on-die arbitration, which is faster and quieter."

---

## Ch 95 — HCI Bluetooth over UART/USB

### AI wording / sledgehammer / buzzwords
- > "since you don't write the HCI controller (it's the chip's firmware) — building a **BLE GATT peripheral** in user-space via BlueZ's D-Bus API (the meaningful 'build it yourself' part)."
  - 30+ word sentence with em-dash and quoted "build it yourself." Rewrite: "You will not write the HCI controller — that lives in the chip's firmware. What you do build is a **BLE GATT peripheral**, in user-space, through BlueZ's D-Bus API."
- > "Understanding HCI demystifies the whole stack; building a GATT peripheral is the practical skill."
  - "Demystifies" is buzzy. Semicolon glue. Rewrite: "Understanding HCI makes the rest of the stack feel less magical. Building a GATT peripheral is the practical skill."
- > "**the controller runs the BT link layer; you build the GATT application**."
  - Bolded `Focus:` with semicolon glue. Rewrite: "The controller (chip firmware) runs the BT link layer. You build the GATT application on top."
- > "Your code is the 'application' — a GATT server exposing characteristics."
  - Em-dash glue. Rewrite: "Your code is the 'application' layer. It is a GATT server that exposes characteristics."
- > "You don't touch HCI directly; you define services and BlueZ handles the rest."
  - Semicolon glue. Rewrite: "You do not touch HCI directly. You define services, and BlueZ handles the rest."
- > "The from-scratch deliverable is a GATT peripheral, written against BlueZ's D-Bus API."
  - Fine.
- > "You rarely send raw HCI — BlueZ does. But understanding it lets you read `btmon` traces (which decode every HCI packet) and debug."
  - Two short sentences but "But understanding" is awkward. Rewrite: "You rarely send raw HCI yourself. BlueZ does it for you. Knowing the format lets you read `btmon` traces and debug."
- > "(The full example needs the service-object + advertisement-object registration boilerplate — ~250 lines total. BlueZ ships a complete `example-gatt-server` in `test/` that you adapt.)"
  - Parenthetical-as-paragraph + em-dash. Move out of parentheses: "The full example needs the service-object and advertisement-object registration boilerplate — about 250 lines in total. BlueZ ships `example-gatt-server` in `test/` and most production code starts from that."
- > "This is the canonical 'BLE sensor that talks to a phone app' pattern."
  - "Canonical" overused in this batch (5+ occurrences). Drop: "This is the standard pattern: a BLE sensor talking to a phone app."

### ESL readability — multiple long sentences
- > "**HCI** (Host Controller Interface) is the standardized boundary between the *host* (Linux + BlueZ) and the *controller* (the BT chip). It's a packet protocol with four packet types:"
  - 28-word sentence with three parentheticals. Rewrite: "**HCI** (Host Controller Interface) is the standardised boundary between two halves of any Bluetooth system: the *host* (Linux plus BlueZ) and the *controller* (the BT chip). HCI is a packet protocol. It defines four packet types:"
- > "BlueZ's `LEAdvertisingManager1` D-Bus interface controls advertising; you register an advertisement object specifying the name, service UUIDs, and any manufacturer-specific data."
  - Semicolon glue, 22 words. Rewrite: "BlueZ exposes a `LEAdvertisingManager1` D-Bus interface that controls advertising. You register an advertisement object with the name, service UUIDs, and any manufacturer-specific data."
- > "More code, but no Python runtime + better performance."
  - "+" used as conjunction. Rewrite: "More code, but no Python runtime and better performance."

### Needs more depth — IMPORTANT, BlueZ + GATT + D-Bus is dense
- §95.3 The BlueZ architecture diagram lists four layers but does not explain *what GATT is* in protocol terms. For an MCU reader who has only read about UART-style serial Bluetooth, add 6 lines:
  - "**GATT** (Generic Attribute Profile) is BLE's data model — every BLE service exposed by a peripheral is a tree of *attributes*, each addressed by a 16-bit *handle* and tagged with a UUID. A *service* attribute groups *characteristic* attributes; a characteristic attribute groups a *value* attribute and any *descriptors* (units, format, configuration). A central reads or writes a characteristic by handle and UUID, or it *subscribes* (writes 0x01 to the Client Characteristic Configuration descriptor) and the peripheral notifies it on change.
  - GATT runs on top of **ATT** (Attribute Protocol), a tiny request/response protocol on top of **L2CAP**, which runs on top of HCI ACL packets. Five layers, but you only ever touch the top one through BlueZ's D-Bus API."
- §95.6 The Python GATT-server example is presented but the *D-Bus object registration* is elided as "boilerplate." For a reader new to D-Bus, add a short paragraph naming the missing pieces: "The missing boilerplate is: (1) a service object inheriting `dbus.service.Object` and exporting `GetManagedObjects` so `org.bluez` can discover the tree; (2) registration with `org.bluez.GattManager1.RegisterApplication`; (3) an `LEAdvertisement1` object describing the advertising data; (4) registration with `org.bluez.LEAdvertisingManager1.RegisterAdvertisement`. The BlueZ sample in `test/example-gatt-server` shows all four. Read that file alongside this chapter."
- §95.7 GAP is only mentioned in passing. One paragraph: "**GAP** (Generic Access Profile) is BLE's connection lifecycle. It defines the *roles* (peripheral, central, broadcaster, observer), the *advertising* and *scanning* state machines, and the *connection parameters* (interval, latency, supervision timeout). A peripheral advertises in one of three modes (connectable undirected, connectable directed, non-connectable). A central scans (passive or active) and may initiate a connection. After connection, GAP yields to GATT. BlueZ's `Adapter1` interface owns the GAP-level controls; once you connect, you mostly use `GattCharacteristic1` instead."

---

## Ch 96 — AT-command BLE modules

### AI wording / sledgehammer / buzzwords
- > "The module *is* the Bluetooth stack; Linux just talks to a UART."
  - Italic "is" + semicolon glue. Rewrite: "The module is the Bluetooth stack. Linux only talks to a UART."
- > "The trade-off: you're limited to the module's fixed GATT profile (usually a single 'transparent UART' characteristic), max ~few hundred bytes/sec, and a non-standard, vendor-specific command set."
  - 30-word colon-introducing run-on with two parentheticals. Rewrite: "The trade-off is real. You are stuck with the module's fixed GATT profile, usually a single 'transparent UART' characteristic. Throughput tops out at a few hundred bytes per second. The AT command set is vendor-specific and non-standard."
- > "**the module is a 'BLE-to-serial cable'**."
  - Bolded `Focus:`. Rewrite: "The module behaves like a wireless serial cable."
- > "It's a wireless serial port. Linux needs *zero* Bluetooth code — just open `/dev/ttymxc2` and read/write."
  - "Zero" + italic + em-dash. Rewrite: "It is a wireless serial port. Linux needs no Bluetooth code — just open `/dev/ttymxc2` and call `read`/`write`."
- > "**The cloning problem**: 'HM-10' modules are cloned five ways, with different firmware and *different AT command syntax*."
  - "Cloned five ways" is idiomatic + bolded subheading-in-prose. Rewrite: "**Clone variants are a real problem.** There are at least five different 'HM-10' modules in the market, each with different firmware and different AT command syntax."
- > "This is *the* reason to use an AT-BLE module: your application code is just serial I/O. No D-Bus, no GATT objects, no BlueZ daemon."
  - Italic "the" + triplet rhythm. Rewrite: "This is the main reason to choose an AT-BLE module. Your application is plain serial I/O — no D-Bus, no GATT objects, no BlueZ daemon."
- > "Compare to Ch 95's GATT server: ~250 lines of D-Bus code vs ~10 lines of serial I/O. The AT module trades capability for simplicity."
  - "Trades capability for simplicity" is reasonable but Claude-flavored. Keep, but rewrite: "Compare to Ch 95's GATT server: about 250 lines of D-Bus code versus ten lines of serial I/O. AT modules trade features for simplicity."
- > "The AT module is for quick, simple, 'wireless serial cable' use."
  - Triplet ("quick, simple, 'wireless serial cable'"). Rewrite: "The AT module fits quick, simple 'wireless serial cable' use cases."

### ESL readability
- > "(Note: genuine HM-10 commands have *no* `\r\n` terminator and *no* `=` for sets in older firmware — e.g., `AT+NAMEMyDevice` not `AT+NAME=MyDevice`. Clones vary. The `AT+VERS?` response identifies your variant.)"
  - 32-word parenthetical block. Move out: "Caveat on syntax. The genuine HM-10 commands omit the `\r\n` terminator and the `=` sign for set commands in older firmware (e.g., `AT+NAMEMyDevice`, not `AT+NAME=MyDevice`). Clone command sets vary. Run `AT+VERS?` first — the version response identifies your variant."
- > "That's the entire integration — no Bluetooth code, just `read`/`write` on a UART."
  - "That's the entire" trim-and-stop. Rewrite: "That is the whole integration. There is no Bluetooth code — just `read` and `write` on a UART."

### Needs more depth
- §96.2 The "transparent UART" model is the chapter's central idea but never explains *how* the module presents it on the BLE side. Add 4 lines: "On the BLE side, the module exposes a single vendor service (UUID varies by module — `ffe0` for HM-10) with two characteristics: a notify characteristic for module-to-phone data, and a write characteristic for phone-to-module data. The phone app subscribes to notifications and writes to the write characteristic. The module bridges these characteristics to its UART TX and RX. No GATT discovery is needed by the user — phone apps like 'Serial Bluetooth Terminal' know the HM-10's UUIDs by name."
- §96.5 The "wrong choice when" list is good, but the *throughput limit* deserves the math: "BLE 4.x connection events run at intervals of 7.5 ms to 4 s, negotiated. Each event can carry one ATT MTU's worth of data (default 23 bytes, often negotiated to 247). At a 30 ms connection interval and 20-byte payload, raw rate is ~5.3 KB/s. Most AT modules cap at the default MTU and a 100 ms interval, giving ~200 B/s in practice. Above this rate, modules drop bytes silently — there is no flow control between the UART side and the BLE side."

(Short chapter — kept to top issues.)

---

## Ch 97 — BLE Mesh

### AI wording / sledgehammer / buzzwords
- > "We cover the mesh architecture (elements, models, addresses, publish/subscribe), the **bluez-mesh** stack on Linux, provisioning a node into a network, and a worked lighting-control example with the i.MX6ULL as a mesh gateway/provisioner."
  - 35-word list-as-prose. Rewrite: "This chapter covers four things: the mesh architecture (elements, models, addresses, publish/subscribe), the **bluez-mesh** stack on Linux, the provisioning flow that adds a node to a network, and a worked lighting-control example with the i.MX6ULL as gateway and provisioner."
- > "smart lighting (the killer app), building sensors, industrial monitoring — by having nodes *relay* each other's messages."
  - "Killer app" cliché. Rewrite: "smart lighting (the dominant use case), building sensors, industrial monitoring. Nodes relay each other's messages to extend coverage."
- > "It's the technology behind commercial smart-lighting systems (the kind in offices and warehouses)."
  - Editorial parenthetical. Rewrite: "It is the technology behind commercial smart-lighting systems, the kind installed in offices and warehouses."
- > "An i.MX6ULL makes an excellent mesh **gateway** (bridging the mesh to WiFi/cloud) or **provisioner** (adding nodes to the network)."
  - 23-word sentence with two parentheticals. Rewrite: "An i.MX6ULL makes a good mesh gateway, bridging mesh traffic to WiFi or the cloud. It can also act as a provisioner, adding new nodes to the network."
- > "**mesh is publish/subscribe over flooded BLE adverts, addressed by models**."
  - Bolded equation-style `Focus:`. Rewrite: "Mesh is a publish/subscribe protocol layered on flooded BLE advertisements, with addresses tied to models."
- > "'Turn off all kitchen lights' = publish OnOff=0 to the 'kitchen' group; every light subscribed to 'kitchen' responds."
  - Equation glyph + semicolon. Rewrite: "'Turn off all kitchen lights' means: publish OnOff=0 to the 'kitchen' group. Every light subscribed to 'kitchen' responds."
- > "Flooding + relay gives whole-building coverage without infrastructure."
  - "+" + buzzword "infrastructure." Rewrite: "Flooding plus relay gives whole-building coverage without any backbone wiring."
- > "Mesh trades the simplicity of point-to-point for scale and coverage."
  - Stock Claude phrasing ("trades X for Y"). Rewrite: "Mesh sacrifices some point-to-point simplicity. In return you get scale and coverage."
- > "A message 'hops' node-to-node: a light in the far room relays a message it overhears, extending range far beyond one radio's reach."
  - 23-word sentence with colon + comma chain. Rewrite: "A message hops node-to-node. A light in a far room can relay a message it overhears, extending the range far beyond a single radio's reach."
- > "That's the power of group addressing."
  - Mic-drop line. Rewrite: "Group addressing is what makes this possible."
- > "the canonical role for a Linux device in a mesh network"
  - "Canonical" overused. Rewrite: "the typical role for a Linux device in a mesh network."
- > "This is analogous to the GATT server of Ch 95 but for mesh models — more involved, and the bluez-mesh D-Bus API is less mature than the GATT one."
  - "Analogous to" formal + em-dash + "more involved" fragment-ish. Rewrite: "The structure is similar to the GATT server of Ch 95 but applies to mesh models. It is more involved, and the bluez-mesh D-Bus API is less mature than the GATT one."

### ESL readability
- > "BLE point-to-point (Ch 95) reaches one device at ~30 m. BLE Mesh covers an entire building with hundreds of nodes — smart lighting (the killer app), building sensors, industrial monitoring — by having nodes *relay* each other's messages."
  - 41-word two-sentence run with double em-dash. Already addressed above.
- > "Mesh has sequence-number replay protection; if a node's stored sequence state is lost (flash erased), it may be rejected."
  - Semicolon glue. Rewrite: "Mesh uses sequence numbers as replay protection. If a node's stored sequence state is lost (because its flash was erased), the network may reject it."
- > "Plan addressing (unicast ranges, group allocation) before deploying hundreds of nodes."
  - Parenthetical readable; keep.

### Needs more depth
- §97.2 The mesh `model` concept is the key abstraction but described only as "the functional units." For an MCU reader, add a worked example showing the bytes on the wire: "A 'Generic OnOff Set' message published by a wall switch to address 0xC000 is a 7-byte access payload: opcode 0x8202 (Generic OnOff Set Unacknowledged), 1 byte OnOff value (0x01 or 0x00), 1 byte transaction ID, optional 2 transition-time bytes. Encrypted with the AppKey, prepended with sequence number + source address + destination 0xC000, encrypted again with the NetKey, then transmitted on the BLE advertising channels. Subscribed Generic OnOff Server models on every kitchen light receive, decrypt twice, decode the opcode, and act on the value. The model defines which opcodes a server handles and which messages a client may publish."
- §97.4 The split between bluetoothd and bluetooth-meshd is mentioned in the pitfalls but never explained where it matters. Add a paragraph in §97.4: "bluetoothd and bluetooth-meshd cannot both own the same HCI controller. Both want exclusive access to advertising and scanning. On a single-controller system, you either run mesh (lose GATT/classic) or run GATT/classic (lose mesh). Production designs that need both use two controllers — one for mesh, one for non-mesh BT — typically a combo module for GATT/classic and a separate dongle (USB or a second UART) for mesh."
- §97.3 Provisioning is one of the most security-critical operations in any IoT product. The current description is procedural but does not explain *why* each step matters. Add three short notes after the seven-step list:
  - "**Why ECDH?** The provisioner and the unprovisioned device derive a session key without ever transmitting it. An attacker passively sniffing the air sees the public keys but cannot reconstruct the shared secret. Without this, mesh would be trivially crackable.
  - **Why OOB authentication?** ECDH defeats passive sniffing but not active man-in-the-middle. OOB (a code on the device's label, a number to confirm on its display, a QR code) lets the user verify they are provisioning *this* device, not an attacker's clone sitting next to it.
  - **Why does the NetKey not encrypt the payload?** Relay nodes need to read the destination address and forward the packet. They do not need to read the application data. The two-key scheme (NetKey for routing, AppKey for content) is what lets cheap relay nodes participate without holding application secrets."





---

# Part VIIc — Style/ESL Review (Ch 98–117, Group M–O cookbook)

## Cross-cutting patterns

- **Em-dash chaining of three clauses.** Still the book's signature tic. Every chapter's `What:` blurb does it (Ch98 LoRa: "long-range modulation (chirp spread spectrum) reaching multiple kilometres at sub-100 kbps — Four real radios compared — and bring up a real LoRaWAN gateway"). Within sections, especially in "Why" and "Focus" headers, three em-dashes per paragraph is the norm. Replace most with periods.
- **Semicolon-glued clauses.** Heaviest in Pitfalls bullets across all 20 chapters ("X happens; Y is the fix"). Convert to two sentences.
- **"Not X — but Y" / "X. Y." sledgehammer.** Especially in Focus blurbs: "The radio is easy. The link budget is the engineering." (Ch98), "The radio is easy. The RF path is where projects die." (Ch98), "Pick the cell. The bands pick you back." pattern recurs in Ch102, 103, 104. Use once per chapter at most.
- **Buzzwords this part overuses:** `crucial`, `critical`, `canonical`, `dominant`, `dominant pattern`, `dominates`, `the killer feature`, `killer detail`, `the whole engineering job`, `the engineering`, `brutal trade`, `cargo-cult`, `mechanical`, `genuinely possible`, `dance` (used twice for "register dance"), `landscape`, `realm`. Drop or vary.
- **Marketing-flavoured praise.** "the workhorse for…" (Ch98), "the killer feature" (Ch99 ×2, Ch100 ×1), "the dominant cheap radio" (Ch99 title), "the only short-message radio that…" (Ch98), "genuinely possible" (Ch98 §98.8), "the Linux skill is" (Ch100). Trim.
- **"That's it." / "That's the whole pattern." / "Done."** Used as a stand-alone sentence at least once per chapter (Ch98 §98.3 "That's it. Eighty registers…"; Ch99 §99.5 "Two boards, same binary…"; Ch100 §100.5 "Done."; Ch103 "Done."; Ch107 "Done.", etc.). Pick one or two per part.
- **Triplet rhythm.** "Read status, ack, snapshot, defer, return." style lists used to signal expertise. When repeated within a chapter it reads AI-generated.
- **Royal "we'll/let's"** is largely absent in Part VII (good), but "we" still appears as authorial voice in Ch98 §98.6 ("We build the smallest possible…") and Ch101 §101.4. Imperative ("Build…") reads cleaner.
- **Numeric drive-by claims without anchor.** "80 % of the budget" (Ch98), "80 % of the RF risk" (Ch98), "80 % of 'ZigBee unreliable' reports" (Ch100), "80 % of the engineering" (Ch101), "90 % of the bugs" (Ch103). The same "80 %" appears 5+ times across this part. Vary or drop.
- **"the X is the engineering" / "X is the whole job".** "The radio is easy. The link budget is the engineering." (Ch98), "the protocol on top … is the other 20 %" (Ch101), "the calibration is 80 % of the engineering" (Ch101). Authorial tic.

---

## Ch98 — LoRa

### AI wording / sledgehammer / buzzwords
- > "long-range modulation (chirp spread spectrum) reaching multiple kilometres at sub-100 kbps. Four real radios compared: … then bring up a real LoRaWAN gateway with **ChirpStack**."
  - One sentence, three colons, three em-dashes worth of structure. Break into three plain sentences in the `What:` blurb.
- > "Most engineers cargo-cult the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna kills 80 % of the budget. This chapter strips the magic."
  - "Cargo-cult" is jargon; "strips the magic" is marketing. Rewrite: "Many engineers copy the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna costs most of your link budget. This chapter walks the whole stack."
- > "The radio is easy. The link budget is the engineering."
  - Slogan. Keep at most once in the Focus blurb; do not repeat the same shape ("The radio is easy. The RF path is where projects die.") in §98.4.
- > "The trade is brutal: LoRa buys range with bitrate."
  - "Brutal trade" is fan-prose. Rewrite: "The trade is direct: LoRa buys range with bitrate."
- > "every commercial UWB anchor system uses it." / "every other chapter says 'the kernel driver does this.'"
  - Absolute "every" claims; soften ("most commercial anchor systems", "almost every other chapter").
- > "A private LoRaWAN network running on one i.MX6ULL is genuinely possible."
  - "Genuinely possible" is marketing hedging. Rewrite: "A private LoRaWAN network on one i.MX6ULL is realistic."
- > "Mandatory rules — every one of these has bricked a board somewhere"
  - Em-dash glue + "bricked somewhere" idiom. Rewrite: "Mandatory rules. Every one of these has destroyed a board in the field."
- > "*Especially* during bring-up when you're tempted to 'just see if it works.'"
  - Italics + quoted slang. Rewrite: "This matters most during bring-up, when it is tempting to power the radio without an antenna just to see if it responds."
- > "The chip is alive after `Sleep`."
  - Pitfall headline reads cute. Rewrite: "`Sleep` does not erase state on SX127x — but on SX1262 Cold Start it does."

### ESL readability
- > "Understanding the **spreading factor / bandwidth / coding rate / preamble** four-tuple — and what each costs in air-time, sensitivity, and power — is the whole engineering job."
  - 30 words, em-dash mid-clause. Rewrite: "The four-tuple of spreading factor, bandwidth, coding rate, and preamble is the whole engineering job. You must know what each one costs in air-time, sensitivity, and power."
- > "Sensitivity improves ~2.5 dB per SF step: SF7 ≈ –123 dBm, SF12 ≈ –137 dBm — that's **14 dB** range, or ~5× the distance."
  - Multi-clause with em-dash. Rewrite: "Sensitivity improves about 2.5 dB per SF step. SF7 is around −123 dBm; SF12 is around −137 dBm. That is 14 dB of headroom, or roughly 5× the range."
- > "Most engineers cargo-cult the 'Arduino LoRa library' without understanding the modulation, the registers, or why a bad antenna kills 80 % of the budget."
  - 28 words, idiom + triplet. See rewrite above.
- > "This is unusual in this book — every other chapter says 'the kernel driver does this.' Here the kernel is the bus controller and nothing more."
  - "Here the kernel is the bus controller and nothing more" — try "On LoRa, the kernel is only the SPI bus controller."

### Needs more depth
- §98.2 "Bitrate ≈ `SF × BW / 2^SF × CR`". The formula is given but **CR is undefined in the formula** (in CR = 4/5, do you mean the literal fraction 4/5, or just the numerator?). Spell it out: "CR here is the literal ratio (4/5 = 0.8, 4/8 = 0.5)." Otherwise the reader gets a number an order of magnitude off.
- §98.2 The CSS diagram is decorative; it does not show that the *start frequency* of each chirp encodes the symbol value. Add one line: "All chirps sweep the same `BW` Hz. The *starting* frequency of each chirp encodes `SF` bits — that is what gives you the data."
- §98.5 "Mainline has refused most LoRa kernel patches" — the reader does not know *why*. One sentence: "Mainline maintainers want a stable subsystem (like ieee802154 or nl80211); the LoRa community never converged on a common MAC, so each driver looks different and none have been accepted."
- §98.6 The `Frf = freq × 2^19 / 32e6` formula appears without derivation. One sentence: "The PLL divides the 32 MHz XTAL by `2^19 / Frf`; rearrange and `Frf = freq × 2^19 / 32e6` is the value you load."
- §98.6 RSSI math is asymmetric (HF subtracts 157, LF subtracts 164) is stated but **why** is left implicit. One sentence: "SX1276 routes HF (>525 MHz) and LF (<525 MHz) through different gain stages with different reference points, so the offset differs by 7 dB."
- §98.8 LoRaWAN classes A/B/C are *named* but not explained. One paragraph: "Class A devices open a 2-second RX window after each uplink only — lowest power. Class B adds beacon-aligned periodic RX windows. Class C keeps RX on continuously — only mains-powered devices."
- §98.10 Pitfall "Duty cycle violations": the math "1 % of 2 packets/min" feels arbitrary. Show the path: "EU 868 g1 = 1 % duty cycle = 36 s of transmit per hour. SF12 at 51 bytes = 2.3 s/packet → 36 / 2.3 = ~15 packets per hour, or two per ~minute."

---

## Ch99 — Sub-GHz proprietary (nRF24L01, CC1101, CC1200)

### AI wording / sledgehammer / buzzwords
- > "**these chips are state machines you drive with SPI commands**; the radio behavior is determined by which state you're in, not by individual register values"
  - Sledgehammer + semicolon. Rewrite: "These chips are state machines driven by SPI commands. The behavior depends on the current state, not on individual register values."
- > "Master the state diagram and the radios are trivial."
  - "Trivial" reads dismissive. Rewrite: "Learn the state diagram and the rest is straightforward."
- > "The killer feature" (used twice — for auto-ACK and for ACK piggyback).
  - Pick one. The auto-ACK one stays; rename the piggyback one to "Bidirectional in one transaction" or similar.
- > "This is why nRF24 dominates the BOM-conscious low-rate radio market."
  - Marketing phrasing. Rewrite: "This is why nRF24 is the default choice when BOM cost matters and rates stay below 1 Mbps."
- > "The single most common reason 'the modules I bought don't work.'"
  - Quoted-slang construction. Rewrite: "This is the most common reason a newly bought module appears dead."
- > "Two boards, same binary, one with `r` arg and one without — instant 1 Mbps ACKed point-to-point link."
  - "Instant" + em-dash glue. Rewrite: "Two boards, same binary — one with the `r` argument, one without — and you have a 1 Mbps ACKed point-to-point link."
- > "CC1101 is harder to use than nRF24L01 because TI gives you the modulator/demodulator + framing primitives but **no auto-ACK**. You build the MAC."
  - "You build the MAC" period-fragment for punch. Fine once. But §99.6 also closes with "the same template fits." Vary.
- > "TI ships **SmartRF Studio** which generates the register dump for any desired modulation / data rate / deviation — you'll absolutely use it."
  - "You'll absolutely use it" is informal. Rewrite: "TI's **SmartRF Studio** generates the register dump for any modulation, data rate, and deviation. Almost everyone uses it for CC1101 bring-up."
- > "The most useful CC1101 starting point is …"
  - "Most useful starting point" is consultant-flavour. Rewrite: "A good CC1101 starting point is …"

### ESL readability
- > "The state-transition rules that bite every newcomer:"
  - "Bite every newcomer" is idiom. Rewrite: "These transition rules catch every newcomer:"
- > "the chip parses it. Easier to use, but very different 'feel' from SX1276 code."
  - "Very different 'feel'" is informal/idiomatic. Rewrite: "Easier to use, but the code looks different from SX1276's."
- > "the in-tree wireless dir does not contain this — verify with current kernel"
  - Parenthetical to the reader mid-sentence. Move to a separate note or footnote.
- > "Switching between TX and RX requires going through Standby-I (`CE=0`, wait 130 µs, set `PRIM_RX`, `CE=1`)."
  - The parenthetical hides the procedure. Promote: "To switch between TX and RX you must pass through Standby-I. Set `CE=0`, wait 130 µs, set `PRIM_RX`, then set `CE=1`."

### Needs more depth
- §99.2 "Enhanced ShockBurst" — `ARD` and `ARC` are introduced inline ("auto-retry delay, auto-retry count") but their *units* are not given. ARD is in 250 µs steps (`SETUP_RETR[7:4]`), ARC is 0..15. The lab code uses `0x3F = ARD=3 (1000 µs), ARC=15` but the reader cannot decode that without the units. Add a sentence with the bit field layout.
- §99.2 The six-pipe diagram shows that pipes 2–5 share the upper 4 bytes with pipe 1. The *why* (per-pipe RX_ADDR is only 1 byte after P1) is missing. One sentence: "Per-pipe RX address registers P2..P5 are only one byte each; the high four bytes are inherited from P1's address. So all five satellites must share that prefix."
- §99.2 STATUS register comes back "for free" on every SPI command — make explicit *why* this is useful. One sentence: "Because the chip clocks STATUS out on the MISO line during the command byte, you read it without any extra SPI transaction. Use this for tight TX-done polling."
- §99.6 CC1101 state machine — 13 states are mentioned but the diagram only shows ~5. Either add the others (CALIBRATE, SETTLING, RX_OVERFLOW, TX_UNDERFLOW, FSTXON, plus IDLE/SLEEP/RX/TX) or downscope the claim to "the five states you use day-to-day".
- §99.6 "registers are write-once and survive across IDLE → RX/TX transitions" — *write-once* is misleading; they are writable any time, just not erased by mode changes. Rewrite: "Once configured, registers persist across IDLE ↔ RX/TX transitions. Strobing `SRX` or `STX` does not reset them. You can rewrite them at any time."
- §99.10 Pitfall "CE pulse too short" gives the spec (≥10 µs) but not what happens if you violate it. One sentence: "If CE is shorter than 10 µs, the chip never advances from Standby-I to TX, the FIFO is not emitted, and `TX_DS` never fires. The driver looks frozen."

---

## Ch100 — ZigBee / Thread / 802.15.4

### AI wording / sledgehammer / buzzwords
- > "the **IEEE 802.15.4** family — the certified mesh networking stack used by Philips Hue, Aqara, Eve, IKEA Trådfri, Google Nest."
  - Bullet-list-as-prose with brand-name parade. Rewrite: "The IEEE 802.15.4 family powers most retail smart-home meshes: Philips Hue, Aqara, Eve, IKEA Trådfri, Google Nest."
- > "Nodes you don't write — you buy them. The Linux skill is **gateway integration**"
  - Three em-dashes worth of telegraphing. Rewrite: "You do not write the nodes; you buy them. The Linux skill is gateway integration."
- > "**the radio firmware is a black box; you talk to it over a serial protocol (EZSP, Thread Spinel, ZNP) that mirrors the network layer**"
  - Sledgehammer + semicolon. Rewrite: "The radio firmware is a black box. You talk to it over a serial protocol (EZSP, Thread Spinel, ZNP) that mirrors the network layer."
- > "the cause of *every* 'my ZigBee network is flaky' thread"
  - "Every" is absolute; "thread" is slang for forum post. Rewrite: "the most common cause of 'my ZigBee network is flaky' reports"
- > "the user's home WiFi is on a different channel than the customer's"
  - Two contradictory roles ("user" vs "customer"). Pick one term.
- > "Devices are categorized by ZCL **clusters**."
  - Fine; keep.
- > "This is the Thread killer feature: every node is a normal IPv6 endpoint."
  - "Killer feature" again. Rewrite: "This is what makes Thread different from ZigBee: every node is a normal IPv6 endpoint."
- > "You'd rarely send raw — the adapter does it — but `btmon`-style debugging (zigbee2mqtt has `debug:true`) shows you the frame stream so you can trace 'why is my pairing failing.'"
  - 37 words, two em-dashes, quoted slang. Break: "You rarely send raw frames; the adapter does it for you. But `btmon`-style debugging (set `debug:true` in zigbee2mqtt) prints the frame stream. This is how you trace a failed pairing."
- > "Modern path."
  - Two-word section opener that reads AI. Rewrite: "This is the modern path."

### ESL readability
- > "Linux's CPU schedule, plus SPI/USB latency, makes a hosted Linux implementation hard."
  - "Linux's CPU schedule" is awkward; "hosted Linux implementation" is jargon. Rewrite: "Between Linux's scheduling jitter and SPI/USB latency, running the MAC on the host CPU is not reliable."
- > "the radio chip runs **its own firmware** containing the PHY + MAC + (optionally) the higher layers."
  - Parenthetical mid-clause. Rewrite: "The radio chip runs its own firmware. The firmware contains the PHY and MAC, and may also contain the higher network layers."
- > "Once running, `wpan0` shows up"
  - "Shows up" idiom. Fine, but follow with concrete output (it does — keep).
- > "A poorly chosen channel gives a network with 30 % packet loss that 'mysteriously works fine at home' (because the user's home WiFi is on a different channel than the customer's)."
  - 30-word run-on, parenthetical mid-sentence. Rewrite: "A poorly chosen channel can give 30 % packet loss in the field. The same network 'works fine at home' because the home WiFi happens to sit on a different channel."

### Needs more depth
- §100.2 The RCP vs NCP vs ZNP table is the heart of the chapter but the *boundary moves* are not described in plain language. Add one paragraph: "Moving the boundary higher (NCP, ZNP) means less work on Linux but a per-stack firmware blob; moving it lower (RCP) means Linux runs the full stack (heavy CPU/RAM) but lets you change MAC behaviour without re-flashing the radio."
- §100.5 ZNP framing protocol "TYPE+SUBSYSTEM selects whose API" — `whose API` is ungrammatical; should be "which subsystem's API." Also the `[TYPE=0x4 MSB | SUBSYSTEM]` byte is described but the four TYPE values (POLL/SREQ/AREQ/SRSP) are not named. Add them so the reader can decode a btmon log.
- §100.5 FCS is "XOR of LEN through last data byte" — confirm: ZNP MT FCS is actually an XOR over LEN+CMD0+CMD1+data. Either confirm or correct.
- §100.6 Spinel header bits "encode flow-control state, transaction IDs, priority" — too vague. Add the actual layout: "Bits 7..6 = flag (always 0b10), bits 5..4 = interface ID, bits 3..0 = TID. Look in `spec/spinel-protocol-src/spinel-frame.md` for the full layout."
- §100.6 The relationship between `wpan0` (Linux netdev), the Thread mesh, and the upstream `eth0` is the trickiest concept for a new reader. Add a short topology paragraph: "otbr-agent runs as a Linux daemon. It owns the radio over a serial line, runs the Thread network stack in user space, and exposes the mesh as a Linux netdev (`wpan0`). It also acts as an IPv6 router between `wpan0` and `eth0`, advertising routes both ways."
- §100.7 nRF52840 802.15.4 hardware accelerator deserves a sentence on *why this matters for Linux*: "Because the hard timing (ACK within 192 µs) is in silicon, the host CPU only needs to handle higher-layer events — milliseconds, not microseconds. That is why RCP-mode Linux Thread works at all."
- §100.11 Pitfall "Network key rotation" — the consequence is given ("un-joins everything") but not the *correct* way to migrate. One sentence: "If you must rotate, use Thread's *commissioner-driven* key update (sends the new key encrypted under the old one); a manual config-file change strands every device."

---

## Ch101 — UWB ranging

### AI wording / sledgehammer / buzzwords
- > "**UWB ranging is a time-of-flight measurement, and ToF accuracy depends on how cleanly the radio captures the first arriving signal**."
  - The whole Focus paragraph is one 75-word block. Break: "UWB ranging is a time-of-flight measurement. ToF accuracy depends on how cleanly the radio captures the first arriving signal. Multipath corrupts the measurement if the demodulator latches the wrong peak. The DW3000 has hardware leading-edge detection and per-antenna delay calibration."
- > "getting the calibration right is 80 % of the engineering. The protocol on top — single-sided two-way ranging vs double-sided TWR vs TDoA — is the other 20 %."
  - "80 % / 20 %" rhetorical split appears elsewhere in this part too. Rewrite: "Calibration is most of the engineering. The protocol on top — SS-TWR, DS-TWR, TDoA — is the smaller piece."
- > "If you're building anything that *positions* objects indoors at sub-metre accuracy, this is the radio."
  - "This is the radio" marketing close. Rewrite: "For sub-metre indoor positioning, UWB is the only practical choice."
- > "the dominant path is **user-space + spidev**."
  - "Dominant path" again (also Ch98, Ch99, Ch101). Rewrite: "Most projects use `spidev` + a user-space driver."
- > "the +10 cm is uncalibrated antenna delay" / "Always calibrate at a known distance first."
  - Fine; useful concrete advice.

### ESL readability
- > "Each pulse is a marker the receiver can timestamp with sub-nanosecond precision. Because radio waves travel ~30 cm/ns, **1 ns of timing error = 30 cm of range error**."
  - Fine; keep.
- > "Error: any clock drift between initiator and responder during Treply scales into the ToF estimate. For ±20 ppm crystals + 200 µs Treply, drift error is ~4 ns ≈ 1.2 m. Bad."
  - Sentence-final "Bad." reads slangy. Rewrite: "For ±20 ppm crystals and 200 µs Treply, the drift is about 4 ns, or 1.2 m of range error. That is unusable."
- > "The trick: scheduling TX at a *future* exact DWT time (the chip has its own 40-bit timestamp counter at 64 GHz / 16 µs wraparound)."
  - "64 GHz / 16 µs wraparound" is wrong: a 40-bit counter at 64 GHz wraps in ~17 s, not 16 µs (the 16 µs is the *low 24 bits* used for delayed-TX scheduling). Fix or clarify the relationship.
- > "Even this skeleton reveals the protocol: ToF = (response-time at initiator − reply-time at responder) / 2."
  - "Reveals the protocol" reads grand. Rewrite: "Even this skeleton shows the protocol: ToF = (response-time at initiator − reply-time at responder) / 2."

### Needs more depth
- §101.1 The DS-TWR formula `ToF = (Tround1×Tround2 - Treply1×Treply2) / (Tround1+Tround2+Treply1+Treply2)` is given without derivation. The reader who has not seen the symmetric DS-TWR paper does not know *why* this cancels drift. Two sentences: "DS-TWR cancels first-order clock drift because each side measures one full round-trip and the asymmetric-Treply formula divides them. The numerator's product/difference structure makes the drift cancel out — see McElroy 2014 for the algebra."
- §101.2 The TX/RX timestamp registers are 40-bit (`5 bytes`). The chapter mentions "5-byte timestamp arithmetic with the DWT 40-bit rollover" only in the closing paragraph of §101.5. Move this fact to §101.2 where it belongs: "Timestamps are 40 bits at 64 GHz × 128 / 499.2 ≈ 15.65 ps per tick. They wrap every 17.2 s. Use uint64 arithmetic and a wrap-aware subtract."
- §101.4 `dwt_setdelayedtrxtime(resp_tx_ts >> 8)` discards the low 8 bits — the reader will ask why. One sentence: "The delayed-TX register has 32 bits (the low 8 bits of the 40-bit timestamp are zero on the wire). Shift right by 8 to load it."
- §101.5 The `poll_msg` byte array `{ 0x41, 0x88, 0, 0xCA, 0xDE, 'R','X','I','N',0xE0 }` is opaque. Decode the IEEE 802.15.4 MHR fields: FCF=0x8841 (data frame, short addr, PAN-ID compress), seq=0, dest PAN=0xDECA, dest short=…, function code 0xE0. Otherwise the reader cannot adapt the code.
- §101.7 Antenna-delay calibration is mentioned but never quantified. Add the typical magnitude (the DWM3000 default is around 16450 ticks ≈ 258 ns; you tune ±200 ticks at a known 1.000 m).
- §101.10 Pitfall "Treply too short" gives `<200 µs` as the failure threshold but does not say what the chip does (does it silently drop the TX? abort with a status flag?). Add: "If Treply is shorter than the responder's scheduled TX time, the DW3000 sets `TXPUTE` (TX power-up time error) in SYS_STATUS and never transmits. Always check this bit on the responder."

---

## Ch102 — USB 4G LTE modems

### AI wording / sledgehammer / buzzwords
- > "the **USB-attached cellular modem** — by far the dominant cellular path on Linux."
  - "By far the dominant" is marketing. Rewrite: "The USB-attached cellular modem is the most common cellular path on Linux."
- > "the trick is the four-layer onion of *which interface mode the modem is in* … *which kernel driver matches it* … *which user-space tool brings up data*."
  - "Onion" metaphor + triplet + italics. Rewrite: "There are three layers to keep straight: the USB interface mode the modem advertises, the kernel driver that binds to it, and the user-space tool that activates the data session."
- > "This chapter strips the mystery: you'll know what every `lsusb` line means…"
  - "Strips the mystery" is marketing. Rewrite: "After this chapter you can read an `lsusb` line, name the driver that bound each endpoint, and trace the data path."
- > "**the modem is a tiny Linux box inside a USB shell**, exposing multiple interfaces simultaneously"
  - "Tiny Linux box inside a USB shell" — cute but vague. Rewrite: "The modem is a small embedded system in a USB case. It exposes several USB interfaces at once."
- > "The split is unusual on Linux but maps cleanly once you draw the picture."
  - "Maps cleanly" is consultant. Rewrite: "The split is unusual on Linux. The diagram in §102.3 makes it concrete."
- > "**This is the single biggest source of 'my modem is in the wrong mode' confusion**"
  - Quoted-slang + bold. Rewrite: "This is the most common reason a modem appears in the wrong mode."
- > "The 'understand it forever' approach: do everything ModemManager would do, by hand."
  - "Understand it forever" reads slangy. Rewrite: "If you want to understand the path, do everything ModemManager would do by hand."
- > "Quectel ships a reference connection manager (`quectel-CM`) that wraps the above. ~3000 lines of C. It's open source; reading it is a tour of the QMI protocol."
  - "Tour" is informal. Rewrite: "Quectel ships a reference connection manager, `quectel-CM`, that wraps the above (~3000 lines of C, open source). Read it as a worked example of the QMI protocol."

### ESL readability
- > "the trick is the four-layer onion of *which interface mode the modem is in* (RNDIS vs ECM vs MBIM vs QMI vs PPP), *which kernel driver matches it*, and *which user-space tool brings up data*."
  - 40-word, three-italic clauses, five-way parenthetical. See rewrite above.
- > "When you buy a new modem and it appears as nothing, **the missing PID in `option_ids[]` is usually why**."
  - "Appears as nothing" and "is usually why" are awkward English. Rewrite: "When you plug in a new modem and no `/dev/ttyUSB*` appears, the most common cause is a missing PID in `option_ids[]`."
- > "Wait for ModemManager to detect the modem"
  - Fine; keep.
- > "`dnsmasq` integration handles DNS."
  - Fine; keep.
- > "Result: random modem resets mid-call."
  - "Mid-call" is OK but consider "mid-transmission" for ESL clarity (call/voice has a different meaning here).
- > "If you `qmicli --start-network` while ModemManager is running, it'll fight you."
  - "Fight you" idiom. Rewrite: "If you call `qmicli --start-network` while ModemManager is running, the two will race each other and the connection will drop."

### Needs more depth
- §102.2 The PID table is excellent but the *reason* QCFG values map non-monotonically (0=PPP, 1=ECM, 2=MBIM, 3=RNDIS, 5=QMI on Quectel) is confusing for the reader who tries to memorise it. Add: "QCFG values are vendor-defined and not consistent across vendors. Always check the AT manual for your specific module before issuing `AT+QCFG=\"usbnet\",N`."
- §102.3 QMI vs MBIM — the chapter says "preferred for new designs" but never explains *why* (MBIM is the open USB-IF standard; QMI is Qualcomm-proprietary). Add one sentence so the reader can defend the choice.
- §102.3 `qmi_wwan_probe()` skeleton ends at "wwan0 appears, but no IP until QMI session opens." The QMI session-open dance is the chapter's central concept but lives only as bullet steps in the prose. Add the actual QMI message sequence: "Open WDS service → set IP family → start network → get runtime settings → configure netdev. The five steps are the same whether `qmicli`, `quectel-CM`, or ModemManager does it."
- §102.5 The bring-up checklist is great. Add the AT response that means each step failed — `AT+CPIN?` may return `SIM PIN`, `SIM PUK`, `READY`, `NOT INSERTED`. The reader should know what each one demands ("PUK is unlocked only with the carrier's PUK code; three wrong PIN attempts is the usual cause").
- §102.5 PPP path closes with "max ~1–2 Mbps due to byte-stuffing overhead." The mechanism is left implicit. One sentence: "PPP uses HDLC byte-stuffing; bytes 0x7E (frame), 0x7D (escape), and any control byte (0x00–0x1F) are escaped, costing ~10–15 % overhead. Combined with the UART speed limit, this caps PPP at 1–2 Mbps regardless of the cellular link."
- §102.10 Pitfall "CGEV events drop the connection unnoticed" — the example `IPv6 routing advertisement` is vague. Concrete: "Carriers periodically send PDP DEACT or PDP MODIFY in CGEV URCs. Without `AT+CGEREP=2,1` you never see them. Subscribe at boot and reconnect on a DEACT event."

---

## Ch103 — UART AT-command modems

### AI wording / sledgehammer / buzzwords
- > "**PPP is a circa-1989 link protocol with HDLC framing, LCP negotiation, IPCP for IPv4 address, and pap/chap auth — and it still works on every modem ever made**."
  - 35-word sentence, four jargon terms, sledgehammer close. Break: "PPP is a 1989-vintage link protocol. It uses HDLC framing, LCP for link negotiation, IPCP for IPv4 address assignment, and PAP/CHAP for authentication. It still works on every modem ever made."
- > "Master `pppd` + chat + an init.d script and you have a robust auto-reconnecting cellular link"
  - "Master X and you have Y" preachy. Rewrite: "With `pppd`, a chat script, and an init.d (or systemd) supervisor, you have a robust auto-reconnecting cellular link."
- > "good UART discipline."
  - "UART discipline" is jargon. Rewrite: "careful UART setup (flow control, baud, framing)."
- > "**Hardware flow control (RTS/CTS) is non-negotiable** above 9600 baud."
  - "Non-negotiable" is corporate. Rewrite: "Above 9600 baud, hardware flow control is mandatory."
- > "Skip it = packets corrupted = PPP LCP timeouts = 'modem doesn't work.'"
  - Equation-as-prose tic appears again. Rewrite: "Without it, the UART drops bytes, PPP LCP times out, and the modem looks broken."
- > "The clever part: `pppd` does protocol negotiation entirely in user space … but data path is fully kernel-side via the line discipline. Result: low CPU even on a Cortex-A7."
  - "Clever part" + "Result:" rhetorical pair. Rewrite: "Note the split: `pppd` does protocol negotiation entirely in user space (LCP, IPCP packets pass through the `/dev/ppp` ioctl), but the data path runs kernel-side via the line discipline. CPU stays low even on a Cortex-A7."
- > "Crude but works for low-frequency queries."
  - Fine, but "crude" is judgmental. Rewrite: "Simple but works for low-frequency queries."

### ESL readability
- > "PWRKEY pulse low for ≥1 s (≥2 s on Air724) to power on. Some boards tie PWRKEY low through a resistor for auto-on; the cleaner pattern is GPIO control so the host can reset the modem."
  - Two thoughts in one bullet. Rewrite: "Pulse PWRKEY low for at least 1 s to power on. The Air724 needs 2 s. Some boards tie PWRKEY low through a resistor for automatic power-on; GPIO control is cleaner because it lets the host reset the modem."
- > "These **URCs (Unsolicited Result Codes)** are the modem reporting boot progress. Don't talk to it before 'SMS Ready' or you'll get spurious ERROR responses."
  - "Don't talk to it" idiom. Rewrite: "These URCs (Unsolicited Result Codes) report boot progress. Do not send AT commands before 'SMS Ready' — they will return spurious ERRORs."
- > "Add `/etc/init.d/celld` or a systemd unit and the cellular link comes up at boot, recovers from any modem hang via PWRKEY power-cycle, and signals status via an LED. ~30 lines of shell that replace 200 lines of C in many vendor SDKs."
  - 35 words, triplet, closing brag. Rewrite: "Install as `/etc/init.d/celld` or a systemd unit. The link comes up at boot, recovers from any modem hang by power-cycling PWRKEY, and shows status on an LED. About 30 lines of shell, replacing several hundred lines of vendor C."

### Needs more depth
- §103.4 The chat script's quoting and pacing rules are obscure. Add one sentence about pacing: "Each chat line is `EXPECT SEND`. An empty `''` expect means 'send immediately.' If the expect string is not seen within the chat timeout (default 45 s), the script aborts. Set `-T 90` if your network is slow."
- §103.4 LCP/IPCP — the reader sees the names but not what is negotiated. Add: "LCP negotiates link options (MTU, magic number, async control character map). IPCP negotiates IPv4 address, DNS servers, and optionally IPCP-CompressionProtocol. Both run after `CONNECT` and before traffic flows. `pppd -v` shows each packet."
- §103.5 The `TIOCSETD, N_PPP` ioctl is the actual mechanism but is mentioned without explanation. One sentence: "`TIOCSETD` swaps the tty's line discipline. The default (`N_TTY`) treats input as text lines; `N_PPP` treats input as HDLC frames and hands assembled frames to `ppp_generic`. This is how the kernel converts a UART into a netdev."
- §103.6 CMUX framing — the user is told to run `ldattach GSM0710` but the *frame format* is opaque. A short ASCII diagram of a GSM 07.10 basic frame (F8 | DLCI/CR/EA | C/EA | data | FCS | F8) would land well. Cross-reference n_gsm.c so the curious reader can grep.
- §103.8 ECM-via-built-in-USB is described well, but the *mechanism* (the module has an internal USB-to-cell bridge) deserves one sentence: "These modules embed a USB device controller and a CDC-ECM gadget driver inside the module firmware. Linux on the host sees a regular USB Ethernet adapter; the module's own MCU forwards frames to the cellular MAC."
- §103.10 Pitfall "Default route conflict" mentions `replacedefaultroute` and "set metric" but does not show how. One concrete line: "Either pass `replacedefaultroute` to pppd, or omit `defaultroute` and add the route manually with `ip route add default via $PEER_IP dev ppp0 metric 700`."

---

## Ch104 — NB-IoT / Cat-M1

### AI wording / sledgehammer / buzzwords
- > "the **low-power-cellular** subset of LTE — **NB-IoT (Cat-NB1/NB2)** and **LTE-M (Cat-M1)**."
  - Em-dash glue. Fine in a header blurb; keep.
- > "the **PSM (Power Saving Mode)** and **eDRX (extended DRX)** features that make a 19 Ah Li-SOCl2 cell last 10 years"
  - "Make X last 10 years" is marketing. Rewrite: "the PSM and eDRX features that let a 19 Ah Li-SOCl2 cell run a sensor for up to ten years."
- > "**PSM is the killer feature; eDRX is the secondary lever.**"
  - "Killer feature" again (Ch99, Ch100, here). "Secondary lever" is corporate. Rewrite: "PSM is the primary power saver; eDRX is a smaller secondary saving."
- > "**Use PSM aggressively or your battery life numbers are fiction**."
  - "Aggressively / fiction" is fan-prose. Rewrite: "Use PSM correctly or your battery life estimate is wrong by orders of magnitude."
- > "Get the AT commands right or you regress to 100 mA always-on and miss the spec by 1000×."
  - "Regress / miss the spec by 1000×" is consultant. Rewrite: "If the AT commands are wrong, the modem stays at 100 mA always-on. Battery life drops by a factor of 1000."
- > "This is the technology behind smart water meters, GPS livestock trackers, vending-machine telemetry, and rural emergency call-boxes."
  - Brand-name parade. Fine for color; keep.
- > "the engineering is **religiously enforcing PSM duty cycle**."
  - "Religiously" is rhetorical. Rewrite: "the engineering is enforcing PSM duty cycle on every wake."
- > "Still: 10 years on one D-cell with no maintenance. The technology is real; the engineering is …"
  - "The technology is real" reads like a sales line. Rewrite: "Ten years on one D-cell with no maintenance is achievable. The engineering is …"

### ESL readability
- > "TX → wait for downlink ACK → enter PSM, radio off, modem off-but-registered. Network keeps the IP/PDP/security context. Next wake (timer or external GPIO): instant resume, no re-registration."
  - "Instant resume" + arrow-as-prose + parenthetical. Break: "The cycle is: TX, wait for the downlink ACK, then enter PSM. The radio and modem are off, but the network still considers the device registered (IP, PDP context, and security keys are kept). On the next wake — by timer or external GPIO — the device resumes immediately, with no re-registration."
- > "The two timers:" with `T3324`/`T3412` listed as bullets is OK, but the units of `"00000100"` are opaque (it is the 8-bit 3GPP timer encoding). Add one sentence: "The argument is a 3GPP timer value encoded as 8 bits — bits 7..5 are the unit (10 minutes, 1 hour, 10 hours…), bits 4..0 are the count. `00000100` = unit 0 (2 seconds) × 4 = 8 s, *or* by another unit code, 4 hours. Decode with Table 10.5.163 in TS 24.008 to avoid surprise."
- > "annoying but simple."
  - "Annoying" is judgmental. Rewrite: "verbose but simple."
- > "Realistic constraints knock this to **8–12 years**:"
  - "Knock this to" is informal. Rewrite: "Real-world constraints reduce this to 8–12 years:"

### Needs more depth
- §104.2 PSM diagram shows currents but does not explain *why* idle DRX is ~5 mA: the radio is off most of the time but wakes every DRX cycle (typically 1.28 s in LTE idle) to listen for paging. Add: "In idle DRX, the modem wakes every paging cycle (default 1.28 s) to listen for downlink. That dominant cycle averages to ~5 mA."
- §104.2 T3412 / T3324 — the chapter mentions the *names* but not the **fact that PSM lasts up to T3412 minus T3324**. Add: "The math: the modem stays idle-listening for T3324, then enters PSM for the remainder of T3412. So T3412=24h, T3324=4s gives 23h:59m:56s of deep sleep per cycle."
- §104.2 eDRX numbers (~2.92 hours) is the *maximum*; the reader does not know what the *typical* values are. Add a sentence: "Typical eDRX cycles are 20 s, 40 s, 81 s, 163 s, up to 2.92 hours. The carrier negotiates the actual value; many grant only up to 81 s."
- §104.3 `AT+NSOST=0,...,5,68656C6C6F` — explain the structure once: "The arguments are socket-id, remote-ip, remote-port, payload-length, payload-as-hex. `68656C6C6F` is ASCII 'hello.'"
- §104.5 The 47-µAh-per-hour table is excellent. Add the **measurement method**: "These numbers are from a 1 Ω shunt on VBAT with a Tek MDO scope at 1 MS/s and the area integrated in software. A handheld DMM averages and hides the TX spike — do not trust it for this work."
- §104.7 Pitfall "Voltage drop at cold temp" — the "wake-warmer" is mentioned but the *passivation* mechanism is left implicit. One sentence: "Li-SOCl2 cells form a lithium-chloride passivation layer on the anode during storage. This layer raises internal resistance, so the first high-current pulse can drop VBAT to 2.7 V momentarily. A low-current 'depassivation' pulse (e.g., 50 mA for 100 ms) breaks the layer before the modem TX."
- §104.7 "PSM not granted by carrier" — add the *visible* symptom that confirms it: "After `AT+CPSMS=1,,,...`, query `AT+CPSMS?`. If T3412 returns a much smaller value than requested (or `0`), the carrier did not grant your requested PSM and your modem will not enter deep sleep."

---

## Ch105 — RFID / NFC

### AI wording / sledgehammer / buzzwords
- > "The chips are cheap (MFRC522 modules are $1), the standards are real, the security is half-broken (Mifare Classic was cracked in 2008), and the kernel actually has an NFC subsystem (`net/nfc/`) most engineers don't know about."
  - 40-word triplet-plus-bonus with two parentheticals. Break: "The chips are cheap (MFRC522 modules cost about $1). The standards are real. The security is half-broken — Mifare Classic was cracked in 2008. And Linux has an NFC subsystem (`net/nfc/`) that most engineers do not know exists."
- > "**RFID/NFC at 13.56 MHz is inductive coupling — the reader's antenna creates a magnetic field at 13.56 MHz, which powers the tag's IC AND carries data via load modulation**."
  - 35 words with a capitalised "AND" for emphasis. Rewrite: "At 13.56 MHz, RFID and NFC use inductive coupling. The reader's antenna generates a magnetic field. That field powers the tag's IC, and the tag sends data back by modulating its load on the field."
- > "The 'register dance' with the reader chip is mostly:"
  - "Register dance" is informal (used twice in this chapter and earlier in Ch98). Rewrite: "The reader chip uses a fixed sequence of register writes:"
- > "the security is half-broken"
  - Fine but reads as opinion. Quantify: "the basic-Mifare-Classic Crypto1 cipher has been broken since 2008."
- > "Cheap and good enough for 90 % of jobs."
  - "90 % of jobs" is filler. Rewrite: "Cheap and adequate for most access-control work."
- > "Don't try to wind your own without an impedance analyzer — buy a module."
  - "Don't try" + em-dash. Rewrite: "Do not wind your own antenna unless you have an impedance analyser. Buy a tuned module instead."
- > "modules that get this wrong are quietly broken."
  - "Quietly broken" is informal. Rewrite: "modules that compute BCC wrong report a passing read but with corrupt UIDs."

### ESL readability
- > "Tag→reader is **load modulation** at 847.5 kHz subcarrier (Type A); reader→tag is direct ASK modulation at 100 % or 10 %."
  - Two technical claims, one semicolon. Rewrite: "Tag-to-reader uses load modulation with an 847.5 kHz subcarrier (Type A). Reader-to-tag uses direct ASK modulation, at either 100 % or 10 % depth."
- > "Most projects skip it for simplicity and use libnfc directly on `/dev/spidev` or the MFRC522 user-space drivers below."
  - 25 words, one clause. Rewrite: "Most projects skip the kernel NFC stack. They use `libnfc` directly against `/dev/spidev`, or one of the MFRC522 user-space drivers shown below."
- > "What this exposes: …" three-bullet list.
  - The list is concise but mixes API points and edge cases. Consider grouping: "API points: transceive does both TX and RX; bit framing must be set before transceive. Edge cases: BCC byte is a sanity check; HALT must come before the next REQA."

### Needs more depth
- §105.2 The diagram is decorative but the *encoding* (Miller for tag-to-reader, Modified-Miller / Manchester for reader-to-tag) is mentioned in the Focus blurb and never illustrated. A simple ASCII waveform of one bit in each direction would land well for the curious reader. At minimum, name the encoding directions correctly in §105.2.
- §105.2 Anticollision steps are shown but the algorithm is not explained — the reader is told it produces the UID without seeing the binary search. One paragraph: "When two or more tags answer REQA, their UIDs collide. The reader sends ANTICOLL with a known prefix length; tags whose UID matches the prefix respond. The reader detects the first colliding bit, fixes its prefix to one side, and recurses. This is a binary tree walk on the UID — log2(N) rounds for N tags."
- §105.3 Crypto1 / Authent — the chapter mentions the Authent command but does not explain that **the tag never sends the key**; it is a challenge-response. One sentence: "Authent never transmits the key on the air; the reader and tag both use the key to encrypt a 32-bit nonce challenge. A correct response proves both sides know the key."
- §105.6 The driver only does REQA + ANTICOLL — the chapter promises authentication and block read in §105.9 lab 3, but the driver skeleton stops at ANTICOLL. Either show the SELECT-then-AUTH commands here, or be explicit that the lab requires the reader to add SELECT + Authent + Read (and cross-reference an example repo with the full code).
- §105.7 "Crypto1 is fundamentally broken" — name the attacks (Nack reuse, Darkside attack, sector-key recovery via mfoc/mfcuk) so the reader can defend the choice of DESFire to a stakeholder. Two sentences max.
- §105.10 Pitfall "Tag already in HALT state" — say *why* this happens (the previous read sent HALT) and add the practical fix: "Use WUPA (0x52) instead of REQA after a HALT or in a multi-reader environment; WUPA wakes HALTed tags too."

---

## Ch106 — Fingerprint sensors

### AI wording / sledgehammer / buzzwords
- > "**standalone fingerprint modules** that do the imaging + matching internally and expose a UART command protocol."
  - Fine.
- > "Fingerprint is the dominant biometric for low-friction access control (vs face: privacy issues, harder to enroll; vs iris: $$$)."
  - "$$$" is slang. Rewrite: "Fingerprint is the dominant biometric for low-friction access control. Face recognition has privacy and enrolment problems; iris is expensive."
- > "**modules are stateful — they remember which template ID is enrolled in which slot, and protocol commands operate on that state**. Enrollment is a 3-step dance: …"
  - "3-step dance" again (also Ch98 §98.3, Ch99 §99.4). Pick one chapter to use this phrase. Here, rewrite: "Enrollment is a three-step sequence:"
- > "Perfect for: smart-lock products, time-and-attendance kiosks, equipment-checkout terminals, secure-area entry."
  - "Perfect for" + bullet-as-prose. Rewrite: "Common applications: smart locks, time-and-attendance kiosks, equipment-checkout terminals, secure-area entry."
- > "trips most integrations."
  - "Trips" idiom. Rewrite: "is where most integrations fail."
- > "The double-capture is for robustness — fingerprints don't sample identically each time; the union improves matching tolerance."
  - Em-dash + semicolon. Rewrite: "Double-capture improves robustness. Fingerprints do not sample identically each time, so the union of two captures gives better matching tolerance."
- > "That's the entire reader: ~150 lines for the core, ~50 for SPI/GPIO setup."
  - "That's the entire" cliché. Rewrite: "The whole reader fits in about 200 lines (150 core, 50 SPI/GPIO setup)."
- > "It's the 'premium feel' choice."
  - "Premium feel" is marketing. Rewrite: "Choose the R503 when the product needs a polished user experience."

### ESL readability
- > "vs face: privacy issues, harder to enroll; vs iris: $$$"
  - The "vs" / colon / semicolon syntax is hard for ESL. See rewrite above.
- > "(or i.MX6ULL in suspend) as wake controller."
  - Parenthetical alternative. Rewrite: "An STM32L0 acts as the wake controller (the i.MX6ULL can be used in suspend, but its standby current is higher)."
- > "Hostile re-enroll detection."
  - "Hostile re-enroll" is jargon. Rewrite: "Detect malicious re-enrolment."
- > "Plus the kernel **`libfprint`** path for USB fingerprint scanners (laptop-style)."
  - Sentence fragment in the What blurb. Rewrite: "This chapter also covers the libfprint path for USB fingerprint scanners — the laptop-style readers."

### Needs more depth
- §106.3 The packet framing protocol description omits a *crucial* point: the checksum is over Packet ID, Length, and Data — **not** the header or the address. The example values implicitly use this rule but the prose says "sum of bytes from Packet ID to last data byte" — which is correct, but ambiguous because the "last data byte" includes the command code. Add one explicit example: "For GetImg (cmd=0x01, no payload): checksum = 0x01 + 0x00 + 0x03 + 0x01 = 0x05. Stored as 0x00 0x05."
- §106.5 Score 0..2000 with threshold 50 is stated but the FAR/FRR curve is not described. One sentence: "Above 50 = match. Raising to 100 cuts false accepts to <0.0001 % but rejects ~5 % of legitimate fingers. Tune for your application's risk profile."
- §106.5 "1:N search" is shown but the chapter does not explain that the chip iterates internally — *the host does not send each candidate*. One sentence: "Search runs entirely on the module's DSP. The host issues one Search command; the module scans all stored templates and returns the best match (or no-match) in about 1 second."
- §106.6 The 9-byte header structure is in the source as a magic literal `{0xEF, 0x01, 0xFF, ..., (n+2) & 0xFF}`. Add a one-line comment in the listing labelling each byte (the prose at §106.3 explains it, but the reader will copy this file and want it self-documenting).
- §106.7 PAM module skeleton — `pam_get_user` and `is_user_authorized` are skeletons. Either show the per-user authorisation file format (e.g., `/etc/r503/users.allow` with lines `alice 1` for slot 1) or note where the example repo has the full code.
- §106.9 Lab 9 "Hostile re-enroll detection" — the prevention is to require admin re-confirmation, but the chapter does not say *how* the firmware should know an admin is present (a second admin fingerprint? a hardware key? a physical lock-out switch?). Add one sentence: "Tie admin re-confirmation to a known admin fingerprint slot (e.g., slot 0) — re-enrolment requires a successful admin match within the last 60 seconds."
- §106.10 "Privacy / GDPR" — biometric data handling deserves more than one bullet. Add: "Templates are not raw images, but they are still biometric data under GDPR / CCPA. Store encrypted at rest (use the kernel's `keyctl` or fscrypt). Never transmit templates over an unencrypted link. Provide a documented deletion path."

---

## Ch107 — GPS / GNSS + PPS

### AI wording / sledgehammer / buzzwords
- > "We compare … turning a $5 receiver into a **stratum-1 time server**."
  - "Turning a $X receiver into a stratum-1 server" is a marketing line. Fine in the blurb; keep.
- > "**NMEA gives you the wall-clock seconds but is laggy and jittery (~50–500 ms after the second); PPS is the actual nanosecond-accurate edge**."
  - "Laggy" is informal. Rewrite: "NMEA reports the wall-clock second, but it arrives 50–500 ms after the actual second. PPS is the nanosecond-accurate edge."
- > "Understanding the PPS plumbing — pin → kernel `pps_gpio` driver → /dev/pps0 → chrony's refclock — is what separates 'GPS time sync' from 'real GPS time sync.'"
  - 30 words, four em-dash steps, quoted-slang close. Rewrite: "The PPS path is the key: GPS pin → kernel `pps_gpio` driver → `/dev/pps0` → chrony refclock. Get this right and you have sub-microsecond GPS time. Skip the PPS and you have NMEA-only ±100 ms."
- > "The killer message: `UBX-NAV-PVT`"
  - "Killer message" again. Rewrite: "The single most useful message: `UBX-NAV-PVT`."
- > "You just built a stratum-1 NTP server with $20 of parts."
  - Marketing close. Rewrite: "Total parts cost is about $20. The result is a stratum-1 NTP server."
- > "The `u-center` Windows tool (or `ubxtool` in Linux's `gpsd` package) is invaluable for crafting these."
  - "Invaluable" is marketing. Rewrite: "Use `u-center` on Windows or `ubxtool` from `gpsd-clients` to build these CFG messages."
- > "The technique generalizes — *any* time-domain measurement on Linux … gets much easier with a real PPS time source."
  - "Generalizes" + italic "any" + closing flourish. Rewrite: "The same PPS technique works for any time-domain measurement on Linux: synchronised audio between boards, distributed instruments, IP-connected oscilloscopes."
- > "30 seconds of Python, ~$15 of hardware, you have your inverter on Home Assistant / Grafana."
  - Time-and-money-then-result tic. Rewrite: "About 30 lines of Python and $15 of hardware put the inverter on Home Assistant or Grafana." *(Note: this quote is actually from Ch108 §108.7 but the same form recurs in Ch107 §107.6 — flag the pattern across chapters.)*

### ESL readability
- > "GNSS time vs UTC leap seconds. GPS time is leap-second-free; UTC isn't."
  - "Leap-second-free" / "isn't" rapid contractions. Rewrite: "GPS time vs UTC leap seconds. GPS time has no leap seconds; UTC does."
- > "PPS-disciplined (kernel timestamps the GPIO edge with hardware-clock precision; chrony combines the slow-but-labelled NMEA with the fast-but-unlabelled PPS edge) gets you to ±100 ns."
  - 32 words, one nested parenthetical, two compound modifiers. Rewrite: "With PPS, the kernel timestamps each GPIO edge using the hardware clock. Chrony combines two streams: NMEA, which is slow but tells you *which* second this is; PPS, which is fast but does not name the second. Together they reach ±100 ns."
- > "The receiver synchronizes its 1 kHz timepulse generator to its GNSS-derived clock; jitter is ~20–50 ns."
  - "1 kHz timepulse generator" — but PPS is 1 Hz, not 1 kHz. Is this a typo (the chip's *internal* timepulse can be configured up to 25 MHz; PPS by default is 1 Hz)? Verify and fix.

### Needs more depth
- §107.4 The PPS path from GPIO IRQ to `/dev/pps0` is described well but the **kernel timestamping mechanism** (`pps_event` → `pps_get_ts`) is hidden. One sentence: "On each GPIO edge, the `pps_gpio` IRQ handler calls `pps_event(pps, &timestamp, ...)`. The PPS core stores the timestamp in a ring buffer keyed by sequence number. Chrony reads it via `PPS_FETCH` ioctl on `/dev/pps0`."
- §107.4 The phrase "captured with `getnstimeofday()` precision — typically sub-microsecond on a Cortex-A7" is misleading. `getnstimeofday` is deprecated; modern kernels use `ktime_get_real_ts64`. Also the *latency* (not the precision of the clock read) is what matters — IRQ-to-handler latency on a non-RT Linux is the bottleneck. Rewrite: "The actual precision is limited by IRQ latency: ~1–10 µs on a non-RT Linux Cortex-A7. PREEMPT_RT brings it under 1 µs."
- §107.6 Chrony refclock — explain *why* PPS needs to be `lock`-ed to a slow source. The `lock GPS prefer trust` clause is given but not derived. One sentence: "PPS edges arrive every second but carry no second-number. Chrony needs a slow 'labelled' source (SHM from gpsd) to assign integer seconds to the PPS edges. `lock GPS` tells chrony to use GPS for labelling and PPS for fine timing."
- §107.7 The Fletcher checksum is computed inline but never *named* — the reader who has only seen CRC16 will wonder what algorithm this is. One sentence: "UBX uses the Fletcher-8 checksum (two byte-wide accumulators, ck_a and ck_b). It is weaker than CRC16 but cheap to compute on small MCUs."
- §107.9 Pitfall "GNSS time vs UTC leap seconds" — the user is told to use `LeapSeconds` but the standard place to look is named differently in each vendor. For u-blox: `UBX-NAV-TIMEUTC` has the `valid` bits including `leapSValid`. One concrete sentence about *where* to find the right field would help.

---

## Ch108 — RS-485 + Modbus RTU

### AI wording / sledgehammer / buzzwords
- > "RS-485 is unglamorous but irreplaceable; learning it opens an enormous market"
  - "Unglamorous but irreplaceable" + "enormous market" = marketing. Rewrite: "RS-485 is everywhere in industrial systems. Knowing it gives you access to the industrial IoT market that pure-WiFi devices cannot reach."
- > "**RS-485 is half-duplex differential signaling on a 2-wire bus; you must control the line driver direction (TX or RX) at sub-bit-time precision, and Modbus framing depends on inter-character timeouts that vary with baud rate**."
  - 45 words, two clauses bridged by "and". Break: "RS-485 is half-duplex differential signalling on a two-wire bus. You must switch the driver between TX and RX with sub-bit-time precision. On top of that, Modbus RTU detects frames by inter-character timeouts that scale with baud rate."
- > "Termination (120 Ω at each bus end), biasing (fail-safe to known idle state), and ground reference (a multi-meter check across grounds is mandatory before connecting devices powered from different sources) are the three things that break a working bench setup when you deploy it."
  - 50-word sentence with three nested parentheticals. Break: "Three things break a bench setup when you deploy it on a real factory floor. Termination — 120 Ω at each end of the bus. Biasing — fail-safe pull-ups so the idle line is a known logic level. Ground reference — measure the voltage between grounds before connecting devices powered from different supplies."
- > "MAX13487 — production, especially on Linux where sub-bit-time DE control is hard. Auto-direction = 'wire it up and forget.'"
  - "Wire it up and forget" is slang. Rewrite: "MAX13487 — recommended for production. Auto-direction removes the timing-critical DE/RE control."
- > "Auto-direction's main benefit."
  - Fragment. Rewrite: "This is auto-direction's main benefit."
- > "30 seconds of Python, ~$15 of hardware, you have your inverter on Home Assistant / Grafana."
  - Marketing tic also flagged in Ch107 above. Rewrite: "About 30 lines of Python and $15 of hardware put the inverter on Home Assistant or Grafana."

### ESL readability
- > "Auto-direction transceivers (MAX13487) solve this in hardware."
  - Fine.
- > "Daisy-chain only (no star, no T-stubs > 30 cm). Termination at both physical ends."
  - "T-stubs" is jargon. Rewrite: "Daisy-chain topology only. No star or branch wiring. Spurs from the main bus must be shorter than 30 cm. Terminate both physical ends."
- > "At 9600 baud, 1 char = 11 bits / 9600 = 1.146 ms; 3.5 char = 4 ms idle to detect end-of-frame."
  - Compressed math with two semicolons. Rewrite: "At 9600 baud, one 11-bit character takes 1.146 ms. The 3.5-character inter-frame gap is therefore about 4 ms — that is the idle time after which a receiver declares end-of-frame."
- > "Holding vs input registers. Function 0x03 = holding (R/W); 0x04 = input (R-only)."
  - Semicolon glue. Fine in a pitfall bullet; keep.
- > "Now your i.MX6ULL is slave 5 on the bus; any master can poll it for sensor data."
  - "Slave" wording — keep terminology consistent with the section header. The Modbus spec uses "server" in newer versions; the rest of the chapter uses "slave." That is fine if consistent.

### Needs more depth
- §108.1 Fail-safe biasing — the diagram shows "+5V via 680 Ω to A; GND via 680 Ω to B (bias)" but does not derive *why* this is required. One sentence: "When no driver is active, the bus floats and the receiver's output is undefined. A weak pull-up on A and pull-down on B forces a defined idle ('1') so frame-start detection works. Some modern transceivers (SP485E, ISL81387) integrate this internally."
- §108.4 Kernel RS-485 mode — the chapter says "Some UARTs (i.MX has integrated '9-bit mode' with hardware DE) do this directly without GPIO toggling — check your reference manual for SER_RS485_AUTO." This is the **single most useful** trick for production. Promote it to its own paragraph: "On i.MX6ULL, the UART's `UCR3.DSR` and `UTS.RXFULL` bits combined with the *RTS-as-DE* function (selected in the IOMUX) make hardware DE control possible. The driver toggles DE inside the UART state machine itself — no IRQ-context GPIO writes, no jitter. Enable via the DT properties shown; verify with a scope on the DE line during TX."
- §108.5 Modbus inter-character timeout — at high baud (115200) the 3.5-char gap is 280 µs. Most Linux UART drivers buffer for at least 10 ms before delivering. So Modbus RTU at 115200 needs *hardware*-assisted byte timestamping or a low-latency reads. Add: "At 115200 baud, the 3.5-char inter-frame gap shrinks to ~280 µs. This is below the kernel's default UART poll/deliver interval (~10 ms). `libmodbus` uses select() and timing heuristics that work to about 38400 baud; above that, you need either kernel-side RS-485 framing support or a hardware timestamper."
- §108.5 CRC16 polynomial 0xA001 — name it: "this is the reversed polynomial of the standard CRC-16-IBM (0x8005). Initial value 0xFFFF, no final XOR. Tables and code are everywhere; do not hand-roll."
- §108.7 The float-encoding pitfall (§108.10) deserves a worked example in §108.7. One sentence: "Inverters often pack a 32-bit float as `(reg[0] << 16) | reg[1]` *or* `(reg[1] << 16) | reg[0]` *or* `reg[0]` and `reg[1]` byte-swapped. Read a known value (the grid voltage, ~230 V) and check which interpretation gives a plausible number."
- §108.9 Lab 4 multi-slave bus — useful to add a sentence about how to detect collisions: "If two devices share an address, one will respond first and the other's response will collide on the wire. The master sees a CRC error or a malformed frame. Use `modpoll -1` to query each slave individually during bring-up to find duplicates."

---

## Ch109 — LIN bus

### AI wording / sledgehammer / buzzwords
- > "LIN is also creeping into industrial actuator buses (HVAC valves, building blinds) for the same reason: $0.40 per node + 1-wire bus is unbeatable for 'dumb' peripherals."
  - "Creeping into" + "unbeatable" + "dumb peripherals" — all informal. Rewrite: "LIN is also spreading into industrial actuator buses (HVAC valves, building blinds). At about $0.40 per node and one wire, it is the cheapest option for simple peripherals."
- > "Linux's lack of native support means you write the framing yourself, which is a great UART exercise."
  - "A great UART exercise" reads like a tutorial blurb. Rewrite: "Linux has no native LIN subsystem; you write the framing yourself. This is also a useful UART exercise."
- > "**LIN is UART + a 'break' pulse + an 8-bit 'sync' byte + a 6-bit 'PID' + 1–8 data bytes + 8-bit checksum, all run by a single master broadcasting schedules; slaves never speak unprompted**."
  - 40 words, six pluses, one semicolon. Rewrite: "A LIN frame is: a UART start, a 'break' pulse, an 0x55 sync byte, a 6-bit Protected Identifier (PID) byte, one to eight data bytes, and a checksum byte. A single master schedules every frame. Slaves never transmit on their own."
- > "The protocol is dirt simple; the trap is getting the timing right on a non-deterministic Linux UART."
  - "Dirt simple" + semicolon. Rewrite: "The protocol is simple. The trap is getting the timing right on a non-deterministic Linux UART."
- > "Robust but ugly."
  - "Ugly" is informal. Rewrite: "Reliable but messy."
- > "That's a working LIN 2.x master in ~80 lines."
  - "That's a working X" close. Fine once per chapter. Pair with the same phrase in §106.6 ("the entire reader: ~150 lines") — vary across chapters.
- > "You've now controlled an automotive comfort actuator from Linux."
  - "You've now …" celebratory close. Rewrite: "At this point you have driven an automotive comfort actuator from Linux."

### ESL readability
- > "The LIN bus is **a single wire pulled up to 12 V (or 7–18 V in practice)**, with each node yanking it low to transmit."
  - "Yanking" is slang. Rewrite: "The LIN bus is a single wire pulled up to 12 V (typically 7–18 V in practice). Each node pulls the wire low to transmit."
- > "Detecting the break from user-space is the awkward part on Linux — there's no clean API."
  - "Awkward / clean API" idiom. Rewrite: "Detecting the break from user-space is hard on Linux; there is no dedicated API."
- > "Both work, neither is elegant. A proper LIN slave belongs on an MCU."
  - "Neither is elegant" / "proper" — opinion. Rewrite: "Both methods work but neither is clean. For real products, run the LIN slave on a dedicated MCU."
- > "The blower controller's slave ID for 'set fan speed' is typically `0x20` (vendor-specific; reverse-engineering via LIN-bus traffic dumps from forums)."
  - 25-word parenthetical run-on. Rewrite: "The blower controller's slave ID for 'set fan speed' is typically `0x20`. The exact ID is vendor-specific; you find it by capturing bus traffic and matching commands to behaviour."

### Needs more depth
- §109.4 The four "tricks" for generating the break are listed but the chapter does not say *which one the example code uses*. The C code in §109.5 picks trick #4 (TIOCSBRK/TIOCCBRK). State that explicitly at the top of §109.5: "The sample code uses trick #4 (i.MX-specific TIOCSBRK). On other SoCs, fall back to trick #2 (baud-rate switch)."
- §109.5 The `cksum_enhanced` function returns the inverted sum, but the chapter says "classic checksum = sum of data only; enhanced = sum of PID + data" without mentioning the **inversion (NOT)** step. Add: "Both classic and enhanced checksums invert the final byte (`~sum`). Forget the inversion and every frame is rejected."
- §109.6 Detecting the break — `TIOCMIWAIT(TIOCM_BRK)` and `TIOCGICOUNT` are the two methods given. Add one sentence about which is more reliable: "`TIOCMIWAIT(TIOCM_BRK)` blocks until the next break event, which is the cleanest option on i.MX UARTs that report it. `TIOCGICOUNT` polling is the fallback if your driver does not raise TIOCM_BRK."
- §109.2 PID parity formulas — list them but also include a worked example so the reader can sanity-check: "For ID=0x10 (binary 010000), P0 = 0^0^0^0 = 0 and P1 = ~(0^0^0^1) = 0. Final PID = 0b01010000 = 0x50." (The lab in §109.9 step 2 already asserts this, so the example is consistent.)
- §109.7 Sleep/wake — the wake pulse is described as "any node pulls the bus low for ≥250 µs." But the *master* also has to power the bus and re-start the schedule. Add: "After a wake pulse, the master must wait at least 50 ms (in LIN 2.x) before issuing the next break — slaves use that time to leave low-power mode and prepare their UARTs."
- §109.10 Pitfall "Bus-off via short" — "Recover by raising EN to put the transceiver in low-power mode" is unclear. Rewrite the recovery: "Recovery: pull EN low for at least 10 µs (transceiver enters sleep), then raise EN. If the short is still present, the bus stays dominant; if the short cleared, the bus returns to idle (recessive)."

---

## Ch110 — CAN deep dive

### AI wording / sledgehammer / buzzwords
- > "Mainline Linux's SocketCAN is the best CAN stack on any OS"
  - Marketing claim. Rewrite: "Mainline Linux's SocketCAN is the most complete CAN stack of any general-purpose OS."
- > "Build deep familiarity here and you become the team's go-to for vehicle/industrial integration."
  - "Go-to / build deep familiarity" — career-coaching tone. Rewrite: "After this chapter you can take on most vehicle and industrial CAN integration work."
- > "**classic CAN is bit-stuffed differential bus with priority arbitration via CSMA/CR; CAN-FD adds a second bit rate during the data phase to squeeze 64 bytes through a 1 Mbps bus in ~120 µs**."
  - 40-word sledgehammer + "squeeze" verb. Break: "Classic CAN is a bit-stuffed differential bus with priority arbitration via CSMA/CR. CAN-FD adds a second, faster bit rate during the data phase. The result: 64 bytes through a 1 Mbps arbitration bus in about 120 µs."
- > "Get the bit-timing right (sample point, SJW, prop+phase segments) or you'll see 'CAN bus errors' that look like wiring problems but are firmware."
  - "But are firmware" awkward phrase. Rewrite: "Get the bit timing right (sample point, SJW, prop and phase segments). Otherwise you will see CAN bus errors that look like a wiring fault but are caused by configuration."
- > "Tries to falter near 1 Mbps under load."
  - "Tries to falter" is awkward English. Rewrite: "Struggles near 1 Mbps under load."
- > "Surprising when first writing code."
  - Fragment. Rewrite: "This surprises people writing CAN code for the first time."
- > "You can build a complete car-diagnostics dashboard in 200 lines of C + a fast Linux box."
  - "Fast Linux box" + plus-sign-as-prose. Rewrite: "About 200 lines of C and a Linux board are enough to build a complete OBD-II dashboard."

### ESL readability
- > "**Dominant** = 0 (driven), **recessive** = 1 (idle). A dominant always overwrites a recessive → low-ID wins."
  - Arrow-as-prose. Rewrite: "Dominant is logical 0 (actively driven). Recessive is logical 1 (idle). Dominant always overwrites recessive, so the lowest-numbered ID wins arbitration."
- > "ID 0 is highest priority. A node that always sends ID 0 starves everyone else."
  - Fine; the consequence is clear.
- > "Use kernel-side RS-485 framing support or a hardware timestamper."
  - This is from §108 — but the same pattern recurs. Keep as a flag for the cross-cutting list.
- > "Some IDs are reserved (0x3C, 0x3D = master/slave request frames; 0x3E, 0x3F = reserved)."
  - Semicolon glue. Fine.
- > "ID 0 is highest priority. A node that always sends ID 0 starves everyone else. Reserve low IDs for hard-real-time critical messages only."
  - "Starves" is OK but consider "blocks everyone else from transmitting" for clarity.

### Needs more depth
- §110.3 Bit timing example — the math is shown but the **propagation segment derivation** is left implicit. Add one sentence: "The propagation segment must cover the round-trip delay between any two nodes on the bus: bus length × 2 × 5 ns/m + transceiver delays (~150 ns each end) + sampling latency. For a 50 m bus, this is ~700 ns — at 16 TQ × 125 ns/TQ, that is 5.6 TQ, so a prop segment of 6+ TQ is required."
- §110.3 SJW (Synchronisation Jump Width) is mentioned only in passing in the Focus blurb and never explained. Add a sentence in §110.3: "SJW is how many TQ the receiver may shift the sample point in either direction to re-synchronise on each edge. Typical SJW = 1 (minimum) to 4 (maximum). Set it equal to the smaller of Phase1/Phase2 for best noise tolerance."
- §110.5 Filters — the example uses `can_id` + `can_mask` but the rule (`(received_id & mask) == (can_id & mask)`) is not stated. Add: "Each filter matches when `(received_id & can_mask) == (can_id & can_mask)`. You can chain up to 64 filters per socket; the kernel ORs them."
- §110.6 ISO-TP — the example sends a UDS request but does not show how the **kernel handles flow control** (FC frames). One sentence: "When the response is multi-frame, the kernel automatically sends FC frames (with BS and STmin from setsockopt or defaults). User-space only sees the reassembled 19-byte VIN."
- §110.6 The chapter says "Without ISO-TP, you'd be writing the segmentation state machine yourself" but does not name the spec. Add: "The segmentation rules are in ISO 15765-2:2016. The kernel `can-isotp` module implements the full state machine."
- §110.8 BCM — `TX_SETUP` is just one BCM opcode; the others (RX_SETUP for receive filters with content change detection, TX_DELETE, etc.) are not mentioned. One sentence: "BCM also has `RX_SETUP` for content-change notification (only wake user-space when a frame's data actually changes), `TX_DELETE`/`RX_DELETE`, and `*_READ`. See `Documentation/networking/can.rst`."
- §110.12 Pitfall "ID 0 is highest priority" — add the practical guidance: "On most automotive buses, IDs below 0x100 are reserved for safety-critical messages (powertrain, ABS). Use IDs in the 0x500–0x7FF range for application traffic."

---

## Ch111 — Quadrature encoders & rotary

### AI wording / sledgehammer / buzzwords
- > "**quadrature decoding is 'two channels 90° out of phase; the leading channel tells direction'**."
  - Sledgehammer + semicolon. Rewrite: "Quadrature decoding works on two channels that are 90° out of phase. The leading channel tells you the direction of rotation."
- > "Mechanical encoders bounce horribly (5+ ms of noise per click) and need debouncing; optical encoders are clean but expensive; magnetic encoders are the middle ground."
  - 25-word triplet with two semicolons. Rewrite: "Mechanical encoders bounce badly — 5 ms or more of noise per click — and need debouncing. Optical encoders are clean but expensive. Magnetic encoders are the middle ground."
- > "For position control, absolute beats incremental every time"
  - "Beats every time" is informal. Rewrite: "For position control, absolute encoders are better in nearly every case."
- > "100 Hz loop is plenty for a brushed motor (much slower mechanical dynamics)."
  - "Is plenty" informal. Rewrite: "A 100 Hz control loop is adequate for a brushed motor. Mechanical dynamics are much slower than that."
- > "Both channels' rising + falling edges call this; it handles all 12 valid transitions and silently zeros the 4 invalid (missed-edge) transitions."
  - Semicolon + "silently zeros" awkward. Rewrite: "Both channels call this on rising and falling edges. The 12 valid transitions produce ±1; the 4 invalid transitions (where both bits changed at once = missed edge) produce 0."
- > "Software bug? Look at the QDEC_TABLE."
  - Fragment-as-question. Rewrite: "If counts are wrong, check the QDEC_TABLE."

### ESL readability
- > "Software-decode in C:" / "Software qdec in user-space (libgpiod)"
  - "Software-decode" / "qdec" mixed terms within one chapter. Use one term ("software decode") consistently.
- > "Status in mainline Linux:"
  - Section heading style; OK.
- > "Software qdec scheduled but missed under load."
  - Pitfall headline. Rewrite: "User-space decode misses edges under CPU load."
- > "AS5048A magnet alignment. The magnet must be on the shaft axis (radially polarized, diametric) within ±0.5 mm; misalignment → non-linear angle errors of several degrees."
  - "Radially polarized, diametric" — these two terms are not the same (radial vs diametric magnetisation). Pick one and define it. Likely should be "diametrically magnetised."

### Needs more depth
- §111.2 The four-row QDEC table maps `prev:curr → ±1`. The table has 8 valid transitions but the prose says "all 12 valid transitions." Re-count: 4 forward + 4 backward = 8 valid, 4 invalid (00↔11, 01↔10), 4 same-state = 16 total. Either say "8 valid transitions" or list the missing four.
- §111.3 The user-space decode latency claim "fails for a 10,000 ppr encoder spinning at 60 RPM (= 40 kHz edge rate)" is short. Add the derivation: "10,000 PPR × 4 edges/cycle × (60 RPM / 60 s) = 40,000 edges/s. At 50 µs latency per edge, the CPU is fully consumed by encoder IRQs alone."
- §111.4 The kernel `rotary_encoder` driver does **not** do 4× decoding; it reports one event per detent. Note this: "This driver is designed for human-operated knobs (detented mechanical encoders), not high-resolution servo feedback. It reports one event per detent step, not per quadrature edge."
- §111.5 The i.MX6ULL ENC peripheral — the chapter says mainline coverage "varies by kernel version." Be more concrete: "As of 6.6, mainline has no i.MX6ULL ENC driver. The NXP downstream BSP (`linux-imx`) ships one in `drivers/iio/counter/`. Check `make menuconfig → Counter Support → Freescale eQEP support` in your tree."
- §111.6 LS7366R sequence — the `0x88` and `0x60` opcodes are given but the *MDR0/MDR1 configuration* (which is what enables filters and 4× decode) is not shown. Add the typical init sequence: `WRITE_MDR0 (0x88, 0x03)` for 4× quadrature + free-running counter; `WRITE_MDR1 (0x90, 0x00)` for 32-bit mode, no flags.
- §111.8 The velocity loop uses fixed `Ki = 0.1` without scaling for sample rate. Add one sentence: "At a 100 Hz loop, integrator accumulates `err * 0.01` per cycle. Scale Ki by your loop period if you change the rate; otherwise the response changes shape."

---

## Ch112 — Stepper & DC motor drivers

### AI wording / sledgehammer / buzzwords
- > "Get these wrong and the result ranges from 'motor whines' to 'MOSFET explodes.'"
  - Cute but informal close. Rewrite: "Get these wrong and the result ranges from an audible whine to a destroyed MOSFET."
- > "**steppers need precise step-rate generation (PWM); DC motors need PWM + H-bridge + current feedback; BLDC needs commutation (rotor-position-aware switching of 3 half-bridges)**."
  - 30-word triplet with semicolons. Rewrite: "Steppers need precise step-rate generation, usually from a PWM. DC motors need a PWM and an H-bridge, with current feedback for control. BLDC motors need commutation — switching three half-bridges in sync with rotor position."
- > "Each must be timed within ~50 µs or torque ripple shows."
  - "Torque ripple shows" awkward. Rewrite: "Each commutation must hit within ~50 µs of the right rotor angle, or torque ripple becomes audible."
- > "Linux's interrupt jitter > 100 µs."
  - Equation-as-prose. Rewrite: "Linux interrupt jitter is typically > 100 µs."
- > "TMC2209 (Trinamic) is the modern silent stepper driver."
  - Marketing. Rewrite: "TMC2209 (Trinamic) is the current go-to silent stepper driver." *(Note: "go-to" is informal too — "common choice" is cleaner.)*
- > "Once configured, the motor is whisper-quiet — a 3D printer goes from 'rocket launch' to 'fridge hum.'"
  - Marketing simile. Rewrite: "Once configured, the motor is near-silent. A 3D printer with TMC2209 drivers is roughly the volume of a fridge fan."
- > "Klipper runs the motion planner on Linux and offloads the step-generation to an STM32 over USB serial; this is the canonical 'Linux + MCU' split for serious CNC."
  - "Canonical / serious CNC" is fan-prose. Rewrite: "Klipper runs the motion planner on Linux and offloads step generation to an STM32 over USB serial. This split is the dominant pattern for high-end CNC and 3D printing."

### ESL readability
- > "**Critical**: every driver has a 'current limit' you set with a trimpot (sense resistor + reference voltage)."
  - "**Critical**:" opener is overused (this part has 6+ bold "Critical:" markers across chapters). Vary: "Important: …" or just lead with the sentence.
- > "Don't rely on coil-color conventions — they're not standard."
  - Fine.
- > "Powering driver Vmot before logic Vcc."
  - Fragment in a pitfall list. Fine.
- > "For absolute-torque or smooth-low-RPM BLDC, you need FOC (Field-Oriented Control) which most engineers offload to a dedicated MCU (e.g., SimpleFOC on STM32) because Linux's jitter exceeds the 10 kHz current-loop budget."
  - 40 words, three parentheticals, one because-clause. Break: "For absolute torque control or smooth low-RPM behaviour, you need FOC (Field-Oriented Control). The current loop runs at 10 kHz or higher, which exceeds Linux's scheduling jitter. Most engineers offload FOC to a dedicated MCU — SimpleFOC on STM32 is the open-source standard."

### Needs more depth
- §112.2 Current limit setting — the formula "Vref = Imax × 5 × 0.1" is given without naming variables. Expand: "Vref = Imax × R_sense × 8 (for DRV8825) or × 5 (for A4988). For a 0.1 Ω sense resistor and 0.8 A target: 0.8 × 5 × 0.1 = 0.4 V. Check the driver datasheet for the exact constant."
- §112.4 TMC2209 UART CRC — "TMC's specific CRC8" — name the polynomial. The CRC8 used is `x^8 + x^2 + x + 1` (poly 0x07), MSB-first, init 0. Without that, the example code is unimplementable.
- §112.4 The `tmc_write` struct uses `uint8_t sync = 0x05` — this is a default member initialiser, which is a C++ feature, not C. In C you must initialise via `= { .sync = 0x05, ... }`. Fix the code or note it is pseudocode.
- §112.5 H-bridge shoot-through — the chapter mentions dead-time but does not give a typical value. Add: "Dead-time between high-side off and low-side on must exceed the FET turn-off time + 20 % margin. For typical TO-220 N-FETs, ~500 ns is safe; for fast logic-level FETs, 100 ns."
- §112.6 BLDC commutation table — the COMMUTATE_TBL has eight entries indexed by 3-bit Hall state. The mapping in the comment ("hall: 000 001 010 011 100 101 110 111" → "gate: inv 4 2 3 6 5 1 inv") is non-obvious. Add one sentence: "The mapping is rotor-angle-to-coil-pair. Halls 000 and 111 are invalid (all sensors off or on = sensor fault). The other six map to the six commutation states; the exact permutation depends on Hall sensor mounting and motor wind direction — swap any two entries if the motor runs backward."
- §112.6 The 2,333 commutations/s number assumes 14 magnetic poles (7 pole pairs). State the formula: "Commutations/s = (electrical RPM) / 60 × 6 steps/cycle = (mechanical RPM × pole pairs) / 60 × 6. For 10,000 RPM × 7 pole pairs = 70,000 electrical RPM, six steps per electrical revolution, so 7,000 commutations/s." (The text's 2,333 number appears off by 3× — verify with the formula.)
- §112.8 Pitfall "PWM frequency in motor's audible range" — the *cause* of the whine is left implicit. One sentence: "The motor's coils act as a speaker driven by the PWM ripple. Audible PWM (1–10 kHz) makes the motor whine in the same frequency. Move above 20 kHz to push the whine into ultrasonic, or use stealthChop which spreads the spectrum."

---

## Ch113 — WS2812 / SK6812 / APA102 addressable LEDs

### AI wording / sledgehammer / buzzwords
- > "**WS2812/SK6812 encode bits as pulse widths on a single wire: a '0' bit = 350 ns high + 800 ns low; a '1' bit = 800 ns high + 450 ns low; reset = 50+ µs low; one byte per channel × 3/4 channels × N LEDs all back-to-back**."
  - 50-word sledgehammer with four semicolons. Break: "WS2812 and SK6812 encode bits as pulse widths on a single wire. A '0' bit is 350 ns high followed by 800 ns low. A '1' bit is 800 ns high followed by 450 ns low. A reset is 50 µs or more of low. Each LED takes 24 bits (3 channels × 8) — or 32 bits for RGBW — and the whole strip is one back-to-back stream."
- > "Bit-banging from Linux user-space is hopeless (microsecond IRQ jitter > nanosecond timing budget)."
  - "Hopeless" judgmental. Rewrite: "Bit-banging from Linux user-space does not work. The IRQ jitter is microseconds; the WS2812 timing budget is hundreds of nanoseconds."
- > "**Don't ship this** — it's a demo trick, not a production approach. Use SPI + DMA."
  - "Demo trick" informal. Rewrite: "Do not ship this approach. It is useful as a demo only. Production designs should use SPI + DMA."
- > "The SPI + DMA trick — gospel for embedded Linux"
  - "Gospel" is religious slang. Rewrite: "The SPI + DMA pattern — the standard approach in embedded Linux."
- > "The timing-painless alternative"
  - "Painless" marketing. Rewrite: "APA102 — no timing constraints"
- > "The elephant in the room."
  - Cliché section title. Rewrite: "Power budgeting — the most-skipped detail."
- > "Quality varies wildly between batches."
  - "Wildly" informal. Rewrite: "Quality varies substantially between batches."

### ESL readability
- > "Encode each WS2812 bit as 4 SPI bits at 3.2 MHz (312.5 ns per SPI bit):"
  - Fine; keep.
- > "Wire MOSI → strip's DIN. Use a 74AHCT125 buffer to convert 3.3 V MOSI to 5 V logic level (WS2812 expects 0.7 × VDD = 3.5 V 'high' threshold; 3.3 V may or may not work depending on strip batch — buffer always)."
  - 40 words, one parenthetical with semicolon and dash. Break: "Wire MOSI to the strip's DIN. Always add a 74AHCT125 buffer to convert 3.3 V MOSI to 5 V. The WS2812 datasheet specifies VIH = 0.7 × VDD = 3.5 V; 3.3 V is below that. Some strip batches accept it; many do not. Buffer every time."
- > "The 5-bit global brightness is a separate PWM domain at ~700 Hz — useful for low-light, but it flickers in camera footage (frame-rate beating against the 700 Hz)."
  - "Frame-rate beating against" — technical jargon. Rewrite: "APA102's 5-bit global brightness is implemented by a separate PWM at about 700 Hz. It is useful for low-light effects, but on camera the 700 Hz beats against the camera's frame rate and shows flicker."
- > "Each LED at full white = 60 mA."
  - Equation-as-prose. Rewrite: "Each LED at full white draws about 60 mA."

### Needs more depth
- §113.3 The encoding LUT (`bit_lut[4] = { 0x88, 0x8E, 0xE8, 0xEE }`) is shown but the **SPI mode / endianness** required for it to work is not stated. Add: "The encoding assumes SPI mode 0, MSB-first byte order. On i.MX eCSPI, this is the default; on other SPI controllers verify with a scope before debugging mysterious 'wrong colour' bugs."
- §113.3 The trailing-low → free reset note is mentioned but the reader may not realise the SPI driver might *not* hold MOSI low after CS rises. Add a sentence: "Some SPI drivers leave MOSI high after the last bit. If you see the first LED of the *next* frame corrupted, your driver does this — work around it by appending 8 zero bytes to `spi_buf`."
- §113.6 APA102 end frame — the chapter says "32+ bits of ones (or zeros — both work)" but the **real** end-frame length is `N/2` bits where N is the number of LEDs. One sentence: "The end frame must be at least `N/2` bits long (where N is the LED count). The clock pulses pass through each LED's latch chain to commit the data. For 100 LEDs, 50 clock bits — 7 bytes of trailing 0xFF or 0x00 — is enough."
- §113.7 Gamma — the python list comprehension is given but the rounding (`+ 0.5`) and clamp are not explained. One sentence: "The `+ 0.5` rounds to nearest integer (Python's `int()` truncates). For very low values (`(1/255)^2.2 = 0.000007`) the result is 0, which is what you want — black truly black."
- §113.8 Power-injection diagram is missing; the reader is told to inject every 50–100 LEDs but the *wiring topology* is not shown. Add a simple ASCII diagram: PSU → wire to start, then taps at LED 50 and LED 100, all GNDs commoned.
- §113.10 Pitfall "Wrong color order" — list each chip's order in a tiny table for quick lookup, not in prose. "WS2812B = GRB. SK6812 = GRB or GRBW. APA102 = BGR. WS2811 = RGB." (The prose already lists most of this — just consolidate into one bullet.)

---

## Ch114 — Beepers, relays, SSRs

### AI wording / sledgehammer / buzzwords
- > "the **discrete actuators** that don't fit anywhere else but appear in every product"
  - "That don't fit anywhere else" is awkward. Rewrite: "the discrete actuators that fall outside the main subsystems but appear in every product."
- > "every product *does things* — beep on user action, switch a pump, turn on a heater, energize a solenoid valve, ring a bell."
  - Italics + bullet-as-prose. Rewrite: "Real products take physical actions: beep on user input, switch a pump, turn on a heater, drive a solenoid valve, ring a bell."
- > "Each actuator has a different electrical personality"
  - "Electrical personality" is a metaphor that does not translate well. Rewrite: "Each actuator has different electrical requirements"
- > "the engineering details that make the difference between 'the demo works' and 'we shipped this for 5 years and it never fails.'"
  - Long quoted-slang construction. Rewrite: "the engineering details that separate a demo from a five-year shipping product."
- > "**for inductive loads (relays, solenoids, motors) you MUST have a flyback diode; for AC loads you MUST have isolation; for zero-cross AC switching you MUST use a zero-cross SSR or you'll arc, generate harmonics, and burn contacts**"
  - 40-word triplet with three "MUSTs" in caps. Break: "Three non-negotiable rules for the actuators in this chapter. Inductive loads (relays, solenoids, motors) need a flyback diode. AC loads need isolation. Zero-cross AC switching needs a zero-cross SSR; non-zero-cross switching arcs, generates harmonics, and burns contacts."
- > "*Know what you're doing or hire someone who does.*"
  - Italic warning reads as a slogan. Rewrite: "Get a qualified electrician to review your design if you are not one."
- > "40 lines. Drop into systemd. From any phone with Home Assistant: tap 'Living Room Lamp' → MQTT → relay clicks → lamp on."
  - Arrow-chain showcase. Rewrite: "About 40 lines. Install as a systemd unit. Open Home Assistant on a phone, tap 'Living Room Lamp', and the relay clicks the lamp on via MQTT."

### ESL readability
- > "Live AC kills."
  - Two-word sentence. Effective for emphasis but reads abrupt. Keep.
- > "Treating 'off' SSR as 'isolated.'"
  - Quoted slang in a pitfall headline. Rewrite: "Treating an off SSR as electrically isolated."
- > "BJT and SoC are slowly killed by repeated back-EMF spikes."
  - "Slowly killed" personification. Rewrite: "Repeated back-EMF spikes will eventually damage the BJT and SoC."

### Needs more depth
- §114.2 Mechanical relay coil current — 30 mA at 12 V = 360 mW, not 150 mW as in §114.8 pitfall. Verify and unify the numbers across §114.2 and the pitfall list. (The relay's coil power depends on the part; quote a typical Songle SRD-05VDC: 5 V at 71 mA = 355 mW.)
- §114.3 The 10 kΩ pull-down — the chapter explains *why* (GPIO floats during boot) but not the **value choice**. One sentence: "10 kΩ is a compromise: low enough to overcome any leakage and pull the gate firmly to ground, high enough not to interfere with the GPIO drive when active. 1 kΩ to 100 kΩ all work; 10 kΩ is the default."
- §114.4 Zero-cross vs random-fire SSR — the chapter says "for inductive loads use random-fire SSR" but does not explain *why*. One paragraph: "A zero-cross SSR switches at the AC voltage zero-crossing. For resistive loads, this means current also starts at zero (no inrush). But an inductive load lags current by 90°: switching at voltage-zero is switching at current-peak. The arc on turn-off is severe. Random-fire SSRs (also called instant-on) switch whenever commanded — pair them with an external current-zero-cross detector for inductive switching."
- §114.5 GFCI/RCD — one sentence on the trip threshold would help: "Residential RCDs trip at ~30 mA imbalance between live and neutral. This will not stop you from feeling a shock, but it should stop you from being killed."
- §114.7 MQTT relay board — the example uses `paho.mqtt.client` and the older `gpiod` Python API (0.x). Modern Buildroot and Debian ship gpiod 2.x with a different API. Note the version: "This example uses python-gpiod 1.x. For gpiod 2.x (Bookworm and later), the API changed: use `gpiod.request_lines(...)` instead of `chip.get_line(...).request(...)`."
- §114.8 Pitfall "AC neutral switching" — add a one-line check the reader can use: "Use a non-contact voltage tester. Touch it to the load wire when the relay is OFF. If the tester chirps, you switched neutral. Rewire to switch live."
- §114.9 The "Going deeper" links — the chapter cross-references Ch 51A (watchdog) for safety but does not explain *why* a watchdog matters for relay control. One sentence in §114.5: "Pair every relay-driving application with a hardware watchdog (Ch 51A). If the controlling process hangs while a heater relay is closed, the load will run until manually disconnected. A 30-second watchdog with a fail-safe-open relay state prevents fires."

---

## Ch115 — Dual FEC + hosted Ethernet

### AI wording / sledgehammer / buzzwords
- > "**dual-MAC on one SoC means two PHYs, each with its own pin-mux + clock + interrupt; the kernel netdev model already isolates them so they look like two cards. The hard part is the bring-up:**"
  - 40 words, one semicolon, one closing colon. Break: "Dual-MAC on one SoC means two PHYs. Each needs its own pinmux, reference clock, and IRQ. The kernel netdev model already isolates the two MACs — they look like two NICs. The hard part is the bring-up."
- > "For SPI Ethernet: the W5500 is *hardware TCP/IP* (you talk to it at the socket layer over SPI, not as a netdev) which is alien on Linux"
  - "Alien on Linux" idiom. Rewrite: "The W5500 implements TCP/IP in hardware. You talk to it at the socket layer over SPI, not as a netdev. This does not fit the Linux netdev model."
- > "We cover all three patterns."
  - Fine.
- > "PMICs win on every axis"
  - "Win on every axis" is sports metaphor. Rewrite: "PMICs are better than discrete LDOs in every dimension"
- > "**Beautiful introspection — see exactly which consumer holds which rail enabled.**"
  - From Ch116 — flagged below.
- > "DM9051 is fine for a 3rd 'management interface' or a Modbus-TCP island bus. Don't expect it to handle real traffic."
  - "Real traffic" is dismissive. Rewrite: "DM9051 is adequate for a management interface or a low-rate Modbus-TCP island. It is not suitable for primary high-bandwidth traffic."
- > "Done. Your i.MX6ULL is a router."
  - "Done." then declarative. Rewrite: "That is the full router setup."
- > "Awkward on Linux."
  - Fragment. Rewrite: "This makes W5500 awkward to use on Linux."

### ESL readability
- > "**Practical Linux choice**: use W5500's sockets directly from user-space via SPI. Or — pick a different chip."
  - "Or — pick a different chip" is choppy. Rewrite: "The practical Linux approach: use W5500's sockets directly from user-space via SPI, or choose a different chip (DM9051, ENC28J60) that presents as a netdev."
- > "Critical: each PHY has a **strap-pin-set MDIO address** (typically 0, 1, 2, …). FEC1's PHY at address 0; FEC2's PHY at address 1. Both share the MDIO bus (MDC/MDIO can be shared on most designs), and FEC2 reads address-1's registers."
  - 45-word block with parenthetical and semicolon. Break: "Each PHY has an MDIO address set by strap pins (typically 0, 1, 2, …). Put FEC1's PHY at address 0 and FEC2's PHY at address 1. Both PHYs can share the same MDIO bus; the FEC reads the address that matches its `phy-handle` in the DT."
- > "The MDIO node is under FEC1 (one MDIO instance), with both PHYs as children. FEC2 references `ethphy1` via `phy-handle`."
  - Fine.

### Needs more depth
- §115.2 The MDIO bus is described as shared in prose but the DT example only shows it under `&fec1`. The reader should know that **only one FEC owns the MDIO controller**; the other accesses PHYs via `phy-handle` referencing the first FEC's MDIO subtree. State this: "Only one FEC owns the physical MDIO controller. The DT puts both PHY child nodes under that FEC's `mdio { }`. The second FEC's `phy-handle` points across to the PHY in the first FEC's MDIO tree. The kernel reads PHY registers through the owning FEC."
- §115.6 W5500 sockets — the chapter notes "out-of-tree drivers that wrap W5500 sockets as Linux `AF_INET` sockets" but does not link or name them. Add: "See `wiznet/W5500-EVB-Pico` for user-space examples, and the out-of-tree `kernel/drivers/net/w5x00` patches (never accepted upstream)."
- §115.7 DM9051 vs ENC28J60 throughput numbers (8 vs 3 Mbps) — show the math so the reader understands the limit: "DM9051 transfers one packet via two SPI transactions (TX = burst write to TX buffer; RX = burst read). At 20 MHz SPI and 1500-byte packets, raw byte time is 600 µs/packet → max ~13 Mbps. SPI overhead (CS settling, header bytes, IRQ servicing) drops effective throughput to ~8 Mbps."
- §115.8 FEC NAPI walk — the `napi_alloc_skb` + `memcpy` line is misleading. Modern fec_main.c uses `napi_build_skb` over DMA-mapped pages (zero-copy). Update the snippet or note: "The NAPI fast path in current kernels uses `napi_build_skb` with the DMA buffer directly, avoiding the memcpy shown here. The memcpy version is the simpler form for explanation."
- §115.10 Pitfall "Pinmux conflict" — be concrete about which pins to check. On i.MX6ULL: ENET2 RXD0/RXD1 share package pins with UART2 TX/RX and ECSPI3 SCK/MOSI on some packages. Name one or two specific conflicts so the reader knows where to look.
- §115.9 Lab 9 PTP — the chapter sets up `ptp4l` but does not explain what success looks like. Add expected output: "After `ptp4l -i eth0` is running on a master and slave, the slave's offset converges to < 1 µs within a minute. Verify with `pmc -u -b 0 'GET CURRENT_DATA_SET'`."

---

## Ch116 — PMICs and the regulator framework

### AI wording / sledgehammer / buzzwords
- > "Get the **boot-sequence races** wrong (kernel starts the FEC before its PHY's 1.8 V rail is stable → PHY doesn't probe), and you'll chase ghost bugs forever."
  - "Chase ghost bugs forever" is fan-prose. Rewrite: "If you get the boot-sequence wrong — for example the kernel starts the FEC before its PHY's 1.8 V rail is stable — you will see PHY probe failures that look random."
- > "PMICs win on every axis once your board has >3 rails or needs real power management."
  - "Win on every axis / real power management" — both opinion-flavoured. Rewrite: "PMICs are better in every dimension once a board has more than three rails or needs runtime power management."
- > "Beautiful introspection — see exactly which consumer holds which rail enabled."
  - "Beautiful" is marketing. Rewrite: "The regulator summary makes the power tree visible: you can see exactly which consumer keeps each rail enabled."
- > "Without PMIC: each rail must be enabled by a separate GPIO with separate timing; the suspend driver becomes ugly. With PMIC: 1 line of code."
  - "Becomes ugly" + "1 line of code" — slogan pair. Rewrite: "Without a PMIC, each rail needs its own GPIO with its own timing; the suspend driver grows complex. With a PMIC, suspend is one I²C transaction."
- > "**the regulator framework treats every rail as a 'supply'; drivers declare their consumer-supply relationships in DT; the kernel computes the power-on order and ensures voltages are stable before any consumer probes**"
  - 40 words, three semicolons. Break: "The regulator framework treats every rail as a 'supply'. Drivers declare their consumer-supply relationship in the DT. The kernel computes the power-on order from the dependency graph, and waits for each rail to stabilise before letting consumers probe."
- > "This is why DVFS exists."
  - Fine.
- > "the silent killer"
  - Section heading "Power-up sequencing — the silent killer". Cliché. Rewrite: "Power-up sequencing — the most subtle bring-up trap."

### ESL readability
- > "ROHM BD71850MWV (compact, integrated for i.MX6/8 cores)."
  - Fine.
- > "Discrete remains common only for ultra-low-cost designs or where you want zero-quiescent on a battery rail (some PMICs have annoying 50 µA quiescent)."
  - "Annoying" is judgmental. Rewrite: "Discrete LDOs remain common only for the cheapest designs, or for battery rails where the PMIC's ~50 µA quiescent is too high."
- > "Linux runtime: the regulator framework's `regulator_enable()` walks dependencies."
  - "Walks dependencies" jargon for ESL. Rewrite: "At runtime, `regulator_enable()` walks the supply dependency graph and powers parent supplies first."

### Needs more depth
- §116.2 PCA9450 voltage encoding — `Vout = 0.6 + N × 0.025 V` is "typical." Be precise: "PCA9450 BUCK1: code = round((Vout − 0.60) / 0.025), valid 0..63 (0.60 V to 2.175 V). Different bucks have different formulas; check the datasheet's Table 27."
- §116.3 The "consumer probes after supply enabled" claim is the heart of the chapter and deserves one more sentence: "If a consumer driver's `probe()` is called before its supply is registered, the framework returns `-EPROBE_DEFER`. The kernel retries the probe later, after the missing supply appears. This is why the order of drivers loading does not matter — the deferral mechanism handles it."
- §116.4 Power-up sequencing list — the constraints (≤10 ms, ≤100 ms) are taken from the i.MX6ULL reference manual. Cite the source explicitly: "These timing limits are from the i.MX6ULL Reference Manual, Chapter 11 (Power Supply Strategy), Table 11-3."
- §116.5 DVFS — the power saving math says "Static (leakage) power ∝ V; ~10 % reduction." This is roughly right at 27 °C but leakage grows exponentially with temperature. One sentence: "Leakage scales linearly with V at constant temperature but doubles for each ~10 °C rise. Real-world DVFS gains are larger on a hot device than on a cool one."
- §116.7 The "don't write registers directly" warning is the right message, but the example does exactly that. Add a more explicit footnote: "This code is for one-time bring-up exploration only. In a production system, even reading these registers from user-space races with the regulator framework's runtime updates. Use `cat /sys/class/regulator/regulator.N/microvolts` instead."
- §116.9 Pitfall "OPP table wrong voltage" — be specific about how to find the right values: "The authoritative source is the i.MX6ULL Data Sheet, Table 12 (Operating Ranges). Each frequency has a Vmin; the OPP table must equal or exceed it. The NXP BSP's `imx6ull.dtsi` `cpu_opp_table` is correct by construction."
- §116.9 Pitfall "Ramp rate too fast" — name the symptom: "Symptom of too-fast ramp: a regulator-clocked consumer (DDR, PLL) glitches on every voltage change. Reduce `regulator-ramp-delay` (units are µV/µs — counterintuitively, *higher* number = slower because it means more µV per µs of allowed change)." (Verify: `regulator-ramp-delay` in DT is documented as "the soft-start ramp rate in µV/s"; double-check units.)

---

## Ch117 — External RTC

### AI wording / sledgehammer / buzzwords
- > "**the RTC chip is a 32.768 kHz oscillator + counters + I²C; the kernel `rtc-*` driver exposes it as `/dev/rtcN`; `hwclock` syncs between hardware clock and system clock; chrony or systemd-timesyncd updates the system clock from NTP/PPS and writes back to the RTC**"
  - 50-word block with five semicolons. Break: "The RTC chip is a 32.768 kHz oscillator plus counters, accessed over I²C. The kernel `rtc-*` driver exposes it as `/dev/rtcN`. `hwclock` syncs between the hardware clock and the system clock. `chrony` (or `systemd-timesyncd`) keeps the system clock disciplined from NTP or PPS, and writes the corrected time back to the RTC."
- > "Alarm interrupts let the RTC wake the SoC from suspend — but the alarm pin must be wired to a real GPIO that's mappable to a wake-up source in the kernel, which is the most-skipped detail."
  - 30-word with em-dash and trailing clause. Rewrite: "Alarm interrupts let the RTC wake the SoC from suspend. The alarm pin must be wired to a GPIO that the kernel can use as a wake source. This wiring requirement is the most-skipped detail in RTC bring-up."
- > "The external RTC fix: $0.50 chip + $0.30 coin cell on the I²C bus = the device knows the right time on every cold boot"
  - Equation-as-prose. Rewrite: "The external RTC fix: a $0.50 chip plus a $0.30 coin cell on the I²C bus. The device knows the correct time on every cold boot, runs scheduled alarms even when Linux is off, and stays calibrated for years."
- > "the high-end favorite"
  - Marketing. Rewrite: "the highest-accuracy popular choice"
- > "**End of Part VII — Device Cookbook (Ch 64–117, 54 chapters).**" closing paragraph claims "Every common device class has been covered" and "every external chip an i.MX6ULL product is likely to integrate is in this Part."
  - "Every X" double absolute. Soften: "Part VII covers most device classes you will integrate on an i.MX6ULL product: from QSPI flash to a GPS-disciplined time server."

### ESL readability
- > "The DS3231's built-in thermometer is a neat freebie — drives the TCXO temperature compensation but is also a usable ±3 °C ambient sensor."
  - "Neat freebie" + em-dash glue. Rewrite: "The DS3231's built-in thermometer is a useful bonus. It drives the TCXO temperature compensation internally and can also be read as a ±3 °C ambient sensor."
- > "battery only protects across short main outages"
  - "Short main outages" — the word "main" is ambiguous (could be "mains" power, or "primary"). Clarify: "The CR2032 only protects against short *main supply* outages. If both the main supply and the battery are removed at the same time, the RTC loses time."
- > "MPU-6050 IMU also defaults to 0x68. Bus conflict. Reroute one to a different address (DS3231 doesn't reconfigure; MPU-6050 has AD0 strap)."
  - Three sentence fragments. Rewrite: "The MPU-6050 IMU also defaults to address 0x68 — bus conflict. The DS3231 address is fixed. Strap the MPU-6050's AD0 pin to move it to 0x69."
- > "Time zone: hwclock can store the RTC in UTC or local time. UTC is the only sensible choice — `/etc/adjtime` records the policy."
  - "Only sensible choice" is opinion. Rewrite: "hwclock can store the RTC in UTC or local time. UTC is strongly recommended — local time breaks across DST transitions. `/etc/adjtime` records which is in use."

### Needs more depth
- §117.3 The `interrupts` line `interrupts = <23 IRQ_TYPE_EDGE_FALLING>;` appears alongside `interrupts-extended = <&gpio4 23 IRQ_TYPE_EDGE_FALLING>;` — these are duplicate (or conflicting) bindings. One sentence to resolve: "Use `interrupts-extended` for cross-controller IRQ references; the plain `interrupts` form is only valid when the parent specifies `interrupt-parent`. The duplicate here is an error; pick one."
- §117.4 `/etc/adjtime` policy — name the three columns: "The file has three lines: drift rate in seconds/day, last calibration time, and either `UTC` or `LOCAL`. hwclock reads all three on each invocation."
- §117.5 `rtcwake` — show the wake source verification: "After `rtcwake -m mem -s 30`, the next `dmesg | grep -i wakeup` should show `PM: suspend exit` with the cause. If the cause is anything other than the RTC alarm, your wake source is misconfigured."
- §117.5 The `tm_min += 5; if (tm_min >= 60) tm_min -= 60, tm_hour++;` adjustment is wrong if the resulting `tm_hour` ≥ 24, or if the day rolls. Use `mktime + timegm` properly: "Computing an alarm time by adjusting `tm_*` fields directly is error-prone. Convert to `time_t` with `timegm`, add seconds, convert back with `gmtime_r`."
- §117.7 chrony `rtcsync` — write-back is every 11 minutes, but only **if** the system clock is well-disciplined. One sentence: "chrony only writes the RTC when it considers the system clock 'trusted' (offset stable for several minutes after NTP convergence). On a freshly-booted, ill-disciplined system, the first RTC write may be delayed by 10–20 minutes."
- §117.9 Lab 6 daily scheduled task — the implementation is sketched but the actual `rtcwake` invocation with a wall-clock target is missing. Add: "Use `rtcwake -m mem -t $(date -d 'tomorrow 06:00' +%s)`. This sets the alarm to the absolute time 06:00 tomorrow."
- §117.10 Pitfall "OSF not cleared" — explain what OSF is: "OSF (Oscillator Stop Flag) is set when the DS3231 detects an oscillator stop (typically VCC and VBAT both lost). After replacing the battery, clear OSF by writing 0 to bit 7 of the STATUS register (0x0F). Until cleared, alarms are inhibited."

---










---

# Part VIII — Style/ESL Review

## Cross-cutting patterns

- **Em-dash chaining** dominates. Many sentences chain two or three clauses with `—`. Half of them should be periods, some commas. Two em-dashes in one sentence appears in every chapter.
- **"Not X — but Y" / sledgehammer "This is X. This is Y."** — the chapter intros lean on this rhetorical move repeatedly. Pick one per chapter, not five.
- **"the right tool for the right symptom" / "the bread-and-butter" / "the killer for ..." / "the secret weapon"** — marketing voice. Use technical voice.
- **Buzzwords**: `indispensable`, `incomparable`, `essential`, `canonical`, `the survivor`, `the universal X`, `the surgical X`, `surgeon's tool`, `medical kit`, `autopsy`, `flashlight`, `the workhorse`, `the modern X`. Heavy across Ch 118 and 119 especially.
- **Royal "we"** is moderate but still present in intros / pivot lines ("we wire JTAG...", "we do both", "you'll debug ...").
- **Hedging filler**: "Important", "Killer for ...", "Master these and ...", "Once you've used X, you wonder how anyone ...". Drop or use once.
- **Footnote-as-emphasis bold inside lists** ("**Important — `--multi` mode**", "**pr_debug is the secret weapon**"). Bold for emphasis is overused; reserve for genuinely critical lines.
- **Triplet rhythm** ("Three things X is good at: 1... 2... 3..." / "Three main modes:"). Used in Ch 118 (Wiring + Pinout + Open-OCD config), Ch 120 (perf three modes).
- **"Master these and you ..." / "Once you ... it ..."** — promise-style closing line ends multiple sections. One per chapter.

---

## Ch 118 — JTAG, OpenOCD, GDB

### AI wording / sledgehammer / buzzwords
- > "the day your bare-metal LED doesn't blink and `printk` isn't an option (because the kernel hasn't started), JTAG is the only ground truth. Same when U-Boot hangs in DCD execution and you have nothing to print to. Same when the kernel oopses in early-boot before serial init."
  - Rewrite: cut one of the three "Same when" lines, and the "ground truth" phrasing. "When the LED doesn't blink and `printk` isn't an option (the kernel hasn't started yet), JTAG is the only way in. The same is true when U-Boot hangs in DCD execution, or the kernel oopses before serial init."
- > "This is the difference between "I guess the boot fails somewhere in CCM init" and "I see XTAL_24M is at 0 mV; the crystal isn't running.""
  - Rewrite: classic "Not X. Y." sledgehammer. Soften: "It's the difference between guessing the boot fails somewhere in CCM init, and seeing that XTAL_24M is at 0 mV because the crystal isn't running."
- > "Single-step a literal assembly program; watch registers change; see exactly which instruction sets the GPIO bit that turns the LED on."
  - Triplet semicolons. Rewrite: "Single-step a literal assembly program. Watch registers change. See exactly which instruction flips the GPIO bit."
- > "This is *how you learn* the bare-metal layer — by stepping every instruction and matching to the reference manual."
  - Rewrite: drop italics + em-dash. "This is how you learn the bare-metal layer: step every instruction and match it to the reference manual."
- > "Hardware breakpoints are essential for read-only memory ..."
  - Rewrite: `essential` → `needed`. "Hardware breakpoints are needed for read-only memory."
- > "The classic problem: target is in some unknown state from a previous crash. How to halt at the very first instruction after reset?"
  - Rewrite: drop the rhetorical question + classic. "Often the target is in an unknown state from a previous crash. You want to halt at the first instruction after reset."

### ESL readability
- > "The tricky parts are: getting the adapter's USB-IDs right for OpenOCD, choosing the right *target* config (Cortex-A7 vs Cortex-M differ massively), handling Cortex-A's complications (multi-CPU, secure-vs-non-secure world, MMU on/off), and giving GDB the right symbol files at the right times (one ELF for bare-metal, another for U-Boot, another for kernel + per-module symbols)."
  - One sentence carries four ideas with three parentheticals. Rewrite as a bullet list under "Tricky parts:" — adapter USB IDs, target config (A7 vs M), Cortex-A complications, GDB symbol files per layer. ESL readers stall on this.
- > "Software breakpoints (default `break`) replace the instruction with the ARM `BKPT` instruction (A32: `0xE1200070`; Thumb-2: `0xBE00`) — the CPU traps to the prefetch-abort vector, the kernel/debugger sees a "debug" exception kind, and gdb regains control."
  - Triple-clause em-dash sentence with three sub-clauses. Break into three sentences. "Software breakpoints replace the instruction with the ARM `BKPT` (A32: `0xE1200070`; Thumb-2: `0xBE00`). The CPU traps to the prefetch-abort vector. The kernel/debugger sees a debug-exception, and gdb regains control."
- > "OpenOCD listens on:" — fine. The block right after the run command is dense; one sentence summary helps.

### Needs more explanation
- **§118.1 TAP/DAP architecture is under-explained for a 6 YOE MCU reader.** The chapter introduces `TAP` (Test Access Port state machine) in one paragraph, then jumps to `CoreSight` and `DAP`. A 6 YOE MCU dev has likely poked SWD on a Cortex-M but has never seen the CoreSight/DAP/AP/MEM-AP hierarchy. Add a half-page diagram: TAP scan chain → CoreSight DAP → APB-AP / AHB-AP → debug registers (DSCR, DBGDRCR) and break-point logic. Without that the reader can't read `target/imx6ull.cfg` and understand what's actually happening on the wire.
- **§118.4 The `target/imx6ull.cfg` is hand-waved.** Show the actual content (or a stripped excerpt): `jtag newtap`, `cti create`, `target create`, the IDCODE field. Otherwise the reader can't write their own when the shipped config doesn't match.
- **§118.5 `gdbserver` vs JTAG-attached `gdb` distinction is missing.** Reader will conflate the two. One paragraph: gdbserver requires a working kernel + libc on target (Ch 120); JTAG via OpenOCD works at any layer (bare-metal, U-Boot, kernel pre-init) because it talks to silicon, not to a process. State this explicitly here so Ch 120 makes sense.
- **§118.7 KASLR + `add-symbol-file` workflow is one line.** For a kernel with KASLR enabled and an unknown offset, show the actual procedure: read `kaslr_offset` from `/proc/kallsyms` (or the kernel log line), then `add-symbol-file vmlinux <text_addr + offset>`. Currently just says "use `add-symbol-file` with the runtime offset" with no example.
- **§118.10 `reset halt` mechanism.** The DBGEN + HRR mention is correct but unexplained. One paragraph: DSCR is the Cortex-A Debug Status and Control Register; setting `HALT_REQ` plus the right enable bits gates the CPU at the reset vector. Otherwise the bullet list reads like magic.

---

## Ch 119 — Kernel debugging without JTAG

### AI wording / sledgehammer / buzzwords
- > "JTAG (Ch 118) is the surgeon's tool; this chapter is the medical kit you actually carry."
  - Sledgehammer metaphor in the intro. Rewrite: drop the analogy. "JTAG is for bench work. This chapter covers what you can run on a deployed device with no debug header."
- > "printk — the survivor", "ftrace — the surgical tracer", "eBPF — modern probes", "kgdb — actual GDB over serial", "Kernel oops — the autopsy"
  - Every §-heading is a personification. Strip to neutral. "119.1 printk", "119.2 ftrace", "119.3 eBPF", etc. The reader doesn't need a thematic title for every section.
- > "**pr_debug is the secret weapon**"
  - Marketing voice + bold. Rewrite: "`pr_debug` is worth knowing about." or just drop the line — the explanation that follows speaks for itself.
- > "This unlocks **massive** existing debug coverage in mainline drivers without recompiling."
  - Drop bold + `massive`. "This enables existing debug prints in mainline drivers without rebuilding."
- > "Killer for performance investigation."
  - Rewrite: "Useful for performance investigation."
- > "Indispensable for "why did this 1-second operation take 10 seconds.""
  - Rewrite: `indispensable` → `useful`. "Useful for `why did this 1-second operation take 10 seconds`."
- > "These are *production-safe* — eBPF verifier prevents infinite loops, bad memory access, kernel crashes."
  - Em-dash chains, triplet of risks. Rewrite: "eBPF programs are production-safe. The in-kernel verifier rejects infinite loops, bad memory access, and anything that would crash the kernel."
- > "for "produced oopses we can't reproduce, give me a full snapshot" it's incomparable."
  - Rewrite: drop `incomparable`. "For oopses you can't reproduce, it's the right tool."
- > "That points to the exact source line. Combine with `git blame` and you know whose patch caused the regression."
  - Rewrite: "That points to the exact source line. Run `git blame` on it to see which patch introduced the regression."

### ESL readability
- > "the **software-only kernel debugging toolkit** that works on a deployed device with no hardware debug access. **printk**'s deeper toolbox (`pr_debug`, `dynamic_debug`, ring-buffer levels), **ftrace** (function tracer + `function_graph` + tracepoint events), **trace-cmd** + **KernelShark** (record + GUI), **bpftrace** and **bcc** (eBPF for live kernel introspection), **kgdb** over serial (when you do want a debugger but only have UART), and the **oops decoder** workflow (`addr2line`, `scripts/decode_stacktrace.sh`)."
  - One sentence of ~80 words. ESL reader stalls. Rewrite as a bullet list under the **What** line.
- > "On a customer's device hanging once every 3 days, you need *post-hoc forensics* — what was the kernel doing in the second before the freeze? ftrace's persistent buffer + an oops decoder gives you that."
  - Idiomatic + Latin. ESL-friendly: "If a customer's device hangs once every three days, you need to know what the kernel was doing in the second before the freeze. ftrace's persistent buffer plus the oops decoder answers that."
- > "eBPF lets you attach a probe to `tcp_retransmit_skb` on a production server and count retransmits per remote — without recompiling the kernel."
  - Em-dash for a single qualifier. "eBPF lets you attach a probe to `tcp_retransmit_skb` on a production server and count retransmits per remote address, without recompiling the kernel."
- > "Spam in `dmesg` → `dynamic_debug` to filter."
  - Idiom (`Spam`) + arrow. Rewrite: "Too much output in `dmesg`: use `dynamic_debug` to filter."

### Needs more explanation
- **§119.2 ftrace internals are skipped.** The chapter shows `echo function > current_tracer` but doesn't explain *how* ftrace patches the kernel: `mcount`/`__fentry__` callsites, CONFIG_FUNCTION_TRACER inserts a nop at every function entry, the tracer patches the nop to a call. For a 6 YOE MCU dev who has done bare-metal hooking, this is the conceptual hook that makes ftrace stop feeling magic. One paragraph + a one-line `objdump` of a traced function.
- **§119.3 eBPF verifier is mentioned but not explained.** "the verifier prevents X" — but what *is* the verifier? It's a kernel-side static analyzer that rejects programs with unbounded loops, out-of-bounds memory access, or paths that could fault. The reader will use bpftrace next chapter; they need to know why their program compiles but then "doesn't load" with a verifier error.
- **§119.4 kgdb workflow is incomplete.** The text shows the boot path with `kgdbwait` but doesn't show how to trigger kgdb from a *running* kernel (sysrq-g, or `echo g > /proc/sysrq-trigger`). That's the common case; `kgdbwait` is the early-boot edge.
- **§119.5 Oops decoding workflow has a gap.** The example shows `addr2line` against `vmlinux` for the kernel PC, and against the `.ko` for the module offset. But it skips how to *compute* the module offset from the oops output. The oops shows `[<7f000024>]`; this is the loaded VA, not the file offset. Show: `cat /proc/modules` to get module load base, subtract from PC, feed to `addr2line`. Otherwise the reader follows the example, gets a confusing answer, and gives up.
- **§119.6 kdump on small-RAM devices is dismissed in one line.** For a 6 YOE MCU dev this is the conceptually hardest part — kexec a second kernel from the dying kernel's memory, save vmcore from the second kernel. Even though the chapter says "skip on i.MX6ULL," explain why kexec works (the capture kernel's memory is reserved at boot, not allocated post-crash). One paragraph; it's a beautiful trick worth knowing.

---

## Ch 120 — User-space debugging

### AI wording / sledgehammer / buzzwords
- > "kernel debugging (Ch 118, 119) is the rare case; you'll debug applications 10× more often."
  - Opinion-as-fact framing. Soften: "Kernel debugging (Ch 118, 119) is less common in day-to-day work; most of the time you're debugging applications."
- > "Master these and you debug embedded apps as productively as desktop ones."
  - Sledgehammer closer. Rewrite: "Once these are set up, embedded app debug feels much like desktop debug."
- > "strace — the syscall flashlight"
  - Personification. Rewrite section header: "120.5 strace — trace syscalls"
- > "perf — the universal profiler"
  - Marketing. "120.7 perf — sampling profiler and counters"
- > "ltrace — same for library calls"
  - Fine. Less marketing.
- > "perf top — htop for CPU functions"
  - Cute analogy, fine if reader knows `htop`. Add one line: "Continuously updated, like `htop`, but functions instead of processes."
- > "The single most useful CPU-profile visualization. ... Once you've used flamegraphs, you wonder how anyone debugged performance without them."
  - Drop both sentences. The screenshot or example sells it; the marketing line doesn't.
- > "Killer for:" (in §120.5)
  - Rewrite: "Useful for:"

### ESL readability
- > "the toolkit for debugging your **user-space applications** on the i.MX6ULL target from a host workstation. **gdbserver** + **gdb-multiarch** for breakpoint-and-step debugging across the network; **strace** for "what syscalls is this program making"; **ltrace** for shared-library calls; **perf** for sampling profilers + hardware-counter-based analysis + flamegraphs; **core dumps** with `coredumpctl` for post-mortem analysis of crashed processes."
  - One 75-word sentence with five semicolons-as-bullets. Rewrite as a bullet list. ESL standard fix.
- > "99 Hz sampling (not a round 100 Hz — that's deliberate, to avoid harmonic with periodic kernel timers that often run at 100/250/1000 Hz) gives ~1 sample per 10 ms with minimal overhead (~0.1–0.5 %). Perfect for "what is this thing actually doing.""
  - Nested parenthetical + dash + quoted aside. Break apart. "99 Hz sampling, not 100 Hz, avoids harmonics with kernel timers (which run at 100/250/1000 Hz). At 99 Hz you get about one sample per 10 ms with 0.1–0.5 % CPU overhead. Good for figuring out what an app is actually doing."
- > "X-axis = sample count (~time spent); Y-axis = call stack."
  - The `~` shortcut and equals-signs read like notes. ESL-friendly: "The x-axis is sample count (roughly time spent); the y-axis is the call stack."
- > "Sysroot pointing to wrong path. gdb finds libc.so.6 in /lib (host) instead of the cross-built one; symbols mismatch."
  - Two semicolon-clauses. "When `sysroot` points at the wrong path, gdb loads the host's `libc.so.6` from `/lib`. Symbols then mismatch."

### Needs more explanation
- **§120.2 `sysroot` and `solib-search-path` are command-line gestures with no explanation of *why*.** The reader needs to know: GDB on the host needs to find the *exact same* shared libraries as the target so symbol offsets match. If the host's `/lib/libc.so.6` differs even slightly, every backtrace in libc is wrong. One paragraph explaining this; otherwise the reader sets sysroot, it still doesn't work, and they don't know why.
- **§120.7 perf hardware counters — what's actually available on Cortex-A7?** The chapter says "limited to a handful" but doesn't list them. The Cortex-A7 PMU exposes 4 programmable counters plus the cycle counter. Mention: `perf list` to enumerate, and which events are useful (`cache-references`, `cache-misses`, `branch-instructions`, `branch-misses`, `L1-dcache-loads`). Without this the reader has no idea what `perf stat -e <event>` is allowed.
- **§120.8 core dump tuning is shallow.** Default `core_pattern` interacts with systemd-coredump on systemd systems, with apport on Ubuntu, with the raw `core` file on others. Spell out the precedence and the `%e/%p/%t/%s` format specifiers. Also mention `coredump_filter` (`/proc/<pid>/coredump_filter`) — needed to capture shared memory regions, often missed.
- **§120.9 the worked example is great but tooling is mixed.** Reader needs to know that `wchan` requires `CONFIG_KALLSYMS=y` (most distros), and that `ss` replaces `netstat` (which is deprecated). One-line aside.

---

## Ch 120A — Mainline patch submission

### AI wording / sledgehammer / buzzwords
- > "if you write a driver in this book and it's useful, it can go upstream. Upstream-merged code is maintained forever (security backports, API migrations); your out-of-tree fork is on you."
  - Slightly preachy. Rewrite: "If you write a driver that's useful, it can go upstream. Upstream-merged code gets security backports and API migrations for free; an out-of-tree fork is yours to maintain."
- > "the kernel community has strict, *unwritten* rules — wrong commit-message format, untested patches, replying to review with hostility, top-posting on mailing lists — these get your patch silently dropped no matter how good the code is."
  - Triple em-dashes, four examples in one breath, sledgehammer close. Break apart. "The kernel community has strict and partly unwritten rules. A wrong commit-message format, an untested patch, a hostile reply to review, or a top-posted email is enough to get a patch silently dropped, no matter how good the code is."
- > "This chapter is the cultural primer the kernel docs don't write down."
  - Self-aggrandizing closer. Drop it; the chapter speaks for itself.
- > "Lore.kernel.org is the public archive of every mailing-list discussion since ~1998; **always search there before sending** — your "novel" fix may have been tried and rejected three times already, and the rejection threads tell you why."
  - Two clauses joined by `;` and `—`. Rewrite: "Lore.kernel.org is the public archive of every mailing-list discussion since ~1998. Always search it before sending. A 'novel' fix may have been tried and rejected three times already, and the rejection threads tell you why."
- > "DT bindings are one of the easiest categories to get merged — they're additive (don't break anything) and self-contained. Good first-patch target."
  - Fine, but the "Good first-patch target." fragment reads like a TV pitch. Either fold in or drop.

### ESL readability
- > "The output is your To: + CC: list. **Do not invent additional CCs** — only what `get_maintainer.pl` says. Spam to "the whole kernel" gets you on people's filter-out lists."
  - The idiom "filter-out lists" is informal. Rewrite: "The output is your To and CC list. Don't add extra CCs beyond what `get_maintainer.pl` returns. CC'ing every kernel address you can find gets you ignored or filtered."
- > "Maintainer responds with feedback. Don't argue; address each point. If you disagree, explain politely."
  - Choppy three-fragment paragraph. ESL-friendly: "When a maintainer responds with feedback, address each point. If you disagree, say so politely and explain why."
- > "Apologies for the missing comment. The hardware register interprets the value in 50% steps; multiplying by 2 converts user-supplied percent to register units. I'll add a comment in v2."
  - This is example dialog — keep it. Fine.
- > "If you go silent for >2 weeks after a review, your patch gets dropped from maintainers' queues. Stay engaged."
  - Two short imperatives. Fine, but `>2 weeks` reads like a math symbol; spell out: "If you go silent for more than two weeks after a review, your patch will be dropped from the maintainer's queue. Stay engaged."

### Needs more explanation
- **§120A.3 commit-message structure is shown but not *taught*.** The example has imperative-mood subject and `WHY not what` body. A 6 YOE MCU dev whose company uses "fixed bug" commits needs to see *why* the kernel insists on imperative mood ("subsystem: do X" reads naturally as "this patch makes the subsystem do X"). One sentence on the grammar pattern. Also: the `Fixes:` tag is shown once with no explanation of where to find the original commit hash — show `git log --oneline --grep=...` or `git log -- <file>` workflow.
- **§120A.4 checkpatch.pl is run but its output isn't read.** Show one or two *actual* failing checkpatch outputs ("ERROR: do not use assignment in if condition", "WARNING: line over 80 characters") and how to interpret them. Otherwise the reader doesn't know what to do when checkpatch complains.
- **§120A.5 `get_maintainer.pl` output is shown but the role-suffix is not explained.** `(maintainer:...)`, `(reviewer:...)`, `(open list)`, `(moderated list:...)` — each is treated differently. Maintainers go to `--to`, reviewers and lists to `--cc`. State this; it's the first practical question the reader has after running the script.
- **§120A.6 `git send-email` SMTP config is hand-waved for Outlook/corporate.** Gmail App Password is explained. Many readers will have a corporate SMTP server with O365 / OAuth2 — say a sentence about `oauth2.py` helpers or recommend a personal address for kernel work (which is what most kernel devs do).
- **§120A.8 `--in-reply-to=<msg-id>` is mentioned but not sourced.** Where do you get the Message-ID? From the lore.kernel.org page of the v1 thread (right-click → copy permalink, or the `Message-ID:` header in the raw mbox). Without this the reader can't actually use `--in-reply-to`.
- **§120A.11 the `b4` workflow is one block of commands with no narrative.** `b4 prep -n` creates a new series; `b4 send` previews and sends; `b4 trailers` collects review tags into your local branch. Show the loop: prep → write → send → wait → trailers → send v2. Currently it reads as a tool reference, not a workflow.
- **§120A.12 the YAML example uses `unevaluatedProperties: false` without explanation.** This is the strictest JSON-Schema validation mode — any property not in `properties:` or inherited via `allOf` is rejected. For a reader new to YAML bindings this is critical (Rob Herring's bot will reject your binding if you forget it). One sentence.

---

## Ch 121 — Capstone: custom board port

### AI wording / sledgehammer / buzzwords
- > "the **capstone exercise** that puts everything in this book together."
  - Self-congratulation in the opening line. Rewrite: "A board-port exercise that uses most of what came before."
- > "every Cookbook chapter taught a slice. Doing a real board port is where those slices integrate into competence."
  - "Slices integrate into competence" reads like a workshop brochure. Rewrite: "Each Cookbook chapter covered one piece. A real board port is where those pieces have to work together."
- > "That deliverable, plus the experience of debugging the inevitable subtle problems, is what makes an embedded-Linux engineer hireable."
  - Career-marketing close. Drop the last clause: "That deliverable, plus the debugging experience that comes with it, is what gets you to the next level of confidence on this stack."
- > "Don't try to "boot everything at once" — bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral, in that order, with a serial-console probe after each."
  - Single em-dash sentence with five clauses. Rewrite: "Don't try to boot everything at once. Bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral. Probe the serial console after each step."
- > "Use Ch 118's JTAG when serial is too coarse. Keep a *known-good* fall-back image you can flash to recover from bricks."
  - Fine. Drop the italics on `known-good`.
- > "And reflect: at the end, what was the surprise? Why? That insight is what makes the next board port faster."
  - Royal "we" / coaching tone. Rewrite: "At the end, ask what surprised you and why. That's what makes the next port faster."
- > "This is the **highest-risk** step. Bad DDR config = nothing else works. The DDR Stress Tool is non-negotiable; do not hand-calculate."
  - "Non-negotiable" + "do not" + bold reads like a sales rep. Rewrite: "This is the riskiest step. If DDR config is wrong, nothing else will work. Use the DDR Stress Tool; don't hand-calculate."
- > "If you see U-Boot banner → 80 % of bring-up complete."
  - Made-up statistic. Soften: "If you see the U-Boot banner, the hard part is behind you."
- > "If this works, you've taken a peripheral from "nonexistent on the EVK" to "fully driven by mainline Linux" via DT alone — the canonical pattern."
  - Rewrite: drop `canonical`. "If this works, you've taken a peripheral the EVK doesn't have to a fully Linux-driven device using DT alone. This is the common pattern."
- > "**This script** is the deliverable. Hand it to a teammate; they get the same image. Reproducibility is the difference between "I shipped a product" and "I have a Linux running on my desk.""
  - Sledgehammer "X is the difference between Y and Z" closer. Rewrite: "The script is the deliverable. A teammate runs it and gets the same image. Without a reproducible build, what you have on your desk isn't a shippable product."

### ESL readability
- > "You'll touch: pin-muxing (Ch 5), DDR initialization (Ch 14), U-Boot porting (Ch 22), kernel DT (Ch 27), each peripheral chapter that applies (whatever your board has)."
  - Inline parentheticals make this hard to scan. Reformat as a short bullet list under "You'll touch:".
- > "A 5 % timing margin difference can mean "works at 25 °C, crashes at 40 °C.""
  - The inline quoted phrase is fine; works for ESL. Keep.
- > "`console=ttyS0` won't work on i.MX6ULL (it's `ttymxc0`). Verify against your DT."
  - Good. Keep.
- > "Solder/desolder peripherals on the existing board:" plus the bullet list with one-line scenarios.
  - Fine but five bullets all start with a verb fragment. Add one connecting sentence: "These changes touch real wiring and partial-board mods. Good practice for DT skills."

### Needs more explanation
- **§121.2 hardware variant tradeoffs are listed but not explained.** Option A "Pretend-port" sounds dismissive — but it's the right starting choice and the chapter doesn't justify it. State: even renaming the board exercises the full toolchain (defconfig, board file, DTS, MAINTAINERS), which is the bulk of what a real port involves. Option C "Full PCB" — say one sentence on the gap (schematic, layout, fab, assembly) and why it's out of scope.
- **§121.4.4 DDR Stress Tool is named without explanation of what it does.** A 6 YOE MCU dev probably hasn't used it. One paragraph: it's an NXP tool that runs on the target, sweeps DDR calibration values, reports the safe operating window. It's a *bring-up* tool, not a *debug* tool — you run it once per layout, capture the calibration block, embed it in U-Boot SPL.
- **§121.5.4 `bootz` vs `bootm` vs `booti` is not explained.** Reader sees `bootz 0x80800000 - 0x83000000` and doesn't know why three addresses with a `-`. State: `bootz <kernel> [initrd] <dtb>`, with `-` for "no initrd." Otherwise the reader copies the magic and panics when it doesn't fit their layout.
- **§121.7 the build script does a `sudo bash -c` heredoc with multiple mounts.** That's a serious footgun for ESL readers — if `sfdisk` partitions the wrong device, you lose your laptop's disk. Mention: confirm `$TARGET_SD` is a USB SD reader, not `/dev/sda`. A `lsblk | grep $TARGET_SD` sanity check before `sfdisk` would save accidents.
- **§121.8 the failures section lacks the JTAG link.** Each failure should say "verify with JTAG / probe / multimeter." Several do; "Driver doesn't probe" should add: `dmesg | grep -i probe`, `cat /sys/kernel/debug/devices_unbound`, and the "EPROBE_DEFER" gotcha (driver returns -EPROBE_DEFER, kernel retries later — looks like a fail in early dmesg but resolves later).

---

## Ch 121A — CI/CD for embedded Linux

### AI wording / sledgehammer / buzzwords
- > "any embedded product shipping updates beyond one engineer's laptop needs CI."
  - Absolutist opening. Soften: "Any embedded product shipping updates from more than one developer benefits from CI."
- > "The fundamental risk: someone merges a DT change that breaks boot; nobody notices until a customer tries to update; days of fire-fighting."
  - Triple semicolons + idiom. Rewrite: "The risk is real: someone merges a DT change that breaks boot, nobody notices until a customer tries to update, and you spend days firefighting."
- > "With CI + real-hardware smoke tests on every PR, that bug is caught in 10 minutes. The cost is one $50 dev board + one Linux box + 4 hours setup. The savings — even on a 3-person team — pay back in the first month."
  - Triplet rhythm + sales pitch. Rewrite as two sentences and drop the dollar-figures-as-flourish: "With CI plus real-hardware smoke tests on every PR, that bug surfaces in ten minutes. The setup cost is small (a dev board, a Linux host, and a few hours) and pays back quickly."
- > "**the trick is that a normal cloud CI runner has no USB to your hardware; you self-host a runner on a Linux box that physically owns the board**"
  - "The trick is X" voice. Drop the rhetorical move: "A normal cloud CI runner has no USB connection to your board. To run hardware tests, self-host a runner on a Linux box that physically owns the board."
- > "A "smoke test" is small (boot, get prompt, run 3 sanity checks, capture log) but enormously valuable."
  - "Enormously valuable" is buzzword. Rewrite: "A smoke test is small (boot, get prompt, run a few checks, capture the log) but catches most regressions."
- > "For embedded, "it compiles" is necessary but not sufficient. The real value of CI is **catching regressions on actual hardware** ..."
  - "Necessary but not sufficient" is academic-paper voice. Rewrite: "For embedded, building cleanly isn't enough. The real value of CI is catching regressions on real hardware ..."
- > "Use short, shielded cables; powered hubs."
  - Fine. Concise.

### ESL readability
- > "`pull_request_target` is dangerous"
  - Fine, but a reader who hasn't met it will not know why. Add one sentence: "`pull_request_target` runs the workflow with write permissions on the target repo, which a forked PR can abuse."
- > "**continuous integration** for embedded Linux — building U-Boot, kernel, rootfs on every commit; running smoke tests on **real hardware** in a board farm via a self-hosted CI runner with USB-OTG flashing; a **Labgrid**-style test harness; pass/fail signaling back to the PR."
  - One 50-word **What** sentence with three semicolons. Bullet-list it.
- > "On every push, the runner does the Ch 121 build, flashes via `uuu`, watches serial for `=>` prompt + a sysfs check, captures the serial log, marks the PR pass/fail."
  - Five comma-clauses. Break into two sentences: "On every push, the runner does the Ch 121 build and flashes via `uuu`. It then watches serial for the `=>` prompt, runs a sysfs check, captures the log, and marks the PR pass or fail."

### Needs more explanation
- **§121A.3 `uuu` is used without an introduction.** Reader who hasn't done Ch 8/19's recovery path won't know what `uuu` is. One sentence: `uuu` (Universal Update Utility) puts the i.MX into Serial Download Protocol mode, then scripts U-Boot + kernel + rootfs loading over USB. Came from NXP's MFGTOOL.
- **§121A.4 the Python smoke-test script needs more guard rails.** No try/except, no carriage-return handling on different shells, no escape if the board hangs partway. For a 6 YOE MCU dev who'll adapt this, mention: wrap each `expect` in try/except, log the buffer on failure, always do a hard power-cycle in `finally`. Pexpect is the canonical library for this kind of script; mention it.
- **§121A.5 Labgrid is one short section.** This is the *hard concept* in the chapter — how multiple test runners coordinate on shared hardware, the coordinator/exporter/client model, and why locking matters. A diagram (Labgrid Coordinator ↔ Exporter on board host ↔ Client/test runner) plus the "place" abstraction would carry it. Currently reads as just "configure a YAML, call the API."
- **§121A.7 ccache for cross-builds has a subtle gotcha.** ccache by default doesn't consider the cross-compiler version in its hash, leading to "stale cache after toolchain upgrade." Mention `CCACHE_COMPILERCHECK=content` to fix this. Currently the chapter just says "5× speed-up" with no mention of cache-poisoning risk.
- **§121A.8 trigger patterns include `paths-ignore` and `paths`** — but the YAML is brittle (e.g., a PR that touches both code and docs runs both, then doesn't run on the next docs-only push). Add one sentence about the limitation: `paths-ignore` is best-effort, not a contract.

---

## Ch 122 — Build your own cross-toolchain

### AI wording / sledgehammer / buzzwords
- > "the **canonical tool**"
  - Used twice in the intro. Rewrite second use: "the standard tool." Or just "crosstool-NG."
- > "for most users, `apt install gcc-arm-linux-gnueabihf` is fine. So why build your own? Three real reasons:"
  - "Three real reasons" triplet rhetoric. Rewrite without the count: "For most users, `apt install gcc-arm-linux-gnueabihf` is fine. Build your own when one of these matters: ..."
- > "Educational value matches Ch 11 (boot ROM image) and Ch 14 (DDR init)."
  - Self-referential praise. Drop. Replace: "It also teaches what every flag and stage actually does."
- > "**the multi-stage build resolves the chicken-and-egg: stage 1 gcc ... → kernel headers → glibc ... → stage 2 gcc ...**"
  - Bold + arrow chain is hard to read. Rewrite the line into clean prose: "A multi-stage build solves the chicken-and-egg problem. Stage 1 gcc has no libc and can only compile freestanding code. It builds the kernel headers, then glibc. Stage 2 gcc is then built against the new glibc and has a full C++/pthread runtime."
- > "Get any of these wrong and the linker can't find libc, or gcc looks in `/usr/lib` instead of the cross sysroot."
  - Fine. Concrete.
- > "Each `configure` line is a tour of GNU autoconf flags."
  - Cute but vague. Drop or replace with concrete: "Each `configure` line is a stack of GNU autoconf flags. The important ones are `--target`, `--prefix`, and `--with-sysroot`."
- > "For one-time understanding, build it by hand. Compressed (a full tutorial is 30+ pages; here's the skeleton):"
  - Aside-as-parenthetical. Move outside: "Building it by hand is a one-time learning exercise. A full tutorial would run 30+ pages; here's the skeleton."
- > "Your own toolchain, pinned to specific versions, reproducible."
  - Triplet-closer. Drop or rewrite: "You now have a toolchain pinned to specific versions, reproducible by anyone with the same config."

### ESL readability
- > "You want to build gcc. gcc needs glibc to compile programs. glibc needs gcc to compile itself. Circular."
  - The four-fragment punch landing on "Circular." is mannered. Rewrite ESL-friendly: "To build gcc, you need glibc. To build glibc, you need gcc. This is circular."
- > "**hf binaries cannot run on soft-float systems** and vice versa."
  - "and vice versa" is short but Latin-source idiom. ESL-friendly: "Hard-float binaries cannot run on a soft-float system. Soft-float binaries can technically run on a hard-float system, but you usually don't mix them."
- > "These three concepts confuse first-time toolchain builders:"
  - Fine. Keep.
- > "When compiling for the target: gcc reads .c source → gcc preprocessor includes ..."
  - The ASCII-art "→" chain is fine for the engineer-at-whiteboard tone. Keep.
- > "**Pick guide:**"
  - Twice in the chapter. Fine.

### Needs more explanation
- **§122.2 bootstrap problem — the "why each stage is configured this way" is hand-waved.** Why does stage-1 gcc need `--disable-shared`, `--disable-threads`? Because shared libraries need a dynamic linker (libc), and threads need libpthread (libc). Stage 1 is freestanding. One paragraph spelling out the *causal* link from "no libc yet" to each disable-flag. Otherwise it reads as a magic incantation.
- **§122.4 manual build — the `libc_cv_forced_unwind=yes` flag is mysterious.** This is the famous glibc-build-against-stage-1-gcc workaround. Mention: glibc's configure checks if gcc supports a feature by *trying to compile a test program that links*; stage-1 gcc can't link, so the check returns false, but the feature actually works at runtime. Forcing `=yes` skips the broken check.
- **§122.5 musl vs glibc — `dlopen support`** row says "yes/yes/yes/partial". This contradicts the well-known "musl static + dlopen don't mix" issue. Clarify: dynamic musl supports dlopen; static musl does not. (Same is true of glibc, but glibc's static dlopen "works" with warnings.)
- **§122.6 ABI suffix — the calling-convention difference is not shown.** Mention concretely: on `gnueabihf`, `float foo(float x)` passes `x` in `s0` (FPU register) and returns in `s0`. On `gnueabi`, `x` is passed in `r0` (general register) and the FPU is used internally if available. That's why the ABIs are not link-compatible.
- **§122.8 sysroot vs prefix vs target — the diagram is good but lacks one concrete check.** Show `gcc -print-sysroot`, `gcc -print-search-dirs`, `gcc -v` (which prints the full include and library search paths used at this invocation). These are the actual commands a reader will need when debugging "why does gcc not find my libc."

---

## Ch 122A — BSP → mainline migration

### AI wording / sledgehammer / buzzwords
- > "You're staring at a project-defining decision. This chapter is the playbook so it doesn't become a project-killing one."
  - Sledgehammer "project-defining → project-killing" wordplay. Rewrite: "This is a project-defining decision. This chapter is the playbook for getting it right."
- > "The "easy" path — stay on 4.1.15 forever — leaves accumulated CVEs unfixed:" / "The "hard" path — migrate to mainline 6.6+ LTS — buys:"
  - Scare-quoted easy/hard pattern. Rewrite without the quotes and the parallel structure: "Staying on 4.1.15 means accumulated CVEs go unfixed: ... Migrating to mainline 6.6+ LTS buys: ..."
- > "After 100+ CVEs, the backport effort exceeds the migration effort. Track this."
  - Fine, "Track this." is a useful imperative.
- > "Months of work, not years."
  - Closer cliche. Rewrite: "Expect months of work, not years."
- > "The hardest bits aren't technical (`git rebase` does most of it); they're *cultural*: convincing management that 6 months of "no new features, just kernel work" pays back over the product's life."
  - "Not X, they're Y" sledgehammer + parenthetical + italics. Rewrite: "The hardest part isn't technical. `git rebase` handles most of the code work. The hardest part is cultural — convincing management that six months of kernel work, with no new features, pays back over the product's lifetime."
- > "This chapter arms you with the data."
  - Drop. The chapter speaks for itself.

### ESL readability
- > "Plus: Old toolchain (gcc 6.x) won't compile mainline kernel 6.6 cleanly. The kernel's hard minimum is gcc 5.1 (Documentation/process/changes.rst), but newer features and warnings require gcc 11+; most distros ship gcc 12+ for embedded cross-builds."
  - Two nested parentheticals. Break apart: "Plus there's a toolchain problem. gcc 6.x won't compile a mainline 6.6 kernel cleanly. The kernel's hard minimum is gcc 5.1 (see `Documentation/process/changes.rst`), but newer features need gcc 11+. Most distros ship gcc 12+ for embedded cross-builds."
- > "Old GStreamer 1.10; mainline drivers use new V4L2 APIs."
  - Fragment-as-sentence + idiomatic shorthand. ESL-friendly: "Old GStreamer 1.10 doesn't speak to mainline V4L2 drivers, which now use newer APIs."
- > "If mainline has it (committed by someone else after 2017): **delete the BSP patch**, use mainline's version."
  - The colon-comma chain reads awkward. Rewrite: "If mainline has it already (someone committed the same fix after 2017), delete the BSP patch and use the mainline version."
- > "Migrate subsystems in dependency order, **most-isolated first**."
  - Fine. ESL clear.
- > "Cutover: schedule a date when new customer shipments come on the mainline-port version."
  - "Cutover" is a project-manager idiom. ESL-friendly: "Plan the cutover. Pick a date. After that date, new customer shipments use the mainline-ported kernel."

### Needs more explanation
- **§122A.2 inventory script is too short.** The `git log --oneline` to spreadsheet flow is the right idea but skips the actual hard part: matching a BSP patch to its mainline counterpart. Show `git log --grep='<subject substring>'` on mainline, plus the `--diff-filter` for "did this file get added later?" Also: `git pickaxe` (`git log -Sfunction_name`) is the workhorse for "where did this code go?" Mention it.
- **§122A.4 subsystem dependency graph** — the ASCII art is good but doesn't explain *why* clk/pinctrl come first. Why: every device driver `probe()` calls `clk_get()` and `pinctrl_select_state()`. If these are wrong, every other subsystem fails to probe with confusing errors (-EPROBE_DEFER loops, "could not get clock"). Spell this out.
- **§122A.5 per-subsystem migration — the cherry-pick conflict handling is just one bullet.** Show a concrete worked example: a BSP patch that adds a parameter to a function that mainline has already removed. Strategy: (a) is the BSP patch's intent already in mainline? `git log -p drivers/foo/foo.c` to see; (b) if no, port the *intent* not the diff — write a new patch against current mainline structure. This is the actual hard skill of the chapter.
- **§122A.6 "pinned driver" section needs concrete pointers.** etnaviv vs Vivante is mentioned but the actual API gap isn't shown. The relevant gap: vendor blob expects `vendor-fbdev` ioctl path; etnaviv exposes only DRM/GBM. A short table of "vendor stack → mainline equivalent + caveat" would help.
- **§122A.9 worked example is light on the actual hard step.** "Boot from existing rootfs first; later update rootfs to libcs ABI-matched to gcc 13" — this *is* the hard step. Mainline 6.6 + glibc 2.38 rootfs + old gcc 6 BSP binaries = ABI mismatch. Spell out the bisect strategy: (1) boot mainline with BSP rootfs to validate kernel; (2) rebuild rootfs with new toolchain; (3) bisect any new-rootfs-only failures. Currently the example skips from "build kernel" to "cutover" in one bullet.

---

## Ch 123 — Yocto vs Buildroot

### AI wording / sledgehammer / buzzwords
- > "the **build-system decision** that defines your product's whole CI/release/maintenance story."
  - Sweeping opening. Rewrite: "Picking a build system shapes your product's CI, release, and maintenance flow for years."
- > "Then the honest verdict: when each wins, when each is a poor fit, when *neither* is right."
  - Italics + triplet rhythm. Rewrite: "Then a verdict on when each wins, when each is a poor fit, and when neither is right."
- > "Choosing badly costs months down the road; choosing well saves them."
  - Cliche. Drop or rewrite: "Choosing badly costs months; choosing well saves them — but mostly later, when you can't tell the difference yet."
- > "Most teams overestimate their multi-variant complexity and end up with Yocto sledgehammers cracking Buildroot walnuts."
  - Cute metaphor; works once but fights for attention with the surrounding bold. Keep, drop the bold around the surrounding sentence so this lands.
- > "That's *everything*: cross-toolchain (built or downloaded), U-Boot, kernel, rootfs with selected packages. One command, one tree, predictable output."
  - Italics + triplet close. Rewrite: "That's everything in one tree: cross-toolchain, U-Boot, kernel, rootfs with the packages you picked. One command, predictable output."
- > "The pieces:" followed by bullets.
  - Fine.
- > "For complex builds, Yocto's task graph (do_fetch, do_unpack, do_patch, do_configure, do_compile, do_install, do_package, ...) gives finer control but more places to get lost."
  - "More places to get lost" is fine. Keep.
- > "Buildroot is *quasi-reproducible*" / "Yocto with `BB_HASHSERVE` is *strongly reproducible*"
  - Italics + parallel structure. Rewrite without italics: "Buildroot is mostly reproducible. Yocto with `BB_HASHSERVE` is strongly reproducible — same inputs always produce bit-for-bit identical outputs."
- > "Choosing Yocto for a 1-person project. You spend 80 % of your time learning Yocto and 20 % on your product. Use Buildroot."
  - Made-up 80/20. Soften: "Yocto on a one-person project: you'll spend more time on Yocto than on your product. Use Buildroot."

### ESL readability
- > "every production embedded Linux team uses one (occasionally both)."
  - The inline parenthetical and the absolutist `every` are awkward. Rewrite: "Most production embedded Linux teams use Buildroot or Yocto. Some use both."
- > "The choice has implications for years: hiring (Yocto skills are scarcer + more expensive than Buildroot), CI infrastructure (Yocto builds are slower + need more storage), how easy it is to onboard a new engineer (Buildroot is friendlier), how easy it is to maintain a fleet of variants (Yocto wins), how easy it is to debug a build problem (Buildroot wins)."
  - 60-word sentence with five parenthetical mini-clauses. Reformat as a bullet list: "The choice affects: ..."
- > "Time-to-first-image | 30–60 min | 1–4 hours (initial); 5–30 min (incremental)"
  - Fine in a table.
- > "Choose badly costs months down the road; choosing well saves them."
  - Already flagged above.

### Needs more explanation
- **§123.1 the comparison table is the chapter's centerpiece but several rows need context.** "sstate-cache (artifacts keyed by input hash)" — what's an input hash? It's BitBake hashing every input to a task (source files + dependencies + recipe content) and using that as a cache key. If the inputs are bit-identical, the cached output is reused. One paragraph in §123.3 would help.
- **§123.3 Yocto layer structure is shown but BitBake variable expansion isn't.** `${PV}`, `${PN}`, `${D}`, `${WORKDIR}`, `${S}`, `${B}` — these appear in §123.3 onward without an introduction. A short reference table: PN=package name, PV=package version, S=source dir, B=build dir, D=destination (install root), WORKDIR=top of the build's working tree. Without this the recipes look like template syntax-noise.
- **§123.4 / §123.5 "when X wins" lists overlap.** Several criteria (size, build time, learning curve) cut both ways. Add a one-paragraph "the decision in 30 seconds": "single product, < 5 engineers, < 3 board variants → Buildroot. Vendor BSP serving multiple downstream products, > 5 board variants, regulatory compliance → Yocto."
- **§123.8 reproducibility — what "BB_HASHSERVE" actually does is not explained.** It's a network-accessible hash equivalence service. Two recipes that produce *functionally* identical outputs from *different* input hashes can share a cache entry. This is the secret behind Yocto's reproducibility claim. Without this, readers don't see why Yocto beats Buildroot here.
- **§123.10 CI mention is one paragraph.** This is a Part VIII chapter; Ch 121A is right next door. Add a sentence cross-referencing: "Ch 121A shows the CI mechanics; this section just notes the storage/cache cost difference."

---

## Ch 123A — Yocto layer development

### AI wording / sledgehammer / buzzwords
- > "the production-grade **Yocto layer design** pattern."
  - "Production-grade" is a marketing adjective. Rewrite: "The Yocto layer design that production vendors use."
- > "the pattern below is what production vendors use; it's the difference between "Yocto is awful" and "Yocto is the best build system in embedded Linux.""
  - Sledgehammer "is the difference between X and Y" close. Drop or rewrite: "Done well, Yocto becomes a tool you'd recommend. Done badly, it becomes the build system everyone hates."
- > "**layers stack like CSS — later layers override earlier ones via priority. Use bbappend to extend an upstream recipe; use a new bb for your own packages; use machine config for "this hardware needs these kernel modules"; use distro config for "this product line needs OpenSSL 3 + systemd"; use image recipes for "this final shipped image contains these packages"**"
  - One 65-word bolded run-on sentence with five `use X for ...` clauses. Reformat. Even with the analogy, ESL readers won't survive it. Bullet list.
- > "Get these separations right and a 5-machine, 3-distro, 10-app matrix becomes trivial. Mix them up (machine-specific stuff in distro config) and you build a tar pit."
  - "Tar pit" — keep, vivid and clear; one of the better metaphors in the book. But the "trivial" claim is overstated. Soften: "Get these separations right and a 5-machine, 3-distro, 10-app matrix becomes manageable."
- > "Common pattern: a vendor recipe almost-does-what-you-want; you bbappend to tweak."
  - Fine. Concise.

### ESL readability
- > "Distinguishing what goes where:" + 3-row table.
  - Fine. Good.
- > "If you mix these — e.g., put a machine-specific kernel module in the distro config — you create surprises:"
  - Em-dash inserts an example mid-sentence. Rewrite: "If you mix these (for example, putting a machine-specific kernel module into the distro config) you create surprises:"
- > "A bad layer organization makes every change a hunt across the metadata tree; a good one isolates your product changes from upstream, makes variants trivial, and survives upstream layer updates."
  - 35-word semicolon-joined sentence. Break: "A bad layer organization makes every change a hunt across the metadata tree. A good one isolates your product from upstream, keeps variants simple, and survives upstream layer updates."
- > "BitBake applies the patch + the config fragment automatically. You haven't forked `meta-imx`'s kernel recipe — you've augmented it. Survives upstream layer updates cleanly."
  - The "Survives upstream layer updates cleanly." fragment is ad-copy. Rewrite: "BitBake applies the patch and the config fragment automatically. You haven't forked `meta-imx`'s kernel recipe; you've augmented it. The change survives upstream layer updates."

### Needs more explanation
- **§123A.1 `BBFILE_COLLECTIONS`, `BBFILE_PATTERN`, `BBFILE_PRIORITY`, `LAYERSERIES_COMPAT`, `LAYERDEPENDS` are shown but not explained.** Each is a critical layer-config variable. A short table of "this variable + what it does" is needed. Otherwise the `layer.conf` looks like boilerplate to copy without understanding.
- **§123A.2 `MACHINEOVERRIDES =. "mx6ull:"` — what does `=.` do?** It's BitBake's "prepend with space" operator, distinct from `:=` (immediate expansion), `+=` (append), `=+` (prepend), and `.=` (append no-space). A short reference to BitBake's many operators is needed; the variable-operator zoo is one of Yocto's main confusions for newcomers.
- **§123A.4 the recipe uses `do_install:append()` (with the colon).** This is the modern syntax (Yocto 3.4+ / Honister+). Older recipes used `do_install_append()` (underscore). Mention this — a 6 YOE MCU dev finding old documentation will mix the two and BitBake errors out cryptically.
- **§123A.5 bbappend pattern `linux-imx_%.bbappend` — the `%` wildcard is not explained.** It matches "any version of the recipe named linux-imx." Use `_%` for "any version," `_6.6.%` for "any 6.6.x." Critical to get right; mismatched patterns silently fail to apply.
- **§123A.10 SRC_URI offline cache — the difference between source tarballs cache and sstate-cache is not stated.** `downloads/` = source archives (small, < 1 GB). `sstate-cache/` = build artifacts (large, 10+ GB). Both are needed for fully-reproducible offline builds; you need to copy both. Currently the section only mentions `downloads/`.
- **§123A.13 the `PR` (Package Revision) pitfall is mentioned but `PR-server` (the service that auto-increments PR across CI builds) isn't.** For production fleets using opkg/rpm/dpkg for delta updates within a kernel-version, this is critical. One sentence pointing to it.

---

## Ch 124 — Secure boot and OP-TEE

### AI wording / sledgehammer / buzzwords
- > "any product that handles user data, payment credentials, certificate-based identity, or DRM content needs verified boot. Without it, an attacker who gets physical access can: replace U-Boot with one that dumps memory, boot a custom kernel that bypasses authentication, extract storage encryption keys."
  - Triplet of attack scenarios + sledgehammer. Rewrite: "Verified boot is needed for any product handling user data, payment credentials, certificate-based identity, or DRM. Without it, an attacker with physical access can replace U-Boot, boot a custom kernel that bypasses authentication, or extract storage encryption keys."
- > "With HAB + dm-verity, even physical access leaves the device unbreakable (modulo silicon-level attacks)."
  - "Unbreakable" is dangerous marketing. Rewrite: "With HAB plus dm-verity, the device resists most physical-access attacks. Silicon-level attacks (decap, side-channel, fault injection) remain possible but require expensive equipment."
- > "**the chain is "the ROM checks U-Boot's signature against the SRK hash in eFuses; verified U-Boot checks the kernel + DT's signature; verified kernel mounts a dm-verity'd rootfs whose hash matches; the user app can use OP-TEE to access secrets that no part of Linux can read". Break any link → all subsequent links lose meaning. Get key management wrong (lose the private key, expose it) and you either brick the fleet or hand attackers full control. This chapter is short on the easy bits and long on the "you'll regret skipping this" bits.**"
  - 90-word bolded run-on; ESL-hostile + sledgehammer close. Reformat as numbered prose chain + a separate line on key management.
- > "This is a ritual, not a checkbox:"
  - Cute. Acceptable. Keep.
- > "For prototyping: simpler procedure (keys on your laptop, no HSM). For production: take the ceremony seriously. Lose the keys → cannot ship a single firmware update ever; the fleet is permanently frozen at whatever was last signed."
  - "Cannot ship a single firmware update ever; the fleet is permanently frozen" is correct but doom-laden. Tone down once: "If you lose the keys, you can't ship firmware updates. Whatever was last signed is what the fleet runs forever."
- > "**This is irreversible**."
  - Fine. Earned.
- > "Real TAs: key storage (the secret stays in Secure World; only operations like sign/verify are exposed), secure storage of credentials, attestation (proving to a server that "the firmware running here is what you expect")."
  - Triplet of TA examples with nested parentheticals. Reformat as a small list.

### ESL readability
- > "**SRK (Super Root Key)**: a 4096-bit RSA public key. The hash of the SRK is **blown into eFuses** during manufacturing."
  - Fine. The bold on "blown into eFuses" is acceptable because it's the once-per-chip irreversible operation.
- > "Each request is an SMC → kernel context switch → OP-TEE serves request → SMC return."
  - Arrow chain. Fine for engineer-whiteboard tone. Keep.
- > "ARMv7-A's TrustZone divides the CPU into two "worlds":"
  - Fine.
- > "After Linux boots to a known-good state (a service reaches "active"), it signals "boot succeeded" via env var."
  - Nested quotes; ESL reader stalls. Rewrite: "Once Linux reaches a known-good state — a specific service reports active — it signals boot success via a U-Boot environment variable."
- > "Cannot OTA. The fleet is permanently bricked at whatever was last signed."
  - Repeat from intro. Pick one place to make the point.

### Needs more explanation
- **§124.2 SRK / CSF / CST acronyms are introduced in one breath.** Worth a one-table layout: SRK = Super Root Key (public, hashed into fuses); CSK = Code Signing Key (the actual day-to-day signing key, chained from SRK); CSF = Command Sequence File (binary blob telling the ROM what to verify and where); CST = Code Signing Tool (NXP host-side tool that produces a CSF). The current text mixes these.
- **§124.4 the CSF-text format is one of the hardest bits in the chapter.** "Blocks = 0x877FF400 0x00000000 0x00065F60 "u-boot-ivt.imx"" — three magic numbers. Spell out: load_address, offset_in_file, length, filename. One sentence per field. Without this the reader copies it blindly and gets opaque CST errors.
- **§124.5 HAB closure — the `fuse prog 0 6 0x2` is shown but the fuse map isn't.** Bank 0, word 6, bit 1 = HAB_TYPE. Show the OCOTP layout from the reference manual. Also mention: many vendors use a *separate* SRK_REVOKE fuse so individual SRKs can be revoked without nuking the chip.
- **§124.7 dm-verity hash tree mechanics is sketched in one sentence.** This is the hard concept: each data block is hashed; those hashes are grouped into hash-blocks; hash-blocks are hashed into the next level; recursively until one root hash. On read, verity recomputes the path from block to root and rejects if any hash mismatches. Without this picture the reader doesn't know why dm-verity needs a separate hash partition.
- **§124.8 TrustZone primer is light on the architecture.** SCR.NS bit, NSACR, Secure Monitor Mode — these aren't named. For a 6 YOE MCU dev who knows Cortex-M (which lacks TrustZone except on Armv8-M), the conceptual gap is: Cortex-A's TrustZone is enforced via the NS (Non-Secure) bit in the SCR register, which propagates to every memory transaction and selects the relevant peripheral access. A diagram of the SCR.NS bit flowing through AXI/AHB transactions would land the concept.
- **§124.10 the hello-world TA is shown but the TA build/sign step is missing.** TAs are signed with a TA signing key (separate from the SRK/CSK chain in U-Boot's HAB). Mention this — readers will be confused about why a TA needs *another* set of keys.

---

## Ch 125 — Field updates

### AI wording / sledgehammer / buzzwords
- > "no shipping product survives without updates."
  - Absolutist. Rewrite: "Most shipping products need a way to deliver updates."
- > "Get the OTA architecture right and you ship one update per week, customers love you. Get it wrong and one bad update wipes out a quarter's revenue."
  - "Wipes out a quarter's revenue" — drop the dramatization. Rewrite: "Get the OTA architecture right and you can ship updates weekly. Get it wrong and one bad update can disable thousands of devices in the field."
- > "**A/B is the universal pattern: two rootfs partitions; the running kernel mounts one; an update writes to the other; bootloader switches to the new one on next reboot; if the new one fails to boot to a "we're good" marker within a deadline, bootloader reverts to the old one**"
  - 50-word bolded run-on with five semicolons. Bullet list it.
- > "The complexity is everywhere else: who hosts the update bundle? how is it signed (Ch 124's keys)? how does the device know an update is available? what if the user's WiFi drops mid-download? how do you stage rollouts (10 % → 50 % → 100 %)? these systems handle all of that."
  - Five rhetorical questions in one sentence, then a sales pitch close. Rewrite as a bullet list of "the open questions:" then "these systems address all of them."
- > "Each has a trade-off:"
  - Fine. Concise.
- > "Use HSMs; rotate."
  - Two-word imperatives. Fine; matches the engineer-whiteboard tone.

### ESL readability
- > "RAUC verifies the signature against the keyring, writes to the inactive slot, updates bootloader env, reboots."
  - Four-comma chain. Slightly long for ESL. Acceptable.
- > "For staged rollouts: serve different `latest.json` to different device IDs (canary 10 %, then 50 %, then 100 %)."
  - Fine.
- > "For privacy: device authenticates via client TLS cert (each device has a unique cert provisioned at manufacturing time); server checks per-device permissions."
  - Semicolon then nested-parenthetical. Rewrite: "For privacy, each device authenticates with its own client TLS certificate, provisioned at manufacturing time. The server checks per-device permissions."
- > "A 1 GB rootfs is too big to push over LTE every week. **casync** (Lennart Poettering's tool) chunks images; only changed chunks transfer:"
  - Fine. ESL-clear.
- > "For products with non-uniform update needs (e.g., the rootfs rarely changes but the FPGA config updates monthly), SWUpdate wins."
  - Fine.

### Needs more explanation
- **§125.2 A/B mechanics — `BOOT_X_LEFT` countdown is the key safety primitive but is glossed over.** Worth a worked example: device boots A, mark-good not called → next reboot, A_LEFT decrements to 2; another bad boot, 1; another, 0; bootloader fails to A and tries B. Show this state machine; otherwise the env-var dance reads as magic.
- **§125.3 the U-Boot scripting is shown but the `if test "${BOOT_ORDER%%* *}"` syntax is opaque.** That's a U-Boot environment variable substitution: `%%* *` strips everything from the first space onward, leaving the first slot in the order. Explain — it's the kind of detail that bites readers who try to modify the script.
- **§125.5 casync chunking — the chunk-deduplication mechanism isn't explained.** It's content-defined chunking via a rolling hash (like rsync's chunking but better at unaligned changes). Two builds of the rootfs differing only in `/usr/bin/myapp` share 99 % of chunks. One paragraph on this; otherwise "5-50 MB instead of 500 MB" sounds like magic.
- **§125.8 boot-success detection — the "watchdog reverts" path is hand-waved.** The mechanism: at boot, U-Boot has set a watchdog timer (e.g., 60 s); userspace's "mark-good" script disables it; if the script never runs, watchdog resets the device; on next boot, U-Boot sees `BOOT_LEFT` decremented and falls back. Spell this out — it's the safety chain that makes A/B reliable.
- **§125.9 lab #7 "force a bad update" — needs the actual test mechanism.** A bundle whose `myapp` crashes doesn't necessarily prevent boot-completion (other services may report good). Show the *real* test: a bundle where the kernel panics during init, or where mark-good is removed from systemd's start chain. Otherwise the lab can pass while the rollback path isn't actually exercised.

---

## Ch 125A — VSCode + gdbserver

### AI wording / sledgehammer / buzzwords
- > "**`launch.json` joining them**"
  - "Joining them" is wishful. Concrete: "`launch.json` ties them together."
- > "Asking them to learn `gdb` tui mode is a barrier they shouldn't have to clear."
  - Slightly preachy. Rewrite: "Forcing them to learn gdb's tui mode just to set a breakpoint is unnecessary."
- > "The cost is one-time `launch.json` setup; the payoff is every subsequent debug session."
  - Salesy. Rewrite: "Setting up `launch.json` once pays back every debug session after."
- > "**VSCode's debug UI is a shell around gdb; the `launch.json` is its config; you tell it which gdb binary to use, what binary to debug, what host:port to connect gdbserver on, and where the source tree lives**"
  - 40-word bolded run-on. Reformat: "VSCode's debug UI is a wrapper around gdb. `launch.json` configures it. You set: which gdb binary, which binary to debug, where gdbserver listens, and where the source tree lives."
- > "The trick is `c_cpp_properties.json`: point IntelliSense at the **target's** sysroot headers, not the host's; otherwise "Go to Definition" finds your laptop's `stdio.h` instead of the cross-compiled one."
  - "The trick is" again. Rewrite: "The non-obvious part is `c_cpp_properties.json`. It must point IntelliSense at the target's sysroot headers, not the host's. Otherwise 'Go to Definition' finds your laptop's `stdio.h`, not the cross-compiled one."
- > "With both files right, IDE-style debug + perfect Go-to-Definition makes embedded debugging as productive as desktop development."
  - "Perfect" is overstated; soften: "With both files right, IDE-style debug and accurate Go-to-Definition make embedded debug feel close to desktop."
- > "It's not a debugger; not an editor for serious projects. But for "I'm reading the kernel source and want to navigate quickly," nothing beats it."
  - "Nothing beats it" — keep, it's an honest endorsement and not buzzword-rotten. Acceptable.

### ESL readability
- > "Plus a sidebar on **Source Insight** for read-only kernel-source navigation (it's old but still the fastest tool for that one task)."
  - "Sidebar" is editor's jargon for "aside." ESL-friendly: "Plus a short note on Source Insight, an old commercial editor that's still the fastest tool for read-only kernel-source navigation."
- > "Critical: without this, IntelliSense reports cross-compile-time errors that don't actually exist (because it thinks you're targeting x86 but ARM-only macros are not defined)."
  - The parenthetical is the actual explanation; promote it. "Without this, IntelliSense reports errors that aren't real: it thinks you're compiling for x86, so ARM-only macros are undefined and code inside `#ifdef __arm__` looks dead."
- > "**`gdb-dashboard`** — terminal alternative if you decide to leave VSCode."
  - Fine.
- > "**`gdbserver` is small (~100 KB statically linked); no debug-info needed on the target.**"
  - Reads as a parenthetical aside. Move to its own line: "`gdbserver` is small — about 100 KB statically linked — and needs no debug info on the target."

### Needs more explanation
- **§125A.3 the `set sysroot` value is hardcoded to a Yocto recipe-sysroot path.** This is the wrong path for most readers, who'll have either a Buildroot SDK at `output/host/arm-buildroot-linux-gnueabihf/sysroot/` or a crosstool-NG sysroot at `~/x-tools/arm-linux-gnueabihf/arm-linux-gnueabihf/sysroot/`. Mention all three patterns. Also: the Yocto path embeds the recipe name (`myapp/1.0-r0`), which changes with version bumps — fragile, mention how to use `populate_sdk` output instead.
- **§125A.5 multi-target — for a 6 YOE MCU dev, the question is "how do I attach to a *running* process?" rather than spawn a new one.** Show the `--attach <pid>` flow with VSCode (`"request": "attach"` instead of `"launch"`, plus `"processId"`). Currently the chapter only shows launch.
- **§125A.6 kernel module debugging via KGDB is shown in one config block.** This is *very* hard and the section under-explains. Spell out: KGDB needs `kgdboc=ttymxc0,115200 kgdbwait` on the cmdline; the target serial cable becomes the gdb transport, displacing the console; VSCode connects to a `socat` bridge that exposes the serial as a TCP port. Without this the example doesn't actually work for the reader.
- **§125A.9 pitfalls is good but missing the "MI parser" gotcha.** VSCode talks to gdb via MI (Machine Interface). Cross-gdb versions that don't fully implement MI cause silent breakpoint-not-set failures. Mention: if breakpoints set silently but never hit, try a newer cross-gdb (the crosstool-NG one built in Ch 122 is usually fine; an old Ubuntu gdb-multiarch may not be).

---

## Ch 126 — Closing

### AI wording / sledgehammer / buzzwords
- > "You have, in 125 chapters, gone from "I am an MCU engineer who has never used Linux" to "I can bring up a custom i.MX6ULL board with mainline U-Boot + mainline Linux + a hand-built rootfs + a real driver + secure boot + CI + OTA." That's not a small feat."
  - Inspirational-poster voice. Rewrite shorter: "In 125 chapters you've gone from MCU engineer to someone who can bring up a custom i.MX6ULL board with mainline U-Boot, Linux, a hand-built rootfs, drivers, secure boot, CI, and OTA. That's a lot of ground."
- > "This chapter is the bridge from here to the rest of your career as an embedded-Linux engineer."
  - "Bridge from here to the rest of your career" — graduation-speech cliche. Rewrite: "This chapter points to what to read and do next."
- > "The mental model it gives you is correct; just check current APIs in the kernel source when implementing."
  - Fine. Concrete advice.
- > "**free, comprehensive, current, and license-permissive**"
  - Four-adjective bold. Drop bold. The list is fine.
- > "The single best free-online resource for further study."
  - Sledgehammer "single best." Rewrite: "Probably the best free online resource for further study."
- > "Reading LWN weekly is *the* way to absorb kernel-development culture and stay current."
  - Italics + "*the* way" superlative. Rewrite: "Reading LWN weekly is one of the most reliable ways to absorb kernel-development culture and stay current."
- > "200 pages total; every new contributor should read it once."
  - Fine. Concrete imperative.
- > "Lurk for a month before posting."
  - Fine. Clear.
- > "Most importantly: now you have the **vocabulary** to read the kernel source, the **frameworks** to think about new problems, the **debugging instincts** to solve them, and the **community connections** to learn faster than you could alone."
  - Bold-quadrilateral, motivational-poster prose. Rewrite without the bold rhythm: "Most importantly, you now have the vocabulary to read kernel source, the frameworks to think about new problems, the debugging instincts to solve them, and the community connections to learn faster than alone."
- > "Build something. Ship it. Watch a customer use it for years. *That* is embedded Linux."
  - Three-fragment closer with italicized "*That*". This is the book's closing line; you may *want* it punchy. Acceptable as a closing flourish — but the italics on "That" is unnecessary. Drop them: "Build something. Ship it. Watch a customer use it for years. That is embedded Linux."
- > "Good luck. Send your first patch."
  - Fine. Short closer earns its keep.

### ESL readability
- > "Five books / sites that take you from where this book ends:"
  - Slash-list. ESL-friendly: "Five books and sites that pick up where this book ends:"
- > "Pay subscription ($10/month) is worth every cent if you work with Linux full-time."
  - Sales pitch. Rewrite: "A paid subscription ($10/month) is worth it if you work with Linux full-time."
- > "Bring questions; the community is welcoming."
  - Fine. Clear.
- > "Cultivate the soft skills — talking to product managers, defending engineering trade-offs."
  - Em-dash + parallel verbs. Rewrite: "Develop soft skills: talking to product managers, defending engineering trade-offs."
- > "you'll never design boards, maybe, but you'll read 1000s."
  - The "maybe" is awkward mid-sentence. Rewrite: "You may never design boards, but you'll read thousands."

### Needs more explanation
- **§126.1 #1 — LDD3 caveats need more pointing.** Beyond "specific APIs are dated," some chapters (USB, PCI) are now substantially outdated; the char-device, sleeping, locking, memory chapters are still excellent. A two-sentence "what's still good vs what's stale" guide would save the reader days of confusion when they hit deprecated APIs.
- **§126.4 path A / B / C — each is one paragraph.** Path A (Kernel hacker) — give one concrete first step: pick a driver in the IIO or GPIO subsystem and read every patch to its file in the last year. Mention `git log --follow drivers/iio/...`. Path B (Product engineer) — name one to-do: build a board with everything in Part VIII chained together. Path C (Embedded security) — mention concrete reading: Boneh's Coursera, plus the *ARM Architecture Security Reference Manual* for TrustZone-Av8.
- **§126.5 "skills outside Linux" — Rust is mentioned but the kernel's Rust-for-Linux status as of 2026 isn't.** As of 6.6 LTS, Rust is in mainline but mostly for new drivers. For a reader picking what to learn, this matters: Rust for new kernel work, C for everything else, C++ for application stacks. One sentence on the current state.





---


