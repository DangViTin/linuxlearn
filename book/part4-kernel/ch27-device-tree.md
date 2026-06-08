---
chapter: 27
title: Device Tree — the contract between firmware and kernel
part: IV — The Kernel
estimated_pages: 30
status: draft
---

# Chapter 27 — Device Tree: the contract between firmware and kernel

> **What:** the **Device Tree** — its origin, its grammar, the standard properties, how it's compiled (`dtc`) and consumed (`of_*` APIs in the kernel), and how a driver binds to a node via the `compatible` string. By the end you should be able to read `imx6ull-14x14-evk.dts` line by line, write an overlay that adds a new I²C device, and predict which kernel driver will probe it.
> **Device Tree** - a data file that describes board hardware to the Linux kernel instead of hard-coding it in C.
>
> **Why:** DT is the biggest mental shift in this chapter. There is no longer a hand-written `board-*.c` with platform device tables. There is a `.dts` file that describes the hardware, and the kernel matches drivers to nodes by string at runtime. Understanding this dynamic-binding model is the prerequisite for every chapter in Part VI.
>
> **Focus:** the **`compatible` string** as the keystone. Compatible-strings in DT nodes are matched against compatible-strings in driver source code. That single mechanism is how every driver in mainline finds its hardware. Once you have this, the rest of DT is just grammar.


## 27.1  Why the Device Tree exists

Before the Device Tree, every ARM board in mainline shipped a hand-written C file under `arch/arm/mach-<soc>/board-<name>.c` containing struct-array declarations like:

```c
static struct platform_device smdk2440_devices[] = {
    &s3c_device_ohci,
    &s3c_device_lcd,
    &s3c_device_wdt,
    &s3c_device_i2c0,
    &s3c_device_iis,
};
static struct s3c2410_uartcfg smdk2440_uartcfgs[] = {
    [0] = { .hwport = 0, .flags = 0, .ucon = 0x3c5, ... },
    ...
};
```

Each board got its own ~500-line C file, hand-written, compiled into the kernel. By 2010 the ARM `arch/` tree held thousands of such files and Linus Torvalds publicly complained that ARM was "a fucking pain in the ass". The community's response was to adopt the **Device Tree**, which had been used on PowerPC since the early 2000s. PowerPC in turn borrowed it from Open Firmware on Sun and Apple machines.

The premise of DT is simple: instead of describing hardware in C code that gets compiled into the kernel, describe it in a structured *text* file (`.dts`) that gets compiled separately into a *binary* blob (`.dtb`). The kernel reads the blob at boot time, builds an in-memory representation, and matches drivers to nodes dynamically. One kernel binary now supports thousands of boards because the per-board description lives outside the kernel.

The consequence: when you support a new board variant, you don't recompile the kernel. You write a DTS file. When you change which I²C chip is on which bus, you edit DT, not C. One ARM kernel binary now works across many boards.

## 27.2  DTS, DTB, DTC, DTSI

Four file extensions you will see:

- **`.dts`** — Device Tree Source. Human-readable text. One file describes one board.
- **`.dtsi`** — Device Tree Source Include. A `.dts` fragment that gets `#include`'d. Used for SoC-wide content shared by every board with that SoC.
- **`.dtb`** — Device Tree Blob. Binary form. What the kernel actually consumes at boot.
- **`.dtbo`** — Device Tree Overlay. A binary fragment that patches a base `.dtb` at runtime (Ch 23A).

The compiler is `dtc` (Device Tree Compiler), in `scripts/dtc/`:

```sh
$ make dtbs           # compile every DTS the current arch defines
$ make dtbs_check     # additionally validate against YAML schemas (Ch 27A)
```

Each `dts` file lists itself in `arch/arm/boot/dts/Makefile`:

```make
dtb-$(CONFIG_SOC_IMX6ULL) += \
    imx6ull-14x14-evk.dtb \
    imx6ull-colibri-eval-v3.dtb \
    imx6ull-9x9-evk.dtb \
    ...
```

To add a board, you add the `.dts` file and one line here.

## 27.3  Anatomy of a DTS file

Let's read `imx6ull-14x14-evk.dts` from the top. (Specific line numbers vary by kernel version. The structure is stable.)

```dts
/dts-v1/;

#include <dt-bindings/input/input.h>
#include "imx6ull.dtsi"

/ {
    model = "Freescale i.MX6 ULL 14x14 EVK Board";
    compatible = "fsl,imx6ull-14x14-evk", "fsl,imx6ull";

    chosen {
        stdout-path = &uart1;
    };

    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x20000000>;   /* 512 MiB */
    };

    reg_sd1_vmmc: regulator-sd1-vmmc {
        compatible = "regulator-fixed";
        regulator-name = "VSD_3V3";
        regulator-min-microvolt = <3300000>;
        regulator-max-microvolt = <3300000>;
        gpio = <&gpio1 9 GPIO_ACTIVE_HIGH>;
        enable-active-high;
    };

    /* ... more nodes ... */
};

&uart1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart1>;
    status = "okay";
};

&fec1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_enet1>;
    phy-mode = "rmii";
    phy-handle = <&ethphy0>;
    status = "okay";
    /* ... */
};
```

Six things going on:

1. **`/dts-v1/;`** — version marker. Always present.
2. **`#include`** — yes, DTS supports C-preprocessor includes. `dt-bindings/input/input.h` is a header that defines named constants (`KEY_ENTER`, etc.) used in DT.
3. **`#include "imx6ull.dtsi"`** — pulls in the SoC-wide DT fragment. *This is where most nodes actually live.* The board-level `.dts` mostly references and patches them.
4. **`/ { ... };`** — the **root node**. Every DT has exactly one. Inside it are all the other nodes (in a tree).
5. **`&uart1 { ... };`** — a **reference** to a node defined in the included `.dtsi`. The `&label` syntax says "modify the node previously labelled `uart1`". This is the canonical pattern: SoC `.dtsi` declares the node disabled by default. board `.dts` references it and sets `status = "okay"` plus board-specific pinctrl.
6. **Properties** — the `key = value;` pairs inside each node.

## 27.4  Node syntax

Every node has the form:

```
[label:] name[@unit-address] {
    property1 = value;
    property2;
    child-node {
        ...
    };
};
```

Each component:

- **`label`** (optional, before `:`) — a phandle/reference target. Lets other parts of the DT refer to this node by `&label`.
- **`name`** (required) — a human-readable name. Convention: same as the kind of device (`uart1`, `i2c2`, `ethphy0`).
- **`@unit-address`** (when applicable) — the device's base address on its parent bus. For an MMIO peripheral like UART1, this is the register-block base address: `serial@2020000`. The unit-address is for human readability and uniqueness. The actual address used by the kernel comes from the `reg` property.
**MMIO** - memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.

Example:

```dts
uart1: serial@2020000 {
    compatible = "fsl,imx6ul-uart", "fsl,imx21-uart";
    reg = <0x2020000 0x4000>;
    interrupts = <GIC_SPI 26 IRQ_TYPE_LEVEL_HIGH>;
    clocks = <&clks IMX6UL_CLK_UART1_IPG>, <&clks IMX6UL_CLK_UART1_SERIAL>;
    clock-names = "ipg", "per";
    status = "disabled";
};
```

`uart1` is the label. `serial@2020000` is `name@unit-address`. Inside: five properties.

## 27.5  Property data types

DT properties take five basic data types:

| Type | Syntax | Example |
|------|--------|---------|
| Empty (boolean flag) | `key;` | `interrupt-controller;` |
| String | `key = "value";` | `model = "Freescale i.MX6 ULL ...";` |
| String list | `key = "v1", "v2";` | `compatible = "fsl,imx6ul-uart", "fsl,imx21-uart";` |
| Cell (32-bit integer) | `key = <0x123>;` | `reg = <0x2020000 0x4000>;` |
| Byte sequence | `key = [00 11 22 33];` | `mac-address = [00 04 9f 01 30 ad];` |

A "cell" is exactly 32 bits. Multiple cells in one property are space-separated inside `< >`. Properties of arbitrary complexity are built from these primitives.

References use the angle-bracket form together with the `&label` shortcut. They can be richer:

```dts
clocks = <&clks IMX6UL_CLK_UART1_IPG>, <&clks IMX6UL_CLK_UART1_SERIAL>;
```

This says: two clock entries. Each entry is a reference to the `clks` node plus an integer index. The clock provider (the node labelled `clks`) decides what that integer means. The number of cells per entry comes from a `#clock-cells` property on the provider node (described in the next section).

## 27.6  Standard properties

The DT specification standardizes a dozen properties that almost every node uses. We will see them in every chapter from here on.

### `compatible` — the binding key

```dts
compatible = "fsl,imx6ul-uart", "fsl,imx21-uart";
```

A list of strings, most-specific first. Each string has the format `vendor,model`. The kernel matches this against drivers' `of_device_id[]` arrays:

```c
/* drivers/tty/serial/imx.c */
static const struct of_device_id imx_uart_dt_ids[] = {
    { .compatible = "fsl,imx6q-uart",  .data = &imx_uart_devdata[IMX6Q_UART] },
    { .compatible = "fsl,imx53-uart",  .data = &imx_uart_devdata[IMX53_UART] },
    { .compatible = "fsl,imx1-uart",   .data = &imx_uart_devdata[IMX1_UART]  },
    { .compatible = "fsl,imx21-uart",  .data = &imx_uart_devdata[IMX21_UART] },
    { /* sentinel */ }
};

static struct platform_driver serial_imx_driver = {
    .driver = {
        .name = "imx-uart",
        .of_match_table = imx_uart_dt_ids,
        ...
    },
    .probe = imx_uart_probe,
    ...
};
```

At boot, the kernel walks the DT. For each node with a `compatible` property, it walks through every registered driver's `of_match_table` looking for a match. The first match (matching against the *first* compatible string in the node, then the second, then ...) wins. The driver's `probe()` is invoked. *This is how the kernel matches drivers to hardware at boot.*

Reading our example:

- The DT says `compatible = "fsl,imx6ul-uart", "fsl,imx21-uart";`
- The driver's match table doesn't have "fsl,imx6ul-uart" (per the snippet above), so that one doesn't bind.
- It does have "fsl,imx21-uart", so the **second** compatible matches. The `.data` field tells the driver "this is the imx21-uart variant" so a single driver can support multiple SoC revisions with minor parameter differences.

The vendor prefix (`fsl,`) is registered in `Documentation/devicetree/bindings/vendor-prefixes.yaml`. The model name follows. together they form a globally unique key.

### `reg` — register addresses

```dts
reg = <0x2020000 0x4000>;          /* one range: 0x2020000, size 0x4000 */
reg = <0x2020000 0x4000>,
      <0x2024000 0x4000>;          /* two ranges, e.g., for split MMIO */
```

A `reg` property is a list of *(base, size)* pairs. **How many 32-bit cells are used for *base* and how many for *size* is determined by the parent node's `#address-cells` and `#size-cells`** — see next section.

### `#address-cells` and `#size-cells`

These are properties on **parent** nodes that tell `reg` properties on **child** nodes how many cells to use:

```dts
soc {
    #address-cells = <1>;   /* every child's reg base is 1 cell (32 bits) */
    #size-cells = <1>;      /* every child's reg size is 1 cell */

    uart1: serial@2020000 {
        reg = <0x2020000 0x4000>;   /* 1 cell base, 1 cell size */
    };
};
```

If `#address-cells = <2>`, the base is a 64-bit value (split as two 32-bit cells, high then low):

```dts
memory@0 {
    #address-cells = <2>;
    #size-cells = <2>;
    reg = <0x0 0x80000000 0x0 0x20000000>;   /* base = 0x80000000, size = 0x20000000 */
};
```

On i.MX6ULL (32-bit), most ranges fit in 1 cell each. On i.MX8M (64-bit), 2 cells is more common.

### `interrupts` and `interrupt-parent`

```dts
interrupts = <GIC_SPI 26 IRQ_TYPE_LEVEL_HIGH>;
```

The number of cells per IRQ entry is dictated by the **`#interrupt-cells`** property on the *interrupt parent* (the node listed in `interrupt-parent`, which defaults to the root node's `interrupt-parent`). For the GIC, `#interrupt-cells = <3>`, encoding *(IRQ type, IRQ number, trigger type)*. The constants `GIC_SPI` and `IRQ_TYPE_LEVEL_HIGH` come from `dt-bindings/interrupt-controller/`.
> **MCU bridge:** Think of the GIC like the Cortex-M NVIC scaled up for Cortex-A: it routes peripheral interrupts to CPU cores and has separate distributor and CPU-interface blocks.
**IRQ** - interrupt request, the signal path that tells the CPU or interrupt controller that hardware needs service.
**GIC** - ARM's Generic Interrupt Controller, the Cortex-A interrupt router roughly analogous to NVIC on Cortex-M.

### `clocks` and `clock-names`

```dts
clocks = <&clks IMX6UL_CLK_UART1_IPG>, <&clks IMX6UL_CLK_UART1_SERIAL>;
clock-names = "ipg", "per";
```

Two clocks. The driver gets them with `devm_clk_get(dev, "ipg")` and `devm_clk_get(dev, "per")`. The integer constants `IMX6UL_CLK_*` are named in `include/dt-bindings/clock/imx6ul-clock.h`.

### `pinctrl-0`, `pinctrl-1`, …, `pinctrl-names`

```dts
pinctrl-names = "default", "sleep";
pinctrl-0 = <&pinctrl_uart1>;
pinctrl-1 = <&pinctrl_uart1_sleep>;
```

Each `pinctrl-N` points to a pin-configuration node, and `pinctrl-names` gives each one a symbolic name. The driver picks a state with `pinctrl_select_state(p, "default")`. Default is automatically activated when the driver probes.

### `status`

```dts
status = "okay";      /* device is functional, probe it */
status = "disabled";  /* device exists in DT but kernel should ignore it */
```

Used to enable/disable a device without removing its DT node. SoC `.dtsi` files declare every peripheral as `status = "disabled"` by default. board `.dts` files set `status = "okay"` on the ones present on that board.

### `aliases` and `chosen`

Two special nodes at the root level:

```dts
/ {
    aliases {
        serial0 = &uart1;
        serial1 = &uart2;
        ethernet0 = &fec1;
    };

    chosen {
        stdout-path = &uart1;
        bootargs = "console=ttymxc0,115200 root=...";
    };
};
```

**`aliases`** names devices by a stable identifier ("serial0" is always the first UART. "serial1" always the second), regardless of where they sit in the tree.

**`chosen`** carries arguments to the kernel that aren't *about* hardware:
- `bootargs` — the kernel cmdline (Ch 26's `setenv bootargs ...` ends up here).
- `stdout-path` — which device `earlycon` should use.
- `linux,initrd-start` / `linux,initrd-end` — where an initrd lives (Ch 29).
- `kaslr-seed` — random seed for kernel address-space randomization.

## 27.7  Reading `imx6ull.dtsi`

`imx6ull.dtsi` is the SoC-wide DT. It includes the per-SoC-family fragment `imx6ul.dtsi` and adds the few i.MX6ULL-specific tweaks (some clock gates differ. The SAI audio block has different pinmuxing).

The general structure:

```dts
/ {
    interrupt-parent = <&gpc>;     /* the General Power Controller, on i.MX6, gates IRQs */

    aliases { /* ... */ };

    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        cpu0: cpu@0 {
            compatible = "arm,cortex-a7";
            device_type = "cpu";
            reg = <0>;
            clocks = <&clks IMX6UL_CLK_ARM>;
            operating-points-v2 = <&cpu0_opp_table>;
            /* ... */
        };
    };

    intc: interrupt-controller@a01000 {
        compatible = "arm,gic-400";   /* current mainline; "arm,cortex-a7-gic" is the older fallback */
        #interrupt-cells = <3>;
        interrupt-controller;
        reg = <0xa01000 0x1000>,
              <0xa02000 0x100>;
    };

    clocks { /* fixed clocks */ };

    soc {
        compatible = "simple-bus";
        #address-cells = <1>;
        #size-cells = <1>;
        interrupt-parent = <&gpc>;
        ranges;          /* identity-mapped: child addresses == parent addresses */

        aips1: aips-bus@2000000 {
            compatible = "fsl,aips-bus", "simple-bus";
            #address-cells = <1>;
            #size-cells = <1>;
            reg = <0x2000000 0x100000>;
            ranges;

            uart1: serial@2020000 { /* ... */ status = "disabled"; };
            uart2: serial@21e8000 { /* ... */ };
            i2c1:  i2c@21a0000 { /* ... */ };
            /* ... ~30 more peripherals ... */
        };

        aips2: aips-bus@2100000 { /* ... */ };
        aips3: aips-bus@2200000 { /* ... */ };

        ocram: sram@900000 {
            compatible = "mmio-sram";
            reg = <0x00900000 0x20000>;
            clocks = <&clks IMX6UL_CLK_OCRAM>;
        };

        ddr_pmu: ddr-pmu@21b0000 {
            compatible = "fsl,imx6ull-ddr-pmu";
            reg = <0x21b0000 0x10000>;
            interrupts = <GIC_SPI 119 IRQ_TYPE_LEVEL_HIGH>;
        };
    };
};
```

Five nodes deserve special attention:

- **`cpus`** — under it, one or more `cpu@N` nodes. For i.MX6ULL (single-core), one. The kernel reads this to know how many cores to bring up.
- **`intc`** — the interrupt controller. The GIC v2 on Cortex-A7 inside the i.MX6ULL. `interrupt-controller;` (empty property) marks it as the IRQ source for any node that doesn't specify `interrupt-parent` otherwise.
- **`clocks`** — fixed-frequency oscillators (the 24 MHz XTAL, the 32 kHz RTC source).
- **`soc`** — a container for the on-SoC peripheral buses. `compatible = "simple-bus"` is the magic that tells the kernel to *automatically* recurse into child nodes and probe them (otherwise it would only probe nodes the parent's driver explicitly enumerated).
- **`aips1` / `aips2` / `aips3`** — the three AIPS bridges from Chapter 5. Each is `simple-bus` too, so the kernel descends into them.

## 27.8  How a peripheral comes alive

Walking the end-to-end binding for UART1 on the EVK:

1. **Boot.** U-Boot has loaded `imx6ull-14x14-evk.dtb` to `0x83000000` and called `bootz`.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
2. **`stext` reads `r2 = 0x83000000`** and stashes it.
3. **`setup_arch()` → `setup_machine_fdt(0x83000000)`** parses the DT blob.
4. **`unflatten_device_tree()`** builds the in-memory tree of `struct device_node`.
5. **`of_platform_default_populate()`** walks the tree, for each `compatible = "simple-bus"` parent, creates platform devices for each child.
6. For each created platform device, the kernel walks every registered platform_driver looking for `compatible` matches. The `imx-uart` driver matches via `fsl,imx21-uart`.
7. **`imx_uart_probe()` is called** with a `struct platform_device *pdev` for that DT node.
8. Inside probe: `clk_get(dev, "ipg")` (via DT's `clocks` + `clock-names`), `clk_prepare_enable(clk)`, `ioremap` of the `reg` range, `request_irq` of the IRQ from `interrupts`, `devm_pinctrl_get` to apply pinmux from `pinctrl-0`, register a TTY device, done.
9. **The driver is now bound to the hardware.** `/dev/ttymxc0` becomes available.

That nine-step flow happens for **every** peripheral. The variation is which `compatible` matches which driver. Every driver chapter in Part VI walks this same flow.

## 27.9  Writing a DT overlay

Suppose you wire a new I²C sensor (a Texas Instruments TMP102 thermometer) to I²C2 of your board, at address `0x48`. You don't want to recompile the kernel. You want to add a DT node at runtime via an overlay.

`tmp102-overlay.dtso`:

```dts
/dts-v1/;
/plugin/;

&i2c2 {
    status = "okay";

    tmp102@48 {
        compatible = "ti,tmp102";
        reg = <0x48>;
    };
};
```

`/plugin/;` marks this as an overlay (vs a standalone DT). The `&i2c2` references the I²C2 node in the base DT (defined in `imx6ull.dtsi`). The new `tmp102@48` becomes a child of `i2c2`.

Compile and apply (from U-Boot, see Ch 23A):

```
=> load mmc 0:1 0x84000000 tmp102-overlay.dtbo
=> fdt addr 0x83000000
=> fdt resize 4096
=> fdt apply 0x84000000
=> bootz 0x82000000 - 0x83000000
```

Or from a Linux user-space with ConfigFS (in newer kernels):

```sh
# mkdir /sys/kernel/config/device-tree/overlays/tmp102
# cat tmp102.dtbo > /sys/kernel/config/device-tree/overlays/tmp102/dtbo
```

After overlay application, the kernel re-walks the DT, finds the new `tmp102@48` node, looks for a driver with `compatible = "ti,tmp102"` (the upstream driver is `drivers/hwmon/tmp102.c`), probes it, and `/sys/class/hwmon/hwmon<N>/temp1_input` becomes readable.

You did not recompile the kernel or touch the rootfs. You added a hardware description and the kernel handled the rest.
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
**rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.

This is why DT exists.

## 27.10  OF API — accessing DT from driver code

When your driver's `probe()` is called, it gets a `struct platform_device *pdev`. From there it reads DT properties via the **OF API** (Open Firmware API — the historical name. today everyone says "DT API" but the C symbols still start with `of_`):

```c
struct device_node *np = pdev->dev.of_node;

const char *name;
of_property_read_string(np, "label", &name);

u32 freq;
of_property_read_u32(np, "clock-frequency", &freq);

u32 vals[4];
of_property_read_u32_array(np, "vals", vals, 4);

if (of_property_read_bool(np, "interrupt-controller"))
    /* this node is an IRQ controller */;

/* Look up a phandle (a &label reference). */
struct device_node *phy = of_parse_phandle(np, "phy-handle", 0);

/* Find a child by name. */
struct device_node *child = of_get_child_by_name(np, "led0");

/* Iterate all children. */
for_each_child_of_node(np, child) {
    /* ... */
}
```

About twenty `of_*` helpers cover every DT-shaped read. They are documented in `include/linux/of.h` and `Documentation/devicetree/usage-model.rst`. We will see most of them in Part VI.

## 27.11  The single biggest mental shift

For an MCU engineer used to:

```c
void uart1_init(void) {
    CCM_CCGR5 |= (3 << 24);   // clock gate
    IOMUXC_SW_MUX_CTL_PAD_UART1_TX = 0;   // pinmux
    // ... 40 more register writes ...
}
```

…the Linux pattern is:

```dts
&uart1 {
    pinctrl-0 = <&pinctrl_uart1>;
    clocks = <&clks IMX6UL_CLK_UART1_IPG>, <&clks IMX6UL_CLK_UART1_SERIAL>;
    status = "okay";
};
```

And then *the driver* — written once for every board with this UART — reads those properties and does the equivalent register writes for you. The board engineer's job is to *describe* what's present, not to *do* the bring-up. The driver author's job is to handle every property correctly so any board can use the driver.

This is the Linux model. Once this clicks, Part VI is much easier.

## 27.12  Lab

1. **Read `imx6ull.dtsi` end-to-end.** Skim every node. Identify which ones describe (a) the CPU, (b) the GIC, (c) on-chip RAM, (d) on-SoC peripherals, (e) clock providers, (f) pinctrl banks.
2. **Read `imx6ull-14x14-evk.dts` end-to-end.** It's much shorter than the `.dtsi`. Identify the lines that (a) set the board's model string, (b) enable specific peripherals via `&uart1 { status = "okay". }`, (c) describe board-specific pinmux fragments, (d) declare board-specific regulators.
3. **Dump a compiled DTB back to source.** Run `dtc -I dtb -O dts arch/arm/boot/dts/nxp/imx/imx6ull-14x14-evk.dtb`. Note the differences from the `.dts` — the `dtc` output is post-include, post-preprocessor, fully resolved.
4. **Find which driver binds.** Pick three DT compatible strings from the EVK DTB and grep mainline for them: `grep -r "fsl,imx6ul-uart" drivers/`. Identify the driver file in each case.
5. **Write your first overlay.** Add a virtual I²C device — pick something innocuous like a non-existent ID at an unused address (`0x57`). Compile with `dtc -@ -O dtb tmp.dts -o tmp.dtbo`. Apply at U-Boot. Boot and `dmesg | grep tmp` to confirm the kernel *tried* to probe it (and failed because there's no actual device — that's fine. We wanted to confirm the overlay-apply path).
6. **Find the `chosen.bootargs`** in your booted kernel by running `cat /proc/cmdline` on the target — that's exactly what U-Boot wrote into the DT.

## 27.13  Pitfalls

- **`compatible` typo.** Off-by-one-character compatible strings are the most common DT bug. Kernel parses the DT, sees no driver match, the device silently doesn't probe. Symptom: device file missing in `/dev/`. nothing in `dmesg` about that device. Fix: `dtc -I dtb -O dts your.dtb | grep compatible` and verify every string is exact.
- **Missing `#address-cells` / `#size-cells` on a parent.** Kernel logs warning ("missing or invalid reg property") but might or might not fail. Always set these on any parent node that has child nodes with `reg`.
- **Hex without `0x`.** `reg = <2020000 4000>;` is decimal, not hex! Always use `0x` for register addresses: `reg = <0x2020000 0x4000>;`.
- **Forgotten `;` at end of property.** DTC error messages for missing `;` are sometimes misleading. Check the line above the error first.
- **Reference vs definition.** `uart1: serial@2020000 { ... };` *defines* the node. `&uart1 { ... };` *references and modifies* it. If you write `uart1 { ... };` (no label, just the bare name in a separate `/ { uart1 { ... } }`), the DTC creates a *new* node `uart1` — which is almost never what you want.
- **`clocks` order matters.** `clock-names` is positional. `clock-names = "ipg", "per"` means the *first* `clocks` entry is "ipg", the *second* is "per". Swap the order and the driver fails to find the right clock.
- **`status = "okay"` typo.** Some old templates use `"ok"` (without "ay"). The DT spec mandates `"okay"`. Older kernels accepted `"ok"` for backward compatibility, but modern `dtbs_check` rejects it as invalid against the schema.

## 27.14  Going deeper

- **`Documentation/devicetree/usage-model.rst`** — the canonical "how DT works" document.
- **`Documentation/devicetree/bindings/`** — every binding's YAML schema. Where you go to look up "what properties does this kind of device want?"
- **`include/linux/of.h`** — every OF API function declared.
- **`drivers/of/`** — the kernel's DT subsystem implementation.
- **`elinux.org/Device_Tree_Reference`** — community tutorial. pleasant introduction.
- **The DeviceTree Specification (v0.4)** at `devicetree.org/specifications/` — the canonical spec. ~80 pages.
- **`scripts/dtc/`** — the DT compiler source. Worth a skim if you want to know exactly what DTC does.

> Next chapter: **Chapter 27A — DT bindings YAML and `dt_binding_check`.** Now that we know DTS, we look at the *contract* it has with drivers: machine-checkable JSON-schema descriptions of every binding, and the build target that validates them.
