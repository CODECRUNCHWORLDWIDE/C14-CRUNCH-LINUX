# Lecture 2 — CPU and process tools

> *Lecture 1 gave us the method. This lecture gives us the first column of the USE matrix — the tools that answer the CPU question. Three small commands and one large interactive viewer: `top`, `htop`, `ps`, and `pidstat`. Plus the per-CPU breakdown from `mpstat`. The skill is not to type the commands — it is to **read** the columns. Every column on `htop` reports a number from `/proc`, and every number means something specific. By the end of the lecture you should be able to point at any column on `htop` and say what file in `/proc` produced it.*

---

## 1. `top` first, because it is everywhere

`top` is on every Linux box, with no installation, since 1984. It is less pretty than `htop` and a little harder to read, but it is universally available — the right reflex when you SSH into a box for the first time. `man 1 top`.

The display is split into a **summary area** at the top and a **task area** below. The summary area:

```
top - 14:32:15 up 12 days,  4:18,  3 users,  load average: 1.23, 0.89, 0.45
Tasks: 234 total,   1 running, 233 sleeping,   0 stopped,   0 zombie
%Cpu(s):  3.2 us,  0.8 sy,  0.0 ni, 95.5 id,  0.5 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :  15876.5 total,    412.3 free,   3201.7 used,  12262.5 buff/cache
MiB Swap:   2048.0 total,   1645.2 free,    402.8 used.  12278.8 avail Mem
```

Line by line:

- **Line 1 — `uptime`** equivalent. Boot time, current time, users logged in, load average (1/5/15 minute).
- **Line 2 — Tasks.** Total, running (state `R`), sleeping (state `S` or `D`), stopped (state `T`), zombie (state `Z`).
- **Line 3 — CPU breakdown.** Aggregated across all CPUs. `us` user-space, `sy` kernel-space, `ni` nice'd (lower-priority) user-space, `id` idle, `wa` IO-wait, `hi` hardware interrupts, `si` software interrupts, `st` time stolen by a hypervisor (only non-zero in VMs).
- **Line 4 — Memory.** Total, free, used, buff/cache. Default unit is configurable; `MiB` or `GiB`.
- **Line 5 — Swap.** Total, free, used. `avail Mem` (the column at the end) is the same number as `available` in `free -h` — the amount of memory that could be made available without paging.

The task area below shows processes. The default columns are `PID`, `USER`, `PR` (priority), `NI` (nice value), `VIRT` (virtual memory), `RES` (resident set size), `SHR` (shared memory), `S` (state), `%CPU`, `%MEM`, `TIME+`, `COMMAND`.

The columns that matter most:

- **`S`** — process state. `R` (running), `S` (interruptible sleep — most processes most of the time), `D` (uninterruptible sleep — usually disk wait), `T` (stopped, typically by a debugger or `SIGSTOP`), `Z` (zombie — exited, parent has not waited).
- **`%CPU`** — percentage of one CPU. On a multi-core machine, a process using two cores fully reports 200 %. The display caps at very large numbers but the data is per-core.
- **`RES`** — resident set size in KiB. The amount of physical memory the process has at this instant. *Sum of `RES` across processes can exceed total RAM* because of shared memory; do not panic.
- **`TIME+`** — total CPU time consumed since the process started, in `MM:SS.hh`. A 12-hour-old process with `TIME+` of 11:50:00.00 has been at 99 % CPU since it started.

Interactive keys you should know:

| Key | Effect |
|-----|--------|
| `1` | Toggle per-CPU breakdown in the summary. From "average" to one line per CPU. |
| `c` | Toggle between the short command name and the full command line. |
| `t` | Toggle between the bar-graph CPU display and the percentage display. |
| `m` | Same for memory. |
| `H` | Toggle threads view (one line per thread, not one per process). |
| `M` | Sort by `%MEM`. |
| `P` | Sort by `%CPU` (the default). |
| `T` | Sort by `TIME+`. |
| `R` | Reverse sort order. |
| `k` | Kill a PID (prompts for PID and signal). |
| `r` | Renice a PID. |
| `f` | Field-management screen (add/remove columns). |
| `o` | Other-field-sort. |
| `q` | Quit. |
| `1` then `t` | Per-CPU bars — surprisingly readable. |

For multi-core servers, **press `1` first**. The aggregated CPU view hides single-thread saturation.

---

## 2. `htop`, because it is better

`htop` is `top` with colour, mouse support, a scrollable view, tree mode, in-place editing, and an interactive setup screen. The same data, presented better. `man 1 htop`.

The default layout: per-CPU bars across the top (one bar per CPU), memory and swap bars below, then the process list. The colour code in the CPU bars:

| Colour | Meaning |
|--------|---------|
| Blue | Low-priority (nice'd) user-space (`%ni`) |
| Green | User-space (`%us`) |
| Red | Kernel-space (`%sy`) |
| Orange | IO-wait (`%wa`) |
| Magenta | Steal (hypervisor stole the CPU; only non-zero in VMs) |
| Grey | Idle (`%id`) |

A solid red bar means a CPU is spending its time in the kernel — which often means heavy IO, heavy network, or heavy syscall traffic. A solid orange bar means the CPU is idle but waiting on IO. A solid green bar is application code running. The colour-coded per-CPU view is the single most informative ten-pixel-tall image in Linux performance work.

The function keys (also shown at the bottom of the screen):

| Key | Effect |
|-----|--------|
| `F1` | Help screen. |
| `F2` | Setup — add/remove columns, change colours, change update interval. |
| `F3` | Search by name (live-filter as you type). |
| `F4` | Filter (only show processes matching a string). |
| `F5` | Tree view (parent/child hierarchy). |
| `F6` | Sort by column. |
| `F7` / `F8` | Nice down / up. |
| `F9` | Send signal (Kill menu). |
| `F10` | Quit. |
| `Space` | Tag a process. |
| `c` | Tag the parent and children. |
| `U` | Untag all. |
| `t` | Tree view (same as F5). |
| `H` | Hide / show user threads. |
| `K` | Hide / show kernel threads. |
| `p` | Show full path of executable. |

Setup (`F2`) is the highest-value menu: you can add a `CPU%` column that is **per-process not per-core** (`PERCENT_CPU` in setup; called `CPU%` by default in the column list), an `IO_RATE` column for disk activity, a `STARTTIME` column, and so on. Spend five minutes in setup the first time and customise your `htop` to the columns you read.

The `htop` default sort is by `CPU%` descending. The top of the list is "what is on the CPU right now."

---

## 3. The process state column — `R`, `S`, `D`, `T`, `Z`

The single column on `top`/`htop`/`ps` that the textbook never explains well. The states:

| Letter | Name | Meaning |
|--------|------|---------|
| `R` | Running | On a CPU, or runnable and waiting for one. |
| `S` | Sleeping (interruptible) | Waiting for some event; can be woken by a signal. The state of almost every process most of the time. |
| `D` | Sleeping (uninterruptible) | Waiting for IO at the kernel level. Cannot be killed except by a reboot. Long-lived `D` is the signal that the storage path is stuck. |
| `T` | Stopped | Suspended by `SIGSTOP` (usually a debugger or a `Ctrl-Z`). |
| `Z` | Zombie | Exited; the parent has not called `wait()` to read the exit status. The process is gone but the entry remains. |
| `I` | Idle (kernel thread) | A new state since kernel 4.20 for idle kernel threads, so they do not inflate the load average. |
| `t` | Tracing stop | Stopped by a debugger via `ptrace`. |

The two important asymmetries:

- **`R` versus `S`.** A `R` process is using the CPU or wants to be. An `S` process is voluntarily waiting. The CPU's time goes to `R` processes; the `S` processes do not appear in `%CPU`. The load average counts both `R` and `D` (not `S`), which is why a busy NFS server can show load 50 with the CPUs idle.
- **`D` versus `S`.** Both look sleeping; the difference is whether a signal can wake the process. `D` processes are blocked in the kernel waiting for IO that must complete; they ignore signals, including `SIGKILL`. A persistent `D` process is almost always disk- or network-IO problem: a missing NFS server, a broken USB drive, a hung block device. The only way to clear a `D` is to satisfy the IO or reboot.

When you spot a `D` process in `top`, the next two questions are:

1. **What is it waiting on?** `cat /proc/<pid>/wchan` shows the kernel function the process is sleeping in. `nfs_readpage_done`, `io_schedule`, `wait_on_page_writeback` — the function name tells you the subsystem.
2. **How many `D` processes are there?** `ps -eo state,pid,comm | grep '^D'`. One D process is a hiccup; ten D processes blocked on the same `wchan` is a system pathology.

---

## 4. The `ps` command — the snapshot view

`top` and `htop` stream. `ps` is one snapshot. The first is for incident response; the second is for scripts and one-shot inspection. `man 1 ps`.

`ps` has two flag dialects:

- **BSD-style** (no dash): `ps aux` — every process, every user, with detailed info.
- **Unix-style** (single-dash): `ps -ef` — every process (`-e`), full format (`-f`).

The two are mostly equivalent. The columns you want most often are:

```bash
ps -eo pid,ppid,user,stat,pcpu,pmem,rss,vsz,start_time,etime,comm,args
```

Field names:

- `pid` — process ID.
- `ppid` — parent process ID.
- `user` — process owner.
- `stat` — state plus flags. `R`, `S`, `D`, `T`, `Z` as above; plus `<` (high priority), `N` (low priority), `s` (session leader), `l` (multi-threaded), `+` (in the foreground process group).
- `pcpu` — percent CPU.
- `pmem` — percent of physical memory.
- `rss` — resident set size in KiB.
- `vsz` — virtual size in KiB.
- `start_time` — wall-clock start time.
- `etime` — elapsed time since start (`[[DD-]hh:]mm:ss`).
- `comm` — short command name (max 15 chars).
- `args` — full command line.

Useful one-liners:

```bash
# Top 10 by CPU
ps -eo pid,pcpu,comm --sort -pcpu | head -11

# Top 10 by RSS (resident memory)
ps -eo pid,rss,comm --sort -rss | head -11

# Every D-state process
ps -eo pid,state,wchan:30,comm --no-headers | awk '$2 == "D"'

# Every zombie
ps -eo pid,ppid,state,comm --no-headers | awk '$3 == "Z"'

# Every thread of a process
ps -T -p $(pgrep -f my-service | head -1)

# Process tree
ps -ejH
# Or: pstree -p
```

The "BSD versus Unix" thing matters in exactly one circumstance: scripts. Pick one and stay with it; do not mix `ps aux` and `ps -ef` in the same script. The output formats differ in small ways (`ps aux` truncates command lines at terminal width by default; `ps -ef` does too but the field positions are different).

---

## 5. `pidstat` — per-process system rates

`pidstat` is what `top` would be if it were a stream of *numbers* instead of a screen of *processes*. It comes from the `sysstat` package and is the per-process companion to `iostat`/`vmstat`. Underused. `man 1 pidstat`.

Default invocation:

```bash
$ pidstat 1 5
Linux 6.8.0 (host)  2026-05-14  _x86_64_  (8 CPU)

14:32:15 UID PID    %usr %system  %guest   %wait    %CPU  CPU  Command
14:32:16   0   1    0.00    0.00    0.00    0.00    0.00    3  systemd
14:32:16   0 412    0.00    0.99    0.00    0.00    0.99    1  sshd
14:32:16 1000 5234 99.00    1.00    0.00    0.00  100.00    5  python3
```

`pidstat 1 5` samples every 1 second for 5 cycles. The columns: `%usr`, `%system`, `%guest`, `%wait` (CPU wait, time spent runnable but not on a CPU — saturation!), `%CPU` (total). Variant flags:

- **`pidstat -d 1`** — per-process IO. `kB_rd/s`, `kB_wr/s`, `kB_ccwr/s` (cancelled writes), `iodelay` (block IO delay).
- **`pidstat -r 1`** — per-process memory. `minflt/s`, `majflt/s` (page faults), `VSZ`, `RSS`, `%MEM`.
- **`pidstat -w 1`** — per-process context switches. `cswch/s` (voluntary), `nvcswch/s` (involuntary).
- **`pidstat -t 1`** — per-thread, not per-process.
- **`pidstat -p PID 1`** — focus on one PID.

The column `pidstat 1` provides that `top` does not is **`%wait`** — runnable time not on a CPU. When `%wait` is high for a process, that process wants to run and cannot get a CPU. Cause: CPU saturation. The fix is more CPUs or less work.

A characteristic invocation when something is wrong:

```bash
pidstat 1                     # what is on the CPU?
pidstat -d 1                  # what is doing IO?
pidstat -r 1                  # what is faulting?
pidstat -w 1                  # what is context-switching?
```

The four together are "the per-process USE matrix."

---

## 6. `mpstat -P ALL 1` — per-CPU breakdown

When `top` aggregate says 12 % CPU and you want to know whether one CPU is at 100 % or all CPUs are at 12 %, `mpstat -P ALL 1` is the answer. `man 1 mpstat`.

```bash
$ mpstat -P ALL 1 1
Linux 6.8.0 (host)  2026-05-14  _x86_64_  (8 CPU)

14:32:15     CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest  %gnice   %idle
14:32:16     all   12.50    0.00    0.50    0.00    0.00    0.00    0.00    0.00    0.00   87.00
14:32:16       0    1.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00    0.00   98.00
14:32:16       1    1.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00   99.00
14:32:16       2    0.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00    0.00   99.00
14:32:16       3   99.00    0.00    1.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00
14:32:16       4    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
...
```

CPU 3 is at 100 %; the rest idle. Aggregate says 12 % because the average of "one at 100 and seven at 0" is 12.5. The pattern is the canonical single-threaded saturation shape from Lecture 1 §7.1.

For NUMA-aware reasoning (which CPU is on which NUMA node — relevant when you have a process pinned to a node and the work is on the other), `mpstat -P NODE0` and `-P NODE1` aggregate by NUMA node. `lscpu` shows the topology.

---

## 7. Reading `/proc/<pid>/status`

The text-file replacement for half of what `top` shows. `cat /proc/<pid>/status`:

```
Name:   python3
Umask:  0022
State:  R (running)
Tgid:   5234
Ngid:   0
Pid:    5234
PPid:   412
TracerPid:      0
Uid:    1000    1000    1000    1000
Gid:    1000    1000    1000    1000
FDSize: 64
Groups: 4 24 27 30 46 100 1000
NStgid: 5234
NSpid:  5234
NSpgid: 5234
NSsid:  412
VmPeak:   123456 kB
VmSize:   123450 kB
VmLck:         0 kB
VmPin:         0 kB
VmHWM:     45678 kB
VmRSS:     45670 kB
RssAnon:   42000 kB
RssFile:    3000 kB
RssShmem:    670 kB
VmData:    50000 kB
VmStk:       132 kB
VmExe:      2000 kB
VmLib:     20000 kB
VmPTE:       300 kB
VmSwap:        0 kB
HugetlbPages:  0 kB
CoreDumping:   0
THP_enabled:   1
Threads:       3
SigQ:   0/63123
SigPnd: 0000000000000000
ShdPnd: 0000000000000000
...
voluntary_ctxt_switches:        12345
nonvoluntary_ctxt_switches:        45
```

The fields you read:

- **`State`** — `R`, `S`, `D`, `T`, `Z`. Same as `top`'s `S` column.
- **`VmPeak`** — high-water mark of virtual memory; ever-grown size.
- **`VmSize`** — current virtual size.
- **`VmHWM`** — high-water mark of resident set size.
- **`VmRSS`** — current RSS (same as `RES` in `top`).
- **`RssAnon`** / **`RssFile`** / **`RssShmem`** — RSS breakdown (anonymous, file-backed, shared memory).
- **`VmSwap`** — pages of this process currently in swap. Non-zero is bad news.
- **`Threads`** — count of threads in this process.
- **`voluntary_ctxt_switches`** — the process voluntarily gave up the CPU (e.g., called `sleep` or blocked on IO).
- **`nonvoluntary_ctxt_switches`** — the kernel pre-empted the process because somebody else needed the CPU; the count grows when the system is CPU-saturated.

The text-file form is the one we will parse in the challenge.

The companion file `/proc/<pid>/io`:

```
rchar: 234567
wchar: 89012
syscr: 1234
syscw: 567
read_bytes: 200000
write_bytes: 80000
cancelled_write_bytes: 0
```

- **`rchar`** / **`wchar`** — total bytes read/written by the process *through the read/write syscalls*. Includes data served from the page cache.
- **`syscr`** / **`syscw`** — count of read/write syscalls.
- **`read_bytes`** / **`write_bytes`** — bytes that *actually went to or came from a block device*. The difference between `rchar` and `read_bytes` is "how much the page cache served." A process can have huge `rchar` and tiny `read_bytes` if it is reading hot data; that is the page cache earning its keep.

Reference: `man 5 proc`, section "`/proc/<pid>/io`".

---

## 8. Putting it together — a CPU-bound diagnostic walk

Suppose the user reports a service is unresponsive. You SSH in. You run the sixty-second checklist. By command three (`vmstat 1`), you see:

```
procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 5  0      0  3210000 100000 8000000   0    0     0    16  234  567 99  1  0  0  0
```

Five runnable processes (`r 5`); high `%us` (99 %); zero `wa` (no IO wait); zero `si`/`so` (no swap). CPU-bound. Continue:

```bash
$ mpstat -P ALL 1 1
14:32:15     CPU    %usr   %nice    %sys ... %idle
14:32:16     all   99.00    0.00    1.00 ...  0.00
14:32:16       0   99.00    0.00    1.00 ...  0.00
14:32:16       1   99.00    0.00    1.00 ...  0.00
...
14:32:16       7   99.00    0.00    1.00 ...  0.00
```

All CPUs at 99 %. Not a single-thread bottleneck — parallel saturation. Now find what:

```bash
$ pidstat 1 1
14:32:15   UID  PID   %usr  %system  %CPU  CPU  Command
14:32:16  1000 5234  399.00   2.00  401.00    -  worker
14:32:16  1000 5235  399.00   2.00  401.00    -  worker
```

Two `worker` processes, each consuming 400 % CPU (i.e., four cores each). That accounts for eight cores. Confirm the process structure:

```bash
$ ps -eo pid,ppid,user,pcpu,nlwp,comm | awk 'NR == 1 || $4 > 100'
PID  PPID USER %CPU NLWP COMMAND
5234  412 alice 401  16  worker
5235  412 alice 401  16  worker
```

Each `worker` has 16 threads. Diagnosis: a parallel workload running multiple workers, each multi-threaded, fully utilising 8 cores. The fix is either to throttle (reduce worker count or thread count), to add cores, or to confirm with the application owner that this is the expected steady state and what looked like an incident is actually correct behavior.

Notice we have not changed anything yet. We have only **measured** and **read**. The change comes after the discussion with the application owner.

---

## 9. Two pitfalls

### 9.1 Sampling versus tracing

`top` and friends are **sampling** tools. They look at `/proc` once per second and report what they saw. Short-lived processes (less than one second on the CPU) can be invisible to `top`. The classic case is a `make -j8` build that spawns thousands of short-lived `gcc` invocations — `top` shows the parent `make` consuming little, and the host shows 100 % CPU.

The solution is a **tracing** tool. `execsnoop` from `bcc-tools` watches every `exec()` system-wide and prints it. Run `execsnoop` while a sampling tool says "100 % CPU but no process is using it" and the answer becomes visible.

We will not run `execsnoop` until the resources walk-through; for now, the lesson is: **if `top` does not show a culprit, the culprit may be many short-lived processes**.

### 9.2 The aggregated-CPU trap

We have said this twice and we will say it a third time because students still trip on it: **`top`'s default `%CPU` is per-core, but the summary line at the top is aggregated**. A 200 % process on an 8-core box is using 25 % of total CPU; the summary may show "25 % us" and you may conclude the system is fine when one of your cores is in fact pinned. Press `1` to break out per-CPU; or use `htop` (which shows per-CPU bars by default); or run `mpstat -P ALL 1`.

The right reflex on a multi-core box is **per-CPU first, aggregated second**.

---

## 10. References for this lecture

- `man 1 top`, `man 1 htop`, `man 1 ps`, `man 1 pidstat`, `man 1 mpstat`
- `man 5 proc` — the `/proc/<pid>/*` files
- Brendan Gregg, *Systems Performance*, Chapter 6 (CPUs)
- Brendan Gregg, "CPU Flame Graphs", <https://www.brendangregg.com/FlameGraphs/cpuflamegraphs.html>
- `htop` source, `htop.dev` — the README is short and the column-name discussion is useful

---

*Next: [Lecture 3 — IO, memory, and syscalls](./03-io-memory-syscalls.md).*
