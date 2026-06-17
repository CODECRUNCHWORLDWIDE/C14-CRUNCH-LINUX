# Exercise 1 — Diagnose a busy CPU

**Time:** 30-45 minutes.
**Goal:** Induce a CPU bottleneck on purpose; find it with `htop`, `top`, and `pidstat`; kill it; verify the system returned to normal. Repeat with parallel saturation to see the difference between single-thread and multi-thread shapes.
**Prerequisites:** Lecture 1 and Lecture 2 read. A Linux box you have a shell on (your own laptop in a VM, your Week 6 VPS, anything Linux).

---

## Why this exercise

The single most basic performance pattern is "one process is using all of one CPU." It is the textbook case for `htop` and the first move of every incident response. The exercise makes the pattern visible, then makes it find-able, then makes you do it again with two and four processes so you can recognise the variants.

If you cannot find a `yes > /dev/null &` in two minutes, you cannot find anything harder. Earn it.

---

## Part 1 — Set up

Open three terminals on the target machine.

- **Terminal A** is where you induce the load.
- **Terminal B** is where you observe with `htop` / `top`.
- **Terminal C** is for ad-hoc inspection commands (`ps`, `pidstat`, `cat /proc/...`).

If you do not have three terminals, use `tmux` with three panes.

Confirm baseline:

```bash
# Terminal B
htop
```

The bars at the top should be mostly grey (idle). The process list, sorted by CPU, should show all processes near 0 %. If anything is consuming serious CPU already, find out what before continuing — you cannot diagnose a bottleneck on top of a bottleneck you did not know about.

---

## Part 2 — One busy CPU

Bash Yellow: `yes` writes the string "y\n" to stdout as fast as the CPU can manage; redirected to `/dev/null` the writes are free; the loop becomes a pure CPU spin. The process never stops on its own. Kill it when you are done.

In **Terminal A**:

```bash
yes > /dev/null &
echo "Started; PID is $!"
```

Note the PID printed; you will use it.

In **Terminal B** (`htop`):

- One of the per-CPU bars at the top should immediately be solid green (user-space) or partially red (some kernel time).
- The process list, sorted by `CPU%` (default), shows `yes` near the top with 100 % CPU. (On a multi-core system other CPUs remain near 0 %; aggregate is `100/N` %.)

Record what you see:

```bash
# Terminal C
date +%H:%M:%S
ps -o pid,user,pcpu,stat,comm -p $!  # the yes process
```

The state should be `R` (running) most of the time, briefly `S` when the kernel schedules a different process.

### 2.1 The aggregate-versus-per-CPU trap

Press `1` in `htop` (if not already in per-CPU mode) — or run `top` and press `1` — and confirm: **one CPU at 100 %, all others near 0 %**. This is the single-thread saturation shape. If you accidentally look at the aggregate `%CPU` you might think the system is "12 % busy" on an 8-core box.

Run the per-CPU view from another tool to confirm:

```bash
# Terminal C
mpstat -P ALL 1 3
```

You should see exactly one CPU column with `%usr` near 100 and `%idle` near 0; all other columns near `%idle 100`.

---

## Part 3 — Find the culprit with the tools we taught

You already know the PID (you saw it from `&`). The exercise is to find it **as if you did not**. Pretend somebody else ran `yes > /dev/null &` on this host and now you are paged.

### 3.1 With `top`

```bash
top -n 1 -b -o %CPU | head -15
```

`-n 1` one iteration; `-b` batch mode (no curses); `-o %CPU` sort by CPU. Top of the list is your culprit.

### 3.2 With `htop`

If `htop` is already open in Terminal B, the process is at the top of the list (default sort by `CPU%`). Press `F3` (search) and type `yes` to highlight it.

### 3.3 With `ps`

```bash
ps -eo pid,user,pcpu,stat,comm --sort=-pcpu | head -5
```

`--sort=-pcpu` sorts by descending CPU percent.

### 3.4 With `pidstat`

```bash
pidstat 1 3
```

After three seconds you see one line per active process, with `%CPU` near 100 for the culprit and the rest near 0.

### 3.5 Read `/proc` directly

To prove you do not need a tool:

```bash
# Replace 5234 with your actual PID
cat /proc/5234/status | grep -E '^(Name|State|VmRSS|Threads|voluntary_ctxt_switches|nonvoluntary_ctxt_switches)'
```

You should see `State: R (running)` and a high `nonvoluntary_ctxt_switches` (the kernel preempts the process every scheduler tick because it does not voluntarily yield).

### 3.6 Kill it

```bash
# Terminal A or C — same PID as before
kill $!
# or by name:
pkill -x yes
# verify:
pgrep -x yes && echo "still running" || echo "gone"
```

Confirm `htop` returns to mostly grey bars and the load average begins to drop (load average is a moving average; it takes a minute or two to fall).

---

## Part 4 — Four busy CPUs

Now the parallel-saturation shape. We launch four `yes` processes:

```bash
for i in 1 2 3 4; do yes > /dev/null & done
echo "PIDs: $(jobs -p)"
```

In `htop`: four CPU bars near 100 %, others near 0 % (if you have more than 4 cores). On a 4-core machine: all four bars at 100 %, system fully saturated.

```bash
mpstat -P ALL 1 3
```

Four CPU rows at high `%usr`. Aggregate average is `400/N` %.

```bash
uptime
```

Watch the load average climb. With four CPU-bound processes, after a minute the 1-minute load average should approach 4. If your machine has 4 cores, this is "fully saturated." If it has 8 cores, it is "half saturated."

```bash
vmstat 1 5
```

Column `r` should be `4` (four runnable). Column `us` should be high. Column `id` low. `wa` and `b` near 0 (no IO involved).

Kill everything:

```bash
pkill -x yes
```

---

## Part 5 — One CPU at 100 % `%sys` (kernel-time)

The shapes so far have been user-space. The kernel-time variant looks subtly different in `htop` (the bars are red instead of green). One way to induce it is a tight syscall loop:

```bash
# Terminal A — a Python one-liner that calls write() in a tight loop
python3 -c 'import os, sys
fd = os.open("/dev/null", os.O_WRONLY)
while True:
    os.write(fd, b"x")' &
echo "PID is $!"
```

This process spends almost all its time in the `write` syscall — kernel time, not user time.

In **Terminal B** (`htop`), the relevant CPU bar should now be mostly red (kernel) rather than green (user). Confirm with `mpstat`:

```bash
mpstat -P ALL 1 3
```

The pinned CPU now shows `%sys` near 100 and `%usr` near 0 — the inverse of the `yes` case.

```bash
# Verify with strace -c (short sample — strace adds overhead)
sudo strace -c -p $! &
sleep 5
sudo kill %2  # stop strace; the process continues
```

The `strace -c` summary will show `write` dominating the syscall count.

Kill:

```bash
kill $!  # or kill <PID-you-recorded>
```

---

## Part 6 — Acceptance criteria

By the end of this exercise you should have, in your notes:

- [ ] The PID of your `yes` process.
- [ ] The output of `top -n 1 -b -o %CPU | head -10` showing `yes` at the top.
- [ ] The output of `mpstat -P ALL 1 3` showing one CPU near 100 % `%usr`.
- [ ] The output of `cat /proc/<pid>/status` showing `State: R (running)`.
- [ ] The output of `vmstat 1 5` during the four-process variant showing `r 4`.
- [ ] The output of `mpstat -P ALL 1 3` during the kernel-time variant showing `%sys` near 100 (not `%usr`).
- [ ] A 1-2 sentence description of the difference between the `yes > /dev/null` shape (user-space) and the `os.write` loop shape (kernel-space), as visible in `htop`.

Save these to `~/c14-w07/exercise-01/notes.md`. The mini-project will draw on the same skills.

---

## Pitfalls

- **Forgetting to kill the load.** `yes > /dev/null &` will run forever. Before you close the terminal, `pkill -x yes`.
- **Looking at the aggregated `%CPU` and concluding the system is fine.** On a 16-core host, one `yes` consumes 6.25 % aggregate. Always look at the per-CPU view.
- **Confusing user-time and kernel-time visually.** Green = user; red = kernel. `htop`'s colour code is the fastest way to tell them apart.
- **Running this on a shared production system.** Don't. Use a VM or a personal scratch host.

---

## Optional extensions

- Pin `yes` to a specific CPU with `taskset -c 3 yes > /dev/null &`. Confirm that CPU 3 (and only CPU 3) lights up in `mpstat`.
- Run `yes` with a niceness of 19 (`nice -n 19 yes > /dev/null &`). Watch what happens to its CPU usage when you start a second, normal-priority `yes` — the niced one yields. Read the `htop` "Blue" colour you have probably never noticed before.
- Use `stress-ng --cpu 4 --cpu-method matrixprod` instead of `yes`. `stress-ng` provides real work (matrix multiplication) and is calibrated; useful for repeatable load testing.

---

*Solutions: [SOLUTIONS.md](./SOLUTIONS.md).*

*Next: [Exercise 2 — trace a syscall](./exercise-02-trace-a-syscall.md).*
