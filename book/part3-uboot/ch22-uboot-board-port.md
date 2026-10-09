---
chapter: 22
title: "Porting U-Boot to a custom board"
part: "III - U-Boot, deeply"
estimated_pages: 22
status: draft
---

# Chapter 22: Porting U-Boot to a custom board

You have built U-Boot for the EVK. Can you put that image on a MINI just because both boards use an i.MX6ULL? Think back to the first LED program: the instruction set could be correct while the clock gate or pad was wrong. A bootloader has the same problem, with an additional dependency. Its normal C code needs working DDR before it can help you diagnose anything.

We will give the new board its own identity, `mx6ull_pa_mini`, and trace which files must change. The reference throughout is **upstream U-Boot v2026.04**, commit `88dc2788777babfd6322fa655df549a019aa1e69`, not a vendor BSP or a moving branch. The starting config is `mx6ull_14x14_evk_defconfig`. It uses **ROM-executed DCD followed by full U-Boot, without SPL**. DCD means Device Configuration Data: register-write instructions packaged in the i.MX boot image.

The host-only result is a buildable **EVK-derived scaffold**, not a MINI-safe image. A completed port also needs the exact schematic revision, populated components, DDR setup and measurements for the physical board. A model string, prompt or successful compilation supplies none of that evidence.

> **Hardware boundary:** Do not run the copied EVK image on the MINI. The examples below retain EVK settings for source/build study until each setting is replaced or justified against the supplied board documents. No board boot, DDR qualification, media write or fuse programming is claimed here.

## 22.1  What "porting" means

Start with a smaller question than "which files do I copy?": **what changed between the two boards?** A different prompt is policy. A different PHY reset GPIO is wiring. A different DDR device or layout affects code that runs before the prompt exists. Those changes belong to different parts of the boot path.

| Change | Evidence to gather | Likely software owner |
|--------|--------------------|-----------------------|
| Prompt, filenames, autoboot policy | Product/development requirements | Defconfig and default environment |
| UART, storage and Ethernet wiring | Schematic net names, pads, voltage domains, reset/clock routes | Control DT and, where needed, board hooks |
| DDR geometry, timing and calibration | Populated part marking, datasheet, PCB revision and qualified DDR results | DCD in this selected boot path |
| Rail sequencing or enables | Power-tree schematic and measured sequencing | Hardware/ROM assumptions, board code and regulator description as applicable |
| Boot source and environment storage | Boot straps, ROM layout, partition map and recovery plan | Image configuration, Kconfig and storage policy |

A PMIC is a programmable power-management chip; a board may instead use discrete regulators. Do not add a PMIC driver because the EVK has one, or omit power sequencing because a DT node compiled. Establish what powers the CPU and DDR *before* ROM uses the DCD.

For your MINI, make a port ledger in `~/imx6ull/notes/mini-port.md`. Record the source page/net for each setting, the inherited EVK value, the intended replacement, and its status: unknown, document-checked, or hardware-qualified. In particular, do not infer DDR capacity, PHY address, eMMC bus width, buzzer type or active polarity from the board's marketing name.

(the-five-files-and-one-directory-that-define-a-board)=
## 22.2  The files that connect a board to U-Boot

In v2026.04 our selected reference lives at **`board/nxp/mx6ullevk/`**. Its Kconfig selects `include/configs/mx6ullevk.h` and its own `imximage.cfg`. There is no `spl.c` in this board directory. See the [versioned EVK config](https://github.com/u-boot/u-boot/blob/v2026.04/configs/mx6ull_14x14_evk_defconfig) and [board Kconfig](https://github.com/u-boot/u-boot/blob/v2026.04/board/nxp/mx6ullevk/Kconfig).

Our local teaching port uses these names consistently:

```text
board/myorg/mx6ull_pa_mini/
    Kconfig
    Makefile
    mx6ull_pa_mini.c
    imximage.cfg
    MAINTAINERS
include/configs/mx6ull_pa_mini.h
configs/mx6ull_pa_mini_defconfig
arch/arm/dts/imx6ull-pa-mini.dts
arch/arm/dts/imx6ull-pa-mini-u-boot.dtsi
```

`myorg` is a teaching namespace, not an already registered DT vendor prefix. A real upstream submission needs an appropriate vendor prefix and compatible binding. The underscore form names the U-Boot target/header; the hyphen form names the DT source and resulting `imx6ull-pa-mini.dtb`.

Two integration files sit outside that directory: `arch/arm/mach-imx/mx6/Kconfig` must expose/source the board, and `arch/arm/dts/Makefile` must list the DTB for this legacy-DTS reference. Other v2026.04 boards use `dts/upstream/`; do not mix that route into this exercise without deliberately migrating the DT setup.

```{figure} ../illustrations/part3/04-board-facts-and-files.png
:name: fig-p3-board-facts-files
:figclass: concept-sketch
:width: 100%
:alt: DDR part and wiring feed DCD setup, device wiring feeds the control DTS, and required features feed defconfig. Early board hooks provide code where needed.

Board facts belong to different files. In this ROM+DCD route, DDR setup must be qualified before U-Boot can use it. A new filename or a successful build does not supply that qualification.
```

## 22.3  Step 1, Fork the EVK

Work in your own U-Boot checkout from Chapter 19, not a shared read-only reference. Chapter 21 may already have added commits on your custom branch, so `HEAD` need not be the release commit. Check the pinned base and inspect the work on top of it:

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src/u-boot
$ git rev-parse 'v2026.04^{commit}'
$ git merge-base --is-ancestor v2026.04 HEAD
$ echo $?
$ git status --short
$ git log --oneline v2026.04..HEAD
```

The tag must resolve to `88dc2788777babfd6322fa655df549a019aa1e69`. The ancestry command prints nothing; the immediately following `echo $?` reports `0` if the pinned release is an ancestor of `HEAD`, `1` if it is not, or another nonzero value for an error. Stop and inspect a failed check rather than resetting away your Chapter 21 work. The exact-tag `HEAD` check from Chapter 19 belongs before those custom commits. See [Git's ancestry check](https://git-scm.com/docs/git-merge-base).

Review the extra commits and uncommitted changes too: ancestry establishes the starting revision, not that today's source is unchanged. Keep your Chapter 3 compiler directory names, including `arm-gnu-toolchain-13.2.Rel1-x86_64-arm-none-linux-gnueabihf`; the compiler prefix is `arm-none-linux-gnueabihf-`. There is no need to edit `.bashrc` or a system toolchain path.

If a destination below already exists, inspect it instead of copying over it. For new destinations:

```sh
$ mkdir -p board/myorg
$ cp -a board/nxp/mx6ullevk board/myorg/mx6ull_pa_mini
$ mv board/myorg/mx6ull_pa_mini/mx6ullevk.c board/myorg/mx6ull_pa_mini/mx6ull_pa_mini.c
$ cp include/configs/mx6ullevk.h include/configs/mx6ull_pa_mini.h
$ cp configs/mx6ull_14x14_evk_defconfig configs/mx6ull_pa_mini_defconfig
$ cp arch/arm/dts/imx6ull-14x14-evk.dts arch/arm/dts/imx6ull-pa-mini.dts
$ cp arch/arm/dts/imx6ull-14x14-evk-u-boot.dtsi arch/arm/dts/imx6ull-pa-mini-u-boot.dtsi
```

The new C file is untracked at this point, so ordinary `mv`, not `git mv`, is appropriate. Preserve the inherited licence/copyright notices. The copied `plugin.S` is not used by this DCD exercise; do not enable `CONFIG_USE_IMXIMG_PLUGIN` or treat it as MINI support.

Open `arch/arm/mach-imx/mx6/Kconfig` in your editor. In its board-choice block, beside the EVK target, add:

```kconfig
config TARGET_MX6ULL_PA_MINI
    bool "Point Atom MINI (unvalidated scaffold)"
    depends on MX6ULL
    select BOARD_LATE_INIT
    select DM
    select DM_THERMAL
    select IOMUX_LPSR
    imply CMD_DM
```

Near the existing board `source` lines in that same file, add this separate line. Merely creating a `board/myorg/Kconfig` does not make Kconfig discover it.

```kconfig
source "board/myorg/mx6ull_pa_mini/Kconfig"
```

Replace the copied board Kconfig with:

```kconfig
if TARGET_MX6ULL_PA_MINI

config SYS_BOARD
    default "mx6ull_pa_mini"

config SYS_VENDOR
    default "myorg"

config SYS_CONFIG_NAME
    default "mx6ull_pa_mini"

config IMX_CONFIG
    default "board/myorg/mx6ull_pa_mini/imximage.cfg"

endif
```

Notice `IMX_CONFIG`: renaming the C file without redirecting this option would still package the EVK's image configuration. In the copied board Makefile, keep its notices and replace the object line with:

```make
obj-y := mx6ull_pa_mini.o
```

No SPL object is added. In the copied `imximage.cfg`, update the inactive `PLUGIN` path to `board/myorg/mx6ull_pa_mini/plugin.bin` so an old EVK path is not hidden in the new directory. This does **not** qualify the plugin or any DCD value.

## 22.4  Step 2, Edit the defconfig

Open `configs/mx6ull_pa_mini_defconfig`. Replace the target/DT lines and add the prompt and disabled-autoboot settings shown below. This is a change list, not a complete defconfig:

```diff
-CONFIG_TARGET_MX6ULL_14X14_EVK=y
+CONFIG_TARGET_MX6ULL_PA_MINI=y
-CONFIG_DEFAULT_DEVICE_TREE="imx6ull-14x14-evk"
+CONFIG_DEFAULT_DEVICE_TREE="imx6ull-pa-mini"
+CONFIG_SYS_PROMPT="pa-mini=> "
+CONFIG_BOOTDELAY=-1
-CONFIG_BOOTCOMMAND="run findfdt;mmc dev ${mmcdev}; if mmc rescan; then if run loadbootscript; then run bootscript; else if run loadimage; then run mmcboot; else run netboot; fi; fi; else run netboot; fi"
+CONFIG_BOOTCOMMAND=""
-CONFIG_ENV_IS_IN_MMC=y
-CONFIG_ENV_RELOC_GD_ENV_ADDR=y
-CONFIG_ENV_MMC_DEVICE_INDEX=1
-CONFIG_ENV_OFFSET=0xC0000
+CONFIG_ENV_IS_NOWHERE=y
```

This scaffold has RAM-only environment changes. It cannot save them to a copied EVK MMC location. Leave `CONFIG_ENV_SIZE=0x2000` as the inherited environment capacity. A later persistent environment needs a deliberately reserved area, correct controller/device/partition selection and backup/recovery procedure before `saveenv` is allowed.

The inherited link address is **`CONFIG_TEXT_BASE=0x87800000`**, not the older `CONFIG_SYS_TEXT_BASE`. It is not a free-RAM declaration or a media offset. Keep it for build comparison only until the board's memory map is qualified. **Do not add `CONFIG_SPL=y`.** That would require a separately designed early loader, build layout and handoff.

In `include/configs/mx6ull_pa_mini.h`, give the include guard a unique name such as `__MX6ULL_PA_MINI_CONFIG_H`. Replace the entire inherited `CFG_EXTRA_ENV_SETTINGS` macro with this small, nonbooting default set:

```c
#define CFG_EXTRA_ENV_SETTINGS \
    "fdtfile=imx6ull-pa-mini.dtb\0" \
    "console=ttymxc0\0"
```

This also removes the EVK macro's reference to `CONFIG_ENV_MMC_DEVICE_INDEX`. Keep a note of every remaining EVK constant in the header. For example, `PHYS_SDRAM_SIZE` and `CFG_FEC_ENET_DEV` are not established MINI facts. Configuration symbols use `CONFIG_*`; many remaining board-header constants use `CFG_*`. Do not mechanically rename either family without checking its consumers.

## 22.5  Step 3, Update the device tree

Which DT are you changing? This file becomes U-Boot's **control FDT**, the flattened tree used by its driver model. The kernel DTB loaded later is a separate artifact. Similar filenames do not make the blobs interchangeable.

For the compile-only scaffold, replace just the root model/compatible block in the copied DTS with:

```dts
/ {
    model = "Point Atom i.MX6ULL MINI (unvalidated scaffold)";
    compatible = "myorg,imx6ull-pa-mini", "fsl,imx6ull";
};
```

Leave the includes and clock block intact for this first build. In particular, `imx6ul-14x14-evk.dtsi` still supplies EVK memory, regulators, peripherals and pads. **Changing the root identity does not remove that inherited hardware.** The copied `imx6ull-pa-mini-u-boot.dtsi` marks the EVK UART pinctrl and RNG for early use with `bootph-all`. Those are also reference settings, not a new pad audit.

In `arch/arm/dts/Makefile`, add a separate entry:

```make
dtb-$(CONFIG_MX6ULL) += imx6ull-pa-mini.dtb
```

For a physical MINI port, replace the EVK board-level include with a local board description and audit its complete expanded tree. Keep SoC definitions such as `imx6ull.dtsi`; rewrite board wiring from the actual schematic. Work through one dependency chain at a time:

1. **Console:** UART instance, TX/RX pad functions, electrical settings, clocks and `chosen/stdout-path` must refer to the routed connector. `ttymxc0` is an example for the kernel's UART1 path, not proof of your connector routing.
2. **Storage:** identify the wired USDHC controller, bus width, card detect, supply, reset and voltage switching. `non-removable` only describes soldered media. It does not initialize or identify an eMMC for you.
3. **Ethernet:** identify the MAC instance, PHY model and strapped MDIO address, RMII/MII mode, reference-clock direction, reset polarity/timing and supplies. A PHY node with `reg = <0>` is correct only if the straps establish address zero.
4. **Optional I/O:** add LED, key or buzzer nodes only after locating the exact nets and the matching driver/binding. A passive PWM beeper and an active GPIO-controlled buzzer are different circuits. There is no generic `pwm0` shortcut in this i.MX6ULL tree.

Do not declare a convenient memory size to make a build pass. The DT's memory description must agree with populated DDR geometry and the bootloader's detected/usable banks. Likewise, disabling a DT peripheral does not undo an unrelated C hook that drives its clock or reset.

(step-4-ddr-config-in-spl-c)=
## 22.6  Step 4, DDR config in DCD

For this selected defconfig, **there is no `spl.c` to edit**. The DDR initialization is the DCD in `board/myorg/mx6ull_pa_mini/imximage.cfg`. ROM applies it before entering U-Boot in DDR. The inherited `dram_init()` calls `imx_ddr_size()` to report the already configured controller; it does not replace the DCD with fresh timing setup.

Open the [v2026.04 EVK DCD](https://github.com/u-boot/u-boot/blob/v2026.04/board/nxp/mx6ullevk/imximage.cfg). Its `DATA` entries program clocks, DDR pads and MMDC, the memory controller. For example, the grammar is:

```text
DATA <register-width-in-bytes> <register-address> <value>
```

That is explanatory syntax, not input to paste into the file. The real file contains concrete register writes. None are offered here as MINI calibration values.

What would justify replacing them? Gather the populated DDR part/speed grade, voltage, bus width, ranks/chip selects, geometry and the exact PCB revision. Use the relevant NXP DDR tooling and its supported setup procedure from Chapter 14 to derive and validate a register sequence. Keep the tool version, input configuration, calibration output, test scope and environmental conditions with the port ledger. A stress result at one voltage/temperature is evidence for that test, not product qualification across all conditions.

Then map the qualified sequence into DCD entries, preserving required ordering and initialization commands. Compare the generated image's DCD with the reviewed input. If power, pads or DDR evidence is missing, stop at the build scaffold. Moving the same unverified numbers into an SPL struct does not solve the evidence gap.

An SPL reference such as `pico-imx6ul_defconfig` in Chapter 20 is useful for studying a different boot architecture. Its image and DDR settings are **not** a MINI recovery image and are not part of this port.

## 22.7  Step 5, Per-board IOMUX and peripheral init

On an MCU, alternate-function selection and output electrical settings may be adjacent register fields. Here, **IOMUX** chooses the pad function, pad control chooses electrical behavior, and input daisy selection can choose which pad feeds a peripheral input. U-Boot's pinctrl driver can apply these from the control DT. Adding a second C pad table unnecessarily creates two owners for the same pins.

Read the actual `mx6ull_pa_mini.c` you copied. The EVK source's early hook is empty; its Ethernet hook configures an internal 50 MHz clock path, and `board_phy_config()` writes a PHY register. Do not replace this with an invented generic `board_eth_init()` that assumes all Ethernet setup is non-driver-model. Match the selected driver's call path and the actual PHY datasheet.

For the source scaffold, make only the identity changes in `board_late_init()` and `checkboard()`: replace EVK board-name/revision strings with `PA-MINI`/`unvalidated`, and change the printed board string to `Point Atom MINI (unvalidated scaffold)`. Preserve function signatures and return values. This is a useful way to check that the new object was linked without toggling an unknown GPIO.

Before physical use, audit or remove the inherited `setup_fec()` and PHY-register write. If a board hook is required, return errors through the caller instead of reporting success after a failed clock/PHY setup. Do not mask a bring-up failure by adding more delays until a prompt happens to appear.

**Prediction check:** if the MINI's PHY uses an external oscillator, can the EVK's internal-clock setup be retained just because both trees say `phy-mode = "rmii"`? No. The interface mode does not establish the source/direction of the reference clock. The schematic, PHY requirements and SoC clock mux must agree.

## 22.8  Step 6, Build and flash

First build; flashing is a separate decision. Use a new output directory rather than cleaning a source tree containing your other work:

```sh
$ . ~/imx6ull/scripts/env.sh
$ cd ~/imx6ull/src/u-boot
$ command -v arm-none-linux-gnueabihf-gcc
$ make O="$HOME/imx6ull/build/u-boot-mini-2026.04" \
    ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- mx6ull_pa_mini_defconfig
$ make O="$HOME/imx6ull/build/u-boot-mini-2026.04" \
    ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- -j"$(nproc)"
$ grep -E 'CONFIG_(TARGET_MX6ULL_PA_MINI|IMX_CONFIG|DEFAULT_DEVICE_TREE|TEXT_BASE|ENV_IS_NOWHERE|SPL)=' \
    ~/imx6ull/build/u-boot-mini-2026.04/.config
$ ls -l ~/imx6ull/build/u-boot-mini-2026.04/u-boot-dtb.imx
$ ~/imx6ull/build/u-boot-mini-2026.04/tools/mkimage -l \
    ~/imx6ull/build/u-boot-mini-2026.04/u-boot-dtb.imx
```

The grep above only selects assignments. An unset SPL option may appear as `# CONFIG_SPL is not set`, or be absent when SPL support is not exposed by the selected target. Check the target's Kconfig, final config and actual output set together. Check the generated `arch/arm/dts/imx6ull-pa-mini.dtb`, not just the existence of an `.imx` file. Use `make O=... savedefconfig` after intentional menu changes, then manually compare the generated `defconfig` with your source file before copying it back.

Read the image listing with the source caveat from Chapter 19: in v2026.04's `tools/imximage.c`, the non-plugin v2 line labeled `Load Address` prints the IVT's **BootData pointer**, not `BootData.start`. It is not another kernel buffer address. Inspect the actual header/BootData and DCD when checking the ROM load range; `Mode: DCD` alone does not prove that a board-qualified DDR sequence is present.

For this reference, the product is `u-boot-dtb.imx`. The [versioned EVK board documentation](https://github.com/u-boot/u-boot/blob/v2026.04/doc/board/nxp/mx6ullevk.rst) describes a media offset of **1 KiB for that EVK SD route**, not SPL at 1 KiB plus U-Boot at 69 KiB. Do not turn that fact into a blanket MINI or eMMC instruction.

Before any later physical write, all of the following must be established:

- The image's DCD, power assumptions, pads and enabled peripherals match the exact board revision and populated parts.
- The selected boot medium, ROM offset, image length, partition table and reserved environment area are documented and do not overlap.
- The host device is identified by model/size/transport and stable identity, its mounts are understood, and a backup exists. A U-Boot MMC index is not a Linux host `/dev` name.
- A known-good recovery path/image is available and qualified for this board, without changing fuses.
- The planned write and read-back verification are reviewed for the actual removable media or eMMC area.

Until then, keep the scaffold on the host. This chapter deliberately provides no raw write command.

## 22.9  Verify per-peripheral

Only after the hardware gate above is satisfied should target bring-up begin. Interrupt autoboot and collect the actual banner/config first. A renamed prompt proves identity, not DDR reliability.

| Check | What it can establish | What it cannot establish |
|-------|-----------------------|--------------------------|
| `version`, `bdinfo` | Build identity and reported memory/relocation layout | DDR margin or all reserved-memory boundaries |
| `mmc list`, then `mmc dev`/`mmc info` for the verified controller | Enumerated storage and card information | Correct boot-media layout or write safety |
| `printenv`, `help` | Active policy and commands compiled in | That defaults match a stored environment from an older image |
| `ping` on an isolated, approved link | One ICMP exchange using the selected MAC/PHY path | Linux Ethernet driver readiness or NFS availability |
| `i2c bus` | U-Boot's configured bus inventory | Which physical chips are safe to probe |

Record observed output and compare it with the ledger. Do not fabricate bus counts, device numbering, DDR sizes or successful ping lines for the MINI. I2C scanning sends transactions and is not harmless for every attached device; inspect the devices and permitted operations before probing.

Do not run `mtest` over a guessed live-DDR range. It can overwrite U-Boot, its stack/heap, the control FDT or loaded images. DDR qualification needs a dedicated, documented test setup from Chapter 14, not a console memory sweep chosen from the apparent capacity.

## 22.10  MAINTAINERS file

Replace the inherited EVK ownership entry. Fill in an actual maintainer before submission; the following is a template:

```text
MX6ULL_PA_MINI BOARD
M: Your Name <you@example.com>
S: Maintained
F: board/myorg/mx6ull_pa_mini/
F: include/configs/mx6ull_pa_mini.h
F: configs/mx6ull_pa_mini_defconfig
F: arch/arm/dts/imx6ull-pa-mini.dts
F: arch/arm/dts/imx6ull-pa-mini-u-boot.dtsi
```

This records ownership and helps `scripts/get_maintainer.pl` find reviewers. It is not a certification that the board works. Keep the hardware ledger and test record alongside the port documentation even if it remains a local product port.

## 22.11  Lab

1. **Trace the reference before copying.** Find the v2026.04 target, its board Kconfig, `IMX_CONFIG`, DCD, header and control DTS. Explain who initializes DDR in this config.
2. **Build the separate scaffold.** Apply Sections 22.3-22.5 and the identity-only edits in 22.7. Verify the final `.config`, object/DT names and `.imx` artifact. Do not boot it on the MINI.
3. **Audit one chain from the supplied schematic.** Choose UART, USDHC or Ethernet. Record every pad, supply, clock and reset dependency, including unknowns. Do not fill missing values from memory.
4. **Prepare the DDR evidence plan.** Identify the actual memory and the supported test configuration. If hardware or documents are unavailable, mark this step blocked by evidence, not "passed" because the build works.
5. **Review the diff.** Use `git diff --check` and inspect both tracked changes and new files with your editor. Confirm the new target does not accidentally retain an EVK `IMX_CONFIG` or persistent MMC environment backend.
6. **Optional qualified-board bring-up.** Only after the hardware/write/recovery gates are met, follow an approved board procedure and record real results from Section 22.9. Keep this evidence separate from host compilation.

## 22.12  Pitfalls

- **A new name with old hardware.** Including the EVK `.dtsi` retains its regulators and pads. Audit the expanded tree and all C hooks, not only `model`.
- **Changing DT memory but leaving DCD.** DT reports hardware; it does not initialize DDR before ROM loads U-Boot. Geometry and initialization must agree.
- **Wrong integration path.** A new board Kconfig must be sourced. A misspelled selected DTS normally fails the build; there is no dependable "fall back to EVK" mechanism to rely on.
- **Confusing addresses.** `CONFIG_TEXT_BASE` is a link address. DCD register addresses, RAM load buffers and media offsets are different address spaces.
- **Blindly copied environment storage.** EVK `ENV_OFFSET=0xC0000`, size `0x2000` and MMC device index `1` are reference facts, not reserved space on your product. The scaffold uses `ENV_IS_NOWHERE`.
- **Wrong PHY or MAC policy.** PHY address comes from hardware straps; PHY register programming comes from its datasheet. MAC addresses need a collision-free allocation policy, not one copied from an EVK or an unreviewed chip-ID hash.
- **Treating one boot as qualification.** A prompt and a small transfer do not cover DDR corners, storage endurance, rail sequencing or recovery behavior.

## 22.13  Going deeper

Read the [v2026.04 board C source](https://github.com/u-boot/u-boot/blob/v2026.04/board/nxp/mx6ullevk/mx6ullevk.c) beside its Kconfig and image config. Follow a real hook into its caller before adding another one. The [v2026.04 DT control documentation](https://docs.u-boot.org/en/v2026.04/develop/devicetree/control.html) explains the tree used by U-Boot's own drivers.

For ROM and DDR decisions, return to the matching i.MX6ULL reference manual, memory datasheet and supplied board schematic revision from Parts I-II. Application-note numbers and another board's successful configuration are not substitutes for those documents. Keep the distinction between build evidence and physical evidence visible in the port's README.

> Next chapter: **Chapter 23: `bootcmd`, `bootargs`, FIT images.** With a qualified bootloader, what must it load, and what information must it hand to Linux? We can study that contract on the host before claiming a MINI boot.
