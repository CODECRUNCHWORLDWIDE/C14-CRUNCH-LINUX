# Exercise 2 — Trace a syscall

**Time:** 30-45 minutes.
**Goal:** Run `strace -c` against `ls`. Read the summary. Identify the dominant syscall. Repeat with a more interesting workload. Learn to read `strace` output without flinching at the volume.
**Prerequisites:** Lecture 3 §4 read. `strace` installed (`sudo apt install strace` or `sudo dnf install strace`).

---

## Why this exercise

Every Linux program eventually does I/O, allocates memory, or talks to the network. Every one of those operations is a **syscall** — a function call from user space into the kernel. Knowing which syscalls a process makes, in what proportion, and with what arguments, is often the difference between "the program is doing what I think" and "the program is reading from `~/.config/old/wrong-file.toml` every request and I would never have guessed."

`strace` is the right tool when the question is **exactly what is this process asking the kernel for**.

---

## Part 1 — `strace -c ls`

The simplest invocation: run `ls` under `strace -c` and read the summary.

```bash
strace -c ls / > /dev/null
```

The redirection of stdout to `/dev/null` is so `ls`'s own output does not clutter your terminal; the `strace` summary still goes to stderr and you see it.

You should see output similar to:

```
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

Exact numbers vary by system, but the **shape** is the same: `mmap`, `mprotect`, `openat`, `close`, `read`, `fstat`, `write`, `getdents64` are the typical top syscalls for `ls`. Why each?

- **`mmap`, `mprotect`** — the dynamic linker (`ld-linux.so`) starts up. Every shared library `ls` links to (libc, libselinux, libacl, libpcre, ...) requires one or more `mmap` calls to map the file and `mprotect` to set the page permissions. There are 27 of them because there are roughly that many shared libraries.
- **`openat`, `close`** — opens for libraries, the binary itself, the directory being listed. 27 opens to mirror the 27 mmaps (each library is opened, then mmap'd, then closed).
- **`fstat`** — stats the directory entries to print sizes and modes (when `ls` is in long-format).
- **`getdents64`** — the syscall that returns directory entries. `ls /` does this once or twice for a small directory; many times for `/usr/lib`.
- **`read`** — reading dynamic-linker data. Not the directory entries (those come via `getdents64`).
- **`write`** — writing the output. The number of `write` calls depends on whether stdout is a terminal (line-buffered, many writes) or a pipe (block-buffered, fewer writes).

If you run the same command with a more populated directory:

```bash
strace -c ls /usr/bin > /dev/null
```

The pattern shifts: `getdents64` and `fstat` counts increase (more entries to read and stat), while `mmap`/`mprotect` stay roughly the same (the same libraries are linked).

### 1.1 Observation question

Look at your output. **Which syscall accounts for the most `% time`?** It is probably `mmap` or `mprotect` — but the answer depends on your `ls` version, your libc, and (in particular) the page-fault traffic at startup. Note the dominant syscall in your notebook.

If your top syscall is `read` or `getdents64`, you are running `ls` against a large directory; the syscall has shifted from "startup costs" (mmap/mprotect) to "doing the work" (reading entries).

---

## Part 2 — `strace -c` on something with more I/O

`ls` is short and startup-dominated. Repeat with a workload that exercises real I/O:

```bash
# Create a 50 MB file (one-time setup)
dd if=/dev/urandom of=/tmp/big.bin bs=1M count=50

# Now strace a cat of the file
strace -c cat /tmp/big.bin > /dev/null
```

Output:

```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 65.10    0.045231          12      3201           write
 32.50    0.022595           7      3201           read
  0.95    0.000660          15        44           mmap
  0.50    0.000348           4        82           mprotect
  ...
100.00    0.069452                  6549         0 total
```

Now `read` and `write` dominate, by roughly a 1:1 ratio (each `read` from the file produces one `write` to `/dev/null`). The `mmap`/`mprotect` startup costs are now a rounding error.

The default read size is `cat`'s buffer (libc's BUFSIZ, typically 8192 bytes). 50 MiB / 8 KiB = ~6400 reads. (The actual count is a little different because of partial reads at EOF.)

### 2.1 What if `cat` used a bigger buffer?

```bash
dd if=/tmp/big.bin of=/dev/null bs=1M
```

`dd` with `bs=1M` reads 1 MiB at a time. Re-run under `strace`:

```bash
strace -c dd if=/tmp/big.bin of=/dev/null bs=1M
```

Output:

```
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 51.20    0.001234         24        50           read
 47.80    0.001152         22        50           write
  ...
100.00    0.002412                   ...         0 total
```

Same data moved, but in 50 reads/writes instead of 6400. The same workload, expressed with a larger buffer, makes 99 % fewer syscalls — and runs measurably faster. Lesson: **syscall count matters**. Larger buffers reduce overhead.

This is one of the most common Python performance lessons. `f.read()` (read all) versus `for line in f: ...` (one syscall per line, sometimes) is a measurable difference when files are large.

---

## Part 3 — `strace -p PID` on a running process

The other major strace use case: attach to a running process and watch what it does.

In **Terminal A**, start a long-running, lightly-active process:

```bash
# A Python script that prints once per second
python3 -c 'import time
while True:
    print("tick", flush=True)
    time.sleep(1)' &
echo "PID: $!"
```

Note the PID. In **Terminal B**, attach `strace`:

```bash
sudo strace -p <PID> -e trace=write,clock_nanosleep
```

You should see, every second:

```
clock_nanosleep(CLOCK_MONOTONIC, 0, {tv_sec=1, tv_nsec=0}, NULL) = 0
write(1, "tick\n", 5) = 5
clock_nanosleep(CLOCK_MONOTONIC, 0, {tv_sec=1, tv_nsec=0}, NULL) = 0
write(1, "tick\n", 5) = 5
...
```

The `-e trace=...` filter limits output to the syscalls you care about. Without it, you would see every Python-internal syscall (mostly `futex` and `epoll_wait`).

Detach `strace` with `Ctrl-C` (the process you attached to continues; only `strace` exits).

Kill the Python process:

```bash
kill <PID>
```

### 3.1 Observer effect

Time the Python loop without `strace` for ten seconds:

```bash
python3 -c 'import time
start = time.time()
i = 0
while time.time() - start < 10:
    i += 1
print(f"{i} iterations in 10 seconds")' &
echo "PID: $!"
```

Note the result, kill the process. Now repeat with `strace` attached:

```bash
python3 -c 'import time
start = time.time()
i = 0
while time.time() - start < 10:
    i += 1
print(f"{i} iterations in 10 seconds")' &
PID=$!
sudo strace -p $PID -o /tmp/strace.log -e trace=all &
wait $PID
```

The iteration count under `strace` will be substantially lower — sometimes 10-50× lower depending on what syscalls the Python interpreter is doing under the hood. This is the **observer effect**: tracing slowed the target. The lesson is to never blindly `strace` a production process.

---

## Part 4 — Filter `strace` to the interesting parts

`strace`'s `-e` flag is the difference between "wall of text" and "useful tool." A few patterns:

```bash
# Only file-related syscalls
strace -e trace=%file ls /

# Only network-related syscalls (sockets, connect, accept, send, recv, ...)
strace -e trace=%network curl -s https://example.com/

# Only openat() and close() — file lifecycle
strace -e trace=openat,close ls / 2>&1 | grep -v "ENOENT\|\.so"

# Translate FDs to filenames (-y)
sudo strace -fy -e trace=openat,read,write,close -p <PID>
```

The `-y` flag is one of the most underused strace features: in the output, `read(3, ...)` becomes `read(3</tmp/big.bin>, ...)` — the FD is annotated with the path it refers to. Read with `-y` whenever you want to know *what file* is being read.

---

## Part 5 — `strace` versus `perf trace`

If you have `perf` installed (`sudo apt install linux-tools-generic`), repeat the `cat /tmp/big.bin > /dev/null` experiment with `perf trace`:

```bash
perf trace -s cat /tmp/big.bin > /dev/null
```

`perf trace -s` provides a syscall summary similar to `strace -c`, but the mechanism is different: `perf` uses kernel tracepoints, not `ptrace`. The overhead is 5-10×, not 2-20×. For long-running processes or production diagnosis, `perf trace` is the more responsible choice.

(`perf trace` is not in every distro by default; it requires the `linux-tools-$(uname -r)` package on Ubuntu. If it is not available, no problem — `strace -c` is the universal tool.)

---

## Part 6 — Acceptance criteria

By the end of this exercise you should have, in your notes:

- [ ] The `strace -c ls /` output, with one annotated line explaining what `mmap` is doing (and why there are ~27 of them).
- [ ] The `strace -c cat /tmp/big.bin > /dev/null` output, with the syscall count for `read` and `write` and a one-line calculation showing 50 MiB / 8 KiB ≈ the syscall count you observed.
- [ ] The `strace -c dd if=/tmp/big.bin of=/dev/null bs=1M` output, showing ~50 reads and ~50 writes, and one sentence on why the larger buffer is faster.
- [ ] The `strace -p PID` output for the Python `tick` script — the line for `write(1, "tick\n", 5) = 5`.
- [ ] A one-paragraph observer-effect note: iterations per second of the busy Python loop with and without `strace` attached.

Save these to `~/c14-w07/exercise-02/notes.md`.

---

## Pitfalls

- **`strace` requires permission.** Unprivileged users can `strace` their own processes. To `strace` a process owned by another user, you need `sudo` or `CAP_SYS_PTRACE`. On Ubuntu with `kernel.yama.ptrace_scope = 1` (the default), even root cannot `strace` a process that did not explicitly allow it via `prctl(PR_SET_PTRACER)`. `sudo` works; if it does not, check `sysctl kernel.yama.ptrace_scope`.
- **Volume of output.** `strace` without `-c` or `-e` on a busy process produces thousands of lines per second. Filter or redirect.
- **The observer effect is real.** `strace` slows things 2-20×. If the bug is "the service is slow," `strace` is probably the *cause* of the slowness you measure under it.
- **`strace -c` measures only what it traced.** If you start strace on a process that has already done all its allocations, `mmap` will not appear. Read `-c` carefully — it is a summary of the traced period, not of the process's lifetime.

---

## Optional extensions

- Run `strace -e trace=execve -f -- bash -c "ls / > /dev/null"`. Watch every `execve`; even a single shell command does several internally.
- Use `strace -y -e trace=openat python3 -c "import json; json.load(open('/etc/passwd'))"`. The `-y` annotation makes the file paths obvious.
- Pick a daemon you run (`sshd`, `systemd-journald`, `nginx`) and `sudo strace -p <PID>` for ten seconds. Watch what it does on a quiet system. Detach. Most of what you see will be `epoll_wait` (waiting for events) — a healthy daemon is mostly sleeping.

---

*Solutions: [SOLUTIONS.md](./SOLUTIONS.md).*

*Next: [Exercise 3 — iostat during dd](./exercise-03-iostat-during-dd.md).*
