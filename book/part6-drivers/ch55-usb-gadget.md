---
chapter: 55
title: USB gadget
part: VI — Driver development
estimated_pages: 16
status: draft
---

# Chapter 55 — USB gadget

> **What:** the **USB gadget** framework — turning the i.MX6ULL's USB OTG controller into a USB *device* (instead of a host). The mainline **ConfigFS** gadget interface lets user-space compose USB devices from "functions" (mass storage, serial, Ethernet, HID) without writing kernel code.
>
> **Why:** USB gadget runs on Android phones, Raspberry Pi Zero in USB-Pi mode, smart meters that expose data over USB-serial, and many other devices. For embedded products: USB-as-device is how your board talks to a PC for debug, firmware update, or as a remote sensor.
>
> **Focus:** **functions composed into a configuration**. A gadget has one *configuration* with one or more *functions*. ConfigFS exposes this as a filesystem: `mkdir` a function, `echo` settings into its files, then bind to a UDC. No kernel code.


## 55.1  USB roles on i.MX6ULL

i.MX6ULL has 2× USB OTG controllers. Each can be:
- **Host** — Linux runs the USB host stack. devices plug into it.
- **Device** (gadget) — the SoC *is* a USB device that gets plugged into something else.
- **OTG** — auto-detect host/device via the ID pin.

Configure in DT:

```dts
&usbotg1 {
    dr_mode = "peripheral";        /* device-only */
    /* or "host", or "otg" */
    vbus-supply = <&reg_usb_otg1_vbus>;
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_usbotg1>;
    status = "okay";
};
```

For "otg" mode you also wire the ID pin to a GPIO.
MCU bridge: Think of Linux GPIO like the same pin set/reset block you used on STM32, but accessed through a kernel subsystem that owns numbering, direction, interrupts, and user-space exposure.
**GPIO** - General-Purpose Input/Output, a pin controlled as a digital input, output, or interrupt source.

## 55.2  ConfigFS gadget overview

ConfigFS is the current way to compose a USB gadget. From userspace:

```sh
# Mount configfs
mount -t configfs none /sys/kernel/config

# Create gadget
cd /sys/kernel/config/usb_gadget
mkdir mygadget
cd mygadget

# Device descriptor
echo 0x1d6b > idVendor      # Linux Foundation
echo 0x0104 > idProduct     # Multifunction Composite Gadget
echo 0x0100 > bcdDevice
echo 0x0200 > bcdUSB        # USB 2.0

# Strings
mkdir strings/0x409          # English (US)
echo "Linuxlearn" > strings/0x409/manufacturer
echo "MyGadget"   > strings/0x409/product
echo "ABCD1234"   > strings/0x409/serialnumber

# Functions: a serial port, a network interface, mass storage
mkdir functions/acm.GS0
mkdir functions/ecm.usb0
mkdir functions/mass_storage.0
echo /dev/loop0 > functions/mass_storage.0/lun.0/file

# Configuration
mkdir configs/c.1
ln -s functions/acm.GS0          configs/c.1/
ln -s functions/ecm.usb0         configs/c.1/
ln -s functions/mass_storage.0   configs/c.1/
mkdir configs/c.1/strings/0x409
echo "Conf 1" > configs/c.1/strings/0x409/configuration
echo 250 > configs/c.1/MaxPower

# Bind to a UDC (USB Device Controller)
ls /sys/class/udc/                                  # find the udc name
echo 2184000.usb > UDC
```

The last line binds the gadget by writing the UDC name. Plug a USB cable from the i.MX6ULL's OTG port into a PC. The PC sees a composite USB device with serial, Ethernet, and mass storage.

## 55.3  Common function types

| Function | Description | Linux usage |
|----------|-------------|-------------|
| `acm` | CDC-ACM serial port | `/dev/ttyACM0` on host |
| `ecm` | CDC Ethernet | `usb0` network interface |
| `ncm` | NCM Ethernet (faster) | same |
| `rndis` | RNDIS Ethernet (Windows-compatible) | same |
| `mass_storage` | USB mass storage | block device on host |
| `hid` | HID device (keyboard, mouse, custom) | input device on host |
| `uvc` | UVC webcam | webcam on host |
| `midi` | USB MIDI | midi device on host |

Each is a kernel module: `g_acm.ko`, `usb_f_ecm.ko`, etc. Built-in or modular.

## 55.4  Real-world examples

### USB-serial console for a headless device

```sh
mkdir -p /sys/kernel/config/usb_gadget/console
cd $_
echo 0x1d6b > idVendor
echo 0x0104 > idProduct
mkdir strings/0x409
echo "Linuxlearn" > strings/0x409/manufacturer
echo "Headless"  > strings/0x409/product
mkdir functions/acm.0
mkdir configs/c.1
ln -s functions/acm.0 configs/c.1/
echo 2184000.usb > UDC
```

Now from the host PC: `/dev/ttyACM0` is the i.MX6ULL's UART/console.

### USB Ethernet for SSH

```sh
mkdir -p /sys/kernel/config/usb_gadget/ssh
cd $_
echo 0x1d6b > idVendor; echo 0x0104 > idProduct
mkdir functions/ecm.usb0
echo aa:bb:cc:dd:ee:01 > functions/ecm.usb0/host_addr
echo aa:bb:cc:dd:ee:02 > functions/ecm.usb0/dev_addr
mkdir configs/c.1; ln -s functions/ecm.usb0 configs/c.1/
echo 2184000.usb > UDC
```

`usb0` appears on both sides. Assign IPs:

```sh
# On i.MX6ULL:
ip addr add 192.168.10.2/24 dev usb0
ip link set usb0 up

# On host PC:
ip addr add 192.168.10.1/24 dev usb0
ip link set usb0 up
ssh root@192.168.10.2
```

### USB mass storage from a file

```sh
dd if=/dev/zero of=/tmp/disk.img bs=1M count=64
mkfs.vfat /tmp/disk.img
losetup /dev/loop0 /tmp/disk.img

mkdir -p /sys/kernel/config/usb_gadget/ms
cd $_
echo 0x1d6b > idVendor; echo 0x0104 > idProduct
mkdir functions/mass_storage.0
echo /tmp/disk.img > functions/mass_storage.0/lun.0/file
mkdir configs/c.1; ln -s functions/mass_storage.0 configs/c.1/
echo 2184000.usb > UDC
```

The host PC sees a 64 MB USB stick.

## 55.5  Writing a custom function

For specialised use cases (e.g., a custom protocol over USB), you can write a kernel function driver. But before doing so, check whether **FunctionFS** (a userspace-driven generic function) fits your needs. With FunctionFS, your gadget function lives in user space — the kernel just relays bytes between endpoints and your daemon. Much less work than a kernel function.

## 55.6  Lab

1. **Compose a USB serial gadget.** Use ConfigFS as in §55.4. Plug into a host PC, see `/dev/ttyACM0`.
2. **USB Ethernet over OTG.** Set up `ecm` function, assign IPs both sides, SSH into the i.MX6ULL.
3. **Mass storage from a backing file.** Expose a virtual disk. mount it on the host. copy files.
4. **HID keyboard.** Use `g_hid` to make the i.MX6ULL appear as a USB keyboard. "type" characters by writing report descriptors.
5. **Hot re-bind.** Write to `UDC` with empty string to disconnect. then re-bind. Useful for changing config without reboot.
6. **Composite gadget.** Stack ACM + ECM + mass storage in one configuration. verify all three function on the host.

## 55.7  Pitfalls

- **Forgetting `vbus-supply`.** USB device mode still needs VBUS sensing. Without it, the controller never detects a "plugged" event.
- **`dr_mode = "host"` when you want device.** Symptom: nothing plugs in on the host. Always check.
- **Wrong VID/PID.** Windows binds drivers based on these. Wrong values → host loads wrong driver → device fails to enumerate.
- **`mass_storage` backing file is too small / wrong format.** Host complains about corrupted filesystem.
- **Two gadgets bound to one UDC.** Only one bind per UDC at a time. Disconnect first.
- **ACM not appearing on Windows.** Windows needs a `.inf` driver file before it will bind to CDC-ACM. Linux/macOS hosts are fine.

## 55.8  Going deeper

- **`Documentation/usb/gadget_configfs.rst`** — the canonical ConfigFS gadget doc.
- **`drivers/usb/gadget/`** — gadget framework and functions.
- **`drivers/usb/gadget/function/`** — individual function drivers (one per `.c` file).
- **`Documentation/usb/functionfs.rst`** — FunctionFS for user-space-driven gadgets.
- **`Documentation/devicetree/bindings/usb/`** — USB controller bindings.

> Next chapter: **Chapter 55A — Kernel timers + hrtimers.** Beyond `mdelay` / `msleep`, the kernel offers precise timers for scheduling delayed work and periodic actions.
