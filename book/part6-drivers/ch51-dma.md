---
chapter: 51
title: DMA
part: VI — Driver development
estimated_pages: 18
status: draft
---

# Chapter 51 — DMA

> **What:** Linux's **`dmaengine`** framework — the portable way to ask a hardware DMA controller to move bytes between memory and a peripheral (or memory and memory) without involving the CPU between start and completion. By the end you'll have an SPI or UART driver that hands off a 4 KB transfer to the SDMA controller and goes to sleep until the completion callback wakes it.
> **Why:** the CPU is a terrible bulk-data mover. Sustained 10 Mbps of SPI traffic eats a chunk of i.MX6ULL's CPU when each byte requires an IRQ; the SDMA controller does it at zero CPU cost. Any driver that streams data — SPI, I²S audio, CSI camera, LCDIF, eMMC — uses DMA. Knowing the dmaengine consumer API turns "this driver is incomprehensible" into "this driver is a textbook dmaengine consumer."
> **Focus:** **the four-step ritual** — request a channel, configure direction & widths, prepare a descriptor, submit + issue + wait. Once you can mentally walk those four steps for any peripheral, every DMA driver in the kernel looks like a variation on one theme.

## 51.1  When and why

i.MX6ULL has a Smart DMA controller (**SDMA**) — a programmable peripheral DMA engine separate from the Cortex-A7. It runs little "scripts" that move data between system DRAM and peripheral FIFOs (UART RX, SPI TX, I²S, etc.), interrupting the CPU only on completion or error.

Without DMA, an SPI driver writes one byte to TX, waits for "TX empty," writes the next byte — at a few MHz that's tens of thousands of IRQs per second. With DMA, you tell SDMA "move these 4096 bytes to SPI TX, then notify me." Zero CPU between start and end.

The trade-off:
- **Setup cost.** Configuring an SDMA transfer costs ~1 µs. For 4-byte transfers, PIO is faster.
- **Memory pinning.** DMA needs physically-contiguous, cache-coherent buffers. `dma_alloc_coherent` (slower, smaller pool) or `dma_map_single` (faster, manages cache) — Ch 4's MMU/cache material matters here.
- **Debug pain.** A misconfigured DMA writes to random memory. Bugs are harder to diagnose than PIO bugs.

Rule of thumb: use DMA for transfers ≥ 64 bytes, polling/PIO for shorter.

## 51.2  The two halves of dmaengine

```
   driver (SPI controller, UART, sound, etc.)
        │  dma_request_chan, dmaengine_prep_*, dmaengine_submit, dma_async_issue_pending
        ▼
   ┌──────────────────────────────────────────────────────────┐
   │   dmaengine core                                          │
   │   - channel allocator (round-robin among free channels)   │
   │   - descriptor management                                 │
   │   - completion callbacks                                  │
   └──────────────────────────────────────────────────────────┘
        │
        ▼
   provider (SDMA controller driver — drivers/dma/imx-sdma.c)
        │ MMIO + IRQ
        ▼
   hardware
```

You don't write a provider unless you're porting Linux to new SoC silicon. You write *consumers*: drivers that request a channel and submit transfers.

## 51.3  Device tree — declaring DMA channels for a peripheral

A peripheral that wants DMA declares it in DT via the standard `dmas` + `dma-names` pair:

```dts
&ecspi3 {
    pinctrl-names = "default";
    pinctrl-0 = <&pinctrl_ecspi3>;
    dmas = <&sdma 7 7 1>, <&sdma 8 7 2>;
    dma-names = "rx", "tx";
    status = "okay";
};
```

Each `<&sdma N M K>` triple is provider-specific. For i.MX SDMA: `<&sdma <channel> <type> <priority>>`. `channel` and `type` come from the SDMA event-mux table (e.g., ECSPI3 RX = event 7); the SoC datasheet has the mapping.

`dma-names` gives each channel a *symbolic* name; drivers ask for `"rx"` or `"tx"` (not channel number 7). Same pattern as PWM and clocks.

## 51.4  The four-step ritual

In a peripheral driver's probe, plus the runtime transfer path:

### Step 1 — Request the channel

```c
struct dma_chan *rx_chan, *tx_chan;

rx_chan = dma_request_chan(&pdev->dev, "rx");
if (IS_ERR(rx_chan))
    return dev_err_probe(&pdev->dev, PTR_ERR(rx_chan), "no RX dma\n");

tx_chan = dma_request_chan(&pdev->dev, "tx");
if (IS_ERR(tx_chan)) {
    err = PTR_ERR(tx_chan);
    goto release_rx;
}
```

Returns a `struct dma_chan *` — your handle. Don't forget `dma_release_channel(chan)` in remove (or use the `devm_` style: `devm_get_free_pages` etc. don't have a DMA equivalent for channel requests, so manual cleanup).

### Step 2 — Configure slave parameters

For peripheral DMA ("slave" DMA — meaning the engine is slave to your peripheral's pacing), tell the engine where the peripheral FIFO is and how wide each transfer is:

```c
struct dma_slave_config cfg = {
    .direction       = DMA_DEV_TO_MEM,            /* receive */
    .src_addr        = peripheral_phys + RX_FIFO,
    .src_addr_width  = DMA_SLAVE_BUSWIDTH_1_BYTE,
    .src_maxburst    = 1,
};
dmaengine_slave_config(rx_chan, &cfg);

cfg.direction      = DMA_MEM_TO_DEV;
cfg.dst_addr       = peripheral_phys + TX_FIFO;
cfg.dst_addr_width = DMA_SLAVE_BUSWIDTH_1_BYTE;
cfg.dst_maxburst   = 1;
dmaengine_slave_config(tx_chan, &cfg);
```

Set once at probe (or whenever it changes).

### Step 3 — Prepare a descriptor

For each transfer:

```c
struct dma_async_tx_descriptor *desc;
dma_cookie_t cookie;
dma_addr_t  dma_buf_phys;

dma_buf_phys = dma_map_single(&pdev->dev, my_buffer, len, DMA_FROM_DEVICE);
if (dma_mapping_error(&pdev->dev, dma_buf_phys))
    return -ENOMEM;

desc = dmaengine_prep_slave_single(rx_chan, dma_buf_phys, len,
                                    DMA_DEV_TO_MEM,
                                    DMA_PREP_INTERRUPT | DMA_CTRL_ACK);
if (!desc) {
    dma_unmap_single(&pdev->dev, dma_buf_phys, len, DMA_FROM_DEVICE);
    return -ENOMEM;
}

desc->callback        = rx_done_cb;
desc->callback_param  = priv;
```

`dma_map_single` pins the buffer in physical memory, flushes the CPU cache appropriately, and returns the bus-visible physical (or IOVA) address. The kernel handles the cache dance — your CPU might have modified the buffer, so caches are flushed *to memory* before DMA reads from it (`DMA_TO_DEVICE`), or invalidated *from memory* after DMA writes to it (`DMA_FROM_DEVICE`).

For scatter-gather (multiple non-contiguous chunks): `dmaengine_prep_slave_sg(chan, sg_list, sg_count, dir, flags)`.

For ring-buffer continuous capture (audio, CSI): `dmaengine_prep_dma_cyclic(chan, dma_addr, total, period, dir, flags)`.

### Step 4 — Submit, issue, wait

```c
cookie = dmaengine_submit(desc);

dma_async_issue_pending(rx_chan);

/* In rx_done_cb (runs in tasklet context): */
static void rx_done_cb(void *param)
{
    struct my_priv *p = param;
    dma_unmap_single(p->dev, p->dma_buf_phys, p->len, DMA_FROM_DEVICE);
    complete(&p->rx_done);     /* wake the waiter */
}

/* In the original context, wait: */
wait_for_completion(&p->rx_done);
```

`dmaengine_submit` queues the descriptor; `dma_async_issue_pending` actually kicks the engine. Most drivers separate them so they can queue multiple descriptors before starting (chained transfers).

The callback runs in *tasklet context* — no sleeping, no `kmalloc(GFP_KERNEL)`, no `mutex_lock`. Use it to release the mapping and signal a completion that a sleeping waiter can pick up.

## 51.5  Cyclic transfers (audio, camera)

For continuous streaming where the same buffer is read in a circle:

```c
/* Allocate a coherent ring buffer of 8 periods × 4096 bytes */
size_t period = 4096, total = 8 * period;
void *cpu_buf;
dma_addr_t dma_buf_phys;

cpu_buf = dma_alloc_coherent(&pdev->dev, total, &dma_buf_phys, GFP_KERNEL);

desc = dmaengine_prep_dma_cyclic(rx_chan, dma_buf_phys, total, period,
                                  DMA_DEV_TO_MEM,
                                  DMA_PREP_INTERRUPT | DMA_CTRL_ACK);
desc->callback       = period_elapsed_cb;
desc->callback_param = priv;

dmaengine_submit(desc);
dma_async_issue_pending(rx_chan);
```

The callback fires once per *period* — every 4096 bytes. User-space drains via separate API (ALSA's snd_pcm_indirect or similar).

`dma_alloc_coherent` allocates from the kernel's coherent-DMA pool — guaranteed cache-coherent (writes from the CPU are immediately visible to DMA and vice versa), at the cost of being uncached for the CPU. For audio ring buffers this is perfect.

## 51.6  Memory-to-memory DMA

For pure memcpy acceleration:

```c
struct dma_chan *chan = dma_request_chan_by_mask(&dma_cap_zero(mask));
dma_cap_set(DMA_MEMCPY, mask);

desc = dmaengine_prep_dma_memcpy(chan, dst_dma, src_dma, len, flags);
/* ... submit, issue, wait ... */
```

Memcpy DMA is rare on i.MX6ULL (CPU is fast enough at small sizes). Useful on bigger SoCs where the DMA engine has multiple lanes and can outpace a single CPU.

## 51.7  Cache coherency — the trap

The trap that catches everyone: you populate a buffer in user-space, give the kernel pointer to your driver, your driver DMAs from it — and DMA reads stale data because the CPU's recent writes are still in L1 cache.

`dma_map_single(dev, ptr, size, DMA_TO_DEVICE)` solves this by **flushing** (writing back) the relevant cache lines to memory before the DMA reads them. The matching `dma_unmap_single` does nothing for `TO_DEVICE`; for `FROM_DEVICE`, it **invalidates** the cache so subsequent CPU reads come from the (DMA-written) memory.

The kernel handles this for you *if you use the APIs correctly*. If you cast a pointer to `dma_addr_t` and skip the map call, you'll get sporadic data corruption that depends on whether the cache line happened to be evicted between operations. **Always use dma_map_* or dma_alloc_coherent — never cast.**

## 51.8  Lab

1. **Inspect existing DMA users.** Read `drivers/spi/spi-imx.c` — find the dma_request_chan, slave_config, prep_slave_single, submit, issue, callback. Note how the driver decides PIO vs DMA based on transfer length.
2. **Write a memory-to-memory test.** Allocate two 4 KB buffers, prepare a memcpy descriptor, submit, wait, verify content matches. Compare timings against `memcpy()` for sizes 64 B → 64 KB.
3. **Enable SPI-with-DMA on your platform.** Add `dmas` + `dma-names` to your `&ecspi3` node, watch dmesg for "DMA acquired" or similar. Repeat your SPI loopback from Ch 47 with a 4 KB transfer; verify it works.
4. **Measure CPU savings.** Use `top` or `perf` while running a 1 MB SPI loopback in tight loop, with and without DMA. The DMA case should idle the CPU between IRQs.
5. **Provoke a cache bug.** Skip the dma_map_single call (cast directly). Observe corruption. Add the map call back; observe correctness.
6. **Cyclic transfer prototype.** Sketch a fake audio capture: a kernel thread fills a ring buffer; a cyclic DMA copies it to a pretend FIFO; each callback prints a count. Verify smoothness.

Commit code to `code/ch51-dma/`.

## 51.9  Pitfalls

- **Forgetting to call `dma_async_issue_pending`.** Descriptor sits queued; callback never fires; driver hangs. The split between submit and issue is intentional (for chaining) but easy to get wrong.
- **Wrong direction in dma_map_single.** `TO_DEVICE` for outgoing (driver writes, DMA reads); `FROM_DEVICE` for incoming (DMA writes, driver reads); `BIDIRECTIONAL` if both. Wrong direction = stale data.
- **Buffer alignment / size constraints.** Some DMA engines require power-of-2 sizes or specific alignment. Check the engine's `device_caps`.
- **DMA on stack buffers.** `dma_map_single(&stack_var, ...)` — the stack isn't necessarily DMA-able memory. Use `kmalloc(GFP_DMA | GFP_KERNEL, ...)` or `dma_alloc_coherent`.
- **Sleeping in the callback.** Tasklet context. Use `complete()`, `wake_up()`, or schedule a workqueue.
- **Not releasing the channel.** `dma_release_channel` in remove (or DMA channels leak; eventually you run out).
- **Two consumers requesting the same channel.** First wins; second fails with -EBUSY. DT specifies which event line each peripheral uses; conflicts mean rewiring.
- **Cache flushing on bidirectional transfers.** Subtle. For `BIDIRECTIONAL` the kernel flushes before *and* invalidates after — slower. Use one direction whenever possible.

## 51.10  Going deeper

- **`Documentation/driver-api/dmaengine/`** — the dmaengine framework documentation. `client.rst` is the consumer guide.
- **`drivers/dma/imx-sdma.c`** — the i.MX SDMA controller driver. Big (~2500 lines). Worth skimming once.
- **`drivers/spi/spi-imx.c`** — a clean dmaengine consumer.
- **`sound/soc/fsl/imx-sdma.c`** + `imx-pcm-dma.c` — audio's cyclic DMA usage.
- **`Documentation/core-api/dma-api-howto.rst`** — DMA buffer ownership rules and cache coherency, the canonical reference.

> Next chapter: **Chapter 51A — Watchdog.** A simple but critical subsystem; every shipping product needs to recover automatically from a hung kernel or stuck application.
