# Mini-Project — A systemd-Managed Python Web Service

> Write a small Python web app and ship it as a `systemd` service. Restart policy. journald logging. A non-trivial sandbox. Survives reboot. A README that another engineer could use to deploy it on a fresh VM in 10 minutes.

**Estimated time:** 6-7 hours, spread Thursday-Saturday.

This mini-project is the deliverable that proves Week 5 took. The Python app you write is deliberately tiny — you are not being graded on the web framework. You are being graded on **the unit file** and **the operational story**: how it starts, how it restarts, how you read its logs, how it survives boot, how it's sandboxed.

The point of the mini-project is to drill **the eight-step lifecycle** (Lecture 1, §8) end-to-end on a service that does something real. You will write the app, write the unit, write the timer (if appropriate), validate, deploy, ratchet the sandbox, document.

---

## Deliverable

A directory in your portfolio repo `c14-week-05/mini-project/` containing:

1. `README.md` — your write-up. Design notes, the unit-file structure, the security score, deployment instructions, known limitations.
2. `app/` — the Python web app. A `main.py`, a `requirements.txt`, optionally a `pyproject.toml`. Whatever framework you like (Flask, FastAPI, `http.server` from stdlib — all fine).
3. `systemd/` — the unit files. At least one `.service`. Optionally a `.timer`, a `.socket`, drop-ins.
4. `install.sh` — a script that, given a clean Ubuntu 24.04 or Fedora 41 machine, deploys the service: installs system packages, creates the user, copies files, installs the unit, enables and starts it. Idempotent.
5. `uninstall.sh` — the reverse. Removes the service, deletes the user, cleans up.
6. `tests/test-deploy.sh` — a script that exercises `install.sh`, makes an HTTP request to the running service, asserts success, then `uninstall.sh`-es. The end-to-end smoke test.
7. `analyze/` — `before.txt` (security score of the un-hardened unit) and `after.txt` (security score of the final unit). Required evidence that the sandbox was applied incrementally.

---

## The Python web app

Pick a small, well-scoped idea. Suggested:

### Option A — A URL shortener (recommended starter)

- `GET /` — a one-line form for submitting URLs.
- `POST /shorten` — accepts a `url=...` form, returns a short code, persists the mapping to a JSON file.
- `GET /<code>` — 302 redirects to the long URL.
- `GET /metrics` — returns a JSON blob of total redirects, total URLs shortened.

### Option B — A pastebin

- `GET /` — a textarea form.
- `POST /paste` — accepts text, stores it, returns a URL with a random ID.
- `GET /<id>` — returns the paste text.
- `GET /<id>/raw` — returns the paste as `text/plain`.

### Option C — A simple feed reader

- `GET /` — lists items from a configured RSS/Atom feed.
- `POST /refresh` — re-fetches the feed (rate-limited).
- The fetch logic uses a periodic timer to update every 15 minutes.

### Option D — Your own idea

Any small web app whose state fits in a single JSON file or SQLite database. Anything bigger and the "small" part of the rubric is lost.

### App requirements (any option)

- **Single binary or single script.** No multi-process model. systemd manages one process; that process is your app.
- **Listens on `127.0.0.1:<PORT>`** by default. Read the port from `$PORT` (with a default of 8080). Bind to `0.0.0.0` only if your `[Service]` directives lock down what counts as "exposed" — defer to a reverse proxy for the real-world case.
- **Logs to stdout/stderr.** Not to a file. systemd captures stdout into the journal; your file would bypass it.
- **Reads config from a directory.** Either `/etc/<app-name>/config.json` or `$CONFIGURATION_DIRECTORY/config.json` (the latter is what `DynamicUser=true` + `ConfigurationDirectory=` provides).
- **Persists data to a writable directory.** Either `/var/lib/<app-name>/` or `$STATE_DIRECTORY/`.
- **Handles `SIGTERM` gracefully.** When systemd sends SIGTERM (on `systemctl stop`), the app should flush pending writes and exit within `TimeoutStopSec=` (default 90s; set to 10s for a web app).
- **Survives kills.** A `SIGKILL` mid-write should leave the data file readable on next start. Use atomic writes (`open(tmp).write(data); os.rename(tmp, final)`).

---

## The unit file

Save under `systemd/<app-name>.service`. Required directives:

```ini
[Unit]
Description=<one-line description of what the app does>
Documentation=<link to your repo's README, plus systemd man pages>
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
ExecStart=/usr/local/bin/<app-name>     # or wherever install.sh puts it
Environment=PORT=8080
Restart=on-failure
RestartSec=5s
StartLimitIntervalSec=60s
StartLimitBurst=5
TimeoutStopSec=10s

# User isolation — choose one approach:
#   (a) DynamicUser=true  (strongest, requires StateDirectory=, ConfigurationDirectory=)
#   (b) User=<app-name> Group=<app-name>  (static, simpler)
DynamicUser=true
StateDirectory=<app-name>
LogsDirectory=<app-name>
ConfigurationDirectory=<app-name>
RuntimeDirectory=<app-name>

# Filesystem sandbox
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Privilege sandbox
NoNewPrivileges=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

# Namespace / misc
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=false       # CPython doesn't need this; flip to true if your interpreter does
SystemCallFilter=@system-service
SystemCallFilter=~@privileged ~@resources

[Install]
WantedBy=multi-user.target
```

The `[Service]` block is roughly 25 directives. That's not unusual for a production service. Each one is one line; each one earns its keep.

### If you also write a `.timer`

For option C (the feed reader), a periodic refresh:

```ini
# systemd/<app-name>-refresh.timer
[Unit]
Description=Refresh the <app-name> feed cache

[Timer]
OnUnitActiveSec=15min
OnBootSec=2min
RandomizedDelaySec=1min
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# systemd/<app-name>-refresh.service
[Unit]
Description=One-shot feed refresh for <app-name>

[Service]
Type=oneshot
ExecStart=/usr/bin/curl -fsS http://127.0.0.1:8080/refresh
User=<app-name>
# Lighter sandbox - this is a curl, no big needs
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true
```

The timer hits the running web app's `/refresh` endpoint. The app does the work. Clean separation.

---

## The `install.sh`

Idempotent. Re-running it is a no-op on a successfully-installed system.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

APP_NAME="<app-name>"
INSTALL_DIR="/usr/local/lib/${APP_NAME}"
BIN_LINK="/usr/local/bin/${APP_NAME}"
UNIT_FILE="/etc/systemd/system/${APP_NAME}.service"
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

require_root() { [[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 77; }; }
log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }

main() {
    require_root

    # 1. Install OS packages (python3, python3-venv, etc.)
    if command -v apt-get >/dev/null; then
        apt-get update
        apt-get install -y python3 python3-venv
    elif command -v dnf >/dev/null; then
        dnf install -y python3 python3-virtualenv
    else
        echo "unsupported distro" >&2; exit 78
    fi
    log "OS packages installed"

    # 2. Install the app to /usr/local/lib/<app-name>/
    mkdir -p "$INSTALL_DIR"
    cp -r -- "$SRC_DIR/app/." "$INSTALL_DIR/"
    log "app files copied to $INSTALL_DIR"

    # 3. Create venv and install requirements
    python3 -m venv "$INSTALL_DIR/.venv"
    "$INSTALL_DIR/.venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"
    log "Python dependencies installed in venv"

    # 4. Create the launcher
    cat > "$BIN_LINK" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_DIR/.venv/bin/python" "$INSTALL_DIR/main.py" "\$@"
EOF
    chmod +x "$BIN_LINK"
    log "launcher installed at $BIN_LINK"

    # 5. Install the unit file
    cp -- "$SRC_DIR/systemd/${APP_NAME}.service" "$UNIT_FILE"
    systemd-analyze verify "$UNIT_FILE"
    log "unit file validated and installed"

    # 6. Reload + enable + start
    systemctl daemon-reload
    systemctl enable --now "${APP_NAME}.service"
    log "service enabled and started"

    # 7. Health check
    sleep 2
    if curl -fsS http://127.0.0.1:8080/ >/dev/null; then
        log "health check passed"
    else
        echo "service started but health check failed" >&2
        systemctl status "${APP_NAME}.service" --no-pager
        exit 75
    fi
}

main "$@"
```

This is one possible structure. Yours may differ; the requirement is that **`install.sh` deploys the entire system from a clean machine, idempotently**, and exits non-zero if anything fails.

---

## The `uninstall.sh`

The inverse. Must remove every file `install.sh` created. Including the journal-stored data if you want a truly clean uninstall (`journalctl --vacuum-time=1s` after `systemctl disable`).

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

APP_NAME="<app-name>"

require_root() { [[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 77; }; }

main() {
    require_root

    systemctl disable --now "${APP_NAME}.service" 2>/dev/null || true
    rm -f -- "/etc/systemd/system/${APP_NAME}.service"
    rm -f -- "/usr/local/bin/${APP_NAME}"
    rm -rf -- "/usr/local/lib/${APP_NAME}"
    rm -rf -- "/var/lib/${APP_NAME}"   # if you used static User= rather than DynamicUser=
    rm -rf -- "/etc/${APP_NAME}"
    systemctl daemon-reload
    systemctl reset-failed 2>/dev/null || true

    echo "[$(date -Iseconds)] $APP_NAME uninstalled" >&2
}

main "$@"
```

---

## The deployment test

`tests/test-deploy.sh` — a smoke test of the full install / use / uninstall loop.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

APP_NAME="<app-name>"
SRC_DIR="$(cd "$(dirname "$0")/.." && pwd)"

require_root() { [[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 77; }; }

main() {
    require_root

    echo "=== Install ==="
    "$SRC_DIR/install.sh"

    echo "=== HTTP smoke test ==="
    curl -fsS http://127.0.0.1:8080/ | head -5

    echo "=== Restart resilience ==="
    pid=$(systemctl show -p MainPID --value "${APP_NAME}.service")
    kill -TERM "$pid"
    sleep 8
    curl -fsS http://127.0.0.1:8080/ | head -1
    echo "OK: survived TERM + restart"

    echo "=== Journal contains startup log ==="
    journalctl -u "${APP_NAME}.service" --since "5 minutes ago" -n 5

    echo "=== Security score ==="
    systemd-analyze security "${APP_NAME}.service" | tail -1

    echo "=== Uninstall ==="
    "$SRC_DIR/uninstall.sh"

    echo "=== Verify gone ==="
    systemctl is-active "${APP_NAME}.service" >/dev/null 2>&1 && {
        echo "FAIL: service still active"; exit 1;
    }

    echo
    echo "PASS: test-deploy.sh"
}

main "$@"
```

Run with: `sudo bash tests/test-deploy.sh`. The expected output is six section banners, one HTTP response, one journal excerpt, one security score, and a final `PASS`.

---

## The README

Your `mini-project/README.md` answers:

1. **What the app does** — one paragraph, two screenshots or curl examples.
2. **How to deploy** — `git clone`, `cd`, `sudo ./install.sh`. That's it.
3. **The unit-file design** — annotated: why each directive is there, why each sandbox setting is appropriate, why you chose `Type=exec` vs `Type=notify`, why `Restart=on-failure` vs `Restart=always`.
4. **The security score** — `before.txt` vs `after.txt` diff. The number should be 2.0 or lower.
5. **How to read its logs** — the three or four `journalctl` incantations someone debugging at 03:00 needs.
6. **How to upgrade** — re-run `install.sh`. (If your structure makes that not work, fix the structure.)
7. **Known limitations** — at minimum three. Honesty here scores points.
8. **What's next** — week 6 will put this behind nginx and a firewall. Note that.

---

## Acceptance criteria

- The Python app runs in isolation (`python3 app/main.py` from a venv works).
- `sudo bash tests/test-deploy.sh` passes on a clean Ubuntu 24.04 VM.
- `systemd-analyze verify systemd/<app-name>.service` is clean.
- `systemd-analyze security <app-name>.service` reports exposure 2.5 or lower.
- The service survives a `kill -TERM` and a `kill -KILL` (the latter triggers a `Restart=on-failure` cycle).
- `journalctl -u <app-name>.service -f` shows live logs from the app.
- The service starts at boot (reboot the VM; service is active without manual intervention).
- `install.sh` is idempotent (re-running it doesn't fail or duplicate work).
- `uninstall.sh` returns the system to a clean state.
- README documents what you built and how to operate it.

---

## Grading rubric

| Element | Points |
|---------|-------:|
| Python app works, has the required endpoints | 10 |
| Unit file passes `systemd-analyze verify` | 5 |
| `Type=`, `Restart=`, `StartLimit*=` correctly chosen | 10 |
| `DynamicUser=` or static `User=` with correct `StateDirectory=` etc. | 10 |
| Sandbox score under 2.5 | 15 |
| `install.sh` deploys end-to-end on a clean VM | 10 |
| `install.sh` is idempotent | 5 |
| `uninstall.sh` cleans up completely | 5 |
| `tests/test-deploy.sh` exercises install/HTTP/restart/uninstall | 10 |
| README is complete and accurate | 10 |
| Service survives reboot | 5 |
| `before.txt` and `after.txt` show the score progression | 5 |
| **Total** | **100** |

90+ = portfolio quality. 80-89 = solid but a rough edge or two. 70-79 = needs revision before week 6. <70 = re-read both lectures and redo exercise 03.

---

## Stretch goals

- Add a `.socket` unit so the service starts on first request, not at boot. The journal will show "socket activated" each time.
- Add a `Type=notify` readiness signal: import `sdnotify` in Python, send `READY=1` after the HTTP server's `socket()` call. Time the difference between `Type=exec` and `Type=notify` in `systemd-analyze blame` output.
- Add a `.timer` that hits the app's `/metrics` endpoint and stores the response into the journal every 5 minutes. Now you have lightweight monitoring with no extra tooling.
- Cap the service's resources: `MemoryMax=128M`, `CPUQuota=25%`, `TasksMax=64`. Then load-test (use `wrk` or `ab`) and confirm the limits are enforced.
- Deploy to a $5/mo VPS. (This is week 6's territory, but doing it now is great prep.) Put nginx in front. Add a `Caddy` or `nginx` reverse-proxy unit alongside your app. Run for a week, observe.
- Set up `systemd`-level alerting: a `OnFailure=email-failure@%n.service` directive that triggers a templated email-send service when your app fails its `StartLimitBurst=`. The pattern is well-documented in `systemd.unit(5)`.

---

## Reflection (after completion)

In `notes.md`, after the project is done, answer:

1. Which directive in the sandbox gave you the most trouble? What did you have to change in the app to make it work?
2. The exposure score dropped from N1 to N2. Which two directives accounted for the largest part of that drop?
3. Run `systemd-cgls` while the service is active. Where does your service live in the cgroup tree? What's the parent slice?
4. Pick a directive we did **not** use in the final unit. Read its man-page entry. Explain (one paragraph) whether your service would benefit from it.
5. The first time you ran `systemctl daemon-reload` and the change didn't take effect, what was the cause? (Common: editing the wrong file, forgetting to save in `sudoedit`, having a syntax error that `verify` would have caught.)

---

## Up next

Once your service is installed, tested, and documented, you're done with Week 5.

[Week 6 — SSH, networking, firewalls](../../week-06/) — where this service goes onto a real machine on the public internet, behind hardened SSH, behind a firewall, behind a reverse proxy. The unit file you wrote this week is what week 6 will ship.

---

*A sandboxed service is not a paranoid service. It is a service that, when it goes wrong, goes wrong in the smallest possible way.*
