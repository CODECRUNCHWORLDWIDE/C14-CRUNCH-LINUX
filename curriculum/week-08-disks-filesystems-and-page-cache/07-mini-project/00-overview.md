# Mini-Project (Track Capstone) — Run a real Linux server for 7 days

> **This is the capstone of C14 · Crunch Linux.** Seven weeks ago you opened your first shell. This week you provision a Linux server, configure it for production-grade observability and security, run it on the public internet (or in a local hypervisor) for seven calendar days, and write a postmortem explaining what worked, what failed, what alerted, what didn't, and what you would change.
>
> This is not a coding exercise. It is an **operational exercise**. The skill being measured is the same skill measured in any junior-Linux-engineer interview: can you set up a server competently, watch it, and reason about what you see.

**Estimated active time:** 11 hours over 7 calendar days. The active work is front-loaded (Monday-Thursday); Days 5-7 are mostly watching and tuning. Plan accordingly.

---

## What you will build

A small Linux VM running:

- **A real web service.** Choose one:
  - **nginx serving a static site.** Simpler. Recommended unless you have prior Flask/Django experience.
  - **A tiny Flask app** (`hello world` plus one form that writes to a file, plus one read endpoint). Slightly more work.

- **TLS** via Let's Encrypt (`certbot`).
- **Logging** — journald + standard nginx access/error logs.
- **Monitoring** — at minimum `sar` (continuous CPU/memory/IO/network collection via `sysstat`) and `journalctl` review. Optionally: `node_exporter` + `prometheus`, or `uptime-kuma`.
- **Intrusion handling** — `fail2ban` watching auth failures and (if you serve Flask) HTTP 4xx storms.
- **Automatic security updates** — `unattended-upgrades` (Debian/Ubuntu) or `dnf-automatic` (Fedora).
- **A hardened SSH** — key-only auth, fail2ban watching, non-default port acceptable.
- **A hardened firewall** — `nftables` or `ufw`, with explicit allow rules for SSH, 80, 443.

Then you **leave it running for 7 days** and watch.

---

## Hosting options

Pick one. All are free.

### Option A — Free-tier VM (recommended for the postmortem experience)

The capstone is most informative if your VM is on the public IPv4 internet, because **every public IPv4 will be port-scanned within minutes of boot**. The fail2ban logs and the auth.log will show you the constant background of attacks; the postmortem section "what attacked" gets its evidence from this.

Free-tier providers (all have $0 tiers as of May 2026; verify before signing up):

- **Oracle Cloud Always Free** — the most generous: 2 AMD micro-VMs or 4 Ampere ARM cores total. <https://www.oracle.com/cloud/free/>
- **Google Cloud Free** — one `e2-micro` in us-west1/us-central1/us-east1 free indefinitely. <https://cloud.google.com/free>
- **AWS Free Tier** — 750 hours/month `t3.micro` for 12 months. <https://aws.amazon.com/free/>
- **Azure Free Account** — `B1S` for 12 months. <https://azure.microsoft.com/free/>
- **Fly.io** — 3 shared-cpu-1x machines, 256 MB RAM each. <https://fly.io/docs/about/pricing/>

Pick the one whose signup is simplest in your country. If you sign up for AWS / Azure / GCP, **set a billing alert** at $1 — the free tier is generous but cliff-edged, and a misconfigured instance can run $5/day.

### Option B — Local VirtualBox / UTM / Multipass

A local Linux VM behind your home router. Practical but you lose the public-internet attack surface (no constant port-scanning). For the postmortem you can simulate attacks by running `nmap` against the VM from another machine; this is acceptable but obviously less representative.

- **VirtualBox** (free, Oracle) — Windows, Mac (Intel), Linux.
- **UTM** (free, Mac with Apple Silicon) — the easiest path on M-series Macs.
- **Multipass** (free, Canonical) — single-command Ubuntu VMs on any host. `multipass launch --name c14-cap --cpus 1 --memory 1G --disk 10G`.

### Option C — A Raspberry Pi or similar

If you have a Pi 4 (or newer) gathering dust, this works beautifully. The hardware is real, the disk is real (or rather, the SD card or USB SSD), and you can use a port-forward on your home router to expose it. Optional path; only choose if you genuinely have the hardware.

**Choose your option and commit before Monday.** Switching mid-week creates evidence gaps in the postmortem.

---

## The seven days, day by day

### Day 1 (Monday) — Provision and harden

1. **Provision the VM.** From your chosen provider's console, create the smallest Ubuntu 24.04 LTS (or Fedora 41) instance. SSH key pre-loaded.
2. **Connect.** `ssh -i ~/.ssh/key user@<ip>`. Confirm `uname -a` matches expectations.
3. **Update.** `sudo apt update && sudo apt upgrade -y` (or `sudo dnf upgrade -y`). Reboot if there is a kernel update.
4. **Create a non-root user** for yourself. `sudo adduser jane && sudo usermod -aG sudo jane`. Copy your SSH key. Log in as the new user. Test sudo.
5. **Harden SSH.** Edit `/etc/ssh/sshd_config.d/99-c14.conf`:
   ```
   PasswordAuthentication no
   PermitRootLogin no
   PubkeyAuthentication yes
   X11Forwarding no
   ```
   Restart sshd: `sudo systemctl restart sshd`. Do **not** close your existing session until you confirm a new one works.
6. **Set up the firewall.** Ubuntu: `sudo ufw allow OpenSSH; sudo ufw allow 80; sudo ufw allow 443; sudo ufw enable`. Fedora: equivalent with `firewalld`.
7. **Install the monitoring stack.** `sudo apt install sysstat htop iotop fail2ban unattended-upgrades`. Enable: `sudo systemctl enable --now sysstat`.
8. **Configure unattended-upgrades.** On Ubuntu: `sudo dpkg-reconfigure -plow unattended-upgrades` and accept defaults. On Fedora: `sudo systemctl enable --now dnf-automatic-install.timer`.
9. **Start a portfolio repository** for the capstone. `c14-week-08/mini-project/` will contain configs, logs, postmortem.
10. **Document hour 0.** Capture: `uname -a`, `lsblk`, `df -h`, `free -h`, `ip addr`, `ss -tulpn`, `systemctl list-units --state=failed`. Save to `evidence/day-1-baseline.txt`.

**Estimated time today: 1.5 hours active.**

### Day 2 (Tuesday) — Install the web service

1. **Install the service.** nginx: `sudo apt install nginx`. Flask: `sudo apt install python3-flask python3-gunicorn` and create a simple app.
2. **Configure.** Static-site users: drop your content under `/var/www/html`. Flask users: write a 30-line `app.py` that does (a) `GET /` returns a hello world; (b) `POST /note` writes to a file; (c) `GET /notes` lists them. Run under gunicorn behind nginx.
3. **Get TLS via Let's Encrypt.** `sudo apt install certbot python3-certbot-nginx`. Get a domain (a free `xyz` from <https://www.freenom.com/> or a paid `.com` for $10/yr; or use a dyn-DNS like Duck DNS for free). Point it at your VM's IP. Run `sudo certbot --nginx -d yourdomain.tld`.
4. **Test.** From your laptop: `curl -v https://yourdomain.tld/`. Should be 200 OK with a valid TLS cert.
5. **Capture.** `nginx -T` (the active config), `journalctl -u nginx --since today` (the service log). Save to `evidence/day-2-service-config.txt`.
6. **Set up a uptime check.** Use <https://uptimerobot.com/> (free, 5-minute checks) or <https://www.uptime.com/> (free trial). Get alerts to your email if the site goes down.

**Estimated time today: 1.5 hours active.**

### Day 3 (Wednesday) — Logging, fail2ban, baseline

1. **Configure logrotate** for nginx. Default config in `/etc/logrotate.d/nginx` is usually fine; verify.
2. **Configure fail2ban** for nginx (in addition to its default sshd jail). Create `/etc/fail2ban/jail.d/nginx-http-auth.conf` (or use the default `nginx-limit-req` jail). Test with `sudo fail2ban-client status nginx-http-auth`.
3. **Read your auth log.** `sudo journalctl -u ssh --since '12 hours ago'`. By now you should have several thousand failed login attempts from various IPs. This is **normal** for a new public IP. Note the rate.
4. **Capture a baseline performance reading.** Run `fio` (Exercise 4's job files) against the VM's disk. Record the four numbers. Save to `evidence/day-3-baseline-fio.txt`. This is the "what was healthy" snapshot you will compare against if performance changes.
5. **Capture a baseline `sar` reading.** `sar -u 1 60 > evidence/day-3-baseline-cpu.txt`. 60 samples of 1 second each. Same for `sar -r 1 60` (memory), `sar -b 1 60` (IO), `sar -n DEV 1 60` (network).

**Estimated time today: 1.5 hours active.**

### Day 4 (Thursday) — Test monitoring, run a small load

1. **Verify automatic updates work.** `sudo unattended-upgrades --dry-run -d` (Ubuntu) shows what would be installed. Watch a real run happen overnight; check `/var/log/unattended-upgrades/` the next morning.
2. **Test fail2ban.** From a different machine (your laptop or a free shell on tinyhost.org), attempt 6 wrong SSH logins:
   ```bash
   for i in 1 2 3 4 5 6; do
       ssh -o PreferredAuthentications=password -o NumberOfPasswordPrompts=1 \
           wronguser@yourdomain.tld
   done
   ```
   The fail2ban default ban is 3-5 attempts; you should see your laptop's IP banned in `sudo fail2ban-client status sshd`. Wait for the ban to expire (default 10 min) before continuing.
3. **Induce a small load on the service.** Pick **one** of the following. Run it for 5-10 minutes:
   - `ab -n 10000 -c 20 https://yourdomain.tld/` (Apache Bench; concurrent requests)
   - `hey -n 10000 -c 20 https://yourdomain.tld/` (hey is newer; `go install github.com/rakyll/hey@latest`)
   - A tight `curl` loop: `while true; do curl -s -o /dev/null https://yourdomain.tld/; done` from your laptop
4. **Watch.** During the load, in a separate SSH session: `htop`, `vmstat 1`, `iostat -x 1`, `sar -n DEV 1`. Note which resource (CPU, memory, network, disk) was first to show pressure.
5. **Capture.** Save the `htop` row for nginx, the `vmstat` lines during the load, and the `sar -n DEV` lines. `evidence/day-4-load-test.txt`.

**Estimated time today: 1.5 hours active.**

### Day 5 (Friday) — Watch and tune

1. **Read your journal.** `sudo journalctl --since yesterday | wc -l` (how many lines did the system generate?). Skim for anything unexpected.
2. **Read your nginx access log.** `sudo wc -l /var/log/nginx/access.log` and `sudo awk '{print $1}' /var/log/nginx/access.log | sort -u | wc -l` (unique IPs visiting). Pick the top 10 IPs and look up where they are from with `geoiplookup` (if installed) or <https://ipinfo.io>.
3. **Look at fail2ban's accumulated bans.** `sudo fail2ban-client status sshd`. Note the count.
4. **Tune one thing.** Examples:
   - Lower `vm.dirty_ratio` to 10. `sudo sysctl vm.dirty_ratio=10; echo 'vm.dirty_ratio=10' | sudo tee /etc/sysctl.d/99-dirty.conf`.
   - Add `noatime` to your data mount in `/etc/fstab` (back up first).
   - Lower nginx worker_connections from default (often 768) to 1024 if you saw saturation.
5. **Document the change.** Hypothesis (what you expected to improve), measurement before, change, measurement after. Save to `evidence/day-5-tuning.md`.

**Estimated time today: 1 hour active.**

### Day 6 (Saturday) — Stress and observe

1. **Run a longer load test** — 30 minutes at a moderate rate. Watch what happens.
2. **Read SMART data.** `sudo smartctl -a /dev/<your_disk>` (or `nvme smart-log`). Compare to Day 1. Most consumer SSDs show zero wear after 30 minutes of load; cloud disks usually do not expose SMART at all (the hypervisor abstracts it).
3. **Look at log volume.** `sudo du -sh /var/log/`. Compare to Day 1. Is anything growing unexpectedly?
4. **Look at filesystem usage.** `df -h`. `du -sh /var/* | sort -h`. Anything you did not expect?

**Estimated time today: 1.5 hours active.**

### Day 7 (Sunday) — Postmortem

1. **Write the postmortem.** Use the template you drafted in Week 8 Homework Problem 6. Now you have data to fill it in.
2. **Submit.** Push to your portfolio repo.
3. **Decide on shutdown.** If you want to keep the VM running past the capstone, fine. If not, **destroy it** (free-tier instances quietly burn hours; you can hit the cap and lose access to the dashboard).

**Estimated time today: 2 hours.**

---

## Deliverable structure

A directory `c14-week-08/mini-project/` in your portfolio repo:

```
c14-week-08/mini-project/
├── README.md                         <- the postmortem (the deliverable)
├── evidence/
│   ├── day-1-baseline.txt
│   ├── day-2-service-config.txt
│   ├── day-3-baseline-fio.txt
│   ├── day-3-baseline-cpu.txt
│   ├── day-3-baseline-mem.txt
│   ├── day-3-baseline-io.txt
│   ├── day-3-baseline-net.txt
│   ├── day-4-load-test.txt
│   ├── day-5-tuning.md
│   ├── day-6-stress.txt
│   ├── auth-log-week.txt             (a redacted week of auth.log)
│   ├── fail2ban-bans.txt
│   └── nginx-access-log-stats.txt
├── configs/
│   ├── nginx.conf                    (or sites-enabled/default)
│   ├── sshd_config.d-99-c14.conf
│   ├── fail2ban-jail.local
│   ├── unattended-upgrades.conf
│   └── etc-fstab.txt
└── scripts/
    ├── inventory.sh                  (the day-1 inventory captures)
    └── load-test.sh                  (your load-test command)
```

---

## The postmortem itself

The postmortem is the **single deliverable that matters most**. It is the document you would write at a real job after a service ran for a week. The grader reads this; the rest is supporting evidence.

Use the 12 sections from Week 8 Homework Problem 6, now filled in with real data. Expected length: **2500-5000 words**, plus configs and evidence in the appendices. Quality matters more than length.

The grader looks for:

- **Evidence chain.** Every claim in the postmortem cites a file in `evidence/`.
- **Honest reporting.** What didn't work, what surprised you, what you did wrong on Tuesday and fixed on Thursday. The capstone is graded on insight, not on heroic results.
- **Concrete improvements.** "I would change X because Y" — not "I would generally do better."
- **Readable prose.** This is also a writing exercise. A senior engineer at the receiving end should be able to understand your week from the postmortem alone.

---

## Grading rubric

The capstone is worth **40 % of the C14 final grade** (the other 60 % is split across weeks 1-8 homework and quizzes). Out of 40 points:

| Component | Points | What earns full marks |
|-----------|--------|----------------------|
| Provisioning and hardening (Day 1) | 5 | Non-root user, key-only SSH, firewall closed by default, automatic updates configured |
| Service running and reachable | 5 | TLS valid, returns 200, no errors in journal |
| Logging and monitoring | 5 | `sysstat` capturing, nginx logs rotated, fail2ban active and tested |
| Day-3 baseline captured | 3 | `fio`, `sar` baselines all present |
| Day-4 load test executed and observed | 4 | Load ran, the observation captures show which resource saturated |
| Day-5 tuning experiment | 3 | One change made, before/after measured |
| Day-6 longer stress and SMART check | 3 | Captures present |
| Postmortem — all 12 sections | 6 | Every section non-empty, every section cites evidence |
| Postmortem — quality of insight | 4 | Specific, honest, concrete improvements |
| Postmortem — readability | 2 | A reader unfamiliar with your VM can understand the week |

Total: 40.

| Score | Grade for the capstone |
|-------|------------------------|
| 36-40 | A — graduation-level work |
| 30-35 | B — solid; revise the postmortem for portfolio use |
| 24-29 | C — passing; one or more weak sections |
| 18-23 | D — significant gaps; re-do specific days |
| <18   | F — re-do the capstone next term |

A capstone in the 36-40 range is portfolio-worthy. Link it from your résumé.

---

## Common pitfalls

- **The instance is in a different region than expected.** Some free tiers force you to a region you cannot reach well from your laptop; the SSH lag will frustrate you. Pick a region close.
- **The free tier expires on a 12-month boundary.** AWS, Azure: keep an eye on the billing dashboard. Destroy the instance at month 11 if you do not want to be charged.
- **You forget to enable `sysstat`.** Then on Day 5 when you try to look back at "what was the server doing Tuesday at 14:00", there is nothing. Enable it on Day 1.
- **Your domain DNS does not propagate in time for the certbot run.** Certbot will fail with a confusing message about the HTTP challenge. Wait 30 minutes after the DNS change; try again.
- **You overflow the disk.** A 10 GB instance with verbose journald can fill up in a week. Configure journald with `SystemMaxUse=500M` in `/etc/systemd/journald.conf` (and `systemctl restart systemd-journald`) to cap.
- **You leave the instance running past the capstone and rack up a bill.** Set the billing alert on Day 1.

---

## When you are done

Open a PR in your portfolio repository with the title `C14 · Week 8 Capstone · <your name>`. Tag the instructor (or the C14 mentor) for review. The mentor will read the postmortem and either approve or request changes. Approval means you graduate the track.

This is the final deliverable. Take it seriously.

---

*If you have questions, ask them on the C14 Discord. The capstone is graded individually; the discussion in the Discord is for clarifying the spec, not for sharing your specific configuration.*
