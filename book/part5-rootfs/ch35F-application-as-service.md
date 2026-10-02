---
chapter: 35F
title: Your application as a service
part: V - Root filesystem and user space
estimated_pages: 16
status: draft
---

# Chapter 35F: Your application as a service

An embedded Linux product is not finished when the shell boots. The product starts when your application starts automatically, logs somewhere useful, restarts if it crashes, and shuts down cleanly.

This chapter shows the three common service paths:

- BusyBox init script,
- systemd unit,
- Buildroot overlay packaging.

## 35F.1  The application contract

Write the app so the init system can manage it.

Good behavior:

- run in the foreground unless the service wrapper backgrounds it,
- print logs to stdout/stderr or syslog,
- exit nonzero on failure,
- handle `SIGTERM`,
- keep runtime data in `/data` or `/var`, not in `/usr`,
- read config from `/etc/myapp.conf` or `/data/myapp/config`.

Bad behavior:

- double-forking without telling the init system,
- silently creating files under `/`,
- ignoring termination signals,
- writing logs forever without rotation.

## 35F.2  A tiny example app

Save as `myapp.c`:

```c
#include <signal.h>
#include <stdio.h>
#include <stdbool.h>
#include <unistd.h>

static volatile sig_atomic_t running = 1;

static void stop(int sig)
{
    (void)sig;
    running = 0;
}

int main(void)
{
    signal(SIGTERM, stop);
    signal(SIGINT, stop);

    puts("myapp: started");
    fflush(stdout);

    while (running) {
        puts("myapp: tick");
        fflush(stdout);
        sleep(5);
    }

    puts("myapp: stopping");
    return 0;
}
```

Build with the same target toolchain:

```sh
$ arm-none-linux-gnueabihf-gcc -O2 -Wall -o myapp myapp.c
```

Install it in the rootfs:

```sh
$ install -D -m 0755 myapp rootfs/usr/bin/myapp
```

## 35F.3  BusyBox init script

For BusyBox init, create `/etc/init.d/S99myapp`:

```sh
#!/bin/sh

case "$1" in
  start)
    echo "Starting myapp"
    start-stop-daemon -S -b -m -p /var/run/myapp.pid \
      -x /usr/bin/myapp -- >> /var/log/myapp.log 2>&1
    ;;
  stop)
    echo "Stopping myapp"
    start-stop-daemon -K -p /var/run/myapp.pid
    ;;
  restart)
    "$0" stop
    sleep 1
    "$0" start
    ;;
  *)
    echo "Usage: $0 {start|stop|restart}"
    exit 1
    ;;
esac
```

Make it executable:

```sh
$ chmod +x rootfs/etc/init.d/S99myapp
```

In a Buildroot overlay:

```text
board/myorg/pa-mini/rootfs-overlay/etc/init.d/S99myapp
```

BusyBox runs scripts in lexical order if your `rcS` does that. `S99myapp` starts late, after filesystems and networking.

## 35F.4  systemd unit

On Ubuntu-base or a systemd Buildroot image, create `/etc/systemd/system/myapp.service`:

```ini
[Unit]
Description=My embedded application
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/bin/myapp
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable:

```sh
[root@pa-mini:~]# systemctl daemon-reload
[root@pa-mini:~]# systemctl enable --now myapp.service
[root@pa-mini:~]# systemctl status myapp.service
```

Read logs:

```sh
[root@pa-mini:~]# journalctl -u myapp.service -f
```

If the app exits, systemd restarts it.

## 35F.5  Config and data

Use this layout:

| Path | Purpose |
|------|---------|
| `/usr/bin/myapp` | executable, from the rootfs image |
| `/etc/myapp.conf` | default config, version-controlled |
| `/data/myapp/` | persistent runtime data |
| `/var/log/myapp.log` | logs, maybe tmpfs or persistent depending on product |
| `/run/myapp/` | pid files and sockets, tmpfs |

Do not write to `/usr`. In production it may be read-only.

## 35F.6  Health checks

At minimum, add a status command:

BusyBox:

```sh
[root@pa-mini:~]# ps | grep myapp
[root@pa-mini:~]# tail -f /var/log/myapp.log
```

systemd:

```sh
[root@pa-mini:~]# systemctl is-active myapp.service
[root@pa-mini:~]# journalctl -u myapp.service -n 50
```

For a product, pair this with a watchdog in Part VIII. The service restarts the app. The watchdog restarts the board if the whole system gets stuck.

## 35F.7  Lab

1. Build `myapp`.
2. Install it into your Buildroot overlay.
3. Start it with BusyBox init.
4. Kill it and observe whether it restarts.
5. Repeat with a systemd unit on Ubuntu-base.
6. Move its writable data to `/data/myapp`.

## 35F.8  Pitfalls

- **App daemonizes itself under systemd.** Use `Type=forking` only if the app really forks. Prefer foreground mode.
- **Logs disappear.** If `/var/log` is tmpfs, logs vanish at reboot. Decide intentionally.
- **App starts before network.** Add ordering (`After=network-online.target`) or make the app handle network loss.
- **Writing config to `/etc` on read-only rootfs.** Store runtime changes under `/data`.
- **No graceful shutdown.** Handle `SIGTERM`, close files, and flush data.

---

Previous chapter: [Chapter 35A - Ubuntu-base rootfs](ch35A-ubuntu-base.md)

Next chapter: [Chapter 35G - Networking, time, and logging](ch35G-network-time-logging.md)
