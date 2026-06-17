# Exercises — Solutions

Step-by-step solutions to the three exercises. Read after you have attempted each. The point of solutions is to confirm the path, not to spare you from walking it.

---

## Exercise 1 — Diagnose a busy CPU

### Part 2

```bash
# Terminal A
yes > /dev/null &
# [1] 5234
# PID is 5234
```

The `yes` binary is part of GNU coreutils; it does exactly what its man page says: "Repeatedly output a line with all specified STRINGS, or 'y'." Redirected to `/dev/null`, the writes are essentially free; the bottleneck is the `write()` syscall loop. On most kernels and CPUs the syscall path runs at hundreds of millions of iterations per second.

In `htop`, the per-CPU bar for whichever CPU the scheduler placed `yes` on lights up at 100 %. Process state alternates rapidly between `R` and `S`; sampling shows it most often as `R`.

### Part 3.1 (`top`)

```bash
$ top -n 1 -b -o %CPU | head -15
top - 14:32:15 up 12 days,  4:18,  3 users,  load average: 1.45, 0.78, 0.32
Tasks: 234 total,   2 running, 232 sleeping,   0 stopped,   0 zombie
%Cpu(s):  12.5 us,  0.1 sy,  0.0 ni, 87.3 id,  0.0 wa,  0.0 hi,  0.1 si,  0.0 st
MiB Mem :  15876.5 total,   ...

PID    USER  PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
5234  alice  20   0    8112    832    768 R 100.0   0.0   0:32.12 yes
   1  root   20   0  167756  11856   8504 S   0.0   0.1   0:08.45 systemd
...
```

`yes` is at the top of the list at 100.0 % CPU. Aggregated `%Cpu(s)` `us` is 12.5 — exactly `100/8` on an 8-core box, the per-core-vs-aggregate trap in action.

### Part 3.2 (`htop`)

`htop`'s default sort is by `CPU%`. Open it; `yes` is at line 1. Press `F3` and type `yes` to confirm; press `Esc` to clear the filter.

### Part 3.3 (`ps`)

```bash
$ ps -eo pid,user,pcpu,stat,comm --sort=-pcpu | head -5
  PID USER     %CPU STAT COMMAND
 5234 alice    99.8 R    yes
   53 root      0.4 S    rcu_sched
  412 root      0.1 Ss   sshd
    1 root      0.0 Ss   systemd
```

Note `pcpu` is *cumulative-since-process-start divided by elapsed time*, so a long-lived process with brief CPU activity will not look as busy as a freshly-started 100 % spinner. For "what is on the CPU *now*", `top` or `pidstat 1` is more accurate.

### Part 3.5 (`/proc`)

```bash
$ cat /proc/5234/status | grep -E '^(Name|State|VmRSS|Threads|voluntary|nonvoluntary)'
Name:   yes
State:  R (running)
VmRSS:    832 kB
Threads:        1
voluntary_ctxt_switches:        0
nonvoluntary_ctxt_switches:     8945
```

Single-threaded; 832 KiB resident; voluntary switches at zero (the process never sleeps); nonvoluntary high because the scheduler preempts it every tick.

### Part 4

Four `yes` processes; after a minute, `uptime` shows the 1-minute load average climbing toward 4. `mpstat -P ALL 1` shows four CPUs near 100 % `%usr` (or all of them if you have 4 CPUs).

`vmstat 1 5`:

```
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 4  0      0  3210000 100000 8000000   0    0     0    16  234  567 50  1 49  0  0
 4  0      0  3210000 100000 8000000   0    0     0    16  223  543 50  1 49  0  0
```

`r 4` (four runnable); `us 50` on an 8-core box (4 cores fully used / 8 cores = 50 % aggregate); `id 49` (other half idle).

### Part 5

The Python `os.write` loop drives kernel-time. `mpstat`:

```
14:32:15     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
14:32:16       3    2.00    0.00   97.00    0.00    0.00    1.00    0.00    0.00    0.00    0.00
```

97 % `%sys`. In `htop`, the bar for CPU 3 is red, not green. `strace -c` confirms `write` dominates:

```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 99.85    0.058432           0   1234567           write
  0.10    0.000059           1        47           others
```

The "user vs kernel time" distinction explains a lot of "the process is at 100 % CPU but the load is mostly system time" investigations. The fix is usually to batch syscalls.

---

## Exercise 2 — Trace a syscall

### Part 1

```bash
$ strace -c ls / > /dev/null
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 ...      ...        ...         27           mmap
 ...      ...        ...         27           mprotect
 ...      ...        ...         27           openat
 ...      ...        ...          8           read
 ...      ...        ...          1           getdents64
 ...      ...        ...          1           write
...
```

Exact numbers vary; the structure is consistent. The dominant syscall is usually one of `mmap` or `mprotect` because `ls`'s startup costs dwarf its work.

**Why 27 `mmap`s?** `ls` is dynamically linked to libc, libselinux, libcap, libacl, libpcre2, libpthread, and ~20 others. Each shared library is opened (1 `openat`), inspected (`fstat`), mmap'd as `read-only` (1 `mmap`), and protected as `read-execute` for the `.text` section (1 `mprotect`). Some libraries have additional `mmap`/`mprotect` for `.data`/`.bss` sections. The dynamic linker (`ld-linux.so`) does this for every library; the count is roughly *3 × (number of libraries)*. `ldd /usr/bin/ls` shows the libraries.

### Part 2

```bash
$ dd if=/dev/urandom of=/tmp/big.bin bs=1M count=50
$ strace -c cat /tmp/big.bin > /dev/null
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 ~55     ...        ...      ~6400           read
 ~40     ...        ...      ~6400           write
  ~3     ...        ...          ...        mmap
...
```

Read/write count: 50 MiB / 8 KiB (libc's BUFSIZ) ≈ 6400 calls. (Actual count is 6401 because of the partial-read returning EOF.)

```bash
$ strace -c dd if=/tmp/big.bin of=/dev/null bs=1M
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 ~50     ...        ...         50           read
 ~50     ...        ...         50           write
...
```

50 reads at 1 MiB each. Two orders of magnitude fewer syscalls; almost-identical CPU time per syscall, but 128× fewer syscalls means meaningfully lower CPU cost overall.

### Part 3

```bash
$ sudo strace -p 5234 -e trace=write,clock_nanosleep
strace: Process 5234 attached
clock_nanosleep(CLOCK_MONOTONIC, 0, {tv_sec=1, tv_nsec=0}, NULL) = 0
write(1, "tick\n", 5) = 5
clock_nanosleep(CLOCK_MONOTONIC, 0, {tv_sec=1, tv_nsec=0}, NULL) = 0
write(1, "tick\n", 5) = 5
^Cstrace: Process 5234 detached
```

The pattern is clear: one nanosleep, then one write, repeating every second. The `strace` output is the cleanest possible visualisation of "what this process is doing."

### Part 3.1 — observer effect

Without `strace`:

```bash
$ python3 -c '...busy loop for 10 seconds...'
40234567 iterations in 10 seconds
```

With `strace -e trace=all` attached:

```bash
$ python3 -c '...same loop...'  # under strace
1234567 iterations in 10 seconds
```

Roughly 30× slowdown — typical for Python (which makes lots of internal syscalls). C programs are usually 2-5× slowdown; high-syscall daemons 10-50×.

---

## Exercise 3 — `iostat -x 1` during a `dd` write

### Part 2

512-byte `dd`:

```
$ dd if=/dev/zero of=/tmp/big-write.bin bs=512 count=1000000
1000000+0 records in
1000000+0 records out
512000000 bytes (512 MB, 488 MiB) copied, 2.3 s, 222 MB/s
```

512 MB at 222 MB/s — limited not by the disk but by the `write` syscall rate (one syscall per 512 bytes; the page cache absorbs them but the syscall overhead is dominating).

1-MiB `dd`:

```
$ dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500
500+0 records in
500+0 records out
524288000 bytes (524 MB, 500 MiB) copied, 0.65 s, 806 MB/s
```

Same data, fewer syscalls, faster — limited now by the cache fill rate.

### Part 4

`iostat` during the 5 GB write at `bs=64K`:

```
Device  r/s  w/s    rkB/s   wkB/s  r_await  w_await  aqu-sz  wareq-sz  %util
sda     0.0  423.0  0.0    216832.0   0.00     2.10    0.89     512.0    98.50
```

Reading the columns:

- `wkB/s` 216 MB/s — close to the SSD's rated write speed.
- `aqu-sz` 0.89 — about one IO in flight; the device is keeping up.
- `w_await` 2.1 ms — within the SATA SSD's normal range.
- `%util` 98.5 — high, because the device is busy more than 98 % of the sampling window.

Interpretation: the device is busy but not saturating. It is doing its rated work. The high `%util` is the per-second average of "the device had at least one IO in flight," which is true 98 % of the time during a steady stream.

If `aqu-sz` had been 30 and `w_await` had been 50 ms, the device would have been over-saturated and IOs would be queueing.

### Part 5

Without `conv=fdatasync`:

```
$ time dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500
500+0 records in
500+0 records out
524288000 bytes (524 MB, 500 MiB) copied, 0.42 s, 1.2 GB/s

real    0m0.421s
user    0m0.000s
sys     0m0.421s
```

1.2 GB/s — much higher than disk bandwidth — because the data went to page cache, not to disk. The disk has not been written yet.

With `conv=fdatasync`:

```
$ time dd if=/dev/zero of=/tmp/big-write.bin bs=1M count=500 conv=fdatasync
500+0 records in
500+0 records out
524288000 bytes (524 MB, 500 MiB) copied, 1.18 s, 444 MB/s

real    0m1.182s
user    0m0.000s
sys     0m0.441s
```

444 MB/s — the honest measurement of the SSD's sustained write rate.

The difference (1.2 GB/s versus 444 MB/s) is the page cache lying to you.

### Part 6

```bash
$ pidstat -d 1
14:32:15  UID  PID  kB_rd/s  kB_wr/s  kB_ccwr/s  iodelay  Command
14:32:16 1000 5234     0.0  216832.0       0.0       12  dd

$ cat /proc/$(pgrep -x dd)/io
rchar: 5368709120
wchar: 5368709120
syscr: 80000
syscw: 80000
read_bytes: 0
write_bytes: 5368709120
```

`rchar` and `wchar` both 5 GB (the dd read 5 GB from `/dev/zero` and wrote 5 GB out). `read_bytes` is 0 — `/dev/zero` is a virtual device; no actual block-IO was done to read from it. `write_bytes` is 5 GB — the writes did go to a block device.

### The summary paragraph

"On this hardware (SATA SSD, kernel 6.8, sysstat 12.6), the most reliable saturation signal during a sustained sequential write was `aqu-sz`. `%util` rose to 98 % almost immediately and stayed there for the entire write, regardless of whether the device was lightly or heavily loaded — it is a busy-fraction, not a saturation measure. `aqu-sz` rose smoothly with workload intensity and is the column I would set an alert threshold on. `w_await` rises in lock-step with `aqu-sz` (queue depth and queue wait are by Little's Law proportional), and is the column I would *report* to a user as the latency signal."

---

*Back to the [exercises index](./exercise-01-diagnose-a-busy-cpu.md).*
