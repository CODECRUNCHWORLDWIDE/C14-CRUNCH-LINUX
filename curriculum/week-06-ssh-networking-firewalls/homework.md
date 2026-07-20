# Week 6 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-06/homework/`.

These are practice problems between the exercises (which drilled the basics) and the mini-project (which asks you to compose freely). Every SSH config change must pass `sudo sshd -t` before reload; every nftables ruleset change must pass `sudo nft -c -f FILE` before apply.

---

## Problem 1 — Tighten the SSH crypto (60 min)

The lecture showed a baseline hardened `sshd_config`. The Mozilla "Modern" OpenSSH baseline tightens further by restricting `KexAlgorithms`, `Ciphers`, `MACs`, and `HostKeyAlgorithms` to only the algorithms not known to be weak.

Write `homework/01-crypto-tightening.conf` for your server's `/etc/ssh/sshd_config.d/`:

```
# Mozilla "Modern" baseline (OpenSSH 9.x)
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,sntrup761x25519-sha512@openssh.com
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
HostKeyAlgorithms ssh-ed25519,rsa-sha2-512,rsa-sha2-256
```

Apply, reload (with a held-open session), and run `ssh-audit your.host` before and after. Save both outputs.

**Acceptance:** `homework/01-crypto-tightening.conf`, `homework/01-ssh-audit-before.txt`, `homework/01-ssh-audit-after.txt`, and `homework/01-notes.md` (3-4 sentences on what changed in the audit output).

---

## Problem 2 — A `Match` block for one user (45 min)

Add a `Match` block to `/etc/ssh/sshd_config.d/02-restricted.conf` that does **one** of the following:

- (a) Forces a specific command (`ForceCommand /usr/local/bin/restricted-shell`) for a user named `backup-bot`.
- (b) Restricts a user to a specific source network (`AllowUsers your-user@203.0.113.0/24`) so they can only log in from your home/work IP range.
- (c) Disables agent forwarding, X11, and TCP forwarding for a `Group operators` (defense in depth — operators get shells but not tunnels).

Pick one. Implement it. Test it (the matched user / group / source actually behaves differently). Document the change in `homework/02-notes.md`.

**Acceptance:** `homework/02-restricted.conf` (the drop-in), `homework/02-notes.md` (the choice, the test command you ran, the observed behavior).

---

## Problem 3 — `~/.ssh/config` with multiple identities (45 min)

Write a `~/.ssh/config` that handles:

- A personal GitHub account (`github.com`) with one key.
- A work GitHub account (`github-work` is the `Host` alias; `HostName github.com`) with a **different** key.
- Your VPS (one stanza).
- A bastion + private host pair (two stanzas, with `ProxyJump`).
- A `Host *` global block with `IdentitiesOnly yes`, `AddKeysToAgent yes`, `ServerAliveInterval 60`, `HashKnownHosts yes`.

`IdentitiesOnly yes` is critical when you have multiple keys — without it, the agent offers all of them in sequence and the server hits `MaxAuthTries` before reaching the right one.

Test each:

```bash
ssh -T github.com                  # should auth as your personal account
ssh -T github-work                 # should auth as your work account
ssh your-vps
ssh private                        # via ProxyJump
```

**Acceptance:** `homework/03-ssh-config.txt` (your config, hostnames sanitized), `homework/03-notes.md` (one paragraph per `Host` stanza explaining the directives).

---

## Problem 4 — Refactor your nftables to use a set (60 min)

Take the ruleset from exercise 03 and refactor it so the allow-list of "permitted SSH source networks" is a **set**:

```nftables
table inet filter {
    set ssh_allow {
        type ipv4_addr
        flags interval
        elements = {
            203.0.113.0/24,
            198.51.100.5,
            192.0.2.0/28
        }
    }

    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iif lo accept

        # ICMP rules (as before)
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } accept

        # SSH from allowed sources only
        ip saddr @ssh_allow tcp dport 22 accept
        tcp dport 22 log prefix "SSH-BLOCKED-SOURCE: " drop

        tcp dport { 80, 443 } accept
        log prefix "INPUT-DROP: " level info limit rate 1/second
    }

    # forward and output (as before)
}
```

Add at least three CIDR entries. Apply. Verify with `nmap` from one of the allowed sources (should see 22 open) and ideally from a non-allowed source (should see 22 filtered, but you may not have a second machine outside your allow-list — explain in notes).

**Acceptance:** `homework/04-nftables-with-set.conf`, `homework/04-nft-list-ruleset.txt` (the output of `sudo nft list ruleset`), `homework/04-notes.md`.

---

## Problem 5 — Read your auth log (45 min)

Without `Fail2Ban`, the journal still records every SSH attempt. Read your server's auth events for the last 7 days (or since boot, if newer):

```bash
sudo journalctl -u sshd --since "7 days ago" -o cat | head -200
# Or, more focused:
sudo journalctl -u sshd --since "7 days ago" | grep "Failed password\|Invalid user\|Accepted publickey"
```

Build a `homework/05-auth-report.md` with:

- **Total successful logins:** count, plus the source IPs (probably just yours).
- **Total failed attempts:** count.
- **Most-frequent attacking source IPs:** top 10 with `awk` or `sort | uniq -c`.
- **Most-tried usernames:** top 10. (`root`, `admin`, `oracle`, `git`, `ubuntu`, `postgres` are common.)
- **Time distribution:** any pattern? (Brute-forcers are typically constant-rate; humans are diurnal.)

A useful pipeline:

```bash
sudo journalctl -u sshd --since "7 days ago" \
    | grep "Failed password\|Invalid user" \
    | grep -oE 'from [0-9.]+' \
    | sort | uniq -c | sort -rn | head -10
```

**Acceptance:** `homework/05-auth-report.md` with the four sections filled in. Include the actual numbers from your server, not synthetic ones.

---

## Problem 6 — Reflection (90 min)

`homework/06-reflection.md`, 600-800 words:

1. The lecture argued `ProxyJump` is strictly better than `ForwardAgent` for the bastion case. In your own words, explain why. Then think of a scenario where `ForwardAgent` is the *right* call (we mentioned one in the lecture; what is it?).
2. You hardened a server with `PasswordAuthentication no`. A brute-forcer hits port 22 with 10,000 attempts per hour for a week. How many of those attempts can possibly succeed? Walk through the reasoning. Now imagine you'd left `PasswordAuthentication yes` and used a 14-character random password; how many attempts before the attacker exhausts the space?
3. Compare `iptables`, `nftables`, `ufw`, and `firewalld` in your own words, in 6-8 sentences. When is each one the right choice? (We teach `nftables` because it's the substrate; that doesn't make the others wrong.)
4. The `nftables` `policy drop` is the secure default. Why is `policy accept` the **insecure** default, and why is it still what most documentation shows? (Hint: history of `iptables`.)
5. The `at` trick (auto-flush ruleset after 2 minutes) saved you in exercise 03. Describe the equivalent trick for `sshd_config` changes. (Hint: a one-line cron / `at` job that restores a known-good config if you don't cancel it.) Sketch the command.
6. Cite the Bash Yellow caution line at the top of your favorite lecture or exercise from this week. (Loyalty test repeats.)

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 1 h |
| 2 | 45 min |
| 3 | 45 min |
| 4 | 1 h |
| 5 | 45 min |
| 6 | 1.5 h |
| **Total** | **~6 h** |

After homework, ship the [mini-project](./mini-project/README.md).
