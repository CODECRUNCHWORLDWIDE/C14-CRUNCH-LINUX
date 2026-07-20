# Exercise 3 — Grep + Pipes on a Real Log

**Goal:** Use `grep`, `sort`, `uniq`, `wc`, `cut`, `awk` to extract insight from a real log file in five queries.

**Estimated time:** 35 minutes.

## Setup

Use any real log file on your system. Try one of:

- `/var/log/syslog` (Debian/Ubuntu) or `/var/log/messages` (Fedora/RHEL)
- `/var/log/auth.log` (SSH and sudo activity)
- `journalctl --no-pager > ~/c14-w1/exercise-03/journal.log` (modern systemd boxes)

Pick one. Cd into a workspace:

```bash
mkdir -p ~/c14-w1/exercise-03
cd ~/c14-w1/exercise-03
cp /var/log/syslog .          # or use the journalctl dump above
```

## The five queries

Answer each in `answers.md` with the command and its output (first 10 lines max).

1. **How many total log lines are in this file?** Use `wc -l`.

2. **How many distinct programs (column 5 or so, depending on format) wrote to this log?** *(Hint: `awk '{print $5}' | sort | uniq | wc -l` — but inspect first to confirm which column has the program name.)*

3. **Top 10 programs by line count** (which programs are noisiest?). *(Hint: `awk '{print $5}' | sort | uniq -c | sort -rn | head`.)*

4. **Every line mentioning "error" or "fail" (case-insensitive).** *(Hint: `grep -iE "error|fail"`.)*

5. **For one of the top programs from query 3, the last 20 messages it produced.** *(Hint: `grep <progname> syslog | tail -20`.)*

## Acceptance criteria

- [ ] All five answers committed in `answers.md`.
- [ ] Each command uses pipes — no temporary files.
- [ ] You can explain what each stage of each pipeline does.

## Stretch

- Find any **failed login attempts** in `/var/log/auth.log` (`Failed password`).
- Plot a chart of log lines per hour. *(Hint: `awk '{print $3}' | cut -c1-2 | sort | uniq -c`.)*
- Watch the log live with `tail -f /var/log/syslog | grep --color sudo`.

## Submission

Commit `answers.md` to your portfolio under `c14-week-01/exercise-03/`.
