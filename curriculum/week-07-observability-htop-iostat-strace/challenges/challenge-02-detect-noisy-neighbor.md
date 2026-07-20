# Challenge 2 — Detect a noisy neighbour

**Time:** 60-90 minutes.
**Goal:** On a host with multiple workloads running, identify which process is the "noisy neighbour" — the one consuming an outsized fraction of CPU, memory, IO, or context switches — without prior knowledge of the workload layout. Use the per-process tools we taught in Week 7 and write a short report explaining the evidence chain.
**Prerequisites:** Exercises 1-3 complete; Lectures 1-3 read.

---

## Why this challenge

"Noisy neighbour" is the polite name for "another tenant or another workload on this host is hurting yours." It is the most common shape of performance complaint in any multi-tenant environment: containers on Kubernetes, processes in a cgroup hierarchy, VMs on a hypervisor. The tools in Week 7 are exactly the ones needed to find the noise.

The challenge induces the situation on purpose: we run several different stressors and you find them, one at a time, using only the per-process tools. The goal is to **build a workflow** you can apply later when the cause is genuinely unknown.

---

## Setup

You need a Linux machine you can pile load onto. Your laptop in a VM is fine; a $5 VPS is fine; a Raspberry Pi is fine.

Install `stress-ng` if you do not have it:

```bash
sudo apt install stress-ng    # Ubuntu/Debian
sudo dnf install stress-ng    # Fedora
```

Open four terminals (or `tmux` panes).

---

## Part 1 — The setup script (intentionally noisy)

Save this as `~/c14-w07/challenge-02/noisy-setup.sh` and make it executable:

```bash
#!/usr/bin/env bash
set -euo pipefail

WORKDIR="$(mktemp -d /tmp/c14-w07-noisy-XXXXXX)"
echo "Working in $WORKDIR (will be cleaned up at the end)"

cleanup() {
  echo "Cleaning up..."
  pkill -f "stress-ng" || true
  pkill -f "noisy-py" || true
  rm -rf "$WORKDIR"
  echo "Done."
}
trap cleanup EXIT INT TERM

# Noisy neighbour A: a CPU spinner running for 3 minutes.
stress-ng --cpu 2 --timeout 180s &
SPIN_PID=$!
echo "[A] stress-ng CPU spinner, PID $SPIN_PID"

# Noisy neighbour B: an IO write loop for 3 minutes.
stress-ng --hdd 1 --hdd-bytes 256M --temp-path "$WORKDIR" --timeout 180s &
IO_PID=$!
echo "[B] stress-ng IO writer, PID $IO_PID"

# Noisy neighbour C: a memory-allocating Python loop, named "noisy-py".
python3 -c '
import time
import sys
data = []
chunk = b"x" * (1024 * 1024)
sys.stdout.write("[C] python memory grower starting\n")
sys.stdout.flush()
for _ in range(300):
    data.append(chunk * 10)
    time.sleep(1)
sys.stdout.write("[C] python memory grower done\n")
' > /tmp/noisy-py.log 2>&1 &
PY_PID=$!
echo "[C] python memory grower, PID $PY_PID"

# Noisy neighbour D: a context-switch storm for 3 minutes.
stress-ng --switch 4 --timeout 180s &
SW_PID=$!
echo "[D] stress-ng context-switch storm, PID $SW_PID"

echo
echo "All four neighbours running. Sleeping 180s; press Ctrl-C to stop early."
echo "PIDs: A=$SPIN_PID  B=$IO_PID  C=$PY_PID  D=$SW_PID"
echo

sleep 180
```

Run it in one terminal:

```bash
chmod +x ~/c14-w07/challenge-02/noisy-setup.sh
~/c14-w07/challenge-02/noisy-setup.sh
```

You now have four "neighbours" running for 3 minutes:

- **A** — a CPU spinner (stress-ng using two CPU workers).
- **B** — a disk-writing loop.
- **C** — a Python process growing memory by 10 MB/s for 5 minutes.
- **D** — a context-switch storm.

You know what they are (you set them up). The challenge is to find them with **only the tools** — pretend you SSH'd into a stranger's machine and have to figure out what is going on.

---

## Part 2 — The investigation

In a second terminal, work through the diagnostic ladder. Take notes; you will need them for the report.

### Step 1 — `uptime` and the sixty-second checklist

```bash
uptime
```

Note the load average. With four parallel workloads, the 1-minute load should already be 4-8 depending on how long they have been running.

```bash
dmesg | tail
```

Anything alarming? (Usually not, unless one of the neighbours triggered OOM. Confirm no surprises.)

```bash
vmstat 1 5
```

Read carefully. The first sample is averages-since-boot; ignore it. The next four are the recent picture. Note:

- `r` (runnable) — should be high (the CPU spinner alone is 2; with the others it can be 4-8).
- `b` (blocked) — non-zero if the IO writer is hurting.
- `si`, `so` — should be 0 unless memory is exhausted.
- `bi`, `bo` — block IO rates; `bo` should be high from the IO writer.
- `cs` — context switches; should be elevated by the context-switch stressor.
- `us`, `sy`, `id`, `wa` — CPU breakdown.

### Step 2 — Per-CPU breakdown

```bash
mpstat -P ALL 1 3
```

You should see at least some CPUs near 100 % `%usr` (from the CPU spinner) and some with elevated `%sys` (from the context-switch storm).

### Step 3 — Per-process CPU

```bash
pidstat 1 5
```

Sort/grep the output for `%CPU > 50`:

```bash
pidstat 1 5 | awk 'NR > 3 && $8 > 50 { print }'
```

The CPU spinner (`stress-ng-cpu`) should be at or near 100 % (per worker), so two workers at 100 % each.

### Step 4 — Per-process IO

```bash
pidstat -d 1 5
```

The IO writer should show `kB_wr/s` in the tens to hundreds of MB. Note the PID and confirm with:

```bash
cat /proc/<PID>/io
```

You should see `write_bytes` growing.

### Step 5 — Per-process memory

```bash
pidstat -r 1 5
```

Note any process whose `RSS` (resident set size, in KiB) is large or growing. The Python memory grower should show RSS climbing by ~10 MiB every second.

```bash
# Periodic snapshot of one PID
while true; do
    grep '^VmRSS' /proc/<py-PID>/status
    sleep 2
done
```

You watch `VmRSS` grow live.

### Step 6 — Per-process context switches

```bash
pidstat -w 1 5
```

The context-switch storm process should show `cswch/s` (voluntary) and/or `nvcswch/s` (nonvoluntary) in the thousands or tens of thousands. Normal processes have `cswch/s` in the tens.

### Step 7 — Disk view

```bash
iostat -xz 1 5
```

The IO neighbour shows up as elevated `w/s`, `wkB/s`, and `aqu-sz` on whatever device `/tmp` is on. Cross-check the PID from step 4.

### Step 8 — The synthesis

You should now be able to fill out:

| Neighbour | PID | Symptom | Tool that found it | Number |
|-----------|-----|---------|---------------------|--------|
| A — CPU spinner | _____ | `%CPU` near 200 (two workers) | `pidstat 1` | _____ |
| B — IO writer | _____ | `kB_wr/s` in MB | `pidstat -d 1` + `iostat` | _____ |
| C — memory grower | _____ | RSS growing 10 MiB/s | `pidstat -r 1` + `/proc/<pid>/status` | _____ |
| D — context-switch storm | _____ | `cswch/s` > 10000 | `pidstat -w 1` | _____ |

Fill in the actual PIDs and numbers from your investigation.

---

## Part 3 — Write the report

Save as `~/c14-w07/challenge-02/report.md`. Length: 400-600 words. Structure:

```markdown
# Noisy-neighbour investigation report

## Summary

One sentence describing the host (laptop / VPS / VM) and the symptom you
investigated.

## Method

A short paragraph naming the tools you used and the order. The order is the
sixty-second checklist from Lecture 1 §3.

## Findings

The table from Part 2 step 8, populated with real numbers.

## Evidence (per neighbour)

For each of the four, a short paragraph:
  1. The PID and command line you identified.
  2. The exact `pidstat` (or other) line that incriminated it, copy-pasted.
  3. The /proc evidence you cross-checked (a `cat /proc/<pid>/...` output).
  4. One sentence on what the workload was doing in mechanical terms (the
     CPU spinner is a tight CPU loop; the IO writer is sequential writes to
     a temp file; etc.).

## Reflection

Three or four sentences. Which of the four was the easiest to spot? Which
required cross-checking? If the host were a production system and one of
these had been an unrelated tenant, what would your next step be? (Cgroup
limits? Notify another team? Migrate the workload?)
```

The report is the deliverable. The investigation is the practice.

---

## Part 4 — Acceptance criteria

Save in `~/c14-w07/challenge-02/`:

- [ ] `noisy-setup.sh` — the setup script, exactly as above.
- [ ] `findings-table.md` — the populated table from Part 2 step 8.
- [ ] `evidence/` directory with one file per neighbour (`A-cpu.txt`, `B-io.txt`, `C-mem.txt`, `D-switch.txt`), each containing the relevant `pidstat`/`iostat`/`cat /proc` output.
- [ ] `report.md` — the written report.

---

## Pitfalls

- **Aggregate versus per-CPU.** On a multi-core host, `top`'s aggregate `%CPU` may not look alarming because two pegged cores out of eight is only 25 %. Always look at the per-CPU view (`mpstat -P ALL 1` or `htop` with bars).
- **The memory grower may be hard to spot in steady state.** Its growth rate (10 MB/s) is what makes it visible. If you take only one snapshot, RSS is "high" but not obviously climbing. Snapshot twice, ten seconds apart, and compute the delta.
- **`/tmp` may be `tmpfs` on your distro.** Some distros mount `/tmp` as `tmpfs` (in RAM). The IO writer then has no disk effect — it just consumes memory. Edit `noisy-setup.sh` to use `/var/tmp` instead if your `/tmp` is `tmpfs` (check with `df /tmp` — if it shows `tmpfs`, switch). `/var/tmp` is on the actual filesystem.
- **`stress-ng --switch` requires multiple CPUs.** On a single-core VM the context-switch storm is degenerate.

---

## Optional extensions

- Re-run the investigation while using only `top` and `cat /proc/...` — no `pidstat`. Confirm you can still find all four. The point is that `pidstat` is convenient but not essential; the data is in `/proc`.
- Use `bcc-tools/execsnoop` for thirty seconds and capture every `exec()`. Can you see the neighbours' lifecycle? Discuss in the report.
- Wrap `mini-htop.py` (from Challenge 1) and run it on the noisy host. Does it find all four neighbours? What is missing? Propose three improvements you could make.

---

*Solutions: rough chains, in [`SOLUTIONS.md`](../exercises/SOLUTIONS.md) (no spoilers for the report itself — the report is the deliverable).*
