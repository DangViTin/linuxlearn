---
chapter: 121
title: Custom board port as a system design
part: VIII - Debug, production, advanced
estimated_pages: 30
status: draft
---

<span id="chapter-121-capstone-custom-board-port"></span>
# Chapter 121: Custom board port as a system design
> **NFS:** Network File System, which lets the target mount a host directory over Ethernet during development.

> **What:** a board port as an integration problem. A custom PCB or MINI variant changes assumptions shared by **U-Boot configuration**, **kernel Device Tree and drivers**, **rootfs contents**, and **image generation**. This chapter follows those dependencies and shows where each layer owns a decision.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **U-Boot:** the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** Each Cookbook chapter covered one piece. A board port is where those pieces have to agree: pin multiplexing (Ch 5), DDR initialization (Ch 14), U-Boot policy (Ch 22), kernel DT (Ch 27), and the peripherals actually fitted. Understanding that agreement makes generated code and configuration easier to assess. A successful build alone does not establish a working board.
> **DDR:** external DRAM that must be configured and trained before most software can run from it.
>
> **Focus:** **dependencies determine the bring-up order**. A console makes early failures observable, DDR supports larger images, and storage or networking supplies later boot inputs. Peripheral integration comes after those foundations. Recovery must remain independent of the candidate being evaluated. The order below is a design example, not a required reader project.
> **MCU bridge:** Think of JTAG like SWD debugging on Cortex-M: halt, read registers, set breakpoints. The Cortex-A path adds MMU state, privilege modes, and more complex reset behavior.
> **JTAG:** the hardware debug scan chain used to halt, inspect, and single-step CPUs.

## 121.1  Scope, what to port

The port spans several contracts:

| Boundary | Design responsibility | Evidence needed separately |
|---|---|---|
| Early hardware | Power, reset, pin routing and DDR assumptions | Measurements and memory qualification on the fitted board |
| Boot inputs | Storage layout, image selection and recovery | Actual loader behavior and artifact integrity |
| Peripheral integration | Supplies, clocks, buses, driver binding and user interface | End-to-end behavior, including failure and removal |
| Build and release | Pinned inputs, configuration and artifact provenance | Repeatable output and a qualified release candidate |

An existing-driver chip such as an AT24 EEPROM or DS3231 RTC keeps the software contract relatively small. Camera, graphics and DMA-heavy additions widen the dependency set. That difference affects integration risk, not which assignment a reader must complete.
> **DMA:** Direct Memory Access. Hardware moves data to or from memory without the CPU copying each byte.

## 121.2  Hardware variants, what counts as "custom"

Three cases change different parts of the contract:

<span id="option-a-pretend-port-the-point-atom-mini"></span>
### Case A, Software policy on unchanged MINI hardware

The physical board can stay unchanged while product policy differs:
- Different model string in U-Boot (board name in `bdinfo`)
- Different default hostname in Linux
- Custom default `bootargs`

These changes affect identity and boot policy, not the power tree or DDR wiring. Adding an external device moves the design into the next case.

<span id="option-b-rework-the-point-atom-mini"></span>
### Case B, A MINI variant with changed connections

Possible additions or changes include:
- Replace the WiFi module (if any) with a different one
- Add an external RTC chip + battery
- Add an SPI Ethernet (DM9051 from Ch 115)
- Mod the LCD interface

Changed wiring introduces new supply, pin-mux and Device Tree dependencies. Each addition needs its actual module specification and connection review. This is a design comparison, not a soldering instruction.

<span id="option-c-full-custom-pcb"></span>
### Case C, A full custom PCB

A custom board can change the early boot assumptions themselves:
- Different RAM (DDR3 256 MB vs the MINI's 512 MB? Different timing).
- Different PMIC.
> **MCU bridge:** Think of a PMIC like a programmable power-tree supervisor: it replaces discrete enables and LDO assumptions with sequenced rails the kernel can model.
> **PMIC:** Power Management IC, a chip that sequences and regulates the board's voltage rails.
- Different boot media (eMMC, QSPI flash instead of SD).
- Different I/O complement (your specific application, sensors, motors, displays).
- Different connectors / form factor.

The port must now account for hardware design and qualification as well as software integration. A similar SoC does not justify reusing another board's DDR, power or reset values. Detailed PCB design is outside this chapter's scope.

<span id="the-bring-up-checklist"></span>
## 121.3  Bring-up as a dependency model

Power and reset must be valid before a ROM observation is meaningful. The ROM then needs the correct boot source and image format. Early software needs a usable stack, console and memory arrangement before later storage, network or peripheral behavior can be interpreted.

Those dependencies do not create a universal pass/fail list. Rail limits come from the actual components and board specification. DDR evidence depends on geometry, timings, operating conditions and the chosen test coverage, not a fixed one-hour run. Destructive memory tests must not overwrite the running image or its data.

Console output also depends on the selected image: the MINI ROM+DCD path in Chapters 19 and 22 has no SPL banner. Similarly, a PHY response, driver probe or bus acknowledgement establishes only part of an interface. The application path and recovery behavior remain separate.

The useful design model is a chain of prerequisites with an observation at each boundary. A symptom narrows the search, but rarely identifies one failed layer by itself.

<span id="u-boot-port-the-steps"></span>
## 121.4  U-Boot's board contract

The bootloader does not discover every detail of a new PCB. Its configuration, board code and hardware description must agree with the fitted design. Chapters 19 and 22 distinguish the vendor MINI reference from the modern MINI candidate. An EVK configuration is a comparison, not a substitute for either.

<span id="fork-the-reference-defconfig"></span>
### 121.4.1  Reference selection

A reference is useful when its assumptions are visible: source revision, CPU, memory geometry, power/reset arrangement, boot media and supported peripherals. A similar processor name is only the beginning of that comparison. Keep inherited features disabled until their connections and supporting drivers are understood.

<span id="create-board-files"></span>
### 121.4.2  Board integration

Build-system entries select which board implementation exists in the resulting image. Board hooks then own operations that cannot be expressed by generic drivers alone. The important design question is which component owns each initialization step, not how many files were copied.

<span id="adapt-the-dts"></span>
### 121.4.3  Hardware description

The U-Boot hardware description must match the services needed before Linux: console, boot storage and any qualified policy inputs. Linux can need additional devices later. The two descriptions have different consumers, but cannot disagree about the physical wiring.

<span id="ddr-config-if-you-changed-ram-chip"></span>
### 121.4.4  DDR handoff

Changed RAM changes the memory contract: geometry, clock, timing, pad settings and calibration belong to the fitted part and board. Chapter 14 explains those relationships. A tool's generated values still need a documented input set and qualification.

The MINI ROM+DCD paths in Chapters 19 and 22 prepare DDR before U-Boot executes. An SPL-based platform assigns that job differently. These are alternative ownership models, not interchangeable places to paste a calibration table.

<span id="build-and-flash"></span>
### 121.4.5  Candidate acceptance and recovery

Compilation establishes a software milestone. Image inspection establishes format and placement. A UART banner establishes observed execution. None represents a fixed percentage of completed bring-up.

Persistent installation is a separate acceptance decision. It needs an identified medium, a verified image layout, safe power conditions and a board-matched recovery path. Building a candidate must not automatically authorize writing it to a disk.

<span id="kernel-dt-port"></span>
## 121.5  Kernel and boot-input agreement

Linux receives a kernel image, a hardware description and boot arguments. The root filesystem supplies the first process and its dependencies. A board port succeeds only when those independently produced inputs agree.

<span id="fork-the-evk-dt"></span>
### 121.5.1  Describe the fitted hardware

A MINI variant starts from a description whose routing matches that variant. Additions and omissions follow the schematic, not the peripherals on an EVK. Pin control, clocks, supplies, reset lines and interrupt wiring form one connected device path.

<span id="add-to-makefile"></span>
### 121.5.2  Own the board artifact

Including a DTS in the build produces an artifact; it does not ensure that the bootloader selects that artifact. Model and compatible strings identify a design, while the release configuration owns which DTB is delivered and loaded.

<span id="build-kernel-dt"></span>
### 121.5.3  Keep runtime dependencies matched

The kernel configuration decides which drivers exist and whether they are built in or loaded as modules. Rootfs assembly must include matching modules, firmware and userspace dependencies. A stale DTB or module tree can invalidate an otherwise successful kernel build.

<span id="boot-from-u-boot"></span>
### 121.5.4  Define the handoff

Load addresses must respect the selected image format and memory layout. Console selection must match the supported UART, and the root argument must identify the intended filesystem. Diagnostic output narrows the failure search; silence alone does not identify a bad DTB, DDR setting or console.

## 121.6  Custom peripheral, adding an external RTC

An attached DS3231 illustrates a small integration boundary. It is an optional device, not a stock MINI feature. Its supply, logic levels, pull-ups, backup circuit and chosen bus need a connection design before software description.

### 121.6.1  DT addition

Inside a qualified I2C controller node, a minimal child fragment can express the device's identity and bus address:

```dts
rtc@68 {
    compatible = "maxim,ds3231";
    reg = <0x68>;
};
```

This is not a complete board DTS. It omits the parent controller, pin control and board-specific resources. The [Linux v6.6 RTC binding](https://github.com/torvalds/linux/blob/v6.6/Documentation/devicetree/bindings/rtc/rtc-ds1307.yaml) defines the node's properties. An interrupt or wakeup property needs actual wiring and a supported wake path; neither should be copied from another board.

<span id="enable-kernel-driver"></span>
### 121.6.2  Driver selection

The compatible string connects the node to a supported driver. The kernel configuration determines whether that implementation is present. Device Tree does not supply a missing driver or implement the RTC protocol.

<span id="verify"></span>
### 121.6.3  Observation boundaries

Driver binding, readable time, valid backup state, alarm behavior and system-clock policy are different observations. Registration as an RTC device does not qualify all of them. Device numbering also does not identify which RTC the product should trust at startup.

<span id="the-reproducible-build-script"></span>
## 121.7  Reproducible artifacts, separate deployment

A build entry point is useful when it exposes its inputs and produces reviewable artifacts. Combining source checkout, compilation and destructive disk writes in one script hides an important approval boundary.

| Layer | Inputs it owns | Output consumed elsewhere |
|---|---|---|
| Bootloader build | Pinned source, board configuration, toolchain and image format | Loader candidate |
| Kernel build | Pinned source, kernel configuration and board description | Kernel, DTB and matching modules |
| Rootfs build | Package selection, libraries, firmware and service policy | Root tree and image |
| Image assembly | Partition layout, placement rules and artifact identities | Candidate media image |
| Deployment | Identified physical medium and recovery policy | Installed candidate |

Reproducibility needs controlled sources, tools, configuration and other build inputs. A script name is not that evidence. The two project-local Arm toolchains and explicit environment selection remain the policy from Chapter 3.

Image assembly can produce a file for inspection without touching a device. Deployment is intentionally separate: a correct build can still be written to the wrong medium, at the wrong offset, or before recovery is available.

<span id="common-failures-recovery"></span>
## 121.8  Failure boundaries and recovery

<span id="u-boot-prints-dcd-garbage-then-dies"></span>
### No usable early output

Power/reset, boot selection, image format, memory initialization and console configuration are possible boundaries. The ROM's DCD is a register-write structure, not a producer of a UART transcript. Preserve observations rather than calling every garbled character a DDR diagnosis.

<span id="u-boot-prompt-but-kernel-hangs-after-uncompressing-linux"></span>
### U-Boot runs, but Linux does not reach userspace

A prompt narrows the search without qualifying all RAM. The next boundary includes kernel format, load ranges, DTB, handoff state and console selection. Later failures add rootfs access, PID 1 and its runtime dependencies.

<span id="kernel-boots-but-no-ethernet"></span>
### Linux runs, but a peripheral path fails

A peripheral depends on routing, power, clocks, reset, controller support and driver binding. For MINI Ethernet, retain the actual carrier/PHY qualification limits from Part III rather than treating EVK networking as board evidence.

<span id="driver-doesnt-probe"></span>
### Description and implementation do not meet

A missing node, disabled node, unmatched compatible or absent driver can prevent binding. A driver may also defer while waiting for a supply or clock provider. A log entry is evidence to interpret, not a universal diagnosis.

<span id="worked-once-now-bricked"></span>
### A candidate cannot start

Recovery must not depend on the failing candidate executing correctly. Chapter 8 distinguishes ROM USB access from later U-Boot services. The recovery image and media layout must match the board; a stock EVK card is not automatically a MINI fallback.


(1219-lab)=
## 121.9  Key Notes

- A board port connects fitted hardware to several software descriptions. Power and reset behavior, early DDR setup, U-Boot configuration, kernel DT, and rootfs contents have distinct owners.
- The dependency chain starts before Linux. Unusable rails, reset, or DDR can prevent any kernel diagnostic, while a serial banner establishes only partial progress.
- Device Tree describes wiring and resources, while drivers implement behavior. A matching `compatible` string alone does not establish correct clocks, supplies, interrupts, or pin mux.
- The external RTC case separates board description, driver selection, and userspace access. Its presence and wiring are additions, not stock MINI assumptions.
- Reproducible image construction needs pinned inputs and matching modules and libraries. Writing an image to a particular medium is a separate, destructive deployment operation.
- Recovery depends on a board-specific known-good image and accessible boot path. Compilation and illustrative output do not qualify a custom board or the MINI.

<span id="reflection"></span>
## 121.10  Design history

A useful bring-up record connects a decision to its assumptions, observed evidence and remaining uncertainty. It explains why a clock, memory setting or recovery policy was accepted, not merely which command was typed.

That history lets a later engineer distinguish a deliberate constraint from an inherited default. A compiler upgrade, changed component or new carrier revision can then reopen the relevant decision without repeating every earlier investigation.

## 121.11  Pitfalls

- **Copying a reference without its assumptions.** Configuration and DTS reuse need a hardware and source-version comparison.
- **Treating one observation as full qualification.** A banner, probe message or successful build establishes only a particular milestone.
- **Hiding deployment inside the build.** Artifact production and permission to write a physical medium are separate responsibilities.
- **Reusing DDR values after hardware changes.** Timing, geometry and calibration need evidence for the fitted design and operating conditions.
- **Shipping mismatched artifacts.** The kernel, DTB, modules, firmware and rootfs must belong to a consistent release.
- **Depending on the candidate for recovery.** Keep a documented board-specific route that remains usable when normal boot fails.

## 121.12  Going deeper

- Chapter 14: DDR timing, initialization ownership and qualification limits.
- Chapters 19 and 22: vendor reference versus modern MINI candidate.
- Chapters 25-27: kernel artifacts, boot inputs and Device Tree.
- Chapters 31-35: init, libraries and rootfs construction.
- Chapter 121A: build evidence and controlled hardware integration in CI.
- Chapter 122A: preserving hardware contracts during BSP migration.
- Chapter 120A: upstream maintenance and review.

---

> Next chapter: **Chapter 121A: CI/CD for embedded Linux**.
