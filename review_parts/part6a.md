# Part VIa — Driver foundations + subsystems: Review

## Cross-cutting observations

- **Mainline kernel API drift (critical).** Multiple chapters use APIs that have changed signatures in the kernels you're likely targeting (5.15 LTS, 6.1 LTS, 6.6 LTS, 6.12 LTS). The most damaging ones:
  - `class_create(THIS_MODULE, "name")` — the `owner` argument was removed in **6.4** (commit 1aaba11da9aa). On 6.6+ the call is `class_create("name")`. Ch 38, Ch 40 comparison table, and Ch 41 references all show the old form. State once which kernel the book targets and add a one-paragraph "API drift" note pointing readers at the new signature when they're on >=6.4.
  - `i2c_driver.probe` lost its `(struct i2c_client *, const struct i2c_device_id *)` two-arg signature in **6.3** (commit b8a1a4cd5a98 made `probe_new` the canonical, then renamed). Modern kernels expect `int probe(struct i2c_client *client)`. Ch 46 uses the old two-arg form everywhere. The AT24/BME280 reference drivers you point to are now single-arg.
  - `.remove` returning `int` for `platform_driver`/`i2c_driver` was changed to `void` in 6.11 (and `remove_new` introduced earlier as the transition mechanism). Ch 39, Ch 46 still show `return 0;` from remove. Note this for readers on bleeding-edge kernels.
  - SPI's `.remove` is already `void` in your Ch 47 example — good — but make this consistency explicit.
- **MCU-bridge sidebars are inconsistent.** Ch 36 has a strong MCU-vs-Linux table; Ch 37 starts the user/kernel-boundary discussion well; Ch 41 nails the FreeRTOS-vs-kernel-context framing in §41.1. But Ch 42 (sleeping), Ch 43 (IRQs), Ch 46/47 (I2C/SPI) jump straight into Linux abstractions with no MCU mental-anchor. Promise from the persona is that *this part* is THE goal — every new concept needs a 2-3 sentence "in MCU/RTOS you would have… in Linux you…" callout.
- **No driver-skeleton callout box.** A persistent reader-friendliness improvement: each chapter would benefit from a tiny "shape of every driver in this category" box at the top, like:
  ```
  init → register subsystem object → callbacks fire → unregister → exit
  ```
  …with the chapter's actual function names plugged in. The MCU dev needs this scaffolding to know what's about to land.
- **`THIS_MODULE` is used dozens of times but never explained.** First mention is Ch 37 §37.4 (`.owner = THIS_MODULE`); first explanation is missing. Add one sentence in Ch 36 when introducing `module_init`: "`THIS_MODULE` is a per-module token, defined by the Kbuild scaffolding, that frameworks use to pin module refcounts so you can't be unloaded while the kernel still has a pointer to your code."
- **`dev_info` vs `pr_info` switch happens silently.** Ch 36 establishes `pr_info`; Ch 39 onwards uses `dev_info(&pdev->dev, ...)` without ever introducing the family. Add 2 lines in Ch 39 §39.3: "Once you have a `struct device *`, prefer `dev_info(dev, ...)`. It prefixes the log line with the device name automatically — `dev_info(&pdev->dev, "ready")` prints `linuxlearn-blinker 0.gpio: ready` instead of just `ready`."
- **`container_of` appears in Ch 37 but is never properly explained.** "Compile-time trick" is the only hint. The MCU reader has never seen offsetof-based pointer math. A 4-line diagram showing `cdev` member inside `hello_dev` and the pointer-subtract is warranted.
- **Locking-context cross-references are weak.** Ch 41 introduces sleeping/atomic distinction. Ch 42 uses `mutex_lock` in driver code. Ch 43 forbids it. Ch 44 says "use `_cansleep` in process context." Ch 46 silently uses `i2c_transfer` (sleeps) inside what could be IRQ-context handlers in some examples. A single "context-rules" sidebar in Ch 41 that you cross-link from every later chapter would clean this up. Suggested name: *"the sleep/atomic compact"*.
- **No upfront DT phandle / `&label` syntax recap.** Chapters from 39 onwards rely heavily on `&i2c1`, `&pwm1`, `&gpio4`, etc. Even the persona who got through Part V may have lost this. One sentence each in Ch 39 and Ch 44 reminding "`&foo` references a node labelled `foo:` elsewhere in the DT" would help.

## Ch36 — Your first kernel module

### Readability
- §36.1 opening "If your last decade was MCU work" — strong hook, keep.
- "Twenty-some lines. Let's go through each." (after the code block at line 60) — change to "About twenty lines. Let's walk through them." ("twenty-some" reads as "approximately twenty plus a few" and is informal/odd for non-native readers).
- §36.3 "The kernel build system (Kbuild) is invasive — it generates per-module ELF sections" — "invasive" has negative connotation; consider "deeply involved" or "tightly coupled to your build."
- §36.6 final paragraph "Crank it up" — informal; use "Increase it" or "Raise it."
- §36.8 Pitfalls bullet on `__init` data: "Compile warning: 'section mismatch.'" — quote the actual modpost warning text: `WARNING: modpost: section mismatch in reference: hello_init (section: .init.text) -> some_runtime_fn (section: .text)` so readers grep-match what they'll see.

### MCU-engineer friendliness
- §36.2 explanation of `MODULE_LICENSE`: great. Add one sentence on *why* `EXPORT_SYMBOL_GPL` exists at all — "the kernel community uses license-tagged symbols as a contract: GPL symbols are stable kernel internals; non-GPL symbols are the stable user-facing kernel API. Without GPL on your module, you only see the user-facing API."
- §36.5 module parameters: missing a bridge — "this is the Linux equivalent of `#define CFG_FOO 1` in your firmware, except you can change it after boot without recompiling." That one sentence saves three paragraphs of explanation.
- §36.6 `printk` table — bridge: "MCU `printf`-over-UART is roughly `pr_warn` level. The level system lets you keep low-priority messages in the dmesg ring buffer without flooding the console — useful when you don't have a fast UART."

### Missing examples / figures
- After §36.2 table headers, show a small "anatomy" ASCII diagram of `hello.ko` listing the sections (`.text`, `.init.text`, `.exit.text`, `.modinfo`, `__versions`) so the `__init`/`__exit` story has visual anchor.
- After §36.3 build log, a one-line diagram of the link relationship: `hello.o + Module.symvers (from kernel) → modpost generates hello.mod.c → hello.mod.o + hello.o → hello.ko`.
- Add a "what happens at `insmod`" mini-diagram between §36.3 and §36.4: ELF on disk → `init_module()` syscall → kernel allocates module address space → relocations applied → `module_init` callback invoked.

### Technical errors
- §36.2 "Stack is ~16 KB and shared with whoever called you" — ARM32 kernel stack is **8 KB by default** (`THREAD_SIZE_ORDER=1`, 2 pages, 4KB pages). 16 KB is x86_64/arm64. Either qualify or state "8 KB on i.MX6ULL." Ch 37 §37.9 even contradicts §36.2 by saying "16 KB on i.MX6ULL (sometimes 8 KB)" — fix both to "8 KB on ARM32 i.MX6ULL with `CONFIG_4KSTACKS`-equivalent (the default)."
- §36.2 "`module_init(hello_init)`. This isn't a function call — it's a macro that expands to a special section entry" — slightly misleading. It expands to `__inittest`/`init_module` aliasing or to an `__initcall` entry (for built-in). It's worth saying "for a `.ko`, it aliases `hello_init` to the symbol `init_module`, which the loader looks up by name."
- §36.3 `vermagic` example shows `mod_unload modversions ARMv7`. Real i.MX6ULL vermagic also typically includes `preempt` / `preempt_rt` / `mod_unload modversions ARMv7 p2v8`. Pull the actual string from a built kernel rather than a synthesized one.
- §36.6 console-loglevel table is **off by one** in the framing: "console shows messages with priority **lower than or equal to** the first number" — actually messages with level **strictly less than** the console_loglevel are printed. With `4 4 1 7`, levels `0..3` print; `4..7` do not. The text says "0–3 print … 4–7 only go to the ring buffer" which agrees in outcome — but the rule stated is "lower than or equal to" which would include 4. Reword to "strictly less than."

### Knowledge prerequisites missing
- `THIS_MODULE` — see cross-cutting note above; introduce in §36.2 alongside `MODULE_LICENSE`.
- `GPF_KERNEL`/`GFP_ATOMIC` — `kmalloc` is mentioned in the MCU/Linux table without GFP flags. A footnote pointing to Ch 37 would suffice.
- `.modinfo` section — `modinfo` is shown without explaining that the kernel reads ELF section data. Brief sentence: "All `MODULE_*` macros build entries in a special `.modinfo` ELF section; `modinfo` is just an ELF reader."

### Other
- Lab #5 says crashing the module on i.MX6ULL is "recoverable" — qualify: a NULL-deref in a kernel module *can* be recoverable on some configs but is **not guaranteed**. It's quite common for ARM32 to panic on a kernel-mode page fault unless `CONFIG_BUG_ON_DATA_CORRUPTION` and friends are set. Suggest: "Often recoverable on i.MX6ULL; sometimes panics. Have a serial console and a reset button ready."

## Ch37 — A character driver, by hand

### Readability
- §37.1 ASCII flow diagram is excellent; keep as-is.
- "It's the most readable way to handle error paths in C — far better than nested `if`s." — slightly preachy; tone down to "It's the kernel's idiomatic error-path style; once you read a dozen drivers it becomes the natural pattern."
- §37.6 table row "Multiple `cat`s in a row read the same 5 bytes each time" — confusing because there's also a "Two `cat /dev/hello > x &` in parallel" row. The first sentence in §37.5 says "Multiple `cat`s in a row read the same 5 bytes each time — because our `read` checks `*ppos >= buf_len` and signals EOF appropriately, then `cat` reopens and starts from `*ppos = 0` next time." This is reasoning about *sequential* `cat` invocations; reword to "Each new `cat` invocation gets a fresh open (so `*ppos` resets to 0); within one `cat`, the first `read` returns 5 bytes and the second returns 0 (EOF)."

### MCU-engineer friendliness
- §37.4 Idea 1 (`container_of`): badly missing the MCU bridge. The MCU dev has never used embedded-struct-with-recover-the-parent. Add a small diagram:
  ```
  struct hello_dev {
      struct cdev cdev;   ← inode->i_cdev points HERE
      ...
  };
                        ↑ container_of subtracts offsetof(cdev) to recover &hello_dev
  ```
  Two lines of explanation: "MCU equivalent: imagine you have `&task->state_field` and need `&task` — `container_of` does that with just compile-time offsetof math."
- §37.4 Idea 2: critical MCU bridge missing on `__user`. The MCU has no MMU and no separate address space. Add a paragraph: "In MCU/RTOS, your firmware sees one flat address space — `memcpy(user_buf, kernel_buf, n)` just works. In Linux, user-space and kernel-space live in *different* page tables. Even though the kernel can technically reach into user memory, *some pages may not be mapped right now* (paged out, lazy-allocation, COW), and the kernel must check permissions. `copy_to_user` does the lookup, brings pages in if needed, and uses the user-side mapping. A raw `memcpy` may oops the kernel."
- §37.4 Idea 3 (locking) mentions `mutex_lock_interruptible` but the MCU dev doesn't know what "interruptible" even means in this context. Add 2 sentences linking to FreeRTOS: "Think of `taskENTER_CRITICAL` (FreeRTOS) — but instead of disabling IRQs, a mutex puts the *waiting* task to sleep. `_interruptible` means: if Ctrl-C fires while sleeping, the wait function returns an error so the syscall can be cleanly aborted. RTOS analogue: an `xSemaphoreTake` with `INCLUDE_xTaskAbortDelay`."
- §37.4 Idea 4 (goto cascade): the MCU dev was taught `goto` is evil. Add one defensive sentence: "Yes, this is `goto`. The kernel coding style explicitly endorses this pattern; it's the only way to keep cleanup ordered correctly without RAII or exceptions. Read it as 'jump to the cleanup that's appropriate at this allocation depth.'"

### Missing examples / figures
- After §37.3, add a 6-line minimal `hello_fops` struct with each callback **labelled** in a comment with what it represents (`.open = ... // called once per fd creation`, etc.). The full driver is shown next, but the reader benefits from seeing the bare `file_operations` first.
- Diagram in §37.4: kernel→driver call stack for one `write()` syscall, with each frame's context and what's safe to do at each level.
- After §37.5 demo, a `ls -l /sys/class/...` or `cat /proc/devices` shot. Currently §37.5 jumps to §37.6 testing without showing the driver's footprint in sysfs/procfs.

### Technical errors
- §37.2 "12 bits major, 20 bits minor" — correct.
- §37.4 `cdev_init(&mycdev, &my_fops)` then `mycdev.owner = THIS_MODULE`. Setting `cdev.owner` *after* `cdev_init` is fine, but the more common idiom is to set it via `cdev_init` itself which already pulls `owner` from `&my_fops.owner`. Mention that since `hello_fops.owner = THIS_MODULE` is already set, the explicit `mycdev.owner = THIS_MODULE` line is redundant. (Not wrong, just noise.)
- §37.7 paragraph "The device file disappears if /dev/ is tmpfs (almost always true; remember Ch 32)." — This is misleading. The issue with `mknod` isn't that tmpfs makes it disappear *automatically*; it's that `/dev` is tmpfs which means **rebooting** wipes the manually-mknod'd node. Reword: "On a tmpfs `/dev`, the node disappears on reboot — you'd need to `mknod` again every boot. Hot-plug agents (udev/mdev) fix this in Ch 38."
- §37.9 "Kernel stacks are 16 KB on i.MX6ULL (sometimes 8 KB)" — see Ch 36 note; ARM32 default is **8 KB**, not 16 KB. Reverse the parenthetical: "8 KB on ARM32 i.MX6ULL (16 KB on x86_64/arm64)."

### Knowledge prerequisites missing
- `IS_ERR` / `PTR_ERR` are not yet introduced in Ch 37 (they appear in Ch 38). Ch 37 uses them implicitly via Knowing-where-to-go but is OK — fine, *but* Ch 38 should introduce them with a sentence: "Linux kernel functions that return `void *` (where `NULL` is a valid 'no such thing' result) signal errors by *casting* a negative errno into the pointer. `IS_ERR(p)` checks the high bits; `PTR_ERR(p)` extracts the errno. Compare to MCU code returning `(void *)-1` or `(void *)NULL` — Linux uses the high address range of pointers as a side-channel."

### Other
- Pitfall on `THIS_MODULE` in `cdev.owner` is excellent — keep.
- §37.10 references LDD3 Chapter 3 — note that LDD3 covers kernel 2.6 era; many APIs in LDD3 are now deprecated (`class_simple_*`, `register_chrdev` legacy). One sentence warning: "Read for the *concepts*; cross-check API names against current kernel before copying code."

## Ch38 — Auto-creating /dev nodes

### Readability
- §38.1 pipeline ASCII is excellent.
- §38.2 "Take the driver from Chapter 37 and add three lines." — actually adds quite a bit more (struct fields, init lines, exit lines, cleanup labels). Reword: "Take the Ch 37 driver and add a class, a device, and matching cleanup labels — about a dozen lines."
- §38.3 final paragraph "(`echo add > uevent` re-triggers — useful for replaying events on a system that booted before udev was running.)" — keep but move out of parens; this is genuinely useful info that the reader will want to find again.

### MCU-engineer friendliness
- §38.1 critical bridge: the MCU dev has no concept of a hot-plug event. Add: "MCU equivalent: there isn't one. The closest analogy is a USB-host stack on a microcontroller that emits 'device attached' callbacks — except in Linux, *every* device, whether hot-pluggable or not, goes through the same notification system. This means a tool sitting in user-space gets the same event whether you `insmod` a driver, plug in a USB stick, or boot the system."
- §38.3 "subsystem framework instead" — Ch 38 hints that "LED → leds; RTC → rtc" without saying which chapter covers them; add forward references explicitly.

### Missing examples / figures
- Before/after sysfs comparison: `find /sys/class/hello -type f` after probe shows the new attributes; this concretises the "shadow of sysfs" claim.
- After §38.2 cleanup code, show the full updated init function with the cleanup labels so the reader sees the goto-cascade extension end-to-end. Currently only the new lines are shown without the cascade context.
- Diagram for §38.5 multi-device: show a tree
  ```
  hello (class)
    ├── hello0  (minor 0, cdev #0)
    ├── hello1  (minor 1, cdev #1)
    ├── hello2  (minor 2, cdev #2)
    └── hello3  (minor 3, cdev #3)
  ```
  …and which struct member holds what.

### Technical errors
- **`class_create` signature: critical.** Throughout the chapter you use `class_create(THIS_MODULE, "hello")`. As of kernel **6.4** the `owner` argument is gone — it's now `class_create("hello")`. Either pick a target kernel version explicitly and stick to that signature, or write a note: "Kernel 6.4+ removed the `THIS_MODULE` argument. The macro magic in modern kernels means `class_create(THIS_MODULE, name)` no longer compiles in some configurations — use `class_create(name)` if you see `error: too many arguments to function 'class_create'`."
- §38.6 `device_create_file` is mentioned alongside `sysfs_create_group` but `device_create_file` is technically deprecated in favor of `default_attrs` / `groups` in `device_attribute_group` set on the class at registration time. Modern style: set `class->dev_groups` before `class_create`, and the core auto-creates attributes. Mention the deprecation, even if you keep `device_create_file` as the introductory pattern.
- §38.6 `sprintf(buf, "loaded\n")` — should be `sysfs_emit(buf, "loaded\n")` in modern kernels (since 5.10). `sysfs_emit` is bounds-checked; `sprintf` is not. Update or note the modern replacement.
- §38.8 Pitfall "Calling `device_create` before `cdev_add`. Device node appears but `open` on it returns `-ENXIO`" — the actual symptom on most kernels is that the open *races* with cdev_add: usually `-ENXIO`, sometimes `-ENODEV`. Mention both.

### Knowledge prerequisites missing
- `IS_ERR`/`PTR_ERR` — see Ch 37 note. Introduce here with at least one sentence before they appear in the code block.
- `kobj` — appears in `&dev->kobj` for `sysfs_create_group` (line 334 area). Briefly: "Every `struct device` embeds a `struct kobject` — the sysfs object model's atom. `&dev->kobj` is how you say 'the sysfs directory belonging to this device.'"
- `DEVICE_ATTR_RW` is used without explaining the wrapper around `dev_attr_state` it produces. The naming convention (the `dev_attr_*` global) trips first-time readers.

### Other
- §38.4 udev rule example uses `KERNEL=="hello"` — correct, but readers who copy-paste with a custom name will often wonder why nothing happens. Add: "After editing rules, run `udevadm control --reload && udevadm trigger`. If still nothing, `udevadm monitor` shows the events the rule is seeing."
- §38.8 Pitfall on race between insmod and udev — good, but mention that the cleanest fix is `udevadm settle --timeout=5` in a script, OR (for embedded) just put your test in a service file with `After=systemd-udev-settle.service`.

## Ch39 — Platform drivers + device tree

### Readability
- §39.3 "Let's pull apart the four interesting pieces." — Pieces A, B, C, D structure is great.
- §39.5 "Useful in development … Also useful in production for power-saving" — overlong sentence; split.
- §39.7 "A driver's `probe()` may depend on something that isn't ready yet — e.g., the PMIC regulator the driver wants hasn't probed itself." — the MCU dev has no concept of "PMIC" + "regulator" + "probed itself." Either swap to a more relatable example ("the clock source isn't registered yet") or define PMIC in passing.

### MCU-engineer friendliness
- §39.1 "the kernel doesn't probe address ranges blindly looking for hardware (that's how PC BIOSes work, and it doesn't scale to SoCs with no buses to enumerate)" — good bridge from PC world. Add the MCU bridge: "On an MCU, your firmware *knows* its own peripherals because you wrote `#include <stm32f4xx.h>` with the base addresses hardcoded. Linux uses DT for the same job, but at runtime, so one kernel image can run on many boards."
- §39.3 "the kernel walks the DT, finds matching nodes, and invokes the driver's `probe()` once per match" — explain the MCU equivalent: "Think of it as: `module_init` gives you 'kernel just loaded this code,' but `probe` gives you 'kernel just found a *device* this code knows about.' In RTOS terms, `module_init` is `void main()`; `probe` is `int driver_init(struct hardware *)`."
- §39.3 Piece C `devm_*` — strong content; add an MCU bridge: "In bare-metal you'd manually pair every `malloc` with a `free`. `devm_kzalloc` is closer to a C++ RAII pattern or scope-bound allocation: the kernel auto-frees when the device goes away. This is the single biggest 'feels like modern code, not C' moment in the kernel."

### Missing examples / figures
- A driver-vs-device-vs-bus diagram between §39.1 and §39.2 would help. Showing:
  ```
  platform_driver "demo"
       ↑    .of_match_table = [{ "linuxlearn,demo" }]
       │
       │  matched by platform_bus
       │
       ↓
  platform_device "demo@1000"
       └── dev.of_node → DT node @ /demo@1000
                          compatible = "linuxlearn,demo"
                          reg = <0x1000 0x100>
  ```
- §39.6 lists six DT-reading APIs without showing how they connect to the DT node's structure. A 3-line example DT alongside the C code would tie it together.
- After §39.4 "Verify in sysfs" output, add a tree showing the platform-bus hierarchy in `/sys`:
  ```
  /sys/bus/platform/
    drivers/demo/      ← the platform_driver
    devices/demo@1000/ ← the platform_device
  ```
  with arrows pointing both directions.

### Technical errors
- §39.3 `platform_get_resource(pdev, IORESOURCE_MEM, 0)` followed by `devm_ioremap_resource(&pdev->dev, res)` — modern kernels prefer **`devm_platform_ioremap_resource(pdev, 0)`** which combines both into one call. Mention it in Going Deeper or as a "modern shortcut" sidebar.
- §39.3 `pdev->dev.of_node->name` — `of_node->name` was deprecated in 4.16 era and removed/changed in some configs. Use `of_node_full_name(pdev->dev.of_node)` or just `dev_name(&pdev->dev)`. The probe log will look slightly different but be more robust.
- §39.3 `static int demo_remove(struct platform_device *pdev)` returning `int` — on kernels 6.11+, platform driver `.remove` returns `void` (and a transitional `.remove_new` was added in 6.5). Add a note.
- §39.7 `if (PTR_ERR(priv->vcc) == -EPROBE_DEFER) return -EPROBE_DEFER;` followed by `dev_err_probe`. This block is logically backwards: `dev_err_probe` *already* handles `-EPROBE_DEFER` silently, so the manual check is redundant. The block should just be:
  ```c
  if (IS_ERR(priv->vcc))
      return dev_err_probe(&pdev->dev, PTR_ERR(priv->vcc), "no vcc regulator\n");
  ```
  The text correctly says so in the next paragraph but the code block contradicts itself. Drop the manual check.
- §39.9 "Driver and device names with hyphens vs underscores" — the kernel itself doesn't care; some *tools* (`modalias`, `depmod`) do, and the *convention* is hyphens in `compatible` and either in `.name`. Slightly stronger phrasing would help: "Stick to lowercase letters, digits, and hyphens for both `.name` and `compatible`. Underscores are tolerated but not idiomatic."

### Knowledge prerequisites missing
- `regulator`/`clock`/`reset` references in §39.6 — first time these appear without forward references. Add: "We'll meet the clock framework in Ch 50A (clocks) and the regulator framework in Ch 51B (power management); for now treat them as 'subsystem APIs that hand you a handle and let you turn things on/off.'"
- The `phandle` concept — mentioned via `<&clks IMX6UL_CLK_GPIO1>` in §39.1 but not explained. Cross-link to whichever DT chapter (presumably Ch 27) introduces phandles.

### Other
- §39.5 manual bind/unbind: excellent feature to demonstrate. Add one line: "The `unbind/bind` files require that the driver and device names be exact; an extra newline from `echo` is what `bind` expects (it strips it)."
- §39.7 shutdown vs remove: clarify that `shutdown()` runs in **process context** but should be *fast*, not "atomic context." Atomic-context shutdown handlers would be exceptional. Reword: "It can sleep, but the whole system is waiting for it — keep it under tens of milliseconds."

## Ch40 — The misc framework

### Readability
- Tight, clean chapter. Minor: "Six lines to register, one to deregister." — quantify the comparison more clearly. The Ch 37 version was ~30 lines in `init` excluding cleanup; the misc version is ~6 lines total. Saying "About 30 lines collapsed to 6" is more vivid.
- §40.5 comparison table — good summary; consider adding a row for "what /sys/class entry appears" to make the trade-off concrete.

### MCU-engineer friendliness
- §40.1 "Use misc when..." — give one MCU-friendly framing first: "Misc is the 'I just need a /dev/ node, don't make me think about classes' shortcut. In bare-metal you'd write a single read/write function. Misc lets your Linux code be almost that small."

### Missing examples / figures
- Add `ls -l /dev/hello` and `ls -l /sys/class/misc/hello` side-by-side to show what the user sees, mirroring Ch 38's approach.
- A diagram comparing the lifecycle of a manual chardev (alloc region → cdev_init → cdev_add → class_create → device_create) vs misc (misc_register) would let the reader see the collapse visually.

### Technical errors
- §40.3 example struct is fine; one small note: setting `.mode = 0660` directly in the struct works, but the kernel framework's preferred path is **a class-level `devnode` callback** (mentioned briefly in Ch 38). Either method works for misc; just mention that the misc layer handles the mode field for you.
- §40.4 lists `loop-control`, `watchdog`, `hwrng`, `rfkill` as misc — all correct. Mention that `/dev/loop-control` minor is 237, `/dev/watchdog` is 130 (reserved minors in `include/linux/miscdevice.h`) — readers reading that header will find a table.

### Other
- §40.6 Lab #3 "Combine misc + platform driver" — this is the canonical embedded chardev pattern and deserves more space. Consider expanding into a small worked example showing the misc-inside-probe pattern fully, not just as a lab exercise.

## Ch41 — Concurrency in the kernel

### Readability
- §41.1 opener is excellent — directly contrasts MCU loop with Linux SMP.
- §41.2 three-question framework is fantastic and is the right pedagogy.
- §41.4 "While you hold a spinlock, the holding CPU has IRQs disabled (in the IRQ-safe variant)" — the bracketed qualifier matters but reads as an afterthought. Restructure: "A bare `spin_lock`/`spin_unlock` only disables preemption. The `_irq` variants additionally disable IRQs on the holding CPU. The reason for the variants is...".
- §41.9 "Lockdep — your friend" is short and breezy — keep, but add a one-line example of what a lockdep splat looks like (just the first 5-6 lines) so readers know what to expect.

### MCU-engineer friendliness
- §41.1 — best MCU bridge in the chapter. Other sections should match this energy. Specifically:
  - §41.4 spinlocks vs MCU `taskENTER_CRITICAL`: explicit mention. "FreeRTOS's `taskENTER_CRITICAL` disables interrupts and preemption on a single-core system. A Linux spinlock is similar, but on SMP must additionally lock out other CPUs. `spin_lock_irqsave` is the closest analogue — it disables IRQs (single-core protection) *and* acquires the bus lock (multi-core protection)."
  - §41.5 mutexes vs RTOS semaphores: "FreeRTOS `xSemaphoreTake(mutex, portMAX_DELAY)` ≈ Linux `mutex_lock`. The RTOS version blocks the calling task and lets the scheduler pick another; Linux mutexes do the same."
  - §41.10 worked example: an MCU dev with a SPSC ring buffer might think "I just need atomic head/tail pointers." Add a sentence: "On a single-core MCU, you can sometimes avoid locks entirely by carefully ordering head/tail updates. Linux on SMP makes that hard — the cost of a single `LDREX/STREX` round-trip across CPU caches dominates. Spinlocks are simpler and almost always fast enough."

### Missing examples / figures
- §41.4 Variants table is comprehensive but lacks a "what gets disabled" column. Suggested:
  | Variant | Preempt off | IRQs off | When |
  |---------|-------------|----------|------|
  | `spin_lock` | yes | no | process only |
  | `spin_lock_bh` | yes | softirqs only | process + softirq |
  | `spin_lock_irq` | yes | yes | known IRQs-on context |
  | `spin_lock_irqsave` | yes | yes (save state) | any context |
- §41.7 RCU example: a diagram showing "writer publishes new pointer; readers in flight still see old; synchronize_rcu waits; old freed" would clarify the magic. Currently it's a wall of code.
- §41.10 ring buffer: a tiny state diagram showing head/tail movement with one producer + consumer would help. The MCU dev knows this from their FreeRTOS queue code; show the parallel.

### Technical errors
- §41.4 "On a single-core CPU (the i.MX6ULL), the per-CPU array has one slot..." (in §41.8) — actually i.MX6ULL is single-core but the *kernel* may still be built `CONFIG_SMP=y` (and usually is, on Linux distros). Per-CPU still uses one slot. The text says this; the lab note in 41.11 #4 says "the test is harder to write on a single-core i.MX6ULL." Slightly contradictory tone — clarify that the *semantics* are the same, only the *demonstrable speedup* is invisible on single-core.
- §41.5 "Mutexes have one nice property over semaphores: the kernel tracks who holds them." — correct, but worth adding: "This is why kernel mutexes are owner-aware and disallow being released by a thread other than the holder; counting semaphores (`struct semaphore`) don't have this." The reader who has used FreeRTOS counting semaphores would otherwise be confused.
- §41.7 `rcu_dereference_protected(cur_config, lockdep_is_held(&write_lock))` — `write_lock` is referenced but never defined in the example. Add `static DEFINE_MUTEX(write_lock);` so the snippet compiles in spirit.
- §41.12 "Linux mutexes are **not recursive**" — correct. Worth strengthening: "Even checking is forbidden — `mutex_is_locked()` returns whether *anyone* holds it, not whether the current task does. To attempt a recursive-like pattern, manage a counter alongside the mutex."

### Knowledge prerequisites missing
- "Softirq" introduced before being defined. §41.2 talks about "Process + softirq/tasklet → spinlock with `_bh` variant." Tasklet is hinted at but never defined until Ch 43. Add a one-paragraph definition: "A softirq is a kernel-internal mechanism for 'do this work later, but soon, at an interrupt-like time.' Tasklets are softirqs scheduled per-instance. Work queues are softirqs scheduled to kernel threads. You'll meet them properly in Ch 43; for now: 'softirq context = not process context, but not hard-IRQ context either.'"
- `ldrex/strex` — mentioned without explanation. The MCU reader who knows ARMv7 will recognize them, but a one-liner — "ARM's load-exclusive/store-exclusive pair, the foundation of all atomic operations on ARM" — is useful.

### Other
- §41.12 Pitfall on `volatile` is excellent and worth keeping — many MCU devs have `volatile` everywhere.
- §41.8 per-CPU section ends with "Per-CPU data is brilliant when reads are rare relative to writes (the opposite of RCU's sweet spot)." — actually per-CPU data is for cases where **writes are local and reads are rare-but-aggregating**, regardless of frequency. The contrast to RCU is reads-vs-writes. Tighten the framing.

## Ch42 — Sleeping, waiting, polling

### Readability
- Strong chapter overall.
- §42.1 "Both eventually rest on the same kernel primitive: a **wait queue**." — concise; keep.
- §42.5 list of sleep/delay functions: this is a critical reference and should be elevated to a "Cheat sheet" callout box. Currently buried inside a flowing paragraph.
- §42.6 task state machine: useful but could be moved earlier (before §42.2's "the macro sets state to `TASK_INTERRUPTIBLE`" comment, which is otherwise opaque).

### MCU-engineer friendliness
- §42.1 — *missing* the MCU bridge entirely. The MCU dev knows `vTaskDelay`, `xQueueReceive`, `xSemaphoreTake` (block until). Add: "In FreeRTOS, a task blocks via `xQueueReceive(queue, &item, portMAX_DELAY)` — the scheduler removes it from the ready list until something puts an item in. Linux wait queues are exactly this, generalized: the 'queue' is just a list of sleeping tasks, the 'condition' is whatever predicate you write, the 'unblock' is the producer calling `wake_up`."
- §42.2 wait_event_interruptible variants — the MCU dev needs to map this to RTOS task states. Add a column to the variant table: "RTOS analogue" with rows like "vTaskDelay-with-abort," "xQueueReceive-with-timeout," etc.
- §42.5 `udelay` / `mdelay`: critical bridge. "These are the Linux equivalents of HAL_Delay(ms) — busy-wait. `msleep` is the equivalent of vTaskDelay — yields to the scheduler. The difference is the same as in MCU code: busy-wait keeps the CPU; sleep lets other tasks run."

### Missing examples / figures
- §42.4 poll/select flow diagram is great. Add a similar diagram for blocking read in §42.3:
  ```
  user: read(fd, buf, n)
        │
  driver: wait_event_interruptible(wq, data_len > 0)
        │      ↳ schedule()  ← task is asleep here
        │
  IRQ/producer: writes data, wake_up_interruptible(&wq)
        │
  driver: wakes, checks condition, returns data
  ```
- §42.6 task state diagram as an actual state diagram, not just a list. Arrows: `TASK_RUNNING ↔ TASK_INTERRUPTIBLE ↔ TASK_UNINTERRUPTIBLE` with labels for the syscalls that cause transitions.

### Technical errors
- §42.3 `wait_event_interruptible(read_wq, data_len > 0)` — `data_len` is read **without holding the lock**. This is a classic subtle bug: `data_len` is set inside `data_lock`, so the check needs a memory barrier or the lock. In practice, on i.MX6ULL ARMv7 with a single core and the wake_up sequence, this happens to work — but the pattern shown is unsafe on SMP. Either:
  - Add a `READ_ONCE(data_len) > 0` (and `WRITE_ONCE` in the producer), OR
  - Move the lock inside the wait expression: `wait_event_interruptible(read_wq, ({ mutex_lock(&data_lock); int r = data_len > 0; if (!r) mutex_unlock(&data_lock); r; }))` (ugly), OR
  - Mention this as a teaching note: "this works for our single-core case but production code uses `READ_ONCE` here to prevent compiler reordering."
- §42.3 `O_NONBLOCK` check happens *before* acquiring the lock — fine, but the `data_len == 0` check has the same memory-ordering question. Mention it.
- §42.4 `__poll_t` is correct. `EPOLLIN | EPOLLRDNORM` is also correct. Worth mentioning: traditional `POLLIN | POLLRDNORM` is also accepted but `EPOLLIN` is preferred in modern kernels (since 4.16) because it forces the typed `__poll_t` cast.
- §42.5 `usleep_range(50, 100)` — minimum is 1 µs, but the kernel coalesces short sleeps. Worth noting: on a busy system, even `usleep_range(50, 100)` may return after 5-10 ms. For sub-millisecond timing, you must `udelay`.
- §42.8 Pitfall on memory-barrier: correctly states "wake_up implies a full barrier." This is true *for the writer*, but the reader who checked the condition before sleeping needs a separate guarantee that `wait_event_interruptible` provides. The `Documentation/memory-barriers.txt` reference is good; consider adding "in practice, `wait_event_*` and `wake_up_*` form a complete pair and you don't need explicit barriers between them. Add barriers only if you're checking flags *outside* the wait_event mechanism."

### Knowledge prerequisites missing
- "jiffies" — used in `wait_event_interruptible_timeout` and `schedule_timeout(jiffies)` (§42.5) without introduction. Sentence: "A jiffy is the kernel's coarse time unit, equal to 1/HZ seconds. On i.MX6ULL with default `CONFIG_HZ=250`, one jiffy is 4 ms. Convert: `msecs_to_jiffies(50)` for 50 ms, etc."
- `kthread_run` (§42.3 example uses a `producer_fn` started by kthread) — never shown. Either include the `kthread_run` line or forward-reference.

### Other
- §42.7 Lab #4 — explicitly note that the test relies on `cat` translating `-ERESTARTSYS` correctly. On some systems, `cat` retries silently and the Ctrl-C is "absorbed." Suggest using a custom test program that returns immediately on read failure.

## Ch43 — Interrupts

### Readability
- §43.1 chain diagram is excellent.
- §43.2 "Five lines of real work. Read status, ack, snapshot, defer, return. Under 1 µs on i.MX6ULL." — punchy, keep.
- §43.4 four-bottom-half choices — clear taxonomy, keep the table.
- §43.5 GPIO interrupts section — well-paced.
- §43.7 `/proc/interrupts` example is good but the table format renders awkwardly with long lines. Pre-format or use a code block fence with horizontal scroll.

### MCU-engineer friendliness
- §43.1 — this is the most critical MCU-bridge spot in the chapter and it's missing. Add: "On an MCU, an IRQ fires → NVIC vectors directly to your ISR. Period. On Linux, the chain has *six* levels because Linux runs on hundreds of SoCs each with different IRQ controllers and the kernel has to abstract them. The kernel's `virq` (virtual IRQ number) is the platform-independent ID; it's what your driver works with. Everything else (GIC, mapping, demux) is plumbing the kernel handles."
- §43.2 contract bullets — strong; add MCU bridge: "MCU equivalent: imagine your ISR could be preempted by a task switch, must hand off work to a deferred task, and shares the CPU with several other things. The 'top half' is the ISR; the 'bottom half' is the deferred task. FreeRTOS's `xTaskNotifyFromISR` followed by a task that processes the notification is the same pattern."
- §43.4 threaded IRQ — best MCU framing would be: "FreeRTOS pattern: ISR signals semaphore → high-priority task takes semaphore → processes. Linux threaded IRQ: kernel runs your primary handler in interrupt context → returns IRQ_WAKE_THREAD → kernel wakes a kthread that runs your threaded handler. Same architecture, different names."
- §43.5 GPIO IRQs — give the explicit MCU comparison: "On STM32 with EXTI, `EXTI0_IRQHandler` fires for any pin-0 across ports. On i.MX6ULL, GPIO IRQ banks work the same — one IRQ line per bank of 32 pins, demuxed by the GPIO driver. The kernel's `gpio_to_irq` (now `gpiod_to_irq`) gives you a per-pin virq so your driver doesn't need to demux."

### Missing examples / figures
- §43.1 chain ASCII is good; add a parallel diagram showing the *MCU* IRQ chain side-by-side to emphasize the abstraction layers Linux adds.
- §43.4 four-option comparison: a flowchart "do you need to sleep?" → "do you need atomic context?" → ... → which bottom half to pick.
- §43.5 GPIO IRQ — show the `/proc/interrupts` line after registration, so readers know how to verify their IRQ actually got connected.
- After §43.6, a Venn diagram of "your handler always called" vs "shared handlers all called" would help.

### Technical errors
- §43.2 "It runs with that IRQ disabled. The GIC won't re-fire the same IRQ on the same CPU until you return. (Other CPUs *can* see it; that's how SMP works.)" — slight nuance: with `IRQF_ONESHOT`, the IRQ is also masked on other CPUs until the threaded handler completes. Without `IRQF_ONESHOT`, the IRQ is re-enabled on the GIC after the top half returns and **can** fire on another CPU. Worth being precise.
- §43.3 `IRQF_TRIGGER_*` flags — "usually omitted for platform drivers because the DT specifies it" is correct. Add: "If you specify both, the kernel uses the DT one and ignores yours. If they conflict, the kernel logs a warning."
- §43.4 `DECLARE_TASKLET_OLD` — your example uses `DECLARE_TASKLET_OLD`, but `DECLARE_TASKLET_OLD` itself was deprecated in 5.9 in favor of `DECLARE_TASKLET` (the new-style with `tasklet_struct *` callback). The "OLD" macro is the *backwards-compat* macro; the modern one is `DECLARE_TASKLET(name, callback)` where `callback(struct tasklet_struct *t)`. Update or note the rename.
- §43.5 `gpiod_to_irq(b->button)` returns int that may be -ve on failure. The pattern `if (virq < 0) return virq;` is correct.
- §43.5 `IRQF_TRIGGER_FALLING | IRQF_ONESHOT` in the request — combining with the DT's `IRQ_TYPE_EDGE_FALLING` is redundant but harmless. Mention.
- §43.7 `/proc/interrupts` row shows `46:    0  gpio-mxc  14 Falling   button` — `gpio-mxc` is correct for the i.MX6ULL GPIO driver name. The IRQ line numbers (46) are example values; vary by kernel.
- §43.9 Pitfall "Symptom: must `modprobe demo` by hand at every boot" appears in Ch 39's pitfalls verbatim — copy-paste from Ch 39? Tighten to be IRQ-specific. (Actually it's in Ch 39; Ch 43's pitfalls don't mention this — false alarm; ignore.)

### Knowledge prerequisites missing
- `irqreturn_t` — appears as a type without introduction. One sentence: "An enum: `IRQ_NONE` (this wasn't mine), `IRQ_HANDLED` (took it), `IRQ_WAKE_THREAD` (top half done; run threaded handler now)."
- `writel`/`readl` — first use in §43.2 without introduction. Sentence: "Linux's portable MMIO accessors. `writel(val, addr)` writes 32 bits with memory-barrier semantics appropriate to the architecture. On ARM, includes a DMB. The reversed argument order vs `*addr = val` is a common stumble — value first, address second."
- `container_of` reappears in §43.4 work queue example. Cross-link back to Ch 37.

### Other
- §43.4 "Tasklets are **discouraged** in new code." — well-stated. Mention that they're being actively removed; some subsystems (notably block-I/O) have already converted. Forward-link to PREEMPT_RT chapter that explains the why.
- Lab #4 force IRQ storm — good, but warn that on production hardware with a watchdog, this might actually reboot. Add a sentence: "Disable any kernel watchdog before this experiment, or set it to a long timeout."

## Ch44 — GPIO subsystem + pinctrl

### Readability
- §44.1 multiplexing table is clear; keep.
- §44.2 the iomux macro deconstruction is just right.
- §44.4 descriptor API: very readable.
- §44.5 worked example is long but well-paced.
- §44.6 libgpiod output is great.
- §44.7 expander section — short and punchy.

### MCU-engineer friendliness
- §44.1 — MCU bridge missing. Add: "On STM32, you set `GPIOA->MODER` to mux a pin, then `GPIOA->ODR` to drive it. Linux splits these into two subsystems because on a complex SoC the pinmux is a *separate hardware block* (IOMUXC on i.MX6ULL) with its own clock and register space, distinct from the GPIO controllers. They're two register banks; Linux gives them two APIs."
- §44.2 the macro `MX6UL_PAD_UART1_RTS_B__GPIO1_IO19` — strong explanation. Add the MCU bridge: "If you've worked with NXP MCUXpresso, this is the same idea as the IOMUXC mux register tool — each macro encodes (mux_reg, conf_reg, input_reg, mux_mode, input_val) as a single 32-bit constant the kernel can write directly."
- §44.4 `gpiod_set_value_cansleep` vs `gpiod_set_value` — MCU bridge: "On an MCU, GPIO writes are register writes — never sleep. On Linux, a GPIO might live behind I²C (the expander); a write triggers an I²C transaction. `_cansleep` flags that 'this might block.' Use it in process context; reserve the non-`_cansleep` version for IRQ handlers and spinlock-held code where blocking is forbidden."

### Missing examples / figures
- A diagram in §44.1 showing the layered relationship:
  ```
   driver → gpiod API → gpio_chip (e.g., gpio-mxc) → IOMUXC + GPIO MMIO
                          ↓
                       (or)  → mcp23017 → I²C transaction → external chip
  ```
- §44.3 DT example — annotate the three cells more concretely with arrows pointing to "GPIO1_IO19 pin on bank 1" so the cell numbering clicks.
- After §44.5 example, show the `/proc/interrupts` line and `gpioinfo gpiochip0` output to prove the driver claimed the pin.

### Technical errors
- §44.2 `MX6UL_PAD_NAND_CE1_B__GPIO4_IO14` in the LED pinctrl entry — cross-check: NAND_CE1_B muxed to GPIO4_IO14 is correct for i.MX6ULL. The conf value `0x10b0` (drive strength 40Ω, slow slew) is reasonable for an LED.
- §44.3 "i.MX6ULL has 5 banks (`gpio1`–`gpio5`), each up to 32 pins" — correct, but **GPIO5 has only 12 pins** (per the i.MX6ULL reference manual; the rest are NC). GPIO4 also has fewer than 32 in some packages. Worth noting: "GPIO5 in particular is only partial — pins 0–11 are available."
- §44.4 `devm_gpiod_get(&pdev->dev, "reset", GPIOD_OUT_HIGH)` — "asserted" semantics — the wording "set as an output, and initialise it to **asserted** (`GPIOD_OUT_HIGH`) or **deasserted** (`GPIOD_OUT_LOW`)" is **incorrect in spirit**. `GPIOD_OUT_HIGH` and `GPIOD_OUT_LOW` set the **logical** initial value, but the names are misleading — they correspond to logical "high" (asserted, considering ACTIVE_LOW polarity) and logical "low" (deasserted). The kernel docs actually say `GPIOD_OUT_HIGH` = asserted, `GPIOD_OUT_LOW` = deasserted *after polarity is applied*. Reword: "`GPIOD_OUT_HIGH` initialises to logical-high (i.e., asserted given the DT polarity flag); `GPIOD_OUT_LOW` to logical-low (deasserted)."
- §44.6 sysfs deprecation: correct that `/sys/class/gpio/` is deprecated. Mention the kernel config: `CONFIG_GPIO_SYSFS=n` in modern kernel configs disables it; on Debian/Ubuntu it's usually still compiled in.
- §44.6 `gpioget gpiochip0 19` returns `1 ← button not pressed` — but the example DT has `GPIO_ACTIVE_LOW`, and `gpioget` returns the **raw line value** unless `--active-low` is passed. Specify: "gpioget shows raw level by default; `gpioget --active-low gpiochip0 19` shows logical."
- §44.9 Pitfall on "GPIO1 IO19 = global GPIO number 19" — correct that global numbers are legacy. On i.MX6ULL, the legacy global mapping was bank*32 + pin: GPIO1_19 = 19, GPIO2_5 = 37, etc. Worth mentioning the formula for readers debugging old DTs or sysfs.

### Knowledge prerequisites missing
- `GPIOD_*` flags — table appears mid-section; promote to a dedicated callout or table. Modern docs use additional flags (`GPIOD_FLAGS_BIT_OPEN_DRAIN`, etc.) — at least mention they exist.
- `pinctrl_select_state` is mentioned in §44.2 multiple-states but not introduced. One sentence: "When a driver wants to switch between declared states (e.g., active → sleep), it calls `pinctrl_select_state(pctrl, state)`. The most common use is the runtime PM hooks in §44.9 / Ch 51B."
- "phandle" again — see cross-cutting note.

### Other
- §44.5 — driver is solid; suggest adding the `#include <linux/of.h>` (referenced implicitly via `of_match_table` but the header isn't shown for the include block). Header completeness matters for the MCU dev who is going to literally copy-paste.
- §44.6 libgpiod — note libgpiod **v2** (releases 2023+) has a different C API than v1; CLI tools are mostly the same. Worth a forward note.

## Ch45 — Input subsystem

### Readability
- §45.1 pipeline diagram is clear.
- §45.2 event types table is great.
- §45.4 worked example structure is good.
- §45.5 — autorepeat/debounce/keymap section reads as three small topics; consider sub-headers for each.

### MCU-engineer friendliness
- §45.1 — MCU bridge missing. Add: "On an MCU, you'd parse a keyboard scan matrix in firmware and emit characters over UART or HID. On Linux, the kernel handles the scan-to-event translation in your driver; everything above (X11, Wayland, terminal) speaks one event protocol. You write the bottom of the stack; the rest is reused."
- §45.2 type/code/value triple — the MCU dev who's done HID will recognize this immediately. Add: "If you've ever written a USB HID descriptor, this is the same idea: 'usage page + usage + value' becomes 'type + code + value.' Linux's input layer is essentially a HID descriptor flattened."
- §45.4 IRQ handler design: critical bridge missing. The driver here uses `gpiod_get_value_cansleep` inside a *threaded* IRQ — that's fine because threaded IRQs can sleep, but the reader who internalized Ch 43 might wonder why it's safe to sleep in an IRQ handler. Add: "Because this is a *threaded* IRQ (via `devm_request_threaded_irq(...)` with `NULL` primary), the handler runs in kthread context — sleeping is fine. If we'd used `devm_request_irq` (non-threaded), `gpiod_get_value_cansleep` would BUG."

### Missing examples / figures
- After §45.4 evtest output, show `cat /proc/bus/input/handlers` so readers see how `evdev` registers itself as a handler.
- A diagram in §45.2 showing the input core's internal flow:
  ```
  input_report_key →  input_event() queues event → input_sync() flushes
                                                     ↓
                                              all evdev handlers
                                                     ↓
                                              wake_up readers of /dev/input/event*
  ```
- §45.5 debounce: the explanation says "implementing this is an exercise" — show the actual `delayed_work` + `cancel_delayed_work` pattern. Without code, the MCU dev reads "exercise" and skips.
- §45.6 multi-touch hint — actually show the bare protocol (one slot, one finger) so the reader doesn't have to flip to Ch 55G for the basic idea.

### Technical errors
- §45.3 `gpio-keys` example: `linux,code = <KEY_ENTER>;` — the kernel binding for `gpio-keys` uses `linux,code = <KEY_ENTER>` as the actual property name. Correct. Note that some older bindings used `code` (without prefix); modern is `linux,code`.
- §45.4 `bd->input->id.bustype = BUS_HOST;` — `BUS_HOST` is fine; some prefer `BUS_VIRTUAL` for software-generated devices. Either works.
- §45.4 IRQ request uses `IRQF_TRIGGER_RISING | IRQF_TRIGGER_FALLING | IRQF_ONESHOT` — to detect both press and release. With **edge-triggered** IRQ on both edges, the GPIO subsystem on i.MX6ULL handles this fine (it's "either edge" mode). Confirm.
- §45.4 in `button_irq`: reads gpio with `gpiod_get_value_cansleep` and reports the current value. This is a **polling-after-IRQ** pattern that handles both press and release with one handler. The classic alternative is to use the IRQ alone and toggle a software state; both work. Worth noting tradeoff: this approach handles bouncing poorly (a contact bounce while reading might give wrong polarity); the `gpio-keys` approach uses a debounce timer.
- §45.4 `input_set_capability(bd->input, EV_KEY, KEY_ENTER)` — correct, but the modern alternative is `set_bit(EV_KEY, input->evbit); set_bit(KEY_ENTER, input->keybit);` for setting multiple at once. Both work; mention.
- §45.7 `input_setup_polling` — correct, but the kernel symbol exists since 5.7. On older kernels it was `input_polled_dev`. State the cutoff.
- §45.10 Pitfalls — strong list. Add: "Don't allocate `input_dev` on the stack; always use `input_allocate_device` or `devm_input_allocate_device`."

### Knowledge prerequisites missing
- `kobj_to_dev` used in some code paths (sysfs callbacks) — for input chapter, not directly used, but in case forward-ref to Ch 46 §46.6.
- The `EV_REP` capability for autorepeat — mentioned in §45.5 but not shown how to enable. One sentence: "Set `input_set_capability(input, EV_REP, 0)` and configure repeat parameters via `input->rep[REP_DELAY] = 250; input->rep[REP_PERIOD] = 33;`."

### Other
- §45.6 absolute axes: `input_set_abs_params(input, ABS_X, 0, 4095, 0, 0);` — the parameters `fuzz` and `flat` need spelling out. "fuzz = noise threshold; events that differ by less than fuzz are not reported. flat = dead-zone for the value (joystick centers)."
- Lab #6 power-button: "With systemd, a long press should trigger a graceful shutdown" — this requires logind configuration. Mention `/etc/systemd/logind.conf` `HandlePowerKey=poweroff` or equivalent.

## Ch46 — I²C drivers

### Readability
- §46.1 split table is clear.
- §46.2 DT rules are well-stated.
- §46.3 skeleton is appropriate length.
- §46.4 SMBus API list is clean.
- §46.5 i2c_msg explanation could be more visual.
- §46.6 worked example is good.
- §46.7 i2c-tools section is great.

### MCU-engineer friendliness
- §46.1 — best MCU bridge in the chapter is missing. Add: "On an MCU, you write a function like `bme280_read(i2c_handle, reg, val)` that twiddles I²C peripheral registers directly. On Linux, the `i2c_adapter` is that 'i2c_handle' but abstracted across all I²C controllers in the kernel — same API for i.MX6ULL, STM32, x86, etc. Your driver only writes the chip-side code; the bus-side is reused."
- §46.3 `module_i2c_driver` — same idea as `module_platform_driver`; cross-reference Ch 39.
- §46.4 SMBus vs raw — MCU bridge: "On a bare-metal I²C library you usually have `i2c_read_register(addr, reg, buf, len)` as a single function. SMBus helpers are that. `i2c_transfer` is the raw form for chips that need unusual sequences (e.g., 16-bit register addresses)."

### Missing examples / figures
- §46.1 ASCII showing the three-player split is text-only; an actual diagram would help.
- §46.5 i2c_msg with repeated-start vs separate transactions — a wave diagram of SDA/SCL with START/repeated-START/STOP would clarify what "atomically" means in §46.5.
- After §46.6 worked example, an `i2cdump 1 0x50` showing the EEPROM contents would tie the example to the user-space view.
- A figure mapping `regmap` (Ch 50) layered over `i2c_transfer` layered over the i.MX I2C controller driver layered over the hardware. (The book has this concept but never illustrates the layering.)

### Technical errors
- **`i2c_driver.probe` signature is the major issue.** Modern kernels (6.3+) use `int probe(struct i2c_client *client)` — one argument. Your example uses the legacy two-argument form `int probe(struct i2c_client *, const struct i2c_device_id *)`. Either pick a target kernel and adjust, or note: "Since kernel 6.3, the second argument is gone. The `id_table` is still used by the I²C core to match, but the probe function no longer needs to look at it. For pre-6.3 kernels, the two-arg form below is correct."
- §46.3 `mychip_remove(struct i2c_client *client)` returning `int` — on kernel 6.11+, this returns `void`. Add a note.
- §46.3 includes `<linux/of.h>` — actually the modern way is `<linux/mod_devicetable.h>` for `of_device_id`. Both work.
- §46.4 `i2c_smbus_read_byte_data` returns `int` (negative on error, value as `s32`). The example correctly handles this.
- §46.6 example uses `dev_get_drvdata(kobj_to_dev(kobj))` — `kobj_to_dev` is the right helper, good. But `dev_get_drvdata` returns the `void *` set by `dev_set_drvdata`; the cast is implicit. Note the macro pattern.
- §46.6 EEPROM write `msleep(5)` — AT24C02's max page write time is 5 ms per datasheet, but ACK-polling (try a `i2c_smbus_write_quick(client, I2C_SMBUS_WRITE)` until it succeeds) is faster and more reliable. Mention it as an improvement.
- §46.9 Pitfall "Bus contention with multiple drivers" — the kernel actually allows multiple addresses if they don't conflict. The pitfall really should be "two DT children at the same `reg = <0x76>`" which would never happen if DT is correct.

### Knowledge prerequisites missing
- "i2c_adapter" — what number is `/dev/i2c-1` vs `/dev/i2c-0`? On i.MX6ULL, `i2c1` in DT → `/dev/i2c-0`? Or 1-indexed? It's 0-indexed by adapter registration order (which usually matches the DT order). Show `cat /sys/class/i2c-dev/i2c-1/device/of_node/full_name` to map.
- `mod_devicetable.h` — referenced indirectly; one mention is enough.
- The `0660` mode for sysfs and udev — already covered in Ch 38; cross-reference.

### Other
- §46.6 worked AT24 example — note that the real `at24` mainline driver uses nvmem framework now, not raw sysfs bin attributes. Reference: `drivers/misc/eeprom/at24.c` is on nvmem; readers might be confused if they cross-check. Add: "For a real driver, the modern path is to register as an nvmem provider; this example uses sysfs binary attributes only to keep the I²C wiring visible."
- Lab #6 strace — wonderful. `I2C_RDWR` ioctl is the right thing to see.

## Ch47 — SPI drivers

### Readability
- §47.1 SPI-vs-I²C table is excellent.
- §47.3 skeleton mirrors Ch 46 cleanly — readers will find it easy.
- §47.4 transfer/message explanation is clear.
- §47.6 spidev section is informative.
- §47.7 MCP3008 example is concise and concrete.

### MCU-engineer friendliness
- §47.1 — Add: "STM32 SPI peripheral or any MCU SPI: the controller pumps bits; you fill TXFIFO, drain RXFIFO. Linux abstracts FIFO management; you give it buffers, it returns when done. The SPI controller may be using DMA — you don't care."
- §47.4 full-duplex emphasis: "On an MCU, you choose between `HAL_SPI_TransmitReceive` (full duplex) and `HAL_SPI_Transmit` (half duplex). Linux's `spi_sync_transfer` with both `tx_buf` and `rx_buf` set is the equivalent of the former; passing NULL for one is the equivalent of the latter."
- §47.6 spidev: the MCU dev probably tried "I'll just write to a file" once. Add: "spidev is the 'I'll just write to a file' for SPI. It works. Use for prototyping; don't ship products on top of it (the real driver gives you proper power management, error handling, and proper user-space ABI)."

### Missing examples / figures
- A timing diagram for §47.4 showing two `spi_transfer`s in one message vs two separate messages — CS waveform highlighting "held vs released."
- §47.3 — show `cat /sys/class/spi_master/spi2/of_node/full_name` and the resulting `/sys/bus/spi/devices/spi2.0/` after probe.
- §47.7 — show the connection diagram of MCP3008 to ecspi (CS, MOSI, MISO, SCK) so the reader can build it.

### Technical errors
- §47.3 `fastadc_remove(struct spi_device *spi)` returning `void` — correct! SPI's `remove` has been `void` for a while now (long before the platform/i2c transition). Good.
- §47.3 the `spi_setup(spi)` call in probe is correct.
- §47.4 `xfers[0].delay.value = 10; xfers[0].delay.unit = SPI_DELAY_UNIT_USECS;` — confirmed the modern `spi_delay` struct (since 5.5). Older kernels used `xfer->delay_usecs` directly; you can mention both.
- §47.5 `spi_write`, `spi_read`, `spi_write_then_read` — correct. Add: "These all use `spi_sync` internally; they sleep, must be called from process context."
- §47.6 `"rohm,dh2228fv"` placeholder — correct historical note. Mention that the kernel now (since ~6.0) accepts `"spidev"` for `compatible` if you really want generic spidev, but it logs a warning about uninstantiable bindings. The community still prefers using the real chip's compatible.
- §47.7 MCP3008 protocol — the 3-byte command `{ 0x01, 0x80 | (ch << 4), 0x00 }` decodes the channel correctly. Note: bit 7 of byte 2 = single-ended/differential select. The example uses single-ended (bit 7 set); correct for typical wiring.
- §47.9 Pitfall on `spi_sync_transfer` from atomic context — correct.
- §47.9 Pitfall "`bits_per_word` != 8 ... byte order may not be what you expect" — slight clarification: when `bits_per_word = 16`, the buffers are read as `__u16` and the kernel handles byte order based on `spi->mode` flags (`SPI_LSB_FIRST` etc.). For most chips, stick to 8.

### Knowledge prerequisites missing
- "ecspi" — i.MX6ULL has 4 controllers named ECSPI1..4. Some boards also have a `gpmi-spi` or similar. Worth one sentence on the i.MX nomenclature: "ECSPI = Enhanced Configurable SPI; the i.MX-specific SPI controller. Mainline driver is `drivers/spi/spi-imx.c`."
- "MOSI/MISO/SCK/CS" — the chapter assumes the reader knows. Probably fine for the persona (6 YOE embedded), but a footnote with the meanings is cheap.
- `spi_set_drvdata` — set in §47.3 but not introduced. Same pattern as `i2c_set_clientdata` — cross-reference.

### Other
- §47.10 Going deeper — strong list. Add: "`Documentation/spi/spi-summary.rst`" (the high-level overview).

## Ch48 — PWM and RTC subsystems

### Readability
- Chapter splits cleanly into PWM and RTC halves.
- §48.1.1 PWM architecture ASCII is good.
- §48.1.2 DT example annotation is excellent.
- §48.2.1 "Two RTCs to know about" framing is great.
- §48.2.6 wake-from-suspend section is short and effective.

### MCU-engineer friendliness
- §48.1.3 consumer API — add MCU bridge: "Equivalent of `HAL_TIM_PWM_Start(htim, channel)` on STM32, but with the period/duty in nanoseconds instead of compare register values. The kernel computes the divisor and compare for you given the requested period."
- §48.2.1 — MCU bridge: "Your RTC chip on the MCU side was probably I²C-attached DS3231 with `Wire.h` calls. Same chip on Linux is registered by a kernel driver; you read it via `hwclock` or the kernel reads it at boot. You almost never write RTC code in a Linux driver."
- §48.2.6 alarms — add: "On an MCU you'd configure the RTC's alarm register and wire it to an EXTI line for wake. On Linux, set `/sys/class/rtc/rtc0/wakealarm` to the future timestamp; the kernel arms the RTC and configures power management to use it as a wake source."

### Missing examples / figures
- A waveform showing PWM output (period, duty cycle, polarity) — even ASCII art:
  ```
  ▕▔▔▔▔▔▔▔▕▁▁▁▁▁▕▔▔▔▔▔▔▔▕▁▁▁▁▁
   on (duty)   off (period-duty)
  ```
- After §48.1.5 sysfs example, a `scope` photograph or a `gpio capture` showing the PWM coming out the pin would help.
- A diagram for §48.2 showing the two RTCs and how Linux picks one as `/dev/rtc0`.

### Technical errors
- §48.1.1 "i.MX6ULL has 8 PWM channels (PWM1–PWM8)" — **8 PWM modules**, each is a single channel. The kernel exposes them as `pwmchip0` through `pwmchip7` typically, with one channel each. Worth being precise: "8 independent PWM controllers, each one channel wide on this SoC."
- §48.1.3 `pwm_apply_state(pwm, &state)` — modern. `pwm_apply_might_sleep` exists in some places too. Standard usage is fine.
- §48.2.2 `compatible = "maxim,ds3231", "dallas,ds1307"` — both compatibles in one node is correct; the kernel matches the first; the second is a fallback for older drivers.
- §48.2.5 `hwclock -w` writes RTC; `hwclock -s` reads RTC into system. Correct.
- §48.2.4 RTC provider sketch — `devm_rtc_allocate_device` and `devm_rtc_register_device` are modern. Correct.
- §48.4 Pitfall on "RTC time-zone confusion" — note that systemd's `timedatectl set-local-rtc 0` is the modern command; the older path was `hwclock --systohc --utc`.

### Knowledge prerequisites missing
- `pwm-backlight` — used in §48.1.2 but the binding details (brightness curve, `brightness-levels`) deserve a sentence on what the array means: "Linear brightness 0–255 mapped to those levels at the indices given. Index N maps to `brightness-levels[N]` as the duty cycle."
- `wakeup-source` flag — introduced in §48.2.2 without context. Note: "This flag tells PM core that the device's IRQ can wake the system from suspend. It enables `/sys/class/.../power/wakeup` controls."
- `SNVS_LP` — i.MX6ULL Secure Non-Volatile Storage / Low Power. Worth one sentence. The reader may have heard of "SNVS" in NXP datasheets and wonder.

### Other
- Lab #2 `pwm-beeper` — note that `pwm-beeper` is driven via `/dev/input/eventN` (yes, an input device!) with EV_SND. The Ch 45 input subsystem chapter doesn't mention this; cross-reference back.
- §48.5 references `drivers/rtc/rtc-ds1307.c` as a masterclass — agree, but warn that the file is ~1700 lines. Skim the family-detection logic at the top first.

## Ch49 — IIO subsystem (ADCs, sensors)

### Readability
- §49.1 architecture ASCII is great.
- §49.2 channel table is comprehensive.
- §49.3 channel definition is clear.
- §49.6 trigger orchestration is well-explained step-by-step.
- §49.7 ADC special case is well-paced.

### MCU-engineer friendliness
- §49.1 — best opportunity for an MCU bridge: "On an MCU, you'd write a sensor driver that exposes `read_temp()`, `read_pressure()`. Each app calls these directly. Linux pushes the same idea to a framework: your driver exposes channels named by type, and *any* app — yours, gnuplot, Grafana, the test harness — reads them through one consistent interface. The cost: more boilerplate. The benefit: tools work without modification."
- §49.2 channels: "Think of each channel as one ADC pin or one sensor axis. The MCU equivalent of a 3-axis accelerometer is calling `accel_read(&x, &y, &z)`. The Linux IIO version is reading three files: `in_accel_x_raw`, `in_accel_y_raw`, `in_accel_z_raw` — each is one channel."
- §49.6 buffered capture: "On MCU + RTOS you'd run a timer ISR sampling at 1 kHz pushing to a circular buffer drained by a task. IIO does the same but the timer is `hrtimer-N`, the buffer is a kfifo, and the drainer is whoever reads `/dev/iio:device0`."

### Missing examples / figures
- §49.2 conversion formula `real_value = (raw + offset) × scale` deserves a worked numeric example with all three numbers shown.
- §49.6 — show the actual `/sys/bus/iio/devices/iio:device0/` tree after enabling buffered capture, with `scan_elements/`, `buffer/`, `trigger/` directories visible.
- §49.7 — diagram showing the relationship between `scan_index`, `scan_type`, and how user-space decodes the binary buffer. The MCU dev who's done binary protocols will get this fast with a picture.

### Technical errors
- §49.3 `IIO_VAL_INT_PLUS_MICRO` returns `*val + *val2/1000000`. The example sets `*val = 0; *val2 = 10000;` and says "0.01 °C per raw." Math: `0 + 10000/1e6 = 0.01`. Correct.
- §49.4 `INDIO_DIRECT_MODE` — correct that this enables polled-via-sysfs.
- §49.4 `devm_iio_device_alloc(&client->dev, sizeof(*p))` — correct.
- §49.5 user-space `iio_attr` and `iio_readdev` — these are from `libiio` (Analog Devices) tooling, not in mainline. Specify package: `libiio-utils` (Debian) or `iio_info` (Yocto). Some distros only ship the in-kernel `tools/iio/` binaries.
- §49.6 the orchestration sequence is correct. Worth adding: triggers are a separate kernel object — `hrtimer-0` is created by writing to `/sys/bus/iio/devices/iio_sysfs_trigger/add_trigger`. Mention this so the reader doesn't wonder where `hrtimer-0` came from.
- §49.7 ADC_CHANNEL macro: `.scan_type = { .sign = 'u', .realbits = 10, .storagebits = 16 }` — for MCP3008 (10-bit unsigned), correct. `shift` defaults to 0.
- §49.9 Pitfall "Forgetting `iio_priv()`" — strongly worded; good. Note: in modern kernels (since 4.x), the private struct is allocated *after* the `iio_dev` in a single block; the alignment is handled by the alloc helper.

### Knowledge prerequisites missing
- "hwmon" — mentioned in §49.9 Pitfall "Two drivers competing... `hwmon` and IIO drivers exist for the same chip" — the reader doesn't know what hwmon is yet. Add one sentence: "hwmon (hardware monitoring) is the older sensor framework, predating IIO. New drivers should be IIO; some chips still have hwmon-only drivers."
- "kfifo" — mentioned without introduction. "Kernel FIFO — a SPSC ring buffer primitive in the kernel. `kfifo_in`, `kfifo_out`, `kfifo_len`. Lockless if there's one reader and one writer."

### Other
- §49.6 ends with "We'll meet triggers and buffers again in Ch 70/71 (IMUs) where they really earn their keep." — good forward reference.
- Lab #4 plot with gnuplot — concrete and good.

## Ch50 — regmap

### Readability
- §50.1 motivation is the strongest opener in Part VI — clear, concrete, sells the abstraction immediately.
- §50.2 minimal example is well-scoped.
- §50.3 variations subsections are clear.
- §50.5 "the full pattern" combining regmap + IIO + IRQ is a great capstone for the whole part.
- §50.6 debugfs section is excellent.

### MCU-engineer friendliness
- §50.1 — already strong. Add the MCU bridge explicitly: "If you've written an MCU driver for an audio codec or sensor with 100+ registers, you wrote the same I²C wrapper functions and bit-manipulation macros over and over. Regmap is Linux's 'enough — let me describe my chip declaratively and stop writing wrappers.'"
- §50.3 cache_type discussion — MCU bridge: "An MCU driver might `static uint8_t shadow[256]` to avoid re-reading registers it just wrote. Regmap's cache is the same idea, but the framework handles invalidation when you mark registers volatile."
- §50.4 `regmap_update_bits` — bridge: "Equivalent of:
  ```c
  uint8_t v;
  i2c_read(reg, &v);
  v = (v & ~mask) | (val & mask);
  i2c_write(reg, v);
  ```
  ...except atomic with respect to other regmap callers on the same device, and possibly cache-only if the register is cached."

### Missing examples / figures
- A layered diagram for §50.1 showing:
  ```
   driver code → regmap API → cache layer → bus layer (I²C/SPI/MMIO) → hardware
                                  ↓
                              debugfs view
  ```
- §50.3 cache types comparison — a small table:
  | Type | Lookup cost | Memory cost | Best for |
  |------|-------------|-------------|----------|
  | NONE | bus hit | 0 | rarely accessed registers |
  | RBTREE | O(log N) | sparse | thousands of regs used sparsely |
  | FLAT | O(1) | dense (max_reg bytes) | <128 regs all used |
- §50.5 full pattern — show the call graph: probe → regmap_init → init_sequence → request_irq → iio_register. The MCU dev wants to see the order of operations.

### Technical errors
- §50.2 `devm_regmap_init_i2c(client, &my_regmap_config)` — correct.
- §50.3 `REGCACHE_RBTREE` and `REGCACHE_FLAT` are both correct constants. There's also `REGCACHE_MAPLE` in newer kernels (6.4+) — replacing rbtree for sparse cases. Mention.
- §50.4 `regmap_multi_reg_write` correctly takes `struct reg_sequence` array. Good.
- §50.5 sketch: `iio_priv(idev)` and `devm_iio_device_alloc` are used correctly. The `regmap_read` for two registers and combining hi/lo is a common pattern; would be cleaner with `regmap_bulk_read(p->regmap, REG_DATA_HI, buf, 2)` followed by `be16_to_cpup(buf)`. Mention as a stylistic improvement.
- §50.6 debugfs path is correct; the directory name `1-0076` is `bus-address` (1 = i2c-1, 0076 = address 0x76). Mention the naming convention.
- §50.8 Pitfall "Mixing regmap and direct bus access" — strong. Worth adding: "Even calling `i2c_smbus_read_byte_data` on the same chip while a regmap exists for it can corrupt the cache."

### Knowledge prerequisites missing
- `REGCACHE_NONE` is the default — worth stating explicitly. The reader might wonder.
- `regcache_mark_dirty` and `regcache_sync` are mentioned in §50.3 and §50.7 Lab — first time they appear without clear definitions. Add: "`regcache_mark_dirty(rm)` marks every cached register as 'cache may differ from hardware.' `regcache_sync(rm)` writes back all dirty registers to hardware. Together they form the suspend/resume idiom."
- `reg_default` vs `reg_sequence` — both used; they're different types. Spell out the difference: "`reg_default` says 'register X defaults to value Y'; the cache uses this to know what *not* to push to hardware. `reg_sequence` says 'send this sequence of writes'; it's an init script."

### Other
- §50.9 Going deeper — note that `sound/soc/codecs/wm8960.c` is a great teaching example; agree. Also recommend `drivers/mfd/syscon.c` for an MMIO regmap example.
- The chapter is the strongest in the part. Use it as the structural template if you ever revise the others.
