# Lecture 1 — The USE method and where to start

> *Performance debugging fails the same way every time. The user reports slow. The engineer reaches for the tool they know. They find a number that looks high. They change a configuration. They wait. The number is still high, or it is low and the user still says slow. They reach for another tool. They have already, by then, made the diagnosis impossible — because the system they were measuring is no longer the system that was slow.*
>
> *The discipline that prevents this is not a tool. It is a **method**. The classical method for Linux performance work is the **USE method**, articulated by Brendan Gregg around 2012 and now the standard vocabulary of the industry. The method has one job: tell you what to measure, in what order, before you change anything. We learn it first because every tool the rest of the week introduces is one of its instruments.*

---

## 1. What "slow" means, and why the user's word is not the answer

A user reports "the page is slow." This sentence has at least four meanings:

1. **Latency** — the page takes longer to start rendering than it used to.
2. **Throughput** — the page renders quickly when one user hits it, but slowly when ten users hit it.
3. **Variance** — the page is usually fast and occasionally slow, and the slow tail is what the user remembers.
4. **Availability** — the page returns a 5xx some fraction of the time and the user is rolling that into "slow."

Latency and throughput are different problems with different tools. Variance is a third problem (the long tail is rarely the median). Availability is a fourth (no amount of perf tuning solves a crashing service). The first move of any performance investigation is to **convert the user's report into one of these four categories**, with a number attached:

- "P50 page load was 80 ms; it is now 9000 ms. Latency, 100× regression."
- "Single-user load is 80 ms; ten-user load is 9000 ms. Throughput, 10× regression."
- "P50 is 80 ms and P99 is 9000 ms; the user is in the tail. Variance."
- "Five percent of requests return 503. Availability."

Without that number, every measurement you make is a guess. With it, every measurement has an acceptance criterion: the number must improve.

This lecture is about the **first three** — latency, throughput, variance. Availability is Week 5's territory (the systemd unit; the restart loop; the journal). Performance work assumes the service is up.

---

## 2. Brendan Gregg's USE method

The USE method asks **one question, three ways, for each resource**:

> For every resource: **Utilization, Saturation, Errors.**

Where:

- **Utilization** is the average fraction of time the resource was busy. "The disk was busy 87 % of the last second."
- **Saturation** is the degree to which the resource has additional work waiting that it could not handle. "There were on average 4 IO requests queued at the disk, waiting their turn."
- **Errors** is the count of error events. "There were 12 read errors on `/dev/sda` in the last hour."

The discipline is to ask the three questions in order, for every resource that could be the bottleneck. For a typical single-host service, the resources are the same four every time:

1. **CPU**
2. **Memory** (capacity and bandwidth)
3. **Disk** (each storage device; IOPS, bandwidth, latency)
4. **Network** (each interface; bandwidth, packet errors)

For each, there is a tool that reports utilization, a tool (often the same one) that reports saturation, and a tool that reports errors. The lecture in §6 walks the four-by-three matrix; for the moment, the shape:

| Resource | U (utilization) | S (saturation) | E (errors) |
|----------|----------------|-----------------|------------|
| CPU | `top` `%CPU`, `mpstat -P ALL 1` per-CPU | `vmstat 1` column `r` (run-queue), load average | `perf stat` (CPU errors are rare) |
| Memory | `free -h` "used" minus "buff/cache" | `vmstat 1` `si`/`so` (any non-zero is bad) | `dmesg` (OOM kills, ECC errors) |
| Disk | `iostat -x 1` `%util` per device | `iostat -x 1` `aqu-sz` (queue depth), `await` | `dmesg`, `/sys/block/*/device/io_errors` |
| Network | `sar -n DEV 1` `%ifutil`, `ip -s link` | `ss -s` accept-queue, `nstat` retransmits | `ip -s link` `RX/TX errors`, `nstat` drops |

The method's value is not that each cell is novel — every line on this matrix was a tool somebody used before 2012. The value is that the **matrix is exhaustive**. If you have asked U, S, and E for every resource and none of them is anomalous, the bottleneck is not in the obvious places, and you can start the more expensive investigation (lock contention, application-level bugs, kernel-internal scheduling pathologies) with confidence that you ruled out the cheap answers first.

Read: Brendan Gregg, "The USE Method", <https://www.brendangregg.com/usemethod.html>. Two screens long; the foundational text.

---

## 3. The first sixty seconds

Before you can ask USE questions thoughtfully, you need a fast scan that tells you which resource to focus on. Brendan Gregg distilled the Netflix engineering team's habits into a **ten-tool checklist** that takes about sixty seconds and is meant to be run in this exact order on any new alert:

```bash
uptime
dmesg | tail
vmstat 1
mpstat -P ALL 1
pidstat 1
iostat -xz 1
free -m
sar -n DEV 1
sar -n TCP,ETCP 1
top
```

The point is not that each command tells you the answer. The point is that running the **whole sequence** in order forces you to look at the system from ten angles before you commit to a hypothesis. Most of the time, the answer is obvious by command three or four — but you keep going, because the bottleneck might be obvious in one and the *cause* obvious in another.

Annotated:

1. **`uptime`** — boot time and load average. If the load average is 0.5 you can skip the panic; if it is 50 on a 4-CPU box, the system is pinned and you already know the shape of the problem.
2. **`dmesg | tail`** — last few kernel messages. OOM kills, hardware errors, NIC link flaps, filesystem errors. Surprisingly often, the answer is here.
3. **`vmstat 1`** — system-wide cycle counter. Watch one minute. `r` (runnable processes) tells you CPU saturation; `b` (blocked) tells you IO saturation; `si`/`so` tells you swap; `us`/`sy`/`id`/`wa` tells you where CPU time is going.
4. **`mpstat -P ALL 1`** — per-CPU CPU breakdown. One CPU pinned and others idle = single-threaded bottleneck. All CPUs pinned = parallel saturation. One CPU at high `%sys` = kernel-time problem.
5. **`pidstat 1`** — per-process CPU rates over time. Identifies *which* process is on the CPU.
6. **`iostat -xz 1`** — extended per-device IO. `%util` and `aqu-sz` tell you which disk (if any) is saturated; `await` tells you the latency.
7. **`free -m`** — memory snapshot. `available` is the number that matters.
8. **`sar -n DEV 1`** — per-interface network rates. Saturation of a 1 Gb link is at about 119 MB/s.
9. **`sar -n TCP,ETCP 1`** — TCP-level rates and errors: connection failures, segments retransmitted.
10. **`top`** — the full process table, sorted by CPU. The grand finale. By now you already know what to look for; `top` confirms.

Print the list. Pin it to your monitor. Run it from memory by the end of Week 7. It is your **`uptime`-to-`top`** procedure.

Reference: Brendan Gregg, "Linux Performance Analysis in 60,000 Milliseconds", <https://www.brendangregg.com/Articles/Netflix_Linux_Perf_Analysis_60s.pdf>.

---

## 4. The four pillars

The four resources — CPU, memory, disk, network — are not equal, and their interactions matter. A few honest observations:

### 4.1 CPU

CPU is the easiest resource to reason about because the question is shallow: "is one of my CPUs at 100 %, and which process?" `top` answers in one screen. The pitfalls:

- **Per-core versus aggregated.** `top` reports `%CPU` per-core by default — a process showing 200 % is using two cores. Press `1` in `top` or `H` in `htop` to break out per-CPU. `htop`'s top bar gives the per-CPU picture without keystrokes.
- **Load average is not CPU percentage.** Load average is the moving average of (runnable + uninterruptible-sleeping) tasks. Load 4 on a 4-CPU box means "fully utilised"; load 4 on a 1-CPU box means "three tasks queued."
- **`%iowait` is not a CPU bottleneck.** `%iowait` is the fraction of CPU idle time during which at least one task was IO-blocked. The CPU was idle — high `%iowait` is a hint that some workload was waiting on IO, but it does not mean the CPU is the bottleneck and it does not even mean the disk is, depending on what the workload was doing.
- **Single-core saturation is the silent killer.** A Python web server with a global lock can pin one CPU at 100 % while the other seven cores idle. `top` aggregated will show "12 % CPU" and you will conclude the system is fine. Always look at the per-core view.

### 4.2 Memory

Memory has two questions:

- **Capacity** — is the system out of memory and paging out anonymous pages to swap? `vmstat` `si`/`so`, `free -h` `available`, `/proc/meminfo` `Available`. Any non-zero swap-in is a latency disaster.
- **Bandwidth** — are the CPUs starved waiting for memory? This is rarely a single-host concern at workshop scale (`perf stat` reports `cache-misses` and `LLC-load-misses`); we mention it for completeness.

The "Linux ate my RAM" misconception is the single most common memory-related confusion. The `free -h` output shows:

```
              total        used        free      shared  buff/cache   available
Mem:           15Gi       3.2Gi       210Mi       110Mi        12Gi        12Gi
```

The 12 GB in `buff/cache` is the page cache. It is **reclaimable** the instant some process asks for memory. The right column to read is `available` — the amount the kernel would hand to a new allocation. On the line above, `available` is 12 Gi; the system is not low on memory. The mistake is to read `free` (210 Mi) and panic.

Reference: linuxatemyram.com (a one-page essay that exists precisely to settle this confusion).

### 4.3 Disk

Disk is the hardest resource to reason about because the tools that report on it predate SSDs. `iostat`'s `%util` was designed for rotating disks (one head, one seek at a time) and tops out at "the disk is saturated" near 100 %. On a multi-queue NVMe device, the disk can be running at 30 % of its theoretical IOPS and `%util` will already show 99 % because the device accepts a new IO most every millisecond. The truer signal on modern hardware is the **queue depth** (`aqu-sz`) and **latency** (`await`).

The four numbers to read on `iostat -x 1`:

- **`r/s`, `w/s`** — operations per second. Compare to your device's spec.
- **`rkB/s`, `wkB/s`** — bandwidth. A 7200 RPM disk peaks around 150 MB/s sequential, 1-2 MB/s random. A SATA SSD peaks around 500 MB/s. An NVMe at 3-7 GB/s.
- **`await`** — mean time per IO in milliseconds. For a rotating disk, 5-10 ms is fine; >50 ms suggests saturation. For an SSD, 0.1-1 ms is fine; >5 ms is concerning. For NVMe, sub-millisecond is the design point.
- **`aqu-sz`** — average queue depth. Persistent values above 1 indicate the disk cannot keep up with the workload; the workload is queueing IOs.

We dedicate Lecture 3 (§3-§5) to reading `iostat` thoroughly.

### 4.4 Network

Network has two questions:

- **Bandwidth** — is the link saturated? `sar -n DEV 1`, `ip -s link`. A 1 Gb link saturates at 119 MB/s of payload (the other 6 % is framing). On modern hosts, network rarely saturates; the question is more often **latency**, which is invisible to `sar`.
- **Connection-level health** — accept-queue overflow, retransmits, listen drops. `ss -s` for the summary; `nstat` for the cumulative counters; `ss -tan state established` for the connections.

The single most common network performance issue is the **application is too slow to accept** — incoming SYNs complete the handshake, the connection sits in the kernel's accept queue, the application has not called `accept()` fast enough, the queue fills, new SYNs are dropped, the client retries with a 3-second back-off and the user calls it "slow." The signal is `ss -tln` showing non-zero `Recv-Q` on the `LISTEN` row.

We come back to this in Lecture 3 §8 and Week 9.

---

## 5. Where the time goes — a mental model

The diagnostic question that subsumes all the above is **"where is the time going?"** A request takes 9 seconds. Those nine seconds are spent in one of:

- **On-CPU time** — the process is executing instructions. The fix is in the application code or in the CPU it runs on.
- **Off-CPU, blocked on IO** — the process called `read()` or `write()` and the kernel has not finished. The fix is in the storage path: filesystem, block layer, device, network.
- **Off-CPU, runnable but not running** — the process is ready to run but no CPU is free. The fix is reducing CPU load (more cores, less work, scheduling priority).
- **Off-CPU, waiting on a lock** — the process is waiting for some other process or thread to release a mutex/futex. The fix is in the locking design.
- **Off-CPU, sleeping** — the process called `sleep()` or `select()` with a timeout. This is intentional; do not mistake intentional sleep for a bottleneck.

Each of the five has a tool that reveals it:

- **On-CPU** — `top`, `pidstat`, `perf top`, flame graphs.
- **Blocked on IO** — process state `D` in `ps`, `/proc/<pid>/wchan`, `iotop`, `iostat`.
- **Runnable** — `vmstat 1` column `r`, load average above core count.
- **Waiting on a lock** — `strace -p PID` shows `futex(...)` waiting; `perf lock` for the kernel side; application-level profilers for the user side.
- **Sleeping** — process state `S`, low CPU, low IO; usually correct behavior.

The mental model the rest of the week trains is:

> **The system has 100 % of its time accounted for, every second. Your job is to find the bucket.**

---

## 6. The USE matrix, expanded

A fuller view of the four-by-three matrix. Use this as a checklist; tape to monitor.

### CPU

- **Utilization** — `mpstat -P ALL 1` per-CPU; `top` aggregated. Alarm threshold: any single CPU above 80 % for sustained periods, or all CPUs above 80 % in aggregate, depending on the workload.
- **Saturation** — `vmstat 1` column `r` greater than the core count; load average above core count; in `pidstat`, column `%CPU` above 100 (single-thread saturation on a multi-thread process).
- **Errors** — `perf stat` records CPU-internal errors (cache misses, mispredictions). Hardware errors are rare; `dmesg` will show them if they happen.

### Memory

- **Utilization** — `free -h` `used`; `/proc/meminfo` `MemAvailable`. Alarm threshold: `MemAvailable` below 10 % of `MemTotal`.
- **Saturation** — `vmstat 1` `si`/`so` non-zero (the system is swapping); `dmesg | grep -i oom` shows the OOM killer ran.
- **Errors** — `dmesg` for OOM kills and ECC errors (on ECC RAM). Application-level allocation failures (`ENOMEM` from `mmap`/`malloc`) usually show up as crashes.

### Disk (per device)

- **Utilization** — `iostat -x 1` `%util`. On rotating disks: high (>90 %) means saturated. On SSDs and NVMe: less reliable; read `aqu-sz` instead.
- **Saturation** — `iostat -x 1` `aqu-sz` persistently above 1 (or above the device's queue capacity); `await` rising above the device's spec.
- **Errors** — `dmesg` for IO errors; `/sys/block/sdX/device/io_errors`; SMART data via `smartctl -a /dev/sdX`.

### Network (per interface)

- **Utilization** — `sar -n DEV 1` `rxkB/s` and `txkB/s` versus link bandwidth; `ip -s link` total bytes since boot.
- **Saturation** — `ss -s` listen drops; `nstat` `TcpExtListenOverflows`; `tc -s qdisc show` queue drops; for high-precision applications, `ss -i` per-socket retransmits and CWND.
- **Errors** — `ip -s link` `RX errors` and `TX errors`; `nstat` `TcpRetransSegs`.

The point of the matrix is that you go through every cell, in order, before you settle on a hypothesis. Most of the time the answer is obvious by the third or fourth cell — but if you skip cells, you find yourself two hours later having "fixed" something orthogonal to the actual problem.

---

## 7. Three common-case patterns

After enough incident response you start to recognise shapes. Three that come up almost weekly:

### 7.1 "One CPU pinned, seven idle"

The single most common performance pattern on multi-core hosts running Python, Ruby, or Node services. You see it in `mpstat`:

```
$ mpstat -P ALL 1
01:23:45     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
01:23:46     all   12.62    0.00    0.50    0.00    0.00    0.00    0.00    0.00    0.00   86.88
01:23:46       0  100.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
01:23:46       1    0.50    0.00    0.50    0.00    0.00    0.00    0.00    0.00    0.00   99.00
01:23:46       2    0.50    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.50
...
```

One CPU at 100 %, others idle. Either:

- A single thread is doing all the work (the GIL in CPython; a serialised loop in your code; a sync I/O loop where you needed `asyncio`).
- A single process is allocated to one CPU by `taskset` or by cgroup pinning and the work is single-threaded.

The fix is either to parallelise the work or to recognise the inherent serialisation. The diagnostic step that proves it is `htop` with the per-CPU bars visible; if one bar is solid red and the others are white, you have your answer.

### 7.2 "High `%iowait`, system feels frozen"

The pattern of an IO-bound system. `vmstat 1` shows:

```
$ vmstat 1
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 0  4      0  423456  88112 8123456    0    0  98432    16  223  315  2  1  3 94  0
 0  5      0  423344  88112 8123480    0    0  87616    32  198  283  1  2  2 95  0
```

The signal: `b` (blocked) is non-zero (4 and 5); `wa` is enormous (94 %, 95 %); `bi` (block IO in) is heavy (87-98 MB/s read). The CPU is mostly idle but at least one task is waiting on IO. The system "feels slow" because every request that touches the disk takes seconds.

The follow-up is `iostat -x 1`:

```
Device   r/s   w/s   rkB/s   wkB/s  await  %util
sda    1234.0   2.0  98765.0    16.0   78.5   99.2
```

99 % util on `sda`; 78 ms `await` (this is a rotating disk in saturation). The fix is to either reduce the IO load, move to faster storage, or find what is reading 98 MB/s from `sda` (`iotop -ao` for the cumulative view; `pidstat -d 1` for the per-process rate).

### 7.3 "Memory is fine but the system is swapping"

The pattern that misleads. `free -h` shows comfortable available memory:

```
              total        used        free      shared  buff/cache   available
Mem:           15Gi       6.0Gi       210Mi        50Mi       9.0Gi       9.0Gi
Swap:         2.0Gi       1.4Gi      600Mi
```

9 GB available, but swap is 1.4 GB used. The cause is usually historical — the kernel paged out idle anonymous memory at some point in the past (when the system was under brief pressure) and never paged it back. The pages will be paged back if and when their owner reads them, paying a one-time latency cost.

This is rarely a real problem unless `vmstat`'s `si`/`so` columns show ongoing activity. The misleading thing is that `free -h` shows non-zero swap-used; the reassuring thing is that current `vmstat` `si`/`so` shows 0/0.

If `vmstat` `si`/`so` are non-zero, the system is paging actively. Buy more RAM, reduce the working set, or tune `vm.swappiness` (the kernel parameter that controls how readily the kernel reaches for swap; default 60; many database tunings set it to 1 or 10).

---

## 8. What the rest of the week does

The remaining two lectures take this method and instrument it:

- **Lecture 2** is the CPU and process-table side. `htop`, `top`, `ps`, `pidstat`, `mpstat`. The tools that answer "which process is on the CPU and what is it doing?" and the way to read process state (`R`, `S`, `D`, `T`, `Z`).
- **Lecture 3** is the IO, memory, and syscall side. `iostat`, `vmstat`, `free`, `strace`, `ltrace`, `/proc/<pid>/io`. The tools that answer "which device is saturated and what is the process asking it for?"

The exercises induce each shape on purpose: a busy CPU (exercise 1), an interesting syscall stream (exercise 2), a saturated disk (exercise 3). The challenges ask you to instrument the system yourself (write a mini-`htop` from `/proc`) and to identify a noisy neighbor when somebody else is the cause. The mini-project gives you a synthetic load and asks for a full diagnostic report, with numbers, identifying which of the four pillars is at fault.

Tape the matrix to your monitor. The discipline is **measure before you change**, and the order of the measurement is the order of the matrix.

---

## 9. Three rules to remember before you change anything

1. **Get a number.** The user's word is not a number. "Slow" is not a number. "P50 page load was 80 ms; it is now 9000 ms" is a number. You cannot tell whether your change helped without a number to compare to.
2. **Run the sixty-second checklist first.** Resist the urge to reach for the tool you used last time. The pattern may be different this time and the checklist forces you to look at the system from ten angles before you commit.
3. **Measure first, change second, measure third.** If you change before you measure, you cannot reproduce the bug. If you change without measuring after, you cannot tell whether you helped.

The third rule is the most violated, because the urge to "do something" is overwhelming when somebody is paging you at 02:00. Resist it. The fastest path through an incident is the one that runs the checklist, identifies the bottleneck, applies one change, and re-runs the checklist to confirm.

---

## 10. References for this lecture

- Brendan Gregg, "The USE Method", <https://www.brendangregg.com/usemethod.html>
- Brendan Gregg, "Linux Performance Analysis in 60,000 Milliseconds", <https://www.brendangregg.com/Articles/Netflix_Linux_Perf_Analysis_60s.pdf>
- Brendan Gregg, *Systems Performance: Enterprise and the Cloud*, 2nd ed., 2020. Chapter 2 (Methodologies), Chapter 6 (CPUs).
- linuxatemyram.com — the "Linux ate my RAM" essay.
- `man 1 vmstat`, `man 1 iostat`, `man 1 mpstat`, `man 1 sar`.
- Linux kernel `Documentation/filesystems/proc.rst`.

---

*Next: [Lecture 2 — CPU and process tools](./02-cpu-and-process-tools.md).*
