# Lecture 2 — `journalctl` and the Sandboxing Options

> **Duration:** ~2 hours. **Outcome:** You read `journalctl` output fluently — by unit, by priority, by time, by boot. You apply the eight sandboxing directives that catch the most attack surface for the least operational pain. You run `systemd-analyze security` against your own services and ratchet the exposure score down by editing the unit file.

The service you wrote in Lecture 1 works. It also runs as root, can write to every file on the system, can open any network socket, and can call any of the ~360 syscalls Linux offers. None of that is necessary for almost any service you will ever write. This lecture is about (a) reading the logs your service produces, and (b) reducing the blast radius of the service before it goes wrong.

Read at the keyboard. The `journalctl` invocations all work against your own machine; the sandbox directives are testable with `systemd-analyze verify`.

## 1. The journal — what systemd does with stdout

When your service writes to stdout or stderr, systemd captures it. By default it goes to **the journal** — a structured, binary log database managed by `systemd-journald`. The journal stores key-value records, not lines: each entry has a `MESSAGE=` field plus dozens of metadata fields (`_PID`, `_UID`, `_COMM`, `_SYSTEMD_UNIT`, `PRIORITY`, `_BOOT_ID`, and more).

The CLI for reading the journal is `journalctl`. Running it with no arguments dumps every entry on the system from oldest to newest — which is rarely what you want. Every useful invocation has at least one filter.

### 1.1 Filter by unit

```bash
# All log entries for my-service.service
journalctl -u my-service.service

# Last 50 entries
journalctl -u my-service.service -n 50

# Follow new entries (like tail -f)
journalctl -u my-service.service -f

# Reverse order (newest first)
journalctl -u my-service.service -r
```

The `-u` flag is the workhorse. It accepts globs:

```bash
# All postgresql units
journalctl -u 'postgresql*'

# Multiple units
journalctl -u my-service.service -u nginx.service
```

If you launched a process as a child of your service (a Python subprocess that `exec`'s `awk`, say), its logs are tagged with `_SYSTEMD_UNIT=my-service.service` as well. The `-u` filter catches them — that's the whole point of structured logging. The `_COMM=` field tells you which child it was.

### 1.2 Filter by priority

The journal stores a syslog priority (0-7) for every entry:

| Priority | Name      | When |
|---------:|-----------|------|
| 0        | emerg     | System is unusable |
| 1        | alert     | Action must be taken immediately |
| 2        | crit      | Critical conditions |
| 3        | err       | Error conditions |
| 4        | warning   | Warning conditions |
| 5        | notice    | Normal but significant |
| 6        | info      | Informational (the default for stdout) |
| 7        | debug     | Debug-level messages |

```bash
# Errors and worse
journalctl -p err

# Warnings and worse
journalctl -p warning

# Per unit
journalctl -u my-service.service -p err
```

The default mapping for stdout is `info` (6); for stderr it's `warning` (4). If your service uses a structured logger (Python `logging`, Go `slog`, Rust `tracing`), it can emit priority hints with the `<N>` SYSLOG-style prefix:

```python
import sys
# Python: writing "<3>error message\n" to stderr is logged at priority err
sys.stderr.write("<3>database connection failed\n")
```

Most languages have a systemd-aware logging adapter that does this for you. The Python `systemd.journal.JournalHandler` is the canonical one.

### 1.3 Filter by time

```bash
# Since 9am today
journalctl --since "today 09:00"

# Last hour
journalctl --since "1 hour ago"

# Specific range
journalctl --since "2026-05-13 14:00" --until "2026-05-13 14:30"

# Per unit, last hour
journalctl -u my-service.service --since "1 hour ago"
```

Time strings accept human-friendly forms (`yesterday`, `today`, `now`, `1 hour ago`, `2 days ago`) and ISO 8601 (`2026-05-13 14:00:00`). The full grammar is in `systemd.time(7)`.

### 1.4 Filter by boot

```bash
# Current boot only
journalctl -b

# Previous boot
journalctl -b -1

# Two boots ago
journalctl -b -2

# List all available boots
journalctl --list-boots
```

`journalctl -b` is the single most useful flag when "what happened since the last reboot." Combined with `-u` and `-p`:

```bash
# Errors and worse, this boot, my service
journalctl -b -u my-service.service -p err
```

### 1.5 Follow mode

```bash
# Like tail -f
journalctl -f

# Per unit
journalctl -u my-service.service -f
```

The follow mode prints new entries as they arrive. Use it during development: edit the unit file, `daemon-reload`, `restart`, watch the logs roll. Ctrl-C exits. The default scroll is 10 lines of history before following starts (`-n 10`); use `-n 0` to start with no history.

### 1.6 Search the body

```bash
# Case-sensitive substring
journalctl -u my-service.service --grep "connection refused"

# Case-insensitive
journalctl -u my-service.service -i --grep "connection refused"

# Combine with -p
journalctl -u my-service.service -p warning --grep "timeout"
```

`--grep` (since systemd 237) is faster than piping to `grep` because the filter happens before pagination. For large journals this matters.

### 1.7 Output formats

```bash
# Default: human-readable lines
journalctl -u my-service.service

# Full record, all fields
journalctl -u my-service.service -o json-pretty

# One-line JSON per entry (for piping to jq)
journalctl -u my-service.service -o json | jq '.MESSAGE'

# Short timestamp + message
journalctl -u my-service.service -o short
```

The JSON formats are the answer when "I need to parse logs." Every metadata field is exposed; you can extract `_PID`, `_BOOT_ID`, `PRIORITY` programmatically. The journal is genuinely structured; `journalctl` lets you take advantage of that.

### 1.8 Persistent vs volatile storage

By default on Ubuntu 24.04, the journal is **volatile** — stored in `/run/log/journal/` (tmpfs), wiped on reboot. On Fedora 41, the journal is **persistent** by default — stored in `/var/log/journal/`, survives reboots.

To switch Ubuntu to persistent:

```bash
sudo mkdir -p /var/log/journal
sudo systemd-tmpfiles --create --prefix /var/log/journal
sudo systemctl restart systemd-journald
```

After this, `journalctl -b -1` shows the previous boot's logs, which is essential for postmortem. To tune capacity, edit `/etc/systemd/journald.conf` (or drop-in under `/etc/systemd/journald.conf.d/`):

```ini
[Journal]
SystemMaxUse=2G
SystemMaxFileSize=128M
MaxRetentionSec=1month
```

The defaults are "10% of the filesystem, no time limit," which can fill `/var` on small VMs. Set explicit limits.

## 2. Sandboxing — the directives that matter

The freedesktop.org `systemd.exec(5)` man page lists roughly **60 sandboxing directives** as of systemd 256. We will not cover all 60. We will cover **the eight that catch the most attack surface for the least friction**, in the order you should apply them.

The model: you write a service. It runs. You then add directives one at a time, restart, check it still works. If a directive breaks the service, you've learned what the service actually needs. Add the next directive. Repeat until `systemd-analyze security UNIT` reports an exposure score in the 1-3 range.

### 2.1 The reference unit

For this section, assume the starting unit is:

```ini
# /etc/systemd/system/wide-open.service
[Unit]
Description=A wide-open service

[Service]
Type=exec
ExecStart=/usr/local/bin/wide-open
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Out of the box, this runs as root, can write anywhere, can read anyone's home directory, can call any syscall. `systemd-analyze security wide-open.service` will score it around **9.6** (one of the worst possible scores). Let's bring it down.

### 2.2 Directive 1 — `User=` (drop root)

```ini
[Service]
User=wide-open
Group=wide-open
```

Don't run as root. Create a dedicated system user:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin wide-open
```

This is the cheapest, biggest single win. A bug that lets the attacker run `system()` can no longer overwrite `/etc/passwd`. Score drop: typically 1.5-2.0 points.

The user must exist before the unit starts. If it doesn't, systemd refuses with `Failed to determine user credentials: No such process` — a phrase that does not mean what it sounds like; it means "no such user."

### 2.3 Directive 2 — `DynamicUser=true` (since systemd 232)

```ini
[Service]
DynamicUser=true
```

Instead of creating a static user, ask systemd to **invent one** for the service. systemd allocates a transient UID from a reserved range (61184-65519), uses it for the service, and frees it when the service stops. The user does not exist in `/etc/passwd`; it only exists while the service runs.

`DynamicUser=` is the strongest user-isolation option. It implies a bundle of other directives:

- `PrivateTmp=yes` (automatic)
- `RemoveIPC=yes` (automatic)
- `ProtectSystem=strict` (automatic, mostly)
- `ProtectHome=read-only` (automatic)
- `NoNewPrivileges=yes` (automatic)

The cost: the service can't write to predictable paths under `/var/lib/`. Use `StateDirectory=` and friends to tell systemd what writable directories to provide:

```ini
[Service]
DynamicUser=true
StateDirectory=wide-open          # creates /var/lib/wide-open, owned by transient UID
CacheDirectory=wide-open          # creates /var/cache/wide-open
LogsDirectory=wide-open           # creates /var/log/wide-open
RuntimeDirectory=wide-open        # creates /run/wide-open, wiped on stop
ConfigurationDirectory=wide-open  # makes /etc/wide-open readable
```

This is the cleanest sandbox pattern in systemd. Score drop: typically 3.0-4.0 points just from this directive. If your service can use it, use it.

### 2.4 Directive 3 — `ProtectSystem=strict`

```ini
[Service]
ProtectSystem=strict
```

Remounts `/usr`, `/boot`, `/efi`, and `/etc` **read-only** for the service. Three levels:

- `ProtectSystem=true` — `/usr` and `/boot` read-only. `/etc` writable.
- `ProtectSystem=full` — `/usr`, `/boot`, `/etc` read-only.
- `ProtectSystem=strict` — entire filesystem read-only except `/dev`, `/proc`, `/sys`, plus any `ReadWritePaths=` you list.

`strict` is the right default. If the service needs to write somewhere, declare it:

```ini
ProtectSystem=strict
ReadWritePaths=/var/lib/wide-open /var/log/wide-open
```

Score drop: 0.5-1.5 points depending on starting state.

### 2.5 Directive 4 — `ProtectHome=true`

```ini
[Service]
ProtectHome=true
```

Hides `/home`, `/root`, and `/run/user` from the service. If the service tries to read `/home/alice/Documents/secrets.txt`, it sees an empty directory. Three values:

- `ProtectHome=true` — bind-mount tmpfs over `/home`, `/root`, `/run/user`.
- `ProtectHome=read-only` — accessible but read-only.
- `ProtectHome=tmpfs` — same as `true`; explicit.

For any service that doesn't legitimately need to read user home directories: `ProtectHome=true`. Score drop: ~0.5 points.

### 2.6 Directive 5 — `PrivateTmp=true`

```ini
[Service]
PrivateTmp=true
```

Gives the service its own private `/tmp` and `/var/tmp`. The service's `/tmp` is invisible to every other service and every other user. Wiped on stop.

This blocks an entire class of attacks: race conditions on shared `/tmp` files, symlink attacks where an attacker pre-creates `/tmp/cache.123` to redirect a write to `/etc/passwd`, and inadvertent information leaks. Score drop: ~0.2-0.5 points.

If `DynamicUser=true` is set, `PrivateTmp=true` is implied.

### 2.7 Directive 6 — `NoNewPrivileges=true`

```ini
[Service]
NoNewPrivileges=true
```

Sets the `no_new_privs` bit on the process. After this, **setuid binaries cannot escalate privileges** within this service. If the service runs `sudo` or `su`, those programs will refuse — they cannot get the elevated UID they need.

The only legitimate reason to omit `NoNewPrivileges=true` is if your service genuinely needs to invoke a setuid helper (`ping` historically; some `mount` helpers). Most services do not. Set it. Score drop: ~0.5 points.

Implied by `DynamicUser=true`.

### 2.8 Directive 7 — `CapabilityBoundingSet=`

```ini
[Service]
CapabilityBoundingSet=
# (empty: drop all capabilities)
```

Linux capabilities split root's all-or-nothing power into ~40 distinct privileges (`CAP_NET_BIND_SERVICE` for binding low ports, `CAP_NET_ADMIN` for network config, `CAP_SYS_ADMIN` for everything else, and so on). The `CapabilityBoundingSet=` directive limits which capabilities the service can ever acquire.

Empty set = no capabilities at all. This is the right default. Most services need zero capabilities. The ones that don't, declare what they need:

```ini
# Service that needs to bind port 80
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
```

(`CapabilityBoundingSet=` caps what the process *can* acquire; `AmbientCapabilities=` are actually granted at startup.)

Score drop: 1.0-2.0 points. Very high return per character typed.

### 2.9 Directive 8 — `RestrictAddressFamilies=`

```ini
[Service]
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
# (only these three socket families allowed)
```

Linux supports ~40 socket address families. Most services need IPv4, IPv6, and Unix sockets. They never need `AF_NETLINK`, `AF_PACKET`, `AF_BLUETOOTH`, `AF_CAN`. The restrict directive prevents the service from creating sockets of any family not listed.

For a typical web service: `AF_UNIX AF_INET AF_INET6` is the right answer. Score drop: ~0.5 points.

If your service only talks over Unix sockets (e.g., a Postgres extension): `RestrictAddressFamilies=AF_UNIX`. Even tighter.

### 2.10 Putting it together

A reasonable production sandbox, applied to the reference unit:

```ini
[Service]
Type=exec
ExecStart=/usr/local/bin/wide-open
Restart=on-failure
RestartSec=5s

# User isolation
DynamicUser=true
StateDirectory=wide-open
LogsDirectory=wide-open

# Filesystem isolation
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true            # implied by DynamicUser, kept explicit
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Privilege isolation
NoNewPrivileges=true       # implied by DynamicUser, kept explicit
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true

# Syscall filter (optional, advanced)
SystemCallFilter=@system-service
SystemCallFilter=~@privileged @resources
```

Run `systemd-analyze security wide-open.service` after each directive add to see the score drop. The reference target is **exposure 2.0 or lower** for a service that shouldn't need broad access. The score can never reach 0 (some directives only apply to certain service types), but staying under 3.0 is a reasonable production goal.

### 2.11 The exposure score reference

`systemd-analyze security UNIT` produces output like:

```
NAME                                                        DESCRIPTION                                  EXPOSURE
✓ User=/DynamicUser=                                       Service runs as transient user
✓ CapabilityBoundingSet=~CAP_SYS_ADMIN                     Service cannot administer the kernel
✓ CapabilityBoundingSet=~CAP_SYS_BOOT                      Service cannot issue reboot()
✓ PrivateDevices=                                          Service has no access to hardware
✗ RestrictAddressFamilies=~AF_PACKET                       Service may allocate packet sockets       0.2
...

→ Overall exposure level for wide-open.service: 1.8 OK 🙂
```

The score breakdown:

| Score | Meaning |
|------:|---------|
| 0.0 - 1.0 | Exposure: minimal. Hard to reach without effort. |
| 1.1 - 2.5 | Exposure: low. Reasonable production posture. |
| 2.6 - 4.9 | Exposure: medium. Common for vendor services. |
| 5.0 - 7.4 | Exposure: high. Default systemd unit without hardening. |
| 7.5 - 9.9 | Exposure: very high. Wide open. |
| 10.0      | Exposure: unsafe. Maximum exposure. |

Run it against every service on your machine. `sshd.service` is intentionally permissive (it needs `CAP_NET_BIND_SERVICE`, network access, and the ability to spawn user shells). Most other services should be in the low or minimal range.

## 3. The two together — logs of a sandboxed service

When a sandboxed service tries to do something it can't, the failure mode is **`EPERM` from a syscall** — and it ends up in the journal:

```
my-service.service: Failed to set up mount namespacing: Permission denied
my-service.service: Failed at step NAMESPACE spawning /usr/local/bin/my-service: Permission denied
```

The `Failed at step` prefix tells you which sandbox check tripped. The full list of step names is in `systemd.service(5)` under "STATUS PROPERTIES." The most common ones:

| Step | What failed |
|------|-------------|
| `EXEC` | `execve()` of the binary failed |
| `NAMESPACE` | Setting up the mount namespace (often `ProtectSystem=`) |
| `CREDENTIALS` | Looking up `User=` |
| `CAPABILITIES` | Dropping or setting capabilities |
| `RLIMIT` | An `RLIMIT_*` cap was rejected |
| `CHROOT` | `RootDirectory=` setup |

When you're ratcheting the sandbox tight, you will see these. The cure is to relax exactly one directive — never two — and re-check.

## 4. The end-to-end pattern

Putting Lecture 1 and Lecture 2 together:

```bash
# 1. Write the unit, wide open
sudoedit /etc/systemd/system/my-service.service

# 2. Validate syntax
systemd-analyze verify /etc/systemd/system/my-service.service

# 3. Reload, start, watch
sudo systemctl daemon-reload
sudo systemctl start my-service.service
journalctl -u my-service.service -f &

# 4. Score the initial sandbox
systemd-analyze security my-service.service

# 5. Add directives one at a time
sudoedit /etc/systemd/system/my-service.service       # add DynamicUser=true
sudo systemctl daemon-reload
sudo systemctl restart my-service.service
systemd-analyze security my-service.service           # check new score

# 6. Repeat until score is in the 1.0-2.5 range, or the service breaks
# When it breaks, check journalctl for the "Failed at step" line, relax that one

# 7. Enable for boot
sudo systemctl enable my-service.service
```

The loop is `edit → reload → restart → check journal → check score`. Ten minutes of this gets a service from exposure 9.6 to exposure 2.0. That is the cheapest security work you will ever do.

## 5. What this lecture skipped

Three things, briefly:

- **`SystemCallFilter=`** — restricting syscalls. Powerful, fiddly. The `@system-service` group is a sensible default. Full reference in `systemd.exec(5)`.
- **Resource limits** — `MemoryMax=`, `CPUQuota=`, `TasksMax=`, `IOWeight=`. Live in `systemd.resource-control(5)`. Cap them on any service that could legitimately grow unbounded.
- **`PrivateNetwork=true`** — gives the service its own empty network namespace. Loopback only. Maximum network isolation, but useless if the service needs to make outbound HTTP calls. Set it on services that genuinely don't need network (offline batch jobs).

You will meet all three in later weeks. For Week 5, the eight directives above plus `journalctl` cover the high-leverage cases.

---

*Read `journalctl(1)` and `systemd.exec(5)` after this lecture. The `journalctl(1)` man page is short and example-heavy. The `systemd.exec(5)` man page is the longest in the systemd suite — skim once front-to-back, then keep it open as a reference whenever you tighten a sandbox.*
