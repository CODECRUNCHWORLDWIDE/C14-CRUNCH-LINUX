# Exercise 02 — A Timer Instead of `cron`

**Time:** ~2 hours. **Goal:** Take a `cron` entry — yours or a textbook one — and rewrite it as a `.timer` + `.service` pair. Compare the two. Build the muscle for `OnCalendar=`, `Persistent=true`, `RandomizedDelaySec=`, and the `systemd-analyze calendar` validator.

You will need systemd 255+, `sudo`, and a willingness to set the system clock forward briefly (to test `Persistent=`). Verify:

```bash
systemctl --version | head -1
systemd-analyze calendar 'daily'
```

Scratch directory:

```bash
mkdir -p ~/c14-week-05/exercises/02
cd ~/c14-week-05/exercises/02
```

---

## Part 1 — The `cron` baseline (15 min)

You will rewrite a `cron` entry. If you have a real one, use it. If not, use this one:

```cron
# /etc/cron.d/log-rotator
30 3 * * * root /usr/local/bin/rotate-logs.sh /var/log/myapp
```

This says: at 03:30 every day, run the log rotator as root.

If you wrote `rotate-logs.sh` in Week 4's mini-project, use that one. If not, write a trivial stand-in:

```bash
# ~/c14-week-05/exercises/02/rotate-logs.sh
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

DIR="${1:?usage: $0 LOGDIR}"
printf '[%s] rotating logs in %s\n' "$(date -Iseconds)" "$DIR" >&2

# A real rotator would gzip *.log files older than 7 days, delete older than 30.
# For this exercise, we just print what would happen.
find "$DIR" -type f -name '*.log' -mtime +7 -print 2>/dev/null \
    | while IFS= read -r f; do
        printf '[%s] would gzip: %s\n' "$(date -Iseconds)" "$f" >&2
    done
```

`chmod +x rotate-logs.sh`. Test by hand against `/var/log` (read-only, harmless):

```bash
./rotate-logs.sh /var/log
```

You should see "rotating logs in /var/log" and possibly several "would gzip" lines. Exit code is 0.

The `cron` form has four problems we will fix by converting to systemd:

1. **Missed runs after sleep.** If your laptop is asleep at 03:30, the run is lost. cron has no notion of "catch up."
2. **No structured logs.** cron sends output via mail or, more commonly, into `/var/log/cron` mixed with everyone else's. No per-job journal.
3. **No restart on failure.** If `rotate-logs.sh` exits non-zero, cron silently does nothing.
4. **No load distribution.** Every cron job at 03:30 starts at exactly 03:30 — every machine, every customer, every tenant.

---

## Part 2 — The `.service` (30 min)

Write the service unit. Since the job is "run once and exit," `Type=oneshot` is correct.

Save as `/etc/systemd/system/log-rotator.service`:

```ini
[Unit]
Description=Rotate logs under /var/log/myapp
Documentation=https://github.com/CODE-CRUNCH-CLUB/C14-CRUNCH-LINUX/blob/main/curriculum/week-05-systemd-services/exercises/exercise-02-timer-instead-of-cron.md

[Service]
Type=oneshot
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/02/rotate-logs.sh /var/log
User=YOUR_USERNAME
# Mild sandboxing - cheap wins
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true
```

Note: **no `[Install]` section**. A oneshot service triggered by a timer doesn't need `WantedBy=`; the timer is what gets enabled, and the timer pulls the service in on each fire.

Validate, reload, test by manual run:

```bash
sudo systemd-analyze verify /etc/systemd/system/log-rotator.service
sudo systemctl daemon-reload
sudo systemctl start log-rotator.service
journalctl -u log-rotator.service -n 20
```

You should see the "rotating logs" output in the journal, attributed to `log-rotator.service`. The service should show as `inactive (dead)` immediately after — that's correct for a oneshot.

---

## Part 3 — The `.timer` (30 min)

Save as `/etc/systemd/system/log-rotator.timer`:

```ini
[Unit]
Description=Daily log rotation at 03:30
Documentation=https://github.com/CODE-CRUNCH-CLUB/C14-CRUNCH-LINUX/blob/main/curriculum/week-05-systemd-services/exercises/exercise-02-timer-instead-of-cron.md

[Timer]
OnCalendar=*-*-* 03:30:00
Persistent=true
RandomizedDelaySec=10min
AccuracySec=1min

[Install]
WantedBy=timers.target
```

Things to note:

- The timer's basename (`log-rotator`) matches the service's basename. systemd pairs them automatically. If you wanted a different pairing, add `Unit=log-rotator.service` to the `[Timer]` section.
- `OnCalendar=*-*-* 03:30:00` is the calendar-spec form of "03:30 every day." Equivalent to `OnCalendar=daily` with a 03:30 offset (which is harder to express in `OnCalendar=`).
- `Persistent=true` is the laptop-and-VM fix. Missed runs catch up at next wake.
- `RandomizedDelaySec=10min` spreads the start time by up to 10 minutes. If you run this on 50 servers, they no longer all hit storage at exactly 03:30.
- `AccuracySec=1min` tells systemd "you can fire any time within 1 minute of the target." Default is 1 minute; explicit here for clarity. Lower values consume more power because systemd has to wake more often.

### Step 3.1 — Validate the calendar spec

```bash
systemd-analyze calendar '*-*-* 03:30:00'
```

Output:

```
  Original form: *-*-* 03:30:00
Normalized form: *-*-* 03:30:00
    Next elapse: Wed 2026-05-14 03:30:00 UTC
       From now: 13h 23min left
```

Always run this. The next-elapse line is your sanity check.

### Step 3.2 — Enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now log-rotator.timer
systemctl list-timers --all log-rotator.timer
```

The `list-timers` output shows when it will next fire:

```
NEXT                         LEFT      LAST  PASSED  UNIT                  ACTIVATES
Wed 2026-05-14 03:30:00 UTC  13h 23min n/a   n/a     log-rotator.timer     log-rotator.service
```

### Step 3.3 — Force a run

You don't have to wait until 03:30:

```bash
sudo systemctl start log-rotator.service
```

This runs the service immediately, regardless of the timer. The timer is unaffected — it still fires at 03:30. Useful for testing.

After the run:

```bash
journalctl -u log-rotator.service -n 20
systemctl status log-rotator.timer
```

The timer status should now show `Last triggered: <a moment ago>`.

---

## Part 4 — Testing `Persistent=true` (30 min)

To prove `Persistent=true` actually catches missed runs, we need to make the timer miss one. Two ways:

### Option A — Stop and restart

```bash
sudo systemctl stop log-rotator.timer

# Wait. Let 03:30 pass without the timer running. (Pick a time and wait, or
# advance the test by setting OnCalendar= to the very near future.)

sudo systemctl start log-rotator.timer
# With Persistent=true, the service fires immediately (catching the missed run).
# With Persistent=false, no run happens; the next fire is the next 03:30.
```

### Option B — A short-interval test timer

Easier and faster. Save as `/etc/systemd/system/persistent-test.timer`:

```ini
[Unit]
Description=Test timer for Persistent= behavior

[Timer]
OnCalendar=*:*:0/30      # every 30 seconds, on :00 and :30
Persistent=true

[Install]
WantedBy=timers.target
```

And `/etc/systemd/system/persistent-test.service`:

```ini
[Unit]
Description=Test service for Persistent= behavior

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo "fired at $(date -Iseconds)"'
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now persistent-test.timer

# Watch it tick
journalctl -u persistent-test.service -f
# You should see one line per 30 seconds. Ctrl-C after a minute.

# Now stop the timer for a minute, then restart
sudo systemctl stop persistent-test.timer
sleep 90
sudo systemctl start persistent-test.timer

# Check the journal - did it fire immediately on restart?
journalctl -u persistent-test.service -n 10
```

With `Persistent=true` and `OnCalendar=*:*:0/30`, on restart the timer notices it missed several 30-second marks and fires once immediately. With `Persistent=false`, it waits for the next mark.

Clean up the test units when done:

```bash
sudo systemctl disable --now persistent-test.timer
sudo rm /etc/systemd/system/persistent-test.{timer,service}
sudo systemctl daemon-reload
```

---

## Part 5 — Compare cron vs systemd timer (15 min)

In `~/c14-week-05/exercises/02/02-notes.md`, fill in this comparison table for your `log-rotator` example:

| Feature | `cron` | systemd timer |
|---------|--------|---------------|
| Schedule expression | | |
| Per-job logs | | |
| Restart on failure | | |
| Catch missed runs | | |
| Load distribution | | |
| Multi-user | | |
| Lines of config | | |
| Tooling to validate the schedule | | |

Then write 4-6 sentences on:

1. Which form is more readable for the simple "daily at 03:30" case?
2. Which form is more powerful for the "every 30 seconds during business hours" case?
3. The `cron` form lives in `/etc/cron.d/`; the systemd form lives in `/etc/systemd/system/`. What user owns each, and what user does the job run as in each form?
4. systemd timers can chain on monotonic time (`OnUnitActiveSec=`). cron cannot. Sketch a use case where that matters.

---

## Clean-up

```bash
sudo systemctl disable --now log-rotator.timer
sudo rm /etc/systemd/system/log-rotator.{timer,service}
sudo systemctl daemon-reload
```

`systemctl list-timers --all log-rotator.timer` should return "0 timers listed."

---

## Acceptance criteria

- `log-rotator.timer` and `log-rotator.service` both pass `systemd-analyze verify`.
- `systemctl list-timers` showed `log-rotator.timer` in the schedule.
- `sudo systemctl start log-rotator.service` triggered the journal entry.
- You can articulate, in `02-notes.md`, the four advantages of timers over cron.
- After clean-up, no `log-rotator` units remain.

---

## Stretch goals

- Convert your Week 4 mini-project's `backup.sh` into a timer-driven service. Schedule daily at 02:00 with `RandomizedDelaySec=30min`.
- Write a **user-mode** timer (under `~/.config/systemd/user/`) for something personal — a calendar sync, an inbox cleanup, a backup of your dotfiles. No `sudo` required, runs as you, follows you across reboots once `loginctl enable-linger` is set.
- Read `man systemd.timer` and find a directive we didn't use (e.g., `WakeSystem=true`, which can wake the machine from suspend to fire the timer). Write a one-paragraph note on what it does and a scenario you'd reach for it.
- Convert the `cron` baseline to a `cron.d`-equivalent that uses `anacron` instead. Then write a paragraph on what `anacron` does and how it overlaps with `Persistent=true`.

---

## Common errors

| Symptom | Likely cause |
|---------|--------------|
| `systemctl list-timers` shows nothing | Forgot `daemon-reload` or `enable --now`. |
| Timer fires once on enable, then not again | `OnCalendar=daily` without `Persistent=true` and the system clock advanced past the next firing. |
| Service runs every minute instead of every hour | Calendar spec typo. Run `systemd-analyze calendar` on it. |
| `Failed to compute next elapse for OnCalendar=...` | The calendar spec is invalid (e.g., `Mon..Fri 9:30:00` — needs `*-*-* 09:30:00`). |
| Service runs but produces no journal output | Your script writes to a file or `/dev/null`. Make it write to stdout/stderr. |

The last one bites people coming from cron. cron mails stdout; systemd journals stdout. Same idea, different sink.
