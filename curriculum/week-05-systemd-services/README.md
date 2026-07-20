# Week 5 — systemd and Services

> *Every script you wrote in Week 4 sat there waiting for you to run it. This week, the machine runs them for you — on a schedule, with a restart policy, with logs you can grep at 03:00, and with sandboxing options that limit how much the script can break when it goes wrong. systemd is not glamorous and not loved, but it is the init system on every mainstream Linux distribution shipping in 2026, and it is the difference between "I ran a script" and "I shipped a service."*

Welcome to **Week 5 of C14 · Crunch Linux**. The first four weeks taught you to live in the shell and write scripts that fail correctly. This week we hand those scripts to **PID 1** and ask it to keep them running. The discipline of writing unit files that boot, restart, log, and sandbox themselves — instead of "my script worked when I tested it."

If Week 4 was `set -euo pipefail` and the double quote, Week 5 is the **`[Unit]` / `[Service]` / `[Install]`** trio, the `journalctl -u name.service` grep, and the `ProtectSystem=strict` line that turns a buggy script into a contained blast radius. Two cheap habits with one heavy tool. We will earn them by writing unit files, breaking them on purpose, watching `journalctl -f` while they crash-loop, and ratcheting the sandbox tighter until the service does its job and nothing else.

## Learning objectives

By the end of this week, you will be able to:

- **Write a `.service` unit file** for a long-running process — pick the right `Type=` (`simple`, `exec`, `forking`, `notify`, `oneshot`), set `ExecStart=` properly, choose a `Restart=` policy, and explain what each one does on failure vs success.
- **Write a `.timer` unit file** that replaces a `cron` entry — both `OnCalendar=` (wall-clock) and `OnUnitActiveSec=` (relative) forms — and explain why `Persistent=true` matters for laptops that sleep.
- **Choose** between a system unit (`/etc/systemd/system/`) and a user unit (`~/.config/systemd/user/`) based on whether the workload needs root, network, or only runs while you're logged in. Know what `loginctl enable-linger` does.
- **Read `journalctl` fluently** — filter by unit, time, priority, boot, and follow mode (`-f`). Know the difference between `journalctl -u foo.service` and `journalctl _SYSTEMD_UNIT=foo.service`. Pipe to `grep` without losing structure.
- **Apply sandboxing directives** — `User=`, `Group=`, `DynamicUser=`, `ProtectSystem=`, `ProtectHome=`, `PrivateTmp=`, `NoNewPrivileges=`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=` — and explain what each one prevents.
- **Recognize** the unit-file mistakes the freedesktop.org docs warn about: `Type=simple` with a forking process, `Restart=always` with a config error (the crash-loop), missing `WantedBy=`, `ExecStart=` with a shell builtin, the absolute-path requirement, the `%` specifier escapes.
- **Compose** a multi-instance template unit (`name@.service`) with `%i` / `%I` specifiers, and instantiate it with `systemctl start name@one.service name@two.service`.
- **Reach** for `systemd-analyze verify`, `systemd-analyze security`, `systemctl status`, `systemctl cat`, and `systemctl show` when something doesn't behave.

## Prerequisites

- **Weeks 1, 2, 3, and 4 of C14** completed. You can navigate, pipe, reason about permissions, and write a script that fails correctly with `set -euo pipefail`.
- A working Ubuntu 24.04 LTS or Fedora 41 environment. This week we target **systemd 255 or newer** (Ubuntu 24.04 ships 255.4; Fedora 41 ships 256.7). Older systemd has fewer sandboxing directives and a different `systemd-analyze security` output — the differences matter.
- Root access via `sudo`. Some exercises edit `/etc/systemd/system/` and run `systemctl daemon-reload`. User units in `~/.config/systemd/user/` need no root, and we use them where we can.
- A scratch directory and a snapshot. As with Week 4, several exercises produce units that crash-loop or fail on purpose. Confirm you can revert with `sudo systemctl disable --now bad.service && sudo rm /etc/systemd/system/bad.service && sudo systemctl daemon-reload` before you start.

## Topics covered

- **systemd anatomy:** PID 1 as a process supervisor, target units (`multi-user.target`, `graphical.target`, `default.target`), the boot sequence, and the `systemctl` verbs (`start`, `stop`, `restart`, `reload`, `enable`, `disable`, `mask`, `unmask`, `cat`, `edit`, `show`, `status`, `list-units`, `list-unit-files`).
- **The three sections** of a unit file: `[Unit]` (metadata, dependencies, ordering), `[Service]` (the process itself), `[Install]` (what happens on `enable`). The `WantedBy=multi-user.target` line and why it matters.
- **`Type=` values:** `simple` (the default — `ExecStart=` is the service), `exec` (like simple but waits for `execve()` to succeed), `forking` (the old SysV daemon pattern; rare in new code), `notify` (the service calls `sd_notify(3)` to signal readiness), `oneshot` (a one-shot command, often paired with a timer), `idle` (delayed start, useful for boot ordering).
- **`Restart=` policies:** `no`, `on-success`, `on-failure`, `on-abnormal`, `on-watchdog`, `on-abort`, `always`. The `RestartSec=`, `StartLimitIntervalSec=`, `StartLimitBurst=` knobs that prevent crash-looping forever.
- **`.timer` units:** wall-clock (`OnCalendar=daily`, `OnCalendar=*-*-* 03:00:00`) versus monotonic (`OnUnitActiveSec=1h`, `OnBootSec=15m`). The `Persistent=true` directive that catches missed runs after sleep. Why systemd timers are strictly more powerful than `cron`.
- **`.socket` units:** socket activation. Why systemd can listen on a port and only start the service when a client connects. The `Sockets=` and `Accept=` directives. Briefly — we don't go deep on this in Week 5.
- **`journalctl`:** the journal is structured (key=value records, not lines). `-u UNIT`, `-p PRIORITY`, `--since`/`--until`, `--boot`, `-f` (follow), `-o json-pretty`, `--no-pager`, `-n N` (last N entries). The `_SYSTEMD_UNIT=` field for child processes. Persistent vs volatile storage (`/var/log/journal/` vs `/run/log/journal/`).
- **Sandboxing directives:** the "Service Settings" page on freedesktop.org lists roughly 80 options that restrict what a service can do. We focus on the eight that catch the most: `User=`, `DynamicUser=`, `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`, `NoNewPrivileges=true`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=`.
- **Template units:** `name@.service`. The `%i` specifier (unescaped instance name), `%I` (escaped), and the rest of the specifier zoo (`%n`, `%N`, `%u`, `%h`, `%U`, `%t`). One unit file, N instances.
- **Drop-ins:** `systemctl edit foo.service` creates `/etc/systemd/system/foo.service.d/override.conf`. Why drop-ins are the polite way to override a vendor unit you don't own.
- **Validation:** `systemd-analyze verify foo.service` catches syntax errors and missing references before reload. `systemd-analyze security foo.service` scores your sandboxing on a 0-10 scale (lower is better). Both are required reading before you ship a unit.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Unit files: `[Unit]`/`[Service]`/`[Install]`, `Type=`, `Restart=`. Lecture 1. |    3h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Tuesday   | Timers and sockets. Exercise 1 (first unit), exercise 2 (cron → timer). |    1h    |    3h     |     0.5h   |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Wednesday | `journalctl` + sandboxing. Lecture 2.              |    2h    |    2h     |     0.5h   |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Thursday  | Exercise 3 (sandbox a service); design mini-proj.  |    0h    |    2h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Template units challenge; polish homework.         |    0h    |    0.5h   |     1.5h   |    0.5h   |   2h     |     1h       |    0h      |     5.5h    |
| Saturday  | Mini-project — systemd-managed Python web service. |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                                  |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                                    | **6h**   | **9.5h**  | **3.5h**   | **3h**    | **6h**   | **7h**       | **1h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | systemd man pages, freedesktop.org documentation, books, and the references we cite |
| [lecture-notes/01-unit-files-services-timers-sockets.md](./lecture-notes/01-unit-files-services-timers-sockets.md) | Unit-file anatomy, `Type=`, `Restart=`, timers, sockets |
| [lecture-notes/02-journalctl-and-the-sandboxing-options.md](./lecture-notes/02-journalctl-and-the-sandboxing-options.md) | `journalctl` end-to-end, the eight sandboxing directives, `systemd-analyze` |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-first-unit-file.md](./exercises/exercise-01-first-unit-file.md) | Write your first `.service` unit, enable it, watch it restart |
| [exercises/exercise-02-timer-instead-of-cron.md](./exercises/exercise-02-timer-instead-of-cron.md) | Replace a `cron` job with a `.timer` + `.service` pair |
| [exercises/exercise-03-sandbox-a-service.md](./exercises/exercise-03-sandbox-a-service.md) | Take a wide-open service and ratchet `systemd-analyze security` from 9.6 toward 1.0 |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-multi-instance-template-units.md](./challenges/challenge-01-multi-instance-template-units.md) | One template unit (`worker@.service`), N instances, all parametric |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | A `systemd`-managed Python web app with restart policy, journald logging, and a non-trivial sandbox |

## A note on which systemd

systemd is not a stable target. Between version 240 (Ubuntu 20.04) and version 256 (Fedora 41), roughly thirty sandboxing directives were added, the `DynamicUser=` semantics tightened, and the `systemd-analyze security` output gained the "exposure level" score. This week's content is written against **systemd 255+** and notes the version each directive landed in.

```bash
# Which systemd?
systemctl --version | head -1
# Ubuntu 24.04 LTS:    systemd 255 (255.4-1ubuntu8.4)
# Fedora 41:           systemd 256 (256.7-1.fc41)

# Which features are available?
systemd-analyze --version | head -1
```

If you're on macOS, **macOS does not run systemd at all** — it uses `launchd`, which is conceptually similar but has none of the same syntax. Do this week's work inside a Linux VM (UTM, Parallels, VirtualBox) or a remote VPS. `systemd` running inside a Docker container is possible but awkward; stick to a real Linux environment for Week 5.

If you're on WSL2, run `systemctl --version` first. WSL2 enabled systemd by default in late 2022 (Microsoft + Canonical announcement, September 2022), but only for distros configured with `systemd=true` in `/etc/wsl.conf`. Without that, `systemctl` will fail in ways that look like "systemd is broken" but are actually "systemd was never PID 1 in this container." Fix it in `/etc/wsl.conf` and restart WSL before proceeding.

## Stretch goals

- Read the **freedesktop.org systemd manual pages** end to end — at minimum `systemd.unit(5)`, `systemd.service(5)`, `systemd.timer(5)`, `systemd.exec(5)`, and `systemd.resource-control(5)`. They are the textbook this week is structured around: <https://www.freedesktop.org/software/systemd/man/>
- Read **Lennart Poettering's "systemd for Administrators"** blog series (the original 2010-2013 essays, 14 parts). Dated in places, but the explanation of socket activation in part III is still the clearest write-up in print: <http://0pointer.de/blog/projects/systemd-for-admins-1.html>
- Read the **`systemd.exec(5)` man page** from `SANDBOXING` to the end. It documents every sandbox directive, with a one-paragraph rationale each. Roughly 60 directives as of systemd 256. Skim once; come back when you need a specific one.
- Run `systemd-analyze security` against every service running on your machine. Score the worst offenders. (`sshd.service` is intentionally permissive; `systemd-timesyncd.service` is a good example of a tight one.)

## Bash Yellow caution

This week contains commands that can:

- Brick your boot by writing a unit with a syntax error and `enable`-ing it into `multi-user.target` (always run `systemd-analyze verify foo.service` before reload).
- Lock you out of a service by `mask`-ing the wrong unit (`systemctl mask sshd.service` is irreversible until you `unmask` from a recovery console).
- Fill `/var/log/journal/` and exhaust disk space (the default `SystemMaxUse=` is 10% of the filesystem; on a 20GB VM that's 2GB of logs).
- Crash-loop a service indefinitely if you set `Restart=always` and the service exits with code 0 immediately — systemd happily restarts it forever, burning CPU.

Every lecture and exercise that runs destructive code uses a scratch directory, a `~/.config/systemd/user/` unit where possible, and a Bash Yellow warning. Snapshot before you start. The line is: **wrong type, wrong restart, wrong sandbox, wrong target** — every footgun this week reduces to one of those four.

## Up next

[Week 6 — SSH, networking, firewalls](../week-06/) — when the systemd service you wrote this week needs to be reachable from the internet, and the only thing standing between it and the world is your `sshd_config` and your firewall rules.

---

*If you find errors, please open an issue or PR.*
