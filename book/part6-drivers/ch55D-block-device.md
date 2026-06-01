---
chapter: 55D
title: Block device drivers
part: VI — Driver development (supplementary v1.1)
estimated_pages: 12
status: draft
---

# Chapter 55D — Block device drivers

> **What:** the **block** layer — `gendisk`, request queues, `blk-mq` (multi-queue block), bio. Most embedded systems consume block devices (eMMC, SD card via MMC subsystem; raw NAND via MTD+UBI). Occasionally you need to *write* one — typically a RAM disk, a loop-style virtual device, or a translation layer over a custom storage chip.
> **Why:** less common to write than char drivers, but worth knowing because (a) the request-queue model differs significantly from "byte stream" and (b) understanding block lets you debug performance of any storage layer above (filesystem latency, fsync behavior).
> **Focus:** **bio is the universal request**. A user-space `read(fd, ..., 4096)` becomes one or more `struct bio`s submitted to a `gendisk`. Drivers either submit one I/O per bio or batch into hardware-specific request structures.

## 55D.1  The path from `read()` to your driver

```
   user-space: read(fd, buf, 8192)
        │
   VFS: dispatches via filesystem (ext4, ubifs, ...) → submit_bio()
        │
   block layer: builds a struct bio, schedules
        │
   blk-mq: per-CPU multi-queue; merges adjacent bios when possible
        │
   driver: receives a queue_rq() callback per request
        │
   hardware
```

`bio` describes: which device, what direction (read/write), what sector range, and a vector of memory buffers. Drivers can process bios one at a time, or convert them to hardware-native request structures.

## 55D.2  Minimal: RAM disk

```c
#include <linux/blk-mq.h>
#include <linux/blkdev.h>
#include <linux/genhd.h>

#define DISK_SIZE_MB 64
#define SECTOR_SIZE  512

struct ramdisk {
    void *data;
    sector_t capacity_sectors;
    struct gendisk *disk;
    struct blk_mq_tag_set tag_set;
    struct request_queue *queue;
};

static blk_status_t ramdisk_queue_rq(struct blk_mq_hw_ctx *hctx,
                                      const struct blk_mq_queue_data *bd)
{
    struct request *req = bd->rq;
    struct ramdisk *r = req->q->queuedata;
    struct bio_vec bvec;
    struct req_iterator iter;
    sector_t pos = blk_rq_pos(req);

    blk_mq_start_request(req);

    rq_for_each_segment(bvec, req, iter) {
        void *user_buf = kmap_local_page(bvec.bv_page) + bvec.bv_offset;
        void *disk_buf = r->data + pos * SECTOR_SIZE;

        if (rq_data_dir(req) == READ)
            memcpy(user_buf, disk_buf, bvec.bv_len);
        else
            memcpy(disk_buf, user_buf, bvec.bv_len);

        kunmap_local(user_buf);
        pos += bvec.bv_len / SECTOR_SIZE;
    }

    blk_mq_end_request(req, BLK_STS_OK);
    return BLK_STS_OK;
}

static const struct blk_mq_ops ramdisk_mq_ops = {
    .queue_rq = ramdisk_queue_rq,
};

static const struct block_device_operations ramdisk_fops = {
    .owner = THIS_MODULE,
};

static int __init ramdisk_init(void)
{
    struct ramdisk *r = kzalloc(sizeof(*r), GFP_KERNEL);
    if (!r) return -ENOMEM;

    r->capacity_sectors = (DISK_SIZE_MB * 1024 * 1024) / SECTOR_SIZE;
    r->data = vmalloc(DISK_SIZE_MB * 1024 * 1024);
    if (!r->data) { kfree(r); return -ENOMEM; }

    r->tag_set.ops          = &ramdisk_mq_ops;
    r->tag_set.nr_hw_queues = 1;
    r->tag_set.queue_depth  = 128;
    r->tag_set.numa_node    = NUMA_NO_NODE;
    r->tag_set.cmd_size     = 0;
    r->tag_set.flags        = BLK_MQ_F_SHOULD_MERGE;
    r->tag_set.driver_data  = r;
    blk_mq_alloc_tag_set(&r->tag_set);

    r->disk = blk_mq_alloc_disk(&r->tag_set, r);
    r->queue = r->disk->queue;
    r->queue->queuedata = r;

    strscpy(r->disk->disk_name, "myram0", DISK_NAME_LEN);
    r->disk->major = 240;
    r->disk->first_minor = 0;
    r->disk->minors = 1;
    r->disk->fops = &ramdisk_fops;
    set_capacity(r->disk, r->capacity_sectors);

    add_disk(r->disk);
    return 0;
}
```

After `insmod`:

```
[root@pa-mini:~]# ls /dev/myram0
[root@pa-mini:~]# mkfs.ext4 /dev/myram0
[root@pa-mini:~]# mount /dev/myram0 /mnt
```

## 55D.3  Real block drivers — what's added

The ramdisk above is minimal. Production block drivers add:

- **DISCARD / TRIM** (`BLK_STS_OK` on `REQ_OP_DISCARD`) — letting the device free unused sectors. eMMCs and SSDs care.
- **FLUSH** (`REQ_OP_FLUSH`) — ensure writes are durable. Critical for ACID-style apps.
- **Zoned device support** (`REQ_OP_ZONE_*`) — SMR drives, ZNS NVMe.
- **Read-only handling** — block O_WRONLY when device is RO.
- **Partition table parsing** — automatic GPT/MBR scan, creating partitions as separate minors.

The kernel's MMC subsystem is the canonical example for SD/eMMC. Read `drivers/mmc/core/`.

## 55D.4  Performance metrics

```
[root@pa-mini:~]# dd if=/dev/myram0 of=/dev/null bs=1M count=64
67108864 bytes (64 MB, 64 MiB) copied, 0.04 s, 1.7 GB/s

[root@pa-mini:~]# fio --name=randread --filename=/dev/myram0 \
  --rw=randread --bs=4k --runtime=10 --time_based --ioengine=psync
   ...
   read: IOPS=350k, BW=1366MiB/s ...
```

For comparison, an eMMC HS200 hits ~120 MB/s sequential, ~10k IOPS random. NAND flash via UBI hits ~10 MB/s.

## 55D.5  Lab

1. **Build the ramdisk.** Load, format, mount, write a file, unmount, reload, observe file persistence (RAM-backed only across reload, not reboot).
2. **Add error injection.** Make every 100th write return `BLK_STS_IOERR`; observe filesystem behavior (ext4 remounts read-only).
3. **Measure throughput.** dd + fio at various block sizes; build a throughput curve.
4. **Inspect with `iostat -x 1`.** While running fio, watch await, %util, IOPS.
5. **Add a sysfs attribute.** Expose stats: total reads, total writes, bytes transferred.

## 55D.6  Pitfalls

- **Forgetting to `blk_mq_start_request`.** Driver does work, calls `end_request`, but the request was never marked started — corrupted statistics, possible deadlock.
- **Block-aligned constraint violations.** Modern kernels require sector-aligned bios. Requests smaller than a sector get split. Honor `bvec` offsets.
- **Holding spinlocks across long memcpy.** `queue_rq` is expected to return quickly. Defer long work to a workqueue.
- **`mkfs.ext4` complaints about a tiny disk.** Some FS minimums apply (~8 MB for ext4 with default settings).
- **Unloading while disk is mounted.** Kernel panics. Always `umount` before `rmmod`.

## 55D.7  Going deeper

- **`Documentation/block/`** — block layer documentation.
- **`drivers/block/`** — many real block drivers, mostly readable.
- **`drivers/block/loop.c`** — the loop driver, a good "real but simple" example.
- **`drivers/mmc/core/block.c`** — MMC block device.
- **LDD3 Chapter 16** — block drivers (some details outdated, but the model is the same).

> Next chapter: **Chapter 55E — WiFi + wpa_supplicant.** Bringing up an SDIO or USB WiFi module on Linux, end-to-end.
