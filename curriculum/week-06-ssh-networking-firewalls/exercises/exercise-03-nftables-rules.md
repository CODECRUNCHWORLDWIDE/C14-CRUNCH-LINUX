# Exercise 03 — Write an `nftables` Ruleset

**Time:** ~3 hours. **Goal:** Write a hardened `nftables` ruleset on a real Linux host. The ruleset accepts only SSH (TCP 22), HTTP (TCP 80), and HTTPS (TCP 443). Default-drops everything else. Logs dropped packets at a sane rate. Persists across reboot with `nftables.service`. Verify the result by running `nmap` from a **second host** and confirming only the allowed ports are `open`.

You will need:

- The **target** server you used in exercises 01 and 02 (or any Linux host with `sudo` and `nftables` ≥ 1.0).
- A **second host** from which to scan (your laptop is fine, as long as it can reach the target). You need `nmap` installed there.
- A **rollback path** — a held-open second SSH session, the VPS provider's web console, or a hypervisor console. The rule that goes wrong here will sever your SSH; you need a way back in.

This exercise is the most dangerous in Week 6. If you have not snapshotted your target, do that first. On a VPS, take a backup. On a VM, save the state. On bare metal, accept that you may need physical access.

Verify on the target:

```bash
sudo nft --version
# nftables v1.0.9 or newer

sudo systemctl status nftables.service
# Loaded: loaded (...; preset: enabled)
# Active: inactive (dead) -- or active, depending on distro defaults

sudo systemctl cat nftables.service | grep -i ExecStart
# ExecStart=/usr/sbin/nft -f /etc/nftables.conf       (Ubuntu)
# OR
# ExecStart=/usr/sbin/nft -f /etc/sysconfig/nftables.conf  (Fedora)
```

Note **which path** your `nftables.service` reads. That's the file you'll edit.

Set up scratch on your laptop:

```bash
mkdir -p ~/c14-week-06/exercises/03
cd ~/c14-week-06/exercises/03
```

---

## Part 1 — Baseline: what's listening, what's reachable (20 min)

### Step 1.1 — On the target: what's listening?

```bash
ssh target
sudo ss -tulpn
# Netid State  Recv-Q Send-Q  Local Address:Port  Peer Address:Port  Process
# tcp   LISTEN 0      128          0.0.0.0:22         0.0.0.0:*       users:(("sshd",pid=...))
# tcp   LISTEN 0      511        127.0.0.1:5432        0.0.0.0:*       users:(("postgres",pid=...))
# udp   UNCONN 0      0          0.0.0.0:68          0.0.0.0:*       users:(("systemd-networkd",...))
```

Walk through every row. For each:

- What process is it? (`Process` column.)
- Is it on `0.0.0.0` (public) or `127.0.0.1` (loopback only)?
- Do you want it reachable from the internet?

Anything you don't recognize is a follow-up question. For now, just note them.

### Step 1.2 — From your laptop: what's reachable?

Install `nmap` on your laptop if you don't have it:

```bash
# Debian/Ubuntu:
sudo apt install nmap

# Fedora:
sudo dnf install nmap

# macOS:
brew install nmap
```

Scan the target (run from your laptop, not from the target):

```bash
nmap -sV -p- --reason --top-ports 100 your.target.ip > ~/c14-week-06/exercises/03/nmap-before.txt
cat ~/c14-week-06/exercises/03/nmap-before.txt
```

`-sV` enumerates service versions; `-p-` would be all 65535 ports but takes 10-20 minutes; `--top-ports 100` keeps it under a minute for the baseline. Run `-p-` later for the final verification.

Read every line. Right now, on a fresh server with no firewall, you may see:

```
PORT     STATE  SERVICE  REASON          VERSION
22/tcp   open   ssh      syn-ack ttl 56  OpenSSH 9.6p1 ...
80/tcp   open   http     syn-ack ttl 56  nginx 1.24.0
443/tcp  open   https    syn-ack ttl 56  nginx 1.24.0
5432/tcp open   postgresql syn-ack ttl 56 PostgreSQL DB 16
```

If `5432/tcp` (PostgreSQL) is reachable from the internet, that is a problem entirely independent of nftables — your PostgreSQL is bound to `0.0.0.0`, which it shouldn't be. We'll fix it with the firewall in part 3; long-term, fix the postgres config too.

---

## Part 2 — Write the ruleset (45 min)

### Step 2.1 — Pick the file path

```bash
ssh target
sudo systemctl cat nftables.service | grep ExecStart
```

Note the path. We'll call it `NFTCONF` below. On Ubuntu: `/etc/nftables.conf`. On Fedora: `/etc/sysconfig/nftables.conf`.

### Step 2.2 — Write the file

```bash
sudoedit $NFTCONF
```

Contents:

```nftables
#!/usr/sbin/nft -f

# C14 Week 6 Exercise 03 — hardened single-host firewall
# Reload with: sudo systemctl reload nftables.service

flush ruleset

table inet filter {

    chain input {
        type filter hook input priority filter; policy drop;

        # 1. Existing connections.
        ct state established,related accept

        # 2. Drop invalid conntrack states.
        ct state invalid drop

        # 3. Loopback.
        iif lo accept

        # 4. ICMPv4 essentials.
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } accept limit rate 4/second

        # 5. ICMPv6 essentials.
        ip6 nexthdr icmpv6 icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept

        # 6. SSH — rate-limited to slow brute-force.
        tcp dport 22 ct state new limit rate 4/minute accept
        tcp dport 22 ct state new log prefix "SSH-RATELIMIT-DROP: " level info drop

        # 7. HTTP + HTTPS.
        tcp dport { 80, 443 } accept

        # 8. Log anything else that's about to be dropped (rate-limited to avoid log floods).
        log prefix "INPUT-DROP: " level info limit rate 1/second
        # The policy `drop` at the chain header does the actual drop after the log rule.
    }

    chain forward {
        type filter hook forward priority filter; policy drop;
        # Not a router. Everything dropped.
    }

    chain output {
        type filter hook output priority filter; policy accept;
        # Trust outbound. Replace with rules + policy drop if you want egress filtering.
    }
}
```

Save.

### Step 2.3 — Syntax check (do this before anything else)

```bash
sudo nft -c -f $NFTCONF
# (silent = OK)
```

`-c` is "check, do not commit." If it prints errors, fix them before continuing. **Do not** run `nft -f` until `nft -c` is silent.

---

## Part 3 — Apply the ruleset (carefully) (30 min)

This is the dangerous step. Read the entire part before doing it.

### Step 3.1 — Hold a second SSH session open

```bash
# Terminal A — your "safe" session. Do not touch this.
ssh target

# Terminal B — where you will apply changes. Use this one.
ssh target
```

### Step 3.2 — Set up an auto-rollback (the `at` trick)

In Terminal B:

```bash
sudo apt install at        # if not already
# OR: sudo dnf install at

# Schedule a flush in 2 minutes, in case the apply locks us out:
echo "/usr/sbin/nft flush ruleset" | sudo at now + 2 minutes 2>&1
# Note the job number (e.g., "job 5 at ...").
sudo atq                   # confirms the job is queued
```

The plan: apply the ruleset; confirm it works within 2 minutes; cancel the `at` job. If you can't confirm within 2 minutes, the `at` will fire and the ruleset will be flushed, restoring access.

### Step 3.3 — Apply

In Terminal B:

```bash
sudo nft -f $NFTCONF
# (silent = OK)
```

Immediately check that Terminal A is still alive (type a command in it — if it works, your SSH session survived).

### Step 3.4 — Open a third terminal and confirm

```bash
# Terminal C — a fresh shell from your laptop:
ssh target
# Should succeed within a few seconds.
```

If it does: your firewall accepts new SSH connections. You're past the danger.

### Step 3.5 — Cancel the auto-rollback

```bash
# In Terminal B:
sudo atrm 5         # use the job number from step 3.2
sudo atq            # should be empty now
```

### Step 3.6 — If it failed

If Terminal C can't connect, your firewall is blocking SSH. The `at` job will fire in <2 minutes and restore access — wait for it. Then read your `INPUT-DROP` log:

```bash
sudo journalctl -k --since "5 minutes ago" | grep INPUT-DROP
# kernel: INPUT-DROP: IN=eth0 OUT= MAC=... SRC=your.laptop.ip DST=... PROTO=TCP SPT=... DPT=22 ...
```

If you see `DPT=22` dropped from your own IP, your SSH rule is wrong. Common bugs:

- `tcp dport 22 ct state new limit rate 4/minute accept` — if you SSH'd 5 times in a minute, you ate the rate limit. Increase to `10/minute` for the exercise.
- The `accept` is after a `drop` for some other reason.
- You wrote `tcp dport ssh accept` and your distro doesn't resolve `ssh` to `22` (most do; Alpine doesn't).

Fix and re-run.

---

## Part 4 — Persist across reboot (15 min)

### Step 4.1 — Enable the service

```bash
sudo systemctl enable nftables.service
sudo systemctl status nftables.service
```

If `nftables.service` was already running and reading from `$NFTCONF`, your applied rules are already there. If not, `systemctl reload nftables.service` re-reads the file.

### Step 4.2 — Reboot the target

```bash
sudo reboot
```

Wait 30-60 seconds. SSH back in:

```bash
ssh target
sudo nft list ruleset
# Expect to see your ruleset, same as before reboot.
```

If the ruleset is **empty** after reboot:

- `nftables.service` didn't load on boot. `sudo systemctl status nftables.service`. Check for errors.
- The file is in the wrong path. `systemctl cat nftables.service` to confirm what path the unit reads.
- Some other firewall (e.g., `firewalld` on Fedora) is running and overwriting. Stop and mask it: `sudo systemctl disable --now firewalld && sudo systemctl mask firewalld`.

---

## Part 5 — Verify from outside (30 min)

This is the only honest test that the firewall works.

### Step 5.1 — Full port scan

From your laptop (not the target):

```bash
nmap -sV -p- --reason your.target.ip > ~/c14-week-06/exercises/03/nmap-after.txt
cat ~/c14-week-06/exercises/03/nmap-after.txt
```

This takes 10-20 minutes; let it run. Expected:

```
Nmap scan report for your.target.ip
Host is up, received echo-reply ttl 56 (0.012s latency).
Not shown: 65532 filtered tcp ports (no-response)
PORT    STATE  SERVICE  REASON          VERSION
22/tcp  open   ssh      syn-ack ttl 56  OpenSSH 9.6p1 Ubuntu ...
80/tcp  open   http     syn-ack ttl 56  nginx 1.24.0 (Ubuntu)
443/tcp open   https    syn-ack ttl 56  nginx 1.24.0 (Ubuntu)
```

The "Not shown: 65532 filtered" is the win condition. Everything except 22/80/443 is silently dropped.

If `5432/tcp` (or any other port you saw in part 1) is still `open` here: the firewall is **not** working for that port. Investigate; the rule order may be wrong, or there's a competing firewall.

### Step 5.2 — Confirm "filtered" vs "closed"

A `filtered` port means your firewall dropped silently. A `closed` port means something replied with RST (e.g., your firewall used `reject` instead of `drop`, or there's nothing listening and no firewall). On a hardened host, you want `filtered`.

```bash
grep -i filtered ~/c14-week-06/exercises/03/nmap-after.txt | head -5
```

Should report 65,532 (or so) filtered ports.

### Step 5.3 — Test the rate limiter

```bash
# From your laptop, hit SSH 10 times rapidly:
for i in {1..10}; do
    ssh -o ConnectTimeout=2 -o BatchMode=yes target true 2>&1 | head -1
done
```

The first 4 should succeed (returning silently). The next 6 should hang or get refused — the rate limiter dropped them.

On the target, the journal records the drops:

```bash
sudo journalctl -k --since "1 minute ago" | grep SSH-RATELIMIT
# kernel: SSH-RATELIMIT-DROP: IN=eth0 OUT= MAC=... SRC=your.laptop.ip ... DPT=22 ...
```

---

## Part 6 — Refactor to use a set (optional, 20 min)

The current SSH rule rate-limits **all** SSH attempts together. A more granular version uses a dynamic set keyed by source IP.

Edit `$NFTCONF`:

```nftables
table inet filter {

    set ssh_blacklist {
        type ipv4_addr
        size 65535
        flags dynamic, timeout
        timeout 10m
    }

    chain input {
        type filter hook input priority filter; policy drop;

        ct state established,related accept
        ct state invalid drop
        iif lo accept

        # ICMP (as before)
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } accept limit rate 4/second
        ip6 nexthdr icmpv6 icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept

        # Blacklist first (any IP in @ssh_blacklist is dropped)
        ip saddr @ssh_blacklist drop

        # Add to blacklist if more than 4 SSH SYNs per minute from one source
        tcp dport 22 ct state new add @ssh_blacklist { ip saddr limit rate over 4/minute } log prefix "SSH-BANNED: " drop

        # Accept SSH (the matching rule above already dropped abusers)
        tcp dport 22 accept

        tcp dport { 80, 443 } accept

        log prefix "INPUT-DROP: " level info limit rate 1/second
    }

    chain forward { type filter hook forward priority filter; policy drop; }
    chain output { type filter hook output priority filter; policy accept; }
}
```

Validate, apply, test, persist. Note that the `set` is **dynamic**: entries are added by the rule itself; they time out after 10 minutes.

To inspect:

```bash
sudo nft list set inet filter ssh_blacklist
# table inet filter {
#     set ssh_blacklist {
#         type ipv4_addr
#         size 65535
#         flags dynamic, timeout
#         timeout 10m
#         elements = { 1.2.3.4 timeout 9m48s expires 9m48s }
#     }
# }
```

This is a homegrown `Fail2Ban` in 10 lines of nftables.

---

## Part 7 — Document and commit (15 min)

Capture the running ruleset:

```bash
ssh target "sudo nft list ruleset" > ~/c14-week-06/exercises/03/nft-list-ruleset.txt
```

Save your `nftables.conf`:

```bash
ssh target "sudo cat /etc/nftables.conf" > ~/c14-week-06/exercises/03/nftables.conf
# (or /etc/sysconfig/nftables.conf on Fedora — adjust)
```

Write `notes.md`:

```markdown
# Exercise 03 — Notes

## Topology
- Target: <hostname> (<public IP>)
- Scanned from: <laptop hostname / location>

## What's on the target
- Listening sockets (from `ss -tulpn`): <list>
- Public-facing ports (from nmap-before): <list>
- Public-facing ports after firewall (from nmap-after): 22, 80, 443

## The ruleset (key decisions)
- inet family (covers IPv4 + IPv6 in one ruleset)
- policy drop on input chain (allow-list model)
- ct state established,related accept (rule one)
- iif lo accept (rule two)
- SSH rate-limited to N/minute
- HTTP+HTTPS open
- Logs to journald with rate-limited prefix

## The rate-limit test
- Test command: <command>
- Expected: first N succeed, rest dropped
- Observed: <result>
- Journal evidence: <one line of SSH-RATELIMIT-DROP log>

## Reboot survival
- Rebooted the target; nft list ruleset shows the same ruleset.
- nftables.service is enabled and active.

## What I'd change for production
- (2-3 bullets — e.g., source restriction on SSH, narrower CIDR for HTTP, etc.)
```

Commit to your portfolio repo under `c14-week-06/exercises/03/`.

---

## Acceptance criteria

- `sudo nft list ruleset` on the target shows the input chain with `policy drop` and the rules above.
- `nmap -sV -p- your.target.ip` from a remote host shows only 22, 80, 443 as `open`. Everything else `filtered`.
- The rate limiter drops SSH attempts after the limit; the journal records `SSH-RATELIMIT-DROP` for the dropped attempts.
- After `sudo reboot`, `nft list ruleset` is unchanged.
- `nftables.service` is `enabled` (boot-time persistence).
- `sudo nft -c -f $NFTCONF` is silent (no syntax errors).

---

## Common failure modes

- **`sudo nft -f /etc/nftables.conf` returns "Error: syntax error".**
  Read the error line and column. nftables errors usually point to the exact issue. Common: unclosed brace, missing semicolon, typo in keyword.
- **The ruleset loads but SSH stops working.**
  Your auto-rollback `at` job will fire. Look at the journal for `INPUT-DROP` lines; find your laptop's IP; understand why it was dropped. Most likely the SSH rule is wrong or comes after a drop.
- **After reboot, no firewall.**
  Either `nftables.service` isn't enabled, or it's reading from the wrong path, or another firewall (firewalld) is winning. `systemctl status nftables.service`; `systemctl cat nftables.service`; `systemctl status firewalld` if applicable.
- **`nmap` says everything is `filtered` including 22.**
  Your firewall is too tight; the SSH rule isn't matching. Run `sudo nft list ruleset` and read the input chain top to bottom. Confirm the SSH `accept` rule is **before** any blanket drop and **after** the `ct state established,related accept`.
- **`nmap` says ports `closed`, not `filtered`.**
  Your chain policy is `reject` instead of `drop`. (Or `nftables` is offline and the kernel is sending RSTs on its own.) Either is acceptable security-wise; the cosmetic difference is whether the scanner knows it was firewalled (closed) or doesn't (filtered).
- **`SSH-RATELIMIT-DROP` never appears in the journal, even after rapid SSH.**
  The rate limit is too generous, or your `limit rate` syntax is wrong. Try `2/minute` for a guaranteed trip.

---

*A firewall that you never tested with `nmap` from outside is a hypothesis. A firewall that survived a reboot is a fact. A firewall that survived an aggressive `nmap -p-` and reported only the ports you opened is what you ship.*
