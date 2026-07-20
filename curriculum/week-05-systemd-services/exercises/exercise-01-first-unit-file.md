# Exercise 01 — Your First Unit File

**Time:** ~2 hours. **Goal:** Write a `.service` unit, validate it, install it, enable it, observe it, and recover from a deliberate crash. Build the muscle memory for the eight-step lifecycle (Lecture 1, §8). Every step exists for a reason; if you skip steps, the lecture's promises stop holding.

You will need systemd 255 or newer and `sudo`. Verify:

```bash
systemctl --version | head -1
sudo true
```

Set up a scratch directory:

```bash
mkdir -p ~/c14-week-05/exercises/01
cd ~/c14-week-05/exercises/01
```

---

## Part 1 — The "hello world" service (30 min)

Write a service that prints "tick" every five seconds to its journal. This will run forever; we'll stop it at the end of part 1.

### Step 1.1 — The script

Save as `~/c14-week-05/exercises/01/tick.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

while true; do
    printf 'tick %s\n' "$(date -Iseconds)"
    sleep 5
done
```

Make it executable: `chmod +x ~/c14-week-05/exercises/01/tick.sh`. Test by running it directly: `./tick.sh`. You should see one tick line every 5 seconds. Ctrl-C to stop.

### Step 1.2 — The unit file

Save as `/etc/systemd/system/tick.service`. You will need `sudo` to write here. Use `sudoedit` (it edits a temp copy and `mv`s on save, so half-saved files never replace the real one):

```bash
sudoedit /etc/systemd/system/tick.service
```

Contents — note the `User=` line, which you must change to your username:

```ini
[Unit]
Description=Tick test service - prints a timestamped line every 5 seconds
Documentation=https://github.com/CODE-CRUNCH-CLUB/C14-CRUNCH-LINUX/blob/main/curriculum/week-05-systemd-services/exercises/exercise-01-first-unit-file.md

[Service]
Type=exec
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/01/tick.sh
Restart=on-failure
RestartSec=2s
User=YOUR_USERNAME

[Install]
WantedBy=multi-user.target
```

Replace `YOUR_USERNAME` with the output of `whoami` (twice — in `ExecStart=` and `User=`).

### Step 1.3 — Validate

```bash
sudo systemd-analyze verify /etc/systemd/system/tick.service
```

If it prints nothing, the unit is syntactically valid. If it prints warnings or errors, fix them before continuing.

### Step 1.4 — Reload, start, watch

```bash
sudo systemctl daemon-reload
sudo systemctl start tick.service
systemctl status tick.service
```

`systemctl status` should show "active (running)" and the most recent few journal lines. Confirm you see "tick" lines.

Follow the journal:

```bash
journalctl -u tick.service -f
```

You should see one "tick" line every 5 seconds. Let it run for 30 seconds, then Ctrl-C the journalctl.

### Step 1.5 — Enable for boot, then stop

```bash
sudo systemctl enable tick.service
systemctl is-enabled tick.service                 # should say "enabled"
sudo systemctl stop tick.service
systemctl is-active tick.service                  # should say "inactive"
```

Note: `enable` and `stop` are independent. The service is **enabled** (will start at next boot) but **not running**. `disable` removes the symlink; `stop` halts the current process. Most of the time you want `enable --now` (enable and start) or `disable --now` (disable and stop).

### Step 1.6 — Inspect the resolved unit

```bash
systemctl cat tick.service
systemctl show tick.service | grep -E '^(Type|ExecStart|Restart|User)='
```

`systemctl cat` shows the unit file plus any drop-ins. `systemctl show` shows every resolved property. Get used to running both — they answer different questions.

**Acceptance for part 1:** the service starts, the journal shows tick lines, the service is enabled, and the resolved properties (`systemctl show`) include `Restart=on-failure`, `Type=exec`, your username under `User=`.

---

## Part 2 — Restart policy under deliberate failure (45 min)

Now we make the service crash and watch systemd handle it. This is where the `Restart=`, `RestartSec=`, `StartLimitIntervalSec=`, `StartLimitBurst=` knobs earn their existence.

### Step 2.1 — A script that crashes

Save as `~/c14-week-05/exercises/01/crash.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

# Print a marker, then exit with code 1 after a short delay.
printf 'crash.sh starting, pid=%d\n' "$$"
sleep 1
printf 'crash.sh about to fail at %s\n' "$(date -Iseconds)" >&2
exit 1
```

`chmod +x ~/c14-week-05/exercises/01/crash.sh`. Run it directly first; verify it exits with code 1 (`echo $?`).

### Step 2.2 — The crashing unit, with the four-knob crash-loop guard

Edit `/etc/systemd/system/tick.service` (or write a separate `crash.service`) so that `ExecStart=` points at `crash.sh`. While you're at it, set the crash-loop knobs:

```ini
[Service]
Type=exec
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/01/crash.sh
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60s
StartLimitBurst=5
User=YOUR_USERNAME
```

`systemd-analyze verify` it. Reload and start:

```bash
sudo systemctl daemon-reload
sudo systemctl restart tick.service
```

### Step 2.3 — Watch it crash, restart, give up

```bash
journalctl -u tick.service -f
```

You should see:

```
[T+0s]  crash.sh starting, pid=...
[T+1s]  crash.sh about to fail at ...
[T+1s]  tick.service: Main process exited, code=exited, status=1/FAILURE
[T+1s]  tick.service: Failed with result 'exit-code'.
[T+1s]  tick.service: Scheduled restart job, restart counter is at 1.
[T+6s]  tick.service: Stopped Tick test service.
[T+6s]  tick.service: Consumed 0s CPU time.
[T+6s]  tick.service: Started Tick test service.
[T+6s]  crash.sh starting, pid=...
[T+7s]  crash.sh about to fail at ...
...
[T+30s+] tick.service: Start request repeated too quickly.
[T+30s+] tick.service: Failed with result 'start-limit-hit'.
```

The exact T+ offsets depend on `RestartSec=` and how aggressive your machine is. The key observations:

- The service tries 5 times (`StartLimitBurst=5`).
- Each retry is 5 seconds after the previous failure (`RestartSec=5s`).
- After 5 failures in 60 seconds, systemd gives up with `start-limit-hit`.

`systemctl status tick.service` will show:

```
● tick.service - Tick test service
     Loaded: loaded (/etc/systemd/system/tick.service; enabled; preset: enabled)
     Active: failed (Result: exit-code) since ...; 12s ago
```

### Step 2.4 — Recover from the failed state

After `start-limit-hit`, the service won't restart even if you `systemctl start` it — systemd remembers the limit was hit. You must reset:

```bash
sudo systemctl reset-failed tick.service
sudo systemctl start tick.service           # crashes again, but the limit window restarts
```

This is the **production rescue pattern**. When you've fixed the underlying bug, `reset-failed` clears the failed state and lets the service start fresh.

**Acceptance for part 2:** you can articulate, in `01-notes.md`, what each of `RestartSec=`, `StartLimitIntervalSec=`, `StartLimitBurst=` does, and what the journal looks like when each one is hit.

---

## Part 3 — A useful service (45 min)

Now write a service that does something real. Pick one of these (or invent your own; the requirements are below):

### Option A — A `journalctl` follower that mails errors

A service that runs `journalctl -f -p err` and pipes any error-level log to `mail -s "system error"` for delivery. Useful on a personal server.

### Option B — A directory watcher

A service that watches `~/Downloads/` (or any directory you pick), prints the names of newly-added files, and applies a default move-or-rename rule. Use `inotifywait` from `inotify-tools`.

### Option C — A periodic health check

A service that, every 30 seconds, makes an HTTPS request to a URL you care about (your blog, a personal API), and logs the status code. (Note: this is closer to a timer's job. Write it as a long-running service for now; we'll convert to a timer in exercise 02.)

### Requirements (any option)

- The service is a **user unit**, not a system unit. Save under `~/.config/systemd/user/`.
- The script lives under `~/c14-week-05/exercises/01/`.
- The unit has a meaningful `Description=`, a `Documentation=` line pointing at a README or note you write.
- `Type=exec`, `Restart=on-failure`, `RestartSec=5s`.
- `User=` is unnecessary (user units run as you).
- `WantedBy=default.target` in the `[Install]` section.

```bash
# To enable a user unit:
systemctl --user daemon-reload
systemctl --user enable --now my-service.service

# To watch its logs:
journalctl --user -u my-service.service -f

# To make it survive after you log out:
sudo loginctl enable-linger $USER
```

### Acceptance for part 3

- `systemctl --user is-active my-service.service` returns "active."
- The service is doing useful work (the journal shows evidence).
- After `sudo loginctl enable-linger $USER` and an SSH disconnect / reconnect, the service is still running.
- The unit passes `systemd-analyze verify`.

---

## Clean-up

When you're done, decide which units to keep:

```bash
# Keep your part-3 user service if you want it. Remove the system unit:
sudo systemctl disable --now tick.service
sudo rm /etc/systemd/system/tick.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

Verify with `systemctl status tick.service` — should report "could not be found."

---

## Reflection

Save as `~/c14-week-05/exercises/01/01-notes.md` (3-5 sentences each):

1. The first time you `systemctl daemon-reload`-ed, did anything visibly change? What does `daemon-reload` actually do, and why is it required after editing a unit file? (Hint: it does *not* restart any service. Read `man systemctl` on `daemon-reload`.)
2. You set `Restart=on-failure`. What would happen with `Restart=always` instead, given the `crash.sh` script in part 2? Try it. Describe the difference.
3. The journal entries from your part-3 service: are they at priority `info`, `notice`, `warning`, or somewhere else? How did the priority get set? (Look at `journalctl -o json-pretty -u my-service.service` to see the `PRIORITY=` field.)
4. You wrote one system unit and one user unit. Which directories did each live in, and what's the operational reason for the distinction?

Commit the three scripts, the two unit files, and `01-notes.md` to your portfolio repo under `c14-week-05/exercises/01/`.

---

## Common errors and how to read them

| Error in `systemctl status` | Likely cause |
|------------------------------|--------------|
| `Failed at step EXEC spawning ...: No such file or directory` | Wrong `ExecStart=` path. |
| `Failed at step USER spawning ...: No such process` | The `User=` doesn't exist on the system. |
| `start request repeated too quickly` | `StartLimitBurst=` was hit. `reset-failed` to clear. |
| `Unit not found` | Forgot `daemon-reload` after writing the file. |
| `(code=exited, status=203/EXEC)` | `ExecStart=` is a script without execute permission, or the shebang's interpreter is missing. |
| `(code=exited, status=200/CHDIR)` | `WorkingDirectory=` doesn't exist. |
| `(code=killed, signal=KILL)` | `OOM killer` took it; check `dmesg`. Or `systemctl stop` with `KillMode=mixed` and a stubborn child process. |

When `systemctl status` shows a numeric exit code: the `code=exited, status=N` form means "exited with code N". The `code=killed, signal=NAME` form means "killed by signal NAME". The numbers in `status=200/CHDIR`, `status=203/EXEC` are systemd's invented codes for "failed during sandbox setup" — see `systemd.exec(5)` § "Process Exit Codes."

Pin this table somewhere you can find it. You will hit half of these in the remaining exercises.
