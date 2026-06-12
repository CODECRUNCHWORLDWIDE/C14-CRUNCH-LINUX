# C14 · Crunch Linux — Syllabus

**8 weeks · ~36 hrs/week intensive (or scaled) · C1 graduate → comfortable Linux user / junior sysadmin**

The Linux foundation for C6, C7, and C15.

---

## Program at a glance

| Phase | Weeks | Outcome |
|-------|-------|---------|
| **Phase 1 — Live in the terminal** | 01 – 02 | Shell, filesystem, pipes |
| **Phase 2 — Scripting & process model** | 03 – 04 | bash discipline, processes, signals |
| **Phase 3 — Services & networking** | 05 – 06 | systemd, SSH, firewall, services |
| **Phase 4 — Operations** | 07 – 08 | Backup, recovery, observability, capstone |

---

## Weekly breakdown

**Week 1 — Shell, filesystem hierarchy, navigation.** What `/etc`, `/var`, `/usr`, `/opt`, `/home`, `/tmp` are for. Symlinks. Mountpoints. The `man` pages.

- *Mini-project:* Map your machine's `/` to a one-page diagram with what's in each directory.

**Week 2 — Text and pipes.** `cat`, `less`, `head`, `tail`, `grep`, `find`, `awk`, `sed`, `xargs`, `cut`, `sort`, `uniq`, `tee`. Composition.

- *Mini-project:* A one-liner pipeline that answers an interesting question about a real log file.

**Week 3 — Permissions, users, groups, ACLs.** `chmod`, `chown`, `umask`, sticky bits, `setuid`. `sudo` and `/etc/sudoers`.

- *Mini-project:* Configure a multi-user demo with appropriate permission boundaries.

**Week 4 — Shell scripting properly.** `set -euo pipefail`. Quoting (the most-missed lesson). `[[ ]]` vs `[ ]`. Functions. Trap signals.

- *Mini-project:* Three scripts: a backup wrapper, a log rotator, and a "where did my disk space go" reporter.

**Week 5 — systemd and services.** Unit files, service / timer / socket types. `journalctl`. Restart policies. Sandboxing options.

- *Mini-project:* A `systemd` service for a small Python web app of your choice with proper restart and journald logging.

**Week 6 — SSH, networking, firewalls.** Key-based auth, agent forwarding, ProxyJump, `~/.ssh/config`. `iptables` / `nftables` / `ufw` / `firewalld`.

- *Mini-project:* Provision a $5/mo VPS or local VM. Harden SSH. Configure firewall. Verify with `nmap`.

**Week 7 — Observability and "why is it slow?"** CPU, memory, disk, network — the four pillars. `htop`, `iostat`, `vmstat`, `ss`, `tcpdump` basics. `strace` and `lsof`.

- *Mini-project:* Diagnose a deliberately slow application using only command-line tooling. Write up the investigation.

**Week 8 — Backup, recovery, capstone.** `rsync`, `borg`, `restic`. The 3-2-1 backup rule. *Restoring* is the only thing that counts. Plus your capstone: a small Linux server running for a week.

- *Capstone:* A small Linux server with a public URL, monitored, with a 1-page runbook and a successful backup-restore drill.

---

## Weekly load

| Component | hrs/wk |
|-----------|------:|
| Lectures / readings | 6 |
| Hands-on exercises | 8 |
| Drills (timed shell challenges) | 4 |
| Quiz | 3 |
| Homework | 6 |
| Mini-project | 7 |
| Self-study | 2 |
| **Total** | **36** |

---

## License

GPL-3.0.
