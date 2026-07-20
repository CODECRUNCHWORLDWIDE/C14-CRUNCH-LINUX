# Week 5 — Resources

Free, public, no signup unless noted. The freedesktop.org man pages and the `systemd-analyze` output are the two references you will bookmark this week.

## Required reading

- **`systemd.unit(5)`** — the canonical reference on the `[Unit]`, `[Install]` sections and the directives that live there. Read sections "OPTIONS", "[UNIT] SECTION OPTIONS", and "[INSTALL] SECTION OPTIONS":
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html>
- **`systemd.service(5)`** — the `[Service]` section. The `Type=`, `Restart=`, `ExecStart=`, `ExecStartPre=`, `ExecReload=`, `ExecStop=` directives. The `KillMode=`, `KillSignal=`, `TimeoutStopSec=` knobs. Read end to end:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html>
- **`systemd.timer(5)`** — wall-clock and monotonic timers. The `OnCalendar=`, `OnBootSec=`, `OnUnitActiveSec=`, `Persistent=`, `RandomizedDelaySec=` directives. Pair with the calendar-spec page below:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html>
- **`systemd.time(7)`** — the calendar-spec format used by `OnCalendar=`. The "CALENDAR EVENTS" section is the only thing in print that documents `*-*-* 03:00:00` style syntax precisely:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html>
- **`systemd.exec(5)`** — the sandboxing directives. The "SANDBOXING" section lists `ProtectSystem=`, `ProtectHome=`, `PrivateTmp=`, `PrivateDevices=`, `NoNewPrivileges=`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=`, and roughly sixty more. The longest man page on a typical Linux system; read it once front-to-back, then keep it open for reference:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html>
- **`journalctl(1)`** — every flag, with example invocations. The "EXAMPLES" section at the bottom is where the high-leverage one-liners live:
  <https://www.freedesktop.org/software/systemd/man/latest/journalctl.html>
- **`systemd.socket(5)`** — socket-activated services. Read once; come back when you build one:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd.socket.html>

## Books

- **"systemd for Administrators" — Lennart Poettering (blog series, 2010-2013)** — fourteen essays by systemd's principal author. The 2010 framing is dated (target audience: skeptical sysadmins migrating from SysV), but the conceptual explanations of socket activation (part III), service supervision (part II), and the journal (parts VIII-X) remain the clearest in print. Free online: <http://0pointer.de/blog/projects/systemd-for-admins-1.html>
- **"The systemd Book" — Werner Heuser, et al. (open community book, current edition 2024)** — community-maintained book, hosted on GitHub. Less polished than a printed text but kept up to date with current systemd. Good for the long tail of edge cases: <https://github.com/dosbox-staging/systemd-book> (community fork; the canonical home moves occasionally — search "systemd book Heuser" if the link is stale)
- **"Linux Service Management Made Easy with systemd" — Donald A. Tevault (Packt, 2022)** — readable introductory text. Covers the same ground as this week with more screenshots and a slower pace. Useful as a complement, not a replacement.
- **"How Linux Works" — Brian Ward (3rd ed., No Starch Press, 2021)** — chapter 6 ("How the Linux Kernel Boots") and chapter 17 ("Booting"). The pre-systemd context (SysV init, Upstart) and the systemd takeover. Useful for understanding why systemd exists, not just how to use it.

## Cheat sheets

- **DigitalOcean — "Understanding Systemd Units and Unit Files"** — long, careful walkthrough of every section of a unit file with worked examples. The canonical tutorial people link to:
  <https://www.digitalocean.com/community/tutorials/understanding-systemd-units-and-unit-files>
- **Arch Wiki — "systemd"** — the Arch wiki is the densest English-language reference on systemd usage. The "Editing provided units" and "Drop-in files" sections are especially useful:
  <https://wiki.archlinux.org/title/Systemd>
- **Arch Wiki — "systemd/Timers"** — a focused page on timer units with example calendar specs and the common gotchas (timezone, `Persistent=`, monotonic vs realtime):
  <https://wiki.archlinux.org/title/Systemd/Timers>
- **Arch Wiki — "systemd/User"** — user-mode systemd. `loginctl enable-linger`, `XDG_RUNTIME_DIR`, and the per-user instance of `systemd`:
  <https://wiki.archlinux.org/title/Systemd/User>
- **`systemd-analyze security` walkthrough — freedesktop.org** — the man page (`systemd-analyze(1)`) documents the security-score command. The "exposure level" 0-10 scale and what each band means:
  <https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html>
- **Red Hat — "Managing systemd unit files"** — Red Hat's docs on creating, modifying, and overriding unit files. Useful if your target distro is RHEL / Fedora / Rocky:
  <https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/managing_systemd>

## Tools and websites

- **`systemd-analyze`** — the systemd swiss-army knife. `verify FILE` parses a unit file and reports problems. `security UNIT` scores its sandbox. `blame` lists the slowest units at boot. `cat-config` dumps the resolved configuration of any systemd component. Comes with systemd; no install needed.
- **`systemctl cat UNIT`** — prints the unit file and all drop-ins, in the order systemd reads them. The single most useful debugging command when "I edited the unit and nothing changed."
- **`systemctl show UNIT`** — dumps every resolved property of a unit, including defaults. Roughly 200 lines of output per service. Pipe to `grep` to find the one you care about: `systemctl show foo.service | grep -i restart`.
- **`journalctl --grep PATTERN`** — full-text search across the journal. Since systemd 237, supports `-i` for case-insensitive. Faster than `journalctl | grep` because it filters before pagination.
- **`systemd-cgls`** — a `tree`-style display of the systemd cgroup hierarchy. Shows which processes belong to which unit. Useful when a service forks unexpected children.
- **`systemd-cgtop`** — `top` for cgroups. CPU, memory, IO per unit. The right answer when "which service is eating my CPU" beats `htop` (which shows processes, not units).
- **`busctl`** — D-Bus introspection. Most systemd interactions go over D-Bus; `busctl list` shows every service's bus name. Mostly useful when you're debugging the deeper layers; safe to ignore in Week 5.
- **`coredumpctl`** — the journal also stores core dumps from crashed services (if `Storage=external` in `/etc/systemd/coredump.conf`). `coredumpctl list`, `coredumpctl info`, `coredumpctl gdb` to attach a debugger. Useful when a service segfaults.

## Videos (free)

- **"systemd, 10 years later: a historical and technical retrospective" — Benno Rice, BSDCan 2019** — one of the calmest, most-balanced explanations of why systemd exists, by a *BSD* developer (i.e., somebody with no political stake in the outcome). 45 minutes. The single best video to start with if you've absorbed any of the "systemd is bad" internet folklore: <https://www.youtube.com/watch?v=o_AIw9bGogo>
- **"systemd: the good, the bad, and the ugly" — Bryan Cantrill, Surge 2013** — older, more critical, but a useful counterweight. Cantrill is a former Solaris engineer; his complaints about systemd's API surface area are technically grounded:
  <https://www.youtube.com/watch?v=o_AIw9bGogo> (the conference archives drift; search "Cantrill systemd Surge")
- **"Modern Linux Initialization with systemd" — Greg Kroah-Hartman, LinuxCon 2014** — kernel maintainer's perspective. Useful for boot-sequence details:
  <https://www.youtube.com/results?search_query=kroah-hartman+systemd>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install systemd systemd-coredump systemd-container
# Most distros have these installed already; the install line is a no-op on Ubuntu 24.04.

# Fedora
sudo dnf install systemd systemd-coredump systemd-container
# Same on Fedora; verify with rpm -q systemd.
```

- `systemd` — assume installed. Confirm `systemctl --version` shows 255 or newer.
- `systemd-coredump` — captures core dumps from crashing services into the journal. Worth installing even if you never debug a crash; the day you do, you'll be grateful.
- `systemd-container` (which provides `machinectl`, `systemd-nspawn`) — not used in Week 5, but useful in later weeks for sandbox testing. Install once.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| systemd version | 255.4 | 256.7 |
| System unit dir | `/etc/systemd/system/` (admin) · `/lib/systemd/system/` (vendor) | `/etc/systemd/system/` (admin) · `/usr/lib/systemd/system/` (vendor) |
| User unit dir | `~/.config/systemd/user/` (user) · `/etc/systemd/user/` (admin) | same |
| Default journal storage | `auto` (uses persistent if `/var/log/journal/` exists, volatile otherwise) | `persistent` (writes `/var/log/journal/` unconditionally) |
| `journalctl` default page size | `less` with `--no-init` | `less` with `--no-init` |
| `systemd-resolved` enabled by default | yes | yes |
| `systemd-timesyncd` enabled by default | yes (NTP via systemd) | no (Fedora uses `chrony` instead) |
| `loginctl enable-linger` available | yes | yes |
| `DynamicUser=` available | yes (since systemd 232) | yes |

The vendor-unit-dir divergence is the one that bites first. Debian and Ubuntu put vendor units in `/lib/systemd/system/`. Red Hat and Fedora put them in `/usr/lib/systemd/system/`. Always **edit in `/etc/systemd/system/`** (which is the same on both) and let systemd's lookup-order resolve the precedence. `systemctl cat foo.service` shows you which copy is actually winning.

The Ubuntu-vs-Fedora journal default also bites. On Ubuntu, journal logs vanish on reboot unless you `sudo mkdir /var/log/journal && sudo systemctl restart systemd-journald`. On Fedora, they persist by default. If your homework relies on `journalctl --boot=-1`, you need persistent journals first.

## Free books and write-ups

- **"Use systemd" — Mahmud Ridwan, on DigitalOcean** — a tutorial series that walks through unit-file creation, timers, sockets, and `journalctl`. Free, fully indexed, and the search-result you'll keep landing on:
  <https://www.digitalocean.com/community/tutorial-collections/getting-started-with-systemd>
- **"Systemd by example" — Jordi Mallach** — short, opinionated, example-driven. The "service with restart policy" example is the cleanest small reference I know of:
  <https://systemd-by-example.com/>
- **"Sandboxing your services with systemd" — Christian Brauner** — the kernel-developer's-eye view of what each sandbox directive actually does at the syscall level. Goes deeper than the man page on `RestrictAddressFamilies=` and `SystemCallFilter=`:
  <https://www.youtube.com/results?search_query=brauner+systemd+sandboxing>
- **freedesktop.org — "The Boot Process" page** — the canonical reference on how systemd takes over from the kernel. Required if Week 5 leaves you wondering "but who starts systemd itself":
  <https://www.freedesktop.org/software/systemd/man/latest/bootup.html>

## systemd directives you will see this week

A quick reference. Every directive links to its man page; we will not duplicate the man pages here.

| Directive | Section | Meaning |
|-----------|---------|---------|
| `Description=` | `[Unit]` | One-line human description shown in `systemctl status`. |
| `After=` / `Before=` | `[Unit]` | Ordering, not dependency. "Start after X" doesn't pull X in. |
| `Wants=` / `Requires=` | `[Unit]` | Dependency. `Requires=` is strict (fail if X fails); `Wants=` is soft. |
| `Type=` | `[Service]` | How systemd judges "the service started." `simple`, `exec`, `forking`, `notify`, `oneshot`. |
| `ExecStart=` | `[Service]` | Absolute path to the binary. Must be absolute. |
| `ExecStartPre=` | `[Service]` | Commands run before `ExecStart=`. `-` prefix means "ignore failure." |
| `Restart=` | `[Service]` | `no`, `on-failure`, `always`. The crash-loop knob. |
| `RestartSec=` | `[Service]` | Delay between restarts. Default `100ms`. Set to `1s+` in production. |
| `User=` / `Group=` | `[Service]` | Drop privileges to this user/group. |
| `DynamicUser=true` | `[Service]` | systemd invents a transient user for the service. Strongest isolation. |
| `ProtectSystem=` | `[Service]` | `full`, `strict`, `true`. Read-only `/usr`, `/boot`, `/etc`. |
| `ProtectHome=` | `[Service]` | `true`, `read-only`, `tmpfs`. Hide `/home`. |
| `PrivateTmp=true` | `[Service]` | Private `/tmp` and `/var/tmp` namespaced to this service. |
| `NoNewPrivileges=true` | `[Service]` | `no_new_privs` bit. Setuid binaries cannot escalate. |
| `WantedBy=` | `[Install]` | The target that pulls this unit in on `enable`. Usually `multi-user.target`. |
| `OnCalendar=` | `[Timer]` | Wall-clock schedule. `daily`, `weekly`, `*-*-* 03:00:00`. |
| `Persistent=true` | `[Timer]` | Catches missed runs after sleep / power-off. |

These are the fifteen you will encounter most. The man pages have the rest.

## Glossary

| Term | Definition |
|------|------------|
| **Unit** | A systemd-managed entity. Eleven kinds: `.service`, `.timer`, `.socket`, `.target`, `.mount`, `.automount`, `.swap`, `.path`, `.scope`, `.slice`, `.device`. |
| **Target** | A grouping unit (like SysV runlevels). `multi-user.target` is the non-graphical login state; `graphical.target` adds the display manager. |
| **PID 1** | The first userspace process; the kernel starts it after kernel init. On every mainstream Linux distribution in 2026, PID 1 is `systemd`. |
| **`systemctl`** | The CLI for managing units. `start`, `stop`, `enable`, `disable`, `cat`, `status`, `show`. |
| **`journalctl`** | The CLI for reading the systemd journal. Structured logs; filter by unit, priority, time, boot. |
| **Drop-in** | A file in `UNIT.d/` that overrides directives in a vendor unit. `systemctl edit UNIT` creates one. The polite way to modify a unit you don't own. |
| **Specifier** | A `%`-prefixed letter inside a unit file that expands at load time. `%i` (instance), `%n` (unit name), `%h` (user home), `%t` (runtime dir). |
| **Template unit** | A unit named `foo@.service`. Instantiate with `systemctl start foo@one.service`. The `%i` in the template becomes `one`. |
| **Socket activation** | systemd creates the listening socket itself, only starts the service when a client connects. Like `inetd`, but with `fork()`-less handoff. |
| **`sd_notify(3)`** | The C API a `Type=notify` service uses to tell systemd "I'm ready" or "I'm reloading." A `READY=1` line over a Unix socket. |
| **Linger** | The state in which `systemd --user` keeps running after the user logs out. Enabled with `loginctl enable-linger USER`. |
| **`DynamicUser=`** | A directive that asks systemd to invent a transient user for the service. The UID is allocated from a dedicated range (61184-65519) and freed on stop. |
| **`ProtectSystem=`** | A sandbox directive that remounts `/usr`, `/boot`, `/etc` read-only. Three levels: `true`, `full`, `strict`. |
| **Exposure level** | The 0-10 score from `systemd-analyze security`. 0 is "ideal", 10 is "unsafe". Most vendor services land between 6 and 9. |

---

*Broken link? Open an issue.*
