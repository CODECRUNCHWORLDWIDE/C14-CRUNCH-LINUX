# Week 6 — SSH, Networking, Firewalls

> *Last week you wrote a service. This week you put it on the internet. The internet is hostile: SSH brute-forcers will find your machine within seven minutes of it answering on port 22, and the only thing standing between your service and a botnet is your `sshd_config`, your firewall, and the fact that you typed `PermitRootLogin no` before the first packet arrived. We learn the four primitives — key auth, agent forwarding, ProxyJump, and nftables — and we earn them by hardening a fresh $5/mo VPS and then scanning it from the outside with `nmap` to prove the locks took.*

Welcome to **Week 6 of C14 · Crunch Linux**. Five weeks of foundation: shell, pipes, permissions, scripts, services. This week the foundation meets the network. The systemd service you wrote in Week 5 stays on the same box; what changes is that the box has a public IP, a registry entry in the global DNS, and a passing population of unwanted visitors. Your job is to keep them out.

If Week 5 was the `[Unit]` / `[Service]` / `[Install]` trio, Week 6 is the **`~/.ssh/config`** entry, the **`AuthorizedKeysFile`** path, the **`nft add rule`** invocation, and the `nmap -sV your.vps.ip` output that proves only ports 22, 80, and 443 are reachable. Three habits with two heavy tools. We earn them by generating keys, configuring the daemon, writing nftables rulesets, locking ourselves out on purpose (and recovering via the provider's web console), and finally hardening a real VPS that we run for the rest of the course.

## Learning objectives

By the end of this week, you will be able to:

- **Generate, distribute, and use SSH keys** — pick the right algorithm (`ed25519` over `rsa-3072` in 2026), encrypt the private key with a passphrase, and load it into `ssh-agent` so you type the passphrase once per session. Know what `ssh-copy-id` actually does and why it sometimes fails.
- **Configure `sshd_config`** for a hardened server: `PermitRootLogin no`, `PasswordAuthentication no`, `PubkeyAuthentication yes`, `AuthenticationMethods publickey`, `AllowUsers <you>`, `LoginGraceTime 30`, `MaxAuthTries 3`, `ClientAliveInterval 300`. Know what each line prevents and the order to apply them in (the `Match` block dance).
- **Write a `~/.ssh/config` file** with `Host`, `HostName`, `User`, `Port`, `IdentityFile`, `ProxyJump`, `ForwardAgent`, `ServerAliveInterval`, `ControlMaster`, `ControlPath`, `ControlPersist`. Have one stanza per host you talk to. Stop typing `ssh user@longhostname.example.com -p 2222 -i ~/.ssh/specific-key`.
- **Use `ProxyJump`** to reach a private host through a bastion in one command (`ssh -J bastion private`). Explain why `ProxyJump` is strictly better than the old `ProxyCommand ssh -W %h:%p bastion` pattern and what changed in OpenSSH 7.3 to make it so.
- **Reason about agent forwarding** — when to use `-A` / `ForwardAgent yes`, when to use `ProxyJump` instead, and why a compromised intermediate host with your agent forwarded is the same blast radius as a compromised intermediate host with your private key copied locally.
- **Write nftables rules** for a hardened single-host firewall: default-drop on `inet filter input`, accept `lo`, accept established/related, accept TCP 22/80/443 with optional rate-limit and source restriction. Persist with `nftables.service` and `/etc/nftables.conf`. Know the difference between `nft list ruleset` and `iptables -L` (one is the future; the other is a translation layer).
- **Verify with `nmap`** from a remote host — the only honest test that your firewall does what you think it does. `nmap -sV`, `nmap -sS`, `nmap -p-`. Read the output. Know what `filtered` vs `closed` vs `open` means at the TCP layer.
- **Recognize** the SSH and firewall mistakes that cause the most outages: editing `sshd_config` without keeping the old session open, `iptables -F` without resetting the default policy, `nft flush ruleset` over an SSH connection that the ruleset is keeping alive, the firewall that blocks loopback, the `Match` block that matches nothing.

## Prerequisites

- **Weeks 1-5 of C14** completed. You can navigate the filesystem, write a shell script that fails correctly, manage permissions, and write a systemd unit that survives `daemon-reload`.
- A working Ubuntu 24.04 LTS or Fedora 41 environment **plus** a second machine you can reach over the network. The second machine can be a VM on your laptop, a Raspberry Pi on your home network, a friend's box, or — recommended — **a $5/mo VPS** from Hetzner, Vultr, DigitalOcean, Linode, or Scaleway. The pedagogical value of "this machine is on the internet, right now, and the brute-forcers are already trying" is unmatched.
- OpenSSH 9.x on both ends. Ubuntu 24.04 ships OpenSSH 9.6; Fedora 41 ships 9.8. Older OpenSSH lacks some `Match` features and a few `sshd_config` defaults are different — the differences matter and we note them.
- nftables 1.0 or newer. `nft --version`. Ubuntu 24.04 ships 1.0.9; Fedora 41 ships 1.1.0. Earlier versions are missing the `meta nftrace` features and the `vmap` shortcuts.
- Root access via `sudo` on the target machine. **Snapshot first.** Several exercises produce firewall rules or `sshd_config` changes that, if applied wrong, lock you out. Always have a recovery path: the VPS provider's web console, a local hypervisor console, or a second SSH session held open while you experiment.

## Topics covered

- **SSH protocol primer:** the three layers (transport, user-auth, connection), the key exchange (Curve25519 by default since OpenSSH 8.5), the host key (and why the first `yes` on a new host is a hostage to fortune), and the difference between `~/.ssh/known_hosts` and `/etc/ssh/ssh_known_hosts`.
- **Key types and rotation:** `ssh-keygen -t ed25519` is the right answer in 2026. `rsa-3072` is acceptable if you must interop with old systems. `ecdsa` is technically fine but politically awkward (NIST curves). `dsa` is dead — sshd 7.0 removed support. Key rotation strategy: one key per laptop, not one key per service.
- **`ssh-agent` and key management:** how the agent works (Unix socket, `SSH_AUTH_SOCK` env var, `ssh-add`), why `IdentityFile` plus an unlocked agent is the right pattern, and what `ssh-add -L` shows versus `ssh-add -l`. The macOS Keychain integration (`UseKeychain yes`, `AddKeysToAgent yes`).
- **`~/.ssh/config`:** the canonical client-side configuration file. `Host` (glob-aware), `Match` (programmable), the per-host stanzas, `Include` for modular configs, the `ProxyJump` directive, the multiplexing trio (`ControlMaster`, `ControlPath`, `ControlPersist`).
- **`sshd_config`:** the server-side configuration file. The hardened-server checklist (~14 directives). `AuthenticationMethods` for layered auth. `Match` blocks for per-user, per-group, or per-network overrides. The reload-not-restart distinction. The `sshd -t` syntax check that should be the last thing you run before reload.
- **ProxyJump and bastion patterns:** one bastion, many private hosts. The bastion sees the inbound SSH; the private hosts see only the bastion. The bastion gets the hardening; the private hosts get to be simple. Why this is operationally and security-wise better than "open SSH on every host."
- **Agent forwarding (and its risks):** `ForwardAgent yes` lets the remote host use your local keys to authenticate further hops. Convenient. Also: any user with root on that remote host can use your forwarded agent for as long as you are connected. `ProxyJump` avoids forwarding entirely.
- **Networking primer:** what an IP address, port, route, and default gateway are. The four-tuple `(src IP, src port, dst IP, dst port)` that uniquely identifies a TCP connection. `ip addr`, `ip route`, `ss -tulpn`, `ss -s`. Why `netstat` is deprecated (`iproute2` replaced it; `ss` is the modern tool).
- **TCP states:** `LISTEN`, `ESTABLISHED`, `TIME_WAIT`, `CLOSE_WAIT`, the three-way handshake. Why `ss -tan` is the right command when "is anything listening on this port" comes up.
- **Firewalls in 2026:** four options. `iptables` (legacy, still present, mostly a translation layer to `nf_tables` since Linux 5.0). `nftables` (current Linux default since 2014, what we teach). `ufw` (Ubuntu's friendly wrapper around iptables/nftables; teaches no concepts but ships secure by default). `firewalld` (Red Hat's daemon-based firewall; rich rules, zones, more abstraction). **We teach `nftables` because it is what `ufw` and `firewalld` both lower to**, and the abstractions leak.
- **nftables anatomy:** tables, chains, rules, sets, maps, verdicts. The `inet` family that covers IPv4 and IPv6 in one ruleset. The hook points (`input`, `output`, `forward`, `prerouting`, `postrouting`) and the priorities. Default policies. The single-file persistence pattern (`/etc/nftables.conf` plus `nftables.service`).
- **Rule-writing patterns:** the canonical "default drop, accept what you mean" template. `ct state established,related` as the first rule. `iif lo` accept. The "knock-knock" of `tcp dport 22 accept`. Rate-limiting (`tcp dport 22 limit rate 4/minute accept`). Source restriction (`ip saddr 203.0.113.0/24 tcp dport 22 accept`).
- **Verification with `nmap`:** the trust-but-verify check. `nmap -sV -p- target` enumerates open ports and their service versions. `nmap -sS` is the SYN scan (root, fastest). `nmap --reason` shows why each port is in its state. Run `nmap` from **outside** the firewall, not the same host — a local nmap proves nothing.
- **`Fail2Ban` and `sshguard`:** intrusion-detection-light for SSH. `Fail2Ban` reads `/var/log/auth.log`, parses failed-login lines, bans the source IP at the firewall for a configurable window. Useful but not essential — a properly configured `PubkeyOnly` SSH with a non-default port already eliminates 99% of the noise.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                              | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | SSH keys, `ssh-agent`, `~/.ssh/config`. Lecture 1. |    3h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Tuesday   | ProxyJump, bastion patterns. Exercises 1 and 2.    |    1h    |    3h     |     0.5h   |    0.5h   |   1h     |     0h       |    0.5h    |     6.5h    |
| Wednesday | Networking primer, nftables anatomy. Lecture 2.    |    2h    |    2h     |     0.5h   |    0.5h   |   1h     |     0h       |    0h      |     6h      |
| Thursday  | Exercise 3 (nftables rules); design mini-proj.     |    0h    |    2h     |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Harden-a-VPS challenge; polish homework.           |    0h    |    0.5h   |     1.5h   |    0.5h   |   2h     |     1h       |    0h      |     5.5h    |
| Saturday  | Mini-project — provision VPS, harden, verify.      |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                                  |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                                    | **6h**   | **9.5h**  | **3.5h**   | **3h**    | **6h**   | **7h**       | **1h**     | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | OpenSSH man pages, nftables documentation, books, references |
| [lecture-notes/01-ssh-keys-agent-config-proxyjump.md](./lecture-notes/01-ssh-keys-agent-config-proxyjump.md) | Key generation, `ssh-agent`, `~/.ssh/config`, `sshd_config` hardening, ProxyJump |
| [lecture-notes/02-nftables-and-firewall-basics.md](./lecture-notes/02-nftables-and-firewall-basics.md) | TCP/IP refresher, nftables tables/chains/rules, the hardened-host template, `nmap` verification |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-key-auth-and-config.md](./exercises/exercise-01-key-auth-and-config.md) | Generate a key, distribute it, write a `~/.ssh/config` stanza, disable password auth |
| [exercises/exercise-02-proxyjump-bastion.md](./exercises/exercise-02-proxyjump-bastion.md) | Reach a private host through a bastion with one command |
| [exercises/exercise-03-nftables-rules.md](./exercises/exercise-03-nftables-rules.md) | Write an `nftables` ruleset for a hardened SSH+HTTP host, persist it, verify with `nmap` |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-harden-a-fresh-vps.md](./challenges/challenge-01-harden-a-fresh-vps.md) | End-to-end: provision a $5/mo VPS, harden it from "fresh image" to "production-shaped" in one sitting |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | Provision a $5/mo VPS, harden SSH, configure firewall, verify with nmap |

## A note on which OpenSSH and which nftables

OpenSSH is a slow-moving target by software-industry standards but every release matters for security. Between OpenSSH 7.0 (which removed DSA support) and 9.6 (which added `KexAlgorithms` improvements and removed `ssh-rsa` from the default `HostKeyAlgorithms` on the server side), roughly thirty defaults changed. This week's content is written against **OpenSSH 9.6 or newer** and notes which directives are new since 8.0 or 9.0.

```bash
# Which OpenSSH client?
ssh -V
# Ubuntu 24.04 LTS: OpenSSH_9.6p1 Ubuntu-3ubuntu13.5
# Fedora 41:        OpenSSH_9.8p1, OpenSSL 3.2.2

# Which OpenSSH server?
sshd -V 2>&1 | head -1
# Same versions.

# Which nftables?
nft --version
# Ubuntu 24.04: nftables v1.0.9 (Old Doc Yak #3)
# Fedora 41:    nftables v1.1.0 (Commodore Bullmoose)
```

If you're on macOS, the macOS-shipped OpenSSH is usually a release or two behind. Install `openssh` from Homebrew (`brew install openssh`) and put `/opt/homebrew/bin` ahead of `/usr/bin` in your `PATH` if you want the latest client. The server-side hardening of this week applies to your Linux VM or VPS — macOS does not run `sshd` for incoming connections (it ships disabled and we keep it that way).

If you're on Windows, use WSL2 with Ubuntu 24.04, or `ssh.exe` from the OpenSSH Windows port (installed by default since Windows 10 1809). Both work; we test against WSL2.

nftables is a Linux-only construct. Your **client** machine can be anything; your **server** must be Linux. If you're firewalling a macOS host you'd reach for `pf`, which is a different tool with a different syntax — outside Week 6's scope.

## Stretch goals

- Read the **OpenSSH manual pages** end to end — at minimum `ssh(1)`, `ssh_config(5)`, `sshd_config(5)`, `ssh-keygen(1)`, `ssh-agent(1)`, `ssh-add(1)`. The `sshd_config(5)` page is the textbook of server hardening: <https://man.openbsd.org/sshd_config>
- Read the **nftables wiki** front to back, especially the "Quick reference" and "Simple ruleset for a server" pages: <https://wiki.nftables.org/>
- Read **Michal Zalewski's "Silence on the Wire"** chapter 9 (on the network-stack fingerprinting that `nmap` exploits). Dense, beautiful, terrifying.
- Read the **OpenSSH `INSTALL` file and `release-notes`** for the last three releases. Each release ships behavioral changes; admins who skip the notes get surprised at the wrong moment.
- Run `nmap -sV --script ssh2-enum-algos -p 22 target` against a public-facing SSH endpoint and read the script output. Compare to the same endpoint after you tighten `KexAlgorithms` and `Ciphers` in `sshd_config`.

## Bash Yellow caution

This week contains commands that can:

- **Lock you out of a server.** `PasswordAuthentication no` plus a missing or mistyped `authorized_keys` entry is the canonical mistake. The fix requires the provider's web console or a hypervisor console — keep one handy before you reload `sshd`.
- **Lock you out of a server, version two.** `nft flush ruleset` over an SSH connection that the ruleset is permitting drops your TCP session mid-command. Either use `iif lo accept; ct state established,related accept` *before* any drop rule, or run via `at` / `screen` / a 30-second `sleep`-and-reset trick.
- **Brick your boot indirectly.** `nftables.service` with a syntax error in `/etc/nftables.conf` will refuse to start; on a stricter setup (no `ssh.service` ordering) this can mean a machine that boots without a firewall and without you noticing.
- **Expose a service you thought was firewalled.** A rule misorder (`accept` after `drop`) does nothing — nftables evaluates top-to-bottom and the first match wins. Always end with `nmap -sV` against the public IP to verify the lock took.
- **Leak your private key.** `chmod 644 ~/.ssh/id_ed25519` is silent (the file works), but `ssh` refuses to use a private key with permissions wider than `0600`. The fix is `chmod 600`; the lesson is to chmod the directory `0700` too.

Every lecture and exercise that runs destructive code uses a scratch host where possible, holds an open SSH session as the rollback path, and shows a Bash Yellow warning before the irreversible line. The line is: **wrong port, wrong key, wrong rule, wrong order** — every footgun this week reduces to one of those four.

## Up next

[Week 7 — Observability and "why is it slow?"](../week-07/) — when the service you've sandboxed, served, and firewalled starts behaving oddly, and you need to find out which of the four pillars (CPU, memory, disk, network) is suffering. Network observability is the bridge: `ss`, `tcpdump`, and the journal that systemd kept while everything went sideways.

---

*If you find errors, please open an issue or PR.*
