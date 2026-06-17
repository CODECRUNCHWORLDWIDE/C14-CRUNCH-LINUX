# Week 6 — Resources

Free, public, no signup unless noted. The OpenBSD man pages and the nftables wiki are the two references you will bookmark this week.

## Required reading

- **`ssh(1)`** — the client. The "OPTIONS" section is the full list of `-X`, `-A`, `-J`, `-L`, `-R`, `-D` flags. Read end to end once; come back to look up the `-o` overrides:
  <https://man.openbsd.org/ssh>
- **`ssh_config(5)`** — the client-side configuration file (`~/.ssh/config` and `/etc/ssh/ssh_config`). The "CONFIGURATION" section lists every directive: `Host`, `Match`, `HostName`, `Port`, `User`, `IdentityFile`, `ProxyJump`, `ForwardAgent`, `ControlMaster`, `ControlPath`, `ControlPersist`. Read the whole page — it is the textbook of this week's client side:
  <https://man.openbsd.org/ssh_config>
- **`sshd_config(5)`** — the server-side configuration file. The hardened-server checklist lives here. Every directive that decides whether somebody gets in: `PermitRootLogin`, `PasswordAuthentication`, `PubkeyAuthentication`, `AuthenticationMethods`, `AllowUsers`, `AllowGroups`, `Match`, `MaxAuthTries`, `LoginGraceTime`, `ClientAliveInterval`. The longest OpenSSH man page; read it once front-to-back:
  <https://man.openbsd.org/sshd_config>
- **`ssh-keygen(1)`** — key generation, fingerprinting, format conversion. The `-t`, `-b`, `-a` flags. The `-l` fingerprint flag. The `-Y` signature-and-verify subcommands (since OpenSSH 8.0). The `-R` known-hosts removal:
  <https://man.openbsd.org/ssh-keygen>
- **`ssh-agent(1)`** and **`ssh-add(1)`** — the key-caching daemon and the key-loader. How `SSH_AUTH_SOCK` is set, how `ssh-add -l` versus `ssh-add -L` differ, the `-t LIFETIME` flag for time-limited keys, the macOS Keychain integration:
  <https://man.openbsd.org/ssh-agent> · <https://man.openbsd.org/ssh-add>
- **`nft(8)`** — the nftables command-line tool. Tables, chains, rules, sets, maps, monitors. The "EXAMPLES" section at the bottom is high-value. Read end to end once:
  <https://www.netfilter.org/projects/nftables/manpage.html>
- **nftables wiki — "Simple ruleset for a server"** — the canonical "what does a hardened single-host ruleset look like" reference. Copy it; understand each line; then write your own:
  <https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_server>
- **nftables wiki — "Quick reference"** — the syntax cheat-sheet. Every meta selector, every payload expression, every statement. Keep open while you write your first ruleset:
  <https://wiki.nftables.org/wiki-nftables/index.php/Quick_reference-nftables_in_10_minutes>

## Books

- **"SSH, The Secure Shell: The Definitive Guide" — Daniel J. Barrett, Richard E. Silverman, Robert G. Byrnes (O'Reilly, 2nd ed., 2005)** — old, but the protocol hasn't changed in twenty years. The chapter on `sshd_config` directives is still the clearest exposition of why each one exists. A newer book on OpenSSH does not exist; this remains the canonical reference.
- **"Linux Firewalls" — Steve Suehring (4th ed., Addison-Wesley, 2015)** — Suehring is the iptables-era expert. Half the book is iptables; the last third covers nftables. Useful for the *why* of firewall design (default-deny, layered defenses, what counts as a chokepoint).
- **"Network Security Assessment" — Chris McNab (O'Reilly, 3rd ed., 2016)** — McNab is the `nmap`-and-reconnaissance reference. The chapters on TCP/IP fingerprinting and on the practical "scan a network you own to confirm it" workflow are exactly what we want for the verification side of Week 6.
- **"The TCP/IP Guide" — Charles M. Kozierok (No Starch Press, 2005)** — the encyclopedia. Free online: <http://www.tcpipguide.com/free/>. Use it when "what is the actual TCP state machine" needs an answer at 03:00.
- **"Silence on the Wire" — Michal Zalewski (No Starch, 2005)** — twenty years old, still chilling. Read for the "what can an attacker learn from the packets you can't avoid sending" perspective. Chapters 8 and 9 on TCP/IP fingerprinting are required for understanding what `nmap` shows.

## Cheat sheets

- **DigitalOcean — "How to Configure SSH Key-Based Authentication on a Linux Server"** — the canonical "I have a fresh VPS; how do I lock down SSH" walkthrough. Polished, careful, exactly the scope of exercise 01:
  <https://www.digitalocean.com/community/tutorials/how-to-configure-ssh-key-based-authentication-on-a-linux-server>
- **DigitalOcean — "How to Set Up SSH Tunneling on a VPS"** — local forwarding, remote forwarding, dynamic SOCKS proxies. We touch this in the lecture; the article goes deeper:
  <https://www.digitalocean.com/community/tutorials/how-to-use-ssh-to-connect-to-a-remote-server>
- **Arch Wiki — "OpenSSH"** — the densest English-language reference on OpenSSH usage and configuration. The "Server" and "Forcing public key authentication" sections are especially useful:
  <https://wiki.archlinux.org/title/OpenSSH>
- **Arch Wiki — "nftables"** — a focused page on nftables with example rulesets and the common gotchas (default-policy, IPv6 by default, service persistence):
  <https://wiki.archlinux.org/title/Nftables>
- **Mozilla — "OpenSSH Security Guidelines"** — Mozilla's published baseline. Aggressive on algorithm allow-lists; useful as a "what does paranoid look like" reference:
  <https://infosec.mozilla.org/guidelines/openssh.html>
- **`ssh-audit`** — a Python tool that audits an SSH server's algorithm selection against the Mozilla guidelines. `pip install ssh-audit`, then `ssh-audit your.host.com`. Free, open source:
  <https://github.com/jtesta/ssh-audit>
- **`nmap` cheat sheet — SANS** — the most-printed `nmap` reference card. Two pages, every common scan type:
  <https://www.sans.org/security-resources/sec560/netcat_cheat_sheet_v1.pdf> (search "SANS nmap cheat sheet" if the link drifts)

## Tools and websites

- **`ssh-keygen`** — the only tool for SSH keys. `-t ed25519` for new keys. `-l -f keyfile` for fingerprints. `-R hostname` to remove stale `known_hosts` entries. `-y -f privatekey` to extract the public key from a private key. Comes with OpenSSH; no install.
- **`ssh-copy-id`** — the canonical "install my public key on a remote host" command. `ssh-copy-id -i ~/.ssh/id_ed25519.pub user@host`. Works on Linux and macOS; on Windows use WSL. The fallback when it fails: `cat ~/.ssh/id_ed25519.pub | ssh user@host 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'`.
- **`ssh -G hostname`** — dumps the effective SSH config for the given host. Resolves `Host` and `Match` blocks. The single most useful debugging command when "I changed my `~/.ssh/config` and the wrong thing happens." Shows you what `ssh` will actually use.
- **`ssh -v` / `-vv` / `-vvv`** — increasing verbosity on the client. `-v` shows the auth attempts and key offers. `-vv` shows the protocol negotiation. `-vvv` shows the bytes. The right answer when "auth fails and I don't know why."
- **`sshd -t`** — config syntax check. **Run this before every `sshd` reload.** Catches typos before they cost you a session. `sshd -T` dumps the effective config (with all defaults resolved); use it to confirm a directive actually applied.
- **`nft`** — the nftables command. `nft list ruleset` shows everything. `nft -f file` loads a file. `nft add rule ...` adds one rule live. `nft flush ruleset` removes everything (do **not** do this over an SSH session unless you've prepared a re-add-from-file plan).
- **`nmap`** — the network mapper. `-sV` enumerate service versions. `-sS` SYN scan (root). `-p-` all 65535 TCP ports. `-Pn` skip the ICMP-ping check. `--reason` shows why each port is in its state. **Run from a different host than the one you're scanning.**
- **`ss` (`iproute2`)** — the modern replacement for `netstat`. `ss -tulpn` shows all TCP and UDP listening sockets with process names. `ss -tan state established` shows established TCP connections. `ss -s` shows summary.
- **`ip` (`iproute2`)** — the modern replacement for `ifconfig` and `route`. `ip addr` (or `ip a`) shows interfaces. `ip route` (or `ip r`) shows the routing table. `ip -s link` shows interface stats.
- **`tcpdump`** — packet capture. `tcpdump -i any port 22 -nn` shows live SSH packets without DNS lookups. Out of Week 6 scope; deferred to Week 7.
- **`Fail2Ban`** — log-watching intrusion-prevention. Reads `/var/log/auth.log`, detects failed-login bursts, bans the source IP at the firewall. Optional in Week 6; we cover the configuration but recommend the simpler "key-only auth on a non-default port" as the first line of defense.

## Videos (free)

- **"Hardening SSH" — Marcus Ranum, USENIX LISA 2017** — Ranum is the gray-beard's gray-beard of network security. 45 minutes; the no-nonsense walkthrough of every `sshd_config` knob worth tightening:
  <https://www.youtube.com/results?search_query=ranum+hardening+ssh+usenix>
- **"nftables: A New Linux Packet Filtering Framework" — Pablo Neira Ayuso, Netfilter Workshop** — Neira Ayuso is the lead nftables maintainer. The single most coherent explanation of the design — why nftables exists, what it replaces, what the named-sets-and-maps machinery is for:
  <https://www.youtube.com/results?search_query=nftables+neira+ayuso>
- **"Demystifying SSH" — Brian Hatch, ShmooCon 2009** — older, still excellent. The protocol layers and the auth dance, drawn on a whiteboard. Forty minutes:
  <https://www.youtube.com/results?search_query=demystifying+ssh+shmoocon>
- **"How nmap Works" — Gordon Lyon (Fyodor)** — Fyodor is the original `nmap` author. The talks at DEF CON / Black Hat each year cover what's new; the best for foundations is the older "Mastering the Network Mapper" series:
  <https://www.youtube.com/results?search_query=fyodor+nmap+defcon>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install openssh-server openssh-client nftables nmap iproute2 fail2ban
# Most distros have openssh-client and iproute2 installed.

# Fedora
sudo dnf install openssh-server openssh-clients nftables nmap iproute fail2ban
# Same set.

# Optional but recommended
pip install --user ssh-audit
# OR: pipx install ssh-audit
```

- `openssh-server` — needed on the **target** machine (the box you SSH into). On a VPS, often pre-installed.
- `openssh-client` — needed on your **laptop**. Almost certainly pre-installed.
- `nftables` — the kernel module has shipped since Linux 3.13 (2014); the userspace `nft` tool is the package you need. Pre-installed on most current distros.
- `nmap` — install on a **second** machine that will scan the target. Do not scan from the target itself; local nmap proves nothing about firewall efficacy.
- `iproute2` — provides `ip`, `ss`. Pre-installed on every modern distro.
- `fail2ban` — optional; we use it briefly in the homework. Not on the critical path.
- `ssh-audit` — Python tool for auditing SSH server crypto. Mozilla-baseline check.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| OpenSSH version | 9.6p1 | 9.8p1 |
| nftables version | 1.0.9 | 1.1.0 |
| `sshd_config` location | `/etc/ssh/sshd_config` (+ `/etc/ssh/sshd_config.d/*.conf`) | same |
| Default `sshd_config` permits root | `PermitRootLogin prohibit-password` | `PermitRootLogin prohibit-password` |
| Default `sshd_config` permits password auth | yes (until you change it) | yes (until you change it) |
| nftables persistence | `nftables.service`, file `/etc/nftables.conf` | `nftables.service`, file `/etc/sysconfig/nftables.conf` (note path) |
| Default firewall daemon | none (manual nftables or `ufw`) | `firewalld` (a wrapper over nftables) |
| `ufw` available | yes (preferred Ubuntu wrapper) | yes (not the default) |
| `firewalld` available | yes (not the default) | yes (the default) |
| `/var/log/auth.log` (SSH log) | yes | no — journald only; use `journalctl -u sshd` |
| `Fail2Ban` available | yes | yes |

The persistence-path divergence is the one that bites first. Ubuntu uses `/etc/nftables.conf`. Fedora uses `/etc/sysconfig/nftables.conf` (because Fedora's `nftables.service` `ExecStart=` points there). Both files are read by `nft -f`; you can put your ruleset in either as long as the systemd unit reads the same path. Confirm with `systemctl cat nftables.service`.

The "is there a firewall daemon by default" divergence matters more than it looks. On Fedora, `firewalld` is up at boot and owns the default ruleset; if you start writing `nft add rule` you may be writing into a ruleset that `firewalld` will overwrite on restart. Pick one approach (raw `nftables.service` *or* `firewalld`) and `systemctl mask` the other to avoid surprises.

The `/var/log/auth.log` versus journald divergence affects `Fail2Ban`. Fedora's `Fail2Ban` reads from systemd's journal (`backend = systemd`); Ubuntu's defaults to file (`backend = auto` chooses `pyinotify` on the auth log). The same `Fail2Ban` config on both distros may behave differently; the docs cover the override.

## Free books and write-ups

- **"OpenSSH Security and Hardening" — DigitalOcean tutorial series** — a careful, step-by-step series. Each tutorial is roughly the scope of one of our exercises; useful as a comparison reference:
  <https://www.digitalocean.com/community/tutorial-collections/securing-ssh-on-an-ubuntu-server>
- **"nftables HOWTO" — Eric Leblond** — Leblond is a long-time netfilter contributor. The HOWTO is older than the wiki but covers the design rationale better:
  <https://home.regit.org/netfilter-en/nftables-howto/> (search "Leblond nftables howto" if the link drifts)
- **NIST SP 800-53 — "AC-17 Remote Access"** — the US federal baseline for remote-admin security. Specifies the controls every public-facing SSH server should meet. Useful as a "what does the auditor want to see" reference even if you don't work in regulated environments:
  <https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final>
- **OWASP — "Secure SSH Configuration"** — short, opinionated, current. The community baseline for SSH hardening:
  <https://cheatsheetseries.owasp.org/cheatsheets/SSH_Cheat_Sheet.html>

## OpenSSH and nftables directives you will see this week

A quick reference. Every directive links to its man page; we will not duplicate the man pages here.

### `sshd_config` directives

| Directive | Default (9.6) | Hardened value | Meaning |
|-----------|---------------|----------------|---------|
| `Port` | `22` | `22` (keep default, rely on firewall) | TCP port `sshd` listens on. Non-22 reduces log noise; does not increase security. |
| `PermitRootLogin` | `prohibit-password` | `no` | Whether root may SSH in. Use `no`; create a sudo-able user. |
| `PasswordAuthentication` | `yes` | `no` | Whether passwords are accepted. The single most important line. |
| `PubkeyAuthentication` | `yes` | `yes` | Whether public-key auth is accepted. Required for `no` above to be usable. |
| `AuthenticationMethods` | `any` | `publickey` | Which methods, in what order. Use `publickey` for single-factor; `publickey,keyboard-interactive:pam` for 2FA. |
| `AllowUsers` | (unset) | `your-username` | Allow-list of users who may log in. Defense-in-depth. |
| `LoginGraceTime` | `2m` | `30` | Seconds to complete auth before disconnect. Tight reduces resource burn from auth-flood. |
| `MaxAuthTries` | `6` | `3` | Failed-auth attempts before disconnect. Tight reduces brute-force ROI. |
| `ClientAliveInterval` | `0` | `300` | Seconds between server-side keep-alive pings. Keeps NAT mappings alive. |
| `ClientAliveCountMax` | `3` | `3` | Missed keep-alives before disconnect. |
| `X11Forwarding` | `yes` (Ubuntu) / `no` (Fedora) | `no` | Whether to forward X11. Almost always wanted off. |
| `AllowTcpForwarding` | `yes` | `no` (server) / `yes` (bastion) | Whether to permit `-L` / `-R` tunnels. Bastions need it; leaves shouldn't. |
| `PermitTunnel` | `no` | `no` | Layer-3 tunneling. Almost never wanted. |
| `GatewayPorts` | `no` | `no` | Whether forwarded ports bind to `0.0.0.0` or `127.0.0.1` only. |

### `ssh_config` directives

| Directive | Meaning |
|-----------|---------|
| `Host` | Pattern (glob-aware) that the following stanza applies to. `Host *` is the catch-all. |
| `Match` | Programmable matcher: `Match user X`, `Match host Y`, `Match exec "test ..."`. |
| `HostName` | The real DNS name or IP (the `Host` line is the alias you type). |
| `Port` | The destination port. |
| `User` | The remote username. |
| `IdentityFile` | Which private key to use. May appear multiple times. |
| `IdentitiesOnly` | When `yes`, do not offer other keys from the agent. Critical when you have many keys. |
| `ProxyJump` | One or more hosts to tunnel through. `ProxyJump bastion` or `ProxyJump bastion1,bastion2`. |
| `ForwardAgent` | Forward `ssh-agent` to the remote. Convenient; risky on compromised intermediates. |
| `ServerAliveInterval` | Client-side keep-alive ping interval (seconds). |
| `ControlMaster` | `auto` enables connection multiplexing. |
| `ControlPath` | Socket path for the multiplexed connection. |
| `ControlPersist` | How long to keep the multiplex socket open after the last session closes. |

### nftables constructs

| Construct | Meaning |
|-----------|---------|
| `table inet filter` | A named container of chains. `inet` covers IPv4 and IPv6. `filter` is the conventional name for the packet-filter table. |
| `chain input` | A named container of rules, hooked into a specific point. `input` runs on locally-destined packets. |
| `hook input priority filter; policy drop;` | The chain's hook point, evaluation priority, and default policy if no rule matches. |
| `ct state established,related accept` | The "let return traffic through" rule. Almost always rule one. |
| `iif lo accept` | Accept loopback. Almost always rule two. |
| `tcp dport 22 accept` | Accept new TCP connections to port 22. |
| `tcp dport 22 limit rate 4/minute accept` | Same, with a rate limit. |
| `ip saddr 203.0.113.0/24 tcp dport 22 accept` | Same, restricted to a source network. |
| `meta nftrace set 1` | Mark matching packets for tracing (`nft monitor trace`). Debugging only. |

These are the directives and constructs you will encounter most. The man pages have the rest.

## Glossary

| Term | Definition |
|------|------------|
| **SSH** | Secure Shell, IETF RFCs 4250-4254. A protocol for encrypted remote login and tunneling. OpenSSH is the dominant implementation. |
| **`sshd`** | The SSH daemon — server side. Listens on TCP 22 by default. |
| **Key pair** | A public/private pair generated by `ssh-keygen`. The public part goes on remote hosts in `authorized_keys`; the private part stays on your laptop. |
| **`ssh-agent`** | A daemon that holds unlocked private keys in memory so you don't retype the passphrase. |
| **`ProxyJump`** | An OpenSSH 7.3+ directive that tunnels SSH through one or more intermediate hosts. `ssh -J bastion target`. |
| **Bastion** | A host whose only purpose is to be the SSH entry point to a private network. Hardened; everything else hides behind it. |
| **Agent forwarding** | The mechanism by which your `ssh-agent` is exposed to a remote host so SSH-from-the-remote can authenticate. Convenient and risky. |
| **`known_hosts`** | The file (`~/.ssh/known_hosts`) where your client records the public host key of every host you've connected to. First-connection `yes` writes here. |
| **`authorized_keys`** | The file (`~/.ssh/authorized_keys`) on the remote host listing the public keys allowed to log in as that user. |
| **`nftables`** | The Linux packet filter framework, current since 2014. Replaces `iptables` (which is now a translation layer). |
| **Table / chain / rule** | The three levels of nftables organization. Tables contain chains; chains contain rules. |
| **Hook** | The point in the network stack where a chain is evaluated. `input` (locally-destined), `output` (locally-originated), `forward` (routed through). |
| **Policy** | The default action when no rule matches. `drop` is the secure default; `accept` is the permissive default. |
| **`ct state`** | Connection-tracking state. `new`, `established`, `related`, `invalid`. The `established,related accept` rule is the bedrock of stateful firewalling. |
| **nmap** | The network mapper. Probes hosts and ports. Free, open-source, the standard reconnaissance tool. |
| **Three-way handshake** | The TCP connection setup: SYN → SYN-ACK → ACK. nmap's `-sS` "SYN scan" sends SYN, watches for SYN-ACK, never completes the third leg — fast, leaves no socket. |
| **`Fail2Ban`** | A Python daemon that watches log files for failed-login bursts and bans the source IP at the firewall. Optional belt to the suspenders of key-only auth. |

---

*Broken link? Open an issue.*
