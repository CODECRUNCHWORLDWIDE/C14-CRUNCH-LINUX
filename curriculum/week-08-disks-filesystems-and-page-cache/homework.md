# Week 8 Homework

Six problems. Approximately six hours total. Some of these are short-answer; some require a Linux box you can experiment on; one is a small write-up. As with Week 7's homework, the grader is looking for **evidence chain**: did you measure, did you cite the numbers, did your conclusion follow from the data.

This is the **final week's homework** of C14. Do it carefully; the mini-project is the capstone but this homework is the last set of structured questions before you are graded only on running a server.

---

## Problem 1 — Read your own block devices (45 min)

On the Linux box you have been using this term:

1. Run `lsblk -f` and copy the full output into your answer.
2. For each line, identify: device, size, filesystem type (or "none"), UUID (or "none"), mount point (or "none"). A table is fine.
3. Identify which filesystem is your **root** (mounted at `/`). Note its filesystem type.
4. Identify whether your root is on a **partition** directly, on an **LVM LV**, or on an **encrypted (LUKS) volume**. Explain how you can tell from the `lsblk` output.
5. Run `cat /proc/mounts | grep " / "`. Compare the mount options the kernel actually has set against the `/etc/fstab` line for `/`. Note any differences and explain.

**Rubric**:

- 4/4: complete inventory, correct type identification, correct stack identification (partition vs LV vs LUKS), thoughtful comparison of `/proc/mounts` to fstab.
- 3/4: minor errors in one column or one missing detail.
- 2/4: half the inventory missing or stack identification wrong.
- 1/4: only the raw output, no analysis.

---

## Problem 2 — Walk a complete partition / format / mount / persist (60 min)

Repeat Exercise 1 from scratch **without looking at the exercise**. Use a loopback file. Capture:

1. The output of each command you ran, in order.
2. The contents of the `/etc/fstab` line you added.
3. The output of `mount | grep /mnt/week08-`.
4. The output of `df -h /mnt/week08-disk1`.
5. The cleanup commands you ran at the end.

If you used a real disk instead of a loopback, note which device and confirm you backed up `/etc/fstab` before editing.

**Rubric**:

- 4/4: every step captured, ten or fewer commands, fstab uses `UUID=`, cleanup is complete (no leftover mounts or loopbacks).
- 3/4: one command missing or fstab uses `/dev/...` instead of `UUID=`.
- 2/4: cleanup incomplete.
- 1/4: exercise re-done with reference; no original work.

---

## Problem 3 — The page cache, with numbers (45 min)

Run the page-cache exercise (Exercise 2) on your machine. Capture and report:

1. The **cold read time** for a 500 MB file (seconds and computed MB/s).
2. The **warm read time** for the same file (seconds and computed MB/s).
3. The **ratio** warm / cold. Discuss whether the ratio is consistent with your hardware: if you have an SSD doing ~500 MB/s sequential, what RAM bandwidth would you need to see a 10× warm/cold ratio?
4. The contents of `/proc/meminfo`'s `Cached:` field **before** and **after** the cold read. Compute the change.
5. Run `vmstat 1` in a side terminal while you do the cold and warm reads. Capture the `bi` (block-in) and `wa` (cpu iowait) columns during each. Note the difference.

**Rubric**:

- 4/4: numbers captured, ratio sensible, `/proc/meminfo` delta near +500 MiB on cold, `vmstat`'s `bi` and `wa` near zero on warm and substantial on cold, thoughtful note on hardware.
- 3/4: most numbers, one missing or off by a clear factor.
- 2/4: numbers captured but not interpreted.
- 1/4: incomplete.

---

## Problem 4 — `fio` and the spec sheet (90 min)

Run the four canonical `fio` jobs (Exercise 4) on your machine. Then look up your disk's spec sheet (or, if you cannot find it: NVMe, run `sudo nvme smart-log /dev/nvme0` and the manufacturer page; SATA SSD, run `sudo smartctl -i /dev/sda` to get the model number and search). Compare:

| Metric | Spec | Measured | Ratio |
|--------|------|----------|-------|
| 4k random read IOPS | | | |
| 4k random write IOPS | | | |
| 1MB sequential read MB/s | | | |
| 1MB sequential write MB/s | | | |

Discuss any large gaps (>30 %). Likely culprits, in rough order of probability: page-cache pollution (did you use `direct=1`?), wrong IO scheduler, PCIe lane allocation (NVMe only), thermal throttling (the device runs hot after sustained writes), drive wear (`smartctl` `percentage_used`).

**Rubric**:

- 4/4: all four numbers measured, all four spec numbers found, table filled, large gaps explained.
- 3/4: one spec number missing.
- 2/4: numbers but no analysis.
- 1/4: incomplete.

---

## Problem 5 — Filesystem decision matrix, applied (30 min)

For each of the following workloads, choose **ext4**, **xfs**, **btrfs**, or **none of the above (use special-purpose)**, and justify in one paragraph:

1. **A small VPS** (1 vCPU, 1 GB RAM, 25 GB disk) running nginx + a Flask app + a SQLite database, no high write volume, single-user development environment.
2. **A 100 TB file server** for a research lab: many large files (1-50 GB each), several users writing in parallel via NFS.
3. **A workstation** for a developer who wants to be able to roll back the system to a known-good state after a botched package update.
4. **A PostgreSQL primary** on a 1 TB NVMe SSD, OLTP workload with high write rate (5000 transactions/sec), strict durability requirements.
5. **A `/boot` partition** on a system that boots via GRUB (BIOS, not UEFI).
6. **A swap partition** on a system with 32 GB RAM.

**Rubric**:

- 4/4: every choice correct, every justification cites at least one design property (CoW, allocation groups, no-shrink, etc.).
- 3/4: 5/6 correct or 6/6 with thin justifications.
- 2/4: 4/6 correct.
- 1/4: 3 or fewer correct.

Sample answer for #1 (do not copy verbatim): **ext4**. The workload is small, mixed-purpose, no specific feature need (no snapshots, no need for parallel-write scaling, no large files). ext4 is the conservative default: mature, well-tooled, the failure modes are well-known. Choosing xfs would be defensible but offers no advantage at this scale; btrfs would add CoW overhead with no rollback usage to justify it.

---

## Problem 6 — Postmortem template (60 min)

The mini-project (running a real server for 7 days) requires a postmortem. **Write the postmortem template now**, before the 7 days start. Use the following section headers and fill each with one or two paragraphs of placeholder text explaining what kind of evidence will go in. Be specific about the questions you intend to answer and the data sources you will use.

Template sections (required):

1. **Executive summary** — one paragraph, the headline finding.
2. **Service description** — what was running, who could reach it, what the SLO was.
3. **Hosting environment** — provider, instance size, disk size, network details, kernel version.
4. **Configuration baseline** — what was installed, what was hardened, the contents of relevant config files.
5. **Observability** — what was logged, what was monitored, what alerts were set up.
6. **The seven days** — what happened, day by day. Both noteworthy events ("port-scan from 1.2.3.4 at 14:00 UTC") and the quiet times ("days 3-4 nominal").
7. **Performance** — `fio` numbers from before the experiment, key `iostat`, `vmstat`, `free` captures during the week, anything you measured.
8. **Security** — what attacked, what fail2ban caught, what the auth.log looked like.
9. **What alerted** — every alert you received, classified by precision (real / noise).
10. **What didn't alert that should have** — gaps in your monitoring, identified by reading the journal afterwards.
11. **What I would change** — three concrete improvements with reasoning.
12. **Appendix: full configuration files** — `nginx.conf`, `fail2ban` jail config, the `unattended-upgrades` config, your `/etc/fstab`.

Submit the template (no fewer than 1000 words; placeholders explaining what evidence goes where).

**Rubric**:

- 4/4: all 12 sections, thoughtful placeholders that name specific data sources, > 1000 words.
- 3/4: 10-11 sections, placeholders less specific.
- 2/4: 7-9 sections, vague placeholders.
- 1/4: an outline only.

---

## Overall grading

Each problem is worth 4 points; 24 total.

| Score | Grade |
|-------|-------|
| 22-24 | A |
| 19-21 | B |
| 16-18 | C |
| 13-15 | D |
| <13   | F — re-do the homework. The mini-project assumes mastery. |

The homework feeds directly into the mini-project. Problem 6 in particular is what you will deliver, expanded, after the seven days. Treat it as a draft, not a placeholder.

---

## Submission format

A single zip / tarball / Git repository containing:

- `problem-1.md` through `problem-6.md` (or one `homework.md` with section headers).
- Any captured outputs as separate files in an `evidence/` directory, referenced from the answers.
- For problem 4, the `fio` log files.

Push to your portfolio repo as `c14-week-08/homework/`. Open a PR if your portfolio uses one.

---

*Office hours: Thursdays 18:00 UTC on the C14 Discord. Bring questions on problem 6 specifically; the postmortem is the deliverable that distinguishes a "did the work" submission from a "graduated the track" one.*
