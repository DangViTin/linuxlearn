---
chapter: 35H
title: Rootfs security basics
part: V - Root filesystem and user space
estimated_pages: 16
status: draft
---

# Chapter 35H: Rootfs security basics

This chapter is not a full security book. It is the minimum checklist before a rootfs leaves the lab.

The goal:

- no empty root password,
- no unnecessary network service,
- app does not run as root unless it must,
- secrets are not baked into public images,
- writable data is separated from immutable system files.

## 35H.1  Remove the lab shortcuts

During bring-up, we often do this:

```text
root::0:0:root:/root:/bin/sh
```

That means root has no password. Fine for a closed lab board. Bad for anything connected to a network.

Before release:

- set a password or lock root,
- prefer SSH keys,
- create a non-root service user,
- disable unused gettys and network daemons.

## 35H.2  Lock root login

In `/etc/shadow`, a locked root account starts with `!`:

```text
root:!:19000:0:99999:7:::
```

Or on target:

```sh
[root@pa-mini:~]# passwd -l root
```

If you need emergency root access, use a recovery mode that requires physical access.

## 35H.3  SSH keys, not passwords

For Dropbear or OpenSSH, install an authorized key:

```sh
mkdir -p /home/dev/.ssh
chmod 700 /home/dev/.ssh
cat > /home/dev/.ssh/authorized_keys <<'EOF'
ssh-ed25519 AAAA... dev@host
EOF
chmod 600 /home/dev/.ssh/authorized_keys
chown -R dev:dev /home/dev/.ssh
```

Disable password login if the product allows it.

For OpenSSH:

```text
PasswordAuthentication no
PermitRootLogin no
```

For Dropbear, pass options from its init script. The exact flags depend on the Buildroot Dropbear version, so check:

```sh
dropbear -h
```

## 35H.4  Run the app as a user

Create a service user:

```text
myapp:x:200:200:myapp:/var/empty:/sbin/nologin
```

In `/etc/group`:

```text
myapp:x:200:
```

BusyBox init script:

```sh
start-stop-daemon -S -b -c myapp -x /usr/bin/myapp
```

systemd unit:

```ini
[Service]
User=myapp
Group=myapp
ExecStart=/usr/bin/myapp
```

If the app needs GPIO, I2C, SPI, or video access, give access to that specific device or group. Do not run everything as root just because one file needed permission.

## 35H.5  File permissions

Useful defaults:

```text
/usr/bin/myapp        0755 root:root
/etc/myapp.conf       0644 root:root
/data/myapp/          0750 myapp:myapp
/data/myapp/secret    0600 myapp:myapp
```

Check:

```sh
find / -perm -4000 -type f 2>/dev/null
find / -writable -type d 2>/dev/null | head
```

Setuid binaries deserve review. World-writable directories should be rare.

## 35H.6  Secrets

Do not bake these into a public rootfs image:

- private SSH keys,
- API tokens,
- customer certificates,
- production passwords,
- signing keys.

Better places:

- provision during manufacturing,
- store under `/data/secure/`,
- derive from a hardware unique key if available,
- use a secure element or TPM for private keys.

At minimum, each shipped board should not share the same private identity.

## 35H.7  Reduce services

List listening sockets:

```sh
ss -lntup
```

On BusyBox-only systems without `ss`, use:

```sh
netstat -lntup
```

Ask for each service:

- Why does this need to listen?
- Is it bound to all interfaces?
- Does it need authentication?
- Can it be disabled in production?

Common development-only services:

- SSH with password login,
- telnet,
- FTP,
- debug HTTP servers,
- gdbserver,
- unrestricted MQTT broker.

## 35H.8  Read-only rootfs helps security

Chapter 35B used read-only rootfs for power-loss safety. It also helps security:

- malware cannot easily modify `/usr/bin`,
- accidental writes fail early,
- factory reset can clear data without reflashing system files.

But read-only rootfs is not enough. If `/data` is writable and the app executes files from `/data`, attackers can still persist. Mount data with conservative options when possible:

```text
LABEL=data  /data  ext4  defaults,noatime,nodev,nosuid  0  2
```

Use `noexec` only if your product never runs programs from `/data`.

## 35H.9  Release checklist

- Root password locked or intentionally set.
- SSH root login disabled.
- Password SSH disabled if keys are available.
- App runs as non-root.
- `/data` permissions reviewed.
- No private keys in the image.
- `ss -lntup` shows only expected services.
- Read-only rootfs tested.
- Factory reset does not erase device identity unless intended.

## 35H.10  Lab

1. Create a non-root user `dev`.
2. Add an SSH key for `dev`.
3. Disable root SSH login.
4. Create a `myapp` service user.
5. Run your service as `myapp`.
6. Confirm it can access only the files it needs.
7. Run `ss -lntup` and write down every listening service.

## 35H.11  Pitfalls

- **One shared password across all boards.** This becomes a fleet-wide secret.
- **Private keys in Git.** Never put production keys in the repository.
- **App runs as root forever.** Convenient in the lab, expensive later.
- **Factory reset wipes identity.** Serial number, MAC address, and certificates often need to survive.
- **Security added after release.** It is much harder after field deployment.

---

Previous chapter: [Chapter 35B - Read-only rootfs and overlayfs](ch35B-readonly-rootfs-overlayfs.md)

Next chapter: [Chapter 35C - Container runtimes on embedded](ch35C-containers-on-embedded.md)
