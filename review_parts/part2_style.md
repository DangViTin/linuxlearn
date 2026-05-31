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
