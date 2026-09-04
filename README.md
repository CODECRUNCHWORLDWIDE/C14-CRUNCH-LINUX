# C14 · Crunch Linux

> A free, open-source **8-week Linux track** for engineers who can write code but feel uncertain in a terminal. From "what shell am I in?" to a small Linux server you run yourself, with systemd services, hardened SSH, and a backup plan you've actually tested. The prerequisite for [C6](../C6-CYBERSECURITY-CRUNCH/), [C7](../C7-WIRE-CRUNCH-EMBEDDED-SYSTEMS/), and [C15](../C15-CRUNCH-DEVOPS/).

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Linux · bash · systemd](https://img.shields.io/badge/stack-Linux_·_bash_·_systemd-FACC15.svg)](#stack)
[![Built in the open](https://img.shields.io/badge/built-in%20the%20open-FACC15.svg)](https://github.com/CODE-CRUNCH-CLUB)

C14 is the shortest specialization track in Tier 1 (8 weeks) because Linux competence is a *foundation* others build on — not a destination. It's deliberately sized to get you ready for C6 (security), C7 (embedded), and C15 (DevOps) without forcing you to take all of those.

---

## Standards & equivalency

> C14 stands in for a university's Unix and Linux system administration course, and for the operator's half of operating systems and systems programming.

**University equivalent.** Three courses, and C14 does not claim them equally.

- **Unix / Linux System Administration** — `CGS 3269`, `CIS 4204`, `CS 2043`. Coverage: **full**. Every outcome an accredited section of that course teaches is taught here, and assessed.
- **Operating Systems** — `COP 4610`, `CS 162`, `CS 4414`. Coverage: **partial**. Partial means the operator's side of the subject. C14 teaches processes and signals, the filesystem hierarchy, users, groups, permissions and ACLs, package management, services and their lifecycle, scheduling and caching as behaviour you can measure, and recovering a machine you broke. It does not have you build the kernel side. You will read a scheduler's effects in `pidstat` and the page cache's effects in `vmstat`; you will not write a scheduler, a pager or a filesystem.
- **Systems Programming** — `COP 4338`, `CS 240`, `15-213`. Coverage: **partial**. Partial means the Unix half: the terminal, pipes and redirection, processes, exit status and signals, permissions, the system-call boundary read through `strace`, and the toolchain your programs run inside. The C-language half of that course — pointers, manual memory, writing programs against the OS in C — is not taught here.

C14 carries no credit, no transcript entry, no accreditation and no proctored exam. The equivalence is one of **content and skill**: what an accredited section teaches, taught here at the same depth or deeper, and assessed by work you have to do. What a registrar records is not something an open repository can give you.

| University outcome | Where this course teaches it | Depth |
| --- | --- | --- |
| Work at the shell: navigate a Unix filesystem, read file metadata, and compose commands with redirection, pipes and globs | [Week 01](curriculum/week-01-shell-and-filesystem/) | same |
| Explain the filesystem hierarchy — what `/etc`, `/var`, `/usr`, `/proc` and `/sys` are for and why | [Week 01](curriculum/week-01-shell-and-filesystem/) | deeper |
| Use the system's own documentation — `man`, `info`, `--help` — as the first reference rather than the last | [Week 01](curriculum/week-01-shell-and-filesystem/) | same |
| Recover a system whose configuration has been broken, without reinstalling it | [Week 01](curriculum/week-01-shell-and-filesystem/) | deeper |
| Filter, transform and summarise text streams with the standard Unix tools | [Week 02](curriculum/week-02-text-and-pipes/) | deeper |
| Administer users and groups, and the account databases behind them | [Week 03](curriculum/week-03-permissions-users-groups/) | same |
| Set and reason about file permissions, `umask`, the special bits, and access control lists | [Week 03](curriculum/week-03-permissions-users-groups/) | deeper |
| Grant elevated privilege deliberately, through `sudo` policy rather than a shared root password | [Week 03](curriculum/week-03-permissions-users-groups/) | same |
| Automate routine administration with shell scripts that handle failure | [Week 04](curriculum/week-04-shell-scripting-properly/) | deeper |
| Reason about processes, exit status and signals, and write code that responds to them | [Week 04](curriculum/week-04-shell-scripting-properly/) | same |
| Install and manage software with the system package manager, on both Debian- and Red Hat-family systems | [Week 04](curriculum/week-04-shell-scripting-properly/) | same |
| Manage services and scheduled work under the system's init and logging facilities | [Week 05](curriculum/week-05-systemd-services/) | deeper |
| Confine a running service to the privileges it actually needs | [Week 05](curriculum/week-05-systemd-services/) | deeper |
| Configure secure remote access and host-based network filtering | [Week 06](curriculum/week-06-ssh-networking-firewalls/) | same |
| Monitor a running system and diagnose a performance problem from measurement | [Week 07](curriculum/week-07-observability-htop-iostat-strace/) | deeper |
| Observe the system-call boundary between a program and the kernel | [Week 07](curriculum/week-07-observability-htop-iostat-strace/) | same |
| Describe CPU scheduling — run queues, priority, and what load average counts | [Week 07](curriculum/week-07-observability-htop-iostat-strace/) | lighter |
| Manage storage: block devices, partition tables, filesystems, mounting, and `/etc/fstab` | [Week 08](curriculum/week-08-disks-filesystems-and-page-cache/) | same |
| Explain buffering and caching in the I/O path, and demonstrate their effect | [Week 08](curriculum/week-08-disks-filesystems-and-page-cache/) | same |
| Describe virtual memory and page replacement, and the writeback of dirty pages | [Week 08](curriculum/week-08-disks-filesystems-and-page-cache/) | lighter |
| Describe how a filesystem lays data out on a device, and choose between filesystems with reasons | [Week 08](curriculum/week-08-disks-filesystems-and-page-cache/) | lighter |

Every row above points at a week that **assigns work** on that outcome — an exercise, a challenge, homework, a quiz item or a mini-project — not a week that merely mentions it. The three `lighter` rows are the kernel-implementation side of an operating systems course: C14 has you measure scheduling, paging and filesystem behaviour on a real machine, and stops short of building any of the three. That gap is declared below and in the ledger.

**The industry bar.** What an employer expects of somebody paid to operate Linux, and where this course makes the learner do it. Two of these are met in a medium other than code, and that is said plainly rather than glossed.

| What the job expects | Where this course does it |
| --- | --- |
| Work lands as a commit in a repository you own, not a file on your desktop | Every mini-project's **Deliverable** section names a directory inside your `crunch-linux-portfolio-<handle>` repository — starting with [`curriculum/week-01-shell-and-filesystem/mini-project/README.md`](curriculum/week-01-shell-and-filesystem/mini-project/README.md) |
| You read code you did not write and form a judgement on it | [`curriculum/week-04-shell-scripting-properly/challenges/challenge-01-rewrite-bad-script.md`](curriculum/week-04-shell-scripting-properly/challenges/challenge-01-rewrite-bad-script.md) — a real-world backup script that works until it does not; and [`curriculum/week-04-shell-scripting-properly/exercises/exercise-03-shellcheck-fixes.md`](curriculum/week-04-shell-scripting-properly/exercises/exercise-03-shellcheck-fixes.md) |
| Tests exist, and the command to run them is written down | [`curriculum/week-04-shell-scripting-properly/mini-project/README.md`](curriculum/week-04-shell-scripting-properly/mini-project/README.md) — `tests/test-*.sh` and a `Makefile`; acceptance is `make test && make lint` exiting 0. Week 03 ships a `verify.sh` harness that asserts the denials as well as the permissions |
| You read the real failure text instead of guessing | The `Common failure modes` sections quote output captured from a real run — for example `Permission denied (publickey)` and `Bad configuration option` in [`curriculum/week-06-ssh-networking-firewalls/exercises/exercise-01-key-auth-and-config.md`](curriculum/week-06-ssh-networking-firewalls/exercises/exercise-01-key-auth-and-config.md) |
| A linter and a formatter run over the work before it ships | ShellCheck and `shfmt` from the first day of Week 04 — [`curriculum/week-04-shell-scripting-properly/resources.md`](curriculum/week-04-shell-scripting-properly/resources.md); zero warnings is an acceptance criterion, and every deliberate exception carries a written reason |
| Work is isolated so a mistake cannot reach the rest of the machine | The systemd sandbox is this course's dependency isolation — [`curriculum/week-05-systemd-services/exercises/exercise-03-sandbox-a-service.md`](curriculum/week-05-systemd-services/exercises/exercise-03-sandbox-a-service.md) ratchets `systemd-analyze security` down from wide open |
| The work runs unattended, on a schedule, without you | [`curriculum/week-05-systemd-services/exercises/exercise-02-timer-instead-of-cron.md`](curriculum/week-05-systemd-services/exercises/exercise-02-timer-instead-of-cron.md). C14 has no hosted-CI unit — a pipeline that runs on every push belongs to [C15 · Crunch DevOps](../C15-CRUNCH-DEVOPS/), and this course says so rather than pretending a timer is the same thing |
| The output is portfolio-grade — a stranger can reproduce it from the README | The capstone deliverable is an operated server and a written runbook, not a program, so "runs from a clean clone" becomes "another engineer can rebuild this host and reach the same state from your runbook" — [`curriculum/week-08-disks-filesystems-and-page-cache/mini-project/README.md`](curriculum/week-08-disks-filesystems-and-page-cache/mini-project/README.md) |
| The professional task is named, not implied | Every week's `## Standards this week meets` block states the task somebody is paid to do, in that week's `README.md` |

**Beyond both bars.** Clearing the two floors is entry, not success. Open any of these and check it in under a minute.

| What we add | Which bar it beats | Where it lives |
| --- | --- | --- |
| Every week's quiz publishes its answer key in the same file as the questions, before anyone sits it — no key withheld until a deadline | both | [`curriculum/week-03-permissions-users-groups/quiz.md`](curriculum/week-03-permissions-users-groups/quiz.md) |
| Worked, step-by-step solutions to every exercise sit beside the exercises, with the commands and the expected output | university | [`curriculum/week-08-disks-filesystems-and-page-cache/exercises/SOLUTIONS.md`](curriculum/week-08-disks-filesystems-and-page-cache/exercises/SOLUTIONS.md) |
| The learner ends holding a server they ran on the public internet for seven days and a postmortem of what it did, instead of a grade only a registrar can see | both | [`curriculum/week-08-disks-filesystems-and-page-cache/mini-project/README.md`](curriculum/week-08-disks-filesystems-and-page-cache/mini-project/README.md) |
| A real host is hardened and then attacked by the internet for a week, and the brute-force traffic it collected is parsed into an evidence report | university | [`curriculum/week-06-ssh-networking-firewalls/mini-project/README.md`](curriculum/week-06-ssh-networking-firewalls/mini-project/README.md) |
| Diagnosis is graded on the evidence chain: every claim in the performance report must be backed by captured output another engineer can replay | industry | [`curriculum/week-07-observability-htop-iostat-strace/mini-project/README.md`](curriculum/week-07-observability-htop-iostat-strace/mini-project/README.md) |
| Every destructive command is paired with its rollback, written down before the command is run, under a standing caution section | both | [`curriculum/week-03-permissions-users-groups/README.md`](curriculum/week-03-permissions-users-groups/README.md) |
| Each week names the exact distro and tool versions its output was captured on, and a cheat sheet for where the two distro families diverge | industry | [`curriculum/week-04-shell-scripting-properly/resources.md`](curriculum/week-04-shell-scripting-properly/resources.md) |

**Gaps we declare.** Against the system administration outcome set, none. Against an operating systems course, C14 stops at the operator's side: you measure scheduling, paging, writeback and filesystem behaviour on a running machine, but you do not implement a scheduler, a pager or a filesystem — that half is the ledger's `stillToAdd` and this course does not claim it. Against a systems programming course, the C-language half — pointers, manual memory, and building against the OS in C — is not taught here. C14 also has no hosted-CI unit; that belongs to [C15 · Crunch DevOps](../C15-CRUNCH-DEVOPS/).

---

## Pathway summary

- **Full-time:** 8 weeks · ~36 hrs/week · ~288 hours
- **Working-engineer pace:** 4 months · ~18 hrs/week
- **Evening pace:** 8 months · ~9 hrs/week

See [`SYLLABUS.md`](SYLLABUS.md).

---

## What you will be able to do at the end of 8 weeks

- **Live in a terminal** for a workday without keyboard-shortcut anxiety.
- **Navigate, search, edit, and pipe** like an engineer: `find`, `grep`, `awk`, `sed`, `xargs`, `cut`, `sort`, `uniq`, `tee`.
- **Read process / system state** with `ps`, `top` / `htop`, `lsof`, `strace`, `journalctl`, `dmesg`.
- **Manage packages** on Debian-family (`apt`) and Red Hat-family (`dnf`) systems.
- **Understand the filesystem hierarchy** — `/etc`, `/var`, `/usr`, `/proc`, `/sys` — and what lives where.
- **Write a useful shell script** with proper quoting, error handling, and `set -euo pipefail` discipline.
- **Manage users, groups, permissions, and ACLs** without breaking your machine.
- **Run a server:** `ssh` hardening, key auth, `systemd` units, log rotation, firewall.
- **Recover from "I broke my machine"** without reinstalling from scratch.
- **Diagnose a slow / hung system** with the *four pillars*: CPU, memory, disk, network.

---

## Who this is for

- **C1 graduate** preparing for any of C6, C7, or C15.
- **Self-taught developer** who's been "getting by" on macOS / Windows and wants real Linux comfort.
- **CS / engineering learner** for whom Linux fluency is an unfair career advantage.
- **Working engineer** who knows bits but never learned the system holistically.

Not for: pure beginners with no code background (do [C1](../C1-Code-Crunch-Convos/) first), nor people who specifically want desktop-Linux daily-driver tips (we cover that briefly but it's not the focus).

---

## Prerequisites

- **C1 Weeks 1–4** (basic Python, file IO).
- A computer that can run Linux — natively, in a VM (VirtualBox / UTM / Parallels are fine), or via WSL2 on Windows. We default to Ubuntu LTS but cover Fedora too.
- Patience. Linux rewards repetition.

---

## What you ship

By the end of the 8 weeks, your `crunch-linux-portfolio-<yourhandle>` GitHub repo contains:

1. A **personal dotfiles repo** — `.bashrc` / `.zshrc`, `.vimrc` / `init.lua`, `.gitconfig` (Week 2).
2. A **filesystem-spelunking write-up** answering ten "where does this live?" questions (Week 3).
3. A **set of three useful shell scripts** with proper error handling and `set -euo pipefail` (Week 4).
4. A **systemd-managed service** that you wrote, running locally, with journald logs and graceful restart (Week 5).
5. A **secured SSH config** with key auth, `Fail2Ban`, and disabled password login on a remote VM (Week 6).
6. A **backup-and-restore drill** — you back up your data, intentionally destroy a file, and restore it (Week 7).
7. **Capstone:** a small Linux server you run for a week (a personal homepage, a Pi-hole, a Mastodon instance, your choice), with public uptime monitor and a written 1-page operations runbook (Week 8).

---

## Tools (all free, all open-source)

| Tool | Role |
|------|------|
| **Ubuntu LTS · Fedora Workstation** | The work systems |
| **bash · zsh · fish** *(any modern shell)* | Command line |
| **vim · neovim · nano · VS Code** | Editing |
| **systemd · journald** | Service management |
| **ssh · sshd · Fail2Ban · ufw / nftables / firewalld** | Server-side |
| **rsync · borg · restic** | Backups |
| **tmux · screen** | Terminal multiplexing |
| **htop · btop · iotop · iftop · sysstat** | Observability |
| **git · gh** | Version control |
| **A small VPS ($5/mo)** *(optional)* | The "real server" experience |

A VPS is not required — VMs on your laptop work fine. But the $5/mo experience of "this is a real machine connected to the internet" is pedagogically powerful and we recommend it for Weeks 5–8.

---

## Next track after C14

- **[C6 · Cybersecurity Crunch](../C6-CYBERSECURITY-CRUNCH/)** — security work needs Linux as a foundation.
- **[C7 · Crunch Wire](../C7-WIRE-CRUNCH-EMBEDDED-SYSTEMS/)** — embedded work needs Linux for cross-compilers, debuggers, JTAG bridges.
- **[C15 · Crunch DevOps](../C15-CRUNCH-DEVOPS/)** — DevOps is *operating* Linux at scale.

---

## License

GPL-3.0.

---

*C14 is part of the Code Crunch open-source curriculum.* [Master catalog ↗](../MASTER-CURRICULUM.md) · [Brand family ↗](../../assets/brand/BRAND-FAMILY.md)
