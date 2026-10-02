---
chapter: 24C
title: Ethernet fallback boot in U-Boot
part: III - U-Boot, deeply
estimated_pages: 18
status: draft
---

# Chapter 24C: Ethernet fallback boot in U-Boot

> **What:** make the board try normal local boot first. If the kernel or DTB is missing from SD/eMMC, U-Boot falls back to Ethernet and boots from TFTP.
>
> **Why:** this is useful in real work. During bring-up, the local boot partition is often wrong. In production, a service technician may need a board to recover from a broken boot partition without reflashing the whole device.
>
> **Result:** one `bootcmd` tries MMC first, then tries TFTP. The serial log clearly says which path was used.
>
> **Focus:** Ethernet in U-Boot is not only for development convenience. It is also a recovery path and a board-port validation tool.

This replaces a less common idea: asking a server for permission before boot. That can be useful in special systems, but most engineers need the pattern in this chapter first.

## 24C.1  The real use case

In early board bring-up, this happens all the time:

```text
U-Boot works.
MMC works sometimes.
The FAT partition is empty or has the wrong filename.
Linux image was copied to the wrong card.
The DTB does not match the board.
```

Without fallback, every mistake means removing the card or entering many manual commands.

With fallback:

```text
1. U-Boot tries SD/eMMC.
2. If local kernel and DTB exist, boot them.
3. If either file is missing, configure Ethernet.
4. Fetch the kernel and DTB from the host with TFTP.
5. Boot the network copy.
```

This gives a clean development and recovery path.

## 24C.2  What this chapter is not

This chapter is not NFS-root. Chapter 24 uses TFTP plus NFS for the fast development loop.

This chapter only does:

```text
TFTP kernel + TFTP DTB + normal rootfs argument
```

The root filesystem can still be on SD/eMMC. We are using Ethernet only to recover the boot images.

## 24C.3  Files changed in this chapter

| File | What changes |
|------|--------------|
| `configs/mx6ull_pa_mini_defconfig` | Enable Ethernet, DHCP, ping, TFTP, and command scripting. |
| `arch/arm/dts/imx6ull-pa-mini.dts` | Make sure FEC, MDIO, PHY reset, and pinmux are correct. |
| `include/configs/mx6ull_pa_mini.h` | Add local boot, network boot, and fallback boot commands. |
| TFTP server directory on host | Add `zImage` and `imx6ull-pa-mini.dtb`. |

This chapter assumes the Chapter 22 board port already has an Ethernet node. Here we turn that port into a repeatable boot policy.

## 24C.4  Enable U-Boot network commands

Open `configs/mx6ull_pa_mini_defconfig` and add:

```text
CONFIG_NET=y
CONFIG_CMD_NET=y
CONFIG_CMD_PING=y
CONFIG_CMD_DHCP=y
CONFIG_CMD_TFTPBOOT=y
CONFIG_HUSH_PARSER=y
CONFIG_CMD_EXT4=y
CONFIG_FS_EXT4=y
CONFIG_CMD_FAT=y
CONFIG_FS_FAT=y
```

What each option does:

| Config | Meaning |
|--------|---------|
| `CONFIG_NET` | Enables U-Boot networking support. |
| `CONFIG_CMD_NET` | Enables common network commands. |
| `CONFIG_CMD_PING` | Adds `ping`, the first Ethernet test. |
| `CONFIG_CMD_DHCP` | Adds `dhcp`, so the board can request an IP address. |
| `CONFIG_CMD_TFTPBOOT` | Adds TFTP loading. In U-Boot, the command is usually `tftp` or `tftpboot`. |
| `CONFIG_HUSH_PARSER` | Enables `if ... then ... else ... fi` in environment scripts. |
| `CONFIG_CMD_EXT4` and `CONFIG_FS_EXT4` | Let U-Boot load files from ext4 partitions. |
| `CONFIG_CMD_FAT` and `CONFIG_FS_FAT` | Let U-Boot load files from FAT partitions. |

The Ethernet controller driver itself is SoC-specific. For the i.MX6ULL FEC driver, your board defconfig may already select it through the i.MX platform. If Ethernet commands exist but no network device appears, check the FEC driver symbol in `drivers/net/Kconfig`.

## 24C.5  Device Tree check: FEC, PHY, and reset

The U-Boot Device Tree must describe the Ethernet controller and PHY.

Example:

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

What each line means:

| Line | Meaning |
|------|---------|
| `phy-mode = "rmii"` | Electrical interface between i.MX6ULL FEC MAC and external PHY. |
| `phy-handle = <&ethphy0>` | Points the MAC to the PHY node. |
| `reg = <0>` | PHY address on the MDIO bus. This comes from hardware strap pins. |
| `reset-gpios` | GPIO used to reset the PHY, if the board has one. |
| `reset-assert-us` | How long reset stays active. |
| `reset-deassert-us` | How long U-Boot waits after reset before talking to PHY. |

If `ping` says the PHY cannot be found, check `reg = <...>` first. PHY address is a hardware strap, not a software preference.

## 24C.6  MAC address: do not ignore it

Ethernet needs a MAC address.

U-Boot normally uses the environment variable:

```text
ethaddr=00:04:9f:12:34:56
```

For a lab board, you can set it manually:

```text
pa-mini=> setenv ethaddr 00:04:9f:12:34:56
pa-mini=> saveenv
```

For a product, do not make up random MAC addresses. Use one of:

| Source | Good for |
|--------|----------|
| Factory-programmed EEPROM | Most boards. Can store MAC, serial, board revision together. |
| SoC OCOTP fuse | Strong identity, but one-time programmable. |
| PMIC or secure element storage | Products that already have a secure identity chip. |

If MAC is missing, stop and print a clear message in production. Two boards with the same MAC address create strange network failures.

## 24C.7  Manual Ethernet test

Use static IP first. It removes DHCP from the test.

On the host:

```sh
$ ip addr show
```

Assume the host Ethernet adapter connected to the board is `192.168.7.1`.

In U-Boot:

```text
pa-mini=> setenv ipaddr 192.168.7.2
pa-mini=> setenv serverip 192.168.7.1
pa-mini=> setenv netmask 255.255.255.0
pa-mini=> ping 192.168.7.1
Using FEC0 device
host 192.168.7.1 is alive
```

If this fails, stop here. Do not write fallback scripts yet.

Common causes:

| Symptom | Likely cause |
|---------|--------------|
| `No ethernet found` | FEC driver or DT node missing. |
| `Could not initialize PHY` | Wrong PHY address, reset GPIO, clock, or MDIO pinmux. |
| Link LED off | Cable, PHY reset, PHY power, or switch issue. |
| Ping times out | Wrong IP/subnet, host firewall, bad cable, or no link. |

## 24C.8  Manual TFTP test

Set up the TFTP root on the host:

```sh
$ mkdir -p ~/imx6ull/tftp
$ cp zImage ~/imx6ull/tftp/
$ cp imx6ull-pa-mini.dtb ~/imx6ull/tftp/
```

Use the TFTP setup from Chapter 24, or temporarily run a simple TFTP server.

In U-Boot:

```text
pa-mini=> setenv kernel_addr_r 0x82000000
pa-mini=> setenv fdt_addr_r 0x83000000
pa-mini=> tftp ${kernel_addr_r} zImage
pa-mini=> tftp ${fdt_addr_r} imx6ull-pa-mini.dtb
```

Expected:

```text
Bytes transferred = ...
```

If `ping` works but TFTP fails:

- Check host firewall.
- Check TFTP root directory.
- Check filename spelling.
- Check file permissions.
- Check that `serverip` points to the TFTP host.

## 24C.9  Local boot command

First write the normal local boot.

```text
local_boot=echo Booting from local MMC; \
    load mmc 0:1 ${kernel_addr_r} zImage; \
    load mmc 0:1 ${fdt_addr_r} ${fdtfile}; \
    setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait; \
    bootz ${kernel_addr_r} - ${fdt_addr_r}
```

Test it manually:

```text
pa-mini=> run local_boot
```

If it fails because files are missing, that is okay. The fallback will handle that.

## 24C.10  Network boot command

Now write the network fallback.

```text
net_boot=echo Booting kernel and DTB from TFTP; \
    setenv autoload no; \
    if dhcp; then echo DHCP ok; else echo DHCP failed, using static IP; fi; \
    tftp ${kernel_addr_r} ${bootfile}; \
    tftp ${fdt_addr_r} ${fdtfile}; \
    setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait; \
    bootz ${kernel_addr_r} - ${fdt_addr_r}
```

This uses Ethernet for kernel and DTB, but still mounts the rootfs from `mmcblk0p2`.

Why `autoload no`?

`dhcp` can be configured to automatically download a file. For this chapter we want DHCP to only obtain network settings. We download exact filenames ourselves.

## 24C.11  Fallback boot command

Now combine both:

```text
bootcmd=if run local_boot; then \
            echo Local boot finished; \
        else \
            echo Local boot failed, trying network; \
            run net_boot; \
        fi
```

Important: `bootz` does not return when Linux starts. So the `else` path only runs when a command before `bootz` fails, such as a missing kernel or DTB file.

Add defaults in `include/configs/mx6ull_pa_mini.h`:

```c
#define PA_MINI_NET_FALLBACK_ENV \
    "kernel_addr_r=0x82000000\0" \
    "fdt_addr_r=0x83000000\0" \
    "fdtfile=imx6ull-pa-mini.dtb\0" \
    "bootfile=zImage\0" \
    "serverip=192.168.7.1\0" \
    "ipaddr=192.168.7.2\0" \
    "netmask=255.255.255.0\0" \
    "local_boot=echo Booting from local MMC; " \
        "load mmc 0:1 ${kernel_addr_r} zImage; " \
        "load mmc 0:1 ${fdt_addr_r} ${fdtfile}; " \
        "setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait; " \
        "bootz ${kernel_addr_r} - ${fdt_addr_r}\0" \
    "net_boot=echo Booting kernel and DTB from TFTP; " \
        "setenv autoload no; " \
        "if dhcp; then echo DHCP ok; else echo DHCP failed, using static IP; fi; " \
        "tftp ${kernel_addr_r} ${bootfile}; " \
        "tftp ${fdt_addr_r} ${fdtfile}; " \
        "setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait; " \
        "bootz ${kernel_addr_r} - ${fdt_addr_r}\0" \
    "bootcmd=if run local_boot; then " \
            "echo Local boot finished; " \
        "else " \
            "echo Local boot failed, trying network; " \
            "run net_boot; " \
        "fi\0"
```

Then include `PA_MINI_NET_FALLBACK_ENV` in `CFG_EXTRA_ENV_SETTINGS`.

## 24C.12  Make failure visible

Good fallback logs are boring and clear:

```text
Booting from local MMC
Failed to load 'zImage'
Local boot failed, trying network
Booting kernel and DTB from TFTP
Using FEC0 device
TFTP from server 192.168.7.1; our IP address is 192.168.7.2
Bytes transferred = ...
```

Do not hide the path. During field service, these lines tell the technician what happened.

## 24C.13  Optional: fetch a boot script

A useful extension is to let the server provide a temporary boot script.

Manual test:

```text
pa-mini=> tftp ${scriptaddr} boot.scr
pa-mini=> source ${scriptaddr}
```

A boot script is created on the host from plain text:

```sh
$ cat > boot.cmd <<'EOF'
echo Boot script from TFTP
tftp ${kernel_addr_r} zImage
tftp ${fdt_addr_r} imx6ull-pa-mini.dtb
setenv bootargs console=ttymxc0,115200 root=/dev/mmcblk0p2 rw rootwait
bootz ${kernel_addr_r} - ${fdt_addr_r}
EOF

$ mkimage -A arm -T script -C none -n "pa-mini net script" \
    -d boot.cmd boot.scr
```

This is very useful in the lab because you can change boot behavior without rebuilding U-Boot or editing saved environment.

For production, be careful. A network boot script can execute arbitrary U-Boot commands. Use it only on trusted service networks, or use signed FIT images and secure boot.

## 24C.14  Lab

1. Enable the network command configs.
2. Confirm the U-Boot Device Tree has the FEC, MDIO, PHY address, reset GPIO, and RMII pinmux.
3. Set `ethaddr` for the lab board.
4. Set `ipaddr`, `serverip`, and `netmask`.
5. Confirm `ping ${serverip}` works.
6. Confirm `tftp ${kernel_addr_r} zImage` works.
7. Add `local_boot`.
8. Add `net_boot`.
9. Add the fallback `bootcmd`.
10. Remove or rename `zImage` on the boot partition and confirm U-Boot falls back to TFTP.
11. Restore the local file and confirm local boot is used again.

## 24C.15  Pitfalls

- **No MAC address.** Set `ethaddr` for the lab. Program a real unique MAC in production.
- **Wrong PHY address.** Check schematic strap pins and the DT `reg` value.
- **PHY reset timing too short.** Some PHYs need tens of milliseconds after reset.
- **Host firewall blocks TFTP.** Ping can work while TFTP fails.
- **Wrong rootfs argument.** In this chapter TFTP loads kernel and DTB only. Rootfs still comes from MMC unless you change `bootargs`.
- **Assuming DHCP always works.** Static IP is simpler for board bring-up.
- **Silent fallback.** Always print which path is used.
- **Network script on an untrusted network.** `source boot.scr` runs commands. Treat it like code.

## 24C.16  Going deeper

- U-Boot `doc/usage/cmd/tftpboot.rst`, for TFTP loading behavior.
- U-Boot `doc/usage/cmd/dhcp.rst`, for DHCP behavior.
- U-Boot `doc/usage/environment.rst`, for `ipaddr`, `serverip`, `ethaddr`, `bootfile`, and `autoload`.
- U-Boot `drivers/net/fec_mxc.c`, for the i.MX FEC driver.
- Linux `drivers/net/ethernet/freescale/fec_main.c`, for the kernel driver that later takes over the same MAC.

---

**Previous:** [Chapter 24B: U-Boot board policy with GPIO and I2C](ch24B-uboot-board-policy-i2c-gpio.md)

**Next:** [Chapter 24D: Board identity and variant selection in U-Boot](ch24D-uboot-board-identity-variants.md)
