---
chapter: 64
title: QSPI NOR flash (W25Q128 / MX25L256 / MT25Q)
part: VII — Device cookbook
estimated_pages: 26
status: draft
---

# Chapter 64 — QSPI NOR flash
**UBI** - Unsorted Block Images, a flash-management layer over raw NAND that handles wear leveling and bad blocks.

> **Naming convention used across Part VII.** Shell prompts shown as `[root@pa-mini:~]#` come from the reference test board — the Point Atom MINI configured with hostname `pa-mini`. Substitute your own hostname. nothing else about the lab assumes it.

> **What:** how a QSPI NOR flash chip actually works on the wire, how the mainline `spi-nor` driver implements it, and how to write your own minimal driver from scratch for one specific chip. Three chips compared — **Winbond W25Q128** (16 MB), **Macronix MX25L25645G** (32 MB), **Micron MT25QL256ABA** (32 MB) — but the from-scratch driver targets the W25Q128 to keep the example concrete.
>
> **Why:** the philosophy of this book is "raw — build it yourself, understand it forever." For QSPI flash that means: command bytes on the wire, status-register polling, page-program timing, JEDEC ID parsing. After this chapter you can read the mainline `spi-nor` source and know exactly what each function is hiding. If you encounter a chip that is not in the database, you can add an entry — or replace the framework with about 200 lines of your own.
>
> **Focus:** **a NOR flash is a state machine driven by single-byte commands**. `0x9F` = read JEDEC ID. `0x06` = write-enable. `0x20` = sector erase. `0x02` = page program. `0x03` = read. Send the right bytes in the right order and you can read, erase, program, and identify any standard NOR flash with about 100 lines of code. The mainline driver wraps this in abstractions and a parameter database, but the wire protocol itself is small.


## 64.1  Why QSPI NOR vs eMMC vs SD vs raw NAND

| | QSPI NOR | eMMC | SD card | Raw NAND |
|---|---|---|---|---|
| Typical size | 8–32 MB | 4–64 GB | 4 GB–1 TB | 256 MB–4 GB |
| Read speed | 50 MB/s | 250 MB/s | 90 MB/s | 30 MB/s |
| Write speed | 0.5 MB/s | 100 MB/s | 60 MB/s | 5 MB/s |
| Erase block | 4–64 KB | invisible | invisible | 128 KB |
| Erase cycles | 100,000 | 1k–10k | varies | 10,000 |
| XIP-capable | ✔ | ✗ | ✗ | ✗ |
| Wear-leveling in HW | none — driver problem | yes | yes | none — UBI |
| Cost (volume) | $1–5 | $5–20 | $3–10 | $2–10 |
| Best for | Small soldered boot device | Main consumer storage | Removable / dev | Mid-size industrial |

QSPI NOR fits when your storage need is under 32 MB, when you want a fast, deterministic boot, when you want a soldered device that resists theft, and when there is little user data to store. Many industrial i.MX6ULL designs boot from QSPI NOR.

## 64.2  Chip comparison

| | W25Q128 (Winbond) | MX25L25645G (Macronix) | MT25QL256ABA (Micron) |
|---|---|---|---|
| Capacity | 16 MB | 32 MB | 32 MB |
| Max SPI clock | 104 MHz | 133 MHz | 166 MHz |
| Max QSPI clock | 80 MHz | 104 MHz | 90 MHz |
| Page program size | 256 B | 256 B | 256 B |
| Sector erase | 4 KB | 4 KB | 4 KB |
| Address bytes | 3 (auto 4-byte cmds also avail.) | 3 + 4-byte mode | 3 + 4-byte mode |
| Erase cycles | 100k | 100k | 100k (rated) |
| Temp grade | -40 to +85 °C | -40 to +85 °C | -40 to +105 °C AEC-Q100 |
| Volume price | $1.20–1.80 | $2.50–4.00 | $5–7 |
| JEDEC ID | `ef 40 18` | `c2 20 19` | `20 ba 19` |

All three speak the same core command set. The chips differ mainly in capacity, top speed, and the 4-byte-address handshake. The from-scratch driver below works on all three (with the address-byte size adjusted).

## 64.3  Schematic

The minimum is six wires:

```
 i.MX6ULL                   W25Q128 / MX25L256 / MT25Q
 ─────────                  ──────────────────────────
 QSPI_A_SCLK  ───────────►  CLK
 QSPI_A_DATA0 ◄──────────►  IO0 (MOSI in 1-bit mode)
 QSPI_A_DATA1 ◄──────────►  IO1 (MISO in 1-bit mode)
 QSPI_A_DATA2 ◄──────────►  IO2 (/WP   in 1-bit mode — pull HIGH for QSPI)
 QSPI_A_DATA3 ◄──────────►  IO3 (/HOLD in 1-bit mode — pull HIGH for QSPI)
 QSPI_A_SS0_B ───────────►  /CS

 VCC          ───────────►  VCC (3.3 V)
 GND          ───────────►  GND
```

**Decoupling:** 100 nF + 4.7 µF close to VCC. Page programming draws sharp ~20 mA pulses. insufficient decoupling causes spurious resets.

**Layout:** ≤ 5 mm length-mismatch between SCLK and IO[0:3] traces at 80 MHz. Series termination 33 Ω on each line is common. Keep traces ≤ 4 cm.

**Pull-ups:** 10 kΩ on IO2 and IO3. These pull-ups keep IO2 and IO3 HIGH while the chip is still in single-IO mode at boot. Quad mode is not enabled yet, so IO2 acts as /WP and IO3 as /HOLD. Both are active-low, so "HIGH" means "not asserted."

## 64.4  The protocol — what's on the wire

NOR flash chips speak a small command set. Each transaction is the same shape:

```
   /CS:   ───┐                                                    ┌───
              │                                                    │
              │           ▲  ▲  ▲  ▲  ▲  ▲  ▲  ▲                  │
              │   cmd     │  │  │  │  │  │  │  │  data            │
              └───────────┴──┴──┴──┴──┴──┴──┴──┴──────────────────┘
              ◄─ command ─►◄── address (if any) ─►◄── data (R or W) ─►
              (1 byte)     (3 or 4 bytes)         (0..N bytes)
```

The host:
1. Drives /CS low.
2. Clocks out a 1-byte command.
3. (Optionally) clocks out the address bytes — 3 bytes for chips ≤ 16 MB, 4 bytes for larger or when explicitly in 4-byte mode.
4. Either clocks out write data (program) or clocks in read data.
5. Drives /CS high.

### The command set you'll use

| Op | Command byte | Address? | Data direction | Notes |
|----|----|----|----|----|
| Read JEDEC ID | `0x9F` | none | 3 bytes in (mfr+type+capacity) | identify chip |
| Read status register 1 | `0x05` | none | 1 byte in | bit 0 = BUSY |
| Write enable | `0x06` | none | none | required before any write/erase |
| Write disable | `0x04` | none | none | optional cleanup |
| Read data (slow) | `0x03` | 3 bytes | N bytes in | ≤ 50 MHz |
| Fast read | `0x0B` | 3 bytes + 1 dummy | N bytes in | up to chip max |
| Page program | `0x02` | 3 bytes | up to 256 B out | within one 256-B page |
| Sector erase (4 KB) | `0x20` | 3 bytes | none | takes ~50 ms |
| Block erase (64 KB) | `0xD8` | 3 bytes | none | takes ~150 ms |
| Chip erase | `0xC7` | none | none | tens of seconds |
| 4-byte address mode | `0xB7` | none | none | switch to 4-byte addressing |

That is the full interface. Some chips add quad-IO commands (`0xEB` for read, `0x32` for program). same idea but with data spread over 4 IO lanes for ~4× throughput.

### Three invariants that catch beginners

1. **Every write/erase must be preceded by `0x06` (write-enable).** The chip silently ignores writes without it. After a successful write/erase, the chip auto-clears write-enable, so it must be re-issued each time.
2. **The BUSY bit (status register bit 0) is set during write/erase and clears when done.** The host must poll until it clears before issuing the next command. A page program can take 700 µs–3 ms. a sector erase takes 50–250 ms.
3. **You can only program 1→0.** Bits cannot be flipped 0→1 except via erase. So "writing" a byte first requires the relevant sector to have been erased to all-0xFF.

## 64.5  Reading JEDEC ID — the smallest useful transaction

Before anything else, identify the chip:

```
   Host                    Chip
   ----                    ----
   /CS↓
   send 0x9F  (read JEDEC ID command)
   receive 3 bytes:
       byte 0: manufacturer (0xEF Winbond, 0xC2 Macronix, 0x20 Micron, ...)
       byte 1: memory type   (e.g., 0x40 for W25Q SPI flash family)
       byte 2: capacity      (0x18 = 2^24 bytes = 16 MB; 0x19 = 32 MB; 0x1A = 64 MB)
   /CS↑
```

From these three bytes the chip is uniquely identified (in 99% of cases). The mainline `spi-nor` driver does exactly this and then looks the triple up in its database.

## 64.6  How the mainline `spi-nor` driver works internally

Source: `drivers/mtd/spi-nor/`.
**MTD** - Memory Technology Device, Linux's raw flash subsystem for eraseblock-based storage.

```
drivers/mtd/spi-nor/
├── core.c        ← framework: read/write/erase loops, sector tracking
├── sfdp.c        ← SFDP (Serial Flash Discoverable Parameters) parser
├── swp.c         ← software write-protect helpers
├── otp.c         ← one-time-programmable region support
├── debugfs.c     ← /sys/kernel/debug/spi-nor/
├── winbond.c     ← parameter table for Winbond chips
├── macronix.c    ← Macronix table
├── micron-st.c   ← Micron + ST + GigaDevice + ISSI tables
├── ... (15+ vendor files)
```

The driver is two-layer: a vendor-agnostic core that handles read / erase / write loops, plus per-vendor parameter tables describing each chip's quirks (size, fast-read opcode choice, quad-enable bit position, etc.).

### Driver flow at probe

```c
/* drivers/mtd/spi-nor/core.c — simplified */
static int spi_nor_probe(struct spi_mem *spimem)
{
    struct spi_nor *nor = ...;

    /* 1. Issue 0x9F, read 3 bytes */
    err = spi_nor_read_id(nor, /* offset */ 0, /* len */ 3, id);

    /* 2. Walk the database for a match */
    for (each registered chip in winbond_nor_parts, macronix_nor_parts, ...) {
        if (memcmp(id, info->id, 3) == 0) {
            nor->info = info;
            break;
        }
    }

    /* 3. Optionally read SFDP for runtime discovery of params not in static table */
    if (info->parse_sfdp || !info)
        spi_nor_parse_sfdp(nor);

    /* 4. Enable quad mode if the chip supports it (chip-specific QE bit) */
    spi_nor_quad_enable(nor);

    /* 5. Register an MTD device */
    nor->mtd.name      = "nor";
    nor->mtd.size      = info->sector_size * info->n_sectors;
    nor->mtd._read     = spi_nor_read;
    nor->mtd._write    = spi_nor_write;
    nor->mtd._erase    = spi_nor_erase;
    return mtd_device_parse_register(&nor->mtd, ...);
}
```

That's the architecture: identify → look up parameters → register as MTD device. The rest is MTD's problem.

### How `spi_nor_read` works

```c
/* Simplified */
static int spi_nor_read(struct mtd_info *mtd, loff_t from, size_t len,
                        size_t *retlen, u_char *buf)
{
    struct spi_nor *nor = mtd_to_spi_nor(mtd);

    while (len > 0) {
        size_t chunk = min(len, /* controller transfer limit */ 4096);

        struct spi_mem_op op = SPI_MEM_OP(
            SPI_MEM_OP_CMD(nor->read_opcode, 1),       /* cmd byte */
            SPI_MEM_OP_ADDR(nor->addr_nbytes, from, 1),/* address */
            SPI_MEM_OP_DUMMY(nor->read_dummy, 1),       /* dummy cycles for fast-read */
            SPI_MEM_OP_DATA_IN(chunk, buf, 1));         /* read data */

        err = spi_mem_exec_op(nor->spimem, &op);
        if (err) return err;

        buf  += chunk;
        from += chunk;
        len  -= chunk;
        *retlen += chunk;
    }
    return 0;
}
```

The `spi_mem_op` struct describes a NOR-style command in four fields (cmd, addr, dummy, data) — `spi_mem_exec_op` translates that into whatever the underlying SPI/QSPI controller wants. For a controller like i.MX QSPI that has hardware support for "command + address + data" transactions, it programs a few registers and DMA-receives the data. For a plain SPI controller, it falls back to bit-banging the same sequence through ordinary `spi_message`s.
> **MCU bridge:** Think of DMA like the MCU DMA controller you used for UART or SPI, but with cache coherency, scatter-gather descriptors, and kernel ownership rules added.
**DMA** - Direct Memory Access. hardware moves data to or from memory without the CPU copying each byte.

### How `spi_nor_write` works

Write is *much* more involved because of erase-before-write, page boundaries, and BUSY polling:

```c
static int spi_nor_write(struct mtd_info *mtd, loff_t to, size_t len,
                         size_t *retlen, const u_char *buf)
{
    struct spi_nor *nor = mtd_to_spi_nor(mtd);

    while (len > 0) {
        /* 1. Compute how much we can write in this page (256 B max, less if not aligned) */
        size_t page_offset = to & (nor->page_size - 1);
        size_t chunk       = min(len, nor->page_size - page_offset);

        /* 2. Issue write-enable */
        spi_nor_write_enable(nor);    /* sends 0x06 */

        /* 3. Issue page program: 0x02 + addr + up to 256 data bytes */
        struct spi_mem_op op = SPI_MEM_OP(
            SPI_MEM_OP_CMD(nor->program_opcode, 1),
            SPI_MEM_OP_ADDR(nor->addr_nbytes, to, 1),
            SPI_MEM_OP_NO_DUMMY,
            SPI_MEM_OP_DATA_OUT(chunk, buf, 1));
        err = spi_mem_exec_op(nor->spimem, &op);

        /* 4. Poll status until BUSY clears */
        err = spi_nor_wait_till_ready(nor);   /* sends 0x05, reads until bit0 = 0 */

        buf += chunk; to += chunk; len -= chunk; *retlen += chunk;
    }
    return 0;
}
```

Step 1's page-boundary clamp matters because NOR chips wrap *within a page*. If you program at address 0xFE with 4 bytes of data, the last 2 bytes go to 0xFE and 0xFF, then the next 2 bytes wrap back to 0x00 and 0x01 of the same page. Silent corruption. The driver splits long writes at page boundaries.

### How erase works

```c
static int spi_nor_erase_sector(struct spi_nor *nor, u32 addr)
{
    spi_nor_write_enable(nor);

    struct spi_mem_op op = SPI_MEM_OP(
        SPI_MEM_OP_CMD(nor->erase_opcode, 1),       /* 0x20 = sector erase */
        SPI_MEM_OP_ADDR(nor->addr_nbytes, addr, 1),
        SPI_MEM_OP_NO_DUMMY,
        SPI_MEM_OP_NO_DATA);
    spi_mem_exec_op(nor->spimem, &op);

    return spi_nor_wait_till_ready(nor);    /* may take 50 ms */
}
```

For a longer range, the MTD-level `erase` callback walks the range and issues one of `0x20` (4 KB) / `0x52` (32 KB) / `0xD8` (64 KB) per granularity that aligns, minimizing the total number of erase commands.

### Status polling

```c
static int spi_nor_wait_till_ready(struct spi_nor *nor)
{
    unsigned long deadline = jiffies + msecs_to_jiffies(40000);  /* 40 s max */
    while (time_before(jiffies, deadline)) {
        u8 sr;
        struct spi_mem_op op = SPI_MEM_OP(
            SPI_MEM_OP_CMD(SPINOR_OP_RDSR, 1),     /* 0x05 */
            SPI_MEM_OP_NO_ADDR, SPI_MEM_OP_NO_DUMMY,
            SPI_MEM_OP_DATA_IN(1, &sr, 1));
        spi_mem_exec_op(nor->spimem, &op);
        if (!(sr & 1))      /* BUSY bit clear */
            return 0;
        cond_resched();
    }
    return -ETIMEDOUT;
}
```

This polling loop is what makes the framework work on Linux: it yields the CPU between checks. For a chip-erase (tens of seconds), the loop runs for a long time but the kernel stays responsive because of `cond_resched`.

## 64.7  Writing a NOR-flash driver from scratch

To prove we understand the chip, let's write a minimal driver that bypasses the `spi-nor` framework entirely. Just a plain `spi_driver` that exposes a `/dev/myflash` char device with `read` / `write` / `ioctl` for erase. ~250 lines.

`myflash.c`:

```c
#include <linux/init.h>
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/uaccess.h>
#include <linux/slab.h>
#include <linux/delay.h>

#define CHIP_SIZE     (16 * 1024 * 1024)   /* 16 MB = W25Q128 */
#define SECTOR_SIZE   4096
#define PAGE_SIZE_N   256

#define CMD_READ_ID       0x9F
#define CMD_READ_STATUS   0x05
#define CMD_WRITE_ENABLE  0x06
#define CMD_READ          0x03
#define CMD_PAGE_PROGRAM  0x02
#define CMD_SECTOR_ERASE  0x20

#define IOC_ERASE_SECTOR  _IO('M', 1)

struct myflash {
    struct spi_device *spi;
    struct cdev cdev;
    dev_t devid;
    struct class *class;
    struct mutex lock;
};

/* === Low-level: send one command + (optional) address + (optional) data === */

static int mf_xfer(struct myflash *m, u8 cmd, u32 addr, bool has_addr,
                   u8 *tx_data, u8 *rx_data, size_t data_len)
{
    u8 hdr[5];
    int hdr_len = 1;
    struct spi_transfer xfers[2] = {0};
    struct spi_message msg;

    hdr[0] = cmd;
    if (has_addr) {
        hdr[1] = (addr >> 16) & 0xff;
        hdr[2] = (addr >>  8) & 0xff;
        hdr[3] =  addr        & 0xff;
        hdr_len = 4;
    }

    spi_message_init(&msg);

    xfers[0].tx_buf = hdr;
    xfers[0].len    = hdr_len;
    spi_message_add_tail(&xfers[0], &msg);

    if (data_len > 0) {
        xfers[1].tx_buf = tx_data;
        xfers[1].rx_buf = rx_data;
        xfers[1].len    = data_len;
        spi_message_add_tail(&xfers[1], &msg);
    }

    return spi_sync(m->spi, &msg);
}

static int mf_read_id(struct myflash *m, u8 id[3])
{
    return mf_xfer(m, CMD_READ_ID, 0, false, NULL, id, 3);
}

static int mf_write_enable(struct myflash *m)
{
    return mf_xfer(m, CMD_WRITE_ENABLE, 0, false, NULL, NULL, 0);
}

static int mf_read_status(struct myflash *m, u8 *sr)
{
    return mf_xfer(m, CMD_READ_STATUS, 0, false, NULL, sr, 1);
}

static int mf_wait_ready(struct myflash *m)
{
    int retries = 1000;     /* ~1 s @ ~1 ms each */
    while (retries-- > 0) {
        u8 sr;
        int err = mf_read_status(m, &sr);
        if (err) return err;
        if (!(sr & 1))      /* BUSY clear */
            return 0;
        msleep(1);
    }
    return -ETIMEDOUT;
}

/* === Mid-level: read N bytes / program 1 page / erase 1 sector === */

static int mf_read(struct myflash *m, u32 addr, u8 *buf, size_t len)
{
    return mf_xfer(m, CMD_READ, addr, true, NULL, buf, len);
}

static int mf_page_program(struct myflash *m, u32 addr, const u8 *buf, size_t len)
{
    int err;
    if (len == 0 || len > PAGE_SIZE_N) return -EINVAL;
    if ((addr & (PAGE_SIZE_N - 1)) + len > PAGE_SIZE_N) return -EINVAL;

    err = mf_write_enable(m);                          if (err) return err;
    err = mf_xfer(m, CMD_PAGE_PROGRAM, addr, true,
                  (u8 *)buf, NULL, len);                if (err) return err;
    return mf_wait_ready(m);
}

static int mf_erase_sector(struct myflash *m, u32 addr)
{
    int err;
    if (addr & (SECTOR_SIZE - 1)) return -EINVAL;
    err = mf_write_enable(m);                          if (err) return err;
    err = mf_xfer(m, CMD_SECTOR_ERASE, addr, true, NULL, NULL, 0);
    if (err) return err;
    return mf_wait_ready(m);
}

/* === Char-device interface === */

static int mf_open(struct inode *inode, struct file *filp)
{
    struct myflash *m = container_of(inode->i_cdev, struct myflash, cdev);
    filp->private_data = m;
    return 0;
}

static ssize_t mf_fops_read(struct file *filp, char __user *u,
                            size_t count, loff_t *ppos)
{
    struct myflash *m = filp->private_data;
    u8 *kbuf;
    int err;

    if (*ppos >= CHIP_SIZE) return 0;
    if (*ppos + count > CHIP_SIZE) count = CHIP_SIZE - *ppos;
    if (count > 65536) count = 65536;   /* cap per call */

    kbuf = kmalloc(count, GFP_KERNEL);
    if (!kbuf) return -ENOMEM;

    mutex_lock(&m->lock);
    err = mf_read(m, *ppos, kbuf, count);
    mutex_unlock(&m->lock);
    if (err) { kfree(kbuf); return err; }

    if (copy_to_user(u, kbuf, count)) { kfree(kbuf); return -EFAULT; }
    kfree(kbuf);
    *ppos += count;
    return count;
}

static ssize_t mf_fops_write(struct file *filp, const char __user *u,
                             size_t count, loff_t *ppos)
{
    struct myflash *m = filp->private_data;
    u8 *kbuf;
    int err;
    size_t done = 0;

    if (*ppos >= CHIP_SIZE) return -ENOSPC;
    if (*ppos + count > CHIP_SIZE) count = CHIP_SIZE - *ppos;

    kbuf = kmalloc(count, GFP_KERNEL);
    if (!kbuf) return -ENOMEM;
    if (copy_from_user(kbuf, u, count)) { kfree(kbuf); return -EFAULT; }

    mutex_lock(&m->lock);
    while (done < count) {
        size_t page_off = (*ppos + done) & (PAGE_SIZE_N - 1);
        size_t chunk    = min((size_t)(PAGE_SIZE_N - page_off), count - done);
        err = mf_page_program(m, *ppos + done, kbuf + done, chunk);
        if (err) break;
        done += chunk;
    }
    mutex_unlock(&m->lock);
    kfree(kbuf);
    if (err) return err;

    *ppos += done;
    return done;
}

static long mf_fops_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
    struct myflash *m = filp->private_data;
    int err;

    if (cmd == IOC_ERASE_SECTOR) {
        u32 addr = (u32)arg;
        mutex_lock(&m->lock);
        err = mf_erase_sector(m, addr);
        mutex_unlock(&m->lock);
        return err;
    }
    return -ENOTTY;
}

static loff_t mf_fops_llseek(struct file *filp, loff_t off, int whence)
{
    return fixed_size_llseek(filp, off, whence, CHIP_SIZE);
}

static const struct file_operations mf_fops = {
    .owner   = THIS_MODULE,
    .open    = mf_open,
    .read    = mf_fops_read,
    .write   = mf_fops_write,
    .llseek  = mf_fops_llseek,
    .unlocked_ioctl = mf_fops_ioctl,
};

/* === Probe / Remove === */

static int mf_probe(struct spi_device *spi)
{
    struct myflash *m;
    u8 id[3];
    int err;

    m = devm_kzalloc(&spi->dev, sizeof(*m), GFP_KERNEL);
    if (!m) return -ENOMEM;
    m->spi = spi;
    mutex_init(&m->lock);

    spi->mode = SPI_MODE_0;
    spi->bits_per_word = 8;
    err = spi_setup(spi);
    if (err) return dev_err_probe(&spi->dev, err, "spi_setup failed\n");

    err = mf_read_id(m, id);
    if (err) return dev_err_probe(&spi->dev, err, "read-id failed\n");
    dev_info(&spi->dev, "JEDEC ID: %02x %02x %02x\n", id[0], id[1], id[2]);

    if (id[0] != 0xEF || id[2] != 0x18)
        return dev_err_probe(&spi->dev, -ENODEV,
                             "expected W25Q128 (EF xx 18), got %02x %02x %02x\n",
                             id[0], id[1], id[2]);

    /* Register chardev */
    err = alloc_chrdev_region(&m->devid, 0, 1, "myflash");
    if (err) return err;
    cdev_init(&m->cdev, &mf_fops);
    m->cdev.owner = THIS_MODULE;
    err = cdev_add(&m->cdev, m->devid, 1);
    if (err) goto unreg;

    m->class = class_create("myflash");
    if (IS_ERR(m->class)) { err = PTR_ERR(m->class); goto del_cdev; }
    device_create(m->class, NULL, m->devid, NULL, "myflash");

    spi_set_drvdata(spi, m);
    return 0;

del_cdev:
    cdev_del(&m->cdev);
unreg:
    unregister_chrdev_region(m->devid, 1);
    return err;
}

static void mf_remove(struct spi_device *spi)
{
    struct myflash *m = spi_get_drvdata(spi);
    device_destroy(m->class, m->devid);
    class_destroy(m->class);
    cdev_del(&m->cdev);
    unregister_chrdev_region(m->devid, 1);
}

static const struct of_device_id mf_of_match[] = {
    { .compatible = "linuxlearn,myflash" },
    { }
};
MODULE_DEVICE_TABLE(of, mf_of_match);

static struct spi_driver mf_driver = {
    .driver = {
        .name = "myflash",
        .of_match_table = mf_of_match,
    },
    .probe  = mf_probe,
    .remove = mf_remove,
};
module_spi_driver(mf_driver);

MODULE_LICENSE("GPL");
```

DT to test it:

```dts
&ecspi3 {
    flash@0 {
        compatible = "linuxlearn,myflash";
        reg = <0>;
        spi-max-frequency = <20000000>;
    };
};
```

Note we're using ordinary SPI (`ecspi3`), not QSPI. The raw protocol works at single-IO mode up to ~50 MHz. using QSPI would require either an MMIO-driver for the i.MX QSPI controller's command-mode registers (more involved) or going through `spi_mem` (which is exactly what we said we were skipping). For this teaching example, ordinary SPI is the right choice.
**MMIO** - memory-mapped I/O, where software accesses peripheral registers through normal load and store instructions.

Build, load, exercise:

```
[root@pa-mini:~]# insmod myflash.ko
[root@pa-mini:~]# dmesg | tail
myflash spi3.0: JEDEC ID: ef 40 18
[root@pa-mini:~]# ls /dev/myflash
/dev/myflash

# Read sector 0 (4 KB at offset 0):
[root@pa-mini:~]# dd if=/dev/myflash bs=4096 count=1 | hexdump -C | head
00000000  ff ff ff ff ff ff ff ff ...    (virgin sector)

# Erase, write, read back:
[root@pa-mini:~]# echo -n "Hello, NOR!" > /tmp/msg
[root@pa-mini:~]# ./myflash-ioctl /dev/myflash --erase 0          # uses ioctl IOC_ERASE_SECTOR
[root@pa-mini:~]# dd if=/tmp/msg of=/dev/myflash bs=11 conv=notrunc
[root@pa-mini:~]# dd if=/dev/myflash bs=11 count=1
Hello, NOR!
```

(The `myflash-ioctl` is a tiny userspace helper that does `ioctl(fd, _IO('M', 1), addr)`. Build alongside.)

What we got, in ~250 lines:
- Identify the chip by JEDEC ID.
- Read arbitrary offsets.
- Page-aligned writes (with the in-driver split-at-page-boundary loop).
- Sector erase via ioctl.
- A chardev `/dev/myflash`.
- Mutex protection against concurrent access.

What we *skipped* compared to `spi-nor`:
- MTD integration (so no partitions, no `fw_setenv`, no boot-from-flash for U-Boot).
> **MCU bridge:** Think of U-Boot like a much larger boot stub plus debug monitor: it initializes hardware, loads the next image, and gives you commands before Linux starts.
**U-Boot** - the bootloader that initializes enough hardware to load and start the Linux kernel.
- Quad-IO mode (4× faster).
- SFDP auto-discovery (works for any chip, not just W25Q128).
- 4-byte address mode for > 16 MB chips.
- Software write-protect ranges.
- Sleep/resume PM.
- DMA for transfers > one SPI controller burst.

That gap is what the mainline framework gives you. For a one-off chip, the from-scratch version is enough. For any product going to market, use the mainline driver.

## 64.8  Now: how to use the mainline driver

With the protocol and the from-scratch driver demystified, the mainline driver is just convenience layers over the same operations.

DT:

```dts
&qspi {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_qspi>;
    status = "okay";

    flash@0 {
        compatible = "winbond,w25q128", "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <80000000>;
        spi-rx-bus-width = <4>;       /* QSPI quad */
        spi-tx-bus-width = <4>;

        partitions {
            compatible = "fixed-partitions";
            #address-cells = <1>;
            #size-cells = <1>;

            partition@0 {
                label = "u-boot";
                reg = <0x000000 0x100000>;       /* 1 MB */
                read-only;
            };
            partition@100000 {
                label = "u-boot-env";
                reg = <0x100000 0x010000>;       /* 64 KB */
            };
            partition@110000 {
                label = "dtb";
                reg = <0x110000 0x010000>;
            };
            partition@120000 {
                label = "kernel-a";
                reg = <0x120000 0x600000>;       /* 6 MB */
            };
            partition@720000 {
                label = "kernel-b";
                reg = <0x720000 0x600000>;
            };
            partition@d20000 {
                label = "user-data";
                reg = <0xd20000 0x2e0000>;
            };
        };
    };
};
```

For Macronix / Micron:

```dts
compatible = "macronix,mx25l25645g", "jedec,spi-nor";
/* or */
compatible = "micron,mt25ql256", "jedec,spi-nor";
```

The `"jedec,spi-nor"` fallback means the driver runs and reads JEDEC ID at probe. If the first compatible isn't recognised, the database fallback identifies the chip from the ID anyway.

After boot:

```
[root@pa-mini:~]# cat /proc/mtd
dev:    size   erasesize  name
mtd0: 00100000 00010000 "u-boot"
mtd1: 00010000 00010000 "u-boot-env"
mtd2: 00010000 00010000 "dtb"
mtd3: 00600000 00010000 "kernel-a"
mtd4: 00600000 00010000 "kernel-b"
mtd5: 002e0000 00010000 "user-data"
```

Read/write/erase from user-space:

```
[root@pa-mini:~]# nanddump /dev/mtd2 > my-dtb.bin     # back up the DTB
[root@pa-mini:~]# flash_erase /dev/mtd3 0 0           # erase kernel-A slot
[root@pa-mini:~]# nandwrite -p /dev/mtd3 zImage       # program kernel
[root@pa-mini:~]# flashcp -v new-dtb.dtb /dev/mtd2    # erase+write atomically
```

For U-Boot env on `mtd1`:

```
[root@pa-mini:~]# cat /etc/fw_env.config
# Device         Offset    Env size  Sector size
/dev/mtd1        0x0       0x10000   0x10000

[root@pa-mini:~]# fw_setenv bootcmd 'sf probe; sf read ${loadaddr} 0x120000 0x600000; bootz'
[root@pa-mini:~]# fw_printenv bootcmd
bootcmd=sf probe; sf read ${loadaddr} 0x120000 0x600000; bootz
```

## 64.9  XIP from QSPI

NOR's signature trick: **eXecute In Place**. The CPU reads instructions directly from QSPI without first copying them to DRAM. i.MX6ULL QSPI maps to a memory window (typically at 0x60000000) where reads transparently fetch from the flash.

- **Pro**: smaller RAM footprint. faster boot (no copy).
- **Con**: slow (max ~50 MB/s vs. DDR3's ~800 MB/s). higher power. instruction-cache misses are expensive.

In practice on i.MX6ULL, XIP is used only for U-Boot (small, fast-boot critical). The kernel and rootfs always run from DRAM. We covered XIP in detail in Ch 11.
> **MCU bridge:** Think of the rootfs as the firmware image's file-backed runtime environment. On an MCU you link everything into flash. On Linux, programs and config live in this mounted tree.
**rootfs** - root filesystem, the directory tree mounted at / that contains /bin, /etc, /dev, and libraries.

## 64.10  Boot from QSPI NOR

U-Boot config sets where to load from:

```
boot_qspi=sf probe; \
  sf read 0x80800000 0x120000 0x600000; \
  sf read 0x83000000 0x110000 0x10000; \
  bootz 0x80800000 - 0x83000000

bootcmd=run boot_qspi
```

- `sf probe` initialises the QSPI controller (U-Boot's own driver).
- `sf read <ram_addr> <flash_offset> <length>` copies from QSPI to RAM.
- `bootz <kernel> - <dtb>` boots.

For A/B updates, define `boot_qspi_a` and `boot_qspi_b` with different `<flash_offset>` values. a boot counter (`fw_setenv boot_count`) + an A/B flag selects which slot.

## 64.11  Lab

1. **JEDEC ID from i2c-tools-style poke.** Without your driver loaded, use raw SPI via `/dev/spidev*` to send `0x9F` and read 3 bytes. Confirm the ID matches your chip.
2. **Build and load `myflash.ko`.** Confirm JEDEC log in dmesg. read sector 0. erase + write + verify cycle.
3. **Compare timings.** Add ktime measurement around a 4-KB read and a 256-B page program. Compare against the mainline driver via `flashcp` on an equivalent area.
4. **Multi-page write bug demo.** Modify `myflash.c`'s `mf_fops_write` to *skip* the page-boundary split — write `count` bytes in one transfer instead. Try writing 300 bytes starting at offset 200. observe the wrap-around to offset 0 of the same page. Restore the split.
5. **Switch to the mainline driver.** Unload `myflash`. bind the same chip with `winbond,w25q128`. verify MTD partitions appear. Run `flashcp`.
6. **Read out the entire chip (mainline).** `nanddump -f all-flash.bin /dev/mtdblock0`. Compare expected size.

## 64.12  Pitfalls

- **Forgetting `write-enable`.** Every write/erase silently no-ops. Status register's WEL bit (bit 1) tells you if write-enable is currently set. Check there if writes mysteriously don't take.
- **Writing without erasing first.** NOR can only flip 1→0. Writing 0xAA to an erased (0xFF) byte gives 0xAA. Writing 0x55 over that 0xAA gives `0xAA & 0x55 = 0x00`, not 0x55. Always erase the sector first.
- **Page-boundary wrap.** Page program wraps within a 256-B page. The split-at-page-boundary loop is mandatory.
- **Status-poll forgotten.** Issuing the next command before BUSY clears = silent failure or chip-state corruption. Always wait.
- **Quad mode enable.** Some chips need their QE (Quad Enable) status bit set before quad-IO commands work. The `spi-nor` driver handles this for known chips. with `"jedec,spi-nor"` only it may not. Symptom: garbage when using quad-mode commands. Add the specific compatible.
- **4-byte addressing for > 16 MB.** Chips > 16 MB need 4 address bytes. The third address byte (high) of a 3-byte command becomes part of the data sent to the chip — silent corruption at offsets > 16 MB. The mainline driver auto-switches via `0xB7` (enter 4-byte mode). Old U-Boots may not.
- **Partition off the chip.** A typo in `reg = <offset size>` past the chip end. Kernel warns. verify dmesg.
- **U-Boot env partition mismatch with `fw_env.config`.** Both reference the same offset. If they disagree, `fw_setenv` writes to areas U-Boot expects to be unwritten. Always cross-check.
- **U-Boot env wear.** Each `saveenv` erases + writes the env sector (~50 ms wear cycle). NOR rated 100k cycles. If your boot script `saveenv`s every boot, you wear out in months. Use `redundant_env` (two ping-ponged copies) or avoid auto-saving.

## 64.13  Going deeper

- **`drivers/mtd/spi-nor/core.c`** — read it cover to cover. ~2000 lines. Notice how `spi_nor_read`, `spi_nor_write_data`, `spi_nor_erase_sector` map to the same protocol the from-scratch driver implements.
- **`drivers/mtd/spi-nor/winbond.c`** — the parameter table for your chip. Compare its `n_sectors`, `page_size`, `flags` against the datasheet.
- **`drivers/spi/spi-fsl-qspi.c`** — i.MX QSPI controller driver. Note how it uses an LUT (look-up table) of pre-baked command sequences to accelerate.
- **`Documentation/devicetree/bindings/mtd/jedec,spi-nor.yaml`** — DT binding details.
- **JEDEC SFDP standard (JESD216)** — Serial Flash Discoverable Parameters. The runtime discovery protocol the mainline driver uses for chips not in its static database.
- **W25Q128JV datasheet**, **MX25L25645G datasheet**, **MT25Q datasheet** — protocol reference for the three chips. The command table is on page 1 of each.

> Next chapter: **Chapter 65 — I²C / SPI EEPROM.** For when you need just a few KB of persistent storage. Same depth: protocol on the wire, the `at24` driver's internals, a from-scratch I²C-EEPROM driver, then DT enablement.
