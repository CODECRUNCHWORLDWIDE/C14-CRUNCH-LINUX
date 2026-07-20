# Week 5 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-05/homework/`.

These are practice problems between the exercises (which drilled the basics) and the mini-project (which asks you to compose freely). Every unit file you write must pass `systemd-analyze verify` with zero errors and score 3.0 or better on `systemd-analyze security` (unless explicitly marked otherwise).

---

## Problem 1 — Your unit-file template (45 min)

Write `homework/01-template.service` — a generic starter you will copy for every system service for the rest of your career. It must include:

- All three sections: `[Unit]`, `[Service]`, `[Install]`.
- A `Description=` placeholder, a `Documentation=` line, an `After=network-online.target` and `Wants=network-online.target` pair.
- `Type=exec`, an `ExecStart=` placeholder with the absolute-path requirement noted in a comment.
- The four-knob crash-loop guard: `Restart=on-failure`, `RestartSec=5s`, `StartLimitIntervalSec=60s`, `StartLimitBurst=5`.
- A `User=` and `Group=` placeholder (commented hint to use a dedicated system user).
- The eight sandbox directives from Lecture 2: `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`, `NoNewPrivileges=true`, `CapabilityBoundingSet=`, `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`, plus `ProtectKernelTunables=true` and `RestrictNamespaces=true`.
- `WantedBy=multi-user.target` in `[Install]`.

Write it as a real file (with `<PLACEHOLDER>` markers for the per-service fields). Save as `01-template.service`.

**Acceptance:** Save the template. `sudo cp 01-template.service /etc/systemd/system/test.service && sudo systemd-analyze verify /etc/systemd/system/test.service` — `verify` is clean (or only reports "missing ExecStart" if you left the placeholder unedited; that counts). `rm` after.

---

## Problem 2 — Convert a real script to a service (60 min)

Pick one of your three Week 4 mini-project scripts (`backup.sh`, `rotate-logs.sh`, `disk-usage.sh`). Write a `.service` unit that runs it.

**Specification:**

- The unit is a **system unit** (`/etc/systemd/system/`).
- Use `Type=oneshot` (the scripts are one-shot operations).
- The service runs as a dedicated user (`User=cron-job` or similar — create it first).
- Sandbox to score 3.0 or lower on `systemd-analyze security`.
- The script's working directory is set with `WorkingDirectory=`.
- Any directories the script writes to are declared with `ReadWritePaths=`.
- The script's output goes to the journal (no redirect to a file).

**Tests:**

```bash
sudo systemctl daemon-reload
sudo systemctl start <your-unit>.service
journalctl -u <your-unit>.service -n 30
```

The service should report success and the journal should show what the script did.

**Acceptance:** Unit file in `homework/02-<scriptname>.service`. A `02-notes.md` with the `systemd-analyze security` score and the journal output from one run.

---

## Problem 3 — Schedule it with a timer (60 min)

Take the service from problem 2 and add a `.timer` that runs it on a meaningful schedule. Examples:

- `backup.sh` — daily at 02:30, randomized by 30 min.
- `rotate-logs.sh` — weekly on Sunday at 04:00, randomized by 1 hour.
- `disk-usage.sh` — every 6 hours, on a monotonic schedule (`OnUnitActiveSec=6h`).

**Specification:**

- Timer basename matches the service basename.
- `OnCalendar=` for wall-clock or `OnUnitActiveSec=` for relative; explain your choice in `03-notes.md`.
- `Persistent=true` for wall-clock timers.
- `RandomizedDelaySec=` for any timer that might run on multiple machines.
- `AccuracySec=` set explicitly (1 minute is fine).
- `[Install]` section with `WantedBy=timers.target`.

**Tests:**

```bash
systemd-analyze calendar 'YOUR CALENDAR SPEC'
sudo systemctl enable --now <your-unit>.timer
systemctl list-timers
```

`list-timers` must show your timer with a `NEXT` time matching the calendar spec.

**Acceptance:** Timer unit in `homework/03-<scriptname>.timer`. `03-notes.md` with the calendar spec, the `systemd-analyze calendar` output, and a `systemctl list-timers` snippet.

---

## Problem 4 — A user service (45 min)

Write a useful **user unit** (`~/.config/systemd/user/`) for something you actually want running on your machine. Examples:

- A music-library scanner that runs nightly.
- A `git fetch --all` across your repo collection every hour.
- A "low-battery warning" service that runs while you're logged in.
- A pomodoro timer / break-reminder.

**Specification:**

- Saved under `~/.config/systemd/user/04-<name>.service`.
- Runs without `sudo` for installation and management.
- `[Install]` section uses `WantedBy=default.target` (the user target equivalent of `multi-user.target`).
- If it's a daemon (long-running), uses `Restart=on-failure`.
- If it's a periodic task, has a corresponding `.timer`.

**Tests:**

```bash
systemctl --user daemon-reload
systemctl --user enable --now 04-<name>.service       # or .timer
journalctl --user -u 04-<name>.service -n 30
```

Then `sudo loginctl enable-linger $USER`, log out, log back in, and confirm the unit is still active.

**Acceptance:** Unit file in `homework/04-<name>.service` (plus `.timer` if applicable). `04-notes.md` describing what it does, why it's a user unit (not system), and proof that it survives an SSH disconnect-reconnect cycle.

---

## Problem 5 — Override a vendor unit (45 min)

`systemctl edit <unit>` creates a drop-in under `/etc/systemd/system/<unit>.d/override.conf`. This is the polite way to modify a vendor-supplied unit (e.g., `nginx.service`, `postgresql.service`) without editing the vendor file (which gets overwritten on package upgrade).

**Specification:**

- Pick a vendor unit on your machine: `cron.service`, `systemd-resolved.service`, `getty@.service`, or any service already installed.
- Run `sudo systemctl edit <unit>` and add at least two directives.
- Suggested edits (pick one):
  - Tighten the sandbox of an already-installed service.
  - Add a `RestartSec=` and `StartLimitBurst=` to a service that currently lacks them.
  - Set a `MemoryMax=` resource cap on a service that could grow unbounded.
- The drop-in must be **additive only** (no overwrites of the vendor's existing `ExecStart=`, `User=`, etc.).
- Document **which** vendor unit you picked and **why** the override is safe.

**Tests:**

```bash
systemctl cat <unit>           # should show the vendor file plus your drop-in
sudo systemctl daemon-reload
sudo systemctl restart <unit>  # service still works?
systemctl status <unit>
```

**Acceptance:** The drop-in file `/etc/systemd/system/<unit>.d/override.conf`, copied to `homework/05-override.conf`. `05-notes.md` with the chosen unit, the change rationale, the `systemctl cat` output, and confirmation the service still runs.

Clean up afterward (`sudo systemctl revert <unit>` removes drop-ins) unless you want to keep the override.

---

## Problem 6 — Reflection (90 min)

`homework/06-reflection.md`, 600-800 words:

1. Pick the `Type=` value you'd use for each of these (one sentence rationale each):
   a) A Go HTTP API that calls `http.ListenAndServe()`.
   b) A shell script that runs `tar`, then `gzip`, then exits.
   c) A C daemon that `fork()`s into the background and writes its PID to `/run/foo.pid`.
   d) A Python service that loads a 4GB embedding model into RAM before accepting requests.
   e) A `systemd-tmpfiles --create` invocation that runs once at boot.
2. The lecture claimed: "Almost every service can drop to exposure 2.0 or lower without functional changes." Pick three services running on your machine right now. Run `systemd-analyze security` against each. Which one has the worst score? Look at the ✗ lines — pick three you could fix without breaking the service. (Don't actually fix them unless you understand them. This is a scouting exercise.)
3. Compare `cron` and systemd timers, in your own words, in 4-6 sentences. When is `cron` still the right tool? (There are scenarios.) When is a systemd timer obviously better?
4. The `Persistent=true` directive is laptop-friendly. The `WakeSystem=true` directive (we didn't cover it in lecture; look it up in `systemd.timer(5)`) is even more laptop-friendly. Read the man page entry. What does it do, and what risk does it carry?
5. Sketch what your **Week 5 mini-project** will look like. Three bullets each on: the Python web app, the unit file, and the deployment story.
6. Cite the Bash Yellow caution line at the top of your favorite lecture or exercise from this week. (Loyalty test repeats.)

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 1 h |
| 3 | 1 h |
| 4 | 45 min |
| 5 | 45 min |
| 6 | 1.5 h |
| **Total** | **~6 h** |

After homework, ship the [mini-project](./mini-project/README.md).
