# Every-chapter review

Perspective: 2 YOE embedded engineer. I am judging whether the chapter helps me actually do the work, what is hard to understand, what looks wrong, what sounds AI-like, and what should improve.

## Front matter

| File | Review |
| --- | --- |
| `book/index.md` | Useful home page, but status is wrong: Part VII and VIII are marked not drafted even though files exist. Cross-reference to "Ch 60" should be `ch122`. Fix status before publishing because this is the first trust signal. |
| `book/status.md` | Currently contradicts the repository. It says later parts are coming soon and Part I + II are the complete material. Either delete it or make it a real progress page. |
| `BOOK_TOC.md` | Strong scope document, but it promises 141 chapters while the actual book tree has Chapter 1-55I, then 64-126. Explain the missing 56-63 range or align the TOC with the real book. |

## Part I - Foundations

| Chapter | Review |
| --- | --- |
| `ch01-preface.md` | Strong voice and clear target reader. Problems: stale Ch 60/61/62 references, "Acknowledgements (placeholder)", and some overconfident lines like "no bug can hide from you later". Improve by making the dependency path concrete and replacing slogans with measurable outcomes. |
| `ch02-what-is-embedded-linux.md` | Good bridge from MCU thinking to Linux vocabulary. Hard part is virtual memory/process/thread differences; add one diagram showing physical memory, kernel virtual memory, user process VA, and syscall crossing. Wording is good and not AI-like. |
| `ch03-host-setup.md` | Practical and valuable, especially serial/TFTP/NFS. Risk: host setup becomes stale quickly; pin package versions or say tested on Ubuntu 22.04. Stale Ch 60 reference should become Ch 122. |
| `ch04-armv7a-for-mcu-engineer.md` | Good concept for the target reader. The mode/privilege/MMU sections are dense; add a "Cortex-M equivalent / Cortex-A difference" table. Stale secure boot reference says Ch 62 but should be Ch 124. |
| `ch05-imx6ull-tour.md` | Useful SoC orientation. The hard part is mapping the block diagram to actual RM chapters and board pins; add a worked example from pad name -> IOMUX register -> Linux DTS property. "Read Chapter 2 (Memory Maps)" seems like an RM chapter, but clarify source. |
| `ch06-toolchain.md` | One of the stronger chapters. It covers Make/ELF/linker basics in useful depth. It may be too long for a foundations chapter, but this is acceptable because later work depends on it. Add a small "common build error -> tool responsible" table. |
| `ch07-boot-rom-ivt-dcd.md` | Strong topic and good focus. Stale HAB reference to Ch 62 should become Ch 124. Add exact byte offsets and an annotated hex dump image/table; this chapter is where readers will make off-by-one mistakes. |
| `ch08-board-bring-up.md` | Practical and reader-friendly. Add more board-revision warnings: voltage levels, USB-UART adapter type, boot switch photos/labels, and "known-good serial log". Good lab discipline. |

## Part II - Bare-metal i.MX6ULL

| Chapter | Review |
| --- | --- |
| `ch09-asm-led.md` | Good first hardware win. The IVT wrapper is temporarily "magic", which conflicts with the book voice but is acceptable if clearly marked. Add expected `hexdump` output and a troubleshooting flow for no LED/no serial/no SDP. |
| `ch10-c-startup-linker.md` | Strong and necessary. Hard parts are VMA/LMA, `.data` copy, and linker symbols; add a memory layout diagram before the linker script. Sidebar heading lacks numbering while the rest is numbered. |
| `ch11-ivt-dcd-image.md` | Good "own the image format" chapter. The Python tool should be shown with unit checks or assertions for IVT offsets. The SD-card boot path needs extra warnings around device selection to avoid overwriting disks. |
| `ch12-uart-printf.md` | Good practical payoff. The baud-rate section needs extra care: show the exact input clock assumption and how to verify it. A 200-line printf clone is useful, but mark supported formats clearly so readers do not assume libc behavior. |
| `ch13-ccm-clocks.md` | Important but hard. The PLL/PFD/root/gate flow needs one end-to-end calculation with register fields and resulting measured frequency. Add more warnings about changing ARM PLL while executing code. |
| `ch14-ddr3-init.md` | The most important bare-metal chapter. Good scope, but it contains a TODO and asks readers to replace placeholder constants; this makes it feel unfinished. Add exact DDR chip part number, tested register table, stress-tool workflow, and "what failure looks like" examples. |
| `ch15-exceptions-gic.md` | Good topic sequence after UART. Hard parts are exception return and GIC acknowledge/EOI; add an interrupt timeline diagram. The Cortex-M EXC_RETURN comparison is helpful, but be precise that ARMv7-A return mechanics differ. |
| `ch16-timers.md` | Clear and useful. It is shorter than surrounding chapters but focused. Add calibration details for GPT source clock and a lab that compares busy-loop delay vs timer delay. |
| `ch17-mmu-caches.md` | Important and hard. The chapter should add a concrete page-table dump and before/after cache performance numbers. Also add stronger warnings about marking MMIO as Normal memory. |
| `ch18-bare-metal-peripherals.md` | Useful optional bridge to Linux drivers. Because it covers I2C, SPI, and LCD in one chapter, each topic is shallow. Add a decision note: this is a taste, not full peripheral mastery. |
| `ch18A-project-organization.md` | Good insertion; a real project needs structure. Make sure it does not feel like refactor-only filler by adding a before/after build tree and how to reuse drivers in later labs. |
| `ch18B-button-beep.md` | Practical and approachable. Add electrical details for active-low buzzer/PNP path and button debounce timing. Good lab, but include oscilloscope or logic analyzer validation. |
| `ch18C-baremetal-rtc.md` | Useful SNVS topic. Hard part is persistent vs non-persistent SNVS state and power domains; add a diagram of VDD_SNVS and main power. The wall-clock conversion exercise may need starter code. |

## Part III - U-Boot

| Chapter | Review |
| --- | --- |
| `ch19-uboot-from-source.md` | Good transition from bare-metal to real bootloader. Wrong reference: "Chapter 60A" migration playbook should be Ch 122A. Add exact U-Boot version and board defconfig tested. |
| `ch20-uboot-spl.md` | Good SPL explanation. The hard part is mapping SPL source to the bare-metal code already written; add a side-by-side table: Ch 14 DDR init vs U-Boot SPL function/file. |
| `ch21-uboot-internals.md` | Strong and detailed. Relocation is the hard part; add an address-before/address-after example with `gd->reloc_off`. This chapter earns the "deeply" claim more than many later ones. |
| `ch22-uboot-board-port.md` | Useful but risky: board ports are easy to oversimplify. Add an explicit checklist for DDR, IOMUX, UART, FEC, MMC, boot media, and env. Include "how to know this is U-Boot vs hardware failure". |
| `ch23-bootcmd-bootargs-fit.md` | Good practical boot chapter. Improve by showing bad bootargs examples and how the kernel fails for each. FIT signing references should point to Ch 124, not Ch 62. |
| `ch23A-multi-variant-fit.md` | Useful production topic. Needs a stronger explanation of when to use FIT configs vs DT overlays vs separate images. Stale Ch 62 references should become Ch 124. |
| `ch24-workflows-tftp-nfs-usb.md` | Practical and important. Add firewall, static IP, and Windows/WSL caveats. The chapter should end with a canonical dev loop diagram and exact expected boot log. |

## Part IV - Kernel

| Chapter | Review |
| --- | --- |
| `ch25-building-mainline-linux.md` | Good build orientation. Add explicit commands for modules install and DTB path differences. Since kernel versions change, add "tested with v6.6.x" and avoid "latest". |
| `ch26-booting-kernel-from-uboot.md` | Useful and clear. Hard part is separating U-Boot failures from kernel failures; add a table keyed by last printed line. This chapter is short but acceptable. |
| `ch27-device-tree.md` | Strong chapter, probably one of the best. Device Tree is hard; the chapter should include a full tiny DTS and a compiled/decompiled DTB comparison. Good candidate for more diagrams. |
| `ch27A-dt-bindings-yaml.md` | Valuable because many books skip bindings. Add a full failing validation example, then fix it. Make sure package/tool versions are pinned because `dtschema` behavior changes. |
| `ch28-kernel-startup-traced.md` | Good source-tracing chapter. Hard but useful. Add exact source paths for v6.6 and note which parts are ARM-specific. Include a call graph from `stext` to PID 1. |
| `ch29-initramfs-from-scratch.md` | Good hands-on chapter. Add a minimal `init` failure table: missing executable bit, wrong interpreter, missing console, missing dev nodes. Good bridge to rootfs. |
| `ch30-kernel-configuration.md` | Useful, but Kconfig can be overwhelming. Add "do not touch yet" and "safe to change" sections. The dozen knobs are good; add why each matters to i.MX6ULL. |
| `ch30A-kernel-lifecycle.md` | Good decision-framework chapter. Wrong Ch 60A references should be Ch 122A. The "4.1.15 trap" section is useful; add more nuance for vendor security support and product certification. |

## Part V - Root filesystem and userspace

| Chapter | Review |
| --- | --- |
| `ch31-rootfs-by-hand.md` | Strong practical chapter. Add exact ownership/permissions for rootfs files and a troubleshooting section for "kernel panic - no init found". |
| `ch32-proc-sys-devtmpfs.md` | Good mental model chapter. The hard part is separating procfs/sysfs/devtmpfs responsibilities; add a table of examples and which filesystem owns each. |
| `ch33-init-systems.md` | Useful comparison. Add more practical detail on BusyBox init scripts and signal handling for PID 1. Avoid making systemd discussion too opinionated; embedded choices depend on product constraints. |
| `ch34-libc-dynamic-linking.md` | Good and important. Add `readelf -l`/interpreter examples for target binaries and common failure: "No such file or directory" when the loader is missing. |
| `ch35-buildroot.md` | Good placement after hand-built rootfs. Add `BR2_EXTERNAL` earlier if the book wants production maintainability. Include what to commit and what not to commit from Buildroot output. |
| `ch35A-ubuntu-base.md` | Useful alternative. Add warnings about image size, package updates, service startup, root password, SSH, and long-term maintenance. Good to compare as peer, not default. |
| `ch35B-readonly-rootfs-overlayfs.md` | Important for products. Needs stronger power-loss testing details and what data belongs in persistent storage. Add mount diagrams for lower/upper/work/merged. |
| `ch35C-containers-on-embedded.md` | Useful but can be dangerous if oversold. Add clear "do not use containers when..." examples around memory, flash wear, real-time, and device access. |
| `appendix-tooling.md` | Helpful reference. It should be generated or audited automatically so tools do not drift. Add version/tested links and group by host tool vs target tool. |

## Part VI - Driver development

| Chapter | Review |
| --- | --- |
| `ch36-hello-lkm.md` | Good first kernel module chapter. Add exact kernel headers/tree relationship and module signing note. Good explanation of `vermagic`. |
| `ch37-character-driver.md` | Good "by hand" driver. Hard parts are file operations and lifetime; add diagrams for userspace fd -> file -> inode -> cdev. Include cleanup paths carefully. |
| `ch38-auto-device-nodes.md` | Useful follow-up. Add modern API version notes because `class_create` changed. Good place to stress udev/devtmpfs distinction. |
| `ch39-platform-driver-dt.md` | Core chapter and important. Add a full DTS node, compatible match table, probe path, and `of_property_read_*` examples. Good bridge from Ch 27. |
| `ch40-misc-framework.md` | Too short but acceptable as a focused alternative to full char drivers. Add when *not* to use misc. This reads more like a note than a chapter. |
| `ch41-concurrency.md` | Good topic and enough depth. RCU experiment references Ch 60 for ftrace; should point to Ch 119. Add "can sleep?" table for each lock/context. |
| `ch42-sleeping-waiting-polling.md` | Useful and practical. Add a complete waitqueue example with timeout and signal interruption. Good chapter for real driver behavior. |
| `ch43-interrupts.md` | Good driver chapter. Ch 60 ftrace reference should point to Ch 119. Add threaded IRQ example and explain top-half constraints more explicitly. |
| `ch44-gpio-subsystem.md` | Useful and modern if it uses descriptor APIs. Add stronger warning against old integer GPIO APIs except when reading legacy code. |
| `ch45-input-subsystem.md` | Good practical chapter. Debounce is left partly as an exercise; for the target reader, show one complete debounce implementation. |
| `ch46-i2c-drivers.md` | Strong because I2C repeats throughout the cookbook. Add SMBus vs raw I2C distinction and adapter capability checks. |
| `ch47-spi-drivers.md` | Useful but spidev handling is risky. The `rohm,dh2228fv` placeholder warning is good, but cookbook chapters must not teach it casually. Add exact production-safe overlay/driver alternative. |
| `ch48-pwm-rtc.md` | Covers two unrelated subsystems, so it feels compressed. Split PWM and RTC if possible, or make clear this is a subsystem sampler. |
| `ch49-iio-subsystem.md` | Important but short for IIO. Add buffered capture, scale/offset, triggered buffer, and userspace read examples. Many cookbook chapters depend on this. |
| `ch50-regmap.md` | Useful abstraction chapter. Add examples for cache type, volatile registers, precious registers, and debugfs. Good but could use more failure cases. |
| `ch51-dma.md` | DMA is too complex for the current length. Add cache coherency, mapping APIs, alignment, DMA-safe memory, and when DMA is not worth it. |
| `ch51A-watchdog.md` | Useful product topic. Add `nowayout`, systemd watchdog interaction, bootloader watchdog handoff, and failure injection lab. |
| `ch51B-power-management.md` | Important but too broad. Needs runtime PM vs system suspend separation, regulator/clock dependencies, and wakeup source examples. |
| `ch52-network-fec.md` | Useful i.MX-specific topic. Add more about PHY reset timing, MDIO scan, pinctrl, and common FEC boot messages. |
| `ch52A-preempt-rt.md` | Good topic but short. Add what changes in driver code under RT: sleeping locks, IRQ threading, priority inversion. |
| `ch53-sound-alsa-asoc.md` | ASoC is too big for this chapter length. Add a block diagram: CPU DAI, codec DAI, machine driver, DAPM routes. |
| `ch54-lcd-drm.md` | DRM/KMS is complex and this feels compressed. Add userspace validation with `modetest`, `kmscube`, or framebuffer fallback. |
| `ch54A-mtd-ubi.md` | Useful but short. Add bad-block handling, UBI attach output, volume layout, and why raw NAND differs from eMMC. |
| `ch54B-v4l2-gstreamer.md` | Useful but likely too shallow. Add media graph, `v4l2-ctl --list-formats-ext`, and a pipeline troubleshooting table. |
| `ch55-usb-gadget.md` | Good product topic. Needs configfs exact sequence, UDC detection, cable role, and Windows host behavior. |
| `ch55A-kernel-timers.md` | Short but useful. Add timer lifetime/cancel rules and race conditions on module unload. |
| `ch55B-async-sigio.md` | Too thin. SIGIO is niche and easy to misuse; add why poll/epoll is usually preferred, complete app+driver pair, and signal race warnings. |
| `ch55C-can-flexcan.md` | Useful but short for CAN. Add bit timing, termination, bus-off recovery, and `candump`/`cansend` examples. |
| `ch55D-block-device.md` | Too thin for block drivers. Add request queue model, bio handling, teardown, and why many products should avoid custom block drivers. |
| `ch55E-wifi.md` | Too thin for WiFi. Needs firmware/NVRAM, regulatory domain, wpa_supplicant, AP mode, and common bring-up logs. |
| `ch55F-cellular.md` | Useful topic but short. Add PPP vs QMI/MBIM decision table and real modem failure modes: SIM PIN, APN, registration, DNS. |
| `ch55G-multi-touch.md` | Too short for a full touch chapter. Add event protocol type B, slot tracking, calibration, and common GT911 reset/I2C-address sequence. |
| `ch55H-hdmi-bridge.md` | Too short. Add EDID, DRM bridge/panel chain, I2C probing, and clock constraints. |
| `ch55I-rust-for-linux.md` | Good as a sidebar. Make clear Rust-for-Linux support is kernel-version dependent and not production-stable for every subsystem. |

## Part VII - Device cookbook

| Chapter | Review |
| --- | --- |
| `ch64-qspi-flash.md` | One of the strongest cookbook chapters by density. Good code/detail balance. Add flash erase/write endurance warnings and bootloader/kernel partition interaction. |
| `ch65-eeprom.md` | Strong practical chapter. Add page-write timing, write-protect pin handling, and what happens when writes cross page boundaries. |
| `ch66-sd-emmc.md` | Useful deep dive. Add more board-level signal integrity notes and eMMC boot partition caveats. |
| `ch67-temp-humid-pressure.md` | Strong sensor chapter. The compensation formula section is good; add how to validate against known environment/reference sensor. |
| `ch68-light-color.md` | Good cookbook format. Add calibration and enclosure/window effects; raw lux/color readings are product-sensitive. |
| `ch69-air-quality.md` | Useful but should be cautious: gas sensors need warm-up, calibration, and drift handling. Avoid implying raw readings equal accurate air quality. |
| `ch70-i2c-imus.md` | Strong and detailed. Add orientation/mounting matrix and timestamping discussion. Good candidate chapter for the cookbook standard. |
| `ch71-spi-imus.md` | Good. Add SPI mode/CS timing pitfalls and FIFO overflow examples. |
| `ch72-distance.md` | Useful but some sensors have undocumented "magic registers"; explain source of those sequences and vendor-library dependency risk. |
| `ch73-magnetometer.md` | Good warning about fake/mislabelled HMC/QMC parts. Add calibration walkthrough with hard/soft iron plots. |
| `ch74-hall-rotary.md` | Useful. Add mechanical mounting tolerance and magnet selection guidance; this is where real products fail. |
| `ch75-current-monitoring.md` | Strong topic. Add shunt power rating, Kelvin routing, calibration, and signed current direction conventions. |
| `ch76-battery.md` | Useful product chapter. Add safety warnings: charger thermal design, cell chemistry, protection IC, and fuel gauge learning cycles. |
| `ch77-one-wire.md` | Good Linux `w1` chapter. Heading "DHT22 - the imposter" is memorable but a bit informal; consider softer wording. |
| `ch78-mems-mics.md` | Useful but too short for ASoC/audio capture. Add clocking, DMA, sample format, and `arecord` validation. |
| `ch79-health-sensors.md` | Good caution needed: health sensors are not medical devices. Add optical/mechanical placement and algorithm limitations. |
| `ch80-external-adc.md` | Useful. Add analog front-end notes: reference voltage, input impedance, anti-aliasing, grounding. |
| `ch81-dac-clockgen.md` | Good honesty about Si5351 complexity. The "left as advanced exercise" is acceptable, but do not call the chapter "from scratch" for that chip. |
| `ch82-rgb-lcd.md` | Good display chapter. Add timing calculation worksheet and what bad sync/polarity looks like on the panel. |
| `ch83-spi-lcd.md` | Useful. Add bandwidth math and partial update tradeoffs. Datasheet "magic" init sequences should be explicitly sourced. |
| `ch84-qspi-lcd.md` | Too thin. It reads like a caveat note, not a 16-page chapter. Expand with a real controller example or mark as short appendix. |
| `ch85-oled-epaper.md` | Good range of display types. Add burn-in/refresh/ghosting warnings and power sequencing differences. |
| `ch86-touch-input.md` | Useful. Add calibration details and event validation with `evtest`. |
| `ch87-csi-cameras.md` | Strong topic but complex. Add media-controller graph diagrams and exact `media-ctl` commands. |
| `ch88-usb-uvc.md` | Too short for the estimated scope. Good bandwidth idea, but add real `v4l2-ctl` format negotiation and failure examples. |
| `ch89-audio-codecs.md` | Useful. ASoC DAPM needs diagrams and complete DT/machine-driver examples. |
| `ch90-class-d-amps.md` | Good product topic. Add EMI, speaker impedance, gain setting, pop/click behavior, and thermal limits. |
| `ch91-sdio-wifi.md` | Useful but should include more firmware/NVRAM/regulatory examples. Add boot log and `iw`/`wpa_supplicant` validation. |
| `ch92-usb-wifi.md` | Too short. Add driver support matrix, out-of-tree driver risk, AP mode caveats, and power draw. |
| `ch93-hosted-wifi.md` | Useful alternative. Add throughput/latency comparison vs SDIO/USB and failure modes for SPI-hosted firmware. |
| `ch94-wifi-bt-combo.md` | Good topic. "just works" for coexistence is too casual; add PTA/coex details and module-specific caveats. |
| `ch95-hci-bluetooth.md` | Useful and practical. Add full BLE GATT example and BlueZ version assumptions. |
| `ch96-at-ble.md` | Too thin. Good overview, but add module command examples, pairing/security caveats, and why AT BLE often becomes limiting. |
| `ch97-ble-mesh.md` | Useful but likely shallow for mesh. Add provisioning security, relay/friend/low-power node behavior, and BlueZ mesh maturity warning. |
| `ch98-lora.md` | Stronger and detailed. The userspace driver approach is good; add legal/regulatory duty-cycle warnings by region. `Ch 47 §47.x` placeholder must be fixed. |
| `ch99-sub-ghz-proprietary.md` | Good detail. Add regulatory warnings and antenna/layout sensitivity. Fix `Ch 47 §47.x` placeholder. |
| `ch100-zigbee-thread.md` | Useful. Add stack selection (Zephyr/OpenThread/vendor NCP) and network commissioning details. |
| `ch101-uwb-ranging.md` | Good modern topic. Fix `Ch 47 §47.x` placeholder. Add antenna calibration, timestamps, and regulatory/channel constraints. |
| `ch102-usb-lte.md` | Useful. Add QMI/MBIM modes, ModemManager vs raw commands, and carrier/APN/SIM troubleshooting. |
| `ch103-uart-modems.md` | Good for low-cost modems. Add PPP logs, chat scripts, and recovery from modem lockups. |
| `ch104-nbiot.md` | Too thin and has very low code/detail density. Add attach flow, PSM/eDRX, carrier certification, and latency realities. |
| `ch105-rfid-nfc.md` | Good density. Add security caveats: MIFARE Classic is broken; do not teach UID-only authentication as safe. |
| `ch106-fingerprint.md` | Useful. Add privacy/security notes and template storage threat model. |
| `ch107-gps-pps.md` | Good product topic. Add PPS kernel config, chrony config, and timing validation with scope/logic analyzer. |
| `ch108-rs485-modbus.md` | Useful. Add direction-control timing, termination/biasing, and Modbus CRC examples. |
| `ch109-lin-bus.md` | Good niche chapter. Add checksum classic/enhanced difference and automotive voltage/transceiver notes. |
| `ch110-can-deep-dive.md` | Useful. Add more SocketCAN commands, ISO-TP examples, and physical-layer debugging. |
| `ch111-quadrature-encoders.md` | Useful. Add debounce/filtering, missed counts, and why Linux userspace may be too slow for high-rate edges. |
| `ch112-motor-drivers.md` | Good caution on hardware. Add safety warnings and distinguish Linux supervisory control from hard real-time motor control. |
| `ch113-smart-leds.md` | Useful. Add timing constraints and why Linux bit-banging is risky; emphasize SPI/RMT-style offload. |
| `ch114-beepers-relays.md` | Practical. Add flyback diode/TVS, relay contact ratings, SSR leakage, and acoustic PWM caveats. |
| `ch115-dual-fec-eth.md` | Good i.MX-specific topic. Add more detail on MDIO addresses, PHY reset GPIOs, and device tree examples. |
| `ch116-pmic.md` | Important and useful. Add regulator boot constraints, always-on rails, brownout behavior, and DVFS validation. |
| `ch117-external-rtc.md` | Useful close to cookbook. Typo in next-part note: "OPCS-grade" likely wrong. Add coin-cell/supercap and clock accuracy comparisons. |

## Part VIII - Debug, production, advanced

| Chapter | Review |
| --- | --- |
| `ch118-jtag-openocd-gdb.md` | Good topic but should be more concrete. Add exact adapter configs and known i.MX6ULL OpenOCD target config. |
| `ch119-kernel-debug-no-jtag.md` | Important but too short for estimated 26 pages. Add full ftrace, dynamic debug, kgdb, oops decoding, and eBPF version caveats. |
| `ch120-userspace-debug.md` | Useful. Add sysroot setup details and examples for `strace`, `ltrace`, `perf`, and core dumps on the target. |
| `ch120A-mainline-patch-submission.md` | Good and practical. Add exact `git send-email --dry-run`, lore links, and maintainer etiquette. Placeholder cover-letter text is fine if clearly part of generated patch workflow. |
| `ch121-custom-board-port.md` | Good capstone idea, but the chapter is too short for a 30-page claim. Add a real board-port checklist with signoff gates and a failure matrix. |
| `ch121A-cicd-embedded.md` | Useful production chapter. Add artifact retention, board power control, serial log capture, and flaky-test handling. |
| `ch122-cross-toolchain.md` | Good advanced topic. Heading "for the masochist" is informal; use "manual mini-build for understanding". Add exact crosstool-NG config fragment. |
| `ch122A-bsp-mainline-migration.md` | Very useful topic. Typo: "libcs ABI-matched" should be "libc ABI-matched". Add a real patch-classification example and risk register. |
| `ch123-yocto-vs-buildroot.md` | Useful and balanced. "honest comparison" in title sounds marketing-like; content can show honesty without saying it. Add maintenance/team-size decision table. |
| `ch123A-yocto-layer-dev.md` | Useful but too compressed for Yocto. Add exact layer tree, `bitbake-layers show-layers`, recipe QA errors, and `COMPATIBLE_MACHINE` examples. |
| `ch124-secure-boot-optee.md` | High-value but high-risk. Needs exact NXP CST/HAB version assumptions, dry-run verification, fuse map, rollback protection, and very strong warnings before closing HAB. |
| `ch125-field-updates.md` | Important. Add power-fail test matrix, rollback state machine, bootloader env handling, and RAUC/SWUpdate/Mender decision criteria. |
| `ch125A-vscode-gdbserver.md` | Practical and useful. Add `sourceFileMap`, sysroot, stripped vs unstripped binary handling, and how to debug shared libraries. |
| `ch126-closing.md` | Good closing references. Since the book is not fully polished, add a stronger errata workflow and "what changed by kernel version" page. |
