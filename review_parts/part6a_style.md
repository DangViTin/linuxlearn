# Part VIa — Style/ESL Review

## Cross-cutting patterns

- **Em-dash overload, still the book's signature tic.** Driver chapters lean on " — " to glue clauses, often three times per paragraph. Many should be periods (a few examples flagged per chapter; the pattern is everywhere).
- **Semicolon-glued clauses.** Less than Parts II–V but still frequent in `Pitfalls` bullets ("X happens; Y is the fix"). Period reads better for ESL.
- **"Not X — but Y" / "Not X, it's Y" cadence.** Ch36, Ch37, Ch41, Ch46 all reach for it. Trim.
- **AI-buzzword hits**: `crucial`, `essential`, `comprehensive` are mostly absent (good), but `internalise/internalize`, `mechanical` (used as praise: "the API choice is mechanical"), `canonical`, and `idiomatic` appear over and over. Vary or drop.
- **Triplet rhythm.** "Sleep, mutex, copy_to_user — all fine." / "Three players:" / "Three questions, one primitive." Rhythmic but reads AI-generated when repeated within one chapter.
- **Royal "we'll/let's" overuse.** "Let's pull apart the four interesting pieces." / "Let's see them in action." / "Let's write the world's simplest..." Replace half with imperative ("Walk through the four interesting pieces.") or drop.
- **"That's it." / "That's the whole pattern." / "That's the whole API."** Used as a sentence at least once per chapter. Pick one or two per part, drop the rest.
- **Cliché phrases.** "the workhorse bus of embedded" (Ch46), "the kernel's cleverest tricks" (Ch41), "the right starting point" (Ch40), "a masterclass" (Ch48). All marketing-flavor; cut.

## Ch36 — Your first kernel module

### AI wording / sledgehammer / buzzwords
- > "A kernel module isn't a program. It's a **library that the kernel dynamically links into itself.**"
  - "Not X. It's Y." sledgehammer. Rewrite: "A kernel module is a library that the kernel dynamically links into itself."
- > "This isn't merely a coding-style change. It changes the failure modes too."
  - Same pattern, paragraph later. Rewrite: "This is more than a coding-style change. The failure modes change too."
- > "Twenty-some lines. Let's go through each."
  - "Twenty-some" is informal English and odd for ESL. Rewrite: "About twenty lines. Walk through each."
- > "The kernel build system (Kbuild) is invasive — it generates per-module ELF sections, applies the kernel's own `CFLAGS`..."
  - "Invasive" has negative tone. Em-dash glue. Rewrite: "Kbuild does a lot of work for you. It generates per-module ELF sections, applies the kernel's own `CFLAGS`..."
- > "**Mismatch = refused load.**"
  - Cute but parses oddly for ESL. Rewrite: "If they differ, the load is refused."
- > "Crank it up:"
  - Idiomatic. Rewrite: "Raise it:"
- > "Useful for debugging; spammy in production."
  - Semicolon glue + "spammy" is slang. Rewrite: "Useful for debugging. Noisy in production."

### ESL readability
- > "Your code is sitting passive — invoked from system calls, interrupts, work queues, kthreads, whatever subsystem you've hooked into."
  - "Sitting passive" is awkward English; "whatever subsystem you've hooked into" is idiomatic. Rewrite: "Your code waits, then runs when something calls into it — a system call, an interrupt, a work queue, a kthread, or whichever subsystem registered it."
- > "A wild pointer in firmware corrupts your `.bss`. A wild pointer in a kernel module corrupts *the kernel*, and the kernel is whatever is currently running — kernel threads, other drivers, the scheduler."
  - 36-word sentence with em-dash mid-clause. Break: "A wild pointer in firmware corrupts your `.bss`. A wild pointer in a kernel module corrupts the kernel itself. That can mean kernel threads, other drivers, or the scheduler — whatever happens to be running."
- > "Without it, the loader can't find your code."
  - Fine; keep.

### Needs more depth
- §36.2 `GFP_KERNEL` / `GFP_ATOMIC` are referenced under `kmalloc` in the MCU table without explanation. The first time `GFP_KERNEL` actually appears in code (Ch37) it is also not explained. Add one paragraph here or in Ch37 §37.4 introducing the flag family: "`GFP_*` flags tell the allocator how hard it can work. `GFP_KERNEL` may sleep waiting for memory reclaim — fine in process context. `GFP_ATOMIC` never sleeps but may fail when memory is tight — required in IRQ context. There are a dozen more; these two cover 95% of driver code."

## Ch37 — A character driver, by hand

### AI wording / sledgehammer / buzzwords
- > "What the user *thinks* they're doing — 'writing to a file' — is whatever your `write` callback chooses to do. Send bytes over UART. Set GPIO pins. Allocate buffers. Cache and return on next read."
  - Triplet-plus-bonus rhythm reads AI. Trim to: "What the user thinks is 'writing to a file' is whatever your `write` callback decides to do — send UART bytes, toggle GPIOs, fill a buffer for next read."
- > "The 'file' abstraction is a façade; you decide what's behind it."
  - "Façade" is poetic; semicolon glue. Rewrite: "The 'file' is a façade. You decide what's behind it." (Or drop "façade" entirely: "The 'file' is just an interface — you decide what's behind it.")
- > "Years ago you'd pick 'an unused major'... Now we ask the kernel:"
  - "Years ago / Now we" rhetorical setup. Rewrite: "The old way was to pick an unused major from a documented list. The modern way is to ask the kernel for one:"
- > "Hard-coding majors was a 1990s pattern and is now actively discouraged."
  - "Actively discouraged" is corporate. Rewrite: "Hard-coding majors is a 1990s pattern. Don't do it."
- > "It's the most readable way to handle error paths in C — far better than nested `if`s. New kernel-module authors find it strange for an afternoon, then can't imagine writing it any other way."
  - Preachy. Rewrite: "It is the kernel's idiomatic error-path style. After a dozen drivers it becomes natural."
- > "There's never a reason to bypass `copy_to/from_user`."
  - Absolute. Rewrite: "Don't bypass `copy_to/from_user`."

### ESL readability
- > "On i.MX6ULL with no MMU domain protection it might *appear* to work — but only when the user buffer happens to be paged in and accessible from kernel mode, which is not always the case."
  - 35 words, two clauses. Break: "On i.MX6ULL there is no MMU domain protection, so a direct dereference might *appear* to work. But it only works when the user buffer is paged in and reachable from kernel mode — not always the case."
- > "Multiple `cat`s in a row read the same 5 bytes each time — because our `read` checks `*ppos >= buf_len` and signals EOF appropriately, then `cat` reopens and starts from `*ppos = 0` next time."
  - 35-word run-on; tense slippage between "next time" and "in a row." Rewrite: "Each new `cat` invocation gets a fresh open, so `*ppos` resets to 0. Within one `cat`, the first `read` returns 5 bytes and the second returns 0 (EOF)."
- > "The pair `cdev_init` + `cdev_add` is conceptually one step that the kernel splits to make initialization-time vs. registration-time allocation distinguishable; you treat it as two lines next to each other."
  - 30-word sentence, semicolon glue, dense vocabulary ("distinguishable"). Rewrite: "`cdev_init` and `cdev_add` are really one logical step. The kernel splits them so it can tell apart initialization from registration. Treat them as two lines next to each other."

### Needs more depth
- §37.4 Idea 1 (`container_of`): explained as "a compile-time trick — no runtime cost." For an MCU reader who has never seen `offsetof`-based parent recovery, this is too thin. Add a 4-line diagram showing the struct layout, the inner cdev pointer, and the pointer-subtract that recovers the outer `hello_dev *`.
- §37.4 Idea 2 (`__user`): the section explains *what* `copy_to_user` does (validate, fault-handle, return uncopied count) but does not explain *why* it cannot be a memcpy. For an MCU reader with no MMU experience, add one sentence: "User-space lives in a separate virtual address space, and the page may not be mapped right now — `copy_to_user` brings it in if needed."
- §37.4 Idea 3 (`mutex_lock_interruptible`): "if a signal is pending while we wait for the lock, `_interruptible` returns `-ERESTARTSYS`" — first mention of signals in driver context for an MCU reader. Add one sentence linking to a familiar idea: "Linux signals are roughly the user-space equivalent of IRQ-driven async events; `Ctrl-C` from the terminal sends SIGINT to the foreground process. `_interruptible` means our wait can be aborted by such a signal."

## Ch38 — Auto-creating /dev nodes

### AI wording / sledgehammer / buzzwords
- > "This is profoundly different from how you might imagine it."
  - "Profoundly" is overdone. Rewrite: "This is different from how you might imagine it."
- > "The kernel does **not** maintain `/dev/`. The kernel publishes events; user-space chooses what to do with them."
  - Sledgehammer + semicolon. Rewrite: "The kernel does not maintain `/dev/`. It publishes events. User-space decides what to do with them."
- > "Take the driver from Chapter 37 and add three lines."
  - It is actually more than three lines (struct fields, init lines, exit lines, cleanup labels). Rewrite: "Take the Ch 37 driver and add a class, a device, and matching cleanup — about a dozen lines."
- > "No `mknod` step. The file appears at load and disappears at unload."
  - Two-sentence reveal; fine, keep.
- > "(`echo add > uevent` re-triggers — useful for replaying events on a system that booted before udev was running.)"
  - Useful info buried in parentheses. Move out: "Writing `echo add > uevent` re-triggers the event. This is useful for replaying events on a system that booted before udev was running."

### ESL readability
- > "Conceptually, a *class* is a group of devices that share a role (LED, RTC, GPIO chip, network interface, sound card). The class directory becomes a namespace under which individual devices live."
  - "Becomes a namespace under which X live" is dense. Rewrite: "A *class* is a group of devices that share a role — LED, RTC, GPIO chip, network interface, sound card. The class directory holds one entry per device in that group."
- > "Drivers that *do* fit (an LED driver belongs in `leds`, an RTC in `rtc`) skip class creation and register with the **subsystem** framework instead (Ch 44–48 cover those frameworks one by one)."
  - 32-word sentence, two parentheticals. Break: "Drivers that fit an existing class skip `class_create` and register with the subsystem framework directly. For example, an LED driver belongs in `leds` and an RTC in `rtc`. Ch 44–48 cover these subsystems."

### Needs more depth
- §38.3 first sentence on `class_create` describes its function but never explains *why* the kernel has both classes (a sysfs hierarchy) and bus types (`platform`, `i2c`, `spi`). For the MCU reader this is the first hint of the device-model split. One sentence: "Classes group devices by *role*; buses group them by *how the CPU reaches them*. A single device belongs to one bus and one class."
- §38.6 `sysfs_emit` — introduced in passing ("bounds-checked since 5.10; prefer over sprintf") with no explanation of *why* a custom sprintf exists at all. One sentence: "`sysfs_emit` is `sprintf` for sysfs callbacks; it checks that you don't write past PAGE_SIZE, which is the kernel's hard cap for any sysfs read."

## Ch39 — Platform drivers + device tree

### AI wording / sledgehammer / buzzwords
- > "Almost everything on an i.MX6ULL is platform: GPIO blocks, UARTs, I²C controllers (the controllers themselves; the *devices on them* are I²C-bus children), SPI controllers, PWM, ADC, timers, FlexCAN, Ethernet MAC, USB OTG controllers, LCDIF, eCSPI, etc."
  - 42-word bulleted-as-prose sentence. Rewrite: "Almost everything on i.MX6ULL is a platform device: GPIO blocks, UARTs, I²C/SPI/eCSPI controllers, PWM, ADC, timers, FlexCAN, Ethernet MAC, USB OTG, LCDIF. (The devices on an I²C bus are I²C-bus children, not platform devices.)"
- > "That's the whole template. Let's pull apart the four interesting pieces."
  - "That's the whole" cliché + "let's" royal we. Rewrite: "That is the full template. Look at the four pieces that matter."
- > "This is the biggest stylistic win in modern kernel code."
  - "Stylistic win" is corporate. Rewrite: "`devm_*` is the biggest readability gain in modern kernel code."
- > "Always prefer it to `dev_err(...) + return -EINVAL;`."
  - Fine; keep.
- > "Useful in development: re-probe a device after fixing a hardware glitch, without rebooting. Also useful in production for power-saving (unbind unused hardware to drop its clocks)."
  - Two "Useful X:" fragments back to back. Rewrite: "Useful in development for re-probing a device after a hardware glitch, without a reboot. Also useful in production: unbind unused hardware to drop its clocks."

### ESL readability
- > "It exists solely to give the driver/device model something to attach to. When the kernel parses the DT at boot, every node whose parent has no `compatible` for a real bus (i.e., everything directly under the SoC node) becomes a platform device."
  - The "every node whose parent has no `compatible` for a real bus" clause is heavy. Break: "It exists only to give the device model something to attach to. At boot, every DT node whose parent does not name a real bus becomes a platform device. In practice that means everything directly under the SoC node."

### Needs more depth
- §39.3 Piece A: `MODULE_DEVICE_TABLE(of, ...)` is explained as "exposes the table to depmod" but the reader has not yet seen what `depmod` does. One sentence: "`depmod` is the tool (run at module-install time) that scans every `.ko` for its `MODULE_DEVICE_TABLE` entries and writes them to `/lib/modules/*/modules.alias`. `modprobe` consults this alias file to find which `.ko` matches a given DT compatible."
- §39.7 `EPROBE_DEFER` mechanism is mentioned but never explained at a system level — the reader might wonder how the kernel knows when to retry. One paragraph: "The kernel keeps a list of devices whose probe returned `-EPROBE_DEFER`. Every time a *new* device successfully probes (which may have provided the missing resource), the kernel re-tries the deferred list. After a few seconds with no progress, deferral times out and the device is logged as never-bound."
- §39.7 shutdown vs remove: "shutdown() runs in atomic context — keep it short." Surprising claim for someone new to PM; deserves a sentence about why ("system is on the way down; scheduler may not be available; you have milliseconds before power is cut").

## Ch40 — The misc framework

### AI wording / sledgehammer / buzzwords
- > "For simple character devices that don't fit a standard subsystem, this is the right starting point."
  - "The right starting point" is consultant-speak. Rewrite: "Use it for simple character devices that don't fit a standard subsystem."
- > "Knowing when to reach for it saves real effort."
  - Idiomatic ("reach for it") and vague ("real effort"). Rewrite: "Knowing when to use it saves you the chardev boilerplate."
- > "For the in-between cases — 'simple chardev, one or two instances, no existing framework' — misc is perfect."
  - "Perfect" is marketing. Rewrite: "For these in-between cases — simple chardev, one or two instances, no matching framework — misc fits."
- > "Two functions. That's the whole API."
  - "That's the whole API" again. Rewrite: "Two functions. The full API."
- > "Six lines to register, one to deregister."
  - Fine; keep.

### ESL readability
- > "**`miscdevice` struct must outlive the registration.** Don't put it on the stack of `init()`. Make it `static` (as in the example) or allocate it from `kmalloc`. The misc layer holds a pointer to your struct."
  - Four sentences for one idea. Tighten: "**`miscdevice` must outlive the registration**, because the misc layer holds a pointer to it. Don't put it on the stack of `init()` — make it `static` or allocate it with `kmalloc`."

### Needs more depth
- §40.1 first bullet "you need a chardev for a single device (or a small fixed number)" without quantifying. The reader is left wondering "what's small." Add one sentence: "Misc has a finite pool of dynamic minors (~150); for hundreds of instances, use a chardev with your own major."

## Ch41 — Concurrency in the kernel

### AI wording / sledgehammer / buzzwords
- > "Pick the wrong primitive and you get the wrong of two failure modes: a silent data-corruption race, or a lockup so deep that `dmesg` can't tell you what happened."
  - "The wrong of two failure modes" is awkward phrasing. Rewrite: "Pick the wrong primitive and you hit one of two failure modes: a silent data-corruption race, or a lockup so deep that `dmesg` cannot tell you what happened."
- > "Concurrency is the rule, not the exception."
  - Cliché. Rewrite: "Concurrency is the default. Every shared variable needs a plan."
- > "Three questions. Answer them and you've picked your primitive."
  - Triplet-rhythm reveal. Fine once; trim sibling triplets nearby.
- > "Read-Copy-Update is one of the kernel's cleverest tricks."
  - "Cleverest tricks" is fan-prose. Rewrite: "Read-Copy-Update is the kernel's read-mostly trick: readers pay zero synchronization cost."
- > "RCU is heavy machinery; you wouldn't use it for a simple counter. But for 'lookup-then-use' data structures read on every packet, it's revolutionary..."
  - "Revolutionary" is marketing. Rewrite: "RCU is heavy machinery — not for a simple counter. But for 'lookup-then-use' data on every packet, it is dramatically faster than any lock."
- > "Per-CPU data is brilliant when reads are rare relative to writes (the opposite of RCU's sweet spot)."
  - "Brilliant" + "sweet spot" both idiomatic. Rewrite: "Per-CPU data works well when reads are rare relative to writes (the opposite of RCU's case)."
- > "Worth turning on. Worth keeping on through development. Then disable for production."
  - Triplet. Rewrite: "Turn it on during development. Disable for production."

### ESL readability
- > "While you hold a spinlock, the holding CPU has IRQs disabled (in the IRQ-safe variant) and the kernel won't preempt the current task."
  - "The holding CPU has IRQs disabled (in the IRQ-safe variant) and..." reads as a parenthetical mid-clause. Rewrite: "While you hold a spinlock, the kernel will not preempt the current task. In the IRQ-safe variant, IRQs are disabled on the holding CPU too."
- > "When it triggers, you get a wall of dmesg output with two stack traces (acquire path 1 vs acquire path 2) and a verdict like 'deadlock possible.' Read it carefully — it tells you exactly which locks, in which order, and from which functions."
  - 40-word sentence. Break: "When it triggers, you get a wall of dmesg output. Two stack traces, one per lock acquisition path, and a verdict like 'deadlock possible.' Read it carefully — it tells you which locks, in which order, from which functions."

### Needs more depth
- §41.4 "the CPU's atomic-instruction support (ldrex/strex on ARM)" — most MCU devs have never used `ldrex/strex`. One sentence: "These are ARM's load-exclusive / store-exclusive instructions: load with a reservation, store only if the reservation is still intact. Failure means another CPU touched the address; retry."
- §41.7 RCU section: the example uses `rcu_dereference_protected` with `lockdep_is_held(&write_lock)` but `write_lock` is never defined. The reader sees a magic identifier. Either define it inline or note that writers must also serialize among themselves via some other lock.

## Ch42 — Sleeping, waiting, polling

### AI wording / sledgehammer / buzzwords
- > "Every driver that produces data on its own schedule — UART, keyboard, sensor, network — needs a way to make a reader wait without polling."
  - Bullet-as-prose. Rewrite: "Drivers that produce data on their own schedule (UART, keyboard, sensor, network) need a way to make a reader wait without polling."
- > "Wait queues are how Linux makes blocking I/O efficient: the thread sleeps, the scheduler runs something else, and an interrupt or timer wakes the thread exactly when its data is ready."
  - 35-word run-on. Break: "Wait queues are how Linux makes blocking I/O efficient. The thread sleeps. The scheduler runs something else. An interrupt or timer wakes the thread when its data is ready."
- > "Get this dance right and your driver's blocking I/O is correct; get it wrong and you have a 'sometimes the read just hangs forever' bug."
  - "Get this dance right" idiom + semicolon glue. Rewrite: "Get the sequence right and your driver's blocking I/O is correct. Get it wrong and reads sometimes hang forever."
- > "Never use the uninterruptible variants — a stuck driver with uninterruptible waiters is the classic D-state hang that takes the system down with it."
  - "Takes the system down with it" is informal. Rewrite: "Never use the uninterruptible variants. A stuck driver with uninterruptible waiters is the classic D-state hang — the user cannot kill the process; only a reboot fixes it."
- > "`O_NONBLOCK` is a per-open flag. The user can also flip it later via `fcntl(fd, F_SETFL, O_NONBLOCK)`. Always honor it."
  - "Flip it" + "honor it" both idiomatic. Rewrite: "`O_NONBLOCK` is a per-open flag. The user can change it later via `fcntl(fd, F_SETFL, O_NONBLOCK)`. Always check it."

### ESL readability
- > "`poll_wait` after returning the mask. The order is: register first (`poll_wait`), then return the mask. Reverse it and the kernel may register no wait at all, leading to busy-looping in `select`."
  - Pitfall headline reads backwards from the explanation. Rewrite the headline: "**`poll_wait` called after returning the mask.** Order matters: register the wait first, then return the mask. Reverse it and the kernel may register no wait, so `select` busy-loops."

### Needs more depth
- §42.2 "This loop is what prevents the 'lost wakeup' race" — names the race but does not explain it. For someone seeing wait queues for the first time, this is a real conceptual gap. Add a small race diagram: producer sets condition → wake_up → meanwhile reader checks condition (false, racing) → reader sleeps → no future wake → forever. Then show how `wait_event_*` sequencing avoids it (set state TASK_INTERRUPTIBLE *before* the final check, so any wake sets us runnable even if we are about to schedule).
- §42.6 task states list is dense. Add a sentence on `TASK_RUNNING` to clarify: "`TASK_RUNNING` does not mean 'on a CPU right now'; it means 'eligible to run.' The scheduler picks one runnable task per CPU at a time."

## Ch43 — Interrupts

### AI wording / sledgehammer / buzzwords
- > "Get the IRQ-handler design wrong and you cause one of two failures — *missed interrupts* (handler too slow or wrong polarity) or *IRQ storms* (handler doesn't acknowledge, hardware re-asserts continuously, system locks up). The right design is mechanical once you know the rules."
  - "The right design is mechanical" again. Rewrite: "Get the IRQ-handler design wrong and you hit one of two failures: *missed interrupts* (handler too slow or wrong polarity) or *IRQ storms* (handler does not acknowledge, hardware re-asserts continuously, system hangs). The rules below give you the right design every time."
- > "Internalise this constraint and the API choices for the rest of this chapter make obvious sense."
  - "Internalise" + "make obvious sense" both AI-flavored. Rewrite: "Once you accept this constraint, the API choices below follow naturally."
- > "Five lines of real work. Read status, ack, snapshot, defer, return. Under 1 µs on i.MX6ULL."
  - Triplet + fragment. Fine for emphasis once, but the next paragraph also opens with a triplet — vary.
- > "**Use threaded IRQ for ~80% of new driver code.** It's the cleanest model."
  - "Cleanest model" is marketing. Rewrite: "**Use threaded IRQ for most new driver code.** It is the simplest correct pattern."

### ESL readability
- > "The DT says `interrupts = <0 99 IRQ_TYPE_LEVEL_HIGH>` — that's the GIC's hardware number. The kernel maps it to a virtual IRQ (`virq`) at boot time, then your `request_irq` uses the virq. You usually don't see the conversion — the framework hands you the virq directly."
  - Three sentences with two em-dash chains. Rewrite: "The DT line `interrupts = <0 99 IRQ_TYPE_LEVEL_HIGH>` carries the GIC hardware number. At boot, the kernel maps it to a virtual IRQ (a *virq*). Your `request_irq` uses this virq. You usually do not see the mapping happen — the framework hands you the virq."
- > "The `IRQF_ONESHOT` flag is important: it keeps the IRQ masked from when the primary returns `IRQ_WAKE_THREAD` until the threaded handler completes. Without it, the IRQ could re-fire and re-schedule before you've finished processing."
  - Two long sentences with technical content. Keep but split the first: "`IRQF_ONESHOT` is important. It keeps the IRQ masked from when the primary returns `IRQ_WAKE_THREAD` until the threaded handler finishes. Without it, the IRQ can re-fire and re-schedule before you have finished processing."
- > "Don't `mdelay` more than ~10 ms; that's bad on a single-core system."
  - "That's bad" is vague. Rewrite: "Do not `mdelay` more than ~10 ms — you stall every other task on a single-core system."

### Needs more depth
- §43.2 top-half contract bullet "It runs with kernel preemption off" — first mention of kernel preemption in any handler context. One sentence: "Preemption is the kernel's right to swap out a running task for a higher-priority one; while it is off, your code keeps the CPU until it voluntarily yields."
- §43.4.1 threaded IRQ: the section says the threaded fn "runs as a kernel thread that runs with normal kernel context — can sleep." The reader needs to know that this kthread is dedicated to *this IRQ* — its name appears in `ps` as `irq/<n>-<name>`. One sentence helps debugging later.
- §43.6 shared IRQs example references a `dev_id` cookie that has not been re-introduced since §43.3. One sentence: "Remember `dev_id` is the void-pointer cookie you passed to `request_irq`; each handler on a shared line gets it back as its second argument and uses it to find its private state."

## Ch44 — GPIO subsystem + pinctrl

### AI wording / sledgehammer / buzzwords
- > "Once you internalise that — and stop thinking in 'GPIO numbers' — every GPIO-using driver in Linux reads the same way."
  - "Internalise" again. Rewrite: "Once you accept that — and stop thinking in 'GPIO numbers' — every GPIO-using driver in Linux looks the same."
- > "The two-step model is a Linux invariant"
  - "Linux invariant" sounds formal/jargon. Rewrite: "The two-step model is fixed across Linux."
- > "Build, load. Press the button: LED toggles. ~90 lines of driver, zero MMIO writes, fully portable to any SoC with a `compatible` Linux GPIO controller."
  - Marketing pitch. Rewrite: "Build, load, press the button: the LED toggles. About 90 lines, zero MMIO writes, portable to any SoC with a Linux GPIO driver."
- > "If you forget step 1 — leave the pin in its default UART function — step 2 reads garbage and your driver thinks the button is always pressed."
  - Em-dash glue. Fine; keep — useful concrete example.

### ESL readability
- > "Pin is still in its default mux (e.g., UART). `gpiod_get` succeeds (the GPIO controller doesn't know the pin is muxed elsewhere) but the GPIO seems 'stuck' — because reads/writes hit the GPIO register, but the IOMUX routes the pin to UART."
  - 40-word sentence with two parentheticals and an em-dash. Break: "Pin is still in its default mux (for example, UART). `gpiod_get` succeeds — the GPIO controller has no idea the pin is muxed elsewhere. But the GPIO seems 'stuck': reads and writes hit the GPIO register, while the IOMUX routes the pin to UART."
- > "Don't hog a pin that a driver will claim; the driver's `pinctrl_select_state` will fail. Hog only 'ownerless' pins."
  - Semicolon glue. Rewrite: "Don't hog a pin that a driver will claim. The driver's `pinctrl_select_state` will fail. Hog only ownerless pins."

### Needs more depth
- §44.2 the `0x17059` magic value is mentioned and decoded ("pull-up enabled, fast speed, drive strength = 40 Ω, etc.") but the *bit layout* of that 32-bit word is never shown. The MCU reader is used to "bit 5 = pull-up, bits 6-7 = drive strength" tables and will want one. A small ASCII table of the IOMUXC_SW_PAD_CTL_PAD bits would land well — even just for the four most common fields.
- §44.4 the difference between `gpiod_set_value` and `gpiod_set_value_cansleep` is given correctly, but the *reason* the plain version is "atomic-safe" is left implicit. One sentence: "The plain version takes a spinlock around the GPIO register write; `_cansleep` may take a mutex (the bus driver does its I/O while holding it). Mutex in atomic context = BUG."

## Ch45 — Input subsystem

### AI wording / sledgehammer / buzzwords
- > "Every keyboard, mouse, touchscreen, joystick, accelerometer-as-tilt-sensor, rotary encoder, and IR remote control on a Linux box flows through the same input subsystem."
  - Bullet-as-prose. Rewrite: "Every input device on a Linux box — keyboard, mouse, touchscreen, joystick, IR remote — goes through the input subsystem."
- > "Once that triple makes sense (`EV_KEY` + `KEY_ENTER` + `1` = 'Enter key was just pressed'), every input subsystem capability you'll meet — abs axes, relative motion, multi-touch slot protocol — is just a different combination of type/code/value."
  - 40-word sentence with parenthetical example *and* em-dash list. Break: "Once that triple makes sense — `EV_KEY` + `KEY_ENTER` + `1` means 'Enter was pressed' — the rest of the input subsystem (abs axes, relative motion, multi-touch slots) is just different combinations of type/code/value."
- > "Your driver is upstream of the type/code/value protocol; user-space is downstream. You don't talk to user-space directly."
  - "Upstream / downstream" metaphor + semicolon. Rewrite: "Your driver feeds events into the type/code/value protocol; the input core delivers them to user-space. You never talk to user-space directly."

### ESL readability
- > "**Allocating with `input_allocate_device` and registering separately, but the alloc/register can fail in different ways.** Standard `goto` cleanup applies."
  - Pitfall headline is a sentence fragment; the explanation is too short. Rewrite: "**Mixing `input_allocate_device` with separate `input_register_device`.** Both can fail, at different points. Use standard `goto` cleanup, or just use `devm_input_allocate_device` to avoid the problem."
- > "Done. Button is a real keyboard key."
  - Fine; keep.

### Needs more depth
- §45.4 `bd->input->id.bustype = BUS_HOST;` appears without explanation. ESL reader does not know what `BUS_HOST` means versus `BUS_USB`, `BUS_I2C`, `BUS_PCI`. One sentence: "`bustype` tells user-space what bus this device came from; `BUS_HOST` is the catch-all for 'on the board, no real bus.' Use `BUS_USB` for USB-HID, `BUS_I2C` for an I²C touch controller, etc."
- §45.5 autorepeat is named but not shown. For an MCU reader who has handled button repeat in firmware before, one paragraph on what `EV_REP` registration looks like (and how the user can set period via sysfs) would be valuable.

## Ch46 — I²C drivers

### AI wording / sledgehammer / buzzwords
- > "I²C is the workhorse bus of embedded"
  - Cliché. Rewrite: "I²C is the most common slow bus in embedded systems."
- > "Master this primitive and you can drive *any* I²C chip — write-then-read, repeated-start, 10-bit addressing, SMBus quirks."
  - "Master this" + triplet+quirks. Rewrite: "Get this primitive right and you can talk to any I²C chip: write-then-read, repeated-start, 10-bit addressing, SMBus quirks."
- > "Modern systems use DT, but the i2c_device_id is the historical fallback; you include both for forward/backward portability."
  - Semicolon. Rewrite: "Modern systems use DT. The `i2c_device_id` is the historical fallback. Include both for portability."
- > "Caveat: if a kernel driver has *bound* to a device, i2c-tools won't let you talk to it (you'd race with the driver). Use `-y -f` to force, but only for known-safe testing."
  - Fine, but "Caveat:" reads like a slide bullet. Rewrite: "If a kernel driver has already bound to the device, `i2c-tools` will refuse to touch it (you would race the driver). Pass `-y -f` to override — only for known-safe testing."

### ESL readability
- > "When the kernel parses DT, it sees: ... and creates an `i2c_client` with `addr = 0x76`, `name = 'bme280'`. When your `i2c_driver` registers, the I²C core walks all clients on all adapters, matches `compatible` to your `of_match_table`, and calls your `probe()`."
  - The second sentence is 28 words across three clauses. Break: "When your `i2c_driver` registers, the I²C core walks every client on every adapter. For each one whose `compatible` is in your `of_match_table`, it calls your `probe()`."
- > "Stress-test page alignment. Write 256 bytes starting at offset 3. Verify the driver correctly handles the page boundaries at 8, 16, 24, …"
  - Fine.

### Needs more depth
- §46.4 SMBus API: the section describes the API but never says what makes "SMBus" different from raw I²C at the protocol level. Three sentences: "SMBus is a subset of I²C used originally for PC motherboard management. It adds strict timing (10–100 kHz only), packet-error checking, and timeouts. In Linux, the SMBus helper functions also work on plain I²C — the kernel adapter advertises which protocol it supports, and the helper falls through to raw I²C when needed."
- §46.5 `i2c_transfer` returns "the number of messages successfully transferred" — easy to miss. The example checks `ret != 2`. Add one sentence: "On success `i2c_transfer` returns the number of messages it sent. So `if (ret != ARRAY_SIZE(msgs))` is the right error check; the code below converts a partial result to `-EIO`."

### Technical note (style-relevant)
- §46.3 driver template uses `static int mychip_probe(struct i2c_client *client)` — the modern single-argument form. Good — but the prose in §46.1 says the kernel calls `probe()` with no signature shown. Add one line: "Modern kernels (≥6.3) pass a single `struct i2c_client *`; older kernels passed a second `const struct i2c_device_id *` argument as well."

## Ch47 — SPI drivers

### AI wording / sledgehammer / buzzwords
- > "Same shape as I²C but with full-duplex transactions and per-CS independent configuration"
  - Fine in the *What* header. In §47.1 the table does the work; cut the redundant prose intro.
- > "Mirror image of the I²C driver from Ch 46. Same idioms: `module_spi_driver`, two match tables, `devm_kzalloc`, `dev_err_probe`."
  - Bullet-as-prose. Rewrite: "Mirror image of the I²C driver from Ch 46 — same idioms: `module_spi_driver`, two match tables, `devm_kzalloc`, `dev_err_probe`."
- > "Why `rohm,dh2228fv`? Because the kernel maintainers refuse to add `'spidev'` as a magic generic compatible (it's not a chip; it's a hack)."
  - Editorialising. Rewrite: "Why `rohm,dh2228fv`? The kernel maintainers will not accept `'spidev'` as a generic compatible — spidev is not a chip, just a user-space access mechanism."
- > "Useful for bring-up. Production code should be a real `spi_driver`."
  - Fine; keep.

### ESL readability
- > "The `len` is the SPI clock count; you need at least that many bytes in `rx_buf`."
  - Semicolon. Rewrite: "The `len` field is the SPI clock count, so you need at least that many bytes in `rx_buf`."
- > "The i.MX eCSPI native CS asserts/deasserts for each `spi_transfer`. If you need CS held across multiple `spi_transfer`s, either build them into one `spi_message` or use GPIO-CS via `cs-gpios` (which is held by software for the whole message)."
  - Long sentence with two options. Break: "The i.MX eCSPI native CS asserts and deasserts for *each* `spi_transfer`. To hold CS across multiple transfers, either (a) put them all in one `spi_message`, or (b) use GPIO-based CS via `cs-gpios` — software holds GPIO-CS for the whole message."

### Needs more depth
- §47.4 "CS asserts before the first transfer, deasserts after the last (unless overridden)." The "unless overridden" is the *whole point* of the `cs_change` field that the next paragraph mentions. Rewrite to make the link explicit: "CS asserts before the first transfer and deasserts after the last. To deassert between transfers in the same `spi_message`, set `cs_change = 1` on the transfer *before* the desired CS toggle."
- §47.4 `spi_async` example: introduces `spi_message_init`, `spi_message_add_tail`, and the `complete`/`context` callback fields without explaining the lifetime contract (who owns the `spi_message`, who must keep it alive until the callback fires). One sentence: "The `spi_message` and its transfers must remain valid until your `complete` callback runs — typical pattern is to embed them in your private struct, not on the stack."

## Ch48 — PWM and RTC subsystems

### AI wording / sledgehammer / buzzwords
- > "two short and orthogonal subsystems combined here because each is small enough on its own and the patterns reinforce each other"
  - "Orthogonal" is jargon. Rewrite: "two short, unrelated subsystems combined here — each is small enough on its own, and the patterns reinforce each other."
- > "You almost always write *consumers*; the SoC vendor wrote the producers."
  - Semicolon. Rewrite: "You almost always write *consumers*. The SoC vendor wrote the producers."
- > "A masterclass in handling chip-family variants."
  - "Masterclass" is fan-prose. Rewrite: "A good reference for handling chip-family variants."

### ESL readability
- > "For a fleet product, you almost certainly want `chrony` or `systemd-timesyncd` running to sync system time to NTP, then write the RTC periodically (`-11` hook or systemd's `systemd-time-sync-target`)."
  - 35-word sentence with parenthetical jargon (`-11 hook`). Break: "For a fleet product, run `chrony` or `systemd-timesyncd` to sync system time to NTP. Then write the RTC periodically — via systemd's `systemd-time-sync-target`, or an init `-11` hook."
- > "Wire up a CR2032; if you can't, accept the limitation and sync via NTP at boot."
  - Semicolon glue. Rewrite: "Wire up a CR2032. If you cannot, accept the limit and sync via NTP at boot."

### Needs more depth
- §48.1.2 the `pwms = <&pwm1 0 5000000 0>` line is decoded inline, which is good. But the broader concept of "DT phandle cells" — where the count of cells (`#pwm-cells`) is set by the provider — is never named. One sentence at the end of the inline comment: "The number of cells after the phandle (here, 3) is set by the controller's `#pwm-cells` property; check the binding doc for what each cell means."
- §48.2.1 *two RTCs* sidebar is excellent, but does not explain the practical consequence of `CONFIG_RTC_HCTOSYS_DEVICE`. Add: "If both register, the kernel reads `/dev/rtc0` at boot to set system time. Whoever registers first wins the `rtc0` name — and on many BSPs that is the SoC internal RTC, even when the external chip is more accurate. Pin the right one via kernel config or a udev rule."

## Ch49 — IIO subsystem (ADC, sensors)

### AI wording / sledgehammer / buzzwords
- > "Every chip in Part VII's sensor cookbook is an IIO driver."
  - Fine; useful forward reference. Keep.
- > "Get these three concepts right and IIO clicks."
  - "Clicks" is informal. Rewrite: "Get those three concepts right and the rest of IIO follows."
- > "Drivers declare a list of `iio_chan_spec` (channel specifications) and provide `read_raw` / `write_raw` callbacks. The core handles user-space exposure."
  - Fine; concise.
- > "We'll meet triggers and buffers again in Ch 70/71 (IMUs) where they really earn their keep."
  - "Earn their keep" is idiomatic English. Rewrite: "We come back to triggers and buffers in Ch 70/71 (IMUs), where they become essential."

### ESL readability
- > "before IIO (~2011), every sensor driver invented its own sysfs layout. Reading an ADXL345 was completely different from reading an LIS3DH despite both being 3-axis accelerometers. IIO standardised the interface: every accelerometer reports `in_accel_x_raw` in the same units after `_scale` is applied."
  - Three sentences flow fine; keep.
- > "`devm_iio_device_alloc(&client->dev, sizeof(*p))` allocates both the `iio_dev` and your private struct in one block. `iio_priv(idev)` recovers the priv pointer."
  - Good; keep.
- > "User-space writes to `scan_elements/in_*_en` to enable channels."
  - "scan_elements/in_*_en" — wildcard inside a path is confusing for ESL. Rewrite: "User-space writes `1` to `scan_elements/in_<channel>_en` for each channel to enable (e.g., `in_accel_x_en`, `in_accel_y_en`)."

### Needs more depth
- §49.3 the return-value table for `read_raw` (`IIO_VAL_INT`, `IIO_VAL_INT_PLUS_MICRO`, `IIO_VAL_FRACTIONAL_LOG2`) lists meaning but does not show what user-space sees. One worked example: "For a scale of 1/4096, return `IIO_VAL_FRACTIONAL_LOG2` with `*val=1, *val2=12`; user-space sees `0.000244` in the sysfs file."
- §49.6 buffered capture pipeline is fast and dense. The phrase "the driver's trigger handler reads a coordinated set of samples and pushes them" deserves a name (`iio_trigger_handler` / `iio_push_to_buffers`) so the reader can grep for it. One sentence with the actual function names would land well.

## Ch50 — regmap

### AI wording / sledgehammer / buzzwords
- > "Get the config right and the rest is mechanical."
  - "Mechanical" again — appears in Ch41, Ch43, here. Rewrite: "Get the config right and the rest is bookkeeping."
- > "That's a hundred lines of identical-feeling code. Regmap factors it all out. You declare *what your chip looks like*; regmap handles *how to talk to it*."
  - Triplet + semicolon. Rewrite: "That is a hundred lines of identical-looking code. Regmap factors it out: declare *what your chip looks like*, and regmap handles *how to talk to it*."
- > "The driver becomes bus-agnostic."
  - "Agnostic" is jargon. Rewrite: "The driver no longer cares which bus it sits on."
- > "Maybe 200 lines total. The same chip, hand-written without regmap and without IIO, would be 600+. The frameworks are leverage."
  - "Frameworks are leverage" is consultant-speak. Rewrite: "Around 200 lines total. The same chip without regmap or IIO would be 600+. The frameworks save you that code."
- > "For interactive driver debugging during bring-up, this is invaluable."
  - "Invaluable" is marketing. Rewrite: "This is the tool you reach for during bring-up."

### ESL readability
- > "With `cache_type = REGCACHE_RBTREE`, regmap caches all non-volatile, non-read-only registers in a red-black tree. A `regmap_read` of a cached register returns the cached value instantly; only volatile registers hit the bus. A `regmap_write` updates the cache *and* the bus; if power is restored after suspend, `regcache_sync(regmap)` flushes the cache back to the chip."
  - Three semicolon-spliced sentences. Break: "With `cache_type = REGCACHE_RBTREE`, regmap caches every non-volatile, non-read-only register in a red-black tree. A `regmap_read` of a cached register returns the cached value instantly. Only volatile registers hit the bus. A `regmap_write` updates both the cache and the bus. After resume from suspend, `regcache_sync(regmap)` flushes the cache back to the chip."
- > "Endianness mismatch. Chip is big-endian, driver assumes little-endian. Symptom: 16-bit values appear byte-swapped. Set `reg_format_endian = REGMAP_ENDIAN_BIG` in config."
  - Fragments fine for a pitfall bullet; keep.

### Needs more depth
- §50.3 the *volatile* concept is named ("ID registers are read-only; status registers change without you writing") but the *consequence* of marking a register volatile is left implicit. One sentence: "Marking a register volatile tells regmap: never cache this — always read the bus. Forget to mark a status register volatile and your driver sees the stale cached value."
- §50.5 the worked example ties regmap + IIO + IRQ together, which is great — but the IRQ handler comment "read data, push to buffer" hides the regmap → IIO call sequence that the rest of the chapter has been building toward. Either expand the comment to actual `regmap_bulk_read` + `iio_push_to_buffers` calls, or cross-link to Ch49 §49.6.
