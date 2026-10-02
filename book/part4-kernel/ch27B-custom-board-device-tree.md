---
chapter: 27B
title: Device Tree for a custom i.MX6ULL board
part: IV - The Kernel
estimated_pages: 22
status: draft
---

# Chapter 27B: Device Tree for a custom i.MX6ULL board

> **What:** create a Linux Device Tree for the same custom board idea used in the U-Boot port: UART console, SD/eMMC, Ethernet, I2C, SPI, LEDs, keys, regulators, aliases, and `/chosen`.
>
> **Why:** Chapter 27 teaches the grammar. This chapter teaches the job: turn a schematic into a `.dts` file that the kernel can boot.
>
> **Result:** you have a board DTS that builds with `make dtbs`, passes useful checks, and boots far enough to prove each peripheral one by one.
>
> **Focus:** do not start by copying the whole EVK and hoping. Start with a small bootable board description, then add one peripheral at a time.

This chapter assumes your U-Boot board port can load a kernel and DTB from Chapter 26.

## 27B.1  The board DTS is not the SoC DTS

The i.MX6ULL SoC file already exists:

```text
arch/arm/boot/dts/nxp/imx/imx6ull.dtsi
```

It describes hardware inside the chip:

- CPU.
- GIC.
- UART controllers.
- I2C controllers.
- SPI controllers.
- USDHC controllers.
- GPIO banks.
- CCM clocks.
- IOMUXC pin controller.
- OCRAM.

Your board file describes what is connected outside the chip and which SoC blocks are actually used:

```text
arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dts
```

Board DTS files answer questions like:

- Which UART is the console?
- Which pins are routed to the SD slot?
- Which regulator powers the SD card?
- Which PHY is connected to FEC Ethernet?
- Which I2C address is the temperature sensor?
- Which GPIO drives the user LED?

## 27B.2  Files changed

| File | What changes |
|------|--------------|
| `arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dts` | New board description. |
| `arch/arm/boot/dts/nxp/imx/Makefile` | Add `imx6ull-pa-mini.dtb` to the build. |
| U-Boot environment | Set `fdtfile=imx6ull-pa-mini.dtb` or load it directly. |

No kernel driver is written in this chapter.

## 27B.3  Start with the smallest bootable DTS

Create `arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dts`:

```dts
// SPDX-License-Identifier: (GPL-2.0+ OR MIT)
/dts-v1/;

#include "imx6ull.dtsi"

/ {
    model = "Point Atom MINI i.MX6ULL";
    compatible = "point-atom,imx6ull-mini", "fsl,imx6ull";

    chosen {
        stdout-path = &uart1;
    };

    memory@80000000 {
        device_type = "memory";
        reg = <0x80000000 0x20000000>; /* 512 MiB */
    };
};

&uart1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_uart1>;
    status = "okay";
};

&iomuxc {
    pinctrl_uart1: uart1grp {
        fsl,pins = <
            MX6UL_PAD_UART1_TX_DATA__UART1_DCE_TX 0x1b0b1
            MX6UL_PAD_UART1_RX_DATA__UART1_DCE_RX 0x1b0b1
        >;
    };
};
```

This is enough for:

- Kernel to identify the machine.
- Kernel to know RAM size.
- Kernel to find the console UART.
- Kernel to print early boot logs.

It is not enough for SD rootfs, Ethernet, GPIO LEDs, or I2C. Add those later.

## 27B.4  Add it to the kernel build

Edit `arch/arm/boot/dts/nxp/imx/Makefile`:

```make
dtb-$(CONFIG_SOC_IMX6ULL) += \
    imx6ull-pa-mini.dtb
```

Keep the list sorted near other `imx6ull-*` boards if the file already has a long block.

Build:

```sh
$ make dtbs
$ ls arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dtb
```

Boot it:

```text
=> tftp 0x82000000 zImage
=> tftp 0x83000000 imx6ull-pa-mini.dtb
=> setenv bootargs 'console=ttymxc0,115200 earlycon root=/dev/mmcblk0p2 rw rootwait'
=> bootz 0x82000000 - 0x83000000
```

The first proof is the model line:

```text
OF: fdt: Machine model: Point Atom MINI i.MX6ULL
```

If you see that line, the kernel consumed your DTB.

## 27B.5  Add fixed regulators

Most boards have always-on rails or GPIO-controlled rails. Describe them explicitly. Drivers use these nodes to know when power is available.

Example SD-card 3.3 V rail:

```dts
/ {
    reg_sd1_vmmc: regulator-sd1-vmmc {
        compatible = "regulator-fixed";
        regulator-name = "VSD_3V3";
        regulator-min-microvolt = <3300000>;
        regulator-max-microvolt = <3300000>;
        gpio = <&gpio1 9 GPIO_ACTIVE_HIGH>;
        enable-active-high;
    };
};
```

If the rail is truly always on and has no GPIO:

```dts
/ {
    reg_3v3: regulator-3v3 {
        compatible = "regulator-fixed";
        regulator-name = "3V3";
        regulator-min-microvolt = <3300000>;
        regulator-max-microvolt = <3300000>;
        regulator-always-on;
    };
};
```

Do not invent regulators just to silence warnings. Each regulator node should correspond to a real rail in the schematic.

## 27B.6  Add SD or eMMC

Example SD slot on USDHC1:

```dts
&usdhc1 {
    pinctrl-names = "default", "state_100mhz", "state_200mhz";
    pinctrl-0 = <&pinctrl_usdhc1>;
    pinctrl-1 = <&pinctrl_usdhc1_100mhz>;
    pinctrl-2 = <&pinctrl_usdhc1_200mhz>;
    cd-gpios = <&gpio1 19 GPIO_ACTIVE_LOW>;
    keep-power-in-suspend;
    vmmc-supply = <&reg_sd1_vmmc>;
    bus-width = <4>;
    status = "okay";
};
```

Pin group:

```dts
&iomuxc {
    pinctrl_usdhc1: usdhc1grp {
        fsl,pins = <
            MX6UL_PAD_SD1_CMD__USDHC1_CMD     0x17059
            MX6UL_PAD_SD1_CLK__USDHC1_CLK     0x10071
            MX6UL_PAD_SD1_DATA0__USDHC1_DATA0 0x17059
            MX6UL_PAD_SD1_DATA1__USDHC1_DATA1 0x17059
            MX6UL_PAD_SD1_DATA2__USDHC1_DATA2 0x17059
            MX6UL_PAD_SD1_DATA3__USDHC1_DATA3 0x17059
        >;
    };
};
```

Use the actual pins from your schematic. The pad names must match `imx6ul-pinfunc.h`.

Boot proof:

```text
mmc0: new high speed SDHC card at address 0001
mmcblk0: mmc0:0001 SD16G 14.8 GiB
```

If you do not see `mmcblk0`, check pinctrl, card-detect GPIO, regulator, and `CONFIG_MMC_SDHCI_ESDHC_IMX`.

## 27B.7  Add Ethernet

Ethernet needs more than a MAC node. You need MAC pins, MDIO, PHY address, reset GPIO, clocking, and sometimes a regulator.

Example:

```dts
&fec1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_enet1>;
    phy-mode = "rmii";
    phy-handle = <&ethphy0>;
    phy-supply = <&reg_3v3>;
    status = "okay";

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        ethphy0: ethernet-phy@0 {
            compatible = "ethernet-phy-ieee802.3-c22";
            reg = <0>;
            reset-gpios = <&gpio5 7 GPIO_ACTIVE_LOW>;
            reset-assert-us = <10000>;
            reset-deassert-us = <80000>;
        };
    };
};
```

Boot proof:

```text
fec 2188000.ethernet eth0: registered PHC device 0
libphy: fec_enet_mii_bus: probed
```

Runtime proof:

```sh
target# ip link show eth0
target# udhcpc -i eth0
```

If the PHY is not found, check:

- `reg = <N>` matches the PHY strap address.
- MDC/MDIO pins are correct.
- PHY reset is deasserted.
- 50 MHz RMII reference clock is present.

## 27B.8  Add I2C devices

Enable the controller:

```dts
&i2c1 {
    clock-frequency = <100000>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_i2c1>;
    status = "okay";

    temp@48 {
        compatible = "ti,tmp102";
        reg = <0x48>;
    };
};
```

Pin group:

```dts
&iomuxc {
    pinctrl_i2c1: i2c1grp {
        fsl,pins = <
            MX6UL_PAD_UART4_TX_DATA__I2C1_SCL 0x4001b8b0
            MX6UL_PAD_UART4_RX_DATA__I2C1_SDA 0x4001b8b0
        >;
    };
};
```

The `0x40000000` bit selects open-drain behavior in the i.MX pin config. I2C also needs pull-ups on the board.

Boot proof:

```text
tmp102 0-0048: initialized
```

Runtime proof:

```sh
target# cat /sys/class/hwmon/hwmon*/temp1_input
```

## 27B.9  Add SPI devices

Enable ECSPI:

```dts
&ecspi1 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi1>;
    cs-gpios = <&gpio4 26 GPIO_ACTIVE_LOW>;
    status = "okay";

    spidev@0 {
        compatible = "rohm,dh2228fv";
        reg = <0>;
        spi-max-frequency = <10000000>;
    };
};
```

For learning, `spidev` is useful. For production, bind the real device to a real driver. Do not ship product logic that depends on a fake compatible string.

Runtime proof:

```sh
target# ls /dev/spidev*
```

## 27B.10  Add LEDs and keys

LED:

```dts
/ {
    leds {
        compatible = "gpio-leds";

        user_led {
            label = "user";
            gpios = <&gpio1 3 GPIO_ACTIVE_LOW>;
            default-state = "off";
        };
    };
};
```

Button:

```dts
/ {
    gpio-keys {
        compatible = "gpio-keys";

        recovery {
            label = "recovery";
            gpios = <&gpio1 5 GPIO_ACTIVE_LOW>;
            linux,code = <KEY_RESTART>;
            wakeup-source;
        };
    };
};
```

Add the include for key constants:

```dts
#include <dt-bindings/input/input.h>
```

Runtime proof:

```sh
target# ls /sys/class/leds
target# echo 1 > /sys/class/leds/user/brightness
target# cat /proc/bus/input/devices
```

## 27B.11  Add aliases and chosen

Make Linux names stable:

```dts
/ {
    aliases {
        serial0 = &uart1;
        ethernet0 = &fec1;
        mmc0 = &usdhc1;
        i2c0 = &i2c1;
        spi0 = &ecspi1;
    };

    chosen {
        stdout-path = &uart1;
    };
};
```

Aliases affect numbering. If you want `/dev/mmcblk0` to stay predictable, use aliases.

## 27B.12  Build and validate

Build only the DTB:

```sh
$ make dtbs
```

Run schema checks:

```sh
$ make dtbs_check DT_SCHEMA_FILES=imx
```

Reverse-compile for inspection:

```sh
$ dtc -I dtb -O dts \
      arch/arm/boot/dts/nxp/imx/imx6ull-pa-mini.dtb \
      > /tmp/imx6ull-pa-mini.expanded.dts
```

Search the expanded file:

```sh
$ grep -n 'Point Atom MINI' /tmp/imx6ull-pa-mini.expanded.dts
$ grep -n 'serial@2020000' /tmp/imx6ull-pa-mini.expanded.dts
$ grep -n 'ethernet-phy' /tmp/imx6ull-pa-mini.expanded.dts
```

The expanded DTS is what the kernel effectively sees after includes.

## 27B.13  Bring-up order

Do not enable everything at once. Use this order:

1. Memory and UART.
2. SD/eMMC.
3. Rootfs boot.
4. Ethernet.
5. LEDs and keys.
6. I2C.
7. SPI.
8. Displays, audio, sensors, and optional devices.

After each step, save a boot log. If step 6 breaks, compare with step 5.

## 27B.14  Lab

1. Create `imx6ull-pa-mini.dts` with only memory and UART.
2. Add it to `arch/arm/boot/dts/nxp/imx/Makefile`.
3. Build and boot. Confirm the model string.
4. Add SD/eMMC. Confirm `mmcblk0`.
5. Add one LED. Toggle it from sysfs.
6. Add Ethernet. Confirm `eth0` appears.
7. Run `dtbs_check` and fix only warnings caused by your new DTS.

## 27B.15  Pitfalls

- **Copying the EVK DTS blindly.** It may describe pins and regulators your board does not have.
- **Enabling a controller without pinctrl.** The driver probes, but pins stay muxed to something else.
- **Wrong GPIO polarity.** `GPIO_ACTIVE_LOW` vs `GPIO_ACTIVE_HIGH` changes behavior completely.
- **Wrong PHY address.** Ethernet will probe MDIO and find nothing.
- **Forgetting `vmmc-supply`.** MMC may work sometimes and fail under load.
- **Using DT to fix driver bugs.** DT describes hardware. Do not encode software policy unless the binding explicitly asks for it.

## 27B.16  Going deeper

- `Documentation/devicetree/bindings/`, for each device class.
- `arch/arm/boot/dts/nxp/imx/`, for i.MX board examples.
- `scripts/dtc/`, for the compiler.
- `drivers/of/`, for how the kernel creates devices from DT.

---

**Previous:** [Chapter 27A: DT bindings YAML and `dt_binding_check`](ch27A-dt-bindings-yaml.md)

**Next:** [Chapter 28: Kernel startup, traced](ch28-kernel-startup-traced.md)
