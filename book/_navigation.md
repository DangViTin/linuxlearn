<!-- Included by Chapter 1; absolute document paths keep navigation independent of its directory. -->

```{toctree}
:hidden:
:caption: Part I — Foundations
:maxdepth: 2

/part1-foundations/ch02-what-is-embedded-linux
/part1-foundations/ch03-host-setup
/part1-foundations/ch04-armv7a-for-mcu-engineer
/part1-foundations/ch05-imx6ull-tour
/part1-foundations/ch06-toolchain
/part1-foundations/ch07-boot-rom-ivt-dcd
/part1-foundations/ch08-board-bring-up
```

```{toctree}
:hidden:
:caption: Part II — Bare-metal i.MX6ULL
:maxdepth: 2

/part2-baremetal/ch09-asm-led
/part2-baremetal/ch10-c-startup-linker
/part2-baremetal/ch11-ivt-dcd-image
/part2-baremetal/ch12-uart-printf
/part2-baremetal/ch13-ccm-clocks
/part2-baremetal/ch14-ddr3-init
/part2-baremetal/ch15-exceptions-gic
/part2-baremetal/ch16-timers
/part2-baremetal/ch17-mmu-caches
/part2-baremetal/ch18-bare-metal-peripherals
/part2-baremetal/ch18A-project-organization
/part2-baremetal/ch18B-button-beep
/part2-baremetal/ch18C-baremetal-rtc
```

```{toctree}
:hidden:
:caption: Part III — U-Boot, deeply
:maxdepth: 2

/part3-uboot/ch19-uboot-from-source
/part3-uboot/ch20-uboot-spl
/part3-uboot/ch21-uboot-internals
/part3-uboot/ch22-uboot-board-port
/part3-uboot/ch23-bootcmd-bootargs-fit
/part3-uboot/ch24-workflows-tftp-nfs-usb
/part3-uboot/ch24A-uboot-new-soc-from-scratch
/part3-uboot/ch24B-uboot-board-policy-i2c-gpio
/part3-uboot/ch24C-uboot-ethernet-fallback-boot
/part3-uboot/ch24D-uboot-board-identity-variants
/part3-uboot/ch24E-multi-variant-fit
/part3-uboot/ch24F-uboot-bootcount-watchdog-rollback
/part3-uboot/ch24G-uboot-factory-recovery-usb
/part3-uboot/ch24H-uboot-pmic-power-policy
/part3-uboot/ch24I-uboot-display-splash
/part3-uboot/ch24J-uboot-spi-lcd-i2c-oled
```

```{toctree}
:hidden:
:caption: Part IV — The Kernel
:maxdepth: 2

/part4-kernel/ch25-building-mainline-linux
/part4-kernel/ch26-booting-kernel-from-uboot
/part4-kernel/ch26A-kernel-boot-failure-playbook
/part4-kernel/ch27-device-tree
/part4-kernel/ch27A-dt-bindings-yaml
/part4-kernel/ch27B-custom-board-device-tree
/part4-kernel/ch28-kernel-startup-traced
/part4-kernel/ch29-initramfs-from-scratch
/part4-kernel/ch29A-initramfs-recovery-system
/part4-kernel/ch30-kernel-configuration
/part4-kernel/ch30A-kernel-lifecycle
/part4-kernel/ch30B-product-kernel-configs
```

```{toctree}
:hidden:
:caption: Part V — Root filesystem & user space
:maxdepth: 2

/part5-rootfs/ch31-rootfs-by-hand
/part5-rootfs/ch32-proc-sys-devtmpfs
/part5-rootfs/ch33-init-systems
/part5-rootfs/ch34-libc-dynamic-linking
/part5-rootfs/ch35-buildroot
/part5-rootfs/ch35D-bootable-sd-emmc-image
/part5-rootfs/ch35I-boot-from-spi-nor-flash
/part5-rootfs/ch35E-buildroot-product-board-directory
/part5-rootfs/ch35A-ubuntu-base
/part5-rootfs/ch35F-application-as-service
/part5-rootfs/ch35G-network-time-logging
/part5-rootfs/ch35B-readonly-rootfs-overlayfs
/part5-rootfs/ch35H-rootfs-security-basics
/part5-rootfs/ch35C-containers-on-embedded
/part5-rootfs/appendix-tooling
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (foundations)
:maxdepth: 2

/part6-drivers/ch36-hello-lkm
/part6-drivers/ch37-character-driver
/part6-drivers/ch38-auto-device-nodes
/part6-drivers/ch39-platform-driver-dt
/part6-drivers/ch40-misc-framework
/part6-drivers/ch41-concurrency
/part6-drivers/ch42-sleeping-waiting-polling
/part6-drivers/ch43-interrupts
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (common subsystems)
:maxdepth: 2

/part6-drivers/ch44-gpio-subsystem
/part6-drivers/ch45-input-subsystem
/part6-drivers/ch46-i2c-drivers
/part6-drivers/ch47-spi-drivers
/part6-drivers/ch48-pwm-rtc
/part6-drivers/ch49-iio-subsystem
/part6-drivers/ch50-regmap
```

```{toctree}
:hidden:
:caption: Part VI — Driver development (advanced + insertions)
:maxdepth: 2

/part6-drivers/ch51-dma
/part6-drivers/ch51A-watchdog
/part6-drivers/ch51B-power-management
/part6-drivers/ch52-network-fec
/part6-drivers/ch52A-preempt-rt
/part6-drivers/ch53-sound-alsa-asoc
/part6-drivers/ch54-lcd-drm
/part6-drivers/ch54A-mtd-ubi
/part6-drivers/ch54B-v4l2-gstreamer
/part6-drivers/ch55-usb-gadget
/part6-drivers/ch55A-kernel-timers
/part6-drivers/ch55B-async-sigio
/part6-drivers/ch55C-can-flexcan
/part6-drivers/ch55D-block-device
/part6-drivers/ch55E-wifi
/part6-drivers/ch55F-cellular
/part6-drivers/ch55G-multi-touch
/part6-drivers/ch55H-hdmi-bridge
/part6-drivers/ch55I-rust-for-linux
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Storage)
:maxdepth: 2

/part7-cookbook/ch64-qspi-flash
/part7-cookbook/ch65-eeprom
/part7-cookbook/ch66-sd-emmc
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Environmental sensors)
:maxdepth: 2

/part7-cookbook/ch67-temp-humid-pressure
/part7-cookbook/ch68-light-color
/part7-cookbook/ch69-air-quality
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Motion sensors)
:maxdepth: 2

/part7-cookbook/ch70-i2c-imus
/part7-cookbook/ch71-spi-imus
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Position & distance)
:maxdepth: 2

/part7-cookbook/ch72-distance
/part7-cookbook/ch73-magnetometer
/part7-cookbook/ch74-hall-rotary
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Power & current)
:maxdepth: 2

/part7-cookbook/ch75-current-monitoring
/part7-cookbook/ch76-battery
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Specialty sensors)
:maxdepth: 2

/part7-cookbook/ch77-one-wire
/part7-cookbook/ch78-mems-mics
/part7-cookbook/ch79-health-sensors
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (ADC / DAC / clocks)
:maxdepth: 2

/part7-cookbook/ch80-external-adc
/part7-cookbook/ch81-dac-clockgen
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Displays)
:maxdepth: 2

/part7-cookbook/ch82-rgb-lcd
/part7-cookbook/ch83-spi-lcd
/part7-cookbook/ch84-qspi-lcd
/part7-cookbook/ch85-oled-epaper
/part7-cookbook/ch86-touch-input
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Cameras)
:maxdepth: 2

/part7-cookbook/ch87-csi-cameras
/part7-cookbook/ch88-usb-uvc
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Audio)
:maxdepth: 2

/part7-cookbook/ch89-audio-codecs
/part7-cookbook/ch90-class-d-amps
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (WiFi)
:maxdepth: 2

/part7-cookbook/ch91-sdio-wifi
/part7-cookbook/ch92-usb-wifi
/part7-cookbook/ch93-hosted-wifi
/part7-cookbook/ch94-wifi-bt-combo
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Bluetooth)
:maxdepth: 2

/part7-cookbook/ch95-hci-bluetooth
/part7-cookbook/ch96-at-ble
/part7-cookbook/ch97-ble-mesh
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Long-range & specialty wireless)
:maxdepth: 2

/part7-cookbook/ch98-lora
/part7-cookbook/ch99-sub-ghz-proprietary
/part7-cookbook/ch100-zigbee-thread
/part7-cookbook/ch101-uwb-ranging
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Cellular)
:maxdepth: 2

/part7-cookbook/ch102-usb-lte
/part7-cookbook/ch103-uart-modems
/part7-cookbook/ch104-nbiot
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Identification)
:maxdepth: 2

/part7-cookbook/ch105-rfid-nfc
/part7-cookbook/ch106-fingerprint
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Positioning)
:maxdepth: 2

/part7-cookbook/ch107-gps-pps
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Industrial buses)
:maxdepth: 2

/part7-cookbook/ch108-rs485-modbus
/part7-cookbook/ch109-lin-bus
/part7-cookbook/ch110-can-deep-dive
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Motors & encoders)
:maxdepth: 2

/part7-cookbook/ch111-quadrature-encoders
/part7-cookbook/ch112-motor-drivers
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Indicators & actuators)
:maxdepth: 2

/part7-cookbook/ch113-smart-leds
/part7-cookbook/ch114-beepers-relays
```

```{toctree}
:hidden:
:caption: Part VII — Device cookbook (Network & system power)
:maxdepth: 2

/part7-cookbook/ch115-dual-fec-eth
/part7-cookbook/ch116-pmic
/part7-cookbook/ch117-external-rtc
```

```{toctree}
:hidden:
:caption: Part VIII — Debug, production, advanced
:maxdepth: 2

/part8-debug/ch118-jtag-openocd-gdb
/part8-debug/ch119-kernel-debug-no-jtag
/part8-debug/ch120-userspace-debug
/part8-debug/ch120A-mainline-patch-submission
/part8-debug/ch121-custom-board-port
/part8-debug/ch121A-cicd-embedded
/part8-debug/ch122-cross-toolchain
/part8-debug/ch122A-bsp-mainline-migration
/part8-debug/ch123-yocto-vs-buildroot
/part8-debug/ch123A-yocto-layer-dev
/part8-debug/ch124-secure-boot-optee
/part8-debug/ch125-field-updates
/part8-debug/ch125A-vscode-gdbserver
/part8-debug/ch126-closing
```

```{toctree}
:hidden:
:caption: Part IX — Applied virtualization
:maxdepth: 2

/part9-virtualization/ch127-why-embedded-hypervisors
/part9-virtualization/ch128-qemu-virtual-hardware-lab
/part9-virtualization/ch129-tiny-linux-in-qemu
/part9-virtualization/ch130-uboot-in-qemu
/part9-virtualization/ch131-hyp-stage2-virtual-interrupts
/part9-virtualization/ch132-xen-in-qemu
/part9-virtualization/ch133-first-domu-linux
/part9-virtualization/ch134-xen-on-imx6ull
/part9-virtualization/ch135-domu-on-imx6ull
/part9-virtualization/ch136-devices-memory-dma
/part9-virtualization/ch137-jailhouse-in-qemu-arm64
/part9-virtualization/ch138-zephyr-baremetal-inmate
/part9-virtualization/ch139-stm32mp1-linux-rtos
```

```{toctree}
:hidden:
:caption: Front matter
:maxdepth: 1

Table of contents </toc>
Status </status>
```
