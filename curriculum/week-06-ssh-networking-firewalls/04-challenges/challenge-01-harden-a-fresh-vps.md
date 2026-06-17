# Challenge 01 — Harden a Fresh VPS

**Difficulty:** medium. **Time:** ~2 hours. **Goal:** Take a freshly-provisioned $5/mo VPS from "click 'create'" to "production-shaped" — root login disabled, key-only SSH, non-root admin user with sudo, hardened `sshd_config`, hardened `nftables` ruleset, optional `Fail2Ban`, verified with `nmap` from outside. Document everything as a runbook another engineer could follow.

This challenge is the first half of the Week 6 mini-project, executed as a single sitting. The mini-project asks you to keep the VPS running for a week and add a service. This challenge stops at "hardened and verified."

## Pre-requisites

- Exercises 01, 02, 03 complete.
- A $5/mo VPS account at one of: Hetzner (€4.51), Vultr ($5), DigitalOcean ($6), Linode ($5), Scaleway (€3.50). All offer Ubuntu 24.04 LTS images.
- A credit card or PayPal. Most providers charge per-hour, so a $5/mo VPS run for one day costs ~$0.17.
- Your ed25519 key from exercise 01.

## The runbook target

Write your work as a `runbook.md` that another engineer could follow start-to-finish, on a fresh VPS, with no other context. Treat it as the deliverable. If your runbook says "click the button you know," it isn't a runbook.

---

## Step 1 — Provision (10 min)

Pick a region close to you (low latency for SSH). Pick the smallest plan ($5/mo or equivalent). Pick Ubuntu 24.04 LTS as the image.

**At provisioning time**, paste the contents of `~/.ssh/id_ed25519.pub` (one line, from your laptop) into the provider's "SSH keys" field. The provider will inject it into the default user's `~/.ssh/authorized_keys`.

Default users by provider:

- **Hetzner**, **Vultr**, **DigitalOcean** (root images): `root`.
- **DigitalOcean** (Ubuntu image with cloud-init customization): you can specify the user.
- **Linode**: `root`.
- **AWS EC2**: `ubuntu` (Ubuntu AMI), `ec2-user` (Amazon Linux).

For this challenge, assume the default is `root`. We'll create a non-root user as our first action.

Wait until the VPS shows "Active" / "Running" in the provider's dashboard. Note the public IP.

## Step 2 — Initial connect (5 min)

```bash
# On your laptop:
ssh -o StrictHostKeyChecking=accept-new root@your.vps.ip
# Welcome to Ubuntu 24.04.2 LTS ...
root@vps:~#
```

`-o StrictHostKeyChecking=accept-new` writes the host key to `~/.ssh/known_hosts` without prompting. (You can verify the host key fingerprint against the provider's web console first if you're paranoid — most providers show it.)

Update the system:

```bash
apt update && apt upgrade -y
apt autoremove -y
```

Reboot if the kernel was updated:

```bash
# Check:
[ -f /var/run/reboot-required ] && echo "reboot required" || echo "no reboot needed"

# If needed:
reboot
# Wait 30 seconds, then SSH back in.
```

## Step 3 — Create a non-root user (10 min)

```bash
# As root, on the VPS:
adduser --gecos "" your-name
# Set a password (we'll disable password auth later, but it's required for the prompt).

usermod -aG sudo your-name           # grant sudo

# Copy your key to the new user:
mkdir -p /home/your-name/.ssh
cp ~/.ssh/authorized_keys /home/your-name/.ssh/
chown -R your-name:your-name /home/your-name/.ssh
chmod 700 /home/your-name/.ssh
chmod 600 /home/your-name/.ssh/authorized_keys
```

Test from your laptop (do **not** close the root session):

```bash
# In a new terminal on your laptop:
ssh your-name@your.vps.ip
# Welcome ...
your-name@vps:~$ sudo -v
# Enter password — should succeed.
```

If both succeed, you have a working non-root admin user.

## Step 4 — Harden `sshd_config` (15 min)

In a held-open root session (or your new your-name session with `sudo`):

```bash
sudoedit /etc/ssh/sshd_config.d/99-c14-hardened.conf
```

Contents:

```
# C14 Week 6 — hardened SSH

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

# Optional: tighten crypto
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,sntrup761x25519-sha512@openssh.com
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
```

Validate, reload, test from a new terminal — as in exercise 01 part 4.

```bash
sudo sshd -t                                  # silent = OK
sudo systemctl reload sshd
# In a new terminal: ssh your-name@your.vps.ip      # must succeed
```

Confirm root login is denied:

```bash
ssh root@your.vps.ip
# root@your.vps.ip: Permission denied (publickey).
```

## Step 5 — Configure `nftables` (20 min)

```bash
sudoedit /etc/nftables.conf
```

Use the ruleset from lecture 2 §4. Save.

Validate, apply, persist. (See exercise 03 parts 2-4.)

```bash
sudo nft -c -f /etc/nftables.conf
sudo nft -f /etc/nftables.conf
sudo systemctl enable nftables.service
```

Confirm:

```bash
sudo nft list ruleset
```

## Step 6 — Optional: `Fail2Ban` (15 min)

`Fail2Ban` is belt-and-suspenders. With `PasswordAuthentication no` already, the value is marginal — attackers can't try passwords anyway. But it's traditional, and the journal evidence is useful.

```bash
sudo apt install -y fail2ban
sudoedit /etc/fail2ban/jail.local
```

Contents:

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

Start it:

```bash
sudo systemctl enable --now fail2ban
sudo fail2ban-client status sshd
```

Watch the journal for bans:

```bash
sudo journalctl -u fail2ban -f
```

Within a few hours, you will see something like:

```
fail2ban.actions [1234]: NOTICE [sshd] Ban 1.2.3.4
```

Welcome to the internet.

## Step 7 — Verify from outside (15 min)

From your laptop:

```bash
nmap -sV -p- --reason your.vps.ip > ~/c14-week-06/challenges/01/nmap-final.txt
```

Wait 10-20 minutes. Read the output.

Expected:

```
PORT    STATE  SERVICE  REASON          VERSION
22/tcp  open   ssh      syn-ack ttl 56  OpenSSH 9.6p1 Ubuntu ...
80/tcp  open   http     syn-ack ttl 56  ...
443/tcp open   https    syn-ack ttl 56  ...
Not shown: 65532 filtered tcp ports (no-response)
```

If you didn't install nginx/Apache, `80` and `443` may be missing from the open list. That's fine — they're allowed by the firewall but nothing is listening.

Run `ssh-audit`:

```bash
ssh-audit your.vps.ip > ~/c14-week-06/challenges/01/ssh-audit-final.txt
```

Read the output. You should be all-green or near-it after the `KexAlgorithms` / `Ciphers` tightening in step 4.

## Step 8 — Document (20 min)

Write `runbook.md`:

```markdown
# VPS Hardening Runbook

## Provider, plan, region
- Provider: <Hetzner / Vultr / DigitalOcean / ...>
- Plan: $5/mo, 1 vCPU, 1 GB RAM
- Region: <choose>
- Image: Ubuntu 24.04 LTS

## Public IP and DNS
- IP: <your.vps.ip>
- DNS: (optional — A record at your.domain.com)

## Step-by-step
1. Provision with SSH key at creation time.
2. SSH as root, update, reboot if kernel changed.
3. Create non-root user with sudo and the same key.
4. Edit /etc/ssh/sshd_config.d/99-c14-hardened.conf. Validate. Reload.
5. Write /etc/nftables.conf. Validate. Apply. Enable nftables.service.
6. (Optional) Install fail2ban; configure jail.local; enable.
7. Reboot. Confirm everything still works.
8. nmap from laptop; ssh-audit. Save outputs.

## Files on the VPS
- /etc/ssh/sshd_config.d/99-c14-hardened.conf
- /etc/nftables.conf
- /etc/fail2ban/jail.local (optional)

## Files in this directory
- runbook.md (this file)
- sshd-hardened.conf (copy of /etc/ssh/sshd_config.d/99-c14-hardened.conf)
- nftables.conf (copy of /etc/nftables.conf)
- jail.local (copy of fail2ban config, if installed)
- nmap-final.txt
- ssh-audit-final.txt

## Time spent
- Total: <N> hours

## Surprises / lessons
- (2-3 paragraphs)
```

## Acceptance criteria

- `ssh root@your.vps.ip` is refused.
- `ssh your-name@your.vps.ip` succeeds with your key, no password prompt.
- `sudo sshd -T` on the VPS reports the hardened directives.
- `sudo nft list ruleset` shows the input chain with the expected rules.
- `nmap -sV -p- your.vps.ip` from outside reports only 22 (and 80, 443 if you have services) as `open`.
- `nftables.service` is `enabled`.
- `runbook.md` is complete enough that another engineer could replicate your setup.

If all six pass, the challenge is done.

## Stretch additions

- **DNS A record.** Point a hostname at the VPS IP. Re-test SSH and nmap against the hostname, not the IP. Confirms DNS resolution path works.
- **Certbot.** Install a real TLS certificate from Let's Encrypt for the DNS name. Use `certbot --nginx` or `certbot --standalone`. Confirm `nmap` still shows 443/tcp open and the cert is valid.
- **Reverse DNS.** Set a PTR record at the provider for the VPS IP. Some mail servers refuse mail from hosts without rDNS; for an SSH-only box it's cosmetic.
- **Unattended upgrades.** `sudo apt install unattended-upgrades && sudo dpkg-reconfigure unattended-upgrades`. Now security patches install automatically; you read the digest by email or `journalctl -u unattended-upgrades`.
- **Audit log.** Run `ssh-audit` weekly (or `sudo journalctl -u sshd --since "1 week ago" | grep "Accepted publickey"`) and confirm only your IPs appear.

---

*A fresh VPS at the moment of provisioning is the most vulnerable it will ever be: every default is permissive, the brute-forcers have already started. The first hour is the difference between a server you run and a botnet member. This runbook is that first hour, written down.*
