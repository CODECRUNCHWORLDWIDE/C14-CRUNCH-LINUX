# Capstone — Run a Real Linux Server for Seven Days

> The C14 capstone is the graduation criterion for the whole track: you provision
> a Linux server from a fresh image, harden it, observe it, survive a week of the
> open internet probing it, and write the runbook and postmortem a real operator
> would hand to the next person on call. Everything in eight weeks points here.

This file is the single source of truth for what the capstone is, how it is graded,
and what you submit. The day-by-day schedule that runs the capstone in the
background of the final week lives in the curriculum:
[`curriculum/week-08-disks-filesystems-and-page-cache`](../../curriculum/week-08-disks-filesystems-and-page-cache/00-overview.md).

You are not building a toy. By the end you have a machine that has been up for a
week, answered real traffic, fended off real port scanners, and left a paper trail
you can read. That is the difference between a Linux *user* and a junior Linux
*engineer* — and it is the whole point of C14.

---

## What you deliver

A **public GitHub repository** — your `crunch-linux-portfolio-<yourhandle>` repo,
the same one you have been filling since Week 2 — with a `capstone/` directory
containing:

1. **A live (or recently-live) Linux server** that ran for **seven calendar days**
   serving a real service of your choice: a personal homepage on nginx, a
   [Pi-hole](https://pi-hole.net/), an [Uptime Kuma](https://github.com/louislam/uptime-kuma)
   status page, a small Flask app behind a `systemd` unit — your pick, as long as
   it is a service you can reach and watch.
2. **A one-page operations runbook** (`runbook.md`) — the document the next operator
   reads at 3 a.m.: what the box runs, how to reach it, where the logs are, how to
   restart the service, how to restore from backup, and the two or three things
   most likely to go wrong.
3. **A seven-day postmortem** (`postmortem.md`) — what you provisioned, what you
   hardened, what the internet did to you (you *will* be port-scanned within
   minutes of going live), what broke, what you measured, and what you tuned.
4. **The artifacts that prove it**: your hardened `sshd_config` (redact nothing
   secret — there are no secrets in a hardened config), your `nftables.conf` (or
   `ufw` rules), your `systemd` unit, your backup script, and the `nmap` output
   from *outside* the box proving only the ports you meant are open.

Free and open-source the whole way. A local VM (UTM, Multipass, VirtualBox, WSL2)
is a fully valid "server." The optional **$5/mo VPS** gives you the genuine
"this machine is on the public internet right now" experience, which is
pedagogically worth it — but it is never required to pass.

---

## At a glance

| Aspect | Detail |
| --- | --- |
| **Deliverable** | A hardened Linux server run for 7 days, plus its runbook and postmortem, in a public GitHub repo |
| **Format** | A `capstone/` directory: `runbook.md`, `postmortem.md`, and the config artifacts (`sshd_config`, firewall rules, `systemd` unit, backup script, `nmap` output) |
| **Submission** | Repo URL + the public URL (or screenshots) of your service + a short walkthrough (written or a 3–5 min screen recording) |
| **Audience** | Yourself first; then future employers, your C6/C7/C15 cohort, and the open-source community reading "in the open" |

---

## How this ties to the course

The capstone is a synthesis exercise — it does not teach a new tool, it makes you
*combine* the tools from the second half of C14 into one operational story:

| You use | From | For |
| --- | --- | --- |
| `systemd` units, `journalctl`, restart policies | [Week 5 — systemd and services](../../curriculum/week-05-systemd-services/00-overview.md) | Running your service so it survives a reboot and logs to the journal |
| Key-only SSH, `sshd_config` hardening, `nftables`/`ufw`, `Fail2Ban`, `nmap` verification | [Week 6 — SSH, networking, firewalls](../../curriculum/week-06-ssh-networking-firewalls/00-overview.md) | Locking the box down and *proving* the locks took from outside |
| The USE method, `htop`, `iostat`, `vmstat`, `ss`, `strace`, reading `/proc` | [Week 7 — Observability](../../curriculum/week-07-observability-htop-iostat-strace/00-overview.md) | Watching the box for a week and writing measured, not guessed, conclusions |
| Disks, `/etc/fstab`, the page cache, `fio`, `smartctl`, `rsync`/`borg`/`restic`, the 3-2-1 rule | [Week 8 — Disks, filesystems, and the page cache](../../curriculum/week-08-disks-filesystems-and-page-cache/00-overview.md) | Provisioning storage, tuning mount options, and proving a *restore* works |

The day-by-day plan that drives the seven days — provision Monday, TLS Tuesday,
logging and `Fail2Ban` Wednesday, monitoring Thursday, watch-and-tune Friday,
induce load Saturday, write the postmortem Sunday — lives in the
[Week 8 overview](../../curriculum/week-08-disks-filesystems-and-page-cache/00-overview.md)
and its [mini-project](../../curriculum/week-08-disks-filesystems-and-page-cache/07-mini-project/00-overview.md).

---

## Milestones

Run these in order. Each one is a checkpoint you can commit and push, so your repo
tells the story as it happens — learn in the open.

1. **Provision (Day 1).** Stand up a fresh Ubuntu 24.04 LTS or Fedora 41 image on a
   VM or VPS. Create a non-root user with `sudo`. Confirm you can reach it. Commit a
   note on what you chose and why.
2. **Harden (Days 1–2).** Key-only SSH (`PasswordAuthentication no`,
   `PermitRootLogin no`), a default-drop firewall that accepts only the ports your
   service needs, `Fail2Ban`, and unattended security upgrades. **Keep a second SSH
   session open** while you change `sshd_config` or firewall rules — locking yourself
   out is the classic Week 6 footgun.
3. **Serve (Day 2).** Install your service and put it behind a `systemd` unit with a
   restart policy. Add TLS if it is internet-facing (Let's Encrypt via `certbot` is
   free). Confirm it survives `systemctl restart` *and* a full reboot.
4. **Prove the locks (Day 2).** Run `nmap -sV` against the box **from another
   machine**. Save the output. Only the ports you meant should be `open`; everything
   else `filtered`. If a port you did not expect is open, fix it before continuing.
5. **Observe (Days 3–5).** Stand up monitoring — [Uptime Kuma](https://github.com/louislam/uptime-kuma),
   a `systemd` timer that logs `vmstat`/`iostat`/`free` snapshots, or both. Read the
   journal daily. Note what the port scanners and SSH brute-forcers are doing in
   `/var/log/auth.log`.
6. **Back up and *restore* (Day 5).** Back up your data with `rsync`, `borg`, or
   `restic` following the 3-2-1 rule. Then **intentionally destroy a file and restore
   it.** A backup you have never restored is a rumor — the restore is the deliverable.
7. **Stress and watch (Day 6).** Induce a small, deliberate load with `stress-ng`,
   `fio`, or real traffic. Use the USE method to find which of the four pillars (CPU,
   memory, disk, network) moves first. Record the numbers, not your guesses.
8. **Write it up (Day 7).** Finish `runbook.md` and `postmortem.md`. Record the short
   walkthrough. Tag a release. Open an issue on your own repo listing the next three
   things you would improve — that issue is a hiring signal.

---

## Grading rubric

100 points. A passing capstone is **70+**; a portfolio-grade one is **90+**.

| Area | Points | What "full marks" looks like |
| --- | ---: | --- |
| **Provisioning & service** | 15 | A real service runs under `systemd` with a restart policy, survives a reboot, and is reachable at a URL (or documented local address). |
| **Hardening** | 20 | Key-only SSH, root login disabled, default-drop firewall, `Fail2Ban`, unattended upgrades — and `nmap` output from outside that *proves* only the intended ports are open. |
| **Observability** | 15 | Monitoring is in place; the postmortem cites real numbers from `htop`/`iostat`/`vmstat`/`ss`/`journalctl`, and reasons with the USE method rather than guessing. |
| **Storage & backup** | 15 | Sensible `/etc/fstab` mount options, a 3-2-1 backup, and — the hard requirement — a **documented, successful restore** of a destroyed file. |
| **The runbook** | 15 | One page, skimmable under pressure: service, access, logs, restart, restore, and the top failure modes. Someone who is not you could operate the box from it. |
| **The postmortem** | 15 | Seven days narrated honestly: what you built, what the internet did, what broke, what you measured, what you tuned. Includes what you would do differently. |
| **Open-in-the-open craft** | 5 | Commit history tells the story, the README orients a stranger, links work, and tone is honest about what went wrong. |

**Honesty bonus, not penalty:** "I locked myself out of SSH on Tuesday and
recovered through the provider console" is a *stronger* postmortem than one where
nothing went wrong. Operators are made by recoveries. Write down the recovery.

---

## Ground rules

- **Free and open-source only.** Every tool in this capstone ships in Ubuntu's and
  Fedora's default repositories. No paid tier is required to earn full marks.
- **No secrets in the repo.** A hardened `sshd_config` and `nftables.conf` contain no
  secrets and *should* be committed. Private keys, passwords, and API tokens must
  never be. If you used a VPS, it is fine to redact its public IP.
- **The restore is non-negotiable.** A backup you never restored does not count. Half
  the storage points hang on the restore drill.
- **`nmap` from outside, always.** A scan run *on* the box proves nothing. Run it from
  a second machine, your laptop, or a friend's host.
- **Measure before you conclude.** Every performance claim in the postmortem needs a
  number behind it. "It felt slow" is not a finding; `aqu-sz` pegged at 12 with
  `%wa` at 40 is.

---

## After the capstone

A finished C14 capstone is the on-ramp to the tracks that build on Linux:

- **[C6 · Cybersecurity Crunch](../../../C6-CYBERSECURITY-CRUNCH/)** — security work
  starts from exactly this: a box you can harden and reason about.
- **[C7 · Crunch Wire](../../../C7-WIRE-CRUNCH-EMBEDDED-SYSTEMS/)** — embedded and
  networking depth, on top of a Linux foundation.
- **[C15 · Crunch DevOps](../../../C15-CRUNCH-DEVOPS/)** — DevOps is *operating* Linux
  at scale; the runbook you just wrote is the first of many.

---

*Part of [C14 · Crunch Linux](../../00-overview.md), in the Code Crunch Worldwide
open-source curriculum. If you find errors, please open an issue or PR.*
