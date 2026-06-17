# Challenge 01 — Multi-Instance Template Units

**Time:** ~2-3 hours. **Goal:** Write **one** unit file, instantiate it **N** times, parametrize each instance via specifiers and per-instance configuration. The pattern every queue worker, every per-tenant service, every "N copies of the same daemon" workload eventually uses.

This challenge has no automated grader. The acceptance is that you can demonstrate three concurrently running instances, each with its own config, each tagged in the journal, all sharing one unit file.

## The pattern

A **template unit** is a unit file whose name contains an `@`:

```
/etc/systemd/system/worker@.service
```

You **never start `worker@.service` directly**. You start instances:

```bash
sudo systemctl start worker@one.service
sudo systemctl start worker@two.service
sudo systemctl start worker@three.service
```

Each instance inherits the template. Inside the unit file, the **instance name** (`one`, `two`, `three`) is available via specifiers:

| Specifier | Expands to |
|-----------|------------|
| `%i` | Instance name, unescaped: `one` |
| `%I` | Instance name, escaped (slashes, etc. preserved): `one` (same here; differs when instance names contain `/` or `-`) |
| `%n` | Full unit name: `worker@one.service` |
| `%N` | Full unit name minus suffix: `worker@one` |
| `%p` | Prefix (everything before `@`): `worker` |
| `%u` | User the service runs as |
| `%h` | Home of the user |
| `%t` | Runtime directory (`$XDG_RUNTIME_DIR` for user units; `/run` for system units) |

A worker template that uses `%i` to pick its config file:

```ini
# /etc/systemd/system/worker@.service
[Unit]
Description=Worker instance %i
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
ExecStart=/usr/local/bin/worker --config /etc/worker/%i.yaml
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Then `systemctl start worker@one.service` runs `/usr/local/bin/worker --config /etc/worker/one.yaml`, while `systemctl start worker@two.service` runs `/usr/local/bin/worker --config /etc/worker/two.yaml`. One unit file, N instances, N different configs.

## Your assignment

Build a multi-instance "echo worker" system. The deliverables:

1. A `worker` script (Bash or Python — your call) that reads its config and prints a greeting every few seconds.
2. A template unit `worker@.service`.
3. Three config files `/etc/worker/one.yaml`, `two.yaml`, `three.yaml` with three different greetings and three different intervals.
4. A demonstration that all three instances run concurrently, each tagged in the journal as `worker@one`, `worker@two`, `worker@three`.
5. A drop-in directory `worker@.service.d/` that adds a sandbox common to all instances.
6. A README explaining what you built, the design, and one limitation.

### The worker script

Suggestion in Python (you can do it in Bash):

```python
#!/usr/bin/env python3
"""Worker that prints a greeting every N seconds, reading config from --config."""
import argparse
import json
import sys
import time
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())   # YAML or JSON; pick one
    greeting = cfg["greeting"]
    interval = float(cfg["interval_sec"])
    name = cfg.get("name", args.config.stem)
    while True:
        print(f"[{name}] {greeting}", flush=True)
        time.sleep(interval)

if __name__ == "__main__":
    main()
```

Save as `/usr/local/bin/worker`, `chmod +x`. (Use JSON for simplicity; YAML requires PyYAML.)

### The three configs

```bash
sudo mkdir -p /etc/worker
sudo tee /etc/worker/one.json   > /dev/null <<<'{"greeting": "hello from one",   "interval_sec": 5,  "name": "one"}'
sudo tee /etc/worker/two.json   > /dev/null <<<'{"greeting": "howdy from two",   "interval_sec": 7,  "name": "two"}'
sudo tee /etc/worker/three.json > /dev/null <<<'{"greeting": "g'\''day from three", "interval_sec": 11, "name": "three"}'
```

(Note the trailing `.json` extension; if you used YAML, adjust `worker@.service` accordingly.)

### The template unit

Save as `/etc/systemd/system/worker@.service`:

```ini
[Unit]
Description=Echo worker, instance %i
After=network-online.target

[Service]
Type=exec
ExecStart=/usr/local/bin/worker --config /etc/worker/%i.json
Restart=on-failure
RestartSec=5s
DynamicUser=true

[Install]
WantedBy=multi-user.target
```

### The drop-in for shared sandbox

Save as `/etc/systemd/system/worker@.service.d/sandbox.conf`:

```ini
[Service]
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
NoNewPrivileges=true
CapabilityBoundingSet=
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
```

Drop-ins under `<unit>.d/*.conf` apply to **all instances** of the template. Edit once, apply everywhere.

### Run all three

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now worker@one.service worker@two.service worker@three.service

# All three running?
systemctl list-units 'worker@*'

# Their logs - one shared follow, tagged by instance
journalctl -u 'worker@*' -f
```

You should see lines from all three workers interleaved, each tagged with its unit name:

```
May 13 14:00:01 host worker@one[1234]: [one] hello from one
May 13 14:00:02 host worker@two[1235]: [two] howdy from two
May 13 14:00:03 host worker@three[1236]: [three] g'day from three
May 13 14:00:06 host worker@one[1234]: [one] hello from one
...
```

### Demonstrate per-instance restart

Stop one instance only:

```bash
sudo systemctl stop worker@two.service
journalctl -u 'worker@*' -f
# Now only one and three show. They keep running.
```

Start it back:

```bash
sudo systemctl start worker@two.service
# All three back.
```

### Score the sandbox

```bash
sudo systemd-analyze security worker@one.service
```

You should land somewhere in the 1.5-2.5 range. Snapshot the output to `worker-security.txt`.

---

## The README

In `~/c14-week-05/challenges/01/README.md`, document:

1. The full file layout (script, configs, unit, drop-in).
2. How you'd add a fourth instance (`worker@four.service`) — and how many files you'd touch.
3. How `%i` expands and why this is more maintainable than three copies of `worker.service`.
4. One limitation of templates: name a real workload where templates are *wrong* and three separate units would be better.
5. The exposure score from `systemd-analyze security`.

---

## Acceptance

- `systemctl list-units 'worker@*'` shows three active instances.
- `journalctl -u 'worker@*' --since "5 minutes ago"` shows lines from all three.
- `systemctl cat worker@one.service` shows the template unit plus the `sandbox.conf` drop-in.
- `systemd-analyze security worker@one.service` reports exposure 3.0 or lower.
- `README.md` answers the five questions.

---

## Clean-up

```bash
sudo systemctl disable --now worker@one.service worker@two.service worker@three.service
sudo rm /etc/systemd/system/worker@.service
sudo rm -rf /etc/systemd/system/worker@.service.d/
sudo rm -rf /etc/worker
sudo rm /usr/local/bin/worker
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

---

## Going further

- Replace `DynamicUser=true` with per-instance static users (`User=worker-%i`) and pre-create them. Compare the trade-offs: easier file ownership vs more setup steps.
- Add an `InstanceLimit=` style cap by writing a drop-in that wraps each instance in a `Slice=` (e.g., `Slice=worker.slice`) and capping the slice's CPU and memory.
- Build a real workload: a Redis-backed job queue with `N` workers, where `N` is set by how many `worker@*.service` instances you've enabled. systemd is your orchestrator; redis is your queue. Run it.
- Write a script that auto-generates configs and enables instances based on a flat directory: `/etc/worker/*.json` exists, therefore `worker@<basename>.service` should be enabled. Re-run on config changes. This is the kind of glue most production systemd setups end up with.
