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

## Ch13 — CCM clocks
### AI wording / sledgehammer / buzzwords
- > "**four-layer clock tree** from Chapter 5 made concrete — XTAL → PLL → root mux+divider → CCGR gate."
  - Em-dash + recap rhetoric. Rewrite: "the four-layer clock tree from Chapter 5: XTAL → PLL → root mux+divider → CCGR gate."
- > "Once you can trace a peripheral's frequency through these four hops, you can predict and debug any clocking issue."
  - "Any" is overreach. Rewrite: "Trace a frequency through these four hops and most clock bugs become obvious."
- > "We are running U-Boot's preamble by hand."
  - Fine, but the previous sentence already said "what U-Boot will set up in Chapter 19." Drop one.
- > "Software-reads-software-writes is the easiest check to lie to itself. For confidence, measure."
  - Two clipped sentences for a punchline. Rewrite: "A read-back of what you just wrote can lie to itself. For confidence, measure the clock externally."
- > "the engineering insight that distinguishes you from someone who only ever uses eval kits."
  - Flattery cliché. Rewrite: "the experience that separates you from someone who only uses vendor eval kits." Or just cut.
- > "Block out an afternoon."
  - Fine; engineer voice.

### ESL readability
- > "Each PLL has `SET` (`+0x4`), `CLR` (`+0x8`), and `TOG` (`+0xC`) sibling addresses that let you set/clear/toggle bits atomically without read-modify-write."
  - Long, with a triplet. Rewrite: "Each PLL also has three sibling addresses: `SET` (`+0x4`), `CLR` (`+0x8`), and `TOG` (`+0xC`). Writing to them sets, clears, or toggles bits atomically (no read-modify-write needed)."
- > "The encoding 'DIV_SELECT' is the *raw divider value*, so we write 58."
  - Slightly awkward. Rewrite: "DIV_SELECT is the raw divider value, so we write 58 directly."
- > "If you don't wait, subsequent reads/writes can race the clock change. Symptom: works on the 5th run, fails on the 6th."
  - Fragment style. Rewrite: "If you skip the wait, the next reads or writes can race the clock change. Symptom: the program works on the 5th run, fails on the 6th."
- > "At 696 MHz a million-iteration empty loop should take ~5 million cycles (roughly 7 ns per iteration on a Cortex-A7). At 396 MHz, the same loop count takes the same *cycles* — but with a slower clock, the wall-time it consumes is longer."
  - Long, em-dash at the punchline. Rewrite: "At 696 MHz a million-iteration empty loop takes ~5 million cycles (~7 ns per iteration). At 396 MHz the loop takes the same number of cycles, but each cycle is longer, so the wall-clock time doubles."
- > "the scope and the GPIO drive strength will not produce cleanly; you'll see a degraded waveform but the *period* is measurable."
  - Semicolon + missing object after "produce". Rewrite: "The scope and the GPIO drive strength cannot reproduce that cleanly. You see a degraded waveform, but the period is still measurable."

### Needs more explanation
- §13.2 PLLs and PFDs: the chapter shows PFD = `f_PLL × 18 / FRAC` and lists FRAC = 12..35, but never explains *why* 18. One sentence: "A PFD takes the PLL output, multiplies by 18 in hardware, then divides by FRAC (range 12..35). This gives ~0.5×–1.5× the PLL frequency in fine steps." Without this, the formula reads like a magic number.
- §13.3 "handshake-in-progress": the prose says wait for `CCM_CDHIPR` to clear "the corresponding busy bit," but the lab code uses `(1u << 0) | (1u << 1) | (1u << 2)` without naming the three fields. Add: "bit 0 = AHB_PODF busy, bit 1 = AXI_PODF busy, bit 2 = PERIPH_CLK_SEL busy. Each divider you change has its own busy bit in CDHIPR; OR them together and wait for all to clear."
- §13.7 "MMDC clock = 396 MHz makes the conversion factors easy: 1 cycle = 2.525 ns." Worth a line on the inverse: "If MMDC ran at 528 MHz, 1 cycle = 1.894 ns; same DDR timings then encode to different cycle counts in MDCFG0/1/2." Reinforces why this chapter must precede Ch14.

## Ch14 — DDR3 init
### AI wording / sledgehammer / buzzwords
- > "Solving it once yourself collapses several 'magic' layers down to 'I know what those registers do.'"
  - AI mottoism with quoted-phrase rhetoric. Rewrite: "Solving it once removes the 'magic' from a layer you will otherwise trust forever."
- > "the **JEDEC initialization sequence** for DDR3 — universal — and the **MMDC register groups** that implement it — i.MX-specific. Understanding both means you can port to a different DRAM part or different SoC without panic."
  - Two parenthetical em-dashes inside one sentence. Rewrite: "The JEDEC DDR3 init sequence is universal across vendors. The MMDC register groups are i.MX-specific. Know both, and you can port to a different DRAM part or a different SoC."
- > "Set an afternoon aside."
  - Echoes Ch13's "block out an afternoon." Pick one chapter for the phrase.
- > "the diagnostic for 'wrong value' is usually 'DRAM doesn't work.'"
  - Quote-phrase rhetoric. Rewrite: "the only diagnostic for a wrong value is 'DRAM doesn't work.'"
- > "When DRAM doesn't work, you cannot `printf` from DRAM, cannot load test patterns into DRAM, cannot do much."
  - Triplet with diminishing returns. Rewrite: "When DRAM doesn't work, you cannot `printf` from it, load test patterns into it, or do much else."
- > "**The first thing you do in this chapter is open your specific DDR chip's datasheet.** If you guess timings, the DRAM may 'kind of work' — pass a 1 MB memtest, fail at 16 MB — which is the worst kind of bug."
  - Em-dash inside em-dash, plus "worst kind of bug" cliché. Rewrite: "Open your DDR chip's datasheet first. Guessed timings produce the worst class of bug: the DRAM passes a 1 MB memtest and fails at 16 MB."
- > "Don't memorize them; learn the *groups*."
  - Fine; engineer voice. Keep.
- > "**Use it on every new board.** Even if you use values from a vendor BSP, validate with the tool."
  - Fine.
- > "Now the trick."
  - Twee. Rewrite: "Now relocate."

### ESL readability
- > "if you have only ever worked with SRAM (on Cortex-M parts with built-in 64 KB-2 MB SRAM) or with the bus-controller view of SDRAM, here is the family tree in 60 seconds:"
  - Long compound with nested parenthetical. Rewrite: "Most Cortex-M parts have 64 KB to 2 MB of built-in SRAM, and many SoCs expose SDRAM through a bus controller. Here is the rest of the family tree in 60 seconds."
- > "DDR datasheets often summarize three of the most-cited timings as a triple **'CL-tRCD-tRP'** (in clock cycles). A '13-13-13 DDR3-1600' part means CL = 13 clocks, tRCD = 13 clocks, tRP = 13 clocks at a 1600 MT/s rate. Tighter (smaller) numbers are better; for our 400 MHz cell clock (= 2.5 ns per cycle), 13 clocks = 32.5 ns of latency."
  - Semicolon, parenthetical inside parenthetical. Split: "Datasheets often summarize three of the most-cited timings as a triple, **'CL-tRCD-tRP'**, in clock cycles. A '13-13-13 DDR3-1600' part has CL = tRCD = tRP = 13 clocks at 1600 MT/s. Smaller numbers are better. At our 400 MHz cell clock (2.5 ns per cycle), 13 clocks = 32.5 ns of latency."
- > "Both chips receive the same address and command; one drives bus bits [7:0], the other [15:8]."
  - Semicolon. Rewrite: "Both chips receive the same address and command. One drives bus bits [7:0]; the other drives [15:8]." (or keep one semicolon; the original has both.)
- > "The order in which we write these matters less than you'd think, with one important exception: **MDSCR (the command register)** is how we send DDR3 commands to the chip (load mode register, ZQ cal, refresh, etc.). It must be used at specific points in the sequence; otherwise it is one register among many."
  - Long sentence with two parentheticals and a semicolon. Split: "The write order for most of these matters less than you'd think. The exception is **MDSCR**, the command register. We use MDSCR to send DDR3 commands (load mode register, ZQ cal, refresh, etc.), and it must be written at specific points in the init sequence."
- > "They were calibrated on someone else's board. Use them as a starting point; re-validate."
  - Semicolon. Rewrite: "They were calibrated on someone else's board. Use them as a starting point and re-validate on yours."
- > "Hairdryers are fine. Heat guns are not. Be careful in the temperature lab."
  - Three short fragments. Rewrite: "A hairdryer is fine for the temperature lab; a heat gun is too hot and can destroy the chip."

### Needs more explanation
- §14.6 The JEDEC sequence: steps 1–10 are listed, but the *reason for each delay* is not explained. Add one paragraph: "The 200 µs after reset is for the DRAM's internal PLL to stabilize. The 500 µs after CKE is JEDEC-mandated and gives the chip's clock-domain logic time to lock. The DLL reset in MR0 then re-trains the chip's internal data-path timing." Reader sees the sequence as physics, not magic.
- §14.6 Mode registers (MR0/MR1/MR2/MR3): the chapter gives bit fields but never says *what each MR controls* at a paragraph level. Add: "MR0 = operating mode (burst, CL, write recovery, DLL reset). MR1 = drive/ODT/DLL enable. MR2 = CWL + Rtt_WR + auto-self-refresh. MR3 = MPR (multi-purpose register) mode; usually 0."
- §14.8 Calibration: the three calibrations (write leveling, DQS gating, read/write delay) get one sentence each. For someone who has never seen DDR3 calibration: add a half-page explaining *what is being aligned to what* in each step. The current text is correct but very compressed for an ESL reader meeting the topic for the first time.
- §14.10 OCRAM → DRAM relocation: the `entry_t entry = (entry_t)(0x80100000 + ((uint32_t)main - 0x00907400));` line is doing fragile pointer arithmetic that assumes `main` lives at a specific offset. Worth a sentence: "This assumes `main` is at offset (its address in OCRAM) − (OCRAM load address). A linker-script `__start_dram` symbol pointing at the DRAM copy of `main` would be cleaner; we do not introduce it until Ch18A's BSP refactor."

## Ch15 — Exceptions and the GIC
### AI wording / sledgehammer / buzzwords
- > "**two-stage IRQ flow** — the GIC routes to the CPU; the CPU vectors to your handler; the handler reads the GIC for the IRQ ID, dispatches, writes EOI. Once you can draw this without looking, every other A-profile system makes sense."
  - Triplet + final aphorism. Rewrite: "the two-stage IRQ flow: the GIC routes the IRQ to the CPU, the CPU vectors to your handler, and the handler reads the GIC for the IRQ ID, dispatches, and writes EOI. Internalize this diagram and every A-profile system feels familiar."
- > "Linux's `arch/arm/kernel/entry-armv.S` is several hundred lines of this boilerplate, all of it correct, all of it terrifying the first time you read it."
  - Triplet-flourish. Rewrite: "Linux's `arch/arm/kernel/entry-armv.S` is several hundred lines of the same pattern. Correct, but intimidating to read the first time."
- > "The pattern is identical in every GIC-based system, including the kernel."
  - Fine; useful payoff.
- > "Eleven steps. Every Linux IRQ in user space follows the same pattern."
  - Two-sentence punchline rhythm. Acceptable, but the same closing tic appears across chapters; consider varying.
- > "polling we have used so far works for hello-world; it falls apart the moment more than one peripheral needs attention."
  - Semicolon. Rewrite: "Polling works for hello-world. It falls apart the moment more than one peripheral needs attention."

### ESL readability
- > "sub     lr, lr, #4              @ adjust LR_irq to point at the *interrupted*
  @ instruction (so RFE re-executes it... no, it
  @ resumes correctly with this -4 fixup)"
  - The "...no, it" mid-comment correction reads like the author thinking out loud. Rewrite as one clean comment: "@ LR_irq = PC_interrupted + 4 on IRQ entry. Subtract 4 so RFE resumes at the interrupted instruction."
- > "`ldr pc, =sym` is the universal far-branch idiom on ARM."
  - "Universal" overreach. Rewrite: "`ldr pc, =sym` is the standard ARM idiom for a far branch."
- > "The IRQ exception model has an architectural offset of 4 for IRQ (4 for IRQ, 8 for prefetch abort, 0 for SVC, etc., per RM table). Subtracting 4 gives us the correct address to return to."
  - "Has an architectural offset of 4 for IRQ (4 for IRQ" repeats itself. Rewrite: "ARM defines a fixed return offset per exception: 4 for IRQ, 4 for prefetch abort, 8 for data abort, 0 for SVC. For IRQ we subtract 4 to land back on the interrupted instruction."
- > "The CPU put `PC_interrupted + 4` in `LR_irq`."
  - Fine, but check: the actual offset for IRQ is +8 in ARM mode (+4 in Thumb). The chapter elsewhere says "subtract 4." Either the prose or the math is off; verify against the ARMv7-A reference and clarify which mode (ARM vs Thumb) we are assuming. As written this is a subtle source of "works for me / not for you" bugs.
- > "`cps     #0x12                    @ mode = IRQ (no mask change)`"
  - The comment "no mask change" is helpful, but the previous code used `cpsid i, #0x13` which *does* change masks. Add one line of prose right above: "`cps #N` changes only the mode bits; `cpsid i, #N` changes mode *and* sets the I bit; `cpsie i, #N` clears it."
- > "we have one core."
  - Fine.

### Needs more explanation
- §15.1 "No auto-stacking. Your handler must save and restore registers itself." — for a Cortex-M dev this is the *single biggest* mental shift. Worth a full paragraph: "Cortex-M's NVIC stacks 8 registers in hardware in 12 cycles. ARMv7-A has no such mechanism. On entry to IRQ mode, the CPU only banks SP and LR, and saves CPSR into SPSR_irq; everything else is your problem. This is why every A-profile RTOS has an asm prologue/epilogue around C interrupt handlers."
- §15.2 "VBAR" — mention that VBAR did not exist before ARMv7 (it's a security-extensions extension that became mainstream). Otherwise the reader who has read older ARM books will wonder why high/low vectors were ever a thing.
- §15.3 `srsdb sp!, #0x12`: the chapter says "store {LR, SPSR} to the IRQ-mode stack pointer." It does *not* explain that the mode operand to SRS picks *which mode's SP* to push to (and that we are using IRQ mode's SP because we have not yet switched away). One sentence: "SRS pushes to *the named mode's* SP, regardless of the current mode. Here we're still in IRQ mode anyway, so it pushes to SP_irq. The encoded mode bits select that SP."
- §15.5 "PPI/SGI are fixed" — the chapter mentions SGIs (0–15) and PPIs (16–31) once each but never defines them. One sentence: "SGI = Software-Generated Interrupt (inter-CPU IPI). PPI = Private Peripheral Interrupt (per-CPU, e.g., the generic timer). SPI = Shared Peripheral Interrupt (everything else)."
- §15.6 `c_irq_dispatch` reads IAR and writes EOI. Worth explaining the "active" state machine: "Reading IAR moves the IRQ from pending to active. Writing EOIR moves it from active to inactive (or pending again, if the source is still asserting)." Otherwise the EOI step looks ceremonial.

## Ch16 — Timers
### AI wording / sledgehammer / buzzwords
- > "**separation of concerns** — EPIT for periodic interrupts (the kernel's tick source), GPT for free-running time (the kernel's clocksource). Linux uses two devices for the same reason; understanding the split here makes Linux's `arch_timer` and `clocksource` framework familiar."
  - "Separation of concerns" is buzzword-adjacent. Em-dash + semicolon. Rewrite: "We use two timers because Linux does: GPT as a free-running counter (clocksource), EPIT for periodic interrupts (tick source). Seeing the split here makes Linux's `arch_timer` and `clocksource` framework easier later."
- > "before we touch the MMU or write any real drivers, we need timing. Every scheduler, every protocol stack, every 'wait at least N ns then check again' needs a primitive."
  - Triplet. Rewrite: "Before we touch the MMU or write real drivers we need timing primitives. Schedulers, protocol stacks, and 'wait at least N ns then check again' all need them."
- > "Convenient."
  - Mottoism. Cut, or expand: "Convenient: each tick equals 1 microsecond."
- > "the `udelay` is now precise to within a microsecond (limited by the spin-loop's reaction time, which on a 696 MHz core is sub-microsecond)."
  - Parenthetical inside a precise claim. Rewrite: "`udelay` is now precise to within 1 microsecond. On a 696 MHz core the spin-loop reaction adds well under a microsecond."
- > "Use PMU for **how efficient is this code on this CPU**; use GPT for **how long does this real-time operation take**. They answer different questions."
  - Bold-phrase rhetoric. Rewrite: "Use PMU to measure cycles (how efficient is the code on this CPU). Use GPT to measure wall time (how long the real-time operation took). They answer different questions."

### ESL readability
- > "Two timers, two jobs"
  - Fine as heading.
- > "GPT_PR is 'divisor minus 1'. For 66 MHz → 1 MHz, write 65. Not 66."
  - Fragmented. Rewrite: "GPT_PR holds *divisor minus 1*. To go from 66 MHz to 1 MHz the divisor is 66, so we write 65."
- > "**`(gpt_now_us() - start) < us`** uses unsigned subtraction modulo 2^32. This correctly handles counter wraparound for delays shorter than 2^32 µs (~71 minutes). For longer delays, extend to 64-bit accumulation."
  - Three sentences, the middle one is dense. Rewrite: "**`(gpt_now_us() - start) < us`** uses unsigned subtraction, which wraps cleanly modulo 2^32. This handles counter rollover correctly for any delay shorter than 2^32 µs (~71 min). For longer delays accumulate into a 64-bit value."
- > "EPIT_LR vs EPIT_CMPR. LR is the reload value; CMPR is the compare threshold (usually 0). Don't swap."
  - Fragment + semicolon. Rewrite: "EPIT_LR vs EPIT_CMPR: LR is the reload value, CMPR is the compare threshold (usually 0). Don't swap them."

### Needs more explanation
- §16.2 `FRR` (free-running) vs the alternative (restart mode): one extra sentence explaining the alternative would set up the reader's mental model. "If FRR = 0, the counter resets to 0 every time it matches an output-compare. Free-running mode (FRR = 1) lets the counter roll past matches, which is what a clocksource needs."
- §16.3 EPIT_CR fields: the code names CLKSRC, IOVW, PRESCALER, RLD, OCIEN, ENMOD, EN, with field positions, but never explains *what* IOVW does. Add: "IOVW = 1 means a write to EPIT_LR takes effect immediately; with IOVW = 0 the new value only loads at the next counter underflow. We want immediate, so we set it."
- §16.5 PMU CCNT: code uses MRC `p15, 0, %0, c9, c13, 0` but the chapter never says CCNT counts at the *processor* clock, not the bus clock. Add: "CCNT increments once per CPU cycle. After Ch13 the CPU runs at 696 MHz, so 1 CCNT tick ≈ 1.437 ns." The chapter does say "cycle-precise" but never anchors what a cycle costs in ns.
- §16.3 The line "GIC SPI ID for EPIT1 = 88 on i.MX6ULL (RM Table 3-1). Verify." — explain the +32 offset once: "EPIT1 is SPI #56 in RM Table 3-1, which is GIC INTID 32 + 56 = 88." (Ch15 made this point for UART1; reinforce it here.)

## Ch17 — MMU and caches
### AI wording / sledgehammer / buzzwords
- > "the MMU and caches are the only remaining 'magic' between us and Linux. Once you can turn them on yourself, every kernel page-table operation looks like a variation on what you just did."
  - "Magic" quote-phrase plus closing aphorism. Rewrite: "The MMU and caches are the last hardware blocks Linux abstracts from you. Turn them on once by hand and every kernel page-table operation looks like a variation on this."
- > "short-descriptor format — a 4096-entry first-level table that maps the 4 GiB address space in 1 MiB sections, with per-section permissions and memory attributes. This is the only translation format we need; LPAE (3 levels, 40-bit PA) is overkill for our 512 MiB DRAM."
  - Em-dash + semicolon stack. Rewrite: "the short-descriptor format: a 4096-entry first-level table covering 4 GiB in 1 MiB sections, with per-section permissions and memory attributes. LPAE (3 levels, 40-bit PA) is overkill for our 512 MiB DRAM."
- > "Roughly an 8× speedup on the memtest. The exact ratio depends on access pattern; sequential memcpy can hit 10–15× with both caches on."
  - Semicolon. Rewrite: "Roughly an 8× speedup on the memtest. The exact ratio depends on the access pattern. Sequential memcpy can hit 10–15× with both caches on."
- > "This is one of the most insidious bugs in low-level code."
  - Cliché. Rewrite: "This is one of the hardest bugs to diagnose in low-level code."
- > "Our way is harder to misconfigure."
  - Fine; engineer voice.
- > "The 10× factor is real and is the reason Linux insists on having caches before doing anything useful."
  - Slight overreach ("insists on", "anything useful"). Rewrite: "The 10× difference is why Linux brings caches up early in arch_setup."

### ESL readability
- > "**`__attribute__((aligned(16384)))`** ensures the table starts at a 16 KiB boundary, which TTBR requires. If you skip this, the high bits of the table base address get truncated and your MMU points at garbage."
  - Mostly fine. Tighten the second sentence: "Skip it and TTBR drops the low 14 bits silently, leaving your MMU pointing at garbage."
- > "**Order matters at enable time.** Invalidate caches *before* enabling them, otherwise stale lines from before-MMU contaminate the cache."
  - Awkward "otherwise stale lines... contaminate the cache." Rewrite: "Invalidate the caches *before* enabling them. Otherwise pre-MMU stale lines stay valid and corrupt your data."
- > "The granularity is one cache line (64 bytes on Cortex-A7). To clean a 4 KB buffer:"
  - Fine.
- > "If you accidentally map a peripheral region as Normal Cacheable: [bullet list] This is one of the most insidious bugs in low-level code. Symptom: code works on a board where MMU is off, breaks the moment caches are on. Cause: a peripheral region was wrongly marked cacheable."
  - The Symptom/Cause two-fragment pattern is fine, but Ch17 stacks it with the earlier triplet. Vary: "Symptoms: it works with MMU off and breaks when caches turn on. Cause: a peripheral region was wrongly marked cacheable."

### Needs more explanation
- §17.2 AP[2:0] encoding: the chapter shows AP2 + AP[1:0] and says "AP = `0b001` → AP2=0, AP[1:0]=01." For an MCU dev coming from MPU regions on Cortex-M (where permissions are also a small bitfield but the encoding is different), one extra sentence helps: "AP2 (bit 15) is the 'access-permission-extended' bit added in ARMv7. AP[1:0] (bits 11:10) is the legacy ARMv6 field. Together they form the 3-bit AP[2:0] code in DDI 0406 table B3-8."
- §17.2 TEX[2:0]/C/B: the chapter shows a small table but never explains the *naming* (TEX = Type Extension, C = Cacheable, B = Bufferable). Worth a sentence: "TEX is the 'type extension' field added in ARMv6. With TEX[2]=0 you get the legacy C/B encoding; with TEX[2]=1 you get the modern 'inner/outer attributes' encoding. We use the modern one (TEX=001) for Normal Cacheable."
- §17.3 `invalidate_dcache_all`: the chapter hardcodes "128 sets × 4 ways × 64-byte lines." For the curious reader: explain *what a set is* in one sentence: "A set-associative cache divides cache lines into 'sets' indexed by an address bit range. 4-way means each set holds up to 4 lines tagged from different addresses. Cortex-A7's L1-D has 128 sets × 4 ways = 512 lines × 64 bytes = 32 KB."
- §17.3 `DACR = 0x55555555`: "every domain = client." But what *is* a domain? One sentence: "ARMv7 short-descriptor mode has 16 'domains'. Each section entry tags itself with a domain ID (bits 5:8). DACR's 2 bits per domain decide whether accesses to that domain go through the AP check ('client'), bypass it ('manager'), or fault outright ('no access'). We use client for all 16."
- §17.6 Cache maintenance: the three ops (DCCMVAC, DCIMVAC, DCCIMVAC) are listed without expanding the acronym. Add: "DCC = Data Cache Clean. DCI = Data Cache Invalidate. DCCI = clean *and* invalidate. MVA = Modify by Virtual Address. The CP15 mnemonic encodes the verb + scope."
- §17.7 "speculative fetching from MMIO" is mentioned once (XN bit) but never tied to why it's bad. One sentence: "The Cortex-A7 fetches instructions ahead of the program counter. If a peripheral region is executable, the CPU might prefetch from a status register and read a stale or write-clearing value — which can change the device's state. XN=1 blocks that."
- §17.5 "branch prediction is on" — for the Cortex-M dev who has never seen branch prediction enabled separately: one sentence on what SCTLR.Z=1 actually does. "Z=1 lets the Cortex-A7 use its branch target buffer. Without it, every taken branch causes a pipeline flush."

## Ch18 — Bare-metal peripherals
### AI wording / sledgehammer / buzzwords
- > "the **driver shape that repeats** — clock, IOMUX, register-init sequence, polled state machine, optional IRQ. Once you can write a peripheral driver bare-metal, the Linux equivalent is mostly bookkeeping."
  - Em-dash, plus the AI-ish "mostly bookkeeping" closer. Rewrite: "the driver pattern that repeats: clock, IOMUX, register init, polled state machine, optional IRQ. After writing a few bare-metal drivers, the Linux equivalents look mostly like glue."
- > "Confidence that the Linux abstractions are not hiding magic. Every subsystem callback eventually pokes the registers in this chapter."
  - "Hiding magic" mottoism. Rewrite: "Confidence that the Linux abstractions are not hiding anything you haven't seen. Every subsystem callback eventually writes the registers in this chapter."
- > "Touching it raw, once, removes the mystery."
  - AI aphorism. Cut, or rewrite: "Doing it raw once removes the mystery."
- > "**End of the required path through Part II.** You have written, by hand, a complete bare-metal stack from reset vector to interrupt-driven multi-peripheral execution out of DRAM with MMU and caches active. The ten chapters 9–18 of Part II are the most concentrated single block of low-level engineering in this book; they are also the chapter set you will reach for again when something deep goes wrong in Parts III–VII."
  - Curtain-fall flourish, with "concentrated single block" hyperbole. Rewrite: "End of the required path through Part II. You have written, by hand, a complete bare-metal stack from reset vector to interrupt-driven peripherals running from DRAM with MMU and caches on. Come back to Chapters 9–18 whenever something deep goes wrong in Parts III–VII."
- > "Now that you have done it the hard way, you get to see how the professionals package it."
  - AI-style closing line. Rewrite: "Next we read U-Boot and see how a production bootloader packages the same work."
- > "Every peripheral in this book — and every Linux driver in Part VI — follows this shape."
  - Em-dash. Rewrite: "Every peripheral in this book, and every Linux driver in Part VI, follows this shape."

### ESL readability
- > "We will *not* try to be efficient. We want correctness; we send and receive one byte at a time."
  - Semicolon, terse. Rewrite: "We are not trying to be efficient. We want correctness, so we send and receive one byte at a time."
- > "The 'read I2DR' step is doubled because the first read latches the byte; the second returns it."
  - Semicolon. Rewrite: "The 'read I2DR' step is doubled: the first read latches the byte, the second returns it."
- > "For the full set of timing values runs to ~30 register writes for a typical 800×480 RGB panel. We do not include them inline; they are panel-specific. (Omitted here; panel-specific.)> **Cache caveat.**"
  - Broken markdown: the "Omitted here; panel-specific." parenthetical and the `>` blockquote run together on one line, and "For the full set" reads as a sentence fragment. Rewrite (and fix the prose around it): "A full set of timing values is about 30 register writes for a typical 800×480 RGB panel. They are panel-specific, so we omit them here.\n\n> **Cache caveat.** ..."
- > "either map the framebuffer as Device memory (slower writes) or `dcache_clean_range(framebuffer, sizeof(framebuffer))` after each frame update."
  - Two options in one sentence; the second is a function call. Rewrite: "Either map the framebuffer as Device memory (slower writes), or call `dcache_clean_range(framebuffer, sizeof(framebuffer))` after each frame update."

### Needs more explanation
- §18.2 I²C IFDR: the chapter mentions Table 31-3 is "non-monotonic" but doesn't say what *non-monotonic* means here. One sentence: "Higher IFDR codes do not always give lower frequencies — the table interleaves divider values for hardware reasons. Always look up the code, don't compute it."
- §18.3 ECSPI CONREG: code sets a magic `(0x07 << 20) | (4 << 12) | (1u << 3) | (1u << 4) | (1u << 0)` but the prose never breaks down the field positions. Worth a small table or a comment block: "CONREG: bits[20:24]=BURST_LENGTH (8 bits ⇒ 0x07), bits[12:15]=PRE_DIVIDER, bit3=SMC, bit4=CHANNEL0_MODE=master, bit0=EN."
- §18.4 LCDIF cache caveat: this is the chapter's most important *learning moment* (why `dma_alloc_coherent` exists), but it is one paragraph. Expand: "When the CPU writes to a cached region, the data lives in L1-D until eviction. The eLCDIF DMA reads from the AXI bus, which sees DRAM after any pending writes from the L2 buffer. If your write is still in L1-D, the DMA reads stale memory. Two fixes: (a) clean the L1 lines for the buffer before each frame, or (b) map the buffer as Device or Non-Cacheable Normal so writes go straight to DRAM. Linux's `dma_alloc_coherent` does (b) for you."
- §18.5 "every Linux driver in Part VI follows this shape" — say where the shape *fails*: PCIe enumeration, USB device probe, GPU drivers do not look like this. One sentence keeps the claim honest: "DMA-heavy and bus-enumerated drivers (USB, PCIe) layer additional structure on top, but the inner peripheral access still follows the same pattern."

## Ch18A — Project organization
### AI wording / sledgehammer / buzzwords
- > "We pay this debt off now, before Part III's U-Boot work expects us to organize larger codebases."
  - "Pay this debt off" cliché. Rewrite: "We refactor now, before Part III's U-Boot work pushes us into larger codebases."
- > "**`imx6ull.h` as a single source of truth** for register layout. Both are what the NXP SDK's `MCIMX6Y2.h` formalizes at the level of generated struct headers. We do the *manual* version so the *automated* version makes sense."
  - "Single source of truth" buzzword + italic-emphasis rhetoric. Rewrite: "`imx6ull.h` holds every register definition in one place. The NXP SDK's `MCIMX6Y2.h` does the same thing with auto-generated struct headers. We hand-write ours so the auto-generated version reads as a productivity tool, not a black box."
- > "That last rule is the load-bearing one."
  - Idiom-as-aphorism. Rewrite: "That last rule is the one that matters."
- > "Mental load when re-reading the code 6 months later: dramatically lower."
  - "Dramatically lower" is a buzzword pair. Rewrite: "Re-reading the code 6 months later: much easier."
- > "Over the rest of Part II and the lifespan of the book's labs, the refactor pays back many times."
  - Pays-back-many-times AI rhythm. Rewrite: "The refactor pays back over the rest of Part II and the lab work that follows."
- > "the reason we did not start with U-Boot in Chapter 9: when you can hand-roll it, the SDK becomes a productivity tool rather than a black box."
  - Repeats the same pattern from the section header. Tighten one instance.
- > "It is boring. It is also the most-used file in your project for the next decade if you keep using i.MX6ULL."
  - "Boring / it is also" rhythm is fine, but "for the next decade" is hyperbole. Rewrite: "It is boring. It is also the file you reach for most often on every i.MX6ULL project."

### ESL readability
- > "**Reuse friction.** You want to use the I²C driver from Chapter 18 in a new project. You have to copy `i2c.c`, *and* the relevant `#define`s from `main.c`, *and* the relevant CCM gate bit, *and* the IOMUX writes. Five files involved per peripheral."
  - Three italic-emphasis "and"s is too many. Rewrite: "**Reuse friction.** To use the Chapter 18 I²C driver in a new project, you copy `i2c.c`, plus the relevant `#define`s from `main.c`, plus the CCM gate bit, plus the IOMUX writes. Five files involved per peripheral."
- > "Two specific kinds of pain start to appear:"
  - Fine.
- > "The 30-vs-10-min number is what matters."
  - Numeric-as-noun reads odd. Rewrite: "The 30-vs-10-minute gap is the point."
- > "Most production projects on NXP parts adopt this style by the time they have three peripherals. We do not — for *this* book — for the same reason we did not start with U-Boot in Chapter 9: when you can hand-roll it, the SDK becomes a productivity tool rather than a black box."
  - Two em-dash parentheticals. Rewrite: "Most production projects on NXP parts adopt the struct style by the time they have three peripherals. We do not — at least not in this book. The same reason applies as in Chapter 9: once you can hand-roll it, the SDK becomes a productivity tool instead of a black box."

### Needs more explanation
- §18A.3 "imx6ull.h is the *only* place that names registers" — the example file later shows both `CCM_CCGR1` (full address) and `CCGR_GPIO1_GATE` (bit mask). Worth one line distinguishing: "Register addresses (`CCM_CCGR1`) live in `imx6ull.h`. Field masks (`CCGR_GPIO1_GATE`) can go in `imx6ull.h` for cross-driver use, or stay private inside `bsp_clk.c`. We put the obviously-cross-driver ones in `imx6ull.h`."
- §18A.7 NXP SDK struct style: the `CCM_Type` example shows the technique but never says *which* CMSIS-style convention this follows. One sentence: "This is the same struct-pointer pattern Arm's CMSIS uses for Cortex-M parts (`SysTick->VAL`, `NVIC->ISER[0]`), extended to Cortex-A SoCs by NXP. If you came from STM32/CubeMX, the style is identical."
- §18A.5 The Makefile uses `find` and `wildcard`. Worth one sentence on what makes this Makefile fragile: "Auto-discovery via wildcard means a `.c` file dropped into a `bsp/*/` folder gets built automatically — convenient, but also means a forgotten experimental file silently joins your build. Production projects prefer an explicit `OBJS = ...` list."

## Ch18B — Button and beep
### AI wording / sledgehammer / buzzwords
- > "Adding a button and a buzzer rounds out the minimal HMI vocabulary, and forces us to confront **debouncing**, which is one of those topics every embedded engineer needs to nail down once."
  - "Rounds out", "forces us to confront", "nail down once" — three idioms in one sentence. Rewrite: "Adding a button and a buzzer completes the minimal HMI vocabulary, and forces us to handle **debouncing** — a topic every embedded engineer should learn once and then trust."
- > "the **debounce decision** — when to spin-debounce, when to use a timer, when to do it in hardware. The right answer depends on what else the CPU is supposed to be doing, and we will see all three approaches."
  - Triplet + em-dash. Rewrite: "the debounce decision: spin-debounce, timer-debounce, or hardware-debounce. The right one depends on what else the CPU has to do; we will see all three."
- > "Always cross-check the RM table for 'GPIO5 is in the SNVS domain' — this is one of the i.MX6ULL's idiosyncrasies and the source of the 'I clocked the wrong GPIO bank' debugging story every i.MX6ULL engineer has told once."
  - Two quoted-phrase rhetorical devices, plus a war-story flourish. Rewrite: "GPIO5 sits in the SNVS power domain. Cross-check the RM table when you bring it up — clocking the wrong GPIO bank is the classic i.MX6ULL bug."
- > "1 kHz tone is well within human hearing; 4 kHz is shrill; 200 Hz is a low buzz."
  - Semicolon triplet. Rewrite: "A 1 kHz tone is comfortable, 4 kHz is shrill, 200 Hz is a low buzz."
- > "The explicit silencing line is not decoration."
  - Mottoism. Rewrite: "Without that final write, the PNP can stay on and the buzzer clicks."
- > "Annoying but unambiguous."
  - Cute aphorism. Cut or rewrite: "Loud enough to verify by ear."

### ESL readability
- > "Why active-low via a transistor? The buzzer draws more current than a bare GPIO can sink without risking the SoC's IO drive specs. The PNP is a small driver stage that lets us sink/source the buzzer's coil current via the 3V3 rail rather than directly through the SoC."
  - "Sink/source" technically wrong here: a PNP from 3V3 to load is sourcing current; it does not sink. Rewrite (and fix the EE detail): "Why active-low via a transistor? A piezo buzzer needs more current than a bare GPIO is rated to drive. The PNP sources the load current from 3V3, and the GPIO only sinks the small base current needed to switch the PNP on."
- > "The naive read-and-act: [...] …works once."
  - The ellipsis-then-fragment reads awkward. Rewrite: "The naive read-and-act works once: [code]. Then bounce ruins it."
- > "The classical fix in 1980s firmware was a 20 ms hardware RC filter on the input. We do it in software instead:"
  - Fine.
- > "tactile switches usually < 5 ms"
  - "<" inline reads as math. Rewrite: "tactile switches usually settle in under 5 ms".
- > "This pattern is the basis of every modern keypad-scan implementation."
  - "Every" overreach. Rewrite: "This pattern is the basis of most modern keypad-scan implementations."

### Needs more explanation
- §18B.1 The PNP wiring: schematic-style explanation is good, but worth one diagram or one extra sentence on the *base resistor* (typically a 1k–10k resistor between GPIO and PNP base). Without it the reader may forget that a real circuit has more than the three nets described. Add: "(In the schematic, the GPIO drives the PNP base through a 1k–10k base resistor — the resistor is on the schematic, not in our software, but worth seeing once.)"
- §18B.2 The sliding-window debounce uses `(key_history & 0xFF) == 0xFF`. The chapter says "last 8 ticks all 1" but does not explain *why 8 and not 32*. Add: "We only check the low 8 bits even though `key_history` is 32 bits, so the validation window stays at 8 × 10 ms = 80 ms. Using all 32 bits would mean 320 ms, which is too sluggish for UI feedback."
- §18B.3 `half_period_us = 500000 / hz`: explain the integer arithmetic. "500_000 µs = 0.5 s. Divide by hz to get half a period. For 1 kHz that gives 500 µs; for 4 kHz, 125 µs. Note: integer truncation makes high frequencies slightly off — at 10 kHz you get 50 µs per half-period (10 kHz exact), but at 7500 Hz you get 66 µs ⇒ 7575 Hz actual."
- §18B.4 The flow `key_tick` runs inside `epit_isr` via `epit_tick_handler`. The chapter never shows how `epit_tick_handler` is registered as the ISR. Add one paragraph: "In `bsp_epit.c`, `epit_isr` calls `epit_tick_handler()` (which is a weak symbol; main.c overrides it). This is the standard 'platform driver calls into board file' pattern; Linux uses the same idea via function pointers in `platform_device`."

## Ch18C — Bare-metal RTC
### AI wording / sledgehammer / buzzwords
- > "every product that needs to know 'what time is it' — log timestamps, scheduled actions, license expiration — relies on an RTC that stays alive across power cycles."
  - Triplet flourish + em-dash. Rewrite: "Any product that needs to log timestamps, run scheduled actions, or check license expiration relies on an RTC that survives power cycles."
- > "**separate power domain** mental model. SNVS has its own supply pin (`VDD_SNVS_IN`, usually wired to a coin-cell or a supercap), its own oscillator (32.768 kHz), its own counter, and its own clock gate. While the main SoC sleeps or browns out, SNVS keeps counting."
  - Triplet "its own ... its own ... its own ... its own ..." x4. Rewrite: "the separate power domain. SNVS has its own supply pin (`VDD_SNVS_IN`, usually tied to a coin cell or supercap), its own 32.768 kHz oscillator, and its own counter. When the rest of the SoC sleeps or browns out, SNVS keeps counting."
- > "This is the lab that makes SNVS feel real."
  - Twee. Rewrite: "Run this lab to see SNVS in action."
- > "Useful in production for tamper detection and reboot accounting."
  - Fine.
- > "**End of Part II inserted chapters.** Part II proper ends with Chapter 18; Chapters 18A–C are supplementary deep-dives, reading them in order is recommended but not required."
  - Comma splice ("recommended but not required" attaches awkwardly). Rewrite: "End of Part II's inserted chapters. Part II proper ends with Chapter 18. Chapters 18A–C are supplementary deep-dives; read them in any order, or skip them entirely."
- > "With the bare-metal foundation complete, we switch from 'writing it all ourselves' to 'reading a real bootloader that does the same things.'"
  - Quoted-phrase rhetoric. Rewrite: "With the bare-metal foundation in place, we move from writing it ourselves to reading a real bootloader that does the same things."

### ESL readability
- > "The actual counter ticks at **32 kHz**, but the architectural view splits it: bit 14 of `LPSRTCLR` increments at 2 Hz; treat **upper 32 bits of the 48-bit concatenation** as seconds."
  - Two semi-colons and a colon in one sentence; arithmetic is unclear. Also: bit 14 of a 32 kHz counter increments at 32768/2^15 = 1 Hz, not 2 Hz; double-check. Rewrite (and fix the math): "The hardware counter ticks at 32.768 kHz. The architectural view treats it as a 48-bit concatenation of LPSRTCMR (high) and LPSRTCLR (low). Bit 15 of the low word increments once per second (32 kHz / 2^15). Shift the 48-bit value right by 15 to get whole seconds."
- > "For the purposes of this chapter we use a simpler model: read `LPSRTCMR` and `LPSRTCLR`, concatenate as 48 bits, shift right by 15 to get seconds. (Why 15: the LSB of the 32 kHz counter is `1 / 2^15 second`.) Verify the exact bit layout against your RM revision."
  - Mostly fine. The `1 / 2^15 second` reads odd. Rewrite the parenthetical: "(Why 15: 32768 = 2^15, so each tick is 1/2^15 of a second; shifting right by 15 divides ticks by 32768.)"
- > "Read twice and retake on rollover — the high word can increment between our reads of low and high."
  - Em-dash. Rewrite: "Read twice and retry on rollover. The high word can increment between our reads of low and high."
- > "Don't expect millisecond accuracy across the power cycle — the read-after-power-on may report 1-2 seconds of slack due to internal SNVS startup."
  - Em-dash + dense second half. Rewrite: "Don't expect millisecond accuracy across the power cycle. The first read after power-on may show 1–2 seconds of slack while SNVS internals settle."

### Needs more explanation
- §18C.1 "tamper inputs" appear in the list, again in §18C.8 as a pitfall, but the chapter never says what a tamper input *is*. One sentence: "A tamper input is a digital pin SNVS monitors continuously, even while the main SoC is off. A glitch on the pin is recorded as a tamper event and (if configured) zeroizes a set of secure key registers. Used in payment terminals to detect chassis intrusion."
- §18C.2 "If your board has no battery: SNVS still works, but power-loss = SNVS reset." Worth one sentence on what *exactly* survives in this case: nothing, since power-loss = no SNVS. The current text reads as if "still works" means partial. Clarify: "Without a battery, SNVS runs normally while main power is on, but power-loss erases everything. The counter resets to 0 on next boot; scratch SRAM contents are lost."
- §18C.3 The chapter says "Verify the exact bit layout against your RM revision" but does not commit to one value. For an ESL reader meeting SNVS for the first time, the prose should pick one layout, state the i.MX6ULL-specific bit numbers, and stop hedging. Either the LSB is at 2^-15 s or it isn't — the RM is the source of truth. Pin it down.
- §18C.4 `rtc_set_seconds` disables the SRTC before writing, then re-enables. Worth one sentence on what happens to the *currently running counter* during this window: "Writes to LPSRTCMR/LR are only honored while SRTC_ENV=0. The disable-write-enable sequence loses 1–2 32 kHz ticks (~30–60 µs) while the counter restarts."
- §18C.5 `format_secs` is half-written: it does the math but throws away the result with `(void)out; (void)buf; ...`. Either implement it via `printf` directly inside `format_secs`, or remove the dead stub. As written it confuses a first-time reader: "is this the implementation or not?"

