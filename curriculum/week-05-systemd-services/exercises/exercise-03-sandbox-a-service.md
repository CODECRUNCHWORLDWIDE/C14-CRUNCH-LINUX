# Exercise 03 — Sandbox a Service

**Time:** ~3 hours. **Goal:** Take a wide-open service and ratchet `systemd-analyze security` from ~9.6 (worst-of-class) down toward 1.5 (production-quality). Add one directive at a time, restart, check the score, check that the service still works. Build the muscle for the eight high-leverage directives from Lecture 2.

You will need systemd 255+ and `sudo`. Verify:

```bash
systemctl --version | head -1
systemd-analyze security --no-pager systemd-resolved.service | tail -1
```

(`systemd-resolved.service` should score around 2.0-3.0 on a stock Ubuntu/Fedora — that's our reference for "what tight looks like.")

Scratch directory:

```bash
mkdir -p ~/c14-week-05/exercises/03
cd ~/c14-week-05/exercises/03
```

---

## The starting service

We will sandbox a small HTTP server. Write the server in Python — it's the language we use in the mini-project, and the imports tell systemd-analyze the right things.

Save as `~/c14-week-05/exercises/03/server.py`:

```python
#!/usr/bin/env python3
"""A trivial HTTP server that responds to GET / with the system uptime."""
import http.server
import subprocess
import sys
from pathlib import Path

PORT = 8765
STATE_DIR = Path("/var/lib/wide-open")
LOG_FILE = STATE_DIR / "requests.log"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        uptime = subprocess.check_output(["uptime"], text=True).strip()
        body = f"uptime: {uptime}\n".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        with open(LOG_FILE, "a") as f:
            f.write(f"{self.client_address[0]} GET /\n")

    def log_message(self, fmt, *args):
        sys.stderr.write(f"{self.client_address[0]} - " + (fmt % args) + "\n")

def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with http.server.HTTPServer(("127.0.0.1", PORT), Handler) as httpd:
        print(f"listening on 127.0.0.1:{PORT}", flush=True)
        httpd.serve_forever()

if __name__ == "__main__":
    main()
```

Make it executable: `chmod +x server.py`. Test by hand:

```bash
sudo mkdir -p /var/lib/wide-open && sudo chown $USER /var/lib/wide-open
./server.py &
curl http://127.0.0.1:8765/
# uptime: 14:00:23 up 2 days, ...
kill %1
```

If that works, proceed.

## The wide-open unit

Save as `/etc/systemd/system/wide-open.service`:

```ini
[Unit]
Description=Wide-open HTTP server (BEFORE hardening)
Documentation=https://github.com/CODE-CRUNCH-CLUB/C14-CRUNCH-LINUX/blob/main/curriculum/week-05-systemd-services/exercises/exercise-03-sandbox-a-service.md

[Service]
Type=exec
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/03/server.py
Restart=on-failure
RestartSec=5s
# No User= - runs as root.
# No sandboxing - this is the baseline.

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemd-analyze verify /etc/systemd/system/wide-open.service
sudo systemctl daemon-reload
sudo systemctl start wide-open.service
curl http://127.0.0.1:8765/
```

Confirm the curl works. Now baseline the security score:

```bash
sudo systemd-analyze security wide-open.service
```

Look at the last line. You should see something in the range:

```
→ Overall exposure level for wide-open.service: 9.6 UNSAFE 😨
```

That is the starting point. Save the full output to `~/c14-week-05/exercises/03/before.txt`:

```bash
sudo systemd-analyze security wide-open.service > ~/c14-week-05/exercises/03/before.txt
```

---

## Part 1 — Apply directives one at a time (90 min)

The rules of engagement:

- Add **one directive at a time**.
- After each, `systemd-analyze verify`, `daemon-reload`, `systemctl restart wide-open.service`, then `curl http://127.0.0.1:8765/`.
- If the service still responds: score it (`systemd-analyze security wide-open.service`), note the new exposure, move on.
- If the service breaks: read the journal (`journalctl -u wide-open.service -n 30`), identify which sandbox check tripped, and decide whether to add a `Read*=` exception or back out the directive.

Keep a running table in `~/c14-week-05/exercises/03/scores.md`:

| Step | Directive added | Exposure before | Exposure after | Service still works? | Notes |
|-----:|-----------------|----------------:|---------------:|---------------------:|-------|
| 0    | (baseline) | n/a | 9.6 | yes | |
| 1    | `User=wide-open` | 9.6 | | | |

### Step 1 — `User=` (drop root)

Create the system user first:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin wide-open
sudo chown -R wide-open:wide-open /var/lib/wide-open
```

Add to `[Service]`:

```ini
User=wide-open
Group=wide-open
```

Reload, restart, curl. Score. Update the table.

### Step 2 — `ProtectSystem=strict`

```ini
ProtectSystem=strict
ReadWritePaths=/var/lib/wide-open
```

Without `ReadWritePaths=`, the service can't write `/var/lib/wide-open/requests.log` and will crash on the first request. With it, only `/var/lib/wide-open` is writable.

Reload, restart, curl. Verify the request log still appends:

```bash
sudo cat /var/lib/wide-open/requests.log
```

Score. Update the table.

### Step 3 — `ProtectHome=true`

```ini
ProtectHome=true
```

The service has no business reading `/home`. Block it.

Reload, restart, curl. Score. Update.

### Step 4 — `PrivateTmp=true`

```ini
PrivateTmp=true
```

Private `/tmp` and `/var/tmp`.

Reload, restart, curl. Score. Update.

### Step 5 — `NoNewPrivileges=true`

```ini
NoNewPrivileges=true
```

setuid binaries can no longer escalate. The service calls `subprocess.check_output(["uptime"])`, so `uptime` must work without setuid (it does on Ubuntu and Fedora; verify with `ls -l $(which uptime)`).

Reload, restart, curl. Score. Update.

### Step 6 — `CapabilityBoundingSet=`

```ini
CapabilityBoundingSet=
```

Empty = drop all. The service binds port 8765 (not 80), so no `CAP_NET_BIND_SERVICE` needed. The service does no network admin, no kernel calls, no filesystem mounts. Empty is correct.

Reload, restart, curl. Score. Update.

### Step 7 — `RestrictAddressFamilies=`

```ini
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
```

The server uses `AF_INET` (IPv4) for the listening socket. Allow that plus `AF_INET6` and `AF_UNIX` for completeness. Block `AF_NETLINK`, `AF_PACKET`, and the rest.

Reload, restart, curl. Score. Update.

### Step 8 — The combo block

The final directives, all together:

```ini
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
```

These are cheap "tighten everything" directives. Each is one line; each removes one syscall surface; each drops the score by 0.1-0.3.

`MemoryDenyWriteExecute=true` will break **JIT compilers** (V8, Java HotSpot, .NET). Python CPython doesn't JIT, so it's fine here. Note this in `scores.md`.

Reload, restart, curl. Final score.

---

## Part 2 — The final unit (30 min)

Your finished unit should look approximately like this:

```ini
[Unit]
Description=Sandboxed HTTP server (AFTER hardening)
Documentation=https://github.com/CODE-CRUNCH-CLUB/C14-CRUNCH-LINUX/blob/main/curriculum/week-05-systemd-services/exercises/exercise-03-sandbox-a-service.md

[Service]
Type=exec
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/03/server.py
Restart=on-failure
RestartSec=5s
User=wide-open
Group=wide-open

# Filesystem
ProtectSystem=strict
ReadWritePaths=/var/lib/wide-open
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true

# Privilege
NoNewPrivileges=true
CapabilityBoundingSet=

# Network
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6

# Namespaces and memory
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
```

Save the final score:

```bash
sudo systemd-analyze security wide-open.service > ~/c14-week-05/exercises/03/after.txt
```

A score in the range **1.5-3.0** is a pass. If you're stuck above 4.0, look at the score lines marked with ✗ — each one names a directive you didn't apply.

### Optional — try `DynamicUser=`

`DynamicUser=true` is the strongest single isolation directive. It implies `User=`, `PrivateTmp=`, `RemoveIPC=`, `ProtectSystem=strict`, `ProtectHome=read-only`, `NoNewPrivileges=`. The catch: the UID is invented per-run, so file ownership doesn't persist across restarts. You must declare writable paths with `StateDirectory=`:

```ini
[Service]
Type=exec
DynamicUser=true
StateDirectory=wide-open
ExecStart=/home/YOUR_USERNAME/c14-week-05/exercises/03/server.py
# Note: server.py will need to use os.environ["STATE_DIRECTORY"] to find the writable path,
# not the hardcoded /var/lib/wide-open. systemd sets that env var automatically.
```

This requires editing `server.py` to honor `$STATE_DIRECTORY`. Try it as a stretch goal.

---

## Part 3 — Compare before and after (30 min)

Diff the two score files:

```bash
diff ~/c14-week-05/exercises/03/before.txt ~/c14-week-05/exercises/03/after.txt | less
```

In `~/c14-week-05/exercises/03/03-notes.md`, answer:

1. The exposure dropped from 9.6 to ___ . Which single directive caused the biggest single drop in your run?
2. The `systemd-analyze security` output flags about 50 separate checks. Pick three checks that were ✗ in `before.txt` and ✓ in `after.txt`. For each, write one sentence describing what the check protects against.
3. The service still works after all this. What changed for the user? Was there a measurable latency cost from the sandboxing? (You can run `time curl http://127.0.0.1:8765/` before and after; the difference should be in the microseconds-to-milliseconds range. Not zero, but not noticeable in HTTP.)
4. Suppose `server.py` had a bug that let an attacker write arbitrary files. With the wide-open unit, the attacker is `root` and can write anywhere. With the hardened unit, what is the attacker's blast radius? Be specific about which directories they could write, which syscalls they could call, which capabilities they have.
5. Cite the `before.txt` and `after.txt` files in your commit. Without those, the exercise is unverifiable.

---

## Clean-up

```bash
sudo systemctl disable --now wide-open.service
sudo rm /etc/systemd/system/wide-open.service
sudo systemctl daemon-reload
sudo userdel wide-open
sudo rm -rf /var/lib/wide-open
```

---

## Acceptance criteria

- The starting unit scored 8.0 or worse.
- The final unit scores 3.0 or better.
- `curl http://127.0.0.1:8765/` succeeded with the final unit running.
- `scores.md` shows the per-step progression.
- `before.txt` and `after.txt` are committed.
- `03-notes.md` answers the five reflection questions.

---

## Stretch goals

- Apply `SystemCallFilter=@system-service ~@privileged ~@resources` and see how much further the score drops. Note any breakage in `scores.md`.
- Rewrite `server.py` to use `os.environ["STATE_DIRECTORY"]` and switch to `DynamicUser=true`. The Unix-paths-and-permissions plumbing is its own little adventure.
- Read `systemd.exec(5)` section "SANDBOXING" end to end. Pick five directives we did **not** use; write a one-sentence rationale for each on why this service doesn't need it.
- Run `systemd-analyze security` against every active service on your machine. The worst three offenders, in terms of exposure: what are they, and is there any directive you could add (via `systemctl edit`) that would tighten them without breaking the service?
- Replicate this exercise on a Fedora 41 VM and an Ubuntu 24.04 VM. Are the scores identical? If not, why? (Hint: different default `User=`s, different default `umask`, different units depending on the distro.)

---

## Common errors

| Symptom in journalctl | Likely cause | Fix |
|-----------------------|--------------|-----|
| `Failed at step NAMESPACE spawning ...: Permission denied` | `ProtectSystem=` is set inside a container that can't remount. | If in container, this isn't your bug; outside, check `CAP_SYS_ADMIN` somewhere up the chain. |
| `OSError: [Errno 13] Permission denied: '/var/lib/wide-open/requests.log'` | `ProtectSystem=strict` blocks writes; no matching `ReadWritePaths=`. | Add `ReadWritePaths=/var/lib/wide-open`. |
| `OSError: [Errno 1] Operation not permitted` | A capability the service needs was dropped. | Identify which `CAP_*` the syscall needs; add it back to `CapabilityBoundingSet=` and `AmbientCapabilities=`. |
| `RuntimeError: ('Cannot lookup uid for user', ...)` | `User=` references a user that doesn't exist. | `sudo useradd --system ...` first. |
| `MemoryError` or `mprotect: Operation not permitted` | `MemoryDenyWriteExecute=true` is blocking a JIT. | Remove the directive; this language runtime needs W+X memory. |

The first one — `Failed at step NAMESPACE` — is the most common. Read the journal carefully; the step name pinpoints which sandbox setup tripped.
