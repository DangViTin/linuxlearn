---
chapter: 121
title: Custom board port as a system design
part: VIII - Debug, production, advanced
estimated_pages: 30
status: draft
---

<span id="chapter-121-capstone-custom-board-port"></span>
# Chapter 121: Custom board port as a system design
> **NFS:** Network File System, which lets the target mount a host directory over Ethernet during development.

> **What:** a board port as an integration problem. A custom PCB or MINI variant changes assumptions shared by **U-Boot configuration**, **kernel Device Tree and drivers**, **rootfs contents**, and **image generation**. This chapter follows those dependencies and shows where each layer owns a decision.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** Each Cookbook chapter covered one piece. A board port is where those pieces have to agree: pin multiplexing (Ch 5), DDR initialization (Ch 14), U-Boot policy (Ch 22), kernel DT (Ch 27), and the peripherals actually fitted. Understanding that agreement makes generated code and configuration easier to assess. A successful build alone does not establish a working board.
> **DDR:** external DRAM that must be configured and trained before most software can run from it.
>
> **Focus:** **dependencies determine the bring-up order**. A console makes early failures observable, DDR supports larger images, and storage or networking supplies later boot inputs. Peripheral integration comes after those foundations. Recovery must remain independent of the candidate being evaluated. The order below is a design example, not a required reader project.
> **MCU bridge:** Think of JTAG like SWD debugging on Cortex-M: halt, read registers, set breakpoints. The Cortex-A path adds MMU state, privilege modes, and more complex reset behavior.
> **JTAG:** the hardware debug scan chain used to halt, inspect, and single-step CPUs.

## 121.1  Scope, what to port

The port spans several contracts:

| Boundary | Design responsibility | Evidence needed separately |
|---|---|---|
| Early hardware | Power, reset, pin routing and DDR assumptions | Measurements and memory qualification on the fitted board |
| Boot inputs | Storage layout, image selection and recovery | Actual loader behavior and artifact integrity |
| Peripheral integration | Supplies, clocks, buses, driver binding and user interface | End-to-end behavior, including failure and removal |
| Build and release | Pinned inputs, configuration and artifact provenance | Repeatable output and a qualified release candidate |

An existing-driver chip such as an AT24 EEPROM or DS3231 RTC keeps the software contract relatively small. Camera, graphics and DMA-heavy additions widen the dependency set. That difference affects integration risk, not which assignment a reader must complete.
> **DMA:** Direct Memory Access. Hardware moves data to or from memory without the CPU copying each byte.

## 121.2  Hardware variants, what counts as "custom"

Three cases change different parts of the contract:

<span id="option-a-pretend-port-the-point-atom-mini"></span>
### Case A, Software policy on unchanged MINI hardware

The physical board can stay unchanged while product policy differs:
- Different model string in U-Boot (board name in `bdinfo`)
- Different default hostname in Linux
- Custom default `bootargs`

These changes affect identity and boot policy, not the power tree or DDR wiring. Adding an external device moves the design into the next case.

<span id="option-b-rework-the-point-atom-mini"></span>
### Case B, A MINI variant with changed connections

Possible additions or changes include:
- Replace the WiFi module (if any) with a different one
- Add an external RTC chip + battery
- Add an SPI Ethernet (DM9051 from Ch 115)
- Mod the LCD interface

Changed wiring introduces new supply, pin-mux and Device Tree dependencies. Each addition needs its actual module specification and connection review. This is a design comparison, not a soldering instruction.

<span id="option-c-full-custom-pcb"></span>
### Case C, A full custom PCB

A custom board can change the early boot assumptions themselves:
- Different RAM (DDR3 256 MB vs the MINI's 512 MB? Different timing).
- Different PMIC.
> **MCU bridge:** Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
> **PMIC:** Power Management IC, a chip that sequences and regulates the board's voltage rails.
- Different boot media (eMMC, QSPI flash instead of SD).
- Different I/O complement (your specific application, sensors, motors, displays).
- Different connectors / form factor.

The port must now account for hardware design and qualification as well as software integration. A similar SoC does not justify reusing another board's DDR, power or reset values. Detailed PCB design is outside this chapter's scope.

<span id="the-bring-up-checklist"></span>
## 121.3  Bring-up as a dependency model

Power and reset must be valid before a ROM observation is meaningful. The ROM then needs the correct boot source and image format. Early software needs a usable stack, console and memory arrangement before later storage, network or peripheral behavior can be interpreted.

Those dependencies do not create a universal pass/fail list. Rail limits come from the actual components and board specification. DDR evidence depends on geometry, timings, operating conditions and the chosen test coverage, not a fixed one-hour run. Destructive memory tests must not overwrite the running image or its data.

Console output also depends on the selected image: the MINI ROM+DCD path in Chapters 19 and 22 has no SPL banner. Similarly, a PHY response, driver probe or bus acknowledgement establishes only part of an interface. The application path and recovery behavior remain separate.

The useful design model is a chain of prerequisites with an observation at each boundary. A symptom narrows the search, but rarely identifies one failed layer by itself.

## 121.4  U-Boot port, the steps

### 121.4.1  Fork the reference defconfig

```sh
cd u-boot
cp configs/mx6ull_14x14_evk_defconfig configs/myboard_defconfig
make myboard_defconfig menuconfig
# Change CONFIG_DEFAULT_DEVICE_TREE to "imx6ull-myboard"
# Change CONFIG_SYS_BOARD to "myboard"
# Change CONFIG_SYS_CONFIG_NAME to "myboard"
```

### 121.4.2  Create board files

```sh
mkdir -p board/myvendor/myboard
cp -r board/freescale/mx6ull_14x14_evk/* board/myvendor/myboard/
# Edit Kconfig, MAINTAINERS, Makefile to reference myvendor/myboard
```

### 121.4.3  Adapt the DTS

```sh
cp arch/arm/dts/imx6ull-14x14-evk.dts arch/arm/dts/imx6ull-myboard.dts
# Edit:
#   model = "MyVendor MyBoard"
#   compatible = "myvendor,myboard", "fsl,imx6ull"
#   Remove unused peripherals
#   Add your additions
```

### 121.4.4  DDR config (if you changed RAM chip)

Run NXP's **DDR Stress Tool** with your DDR chip's datasheet values. Export the calibration. Update `board/myvendor/myboard/mx6ullevk.c` (the C-language DDR init in U-Boot SPL) with the new register values:
> **MCU bridge:** Think of SPL like the tiny early startup code that runs from internal SRAM before DDR is usable.
> **SPL:** Secondary Program Loader, a tiny first U-Boot stage that fits in OCRAM and initializes DDR.

```c
const struct mx6_mmdc_calibration mx6_mmcd_calib = {
    .p0_mpwldectrl0  = 0x00000000,
    .p0_mpwldectrl1  = 0x00000000,
    .p0_mpdgctrl0    = 0x4140043F,        /* from Stress Tool */
    .p0_mpdgctrl1    = 0x0124013E,
    .p0_mprddlctl    = 0x40404546,
    .p0_mpwrdlctl    = 0x40402E32,
};
```

This is the riskiest step. If DDR config is wrong, nothing else will work. Use the DDR Stress Tool. Don't hand-calculate.

### 121.4.5  Build and flash

```sh
make CROSS_COMPILE=arm-none-linux-gnueabihf- -j8
# u-boot-dtb.imx is the SD-flashable image

sudo dd if=u-boot-dtb.imx of=/dev/sdX bs=1k seek=1 conv=fsync
sudo eject /dev/sdX

# Insert SD into target; power on; watch serial console
```

If you see U-Boot banner → 80 % of bring-up complete. If you see only DCD garbage → DDR config wrong, debug with JTAG.
> **DCD:** Device Configuration Data: ROM-executed register writes that prepare clocks and DDR before your code runs.

## 121.5  Kernel DT port

Once U-Boot is up, port the kernel DT.

### 121.5.1  Fork the EVK DT

```sh
cd linux
cp arch/arm/boot/dts/nxp/imx/imx6ull-14x14-evk.dts arch/arm/boot/dts/nxp/imx/imx6ull-myboard.dts
# Edit to match your hardware
```

### 121.5.2  Add to Makefile

```
# arch/arm/boot/dts/Makefile
dtb-$(CONFIG_SOC_IMX6ULL) += imx6ull-myboard.dtb
```

### 121.5.3  Build kernel + DT

```sh
make ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- imx_v7_defconfig
make ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- zImage imx6ull-myboard.dtb modules
```

### 121.5.4  Boot from U-Boot

```
=> tftp 0x80800000 zImage
=> tftp 0x83000000 imx6ull-myboard.dtb
=> setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw
=> bootz 0x80800000 - 0x83000000
```

If kernel hangs early → use `earlycon` to see early printks. If kernel hangs after init → check `console=` arg matches your DT's UART.

## 121.6  Custom peripheral, adding an external RTC

Pick something simple: DS3231 RTC on I²C2.

### 121.6.1  DT addition

```dts
&i2c2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c2>;
    clock-frequency = <100000>;
    status = "okay";

    rtc@68 {
        compatible = "maxim,ds3231";
        reg = <0x68>;
        interrupt-parent = <&gpio4>;
        interrupts = <23 IRQ_TYPE_EDGE_FALLING>;
        wakeup-source;
    };
};
```

### 121.6.2  Enable kernel driver

```sh
make ARCH=arm menuconfig
# Device Drivers → Real Time Clock → Dallas/Maxim DS1307/37/38/39/40, DS1685/87/89 → built-in
```

Rebuild zImage + DT.

### 121.6.3  Verify

```sh
dmesg | grep ds
# rtc-ds1307 1-0068: registered as rtc1
# rtc-ds1307 1-0068: setting system clock to 2026-05-31 12:34:56 UTC

hwclock --show
# 2026-05-31 12:34:56.123456+00:00
```

If this works, you've taken a peripheral from "nonexistent on the EVK" to "fully driven by mainline Linux" via DT alone, the canonical pattern.

## 121.7  The reproducible build script

The example collects source selection, configuration, artifact generation and image assembly behind one build entry point. The script makes those dependencies visible, but does not by itself make a build reproducible.

`build.sh`:

```bash
#!/bin/bash
set -euo pipefail

ROOT=$(pwd)
JOBS=$(nproc)
TARGET_SD=${1:-}
[ -z "$TARGET_SD" ] && { echo "Usage: $0 /dev/sdX"; exit 1; }

# Tools
. ~/imx6ull/scripts/env.sh

# 1. Build U-Boot
cd "$ROOT/u-boot"
[ -d .git ] || git clone https://git.denx.de/u-boot.git . && git checkout v2026.04
make myboard_defconfig
make -j$JOBS

# 2. Build kernel
cd "$ROOT/linux"
[ -d .git ] || git clone https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git . && git checkout v6.6
make imx_v7_defconfig
make -j$JOBS zImage modules dtbs

# 3. Build rootfs (Buildroot)
cd "$ROOT/buildroot"
[ -d .git ] || git clone https://git.buildroot.net/buildroot . && git checkout 2026.02
make myboard_defconfig
make -j$JOBS

# 4. Flash SD
sudo bash -c "
  set -euo pipefail
  # Partition (1 MB unused | 64 MB FAT for boot | rest EXT4 for root)
  sfdisk $TARGET_SD <<EOF
,,1M
,64M,c,*
,,L
EOF
  mkfs.vfat ${TARGET_SD}1
  mkfs.ext4 -F ${TARGET_SD}2

  # Mount + copy
  mkdir -p /mnt/boot /mnt/root
  mount ${TARGET_SD}1 /mnt/boot
  mount ${TARGET_SD}2 /mnt/root

  cp $ROOT/linux/arch/arm/boot/zImage /mnt/boot/
  cp $ROOT/linux/arch/arm/boot/dts/nxp/imx/imx6ull-myboard.dtb /mnt/boot/

  tar -C /mnt/root -xf $ROOT/buildroot/output/images/rootfs.tar
  cd $ROOT/linux && make ARCH=arm CROSS_COMPILE=arm-none-linux-gnueabihf- INSTALL_MOD_PATH=/mnt/root modules_install

  umount /mnt/boot /mnt/root

  # Flash U-Boot (with offset 1k)
  dd if=$ROOT/u-boot/u-boot-dtb.imx of=$TARGET_SD bs=1k seek=1 conv=fsync
  sync
"

echo "Done. Eject SD and boot the target."
```

The example accepts a target device argument. A real image-writing operation requires independent identification of the removable medium and verification of its layout. `/dev/sdb` is a placeholder, not a disk recommendation.

Reproducibility depends on pinned source revisions, toolchains, configuration, dependencies and controlled build inputs. Another engineer needs those inputs and the artifact checks, not only the script. Producing the same bytes and qualifying those bytes on hardware are separate responsibilities.

## 121.8  Common failures + recovery

### "U-Boot prints DCD garbage then dies"
- DDR init failed. Use JTAG to dump MMDC registers. Compare to Stress Tool output.
> **MMDC:** the i.MX6ULL DDR controller block that owns timing, calibration, and DRAM command sequencing.
- Verify the SPL DDR init values match your DDR3 chip's datasheet.

### "U-Boot prompt but kernel hangs after 'Uncompressing Linux...'"
- DT name mismatch, kernel can't find the DT. Verify `console=` and root= args.
- `earlycon` and `loglevel=8` for more info.

### "Kernel boots but no Ethernet"
- PHY MDIO address wrong. `cat /sys/class/net/eth0/phydev/phy_id` to see. `mdio` U-Boot command to scan addresses.
> **PHY:** physical-layer block or chip that converts digital MAC signals to electrical or radio signals.
- PHY power rail not up. Verify with multimeter.

### "Driver doesn't probe"
- Compatible string mismatch, check kernel's table vs your DT.
- Required clock not declared, check `clocks` in DT.
- Required regulator not declared, `dmesg | grep regulator`.

### "Worked once, now bricked"
- Boot back into recovery via USB-OTG SDP (Ch 8).
- Re-flash known-good image.


(1219-lab)=
## 121.9  Key Notes

- A board port connects fitted hardware to several software descriptions. Power and reset behavior, early DDR setup, U-Boot configuration, kernel DT, and rootfs contents have distinct owners.
- The dependency chain starts before Linux. Unusable rails, reset, or DDR can prevent any kernel diagnostic, while a serial banner establishes only partial progress.
- Device Tree describes wiring and resources, while drivers implement behavior. A matching `compatible` string alone does not establish correct clocks, supplies, interrupts, or pin mux.
- The external RTC case separates board description, driver selection, and userspace access. Its presence and wiring are additions, not stock MINI assumptions.
- Reproducible image construction needs pinned inputs and matching modules and libraries. Writing an image to a particular medium is a separate, destructive deployment operation.
- Recovery depends on a board-specific known-good image and accessible boot path. Compilation and illustrative output do not qualify a custom board or the MINI.

## 121.10  Reflection

After 4 weeks of bring-up, write a 500-word retrospective:

- What did you expect to be hard that wasn't?
- What did you expect to be easy that wasn't?
- What did you learn that surprised you?
- What did you wish you'd known on day 1?
- What single tool / technique saved the most time?
- What was the most frustrating debug session, and how did you eventually solve it?

These answers are gold for the next board you port. Reread them when you start.

## 121.11  Pitfalls

- **Trying to bring up everything at once.** Bring up one layer at a time. Verify each.
- **No serial console early.** UART1 with PowerView / minicom from minute zero. Other debug paths require more setup.
- **No JTAG when needed.** When the serial output is "boots and hangs at unknown location," JTAG is the only ground truth. Don't argue.
- **Cargo-culting EVK config.** Read every line of the defconfig and DTS. Understand why each is there before changing.
- **DDR config "close enough."** No. Stress Tool every time. A 5 % timing margin difference can mean "works at 25 °C, crashes at 40 °C."
- **DT compile errors not fatal-looking.** `dtc` gives warnings that often hide errors. Read every line.
- **One-script build that depends on your laptop.** Test on a fresh checkout in a fresh VM. If it doesn't work, it's not reproducible.
- **Forgetting modules.** `make modules_install` to the rootfs partition. Without it, your driver isn't actually present on the target.
- **Wrong rootfs init.** Buildroot's default init is BusyBox. Verify `/sbin/init` exists.
- **Wrong console in bootargs.** `console=ttyS0` won't work on i.MX6ULL (it's `ttymxc0`). Verify against your DT.
- **No fallback image.** Brick your custom board with no way to recover. Always keep a stock-EVK SD on hand for comparison.

## 121.12  Going deeper

- **NXP IMX6ULL Reference Manual**: your single most important reference.
- **NXP DDR Stress Tool**: for DDR bring-up.
- **`U-Boot README.imx` + `doc/imx/mkimage/`**: for IMX-specific boot flow.
- **`Documentation/devicetree/bindings/arm/fsl.yaml`**: the i.MX SoC binding.
- **`MAINTAINERS`**: to find subsystem maintainers when upstreaming.
- **Bootlin training materials**: http://bootlin.com/training/embedded-linux/.
- **i.MX Solutions Catalog**: NXP's reference designs for various i.MX SoCs.
- **Ch 120A**: for upstreaming your DT.
- **Ch 121A**: to wire your `build.sh` into CI.
- **Ch 22 + Ch 25**: the original U-Boot and kernel port chapters.

---

> Next chapter: **Chapter 121A: CI/CD for embedded Linux**.
