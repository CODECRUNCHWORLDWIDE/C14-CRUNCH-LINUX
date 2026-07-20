# Week 7 — Observability: htop, iostat, strace, and the /proc filesystem

> *Last week you put your service on the internet. This week it gets slow, and the user wants to know why by 3 p.m. There are four possible answers — CPU, memory, disk, network — and they correspond to four sets of tools. The discipline of finding which of the four is responsible, before you start changing anything, is called **performance debugging**, and the standard mental model is Brendan Gregg's USE method: for every resource, ask Utilization, Saturation, and Errors. We earn the model by inducing each kind of bottleneck on purpose with `yes`, `dd`, `stress-ng`, and a single misbehaving Python loop, then finding the cause with `htop`, `iostat`, `vmstat`, `free`, `ss`, `strace`, and a careful read of `/proc`.*

Welcome to **Week 7 of C14 · Crunch Linux**. Six weeks of mechanics: shell, pipes, permissions, scripts, services, SSH and firewalls. Your service is provisioned, hardened, and serving traffic. Now the user opens a ticket: "the page that loaded in 80 ms last Tuesday takes nine seconds today." Your job is not to guess which subsystem is at fault. Your job is to **measure**.

If Week 6 was the `~/.ssh/config` entry and the `nft add rule` invocation, Week 7 is the `htop` row that shows one process at 100 % of one core, the `iostat -x 1` column that shows `%util` pegged at 99, the `strace -c -p PID` summary that names the syscall eating the time, and the `cat /proc/PID/status` line that confirms the process is in state `D` (uninterruptible IO wait) and not state `R` (running). Three habits with five small tools, and one very large filesystem (`/proc`) that ties them all together. We earn them by inducing each kind of bottleneck on purpose and walking the diagnostic path the way Brendan Gregg taught the industry to walk it.

## Learning objectives

By the end of this week, you will be able to:

- **State and apply the USE method** — for every resource (CPU, memory, disk, network), measure Utilization (% of time busy), Saturation (queue depth or wait), and Errors (count of failures). Know which Linux tool reports each, and have the **USE method checklist** memorized for the four resources. Reference: Brendan Gregg, "The USE Method" (brendangregg.com).
- **Read `htop` and `top` fluently.** Know what each column means: `PID`, `USER`, `PRI`, `NI`, `VIRT`, `RES`, `SHR`, `S` (process state), `%CPU`, `%MEM`, `TIME+`. Know that `%CPU` in `top` is **per-core** by default (so 200 % is a process using two cores) and how to toggle "Irix mode" off. Know what the load-average numbers actually count (running + uninterruptible-waiting tasks, not "CPU percentage").
- **Read `iostat -x 1` fluently.** `r/s`, `w/s`, `rkB/s`, `wkB/s`, `await`, `r_await`, `w_await`, `aqu-sz` (the queue depth), `%util`. Know that on multi-queue NVMe `%util` saturates well below "real" saturation and you must read `aqu-sz` as the truer signal. Reference: `man 1 iostat`.
- **Read `vmstat 1` fluently.** The `r` (runnable) and `b` (blocked) columns are the heart of it. Know that high `r` plus high `%us` means CPU-bound; high `b` plus high `%wa` means IO-bound; high `si` / `so` means you are swapping and the conversation is over until you fix memory.
- **Read `free -h` and the `/proc/meminfo` file** — distinguish `used`, `free`, `available`, `buff/cache`. Know why "Linux ate my RAM" is a misunderstanding: `buff/cache` is reclaimable on demand; `available` is the number that matters. Reference: `man 5 proc` (`/proc/meminfo` section).
- **Use `ss -tulpn` and `ss -tan`** to enumerate listening sockets and established connections. Know that `ss` is the modern replacement for `netstat`. Read `Recv-Q` and `Send-Q` (these are bytes queued kernel-side, not in flight) and explain what a non-zero `Recv-Q` on a `LISTEN` socket means (accept-queue overflow).
- **Use `strace -c` and `strace -p`** to profile syscalls of a process. `-c` summarises by syscall and shows the time per call; `-p PID` attaches to a running process. Know that strace slows the target by a factor of 2-20× (it intercepts every syscall via `ptrace`); it is a diagnostic tool, not a profiler in production.
- **Use `ltrace`** to trace library calls when the syscall view is too low-level. Same `ptrace` mechanism, same caveats.
- **Read `/proc` directly.** `/proc/<pid>/status` (the process state, RSS, VmPeak, threads), `/proc/<pid>/io` (bytes read/written), `/proc/<pid>/fd/` (open files), `/proc/<pid>/maps` (memory map), `/proc/loadavg`, `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/sockstat`. Reference: kernel `Documentation/filesystems/proc.rst`.
- **Apply the four-question diagnostic.** Given a slow system, ask in order: (1) Is one CPU pegged or are they all? (2) Is memory exhausted or is the system swapping? (3) Is a disk saturated? (4) Is a network link saturated or is a connection backlogged? Each question has a tool and a number. The answer to question N before N+1 keeps you from guessing.
- **Recognise the observer effect.** `strace`, `ltrace`, `perf trace`, and to a lesser extent `top -d 0.1` all perturb the system they observe. Choose the lightest tool that answers the question. Read `/proc` files directly when you can.

## Prerequisites

- **Weeks 1-6 of C14** completed. You can navigate the filesystem, write scripts, read systemd units, and SSH into a hardened server. Week 6 is not strictly required, but the mini-project assumes a Linux box you have root on.
- A working Ubuntu 24.04 LTS or Fedora 41 environment. The exercises run on any modern Linux; the man-page line numbers and `iostat` column names match Ubuntu 24.04 by default. macOS users: most tools either do not exist (`htop` is available, `strace` is not; macOS has `dtruss`) or have different output. Run the exercises in a Linux VM (UTM, Lima, Multipass) or on your Week 6 VPS.
- Packages: `htop`, `sysstat` (provides `iostat`, `mpstat`, `sar`, `pidstat`), `procps` (provides `top`, `ps`, `vmstat`, `free`; usually preinstalled), `strace`, `ltrace`, `iproute2` (provides `ss`; preinstalled), `stress-ng` (for inducing load), `bpfcc-tools` (optional; we touch BPF observability in the resources). On Ubuntu: `sudo apt install htop sysstat strace ltrace stress-ng bpfcc-tools`. On Fedora: `sudo dnf install htop sysstat strace ltrace stress-ng bcc-tools`.
- Python 3.10 or newer for the challenge (the mini-`htop`). No external dependencies — we parse `/proc` with the standard library.
- Patience to **measure before you change**. Almost every performance bug looks like the one you saw last month. It almost never is.

## Topics covered

- **The USE method** (Brendan Gregg, 2012) — Utilization, Saturation, Errors, applied to every resource. The checklist for CPU, memory, disk, network. The "first sixty seconds of incident response" runbook: `uptime`, `dmesg | tail`, `vmstat 1`, `mpstat -P ALL 1`, `pidstat 1`, `iostat -xz 1`, `free -m`, `sar -n DEV 1`, `sar -n TCP,ETCP 1`, `top` — in that order. We learn it because it is the discipline that distinguishes diagnosis from guessing.
- **The four pillars: CPU, memory, disk, network.** For each, the question that finds saturation, the tool that answers it, the number that means trouble, and the next tool that finds the cause. CPU: `top` / `mpstat` / `pidstat`. Memory: `free` / `vmstat` / `/proc/meminfo`. Disk: `iostat` / `pidstat -d` / `iotop`. Network: `ss` / `sar -n DEV` / `nstat` / `tcpdump`.
- **`htop` and `top`** — the process table. Columns, sorts, filters, the `F` keys (`F4` filter, `F5` tree, `F6` sort, `F9` kill). The `state` column (`R` running, `S` interruptible sleep, `D` uninterruptible sleep — usually disk wait, `T` stopped, `Z` zombie). The `Irix mode` versus `Solaris mode` `%CPU` distinction. The load-average reading.
- **`ps`** — the process snapshot. The two flag dialects (`BSD`: `ps aux`; `Unix`: `ps -ef`). The columns you actually want: `ps -eo pid,ppid,user,stat,pcpu,pmem,rss,vsz,comm,args`. Why `ps` is a snapshot and `top` is a stream.
- **`iostat -x 1`** — the disk-extended view. Every column means something specific. `r/s` and `w/s` are operations per second. `rkB/s` and `wkB/s` are bandwidth. `await` is mean time per IO in milliseconds. `aqu-sz` (queue length) is the saturation signal. `%util` is busy-time; on rotating disks it tops out near 100 % at saturation; on multi-queue SSDs it tops out well before "real" saturation and `aqu-sz` is the truer signal.
- **`vmstat 1`** — the system-wide cycle counter. `r` runnable processes (queue depth on the CPU run-queue). `b` blocked processes (waiting on IO). `swpd`, `free`, `buff`, `cache`. `si`, `so` (swap-in, swap-out — any non-zero is bad news). `bi`, `bo` (block IO in/out). `in`, `cs` (interrupts and context switches per second). `us`, `sy`, `id`, `wa`, `st` (CPU breakdown).
- **`free -h`** and `/proc/meminfo` — the memory picture. The `available` column is the answer to "how much could I actually use right now without paging out." `buff/cache` is reclaimable. Swap usage and swappiness. The OOM killer and the dmesg trail it leaves.
- **`sar`** — the systat data collector. `sar -u` CPU, `sar -r` memory, `sar -b` IO, `sar -n DEV` network, `sar -q` run-queue. The genius of `sar` is that it **records continuously** (via the `sysstat` cron) so you can look at *yesterday at 14:00* when the user reports an outage that ended before you logged in. Reference: `man 1 sar`.
- **`ss`** — the modern `netstat` replacement. `ss -tulpn` (TCP+UDP listening, with processes and ports). `ss -tan` (TCP all, numeric). `ss -tan state established` (only established TCP). `ss -i` (extended TCP info: RTT, CWND, retransmits — the in-kernel TCP CC view). `Recv-Q` and `Send-Q`.
- **`strace`** — syscall tracing via `ptrace`. `strace -c COMMAND` summarises syscall counts and time. `strace -p PID` attaches to a running process. `strace -f` follows forks. `strace -e trace=openat,read,write` filters. The overhead caveat: 2-20× slowdown is normal; do not run on production without thinking. Reference: `man 1 strace`.
- **`ltrace`** — library-call tracing, same mechanism, one level up. When `strace` shows you only `read(3, ...)` repeatedly and you want to know what `libxml` was doing, `ltrace` is the next step.
- **`/proc`** — the kernel-as-filesystem. Every running process has a directory `/proc/<pid>/` with `status`, `io`, `fd/`, `maps`, `stack`, `cmdline`, `environ`, `cgroup`. System-wide files: `/proc/loadavg`, `/proc/stat`, `/proc/meminfo`, `/proc/diskstats`, `/proc/net/sockstat`, `/proc/cpuinfo`, `/proc/uptime`. The whole filesystem is "the kernel willing to answer a question if you `cat` the right file." Reference: kernel `Documentation/filesystems/proc.rst`.
- **`pidstat`** — per-process variants of the system tools. `pidstat 1` (CPU). `pidstat -d 1` (disk). `pidstat -r 1` (memory). `pidstat -w 1` (context switches). Underused, exactly the right tool when "the system is fine but one process is sick."
- **`mpstat -P ALL 1`** — per-CPU breakdown. The difference between "one CPU at 100 %" (single-threaded bottleneck) and "all CPUs at 100 %" (parallel work or runaway). Reference: `man 1 mpstat`.
- **`stress-ng`** — the load-induction tool. `stress-ng --cpu 4`, `stress-ng --io 4`, `stress-ng --vm 2 --vm-bytes 1G`. Use it to create the symptom you are about to diagnose so the diagnosis is a closed loop. Free, open-source, in every distro's repos.
- **A glance at BPF observability.** `bcc-tools` ships dozens of small tools (`execsnoop`, `opensnoop`, `tcplife`, `biolatency`) that use kernel BPF programs to observe without the `ptrace` overhead. We do not teach BPF programming this week (it is a course in itself; see *Linux Observability with BPF*), but we run two of the tools so you know they exist.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | USE method; "where does the time go." Lecture 1.       |    3h    |    1h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Tuesday   | CPU and process tools (`htop`, `top`, `ps`). Lecture 2.|    2h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Wednesday | IO, memory, syscalls (`iostat`, `vmstat`, `strace`). Lecture 3. |    2h    |    2h     |     0.5h   |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Thursday  | Exercise 3 (iostat during dd); design mini-proj.       |    0h    |    2h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Mini-`htop` challenge; polish homework.                |    0h    |    0.5h   |     2h     |    0.5h   |   2h     |     1h       |    0h      |     6h      |
| Saturday  | Mini-project — synthetic-load perf report.             |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                                      |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0.5h    |     1h      |
| **Total** |                                                        | **7h**   | **7.5h**  | **3.5h**   | **3h**    | **6h**   | **7h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Brendan Gregg's USE method, Linux Performance docs, man pages, BPF references |
| [lecture-notes/01-the-use-method-and-where-to-start.md](./lecture-notes/01-the-use-method-and-where-to-start.md) | The USE method; the four pillars; the first-sixty-seconds runbook |
| [lecture-notes/02-cpu-and-process-tools.md](./lecture-notes/02-cpu-and-process-tools.md) | `htop`, `top`, `ps`, `pidstat`, `mpstat`; columns and process states |
| [lecture-notes/03-io-memory-syscalls.md](./lecture-notes/03-io-memory-syscalls.md) | `iostat`, `vmstat`, `free`, `strace`, `ltrace`, `/proc/<pid>/io`; the IO-and-syscall view |
| [exercises/exercise-01-diagnose-a-busy-cpu.md](./exercises/exercise-01-diagnose-a-busy-cpu.md) | Run `yes > /dev/null &`, find it with `htop`/`top`/`pidstat`, kill it |
| [exercises/exercise-02-trace-a-syscall.md](./exercises/exercise-02-trace-a-syscall.md) | `strace -c ls`; read the summary; identify the dominant syscall |
| [exercises/exercise-03-iostat-during-dd.md](./exercises/exercise-03-iostat-during-dd.md) | Run `iostat -x 1` while `dd` writes; identify the saturated column |
| [exercises/SOLUTIONS.md](./exercises/SOLUTIONS.md) | Step-by-step solutions to all three exercises |
| [challenges/challenge-01-write-your-own-mini-htop.py](./challenges/challenge-01-write-your-own-mini-htop.py) | A type-hinted Python parser of `/proc` that mimics a slice of `htop` |
| [challenges/challenge-02-detect-noisy-neighbor.md](./challenges/challenge-02-detect-noisy-neighbor.md) | Find the noisy process on a busy host with `pidstat`, `iotop`, and `/proc/<pid>/io` |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | Diagnose a synthetic load; write a full performance-debug report with numbers |

## A note on which tools and which kernel

Linux observability is a moving target. New tools land each kernel release; `perf` and BPF replace older mechanisms; column names in `iostat` change between `sysstat` versions. This week's content is written against:

- **Kernel 6.8** (Ubuntu 24.04 LTS default) and **kernel 6.11** (Fedora 41 default). Older kernels (5.x) are fine; the `/proc` files we read have existed unchanged since 2.6.
- **`sysstat` 12.6** (Ubuntu 24.04) and **`sysstat` 12.7** (Fedora 41). The `iostat -x` columns include `r_await` and `w_await` (split since `sysstat` 12.0, 2019); older versions show only `await`. If your `iostat` is older the lecture's column names will not all match.
- **`procps-ng` 4.0** (both distros). `top`, `ps`, `free`, `vmstat`, `pmap`, `pgrep`, `pkill`.
- **`util-linux` 2.39** (Ubuntu) / 2.40 (Fedora). `lsof`, `lscpu`, `lsblk`.
- **`htop` 3.3.0** (both distros).
- **`strace` 6.5** (both distros).

```bash
# Versions
uname -r                  # 6.8.0-x or 6.11.x
iostat -V | head -1       # sysstat 12.6.x
top -v | head -1          # procps-ng 4.0.x
htop --version | head -1  # htop 3.3.0
strace --version | head -1 # strace -- version 6.5
```

If you are on macOS, install a Linux VM. Most tools have macOS equivalents (`top` exists, `htop` exists via Homebrew, but `strace` is replaced by `dtruss` and `iostat` reports different columns), and the exercises assume Linux output. WSL2 with Ubuntu 24.04 works for almost everything, with the caveat that WSL's kernel is a special build and a few `/proc` files behave differently (notably `/proc/diskstats`, which reports the virtual disk).

## Stretch goals

- Read **Brendan Gregg, *Systems Performance: Enterprise and the Cloud* (2nd ed., 2020)** — the canonical textbook. Chapters 2 ("Methodologies") and 6 ("CPUs") are required reading for any operator who wants to graduate from "use the tool" to "design the measurement." See <https://www.brendangregg.com/systems-performance-2nd-edition-book.html>.
- Read the kernel's `Documentation/filesystems/proc.rst` end to end. It is the only authoritative reference for what every `/proc` file contains. Slow reading; worth it. Source: <https://www.kernel.org/doc/html/latest/filesystems/proc.html>.
- Run `bcc-tools/execsnoop` and `bcc-tools/opensnoop` for ten minutes on your laptop. Both use BPF to observe `execve()` and `openat()` system-wide without the `strace` overhead. The visibility is uncomfortable on first encounter.
- Read **Brendan Gregg, "The USE Method"** (<https://www.brendangregg.com/usemethod.html>) and its companion **"Linux Performance Analysis in 60,000 Milliseconds"** (the Netflix engineering blog post). Both short; both define the diagnostic vocabulary of the discipline.
- Run `perf stat -d ls` (you may need `sudo apt install linux-tools-generic`). The output is the per-syscall view from the kernel's hardware-counter machinery — orthogonal to `strace`, no `ptrace` involved, ~0 % overhead.

## Bash Yellow caution

This week contains commands that can:

- **Lock up a workstation.** `stress-ng --vm 2 --vm-bytes 100% --timeout 60s` allocates real memory and forces swapping. On a laptop with 16 GB and slow swap, this can render the GUI unresponsive for minutes. Run inside a VM with a swap cap, or use `--vm-bytes 50%` until you know your machine.
- **Wear an SSD.** Repeated `dd if=/dev/zero of=/tmp/big bs=1M count=10000` writes 10 GB per run. SSDs have finite write endurance; do this once or twice for the exercise and then `rm` the file. Do **not** loop it.
- **Mislead you about production.** `strace -p PID` on a production process slows it 2-20×. The slowdown is itself the bug for any latency-sensitive service. Use `strace` on test instances; use `perf` or BPF tools on production.
- **Confuse you with kernel caching.** A `read` of a 1 GB file the second time is mostly served from the page cache and is 100× faster than the first read. If you measure performance without accounting for caching, you will diagnose the wrong thing. `echo 3 > /proc/sys/vm/drop_caches` (as root) clears the cache between runs; the production answer is to design the test so caching is part of what you are measuring.
- **Hide the cause behind the symptom.** A "slow disk" is sometimes a "slow filesystem because the directory has 500,000 files." A "slow process" is sometimes a "noisy neighbor on the same host." `htop`'s row for *one* process never tells the whole story — pair it with `pidstat -d`, `ss`, and `iostat`. The diagnostic discipline is **measure the whole system before you accuse one part of it**.

Every lecture and exercise that runs destructive or load-inducing code says so on the line above, uses a scratch directory or VM, and shows the cleanup command. The line is: **measure before you change, and prefer the lightest tool that answers the question**.

## Up next

[Week 8 — Disks, filesystems, and the page cache](../week-08/) — Now that you can see *what* is slow, we look closer at *why* disks are slow. Filesystems, block devices, LVM, the page cache, `fsync` semantics, IO schedulers. The bridge from "the disk is busy" (which Week 7 lets you say) to "the disk is busy because ext4 is journalling every write and you can batch them" (which Week 8 lets you fix).

---

*If you find errors, please open an issue or PR.*
