# C14 · Crunch Linux

> A free, open-source **8-week Linux track** for engineers who can write code but feel uncertain in a terminal. From "what shell am I in?" to a small Linux server you run yourself, with systemd services, hardened SSH, and a backup plan you've actually tested. The prerequisite for [C6](../C6-CYBERSECURITY-CRUNCH/), [C7](../C7-WIRE-CRUNCH-EMBEDDED-SYSTEMS/), and [C15](../C15-CRUNCH-DEVOPS/).

[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](LICENSE)
[![Linux · bash · systemd](https://img.shields.io/badge/stack-Linux_·_bash_·_systemd-FACC15.svg)](#stack)
[![Built in the open](https://img.shields.io/badge/built-in%20the%20open-FACC15.svg)](https://github.com/CODECRUNCHWORLDWIDE)

C14 is the shortest specialization track in Tier 1 (8 weeks) because Linux competence is a *foundation* others build on — not a destination. It's deliberately sized to get you ready for C6 (security), C7 (embedded), and C15 (DevOps) without forcing you to take all of those.

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
- **CS / engineering student** for whom Linux fluency is an unfair career advantage.
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


---

<!-- CCWW:AUTO-INDEX:START — generated by scripts/restructure_course_repos.py; edit ABOVE this marker -->

## Course at a glance

| Section | Count |
| --- | --- |
| Curriculum entries | 9 |
| Projects | 0 |
| Past sessions | 1 |

## Curriculum

- [SYLLABUS](curriculum/SYLLABUS.md)
- [week 01 shell and filesystem](curriculum/week-01-shell-and-filesystem/README.md)
- [week 02 text and pipes](curriculum/week-02-text-and-pipes/README.md)
- [week 03 permissions users groups](curriculum/week-03-permissions-users-groups/README.md)
- [week 04 shell scripting properly](curriculum/week-04-shell-scripting-properly/README.md)
- [week 05 systemd services](curriculum/week-05-systemd-services/README.md)
- [week 06 ssh networking firewalls](curriculum/week-06-ssh-networking-firewalls/README.md)
- [week 07 observability htop iostat strace](curriculum/week-07-observability-htop-iostat-strace/README.md)
- [week 08 disks filesystems and page cache](curriculum/week-08-disks-filesystems-and-page-cache/README.md)

## In this course

- **Community** — [community/](community/)
- **Curriculum** — [curriculum/](curriculum/)
- **Projects** — [projects/](projects/)
- **Resources** — [resources/](resources/)
- **Past sessions** — [past-sessions/](past-sessions/)

<!-- CCWW:AUTO-INDEX:END -->
