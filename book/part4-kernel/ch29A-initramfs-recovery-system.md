---
chapter: 29A
title: Initramfs as a recovery system
part: IV - The Kernel
estimated_pages: 18
status: draft
---

# Chapter 29A: Initramfs as a recovery system

Chapter 29 built a tiny initramfs so the kernel had something to run as PID 1.

In real products, initramfs is often more useful than that. It becomes a small recovery system that can boot even when the real root filesystem is broken. This chapter builds that idea in a direct way.

The goal is not to make a pretty rescue UI. The goal is to make a system that can:

- boot without the main root filesystem,
- print useful logs,
- mount the real root filesystem read-only,
- collect files for debugging,
- enter a shell,
- run a controlled update or factory reset path.

That is a practical embedded Linux tool.

## 29A.1  Where the recovery initramfs sits

Normal boot:

```text
U-Boot -> kernel + DTB -> real rootfs -> /sbin/init
```

Recovery boot:

```text
U-Boot -> kernel + DTB + initramfs -> /init inside initramfs
```

The recovery initramfs is loaded by U-Boot together with the kernel. The kernel unpacks it into RAM and runs `/init`.

Because it lives in RAM, it can still boot when the SD card, eMMC partition, or root filesystem has a problem.

| Piece | Normal boot | Recovery boot |
|-------|-------------|---------------|
| Kernel | Same kernel, usually | Same kernel, or a smaller recovery kernel |
| DTB | Board DTB | Same board DTB |
| Root filesystem | SD/eMMC/NFS root | initramfs in RAM |
| PID 1 | `/sbin/init` from rootfs | `/init` from initramfs |
| Main purpose | Run the product | Repair, debug, update, or reset |

## 29A.2  Start from the BusyBox rootfs

Use the BusyBox initramfs from Chapter 29 as the base.

```sh
$ cd ~/imx6ull/code/ch29
$ cp -a initramfs initramfs-recovery
```

The directory should look like this:

```text
initramfs-recovery/
  bin/
  dev/
  etc/
  proc/
  sbin/
  sys/
  tmp/
  usr/
```

Now replace the simple `/init` with a recovery script.

## 29A.3  A small recovery `/init`

Save this as `initramfs-recovery/init`:

```sh
#!/bin/sh

export PATH=/sbin:/bin:/usr/sbin:/usr/bin

mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev 2>/dev/null || mount -t tmpfs tmpfs /dev
mount -t tmpfs tmpfs /tmp

echo
echo "i.MX6ULL recovery initramfs"
echo "Kernel command line:"
cat /proc/cmdline
echo

mount_real_root_ro()
{
    mkdir -p /mnt/root

    echo "Trying /dev/mmcblk0p2 as real rootfs..."
    if mount -o ro /dev/mmcblk0p2 /mnt/root; then
        echo "Mounted real rootfs read-only at /mnt/root"
        return 0
    fi

    echo "Could not mount /dev/mmcblk0p2"
    return 1
}

collect_logs()
{
    mkdir -p /tmp/recovery-logs

    dmesg > /tmp/recovery-logs/dmesg.txt
    cat /proc/cmdline > /tmp/recovery-logs/cmdline.txt
    mount > /tmp/recovery-logs/mounts.txt

    if [ -d /mnt/root/var/log ]; then
        cp -a /mnt/root/var/log /tmp/recovery-logs/root-var-log
    fi

    echo "Logs collected in /tmp/recovery-logs"
}

factory_reset()
{
    echo "Factory reset example"
    echo "This book does not erase anything automatically."
    echo "In a real product, erase only the data partition, not the bootloader."
}

while true; do
    echo
    echo "Recovery menu"
    echo "1) Shell"
    echo "2) Mount real rootfs read-only"
    echo "3) Collect logs"
    echo "4) Factory reset placeholder"
    echo "5) Reboot"
    printf "> "
    read choice

    case "$choice" in
        1)
            sh
            ;;
        2)
            mount_real_root_ro
            ;;
        3)
            grep -q " /mnt/root " /proc/mounts || mount_real_root_ro
            collect_logs
            ;;
        4)
            factory_reset
            ;;
        5)
            reboot -f
            ;;
        *)
            echo "Unknown choice"
            ;;
    esac
done
```

Make it executable:

```sh
$ chmod +x initramfs-recovery/init
```

This script is plain on purpose. In recovery code, boring is good. You want behavior you can read at 2 AM on a failing board.

## 29A.4  Repack the recovery initramfs

```sh
$ cd initramfs-recovery
$ find . -print0 | cpio --null -ov --format=newc | gzip -9 > ../initramfs-recovery.cpio.gz
$ cd ..
```

Copy it to the TFTP directory:

```sh
$ cp initramfs-recovery.cpio.gz ~/imx6ull/tftp/
```

## 29A.5  Boot it from U-Boot

Use the same kernel and DTB, but pass the recovery initramfs as the second `bootz` argument.

```text
=> setenv serverip 192.168.1.10
=> setenv ipaddr 192.168.1.50
=> tftp 0x82000000 zImage
=> tftp 0x83000000 imx6ull-your-board.dtb
=> tftp 0x84000000 initramfs-recovery.cpio.gz
=> setenv initrd_size ${filesize}
=> setenv bootargs 'console=ttymxc0,115200 earlycon loglevel=8 rdinit=/init'
=> bootz 0x82000000 0x84000000:${initrd_size} 0x83000000
```

The `addr:size` form matters. A raw initramfs file does not carry its own size in a way `bootz` can always infer. We save `${filesize}` immediately after the initramfs TFTP command, then pass it to `bootz`.

Expected result:

```text
i.MX6ULL recovery initramfs
Kernel command line:
console=ttymxc0,115200 earlycon loglevel=8 rdinit=/init

Recovery menu
1) Shell
2) Mount real rootfs read-only
3) Collect logs
4) Factory reset placeholder
5) Reboot
>
```

## 29A.6  Add a real-root handoff

Sometimes recovery should repair something and then continue into the normal root filesystem.

The usual flow is:

1. Mount the real root filesystem.
2. Mount `proc`, `sys`, and `dev` under it.
3. Replace the initramfs process with the real init process.

Example:

```sh
mount /dev/mmcblk0p2 /mnt/root || {
    echo "Cannot mount real rootfs"
    sh
}

mount --move /proc /mnt/root/proc
mount --move /sys  /mnt/root/sys
mount --move /dev  /mnt/root/dev

exec switch_root /mnt/root /sbin/init
```

Use this only when the real root filesystem is healthy enough to boot. If the point is recovery, keep the menu path available.

## 29A.7  Network recovery

For factory or lab boards, recovery often needs Ethernet.

If BusyBox was built with `ip`, `udhcpc`, `wget`, and `tftp`, you can do:

```sh
ip link set eth0 up
udhcpc -i eth0
```

Or use a fixed address:

```sh
ip addr add 192.168.1.51/24 dev eth0
ip link set eth0 up
ip route add default via 192.168.1.1
```

Then fetch an update:

```sh
tftp -g -r rootfs.ext4.gz -l /tmp/rootfs.ext4.gz 192.168.1.10
tftp -g -r rootfs.ext4.gz.sha256 -l /tmp/rootfs.ext4.gz.sha256 192.168.1.10
cd /tmp
sha256sum -c rootfs.ext4.gz.sha256
```

Do not write the update until the checksum passes.

## 29A.8  Safe update rules

Recovery code can save a product, but it can also destroy one if it writes the wrong block device.

Use rules like these:

| Rule | Why |
|------|-----|
| Print the target block device before writing | Makes mistakes visible on the console |
| Verify checksum before flashing | Detects broken downloads |
| Do not update the bootloader unless necessary | A bad bootloader update can remove recovery |
| Do not write a mounted filesystem | Avoids corruption |
| Keep factory data separate from rootfs | Reset should not erase MAC address, serial number, or calibration |
| Prefer A/B rootfs for products | Allows rollback after a failed update |

For example:

```sh
TARGET=/dev/mmcblk0p2

echo "About to write rootfs to $TARGET"
echo "Type YES to continue:"
read answer
[ "$answer" = "YES" ] || exit 1

mount | grep -q "$TARGET" && {
    echo "$TARGET is mounted. Refusing to write."
    exit 1
}

sha256sum -c /tmp/rootfs.ext4.gz.sha256 || exit 1
gunzip -c /tmp/rootfs.ext4.gz > "$TARGET"
sync
```

This is not fancy, but it prevents many expensive mistakes.

## 29A.9  U-Boot recovery trigger

Recovery is usually selected by U-Boot.

Common triggers:

| Trigger | Example |
|---------|---------|
| Button held at power-on | Read GPIO in U-Boot, boot recovery if pressed |
| Bootcount exceeded | If Linux fails too many times, boot recovery |
| Environment variable | `setenv bootmode recovery` |
| Factory command | A production tool asks U-Boot to boot recovery |
| Missing rootfs | U-Boot cannot load normal rootfs, so it loads recovery |

Example U-Boot logic:

```text
if test "${bootmode}" = "recovery"; then
    run boot_recovery;
else
    run boot_normal;
fi
```

Recovery is most useful when U-Boot can choose it before Linux is involved.

## 29A.10  Lab

1. Boot the recovery initramfs by TFTP.
2. Select the shell option.
3. Run:

```sh
# cat /proc/cmdline
# dmesg | tail
# mount
```

4. Select the read-only rootfs mount option.
5. Confirm:

```sh
# mount | grep /mnt/root
# ls /mnt/root
```

6. Select the log collection option.
7. Confirm:

```sh
# ls /tmp/recovery-logs
```

At this point you have a recovery system that boots independently from the main root filesystem.

## 29A.11  Common mistakes

| Symptom | Likely cause |
|---------|--------------|
| Kernel ignores initramfs | `bootz` did not receive `addr:size` for the raw initramfs |
| Kernel says `No working init found` | `/init` is missing, not executable, or built for the wrong architecture |
| Shell commands are missing | BusyBox applets were not enabled |
| `/dev/mmcblk0p2` does not exist | MMC driver, device tree, or partition table problem |
| Update writes the wrong partition | Script used a hard-coded device name without checking |
| Recovery loses serial number | Factory data was stored inside an erased partition |

Recovery is not only a debugging trick. It is part of product design.

---

Previous chapter: [Chapter 29 - Initramfs from scratch](ch29-initramfs-from-scratch.md)

Next chapter: [Chapter 30 - Kernel configuration](ch30-kernel-configuration.md)
