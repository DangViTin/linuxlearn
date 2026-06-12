---
chapter: 22
title: Porting U-Boot to a custom board
part: III - U-Boot, deeply
estimated_pages: 22
status: draft
---

# Chapter 22: Porting U-Boot to a custom board

> **What:** fork the mainline `mx6ull_14x14_evk` board into a new `mx6ull_pa_mini` (Point Atom MINI) board directory. Update DDR timings, IOMUX, MAC PHY address, and defaults. End with a U-Boot binary that boots cleanly on the MINI from your bare-board changes, not on the EVK config.
> **MCU bridge:** Think of IOMUX like STM32 alternate-function selection, but with separate pad electrical settings and board-level ownership by Device Tree.
> **MAC:** Media Access Control in networking and radio chapters. It is the layer that owns framing and medium access.
> **PHY:** physical-layer block or chip that converts digital MAC signals to electrical or radio signals.
> **DDR:** external DRAM that must be configured and trained before most software can run from it.
> **IOMUX:** the pin multiplexer that decides which peripheral function appears on each package pin.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** In real product work, you rarely ship the vendor reference board. The custom PCB looks similar but has different pads, different I/O, different DRAM. The port is the deliverable. This chapter is how you produce it.
>
> **Focus:** the **anatomy of a board port**, board folder, defconfig, board header, DT, and the points where each touches U-Boot's core. After the first port, every later one is a copy-and-modify of the same five files.


## 22.1  What "porting" means

Three categories of port:

1. **Cosmetic port**: Same board, different default behavior (custom hostname, prompt, autoboot env). One file changes. Not really a port.
2. **Variant port**: Same SoC, same DDR, different peripherals. New defconfig + new DT + maybe new pinmux. Most "custom" boards.
3. **Real port**: Same SoC family, different DDR part, different PMIC, different boot media. New defconfig + new DT + new DDR config + new board.c. The Point Atom MINI vs the NXP EVK is approximately this. It is mostly a variant port plus DDR and pinmux work.
> **MCU bridge:** Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
> **PMIC:** Power Management IC, a chip that sequences and regulates the board's voltage rails.

For this chapter we do a **variant + DDR port**: fork the EVK to a new board directory, change DDR timings to match the MINI's specific DRAM part, change the pinmux for KEY/LED/BEEP/Ethernet PHY, and update the env defaults.

## 22.2  The five files (and one directory) that define a board

For any mainline U-Boot board, the per-board content lives in:

```
arch/arm/dts/imx6ull-pa-mini.dts          # device tree source for the board
board/myorg/mx6ull_pa_mini/               # board folder
├── Kconfig                               # optional: board-specific options
├── MAINTAINERS                           # required for mainline submission
├── Makefile
├── mx6ull_pa_mini.c                      # full U-Boot board hooks
├── spl.c                                 # SPL board hooks (incl. DDR)
└── README                                # what's on this board
include/configs/mx6ull_pa_mini.h          # legacy "board config" header
configs/mx6ull_pa_mini_defconfig          # the .config we ship
```

That's six items, four of which are short. About 90% of the work is in `spl.c` (DDR config) and the DTS.
> **SPL:** Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.

## 22.3  Step 1, Fork the EVK

```sh
$ cd ~/imx6ull/src/u-boot

# DT
$ cp arch/arm/dts/imx6ull-14x14-evk.dts arch/arm/dts/imx6ull-pa-mini.dts

# Board folder
$ cp -r board/freescale/mx6ull_14x14_evk board/myorg/mx6ull_pa_mini
$ cd board/myorg/mx6ull_pa_mini

# Rename the C file
$ git mv mx6ull_14x14_evk.c mx6ull_pa_mini.c

# Board header
$ cp ../../../include/configs/mx6ullevk.h ../../../include/configs/mx6ull_pa_mini.h

# Defconfig
$ cp ../../../configs/mx6ull_14x14_evk_defconfig ../../../configs/mx6ull_pa_mini_defconfig
```

Add `board/myorg/Kconfig` if it doesn't exist:

```kconfig
source "board/myorg/mx6ull_pa_mini/Kconfig"
```

Then in `arch/arm/mach-imx/mx6/Kconfig`, add to the `choice` of board options:

```kconfig
config TARGET_MX6ULL_PA_MINI
    bool "Point Atom MINI (mx6ull)"
    depends on MX6ULL
    select BOARD_LATE_INIT
    select DM
    select DM_THERMAL
    imply CMD_DM
```

And in `board/myorg/mx6ull_pa_mini/Kconfig`:

```kconfig
if TARGET_MX6ULL_PA_MINI

config SYS_BOARD
    default "mx6ull_pa_mini"

config SYS_VENDOR
    default "myorg"

config SYS_CONFIG_NAME
    default "mx6ull_pa_mini"

endif
```

In the `Makefile` inside the board folder, change the object name:

```make
# board/myorg/mx6ull_pa_mini/Makefile
obj-y := mx6ull_pa_mini.o
obj-$(CONFIG_SPL_BUILD) += spl.o
```

## 22.4  Step 2, Edit the defconfig

Open `configs/mx6ull_pa_mini_defconfig`. The relevant lines to change:

```
- CONFIG_TARGET_MX6ULL_14X14_EVK=y
+ CONFIG_TARGET_MX6ULL_PA_MINI=y

- CONFIG_DEFAULT_DEVICE_TREE="imx6ull-14x14-evk"
+ CONFIG_DEFAULT_DEVICE_TREE="imx6ull-pa-mini"

- CONFIG_SYS_PROMPT="=> "
+ CONFIG_SYS_PROMPT="pa-mini=> "

CONFIG_NR_DRAM_BANKS=1
CONFIG_SYS_TEXT_BASE=0x87800000
CONFIG_SPL=y
CONFIG_SYS_MALLOC_LEN=0x400000
...
```

`make oldconfig` (after `make distclean && make mx6ull_pa_mini_defconfig`) will fill in any missing settings.

## 22.5  Step 3, Update the device tree

```sh
$ vim arch/arm/dts/imx6ull-pa-mini.dts
```

Key changes from the EVK DTS:

```dts
/dts-v1/;
#include "imx6ull.dtsi"

/ {
    model = "Point Atom i.MX6ULL MINI";
    compatible = "myorg,imx6ull-pa-mini", "fsl,imx6ull";

    chosen {
        stdout-path = &uart1;
    };

    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x20000000>;   /* 512 MiB */
    };

    leds {
        compatible = "gpio-leds";
        led0 {
            label = "led0";
            gpios = <&gpio1 3 GPIO_ACTIVE_LOW>;   /* Point Atom LED, Ch 9 fix */
            default-state = "off";
        };
    };

    gpio-keys {
        compatible = "gpio-keys";
        key0 {
            label = "KEY0";
            gpios = <&gpio1 18 GPIO_ACTIVE_LOW>;  /* Point Atom KEY0 */
            linux,code = <KEY_HOME>;
        };
    };

    beep {
        compatible = "pwm-beeper";   /* or gpio-buzzer for the polled variant */
        pwms = <&pwm0 0 50000>;       /* eventually; for now GPIO-driven */
    };
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

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        ethphy0: ethernet-phy@0 {
            reg = <0>;               /* MINI's PHY address — verify */
            micrel,led-mode = <1>;
        };
    };
};

&usdhc2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_usdhc2>;
    non-removable;
    no-1-8-v;
    keep-power-in-suspend;
    bus-width = <8>;
    status = "okay";                 /* eMMC */
};

&iomuxc {
    pinctrl_uart1: uart1grp {
        fsl,pins = <
            MX6UL_PAD_UART1_TX_DATA__UART1_DCE_TX 0x1b0b1
            MX6UL_PAD_UART1_RX_DATA__UART1_DCE_RX 0x1b0b1
        >;
    };

    pinctrl_enet1: enet1grp {
        fsl,pins = <
            MX6UL_PAD_GPIO1_IO07__ENET1_MDC       0x1b0b0
            MX6UL_PAD_GPIO1_IO06__ENET1_MDIO      0x1b0b0
            /* ... full RMII pin list ... */
        >;
    };
};
```

Add the file to the build by editing `arch/arm/dts/Makefile`:

```make
dtb-$(CONFIG_MX6ULL) += imx6ull-pa-mini.dtb
```

This is the *U-Boot* device tree (used to inform U-Boot of its own board's hardware). The kernel will use a similar but separately-maintained DT in Chapter 27.

## 22.6  Step 4, DDR config in `spl.c`

There is no shortcut for DDR. The Point Atom MINI's DDR3 chip and trace layout differ from the EVK's. You must produce matching calibration values.

Open `board/myorg/mx6ull_pa_mini/spl.c`. Find these three structs (the names and fields match `board/freescale/mx6ull_14x14_evk/spl.c`):

```c
static struct mx6_ddr_sysinfo ddr_sysinfo = {
    .dsize = 0,                   /* 16-bit bus */
    .cs_density = 16,             /* in Gb per chip × #chips per rank */
    .ncs = 1,                     /* 1 chip select */
    .cs1_mirror = 0,
    .rtt_wr = 0,
    .rtt_nom = 1,                 /* RZQ/4 */
    .walat = 1,
    .ralat = 5,
    .mif3_mode = 3,
    .bi_on = 1,
    .sde_to_rst = 0x10,
    .rst_to_cke = 0x23,
    .refsel = 1,                  /* refresh = 32 kHz / 64 */
    .refr = 7,
};

static struct mx6_ddr3_cfg mt41k128m16jt_125 = {
    /* Micron MT41K128M16, JEDEC DDR3L-1066 / -1333 / -1600 */
    .mem_speed = 1600,
    .density = 2,                 /* Gb */
    .width = 16,
    .banks = 8,
    .rowaddr = 14,
    .coladdr = 10,
    .pagesz = 2,
    .trcd = 1310,
    .trcmin = 4875,
    .trasmin = 3500,
};

static struct mx6_mmdc_calibration mx6_mmdc_calib = {
    /* THESE VALUES MUST COME FROM YOUR BOARD'S DDR-STRESS-TOOL RUN */
    .p0_mpwldectrl0 = 0x001F001F,
    .p0_mpwldectrl1 = 0x001F001F,
    .p0_mpdgctrl0   = 0x4140414C,
    .p0_mpdgctrl1   = 0x40404152,
    .p0_mprddlctl   = 0x40404546,
    .p0_mpwrdlctl   = 0x40402E32,
};
```

The first two structs (`ddr_sysinfo`, `mt41k128m16jt_125`) describe what the DRAM *is*. They are the same for any board using this chip in this width.

The third struct (`mx6_mmdc_calib`) describes calibration values *for your specific PCB*. These must come from a fresh run of NXP's `mx6ull_ddr_stress_tester` on your MINI board (Chapter 14 §14.13). Do not copy these from another project's source. The trace lengths differ.

Once filled in:

```c
static void spl_dram_init(void)
{
    mx6_dram_cfg(&ddr_sysinfo, &mx6_mmdc_calib, &mt41k128m16jt_125);
}
```

That one call performs every register write from Chapter 14. The library in `arch/arm/mach-imx/mx6/ddr.c` walks the structs and emits the right sequence.

## 22.7  Step 5, Per-board IOMUX and peripheral init

In `mx6ull_pa_mini.c`, replace the EVK's pinmux for any pad the MINI uses differently. The pattern:

```c
static iomux_v3_cfg_t const uart1_pads[] = {
    MX6_PAD_UART1_TX_DATA__UART1_DCE_TX | MUX_PAD_CTRL(UART_PAD_CTRL),
    MX6_PAD_UART1_RX_DATA__UART1_DCE_RX | MUX_PAD_CTRL(UART_PAD_CTRL),
};

static iomux_v3_cfg_t const fec1_pads[] = {
    MX6_PAD_GPIO1_IO07__ENET1_MDC      | MUX_PAD_CTRL(ENET_PAD_CTRL),
    MX6_PAD_GPIO1_IO06__ENET1_MDIO     | MUX_PAD_CTRL(ENET_PAD_CTRL),
    /* ... */
};

static void setup_iomux_uart(void)
{
    imx_iomux_v3_setup_multiple_pads(uart1_pads, ARRAY_SIZE(uart1_pads));
}

static void setup_iomux_fec(void)
{
    imx_iomux_v3_setup_multiple_pads(fec1_pads, ARRAY_SIZE(fec1_pads));
}

int board_init(void)
{
    setup_iomux_uart();
    setup_iomux_fec();
    /* ... */
    return 0;
}
```

These macros come from the i.MX6ULL IOMUX tables. Each one encodes the pad, the mux mode, and the SELECT_INPUT value in a single constant. See `arch/arm/include/asm/arch-mx6/mx6ul_pins.h`.

Add overrides if you need them: `board_late_init` for env defaults, `board_phy_config` for RGMII PHY tweaks, `board_eth_init` for PHY-address overrides.

## 22.8  Step 6, Build and flash

```sh
$ make distclean
$ make mx6ull_pa_mini_defconfig
$ make -j$(nproc)
$ sudo dd if=SPL of=/dev/sdX bs=1k seek=1 conv=fsync
$ sudo dd if=u-boot-dtb.imx of=/dev/sdX bs=1k seek=69 conv=fsync
$ sync
```

Boot the MINI. The prompt should now read:

```
U-Boot 2025.01-myorg ...
Model: Point Atom i.MX6ULL MINI
DRAM:  512 MiB
...
pa-mini=>
```

Notice: model string, DRAM size, and prompt all reflect your port.

## 22.9  Verify per-peripheral

For each peripheral you ported, exercise it:

```
pa-mini=> mtest 0x80000000 0x90000000 0xa5a5a5a5 3
                              # 256 MB × 3 passes; ~30 s; expect 0 errors

pa-mini=> mmc list
FSL_SDHC: 0 (boot SD)
FSL_SDHC: 1 (eMMC)

pa-mini=> mmc dev 1
pa-mini=> mmc info
                              # eMMC details

pa-mini=> setenv ipaddr 192.168.7.2
pa-mini=> setenv serverip 192.168.7.1
pa-mini=> ping 192.168.7.1
Using FEC0 device
host 192.168.7.1 is alive
                              # FEC + PHY working

pa-mini=> i2c bus
                              # all 4 buses listed

pa-mini=> i2c dev 0
pa-mini=> i2c probe
Valid chip addresses: ...     # whatever's on I2C1
```

Each line confirms a piece of the port. If any check fails, go back to the section that introduced that peripheral and check the file mentioned there.

## 22.10  MAINTAINERS file

For mainline submission (Chapter 58A), the port also needs a `MAINTAINERS` file:

```
MX6ULL_PA_MINI BOARD
M:	Your Name <you@example.com>
S:	Maintained
F:	board/myorg/mx6ull_pa_mini/
F:	include/configs/mx6ull_pa_mini.h
F:	configs/mx6ull_pa_mini_defconfig
F:	arch/arm/dts/imx6ull-pa-mini.dts
```

Even if you never plan to submit upstream, this file documents who owns the port. Required by `scripts/get_maintainer.pl` if anyone else ever tries to send a fix.

## 22.11  Lab

1. **Fork the EVK** into `mx6ull_pa_mini` exactly as §22.3 describes.
2. **Configure your defconfig** and confirm `make mx6ull_pa_mini_defconfig` succeeds.
3. **Run DDR Stress Tool on your MINI.** Copy its values into `mx6_mmdc_calib`.
4. **Boot.** Confirm "Model: Point Atom..." appears, custom prompt appears, `mtest` is clean.
5. **Add one MINI-specific touch.** Pick something the EVK doesn't have, for instance, the BEEP GPIO toggling once on boot from `board_late_init`. Or a custom logo string in the boot banner.
> **GPIO:** General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.
6. **Generate a single patch series.** `git format-patch -7 origin/master` (assuming your branch has 7 new-board commits on top of upstream `master`). Inspect the patch files. Ensure each is self-contained.

## 22.12  Pitfalls

- **DDR values copied from another board.** Will sometimes work. Will sometimes fail in subtle ways (occasional bit flips under thermal load). *Always* validate with the stress tool on your specific board.
- **Forgetting to add the DTB to `dtb-y`.** The DTS compiles to a `.dtb` only if `arch/arm/dts/Makefile` references it. Symptom: build succeeds but the `.dtb` is missing and U-Boot uses a fallback (often the EVK's DT).
- **Mismatched `CONFIG_SYS_TEXT_BASE`.** Determines where U-Boot is *linked* for. If you change it, you must change the corresponding SPL `CONFIG_SYS_LOAD_ADDR` for `u-boot.imx`.
- **PHY address wrong.** Symptom: `ping` says "Could not initialize PHY". The PHY's MDIO address is wired by hardware (strapping resistors). Check your schematic and update DT.
- **`ethaddr` not set.** First boot has no MAC. Either set it via `setenv ethaddr xx:xx:xx:xx:xx:xx; saveenv`, or generate from a unique chip ID in `board_late_init`.
- **Building without `make distclean` after a defconfig change.** Stale objects mismatched against the new config silently corrupt the build.
- **Kconfig syntax errors.** Easy to miss. `make` reports them tersely. Compare against an existing `Kconfig` line by line.

## 22.13  Going deeper

- **`doc/board/freescale/`**: every NXP board's README. Useful reference patterns.
- **The `mxc_jtag_init` and `arm_pmu_init` weak hooks**: for boards with JTAG or PMU specifics.
> **MCU bridge:** Think of JTAG like SWD debugging on Cortex-M: halt, read registers, set breakpoints. The Cortex-A path adds MMU state, privilege modes, and more complex reset behavior.
> **JTAG:** the hardware debug scan chain used to halt, inspect, and single-step CPUs.
- **`board/freescale/common/`**: shared NXP utilities (`mpc8xxx`-style env helpers, PMIC drivers).
- **U-Boot mainline commit history**: `git log board/freescale/mx6ull_14x14_evk/` is a tour of every issue that the EVK port has ever had. Read at least the most recent 50 commits.
- **AN12085**: *Designing a Hardware Solution Based on the i.MX 6UL/6ULL*. From a U-Boot perspective: what needs to be true on a custom board for the mainline boot path to just work.

> Next chapter: **Chapter 23: `bootcmd`, `bootargs`, FIT images.** With a working board port, we turn to the *contract* between U-Boot and the kernel: how U-Boot decides what kernel to load, what it tells the kernel about the system, and the modern FIT image format.
> **FIT:** Flattened Image Tree, U-Boot's container format for kernels, DTBs, initramfs images, hashes, and signatures.
