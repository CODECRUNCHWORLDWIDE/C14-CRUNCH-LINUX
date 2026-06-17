# Lecture 1 — Unit Files: Services, Timers, Sockets

> **Duration:** ~3 hours. **Outcome:** You can write a `.service` unit file from memory, pick the right `Type=`, set a sane `Restart=` policy, replace a `cron` job with a `.timer` + `.service` pair, and recognize when a `.socket` unit is the right tool. You read `systemctl cat`, `systemctl show`, and `systemd-analyze verify` fluently.

systemd is a process supervisor. The thing it supervises is described by a **unit file** — an INI-style text file that says "this is the binary, this is how to start it, this is what to do when it stops." That is the whole conceptual model. Everything in this lecture is a refinement on it. Read it at the keyboard, with `systemctl --version` showing 255 or newer.

## 1. The anatomy of a unit file

Every unit file is an INI file with three sections. The minimum viable `.service` unit:

```ini
[Unit]
Description=A minimum viable service

[Service]
ExecStart=/usr/local/bin/my-service

[Install]
WantedBy=multi-user.target
```

Six lines. Save as `/etc/systemd/system/my-service.service`, run `sudo systemctl daemon-reload && sudo systemctl enable --now my-service`, and you have a service. Let's unpack each section.

### 1.1 The `[Unit]` section

The `[Unit]` section is **metadata and ordering**. It describes what the unit is (`Description=`), what it depends on (`Requires=`, `Wants=`), what it must run after (`After=`), and what conditions must hold before it starts (`ConditionPathExists=`, `AssertPathExists=`).

```ini
[Unit]
Description=Web service for /api/* requests
Documentation=man:my-service(8) https://internal.example.com/docs/my-service
After=network-online.target
Wants=network-online.target
ConditionPathExists=/etc/my-service/config.yaml
```

Things to note:

- **`After=` is ordering, not dependency.** It says "if X is also being started, start it first." If X is not pulled in by anything else, `After=` does nothing on its own. To pull X in, use `Wants=X` (soft) or `Requires=X` (strict).
- **`Wants=network-online.target`** is the common idiom for "I need the network." `network.target` is *not* enough — it means "the network stack is loaded," not "the network is up." `network-online.target` blocks until at least one interface is online. The `Wants=` plus `After=` pair is the canonical form.
- **`ConditionPathExists=`** versus **`AssertPathExists=`**: a failed `Condition` quietly skips the unit (no error). A failed `Assert` is a hard failure that systemd logs. Use `Condition` for "this unit only applies if X"; use `Assert` for "this unit must have X."
- The `Documentation=` line shows up in `systemctl status` output. Use it. The `man:` URI form is the convention for man pages.

### 1.2 The `[Service]` section

The `[Service]` section is **the process**. It says how to start the binary, what user to run it as, what to do when it exits, and where its stdout/stderr go.

```ini
[Service]
Type=simple
ExecStart=/usr/local/bin/my-service --config /etc/my-service/config.yaml
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=5s
User=my-service
Group=my-service
WorkingDirectory=/var/lib/my-service
Environment="LOG_LEVEL=info"
EnvironmentFile=-/etc/my-service/env
```

Things to note:

- **`ExecStart=` must be an absolute path.** Not `my-service`. Not `./my-service`. Not `bash my-service`. The path must start with `/`. If you need shell features (pipes, redirections, glob expansion), wrap the command in `bash -c "..."` — but think twice before you do. The right answer is usually a wrapper script.
- **`ExecStart=` takes one command, not many.** If you write two `ExecStart=` lines, the second replaces the first (unless `Type=oneshot`, in which case multiple are allowed). To run setup commands first, use `ExecStartPre=`. To run teardown commands after, use `ExecStopPost=`.
- **`Environment=` versus `EnvironmentFile=`.** `Environment=` sets one variable per line. `EnvironmentFile=` reads `KEY=VALUE` lines from a file. The `-` prefix on `EnvironmentFile=` means "ignore if missing" — useful for optional config.
- **`$MAINPID` in `ExecReload=`** is a systemd specifier that expands to the PID of the main service process. Used here to send `SIGHUP` for config reload.
- **`User=`** drops privileges before running `ExecStart=`. If the user doesn't exist, systemd refuses to start the unit. We will spend most of Lecture 2 on the security implications of this section.

### 1.3 The `[Install]` section

The `[Install]` section says **what happens on `systemctl enable`**. Specifically, it tells systemd which other unit should pull this one in.

```ini
[Install]
WantedBy=multi-user.target
```

That one line says: "When `multi-user.target` is started (which is, on most systems, every boot), pull this service in too." On `systemctl enable my-service`, systemd creates a symlink:

```
/etc/systemd/system/multi-user.target.wants/my-service.service
    -> /etc/systemd/system/my-service.service
```

On `systemctl disable`, the symlink is removed. The unit file itself is untouched.

The `WantedBy=` line is **not optional for boot-time services**. If you forget it, `systemctl enable` will refuse:

```
$ sudo systemctl enable my-service
The unit files have no installation config (WantedBy=, RequiredBy=, Also=,
Alias= settings in the [Install] section, and DefaultInstance= for template
units). This means they are not meant to be enabled or disabled using systemctl.
```

Common values:

- `WantedBy=multi-user.target` — the typical choice. Pulled in at boot, on every system that isn't a GUI desktop.
- `WantedBy=graphical.target` — for services that need the display server. Rare.
- `WantedBy=default.target` — for user units. The user's default target.
- `RequiredBy=...` — strict dependency. Use sparingly; failure cascades.

## 2. `Type=` — how systemd judges "started"

Every service has a `Type=`. The type tells systemd how to interpret "the service has started" — which matters because the next unit in the boot sequence depends on it.

### 2.1 `Type=simple` (the default)

```ini
[Service]
Type=simple
ExecStart=/usr/local/bin/my-service
```

`Type=simple` says: **the service is considered started the moment systemd calls `fork()`**. The actual binary may not have called `execve()` yet, let alone `bind()`-ed its listening socket. systemd doesn't know and doesn't wait.

This is fine for most services. It is wrong when the next unit depends on this service being ready. Example:

```ini
# database.service has Type=simple
# webapp.service has After=database.service
```

When `database.service` reports "started" at `fork()` time, systemd will start `webapp.service` immediately — possibly before the database is listening on its socket. The webapp will fail to connect and crash. The cure is either `Type=notify` (the database tells systemd "I'm ready" via `sd_notify(3)`) or socket activation (systemd opens the socket, hands it to the database; the webapp's connection blocks until the database accepts).

### 2.2 `Type=exec` (since systemd 240)

```ini
[Service]
Type=exec
ExecStart=/usr/local/bin/my-service
```

`Type=exec` is `Type=simple` with one extra wait: systemd waits for `execve()` to return successfully before considering the service started. If `ExecStart=` points to a non-existent binary, `Type=simple` reports "started" and then immediately reports "failed" a moment later. `Type=exec` reports "failed" cleanly, before any dependent unit starts.

Prefer `Type=exec` over `Type=simple` for new units. The cost is negligible and the error messages are better. Both behave identically once the service is running.

### 2.3 `Type=forking` (the legacy SysV pattern)

```ini
[Service]
Type=forking
ExecStart=/usr/local/sbin/my-daemon
PIDFile=/run/my-daemon.pid
```

`Type=forking` says: **the binary will `fork()`, the parent will exit, and the child is the real service**. This was the standard for SysV daemons in the 1990s. Almost nothing new uses it — but if you're packaging a 30-year-old C daemon, this is the type.

The `PIDFile=` line tells systemd which file the daemon writes its child PID to, so systemd can track it. Without `PIDFile=`, systemd guesses based on cgroup membership, which is unreliable.

If you are writing a new daemon: **do not double-fork to detach.** Use `Type=exec` (or `Type=simple`) and let systemd manage you. The double-fork pattern is a workaround for a problem (no supervisor) that systemd solves.

### 2.4 `Type=notify` (the readiness-aware type)

```ini
[Service]
Type=notify
ExecStart=/usr/local/bin/my-service
NotifyAccess=main
```

`Type=notify` says: **the service will explicitly tell systemd when it is ready**, via a `READY=1` message over a Unix socket pointed to by `$NOTIFY_SOCKET`. The C API is `sd_notify(3)`; bindings exist for Python (`sdnotify`), Go (`github.com/coreos/go-systemd/daemon`), Rust (`sd-notify`), and most modern languages.

This is the right type for any service where "the binary started" and "the service is ready to handle requests" are different moments. Examples:

- A database that loads 4GB of indexes before accepting connections.
- A web app that warms a cache.
- A service that publishes a D-Bus interface and needs the interface ready before clients connect.

The `READY=1` message is one byte over a socket. Cheap to send; pays for itself the first time a downstream unit's `After=` does the right thing.

### 2.5 `Type=oneshot` (run once and exit)

```ini
[Service]
Type=oneshot
ExecStart=/usr/local/bin/run-migrations
RemainAfterExit=yes
```

`Type=oneshot` says: **this is a one-shot command, not a long-running daemon**. systemd waits for it to exit, considers it "started" (in the success case), and moves on. Multiple `ExecStart=` lines are allowed and run in sequence.

`RemainAfterExit=yes` tells systemd "remember this as active even after the process exited." Useful when other units `Require=` this one as a precondition. Without it, the oneshot's effect is invisible to dependency resolution after exit.

Almost every `.timer` you write pairs with a `.service` of `Type=oneshot`. The timer fires, the oneshot runs to completion, the timer fires again next interval. Clean.

### 2.6 The `Type=` decision tree

You almost never need `Type=forking`. Use:

- **`Type=notify`** if the service knows when it's ready and can send `sd_notify()`.
- **`Type=exec`** if the service is "ready" the moment `execve()` succeeds (most CLI binaries; most simple daemons).
- **`Type=oneshot`** if it's a script that runs and exits (timers, setup commands).
- **`Type=simple`** is the default but `Type=exec` is strictly better for new code.

## 3. `Restart=` — what to do when the service exits

Long-running services crash. Configs change. Dependencies disappear. The `Restart=` directive tells systemd what to do when the main process exits.

### 3.1 The seven values

```ini
[Service]
Restart=on-failure
RestartSec=5s
```

The seven values, by frequency of use:

- **`Restart=on-failure`** — restart if the service exits non-zero, is killed by a signal (other than `SIGTERM`, `SIGINT`, `SIGHUP`, `SIGPIPE`), or hits a watchdog timeout. The right default for most services.
- **`Restart=always`** — restart no matter why the service exited, including clean exits. Use only if "clean exit means restart" is genuinely what you want (a service whose protocol involves exiting after each work unit, for example).
- **`Restart=on-abnormal`** — like `on-failure` but ignores non-zero clean exits. Useful for services that signal "shutdown gracefully" with `exit(42)`.
- **`Restart=on-success`** — restart only on clean exit. Rare; mostly for batch-style services that loop externally.
- **`Restart=on-abort`** — restart only if killed by uncaught signal. Rare.
- **`Restart=on-watchdog`** — restart only on `WatchdogSec=` timeout. Used with `Type=notify` services that send `WATCHDOG=1` periodically.
- **`Restart=no`** (the default) — never restart. Wrong for any service you want supervised.

### 3.2 `RestartSec=` and the crash-loop guard

```ini
[Service]
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60s
StartLimitBurst=5
```

The four-knob crash-loop guard:

- **`RestartSec=5s`** — wait 5 seconds between exit and restart. Default is **`100ms`**, which is too aggressive: a service that crashes immediately will burn CPU restarting hundreds of times per second. Set to 1-5 seconds in production.
- **`StartLimitIntervalSec=60s`** — the rate-limit window. Counts restarts in the last 60 seconds.
- **`StartLimitBurst=5`** — the max number of restarts in that window.
- After 5 restarts in 60 seconds, systemd gives up. The service goes into `failed` state with status "start-limit-hit." You have to `systemctl reset-failed` and `systemctl start` it explicitly to clear.

These four lines together say: "Restart on failure, wait 5s between tries, give up after 5 failures in a minute." That is the configuration you want for almost every service. Without `StartLimitBurst=`, a buggy service will crash-loop forever.

### 3.3 The crash-loop you will write

The most common Week 5 mistake:

```ini
# WRONG: crash-loops forever burning CPU
[Service]
Type=simple
ExecStart=/usr/local/bin/my-broken-service
Restart=always
# (no RestartSec, defaults to 100ms)
# (no StartLimitBurst, defaults to 5 in 10s window, but on Ubuntu 24.04's
#  vendored configuration the limit can be effectively higher)
```

`my-broken-service` crashes on startup. systemd restarts it 100ms later. It crashes again. Repeat. CPU pegs at 100%. The unit eventually hits `StartLimitBurst=` and gives up, but by then your boot has taken minutes and `journalctl` is full of crash records.

The right form:

```ini
# RIGHT: bounded crash-loop, gives up after 5 tries
[Service]
Type=exec
ExecStart=/usr/local/bin/my-broken-service
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60s
StartLimitBurst=5
```

The service still crashes. But it crashes 5 times spaced 5 seconds apart, then systemd marks it failed and stops. You get a clean `journalctl -u my-broken-service` to read, and your machine stays responsive.

## 4. Timers — replacing `cron` properly

`cron` is older than systemd by 24 years (cron: 1975; systemd: 2010). On a modern systemd system, **`.timer` units are strictly more powerful than `cron` entries** and you should default to them.

### 4.1 The timer + service pair

A timer always pairs with a service. The timer is the schedule; the service is the work.

```ini
# /etc/systemd/system/backup.timer
[Unit]
Description=Daily backup, at 03:00

[Timer]
OnCalendar=*-*-* 03:00:00
Persistent=true
RandomizedDelaySec=10min

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/backup.service
[Unit]
Description=Run the backup script

[Service]
Type=oneshot
ExecStart=/usr/local/bin/backup.sh /etc /var/backups/etc
```

The convention: **timer and service share a basename**. `backup.timer` triggers `backup.service`. If you want a different name, add `Unit=other.service` in the `[Timer]` section.

To start: `sudo systemctl enable --now backup.timer`. Note that you enable the **timer**, not the service. The timer is what runs at boot; it activates the service on schedule.

### 4.2 `OnCalendar=` — wall-clock schedules

`OnCalendar=` accepts a calendar spec. The full grammar is in `systemd.time(7)`; the short version:

```ini
OnCalendar=daily                   # 00:00:00 every day
OnCalendar=weekly                  # Monday 00:00:00
OnCalendar=hourly                  # :00 every hour
OnCalendar=*-*-* 03:00:00          # 03:00:00 every day
OnCalendar=Mon..Fri *-*-* 09:00:00 # 09:00:00 on weekdays
OnCalendar=*-*-1 04:00:00          # 04:00:00 on the 1st of every month
OnCalendar=2026-*-* 12:00:00       # noon every day in 2026
OnCalendar=*-*-* *:0/15:00         # every 15 minutes on the quarter
```

To check a calendar spec: `systemd-analyze calendar 'EXPR'`. It prints the next 5 firing times. Always run this before deploying — you will get one wrong eventually.

```bash
$ systemd-analyze calendar '*-*-* 03:00:00'
  Original form: *-*-* 03:00:00
Normalized form: *-*-* 03:00:00
    Next elapse: Wed 2026-05-14 03:00:00 UTC
       From now: 12h 59min left
```

### 4.3 `OnUnitActiveSec=` — relative schedules

```ini
[Timer]
OnBootSec=15min
OnUnitActiveSec=1h
```

This says: "First fire 15 minutes after boot, then every hour after the last activation." Monotonic time, not wall clock. Useful for services that should run "every hour" rather than "at :00 every hour" — the offset distributes load if many machines have the same boot time.

The full set of monotonic timers:

- `OnBootSec=` — relative to system boot.
- `OnStartupSec=` — relative to systemd start (similar to boot, but distinct in containers).
- `OnUnitActiveSec=` — relative to the unit's last activation.
- `OnUnitInactiveSec=` — relative to the unit's last deactivation.

You can stack them. `OnBootSec=15min` plus `OnUnitActiveSec=1h` means "first run 15 minutes after boot, then every hour."

### 4.4 `Persistent=true` — the laptop directive

```ini
[Timer]
OnCalendar=daily
Persistent=true
```

A `cron` entry that fires at 03:00 will be missed if the machine is asleep at 03:00. A `.timer` with `Persistent=true` will fire **as soon as the machine wakes up**, catching the missed run. This is huge for laptops and ephemeral VMs. Default behavior is `Persistent=false`; flip it on for any timer where missing a run matters.

`Persistent=true` works by storing the timer's last-run timestamp under `/var/lib/systemd/timers/`. On boot, systemd checks "should this have fired since last run?" If yes, fire immediately.

### 4.5 `RandomizedDelaySec=` — load distribution

```ini
[Timer]
OnCalendar=daily
RandomizedDelaySec=30min
```

Adds a random delay (uniformly distributed in `[0, 30min]`) before each firing. If you have 100 machines running the same daily backup, `OnCalendar=daily` makes all 100 hit the storage at exactly 00:00. With `RandomizedDelaySec=30min`, they hit it spread over a 30-minute window. Use it for any timer running on more than one machine.

### 4.6 Listing and debugging timers

```bash
# All active timers, sorted by next firing
systemctl list-timers --all

# What did backup.timer last do?
systemctl status backup.timer

# Run backup.service right now, ignoring the schedule
sudo systemctl start backup.service

# What would this calendar spec do?
systemd-analyze calendar '*-*-* 03:00:00'
```

The `list-timers` output shows `NEXT`, `LEFT`, `LAST`, `PASSED`, `UNIT`, and `ACTIVATES` columns. The single most useful command for "what is running and when."

## 5. Sockets — activation on demand

A `.socket` unit tells systemd: "Open this listening socket. When a client connects, start the corresponding `.service` and hand it the socket." This is **socket activation**.

### 5.1 The simple case

```ini
# /etc/systemd/system/echo.socket
[Unit]
Description=Echo socket

[Socket]
ListenStream=2222
Accept=no

[Install]
WantedBy=sockets.target
```

```ini
# /etc/systemd/system/echo.service
[Unit]
Description=Echo service
Requires=echo.socket

[Service]
ExecStart=/usr/local/bin/echo-handler
StandardInput=socket
```

On boot, systemd opens TCP port 2222 and waits. The `echo` binary is not running. When the first client connects, systemd starts `echo.service` and gives it the listening fd as stdin (via `StandardInput=socket`). The service handles the connection; subsequent connections are also passed to the running service.

`Accept=no` means: "one service handles all connections." `Accept=yes` means: "one service instance per connection" (the `inetd` model). `Accept=no` is the modern default; `Accept=yes` exists for legacy compatibility.

### 5.2 Why bother with socket activation

Three reasons:

- **Parallel boot.** systemd can open all sockets early in boot, in parallel, before any service starts. When `webapp` needs to connect to `database`, the connection blocks until `database.service` is ready to accept it — no need for `After=` ordering. This is the original 2010 motivation for systemd.
- **On-demand startup.** A service that handles 3 requests per day doesn't need to run 24/7. The socket sits there cheap; the service starts when needed.
- **Restart without dropping connections.** systemd holds the listening socket. When the service restarts, the socket stays open; pending connections wait. The client sees a brief delay, not a refused connection.

You will write socket-activated services in Week 6 (SSH) and Week 8 (the capstone). For Week 5, recognize the pattern and know when to reach for it.

## 6. User units vs system units

Two scopes:

- **System units** live in `/etc/systemd/system/`. Run as root by default (use `User=` to drop). Started by `systemd` (PID 1). Visible to all users.
- **User units** live in `~/.config/systemd/user/`. Run as the user. Started by `systemd --user` (one per logged-in user). Invisible to other users.

```bash
# System unit (root)
sudo systemctl enable --now my-service.service

# User unit (no sudo)
systemctl --user enable --now my-service.service
```

For services that don't need root, **prefer user units**. They are easier to debug, can't accidentally break the system, and don't require `sudo` for every change.

The one gotcha: by default, `systemd --user` exits when the user logs out. For a user service that should keep running, enable linger:

```bash
sudo loginctl enable-linger $USER
```

This tells systemd: "Keep `systemd --user` for this user running even when they're logged out." Without it, your user service stops the moment you `exit` your SSH session.

## 7. Validation — `systemd-analyze` and `systemctl cat`

Before you reload, validate. After you reload, inspect.

### 7.1 `systemd-analyze verify`

```bash
systemd-analyze verify /etc/systemd/system/my-service.service
```

This parses the unit file, resolves dependencies, and reports errors. Catches:

- Syntax errors in the INI file.
- Unknown directives.
- Invalid values for known directives.
- Missing referenced units.
- Bad `ExecStart=` paths (the binary doesn't exist).
- Wrong section for a directive (`Restart=` in `[Unit]`, for example).

Run it before every `daemon-reload`. The lecture's promise is: if `systemd-analyze verify` is clean, your unit will at least load.

### 7.2 `systemctl cat`

```bash
systemctl cat my-service.service
```

Prints the unit file and all drop-ins in the order systemd reads them. The single most useful debugging command. If you `systemctl edit` a unit and the change doesn't take effect, `systemctl cat` shows you why — usually because the drop-in is in the wrong directory.

### 7.3 `systemctl show`

```bash
systemctl show my-service.service
```

Dumps every resolved property of the unit, including defaults. About 200 lines per service. Pipe to `grep` for the field you care about:

```bash
systemctl show my-service.service | grep -i restart
# Restart=on-failure
# RestartUSec=5s
# RestartKillSignal=SIGTERM
# ...
```

This is how you confirm "did my drop-in actually set `RestartSec=`?" without reading every file. The shown value is what systemd actually uses.

## 8. The end-to-end pattern

The full lifecycle of writing a new service:

```bash
# 1. Write the unit file
sudoedit /etc/systemd/system/my-service.service

# 2. Validate
systemd-analyze verify /etc/systemd/system/my-service.service

# 3. Reload systemd's view of unit files
sudo systemctl daemon-reload

# 4. Start it
sudo systemctl start my-service.service

# 5. Check status
systemctl status my-service.service

# 6. Watch logs
journalctl -u my-service.service -f
# Ctrl-C to stop following

# 7. If happy, enable for boot
sudo systemctl enable my-service.service

# 8. Inspect resolved properties
systemctl cat my-service.service
systemctl show my-service.service | grep -E '^(Restart|Type|ExecStart|User)='
```

Eight steps. Memorize the sequence. Every service you write this week (and every service you ship for the rest of your career) goes through these eight steps.

## 9. What you skipped, and what's next

This lecture skipped:

- **`.mount`, `.automount`, `.swap`, `.path`, `.scope`, `.slice`, `.device`** unit types. You will meet them in passing in later weeks; for Week 5, `service` / `timer` / `socket` covers 95% of what you write.
- **`Type=dbus`** and **`BusName=`**. Almost never used in new code; mentioned here for completeness.
- **Resource control** — `MemoryMax=`, `CPUQuota=`, `TasksMax=`. These live in `systemd.resource-control(5)`. Briefly: any unit can be capped. We touch on this in Lecture 2 alongside sandboxing.

Lecture 2 covers `journalctl` end-to-end and the sandboxing directives. The service you wrote in this lecture is wide open — runs as root, can write anywhere, can call any syscall. Lecture 2 ratchets it down.

---

*Read `systemd.unit(5)`, `systemd.service(5)`, and `systemd.timer(5)` after this lecture. Open each in a terminal pager (`man 5 systemd.service`) so the SEE ALSO links work. The man pages are dense but precise; they are the source of truth.*
