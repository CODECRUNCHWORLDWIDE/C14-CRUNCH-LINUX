# Exercise 2 — The page cache, cold versus warm

**Time:** 30-45 minutes.
**Goal:** Demonstrate the page cache by measuring the difference between a cold read (no cached pages) and a warm read (file in cache). Use `drop_caches` to clear the cache. Watch `/proc/meminfo` and `free` to see the cache grow and shrink. End able to explain "Linux ate my RAM" to a colleague who has just panicked about it.
**Prerequisites:** Lecture 3 read. Root access on a Linux box. About 1 GiB of free disk space.

---

## Why this exercise

Every Linux performance debugging conversation eventually reaches the page cache. A junior engineer benchmarks their service, gets fast numbers, deploys to production, gets slow numbers, and is confused — because the benchmark was reading the same file twice and the second read was free. A senior engineer asks "was the cache warm?" before looking at the numbers.

The exercise makes the cache visible, measurable, and intuitive. You will see — with your own eyes, on your own box — the cache growing, the cache being dropped, the timing changing in the predicted direction.

---

## Part 1 — Set up

You need root for `drop_caches`. Open one terminal:

```bash
# Create a scratch directory.
mkdir -p ~/c14-w08-cache
cd ~/c14-w08-cache

# Create a 500 MB test file with random bytes.
# Random bytes prevent any "but you were reading from /dev/zero which the
# kernel optimises" objection. (urandom is plenty fast on modern kernels.)
dd if=/dev/urandom of=testfile bs=1M count=500 status=progress
sync                                    # flush any dirty pages

ls -lh testfile                         # confirm size
```

In a second terminal, watch the cache live:

```bash
watch -n 1 'free -h && echo && grep -E "MemAvailable|Buffers|Cached|Dirty" /proc/meminfo'
```

You will keep an eye on this throughout the exercise. The `Cached:` line is the page-cache size.

---

## Part 2 — Cold read

In terminal one, drop caches and run a timed read:

```bash
# Drop caches (root required).
sudo sync                                # flush dirty pages first
sudo sysctl vm.drop_caches=3

# Look at the watch in terminal two — Cached: should have dropped sharply.
# In terminal one:
time dd if=testfile of=/dev/null bs=1M status=none
```

Record the timing. On a typical SSD you should see something like 1.5-3 seconds for a 500 MB file. On a slower disk, considerably longer.

What happened, from the kernel's view:

1. Your process called `read(fd, buf, 1MB)` 500 times.
2. The kernel checked the page cache for the requested file pages. Each was a **miss**.
3. The kernel issued read requests to the block device, one extent at a time.
4. As pages came back, the kernel filled the cache and copied to your user buffer.
5. By the end, the page cache held 500 MB of `testfile` pages.

The watch in terminal two should now show **`Cached:` higher by ~500 MB**. The cache has grown.

---

## Part 3 — Warm read

Without dropping caches, immediately re-run the same read:

```bash
time dd if=testfile of=/dev/null bs=1M status=none
```

Record the timing. The same 500 MB now reports something like 0.15-0.4 seconds — **5x to 20x faster**, depending on your RAM bandwidth and CPU.

What happened this time:

1. Your process called `read(fd, buf, 1MB)` 500 times.
2. The kernel checked the page cache for the requested file pages. Each was a **hit**.
3. The kernel copied directly from cache to user buffer. No disk IO.

The disk did not move. The bytes you read came from RAM.

Reference: kernel `Documentation/admin-guide/mm/concepts.rst`.

---

## Part 4 — How big is the cache, exactly

Look at `/proc/meminfo`:

```bash
grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached|Dirty|Writeback' /proc/meminfo
```

`Cached:` should be at least 500 MB higher than before Part 2.

Look at `free -h`:

```bash
free -h
```

`buff/cache` is up. `available` is `MemFree + reclaimable cache`, so it should be approximately what it was before (you have not lost usable memory; the cache is reclaimable).

This is the picture that makes new Linux users panic: `top` shows "memory used: 95 %" because **the cache counts as used in that view**. It is not "used" in any meaningful sense.

Read aloud: "Linux did not eat my RAM. The cache holds hot file pages and is reclaimable on demand. The number to watch is `MemAvailable`."

---

## Part 5 — Force a cache drop and re-measure

```bash
sudo sysctl vm.drop_caches=3

# In terminal two: watch Cached: drop sharply.
free -h

# Run the read again. It should be cold-slow again.
time dd if=testfile of=/dev/null bs=1M status=none
```

The timing should match Part 2's cold read, within noise. The cache was empty; we paid the disk again.

---

## Part 6 — `posix_fadvise(POSIX_FADV_DONTNEED)`

`drop_caches` is system-wide. Sometimes you want to drop **just this file** from cache. The mechanism is `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)`, available via the `nocache` userspace utility or directly from Python.

```bash
# Make sure the file is warm.
time dd if=testfile of=/dev/null bs=1M status=none

# Use python's posix_fadvise to drop just this file:
python3 - <<'EOF'
import os
fd = os.open("testfile", os.O_RDONLY)
os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
os.close(fd)
print("Hinted POSIX_FADV_DONTNEED for testfile.")
EOF

# Re-read. Should be cold again.
time dd if=testfile of=/dev/null bs=1M status=none
```

The third read should be cold-slow even though we did not run `drop_caches`. The kernel obeyed the advisory hint for just this file.

This is the technique the challenge implements: a `cp` that does **not** pollute the page cache, useful for one-shot copies of huge files where you do not want to evict useful pages.

Reference: `man 2 posix_fadvise`.

---

## Part 7 — Cache pressure and reclaim

Now demonstrate the inverse: the cache is reclaimed on demand.

```bash
# Confirm the file is warm.
time dd if=testfile of=/dev/null bs=1M status=none

# Allocate a large anonymous memory region — about half of system RAM.
# This is NOT a memory leak; the python process exits and frees the memory.
TOTAL=$(awk '/MemTotal/ {print int($2/1024/2)}' /proc/meminfo)
echo "Will allocate ${TOTAL} MiB"

python3 - <<EOF
import time
mb = ${TOTAL}
print(f"Allocating {mb} MiB and touching every page...")
data = bytearray(mb * 1024 * 1024)
# Touch every page so the kernel actually maps it.
for i in range(0, len(data), 4096):
    data[i] = 1
print("Allocated. Holding for 3 seconds...")
time.sleep(3)
print("Releasing.")
EOF

# Read again. Was the cache evicted by the allocation?
time dd if=testfile of=/dev/null bs=1M status=none
```

The pattern depends on your system:

- If your machine has lots of free RAM (more than 2× `TOTAL`), the cache survives and the read is still fast.
- If memory was tight before this test (e.g. 4 GiB total, half allocated = 2 GiB, with a 500 MB cache: the kernel may have evicted some), the read is partially or fully cold.

In either case, watch `Cached:` in terminal two before, during, and after the allocation. You should see it drop when the allocation pressure is high, and slowly recover as you read again.

The lesson: **the page cache is the kernel's "shared with everyone" memory**. When a process needs anonymous memory, the kernel reclaims from the cache. This is exactly the behaviour `MemAvailable` predicts.

---

## Part 8 — A practical demonstration: `vmstat 1` during cold and warm reads

```bash
# In terminal two (replace the watch):
vmstat 1

# In terminal one:
sudo sysctl vm.drop_caches=3
time dd if=testfile of=/dev/null bs=1M status=none
time dd if=testfile of=/dev/null bs=1M status=none
```

In `vmstat`, watch the `bi` (block IO in, KiB/s) and `wa` (CPU iowait %) columns:

- **Cold read** — `bi` shoots up to the device's bandwidth (hundreds of MiB/s on SSD); `wa` shows non-zero.
- **Warm read** — `bi` stays near zero; `wa` stays near zero.

This is the `iostat`/`vmstat` view of the same phenomenon you measured with `time` in Parts 2 and 3.

---

## Part 9 — Clean up

```bash
cd ~
rm -rf ~/c14-w08-cache
```

The cache will retain the file pages briefly after deletion, then drop them as pressure rises. This is fine.

---

## Reflection

Answer in your notebook:

1. **Why is the warm read so much faster?** The disk bandwidth has not changed; what bandwidth are we actually measuring on the warm read?
2. **What does `MemAvailable` tell you that `MemFree` does not?**
3. **Why should you not use `drop_caches` in production?** What is the cost?
4. **When would `posix_fadvise(POSIX_FADV_DONTNEED)` be useful in real code?** Give one example.
5. **A colleague writes a benchmark script. It runs the same workload 5 times in a row and reports the mean.** What is wrong with this approach and how do you fix it?

---

## Stretch goals

- Repeat the experiment with **`O_DIRECT`** by adding `iflag=direct` to `dd`. The cache should not be filled; the cold and warm runs should take the same time.
- Use **`fincore`** (from the `linux-ftools` package) to look at exactly which pages of `testfile` are cached at any moment. After a partial read of the file with `dd ... count=100`, `fincore testfile` should show the first 100 MiB cached and the rest not.
- Read `/proc/<pid>/io` for your `dd` process during a cold and warm run. The difference between `rchar` (bytes read through syscalls) and `read_bytes` (bytes fetched from the block device) is exactly what the page cache served.

---

*Solutions in `SOLUTIONS.md`.*
