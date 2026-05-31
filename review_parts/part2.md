# Part II — Bare-metal: Review

## Cross-cutting observations

- **Cortex-M → Cortex-A bridging is uneven.** Ch15 has an explicit "What is different from Cortex-M" section. Ch09–Ch14 introduce the chip without ever telling an MCU engineer what is different about Cortex-A7. The reader meets banked registers (`LR_irq`, `SP` in SVC vs IRQ mode), CPSR mode bits, CP15 system registers, CPSID/CPS instructions, and "PL1/PL0" without ever being told that on Cortex-M they had `MSP`/`PSP` and `IPSR`-coded handlers and that A-profile is a different beast. Add a short "From Cortex-M to Cortex-A7" sidebar somewhere in Ch09 or Ch10 — ideally a one-page table (NVIC↔GIC, MSP/PSP↔banked-SP-per-mode, fixed-vector-table↔VBAR, MPU↔MMU, SysTick↔EPIT/GPT, BX_LR-magic↔explicit-RFE).
- **CCGR enable values are not explained.** Every chapter does `REG(CCM_CCGRx) |= (3u << N)` and says "enable the clock," but the 2-bit-per-gate encoding (`0b00`=off, `0b01`=on-when-CPU-running, `0b11`=always-on, `0b10`=reserved) is never spelled out. An MCU engineer wonders why it's `0b11` not `0b1`. Add a one-paragraph CCGR encoding sidebar in Ch09 or Ch13 (it's also the source of every "why did the author write 3 << x?" moment).
- **`volatile` justification is good but its semantics relative to memory barriers is missed.** Ch10 §10.9 sells `volatile` correctly. But `volatile` does NOT give memory ordering, and on a CPU with caches and write buffers (Ch17+) you also need `dsb` / `dmb` between MMIO writes that must observe each other on the bus. Add a one-paragraph forward reference: "`volatile` covers the compiler; `dsb` covers the CPU; Ch17 will explain why both are needed."
- **Linker-symbol-as-address idiom is never explained.** Ch10's `ldr r0, =_sbss` and Ch14's `extern uint32_t _text_start; … (uint32_t)&_text_start` both rely on the trick that the *address of* a linker-defined symbol is the symbol's value. MCU engineers used to STM32 startup files have usually seen this, but it deserves one paragraph. Otherwise `&_text_start` looks like "addressing a four-byte variable" instead of "asking the linker for the location it stamped at link time."
- **No memory map figure for the SoC.** Every chapter quotes hex addresses (`0x020C406C`, `0x0209C000`, `0x021B0000`, `0x80000000`) but Part II never shows a 4 GiB map: ROM, OCRAM, AIPS-1, AIPS-2, GIC, DDR. Add one ASCII figure early in Ch09 (or pull it forward from Ch17 §17.2 which already maps DRAM and peripherals indirectly). Without it, the addresses feel arbitrary.
- **Inconsistent bit-position notation.** Some tables use "bits 26:27" (high:low order), some use "bits 27:26" (low:high), some use "Bits 26-27" (range). Pick one — ARM's convention is `[high:low]`, so write `[27:26]`. Mixing both inside Ch13 alone is visible.
- **"3% baud error tolerated" / "within 1% / 10% / 15%" claims are scattered.** These rules-of-thumb help, but they go by quickly. Box one (UART tolerance, DDR overclock margin, RTC drift) in a callout each time so the MCU engineer who is used to hand-tweaking knows where the limit lives.
- **Voice and sentence length.** Many sentences are short and choppy ("DDR works. We want to copy the *entire* image to DRAM at `0x80100000`…"). Reader's first language is not English; choppy fragments read worse than connected prose. Combine where you can. Specific examples noted per chapter.

## Ch09 — Assembly LED

### Readability
- "**Internalize it; we use it for every peripheral, forever.**" — drop "forever" (sounds dramatic); replace with "throughout this book."
- "**The blink is, in the most literal sense, you driving electrons through silicon you wrote a contract with.**" — striking but grammatically tortured. Suggest: "The blink is, in the most literal sense, electrons moving through silicon under a contract you wrote."
- "**Hanging off the end of an asm program is not a thing on bare-metal — you must explicitly loop forever.**" — "is not a thing" is colloquial; for an ESL reader, write "On bare-metal there is no OS to catch the fall-through; you must explicitly loop forever."
- "**About 160 bytes. Now we know how small bare-metal can be.**" — fine, but the next paragraph immediately jumps to objdump. Add a sentence connecting the two: "Let's look at what those bytes actually became."

### MCU-engineer friendliness
- The first paragraph of §9.1 ("The Chapter 9 program had no `.data` and no `.bss`...") never explains *why* the program has no `.data`/`.bss` and what the implication is — an MCU dev knows STM32 startup hits a `.bss` zero loop. One sentence: "An STM32 startup file would normally zero `.bss` and copy `.data`; we postpone both to Ch 10 because this program uses neither."
- §9.2 says "Without [the CCGR], all writes to the GPIO registers go into the void." Good. But add the MCU-style hook: "On STM32, this is `RCC->AHBxENR |= GPIOxEN`. The pattern is identical; only the name changes."
- "`ldr r0, =0x...` is GNU assembler syntax for 'load-pc-relative pool constant'." — a Cortex-M engineer has seen this with `ldr Rn, =label`; mention it: "On Cortex-M you've probably seen `LDR R0, =SomeFn`; this is the same construct."
- Nothing tells the reader that Cortex-A7 starts in **SVC mode** with `CPSR.I = CPSR.F = 1` after reset. Ch10's `startup.S` mentions it but Ch09 doesn't. The reader is doing memory writes with no awareness of what mode they're in.

### Missing examples / figures
- After the three-write-pattern paragraph in §9.2, add an ASCII diagram of how the three writes route signal flow: `CCGR1[27:26]` → "GPIO1 module clock gate enable" → `IOMUXC pad mux ALT5` → "pad-to-GPIO1_IO03 routing" → `GPIO1_GDIR.bit3=1` → "drive direction" → `GPIO1_DR.bit3=^bit3` → "level on pad."
- The IVT layout described in §9.5 is text-heavy. Add a tiny figure: a vertical strip showing offset 0x000 (pad), 0x400 (IVT 32B), 0x420 (BootData 12B), 0x42C (pad), 0x1000 (`_start`). Ch11 has this content but Ch09 introduces it first and would benefit from the picture too.
- A register layout figure for `CCM_CCGR1` showing CG0–CG15 as 2-bit fields with CG13 highlighted would unlock the "why `3 << 26`?" question instantly.

### Technical errors
- **Bit number inconsistency.** Tables on lines 55–56 say "(bit 4 = our pin)" for `GPIO1_DR` and `GPIO1_GDIR`. Code comment on line 115 says "Toggle bit 4 in GPIO1_DR." But pin `GPIO1_IO03` is **bit 3**, and the code itself correctly uses `(1 << 3)`. The summary line at line 27 also says "bit 3" correctly. Fix the table column ("bit 3 = our pin") and the two `bit 4` comments in the asm.
- "**Cortex-A7 cannot encode arbitrary 32-bit immediates in a single instruction**" — true, but the cause is the 12-bit rotated-immediate encoding of `MOV/MOVT` predecessors. A clarifying half-sentence helps: "...because the data-processing immediate form encodes only a rotated 8-bit value."
- §9.4 footnote about `-Ttext=0x00907400`: the OCRAM start is 0x00900000 with 128 KB, so 0x00907400 is at offset 29 KB. The chapter says "above the ROM's bookkeeping at the bottom of OCRAM." RM §8.7 puts the ROM's working area at 0x00900000–0x00906FFF (28 KB). State the 28 KB ROM region explicitly so the offset makes sense.
- "**The CCGR encoding for 'always on' is `0b11`.**" The CCM_CCGRx field encoding has four values: 00=off, 01=on-during-run, 10=reserved/off, 11=on-always. Spell out the table; this is the most reusable nugget in the chapter and it's hidden in one sentence.

### Knowledge prerequisites missing
- The chapter assumes `uuu` and SDP boot from Ch07/08. Fine — but the reader hasn't seen IVT/BootData yet; §9.5 hand-waves "accept the magic." A two-sentence "what the IVT is for, just enough to make this chapter run" callout would help. Currently the chapter says "we will write a Python tool in Chapter 11" without saying *why* an IVT is needed at all (i.e., "the ROM only loads images that begin with a 32-byte header").
- `.syntax unified`, `.cpu`, `.global` are briefly mentioned. A new-to-GAS reader needs one more sentence per directive — these aren't familiar from Keil/IAR.
- `_start` is the default GCC entry point — the chapter says "GCC's default entry is `_start` already" but never connects this to: "On STM32 your reset handler is named `Reset_Handler` and lives at vector[1]; here we just name our entry `_start` and the linker places it first."

### Other
- The 1.5 M iteration "≈ 8 ms" calculation in §9.3 should show its working. At 396 MHz with a 4-instruction loop body, `4/(396e6) × 1.5e6 ≈ 15 ms`, not 8. The lab at §9.8.1 then says "an inner-loop body of 4 instructions and a counter of 1.5M is ~15 ms" — so the §9.3 "~8 ms" is inconsistent with the lab. Pick one and be consistent.
- §9.6 step 4 calls out USB ID `15a2:0080`. The data sheet sometimes shows different VID for different mask sets; reference the *RM Table 8-X* or note "Your VID may be `15a2:00xx` depending on chip revision."

## Ch10 — C + startup.S + linker script

### Readability
- "**Without it, the first function-call instruction in C destroys the world.**" — drop the hyperbole or save it; for ESL readers it parses as literal. Suggest: "Without SP set, the first `push` in a C prologue writes to an undefined address and corrupts memory."
- "**Habit is cheap, and bugs from 'we will never need this' are expensive.**" — keep; this one lands.
- "**`bl main` is a *branched-and-link***" — typo: "branch-and-link" (no -ed).
- "**One instruction; three guarantees.**" — fine pithy line, but unpack which three explicitly since the prior line bundled them: "(1) mode = SVC, (2) IRQ masked, (3) FIQ masked."

### MCU-engineer friendliness
- §10.1 sells the no-loader idea well. Add one sentence: "On STM32, the linker and the ST-provided `startup_stm32fXXX.s` together provide what we are about to build."
- §10.3's mode-bit `0x13` for SVC is dropped without context. An MCU engineer hasn't seen CPSR `M[4:0]`. Add a tiny table (SVC=10011, IRQ=10010, FIQ=10001, USR=10000, etc.) at first use. Without this, the reader reads "mode = SVC" as a magic incantation.
- "`cpsid if, #0x13`" — explain that `i` flag masks IRQ, `f` flag masks FIQ. The `if` together is "mask both." Currently the comment says `@ mode = SVC, mask IRQ+FIQ` but the syntax is not parsed.
- §10.5 introduces `-mfpu=neon-vfpv4 -mfloat-abi=hard`. Cortex-A7 *has* a VFP and NEON; Cortex-M4F has VFP too. But on bare-metal you must enable the FPU before using it (writes to `FPEXC`/`CPACR`). The flags compile-time-enable codegen; the chapter never runtime-enables the FPU. If the reader's `main` accidentally uses a float, they will trap. Add a one-paragraph warning: "We pass `-mfpu` for codegen but we do not yet enable the FPU at runtime; Ch15 mentions where; until then, avoid float."

### Missing examples / figures
- §10.2 introduces `_etext`, `_sdata`, `_edata`, `_sbss`, `_ebss`. Add an ASCII figure showing the OCRAM layout with these labels stamped at the boundaries: a vertical strip from `0x00907400` (ORIGIN) up to `_stack_top`, with `.text`, `_etext`, `.data(VMA=LMA here)`, `_edata`, `.bss`, `_ebss`, `_irq_stack`, `_stack_top`. This single figure makes the whole script click.
- §10.2 should follow with a *second* figure showing the LMA-vs-VMA split when `.data` is moved to DRAM (forward-referenced from Ch14). One picture, two layouts side-by-side, would crystallize `AT(_etext)`.
- The literal pool concept from Ch09 is repeated here in §10.7 ("the literal pool follows the function"). Add a small disassembly snippet annotating "this is the pool" so the reader can see it.

### Technical errors
- §10.3 comment: "**The Boot ROM may have left us in another mode; SVC is what we want.**" The ROM enters SVC mode on i.MX6ULL after reset (per RM §8.X). The "may have left us in another mode" wording is overcautious and misleading. Better: "We are entered in SVC mode after reset; we re-assert mode and masks defensively."
- §10.4: `(1u << 3)` is `LED_BIT`. Code is correct (GPIO1_IO03 = bit 3). But the macro name suggests it's a *bit number* `3`, while the macro evaluates to a *mask* `0x08`. Either rename (`LED_PIN_BIT` for the bit number, `LED_PIN_MASK` for the mask) or note in a comment.
- §10.5 Makefile: `LDFLAGS := -T link.ld -nostdlib`. The rule invokes `$(CC) $(LDFLAGS) -o $@ $(OBJS)`, where `-Tlink.ld` is being passed to gcc — gcc forwards it to the linker. Works, but stylistically passing linker options to gcc usually uses `-Wl,-T,link.ld`. Not wrong; just note for the curious. (`gcc` does accept `-T` directly.)
- §10.5 `-fno-builtin -nostdlib` — `-nostdlib` already implies you have no libc; adding `-fno-builtin` on top is conservative but worth a one-line explanation ("prevents GCC from recognising e.g. `memcpy` and substituting library calls"). Otherwise the reader wonders why two flags say "no library."
- The `__attribute__((noreturn))` discussion in §10.8 is good. Note that GCC requires `void` return type for `noreturn`; `noreturn int main(void)` is contradictory. The compiler will warn or error; flag this.

### Knowledge prerequisites missing
- "**AAPCS requires SP to be 8-byte aligned at every public function entry.**" — what is AAPCS? First mention, no expansion. Spell out: "ARM Architecture Procedure Call Standard (AAPCS)."
- `KEEP(*(.vectors))` — the `*(.section)` linker syntax is explained ("gather all `.text*`"), but `KEEP` itself only gets one sentence about `-gc-sections`. An MCU engineer using IAR/Keil has not necessarily met `-gc-sections`. One additional sentence: "GCC's linker can be told to discard sections that nothing references; `KEEP` opts a section out of that."
- The CRT0 concept appears in "Going deeper" but never in the body. Worth a one-line callout: "`crt0.S` is what the standard C runtime uses as its `startup.S`; we are writing our own because crt0 expects a hosted environment."

### Other
- §10.7 ends with "Try it: change ORIGIN to `0x00908000`, rebuild, redump." Then "Then change it back." Combine into the lab section instead of mid-prose; the reader is unsure if it's mandatory.
- §10.11 mentions `_sbss` 4-byte alignment, but the zero loop uses `strlo r2, [r0], #4` which assumes 4-byte alignment of the *length* too. If `_ebss - _sbss` is not a multiple of 4, the loop overshoots. The `ALIGN(4)` on `.bss` handles the start but not the end. Mention or use a different terminator (`bne` on remaining bytes).

## Ch11 — Hand-building a Boot ROM-acceptable image

### Readability
- "**Owning the tool means owning the image format. Once you own the image format, you own boot.**" — fine.
- "**`uuu`'s magic and let it work.**" — confusing because the next chapter is the one that demystifies. Suggest: "...let the magic work for now; the next sentence shows what's inside it."
- "**Wait — entry is `0x00908000` but the code is *placed* at `0x00908400`? That's wrong.**" — strong rhetorical move; works. Just make sure the previous output block clearly shows the contradiction. Currently it does, but a "Look at the third line of the output:" pointer would help an ESL reader catch it.
- "**With 60 lines of Python and 50 lines of C and assembly.**" — closer might be 100 lines of Python + 30 lines of asm. Update or footnote with the actual count.

### MCU-engineer friendliness
- An MCU engineer rarely sees an "image header" — they `objcopy -O binary` directly to flash. The reason an i.MX needs one (mask ROM is generic, BootData is part of the boot protocol) is explained in Ch7 but worth a one-paragraph recap here: "Unlike STM32, where the boot ROM jumps directly to a fixed address and your reset vector at 0x08000004 is enough, the i.MX boot ROM accepts arbitrary load+entry through a small header."
- The big-endian-length-but-little-endian-rest gotcha is well-flagged. Add a one-paragraph explanation of *why*: "The header was designed for HAB (High Assurance Boot) sign/verify tools that came from networking codebases where big-endian lengths are conventional. The rest of the IVT was added later and is native ARM little-endian."

### Missing examples / figures
- §11.1's offset table is the layout. Convert it to a one-page ASCII picture (vertical strip of file offsets) — readers internalize spatial layouts faster than dotted tables.
- §11.3's hex dump + decode table is great. Worth adding "in pictures": draw the 32-byte IVT as a 4×8 grid with field names and the actual bytes for one example image.
- After §11.5, an ASCII figure of the SD card layout from byte 0 with sectors labeled: `[byte 0..0x400 = MBR area / pre-pad] [0x400..0x420 = IVT] [0x420..0x42C = BootData] [pad] [0x1000.. = code]`. The "LBA 2" / "byte offset 0x400" relationship is hard to track in prose.

### Technical errors
- §11.5: "`dd if=led.imx of=/dev/sdX bs=1k seek=1`" — `seek=1` with `bs=1k` writes at offset 1024 (0x400). Correct.
- §11.5 Option 2: "the `0x400` pad inside the `.imx` IS the first 1 KB of the SD card." Correct, and the cleaner approach. The chapter weighs both options well.
- "**`BootData.length` shorter than the file. Tail bytes are not loaded.**" — verify against RM. Some ROMs stop at `length`; some load entire input. For i.MX6ULL it's truly `BootData.length` that's authoritative.
- §11.6 vendor-image decode: the math "the simpler view is that `dcd_addr` is the *post-load* address" is glossed. Spell it out: "After the ROM finishes loading from the boot device into RAM at `BootData.start`, the DCD lives at `(dcd_addr - BootData.start)` bytes into the image, which on disk equals `0x400 + (dcd_addr - BootData.start)`."

### Knowledge prerequisites missing
- The chapter assumes Python 3, `struct`, `argparse` are familiar. They are for most readers; an MCU engineer who lives in C may not be. One-paragraph "if Python is unfamiliar, the script is doing X" footnote at the top of §11.2 helps.
- "HAB" is mentioned ("disables HAB signature checking. Will revisit in Chapter 62.") but not expanded. First-mention expansion: "HAB = High Assurance Boot, NXP's secure boot framework."

## Ch12 — UART driver and `printf`

### Readability
- "**This text travels at 115200 baud.**" — cute. Keep.
- "**Without it, RX appears dead.**" — keep.
- "**The chip rounds; up to ~3% baud error is tolerated by most receivers.**" — combine the next sentence: "Mismatched baud manifests as garbage characters that resemble valid ASCII but aren't."  Tighter: "Up to ~3% baud error is tolerated; beyond that you get garbage characters that resemble ASCII but aren't."
- "**Always. Every. Time.**" — final pitfall ("Forgot the CCGR"). Sets tone; works.

### MCU-engineer friendliness
- An MCU engineer has used STM32's USART, which also has UBRR-style baud divisors. Open §12.2 with one sentence: "STM32's USART uses `BRR = f_CK / baud`; the i.MX is the same shape but with a *fractional* divisor (numerator/denominator pair) instead of an integer." This frames the whole chapter.
- §12.4 says "8N1; RX+TX enable; release SRST." Spell out what 8N1 means once on first use ("8 data bits, no parity, 1 stop bit") — most know it, but completeness costs nothing.
- "`UCR2.SRST` is **active-low**" — write `SRST = 0` means *asserted reset*. Counterintuitive for an MCU engineer who is used to "1 = active." Bold this sentence — it's the most surprising single thing in the chapter.

### Missing examples / figures
- §12.2 baud-rate derivation deserves an ASCII flow: `XTAL 24 MHz → PLL3 480 MHz → /6 → uart_clk_root 80 MHz → ÷RFDIV(1) → ÷16 oversample → × UBIR/UBMR fraction → 115200`. The intermediate divisions are scattered in prose.
- A register-bit diagram of `UCR2` showing `IRTS / WS / TXEN / RXEN / SRST` highlighted would help. Same for `USR1` and `USR2`.
- After §12.4, a sequence diagram of "what `uart_putc('A')` does on the wire": spin on TRDY → write 0x41 to UTXD → 1 start + 8 data + 1 stop bits at 8.68 µs each → 10 × 8.68 µs ≈ 87 µs.

### Technical errors
- §12.1: "On the Point Atom MINI these are routed to pads **UART1_TX_DATA** and **UART1_RX_DATA**." This is circular wording. Suggest: "On the MINI these signals are routed to the pads named `UART1_TX_DATA` and `UART1_RX_DATA` (the pads have the same names as the UART1 module signals because they default to that function at ALT0)."
- §12.1: "**IOMUXC_UART1_RX_DATA_SELECT_INPUT** at `0x020E0624`, telling UART1 which pad to listen on for RX (usually `0` for the matching `UART1_RX_DATA` pad)." Then §12.4 sets `REG(IOMUX_DAISY) = 3`. Discrepancy: "usually 0" but code writes `3`. Cross-check against the RM SELECT_INPUT register table. For UART1_RX_DATA_SELECT_INPUT the daisy values map to specific pads; if the MINI uses the `UART1_RX_DATA` pad itself, the value is 3 per RM (selecting that pad as the input source). The comment "usually 0" is wrong — fix or explain.
- §12.4 UCR4 comment: "`(1u << 0)` /* DREN: receive-ready interrupt enable bit; we don't use IRQ yet but writing 0 elsewhere is fine */". The code sets bit 0 (= DREN = DMA Enable for Receive). Then comment contradicts itself ("we don't use IRQ"). Per RM §55.15.4, UCR4 bit 0 is `DREN` (DMA Receive Enable). Setting it to 1 in polled mode is wrong — should be 0. This is likely a bug.
- §12.2 baud calc: "(UBIR + 1) / (UBMR + 1) = 0.02304" then "UBIR = 70, UBMR = 3082". 71/3083 = 0.02303. Correct. Show the actual achieved baud (80e6 / 16 × 71/3083 = 115,160 Hz, off by 0.035%) so the reader sees how close — and add "this is within the 3% tolerance band."
- §12.5 `va_arg(ap, unsigned)` discussion: on AAPCS / 32-bit ARM, `unsigned int` and `unsigned long` are both 32 bits, so the code works, but on 64-bit ARM (AArch64) they differ. Add a one-line note "On AArch64 we'd need `unsigned long` for the same code; we are 32-bit here."

### Knowledge prerequisites missing
- `va_arg`, `va_list`, `va_start`, `va_end` (§12.5) come in unannounced. Most C devs know them, but a one-paragraph recap with the warning "these are macros, not functions; their internal state is implementation-defined" would be charitable.
- `picocom` — first introduced in earlier chapters? Quickly recap connection params (`picocom -b 115200 /dev/ttyUSB0`) in the §12.6 build/run block.

### Other
- §12.4 sets `IOMUX_PAD_RX = 0x000130B1` (with keeper) but `IOMUX_PAD_TX = 0x000010B0`. The two pad-control values differ; the difference (HYS bit and keeper) is buried. Add a one-line decode of each: "HYS=1, keeper enabled, PUS=… for RX to avoid floating; output-only TX needs none."
- §12.9 pitfalls is great. Add: "`UBMR` written before `UBIR`" symptom = baud rate inverted/scrambled.

## Ch13 — CCM clock tree bring-up

### Readability
- "**Every peripheral hangs off one root clock; each root clock hangs off one PLL.**" — keep, but slightly inaccurate (some peripherals use osc24m directly, no PLL). Soften to "most peripherals."
- "**Software-reads-software-writes is the easiest check to lie to itself.**" — elegant.
- "**Or, more simply: put PLL1 in bypass while reprogramming. Bypassed PLL1 outputs the 24 MHz reference, so the core runs slow but never crashes.**" — clearer than the step-clk alternative; move this to be the primary explanation rather than alternative.
- "**Looks like text but has occasional corruption.**" (re: baud) — concrete; good.

### MCU-engineer friendliness
- §13.2: An MCU engineer knows PLLs from STM32's RCC: HSE → PLLM/PLLN/PLLP → SYSCLK. Frame i.MX's tree against that: "STM32's PLL has one VCO and a few post-dividers. i.MX has *many* PLLs and *PFDs*, which are fractional dividers off each PLL's VCO. This gives more output options at the cost of complexity."
- §13.4 step 1 talks about "step_clk" then says "Or, more simply: bypass." Choose one and explain it. Right now the reader is told two ways without a recommendation — actually the second is the chosen path.
- "**PMU**" is introduced in §13.6 with no explanation. On Cortex-M there's no PMU (you use SysTick/DWT). One sentence: "The Cortex-A7's PMU (Performance Monitor Unit, ARM PMUv2) provides cycle counter, event counters, and architectural events; we use only CCNT (cycle counter)."

### Missing examples / figures
- An ASCII tree diagram of the clock tree we're building. Roots: 24 MHz XTAL. Branches: PLL1 (ARM), PLL2 (System=528 MHz fixed → PFD0/1/2/3), PLL3 (USB1=480 MHz fixed → PFD0/1/2/3), PLL5 (Video), PLL6 (ENET), PLL7 (USB2). Each PFD feeds a mux feeding a divider feeding a peripheral. This *is* the chapter — without the picture, the reader has to draw it themselves.
- §13.2 PFD encoding: figure showing each 32-bit `ANATOP_PFD_528` register as four 8-bit byte lanes (PFD0..PFD3), each with FRAC[5:0], CLKGATE, STABLE.
- §13.5 "Expected" output should be paired with a "what you actually saw" troubleshooting box for common deviations.

### Technical errors
- §13.4 step 6: "PFD2 is in ANATOP_PFD_528 bits 16:21 (PFD2_FRAC). Bit 23 (PFD2_CLKGATE) must be 0." Per RM §18.7.16, PFD2_FRAC is bits **21:16** (FRAC[5:0]) and PFD2_CLKGATE is **bit 23**. Correct.
- §13.4 step 7 (CBCMR PRE_PERIPH_CLK_SEL): "Bits [19:18] -- select what feeds the periph_clk mux: 00=PLL2 (528), 01=PLL2_PFD2 (396), 10=PLL2_PFD0, 11=PLL2_PFD2/2." Per RM §18.6.10, the encoding is: 00=PLL2 528, 01=PLL2_PFD2, 10=PLL2_PFD0, 11=PLL2/2 (PLL2 divided by 2). The "11=PLL2_PFD2/2" claim is suspect — cross-check the table. Default reset value is 01 (PLL2_PFD2). The reset already does what we want; the code is fine but the table description for `11` needs verification.
- §13.4 step 9 "CSCDR1.UART_CLK_SEL (bit 6) = 0 -> PLL3_80M (already /6)". Per RM §18.6.13, UART_CLK_SEL bit 6: 0 = derive from PLL3 80MHz, 1 = osc_clk. Correct.
- §13.5: "Pre-clocks_init(): ARM = 396000000 Hz". The function `clocks_get_arm_hz()` does `XTAL × DIV / 2 / (CACRR+1)`. After ROM, with default CACRR + default PLL_ARM (DIV=88? actual reset varies), what does it report? The chapter just states 396 MHz. Actual i.MX6ULL boot-ROM leaves ARM_PODF defaulting to /1 and PLL_ARM at the reset DIV_SELECT (88), so ARM = 24*88/2 = 1056? Or the ROM reprograms? Verify the claim "ARM = 396 MHz" experimentally and document the chain.
- §13.7 "1 cycle = 2.525 ns" at 396 MHz: 1/396e6 = 2.525e-9 s. Correct.

### Knowledge prerequisites missing
- The chapter uses "ATOMIC SET/CLR/TOG registers at +4/+8/+0xC" once (§13.2) but the reader has not seen this NXP idiom. One paragraph: "Each ANATOP register has three sibling addresses 4/8/12 bytes ahead, used for atomic SET (write-ones-to-set), CLR (write-ones-to-clear), TOG (write-ones-to-toggle). On a multi-core SoC this avoids the read-modify-write race; on our single-core bare-metal, it's a convenience."
- `mrc p15, …` / `mcr p15, …` (§13.6 PMU): co-processor instruction syntax. An MCU engineer hasn't used CP15. One paragraph at first use explaining `mcr<sub>15</sub>(opc1, CRn, CRm, opc2)` mapping to architectural register names.

### Other
- §13.6 "scope a GPIO" — at 696 MHz, a 5-cycle-per-iteration loop produces 70 MHz; the chapter notes "the scope and the GPIO drive strength will not produce cleanly; you'll see a degraded waveform but the *period* is measurable." The MCU engineer reading might not have a 100+ MHz scope. Suggest a lower-frequency variant ("add 20 nops; toggle at ~1 MHz") for cheaper instruments.
- §13.8 step 4 "set DIV_SELECT = 66" should give 24 × 66 / 2 = 792 MHz. Verify the wording matches.

## Ch14 — DDR3 initialization with MMDC

### Readability
- "**Set an afternoon aside.**" — keep.
- "**You cannot guess them; you must look them up.**" — keep; punchy.
- "**Treat them as a black box you can re-derive at any time by running the tool.**" — re-derive *by* not *at*.
- "**For *learning*, doing it in C (as we did) is better — you see the logic. For *deployment*, the DCD is better — it lets you load larger images.**" — neat trade-off framing.

### MCU-engineer friendliness
- Most MCU engineers have never touched external DRAM (STM32H7 has an FMC controller, but few use it). The §14.1a primer is helpful but should highlight *why DRAM is hard*: refresh requirement, timing sensitivity, calibration drift with temperature, signal integrity demands beyond a Cortex-M's SRAM connection. Even a one-paragraph "what makes DRAM bring-up different from peripheral bring-up" would orient the reader.
- "**Refreshed every 64 ms**" — explain the consequence: "the DRAM controller has to issue ~8000 refresh commands per second in the background." Otherwise "refresh" is an abstract word.

### Missing examples / figures
- An ASCII figure of the DDR3 protocol: command bus, address bus (RAS/CAS/CKE), data bus (DQ + DQS), control (CS, ODT). MCU engineers know SPI; DDR3 is "very wide SPI on steroids" but the analogy needs a picture.
- A timing diagram showing the JEDEC init sequence in §14.6: RESET#, CKE, NOPs, MRS0..3, ZQCL spread across the 500 µs+200 µs+ZQ window.
- A diagram of MMDC's three calibration steps (write leveling, DQS gating, read/write delay) showing what each compensates for (CK vs DQS skew, DQS framing window, per-bit data eye centering).
- The "two chips, one bus" picture in §14.3 (16-bit bus from two ×8 chips) deserves an ASCII figure with chip-1 driving DQ[7:0], chip-2 driving DQ[15:8].

### Technical errors
- §14.6 MR0 encoding table: "CAS latency CL = 11 → 1110_1 → 0b01110". The MR0 CL field is bits {6:4, 2}, *not* contiguous. The encoding for CL=11 per JEDEC JESD79-3F Table 41 is `A6:A4 = 0b011`, `A2 = 0b1`. So the bit pattern across MR0 is `... A6=0, A5=1, A4=1, A3=?, A2=1 ...`. The "0b01110" looks like a contiguous 5-bit value, which is not how MR0 encodes it. Re-derive and present as the {6:4} + {2} split.
- §14.6 MR0 "tWR for tWR=15ns@800MHz, 6 ⇒ 0b101". For DDR3, tWR_min(cycles) = ceil(15 ns / tCK). At 800 MT/s, tCK = 2.5 ns, so tWR = ceil(15/2.5) = 6 cycles. MR0[11:9] encoding for tWR=6 is `010` per JEDEC; for tWR=8 it's `100`. The "6 ⇒ 0b101" claim is wrong (`101` encodes tWR=14). Verify and correct.
- §14.6 representative MR values labeled as "depends on exact tWR/CL". MR0 = 0x00000A50. Decode: bits[11:9]=`101`(=tWR_enc 5 → 14 cycles), bits[8]=`0`(DLL not reset), bits[6:4]=`101`(CL bits hi)=>CL_hi=5, bit[3]=`0`, bit[2]=`0`(CL low bit). The actual MR0 for CL=11, tWR=6 should be ~0x00000C50 or ~0x00000A60 depending on burst length. **Strongly recommend recomputing from JEDEC tables and republishing exact values**, OR clearly labelling these as "placeholder bit patterns, not valid for any real configuration."
- §14.6 MR1 = 0x00000044. Decode: bit 6 = `1` (Rtt_Nom A6), bit 2 = `1` (Rtt_Nom A2 → composite Rtt_Nom = 0b101 with A9 = 0 → invalid for DDR3). The values look ad-hoc.
- §14.10 `relocate_to_dram`: `entry_t entry = (entry_t)(0x80100000 + ((uint32_t)main - 0x00907400));`. This assumes `main` was linked at the OCRAM load address. But the linker placed `main` somewhere inside `.text` starting at `_text_start` not at `0x00907400` (which is the IVT/header base). The arithmetic is plausible if `_text_start = 0x00907400` and `main` lives there, but the chapter never reconciles. Recommend using a linker-provided symbol `_main_offset = main - ORIGIN(OCRAM)` and then `entry = 0x80100000 + _main_offset`. As written, the off-by-IVT-header (0x1000) is potentially wrong if the loaded image starts at 0x00907400 but `_start` is at 0x00908400 (per Ch11 §11.3).
- §14.10 "The flag-in-`.data` works because we copy `.data` along with `.text`" — but `relocate_to_dram` only copies `_text_start..._text_end + _data_start..._data_end`. The chapter shows two contiguous copies but the source addresses use `0x00907400` as the start of *everything*, which conflates `.text` LMA with `.data` LMA. Per Ch10's linker script, `.data` LMA is at `_etext`, not `_text_start`. The logic is broken: the second copy would copy the *same* address range as the first (because both start from `src = 0x00907400`). Rewrite the relocation code with explicit per-section source/dest addressing, OR copy the contiguous OCRAM image as one block.
- §14.7 `MDCFG2 = 0x01FF00DB` value placement: the comment says "tDLLK, tRTP, tWTR, tRRD" but MDCFG2 layout is tDLLK[31:16], tRTP[6:4], tWTR[3:0] (no tRRD in MDCFG2 — tRRD is elsewhere). Cross-check RM §39.4 register map. The chapter's claim "MDCFG2: tDLLK, tRTP, tWTR, tRRD" is approximate at best.
- §14.13 NXP DDR Stress Tool — "Windows GUI / CLI program." Newer releases also have Linux CLI variants. Update if appropriate.
- §14.10 "use a flag" pattern: `static uint32_t already_in_dram = 0;` followed by `if (!already_in_dram) { ... already_in_dram = 1; relocate_to_dram(); }`. But the *DRAM copy* sees `already_in_dram = 1` only if `.data` (which contains `already_in_dram`) was correctly copied to DRAM with the value `1` *after* the OCRAM execution set it to 1. Order matters: the OCRAM main first sets `already_in_dram = 1`, then calls relocate which copies `.data` (now containing `1`) to DRAM, then jumps. The DRAM copy reads `1` and skips the init block. This works iff the copy happens AFTER the OCRAM main sets the flag. The current code in §14.10 sets `already_in_dram = 1` *then* calls `relocate_to_dram()` — correct. But this is subtle; add a comment explaining the ordering.

### Knowledge prerequisites missing
- The "Mode Register" terminology comes from JEDEC DDR3 standard, not from i.MX. State explicitly: "MR0..MR3 are *DDR3 chip* registers (not MMDC registers). The MMDC's `MDSCR` command interface is what sends `MRS` (Mode Register Set) packets to the chip over the DRAM bus."
- "ZQ calibration" is named without explanation. One sentence: "ZQ calibration tunes the chip's output driver impedance against an external 240 Ω precision resistor (ZQ pin); it must be done at boot and periodically thereafter."
- "ODT" briefly explained as "on-die termination" but its purpose (signal-integrity matching for the bus's reflection-free operation) is left implicit.

### Other
- §14.7 `ddr_iomux()` shows one register write and "... (all DRAM pads) ...". For a chapter that demands the reader run real code, omitting the bulk of pad config is risky. Either provide the full list (it's ~30 lines), reference a downloadable companion file with the complete table, or warn loudly "this is a sketch; you cannot run this without the full pad config from §14.5."
- §14.15 pitfall "Wrong MR0 CAS latency": "CL=11 on chip = `MR0[6:4,2] = 0b1110_1`". Note same `0b1110_1` issue as §14.6 — the field is non-contiguous and the underscore should make that explicit.
- The chapter could really use the calibration values from a known-good Point Atom MINI BSP committed as a constant block, so a reader can compile-and-go for first attempt before running the Stress Tool. Currently the reader can't even *try* without the tool.

## Ch15 — Exceptions and the GIC

### Readability
- §15.1 "**No auto-stacking. Your handler must save and restore registers itself.**" — perfect framing for the MCU engineer. This is the best Cortex-M-vs-Cortex-A intro in Part II.
- "**All of it correct, all of it terrifying the first time you read it.**" — re: Linux entry-armv.S; keep.
- "**Eleven steps. Every Linux IRQ in user space follows the same pattern.**" — strong closing of §15.8.

### MCU-engineer friendliness
- §15.1 is genuinely good. Apply this exact pattern (Cortex-M-vs-A diff box) at the start of Ch09 and Ch10 too — the rest of Part II is missing this scaffolding.
- The "banked register" concept is implicit in §15.4 ("IRQ mode needs its own stack") but never visually shown. A reader who has never seen banked registers will mentally model "IRQ mode" as "a flag" rather than "a different SP/LR pair." Show the bank.
- "**`bl c_irq_dispatch` is the standard branch-and-link, but with our preserved state.**" — fine; but emphasise that `BL` writes LR with the return address (= current PC+4 in ARM mode), and that this LR is the *SVC mode LR* now that we switched modes. The mode-switch erases the `LR_irq` from view (it's banked).

### Missing examples / figures
- **A banked register diagram.** Show R0–R7 shared, R8–R12 shared (with FIQ-mode having its own R8–R12), then for each mode (USR/SYS, SVC, IRQ, FIQ, ABT, UND) show separate SP and LR, plus SPSR per privileged mode. This single figure is the missing centerpiece of Ch15.
- **A CPSR/SPSR bit-layout diagram.** Show the mode bits M[4:0] with the five encodings used, plus the I/F/T/A flags.
- **A "vector table on disk vs in memory after VBAR" picture.** Show the 8-instruction table at `_vectors` with each slot's offset and what it branches to.
- **A timing diagram of `irq_entry`'s stack manipulation.** Show the IRQ stack before/after `srsdb`, the SVC stack before/after `push`, and the return path.
- §15.5 GIC flow has 9 steps in prose. Convert to an ASCII swimlane diagram (Peripheral | Distributor | CPU IF | CPU | Handler).

### Technical errors
- §15.3 `sub lr, lr, #4` comment: "**adjust LR_irq to point at the *interrupted* instruction (so RFE re-executes it... no, it resumes correctly with this -4 fixup)**". The wording is confused. The CPU stores PC+4 in LR_irq on IRQ entry (or PC+8 for prefetch/data abort, depending on the spec edition). The -4 makes LR_irq point to the *next* instruction to execute, which is the one that *would have* executed had the IRQ not fired. `rfeia` then resumes there. Clean up the comment — the "no, it resumes correctly" mid-sentence reverse is confusing.
- §15.3 `srsdb sp!, #0x12`. Per ARM ARM, `SRSDB SP!, #mode` stores `LR_<current_mode>` and `SPSR_<current_mode>` to the *banked SP for <mode>*. So `SRSDB SP!, #0x12` from IRQ mode stores onto the IRQ stack — but it reads LR_irq and SPSR_irq from the *current* mode (IRQ, since we're in it). This is correct in the chapter's code but the explanation "stores `{LR, SPSR}` to the IRQ-mode stack pointer. Mode 0x12 = IRQ" reads as if the mode operand selects what to *save*. Clarify: "the `#0x12` selects which mode's SP is used as the storage base."
- §15.5 table for `GICD_IPRIORITYRn`: "Priority (8 bits each; 256 bytes for 256 IRQs)". The total IRQ count on this GIC is 160 (TYPER reports it); 256 was overstated. Match `MAX_IRQ = 192`.
- §15.5 says GIC distributor at `0x00A01000`. The Cortex-A7 typically *exposes* the GICD inside an internal `peripheral base + 0x1000`. The peripheral base on i.MX6ULL is `0x00A00000`, so GICD = `0x00A01000`. Correct, but mention the parent peripheral-base CP15 register `CBAR` so the curious can verify.
- §15.7: "UART1's IRQ goes through GIC SPI ID **26**. In GIC terms that's `26 + 32 = 58` — but the *GIC's view* of the IRQ ID also adds 32 internally. Conventionally we use the SoC's labeling, which on i.MX6ULL puts UART1 at GIC ID 58." This is muddled. Per RM Table 3-1, the listed IRQ number is the SPI number minus 32 — actually per RM the listed IRQ uses GIC INTID directly (so the table number IS the SPI number, with `+32` going to the GIC INTID). The chapter's claim "GIC's view of the IRQ ID also adds 32 internally" is wrong — the GIC distributor uses INTIDs directly with SGIs=0–15, PPIs=16–31, SPIs=32+. Verify against the GIC v2 spec, and rewrite this paragraph. Suggested clean version: "RM Table 3-1 lists this as 'IRQ 26.' That number is the SPI offset; the GIC INTID is `32 + 26 = 58`, which is what we pass to `gic_register` and `gic_enable_irq`."
- §15.6 `c_irq_dispatch`: `uint32_t irq = iar & 0x3FF;`. Correct (IAR's INTID is bits 9:0 = 10 bits). But the *spurious interrupt* check is missing. If `iar == 1023` (spurious), `handlers[1023]` is OOB. Add a check.
- §15.7 "`UCR1.RRDYEN`" (bit 9) — verify against RM. UCR1 bit 9 is RRDYEN (Receiver Ready Interrupt Enable) per §55.15.4. Correct.

### Knowledge prerequisites missing
- `mcr` / `mrc` syntax: introduced briefly in Ch13 PMU code, used here for VBAR. The mnemonic decode (`mcr p15, opc1, Rt, CRn, CRm, opc2`) deserves a one-paragraph reference card on first heavy use.
- "AAPCS" referenced in pitfalls and prose but expanded only in Ch10.
- `dsb`, `isb` introduced in §15.4 ("isb after VBAR write") and §15.10 ("`dsb; isb` around MMU/cache changes"). Define on first use: "`dsb` (Data Synchronization Barrier) waits for all preceding memory accesses to complete before the next instruction; `isb` (Instruction Synchronization Barrier) flushes the pipeline so the next fetch sees the new system state."

### Other
- §15.6 `gic_register` uses a flat array `handlers[MAX_IRQ]` indexed by INTID. Memory: 192 × 4 = 768 bytes in `.bss`. Fine for bare-metal; might be worth a comment.
- §15.9 lab 5 (trigger data abort): the suggested fix "use JTAG to inspect" is fine but for a reader without a JTAG dongle, the lab is unrunnable. Provide an alternative: "or rewrite `data_handler` to switch to SVC mode and `printf` the fault address from `DFAR`."

## Ch16 — Timers

### Readability
- "**You could use one timer for both jobs ... but separating them keeps each minimal.**" — keep.
- "**Production code would track 64-bit ticks (read low, read high, re-read low, retry on wrap — the standard 32-bit pair pattern).**" — good — this is the same pattern §18C.6 uses; cross-reference them.
- "**`udelay(1)` calibration. From Ch 16, `udelay` is GPT-based; should be accurate to within 1 µs.**" — accurate phrasing.

### MCU-engineer friendliness
- "**EPIT (Enhanced Periodic Interrupt Timer)**" — name decoded; good.
- "**GPT (General Purpose Timer)**" — also good.
- Frame against SysTick: "SysTick on Cortex-M is a 24-bit countdown timer with a single ISR; Cortex-A7 has no integrated SysTick equivalent. Linux on i.MX6ULL uses the Cortex-A7 *generic timer* for both tick and clocksource; we use EPIT (analog of SysTick) and GPT (analog of an STM32 TIM in free-run mode)." This bridge is missing.

### Missing examples / figures
- A timing diagram: the IPG clock (66 MHz) feeding EPIT's down-counter loaded with 66000, hitting zero every 1 ms, triggering IRQ.
- GPT register bit-fields: a one-figure diagram of `GPT_CR` showing `EN, ENMOD, FRR, CLKSRC[8:6], SWR[15]` highlighted.
- A picture comparing PMU CCNT (cycle-precise, clock-tied) vs GPT (time-precise, divided to 1 MHz). Useful for "when do I use which."

### Technical errors
- §16.2: "`PRESCALER = 0 (divide-by-1)`" in EPIT discussion. EPIT_CR has PRESCALER at bits [15:4] (12 bits). 0 means /1. Correct.
- §16.2 GPT prescaler "65 = divisor 66". Register field `PRESCALER[11:0]` value N means divide by N+1, so 65 → /66. Correct.
- §16.3 EPIT IRQ ID: "GIC SPI ID for EPIT1 = 88 on i.MX6ULL (RM Table 3-1). Verify." Per RM Table 3-1 (entry 56: "epit1 - EPIT1 output compare interrupt"), the listed IRQ is 56, which gives GIC INTID = 56 + 32 = 88. Correct under the SPI+32 convention. But the comment "GIC SPI ID = 88" is again confused — 56 is the SPI ID; 88 is the GIC INTID. Same issue as Ch15. Fix wording.
- §16.3 "Bits to enable in EPIT_CR: (1 << 25) CLKSRC, (1 << 22) IOVW, (1 << 3) RLD, (1 << 2) OCIEN, (1 << 1) ENMOD, (1 << 0) EN." Per RM §30.5.1 EPIT_CR: CLKSRC[25:24] (2 bits). Writing `1 << 25` sets bit 25 alone, which is CLKSRC = 0b10 (high-frequency reference). The chapter intends "peripheral clock" which is CLKSRC = 0b01, i.e., `1 << 24`. **Bug.** Verify and fix.
- §16.3 IOVW bit position: per RM §30.5.1, IOVW is bit 17, not bit 22. **Bug** — verify and fix.
- §16.2 GPT_CR bits used: "`(1 << 9) FRR free-run, (1 << 1) ENMOD, (1 << 6) CLKSRC, (1 << 0) EN`". Per RM §29.5.1 GPT_CR: CLKSRC[8:6] (3 bits). `1 << 6` = CLKSRC = 0b001 = peripheral clock. Correct. FRR is bit 9. Correct. ENMOD is bit 1. Correct. EN is bit 0. Correct. Good.
- §16.5 "A 4 MB write + 4 MB read on DDR3 at 396 MHz takes ~30 ms (≈ 250 MB/s). At 696 MHz CPU that's ~21 million CPU cycles. The cycle/µs ratio should be ~696, matching the CPU clock; if it isn't, your clock initialization (Chapter 13) is wrong." — Math: 30 ms = 0.03 s. At 696 MHz CPU, 30 ms = 0.03 × 696e6 = 20.88 million cycles. Correct. Cycle/µs at 696 MHz = 696. Correct.

### Knowledge prerequisites missing
- "Jiffies" is a Linux kernel term meaning "the tick counter." The chapter uses `jiffies_ms` without explaining; an MCU engineer who's seen FreeRTOS knows `xTickCount` but not `jiffies`. One footnote: "Linux calls this counter `jiffies`; we keep the name as forward-compatibility."
- W1C (write-1-to-clear) is used several times without expansion. First-use definition: "the status flag is cleared by writing 1 to it, *not* by writing 0. This is conventional for sticky flags in ARM peripherals."

### Other
- §16.4 main() does `uart_init(); clocks_init(); uart_init();`. The double init is intentional (clocks change → UART divisors stale). Comment it.
- §16.6 lab 4 "Inside `epit_isr`, `printf("tick\n")`." `uart_putc` polls; printf is heavy. The lab is valid but the result at 1 ms tick × 87 µs per character × ~5 chars/line = 435 µs per tick — close to 1 ms — the system will spend half its time inside the ISR. Note this as the *teaching* point of the lab.

## Ch17 — MMU and caches

### Readability
- "**The last bare-metal infrastructure piece.**" — keep.
- "**Our way is harder to misconfigure.**" — keep.
- "**The 10× factor is real and is the reason Linux insists on having caches before doing anything useful.**" — keep.
- "**Memory-mapped IO that wrongly cached: works on a board where MMU is off, breaks the moment caches are on.**" — paraphrasing; the §17.7 wording is "code works on a board where MMU is off, breaks the moment caches are on." Slightly awkward — should be "code that works without the MMU on breaks the moment caches turn on." Re-flow.

### MCU-engineer friendliness
- Cortex-M3/M4/M7 has an *optional* MPU (Memory Protection Unit) with 8 or 16 regions, no virtual-physical translation. Cortex-A7 has an MMU with 1 MiB sections (and 4 KiB pages via L2). Frame the leap explicitly: "MPU: protection only, VA=PA, region table. MMU: protection + translation + caching attributes, full page table." This is the chapter's biggest opportunity to bridge.
- The "short descriptor" vs "long descriptor (LPAE)" choice — explain in one paragraph that LPAE is needed for >4 GiB physical, which we don't have.
- §17.6 cache maintenance: "Before a DMA peripheral reads from a buffer, the CPU must **clean** the buffer's cache lines." Frame this with Cortex-M analog: "On Cortex-M7 with DMA you've maybe seen `SCB_CleanDCache_by_Addr` / `SCB_InvalidateDCache_by_Addr`. The Cortex-A7 versions are CP15 ops; same intent, different mnemonics." Then the readers' knowledge transfers.

### Missing examples / figures
- **The L1 entry bit layout diagram (Critical, identified in user prompt).** §17.2 has a quasi-figure but it's misaligned and bit numbers are confusing ("TX EX") . Redraw as ASCII with bit ranges clearly stamped:
  ```
   31      20  19  18  17 16 15 14   12 11   10 9  8   5 4 3 2 1 0
  ┌──────────┬───┬───┬───┬──┬───┬──────┬─────┬───┬─────┬──┬─┬─┬─┬─┐
  │ Sect base│NS │ 0 │nG │ S│AP2│TEX[2:0]│AP[1:0]│IMP│Dom │XN│C│B│1│0│
  └──────────┴───┴───┴───┴──┴───┴──────┴─────┴───┴─────┴──┴─┴─┴─┴─┘
  ```
  with TEX/C/B encodings table beneath.
- **A 4 GiB virtual-to-physical map.** Show the 4096 L1 entries as a stack: 0..0x009 device, 0x009 OCRAM (Normal), 0x00A..0x07F device, 0x080–0x09F DRAM (Normal), 0x0A0..0xFFF device. (Or whatever exact mapping the code produces.)
- **A two-stage figure of "page table walk" for a hypothetical access.** Show the CPU emitting a VA, the MMU splitting VA[31:20] as L1 index, looking up the L1 entry, extracting the section base, concatenating with VA[19:0] to form PA, sending PA to the bus.
- **Before-MMU / After-MMU bandwidth comparison.** §17.8 has a table; promote it to a chart-style ASCII or at minimum bold the 10× factor.

### Technical errors
- §17.2 bit layout figure includes "TX EX" — that should be "TEX". Typo.
- §17.2 AP encodings: "For 'full access at PL1, no access at PL0,' AP = `0b001` → AP2=0, AP[1:0]=01. For 'full access at PL1 and PL0,' AP = `0b011`." Per ARM ARM B3.7.1: AP[2:0]=001 means PL1 RW, PL0 no access. AP[2:0]=011 means PL1 RW, PL0 RW. Correct.
- §17.3 `__attribute__((aligned(16384)))` is correct (L1 table base alignment). But the size of the table is `4096 × 4 = 16384` bytes, which matches the alignment. Good — note this coincidence in prose.
- §17.3 `invalidate_dcache_all` uses "256 sets × 4 ways" hardcoded. Per Cortex-A7 TRM the L1 D-cache is 32 KB with 4-way set-assoc and 64-byte lines: 32768/(4×64) = 128 sets, not 256. **Probable bug.** Verify against `CCSIDR_EL1` (in 32-bit ARM, `CCSIDR`) which tells you `(NumSets-1)` and `(Associativity-1)`. The chapter even mentions "256 sets, 4 ways, 64-byte lines" inline (twice in §17.3 and §17.10). If wrong, all the "invalidate D-cache" inner-loop iterations are wrong.
- §17.3 set/way invalidate mnemonic and operand layout: per ARM ARM, the DCISW operand is `way[A-1:A-W]:set[L+S-1:L]:level[3:1]:...` where W = log2(associativity), S = log2(num_sets), L = log2(line_size). For Cortex-A7: way occupies bits [31:30] (W=2), set occupies bits [13:6] (S=8 for 256 sets, or [12:6] S=7 for 128 sets), line bits [5:0]. The chapter writes `(way << 30) | (set << 6)`. If sets=128, set should be in [12:6], which means `(set << 6)` for set up to 127 works (fits in bits 6..12). Verify against the geometry above.
- §17.3 `cp15_write_dacr(0x55555555)`: each domain is 2 bits, 16 domains. `0x5 = 0b0101` → bits[1:0]=01 (client). `0x55555555` = all 16 domains as client. Correct.
- §17.4: "Roughly an 8× speedup on the memtest. The exact ratio depends on access pattern; sequential memcpy can hit 10–15× with both caches on." Believable for L1-resident sizes; 4 MB doesn't fit in 32 KB L1, so the L1 D-cache is mostly thrashing and the *L2* (128 KB) takes over. The "10–15×" feels optimistic for 4 MB — likely the right ballpark is 4-8× for that size. Validate with a real measurement if possible.
- §17.6 `dcache_clean_va` macro: "DCCMVAC". Verify: per ARM ARM, the `DCCMVAC` op (Data Cache Clean by Modified Virtual Address to PoC) is `mcr p15, 0, Rt, c7, c10, 1`. Correct.

### Knowledge prerequisites missing
- "PL0/PL1" privilege levels are mentioned but never defined. One sentence: "Cortex-A7 has Privilege Level 0 (user mode) and Privilege Level 1 (everything else: SVC, IRQ, etc.). We are always at PL1 in this book."
- "VIPT cache" mentioned in §17.9 lab 4. "Virtually Indexed, Physically Tagged" — Cortex-A7 L1 caches are VIPT. Define on first use.

### Other
- §17.6 cache maintenance ops: `dcache_clean_range` example is good. Add: "Linux kernel calls these `__cpuc_clean_dcache_range`, `__cpuc_inv_dcache_range` etc. in `arch/arm/mm/cache-v7.S`; the names differ but the CP15 ops are the same."
- §17.9 lab 4 "Construct this [aliasing] by adding a second mapping in your page table" — the lab is interesting but quite advanced for a Part II reader. Mark it `(optional/advanced)`.

## Ch18 — Optional bare-metal peripherals

### Readability
- "**Confidence that the Linux abstractions are not hiding magic. Every subsystem callback eventually pokes the registers in this chapter.**" — keep.
- "**Touching it raw, once, removes the mystery.**" — keep.
- "**This is how the rest of the book uses the bare-metal foundation: not as a thing we keep building on, but as a *mental rosetta stone* for understanding the higher layers.**" — strong closing.
- "**Annoying but unambiguous.**" (re: 1 kHz tone) — funny; keep.

### MCU-engineer friendliness
- I²C: MCU engineers know Phillips/NXP's `IC1`/`IIC` controllers and STM32's `I2C1`. State once: "The i.MX I²C peripheral is the same Philips IP that NXP ships on Kinetis and on many other parts. Same registers, same names — you may have used it under a different memory base." This frames the chapter as "you already know this."
- SPI/ECSPI: same. "ECSPI is a more flexible variant of the classic Philips SPI. CPOL/CPHA/MSB-first/CS-as-software work the same."
- The "driver shape that repeats" in §18.5 is good. Make it a numbered figure / template that the rest of the book can refer back to.

### Missing examples / figures
- I²C transaction timing: a waveform showing START / address+W / ACK / register / ACK / repeated START / address+R / ACK / data / NAK / STOP. Most i.MX engineers haven't seen the i.MX bus controller emit this; the wave makes the polled state machine click.
- ECSPI burst-length and FIFO layout — a small diagram of the 32-bit TXDATA/RXDATA being interpreted as a single 8-bit burst would help.
- §18.4 mentions cache+DMA but doesn't draw the issue. Add a tiny "cache coherency problem" figure: CPU writes to `framebuffer[]` → lines in L1 cache → physical DRAM still has old → eLCDIF reads physical DRAM → stale.

### Technical errors
- §18.3 ECSPI `CONREG` write `(1u << 4)`: per RM §21.6.3, CONREG bits [7:4] are CHANNEL_MODE[3:0] (per-channel master/slave). `1 << 4` sets CHANNEL_MODE[0]=1 → channel 0 master. Correct.
- §18.3 CONFIG register: `(1u << 0) | (1u << 12)`. Per RM §21.6.4 CONFIGREG: bit 0 = SCLK_PHA0 (CPHA for CS0); bit 12 = SS_POL[0]. Setting CPHA=1 and SS_POL=1 may not match the W25Q32 (CPOL=0/CPHA=0 mode is standard for JEDEC ID read). Verify; the comment "/* SS_CTL_0 + SS_POL_0 */" doesn't match the math (SS_CTL is at bits [11:8]; SS_POL is bits [15:12]). Likely incorrect; revisit.
- §18.2 I²C read sequence: "**The 'read I2DR' step is doubled because the first read latches the byte; the second returns it.**" Actually the i.MX I²C: clearing `IIF` after the address-ACK starts the next byte fetch (clock pulses on SCL); the next byte appears after the read. The "doubled read" is the dummy-read-to-start-clocking idiom. Worth one more sentence explaining *why* (the read of I2DR triggers the next 9 clock cycles).
- §18.2 `i2c_init`: `REG(I2C_IFDR) = 0x15`. Per RM Table 31-3 IFDR encoding, `0x15` = divider 320 → at 66 MHz IPG → 206 kHz, not 100 kHz. The comment "~100 kHz from 66 MHz" is wrong. For 100 kHz, IFDR should be ~`0x1E` (divider 640) or `0x18` (divider 480). Recompute.

### Knowledge prerequisites missing
- ELCDIF, eMMC, eSPI — the "e" prefix means "enhanced" but readers wonder. One footnote: "NXP's convention: `e<thing>` is enhanced (more FIFO, more channels) compared to the simpler base IP."
- JEDEC ID lookup: "EF 40 16" decoded as Winbond W25Q32 — explain how to look up JEDEC manufacturer codes (jedec.org / SPI Flash Programmer table).

### Other
- §18.4 LCD section is acknowledged-incomplete ("Pseudocode" + "Omitted here; panel-specific"). For a chapter where the reader is supposed to run code, this section reads as a placeholder. Either (a) provide a complete LCD bring-up for the specific Point Atom carrier panel, or (b) move LCD to "Going deeper" and remove the pseudocode skeleton.
- §18.6 transition into Part III is excellent. Keep.

## Ch18A — Project organization

### Readability
- "**Once a bare-metal project crosses ~500 lines and ~3 peripherals, the single-file layout costs more than it saves.**" — keep.
- "**It is boring. It is also the most-used file in your project for the next decade if you keep using i.MX6ULL.**" — keep.
- "**The 30-vs-10-min number is what matters.**" — keep.

### MCU-engineer friendliness
- An MCU engineer using STM32 CubeMX has seen `stm32f4xx.h` (CMSIS struct-based header) and per-peripheral driver folders (`stm32f4xx_hal_uart.c` etc.). The chapter's BSP layout is essentially a hand-written CubeMX-equivalent. Open the chapter with one sentence: "If you've used STM32CubeMX, this is the layout you got for free; here we build it deliberately, so you understand why the structure exists." This grounds the whole chapter.

### Missing examples / figures
- A "before / after" file-tree diagram. The chapter has a one-line "Chapter 16 code" then a target tree; visually compare them side-by-side.
- A "header dependency graph" — `imx6ull.h` at the bottom, `bsp_*.h` above it, `main.c` and `bsp_*.c` at the top with arrows showing includes. Helps the §18A.9 "header layering" warning click.

### Technical errors
- §18A.5 Makefile uses `find . -name '*.o' -delete` in clean. Cross-platform issue: on Windows-MSYS / Cygwin / WSL this should still work; on bare Windows CMD it won't. Note the dependency on a POSIX environment (which the rest of the book already assumes).
- §18A.5 wildcard usage `$(wildcard bsp/*/*.c)` recurses one level only. If a peripheral subfolder grows nested files, the build silently skips them. Either document the one-level constraint or use `$(shell find bsp -name '*.c')`.

### Knowledge prerequisites missing
- Makefile pattern rules (`%.o: %.c`), variables, automatic vars (`$@`, `$<`). The chapter assumes these; for an MCU engineer who uses IAR's project-file-only build, a one-paragraph Make primer would help. Or reference an earlier chapter (Ch04? Ch08?) where Make basics were introduced.

### Other
- §18A.7 SDK sidebar is good. Add a one-line: "We use `REG(addr)` macros in this book to keep addresses visible. Production code on NXP parts typically uses `MCIMX6Y2.h` struct-style access."
- The chapter could end with a "checklist for refactoring an existing project" — 5 bullets — making §18A.8 lab 1 more guided.

## Ch18B — Button input and beep

### Readability
- "**Production code retries.**" (re: I²C ACK polling) — keep.
- "**Annoying but unambiguous.**" — repeat from Ch18 — different sentence here, but mind the repetition if you reuse.
- "**The explicit silencing line is not decoration.**" — keep.
- "**The right answer for production: drive BEEP from a *PWM peripheral* ... we plumb the same buzzer via the PWM framework instead of bit-banging.**" — clear forward link.
- "**Why active-low via a transistor? The buzzer draws more current than a bare GPIO can sink without risking the SoC's IO drive specs.**" — accurate for a piezo; piezos are nearly capacitive — peak inrush current can exceed GPIO drive. Keep.

### MCU-engineer friendliness
- §18B.2 "**The classical fix in 1980s firmware was a 20 ms hardware RC filter on the input.**" — good. Add: "On STM32 you may also have seen TIM2 with an external clock from the button used as a debouncer — same idea via a different mechanism."
- §18B.2 sliding-window debouncer with `key_history` is the same Ganssle pattern. Cite Ganssle inline (§18B.7 has it; promote to the body).

### Missing examples / figures
- A bouncing-switch waveform vs the sliding-window sample's view (8 ticks of 0 followed by some bouncing 0/1 then steady 1). Makes the 80 ms validation visible.
- The PNP-transistor circuit (3V3 → buzzer → C → Q1 collector; Q1 base ← GPIO via R; Q1 emitter ← GND) as a small ASCII schematic. Reader who doesn't read schematics needs help.

### Technical errors
- §18B.1: "**KEY0 — a normally-open momentary tactile switch wired between the UART1_CTS_B pad (which in ALT5 becomes GPIO1_IO18) and GND.**" Verify: in i.MX6ULL IOMUX, UART1_CTS_B has ALT5 = GPIO1_IO18 (per RM Table 32-X). Correct based on the IOMUX table.
- §18B.3: `REG(IOMUXC_SNVS_BASE + 0x00) = 5;` — the SNVS IOMUXC base is at `0x02290000` on i.MX6ULL (separate from main IOMUXC at `0x020E0000`). The chapter never defines `IOMUXC_SNVS_BASE`. Fix.
- §18B.3 GPIO5_BASE = `0x020AC000` (per Ch18A). GPIO5 *is* in the SNVS power domain on i.MX6ULL — its register addresses live in the regular AIPS-1 space but the pins are SNVS pads. Worth one sentence clarifying.
- §18B.6 pitfall "EPIT tick too fast. A 1 ms tick × 8-deep history = 8 ms" — if your `key_history` is masked to `0xFF` (8 bits), then 8 ms total at 1 ms tick. Math is right.

### Knowledge prerequisites missing
- "Passive vs active buzzer" distinction in §18B.6 pitfall — actually mentioned. But the §18B.3 prose just says "passive piezo." Add the active-vs-passive callout near the top of §18B.3, not just in pitfalls.

### Other
- §18B.4 `key_tick()` is called from the EPIT ISR. ISR running `printf`-via-poll-UART is risky if `key_tick` later calls `on_key_press` which prints. The chain works because `uart_putc` polls (no IRQ recursion), but the call depth in ISR context is non-trivial. Comment on this; it's also a teaching opportunity for §18B.5 lab 3.

## Ch18C — Bare-metal RTC

### Readability
- "**While the main SoC sleeps or browns out, SNVS keeps counting.**" — keep.
- "**This is the lab that makes SNVS feel real.**" — keep.
- "**The error is rare (~once per 2^15 reads) but real.**" — keep.
- "**The fix is in hardware.**" — keep.

### MCU-engineer friendliness
- The "separate power domain" framing (§18C.1) is excellent — MCU engineers from STM32 know the LSE/BKP-domain pattern (STM32's RTC + backup registers are in a separate VBAT-powered domain). Cite the analogy: "STM32's RTC + backup registers live in a VBAT-backed domain; i.MX's SNVS is the same idea, with the additional security-friendly features (tamper, secure secrets)."

### Missing examples / figures
- A power-domain diagram: VDD_SOC_IN (main), VDD_SNVS_IN (always-on / VBAT), with the SNVS oscillator, counter, and scratch SRAM inside the VDD_SNVS_IN island.
- The 48-bit counter layout: a strip showing bits 47:32 in `LPSRTCMR`, bits 31:0 in `LPSRTCLR`, the 32 kHz tick rate, and the "shift right by 15 = seconds" derivation.

### Technical errors
- §18C.3: "**The actual counter ticks at 32 kHz, but the architectural view splits it: bit 14 of `LPSRTCLR` increments at 2 Hz; treat upper 32 bits of the 48-bit concatenation as seconds.**" The wording is confused. The SRTC clocks at 32.768 kHz so the LSB increments at 32768 Hz (period 1/32768 s ≈ 30.5 µs). Bit 15 increments at 1 Hz (1/2 Hz pair). The "upper 32 bits of the 48-bit concatenation as seconds" works only after shifting right by 15. Re-explain cleanly: "The 47-bit counter (`LPSRTCMR[14:0]:LPSRTCLR[31:0]`) ticks at 32.768 kHz. Bits[46:15] count seconds; bits[14:0] are sub-second."
- §18C.4 `rtc_get_seconds`: `uint64_t raw = ((uint64_t)hi1 << 32) | lo;` then `return raw >> 15;`. The high register is only 15 bits wide (`LPSRTCMR[14:0]`), so shifting it << 32 places its high bit at position 46 — correct for a 47-bit counter. The chapter says "32 bits high, 32 bits low" but `LPSRTCMR` is not 32 bits of seconds; it's 15 bits of (high part of the 47-bit count). **Verify per RM §47**. The computation may be off-by-shift if `LPSRTCMR`'s low 15 bits are the high part.
- §18C.4 `rtc_set_seconds`: writing `raw = s << 15` then writing the high/low pair. Same width concern.

### Knowledge prerequisites missing
- "32.768 kHz" — why this specific frequency? Because 2^15 = 32768. Spell out the connection: "32768 Hz is chosen so that bit 15 ticks at 1 Hz, giving an integer-second sub-counter."

### Other
- §18C.5 `format_secs` has unused locals (`(void)out; (void)buf; (void)days; ...`). Cleanup before publication.
- §18C.7 lab 5 (wall-clock UNIX time) is a great exercise but pulls in `gmtime`-style date math; mention that the standard `<time.h>` is unavailable bare-metal and the reader will need to roll their own (or limit to UTC seconds → readable string).
