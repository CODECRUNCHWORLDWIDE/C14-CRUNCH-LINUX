# Week 5 — Exercises

Three exercises, ~7 hours total. Order matters; do them in sequence. Every unit file you write must pass `systemd-analyze verify` with zero errors.

| # | File | Time | What you build |
|---|------|------|----------------|
| 01 | [exercise-01-first-unit-file.md](./exercise-01-first-unit-file.md) | 2 h | Your first `.service` unit. Enable it. Watch it restart on failure. |
| 02 | [exercise-02-timer-instead-of-cron.md](./exercise-02-timer-instead-of-cron.md) | 2 h | Replace a `cron` job with a `.timer` + `.service` pair. `Persistent=true`, `RandomizedDelaySec=`. |
| 03 | [exercise-03-sandbox-a-service.md](./exercise-03-sandbox-a-service.md) | 3 h | Take a wide-open service and ratchet `systemd-analyze security` from 9.6 toward 1.0. |

Set up a scratch directory:

```bash
mkdir -p ~/c14-week-05/exercises/{01,02,03}
```

Before each exercise: `systemctl --version` shows 255 or newer, you can `sudo`, and you have snapshot-and-rollback capability on your test machine. After each exercise: the unit you wrote is **disabled and removed** unless the exercise says otherwise.

The clean-up incantation at the end of every exercise:

```bash
sudo systemctl disable --now my-unit.service
sudo rm /etc/systemd/system/my-unit.service
sudo systemctl daemon-reload
```

If you skip the `daemon-reload`, systemd will not notice the file is gone and `systemctl status my-unit.service` will still report it. Always reload after removing.
