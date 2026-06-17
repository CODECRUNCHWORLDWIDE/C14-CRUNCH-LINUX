#!/usr/bin/env python3
"""
Challenge 01 — Write your own mini-htop.

Reads /proc directly and prints a snapshot of the most CPU-active processes,
similar to the top of htop's display. Type-hinted, standard library only,
runs on any Linux 4.0+.

Usage:
    python3 challenge-01-write-your-own-mini-htop.py            # one shot
    python3 challenge-01-write-your-own-mini-htop.py --interval 1  # stream every 1s
    python3 challenge-01-write-your-own-mini-htop.py --rows 20  # 20 processes

Read /proc/<pid>/stat for CPU time and command name; /proc/<pid>/status for
state and memory; /proc/stat for system-wide CPU time. The CPU % calculation
is the difference of two snapshots divided by elapsed wall-clock time, the
same approach top and htop use.

Reference:
  - kernel Documentation/filesystems/proc.rst
  - man 5 proc
  - htop source (Process.c, LinuxProcessList.c) at https://github.com/htop-dev/htop

This is a teaching toy. It is intentionally about 250 lines so you can read
the whole thing. Do not use it as a replacement for htop.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


# /proc/<pid>/stat is one whitespace-separated line. The fields are documented
# in `man 5 proc` (section "/proc/[pid]/stat") and in
# Documentation/filesystems/proc.rst. The fields are indexed from 1 in the man
# page; we use 0-indexed positions in the Python list below.
#
# A complication: field 2 is `(comm)`, the executable name, which may itself
# contain spaces or parentheses (consider `/bin/echo "hello world"`). The
# canonical parsing approach is to find the FIRST `(` and the LAST `)`,
# treating everything between them as field 2.
#
# We only read a handful of fields:
#   field  0   pid
#   field  1   comm           (in parens; may contain spaces)
#   field  2   state          (single letter)
#   field 13   utime          (user CPU time in clock ticks)
#   field 14   stime          (kernel CPU time in clock ticks)
#   field 15   cutime         (children user CPU time)
#   field 16   cstime         (children kernel CPU time)
#   field 21   starttime      (process start time, clock ticks since boot)
#   field 22   vsize          (virtual memory size in bytes)
#   field 23   rss            (resident set size in pages)

# Clock ticks per second (USER_HZ). On every Linux distribution we have seen
# this is 100. Read from sysconf to be safe.
CLOCK_TICKS: int = os.sysconf("SC_CLK_TCK")
# Page size in bytes; used to convert RSS pages to bytes.
PAGE_SIZE: int = os.sysconf("SC_PAGESIZE")


@dataclass
class ProcSnapshot:
    """One snapshot of /proc/<pid>/stat plus the bits of /proc/<pid>/status
    we need.

    All fields populated by `read_proc_snapshot` below.
    """

    pid: int
    comm: str
    state: str
    utime_ticks: int
    stime_ticks: int
    starttime_ticks: int
    vsize_bytes: int
    rss_bytes: int
    user: str = "?"
    threads: int = 1

    @property
    def total_ticks(self) -> int:
        """User + system CPU ticks consumed by this process so far."""
        return self.utime_ticks + self.stime_ticks


@dataclass
class CpuSnapshot:
    """One snapshot of /proc/stat's first line.

    The fields, per `man 5 proc`:
        user, nice, system, idle, iowait, irq, softirq, steal, guest, guest_nice

    We sum them all into total_ticks to compute per-process %CPU; the
    individual breakdowns are used for the summary bars at the top.
    """

    user: int
    nice: int
    system: int
    idle: int
    iowait: int
    irq: int
    softirq: int
    steal: int
    guest: int
    guest_nice: int

    @property
    def total_ticks(self) -> int:
        """All CPU time, sums to (cpu_count * uptime * CLOCK_TICKS)."""
        return (
            self.user
            + self.nice
            + self.system
            + self.idle
            + self.iowait
            + self.irq
            + self.softirq
            + self.steal
            + self.guest
            + self.guest_nice
        )

    @property
    def idle_ticks(self) -> int:
        """Idle + iowait. Both are "the CPU was not executing user/kernel
        code." Treating them the same simplifies the busy-fraction math."""
        return self.idle + self.iowait


@dataclass
class MemoryInfo:
    """A subset of /proc/meminfo.

    Values are in KiB to match the file. We render in MiB / GiB.
    """

    total_kb: int = 0
    free_kb: int = 0
    available_kb: int = 0
    buffers_kb: int = 0
    cached_kb: int = 0
    swap_total_kb: int = 0
    swap_free_kb: int = 0


def read_proc_stat() -> CpuSnapshot:
    """Read the aggregate CPU line from /proc/stat.

    The first line of /proc/stat is the aggregate; subsequent lines `cpu0`,
    `cpu1`, ... are per-CPU. We only need the aggregate.
    """
    with open("/proc/stat", "r") as f:
        first_line = f.readline().split()
    # first_line[0] is "cpu"; the rest are the ten counters.
    ticks = [int(x) for x in first_line[1:11]]
    while len(ticks) < 10:
        # Older kernels omit some trailing fields. Pad with zeros.
        ticks.append(0)
    return CpuSnapshot(*ticks)


def read_meminfo() -> MemoryInfo:
    """Read /proc/meminfo and return the fields we care about.

    `man 5 proc` documents every field. We grab a handful and ignore the rest.
    """
    info = MemoryInfo()
    field_map = {
        "MemTotal:": "total_kb",
        "MemFree:": "free_kb",
        "MemAvailable:": "available_kb",
        "Buffers:": "buffers_kb",
        "Cached:": "cached_kb",
        "SwapTotal:": "swap_total_kb",
        "SwapFree:": "swap_free_kb",
    }
    with open("/proc/meminfo", "r") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] in field_map:
                setattr(info, field_map[parts[0]], int(parts[1]))
    return info


def read_proc_snapshot(pid: int) -> ProcSnapshot | None:
    """Read /proc/<pid>/stat and /proc/<pid>/status, return a ProcSnapshot.

    Returns None if the process has exited between us listing it and us
    reading it (which happens; PIDs come and go).
    """
    stat_path = Path("/proc") / str(pid) / "stat"
    status_path = Path("/proc") / str(pid) / "status"
    try:
        raw = stat_path.read_text()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None

    # The `comm` field is in parens and may contain spaces or parens. Parse
    # using the first `(` and the last `)`. Everything between is `comm`.
    open_paren = raw.find("(")
    close_paren = raw.rfind(")")
    if open_paren < 0 or close_paren < 0:
        return None
    comm = raw[open_paren + 1 : close_paren]
    after = raw[close_paren + 2 :].split()
    # `after` now starts with field 3 (state). Indexes shift by 2 from man
    # page numbering (man page is 1-indexed and counted comm separately).
    try:
        state = after[0]
        utime = int(after[11])
        stime = int(after[12])
        starttime = int(after[19])
        vsize = int(after[20])
        rss_pages = int(after[21])
    except (IndexError, ValueError):
        return None

    snap = ProcSnapshot(
        pid=pid,
        comm=comm,
        state=state,
        utime_ticks=utime,
        stime_ticks=stime,
        starttime_ticks=starttime,
        vsize_bytes=vsize,
        rss_bytes=rss_pages * PAGE_SIZE,
    )

    # Read status for user and thread count (status is friendlier to parse
    # than stat for these specific fields).
    try:
        status_text = status_path.read_text()
        for line in status_text.splitlines():
            if line.startswith("Uid:"):
                # `Uid:` line: real, effective, saved, fs.
                uid_real = int(line.split()[1])
                snap.user = uid_to_username(uid_real)
            elif line.startswith("Threads:"):
                snap.threads = int(line.split()[1])
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        pass

    return snap


_uid_cache: dict[int, str] = {}


def uid_to_username(uid: int) -> str:
    """Map a numeric UID to a username via /etc/passwd.

    pwd.getpwuid() is the friendly approach; we hand-roll for portability
    (no `pwd` on Windows; we still want the file to load).
    """
    if uid in _uid_cache:
        return _uid_cache[uid]
    try:
        with open("/etc/passwd", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) >= 3 and int(parts[2]) == uid:
                    _uid_cache[uid] = parts[0]
                    return parts[0]
    except (FileNotFoundError, PermissionError):
        pass
    _uid_cache[uid] = str(uid)
    return str(uid)


def list_pids() -> list[int]:
    """Every directory in /proc whose name is a number is a PID."""
    pids: list[int] = []
    for entry in os.listdir("/proc"):
        if entry.isdigit():
            pids.append(int(entry))
    return pids


def capture_snapshot() -> tuple[CpuSnapshot, dict[int, ProcSnapshot]]:
    """Take one snapshot of system CPU and every accessible process."""
    cpu = read_proc_stat()
    procs: dict[int, ProcSnapshot] = {}
    for pid in list_pids():
        snap = read_proc_snapshot(pid)
        if snap is not None:
            procs[pid] = snap
    return cpu, procs


def compute_cpu_percents(
    before: dict[int, ProcSnapshot],
    after: dict[int, ProcSnapshot],
    elapsed_ticks: int,
    cpu_count: int,
) -> dict[int, float]:
    """For each PID present in both snapshots, compute the CPU percentage.

    The math: percent CPU is (delta_process_ticks / elapsed_total_ticks) * 100
    * cpu_count, where elapsed_total_ticks = elapsed_ticks (per-CPU). We
    multiply by cpu_count because htop's default is "per-core" — a process
    using two cores fully shows 200%.

    Returns a dict pid -> percent. New processes (in `after` but not in
    `before`) get 0%; dead processes (in `before` but not `after`) are
    omitted.
    """
    percents: dict[int, float] = {}
    if elapsed_ticks <= 0:
        return percents
    for pid, after_snap in after.items():
        before_snap = before.get(pid)
        if before_snap is None:
            percents[pid] = 0.0
            continue
        delta_ticks = after_snap.total_ticks - before_snap.total_ticks
        # *100 to convert to percent, *cpu_count for the per-core convention.
        percents[pid] = (delta_ticks / elapsed_ticks) * 100.0 * cpu_count
    return percents


def format_kb(kb: int) -> str:
    """Format a KiB value as MiB or GiB, whichever is more readable."""
    mb = kb / 1024.0
    if mb < 1024:
        return f"{mb:.0f}M"
    return f"{mb / 1024.0:.1f}G"


def format_bytes(b: int) -> str:
    """Format bytes as KiB / MiB / GiB."""
    if b < 1024 * 1024:
        return f"{b / 1024:.0f}K"
    if b < 1024 * 1024 * 1024:
        return f"{b / 1024 / 1024:.1f}M"
    return f"{b / 1024 / 1024 / 1024:.2f}G"


def render(
    cpu_before: CpuSnapshot,
    cpu_after: CpuSnapshot,
    percents: dict[int, float],
    procs: dict[int, ProcSnapshot],
    meminfo: MemoryInfo,
    rows: int,
) -> None:
    """Render the summary block, the column header, and the top N processes."""
    cpu_total = cpu_after.total_ticks - cpu_before.total_ticks
    cpu_idle = cpu_after.idle_ticks - cpu_before.idle_ticks
    cpu_busy_frac = 1.0 - (cpu_idle / cpu_total) if cpu_total > 0 else 0.0
    cpu_user = cpu_after.user + cpu_after.nice - cpu_before.user - cpu_before.nice
    cpu_sys = cpu_after.system - cpu_before.system
    user_frac = (cpu_user / cpu_total) if cpu_total > 0 else 0.0
    sys_frac = (cpu_sys / cpu_total) if cpu_total > 0 else 0.0

    used_kb = meminfo.total_kb - meminfo.available_kb
    used_frac = used_kb / meminfo.total_kb if meminfo.total_kb > 0 else 0.0

    print()
    print(
        f"CPU: {cpu_busy_frac * 100:5.1f}%  "
        f"(user {user_frac * 100:5.1f}%  sys {sys_frac * 100:5.1f}%)  "
        f"| Memory: {format_kb(used_kb)}/{format_kb(meminfo.total_kb)} "
        f"used ({used_frac * 100:.0f}%)  "
        f"available {format_kb(meminfo.available_kb)}"
    )
    print(
        f"Swap: {format_kb(meminfo.swap_total_kb - meminfo.swap_free_kb)}/"
        f"{format_kb(meminfo.swap_total_kb)} used"
    )
    print()

    print(
        f"{'PID':>7} {'USER':<10} {'S':>2} {'THR':>4} "
        f"{'RSS':>7} {'VSZ':>7} {'%CPU':>6} COMMAND"
    )

    # Sort processes by %CPU descending, break ties by PID for determinism.
    sorted_pids = sorted(
        procs.keys(),
        key=lambda p: (-(percents.get(p, 0.0)), p),
    )

    for pid in sorted_pids[:rows]:
        snap = procs[pid]
        pct = percents.get(pid, 0.0)
        # Truncate command to keep the line within 100 chars on 80-col tty.
        comm = snap.comm[:30]
        print(
            f"{pid:>7} {snap.user[:10]:<10} {snap.state:>2} "
            f"{snap.threads:>4} {format_bytes(snap.rss_bytes):>7} "
            f"{format_bytes(snap.vsize_bytes):>7} {pct:>6.1f} {comm}"
        )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "A minimal htop-like process viewer that reads /proc directly. "
            "Pure standard library; runs on any Linux with /proc mounted."
        )
    )
    p.add_argument(
        "--interval",
        type=float,
        default=0.0,
        help=(
            "Refresh interval in seconds (default: 0 = one-shot). "
            "If non-zero, the program loops until Ctrl-C."
        ),
    )
    p.add_argument(
        "--rows",
        type=int,
        default=15,
        help="Number of process rows to display (default: 15).",
    )
    return p.parse_args()


def cpu_count() -> int:
    """Number of online CPUs. Used to scale per-process %CPU."""
    n = os.cpu_count()
    return n if n is not None else 1


def main() -> int:
    if not Path("/proc").exists():
        print(
            "Error: /proc is not mounted. This program reads /proc; it is "
            "Linux-only.",
            file=sys.stderr,
        )
        return 1

    args = parse_args()
    cpus = cpu_count()

    # First snapshot. CPU% requires a second snapshot some time later, so
    # we sleep and then take it.
    cpu_before, procs_before = capture_snapshot()
    if args.interval > 0:
        # Streaming mode.
        try:
            while True:
                t0 = time.monotonic()
                time.sleep(args.interval)
                cpu_after, procs_after = capture_snapshot()
                elapsed = time.monotonic() - t0
                elapsed_ticks = int(elapsed * CLOCK_TICKS)
                percents = compute_cpu_percents(
                    procs_before, procs_after, elapsed_ticks, cpus
                )
                # ANSI clear screen + home cursor. Cheap, works on any tty.
                sys.stdout.write("\033[H\033[J")
                meminfo = read_meminfo()
                render(
                    cpu_before, cpu_after, percents, procs_after, meminfo, args.rows
                )
                cpu_before, procs_before = cpu_after, procs_after
        except KeyboardInterrupt:
            print("\nExiting.")
            return 0
    else:
        # One-shot mode: take a second snapshot ~0.5 s later for CPU%
        # accuracy, then render once.
        t0 = time.monotonic()
        time.sleep(0.5)
        cpu_after, procs_after = capture_snapshot()
        elapsed = time.monotonic() - t0
        elapsed_ticks = int(elapsed * CLOCK_TICKS)
        percents = compute_cpu_percents(
            procs_before, procs_after, elapsed_ticks, cpus
        )
        meminfo = read_meminfo()
        render(cpu_before, cpu_after, percents, procs_after, meminfo, args.rows)
        return 0


if __name__ == "__main__":
    sys.exit(main())
