# Mini-Project — Provision, Harden, and Verify a $5/mo VPS

> Provision a small Linux VPS from a real provider. Harden SSH to key-only auth, non-root admin. Configure `nftables` for SSH-and-web-only. Optionally run `Fail2Ban`. Verify the result with `nmap` from your laptop. Write a one-page operational runbook. Keep the VPS alive for at least a week so we can revisit it in weeks 7 and 8.

**Estimated time:** 6-7 hours, spread Thursday-Saturday.

This mini-project is the deliverable that proves Week 6 took. You are not being graded on the choice of provider, the choice of region, or whether nginx is on the box. You are being graded on **the configuration files** (`sshd_config.d/*.conf`, `/etc/nftables.conf`) and **the operational story**: how SSH is locked down, how the firewall is shaped, how you verified it from outside, how you'd recover if you lose access, how you'd onboard another admin.

The point of the mini-project is to drill **the ten-step hardening lifecycle** (Lecture 1 §9 + Lecture 2 §12) end-to-end on a real machine on the public internet. You will provision, harden, verify, document.

---

## Deliverable

A directory in your portfolio repo `c14-week-06/mini-project/` containing:

1. `README.md` — your write-up. Provider choice, region, plan, design decisions, the unit-file structure, the nftables ruleset, the verification methodology, the runbook.
2. `configs/sshd-hardened.conf` — a copy of your `/etc/ssh/sshd_config.d/99-c14-hardened.conf`.
3. `configs/nftables.conf` — a copy of your `/etc/nftables.conf`.
4. `configs/jail.local` — your `Fail2Ban` config if you installed it (optional).
5. `scripts/install.sh` — an idempotent shell script that, given a fresh Ubuntu 24.04 VPS as `root` and a public key in the environment, performs the entire hardening sequence. Re-running it is a no-op.
6. `scripts/verify.sh` — a script (run from your **laptop**) that performs the outside checks: `nmap`, `ssh-audit`, optional `testssl.sh` against the web ports if you opened them. Exits non-zero if anything is off.
7. `evidence/nmap-before.txt` — `nmap` output before hardening (right after provisioning).
8. `evidence/nmap-after.txt` — `nmap` output after hardening.
9. `evidence/ssh-audit-after.txt` — `ssh-audit` output after hardening.
10. `evidence/auth-report.md` — 7 days of `journalctl -u sshd` parsed: successful logins, failed attempts, top brute-force source IPs.
11. `runbook.md` — one page. The operational shape: how to SSH in, how to add a user, how to add a firewall rule, how to recover if locked out, how to upgrade. Another engineer should be able to operate the VPS after reading this.

---

## The VPS

Pick a provider. Any of these are fine; the table is for orientation, not endorsement.

| Provider | Cheapest plan | Region count | API quality |
|----------|--------------|--------------|-------------|
| **Hetzner** | €4.51/mo (CX22: 2 vCPU, 4 GB) | EU + USA | Good |
| **Vultr** | $5/mo (1 vCPU, 1 GB) | 30+ | Good |
| **DigitalOcean** | $6/mo (1 vCPU, 1 GB) | 14 | Excellent |
| **Linode (Akamai)** | $5/mo (1 vCPU, 1 GB) | 11 | Good |
| **Scaleway** | €3.50/mo (DEV1-S) | EU + Africa | Good |
| **OVH** | €3.50/mo | EU + Canada + APAC | Adequate |

Pick a region close to you (low latency for interactive SSH). Pick the smallest plan that meets your needs (1 vCPU, 1 GB RAM is plenty for what we're doing). Pick **Ubuntu 24.04 LTS** as the image so we have one OpenSSH and one nftables version to reason about.

If $5/month is a problem, ask in the course Discord — we have sponsorship credits for several providers. The pedagogical value of running a real public-facing server is large enough that we want everybody to have access.

---

## The hardening sequence

The whole sequence is roughly what challenge 01 walks through, with the extras that turn it into a portfolio-quality deliverable.

### 1. Provision

- Image: Ubuntu 24.04 LTS.
- Plan: cheapest 1 vCPU / 1 GB / 25 GB disk.
- Region: closest to you.
- SSH key: paste your `~/.ssh/id_ed25519.pub` into the "SSH keys" field at provisioning. (Do **not** rely on password auth even for the first login.)
- Hostname: pick something meaningful — `c14-mini.your-name.tld` or `c14-mini-2026-05`. The hostname appears in `journald` and in any DNS you set up.

### 2. First connect — snapshot the "before"

```bash
ssh -o StrictHostKeyChecking=accept-new root@your.vps.ip
apt update && apt upgrade -y
apt install -y nftables fail2ban           # nftables is preinstalled; fail2ban optional
[ -f /var/run/reboot-required ] && reboot
```

From your laptop (before any hardening):

```bash
nmap -sV -p- --reason your.vps.ip > evidence/nmap-before.txt
```

This is "what the world sees of a fresh Ubuntu VPS." Typically only SSH is open (Ubuntu doesn't enable any other public service by default), but check.

### 3. Create the admin user

```bash
adduser --gecos "" your-name
usermod -aG sudo your-name
mkdir -p /home/your-name/.ssh
cp ~/.ssh/authorized_keys /home/your-name/.ssh/
chown -R your-name:your-name /home/your-name/.ssh
chmod 700 /home/your-name/.ssh
chmod 600 /home/your-name/.ssh/authorized_keys
```

### 4. Harden `sshd_config`

`/etc/ssh/sshd_config.d/99-c14-hardened.conf`:

```
Port 22

PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers your-name

LoginGraceTime 30
MaxAuthTries 3
MaxSessions 4

ClientAliveInterval 300
ClientAliveCountMax 2

X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
GatewayPorts no
PermitUserEnvironment no

# Mozilla "Modern" crypto baseline
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,sntrup761x25519-sha512@openssh.com
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
```

`sudo sshd -t && sudo systemctl reload sshd` — with a held-open root session as rollback.

### 5. Write nftables

`/etc/nftables.conf` (use the lecture 2 §4 template; adjust for your needs).

Apply with the `at`-trick auto-rollback:

```bash
echo "/usr/sbin/nft flush ruleset" | sudo at now + 2 minutes
sudo nft -c -f /etc/nftables.conf
sudo nft -f /etc/nftables.conf
# Confirm SSH still works from a new terminal within 2 minutes.
# If yes:
sudo atrm <job_id>
sudo systemctl enable nftables.service
```

### 6. Optional: `Fail2Ban`

`/etc/fail2ban/jail.local`:

```ini
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 3
backend  = systemd

[sshd]
enabled = true
port    = ssh
```

```bash
sudo systemctl enable --now fail2ban
```

### 7. Reboot, verify

```bash
sudo reboot
# Wait, then SSH back in.
ssh your-name@your.vps.ip
sudo nft list ruleset       # confirm the firewall came back
sudo systemctl status nftables sshd fail2ban
```

From your laptop:

```bash
nmap -sV -p- --reason your.vps.ip > evidence/nmap-after.txt
ssh-audit your.vps.ip > evidence/ssh-audit-after.txt
```

Diff `evidence/nmap-before.txt` against `evidence/nmap-after.txt`. The after file should show only 22 (and 80/443 if you have services) as `open`.

### 8. Wait one week, read the log

A week after step 7, capture the auth report:

```bash
ssh your-name@your.vps.ip
sudo journalctl -u sshd --since "7 days ago" > /tmp/sshd.log
# Then analyze (see Homework problem 5).
```

Save as `evidence/auth-report.md`.

---

## The `install.sh`

Idempotent. Run as `root` on a fresh Ubuntu 24.04 VPS. Re-runnable; second run is a no-op.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

ADMIN_USER="${ADMIN_USER:-c14admin}"
PUBKEY_FILE="${PUBKEY_FILE:-/root/.ssh/authorized_keys}"

require_root() { [[ $EUID -eq 0 ]] || { echo "must run as root" >&2; exit 77; }; }
log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }

ensure_user() {
    if id "$ADMIN_USER" >/dev/null 2>&1; then
        log "user $ADMIN_USER exists"
        return 0
    fi
    adduser --disabled-password --gecos "" "$ADMIN_USER"
    usermod -aG sudo "$ADMIN_USER"
    mkdir -p "/home/$ADMIN_USER/.ssh"
    cp "$PUBKEY_FILE" "/home/$ADMIN_USER/.ssh/authorized_keys"
    chown -R "$ADMIN_USER:$ADMIN_USER" "/home/$ADMIN_USER/.ssh"
    chmod 700 "/home/$ADMIN_USER/.ssh"
    chmod 600 "/home/$ADMIN_USER/.ssh/authorized_keys"
    log "user $ADMIN_USER created with sudo and key"
}

install_sshd_config() {
    cat > /etc/ssh/sshd_config.d/99-c14-hardened.conf <<EOF
Port 22
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers ${ADMIN_USER}
LoginGraceTime 30
MaxAuthTries 3
MaxSessions 4
ClientAliveInterval 300
ClientAliveCountMax 2
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
GatewayPorts no
PermitUserEnvironment no
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,sntrup761x25519-sha512@openssh.com
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
EOF
    sshd -t
    systemctl reload sshd
    log "sshd hardened and reloaded"
}

install_nftables() {
    cat > /etc/nftables.conf <<'EOF'
#!/usr/sbin/nft -f
flush ruleset

table inet filter {
    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        ct state invalid drop
        iif lo accept
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } accept limit rate 4/second
        ip6 nexthdr icmpv6 icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept
        tcp dport 22 ct state new limit rate 4/minute accept
        tcp dport 22 ct state new log prefix "SSH-RATELIMIT-DROP: " level info drop
        tcp dport { 80, 443 } accept
        log prefix "INPUT-DROP: " level info limit rate 1/second
    }
    chain forward { type filter hook forward priority filter; policy drop; }
    chain output { type filter hook output priority filter; policy accept; }
}
EOF
    nft -c -f /etc/nftables.conf
    nft -f /etc/nftables.conf
    systemctl enable --now nftables.service
    log "nftables ruleset installed and persisted"
}

install_fail2ban() {
    if ! command -v fail2ban-client >/dev/null; then
        apt update && apt install -y fail2ban
    fi
    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 3
backend  = systemd

[sshd]
enabled = true
port    = ssh
EOF
    systemctl enable --now fail2ban
    log "fail2ban configured"
}

main() {
    require_root
    apt update && apt upgrade -y
    apt install -y nftables fail2ban
    ensure_user
    install_sshd_config
    install_nftables
    install_fail2ban
    log "C14 mini-project hardening complete"
    log "Now SSH as: ssh ${ADMIN_USER}@<this-host>"
    log "And exit this root session."
}

main "$@"
```

Save as `scripts/install.sh`. Run on a fresh VPS:

```bash
ssh root@your.vps.ip
curl -sSf https://raw.githubusercontent.com/your-name/portfolio/main/c14-week-06/mini-project/scripts/install.sh | ADMIN_USER=your-name bash
# OR if you cloned the repo:
sudo ADMIN_USER=your-name bash install.sh
```

The script must be idempotent: re-running it is a no-op (or at worst a re-apply of the same config).

---

## The `verify.sh`

Run from your **laptop**, not the VPS. Performs all outside checks.

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

TARGET="${1:?usage: verify.sh <target.ip-or-hostname>}"
OUT="evidence"
mkdir -p "$OUT"

log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }

run_nmap() {
    log "running nmap -sV -p- (this may take 10-20 min)..."
    nmap -sV -p- --reason "$TARGET" > "$OUT/nmap.txt"
    grep -E '^[0-9]+/tcp' "$OUT/nmap.txt"
}

check_only_expected_open() {
    local open_ports
    open_ports=$(grep -E '^[0-9]+/tcp\s+open' "$OUT/nmap.txt" | awk '{print $1}' | sort)
    local expected="22/tcp 80/tcp 443/tcp"
    log "open ports: $(echo "$open_ports" | tr '\n' ' ')"
    for port in $open_ports; do
        if ! grep -q "$port" <<<"$expected"; then
            log "UNEXPECTED open port: $port"
            return 1
        fi
    done
}

run_ssh_audit() {
    if command -v ssh-audit >/dev/null; then
        log "running ssh-audit..."
        ssh-audit "$TARGET" > "$OUT/ssh-audit.txt" || true   # exits non-zero on fail-but-readable
        tail -20 "$OUT/ssh-audit.txt"
    else
        log "ssh-audit not installed; skipping"
    fi
}

main() {
    log "verifying $TARGET"
    run_nmap
    check_only_expected_open
    run_ssh_audit
    log "verify.sh complete; see $OUT/"
}

main "$@"
```

Run with: `bash scripts/verify.sh your.vps.ip`. Exits non-zero if unexpected ports are open.

---

## The `runbook.md`

One page. Operational shape. Format:

```markdown
# C14 Mini-Project Runbook

## VPS
- Provider: <X>
- Region: <Y>
- Plan: <Z>
- Public IP: <a.b.c.d>
- Hostname: <c14-mini.your-name.tld>
- Provisioned: <date>

## SSH
- Connect: `ssh c14admin@<host>`
- Key on laptop: `~/.ssh/id_ed25519`
- AuthMethod: publickey only (no passwords accepted)
- Root: cannot log in remotely
- Allowed users: `c14admin`

## Firewall
- nftables, rules in `/etc/nftables.conf`
- Open ports: 22, 80, 443
- Persistent: `nftables.service` (enabled)

## Common operations

### Add a new SSH user
1. `sudo adduser <name>`
2. Copy public key to `/home/<name>/.ssh/authorized_keys`
3. Edit `/etc/ssh/sshd_config.d/99-c14-hardened.conf`, add to `AllowUsers`
4. `sudo sshd -t && sudo systemctl reload sshd`

### Open a new port
1. Edit `/etc/nftables.conf`
2. `sudo nft -c -f /etc/nftables.conf` (validate)
3. `sudo systemctl reload nftables.service`
4. Verify from outside: `nmap -p <port> <host>`

### Read recent SSH attempts
- `sudo journalctl -u sshd --since "1 hour ago"`

### Recover if locked out
1. Open the VPS provider's web console (link: <provider-console-url>).
2. Log in via console (you have a root password from setup or can reset via provider).
3. `sudo systemctl restart nftables.service` to re-load known-good rules from `/etc/nftables.conf`.
4. Or `sudo systemctl revert ssh` (removes drop-ins) to revert sshd_config.

### Upgrade packages
- `sudo apt update && sudo apt upgrade -y`
- `[ -f /var/run/reboot-required ] && sudo reboot`

## Emergency contacts
- (you)
- (one trusted person who has the recovery key, optional)
```

---

## Acceptance criteria

- The VPS is real, public, and addressable by IP or DNS.
- `ssh c14admin@host` (or your equivalent) works with your key, no password prompt.
- `ssh root@host` is refused.
- `sudo sshd -T | grep -E 'permitroot|passwordauth|authmethods'` shows the hardened values.
- `sudo nft list ruleset` shows the input chain with policy `drop` and the expected rules.
- `nmap -sV -p- host` from your laptop reports only 22 (and 80/443 if running) as `open`. Everything else `filtered`.
- `nftables.service` is enabled (boot-time persistence).
- `scripts/install.sh` is idempotent (re-running doesn't fail or duplicate state).
- `scripts/verify.sh` exits zero on a correctly-hardened host.
- `runbook.md` is complete enough that another engineer could operate the VPS.
- 7 days after the initial setup, `evidence/auth-report.md` shows the brute-force attempts the server saw.

---

## Grading rubric

| Element | Points |
|---------|-------:|
| VPS provisioned and reachable | 5 |
| `sshd_config` hardened (PermitRootLogin no, PasswordAuthentication no, AuthMethods publickey) | 10 |
| Non-root sudo user with key-only auth | 5 |
| Crypto tightened (KexAlgorithms / Ciphers / MACs) | 5 |
| `nftables` ruleset with policy drop on input | 10 |
| Loopback and conntrack rules present | 5 |
| Only 22 (and 80/443 if used) reachable from `nmap` | 15 |
| `nftables.service` enabled and survives reboot | 10 |
| `install.sh` is idempotent and exits zero on a clean run | 10 |
| `verify.sh` runs from laptop, exits non-zero on any anomaly | 5 |
| `runbook.md` is operationally complete | 10 |
| `evidence/` has before, after, and auth-report files | 5 |
| Optional Fail2Ban installed and effective | 5 |
| **Total** | **100** |

90+ = portfolio quality. 80-89 = solid but a rough edge or two. 70-79 = needs revision before week 7. <70 = re-read both lectures, redo exercise 03, then try again.

---

## Stretch goals

- **DNS A record.** Get a domain (Namecheap, Porkbun, Cloudflare Registrar; ~$10/yr for a `.com`, free for many `.dev` and `.app`-style TLDs with special pricing). Point an A record at your VPS. Re-test SSH/nmap against the hostname.
- **Let's Encrypt certificate.** `sudo certbot --nginx -d your.vps.tld` (if nginx is running) or `--standalone -d your.vps.tld` (if not). Confirm the cert via `openssl s_client -connect your.vps.tld:443` from your laptop.
- **Unattended upgrades.** `sudo apt install unattended-upgrades && sudo dpkg-reconfigure unattended-upgrades`. Auto-applies security patches.
- **Two-factor SSH.** Add `google-authenticator` + a Match block that adds `AuthenticationMethods publickey,keyboard-interactive:pam` for one user. TOTP from a phone app, in addition to the key. Bash Yellow: test with a held-open session.
- **Per-source SSH allow-list.** Replace the public SSH `accept` with `ip saddr @ssh_allow tcp dport 22 accept`. Manage the set with `nft add element inet filter ssh_allow { x.y.z.w }` when you change IPs.
- **Auditbeat / Wazuh / OSSEC.** A host-based intrusion-detection system. The configuration is heavy; this is a real-DevOps-style addition. Optional.
- **Backups.** Set up `restic` (or `borg` or `rsync.net`) to back up `/etc`, `/home`, and `/var/lib` to off-host storage. Test restore. Week 8 covers this in depth; doing it now is great prep.
- **Public uptime monitor.** Sign up for a free tier of UptimeRobot / BetterStack / Hetrix and point it at your VPS. Get an alert when it goes down. Week 8 expects this for the capstone.

---

## Reflection (after completion)

In `notes.md`, after the project is done, answer:

1. Which step in the hardening surprised you most? What did you learn from it that wasn't in the lecture?
2. Read the `journalctl -u sshd` output for the first hour after provisioning. How quickly did the brute-force attempts start? What does that tell you about port 22 as the default?
3. Pick one directive in `sshd_config` we did **not** tighten. Read its man-page entry. Argue (one paragraph) for or against tightening it.
4. Pick one nftables construct we did **not** use (a `vmap`, a `chain` jump, a `counter`). Sketch how it would simplify or extend your current ruleset.
5. The first time `nmap` showed an unexpected open port, what was it, and how did you fix it? (If it never did: pretend it did, and answer for one of `5432`, `6379`, `9200`, or whatever your `ss -tulpn` showed listening on `0.0.0.0`.)

---

## Up next

Once your VPS is hardened, verified, and documented, you're done with Week 6. Keep it running — Week 7 (observability) and Week 8 (backup, capstone) build on it.

[Week 7 — Observability and "why is it slow?"](../../week-07/) — when the service on this VPS starts behaving oddly, and you need to find out which of the four pillars (CPU, memory, disk, network) is suffering.

---

*A hardened VPS is not a paranoid VPS. It is a VPS that, when it goes wrong, goes wrong in the smallest possible way — usually a misconfigured firewall rule that you can fix from the provider's web console in three minutes.*
