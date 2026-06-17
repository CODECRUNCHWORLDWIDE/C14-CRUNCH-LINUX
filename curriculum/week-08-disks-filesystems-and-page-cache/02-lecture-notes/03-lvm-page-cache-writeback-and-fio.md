# Lecture 3 — LVM, the page cache, writeback, and `fio`

> *Two lectures in, you can take a disk, slice it, format it, and mount it. This lecture stretches the stack in two directions. **Up the stack**, into LVM — a layer between the partition and the filesystem that lets you pool, slice, resize, and snapshot. **Sideways into memory**, where the **page cache** sits between every read and every disk: a fast in-RAM copy of file pages that turns the second read of a file into a memory operation. We end with **dirty pages and writeback** (the part where the cache has to meet the disk), a short tour of **`fio`** (the canonical IO benchmark), and a beginner-aware mention of **`io_uring`** (the modern async-IO interface). With these three concepts the rest of Linux performance work becomes legible.*

---

## 1. LVM — Logical Volume Manager

LVM is a kernel layer (the device-mapper `dm-linear`, `dm-snapshot`, `dm-mirror`, `dm-thin` modules) plus a userspace toolset (`lvm2`) that lets you **pool block devices**, **slice the pool**, and **resize and snapshot the slices online**. It was added to the kernel around 2.4 (2001) and has been the default storage layer on most server distributions ever since.

### 1.1 The three objects: PV, VG, LV

The mental model:

```
                ┌──────────────────────────────────────────────┐
                │                Volume Group (VG)             │
                │                                              │
   /dev/sdb1 →  │  PV ─────┐                                    │
                │           ├─→ free pool of "physical extents"│
   /dev/sdc1 →  │  PV ─────┘                                    │
                │                                              │
                │  ┌─────────────┐    ┌─────────────┐          │
                │  │   LV "web"  │    │  LV "data"  │          │
                │  │   (50 GiB)  │    │  (200 GiB)  │          │
                │  └─────────────┘    └─────────────┘          │
                └──────────────────────────────────────────────┘
                          ↓                    ↓
                    /dev/mapper/    /dev/mapper/
                       vg-web          vg-data
```

- **Physical Volume (PV)** — a block device (usually a partition) prepared for use by LVM. `pvcreate /dev/sdb1` writes an LVM signature to the device.
- **Volume Group (VG)** — a pool of one or more PVs. `vgcreate data /dev/sdb1 /dev/sdc1` creates a VG named `data` containing the listed PVs. The VG is the unit you allocate from.
- **Logical Volume (LV)** — a slice of a VG presented as a block device. `lvcreate -L 50G -n web data` creates a 50 GiB LV named `web` in the VG `data`. The LV appears as `/dev/mapper/data-web` (and as a symlink `/dev/data/web`).

You **format the LV**, not the underlying PV. `mkfs.ext4 /dev/mapper/data-web` puts an ext4 filesystem on the LV; the filesystem sees a block device of exactly 50 GiB, no knowledge of LVM underneath.

### 1.2 Why use LVM

Four reasons, in order of how often each one saves the day:

1. **Online resize.** Need more space? `lvextend -L +50G -r /dev/data/web` adds 50 GiB to the LV **and resizes the filesystem on top** (the `-r` flag, since `lvm2` 2.02.108). No unmount. No downtime. Cannot do this on a raw partition.
2. **Snapshots for backup.** `lvcreate -L 10G -s -n web-snap /dev/data/web` creates a snapshot of the `web` LV at a moment in time. The snapshot is a copy-on-write view: it shows the LV as it was when the snapshot was taken, even as the original LV continues to be written. Mount the snapshot read-only, run `rsync` over it, and you have a consistent backup of a busy filesystem.
3. **Span multiple physical disks.** A VG can span any number of disks. An LV can be larger than any single disk. The kernel's device-mapper concatenates or stripes across them transparently.
4. **Decouple naming from physical location.** The LV `data-web` lives at the same `/dev/mapper/` path regardless of which physical device holds the bytes. Swap a failing disk, and the LV name does not change.

LVM costs you almost nothing in performance (a few percent on metadata-heavy workloads; nothing on bulk IO). The flexibility is almost always worth it. On a typical Linux server in 2026, the root filesystem is on an LV.

### 1.3 The four commands you actually run

```bash
# 1. Create a PV (a block device prepared for LVM)
sudo pvcreate /dev/sdb1

# 2. Create a VG (a pool of PVs)
sudo vgcreate data /dev/sdb1

# 3. Create an LV (a slice of the VG)
sudo lvcreate -L 50G -n web data

# 4. Format and mount as normal
sudo mkfs.ext4 -L web /dev/mapper/data-web
sudo mkdir -p /srv/web
sudo mount /dev/mapper/data-web /srv/web
```

And the four display commands:

```bash
pvs            # short summary of PVs
vgs            # short summary of VGs
lvs            # short summary of LVs
pvdisplay      # verbose
vgdisplay
lvdisplay
```

Example output:

```
$ sudo pvs
  PV         VG   Fmt  Attr PSize    PFree
  /dev/sdb1  data lvm2 a--  <100.00g <50.00g

$ sudo vgs
  VG   #PV #LV #SN Attr   VSize    VFree
  data   1   1   0 wz--n- <100.00g <50.00g

$ sudo lvs
  LV   VG   Attr       LSize   Pool Origin Data%
  web  data -wi-ao---- <50.00g
```

The attribute columns are a pithy summary; the canonical reference is `man 8 lvs` (the "FIELDS" section explains each character).

### 1.4 Extending an LV online

The most common LVM operation. You created a 50 GiB LV, you filled it up, you want more.

```bash
# Confirm there is free space in the VG.
sudo vgs data
# If not, add a disk to the VG first:
sudo pvcreate /dev/sdc1
sudo vgextend data /dev/sdc1

# Extend the LV by 20 GiB AND resize the filesystem on top.
sudo lvextend -L +20G -r /dev/data/web
```

The `-r` flag is the magic. It runs `resize2fs` (for ext4) or `xfs_growfs` (for xfs) or `btrfs filesystem resize max` (for btrfs) on the mounted filesystem, automatically, after the LV is extended. The whole operation is online; nothing is unmounted; the running application sees the new free space within seconds.

**Note**: `lvreduce` (shrinking an LV) is supported but **dangerous** because it requires the filesystem to be shrunk first (or you destroy data). ext4 can be shrunk only when unmounted. xfs **cannot be shrunk at all**. Practice: grow, never shrink.

### 1.5 Snapshots for backup

```bash
# Create a snapshot LV.
sudo lvcreate -L 10G -s -n web-snap /dev/data/web

# Mount it read-only.
sudo mkdir -p /mnt/web-snap
sudo mount -o ro /dev/data/web-snap /mnt/web-snap

# Back up.
sudo rsync -a /mnt/web-snap/ /backup/web/

# Tear down.
sudo umount /mnt/web-snap
sudo lvremove /dev/data/web-snap
```

Three notes:

- **The snapshot is sized for the changes you expect during its lifetime**, not the size of the source LV. A 10 GB snapshot of a 50 GB LV is enough as long as fewer than 10 GB of unique blocks are written to the source during the snapshot's life. If the snapshot fills up, it is **invalidated** and dropped. Size generously; remove the snapshot promptly.
- **The snapshot consumes some IO performance on the source LV** while it exists (every write to the source must be CoW'd into the snapshot first). For long-lived snapshots use btrfs or zfs; for short-lived backup snapshots, LVM is fine.
- **Snapshots are not a backup.** They are a point-in-time view. A snapshot does not protect against disk failure; the snapshot is on the same disks. The snapshot is a **technique** for taking a consistent backup of a busy filesystem; the backup itself must go to a different disk, host, or location.

### 1.6 LVM and the device-mapper

LVM does not invent its own kernel facilities; it sits on the kernel's **device-mapper** subsystem (`dm-*`). The device-mapper is a generic framework for stacking block-device transforms: LVM uses `dm-linear` (concatenation) and `dm-thin` (thin provisioning); `dm-crypt` provides full-disk encryption; `dm-cache` provides SSD-as-cache-for-HDD; `dm-integrity` provides checksumming.

You see the device-mapper output in `/dev/mapper/`:

```
$ ls /dev/mapper/
control  data-web  data-data  cryptroot
```

`data-web` is the LVM LV "web" in VG "data". `cryptroot` is a LUKS-encrypted block device. Both are the same kind of object (a dm-device); LVM is one of many uses of the underlying machinery.

Reference: `man 8 lvm` (umbrella), `man 8 pvcreate`, `man 8 vgcreate`, `man 8 lvcreate`, `man 8 lvextend`, kernel `Documentation/admin-guide/device-mapper/`.

---

## 2. The page cache — why your second `cat` is free

### 2.1 The fundamental observation

Run this on any Linux box with a moderately large file (say a few hundred MB):

```bash
# Cold: clear caches first (root required).
sudo sync
sudo sysctl vm.drop_caches=3

time cat /var/log/journal/$(ls /var/log/journal | head -1)/system.journal > /dev/null

# Warm: do not clear caches.
time cat /var/log/journal/$(ls /var/log/journal | head -1)/system.journal > /dev/null
```

The first `time` reports something like 0.5-2 seconds (depending on file size and disk). The second reports under 0.1 seconds. **The file did not change. The disk did not get faster. The kernel served the second read from RAM.**

This is the **page cache**: an in-kernel cache of file contents, organised by `(file, offset)` and indexed in a radix tree per inode. Every `read` of a regular file on Linux checks the page cache first; a hit returns the data without touching the disk. A miss reads the data, fills the cache, and then returns.

The cache is **automatic**: there is no `enable cache` option. There is no `cache size` to configure. The kernel grows the cache to fill free RAM and shrinks it under memory pressure. This is the source of the perennial "Linux ate my RAM" panic: a freshly-booted machine has 16 GiB used, 1 GiB free, and the user assumes a leak. The user is looking at the wrong column; see §2.3.

### 2.2 Where to see the page cache

In `/proc/meminfo`:

```bash
$ grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached|Dirty|Writeback' /proc/meminfo
MemTotal:       16261408 kB
MemFree:         1234567 kB
MemAvailable:   11000000 kB
Buffers:           88112 kB
Cached:          8123456 kB
Dirty:               412 kB
Writeback:             0 kB
```

The fields, per `man 5 proc`:

- **`MemTotal`** — total RAM the kernel sees. Constant.
- **`MemFree`** — RAM not allocated to anything. Misleading; see below.
- **`MemAvailable`** — the estimated RAM that could be made available to a new application without swapping. **This is the number that matters.** Available since kernel 3.14 (2014); `free -h` derived this number on older kernels and got it slightly wrong.
- **`Buffers`** — page cache for **raw block devices** (the metadata blocks of a filesystem, the partition table reads, etc.). Small.
- **`Cached`** — page cache for **file contents**. This is the bulk of what the page cache holds.
- **`Dirty`** — pages modified in cache but not yet written to disk. §3 covers what this means.
- **`Writeback`** — pages currently being flushed to disk.

In `free -h`:

```
$ free -h
              total        used        free      shared  buff/cache   available
Mem:           15Gi       6.5Gi       1.2Gi       400Mi       7.8Gi        11Gi
Swap:         2.0Gi       128Mi       1.9Gi
```

- `used` is RAM allocated to processes.
- `free` is RAM allocated to nothing.
- `buff/cache` is the page cache (Buffers + Cached + Slab-reclaimable).
- `available` is the **estimated free RAM that includes reclaimable cache**.

The right mental model: `total = used + free + buff/cache`. `available ≈ free + reclaimable parts of buff/cache`. The cache **looks like** used RAM but is **available** to any process that needs it.

### 2.3 The "Linux ate my RAM" mistake

`top` shows `MEM 87 %`. The user panics. Run `free -h`:

```
              total        used        free      shared  buff/cache   available
Mem:           15Gi       6.5Gi       1.2Gi       400Mi       7.8Gi        11Gi
```

11 GiB available. The 8 GiB of "buff/cache" is the page cache holding hot file pages so future reads are fast. **Nothing is wrong.** The cache is doing its job. The site <https://www.linuxatemyram.com/> exists because this confusion is universal among new Linux users.

The number to watch for memory pressure is `MemAvailable` (or the `available` column of `free`). If `MemAvailable` is under 10 % of `MemTotal`, you may be in pressure. If `Dirty` is high or rising and `Writeback` is constant, you have a write throughput problem. If `vmstat 1` shows `si`/`so` non-zero, you are paging out anonymous memory — the conversation is over until you fix the memory pressure.

### 2.4 Demonstrating the cache: `dd` and `drop_caches`

The exercise (`exercise-02-page-cache-cold-vs-warm.md`) walks the demonstration in detail. Here is the condensed version:

```bash
# Create a 500 MB test file.
sudo dd if=/dev/urandom of=/tmp/testfile bs=1M count=500 status=none
sync

# Cold read — drop caches first.
sudo sysctl vm.drop_caches=3
time dd if=/tmp/testfile of=/dev/null bs=1M status=none
# (e.g., 2.4 s, 208 MB/s)

# Warm read — the file is in cache.
time dd if=/tmp/testfile of=/dev/null bs=1M status=none
# (e.g., 0.18 s, 2.8 GB/s)

# Clean up.
rm /tmp/testfile
```

The warm read is **memory bandwidth**, not disk bandwidth. The factor is 10-20× on a fast SSD; 50-100× on a spinning disk.

### 2.5 `drop_caches`: do not use it in production

```bash
sudo sync                              # flush dirty pages first
sudo sysctl vm.drop_caches=3
# or:
echo 3 | sudo tee /proc/sys/vm/drop_caches
```

The values:

- `1` — drop the page cache (clean file pages).
- `2` — drop slab caches (dentries and inodes).
- `3` — drop both.

`drop_caches` is **diagnostic**. It is for benchmarks where you want a known-cold cache between runs. **Do not** use it in production: every cache miss after is a real disk read, every program slows down for the next few seconds while the cache refills, and the kernel's page-replacement algorithm has no reason to keep your old hot pages out (it will fetch them right back).

You will see "drop caches before benchmark" advice in old documentation and old Stack Overflow answers. It is correct **for benchmarks**. Do not generalise.

### 2.6 Useful syscalls: `posix_fadvise`, `readahead`, `O_DIRECT`

A user-space program can interact with the page cache:

- **`posix_fadvise(fd, off, len, advice)`** — tell the kernel how the file will be used. `POSIX_FADV_SEQUENTIAL` (read sequentially; aggressive readahead), `POSIX_FADV_RANDOM` (random access; minimal readahead), `POSIX_FADV_NOREUSE` (will read once; do not cache aggressively), `POSIX_FADV_DONTNEED` (already read; you may drop the cached pages). The challenge exercise uses `POSIX_FADV_DONTNEED` to copy a huge file without polluting the cache.
- **`readahead(fd, off, count)`** — asynchronously prefetch a range of a file into the cache. Useful if you know the future access pattern.
- **`O_DIRECT`** (open flag) — bypass the page cache entirely. Reads and writes go directly between the user buffer and the device. Used by databases (PostgreSQL has `effective_io_concurrency`; some databases use `O_DIRECT` to manage their own cache). Requires careful alignment (buffer, file offset, IO size all multiples of the device's logical block size). **Not a generic "make it fast" knob**; it almost always makes things slower for non-database workloads.

Reference: `man 2 posix_fadvise`, `man 2 readahead`, `man 2 open` (the `O_DIRECT` section).

---

## 3. Dirty pages and writeback

### 3.1 What "dirty" means

When a process writes to a file, the kernel:

1. Allocates page cache pages for the affected file ranges (if not already cached).
2. Copies the new data into those pages.
3. Marks the pages **dirty** — in-memory copy is newer than the on-disk copy.
4. Returns from `write(2)` immediately.

The disk has not been touched. The user's program has moved on. The kernel will eventually write the dirty pages to disk; this **eventual** is the **writeback**.

This is the fundamental optimisation that makes Linux feel fast under writes. A `dd if=/dev/zero of=/tmp/big bs=1M count=1000` that "writes 1 GB" usually returns in well under a second; the disk is nowhere near that fast. The bytes went into the page cache and `dd` exited. The kernel's writeback threads will flush them in the background over the next several seconds.

The pattern is excellent until it isn't. When does it fail? When **you write faster than the disk can absorb for long enough that the cache fills up**.

### 3.2 The three writeback thresholds

The kernel flushes dirty pages on three triggers:

1. **`vm.dirty_background_ratio`** — when dirty pages reach this percentage of available RAM, the kernel starts background writeback. **Default: 10**. Background writeback does not block user processes.
2. **`vm.dirty_ratio`** — when dirty pages reach this percentage, the writing process is forced to do **synchronous writeback** (it cannot proceed until pages are flushed). **Default: 20**. This is the "the write got fast then suddenly slow" pattern.
3. **`vm.dirty_expire_centisecs`** — dirty pages older than this (in centiseconds, default 3000 = 30 seconds) are unconditionally flushed. The writeback thread (`kworker/u*:*flush*` in `ps`) wakes up every `vm.dirty_writeback_centisecs` (default 500 = 5 s) and checks.

Plus the application-driven trigger:

4. **`fsync(fd)` / `fdatasync(fd)` / `sync()`** — userspace asks the kernel to flush *this file's* dirty pages (or all dirty pages) and **wait for completion**. Databases call `fsync` after every transaction; this is what gives them durability.

### 3.3 The "fast then slow" `dd` pattern

You run:

```bash
dd if=/dev/zero of=/tmp/bigfile bs=1M count=10000
```

The output shows speed reports. The first few seconds are at 2-3 GB/s (RAM bandwidth). Then it drops to ~200 MB/s and stays there. What happened:

1. The first few seconds, writes filled the page cache. `dd` reported the RAM bandwidth.
2. At about 10 % of available RAM (default `vm.dirty_background_ratio`), background writeback started. The disk was now being written, but `dd` could continue ahead of writeback because the cache was not full.
3. At about 20 % of available RAM (default `vm.dirty_ratio`), `dd` was forced to wait for writeback before each new write. Now `dd`'s reported speed is the **disk's speed**.
4. The rest of the writes proceed at disk speed until `dd` finishes.

If you call `sync` (or `dd conv=fsync`), the kernel waits for **all** dirty pages to flush, and the wall-clock time reflects the real throughput.

### 3.4 Tuning the dirty ratios

The defaults — 10 % and 20 % — were chosen when RAM sizes were 1-4 GB. On a modern server with 64 GB RAM, 20 % is 12.8 GB of dirty pages, and a sudden synchronous flush of 12.8 GB to even a fast SSD is a multi-second stall during which the entire server is unresponsive.

The recommended tuning for servers with fast SSDs and large RAM is to **lower the ratios**:

```bash
# /etc/sysctl.d/99-dirty.conf
vm.dirty_background_ratio = 5
vm.dirty_ratio = 10
vm.dirty_expire_centisecs = 1500
vm.dirty_writeback_centisecs = 500
```

Apply: `sudo sysctl --system`. The lower ratios mean less data sitting dirty, smoother latency, less catastrophic flushes. The trade-off is slightly more writeback IO (because pages are flushed sooner and may be re-dirtied), which is usually invisible.

For a desktop or laptop, the defaults are usually fine. For a database server, lowering them is one of the most-recommended first tunings.

Reference: kernel `Documentation/admin-guide/sysctl/vm.rst` — the authoritative reference for every `vm.*` knob.

### 3.5 `swappiness`

The related knob is `vm.swappiness` — a 0-200 value that controls how aggressively the kernel prefers swapping anonymous memory versus reclaiming page cache. **Default: 60**.

- `swappiness=0`: never swap unless absolutely necessary.
- `swappiness=60`: prefer to reclaim cache but swap if the math says swapping is cheaper.
- `swappiness=200`: prefer swapping over cache reclaim.

Common recommendations:

- **Desktop with a fast SSD**: 10-20. Keep more cache; do not swap aggressively.
- **Server with a fast SSD**: 10. Same reasoning.
- **Workstation with a spinning disk**: leave the default. Swap is slow; cache reclaim is even slower.
- **A laptop on battery**: same default; the kernel does well.

### 3.6 `fsync` and durability

`fsync(fd)` flushes a single file's dirty pages and **waits for the disk to confirm the write**. The unit of durability for any database that cares about ACID is the `fsync` call after each transaction commit.

`fsync` is **expensive** — a syscall, a flush of every dirty page of the file, a flush of the disk's write cache (if barriers are on, which they should be), the wait for the disk to confirm. On an HDD, an `fsync` can take 10-30 ms. On a fast SSD, 100 µs to 1 ms. Either way, it is the slowest thing in the lifecycle of a transaction.

Common errors:

- **A database with `synchronous_commit = off`** (PostgreSQL) skips `fsync` and gets a 10x throughput improvement at the cost of potentially losing the last few seconds of writes after a crash. For most workloads this is wrong; for some (logs, metrics, advisory data) it is acceptable.
- **A test environment using `eatmydata`** (a small library that intercepts `fsync` and returns success without actually flushing) speeds up integration tests 10-100x. Useful for tests. Catastrophic if used in production.
- **A filesystem mounted with `barrier=0`** disables write barriers, so the disk's volatile cache is not flushed even on `fsync`. **Never** do this on a disk without a battery-backed write cache. Power loss = data loss.

Reference: `man 2 fsync`, `man 2 fdatasync`, `man 2 sync`.

---

## 4. `fio` — the canonical disk benchmark

### 4.1 What `fio` is

`fio` (Flexible IO tester) was written by Jens Axboe — the same engineer who maintains the Linux block layer and designed `io_uring`. It is the canonical Linux disk benchmark. Free, in every distro's repository.

`fio` runs configurable workloads against block devices or files and reports IOPS, bandwidth, and latency percentiles. The key concept is the **job file**: a small INI-style configuration that describes the workload (read or write, sequential or random, IO size, queue depth, duration, file or device target).

### 4.2 The four canonical jobs

A complete IO performance evaluation tests four points:

1. **4 KiB random read** — small-block random reads. Measures IOPS. The shape of a database transaction's index lookup.
2. **4 KiB random write** — small-block random writes. Measures durable-write IOPS. The shape of a database transaction's commit.
3. **1 MiB sequential read** — large-block sequential reads. Measures read bandwidth. The shape of streaming a large file.
4. **1 MiB sequential write** — large-block sequential writes. Measures write bandwidth. The shape of `dd`-ing a big file.

A typical SSD spec gives all four; a typical Linux server's `fio` benchmark should match the spec within ~20 %. If it does not, something is wrong — alignment, filesystem overhead, kernel scheduler choice.

### 4.3 The four job files

`exercises/exercise-04-fio-four-canonical-jobs.md` includes complete job files. Here are the essentials.

**`fio-randread-4k.fio`:**

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1

[randread-4k]
filename=/tmp/fio.testfile
size=2G
bs=4k
rw=randread
iodepth=32
numjobs=1
```

**`fio-randwrite-4k.fio`:** same as above but `rw=randwrite`. **Bash Yellow**: writes 2 GB to the disk, generates 30 seconds of random write IO. Wears the SSD; do not run repeatedly.

**`fio-seqread-1m.fio`:**

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1

[seqread-1m]
filename=/tmp/fio.testfile
size=2G
bs=1M
rw=read
iodepth=8
numjobs=1
```

**`fio-seqwrite-1m.fio`:** same with `rw=write`.

Run each:

```bash
fio fio-randread-4k.fio
```

The output is voluminous. The lines to read:

```
randread-4k: (groupid=0, jobs=1): err= 0: pid=12345: ...
  read: IOPS=98.7k, BW=386MiB/s (404MB/s)(11.3GiB/30001msec)
    slat (nsec): min=1234, max=12345, avg=2345, stdev=567
    clat (nsec): min=12345, max=2345678, avg=123456, stdev=23456
     lat (nsec): min=12345, max=2345678, avg=125678, stdev=23456
    clat percentiles (nsec):
     |  1.00th=[  ...], 99.99th=[ ...]
```

- **`IOPS`** — the headline IOPS. Compare to spec.
- **`BW`** — bandwidth. For 4 KiB jobs, BW = IOPS × 4096 bytes.
- **`clat`** — completion latency: time from submission to completion. The headline latency. Mean (avg), max, and percentile distribution (`99.99th`).
- **`slat`** — submission latency: time from the application calling submit to the kernel acknowledging. Usually negligible.

### 4.4 Cold versus warm cache

`direct=1` in the job files bypasses the page cache (`O_DIRECT`). For a "real disk benchmark" this is correct: you want to measure the device, not the cache.

For a "real workload simulation", drop `direct=1` and the cache is in play. The numbers will be higher; you are measuring the **page cache + device** combination, not just the device. Both are useful; know which you are measuring.

The exercise has you run each job twice: once cold (`drop_caches` first, no `direct=1`), once warm (back-to-back; no `drop_caches`), and compare.

### 4.5 Common mistakes

- **Running `fio` against the file you mounted from.** `fio` happily writes to `/tmp/fio.testfile` even if `/tmp` is a tmpfs in RAM. You are then benchmarking RAM, not the SSD. Confirm the target with `df /tmp` or use an explicit `filename=/var/data/fio.testfile`.
- **Reusing the test file across `direct=1` and non-direct runs.** The non-direct runs leave the file pages in the page cache, polluting the next direct run's results. `rm` the file between switches, or use different filenames.
- **Reading the wrong percentile.** `99th` is what you want; `mean` hides the tail. Real users care about the long tail; benchmarks should too.

Reference: `man 1 fio`, the upstream HOWTO at <https://fio.readthedocs.io/en/latest/fio_doc.html>.

---

## 5. `io_uring` — what it is, why you should know the name

### 5.1 The interface

`io_uring` is a Linux asynchronous-IO interface introduced in **kernel 5.1 (May 2019)**, designed by Jens Axboe (the same engineer behind `fio` and the block layer). It replaces the old Linux `aio` interface (the POSIX-ish `io_setup`/`io_submit`/`io_getevents`/`libaio` family), which was limited to `O_DIRECT` and a few syscalls and not widely adopted.

The mechanism, in one paragraph: a userspace program creates a pair of ring buffers (a **submission queue** SQ and a **completion queue** CQ) shared with the kernel via `mmap`. To submit an IO operation, the program writes a Submission Queue Entry (SQE) and updates the head pointer. To consume a completion, the program reads a Completion Queue Entry (CQE) and updates the tail pointer. **No syscall is required per operation** (in polling mode); the kernel-userspace handshake is via shared memory and per-batch syscalls. The throughput ceiling is much higher than syscall-per-IO interfaces.

### 5.2 What `io_uring` adds

- Asynchronous `read`, `write`, `readv`, `writev`, `fsync`, `accept`, `connect`, `recv`, `send`, `openat`, `close`, and roughly 60 other syscalls (the list has grown over kernel versions).
- Supports buffered IO (not just `O_DIRECT`), so it is useful for regular applications, not just databases.
- Supports linked operations (operation B starts only when operation A completes) for building dependency chains in the kernel.
- Supports a polling mode that reduces syscall count to zero for ultra-high-throughput workloads.

### 5.3 Why you should know the name

You are not going to write an `io_uring` program in this course. The interface is C-level and intricate; the userspace library is `liburing`; the design paper is 12 pages. **Mention only**, as the lecture title says.

But you should:

- **Recognise the name** when you see it in a job description ("experience with `io_uring` a plus"), a Linux performance flame graph (the `io_uring_*` symbols), or a postmortem ("we switched our event loop to use `io_uring` and latency dropped 30 %").
- **Recognise the kernel-version dependency**: `io_uring` requires kernel 5.1+ (May 2019), and the surface area has grown each release; many real-world deployments require 5.10+ for the features they need.
- **Recognise the security caveat**: `io_uring` has had a stream of security CVEs since 2020 because it is a new syscall surface. Several distributions have toggled it off by default for unprivileged users in recent years (Google ChromeOS, Docker's default seccomp profile). Check `/proc/sys/kernel/io_uring_disabled` on your system.
- **Recognise the application list**: nginx, Postgres (as of v18 there is `io_method=io_uring` for WAL writes), MariaDB, `rustls`, `tokio`, Go runtime considerations. Many high-performance servers either use `io_uring` directly or are evaluating it.

For depth: the design paper at <https://kernel.dk/io_uring.pdf> is the canonical text. Twelve pages, readable in an hour. Schedule it for the week after you finish C14.

---

## 6. Filesystem maintenance: `fsck` and friends

### 6.1 The cardinal rule

**Never run `fsck` on a mounted filesystem.** Repeat aloud. The kernel and `fsck` both write to the filesystem from different cached views; the result is corruption — and not the kind `fsck` can fix. The exception is **`btrfs scrub`**, which is explicitly designed to run on a mounted filesystem because btrfs's CoW design isolates the scrub from the live tree.

For ext4 and xfs:

```bash
# Wrong:
sudo fsck.ext4 /dev/sda1     # /dev/sda1 is mounted as /

# Right:
# Boot from rescue media; or, for non-root filesystems:
sudo umount /dev/sdb1
sudo fsck.ext4 -y /dev/sdb1
sudo mount /dev/sdb1
```

For the root filesystem, the system handles this automatically at boot. systemd runs `systemd-fsck-root.service` before the root is mounted read-write, and `systemd-fsck@.service` for each other ext4/xfs filesystem listed in `/etc/fstab` with `pass=1` or `pass=2`.

### 6.2 ext4 maintenance

```bash
# When was the filesystem last checked?
sudo tune2fs -l /dev/sdb1 | grep -E 'Last check|Check interval|Maximum mount count'

# Force a check on next boot.
sudo touch /forcefsck            # ext4 looks for this at boot
# (Or, classically: sudo tune2fs -C 99 /dev/sdb1 to bump mount count.)

# Schedule periodic checks (every 30 mounts OR 6 months, whichever first).
sudo tune2fs -c 30 -i 6m /dev/sdb1

# Disable scheduled checks entirely (server convention).
sudo tune2fs -c 0 -i 0 /dev/sdb1
```

Servers typically disable scheduled checks because a 30-mount check happens at boot and adds minutes of unavailability. Trust the journal; check explicitly if you suspect corruption.

### 6.3 xfs maintenance

```bash
# xfs has no "schedule a periodic check" because xfs_repair is run on demand.
# To check (filesystem MUST be unmounted):
sudo umount /dev/sdb1
sudo xfs_repair /dev/sdb1
sudo mount /dev/sdb1

# To check without repair (read-only):
sudo xfs_repair -n /dev/sdb1
```

xfs's design philosophy: the journal handles all crash recovery automatically; `xfs_repair` is for the cases where the journal cannot.

### 6.4 btrfs maintenance

btrfs's analog of `fsck` is `btrfs scrub`, which **runs online**:

```bash
# Start a scrub of the filesystem mounted at /.
sudo btrfs scrub start /

# Watch progress.
sudo btrfs scrub status /

# Cancel.
sudo btrfs scrub cancel /
```

`btrfs scrub` reads every block, verifies the checksum, and on mismatch repairs from the RAID redundancy. Run monthly on multi-device btrfs setups; less often on single-device.

### 6.5 SMART disk health

`smartctl` reads the disk's firmware-tracked SMART attributes. The single most important command:

```bash
sudo smartctl -a /dev/sda | less
```

The attributes to watch:

- **`Reallocated_Sector_Ct`** — bad sectors the firmware has remapped. Any non-zero is a yellow flag. Growing over time is a red flag and the disk should be replaced.
- **`Current_Pending_Sector`** — sectors the firmware suspects are bad but has not yet remapped. Non-zero is a red flag.
- **`UDMA_CRC_Error_Count`** — cable / port errors. Non-zero suggests a hardware (not disk) problem.

Schedule short and long self-tests:

```bash
sudo smartctl -t short /dev/sda           # ~2 min
sudo smartctl -t long /dev/sda            # ~2 hours

sudo smartctl -l selftest /dev/sda        # results
```

For NVMe, use `nvme-cli`:

```bash
sudo nvme list
sudo nvme smart-log /dev/nvme0
```

The NVMe SMART log includes `critical_warning` (any non-zero is a red flag), `media_errors`, `temperature`, and `percentage_used` (the firmware's estimate of life expended).

---

## Summary

- **LVM** sits between the partition and the filesystem. **PV** = a block device claimed by LVM; **VG** = a pool of PVs; **LV** = a slice of the VG. You format and mount the LV. The killer feature is **online resize** (`lvextend -r`) and **snapshots for backup** (`lvcreate -s`). Use LVM by default on servers.
- The **page cache** is an in-kernel cache of file pages, sized automatically to fill free RAM and shrunk under pressure. **Every file read** on Linux passes through it; cache hits are RAM-fast. `Cached:` in `/proc/meminfo`; `buff/cache` in `free`. The `MemAvailable` field (or `available` in `free`) is the number that matters for memory pressure; `MemFree` is misleading.
- **Dirty pages** are page-cache pages modified but not yet flushed to disk. The kernel writes them back lazily, controlled by `vm.dirty_background_ratio` (10 % default), `vm.dirty_ratio` (20 % default; the "stall ceiling"), and `vm.dirty_expire_centisecs` (30 s default).
- **`fsync(fd)`** is the unit of durability: flush this file's dirty pages and wait for confirmation. Expensive but unavoidable for databases. **Never** disable `barrier=` mount options on a non-battery-backed disk — power loss equals data loss.
- **`fio`** is the canonical IO benchmark. Four canonical jobs: 4k random read, 4k random write, 1m sequential read, 1m sequential write. Read `IOPS`, `BW`, and the `99th` percentile of `clat`. Use `direct=1` for device measurement, drop it for workload simulation.
- **`io_uring`** is the modern Linux async-IO interface (kernel 5.1+, 2019). Submission and completion queues shared with the kernel via mmap. You will not write it this week; know the name.
- **`fsck`** runs **only on unmounted filesystems**. **`btrfs scrub`** is the online exception. **`smartctl -a`** is the per-disk health check; `Reallocated_Sector_Ct` and `Current_Pending_Sector` are the canaries.

This is the last lecture of C14 · Crunch Linux. Next: the final exercises, the final quiz, and the 7-day capstone.

Reference: kernel `Documentation/admin-guide/sysctl/vm.rst`, `Documentation/admin-guide/mm/concepts.rst`, `Documentation/admin-guide/device-mapper/`. `man 8 lvm`, `man 5 proc`, `man 1 fio`, `man 8 smartctl`. Jens Axboe, "Efficient IO with io_uring" (<https://kernel.dk/io_uring.pdf>).
