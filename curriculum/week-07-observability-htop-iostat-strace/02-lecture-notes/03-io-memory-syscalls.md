# Lecture 3 — IO, memory, and syscalls

> *Lecture 2 covered the CPU column of the USE matrix. This lecture covers the other three — memory, disk, and the syscall layer that mediates between them. `iostat`, `vmstat`, `free`, `strace`, `ltrace`, and the `/proc/<pid>/io` file that ties them together. The skill is to look at a column on `iostat -x 1` and know whether the number is big, and what it means if it is.*

---

## 1. `iostat -x 1` — the disk view

`iostat` is the canonical block-device monitor. Comes with the `sysstat` package. `man 1 iostat`.

The plain `iostat` is almost useless — averages since boot, in coarse units. The variant that matters is `iostat -x 1`: extended mode (`-x`), one-second intervals. Optionally add `-z` to skip devices with zero activity, `-m` to display in MiB, `-p ALL` to include partitions.

```bash
$ iostat -xz 1
Linux 6.8.0 (host)  2026-05-14  _x86_64_  (8 CPU)

avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           5.20    0.00    1.30   12.00    0.00   81.50

Device  r/s     w/s    rkB/s   wkB/s  rrqm/s  wrqm/s  %rrqm  %wrqm  r_await  w_await  aqu-sz  rareq-sz  wareq-sz  svctm  %util
sda    1234.0   2.0   98765.0    16.0     0.0     1.0   0.00  33.33    78.50     1.50    96.78    80.04     8.00   0.81   99.20
```

The columns:

- **`r/s`, `w/s`** — read / write operations per second. The IOPS the device is delivering.
- **`rkB/s`, `wkB/s`** — read / write bandwidth in KiB/s. Compare to your device's spec.
- **`rrqm/s`, `wrqm/s`** — reads / writes **merged** per second. The block layer merges adjacent IOs before sending them to the device. Higher merge rate = more sequential workload = the device is happier.
- **`%rrqm`, `%wrqm`** — fraction of reads / writes that were merged. Zero on SSD or random workloads; can be 50-90 % on rotating disks with sequential workloads.
- **`r_await`, `w_await`** — mean wait time per read / write in milliseconds, **including time in the queue**. Available since `sysstat` 12.0 (2019); older versions only show one combined `await`.
- **`aqu-sz`** — average queue length. The number of IOs in flight on average over the sample window. Persistent values above 1 mean the device is in saturation.
- **`rareq-sz`, `wareq-sz`** — average request size in KiB. Small request sizes (4 KiB) with high IOPS = random IO. Large request sizes (1024 KiB) with modest IOPS = sequential IO.
- **`svctm`** — service time. *Deprecated*: `iostat` since 12.0 emits `svctm` as 0 because the computation was always misleading on multi-queue devices. Ignore.
- **`%util`** — fraction of time the device had at least one IO in flight. **The trap column for SSDs and NVMe.** On a rotating disk, `%util` near 100 % means the disk is saturated. On a modern device with internal parallelism, `%util` can reach 99 % at a fraction of the device's real throughput because the device is happy to accept the next IO before the previous one finishes. **Read `aqu-sz` as the truer saturation signal on multi-queue hardware.**

The line we read most: `r/s + w/s` (total IOPS), `aqu-sz` (queue depth), `r_await + w_await` (latency). Compare each to the device's spec.

### 1.1 What "saturation" looks like by device class

| Device | Saturated `%util` | Saturated `aqu-sz` | Healthy `await` | Saturated `await` |
|--------|------------------|---------------------|------------------|-------------------|
| 7200 RPM SATA HDD | 90-100 % | 1-2 | 5-15 ms | >50 ms |
| SATA SSD | 90-100 % | ~32 (the SATA queue) | 0.1-1 ms | >5 ms |
| NVMe SSD | 50-100 % (unreliable) | 32-128 | 0.05-0.5 ms | >2 ms |
| RAID volume | depends | depends | depends | depends |

The rule: **on rotating disks, trust `%util`. On SSDs and NVMe, trust `aqu-sz` and `await`.**

### 1.2 Per-process IO: `pidstat -d 1` and `/proc/<pid>/io`

`iostat` shows the device. To answer "which process is generating the IO", you need a process-level view. The two options:

```bash
$ pidstat -d 1
14:32:15  UID  PID  kB_rd/s  kB_wr/s  kB_ccwr/s  iodelay  Command
14:32:16 1000 5234  98000.0     16.0       0.0       10  python3
```

Or read `/proc/<pid>/io` directly:

```bash
$ cat /proc/5234/io
rchar: 2345670000
wchar: 89012345
syscr: 12345
syscw: 6789
read_bytes: 200000000000
write_bytes: 800000000
cancelled_write_bytes: 0
```

The difference between `rchar` (bytes read through syscalls) and `read_bytes` (bytes actually fetched from a block device) tells you how much the page cache served. A process with `rchar` 100 GB and `read_bytes` 100 MB is hot — almost everything is in cache. A process with `rchar` and `read_bytes` equal is reading cold data.

For the third option, `iotop` (requires root): a `top`-style per-process IO view, in real time. Same source (`/proc/<pid>/io`), prettier.

---

## 2. `vmstat 1` — the system cycle counter

`vmstat` is the cardiac monitor of the Linux kernel. Cheap, present everywhere, surprisingly informative. `man 8 vmstat`.

```bash
$ vmstat 1
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 0  0      0  423456  88112 8123456    0    0    23    16  234  315  3  1 95  1  0
 1  0      0  423344  88112 8123480    0    0     0    32  198  283  5  2 92  1  0
 0  4      0  423344  88112 8123480    0    0 98432    16  823 1315  2  3  1 94  0
```

Columns, in order:

### `procs` block

- **`r`** — count of runnable processes (running or waiting for CPU). On an idle system this is 0 or 1. Sustained `r` higher than CPU count means CPU saturation.
- **`b`** — count of processes in uninterruptible sleep (state `D`). Sustained non-zero `b` means IO saturation.

### `memory` block

- **`swpd`** — KiB of memory swapped to disk.
- **`free`** — KiB of idle memory.
- **`buff`** — KiB of kernel buffers (metadata, journal blocks).
- **`cache`** — KiB of page cache (file data).

### `swap` block — the doom column

- **`si`** — KiB swapped *in* per second (from disk to memory). Non-zero means memory pressure is paging data back.
- **`so`** — KiB swapped *out* per second (memory to disk). Non-zero means the kernel is evicting anonymous memory.

**Any persistent non-zero `si`/`so` is a five-alarm fire** for an interactive or latency-sensitive workload. Swap is two-to-three orders of magnitude slower than RAM; any IO that hits swap is a frozen UI from the user's perspective.

### `io` block

- **`bi`** — KiB of block IO **in** (read from devices).
- **`bo`** — KiB of block IO **out** (written to devices).

### `system` block

- **`in`** — interrupts per second.
- **`cs`** — context switches per second.

A normal system at light load shows `cs` around 100-1000. Sustained `cs` above 100,000 suggests excessive thread-thrash — a fork bomb, a misconfigured server with too many threads competing on a lock, or a database with insufficient connection pooling.

### `cpu` block (aggregated across all CPUs)

- **`us`** — user-space time.
- **`sy`** — kernel-space time.
- **`id`** — idle.
- **`wa`** — IO wait.
- **`st`** — stolen by hypervisor (VMs only).

Sums to 100. The signal: high `us` = application CPU; high `sy` = kernel CPU (often syscall-heavy); high `wa` = blocked on IO; high `st` = noisy hypervisor neighbour.

### 2.1 Reading `vmstat 1` quickly

The decision tree for the *first second* of `vmstat 1` output:

1. Is `si` or `so` non-zero? → **memory pressure**; go to §3.
2. Is `b` non-zero or `wa` high? → **IO saturation**; go back to `iostat`.
3. Is `r` higher than CPU count, or `us` high? → **CPU saturation**; go back to Lecture 2.
4. Is `cs` very high? → **thread-thrash**; check `pidstat -w 1` for the noisy process.
5. None of the above? → **the system is fine**; the bottleneck is elsewhere.

---

## 3. `free -h` and `/proc/meminfo`

`free -h` shows the memory summary in human-readable units:

```bash
$ free -h
              total        used        free      shared  buff/cache   available
Mem:           15Gi       3.2Gi       210Mi       110Mi        12Gi        12Gi
Swap:         2.0Gi       1.4Gi      600Mi
```

The five numbers:

- **`total`** — physical RAM the kernel saw at boot.
- **`used`** — `total` minus `free` minus `buff/cache` (roughly — see `man 1 free` for the exact formula).
- **`free`** — completely unused, not even for cache.
- **`shared`** — memory used by `tmpfs` mounts (e.g. `/dev/shm`).
- **`buff/cache`** — memory the kernel is using for buffers and page cache.
- **`available`** — the number that matters. An estimate of how much memory could be made available to a new allocation without paging anything out, taking into account that `buff/cache` is reclaimable.

The single most common memory-related confusion is that "free" is low while the system is in fact fine. `free` being small is correct kernel behaviour: idle memory is wasted memory, so the kernel fills it with page cache. The right column to read is `available`.

When `available` is below 10 % of `total`, the system is in real memory pressure. Combine with `vmstat 1` `si`/`so` to confirm; if non-zero, the system is paging and the conversation moves to "buy more RAM, reduce working set, or accept the latency."

`/proc/meminfo` is the source. It has 40+ fields. The ones you read:

```bash
$ grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree|Dirty|Writeback|AnonPages|Mapped|Slab|SReclaimable|SUnreclaim)' /proc/meminfo
MemTotal:       16245788 kB
MemFree:          215120 kB
MemAvailable:   12504000 kB
Buffers:           90112 kB
Cached:         12320000 kB
SwapTotal:       2097148 kB
SwapFree:         614876 kB
Dirty:              5120 kB
Writeback:             0 kB
AnonPages:       3450000 kB
Mapped:           340000 kB
Slab:             450000 kB
SReclaimable:     320000 kB
SUnreclaim:       130000 kB
```

The fields that matter for diagnosis:

- **`MemAvailable`** — as above.
- **`Dirty`** — bytes of file-backed memory that have been modified and need to be written back to disk. Persistent high `Dirty` (more than a few hundred MB) means the writeback pipeline is saturated and writes are queueing.
- **`Writeback`** — bytes currently being written back. Should track `Dirty`.
- **`AnonPages`** — anonymous memory (`malloc`, `mmap MAP_ANONYMOUS`). The bytes that *do not have a file to be evicted to* and so will go to swap if the system is under pressure.
- **`SReclaimable`** / **`SUnreclaim`** — kernel slab memory: reclaimable (caches like dentry, inode cache) versus not (truly needed). High `SUnreclaim` is a kernel-memory leak signal.

Reference: `man 5 proc`, section `/proc/meminfo`. Kernel docs: `Documentation/filesystems/proc.rst` (search for "meminfo").

---

## 4. `strace` — syscall tracing

`strace` attaches to a process via `ptrace` and prints every syscall as it happens. `man 1 strace`.

The two invocations you use most:

```bash
# Count syscalls in a command's execution
strace -c COMMAND

# Attach to a running PID and stream syscalls
strace -p PID
```

### 4.1 `strace -c` — the summary view

```bash
$ strace -c ls /
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 22.45    0.000312          11        27           mmap
 18.20    0.000253           9        27           mprotect
 12.05    0.000168           6        27           openat
 10.78    0.000150           5        27           close
  8.91    0.000124          15         8           read
  7.83    0.000109           4        25           fstat
  6.10    0.000085          11         8           write
  4.45    0.000062           5        13           getdents64
  3.20    0.000045           4        12           rt_sigprocmask
  6.03    0.000084           - varied         9 other
------ ----------- ----------- --------- --------- ----------------
100.00    0.001392                  173         9 total
```

The columns:

- **`% time`** — fraction of the *traced time* spent in this syscall. Note: this is fraction of *time strace observed*, not fraction of wall-clock time. A process that spends 99 % of its time off-CPU on a `read` syscall will show 99 % on `read`.
- **`seconds`** — total time in this syscall.
- **`usecs/call`** — average microseconds per call.
- **`calls`** — total count.
- **`errors`** — count of failures (return code -1).

The summary is the single most useful first look at "what is this process actually doing." A short-lived command like `ls` shows the startup pattern (lots of `mmap` and `mprotect` from the dynamic linker). A long-running daemon shows whatever it spends its time on — usually `read`, `epoll_wait`, `futex`, or similar.

### 4.2 `strace -p PID` — the live stream

```bash
$ sudo strace -p 5234
strace: Process 5234 attached
read(3, "Hello world\n", 8192)         = 12
write(1, "Hello world\n", 12)           = 12
read(3, "", 8192)                       = 0
close(3)                                = 0
exit_group(0)                           = ?
+++ exited with 0 +++
```

Every syscall is shown with its arguments and return value. `read(3, "Hello world\n", 8192) = 12` means "called read on FD 3 with an 8192-byte buffer; read returned 12 bytes; the buffer now contains 'Hello world\n'."

### 4.3 Useful flags

- **`-f`** — follow child processes (forks). Without `-f`, `strace` traces only the original process.
- **`-e trace=GROUP`** — filter to specific syscalls or syscall groups. `-e trace=openat,read,write` shows only those three. `-e trace=%file` shows all file-related syscalls. `-e trace=%network` for network.
- **`-o FILE`** — write to a file instead of stderr.
- **`-T`** — record time spent in each syscall (added column at the end).
- **`-r`** — relative timestamp for each syscall.
- **`-tt`** — wall-clock timestamp with microseconds.
- **`-s LEN`** — string length to print (default 32; the rest is `...`-truncated).
- **`-y`** — translate FD numbers to file paths in the output.

A useful daily invocation:

```bash
strace -fTtt -y -e trace=%file,%network -o /tmp/trace.log -p PID
```

Files-and-network with timestamps and durations, writing to a log so the live terminal stays readable. `-f` to follow forks; `-y` to translate FDs.

### 4.4 The observer effect

`strace` slows the target by a factor of 2-20×. The mechanism is `ptrace`: every syscall causes a context switch into `strace`, which reads the syscall arguments via `process_vm_readv`, then resumes the target. The overhead is per-syscall; processes with very high syscall rates (database engines, busy network servers) can be slowed by a factor of 100 or more.

**Do not run `strace` on production processes unless you have decided that the slowdown is acceptable.** For production observability without `ptrace` overhead, the alternatives are:

- **`perf trace`** — same syscall view, no `ptrace`, ~5 % overhead. `perf trace -p PID`.
- **`bpftrace`** — write a one-line BPF program. `bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s\n", str(args->filename)); }'`.
- **`bcc-tools/opensnoop`** — pre-built BPF tools for the common cases. `sudo opensnoop`.

We will not lean on BPF this week; we mention it so you know the production-safe alternative exists.

### 4.5 What `strace` shows you that you would not otherwise see

Three diagnostic scenarios where `strace` is the right tool:

1. **"The process is running but doing nothing."** `strace -p PID` and watch. If it shows the same syscall repeatedly with a long latency, the process is blocked there. Common cases: `futex(FUTEX_WAIT, ...)` blocked on a lock; `select(...)` waiting for a network event; `read(FD, ...)` waiting for input.
2. **"The process is reading a config file from the wrong place."** `strace -e trace=openat COMMAND 2>&1 | grep config`. Every `openat` for files containing "config" is shown; you see which paths were tried and which succeeded.
3. **"The process is making network calls I do not expect."** `strace -e trace=%network -e signal=none COMMAND`. Every `socket`, `connect`, `bind`, `accept`, `sendto`, `recvfrom` is shown.

---

## 5. `ltrace` — library-call tracing

`ltrace` is `strace` one level up the stack: it traces calls to dynamically-linked library functions, not syscalls. `man 1 ltrace`.

```bash
$ ltrace -e printf+puts ls /
puts("bin")                                              = 4
puts("boot")                                             = 5
puts("dev")                                              = 4
puts("etc")                                              = 4
puts("home")                                             = 5
...
+++ exited (status 0) +++
```

Each line shows a library call. The mechanism is the same `ptrace`: the slowdown is similar. The use case is narrower — `ltrace` is the right tool when:

- The syscall view is too low-level. `strace` shows `read(3, ...)` and you want to know which `libxml` function called `read`.
- You are debugging library version issues. `ltrace -e openssl_*` shows every OpenSSL call.
- You are reverse-engineering a closed-source binary. `ltrace` is one of the standard tools.

`ltrace` is less universally installed than `strace` (Fedora ships it; Ubuntu requires `sudo apt install ltrace`).

---

## 6. The `/proc/<pid>/` files we read most

`/proc/<pid>/status` (Lecture 2 §7) — the process state plus memory and context-switch counts.

`/proc/<pid>/io` (Lecture 3 §1.2) — bytes and syscalls of IO.

`/proc/<pid>/fd/` — symbolic links to every open file descriptor:

```bash
$ ls -la /proc/5234/fd/
total 0
dr-x------ 2 alice alice  0 May 14 14:32 .
dr-xr-xr-x 9 alice alice  0 May 14 14:32 ..
lr-x------ 1 alice alice 64 May 14 14:32 0 -> /dev/null
l-wx------ 1 alice alice 64 May 14 14:32 1 -> /home/alice/log/out.log
l-wx------ 1 alice alice 64 May 14 14:32 2 -> /home/alice/log/err.log
lrwx------ 1 alice alice 64 May 14 14:32 3 -> 'socket:[12345]'
lr-x------ 1 alice alice 64 May 14 14:32 4 -> /home/alice/data/big.csv
lrwx------ 1 alice alice 64 May 14 14:32 5 -> 'socket:[67890]'
```

Equivalent to `lsof -p PID`. Useful for "what files does this process have open?" and "why is the process holding on to that deleted file?" (you will see `/path/to/file (deleted)` in the link target).

`/proc/<pid>/maps` — the memory map:

```bash
$ cat /proc/5234/maps
55c00b400000-55c00b401000 r--p 00000000 fd:00 1234 /usr/bin/python3
55c00b401000-55c00b403000 r-xp 00001000 fd:00 1234 /usr/bin/python3
55c00b403000-55c00b404000 r--p 00003000 fd:00 1234 /usr/bin/python3
55c00b404000-55c00b405000 r--p 00003000 fd:00 1234 /usr/bin/python3
55c00b405000-55c00b406000 rw-p 00004000 fd:00 1234 /usr/bin/python3
7f1234500000-7f1234540000 r--p 00000000 fd:00 5678 /usr/lib/x86_64-linux-gnu/libc.so.6
...
7ffd12340000-7ffd12361000 rw-p 00000000 00:00 0    [stack]
```

Each line is one memory mapping. The columns: start-end address, permissions (`r`/`w`/`x`/`s` shared / `p` private), offset in file, device, inode, pathname (or `[stack]`, `[heap]`, `[vdso]`, etc.). `pmap PID` formats this same data more readably.

`/proc/<pid>/wchan` — the kernel function the process is sleeping in, when in state `S` or `D`. One word, very informative:

```bash
$ cat /proc/5234/wchan
do_nanosleep   # the process is sleeping
$ cat /proc/5235/wchan
io_schedule    # the process is blocked on disk IO
$ cat /proc/5236/wchan
futex_wait_queue # the process is blocked on a lock
```

`/proc/<pid>/comm` — the process command (15 chars max). `/proc/<pid>/cmdline` — the full command line, with NUL between arguments.

`/proc/<pid>/cgroup` — the cgroup hierarchy. Tells you which systemd slice or container the process is in.

---

## 7. Putting it together — an IO-bound diagnostic walk

A user reports a service is slow. Sixty-second checklist. `vmstat 1` shows:

```
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 0  3      0  423344  88112 8123480    0    0 98432    16  823 1315  2  3  1 94  0
```

`b 3` (three processes blocked); `wa 94` (CPUs mostly idle but waiting on IO). IO-bound. `iostat -xz 1`:

```
Device  r/s     w/s    rkB/s   wkB/s  r_await  w_await  aqu-sz  %util
sda    1234.0   2.0   98765.0    16.0    78.50     1.50    96.78  99.20
```

`sda` saturated: 99 % util, 96 in queue, 78 ms read latency. Which process?

```bash
$ pidstat -d 1
14:32:15  UID  PID  kB_rd/s  kB_wr/s  Command
14:32:16 1000 5234  98432.0     16.0  python3
```

`python3 PID 5234` reading 98 MB/s. Confirm with `/proc/5234/io`:

```bash
$ cat /proc/5234/io
rchar: 9876543210
wchar: 12345
syscr: 12345
syscw: 23
read_bytes: 9876543210
write_bytes: 0
```

`rchar` and `read_bytes` are almost equal — cold reads from disk, not from cache. Diagnosis: process 5234 is reading 98 MB/s sequentially from `sda`; the disk is a 7200 RPM HDD pegged at saturation. Either the workload is reading too much, the data should be in cache (and is not), or the disk is too slow for the workload.

To prove the page-cache hypothesis would be true if the data were already cached, we could `cat /home/alice/data/big.csv > /dev/null` once to warm the cache, then re-run the workload. Re-running `iostat` then would show much lower `read_bytes` per second; `rchar` would be the same (the process reads the same bytes); the difference is whether the bytes come from disk or RAM.

Notice: same as the CPU example, we did not change anything. We measured, identified, hypothesised, designed a confirming test.

---

## 8. Networks — `ss` and a glance at the rest

The fourth pillar. `ss` is the modern replacement for `netstat`; comes with `iproute2`; preinstalled. `man 8 ss`.

```bash
# All listening TCP and UDP sockets, with process and PID
$ ss -tulpn
Netid State    Recv-Q Send-Q Local Address:Port Peer Address:Port Process
udp   UNCONN   0      0      0.0.0.0:68         0.0.0.0:*         users:(("dhclient",pid=300,fd=7))
tcp   LISTEN   0      128    0.0.0.0:22         0.0.0.0:*         users:(("sshd",pid=412,fd=3))
tcp   LISTEN   0      128    0.0.0.0:80         0.0.0.0:*         users:(("nginx",pid=523,fd=6))
tcp   LISTEN   0      128    [::]:80            [::]:*            users:(("nginx",pid=523,fd=7))

# All TCP, numeric
$ ss -tan
State    Recv-Q Send-Q Local Address:Port Peer Address:Port
LISTEN   0      128    0.0.0.0:22         0.0.0.0:*
LISTEN   0      128    0.0.0.0:80         0.0.0.0:*
ESTAB    0      0      192.0.2.10:22      203.0.113.55:54321
ESTAB    0      0      192.0.2.10:80      198.51.100.7:62115
TIME-WAIT 0     0      192.0.2.10:80      198.51.100.4:60223
```

The two columns worth understanding:

- **`Recv-Q`** — on a `LISTEN` socket: the number of completed-handshake connections waiting for the application to `accept()`. **Non-zero on a `LISTEN` row means the application is too slow to accept**; the kernel is queueing. If the count reaches the `Send-Q` limit (the second number, 128 here), new SYNs are dropped. On an `ESTAB` socket: bytes received but not yet read by the application.
- **`Send-Q`** — on a `LISTEN` socket: the accept-queue capacity (the `backlog` argument to `listen(2)`). On an `ESTAB` socket: bytes queued for transmission, not yet ACKed by the peer.

The summary view, `ss -s`:

```bash
$ ss -s
Total: 1234
TCP:   456 (estab 200, closed 56, orphaned 0, timewait 100)

Transport Total  IP    IPv6
RAW       0      0     0
UDP       12     8     4
TCP       300    250   50
INET      312    258   54
FRAG      0      0     0
```

For per-socket TCP detail (RTT, congestion window, retransmits): `ss -ti`.

The rest of the network observability path is `sar -n DEV 1` (bandwidth), `nstat` (cumulative SNMP counters), `tcpdump` (packet capture; out of scope this week). We come back to network observability in Week 9.

---

## 9. A note on `sar` — the recorder you should turn on

`sar` is the continuous-collection backbone of the `sysstat` package. While the other tools sample on demand, `sar` records every 10 minutes by default to `/var/log/sysstat/`. This is what makes "the system was slow yesterday at 14:00" answerable.

Enable:

```bash
sudo systemctl enable --now sysstat
# Optionally tighten the collection interval:
sudo sed -i 's|^\*/10|\*/5|' /etc/cron.d/sysstat   # every 5 minutes instead of 10
```

After running for a day, the historical query:

```bash
# CPU stats for today
sar -u

# Same, for a specific date
sar -u -f /var/log/sysstat/sa14

# Same, for a specific time window
sar -u -s 14:00:00 -e 15:00:00

# IO history
sar -b

# Network history
sar -n DEV

# Memory history
sar -r
```

`sar` is the unsung hero of incident response. The user reports "it was slow at 14:00, fine now." Without `sar`, you have nothing. With `sar`, you have a record. Turn it on. The disk cost (a few MiB per day) is negligible; the value is enormous.

---

## 10. Three rules to close

1. **Read `iostat -x 1` like a chart, not a list.** Each column has a meaning; learn the columns once, then read each one. The wrong reflex is to glance at `%util`, conclude "the disk is busy", and stop. The right reflex is to look at `aqu-sz`, `await`, IOPS, and bandwidth together.
2. **`/proc/<pid>/io` is the answer to "which process is doing the IO."** Not `iotop`, not `pidstat -d` — those are presentation layers. The data is in `/proc/<pid>/io` and you should be able to read it without a tool when the tools fail.
3. **`strace` is a diagnostic, not a profiler.** It is the right tool when you need to see *exactly* what a process is asking the kernel for. It is the wrong tool when you need to know *how much* time the process is spending — `strace -c` is OK for short commands; for long-running workloads use `perf trace` or BPF tools.

---

## 11. References for this lecture

- `man 1 iostat`, `man 8 vmstat`, `man 1 free`, `man 1 strace`, `man 1 ltrace`, `man 8 ss`, `man 1 sar`, `man 1 pidstat`
- `man 5 proc` — `/proc/<pid>/io`, `/proc/<pid>/status`, `/proc/<pid>/maps`
- Linux kernel `Documentation/filesystems/proc.rst`
- Brendan Gregg, *Systems Performance*, Chapter 7 (Memory), Chapter 9 (Disks), Chapter 10 (Network)
- Brendan Gregg, "Linux Performance Tools", <https://www.brendangregg.com/linuxperf.html>
- "linuxatemyram.com" — for the buff/cache misconception, once

---

*Next: the [exercises](../03-exercises/exercise-01-diagnose-a-busy-cpu.md).*
