# Week 7 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 8.

---

**Q1.** Brendan Gregg's USE method asks three questions for every resource. Which three?

- A) Used, Spare, Errors
- B) Utilization, Saturation, Errors
- C) User, System, Errors
- D) Usage, Sampling, Events

---

**Q2.** A process is in state `D` for ninety seconds. Which is the most accurate description?

- A) It is using the CPU.
- B) It is sleeping interruptibly and will wake on any signal.
- C) It is sleeping uninterruptibly, usually blocked on IO at the kernel level; even `SIGKILL` will not clear it until the IO completes.
- D) It is a zombie waiting for the parent to call `wait()`.

---

**Q3.** `top` shows a process with `%CPU` of 200 on an 8-CPU host. Which is true?

- A) The process is using all 8 CPUs at 25 % each.
- B) The process is using two CPUs (200 % = 2 cores at 100 %).
- C) `top` is reporting an error; `%CPU` cannot exceed 100.
- D) The number is normalised to one CPU; the process is using 200/8 = 25 % of the host.

---

**Q4.** Which `iostat -x 1` column is the **most reliable** saturation signal on a modern multi-queue NVMe device?

- A) `%util`
- B) `aqu-sz` (average queue length)
- C) `rkB/s` (read bandwidth)
- D) `r/s` (reads per second)

---

**Q5.** `vmstat 1` shows `si 1234` and `so 5678` (KB swapped in/out per second). What does this most likely indicate?

- A) The system is using swap memory casually; this is normal.
- B) The system is paging actively; memory is exhausted and latency-sensitive workloads will suffer dramatically.
- C) The disk is being written to.
- D) The CPU is in iowait state.

---

**Q6.** `free -h` shows `total 16Gi`, `used 4Gi`, `free 200Mi`, `buff/cache 11Gi`, `available 11Gi`. Is the system out of memory?

- A) Yes, only 200 MiB free.
- B) No, the `buff/cache` is reclaimable and `available` (11 Gi) is the column that matters.
- C) Yes, total memory is fragmented.
- D) Cannot tell without `vmstat`.

---

**Q7.** `strace -p PID` is attached to a busy database process. The database becomes 10× slower. Why?

- A) `strace` is buggy in OpenSSH 9.x.
- B) `strace` uses `ptrace`, which intercepts every syscall and context-switches into the tracer; the overhead can be 2-20× depending on syscall rate.
- C) `strace` consumes the database's network bandwidth.
- D) The disk is now busier because `strace` writes to a log file.

---

**Q8.** Which `/proc` file tells you, for a single process, how many bytes have been read from a block device (versus served from the page cache)?

- A) `/proc/<pid>/stat` field 23 (RSS)
- B) `/proc/<pid>/io` field `read_bytes`
- C) `/proc/<pid>/status` field `VmRSS`
- D) `/proc/<pid>/maps`

---

**Q9.** `ss -tln` shows your web server's `LISTEN` row has `Recv-Q` 128 and `Send-Q` 128. What is the most likely meaning?

- A) The server has received 128 bytes and is about to send 128 bytes.
- B) `Recv-Q` is the number of completed-handshake connections waiting for `accept()`; non-zero (and equal to `Send-Q` = the accept-queue capacity) means the application is too slow to accept and the queue is full. New SYNs are being dropped.
- C) The server is healthy; this is the default queue size.
- D) The server has 128 idle TCP connections.

---

**Q10.** You enabled `sar` collection two weeks ago. A user reports the system was slow yesterday at 14:00. Which is the right first command?

- A) `top` (right now).
- B) `dmesg | tail` and pray the relevant message is still there.
- C) `sar -u -f /var/log/sysstat/sa<DD> -s 14:00:00 -e 15:00:00` to see the recorded CPU stats for that hour.
- D) Restart the affected service.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **B** — Utilization (busy fraction), Saturation (queue depth or wait), Errors (count of failures). The discipline is to ask all three for every resource: CPU, memory, disk, network. Brendan Gregg, "The USE Method" (brendangregg.com).
2. **C** — `D` is uninterruptible sleep, almost always blocked on IO at the kernel level. The hallmark: even `SIGKILL` will not clear it. The process must be unblocked by the IO completing (or by reboot). Long-lived `D` is a signal that the storage path is stuck — a missing NFS server, a hung block device. `cat /proc/<pid>/wchan` shows the kernel function the process is sleeping in.
3. **B** — `top`'s default `%CPU` is per-core: 200 % = two cores at 100 %. On an 8-CPU host, the aggregate is 200/8 = 25 %, but the per-process column is unnormalised. Press `1` in `top` (or `H` in `htop`) to see per-CPU. This is the most common single-thread-vs-multi-thread confusion in performance work.
4. **B** — `aqu-sz` (average queue length). On rotating disks, `%util` near 100 % means saturation, but on modern multi-queue NVMe the device accepts the next IO before the previous one completes, so `%util` saturates well below the device's real capacity. `aqu-sz` tracks queue depth and is the truer signal. `await` (latency) is a useful companion.
5. **B** — `si`/`so` non-zero means the kernel is moving memory between RAM and swap. Any persistent non-zero is bad news for latency-sensitive workloads. Swap IO is 100-1000× slower than RAM access; pages-in/out add latency to any operation that touches them. Buy more RAM, reduce working set, or accept the latency.
6. **B** — The `available` column is the column that matters. The kernel uses idle RAM for page cache (`buff/cache`) because idle memory is wasted; the cache is reclaimable the instant some process asks for memory. linuxatemyram.com exists precisely to settle this confusion. With 11 GiB available, the system has plenty of memory.
7. **B** — `strace` uses `ptrace(2)`, which stops the target on every syscall, lets `strace` read the arguments, and resumes the target. The cost is per-syscall; a busy database with millions of syscalls per second can be slowed 10-100×. Production-safe alternatives: `perf trace` (uses tracepoints, ~5 % overhead) and BPF tools (`bpftrace`, `bcc-tools`).
8. **B** — `/proc/<pid>/io` is the kernel's per-process IO counters. `rchar`/`wchar` are bytes read/written by the process via syscalls (includes cache hits). `read_bytes`/`write_bytes` are bytes actually transferred to/from a block device. The difference is what the page cache served — a process with `rchar` 100 GB and `read_bytes` 100 MB is hot (99 % cache). See `man 5 proc`.
9. **B** — On a `LISTEN` socket in `ss`, `Recv-Q` is the accept queue (completed handshakes waiting for `accept()`) and `Send-Q` is the queue's capacity. Non-zero `Recv-Q` means the application is not calling `accept()` fast enough. When `Recv-Q` reaches `Send-Q`, the queue is full and the kernel drops new SYNs — clients see connection refusals or timeouts. The signature of "the service is slow to accept connections" — common shape of "the API is slow" on overloaded HTTP servers.
10. **C** — This is what `sar` is for. The `sysstat` collector (when enabled) records every 10 minutes; the `sar` command queries the recorded data by date and time. Without `sar`, "what was the system doing yesterday" is unanswerable. The disk cost of `sar` is negligible (~MB/day); enable on every server you care about with `sudo systemctl enable --now sysstat`.

</details>

If you scored 9+: move to homework. 7-8: re-read the lecture sections you missed (especially USE method semantics and the `%util` vs `aqu-sz` distinction). <7: re-read all three lectures from the top, then redo exercise 01 and exercise 03.
