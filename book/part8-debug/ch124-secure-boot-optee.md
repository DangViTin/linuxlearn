---
chapter: 124
title: Secure boot (HAB) and OP-TEE
part: VIII — Debug, production, advanced
estimated_pages: 26
status: draft
---

# Chapter 124 — Secure boot (HAB) and OP-TEE

> **Lab vs production:** Do not burn fuses, enroll production keys, or sign release images while following the lab.
> Use throwaway keys and back up the unsigned image plus the key directory before testing irreversible security flows.


> **What:** **NXP HAB (High Assurance Boot)** — the SoC-enforced chain-of-trust that ensures only signed bootloaders/kernels run on production i.MX devices. Plus **TrustZone** and **OP-TEE** — the ARM-architectural Secure World and the most-used open-source TEE (Trusted Execution Environment). We walk: the cryptographic chain ROM → SRK fuses → CSF → signed U-Boot → signed kernel → dm-verity rootfs. NXP's **CST (Code Signing Tool)** for producing CSF files. The *key ceremony* (how to generate, store, and rotate signing keys). TrustZone primer (monitor mode, SMC calls, world switch). OP-TEE basics (Trusted Application lifecycle, REE↔TEE communication, TA development).
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
> **rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.
> **U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
>
> **Why:** verified boot is needed for any product handling user data, payment credentials, certificate-based identity, or DRM. Without it, an attacker with physical access can replace U-Boot, boot a custom kernel that bypasses authentication, or extract storage encryption keys. With HAB plus dm-verity, the device resists most physical-access attacks. Silicon-level attacks (decap, side-channel, fault injection) remain possible but require expensive equipment. OP-TEE adds a runtime-isolated execution domain — Secure World keys, crypto operations, attestation primitives are inaccessible even to a fully-compromised Linux kernel.
>
> **Focus:** the chain works like this:
> 1. The ROM checks U-Boot's signature against the SRK hash in eFuses.
> 2. Verified U-Boot checks the kernel and DT signature.
> 3. The verified kernel mounts a dm-verity'd rootfs whose hash matches.
> 4. User apps can use OP-TEE to access secrets that no part of Linux can read.
>
> Break any link and all later links lose meaning.
>
> Key management is the part that bites: if you lose the private key you brick the fleet. If you expose it you hand attackers full control. This chapter is short on the easy bits and long on the parts you'll regret skipping.
>
> **Tooling.** **Host:** `openssl` (preinstalled), NXP's **CST** (Code Signing Tool — downloaded from NXP after registration, non-redistributable). **Target:** OP-TEE client (`tee-supplicant`, `libteec`) — build from `OP-TEE/optee_os` + `OP-TEE/optee_client`, or use Buildroot's `BR2_PACKAGE_OPTEE_CLIENT=y`. Full reference: [Userspace tooling appendix](../part5-rootfs/appendix-tooling.md).
> **Buildroot** - a configuration-driven build system that produces a complete root filesystem and related images.


## 124.1  The threat model

What HAB + dm-verity defends against:
- **Boot-time tampering**: attacker replaces U-Boot on SD with a modified copy. ROM checks the signature. fails. refuses to boot.
- **OS modification**: attacker mounts the SD on their PC and edits `/etc/passwd`. dm-verity detects the hash mismatch. mount fails. Linux refuses to boot.
- **Kernel module injection**: attacker installs a rootkit `.ko`. Linux's `module.sig_enforce` (paired with a hash in initramfs) rejects unsigned modules.
- **Runtime malware**: attacker exploits a Linux vulnerability. runs code in Normal World. OP-TEE's secure-world keys remain inaccessible.

What it *doesn't* defend against:
- **Silicon-level attacks**: chip decapping, side-channel power analysis, fault injection. Requires expensive equipment and is detected by audit.
- **JTAG**: must be disabled by fuse in production.
> **MCU bridge:** Think of JTAG like SWD debugging on Cortex-M: halt, read registers, set breakpoints. The Cortex-A path adds MMU state, privilege modes, and more complex reset behavior.
> **MCU bridge:** Think of the MMU as a hardware address translator in front of every load/store. Cortex-M usually runs physical addresses directly. Linux relies on virtual addresses and page permissions.
**JTAG** - the hardware debug scan chain used to halt, inspect, and single-step CPUs.
- **Pre-fuse-blown attacker**: someone with the device before it leaves the factory. Manufacturing security is a separate concern.
- **TEE compromise**: OP-TEE itself has bugs. Keep it updated.

## 124.2  i.MX HAB — the chain of trust

```
   Power on
        │
        ▼
   ROM verifies: U-Boot signature matches SRK in fuses?
        │ yes
        ▼
   U-Boot runs
        │
        ▼
   U-Boot verifies: FIT image (kernel + DT + initramfs) signed?
        │ yes
        ▼
   Kernel runs
        │
        ▼
   Kernel mounts rootfs with dm-verity: root hash matches kernel cmdline?
        │ yes
        ▼
   userspace
        │
        ▼
   Kernel module load: each .ko signed with key in keyring?
        │ yes
        ▼
   Daemons run
```

Each step refuses to proceed if signature fails. Fail-open is impossible — the SoC's mask ROM hardcodes this behavior.

### The crypto

- **SRK (Super Root Key)**: a 4096-bit RSA public key. The hash of the SRK is **blown into eFuses** during manufacturing.
- **CSF (Command Sequence File)**: a binary blob that points to the SRK, the actual signing key (CSK), the signature, and the regions of the image to verify.
- **CST (Code Signing Tool)**: NXP's tool that generates the CSF from your image + your keys.

For a single i.MX6ULL part: you have one set of SRK keys. You sign all your firmware with the corresponding CSK. The part trusts your firmware and nothing else.

## 124.3  Key ceremony — the most under-emphasized topic

Before any HAB, you generate **the keys**. This is a ritual, not a checkbox:

1. **Air-gapped machine**: never connected to the internet. A laptop in a safe.
2. **Generate root CA**: `openssl genrsa -aes256 -out ca.key 4096`. Password protect.
3. **Generate SRKs (× 4)**: NXP CST supports up to 4 SRKs (you can revoke individual ones). Generate all 4 on the air-gapped machine.
4. **Hash for fuse blow**: compute SHA-256 of SRK public key concatenation. This 256-bit hash goes into 8 OTP fuses.
5. **Backup**: SRK private keys go on (multiple) hardware tokens (Nitrokey HSM, YubiHSM). Store in different physical locations.
6. **Signing**: production signing happens on the air-gapped machine. signed binaries go out via USB stick.
7. **Rotation plan**: if SRK 1 is compromised, you can blow another fuse to revoke it. SRK 2 becomes active. **If all 4 are compromised, you must scrap the fleet** — the SoC will never trust new keys.

For prototyping: simpler procedure (keys on your laptop, no HSM). For production: take the ceremony seriously. If you lose the keys, you can't ship firmware updates. Whatever was last signed is what the fleet runs forever.

## 124.4  Producing a signed U-Boot

```sh
# 1. Generate keys (CST has a key-gen script)
cd cst-3.4.0/keys
./hab4_pki_tree.sh
# Answers:
#   key length: 4096
#   keys are signed: yes
#   serial number: random
#   key passphrase: <set one>

# This produces:
#   SRK_1_2_3_4_table.bin    (the SRK table U-Boot embeds)
#   SRK_1_2_3_4_fuse.bin     (the hash to blow into fuses)
#   crts/SRK1_sha256_4096_65537_v3_ca_crt.pem  (the SRK certs)
#   keys/SRK1_sha256_4096_65537_v3_ca_key.pem  (the SRK private keys)
#   crts/CSF1_1_sha256_4096_65537_v3_usr_crt.pem
#   keys/CSF1_1_sha256_4096_65537_v3_usr_key.pem

# 2. Build U-Boot with HAB support
cd u-boot
make CONFIG_SECURE_BOOT=y CONFIG_FIT_SIGNATURE=y CONFIG_HAB=y myboard_defconfig
make CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc)

# 3. Generate CSF (Command Sequence File)
# Use the helper script that comes with U-Boot or NXP's CST
cat > csf.txt <<EOF
[Header]
    Version = 4.3
    Hash Algorithm = sha256
    Engine Configuration = 0
    Certificate Format = X509
    Signature Format = CMS

[Install SRK]
    File = "crts/SRK_1_2_3_4_table.bin"
    Source index = 0

[Install CSFK]
    File = "crts/CSF1_1_sha256_4096_65537_v3_usr_crt.pem"

[Authenticate CSF]

[Install Key]
    Verification index = 0
    Target index = 2
    File = "crts/IMG1_1_sha256_4096_65537_v3_usr_crt.pem"

[Authenticate Data]
    Verification index = 2
    Blocks = 0x877FF400 0x00000000 0x00065F60 "u-boot-ivt.imx"
EOF

cst -i csf.txt -o csf.bin

# 4. Append CSF to U-Boot
cat u-boot.imx csf.bin > u-boot-signed.imx

# 5. Flash + verify
dd if=u-boot-signed.imx of=/dev/sdX bs=1k seek=1 conv=fsync
# Boot; in U-Boot:
hab_status
# No HAB Events Found!     <-- success
```

The hard part is *verifying* the CSF before fuse-blow. Once you blow the SRK fuse, an unsigned U-Boot will brick the part forever (well, recoverable via SDP if HAB hasn't been closed). Test with **HAB open** mode first (the SoC checks signatures and logs failures but still boots) until you're confident.

## 124.5  Closing HAB — the irreversible step

Once you're sure:

```
=> fuse prog 0 6 0x2                 # set HAB_TYPE = closed
=> reset
```

After reset: ROM refuses to boot any unsigned image. **This is irreversible**. The part will only run firmware signed by your SRK forever.

Production flow:
- All fuses blown at factory programming station.
- Devices that ship are HAB-closed.
- Devices for development have HAB open (separate part SKUs or marked units).

## 124.6  Signed FIT for kernel + DTB

After U-Boot is signed, sign the kernel-DTB-initramfs FIT image so U-Boot only boots a trusted kernel:
**FIT** - Flattened Image Tree, U-Boot's container format for kernels, DTBs, initramfs images, hashes, and signatures.

```sh
# .its file describing the FIT
cat > kernel.its <<EOF
/dts-v1/;
/ {
    description = "Kernel + DTB + ramdisk";
    #address-cells = <1>;
    images {
        kernel {
            description = "Linux kernel";
            data = /incbin/("zImage");
            type = "kernel"; arch = "arm"; os = "linux"; compression = "none";
            load = <0x80800000>; entry = <0x80800000>;
            hash-1 { algo = "sha256"; };
        };
        fdt {
            description = "Flattened DT";
            data = /incbin/("imx6ull-myboard.dtb");
            type = "flat_dt"; arch = "arm"; compression = "none";
            hash-1 { algo = "sha256"; };
        };
        ramdisk {
            description = "Initramfs";
            data = /incbin/("initramfs.cpio.gz");
            type = "ramdisk"; arch = "arm"; os = "linux";
            compression = "gzip";
            load = <0>; entry = <0>;
            hash-1 { algo = "sha256"; };
        };
    };
    configurations {
        default = "conf-1";
        conf-1 {
            description = "Boot";
            kernel = "kernel";
            fdt = "fdt";
            ramdisk = "ramdisk";
            hash-1 { algo = "sha256"; };
            signature-1 {
                algo = "sha256,rsa4096";
                key-name-hint = "dev";
                sign-images = "kernel", "fdt", "ramdisk";
            };
        };
    };
};
EOF

# Sign
mkimage -f kernel.its -K imx6ull-myboard.dtb -k keys/ -r kernel.itb

# The U-Boot DTB now contains the public key as a /signature/key-dev node
```

U-Boot's `bootm` verifies signatures before transferring control. Boot fails noisily if mismatched.

## 124.7  dm-verity for the rootfs

dm-verity = a kernel feature that hashes each block of a read-only block device into a Merkle tree. The root hash is verified at mount. any disk modification is detected on the read of the affected block.

```sh
# Build verity tree
veritysetup format /dev/loop0 /dev/loop1
# Outputs: Root hash: abcdef01234... (this hash is the "trusted" anchor)

# At kernel cmdline:
# root=/dev/dm-0 dm-mod.create="root,,,ro, 0 7864320 verity 1 /dev/mmcblk0p2 /dev/mmcblk0p3 4096 4096 983040 1 sha256 abcdef01... abcdef01..."

# Or via dracut/initramfs that calls veritysetup
```

The root hash goes in the kernel cmdline (signed via FIT signature, so an attacker can't change it). The rootfs is read-only. logs go to overlayfs in tmpfs (lost on reboot, by design) or to a separate data partition.

## 124.8  TrustZone + OP-TEE

ARMv7-A's TrustZone divides the CPU into two "worlds":
- **Normal World** (NW): regular Linux
- **Secure World** (SW): runs a Trusted OS (OP-TEE)

Each has its own MMU, exception vectors, peripheral access rules (configurable per peripheral). Switching is via **SMC** (Secure Monitor Call) instruction → traps to Monitor Mode → switches world.
**MMU** - Memory Management Unit, hardware that translates virtual addresses to physical addresses and enforces permissions.

```
   ┌─────────────────────────────────────────────────────┐
   │                  Normal World                        │
   │                                                       │
   │  ┌──────────────┐    ┌──────────────┐                │
   │  │   Linux       │    │  Apps        │                │
   │  │   kernel      │    │              │                │
   │  └──────┬───────┘    └──────┬───────┘                │
   │         │ libteec API       │ libteec API             │
   │         ▼                    ▼                          │
   │  ┌────────────────────────────────────┐                │
   │  │  optee_linuxdriver (in kernel)      │                │
   │  └──────────────┬─────────────────────┘                │
   └─────────────────┼─────────────────────────────────────┘
                     │ SMC instruction
   ┌─────────────────┼─────────────────────────────────────┐
   │  Monitor Mode    ▼                                      │
   │  ┌─────────────────────────────────────────┐           │
   │  │  Secure Monitor (lowest in OP-TEE OS)    │           │
   │  └──────────────┬───────────────────────────┘           │
   │                 ▼                                        │
   │  ┌─────────────────────────────────────────┐           │
   │  │  OP-TEE OS (the Trusted OS kernel)       │           │
   │  └──────────────┬───────────────────────────┘           │
   │                 ▼                                        │
   │  ┌─────────────────────────────────────────┐           │
   │  │  Trusted Applications (TAs)              │           │
   │  │  (e.g., key storage, crypto ops)         │           │
   │  └─────────────────────────────────────────┘           │
   │                  Secure World                            │
   └─────────────────────────────────────────────────────────┘
```

The kernel can request services from OP-TEE via the optee driver. user-space talks via `libteec`. Each request is an SMC → kernel context switch → OP-TEE serves request → SMC return.

## 124.9  Bringing up OP-TEE on i.MX6ULL

```sh
# Get OP-TEE
git clone https://github.com/OP-TEE/optee_os.git
cd optee_os

make PLATFORM=imx-mx6ull CROSS_COMPILE=arm-linux-gnueabihf- \
     CFG_TZDRAM_START=0x9e000000 CFG_TZDRAM_SIZE=0x02000000

# Produces tee.bin (the Trusted OS image)
```

In FIT image:

```
loadables {
    tee {
        description = "OP-TEE";
        data = /incbin/("tee.bin");
        type = "tee";
        arch = "arm";
        load = <0x9e000000>; entry = <0x9e000000>;
        compression = "none";
    };
};

configurations {
    conf-1 {
        kernel = "kernel"; fdt = "fdt";
        loadables = "tee";
    };
};
```

U-Boot loads TEE. kernel cmdline `tee=on` enables it. on boot the kernel finds it via DT (`firmware/optee` node).

```sh
dmesg | grep tee
# optee: probing for conduit method.
# optee: revision 3.20 (abcdef01)
# optee: dynamic shared memory is enabled
# optee: initialized driver
```

## 124.10  A simple Trusted Application

OP-TEE TAs are ELFs that run in Secure World. Hello-world TA:

```c
// ta/hello_ta.c
#include <tee_internal_api.h>

#define TA_HELLO_UUID { 0x12345678, 0x1234, 0x5678, { 0x9a, 0xbc, ... } }

TEE_Result TA_CreateEntryPoint(void) { return TEE_SUCCESS; }
void TA_DestroyEntryPoint(void) {}
TEE_Result TA_OpenSessionEntryPoint(uint32_t param_types, TEE_Param params[4],
                                     void **sess_ctx) {
    return TEE_SUCCESS;
}
void TA_CloseSessionEntryPoint(void *sess_ctx) {}

TEE_Result TA_InvokeCommandEntryPoint(void *sess_ctx, uint32_t cmd_id,
                                       uint32_t param_types, TEE_Param params[4]) {
    if (cmd_id == 0) {
        DMSG("hello from secure world");
        return TEE_SUCCESS;
    }
    return TEE_ERROR_BAD_PARAMETERS;
}
```

Normal-world client:

```c
// host/main.c
#include <tee_client_api.h>

int main(void) {
    TEEC_Context ctx;
    TEEC_Session sess;
    TEEC_UUID uuid = TA_HELLO_UUID;
    uint32_t err_origin;

    TEEC_InitializeContext(NULL, &ctx);
    TEEC_OpenSession(&ctx, &sess, &uuid, TEEC_LOGIN_PUBLIC, NULL, NULL, &err_origin);
    TEEC_InvokeCommand(&sess, 0, NULL, &err_origin);
    TEEC_CloseSession(&sess);
    TEEC_FinalizeContext(&ctx);
    return 0;
}
```

Run. OP-TEE kernel side passes the request. The TA in Secure World prints "hello from secure world" to OP-TEE's serial log (which the kernel may or may not relay).

Real TAs include:
- **Key storage** — the secret stays in Secure World. only operations like sign/verify are exposed.
- **Secure storage of credentials** — passwords, tokens, certificates that survive a kernel compromise.
- **Attestation** — proving to a server that the firmware running here is what the server expects.

## 124.11  Lab

1. **Generate keys.** Run `hab4_pki_tree.sh`. Inspect outputs. Keep keys safe.
2. **Build signed U-Boot.** Run CST. produce signed `u-boot-signed.imx`. Flash to SD.
3. **HAB open verification.** Without blowing fuses, boot the signed image. `hab_status` in U-Boot should show no events. Then flash a deliberately-wrong-signed image. `hab_status` shows events.
4. **(IRREVERSIBLE!) Close HAB on a sacrificial board.** Don't do this on your only board — it will refuse to boot anything unsigned forever.
5. **Sign FIT.** Build a signed FIT with kernel+DTB. verify U-Boot's `bootm` validates before transferring control.
6. **dm-verity.** Format a partition with veritysetup. add the root hash to cmdline. boot. verify mount succeeds. Then modify a byte of the rootfs partition (offline). boot. mount fails as expected.
7. **OP-TEE build + boot.** Build tee.bin. add to FIT. verify `dmesg` shows OP-TEE initialized.
8. **Hello TA.** Write the hello TA + host. Cross-compile both. Run on target. Verify OP-TEE serial log shows the message.
9. **Secure storage TA.** Use OP-TEE's secure-storage API to save a value. reboot. recover it. Demonstrate that even a hostile kernel can't read it.
10. **Attestation TA (stretch).** Implement a TA that signs a server challenge with a key held in Secure World. Server verifies. can't be forged from Normal World.

## 124.12  Pitfalls

- **Lost SRK keys.** You can't sign new firmware. Whatever was last signed is what the fleet runs from then on. Use HSMs. back up. document.
- **Closing HAB on an untested binary.** Brick.
- **Forgot to revoke an old SRK.** Compromised CSK can sign malicious firmware. Periodically rotate.
- **Keys committed to git.** Even private repos leak. Audit your repos. `git-secrets` to scan.
- **CSF aligned wrong.** "Blocks = 0x... 0x... 0x..." with wrong offsets → CSF validates wrong region. sig matches but actual binary is different. Use NXP's tools. don't hand-edit.
- **U-Boot env on writable storage with secure boot.** If env can be modified, attacker can set bootargs. Either: sign env, or move to read-only env, or strip non-essential commands from U-Boot.
- **Boot from USB-SDP with HAB closed.** USB-SDP still works because Boot ROM accepts a signed binary over USB. Attacker with USB access can replace your firmware → make sure UART/USB ports are physically inaccessible in field.
- **dm-verity hash on cmdline becomes leaked.** Not a security failure per se (the hash is public), but reveals the rootfs version. Use signed cmdline.
- **OP-TEE bug = full Secure World compromise.** Keep OP-TEE updated. subscribe to OP-TEE security advisories.
- **TA crashes due to TEE_TIMEOUT_INFINITE bugs.** Some operations block forever. reset OP-TEE only by reboot.
- **No anti-rollback.** Attacker downgrades to an old, vulnerable firmware. Use FIT's `compatible` versioning + monotonic version counter checked by U-Boot.

## 124.13  Going deeper

- **NXP AN4581: Secure Boot on i.MX 6 Series** — the canonical reference.
- **NXP CST 3.4+ documentation** + sample CSFs.
- **U-Boot's `doc/imx/habv4/`** — practical signing setup.
- **OP-TEE documentation** — https://optee.readthedocs.io.
- **`Documentation/admin-guide/dm-verity.rst`** in kernel.
- **`mkimage -k <keydir> -r <its>`** — for FIT signing.
- **`/lib/modules/$(uname -r)/build/scripts/sign-file`** — for kernel-module signing.
- **GlobalPlatform TEE specifications** — for cross-vendor TEE compatibility.
- **NIST SP 800-193: Platform Firmware Resilience** — government-grade requirements.
- **Ch 125** — OTA needs secure boot to be meaningful.
- **Ch 7** — the original Boot ROM chapter.

---

> Next chapter: **Chapter 125 — Field updates (RAUC, SWUpdate, Mender)**.
> **RAUC** - an embedded update framework for signed A/B image installation and rollback.
