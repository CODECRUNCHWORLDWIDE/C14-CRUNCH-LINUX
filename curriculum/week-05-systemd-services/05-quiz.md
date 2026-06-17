# Week 5 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 6.

---

**Q1.** Which three sections does every typical `.service` unit file contain?

- A) `[Header]`, `[Body]`, `[Footer]`
- B) `[Unit]`, `[Service]`, `[Install]`
- C) `[Metadata]`, `[Process]`, `[Boot]`
- D) `[Required]`, `[Optional]`, `[OnFailure]`

---

**Q2.** What is the difference between `Type=simple` and `Type=exec`?

- A) `simple` is faster; `exec` is slower.
- B) `simple` is for shell scripts; `exec` is for compiled binaries.
- C) `simple` reports "started" the moment systemd calls `fork()`; `exec` waits until `execve()` returns successfully. `exec` gives better error messages when `ExecStart=` points to a missing binary.
- D) They are aliases for the same value.

---

**Q3.** A service with `Restart=always` and a startup bug crashes immediately on every restart. Which directives prevent it from crash-looping forever and burning CPU?

- A) `RestartSec=` alone.
- B) `RestartSec=` and `StartLimitBurst=` together.
- C) `OnFailure=` triggering a notification.
- D) systemd handles this automatically; no directives needed.

---

**Q4.** You want a `.timer` to catch up if the machine was asleep at its scheduled time. Which directive enables this?

- A) `OnCalendar=daily`
- B) `Persistent=true`
- C) `AccuracySec=1us`
- D) `WakeSystem=true`

---

**Q5.** What does `systemctl enable foo.service` actually do on disk?

- A) Starts the service.
- B) Copies the unit file into `/lib/systemd/system/`.
- C) Creates a symlink in the target directory referenced by `WantedBy=` (e.g., `/etc/systemd/system/multi-user.target.wants/foo.service`).
- D) Marks the service as "active" in the systemd database.

---

**Q6.** A user unit (in `~/.config/systemd/user/`) stops running when you log out of the SSH session. What enables it to keep running after logout?

- A) `Restart=always` in the `[Service]` section.
- B) `WantedBy=multi-user.target` in the `[Install]` section.
- C) `sudo loginctl enable-linger $USER`.
- D) Moving the unit to `/etc/systemd/system/`.

---

**Q7.** Which `journalctl` invocation shows the last 50 error-or-worse log entries for `nginx.service` from the current boot?

- A) `journalctl -u nginx.service -p err -b -n 50`
- B) `journalctl --grep "error" nginx`
- C) `tail -n 50 /var/log/nginx.service.log`
- D) `systemctl show nginx.service -p Logs`

---

**Q8.** What does `DynamicUser=true` do, and which directives does it imply?

- A) Creates a `dynamicuser` user in `/etc/passwd` at install time. Implies nothing else.
- B) Allocates a transient UID for the service that exists only while the service runs. Implies `PrivateTmp=`, `RemoveIPC=`, `ProtectSystem=strict`, `ProtectHome=read-only`, `NoNewPrivileges=`.
- C) Lets the service create new users via `useradd`. Implies `CapabilityBoundingSet=CAP_SYS_ADMIN`.
- D) Runs the service as the user who ran `systemctl start`.

---

**Q9.** A `.timer` unit named `backup.timer` has no `Unit=` directive in its `[Timer]` section. Which `.service` does it activate when it fires?

- A) The first `.service` that has `BindsTo=backup.timer`.
- B) `backup.service` — systemd pairs by basename.
- C) `default.service` in the same directory.
- D) None; `Unit=` is required.

---

**Q10.** You sandbox a Python web service with `ProtectSystem=strict`. The service crashes on first request with `Errno 13 Permission denied` writing to `/var/lib/myapp/cache`. What's the fix?

- A) Add `ReadWritePaths=/var/lib/myapp/cache` to the `[Service]` section.
- B) Change `ProtectSystem=strict` to `ProtectSystem=true`.
- C) Run the service as root.
- D) Move the cache to `/tmp`.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **B** — `[Unit]` (metadata, dependencies), `[Service]` (the process), `[Install]` (what `enable` does). Every `.service` follows this shape. Timers add `[Timer]`; sockets add `[Socket]`; mounts add `[Mount]`.
2. **C** — `Type=exec` waits for `execve()` to return before reporting the service as started. `Type=simple` reports started at `fork()` time. For new units, `Type=exec` is strictly better.
3. **B** — `RestartSec=` controls the delay between attempts; `StartLimitBurst=` (with `StartLimitIntervalSec=`) caps the total number of attempts in a window. After the burst limit, systemd gives up with `start-limit-hit`. Without `StartLimitBurst=`, the crash-loop has a guard from systemd's default but it isn't aggressive enough for fast crashes.
4. **B** — `Persistent=true` stores the last-run time and fires immediately on the first activation after a missed run. Essential for laptops and ephemeral VMs.
5. **C** — `enable` creates a symlink in the target's `.wants/` directory. The unit file itself is untouched. `disable` removes the symlink. `enable` does **not** start the service; use `enable --now` for both.
6. **C** — `loginctl enable-linger USER` tells systemd to keep `systemd --user` running after the user logs out. Without it, the per-user systemd exits and stops all user services. The other answers are unrelated.
7. **A** — `-u nginx.service` filters by unit, `-p err` by priority (err and worse), `-b` to this boot, `-n 50` last 50 entries. All four flags compose. The other answers either don't work or use the wrong tools.
8. **B** — `DynamicUser=true` invents a UID in the range 61184-65519, uses it for the service, frees it on stop. Implies a bundle of hardening directives. The strongest single isolation knob in systemd.
9. **B** — systemd pairs timers and services by basename (`backup.timer` ↔ `backup.service`). You can override with `Unit=other.service` in the `[Timer]` section if you want a different pairing.
10. **A** — `ProtectSystem=strict` makes the entire filesystem read-only except for explicitly declared `ReadWritePaths=`. Add the path; do not weaken the protection. The other answers either reduce security or move the problem elsewhere.

</details>

If you scored 9+: move to homework. 7-8: re-read the lecture sections you missed (especially `Type=` selection and the four-knob crash-loop guard). <7: re-read both lectures from the top, then redo exercise 01.
