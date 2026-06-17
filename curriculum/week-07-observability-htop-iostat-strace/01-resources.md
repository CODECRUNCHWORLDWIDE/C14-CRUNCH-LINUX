# Week 7 — Resources

Free, public, no signup unless noted. Brendan Gregg's site and the Linux kernel `proc` documentation are the two references you will bookmark this week and revisit for years afterwards.

## Required reading

- **Brendan Gregg — "The USE Method"** — the foundational essay. Two screens long; defines the vocabulary the rest of the discipline uses. Read it before lecture 1:
  <https://www.brendangregg.com/usemethod.html>
- **Brendan Gregg — "Linux Performance Analysis in 60,000 Milliseconds"** — the famous Netflix engineering post. The first-sixty-seconds checklist (`uptime`, `dmesg | tail`, `vmstat 1`, `mpstat -P ALL 1`, `pidstat 1`, `iostat -xz 1`, `free -m`, `sar -n DEV 1`, `sar -n TCP,ETCP 1`, `top`). Print and tape to your monitor:
  <https://www.brendangregg.com/Articles/Netflix_Linux_Perf_Analysis_60s.pdf>
- **Brendan Gregg — "Linux Performance"** — the master reference page. Tools, books, talks, blog posts, all sorted by topic. The single most useful page on the public internet for performance work:
  <https://www.brendangregg.com/linuxperf.html>
- **Linux kernel — `Documentation/filesystems/proc.rst`** — the authoritative spec of every file in `/proc`. The only place where, for example, the meaning of the eleven fields in `/proc/diskstats` is documented. Slow reading; the reference for the lifetime of your career:
  <https://www.kernel.org/doc/html/latest/filesystems/proc.html>
- **`man 1 htop`** — the htop manual. Read end to end. Every column, every key, every interactive command:
  <https://man.archlinux.org/man/htop.1>
- **`man 1 top`** — the top manual. Long, dense, exhaustive. The "INTERACTIVE COMMANDS" and "FIELDS / Columns" sections are where most of the answers are:
  <https://man7.org/linux/man-pages/man1/top.1.html>
- **`man 1 iostat`** — the iostat manual. The "FIELDS" section defines every column. The "EXAMPLES" section at the bottom is high-value:
  <https://man7.org/linux/man-pages/man1/iostat.1.html>
- **`man 8 vmstat`** — the vmstat manual. Field meanings; the `procs`, `memory`, `swap`, `io`, `system`, `cpu` columns:
  <https://man7.org/linux/man-pages/man8/vmstat.8.html>
- **`man 1 strace`** — the strace manual. `-c`, `-p`, `-f`, `-e trace=`, `-o`, `-T`, `-r`. The "EXAMPLES" section at the bottom is where the practice lives:
  <https://man7.org/linux/man-pages/man1/strace.1.html>
- **`man 5 proc`** — the procfs manual page (separate from the kernel docs; more terse, more example-driven). The single most useful man page in the system:
  <https://man7.org/linux/man-pages/man5/proc.5.html>
- **`man 8 ss`** — the ss manual. `-tulpn`, `-tan`, `-i`, state filters, the `Recv-Q` and `Send-Q` semantics:
  <https://man7.org/linux/man-pages/man8/ss.8.html>
- **`man 1 pidstat`** — per-process system stats. The under-used companion to `iostat`/`vmstat`:
  <https://man7.org/linux/man-pages/man1/pidstat.1.html>
- **`man 1 sar`** — the systat data collector. Continuous recording of CPU, memory, IO, network. Reads `/var/log/sysstat/*` to answer "what was the system doing yesterday at 14:00":
  <https://man7.org/linux/man-pages/man1/sar.1.html>

## Books

- **Brendan Gregg — *Systems Performance: Enterprise and the Cloud* (Pearson, 2nd ed., 2020)** — the textbook of the discipline. 800 pages. Chapter 2 (Methodologies — the USE method's home in book form), Chapter 6 (CPUs), Chapter 7 (Memory), Chapter 9 (Disks), Chapter 10 (Network) are this week's reference text. Buy or borrow; the textbook lasts a decade. Author's page (with sample chapters): <https://www.brendangregg.com/systems-performance-2nd-edition-book.html>
- **Brendan Gregg, David Calavera, Lorenzo Fontana — *Linux Observability with BPF* (O'Reilly, 2019)** — short (~150 pages), free PDF chapters available from O'Reilly's preview. The introduction to BPF as the new observability substrate (orthogonal to and lighter than `strace`). We do not teach BPF programming this week, but you should know it exists. Free chapter samples: <https://www.oreilly.com/library/view/linux-observability-with/9781492050193/>
- **W. Richard Stevens — *Advanced Programming in the UNIX Environment* (3rd ed., Addison-Wesley, 2013)** — the syscall textbook. When `strace` shows a syscall and you ask "what is `setsockopt` actually doing?", APUE is the answer. The book that taught every Linux engineer how the syscall ABI works.
- **Daniel P. Bovet, Marco Cesati — *Understanding the Linux Kernel* (O'Reilly, 3rd ed., 2005)** — old, still the clearest single explanation of how `/proc` is implemented and why the kernel exposes what it does. The schedulers chapter is essential reading for understanding what `load average` *means*.
- **Robert Love — *Linux Kernel Development* (Addison-Wesley, 3rd ed., 2010)** — companion to Bovet/Cesati; shorter, more readable, less complete. The chapter on the scheduler (CFS) is where "what is process state `D` and why does it not yield" becomes legible.
- **Tanel Poder's "TPT-collector" — Linux Performance Cookbook** — Tanel is the database performance gray-beard who applies the Brendan Gregg toolset to Oracle workloads. The blog posts and `psnapper` tool (which samples `/proc/<pid>/task/*/status` to build a flame-graph-shaped picture of what processes are blocked on) are an under-appreciated complement to `strace`: <https://tanelpoder.com/>

## Cheat sheets

- **Brendan Gregg — "Linux Performance Tools" — the one-page tool map**, every tool annotated to the kernel subsystem it observes. Print A3, frame:
  <https://www.brendangregg.com/Perf/linux_observability_tools.png>
- **Brendan Gregg — "Linux Performance Tools: BPF" — the BPF-era version of the same map** (when you are ready to graduate from `strace` to `bpftrace`):
  <https://www.brendangregg.com/Perf/bcc_tracing_tools.png>
- **`procps-ng` cheat sheet** — every flag of `top`, `ps`, `free`, `vmstat`, `pmap`, `pgrep`, `pkill` on one page:
  <https://gitlab.com/procps-ng/procps>
- **Arch Wiki — "Improving performance"** — pragmatic, distro-agnostic notes on the same toolset, with attention to which knobs actually move the needle:
  <https://wiki.archlinux.org/title/Improving_performance>
- **`strace` cheat sheet — Julia Evans** — Julia Evans's two-page zine on `strace`. Cheap, illustrated, the friendliest possible introduction:
  <https://jvns.ca/blog/2014/04/20/debug-your-programs-like-they-are-closed-source/>
  Her *Linux Debugging Tools You'll Love* zine is also worth the $12 if you want the whole thing on paper.
- **`/proc` cheat sheet** — Red Hat's distilled summary of `Documentation/filesystems/proc.rst`. Less complete than the kernel source, more readable:
  <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/system_administrators_guide/ch-the_proc_file_system>

## Tools and websites

- **`htop`** — the interactive process viewer. F-keys, mouse, customizable columns, tree view. Reads `/proc` exclusively; no kernel module. Free, GPLv2: <https://htop.dev/>
- **`top`** — the original. Slightly less pretty, present everywhere. Reads `/proc`. Part of `procps-ng`.
- **`btop`** — the modern reimagining of `htop` (Rust/C++, themes, mouse, includes disk/network panels). Optional; useful as the "show me everything on one screen" tool. <https://github.com/aristocratos/btop>
- **`iotop`** — per-process IO view. Requires root or `CAP_NET_ADMIN`. Excellent companion to `iostat`. Most distros: `sudo apt install iotop` / `sudo dnf install iotop`.
- **`strace`** — syscall tracing via `ptrace`. The slow, complete view. `man 1 strace`. <https://strace.io/>
- **`ltrace`** — library-call tracing. Same `ptrace` mechanism, one level up. <https://gitlab.com/cespedes/ltrace>
- **`perf`** — the kernel's profiling framework. `perf top` (sampling profiler), `perf stat` (hardware counter view), `perf record` / `perf report` (flame-graph input). `linux-tools-generic` on Ubuntu; `perf` on Fedora. Free.
- **`bcc-tools`** — the BPF Compiler Collection. Dozens of small tools: `execsnoop`, `opensnoop`, `tcplife`, `biolatency`, `cachestat`, `cachetop`. Each one prints "things happening" in a category. `sudo apt install bpfcc-tools`. <https://github.com/iovisor/bcc>
- **`bpftrace`** — the higher-level BPF DSL. One-liners over the kernel's tracepoints. Out of scope for Week 7; queued for a later week. <https://github.com/iovisor/bpftrace>
- **`sysstat` suite** — `iostat`, `mpstat`, `pidstat`, `sar`, `tapestat`. The continuous-collection bedrock. `sudo apt install sysstat`; enable with `sudo systemctl enable --now sysstat`. <https://sysstat.github.io/>
- **`procps`** — `top`, `ps`, `free`, `vmstat`, `pmap`, `pgrep`, `pkill`. Preinstalled.
- **`iproute2`** — `ss`, `ip`, `tc`. The modern replacement for `net-tools` (`netstat`, `ifconfig`, `route`). Preinstalled.
- **`stress-ng`** — load induction. `--cpu N`, `--io N`, `--vm N --vm-bytes K`, `--hdd N --hdd-bytes K`, `--sock N`. Free, open-source. <https://github.com/ColinIanKing/stress-ng>
- **`flamegraph.pl`** — Brendan Gregg's flame-graph generator. Takes `perf record` output, renders an interactive SVG of where CPU time goes. Free, MIT. <https://github.com/brendangregg/FlameGraph>
- **`psnapper` — Tanel Poder** — samples `/proc/<pid>/task/*/status` to show what *every* thread on the system is blocked on. Excellent for "where is the contention." <https://github.com/tanelpoder/psnapper>

## Videos (free)

- **Brendan Gregg — "Linux Performance Tools" (LinuxCon, 2014; updated talks since)** — the foundational talk, in the tool-map style. Forty minutes:
  <https://www.brendangregg.com/Slides/LinuxConNA2014_LinuxPerfTools.pdf>
- **Brendan Gregg — "Performance Methodologies" (USENIX LISA 2017)** — the methodology talk. The USE method, the RED method (rate, errors, duration; a complement for distributed-systems work), the workload-characterisation method. The intellectual centre of the discipline:
  <https://www.usenix.org/conference/lisa17/conference-program/presentation/gregg>
- **Brendan Gregg — "Performance Analysis Superpowers with Linux BPF" (USENIX LISA 2018)** — what BPF replaces and what it adds. Strictly orthogonal to `strace`. Forty minutes:
  <https://www.usenix.org/conference/lisa18/presentation/gregg>
- **Julia Evans — "What does the kernel do?" (RubyConf 2017)** — a friendly tour of `strace`, `tcpdump`, and `/proc` from the syscall side. Twenty-five minutes; non-intimidating:
  <https://www.youtube.com/watch?v=Bk0V4z6CCu0>
- **Tanel Poder — "Linux Performance Tuning for Database Workloads"** — a database performance gray-beard applying the same `pidstat`/`/proc` toolkit to Oracle. The methodology is general; you can take it back to web servers. Multiple talks on the public web; search "Tanel Poder linux performance".

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install -y htop sysstat strace ltrace iotop stress-ng \
                    bpfcc-tools linux-tools-generic procps iproute2

# Fedora
sudo dnf install -y htop sysstat strace ltrace iotop stress-ng \
                    bcc-tools perf procps-ng iproute

# Optional but recommended on both
sudo systemctl enable --now sysstat   # turns on the sar continuous collector
```

- `htop` — the interactive process viewer.
- `sysstat` — gives you `iostat`, `mpstat`, `pidstat`, `sar`. The `sar` collector is off by default; the `systemctl enable --now sysstat` line turns it on. Once on, `sar` quietly logs CPU, memory, IO, and network every 10 minutes to `/var/log/sysstat/`; you can query the day before. Worth every byte of disk.
- `strace`, `ltrace` — the syscall- and library-call tracers.
- `iotop` — per-process IO viewer.
- `stress-ng` — load-induction tool. Used in every exercise.
- `bpfcc-tools` / `bcc-tools` — the BPF Compiler Collection. `execsnoop`, `opensnoop`, `tcplife`, `biolatency`. Used in the resources walk-through.
- `linux-tools-generic` / `perf` — the `perf` profiling framework. Optional this week; required next time we touch flame-graphs.
- `procps`, `iproute2` — preinstalled, listed for completeness.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| Kernel version | 6.8.x | 6.11.x |
| `htop` version | 3.3.0 | 3.3.0 |
| `sysstat` version | 12.6.0 | 12.7.x |
| `strace` version | 6.5 | 6.10 |
| `procps-ng` version | 4.0.x | 4.0.x |
| `iostat -x` columns | `r_await`, `w_await` since 12.0 | same |
| `sar` collector default | off; enable with `systemctl enable --now sysstat` | off; same procedure |
| BPF tools package | `bpfcc-tools` (note `bpfcc-` prefix) | `bcc-tools` |
| `perf` package | `linux-tools-generic` (and `linux-tools-$(uname -r)`) | `perf` |
| `/var/log/sysstat/` files | `sa01`, `sa02`, ... per day of month | same |
| `iotop` needs root | yes | yes |

The two divergences that bite are the package names (`bpfcc-tools` versus `bcc-tools`) and the `perf` install (Ubuntu splits it per kernel version; Fedora ships one). Confirm with `which perf` after install.

## Free books and write-ups

- **Brendan Gregg — *Systems Performance* sample chapters (Chapter 1, "Introduction")** — the first chapter is freely available from the publisher's site. Read it as the entry point: <https://www.brendangregg.com/systems-performance-2nd-edition-book.html>
- **The Netflix Performance Engineering blog** — case studies in real-world performance work, at scale, on Linux. The "Linux Performance Analysis in 60,000 Milliseconds" article above is the most-cited; the rest of the archive is dense:
  <https://netflixtechblog.com/tagged/performance>
- **Julia Evans — *Linux Debugging Tools You'll Love* (free PDF of zine #2; print zine available)** — a 30-page illustrated zine on `strace`, `ltrace`, `lsof`, `perf`, `tcpdump`. The single best gateway to the toolset for somebody who does not yet have the methodology:
  <https://jvns.ca/blog/2014/04/20/debug-your-programs-like-they-are-closed-source/>
- **Linux Performance Wiki (`perf` wiki on the kernel.org site)** — the project documentation for the `perf` tool. Dense; useful as the authoritative reference when StackOverflow disagrees with itself:
  <https://perf.wiki.kernel.org/index.php/Main_Page>
- **`sysstat` documentation** — Sebastien Godard's docs on `iostat`, `mpstat`, `pidstat`, `sar`. The field definitions are subtler than the man pages suggest:
  <https://sysstat.github.io/documentation.html>
- **Greg Kroah-Hartman — "Linux Kernel in a Nutshell"** — free PDF. Older (2007) but the chapter on `/proc` is still the clearest "what does each file contain" reference outside the kernel source:
  <https://www.kroah.com/lkn/>

## Tools and constructs you will see this week

A quick reference. Every tool links to its man page; we will not duplicate the man pages here.

### Process and CPU tools

| Tool | Source of truth | What it shows |
|------|-----------------|---------------|
| `top` | `/proc/<pid>/stat`, `/proc/stat` | Stream of process table sorted by CPU. Built-in. |
| `htop` | Same | Interactive top with colour, mouse, tree, filter. |
| `ps` | Same | One-shot snapshot of the process table. |
| `pidstat 1` | Same | Per-process CPU, memory, IO, context-switch rates. |
| `mpstat -P ALL 1` | `/proc/stat` | Per-CPU breakdown. |
| `uptime` | `/proc/loadavg`, `/proc/uptime` | 1/5/15-minute load average and how long the host has been up. |

### Memory tools

| Tool | Source of truth | What it shows |
|------|-----------------|---------------|
| `free -h` | `/proc/meminfo` | Total, used, free, buff/cache, available, swap. |
| `vmstat 1` | `/proc/stat`, `/proc/meminfo` | System cycle: run-queue, blocked, memory, swap, IO, system, CPU. |
| `cat /proc/meminfo` | The source | Every memory counter the kernel exposes (40+ fields). |
| `pmap PID` | `/proc/<pid>/maps` | Per-process memory map: each mmap region, size, permissions, backing. |

### Disk and IO tools

| Tool | Source of truth | What it shows |
|------|-----------------|---------------|
| `iostat -x 1` | `/proc/diskstats` | Per-device IO rates, bandwidth, latency, queue depth, %util. |
| `iotop` | `/proc/<pid>/io` | Per-process IO rates (root). |
| `pidstat -d 1` | `/proc/<pid>/io` | Per-process IO rates (non-root). |
| `cat /proc/<pid>/io` | The source | rchar, wchar, syscr, syscw, read_bytes, write_bytes per process. |
| `lsof -p PID` | `/proc/<pid>/fd/` | All open file descriptors for a process. |

### Network tools

| Tool | Source of truth | What it shows |
|------|-----------------|---------------|
| `ss -tulpn` | `/proc/net/tcp`, `/proc/net/udp`, kernel | Listening TCP+UDP sockets with processes and ports. |
| `ss -tan` | Same | All TCP sockets, numeric. |
| `ss -i` | Same plus `tcp_info` socket option | Per-socket TCP details: RTT, CWND, retransmits. |
| `sar -n DEV 1` | `/proc/net/dev` | Per-interface bandwidth, packets, errors. |
| `nstat` | `/proc/net/netstat` | Cumulative counters from the SNMP MIB. |

### Syscall and library tracing

| Tool | Mechanism | What it shows |
|------|-----------|---------------|
| `strace -c CMD` | `ptrace` | Summary of syscall counts and total time per syscall. |
| `strace -p PID` | `ptrace` | Live stream of syscalls for a running process. |
| `strace -f CMD` | `ptrace` | Same, following forks. |
| `ltrace CMD` | `ptrace` | Library-call trace (one level above syscalls). |
| `perf trace CMD` | `tracepoints` (no `ptrace`) | Lower-overhead syscall trace. |

### `/proc` files we read most this week

| File | Contents |
|------|----------|
| `/proc/loadavg` | 1/5/15-minute load averages, running/total tasks, last PID. |
| `/proc/uptime` | Seconds since boot; seconds spent idle. |
| `/proc/stat` | System-wide CPU, interrupts, context switches, boot time. |
| `/proc/meminfo` | All memory counters. |
| `/proc/diskstats` | Per-block-device IO counters. |
| `/proc/cpuinfo` | Per-CPU model, flags, MHz. |
| `/proc/<pid>/stat` | One-line summary of the process (47 fields, see `man 5 proc`). |
| `/proc/<pid>/status` | Human-readable version of `stat` plus more (state, RSS, VmPeak, threads). |
| `/proc/<pid>/io` | Bytes read/written, syscalls read/wrote. |
| `/proc/<pid>/fd/` | Symbolic links to every open FD. |
| `/proc/<pid>/maps` | Memory map; what is mmap'd where. |
| `/proc/<pid>/cmdline` | Argv joined by NUL. |
| `/proc/<pid>/cgroup` | Which cgroup hierarchy the process is in. |

## Glossary

| Term | Definition |
|------|------------|
| **USE method** | Brendan Gregg's diagnostic framework: for every resource, measure Utilization, Saturation, Errors. |
| **Utilization** | Fraction of time the resource is busy. CPU %util, disk %util, network %util. |
| **Saturation** | Degree to which the resource has work queued up beyond what it can handle now. Run-queue length, IO queue depth, accept-queue depth. |
| **Errors** | Count of failures: dropped packets, IO errors, segmentation faults, page-fault errors. |
| **Process state** | `R` running, `S` interruptible sleep, `D` uninterruptible sleep (usually disk wait), `T` stopped, `Z` zombie, `I` idle (kernel threads only). |
| **Load average** | 1/5/15-min exponentially-weighted moving average of (running + uninterruptible-sleeping) tasks. Not a percentage. |
| **`/proc`** | The procfs. A virtual filesystem the kernel mounts at `/proc/` exposing process and system state as text files. |
| **`ptrace`** | The kernel facility (`ptrace(2)`) that lets one process inspect and control another. The mechanism behind `strace`, `ltrace`, `gdb`. |
| **Syscall** | A function call from user space into the kernel. `open`, `read`, `write`, `mmap`, `execve`. The unit `strace` traces. |
| **Page cache** | The kernel's in-memory cache of file contents. The reason a file's second read is much faster than its first. |
| **Swap** | Disk space used as overflow memory when RAM is exhausted. Swapping (`si`/`so` in `vmstat`) means the system is paging out anonymous memory to disk; bad news for latency. |
| **OOM killer** | The kernel's last-resort response to memory exhaustion; picks a process by score and kills it. Leaves a record in `dmesg`. |
| **BPF** | Berkeley Packet Filter (now used far beyond packets). A safe in-kernel virtual machine; the substrate for `bpftrace`, `bcc-tools`, modern observability. |
| **Flame graph** | Brendan Gregg's stack-sample visualisation. CPU time as a horizontal-bar tree. |
| **`%iowait`** | Fraction of CPU idle time during which at least one task was waiting on IO. Misleading; high `%iowait` does not mean "the disk is the bottleneck" — it means CPUs were idle and at least one task was IO-blocked. |
| **Accept queue** | The kernel-side queue of completed-handshake TCP connections waiting for the application to `accept()`. Overflowing means the application is too slow to accept; you see this as non-zero `Recv-Q` on a `LISTEN` socket in `ss -tln`. |
| **Observer effect** | The principle that observing a system changes its behaviour. `strace` slows the target 2-20×; `top -d 0.1` consumes its own CPU. Pick the lightest tool. |

---

*Broken link? Open an issue.*
