# Exercise 4 — `fio`: the four canonical jobs

**Time:** 60-90 minutes (including read time for the output).
**Goal:** Run `fio` against your local disk with the four canonical jobs: 4k random read, 4k random write, 1m sequential read, 1m sequential write. Capture and interpret the output. Compare cold-cache (`direct=1`) and warm-cache (no `direct=1`) measurements. Compare to the device's spec sheet.
**Prerequisites:** Lecture 3 read. `fio` installed (`sudo apt install fio` or `sudo dnf install fio`). About 4 GiB of free disk space.

---

## Why this exercise

A "disk benchmark" is a meaningless phrase until you specify the workload. A disk that does 5 GB/s sequential read may do 100 MB/s random 4k read. A disk that handles 100k IOPS at queue depth 32 may handle 5k IOPS at queue depth 1. The four canonical `fio` jobs cover the four corners of the workload space; running them is the standard way to characterise a Linux block device.

After this exercise you can read a vendor's spec sheet, run the matching `fio` job, and confirm or refute the spec on your hardware.

---

## Part 1 — Set up

Make sure `fio` is installed:

```bash
fio --version
# fio-3.36 or newer
```

Create a scratch directory and `cd` to it:

```bash
mkdir -p ~/c14-w08-fio
cd ~/c14-w08-fio
```

Confirm the directory is on a real disk, not a tmpfs in RAM:

```bash
df -h .
# Should NOT show "tmpfs"; should show /dev/sdaX or /dev/nvmeXnY.
```

If it shows tmpfs, pick a different location (your home directory, `/var/tmp`).

---

## Part 2 — Write the four job files

Four files. Each is short.

### `fio-randread-4k.fio`

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1
filename=fio.testfile
size=2G

[randread-4k]
bs=4k
rw=randread
iodepth=32
numjobs=1
```

### `fio-randwrite-4k.fio`

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1
filename=fio.testfile
size=2G

[randwrite-4k]
bs=4k
rw=randwrite
iodepth=32
numjobs=1
```

### `fio-seqread-1m.fio`

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1
filename=fio.testfile
size=2G

[seqread-1m]
bs=1m
rw=read
iodepth=8
numjobs=1
```

### `fio-seqwrite-1m.fio`

```ini
[global]
ioengine=libaio
direct=1
runtime=30
time_based=1
group_reporting=1
filename=fio.testfile
size=2G

[seqwrite-1m]
bs=1m
rw=write
iodepth=8
numjobs=1
```

Save these in `~/c14-w08-fio/`.

What the options mean:

- `ioengine=libaio` — use Linux's `libaio` async-IO engine (the predecessor of `io_uring`). Required for `iodepth>1` to be meaningful.
- `direct=1` — bypass the page cache (open with `O_DIRECT`). Measures the device, not the cache.
- `runtime=30` — run for 30 seconds.
- `time_based=1` — keep running for the full `runtime` even if the file size is exceeded (repeat).
- `group_reporting=1` — report one summary for the group, not one per job thread.
- `filename=fio.testfile` — the file to read/write. `fio` will pre-allocate it to `size` if needed.
- `size=2G` — file size, 2 GiB.
- `bs=` — block size for the IOs.
- `rw=` — `randread`, `randwrite`, `read`, `write`. (Also `randrw` and `rw` for mixed.)
- `iodepth=` — how many IOs to keep in flight at once. Higher = more parallelism, deeper queues.
- `numjobs=1` — one job thread. (Multi-job is `numjobs=4` etc; useful for measuring multi-core scaling.)

Reference: `man 1 fio`, the HOWTO at <https://fio.readthedocs.io/>.

---

## Part 3 — Run the random-read job

Bash Yellow: this writes 2 GiB to `fio.testfile` and runs 30 seconds of disk activity. Modern SSDs can take this many times before wearing measurably; do not loop it.

```bash
fio fio-randread-4k.fio | tee randread-4k.log
```

The output is verbose. The lines to read:

```
randread-4k: (g=0): rw=randread, bs=(R) 4096B-4096B, ...
fio-3.36
Starting 1 process
randread-4k: Laying out IO file (1 file / 2048MiB)
Jobs: 1 (f=1): [r(1)][100.0%][r=386MiB/s][r=98.7k IOPS][eta 00m:00s]
randread-4k: (groupid=0, jobs=1): err= 0: pid=12345: ...
  read: IOPS=98.7k, BW=386MiB/s (404MB/s)(11.3GiB/30001msec)
    slat (nsec): min=1234, max=98765, avg=2345, stdev=567
    clat (usec): min=12, max=3214, avg=323, stdev=87
     lat (usec): min=14, max=3216, avg=326, stdev=87
    clat percentiles (usec):
     |  1.00th=[ 234], 99.00th=[ 567],
     | 99.50th=[ 678], 99.90th=[1234],
     | 99.99th=[2345]
   bw (  KiB/s): min=358000, max=400000, per=100.00%, avg=395000.0, stdev=10000.0
   iops        : min=98000, max=101000, avg=99500.0, stdev=2500.0
```

Pull out:

- **IOPS** (the headline number for random workloads)
- **BW** (bandwidth; equals IOPS × bs for the random jobs)
- **`clat` 99th** (the 99th-percentile completion latency — the tail)

Record them.

---

## Part 4 — Run the random-write job

```bash
fio fio-randwrite-4k.fio | tee randwrite-4k.log
```

Same shape of output. **Random write IOPS** are usually 30-70 % of random read IOPS on consumer SSDs (the firmware has to find a place to write); on enterprise SSDs the ratio is closer to 1:1.

If you see **random write IOPS dramatically below random read** (e.g. 10x slower), you may be hitting:

- The SSD's SLC cache (a fast region used for bursts). Below the cache size: fast. Beyond it: slow. Try `size=10G` to push past the cache and re-measure.
- A non-SSD device. Run `cat /sys/block/<dev>/queue/rotational` — `1` is HDD, `0` is SSD. HDDs are 100-200 random IOPS; SSDs are 10k-1M.
- The kernel's filesystem journal flushing on each write. For raw-device characterisation, run `fio` against the **device** (`filename=/dev/sdXY`), not a file. **This requires the device to be unmounted and unused** — practice on a loopback first, or use a spare partition.

Record.

---

## Part 5 — Run the sequential-read and sequential-write jobs

```bash
fio fio-seqread-1m.fio | tee seqread-1m.log
fio fio-seqwrite-1m.fio | tee seqwrite-1m.log
```

For sequential workloads, **bandwidth (BW)** is the headline number, not IOPS. A SATA SSD should give ~500-550 MB/s sequential. An NVMe consumer SSD should give 1500-7000 MB/s. A spinning disk gives 100-200 MB/s.

The IOPS for sequential 1 MiB blocks is intentionally low because each "IO" is large. Do not be alarmed at "only 500 IOPS" — at 1 MiB each, that is 500 MiB/s.

Record.

---

## Part 6 — Cold versus warm

Take the random-read job and run it three ways. First, build a table:

| Run | `direct=1`? | Drop caches before? | Expected speed |
|-----|-------------|---------------------|----------------|
| 1   | yes         | no (does not matter — direct bypasses cache) | device speed |
| 2   | no          | yes                  | device speed (cache will fill during the run) |
| 3   | no          | no — back-to-back with run 2  | RAM speed (cache from run 2 still warm) |

Make a second job file `fio-randread-4k-warm.fio` identical to `fio-randread-4k.fio` but with **`direct=0`** (or just remove the `direct=` line):

```ini
[global]
ioengine=libaio
direct=0
runtime=30
time_based=1
group_reporting=1
filename=fio.testfile
size=2G

[randread-4k-warm]
bs=4k
rw=randread
iodepth=32
numjobs=1
```

Now:

```bash
# Run 1: direct=1, the original job.
fio fio-randread-4k.fio | tee run1-direct.log

# Run 2: direct=0, cold cache.
sudo sync && sudo sysctl vm.drop_caches=3
fio fio-randread-4k-warm.fio | tee run2-cold.log

# Run 3: direct=0, warm cache (back-to-back).
fio fio-randread-4k-warm.fio | tee run3-warm.log
```

Compare the IOPS and BW of the three:

- Run 1 (direct=1) and Run 2 (direct=0, cold) should be similar — both are reading from the device.
- Run 3 (direct=0, warm) should be **much faster** — the file is now in the page cache.

This is the same lesson as Exercise 2, restated as a real benchmark. The number an application sees in production depends on **whether the working set fits in the page cache**.

---

## Part 7 — Compare to spec

Look up your disk's specification. For SATA SSDs the manufacturer's site usually states 4k random read IOPS, 4k random write IOPS, 1MB sequential read MB/s, 1MB sequential write MB/s.

Compare your measured numbers to spec. If you are within 20 %, the device is healthy and configured well. If you are **substantially below spec**, common causes:

- **Filesystem journaling overhead** — measure against the raw device if you can.
- **Wrong scheduler** — `cat /sys/block/<dev>/queue/scheduler`; for NVMe and SSDs the right choice is `none` or `mq-deadline`, not `bfq`.
- **PCIe lane allocation** (NVMe) — `lspci -vvv | grep -i nvme` should show 4 lanes at PCIe 3.0 or higher.
- **Wear / SLC cache exhaustion** — try `size=20G` to push past the cache, and `smartctl -a` to check wear.

---

## Part 8 — Clean up

```bash
rm fio.testfile
# Optional: keep the .log files for the homework
```

---

## Reflection

Answer in your notebook:

1. **Why use `direct=1` for benchmarks?** What are you measuring without it?
2. **For a SATA SSD with a 500 MB/s sequential read spec, what 4k random read IOPS would you expect roughly?** (Order of magnitude.)
3. **Look at the `clat` percentile output of one of your runs. Why is the 99.99th percentile so much higher than the mean?** What kinds of events cause the tail?
4. **You ran the random-write job and got 80,000 IOPS. The spec says 90,000. Is the disk OK?**
5. **Your colleague reports "the database is slow."** Which `fio` job most closely matches a database's IO pattern, and why?

---

## Stretch goals

- Add a **mixed read/write** job: `rw=randrw,rwmixread=70`. 70 % reads, 30 % writes — the shape of many real workloads.
- Run `fio` with **`ioengine=io_uring`** instead of `libaio` (requires fio 3.13+ and kernel 5.1+). Compare the numbers. On a fast NVMe, `io_uring` often shows 10-30 % higher IOPS at high queue depth.
- Run `fio` with `numjobs=4` and observe scaling. Does throughput scale linearly with jobs? At what `numjobs` does it plateau?
- Read the `man 1 fio` section on `LATENCY MEASUREMENTS` and produce a per-percentile latency CSV: `fio --output-format=json fio-randread-4k.fio | jq '.jobs[0].read.clat_ns.percentile'`. Useful for graphing.

---

*Solutions in `SOLUTIONS.md`.*
