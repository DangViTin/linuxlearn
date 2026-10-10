---
chapter: "24C"
title: Ethernet fallback boot in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24C: Ethernet fallback boot in U-Boot

Suppose U-Boot is running, but the boot partition has no kernel. Ethernet can supply a replacement kernel and DTB without repairing that partition first. The trap is that a failed load leaves old bytes in RAM: a script separated only by semicolons can boot those bytes instead of taking its fallback.

This chapter builds a local-first loading policy for **U-Boot v2026.04**, commit `88dc2788777babfd6322fa655df549a019aa1e69`. Each path reaches `bootz` only after both files load. The commands are for an isolated development network, not an authenticated production recovery service.

The modern port name remains `mx6ull_pa_mini`, its header `mx6ull_pa_mini.h`, and its base DTS `imx6ull-pa-mini.dts`. The supplied MINI V2.2 schematic establishes **one RJ45, on ENET2**, with an **SR8201F at MDIO address 1**. Earlier MINI revisions use LAN8720 at the same address. We will use that wiring, not the EVK's two-port assumptions.

Hardware documentation is not a claim of a working link. Chapter 19's vendor source selects an SMSC driver, and our first-lab build disables that network path. Section 22.7 compares the SR8201F-VB datasheet's `0x001cc816` ID with the modern RTL8201F driver's match table and enables `CONFIG_PHY_REALTEK` as a concrete candidate. Confirm the fitted PHY's actual ID and behavior before a V2.2 network test. A source/datasheet ID match is stronger than a similar name or generic fallback, but still does not establish complete silicon compatibility, RMII timing or measured packet transfers.

## 24C.1  The real use case

The policy has three outcomes:

1. Local kernel and DTB load, and U-Boot hands control to Linux.
2. Local loading or a returning `bootz` fails; U-Boot tries the network path.
3. The network path also fails; U-Boot returns to the prompt.

This cannot recover a board on which U-Boot itself does not start. Nor does it detect that Linux later panics or cannot mount root: once control passes to the kernel, this script is no longer running. Watchdog and boot-attempt recovery are a separate subject in Chapter 24F.

## 24C.2  What this chapter is not

TFTP supplies **kernel and DTB only**. The example root filesystem remains on MMC. If that rootfs is broken, loading the kernel by Ethernet does not repair it. Chapter 24's NFS-root workflow changes that assumption; a self-contained recovery initramfs is another design.

There is also no authenticity check on loose `zImage` and DTB files. TFTP has no image authentication. Chapter 24E explains why hashes alone do not solve this.

## 24C.3  Files changed in this chapter

| File | Responsibility |
|------|----------------|
| `configs/mx6ull_pa_mini_defconfig` | Network, FEC/PHY, filesystem and scripting support. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | U-Boot control-DT wiring for FEC, MDIO and PHY. |
| `include/configs/mx6ull_pa_mini.h` | Guarded local/network environment helpers. |
| Existing host TFTP root | Matching `zImage` and `imx6ull-pa-mini.dtb`. |

The port must already initialize MINI Ethernet clocks and pads and qualify the revision's PHY. This is v2026.04 migration work, separate from the old vendor configuration. A network command's existence does not establish that the hardware is usable.

## 24C.4  Enable U-Boot network commands

Merge this configuration fragment into the Chapter 22 port:

```text
CONFIG_NET=y
CONFIG_DM_ETH=y
CONFIG_FEC_MXC=y
CONFIG_PHYLIB=y
CONFIG_DM_ETH_PHY=y
CONFIG_CMD_NET=y
CONFIG_CMD_PING=y
CONFIG_CMD_DHCP=y
CONFIG_CMD_TFTPBOOT=y
CONFIG_HUSH_PARSER=y
CONFIG_HUSH_OLD_PARSER=y
CONFIG_CMD_MMC=y
CONFIG_CMD_FS_GENERIC=y
CONFIG_CMD_BOOTZ=y
CONFIG_CMD_FAT=y
CONFIG_FS_FAT=y
CONFIG_CMD_EXT4=y
CONFIG_FS_EXT4=y
```

For a **preV2.2 LAN8720 MINI**, `CONFIG_PHY_SMSC=y` selects the named LAN8710/LAN8720 driver; clocks, reset and negotiation still need testing. For the supplied **V2.2 SR8201F design**, retain Chapter 22's source-checked `CONFIG_PHY_REALTEK=y` candidate, then compare the actual MDIO ID and test the chip-specific behavior. Do not enable another platform's RTL8201F timing adjustment merely to make a link appear. In particular, do not transplant the vendor hook's unchecked register `0x1f` write of `0x8190` as a universal PHY fix.

`CMD_FS_GENERIC` provides the generic `load` used below; FAT/ext4 support handles the chosen filesystem. `CMD_BOOTZ` starts the loose ARM zImage. `CMD_DHCP` is optional for the static example, but permits the separate test in 24C.10. Retain 24B's DM GPIO and i.MX pinctrl support for reset ownership.

In the prepared Ubuntu Bash terminal, run `. ~/imx6ull/scripts/env.sh`, require success, and use the established `arm-none-linux-gnueabihf-` compiler. Reconfigure and build out of tree as in 24B.3/24B.9; do not edit global shell setup.

## 24C.5  Device Tree check: FEC, PHY, and reset

The MINI V2.2 route is documented in schematic sheets 1 and 3, CORE sheets 5-6, and guide pp274-275:

| Signal | MINI route |
|--------|------------|
| RMII MAC | ENET2; ENET1 signals are exposed on P4, not a second onboard RJ45. |
| MDIO / MDC | GPIO1_IO06 / GPIO1_IO07 muxed to ENET2 management signals. |
| PHY address | 1, from straps; unchanged across the documented PHY replacement. |
| Active-low reset | SNVS_TAMPER8 / GPIO5_IO08, net `ENET2_RST`. |
| RMII reference | ENET2_TX_CLK to the PHY TXC input; vendor setup supplies 50 MHz from the SoC. |

The RJ45 symbol and some differential-side nets retain `ENET1` names on sheet 3. Follow the **MAC-side ENET2 nets** into U11; the connector label is not a second MAC connection. Likewise, the guide's "two RJ45" sentence is an ALPHA carry-over, not MINI wiring.

Chapter 22 already supplies these routes and uses the FEC driver's **MAC-node** reset properties. Keep that working integration as the starting point. The fragment below is an **alternative PHY-uclass reset arrangement**, not another reset owner to paste beside it. To study it, remove the MAC's `phy-reset-*` properties first, then merge these properties into the existing `mini_phy` node. Do not duplicate PHY nodes or change reset ownership on hardware without a reviewed reason.

```dts
/ {
    aliases {
        ethernet0 = &fec2;
    };
};

&fec1 {
    status = "disabled";
};

&fec2 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_enet2 &pinctrl_enet2_reset>;
    phy-mode = "rmii";
    phy-handle = <&mini_phy>;
    status = "okay";

    mdio {
        #address-cells = <1>;
        #size-cells = <0>;

        mini_phy: ethernet-phy@1 {
            reg = <1>;
            reset-gpios = <&gpio5 8 GPIO_ACTIVE_LOW>;
            reset-assert-us = <100000>;
        };
    };
};

&iomuxc_snvs {
    pinctrl_enet2_reset: enet2-reset-grp {
        fsl,pins = <
            MX6ULL_PAD_SNVS_TAMPER8__GPIO5_IO08 0x1b0b0
        >;
    };
};
```

`pinctrl_enet2` must already contain the documented RMII and management signal muxing. The fragment omits that group and clock initialization deliberately; a DT node alone does not configure the SoC clock direction. The 100000 us assertion mirrors the vendor code's 100 ms low pulse, **not a verified SR8201F timing requirement**. No post-release delay is invented here: add the fitted PHY's required delay after checking its specification and measured supply/reference-clock startup. The reset pad-control value also requires electrical qualification.

In v2026.04, [the Ethernet PHY uclass](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/eth-phy-uclass.c) consumes these PHY-node reset properties with `DM_ETH_PHY` and `DM_GPIO`. [FEC](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/fec_mxc.c) also supports the older **MAC-node** `phy-reset-gpios`, `phy-reset-duration` and `phy-reset-post-delay`, whose delays are milliseconds. Do not specify both paths for the same GPIO or mix their units.

GPIO5_IO08 is an SNVS/tamper pad: use the i.MX6ULL SNVS pin-function header and **IOMUXC-SNVS**, as above, not the main controller's older i.MX6UL pad offsets. The reset line must not also be a recovery button, strap reader or C routine's independently requested output. Choose one reset owner when migrating away from the vendor's raw-GPIO routine.

## 24C.6  MAC address: do not ignore it

A valid Ethernet MAC is six bytes, nonzero and unicast. All-ones is broadcast and is invalid. Valid syntax does not imply ownership or uniqueness.

The modern fragment deliberately makes **ENET2 Ethernet sequence 0**, using `ethaddr`, with ENET1 disabled. Hardware MAC number 2 does not mean environment sequence 1. Sequence 1 uses `eth1addr`; inspect the built aliases and selected device rather than carrying over an EVK `ethprime`. The vendor header's legacy `CONFIG_FEC_ENET_DEV=1` selects the second hardware FEC, not this driver-model sequence contract.

Prefer an assigned, unique factory address from a documented source. A read-only SoC address may be usable if it is actually provisioned; a chip UID is not automatically a MAC allocation. An EEPROM/secure element/PMIC is only an identity source when the board has one with a defined record and provisioning process.

For an isolated lab, this is an **example locally administered unicast address**, not a shared default for every board:

```text
=> setenv ethaddr 02:7a:60:00:00:01
```

Bit 1 of the first byte marks local administration; bit 0 is clear for unicast. Allocate a different address for each board on the lab network and check for collisions. Do not copy a vendor's public prefix, and do not `saveenv` merely to run a network test. Existing environment protection may reject changing an already assigned `ethaddr`; do not enable blanket overwrite as a workaround. Chapter 24D uses an explicit identity policy and checks assignment errors.

## 24C.7  Manual Ethernet test

Use an isolated subnet that does not conflict with the host's VPN or existing adapters. `192.168.7.1` for the host and `.2` for one board are examples, not universal addresses.

Inspect the host's current adapters using `ip addr show`. Use Chapter 24's existing service setup rather than reinstalling packages or changing the host globally. With a qualified board and an interruptible autoboot:

```text
=> setenv ipaddr 192.168.7.2
=> setenv serverip 192.168.7.1
=> setenv netmask 255.255.255.0
=> ping ${serverip}
```

There is no predicted board log here. Record the actual selected device and result. A failed ping can also be host ICMP filtering; it does not uniquely diagnose hardware. If initialization reports no controller/PHY, fix the driver, clock, reset, address and mux before attempting fallback.

## 24C.8  Manual TFTP test

Place the matching kernel and OS DTB in the **already configured** TFTP root from Chapter 24. `imx6ull-pa-mini.dtb` is the modern exercise's OS-tree name; the vendor environment instead chooses `imx6ull-alientek-emmc.dtb`. Neither U-Boot's control DT nor a renamed unrelated DTB substitutes for a kernel-compatible MINI OS tree. Creating a directory does not configure the server to use it. Do not disable the host firewall globally; diagnose the service and its allowed traffic. TFTP uses UDP port 69 for the initial request and a server-selected transfer port afterward.

The example RAM slots are:

| Slot | Address | Qualification |
|------|---------|---------------|
| Kernel | `0x82000000` | Kernel payload and self-decompression must not overlap reserved data. |
| OS DTB | `0x83000000` | DTB and later growth/relocation need space. |

Check `bdinfo`, actual file sizes, available DDR, U-Boot relocation/stack/malloc and boot memory limits. These addresses are not guarantees for every memory size or large image. A successful load does not mean the buffers were safely placed.

For a manual read-to-RAM test:

```text
=> setenv kernel_addr_r 0x82000000
=> setenv fdt_addr_r 0x83000000
=> tftpboot ${kernel_addr_r} zImage
=> tftpboot ${fdt_addr_r} imx6ull-pa-mini.dtb
```

Inspect each result before proceeding. `filesize` describes the most recent successful load, not both files; failure may leave old RAM and old metadata. The automated scripts below use return status, not stale `filesize`, to decide whether boot is permitted.

## 24C.9  Local boot command

The complete header block in 24C.11 defines the commands. Read its local path first:

```text
if mmc dev ${mmcdev} && mmc rescan; then
    if load mmc ${mmcdev}:${bootpart} ${kernel_addr_r} zImage && load mmc ${mmcdev}:${bootpart} ${fdt_addr_r} ${fdtfile}; then
        if run set_local_args; then
            bootz ${kernel_addr_r} - ${fdt_addr_r}
        else
            false
        fi
    else
        echo Local image load failed; false
    fi
else
    echo MMC unavailable; false
fi
```

This is the **body of `local_boot`**, not a Bash program or a prompt assignment. `&&` stops after the first failure. Each failure branch ends in `false`, so an `echo` cannot accidentally convert failure into success. A `bootz` that returns reports its own status to the caller.

The `-` means no initrd. This exercise chooses the **MINI TF slot on USDHC1** as local media, conventionally U-Boot `mmcdev=0` in the vendor board code. The eMMC core's USDHC2 is conventionally `mmcdev=1`; a NAND core does not gain eMMC merely by changing that variable. Confirm the modern port's device sequences before use. Optional SDIO WiFi at P2 shares USDHC1 with TF, so do not fit/use that module while relying on this TF path.

The illustrative `rootdev=/dev/mmcblk0p2` in the header must be checked against **Linux's** MMC numbering. U-Boot `mmcdev=0` does not prove Linux `mmcblk0`. A measured PARTUUID is often clearer; obtain it from the intended root partition, never invent one. To use eMMC instead, coordinate device, partitions, root arguments and matching kernel/DTB; do not merely change one number.

## 24C.10  Network boot command

The default network path deliberately uses static settings. It reapplies all three addresses before attempting TFTP, so no earlier DHCP attempt silently supplies different values. Both network loads must succeed before arguments are set and `bootz` is called.

DHCP is an optional **separate** test:

```text
=> setenv autoload no
=> dhcp
```

`autoload=no` requests network configuration without the automatic boot-file transfer. If DHCP fails, printing "using static IP" does not restore overwritten or cleared variables. Explicitly reset `ipaddr`, `serverip`, `netmask` and any stale `gatewayip` before a static retry, as `net_boot` does below. If DHCP succeeds, its TFTP server and boot filename still need to match your intended server/payload; do not silently trust arbitrary DHCP boot options.

## 24C.11  Fallback boot command

This is a complete macro definition for the two loading paths and their dispatcher. Merge it into the existing header, retaining unrelated board defaults. Replace the `normal_boot` placeholder from 24B, and remove duplicate address/filename keys. Keep the non-booting `recovery_boot` until a real recovery image exists.

```c
#define PA_MINI_NET_FALLBACK_ENV \
    "kernel_addr_r=0x82000000\0" \
    "fdt_addr_r=0x83000000\0" \
    "fdtfile=imx6ull-pa-mini.dtb\0" \
    "bootfile=zImage\0" \
    "mmcdev=0\0" \
    "bootpart=1\0" \
    "rootdev=/dev/mmcblk0p2\0" \
    "lab_ip=192.168.7.2\0" \
    "lab_server=192.168.7.1\0" \
    "lab_mask=255.255.255.0\0" \
    "set_local_args=setenv bootargs console=ttymxc0,115200 " \
        "root=${rootdev} rw rootwait\0" \
    "local_boot=echo Trying local MMC; " \
        "if mmc dev ${mmcdev} && mmc rescan; then " \
            "if load mmc ${mmcdev}:${bootpart} ${kernel_addr_r} zImage && " \
                "load mmc ${mmcdev}:${bootpart} ${fdt_addr_r} ${fdtfile}; then " \
                "if run set_local_args; then " \
                    "bootz ${kernel_addr_r} - ${fdt_addr_r}; " \
                "else false; fi; " \
            "else echo Local image load failed; false; fi; " \
        "else echo MMC unavailable; false; fi\0" \
    "net_boot=echo Trying static-IP TFTP; " \
        "if setenv ipaddr ${lab_ip} && setenv serverip ${lab_server} && " \
            "setenv netmask ${lab_mask} && setenv gatewayip; then " \
            "if tftpboot ${kernel_addr_r} ${bootfile} && " \
                "tftpboot ${fdt_addr_r} ${fdtfile}; then " \
                "if run set_local_args; then " \
                    "bootz ${kernel_addr_r} - ${fdt_addr_r}; " \
                "else false; fi; " \
            "else echo Network image load failed; false; fi; " \
        "else echo Network setup failed; false; fi\0" \
    "fallback_boot=if run local_boot; then true; " \
        "else echo Local path returned failure; run net_boot; fi\0" \
    "normal_boot=run fallback_boot\0"
```

Append this macro to `CFG_EXTRA_ENV_SETTINGS` once. Use `CONFIG_USE_BOOTCOMMAND=y` and `CONFIG_BOOTCOMMAND="run normal_boot"` from 24B. When board policy is enabled, its late hook selects either `run normal_boot`, `run recovery_boot`, or a blocked command. **Do not replace that hook's gate with an unconditional fallback bootcmd.**

Successful kernel handoff does not return. Fallback can run after a failed load or a `bootz` error returned before handoff; it cannot run after a Linux failure. The `true` branch preserves success in a host mock or another returning command; it is not a "Linux finished" message.

## 24C.12  Make failure visible

```{figure} ../illustrations/part3/11-fallback-before-handoff.png
:name: fig-p3-fallback-before-handoff
:figclass: concept-sketch
:width: 100%
:alt: Local and network paths each require a fresh kernel and DTB and successful checks before handoff. A returned local failure can try the network path, but Linux does not return to this dispatcher after handoff.

Fallback handles failures returned before kernel handoff. Both paths must load their complete image pair and pass argument checks. A later Linux hang requires a separate reset and recovery policy.
```

Log attempts at path boundaries, then keep the underlying load/PHY error. The code emits "Trying local MMC", "Local image load failed" or "MMC unavailable", and "Trying static-IP TFTP" as appropriate. Those are source strings, not promised serial output from this board.

Distinguish three observations in your notes: which path was attempted, whether each payload loaded, and whether handoff occurred. A TFTP transfer alone establishes none of the kernel's rootfs, driver or application results.

## 24C.13  Optional: fetch a boot script

A legacy `boot.scr` is executable command input. Its CRC is not authentication. A trusted lab may use one, but fetching a script from an untrusted server grants that server whatever commands the build exposes, including potential storage writes. A signed kernel FIT does not authenticate an unrelated script.

For an isolated, deliberate lab only, the following is the complete content of `boot.cmd`, to create in the editor:

```text
if tftpboot ${kernel_addr_r} zImage && tftpboot ${fdt_addr_r} imx6ull-pa-mini.dtb && run set_local_args; then
    bootz ${kernel_addr_r} - ${fdt_addr_r}
else
    echo Script image load or argument setup failed
fi
exit 1
```

The final `exit 1` is outside the conditional. It reports failure if either load or argument setup fails, or if `bootz` returns instead of handing control to Linux. Successful kernel handoff never reaches it. In this pinned old-hush multiline `source` path, a nested conditional ending in `false` can still return status 0 to its caller, even though it correctly blocks handoff. Do not use that structure to report packaged-script failure. The [pinned exit reference](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/cmd/exit.rst) describes leaving the innermost script; the single-line `run` helpers in 24C.11 are unchanged.

Using the host `mkimage` built from the pinned source:

```sh
mkimage -A arm -T script -C none -n "pa-mini lab net script" -d boot.cmd boot.scr
```

With `CONFIG_CMD_SOURCE` and `CONFIG_LEGACY_IMAGE_FORMAT` deliberately enabled for this legacy lab script, a **single guarded command** is:

```text
=> if tftpboot ${scriptaddr} boot.scr; then source ${scriptaddr}; else echo Script load failed; false; fi
```

Define and qualify a separate `scriptaddr` first, for example `0x84000000` only after the RAM map is checked. Do not default to executing remotely supplied scripts in production. Required FIT signatures, trusted configuration policy and a verified boot chain require a separate security design, not simply this `source` command with a different image nearby.

## 24C.14  Lab

1. Compile the environment block and test its dispatcher in host/sandbox fixtures.
2. Inject local kernel failure, local DTB failure, MMC failure and returning boot failure. Confirm only the intended cases invoke network loading.
3. Inject either network load failure and argument-setting failure. Confirm no boot command is reached with stale bytes.
4. Before any board networking, identify the MINI baseboard revision and qualify its PHY ID/driver, MAC uniqueness, clocks, reset, RAM slots and TF/eMMC root partition. V2.2 SR8201F support is a prerequisite, not a result of the vendor build.
5. On isolated hardware, test each transfer separately, using volatile settings and the existing TFTP service.
6. Simulate a missing file by temporarily changing its filename in RAM, not by deleting files from live storage. Restore that variable afterward.

No storage/environment write is needed. Any later persistence or media replacement must be deliberate and qualified on spare media.

## 24C.15  Pitfalls

- **Semicolon-only loads.** A later successful command can mask failure and boot stale data.
- **Last-command status.** `echo` returns success; explicit failure branches must end in failure.
- **DHCP retry state.** A message does not restore static settings.
- **Rootfs assumption.** TFTP kernel/DTB does not fix MMC rootfs corruption.
- **Reset domains and units.** PHY-node microseconds differ from legacy FEC-node milliseconds.
- **Public or duplicate MAC.** Use an owned factory address, or unique locally administered lab addresses.
- **Authentication.** Loose payloads and legacy boot scripts are not trusted merely because they transfer successfully.

## 24C.16  Going deeper

- [Command Kconfig](https://github.com/u-boot/u-boot/blob/v2026.04/cmd/Kconfig): `load`, networking, `bootz`, hush and legacy script options.
- [Network commands](https://github.com/u-boot/u-boot/blob/v2026.04/cmd/net.c) and [BOOTP/DHCP](https://github.com/u-boot/u-boot/blob/v2026.04/net/bootp.c): return paths and `autoload` behavior.
- [TFTP implementation](https://github.com/u-boot/u-boot/blob/v2026.04/net/tftp.c): transfer ports, loading and retries. The pinned tree has no separate `dhcp.rst` or `tftpboot.rst`; inspect `cmd/net.c` for those commands.
- [Environment documentation](https://github.com/u-boot/u-boot/blob/v2026.04/doc/usage/environment.rst): network variables and defaults.
- [FEC driver](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/fec_mxc.c) and [PHY uclass](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/eth-phy-uclass.c): actual consumers of reset properties.
- [SMSC PHY driver](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/phy/smsc.c) and [PHY matching/fallback](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/phy/phy.c): named LAN8720 support is not evidence of SR8201F qualification.
- [Vendor board header](https://github.com/alientek-openedv/uboot-imx-rel_imx_4.1.15_2.1.0_ga_alientek/blob/edb7ca5ac4be2d978be60a2a12c61e0b6d1f7feb/include/configs/mx6ull_alientek_emmc.h) and [board setup](https://github.com/alientek-openedv/uboot-imx-rel_imx_4.1.15_2.1.0_ga_alientek/blob/edb7ca5ac4be2d978be60a2a12c61e0b6d1f7feb/board/freescale/mx6ull_alientek_emmc/mx6ull_alientek_emmc.c): historical controller, clock and PHY assumptions to audit during migration, not a tested V2.2 Ethernet result.

---

**Previous:** [Chapter 24B: U-Boot board policy with GPIO and I2C](ch24B-uboot-board-policy-i2c-gpio.md)

**Next:** [Chapter 24D: Board identity and variant selection in U-Boot](ch24D-uboot-board-identity-variants.md)
