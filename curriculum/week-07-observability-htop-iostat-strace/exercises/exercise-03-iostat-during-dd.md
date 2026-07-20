# Exercise 3 — `iostat -x 1` during a `dd` write

**Time:** 30-45 minutes.
**Goal:** Induce a sustained disk write with `dd`. Watch the device saturate in `iostat -x 1`. Identify which column is the saturation signal. Repeat with different block sizes and with the page cache primed versus cold.
**Prerequisites:** Lecture 3 §1 read. `sysstat` installed (`sudo apt install sysstat` or `sudo dnf install sysstat`).

Bash Yellow: `dd` of multi-GB writes wears SSDs. Run this exercise once or twice; do not loop it. Clean up the test files (`rm /tmp/big-write.bin`) after.

---

## Why this exercise

Disk is the most commonly misdiagnosed performance bottleneck. The `iostat` output has 17 columns and most engineers learn to read maybe four of them. The exercise is to make each column light up in turn so you know which one to trust under which conditions.

The single most important thing you will learn: **on modern hardware, `%util` is a misleading number**. The reliable saturation signal is `aqu-sz` (queue depth) and `await` (latency).

---

## Part 1 — Setup

You need three terminals (or `tmux` panes).

- **Terminal A** — where you run `dd`.
- **Terminal B** — where `iostat -x 1` streams.
- **Terminal C** — for one-off commands (`pidstat -d`, `cat /proc/<pid>/io`, etc.).

Identify your target disk:

```bash
lsblk
```

Find the device that `/tmp` lives on:

```bash
df /tmp
```

On most Linux installs `/tmp` is on the root filesystem (`/dev/sda` or `/dev/nvme0n1` or similar). Note the device name — `iostat` reports per-device, and you want to know which row to read.

Check the device type:

```bash
cat /sys/block/$(lsblk -no PKNAME $(df --output=source /tmp | tail -1) | head -1)/queue/rotational
# 0 = SSD / NVMe / virtual disk
# 1 = rotating disk
```

Knowing whether the device is rotating or solid-state matters for interpreting `%util` (Lecture 3 §1.1).

Start `iostat` in Terminal B:

```bash
iostat -xz 1
```

`-x` extended; `-z` skip devices with zero activity. You should see your system disk(s); on an idle system, the device rows scroll by with mostly zeros.

---

## Part 2 — A baseline `dd` write

In Terminal A:

```bash
# Write 500 MB to a file, default block size (512 bytes)
dd if=/dev/zero of=/tmp/big-write.bin bs=512 count=1000000
```

This is intentionally slow — 512-byte blocks force one syscall per block. Watch Terminal B.

You should see the relevant device row change:

```
Device  r/s  w/s  rkB/s   wkB/s  r_await  w_await  aqu-sz  rareq-sz  wareq-sz  %util
sda     0.0  ...  0.0     ...      0.00     0.50    ...       0.00      0.50    ...
```

Bandwidth (`wkB/s`) depends on your hardware. On a SATA SSD you might see 100-200 MB/s; on a fast NVMe, 1-3 GB/s. On a 7200 RPM HDD, 30-100 MB/s sequential.

When `dd` finishes, it prints a summary line:

```
1000000+0 records in
1000000+0 records out
512000000 bytes (512 MB, 488 MiB) copied, 2.3 s, 222 MB/s
```

The "222 MB/s" is the workload's measured throughput. Compare to what `iostat` showed.

---

## Part 3 — Different block sizes

The same data with different block sizes shows a dramatic syscall-count difference (similar to Exercise 2 §2.1).

```bash
# 1 MiB blocks — fewer syscalls
dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500
```

Output:

```
500+0 records in
500+0 records out
524288000 bytes (524 MB, 500 MiB) copied, 0.65 s, 806 MB/s
```

Notice: the same amount of data but **much faster**, because the number of `write` syscalls fell from 1,000,000 to 500. The disk has the same throughput; the syscall overhead dominated the slow version.

Run with `bs=4K` (typical Linux page size):

```bash
dd if=/dev/zero of=/tmp/big-write.bin bs=4K count=128000
```

And `bs=64K`:

```bash
dd if=/dev/zero of=/tmp/big-write.bin bs=64K count=8000
```

Record the throughput from each `dd` summary line. Plot in your notes the throughput as a function of block size; the curve typically rises sharply from 512 B to 4 KiB, levels off around 64 KiB-1 MiB, and may decline very slightly at multi-MB block sizes (because the kernel must allocate a large kernel buffer).

The lesson: **block size matters**. Real applications that use `read()` and `write()` should pick a block size of at least 4 KiB; 64 KiB is a good default for sequential workloads.

---

## Part 4 — `iostat` columns under sustained write

Run a longer write so you can read `iostat` while it streams:

```bash
# Terminal A
dd if=/dev/zero of=/tmp/big-write.bin bs=64K count=80000   # ~5 GB
```

This takes a few to several seconds depending on disk. In Terminal B, `iostat -xz 1` shows multiple seconds of activity. Take a screenshot or copy the rows.

The columns to read, in order of importance:

### 4.1 `aqu-sz` (queue depth)

The number of IOs the device has outstanding on average. On a saturated rotating disk this is 1-2. On a saturated SATA SSD it is 4-32 (the device's queue depth). On a saturated NVMe it can be 64-128.

**If `aqu-sz` is steadily growing, the workload is generating IOs faster than the device can complete them.** That is saturation. If `aqu-sz` is stable around the device's design queue depth, the device is busy but keeping up.

### 4.2 `w_await` (write latency)

Mean wait time per write, including time in the queue, in milliseconds.

- Rotating disk: 5-15 ms is normal; >50 ms suggests saturation.
- SATA SSD: 0.1-1 ms is normal; >5 ms suggests saturation.
- NVMe: <0.5 ms is normal; >2 ms is saturating.

If `w_await` is climbing, the device is taking longer to service each write — which means it is either busy or sick.

### 4.3 `wkB/s` (write bandwidth)

The actual throughput in KiB/s. Compare to the device's spec sheet. A SATA SSD doing 400-500 MB/s sequential write is near its spec; one doing 50 MB/s is either being sequential-written-to-cache-then-stalled or has a workload problem.

### 4.4 `%util` — the trap column

The fraction of the sample where the device had at least one IO in flight. On a rotating disk this directly correlates with saturation (the single head can only do one thing). On modern storage it saturates near 100 % long before the device is actually saturated.

You will probably see `%util` 95-100 % during `dd`. Do not interpret that as "the device is at its limit." Read `aqu-sz` and `w_await` to find out.

---

## Part 5 — The page cache effect

Buffered writes go to the page cache first, then to disk asynchronously. The cache effect is enormous: a write that goes to free page cache appears instant; the actual disk IO happens later (or never, if the data is overwritten before being flushed).

Repeat the earlier `dd` with a smaller size, several times in succession, watching memory:

```bash
# Terminal C
free -h
sync   # flush any pending writes from previous dd runs
echo 3 | sudo tee /proc/sys/vm/drop_caches   # drop page cache (privileged)
free -h
```

After dropping caches, `buff/cache` should fall. Now run the write:

```bash
# Terminal A
dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500
```

Watch `iostat` while it runs. Then check memory:

```bash
free -h
```

The `buff/cache` column should rise by roughly 500 MiB. The kernel held the just-written data in cache. The actual disk write may not have completed yet — it is queued for asynchronous flush.

Force flush:

```bash
sync
```

`sync` blocks until all dirty pages are written. After `sync`, the data is on disk. The wall-clock time for `sync` is your real disk-write latency for that 500 MiB.

This is why "the file was written in 0.6 seconds" reported by `dd` is sometimes a lie: the data went to cache, not to disk, and the disk catches up later. For honest write measurements:

```bash
dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500 conv=fdatasync
```

`conv=fdatasync` calls `fdatasync` at the end of `dd`'s work — it does not return until the data is on disk. The `dd` summary now reflects the true disk-write time.

Run both with and without `conv=fdatasync` and compare. You should see a noticeable difference (sometimes 2-5×) on systems with plenty of RAM.

---

## Part 6 — Per-process IO

While a `dd` is running, identify it from the per-process IO view:

```bash
# Terminal C
pidstat -d 1
```

You should see a row for `dd` with `kB_wr/s` near the same number `iostat` shows for `wkB/s`. The match confirms that `dd` is the writer.

For the `/proc` view:

```bash
# Find the PID
pgrep -x dd
# Read its IO counters
cat /proc/$(pgrep -x dd)/io
```

You will see `write_bytes` growing with each read.

The point of this part: `iostat` tells you the device is busy; `pidstat -d` and `/proc/<pid>/io` tell you **which process** is making it busy. The first is the symptom; the second is the cause.

---

## Part 7 — Acceptance criteria

By the end of this exercise you should have, in your notes:

- [ ] The device name you wrote to and whether it is rotating or solid-state.
- [ ] `iostat -x 1` output captured during a `bs=1M` `dd`, with one annotated column for `aqu-sz`, one for `w_await`, one for `wkB/s`.
- [ ] A table of `dd` throughput at four block sizes (512 B, 4 KiB, 64 KiB, 1 MiB).
- [ ] Wall-clock times for `dd ... bs=1M count=500` with and without `conv=fdatasync`; a one-sentence comment on the difference.
- [ ] `pidstat -d 1` output during `dd` showing `dd` is the heavy writer.
- [ ] The result of `cat /proc/<dd-pid>/io` taken mid-write.
- [ ] One paragraph summarising which `iostat` column you would trust to declare "the disk is saturated" on this hardware, and why.

Save these to `~/c14-w07/exercise-03/notes.md`.

Cleanup:

```bash
rm /tmp/big-write.bin
```

---

## Pitfalls

- **`dd` and SSD wear.** Each repetition writes hundreds of MB to GB. Do not run this exercise in a loop; the exercise once or twice is harmless, but do not include `dd` in a daily benchmark cron.
- **The page cache hides the truth.** If you forget `conv=fdatasync`, `dd` reports cache-write speeds, not disk-write speeds. The fix is `conv=fdatasync` or `oflag=direct` (which bypasses the cache entirely).
- **Running on the same disk you are observing from.** If `iostat` writes its own output to the disk you are stressing, you are reading slightly inflated numbers. In practice the effect is negligible (a few KiB/s), but for forensic-grade work, observe from a different disk.
- **`iostat` first sample is averages-since-boot.** The first row from `iostat -x 1` is the average since the system booted, not the current second. Skip it; use the second and subsequent samples.

---

## Optional extensions

- Read from `/dev/zero` to `/dev/null` with `dd`. The disk is not involved; what does `iostat` show? (Nothing — `iostat` only reports block-device traffic, not pipe-to-pipe.) What does `vmstat`'s `bi`/`bo` show? (Also zero.)
- Run two `dd`s in parallel writing to the same disk. Watch `iostat`: does the total throughput double, half, or stay the same? On most storage it does *not* double — sequential workloads conflict.
- Use `oflag=direct` (bypass cache) and re-run the block-size experiment. With direct IO, small block sizes are much slower because the kernel cannot batch.
- Use `stress-ng --hdd 1 --hdd-bytes 1G --hdd-method seq-wr --hdd-write-size 1M --timeout 30s` for a calibrated load. Compare the `iostat` output to your `dd` runs.

---

*Solutions: [SOLUTIONS.md](./SOLUTIONS.md).*

*Next: the [challenges](../challenges/challenge-01-write-your-own-mini-htop.py).*
