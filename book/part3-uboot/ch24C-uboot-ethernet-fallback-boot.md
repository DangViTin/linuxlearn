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

The board name remains `mx6ull_pa_mini`, its header `mx6ull_pa_mini.h`, and its base DTS `imx6ull-pa-mini.dts`. Ethernet wiring, PHY type/address, clock direction and reset pin must come from the schematic. The illustrative values below do not establish the MINI's wiring.

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

The port must already initialize Ethernet clocks and pads. A network command's existence does not establish that the hardware is usable.

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

Select the driver for the **actual PHY**, not an arbitrary EVK PHY. `CMD_FS_GENERIC` provides the generic `load` used below; FAT/ext4 support handles the chosen filesystem. `CMD_BOOTZ` starts the loose ARM zImage. `CMD_DHCP` is optional for the static example, but permits the separate test in 24C.10.

In the prepared Ubuntu Bash terminal, run `. ~/imx6ull/scripts/env.sh`, require success, and use the established `arm-none-linux-gnueabihf-` compiler. Reconfigure and build out of tree as in 24B.3/24B.9; do not edit global shell setup.

## 24C.5  Device Tree check: FEC, PHY, and reset

This is a **hypothetical integration fragment**, not a complete Ethernet port. It proposes FEC1, RMII, MDIO address 0 and a dedicated active-low reset on GPIO5_IO07:

```dts
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
            reg = <0>;
            reset-gpios = <&gpio5 7 GPIO_ACTIVE_LOW>;
            reset-assert-us = <10000>;
            reset-deassert-us = <30000>;
        };
    };
};
```

`pinctrl_enet1` must already contain schematic-qualified signal muxing. The fragment omits pad and clock setup deliberately. RMII needs a valid 50 MHz reference with the correct source/direction; MDIO/MDC and PHY supply must also work. `reg` comes from PHY straps. The two delays are example microsecond values to replace with that PHY's requirements.

In v2026.04, [the Ethernet PHY uclass](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/eth-phy-uclass.c) consumes these PHY-node reset properties with `DM_ETH_PHY` and `DM_GPIO`. [FEC](https://github.com/u-boot/u-boot/blob/v2026.04/drivers/net/fec_mxc.c) also supports the older **MAC-node** `phy-reset-gpios`, `phy-reset-duration` and `phy-reset-post-delay`, whose delays are milliseconds. Do not specify both paths for the same GPIO or mix their units.

GPIO5_IO07 is an SNVS/tamper pad on this SoC: its pad mux belongs under IOMUXC-SNVS, with the relevant supply/domain considered. The reset line must not also be a recovery button, strap reader or another driver's output. Do not copy the proposed reset pin without schematic proof.

## 24C.6  MAC address: do not ignore it

A valid Ethernet MAC is six bytes, nonzero and unicast. All-ones is broadcast and is invalid. Valid syntax does not imply ownership or uniqueness.

These examples assume one enabled controller at U-Boot Ethernet sequence 0, using `ethaddr`. Sequence 1 uses `eth1addr`; do not assume the EVK's saved `ethprime` or enabled second FEC matches this port. Check the control-DT Ethernet aliases and actual selected device, and disable controllers that are not wired on the board.

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

Place the matching kernel and OS DTB in the **already configured** TFTP root from Chapter 24. Creating a directory does not configure the server to use it. Do not disable the host firewall globally; diagnose the service and its allowed traffic. TFTP uses UDP port 69 for the initial request and a server-selected transfer port afterward.

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

The `-` means no initrd. The illustrative `rootdev=/dev/mmcblk0p2` in the header must be checked against **Linux's** MMC numbering. U-Boot `mmcdev=0` does not prove Linux `mmcblk0`. A measured PARTUUID is often clearer; obtain it from the intended root partition, never invent one.

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
4. Before any board networking, qualify MAC uniqueness, wiring, clocks, reset, RAM slots and root partition.
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

---

**Previous:** [Chapter 24B: U-Boot board policy with GPIO and I2C](ch24B-uboot-board-policy-i2c-gpio.md)

**Next:** [Chapter 24D: Board identity and variant selection in U-Boot](ch24D-uboot-board-identity-variants.md)
