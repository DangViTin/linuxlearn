---
chapter: 121
title: Capstone — custom board port
part: VIII — Debug, production, advanced
estimated_pages: 30
status: draft
---

# Chapter 121 — Capstone: custom board port

> **What:** a board-port exercise that uses most of what came before. Take a custom PCB (or a rework of the Point Atom MINI into a non-trivial variant) and port the entire stack to it: **U-Boot defconfig + DTS**, **kernel DTS + drivers**, **at least one new peripheral** the original board didn't have, and a **reproducible build script** that goes from clean checkout → bootable SD in one command. The deliverable is a working, customized Linux system on hardware you (or a colleague) designed.
>
> **Why:** Each Cookbook chapter covered one piece. A real board port is where those pieces have to work together. You'll touch: pin-muxing (Ch 5), DDR initialization (Ch 14), U-Boot porting (Ch 22), kernel DT (Ch 27), each peripheral chapter that applies (whatever your board has). At the end you have a binary build script + a custom DT that any teammate can run and reproduce. That deliverable, plus the debugging experience that comes with it, is what gets you to the next level of confidence on this stack.
>
> **Focus:** **the bring-up sequence is U-Boot first (you need a boot loader), then kernel + DT for *each* peripheral one at a time, with verification at every step**. Don't try to boot everything at once. Bring up serial, then DDR, then SD, then Ethernet, then your custom peripheral. Probe the serial console after each step. Use Ch 118's JTAG when serial is too coarse. Keep a known-good fall-back image you can flash to recover from bricks. At the end, ask what surprised you and why. That's what makes the next port faster.

## 121.1  Scope — what to port

A realistic 4-week capstone:

| Phase | What | Deliverable |
|---|---|---|
| Week 1 | Hardware bring-up | Custom DT compiles; U-Boot prompt over serial; DDR test passes |
| Week 2 | Storage + Network | SD/eMMC boot; Ethernet up; NFS root works |
| Week 3 | Custom peripheral | One chip from Part VII wired + driver bound + user-space test |
| Week 4 | Reproducible build | One-script flow: clean checkout → bootable image |

Pick the peripheral wisely: easiest first time = an existing-driver chip (e.g., AT24 EEPROM, DS3231 RTC, BME280 sensor). Avoid for first attempt: cameras, complex graphics, anything DMA-heavy.

## 121.2  Hardware variants — what counts as "custom"

Three options, in order of ambition:

### Option A — Pretend-port the Point Atom MINI

Even using the standard MINI, you can do a meaningful port:
- Different model string in U-Boot (board name in `bdinfo`)
- Different default hostname in Linux
- Add a peripheral the stock MINI doesn't ship (e.g., RTC on I²C, second SPI flash)
- Custom default `bootargs`

You learn the workflow without designing a PCB.

### Option B — Rework the Point Atom MINI

Solder/desolder peripherals on the existing board:
- Replace the WiFi module (if any) with a different one
- Add an external RTC chip + battery
- Add an SPI Ethernet (DM9051 from Ch 115)
- Mod the LCD interface

Real wiring, partial-board changes; tests your DT skills.

### Option C — Full custom PCB

Design your own i.MX6ULL board (KiCad / Altium):
- Different RAM (DDR3 256 MB vs the MINI's 512 MB? Different timing).
- Different PMIC.
- Different boot media (eMMC, QSPI flash instead of SD).
- Different I/O complement (your specific application — sensors, motors, displays).
- Different connectors / form factor.

This is the real-world product workflow. Takes 4–8 weeks for the PCB alone; not for the time-constrained reader.

For most readers: **Option A or B is right**. The PCB design is a different book.

## 121.3  The bring-up checklist

```
□ Power
  □ All rails come up in the right sequence (scope each)
  □ All rails at the right voltage (within ±5 %)
  □ POR_B deasserts after rails stable

□ Boot ROM
  □ BOOT_MODE pins strap to expected boot source
  □ Boot ROM reads IVT/DCD from boot media
  □ DCD configures clocks + DDR (or SPL does)

□ Serial console
  □ UART1 (or your chosen) at 115200 8N1
  □ U-Boot prints "U-Boot SPL ..." then "U-Boot ..."
  □ Enter U-Boot prompt with key press

□ DDR
  □ U-Boot's "mtest" passes across full DDR range
  □ DDR Stress Tool (NXP) green for 1 hour

□ Storage
  □ U-Boot can read SD/eMMC (mmc info; ls mmc 0:1)
  □ Kernel mounts root from same

□ Network
  □ PHY detected (mdio probes return correct ID)
  □ Link up when cable plugged
  □ DHCP gets IP; ping gateway works

□ Each custom peripheral
  □ I²C bus shows device at expected address (i2cdetect)
  □ SPI device responds with expected ID
  □ Kernel driver probes successfully (dmesg | grep <chip>)
  □ User-space test exercises the device end-to-end
```

Tick each off in order. Each failure isolates to one layer.

## 121.4  U-Boot port — the steps

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

Run NXP's **DDR Stress Tool** with your DDR chip's datasheet values; export the calibration. Update `board/myvendor/myboard/mx6ullevk.c` (the C-language DDR init in U-Boot SPL) with the new register values:

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

This is the riskiest step. If DDR config is wrong, nothing else will work. Use the DDR Stress Tool; don't hand-calculate.

### 121.4.5  Build and flash

```sh
make CROSS_COMPILE=arm-linux-gnueabihf- -j8
# u-boot-dtb.imx is the SD-flashable image

sudo dd if=u-boot-dtb.imx of=/dev/sdX bs=1k seek=1 conv=fsync
sudo eject /dev/sdX

# Insert SD into target; power on; watch serial console
```

If you see U-Boot banner → 80 % of bring-up complete. If you see only DCD garbage → DDR config wrong, debug with JTAG.

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
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx_v7_defconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- zImage imx6ull-myboard.dtb modules
```

### 121.5.4  Boot from U-Boot

```
=> tftp 0x80800000 zImage
=> tftp 0x83000000 imx6ull-myboard.dtb
=> setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw
=> bootz 0x80800000 - 0x83000000
```

If kernel hangs early → use `earlycon` to see early printks. If kernel hangs after init → check `console=` arg matches your DT's UART.

## 121.6  Custom peripheral — adding an external RTC

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

If this works, you've taken a peripheral from "nonexistent on the EVK" to "fully driven by mainline Linux" via DT alone — the canonical pattern.

## 121.7  The reproducible build script

The deliverable: one script, one command, bootable SD.

`build.sh`:

```bash
#!/bin/bash
set -euo pipefail

ROOT=$(pwd)
JOBS=$(nproc)
TARGET_SD=${1:-}
[ -z "$TARGET_SD" ] && { echo "Usage: $0 /dev/sdX"; exit 1; }

# Tools
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm

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
  cd $ROOT/linux && make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- INSTALL_MOD_PATH=/mnt/root modules_install

  umount /mnt/boot /mnt/root

  # Flash U-Boot (with offset 1k)
  dd if=$ROOT/u-boot/u-boot-dtb.imx of=$TARGET_SD bs=1k seek=1 conv=fsync
  sync
"

echo "Done. Eject SD and boot the target."
```

Run: `./build.sh /dev/sdb`. 30 minutes later (mostly compile time), bootable card.

**This script** is the deliverable. Hand it to a teammate; they get the same image. Reproducibility is the difference between "I shipped a product" and "I have a Linux running on my desk."

## 121.8  Common failures + recovery

### "U-Boot prints DCD garbage then dies"
- DDR init failed. Use JTAG to dump MMDC registers; compare to Stress Tool output.
- Verify the SPL DDR init values match your DDR3 chip's datasheet.

### "U-Boot prompt but kernel hangs after 'Uncompressing Linux...'"
- DT name mismatch — kernel can't find the DT. Verify `console=` and root= args.
- `earlycon` and `loglevel=8` for more info.

### "Kernel boots but no Ethernet"
- PHY MDIO address wrong. `cat /sys/class/net/eth0/phydev/phy_id` to see; `mdio` U-Boot command to scan addresses.
- PHY power rail not up. Verify with multimeter.

### "Driver doesn't probe"
- Compatible string mismatch — check kernel's table vs your DT.
- Required clock not declared — check `clocks` in DT.
- Required regulator not declared — `dmesg | grep regulator`.

### "Worked once, now bricked"
- Boot back into recovery via USB-OTG SDP (Ch 8).
- Re-flash known-good image.

## 121.9  Lab

1. **Set up workspace.** Clone u-boot, linux, buildroot at known versions. Verify each compiles.
2. **Stock build first.** Build U-Boot + kernel for the EVK (no changes). Boot the stock Point Atom MINI. Verify everything works.
3. **Customize step by step.** Fork the EVK as your board; change only the model string; rebuild; reboot; verify `bdinfo` shows your name.
4. **Add a peripheral.** Wire DS3231 RTC (Ch 117); add DT; enable driver; verify.
5. **Or replace a peripheral.** Remove the stock WM8960 audio; add an SGTL5000 (Ch 89); update DT; verify `aplay` works.
6. **Or add a new bus.** Wire a second I²C bus to spare pins; add DT; verify `i2cdetect -y 1` works.
7. **Build script.** Write `build.sh` from scratch; test on a clean checkout. Time the full build.
8. **CI integration (preview of Ch 121A).** Wire `build.sh` into GitHub Actions; verify it runs on every commit.
9. **Document it.** Write a 1-page README: "what hardware is needed, what software prerequisites, how to build, how to flash, how to verify." A new engineer should be able to follow it.
10. **(Stretch) Upstream the DT.** Format-patch + send your board DT to linux-arm-kernel + linux-imx (per Ch 120A). Even if rejected, the experience is valuable.

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

- **Trying to bring up everything at once.** Bring up one layer at a time; verify each.
- **No serial console early.** UART1 with PowerView / minicom from minute zero. Other debug paths require more setup.
- **No JTAG when needed.** When the serial output is "boots and hangs at unknown location," JTAG is the only ground truth. Don't argue.
- **Cargo-culting EVK config.** Read every line of the defconfig and DTS; understand why each is there before changing.
- **DDR config "close enough."** No. Stress Tool every time. A 5 % timing margin difference can mean "works at 25 °C, crashes at 40 °C."
- **DT compile errors not fatal-looking.** `dtc` gives warnings that often hide errors. Read every line.
- **One-script build that depends on your laptop.** Test on a fresh checkout in a fresh VM. If it doesn't work, it's not reproducible.
- **Forgetting modules.** `make modules_install` to the rootfs partition; without it, your driver isn't actually present on the target.
- **Wrong rootfs init.** Buildroot's default init is BusyBox; verify `/sbin/init` exists.
- **Wrong console in bootargs.** `console=ttyS0` won't work on i.MX6ULL (it's `ttymxc0`). Verify against your DT.
- **No fallback image.** Brick your custom board with no way to recover. Always keep a stock-EVK SD on hand for comparison.

## 121.12  Going deeper

- **NXP IMX6ULL Reference Manual** — your single most important reference.
- **NXP DDR Stress Tool** — for DDR bring-up.
- **`U-Boot README.imx` + `doc/imx/mkimage/`** — for IMX-specific boot flow.
- **`Documentation/devicetree/bindings/arm/fsl.yaml`** — the i.MX SoC binding.
- **`MAINTAINERS`** — to find subsystem maintainers when upstreaming.
- **Bootlin training materials** — http://bootlin.com/training/embedded-linux/.
- **i.MX Solutions Catalog** — NXP's reference designs for various i.MX SoCs.
- **Ch 120A** — for upstreaming your DT.
- **Ch 121A** — to wire your `build.sh` into CI.
- **Ch 22 + Ch 25** — the original U-Boot and kernel port chapters.

---

> Next chapter: **Chapter 121A — CI/CD for embedded Linux**.
