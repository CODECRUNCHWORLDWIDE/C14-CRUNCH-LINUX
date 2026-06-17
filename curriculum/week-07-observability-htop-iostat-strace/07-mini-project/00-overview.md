# Mini-Project — Diagnose a synthetic load; write a full performance report

> Take a deliberately-engineered busy workload running on a Linux host you control. Apply the USE method end-to-end. Identify which of the four pillars (CPU, memory, disk, network) is the bottleneck. Prove it with numbers. Recommend a fix. Write a single, defensible report that another engineer could replicate.

**Estimated time:** 6-7 hours, spread Thursday-Saturday.

This mini-project is the deliverable that proves Week 7 took. You are not being graded on the speed of your discovery, on whether you knew the answer in advance, or on the prettiness of your graphs. You are being graded on **the evidence chain**: did the report identify the bottleneck by measurement and not by guesswork; do the numbers in the report match the captured output; could another engineer read the report, follow the steps, and confirm the conclusion.

The point of the mini-project is to drill **the USE method at full length** on a non-trivial load, end-to-end, on a real Linux host. You will measure, hypothesise, confirm, recommend.

---

## Deliverable

A directory in your portfolio repo `c14-week-07/mini-project/` containing:

1. `README.md` — your full report. Structure below.
2. `setup.sh` — the script you ran to induce the synthetic load. Reusable; commenters can replay.
3. `evidence/` — captured outputs:
   - `evidence/01-uptime.txt`
   - `evidence/02-dmesg.txt`
   - `evidence/03-vmstat.txt`
   - `evidence/04-mpstat.txt`
   - `evidence/05-pidstat.txt`
   - `evidence/06-iostat.txt`
   - `evidence/07-free.txt`
   - `evidence/08-sar-dev.txt` (or `08-ss.txt` if `sar -n DEV` is empty)
   - `evidence/09-ss.txt`
   - `evidence/10-top.txt`
   - `evidence/11-strace-c.txt` (if relevant — see "phase 3" below)
   - `evidence/12-proc-pid-io.txt`
   - `evidence/13-proc-pid-status.txt`
   - Any other captures you cite in the report.
4. `findings-table.md` — the USE matrix populated with numbers from your measurements (a 4×3 table; one cell per resource × question).
5. `recommendation.md` — one page on the recommended fix. Not "buy more RAM" — a specific, technical fix tied to evidence in the report.

---

## The synthetic load — pick one

Choose one of three scenarios (or invent your own and document it). Each is designed to look like a real-world bug shape.

### Scenario A — "The slow file processor"

A Python script that reads a large file line-by-line, does a small string operation on each line, and writes the result. The bottleneck is intentionally subtle: a 4 KB read buffer, plus a `sleep(0.001)` per line that simulates a slow downstream consumer. The user reports "the script takes hours."

```bash
# setup.sh excerpt:
mkdir -p ~/c14-w07-mp
python3 -c '
import random, string
with open("/tmp/bigtext.txt", "w") as f:
    for _ in range(2_000_000):
        f.write("".join(random.choices(string.ascii_lowercase, k=80)) + "\n")
'
# Then run the "slow processor":
python3 ~/c14-w07-mp/slow_processor.py /tmp/bigtext.txt /tmp/out.txt &
```

Where `slow_processor.py` is:

```python
import sys
import time

infile, outfile = sys.argv[1], sys.argv[2]
with open(infile, "r", buffering=4096) as fin, open(outfile, "w", buffering=4096) as fout:
    for line in fin:
        fout.write(line.upper())
        time.sleep(0.001)
```

The bottleneck is the `time.sleep(0.001)` (in a 2M-line file: 2000 seconds = 33 minutes of pure sleep). The disk is fine; the CPU is fine; the process is just **off-CPU sleeping** most of the time. Your investigation should reveal that `pidstat`'s `%wait` is high or that `strace -c` shows `clock_nanosleep` dominating.

### Scenario B — "The memory grower"

A Python script that allocates 100 MB per second indefinitely, with a small CPU-bound section. The user reports "the system gets slow then locks up."

```python
# memgrow.py
import time
data = []
chunk = b"x" * (100 * 1024 * 1024)
while True:
    data.append(chunk)
    # Tiny CPU work to make it visible on top:
    _ = sum(i for i in range(1000))
    time.sleep(1)
```

Bottleneck: anonymous memory. RSS grows by 100 MB/s. Eventually the kernel pages out, then OOM-kills. Your investigation should reveal memory pressure (low `MemAvailable`, non-zero `si`/`so` in `vmstat` at the late stages, possibly OOM messages in `dmesg`).

### Scenario C — "The IO storm"

A shell loop that writes many small files in a tight loop, each with `fsync`:

```bash
mkdir -p /tmp/iostorm
for i in $(seq 1 10000); do
    echo "row $i $(date +%s%N)" > /tmp/iostorm/f$i.txt
    sync /tmp/iostorm/f$i.txt
done
```

Bottleneck: filesystem metadata operations plus `fsync` latency. The disk shows surprisingly low `wkB/s` but high `w/s` (small IOs); `iostat` `await` is high; CPU is mostly idle but `%wa` is high; `pidstat -d` shows the loop is the culprit.

### Or — invent your own

Document it clearly in `setup.sh`. The constraints:

- Runs unattended for 60-300 seconds.
- Produces a measurable bottleneck in **exactly one** of the four resources.
- Cleans up after itself.

---

## The report structure

`README.md` (the report) must include the following sections, in order:

### 1. Executive summary (one paragraph)

Five sentences. The host, the load, the measured bottleneck, the recommended fix, the expected improvement.

Example: "Host is an Ubuntu 24.04 VPS, 1 vCPU / 1 GB RAM. Load is the 'slow file processor' (Scenario A). The bottleneck is off-CPU sleep, not disk or CPU: `strace -c` shows `clock_nanosleep` accounting for 99.7 % of traced time, and `pidstat -p PID 1 60` shows mean `%CPU` of 2.1 % and mean `%wait` of 0.0 %. Recommended fix: remove the `time.sleep(0.001)` per-line throttle (added defensively but no longer necessary). Expected improvement: 33-minute job becomes 12-second job."

### 2. The host

Provider, plan, region. `uname -r`, `lscpu` summary, `free -h` summary, `df -h` summary, kernel/sysstat/strace versions.

### 3. The load

What you ran. The `setup.sh` script. The expected behaviour.

### 4. The diagnostic walk

The sixty-second checklist, applied in order. For each of the ten commands:

- **The command**, copy-pasted.
- **A short excerpt** of the relevant output (3-10 lines, not the whole thing — but the full output goes in `evidence/`).
- **One sentence** describing what the block shows.

After the ten commands, a 2-3 sentence interim conclusion: which of the four pillars looked most suspicious, and what your next step is.

### 5. The deep dive

Whichever pillar looked suspicious, you now drill in:

- **CPU bottleneck?** `pidstat 1`, `mpstat -P ALL 1`, possibly `strace -c -p PID` (briefly!) or `perf top -p PID`.
- **Memory bottleneck?** `cat /proc/<pid>/status`, watch RSS grow over time, `cat /proc/meminfo`, check OOM in `dmesg`.
- **Disk bottleneck?** `iostat -xz 1`, `pidstat -d 1`, `cat /proc/<pid>/io`, possibly `strace -e trace=%file -p PID`.
- **Network bottleneck?** `ss -tan state established | wc -l`, `ss -i`, `sar -n DEV 1`, `nstat`, possibly `tcpdump -i any -n -c 100`.

Capture each command's output. Quote the **specific number** that incriminated the resource.

### 6. The USE matrix

A 4-row × 3-column table. Each cell is either a number (with units) or "n/a" (clear that it was not measured on this run and why). Like:

| Resource | Utilization | Saturation | Errors |
|----------|-------------|------------|--------|
| CPU | `%us 2.1, %sy 0.5, %id 97.4` | `r 0-1, load avg 0.05` | none |
| Memory | `MemAvailable 870 Mi (87%)` | `si/so 0/0` | none |
| Disk | `%util 0.1, wkB/s 0` | `aqu-sz 0.0, await 0.0 ms` | none |
| Network | `rxkB/s 0.1, txkB/s 0.1` | `Recv-Q 0, retrans 0` | none |

The point of presenting the matrix is to make the **non-anomalous** cells visible too. "I checked memory, network, disk; only CPU was anomalous." The matrix is the proof.

### 7. Hypothesis and confirmation

State your hypothesis as a sentence. Design a confirming test (a change to the workload that should make the symptom go away). Run it. Capture the result. Quote the number.

Example: "Hypothesis: the bottleneck is the `time.sleep(0.001)` per line. Test: remove the sleep, re-run. Result: wall-clock time falls from 33 minutes to 12 seconds. Confirmed."

### 8. Recommendation

`recommendation.md` (one page). The proposed fix, tied to the evidence. Not "buy more RAM" — a specific technical change.

### 9. Reflection

Two or three sentences. What would you do differently next time? Was there a measurement you wish you had taken earlier? Was there a tool you reached for first that turned out to be the wrong one?

---

## Grading rubric

| Criterion | Weight |
|-----------|-------:|
| The synthetic load runs and produces a real bottleneck. | 10 % |
| The sixty-second checklist was executed in order and captured. | 20 % |
| The bottleneck is identified by **number**, not by hand-wave. | 25 % |
| The USE matrix is populated for all four resources (including the unaffected ones). | 15 % |
| The hypothesis is confirmed by a designed test. | 15 % |
| The recommendation is specific, technical, and tied to the evidence. | 10 % |
| Writing is clear, evidence chain is followable. | 5 % |

A score below 70 % is "redo with another scenario." A score above 90 % is ready to be the kind of artifact you would link to on a resume.

---

## Pitfalls

- **Capturing without context.** A wall of `pidstat` output without a sentence explaining what to look at is not evidence. Quote the specific number you read.
- **Skipping the unaffected cells.** "I only need to check CPU because the load is CPU-bound" is the trap that catches every junior. The matrix is exhaustive on purpose; fill all twelve cells.
- **The page cache lying.** If your scenario involves disk IO, account for whether the page cache is hot or cold. `echo 3 > /proc/sys/vm/drop_caches` (as root) before runs, or use `conv=fdatasync` / `oflag=direct` to bypass.
- **Tracing in production.** This is not production. `strace -p PID` is fine on your VM. But note in the report that you would not run it on production unless overhead were acceptable, and what you would use instead (`perf trace`, `bpftrace`, `bcc-tools/<tool>`).
- **Forgetting to clean up.** `setup.sh` should leave the machine in the state it started in. `rm` the temp files; `pkill` the stressors; check `pgrep -f stress-ng` returns empty.

---

## Tips

- **Use `tmux` or `screen`.** You will run many commands, and losing your scrollback at the wrong moment is annoying.
- **Use `script` to capture everything.** `script ~/c14-w07-mp/session.log` at the start, `exit` at the end. Every command and output is captured.
- **Use timestamps.** `date >> evidence/XX.txt && command >> evidence/XX.txt` makes the chronology clear.
- **Read your evidence before writing the report.** If a number you cite in the report does not match a number in the evidence, the report is wrong. Fix it before submitting.
- **Be honest about what you did not measure.** If `sar -n TCP` showed no relevant data because there was no TCP traffic, say so in the report ("network is not in play; ss confirms no relevant traffic"). Honesty about non-findings is part of the discipline.

---

## Optional extensions

- Run the same scenario twice with different mitigations. Compare the USE matrices side-by-side. This is what a real before/after performance fix looks like.
- Capture a flame graph (`perf record -g -p PID ...`, then `perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg`) for the CPU-heavy scenario. Embed in the report.
- Use `bcc-tools/biolatency` for the IO scenario. Capture the latency histogram. Compare to the `iostat` `await` reading.
- Write the report twice: once for an engineering audience (technical, with numbers) and once for a manager (one screen, with one number and one recommendation). The skill is the translation.

---

*If you've done this exercise once, you can do it. The 100th time you do it is the same shape; you just go faster. Up next: [Week 8 — Disks, filesystems, page cache](../../week-08/).*
