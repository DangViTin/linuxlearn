---
chapter: 35G
title: Networking, time, and logging
part: V - Root filesystem and user space
estimated_pages: 18
status: draft
---

# Chapter 35G: Networking, time, and logging

The rootfs boots. Your app starts. Now the normal field problems begin:

- It has no IP address.
- DNS does not work.
- Time is 1970.
- Logs vanish after reboot.
- The network comes up after your app already failed.

This chapter gives the practical checklist.

## 35G.1  Bring up Ethernet manually

On a small BusyBox rootfs:

```sh
[root@pa-mini:~]# ip link set eth0 up
[root@pa-mini:~]# ip addr add 192.168.1.50/24 dev eth0
[root@pa-mini:~]# ip route add default via 192.168.1.1
[root@pa-mini:~]# echo 'nameserver 8.8.8.8' > /etc/resolv.conf
```

Test:

```sh
[root@pa-mini:~]# ping -c 3 192.168.1.1
[root@pa-mini:~]# ping -c 3 8.8.8.8
[root@pa-mini:~]# ping -c 3 example.com
```

If the first works but the second fails, routing is wrong.

If the second works but the third fails, DNS is wrong.

## 35G.2  DHCP with BusyBox

BusyBox provides `udhcpc`.

```sh
[root@pa-mini:~]# udhcpc -i eth0
```

For boot, add to `/etc/init.d/rcS`:

```sh
ip link set eth0 up
udhcpc -i eth0 -q
```

`-q` exits after it gets a lease. Without it, `udhcpc` stays in the foreground unless scripted differently.

## 35G.3  Static IP config file

For a simple product, keep one config file:

```sh
# /etc/network.conf
IFACE=eth0
ADDR=192.168.1.50/24
GATEWAY=192.168.1.1
DNS=192.168.1.1
```

Read it from `rcS`:

```sh
if [ -f /etc/network.conf ]; then
    . /etc/network.conf
    ip link set "$IFACE" up
    ip addr add "$ADDR" dev "$IFACE"
    ip route add default via "$GATEWAY"
    echo "nameserver $DNS" > /etc/resolv.conf
else
    udhcpc -i eth0 -q
fi
```

Move the runtime-editable copy to `/data/network.conf` if rootfs is read-only.

## 35G.4  Hostname and `/etc/hosts`

Set:

```sh
echo pa-mini > /etc/hostname
```

And:

```text
127.0.0.1   localhost
127.0.1.1   pa-mini
```

On boot:

```sh
hostname -F /etc/hostname
```

Some tools behave strangely when hostname is missing.

## 35G.5  Time

Many i.MX6ULL boards do not have a battery-backed RTC installed. Without network time, the system may boot at 1970.

Check:

```sh
[root@pa-mini:~]# date
```

Use BusyBox NTP:

```sh
[root@pa-mini:~]# ntpd -n -q -p pool.ntp.org
```

For boot:

```sh
ntpd -p pool.ntp.org
```

On Ubuntu-base, use systemd-timesyncd or chrony:

```sh
[root@pa-mini:~]# timedatectl status
[root@pa-mini:~]# systemctl status systemd-timesyncd
```

If the device has no internet, set time from:

- RTC,
- GPS,
- local NTP server,
- manufacturing tool,
- signed update metadata.

## 35G.6  Logging paths

Decide where logs live:

| Path | Storage | Use |
|------|---------|-----|
| `/run/log` | tmpfs | boot-only logs |
| `/var/log` | tmpfs or persistent | system logs |
| `/data/log` | persistent data partition | field logs |
| `journalctl` | systemd journal | Ubuntu/systemd images |

For BusyBox syslog:

```sh
syslogd -n -O /var/log/messages
```

For background:

```sh
syslogd -O /var/log/messages
klogd
```

If `/var/log` is tmpfs, logs are lost on reboot. That is okay for development. For field debugging, copy important logs to `/data/log`.

## 35G.7  Log rotation

Without rotation, logs fill storage.

Simple BusyBox rotation:

```sh
LOG=/data/log/messages

if [ -f "$LOG" ] && [ "$(wc -c < "$LOG")" -gt 1048576 ]; then
    mv "$LOG" "$LOG.1"
    : > "$LOG"
fi
```

Run it from cron or before starting syslog.

Buildroot can also include `logrotate`.

## 35G.8  Debug checklist

When the board says "network broken":

```sh
ip link
ip addr
ip route
cat /etc/resolv.conf
ping -c 3 <gateway>
ping -c 3 8.8.8.8
ping -c 3 example.com
dmesg | grep -i eth
```

When time is wrong:

```sh
date
hwclock -r
timedatectl status 2>/dev/null || true
ps | grep ntp
```

When logs are missing:

```sh
mount | grep ' /var\| /data'
ps | grep 'syslog\|journald'
ls -lh /var/log /data/log 2>/dev/null
```

## 35G.9  Lab

1. Bring up `eth0` manually with static IP.
2. Bring up `eth0` with DHCP.
3. Break DNS and prove ping-by-IP still works.
4. Start NTP and verify time changes.
5. Configure BusyBox `syslogd` to log to `/data/log/messages`.
6. Reboot and confirm logs survive only if `/data` is persistent.

## 35G.10  Pitfalls

- **App assumes network is ready.** Network may come up after init starts your app. Retry inside the app.
- **DNS file overwritten.** DHCP clients may replace `/etc/resolv.conf`.
- **No RTC.** TLS, package managers, and certificates fail if time is far wrong.
- **Persistent logs fill flash.** Rotate or cap them.
- **Logging too much to eMMC.** Flash has wear. Use tmpfs for noisy logs and persistent storage only for useful summaries.

---

Previous chapter: [Chapter 35F - Your application as a service](ch35F-application-as-service.md)

Next chapter: [Chapter 35B - Read-only rootfs and overlayfs](ch35B-readonly-rootfs-overlayfs.md)
