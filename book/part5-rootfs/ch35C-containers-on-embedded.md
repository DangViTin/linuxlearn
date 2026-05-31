---
chapter: 35C
title: Container runtimes on embedded (Podman + OCI)
part: V — Root filesystem & user space (supplementary v1.2)
estimated_pages: 16
status: draft
---

# Chapter 35C — Container runtimes on embedded

> **What:** running OCI containers on an i.MX6ULL with Podman. By the end you'll have an Alpine Linux container running a small Python web server, accessing the host's GPIO from inside the container.
> **Why:** modern embedded products increasingly separate "the base system" (kernel + bootloader + minimal rootfs, updated rarely) from "the application" (one or more containers, updated whenever a customer-facing change is needed). Containers give you reproducible app deployment, image-based updates, and the ability to roll back in seconds. The cost is some RAM and some complexity; the benefit is a deployment story that scales from one device to one million.
> **Focus:** **the three kernel features that make containers work** — namespaces (process isolation), cgroups (resource limits), and overlayfs (storage). All three are in mainline Linux for years; you just need them turned on in `.config`.

## 35C.1  When containers make sense on embedded

| Reason | Yes | No |
|--------|:---:|:---:|
| App + base system have different update cadences | ✓ | |
| Single product variant, single binary | | ✓ |
| Multiple apps that mustn't interfere | ✓ | |
| Need to ship third-party software unmodified | ✓ | |
| Need 100 % minimum disk footprint | | ✓ |
| Need < 50 ms cold-start latency | | ✓ |
| Need to roll back app-only without touching kernel | ✓ | |

For a single-purpose appliance with one in-house binary, containers are overhead. For a smart-camera platform that ships one base image to thousands of customers, with each customer running 1-5 of *their* applications on top, containers are how you keep your sanity.

The i.MX6ULL is on the small side for containers, but it's tractable: a single Alpine-based container costs ~30 MB additional disk and ~15 MB RAM at idle.

## 35C.2  What containers actually are

A "container" is just a Linux process group with three things layered on:

1. **Namespaces** — the kernel maintains separate "views" per namespace type: PID, network, mount, UTS (hostname), IPC, user, cgroup. A process in a PID namespace sees only processes in that namespace; it thinks it's PID 1.
2. **Cgroups (control groups)** — resource limits per group: CPU, memory, IO. Enforced by the kernel.
3. **Overlay filesystem** — the container's root is an overlayfs over the image's read-only layers + a writable upper. Same `overlayfs` from Chapter 35B.

That's it. There is no "container runtime" magic — just a process with namespaces, cgroups, and a careful mount setup. **Docker, Podman, containerd, and CRI-O all do the same thing**; they differ in UI, daemons (or lack of), and ecosystem.

For embedded, **Podman** wins:

- **Daemonless.** Docker has a privileged daemon that runs as root and listens on a socket. Podman has no daemon — `podman run` directly spawns the container process. One less moving part.
- **Rootless mode.** Containers can run as a normal user, using user namespaces. Better security story than Docker.
- **Drop-in CLI-compatible with Docker.** `podman pull`, `podman run`, `podman ps` all work like `docker pull`, etc.

## 35C.3  Kernel configuration

The kernel features containers need. Check your `.config`:

```
CONFIG_NAMESPACES=y
CONFIG_UTS_NS=y
CONFIG_IPC_NS=y
CONFIG_USER_NS=y
CONFIG_PID_NS=y
CONFIG_NET_NS=y
CONFIG_CGROUPS=y
CONFIG_MEMCG=y
CONFIG_CPUSETS=y
CONFIG_CGROUP_DEVICE=y
CONFIG_CGROUP_FREEZER=y
CONFIG_CGROUP_PIDS=y
CONFIG_CGROUP_SCHED=y
CONFIG_CGROUP_NET_PRIO=y
CONFIG_BRIDGE=y                # for the container network bridge
CONFIG_NETFILTER=y
CONFIG_NETFILTER_XT_MATCH_ADDRTYPE=y
CONFIG_NF_CONNTRACK=y
CONFIG_OVERLAY_FS=y
CONFIG_SECCOMP=y
CONFIG_VETH=y                  # virtual ethernet pair for container networking
```

`imx_v6_v7_defconfig` enables most of these; `CONFIG_USER_NS` is sometimes off for size and needs flipping on.

After confirming and rebuilding the kernel:

```
[root@pa-mini:~]# zgrep -E "CONFIG_(NAMESPACES|CGROUPS|OVERLAY_FS|USER_NS)" /proc/config.gz
CONFIG_NAMESPACES=y
CONFIG_USER_NS=y
CONFIG_CGROUPS=y
CONFIG_OVERLAY_FS=y
```

(If `/proc/config.gz` is empty, your kernel was built without `CONFIG_IKCONFIG_PROC=y`. The check still works by inspecting `.config` on the build host.)

## 35C.4  Install Podman

On a Buildroot rootfs, enable `BR2_PACKAGE_PODMAN`. On Ubuntu-base:

```sh
$ ./mount-ubuntu.sh   # chroot in
root@host:/# apt update
root@host:/# apt install -y podman
```

Verify:

```
[root@pa-mini:~]# podman --version
podman version 4.3.1

[root@pa-mini:~]# podman info | head
host:
  arch: arm
  buildahVersion: 1.28.2
  cgroupManager: systemd        ← or "cgroupfs" for non-systemd setups
  cgroupVersion: v2
  ...
```

If `cgroupManager` is shown but errors are reported, you may need to switch to `cgroupfs`. On a BusyBox rootfs:

```sh
cat > /etc/containers/containers.conf <<'EOF'
[engine]
cgroup_manager = "cgroupfs"
events_logger = "file"
EOF
```

## 35C.5  Pull and run a first container

```
[root@pa-mini:~]# podman pull docker.io/library/alpine:latest
Trying to pull docker.io/library/alpine:latest...
Getting image source signatures
Copying blob sha256:abcdef... done
Copying config sha256:fedcba... done
Writing manifest to image destination
abcdefabcdef...

[root@pa-mini:~]# podman run --rm alpine sh -c "echo hello from $(uname -m)"
hello from armv7l
```

A real Alpine Linux 3.x container, pulled, run, exited, cleaned up — in roughly 30 seconds plus download time. Alpine images for armv7 are ~3-5 MB compressed, ~10 MB on disk.

Run it interactively:

```
[root@pa-mini:~]# podman run --rm -it alpine sh
/ # cat /etc/os-release
NAME="Alpine Linux"
ID=alpine
VERSION_ID=3.19.1
...
/ # apk add python3
/ # python3 -c 'print("hi")'
hi
/ # exit
```

You just ran Alpine's apk inside a container running on Ubuntu (or BusyBox), all on top of the same kernel. The container thinks it's a complete Alpine system.

## 35C.6  Container that talks to GPIO

The interesting case for embedded: a container that can access host hardware.

Goal: a container running a Python script that toggles the LED via `/sys/class/leds/led0/brightness`.

`Dockerfile`:

```dockerfile
FROM alpine:latest

RUN apk add --no-cache python3

COPY blink.py /blink.py

CMD ["python3", "/blink.py"]
```

`blink.py`:

```python
#!/usr/bin/env python3
import time

LED = "/sys/class/leds/led0/brightness"

while True:
    with open(LED, "w") as f:
        f.write("1")
    time.sleep(0.5)
    with open(LED, "w") as f:
        f.write("0")
    time.sleep(0.5)
```

Build:

```
[root@pa-mini:~]# podman build -t led-blinker .
```

Run, with `/sys/class/leds/` bind-mounted into the container:

```
[root@pa-mini:~]# podman run --rm -v /sys/class/leds:/sys/class/leds:rw led-blinker
```

The LED blinks. Inside the container, the Python script writes to `/sys/class/leds/led0/brightness`; thanks to the bind mount, those writes hit the host's actual sysfs.

A more careful invocation passes only the *specific* device, not the entire sysfs hierarchy:

```
[root@pa-mini:~]# podman run --rm \
    -v /sys/class/leds/led0:/sys/class/leds/led0:rw \
    led-blinker
```

That gives the container access to *only* `led0`'s files. Other LEDs (and the rest of `/sys/`) remain invisible.

For more privileged access patterns:

- **`--device /dev/i2c-0`** to expose `/dev/i2c-0` to the container.
- **`--cap-add SYS_RAWIO`** to grant a capability the container needs.
- **`--privileged`** (last resort) to give the container full host access. Bad practice except for development.

## 35C.7  Storage and rootfs layout

Podman stores images and containers under `/var/lib/containers/` (rootful) or `~/.local/share/containers/` (rootless). On embedded systems where `/var/` may be tmpfs (Ch 35B), redirect this:

```sh
$ cat > /etc/containers/storage.conf <<'EOF'
[storage]
driver = "overlay"
runroot = "/run/containers/storage"
graphroot = "/data/containers/storage"
EOF
```

`graphroot` should be on persistent storage. `runroot` (the per-run temp) on tmpfs is fine.

## 35C.8  When *not* to use containers

Be honest about the costs:

- **RAM.** Each container adds ~10-20 MB at minimum. On 512 MB i.MX6ULL with three containers, that's 50 MB just to *be* in containers. Not always a problem; sometimes prohibitive.
- **Boot time.** `podman.service` plus container-pull-and-start adds 2-5 seconds.
- **Complexity.** "Why isn't my hardware working?" answers gain a layer: "Is it the device driver? The bind mount? The cgroup device controller? The user-namespace mapping?"
- **Determinism.** A pulled container's exact bytes depend on the registry server. For a closed-supply-chain product, you'd mirror the registry or build images locally and bake them into the rootfs.

For one-purpose appliances, just ship a binary. For dynamic product lines that update frequently, containers earn their cost.

## 35C.9  Production patterns

A few real-world patterns:

### Pre-loaded image, no registry pulls

For products without reliable internet, you don't `podman pull` on every boot — you bake the image into the rootfs at build time:

```sh
# At build time on the host:
$ podman save -o myapp.tar localhost/myapp:v1.0
$ cp myapp.tar $TARGET_ROOTFS/opt/preloaded-images/

# At first boot on the target:
[root@pa-mini:~]# podman load -i /opt/preloaded-images/myapp.tar
[root@pa-mini:~]# podman run -d --restart=always myapp:v1.0
```

### `podman generate systemd`

Generate a systemd unit file for a container:

```
[root@pa-mini:~]# podman generate systemd --new --name myapp --files
$ ls
container-myapp.service
[root@pa-mini:~]# cp container-myapp.service /etc/systemd/system/
[root@pa-mini:~]# systemctl enable --now container-myapp.service
```

The systemd unit handles auto-start, dependencies, log capture, and restart-on-failure.

### Updates via image swap

```sh
# New version available:
podman pull registry.example.com/myapp:v1.1
podman stop myapp
podman rm myapp
podman run -d --name myapp --restart=always registry.example.com/myapp:v1.1

# If it crashes immediately:
podman rollback ...    # or pull v1.0 again
```

Image swap is atomic at the container level: either the new image is running or the old one is. Much cleaner than "extract a tarball into /opt/myapp/" updates.

## 35C.10  Lab

1. **Install Podman.** Get to `podman --version` on the target.
2. **Pull and run Alpine.** Confirm it works.
3. **Build a custom image.** Write a `Dockerfile` for a tiny Python script. `podman build` it; `podman run` it.
4. **Bind-mount sysfs.** Build the LED blinker container and run it with `--v` mounting `/sys/class/leds/`. Verify LED toggles.
5. **Measure overhead.** `podman info` reports memory; do a `free -h` before and after `podman run`. Quantify the cost.
6. **Pre-bake an image.** `podman save` on the host, copy to the target, `podman load` on first boot. Verify no network calls happen.
7. **Systemd integration.** Generate a unit file via `podman generate systemd`; enable it; reboot; verify the container starts.

## 35C.11  Pitfalls

- **`USER_NS` disabled.** Symptom: Podman rootless mode fails with "no subuid map". Fix: rebuild kernel with `CONFIG_USER_NS=y`.
- **cgroup v1 vs v2 mismatch.** Some older systemd setups expect v1 hierarchies; Podman 4.x prefers v2. Force v2 in the kernel cmdline: `cgroup_no_v1=all systemd.unified_cgroup_hierarchy=1`.
- **Network bridge not created.** Without `CONFIG_BRIDGE` and `CONFIG_VETH`, containers have no network. Symptom: container can't reach the internet. Fix: kernel config.
- **`/var/lib/containers/` on tmpfs.** Loses every image on reboot. Always redirect `graphroot` to persistent storage.
- **Trying to `podman pull` from a registry behind a corporate proxy.** Set `HTTPS_PROXY=...` in `/etc/containers/registries.conf` or globally.
- **Image platform mismatch.** `podman pull alpine` might fetch x86_64 by default if the registry doesn't auto-select. Force: `podman pull --platform linux/arm/v7 alpine`.
- **Bind-mount permissions.** Containers run as a different UID than the host's. Bind-mounting `/sys/class/gpio/` may work for reads but not writes if UID-mapping isn't right. The `--privileged` workaround is too coarse; the correct fix is `--user 0:0` plus careful capability grants.

## 35C.12  Going deeper

- **Podman documentation** at `docs.podman.io/` — comprehensive and well-organised.
- **`man podman-run`** for the full set of options.
- **`runc`** — the lower-level container runtime that Podman invokes. Smaller, fewer dependencies; sometimes used directly on resource-constrained systems.
- **`containerd` and `nerdctl`** — alternative runtime + CLI, slightly closer to "what Kubernetes uses." Heavier than Podman but ecosystem-richer.
- **`Buildah`** — image-building companion to Podman without needing a daemon.
- **OCI Image Specification** at `github.com/opencontainers/image-spec` — the standard image format Podman, Docker, and friends all consume.
- **`balenaEngine`** — a stripped-down Docker variant specifically for embedded. Used by balena.io's commercial fleet-management platform.

---

**End of Part V.** You can now build a rootfs three ways (by hand, Buildroot, Ubuntu-base), harden it for production (RO + overlayfs), and ship containerised applications on top.

> Next chapter: **Chapter 36 — Your first kernel module.** With the user-space picture complete, we turn back to the kernel to write the driver that gives `/sys/class/leds/led0/brightness` its behavior.
