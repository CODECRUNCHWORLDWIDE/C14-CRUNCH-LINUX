# Week 7 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-07/homework/`.

These are practice problems between the exercises (which drilled the tools) and the mini-project (which asks you to compose freely). Every measurement-and-report problem must include the raw output captured (not retyped) plus your interpretation.

---

## Problem 1 — The sixty-second checklist, recorded (45 min)

Open one terminal on your target machine. Run, in order:

```bash
uptime
dmesg | tail
vmstat 1 5
mpstat -P ALL 1 3
pidstat 1 3
iostat -xz 1 3
free -m
sar -n DEV 1 3
sar -n TCP,ETCP 1 3
top -n 1 -b -o %CPU | head -15
```

Capture each command's output (`script` is the friend here, or `tee`-ing each command).

Then write `homework/01-sixty-seconds.md` containing:

- The complete captured output, in order, each block labelled with the command that produced it.
- After each block, **one sentence** stating what that block shows about the current state. (Format: "Block 3 — `vmstat 1 5` shows the system is mostly idle: `r 0-1`, `b 0`, `id 95-99`, `wa 0-1`. No CPU or IO pressure.")
- A two-sentence summary at the end: "If this had been an incident, the bottleneck would be ___ because ___."

If your system is idle, this is fine — the exercise is to **run the checklist**, not to find a problem. The skill is the muscle memory.

**Acceptance:** `homework/01-sixty-seconds.md` with all ten blocks captured and per-block sentences.

---

## Problem 2 — Strace your own shell (45 min)

Pick a command you use every day. Examples: `git status`, `ls -la`, `pip list`, `python3 -c "import requests"`, `curl https://example.com/`.

Run it under `strace -c`:

```bash
strace -c -o homework/02-strace-summary.txt <YOUR-COMMAND> > /dev/null 2>&1
```

Now run it filtered to only file-related syscalls and capture the output:

```bash
strace -e trace=%file -o homework/02-strace-files.txt <YOUR-COMMAND> > /dev/null 2>&1
```

Write `homework/02-notes.md`:

- Top three syscalls by `% time` in the summary, with one sentence each on why they were called.
- Top three **files** opened (from the `%file` trace) and what each is for.
- One paragraph: was there a surprise? (A config file checked from a path you did not expect? A library you did not know was being loaded? A network connection you did not initiate?)

**Acceptance:** `homework/02-strace-summary.txt`, `homework/02-strace-files.txt`, `homework/02-notes.md`.

---

## Problem 3 — Read your own `/proc/self` (60 min)

Write a shell script `homework/03-self-inspect.sh` that prints, for the current shell process:

1. The PID.
2. The contents of `/proc/self/status` (filter to lines you understand and discard the rest, but keep at least: `Name`, `State`, `PPid`, `Uid`, `Gid`, `VmSize`, `VmRSS`, `Threads`, `voluntary_ctxt_switches`, `nonvoluntary_ctxt_switches`).
3. The contents of `/proc/self/io` (all seven fields).
4. The first 5 lines of `/proc/self/maps` and the last 5 lines.
5. The output of `ls -la /proc/self/fd/`.
6. The contents of `/proc/self/cmdline` (with NULs replaced by spaces so it is readable; `tr '\0' ' ' < /proc/self/cmdline; echo`).

Run the script. Save output to `homework/03-output.txt`.

Then write `homework/03-notes.md`:

- One paragraph: which of these `/proc/self/...` views surprised you most, and why?
- One paragraph: which of these would you check if a process you suspected of leaking memory was running slowly? (Hint: more than one.)
- One sentence: what is the difference between `VmSize` and `VmRSS`?

**Acceptance:** `homework/03-self-inspect.sh`, `homework/03-output.txt`, `homework/03-notes.md`.

---

## Problem 4 — Find the noisy process (60 min)

This problem is a smaller version of Challenge 2. On your target machine, in one terminal:

```bash
# Induce a single mystery load.
stress-ng --vm 1 --vm-bytes 80% --timeout 120s &
echo "Started; this will run for 2 minutes."
```

Then **without looking at the `stress-ng` invocation again**, pretend you have inherited this machine and find the noisy process. Capture, in `homework/04-investigation.md`:

- Your initial `vmstat 1 5` output and what it tells you (you should see `si`/`so` or just memory pressure).
- Your `free -h` and `/proc/meminfo` snapshot.
- The `pidstat -r 1 5` output that incriminated the process.
- The PID, command line (from `/proc/<pid>/cmdline`), and the offending value(s).
- A 4-5 sentence summary of the workload's behaviour as you understood it from the evidence.

When done:

```bash
pkill stress-ng
```

**Acceptance:** `homework/04-investigation.md`.

---

## Problem 5 — Measure your mini-htop's overhead (45 min)

Run the Challenge 1 mini-htop (`challenge-01-write-your-own-mini-htop.py`) in streaming mode (`--interval 1`) for 60 seconds on an otherwise-idle host. While it runs, in a second terminal, measure its own resource use:

```bash
# Find the PID
pgrep -f mini-htop || pgrep -f challenge-01-write
# Or note it from the script's stderr.

# Measure
pidstat -p <PID> 1 60 > homework/05-pidstat.txt
```

Then run real `htop` (not the toy) for 60 seconds and measure the same way:

```bash
htop &
HTOP_PID=$!
pidstat -p $HTOP_PID 1 60 > homework/05-pidstat-real.txt
kill $HTOP_PID
```

Write `homework/05-notes.md`:

- Mean `%CPU` of the toy.
- Mean `%CPU` of real `htop`.
- Mean `RSS` of each (from `pidstat -r 1` if you prefer).
- One paragraph: why does real `htop` use less CPU than the toy? (Hint: file caching, ncurses, written in C, reads only what changed.)
- One paragraph: name two specific things you could change in the toy to reduce its overhead.

**Acceptance:** `homework/05-pidstat.txt`, `homework/05-pidstat-real.txt`, `homework/05-notes.md`.

---

## Problem 6 — Reflection (90 min)

`homework/06-reflection.md`, 600-800 words:

1. The lecture argued the USE method is **exhaustive** for first-pass diagnosis: if you have checked U, S, and E for every resource and nothing is anomalous, the bottleneck is somewhere subtler. In your own words, why is exhaustiveness valuable here? What goes wrong when an engineer skips cells?
2. `top`'s `%CPU` is per-core; `htop`'s default is the same. Why does this trip new operators so often? Suggest a default that would not trip them, and explain the trade-off.
3. The "Linux ate my RAM" misconception persists despite decades of explanation. Why is it so sticky? Construct one explanation that you think would land with a first-time Linux user.
4. Compare `strace` and BPF (via `bcc-tools` or `bpftrace`) as observability mechanisms. When is `strace` the right tool? When is BPF? (Hint: ~one production constraint each.)
5. The `sar` recorder is off by default on most distros. Why do you think that is? Should it be on by default? Argue one side and acknowledge the other.
6. Cite the Bash Yellow caution line at the top of your favourite lecture or exercise from this week. (Loyalty test repeats.)

**Acceptance:** `homework/06-reflection.md` of 600-800 words.

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 45 min |
| 3 | 1 h |
| 4 | 1 h |
| 5 | 45 min |
| 6 | 1.5 h |
| **Total** | **~6 h** |

After homework, ship the [mini-project](./mini-project/README.md).
