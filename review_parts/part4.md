# Part IV — Kernel: Review

## Cross-cutting observations

- **DTS path is stale for v6.5+.** Every chapter (25, 26, 27, 27A) refers to `arch/arm/boot/dts/imx6ull-*.dts` and `arch/arm/boot/dts/Makefile`. Since v6.5 (mid-2023), mainline reorganised ARM 32-bit DTS into per-vendor subdirectories: i.MX files live under `arch/arm/boot/dts/nxp/imx/`. The book pins to v6.6 in Ch 25 (`git checkout v6.6`), so every cited path is wrong. Either pin to a pre-v6.5 tag (`v6.1` LTS works) or globally update paths to `arch/arm/boot/dts/nxp/imx/imx6ull-14x14-evk.dts`. This affects the Makefile snippet in §27.2 too — that snippet now lives in `arch/arm/boot/dts/nxp/imx/Makefile`.
- **MCU-bridge style applied unevenly.** Ch 25 and Ch 26 have light bridging; Ch 27 has one excellent §27.11 bridge but most other DT mechanics arrive without analogy. Ch 28 has almost no MCU comparisons despite covering material (page tables, idle thread, BSS zeroing) that maps cleanly onto bare-metal startup code the reader has already written. Suggest a consistent "MCU parallel" sidebar pattern, one or two per chapter.
- **First-time term policy.** "platform_device", "platform_driver", "phandle", "tmpfs", "devtmpfs", "udev", "mdev", "regmap", "devm_", "CONFIG_OF", "EXPORT_SYMBOL_GPL", "noinline __ref", "user_mode_thread", "kernel_thread" all appear without inline definition somewhere across these chapters. Decide whether to define on first use or to add a Part IV glossary appendix; right now the reader has to guess from context.
- **MCU-style line-numbered or commented register-map diagrams are absent across all chapters.** The author leaves them in code text. Ch 26's pre-boot contract table and Ch 28's phase-diagram are the only ASCII visuals — these work well; replicate the style.
- **Lab steps occasionally assume tooling the book has not introduced.** `picocom -L`, `cpio -H newc`, `dtc -@`, `make scripts/config`, `pip install dtschema` — each is referenced once but never previously installed. Add a per-chapter "you will need" preamble or a one-page "Part IV tooling" appendix.
- **Boot decompressor claim.** Ch 25 §25.5 says "the stub copies itself out of the way". Ch 26 §26.8 says "the kernel is < 16 MiB" justifies `0x83000000` for DTB. These two together undersell the rule: on ARM the decompressor by default places the decompressed kernel at `ZRELADDR` (`0x80008000` on i.MX6ULL) and walks upward; the DTB at `0x83000000` is safe because it's above the 16 MiB the kernel needs at run time, **not** because the compressed image is small. Reader will infer the wrong rule when they bump kernel size.

## Ch25 — Building mainline Linux

### Readability
- §25.1, "thousands of patches on top" is fine but the surrounding paragraph is choppy: "The NXP fork for i.MX6ULL is `linux-imx`, currently pinned around `5.15` and `6.6` depending on the branch." Two clauses joined by "depending on the branch" reads stilted to an ESL reader. Suggest: "NXP forks mainline into `linux-imx`. Active branches are pinned to `5.15` and `6.6`; older branches exist for legacy products."
- §25.3, "Every Y in `.config`" — should be "Every entry" or "Every line". "Y" reads like a placeholder.
- §25.4, "Three independent targets" is misleading — `zImage` depends on the same Makefile-generated objects as `modules` if those modules are `=y`. Reword to "three artifact groups" or "three build targets".
- §25.4 "First build takes 5–10 minutes on a modern host depending on `-j` parallelism. Subsequent incremental builds are seconds." — split to two sentences without "depending on": "On a modern host with `-j$(nproc)`, the first build takes 5–10 minutes. Incremental rebuilds finish in seconds."
- §25.9 pitfalls — "aaprcp" is a typo (probably "aarch64"-related or "aapcs"). Fix.

### MCU-engineer friendliness
- §25.1 "vendor BSPs" — bridge to what the reader knows: "Like the STM32CubeMX HAL: the vendor's curated, well-tested but slow-moving snapshot. NXP's `linux-imx` is the equivalent for i.MX."
- §25.2 directory layout — add a one-line note next to `arch/arm/kernel/`: "MCU equivalent: vendor `startup.s` and `system_xxx.c` files — the bring-up code that runs before `main`."
- §25.4 — the `=y` vs `=m` distinction needs the bridge: "`=y` is what you're used to — code linked into the final binary. `=m` is *new* to you: a separately-loadable driver, a `.ko` file that the running kernel can `insmod` and `rmmod`. There is no MCU equivalent; it's one of Linux's defining capabilities."
- §25.4 table — `vmlinux` "ELF with full debug info" — bridge: "Like the `.elf` your STM32 toolchain produces alongside the `.bin`. Same idea: full symbol table for the debugger."
- §25.5 — the bare-metal reader has done their own decompressor exactly never. Compare to "an STM32 bootloader that XIPs out of flash" vs "Linux's compressed kernel that *self*-decompresses". Spell out the novelty.

### Missing examples / figures
- After §25.2 directory layout add a "where does the equivalent live in a typical MCU project?" two-column comparison table (e.g., `arch/arm/kernel/head.S` ↔ `startup_stm32f4xx.s`, `kernel/sched/` ↔ "your RTOS scheduler", `drivers/tty/serial/imx.c` ↔ "your `uart.c` HAL", etc.).
- After §25.4 add an artifact-flow ASCII diagram complementing §25.5's wrapping diagram: a left-to-right "source files → object files → vmlinux ELF → Image → zImage → boot" pipeline so the reader sees the full chain in one figure.
- §25.4 "What just got produced" — show one screenful of `size vmlinux` output (`text data bss dec hex filename`) so the reader sees the segment sizes. Reinforces the bare-metal mental model (`.text/.data/.bss`).

### Technical errors
- §25.3 reads "`imx_v6_v7_defconfig` (formerly `imx_v7_defconfig`) is the omnibus i.MX configuration that covers every i.MX SoC the v6/v7 ARM cores support — i.MX5, i.MX6 (all variants including ULL), i.MX7." This omnibus does *not* cover i.MX5 (that's `imx_v6_v7_defconfig` for v5 series — actually some i.MX5 boards are covered, but framing it as "every i.MX SoC" is too broad). Verify: in v6.6, `imx_v6_v7_defconfig` covers i.MX31/35/27 (v6), i.MX5/6/7 (v7). Tighten the claim.
- §25.4 the table row `arch/arm/boot/Image` says "rarely used on ARM32 (used on AArch64)" — true but worth noting that `Image` *is* what some bootloaders prefer on ARM32 with FIT images. Not an error, but the parenthetical undersells.
- §25.6 "Entry point address: 0x80008000" — confirm. On i.MX6ULL DRAM base is `0x80000000` and the ARM Linux convention is `PHYS_OFFSET + 0x8000`. Correct, but worth noting that this is the *physical* entry; the virtual `_text` is at the kernel's virtual base (`PAGE_OFFSET + TEXT_OFFSET` = `0xC0008000` historically; with `CONFIG_VMSPLIT_*` it varies). The reader will check the wrong number against `vmlinux`.
- §25.8 lab #2: `init/version-timestamp.c` — that filename does not exist in mainline v6.6. The banner string is built in `init/version.c` and `init/version-timestamp.c` only exists conditionally on some configs; `kernel/Makefile` and `scripts/mkcompile_h` are involved. Verify before publishing; reader will copy/paste and fail.
- §25.10 path "`Documentation/arch/arm/`" — modern path is `Documentation/arch/arm/` in v6.5+; pre-v6.5 it was `Documentation/arm/`. Pin to whichever version you're using.

### Knowledge prerequisites missing
- §25.2 introduces `arch/arm/boot/compressed/` without explaining what that subdirectory's contents do until §25.5. Forward-reference or move §25.5's diagram concept up.
- §25.3 uses `CONFIG_ARCH_MULTIPLATFORM=y` and `CONFIG_SOC_IMX6=y` without ever defining "Kconfig symbol", "compiled in (`=y`) vs module (`=m`)", or the `.config` mechanic — that lands in Ch 30. Add a 2-sentence forward-reference in §25.3: "We treat `.config` as a black box here; Ch 30 is the deep dive."
- §25.4 references "the version's vermagic string" in pitfalls — never defined. Add one sentence.
- §25.7 says `O=` "puts every generated file in a sibling directory" without explaining *why* out-of-tree builds matter beyond `git status` cleanliness (parallel configs, faster clean, CI sharing). Worth two more sentences.

### Other
- Lab step 5 says "`ccache` is the reason if you have it installed; otherwise the same speed." That second clause is wrong — without ccache, `make distclean` forces a full recompile, much slower than incremental. Verify and rewrite; the lab as written will confuse the reader who runs it.
- §25.2 — the i.MX clock-driver path is `drivers/clk/imx/`, written correctly, but elsewhere when bindings are referenced the path is the older flat one. Be consistent.

## Ch26 — Booting the kernel from U-Boot

### Readability
- §26.1 "Get `r2` right and a 95% chance the kernel boots; get it wrong and you stare at silence wondering what's happening." — grammar is off. Suggest: "Get `r2` right and the kernel boots ~95% of the time. Get it wrong and you stare at silence."
- §26.2 "The address was chosen for two reasons" — passive and clipped. Suggest: "We picked `0x82000000` for two reasons: it sits 32 MiB above the DRAM base (`0x80000000`) so it doesn't collide with U-Boot's relocated image near the top of DRAM, and it leaves room below for the decompressed kernel to land at the canonical `0x80008000`."
- §26.3 "If this token is wrong, you see no kernel output." reads abrupt; expand: "If `console=` names a device the kernel cannot find, every `printk` after console init goes nowhere and you see no kernel output past the early-decompressor banner."
- §26.4 caption "Read every line. Each tells you something concrete:" — split. "Read every line. Each one carries a piece of state the kernel just discovered."
- §26.5 "Symptom: silence." appears three times in one bullet list. Vary: "you see nothing", "the boot log is empty", "the UART stays quiet."

### MCU-engineer friendliness
- §26.1 — the pre-boot contract table needs the bridge: "This is the kernel's ABI to the bootloader. The MCU equivalent is the reset-vector contract in your STM32 startup code: the bootloader (or ROM) hands off in Thumb mode, MSP loaded from `0x0`, PC from `0x4`. Same idea — just more registers carrying state."
- §26.2 — `bootz` looks like magic. Bridge: "`bootz` plays the role your STM32 bootloader's `JumpToApp()` plays: it sets up the handoff state then `bx` into the application. The complication is that the 'application' (Linux) wants a DTB pointer in `r2`, where your STM32 app only wanted `SP` in `MSP`."
- §26.3 — `bootargs` deserves explicit bridging to "what an MCU engineer has never seen": the runtime-parsed command line. "Bare metal has no equivalent. The closest analog is a config struct you set in flash before boot, except this string is dynamic and the kernel parses dozens of tokens at startup."
- §26.4 boot-log walk-through — bridge `MIDR` to a concept the reader owns: "MIDR is the ARM Cortex equivalent of `DBGMCU_IDCODE` on STM32 — the silicon-readable 'what am I'."
- §26.4 — `CMA: Reserved 64 MiB` is unintroduced. Bridge: "Like reserving a heap pool at link time, but at run time and from the page allocator. Used when a peripheral needs a physically-contiguous DMA buffer larger than a single page."

### Missing examples / figures
- After §26.1 add an ASCII handoff diagram: U-Boot DRAM map immediately before `bootz` — show where U-Boot itself lives (top of DRAM), where the zImage is loaded, where the DTB sits, and which register holds which address. The reader has the bare-metal mental model for memory maps; activate it here.
- After §26.4 add a labeled annotated boot-log: take the 20-line example, draw arrows from each line back to the kernel subsystem that produced it (preview of Ch 28).
- §26.5 troubleshooting — flowchart of "what to check when there's no output": is `bootargs` set? did the DTB load? did `bootz` syntax include the `-`? Diagram is more navigable than the bullet list.

### Technical errors
- §26.1 row 1 "MMU off, caches off" — i.MX6ULL U-Boot at the time of `bootz` has typically *enabled* I-cache, sometimes D-cache too, for boot speed. `cleanup_before_linux()` flushes and disables before the jump. The current wording ("MMU off, caches off … `bootz` calls `cleanup_before_linux()` before the jump") technically tells the truth but reads as if caches are off long before the jump. Tighten to "caches are flushed and disabled inside `cleanup_before_linux()` right before the jump."
- §26.2 — "this is the magic line" overstates `bootz`. It's just a regular U-Boot command. Suggest "this is the line that hands control over."
- §26.4 boot log "CPU: ARMv7 Processor [410fc075] revision 5 (ARMv7), cr=10c5387d" and accompanying table entry "`0x410FC075` decodes to ARM-implemented Cortex-A7." Verify the MIDR decode: 0x410FC075 → implementer 0x41 (ARM), variant 0xF, architecture 0xC, primary part 0x075. Cortex-A7's primary part number is 0xC07, not 0xC075. The `5` in `C075` is the revision nibble. The decode statement is slightly wrong as written; correct is "implementer ARM, part 0xC07 (Cortex-A7), revision r0p5."
- §26.4 table row "Movable zone start for each node" — accompanying boot-log line is informational and present in modern kernels but readers will not always see it. Note it's optional/conditional.
- §26.6 "`earlycon=ec_imx6q,0x02020000`" — verify the earlycon driver name. Mainline registers as `ec_imx6q` for the i.MX UART early-console. Confirm against `drivers/tty/serial/imx.c` (it uses `EARLYCON_DECLARE(ec_imx6q, ...)`)). The address `0x02020000` is UART1's base — correct per IMX6ULL RM.
- §26.8 pitfall on `CONFIG_ARCH_MULTI_V6_V7` / `CONFIG_ARCH_MULTI_V7_ONLY`: the latter symbol does not exist in mainline (the canonical symbols are `ARCH_MULTI_V7` and `ARCH_MULTI_V6_V7`). Fix.

### Knowledge prerequisites missing
- §26.1 introduces "SVC mode, IRQ/FIQ masked" — the reader knows IRQ from MCU world, but ARM-A processor modes (USR/SVC/IRQ/FIQ/ABT/UND/SYS) were not covered in Parts I–III in this depth. Add one sentence or forward to Ch 28.
- §26.3 `earlycon` is introduced here and again in §26.6. Combine: first introduction should land in §26.3 with one paragraph; §26.6 is the deep dive.
- §26.5 "VFS panic" — `VFS` is not defined yet. Inline: "VFS = Virtual File System, the kernel layer that abstracts over ext4 / vfat / NFS / etc. We meet it properly in Part V."
- §26.5 "PMIC over I²C" — PMIC was covered in Part II but ESL readers benefit from the one-line reminder.

### Other
- Lab step 3 ("Mismatch the DT") and step 4 ("Bad cmdline") are excellent — they teach failure modes by induction. Add a step 6: deliberately load a corrupt DTB (truncate the file by 100 bytes) and observe `__vet_atags` rejecting it.
- §26.8 mentions "kernel built ARMv8-only" as a pitfall — but the reader almost certainly cannot build an arm64 kernel by accident given the toolchain they have. Remove or replace with a more likely real-world trap (e.g., `CONFIG_THUMB2_KERNEL=y` mismatch with bootloader thumb-state assumption).

## Ch27 — Device Tree

### Readability
- §27.1 — "the community's response was to adopt the **Device Tree**" — fine, but the quote about Linus is informal anecdote that some readers will read as unprofessional. Either drop the quote or set it off as a sidebar.
- §27.2 "what the kernel actually consumes at boot" — fine. But the surrounding paragraph reads list-of-bullets-then-prose, then list-of-bullets-then-prose. Vary the structure.
- §27.4 — "for an MMIO peripheral like UART1, this is the register-block base address: `serial@2020000`" — slightly muddled because `@2020000` follows the *name* and the example then mentions the address again. Suggest: "The unit address comes from the device's base address on its parent bus. For UART1 (memory-mapped at `0x02020000`), the node is named `serial@2020000`."
- §27.5 "A 'cell' is exactly 32 bits." — abrupt. Expand: "A cell is the DT's atomic integer unit — always exactly 32 bits, regardless of the host architecture's word size."
- §27.6 — the heading "`compatible` — the binding key" is good. Sub-section flow then jumps to `reg`, then back to `#address-cells`, then `interrupts`. Re-order so dependencies flow forward: `compatible` → `#address-cells/#size-cells` → `reg` → `interrupts` → `clocks` → `pinctrl` → `status` → `aliases/chosen`.
- §27.11 — title "The single biggest mental shift" is duplicated wording from the chapter-opener "What" line. Pick one place to say it.

### MCU-engineer friendliness
- §27.1 — fantastic motivational opener for an MCU engineer, *but* the C-array example is from Samsung S3C2440 not i.MX. Use a fictional/redacted snippet that's more obviously similar to "what you would have written on STM32 if you booted Linux on it." Or actually reference an old `arch/arm/mach-imx/mach-mx6q_sabrelite.c`-style file that no longer exists but would have on the i.MX side.
- §27.5 "cell" — bridge: "Think of a cell as a `uint32_t` in your driver code, packed big-endian in the binary form."
- §27.6 — phandles arrive without naming. Define explicitly: "A phandle is a 32-bit unique integer the DTC assigns to every labelled node. The `&label` syntax expands at compile time to the phandle of that node. In the runtime kernel, `of_parse_phandle()` does the reverse lookup. The MCU equivalent: a pointer-by-name resolved at link time — except DT does this in a binary blob and the kernel resolves it on the fly."
- §27.8 nine-step flow — superb. Reinforce: end with one sentence "All nine steps fire automatically; the board engineer's only contribution is the DT node."

### Missing examples / figures
- §27.3 needs an ASCII tree diagram. The textual description ("`/`, then `chosen`, then `memory@…`, then `reg_sd1_vmmc:`, then `&uart1`") is hard to picture. A `tree(1)`-style figure with `/`, `chosen`, `aliases`, `memory@80000000`, `soc { aips1 { ... } }`, `&uart1`, etc., would help enormously.
- §27.6 `#address-cells`/`#size-cells` — add a 2x2 figure: parent `<1>/<1>` → child `reg = <0xA 0xB>`; parent `<2>/<2>` → child `reg = <0x0 0xA 0x0 0xB>`. Visual makes the rule click.
- §27.7 `imx6ull.dtsi` walk-through is a wall of text; add an ASCII tree of the SoC's DT hierarchy: root → `intc`, `cpus`, `clocks`, `soc { aips1, aips2, aips3, ocram, ddr-pmu }` with the AIPS bridges expanded.
- §27.8 nine-step flow — turn into a numbered flow diagram with arrows from "DTB in DRAM" → "unflatten_device_tree" → "platform devices" → "driver match" → "probe()" → "/dev/ttymxc0". Reader sees the whole pipeline.
- §27.10 — add an end-of-section ASCII showing "DT node properties" ↔ "of_* API calls" mapping (e.g., `reg = <…>;` ↔ `platform_get_resource(MEM)` / `devm_ioremap_resource`; `clocks = <…>` ↔ `devm_clk_get`; `interrupts = <…>` ↔ `platform_get_irq` / `devm_request_irq`).

### Technical errors
- §27.7 `imx6ull.dtsi` — the snippet shows `intc: interrupt-controller@a01000` with `compatible = "arm,cortex-a7-gic"`. The actual mainline binding for the i.MX6ULL GIC is `compatible = "arm,gic-400"` (with `arm,cortex-a7-gic` accepted as a fallback by some versions). Verify the exact string in current `imx6ull.dtsi`; the example will mislead a reader who greps for it.
- §27.7 `aips1: aips-bus@2000000` — modern mainline DTS uses `compatible = "fsl,aips-bus", "simple-bus"` *and* node names like `bus@2000000` (the kernel DT-bindings YAML team has been renaming `aips-bus@` to `bus@`). Verify against v6.6 `imx6ul.dtsi`.
- §27.7 mentions `ddr_pmu: ddr-pmu@21b0000` with `reg = <0x21b0000 0x10000>`. Verify — i.MX6ULL MMDC base per the IMX6ULL RM is `0x021B0000` (correct). Region size of `0x10000` (64 KiB) — verify, the MMDC register region is much smaller (~4 KiB in the RM register definition section). A 64K reg region works because it's a power-of-two MMU mapping unit but the actual register block is smaller — the YAML `reg` should reflect the actual block size, not the page.
- §27.8 step 3: "`setup_arch()` → `setup_machine_fdt(0x83000000)`" — `setup_machine_fdt` doesn't take the raw address as an argument in recent kernels; it uses the global `__atags_pointer` saved by Phase 1. Tighten the wording so the reader doesn't grep for that signature.
- §27.9 last paragraph: "the upstream driver `drivers/hwmon/tmp103.c` and its variants — verify the exact name in current sources". You're correct to flag verification, but the canonical TMP102 driver is `drivers/hwmon/tmp102.c`, not `tmp103.c`. Fix the speculation; show the real path.
- §27.6 `chosen` properties: `linux,initrd-start` and `linux,initrd-end` properties take **physical addresses**, not flag them as "where an initrd lives" without that detail. Worth a sentence.
- §27.12 lab step 4 `grep -r "fsl,imx6ul-uart" drivers/` — correct command but the reader will hit no match because mainline uses `fsl,imx21-uart` as the fallback. Worth a hint: "If grep returns nothing, try the *second* compatible string in the DT list — that's the fallback that drivers actually match."
- §27.13 "`status = "okay"` typo" pitfall says newer dtbs_check will warn on `"ok"`. Verify — dtschema currently flags `"ok"` as invalid (it's not in the enum); strengthen from "lenient about it" to "older kernels accepted `"ok"`; modern dtbs_check rejects it as invalid."

### Knowledge prerequisites missing
- §27.6 `interrupt-controller;` (empty property) marks the node as an IRQ source — but `#interrupt-cells` and the interrupt-parent inheritance chain deserve their own short subsection. Currently scattered.
- §27.6 `#clock-cells` is mentioned in passing ("the number of cells per entry comes from a `#clock-cells` property on the provider node") but never shown in an example. Show the provider's `#clock-cells = <1>;` declaration explicitly.
- §27.8 step 7 uses `struct platform_device *pdev` — the reader needs a one-paragraph "platform_device = the Linux representation of a non-discoverable bus device", because the term will be used through Part VI. Define it once here.
- §27.10 `devm_clk_get` and `devm_pinctrl_get` — both `devm_*` helpers are introduced without explaining the managed-resource pattern. Worth one sidebar: "`devm_*` functions auto-free their resource when the device is detached. Saves you from writing error-unwind code. We meet them properly in Part VI."
- §27.10 "About twenty `of_*` helpers" — name a few more in a table (of_property_present, of_property_match_string, of_iomap, of_address_to_resource). The current sample is short.
- §27.10 introduces `pdev->dev.of_node` without ever explaining `struct device` vs `struct platform_device`. Worth a forward reference: "the device structure embeds the DT node pointer; we cover the device/driver model in Ch 41."

### Other
- §27.9 overlay example uses `dtc -@ -O dtb` — the `-@` flag is necessary for overlays and never explained. Add: "`-@` instructs dtc to emit a symbol table in the DTB so phandles can be resolved at overlay-apply time."
- Lab step 5 says "compile with `dtc -@ -O dtb`" — also missing `-I dts` and the input filename in the example command line. Reader will run a broken command. Fix to the full form: `dtc -@ -I dts -O dtb -o tmp.dtbo tmp.dtso`.

## Ch27A — DT bindings YAML and dt_binding_check

### Readability
- §27A.1 — first sentence is long. "For the first ~15 years of Device Tree's life, 'bindings' lived as free-form `.txt` files in `Documentation/devicetree/bindings/`." Split: "Bindings used to be free-form `.txt` files. They lived in `Documentation/devicetree/bindings/` for the first ~15 years of DT."
- §27A.2 — "the value `true` after a name is the YAML shorthand for 'this is a valid property with no additional constraints'" — confusing because `true` in YAML is a scalar. The DT-schema rule is that `<name>: true` means "this property is allowed; inherit constraints from parent". Reword: "`uart-has-rtscts: true` says 'this property is permitted; inherit its type from the parent schema (`serial.yaml`).'"
- §27A.3 "A typical `dtbs_check` run on the i.MX tree produces ~100 warnings as of v6.6" — give the reader an action: "Don't try to fix all of them; we'll add zero new ones."
- §27A.5 pattern "A pair of related arrays whose lengths must match" — the surrounding example has no `dependencies:` clause showing how arity is *actually* enforced. The current explanation only says lengths "should" match. Either show the schema construct that enforces or relabel as "convention".

### MCU-engineer friendliness
- §27A.1 — "machine-checkable" is the key concept. Bridge: "Compare to your STM32 CMSIS SVD files: they describe the chip's registers in a machine-readable XML so headers can be auto-generated. DT bindings are the same idea — a machine-readable schema so DTS files can be auto-validated."
- §27A.2 — `oneOf` / `allOf` are JSON-Schema constructs. The MCU engineer has not seen JSON-Schema. One sentence: "`oneOf` = exactly one of these forms is permitted. `allOf` = all of these constraints apply (used for inheritance)."

### Missing examples / figures
- §27A.2 — after walking the YAML, add an ASCII showing the inheritance chain: `fsl-imx-uart.yaml` → `serial.yaml` → `serial-base.yaml` / `dtschema/types.yaml`. The reader needs to *see* what `allOf` does.
- §27A.3 — show one actual error message from `dtbs_check` when it fires. The reader has never seen the output format; they won't know what to look for. Suggest: a 5-line excerpt like `imx6ull-14x14-evk.dtb: serial@2020000: clock-name: 'ipg' is not one of ['per', 'ipg']`.
- §27A.5 — visual table of "intent → JSON-Schema construct → example" rather than free-form sections, would compress the page and help navigation.

### Technical errors
- §27A.1 "Since kernel v4.18 (mid-2018), every new binding *must* ship a YAML schema" — *strong* statement. The actual policy: since v4.18 the infrastructure existed, but the *requirement* for new bindings to be YAML was rolled in gradually and the strict-rejection policy is more recent (v5.x). Tighten: "From v4.18 the YAML infrastructure landed. Since roughly v5.x, the policy has hardened: new bindings without a YAML schema are typically rejected on the lists."
- §27A.2 `clock-names: items: [const: ipg, const: per]` — verify against current `fsl-imx-uart.yaml`. The order in current mainline matches; just confirm before printing.
- §27A.2 `fsl,uart-has-rtscts` "Deprecated, use uart-has-rtscts instead." — confirm the property is actually deprecated upstream; the schema as quoted in some kernel versions does not say "deprecated" but "obsolete" or carries the deprecation in `description`. Pin to v6.6 exactly.
- §27A.4 "Save that and run: `make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- dt_binding_check DT_SCHEMA_FILES=leds/myorg,pa-led.yaml`" — `DT_SCHEMA_FILES` takes a path relative to `Documentation/devicetree/bindings/`. The shell will not expand the comma in `myorg,pa-led.yaml` to a special character; you want the full filename. Verify the exact path syntax.
- §27A.4 binding example has `additionalProperties: false` — but if you inherit (`allOf: $ref: ...`) you generally want `unevaluatedProperties: false` (the §27A.8 pitfall says exactly this). The example as written contradicts the pitfall. Use `unevaluatedProperties: false` in the example.

### Knowledge prerequisites missing
- §27A.2 "`$id`" and "`$schema`" — JSON-Schema concepts. Define inline.
- §27A.2 "`$ref: serial.yaml#`" — explain the `#`-fragment syntax (refers to the root of the document).
- §27A.6 "inheriting from base schemas" — `i2c-controller.yaml` and `spi-controller.yaml` are mentioned, but the reader has not seen I²C or SPI bindings yet. Add a forward reference: "see Ch 41-42 for the bindings these inherit from."

### Other
- Lab step 4 ("Write your first schema") forward-references Ch 41 ("e.g., one of your own from Chapter 41 onward"). Fine, but the reader cannot do this lab today. Maybe convert to a guided exercise where the reader writes a schema for a fictional GPIO-LED variant that we provide a DTS for.
- §27A.9 references "`grep -r "unevaluatedProperties" Documentation/devicetree/bindings/`" — recommend using `--include='*.yaml'` or the reader gets noise from matching string in Python files under `dtschema/`.

## Ch28 — Kernel startup, traced

### Readability
- Phase-overview ASCII diagram is excellent; keep.
- §28.2 — "Worth pinning:" reads informal/abrupt. Suggest: "Four points worth pinning down:" then the bullets.
- §28.4 — the bullet-list of init calls runs ~50 lines of `name();` followed by a comment. After the first ten, the reader's eyes glaze. Suggest: keep the first 15 inline, then summarize "and roughly 30 more init calls" earlier (which §28.4 already does at the end). Tighter pacing.
- §28.4 "After this, `kmalloc()` works." / "After this, `schedule()` works" / "After this, IRQs from devices can be registered" — repetition of "After this" is intentional cadence and works; keep. Just verify each claim is accurate (see Technical Errors).
- §28.6 — the long `kernel_init` C snippet pasted in full (~80 lines) is too much. Cut to the structurally interesting parts (initmem free, init-path search), drop the routine bookkeeping (do_sysctl_args, pti_finalize).
- §28.7 mapping-table is gold. Highlight it more — make it a numbered figure or call-out.

### MCU-engineer friendliness
- §28.2 — `stext` and `__create_page_tables` need bridging. "Your bare-metal `Reset_Handler` set up SP, zero'd BSS, copied .data. `stext` does the same — plus it builds an early MMU page table (which you've never done because MCUs don't have an MMU) and then *enables the MMU mid-function*. The instruction after MMU-enable runs at a different virtual address than the one before. This is the single most magical line of code in the kernel."
- §28.3 `__mmap_switched` "does the C runtime setup" — bridge: "This is your `__libc_init_array` / SystemInit equivalent: zero BSS, copy initial-data, set up stack. Then it calls `start_kernel` the way your reset handler calls `main`."
- §28.4 — `start_kernel` as "the boss function" — keep, but expand: "Compare to your MCU `main()`: a long sequence of `HAL_Init()`, `SystemClock_Config()`, `MX_GPIO_Init()`, etc. `start_kernel` is the same pattern, just 200 calls deep and with a lot of internal dependency."
- §28.5 — kernel_thread / user_mode_thread / PID 0/1/2 — the MCU reader has *never* dealt with multiple tasks created from inside the kernel. Bridge: "RTOS analogy: `xTaskCreate` from inside the scheduler-startup code. The boot CPU's current stack becomes one of the tasks. The difference: PID 0 (idle) is implicit — it *is* the current execution context after `rest_init` returns, not a separately-created task."
- §28.6 — `kernel_execve` "replaces the calling task's image" is a syscall-mode concept foreign to MCU. Expand: "exec is the single most powerful syscall in Unix — it tears down the calling process's memory map, mmaps the binary at `/sbin/init`, sets the PC to the binary's entry, and returns to user space *as that program*. There is no MCU equivalent because MCUs don't reload programs at run time."

### Missing examples / figures
- After §28.2 add an ASCII showing the ARM virtual-address layout that `__create_page_tables` produces: kernel `_text`/`_etext`/`_data`/`_bss` regions, vector page, identity map area. The reader knows physical address layout from bare-metal but has never seen kernel virtual mapping.
- After §28.4 add a small "subsystem dependency graph": which init step depends on which other one (`mm_init` before `sched_init`, `init_IRQ` before `time_init`, etc.). One ASCII figure beats a paragraph of prose.
- §28.5 — diagram of "PID 0 / PID 1 / PID 2 after `rest_init`": three boxes labelled with their entry function (`do_idle`, `kernel_init`, `kthreadd`), their stack base, the CPU they're running on. Reader needs the visual.
- §28.6 — annotated diagram of the process address space *before* and *after* `kernel_execve` for PID 1 (kernel-only mapping → user mapping + kernel mapping). This is the most under-illustrated transition in the chapter.

### Technical errors
- §28.4 `start_kernel` snippet calls `page_alloc_init()` — in mainline v6.6 the corresponding function is `mem_init_print_info` / `page_alloc_init_cpuhp` (depending on whether you mean the early or the CPU-hotplug init). Verify the exact symbol present in v6.6's `start_kernel`.
- §28.4 same snippet calls `boot_cpu_init()` and `page_address_init()`, then `pr_notice("%s", linux_banner);`. In v6.6 the order has `boot_cpu_init`, `boot_cpu_hotplug_init` (later), `page_address_init`. Check the v6.6 source and reorder.
- §28.4 same snippet calls `mm_core_init()` — verify. The function is `mm_core_init` in v6.6+ (added around v6.2; before that it was `mm_init`). Correct.
- §28.4 same snippet calls `sched_init()` then `radix_tree_init()` then `maple_tree_init()`. In modern kernels `radix_tree_init` was removed (xarray took over) and `maple_tree_init` may not be a public-facing init. Verify against current `init/main.c` and prune the list to what's actually there.
- §28.4 `early_irq_init()` followed by `init_IRQ()` — both exist, order is correct, but `early_irq_init` does the irq_desc array allocation; `init_IRQ` does the GIC probe. Worth a one-line distinction.
- §28.6 `kernel_init` snippet uses `try_to_run_init_process` and four hard-coded paths (`/sbin/init`, `/etc/init`, `/bin/init`, `/bin/sh`). Mainline currently uses `try_to_run_init_process` indeed, and the four paths are correct. Good.
- §28.7 table row "`OF: fdt: Machine model: ...`" mapped to `drivers/of/fdt.c` `early_init_dt_scan` — verify. The exact `pr_info` call is in `drivers/of/fdt.c` `early_init_dt_scan_root` or similar helper, not `early_init_dt_scan` itself. Pin to the exact function.
- §28.7 table row "`Memory: 444184K/524288K available ...`" mapped to `mm/page_alloc.c` `mem_init_print_info` — verify. In v6.6 the function is `mem_init_print_info` in `mm/mm_init.c`, not `mm/page_alloc.c`. Fix the path.
- §28.9 pitfall "`free_initmem` recycles `.init.text` and `.init.data`. Function names like `init_IRQ`, `setup_arch`, `start_kernel` themselves get freed" — `start_kernel` is marked `__init` so yes, it gets freed. Confirm by `objdump -h vmlinux | grep init.text`. Correct.

### Knowledge prerequisites missing
- §28.2 — `safe_svcmode_maskall` is a macro from `arch/arm/include/asm/assembler.h`. The reader has not seen this macro and does not know what "SVC mode" is in ARMv7 (covered briefly in Part I but not in this detail). One sentence: "SVC mode is the ARM-A processor mode the kernel runs in; the bootloader may hand off in another mode (HYP, USR, etc.); this macro forces SVC and masks IRQs."
- §28.2 — `mrc p15, 0, r9, c0, c0` is a coprocessor read of the MIDR. The reader has likely never written `mrc`/`mcr`; explain inline: "ARMv7 coprocessor-15 register access; reads the Main ID Register (MIDR) into `r9`."
- §28.2 `__proc_info_begin..__proc_info_end` — linker-supplied symbols. The reader has not seen the kernel's section-symbol pattern. One sentence on how the linker script `arch/arm/kernel/vmlinux.lds.S` collects all `struct proc_info_list` into one section.
- §28.4 `__init` is used in `asmlinkage __visible void __init start_kernel(void)` — `__init`, `__visible`, `asmlinkage` all unintroduced. Define each in a small sidebar.
- §28.5 `noinline __ref` — `__ref` allows a non-`__init` function to call an `__init` function safely; the reader needs this defined.
- §28.6 `kernel_init_freeable` — vague name, no description of what it actually does. Expand the comment or replace with §-§28.6 sub-bullet.

### Other
- §28.10 "Going deeper" link to "Bootlin's 'Embedded Linux kernel' training material" — verify the link/name; Bootlin has multiple courses with similar names. Pick the right one.
- Lab step 3 — `initcall_debug` is the boot-arg; `printk.devkmsg=on` is unrelated to seeing initcalls. Drop `printk.devkmsg=on` or explain its separate purpose.

## Ch29 — Initramfs from scratch

### Readability
- §29.1 "An **initramfs** is a small filesystem image that the kernel loads into RAM before any 'real' disk filesystem is mounted." — good opening. The next sentence: "The kernel mounts the initramfs as `/`, runs `/init`, and from there `/init` can do whatever it wants — usually pivot to a real rootfs on disk, but for embedded systems the initramfs *is* the rootfs." — too long. Break into two.
- §29.2 — "30 KB. That's roughly the minimum a statically-linked C program reaches." — slightly off; with klibc you get tiny binaries (a few KB). Reword to "roughly the floor for a glibc-or-musl static binary; klibc and stripped assembly can go further."
- §29.3 "Notice the new things" — chatty. "Three new pieces:" lands cleaner.
- §29.4 — the busybox build instructions ("Settings → Build static binary (no shared libs) → [*]") are interleaved with shell commands. Separate into "1. Build busybox", "2. Configure busybox static", "3. Strip", "4. Populate rootfs", "5. Pack cpio" — numbered steps make the lab reproducible.

### MCU-engineer friendliness
- §29.1 — the initramfs concept needs the MCU bridge explicit: "An MCU has no equivalent. Closest: imagine your bootloader copying a separate flash partition into RAM, and your application using that RAM region as 'C: drive' before any SD-card driver has come up. The cpio archive is just how Linux packs that RAM disk's contents."
- §29.2 — "Build statically so we have no library dependencies on the target" — bridge: "Like building your STM32 firmware with `-static` linker option turned on — there's no `libc.so` to dlopen at run time. Linux makes dynamic linking the default and you opt out of it here."
- §29.4 — BusyBox's "applets" via symlinks — the multi-call binary pattern is foreign. Worth one sentence: "BusyBox inspects `argv[0]` at start. If invoked as `ls`, it runs the ls applet; if invoked as `sh`, the shell. One binary, dozens of personalities — saves flash."
- §29.6 init-systems table is helpful but `systemd` "powerful, big, dependency-heavy" undersells *why* it's used. One more sentence on socket activation, journald, dependency-aware service start — gives the MCU reader the context for the Part IX coverage.

### Missing examples / figures
- After §29.1 add an ASCII showing the boot-path with vs without initramfs. Two parallel timelines: "no initramfs → kernel → directly mount /dev/mmcblk0p2 → /sbin/init" vs "with initramfs → kernel → unpack cpio into tmpfs → run /init → /init does pivot_root → mount real disk → exec real init". Visual disambiguates.
- §29.2 add a hex dump of the cpio header bytes (a "newc" header is 110 chars per file entry). Show what the kernel's cpio parser sees byte-for-byte.
- §29.4 — `find . | cpio -o -H newc` produces a flat archive. Show a tree of the busybox-initramfs directory before packing (with the symlinks) and the cpio archive after. Reader needs to see "this directory becomes that file" as one figure.

### Technical errors
- §29.2 `puts("\n*** hello from a one-binary initramfs ***\n");` — `puts` adds its own newline; the explicit `\n` at the end is redundant. Reader will see a blank line. Minor.
- §29.3 `bootz 0x82000000 0x84000000 0x83000000` — verify U-Boot's bootz argument order. Per `cmd/booti.c` / `cmd/bootm.c`, `bootz <kernel-addr> [<initrd-addr>[:<initrd-size>]] [<fdt-addr>]`. The example is correct, but the §29.3 prose says "the second argument is now the initrd address (no longer `-`)" — which is right. Just confirm before publishing.
- §29.4 `mount -t devtmpfs none /dev` — works, but on a kernel built with `CONFIG_DEVTMPFS_MOUNT=y` (which §29.8 recommends), the kernel has already auto-mounted devtmpfs before init runs. Mounting again on top is harmless but redundant. Either remove the line from the rcS or note that the redundancy is intentional for the case where someone builds without `CONFIG_DEVTMPFS_MOUNT`.
- §29.4 `cd initramfs/bin; for app in $(./busybox --list)` — running `./busybox` from the *target's bin dir* may fail on the host if the binary is cross-compiled for ARM. The host can run `./busybox` only via QEMU user-mode emulation or if you happen to be on an ARM host. Replace with: run `--list` on the host using a host BusyBox or hardcode the symlink list.
- §29.4 the inittab `::respawn:-/bin/sh` — the leading `-` on `-/bin/sh` makes the shell a login shell. Worth a note; the reader doesn't know this convention.
- §29.5 `CONFIG_INITRAMFS_SOURCE="/home/you/imx6ull/initramfs.cpio.gz"` — the source can also be a directory or a cpio_list file. Mention briefly.
- §29.8 pitfall "Cpio archives don't error on missing init." — actually `init/initramfs.c` does check that `/init` exists and falls through to the `prepare_namespace` path otherwise. Verify the exact behavior: missing `/init` → kernel tries to mount `root=`; missing `/init` *and* no `root=` → panic with "No filesystem could mount root, tried…". Tighten the wording.

### Knowledge prerequisites missing
- §29.1 "tmpfs" appears without definition. One sentence: "tmpfs is the kernel's in-RAM filesystem (think `ramdisk` but reclaimable and growable). The initramfs lives in a tmpfs the kernel creates at boot."
- §29.1 "cpio" — the reader has likely not used cpio. One sentence on the format ("a sequence of (header, filename, content) records concatenated"), or a forward reference to a "What is cpio?" sidebar.
- §29.2 "musl" and "glibc" — both libc implementations appear. Quick definition: "musl is a smaller, simpler libc; glibc is the desktop default. Cross-compilers tagged `*-musleabihf` use musl. Toolchains tagged `*-gnueabihf` use glibc."
- §29.4 "Settings → Build static binary (no shared libs)" — the reader has never run busybox menuconfig. Cross-reference to Ch 30's menuconfig coverage; the navigation is similar.
- §29.6 "respawn / sysinit semantics" — System V init semantics are unintroduced. One sentence each.

### Other
- §29.7 lab step 5 — "Echo a value to `/sys/class/leds/<your-led>/brightness`" — the reader does not yet have an LED in their DT. Forward-reference to Ch 38 (GPIO chapter) or set up a simulated LED earlier.
- §29.9 "Going deeper" — "klibc — an even smaller libc-replacement than musl, designed specifically for in-kernel-cpio-initramfs static binaries." Correct, but klibc is actually used by some distro initramfs (and is mostly orthogonal to musl). Soften "designed specifically for".

## Ch30 — Kernel configuration deep-dive

### Readability
- §30.1 "The kernel has ~7000 configurable options across hundreds of `Kconfig` files scattered through the source tree." — fine.
- §30.2 — "You'll get a full-screen ncurses interface." — describe what they will see before listing keys. Currently: "From a configured tree: `make ... menuconfig` | You'll get a full-screen ncurses interface. | Navigation:" — three jumps in three sentences.
- §30.5 — "You can read every help text in `menuconfig` and learn nothing useful for hours." — informal, OK for a book in this voice but verify the author wants that tone consistently.
- §30.5 each knob's blurb is structured well; keep.
- §30.6 — "Aggressive trimming" bullet list is good. Add a one-line summary at the end: "Trimmed kernel size: 3.2 MiB. Trade-off: removed audio, USB gadget, debug info."

### MCU-engineer friendliness
- §30.1 — "Kconfig" is the kernel's analog to what the MCU engineer might know from STM32CubeMX or KConfig-style menus in IDE settings. Bridge: "Kconfig is the kernel's equivalent of your IDE's project-options dialog: select features by checkbox; the build system reads those selections and includes/excludes files accordingly. Difference: Kconfig is text-driven, scriptable, and version-controlled."
- §30.2 — "ncurses" is unintroduced jargon. Brief: "ncurses is the terminal-graphics library that draws the menu's box characters; you need no separate install on a typical Linux host."
- §30.5 — `PREEMPT_RT` mentioned but the reader's first impression of "preemption" is the RTOS kind. Bridge: "Linux defaults to non-preemptible kernel code (a syscall runs to completion). PREEMPT_RT changes this so almost every kernel codepath is preemptible — like turning the kernel into an RTOS task itself."
- §30.5 — `NO_HZ_IDLE` "saves power" — bridge: "Like your STM32 stopping the SysTick when going into STOP mode. The Linux scheduler can stop the periodic tick when idle and wake on the next scheduled timer."

### Missing examples / figures
- After §30.3 (the .config file) — show a side-by-side: `defconfig` (terse, ~324 lines) vs `.config` (full, ~2147 lines) headers, so the reader sees the size difference visually.
- After §30.5 — a single visual cheat-sheet listing the twelve knobs with their menu paths and "for our i.MX6ULL: set to X". This is a reference page the reader will revisit; making it scannable matters.
- §30.6 — a before/after `ls -lh zImage` showing the trimmed result. Currently described in prose ("A trimmed image for i.MX6ULL can reach ~3 MB"); show the actual numbers.

### Technical errors
- §30.4 "That `defconfig` file (324 lines vs 2147 for full `.config`) contains *only* the lines that differ from the architecture default." — slightly imprecise. `savedefconfig` strips lines that match Kconfig defaults *and* lines that follow trivially from dependencies. A `defconfig` is the minimal set that, when run through `make defconfig`, reproduces the same final `.config`. Tighten.
- §30.5 PREEMPT_RT description "turns the kernel into a deterministic real-time kernel (Chapter 52A is dedicated to this)" — PREEMPT_RT is *not* hard real-time deterministic in the strict sense; it's *bounded* latency. Soften to "low, bounded latency".
- §30.5 `CONFIG_FEC` menu path — verify the exact menu label. In v6.6 it's "FEC ethernet controller" (not "FEC (Freescale FEC and i.MX6UL/ULL)") in `drivers/net/ethernet/freescale/Kconfig`. The current text suggests the menu label includes "(i.MX6UL/ULL)" which it does not.
- §30.5 "MMC/SD/SDIO card support" → "Secure Digital Host Controller Interface support" → "Freescale eSDHC/uSDHC i.MX controller" — verify exact menu strings (they migrate occasionally).
- §30.6 — "Disable IPv6 / IPv4 sub-features you don't need. TCP / UDP / unicast routing — yes. Multicast routing / fib_rules / netfilter — no. Saves ~500 KB." — disabling `fib_rules` is risky; many distros require it for basic functionality even without netfilter rules. Soften to "if you don't use complex routing/policy".
- §30.7 — "`scripts/config --disable AUDIT`" — verify the symbol; `CONFIG_AUDIT` exists. Correct.
- §30.7 — "Combine multiple defconfigs" subsection is mislabeled: the example combines a *defconfig* with a *single-flag override*, not two defconfigs. Rename "Targeted Kconfig override on a base defconfig".

### Knowledge prerequisites missing
- §30.5 `CONFIG_BLK_DEV_INITRD` mentions "Initial RAM filesystem and RAM disk (initramfs/initrd)" — by Ch 30 the reader knows what initramfs is (Ch 29). Good. But the *option name* implies "BLK_DEV" — explain why a RAM-filesystem option is in the block-device subtree (historical artifact: initrd was originally a block device).
- §30.5 PREEMPT_RT "turns the kernel into a deterministic real-time kernel (Chapter 52A is dedicated to this)" — fine forward-ref; the reader doesn't need depth here.
- §30.6 — disabling "ARM_AT91 / ARM_OMAP / ARCH_BCM" assumes the reader knows these are SoC families. One sentence: "Each ARCH_* is a SoC family. ARCH_MXC is i.MX. The others are AT91 (Atmel), OMAP (TI), Broadcom, etc."
- §30.7 `scripts/config` — useful tool, no prior introduction. Explain it's a shell script wrapper around the `.config` file format that maintains dependency reconciliation.

### Other
- Lab step 4: "Find a driver currently `=y` (e.g., `CONFIG_USB_F_MASS_STORAGE`). Change it to `=m`." — verify USB_F_MASS_STORAGE is `=y` in `imx_v6_v7_defconfig` (it may be `=m` or unset by default; pick a driver that's actually `=y`).
- §30.10 "`Documentation/admin-guide/`" — there's no "Going deeper" link to `Documentation/admin-guide/sysctl/` which is where many runtime tunables live; worth a one-line cross-reference.

## Ch30A — Kernel lifecycle

### Readability
- §30A.1 — table header "Maintainer" then "Maintainer | Release cadence | Lifetime" — table is dense; consider one column at a time as separate sub-tables, or annotate the table with which columns matter for "decisions".
- §30A.2 — "The day 6.6 ships, 6.7-rc1 is already absorbing the next merge window." — vivid, keep.
- §30A.4 — table "LTS | Released | Support ends | Notes". The 6.6 row says "Default LTS pick for new 2024+ products" — the book is dated 2026; phrasing should be "as of writing" because 6.12 LTS is the current default by 2026.
- §30A.6 — the decision-framework flowchart is the highlight of the chapter. Good.
- §30A.7 — "The 4.1.15 trap is real." — informal-but-effective. Keep.

### MCU-engineer friendliness
- §30A.5 — vendor BSP "Thousands. Drivers for proprietary silicon" — bridge: "Like the STM32CubeMX HAL bundle — vendor code that lives outside your project but you depend on. Difference: NXP's BSP carries kernel patches, not just user-facing HAL. So you're forking the OS itself."
- §30A.6 — flowchart applies the same maintenance-economics lens an MCU engineer applies to "do we stay on this STM32F4 BSP or migrate to F7?" Make the parallel explicit.
- §30A.7 "4.1.15 trap" — the reader probably has not lived through inheriting a five-year-old MCU BSP. Add the MCU parallel: "Imagine inheriting an STM32F4 firmware built against StdPeriph 1.4.0 from 2014. The HAL is gone. The toolchain is ancient. New libraries assume CMSIS 5. Migration is mandatory. Same situation, kernel scale."

### Missing examples / figures
- §30A.1 — add a horizontal timeline showing the release cadence: a horizontal axis (2018 → 2030), with bars for each LTS (when released, when EOL). Visualises "your product life vs LTS coverage" at a glance.
- §30A.6 — the decision-framework flowchart is text-only. Render it as ASCII with proper branches.
- §30A.8 worked examples — add a fourth scenario: "Hobbyist Yocto-based home-automation hub, 5-year product life, OTA-managed." This is the gap between B and C: a real product, but not industrial, and Yocto-curated. Useful for the maker reader.

### Technical errors
- §30A.4 table row "5.10 | Dec 2020 | Dec 2026 | Android 11/12 ABI baseline" — verify the EOL date. As of 2026, 5.10 LTS support window has been extended in some plans. Pin exact dates.
- §30A.4 "The 'extended LTS' track (sometimes called 'Civil Infrastructure Platform' or CIP)" — CIP is one specific extended-LTS effort. There are others (Greg KH's "super-long-term-support" stable trees, vendor-managed extended LTS). Tighten the wording or clarify CIP is one of several.
- §30A.5 "NXP about quarterly" — verify the cadence; NXP's `linux-imx` cadence is closer to per-Yocto-release (2-3 times per year). Pin precisely.
- §30A.5 "github.com/nxp-imx/linux-imx" — confirm the canonical repo URL. NXP has moved between several Git hosts.

### Knowledge prerequisites missing
- §30A.4 "CIP" appears with one expansion ("Civil Infrastructure Platform"). Add a one-line "industrial-Linux consortium funded by Toshiba, Siemens, Hitachi etc.; backports security fixes for 6+ years on selected LTS releases."
- §30A.5 "Yocto layer (`meta-imx`)" — Yocto and `meta-imx` not yet introduced in Part IV. Forward-reference to Part V/VI.
- §30A.8 scenario B mentions "ISP driver" and "ISP" — image-signal-processor. Reader from MCU world may not know. Define inline.
- §30A.11 "drm/kernel-doc-rst discussions" — appears to be a typo or copy-paste error; the symbol doesn't match anything. Either remove or correct to whatever was intended.

### Other
- §30A.10 pitfalls bullet "Our customer requires the vendor BSP." — strong opinion phrased as fact. Soften to "Sometimes a customer mandates the vendor BSP. Push back when the technical justification is weak; accept it when contract or compliance demands it."
- The chapter sits between Ch 30 (config) and Part V. The chapter's title says "Kernel lifecycle" but content is also a strategic-decision-framework chapter. Consider re-titling to "Kernel lifecycle and selection: which kernel ships?" to set expectations.
