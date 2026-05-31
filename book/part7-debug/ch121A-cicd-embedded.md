---
chapter: 121A
title: CI/CD for embedded Linux
part: VIII — Debug, production, advanced
estimated_pages: 18
status: draft
---

# Chapter 121A — CI/CD for embedded Linux

> **What:** **continuous integration** for embedded Linux — building U-Boot, kernel, rootfs on every commit; running smoke tests on **real hardware** in a board farm via a self-hosted CI runner with USB-OTG flashing; a **Labgrid**-style test harness; pass/fail signaling back to the PR. We use **GitHub Actions** (or **GitLab CI**) with a self-hosted runner that has USB connection to a Point Atom MINI; on every push, the runner does the Ch 121 build, flashes via `uuu`, watches serial for `=>` prompt + a sysfs check, captures the serial log, marks the PR pass/fail.
> **Why:** any embedded product shipping updates beyond one engineer's laptop needs CI. The fundamental risk: someone merges a DT change that breaks boot; nobody notices until a customer tries to update; days of fire-fighting. With CI + real-hardware smoke tests on every PR, that bug is caught in 10 minutes. The cost is one $50 dev board + one Linux box + 4 hours setup. The savings — even on a 3-person team — pay back in the first month.
> **Focus:** **the trick is that a normal cloud CI runner has no USB to your hardware; you self-host a runner on a Linux box that physically owns the board**. GitHub Actions / GitLab CI register the self-hosted runner; the runner does cross-builds, then drives the board via uuu + a serial terminal scripted in Python. A "smoke test" is small (boot, get prompt, run 3 sanity checks, capture log) but enormously valuable. Scale from one board to a farm of 10 via Labgrid (RPC framework for board control).

## 121A.1  What "CI" means for embedded

Traditional cloud CI (Travis, Circle, GitHub Actions hosted runners):
- Runs in a VM with no hardware access.
- Can cross-compile your kernel + check it builds.
- Can run unit tests on x86 (QEMU is option).
- **Cannot** verify the binary works on real silicon.

For embedded, "it compiles" is necessary but not sufficient. The real value of CI is **catching regressions on actual hardware** — a DT change that compiles but breaks boot, an MMC driver edit that boots but corrupts the rootfs, a regulator change that boots but burns more power.

The architecture:

```
   PR opened
        │
        ▼
   GitHub Actions (cloud runner): cross-build U-Boot + kernel
        │
        ▼
   Artifact upload (kernel.zImage, dtb, u-boot.imx, rootfs.tar)
        │
        ▼
   Self-hosted runner (your Linux box with USB to a board):
        │ - download artifacts
        │ - flash board via uuu
        │ - power-cycle board (via USB-power-switch GPIO)
        │ - capture serial; wait for "=>"
        │ - in U-Boot, load kernel + boot
        │ - wait for shell prompt
        │ - run sysfs check (e.g., ls /sys/class/net/eth0 should exist)
        │ - capture full serial log
        │ - report pass/fail
        ▼
   PR status updated
```

## 121A.2  GitHub Actions — the cross-build half

`.github/workflows/build.yml`:

```yaml
name: build
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  cross-build:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: recursive

      - name: Install cross toolchain
        run: |
          sudo apt-get update
          sudo apt-get install -y gcc-arm-linux-gnueabihf bison flex bc \
            libssl-dev device-tree-compiler u-boot-tools

      - name: Build U-Boot
        run: |
          cd u-boot
          make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- myboard_defconfig
          make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc)

      - name: Build kernel
        run: |
          cd linux
          make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- imx_v7_defconfig
          make ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc) zImage dtbs

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: board-images
          path: |
            u-boot/u-boot-dtb.imx
            linux/arch/arm/boot/zImage
            linux/arch/arm/boot/dts/imx6ull-myboard.dtb
```

Now every PR gets a clean build. Failure = compile error caught.

## 121A.3  The self-hosted runner — the hardware half

On your Linux box that physically owns a Point Atom MINI:

```sh
# 1. Install runner
mkdir actions-runner && cd actions-runner
curl -O -L https://github.com/actions/runner/releases/download/v2.310.0/actions-runner-linux-x64-2.310.0.tar.gz
tar xzf actions-runner-linux-x64-2.310.0.tar.gz

# 2. Register (token from GitHub → repo settings → Actions → Runners)
./config.sh --url https://github.com/myuser/myrepo --token AABBCCDDEEFF

# 3. Run (or systemd-install)
./run.sh
# Connected to GitHub
# 2026-05-31 12:00:00Z: Listening for Jobs
```

Now add a hardware-test job:

```yaml
  hardware-smoke:
    needs: cross-build
    runs-on: [self-hosted, imx6ull]
    steps:
      - name: Download artifacts
        uses: actions/download-artifact@v4
        with:
          name: board-images

      - name: Flash via uuu
        run: |
          # Power off board (via USB power-control GPIO on the runner)
          gpioset gpiochip0 18=0
          sleep 2

          # Set boot mode pins to USB-SDP (also via GPIO)
          gpioset gpiochip0 19=1

          # Power on
          gpioset gpiochip0 18=1
          sleep 1

          # uuu sees the board enter SDP; loads U-Boot to OCRAM, runs it
          uuu -b emmc u-boot-dtb.imx

          # Now uuu pushes kernel + rootfs
          uuu -b emmc_all u-boot-dtb.imx zImage imx6ull-myboard.dtb rootfs.tar

      - name: Smoke test
        run: |
          python3 smoke_test.py /dev/ttyUSB0 --timeout 60

      - name: Upload serial log
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: serial-log
          path: serial.log
```

The runner is labelled `imx6ull`; only jobs targeting that label run on this hardware. You can have multiple labelled runners (one per board type).

## 121A.4  The smoke test script

```python
#!/usr/bin/env python3
"""Smoke test: power-cycle target, watch serial for boot completion + checks."""
import serial, time, sys, argparse

def expect(port, pattern, timeout):
    deadline = time.time() + timeout
    buf = ''
    while time.time() < deadline:
        chunk = port.read(port.in_waiting or 1).decode('utf-8', errors='replace')
        buf += chunk
        sys.stdout.write(chunk)
        sys.stdout.flush()
        if pattern in buf:
            return buf
    raise TimeoutError(f"Did not see {pattern!r} within {timeout}s")

def send(port, line):
    port.write((line + '\r\n').encode())
    port.flush()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('device')
    ap.add_argument('--timeout', type=int, default=60)
    args = ap.parse_args()

    p = serial.Serial(args.device, 115200, timeout=1)

    # Watch for U-Boot prompt
    expect(p, '=>', args.timeout)
    print("\n[OK] U-Boot prompt detected")

    # Boot kernel
    send(p, 'boot')

    # Watch for login prompt (BusyBox-typical)
    expect(p, 'login:', 60)
    print("\n[OK] Kernel booted to login")

    # Auto-login
    send(p, 'root')
    expect(p, '# ', 10)
    print("\n[OK] Logged in")

    # Sanity checks
    send(p, 'ls /sys/class/net/eth0')
    expect(p, '# ', 5)
    send(p, 'echo $?')
    rc = expect(p, '# ', 5)
    assert '0' in rc.split('\n')[-2], "eth0 not present"
    print("[OK] eth0 sysfs present")

    send(p, 'cat /proc/meminfo | head -3')
    expect(p, '# ', 5)

    send(p, 'i2cdetect -y 0 2>&1')
    expect(p, '# ', 10)

    # Power off cleanly
    send(p, 'poweroff')
    print("[OK] All checks passed")

if __name__ == '__main__':
    main()
```

Run on the self-hosted runner; outputs all of the serial conversation; exit 0 on success, non-zero on any failure → PR gets a red X.

## 121A.5  Labgrid — for board farms

When you have 5+ boards or want richer control (toggle pins, video capture, multimeter readings), **Labgrid** (Pengutronix) is the answer. It's a Python framework + RPC server that owns the hardware.

```sh
pip install labgrid

# Config: /etc/labgrid/places.yaml
places:
  imx6ull-1:
    drivers:
      - DigitalOutputPowerDriver:
          name: power
          gpio: gpio18-out
      - SerialDriver:
          name: serial
          port: /dev/ttyUSB0
      - SDMuxDriver:
          name: sdmux
          gpio: gpio20-out

# In tests
client = labgrid.Client()
target = client.acquire('imx6ull-1')
target.power.on()
target.sdmux.switch_to_target()
target.serial.expect('=>')
```

Multiple test runners can share the same board farm; Labgrid handles locking. For larger teams, this is the production-grade setup.

## 121A.6  Test artifact storage

A board boot log is ~50 KB; build outputs are ~150 MB; you generate 10–50 builds/day. Plan storage:

- **GitHub Actions artifact retention**: 90 days default; configurable.
- **Self-hosted artifact server** (e.g., minio S3-compatible): infinite retention.
- **A binary cache** (e.g., `sccache` for builds): speeds up re-builds.

For long-term: stash every shipped build's `vmlinux` and `.ko` files in S3, keyed by git-sha. When a customer reports an oops, you can decode it (Ch 119).

## 121A.7  Caching for fast cross-builds

Cross-builds are slow (~10–30 min). Speed up:

- **ccache**: caches compiler output keyed by source hash. 80 % cache hit = 5× speed-up.
  ```yaml
  - uses: actions/cache@v3
    with:
      path: ~/.ccache
      key: ccache-${{ matrix.target }}-${{ github.sha }}
      restore-keys: ccache-${{ matrix.target }}-
  ```
- **Module dependencies cache**: kernel `*.cmd` files + `.o` files. `make` is incremental if these survive.
- **Toolchain cache**: download the cross compiler once; cache the result.

## 121A.8  Trigger patterns

Don't run the full pipeline on every commit:

```yaml
on:
  push:
    branches: [main]                # always test main
    paths-ignore:
      - '**/*.md'                   # skip docs-only changes
  pull_request:
    branches: [main]
    paths:
      - '!**/*.md'
  schedule:
    - cron: '0 6 * * *'             # daily build (catches dependency drift)
  workflow_dispatch:                 # manual trigger via UI
```

Tag pushes can trigger the **release** workflow (build + sign + upload a downloadable image to your customer portal).

## 121A.9  Notifications

When the board farm is offline or builds fail repeatedly:

- **Slack webhook**: `${{ secrets.SLACK_WEBHOOK }}` posts to a channel on failure.
- **Email**: GitHub does this by default for failed Actions.
- **Pager**: PagerDuty integration for production-blocking failures.

```yaml
- name: Notify on failure
  if: failure()
  run: |
    curl -X POST $SLACK_WEBHOOK_URL \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\":x: Build failed: ${{ github.event.pull_request.title }} (${{ github.run_id }})\"}"
```

## 121A.10  Lab

1. **GitHub Actions cross-build.** Set up `.github/workflows/build.yml`. Push a commit; verify the build runs in cloud.
2. **Trigger failure.** Introduce a syntax error in a DT; push; verify the build fails red.
3. **Self-hosted runner.** Install runner on a Linux box with USB to a board. Register; verify it shows "Idle" in GitHub UI.
4. **Hardware test job.** Add `hardware-smoke` job; verify it runs on the self-hosted runner.
5. **smoke_test.py.** Write a Python script that drives the serial console and runs 3 checks. Run locally first; then in CI.
6. **Power-cycle GPIO.** Wire a USB-controlled power switch (e.g., `usbrelay`) so the runner can hard-reboot the board between tests.
7. **uuu flashing.** Set up the runner to use `uuu` to flash a fresh image on every test. Verify it works clean.
8. **ccache.** Wire ccache into the build; observe 5× speedup on the second run.
9. **Labgrid (stretch).** Install Labgrid; expose 2 boards via the framework; have CI acquire one at random.
10. **Slack notification.** On test failure, post a message to a Slack channel.

Commit `.github/workflows/*.yml`, `smoke_test.py`, runner setup notes to `code/ch121A-cicd/`.

## 121A.11  Pitfalls

- **Self-hosted runner security.** A runner with checkout permissions can run arbitrary PR code. Don't allow forks to trigger your hardware runner without manual approval (`pull_request_target` is dangerous).
- **USB instability.** Long USB cables drop intermittently; uuu fails randomly. Use short, shielded cables; powered hubs.
- **uuu version drift.** New SoCs need new uuu versions; pin to a known-good.
- **Serial port conflicts.** Two tests grabbing /dev/ttyUSB0 simultaneously = chaos. Labgrid handles locking; ad-hoc scripts need flock.
- **Board "stuck on" between tests.** If a previous test crashed the board, it may not respond to flash. Always hard-power-cycle at test start.
- **Time-of-day cron.** `cron: '0 6 * * *'` is UTC; off-by-time-zone embarrassment. Comment your timezone assumption.
- **Caches stale.** ccache occasionally returns wrong objects when toolchain changes; invalidate cache on toolchain bump.
- **Test pollution.** Test #1 leaves the board with the wrong network config; test #2 fails for unrelated reasons. Always flash a fresh image.
- **Storage exhausted.** Build artifacts add up; GitHub limits to 500 MB per repo. Purge old artifacts.
- **Workflow YAML errors.** Subtle indentation or quoting bugs in YAML cause "workflow failed before starting" with no useful error. Validate with `actionlint`.

## 121A.12  Going deeper

- **GitHub Actions documentation** — https://docs.github.com/actions.
- **GitLab CI docs** — similar concepts, different syntax.
- **Labgrid** — https://labgrid.org/.
- **uuu (Universal Update Utility)** — NXP's MFGTOOL successor; https://github.com/nxp-imx/mfgtools.
- **`usbrelay`** — controls cheap USB relay boards for power-cycling.
- **`actionlint`** — GitHub Actions YAML validator.
- **Pengutronix's "Labgrid" talks on YouTube** — board-farm architecture in production.
- **LAVA (Linaro Automated Validation Architecture)** — the Linaro-style board farm; complex but powerful.
- **Ch 121** — the build script that CI calls.
- **Ch 125** — for over-the-air updates that CI builds and signs.

---

> Next chapter: **Chapter 122 — Build your own cross-toolchain** — bootstrapping gcc + glibc/musl from sources.
