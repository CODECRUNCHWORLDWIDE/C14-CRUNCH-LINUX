# Lecture 2 — nftables and Firewall Basics

> **Duration:** ~3 hours. **Outcome:** You read and write `nftables` rulesets. You understand the table/chain/rule hierarchy, the four hook points, the `ct state` machine, and the difference between `accept`, `drop`, and `reject`. You can write a hardened single-host firewall (SSH + HTTP + HTTPS only), persist it with `nftables.service`, and verify with `nmap` from a remote host. You read `nft list ruleset` fluently.

A firewall is a packet-classifier with a small vocabulary. It says, for each packet that crosses the network stack: **accept, drop, reject, or jump-to-another-chain-and-decide-there**. The Linux kernel has done this since 2.0 (1996, `ipfwadm`); the *userspace* tool has changed three times: `ipchains` (1999), `iptables` (2001), and `nftables` (2014, default since 2018 or so). This lecture is `nftables`.

We teach `nftables` because:

- It is what the kernel actually understands; `iptables` on a current distro is a *translation layer* (`iptables-nft`) that turns iptables syntax into nftables internals.
- `ufw` (Ubuntu's friendly wrapper) and `firewalld` (Red Hat's daemon) both **lower to** nftables. Knowing the substrate makes the abstractions debuggable.
- The syntax is one tool, one tool's grammar — not the iptables / ip6tables / arptables / ebtables / ipset hairball.

Read at the keyboard, on a Linux box where you have `sudo` and a way to roll back if the firewall locks you out (a held-open SSH session, the provider's web console, or a hypervisor console). `nft --version` should report **1.0 or newer**.

## 1. The network stack, in one paragraph

Linux exposes the network as the **socket** API. Applications `socket(AF_INET, SOCK_STREAM, 0)`, `bind()` to an address-and-port, `listen()`, `accept()`. The kernel receives packets at the network interface, runs them through the **netfilter** framework (the in-kernel hook system), and either delivers them to the right socket, forwards them, or drops them. `nftables` is the modern userspace for configuring those netfilter hooks.

Three things you need to be fluent with:

- **IP address** — `203.0.113.42` (IPv4) or `2001:db8::42` (IPv6). The host's identifier on a network.
- **Port** — `0-65535`, decided by the application. TCP and UDP each have their own port-space; `tcp/22` and `udp/22` are different sockets.
- **Connection** — a 4-tuple `(src IP, src port, dst IP, dst port)`. For TCP, this plus the protocol uniquely identifies the connection in the kernel's tracking table.

Listening sockets ("things that will accept new connections"):

```bash
ss -tulpn
# Netid State  Recv-Q Send-Q Local Address:Port  Peer Address:Port  Process
# tcp   LISTEN 0      128       0.0.0.0:22         0.0.0.0:*         users:(("sshd",pid=854,fd=3))
# tcp   LISTEN 0      511       127.0.0.1:80       0.0.0.0:*         users:(("nginx",pid=912,fd=6))
# tcp   LISTEN 0      128             [::]:22            [::]:*      users:(("sshd",pid=854,fd=4))
# udp   UNCONN 0      0      0.0.0.0:68         0.0.0.0:*         users:(("systemd-networkd",pid=802,fd=18))
```

Flags: `-t` TCP, `-u` UDP, `-l` listening, `-p` show process, `-n` numeric (no DNS).

The `Local Address:Port` column tells you what's exposed:

- `0.0.0.0:22` — listening on every IPv4 interface (the public IP, loopback, anything).
- `127.0.0.1:80` — listening only on loopback. Not reachable from outside the box.
- `[::]:22` — listening on every IPv6 interface.

A firewall does **not** make a listening socket private. The socket still binds; the kernel still accepts the packet at the interface; the firewall is what drops it before the socket sees it. (For "actually private" you bind to `127.0.0.1`. For "public but filtered" you bind to `0.0.0.0` and rely on the firewall.)

## 2. The TCP three-way handshake (the part `nmap` exploits)

Every TCP connection starts with:

1. Client sends **SYN** to `server:port`.
2. Server sends **SYN-ACK** back.
3. Client sends **ACK**.

Now the connection is `ESTABLISHED` on both sides. Data flows.

What `nmap -sS` (the "SYN scan") does:

1. Send SYN.
2. If SYN-ACK comes back, the port is **open**.
3. If RST comes back, the port is **closed** (something replied; nothing listening).
4. If nothing comes back, the port is **filtered** (a firewall ate the packet).
5. Never send the ACK. The half-open socket is dropped by the kernel after a timeout.

The distinction between **closed** (something said no) and **filtered** (silence) is what tells `nmap` whether there's a firewall and where it lives.

Your hardened host should answer:

- TCP 22: **open** (SSH).
- TCP 80, 443: **open** (HTTP, HTTPS).
- Everything else: **filtered** (silent). Not "closed."

If `nmap` reports `closed` for ports you didn't open, your firewall is dropping correctly but the host is replying with RST to the SYN — which means the firewall is `reject`-ing (RFC 1812 style) instead of `drop`-ing. Either is fine; `drop` is slightly less informative to the scanner, `reject` is slightly more polite.

## 3. `nftables` — the mental model

Three levels of organization:

- **Table** — a named container. `table inet filter { ... }`. The first word after `table` is the *family*: `inet` (both IPv4 and IPv6), `ip` (IPv4 only), `ip6` (IPv6 only), `arp`, `bridge`, `netdev`. The second word is the name (you pick; `filter` is convention).
- **Chain** — a named container of rules, inside a table. A chain is either a **base chain** (hooked into the network stack) or a **regular chain** (jumped-to from another chain).
- **Rule** — a single line: a match expression and a verdict.

A base chain has four things in its header:

```
chain input {
    type filter hook input priority filter; policy drop;
    # ... rules ...
}
```

- **`type filter`** — what kind of chain. `filter` (packet filtering, the common case), `nat` (NAT), `route` (advanced routing decisions).
- **`hook input`** — where in the network stack this chain runs. `input` (packets destined for this host), `output` (packets originating here), `forward` (packets being routed through), `prerouting`, `postrouting` (NAT and mangling).
- **`priority filter`** — the order if there are multiple chains on the same hook. `filter` is the standard priority (numerically 0); lower priorities run first.
- **`policy drop`** — what happens when **no rule matches**. `drop` (silently discard), `accept` (let it through). Default is `accept`; we override to `drop`.

A regular chain has no header:

```
chain ssh_in {
    # ... rules that other chains "jump" or "goto" to ...
}
```

### 3.1 Rule anatomy

A rule is `MATCH ... VERDICT`. Examples:

```
tcp dport 22 accept                              # match: TCP destination port 22; verdict: accept
ip saddr 203.0.113.0/24 accept                   # match: IPv4 source in that subnet; verdict: accept
ct state established,related accept              # match: an existing or related conntrack entry; accept
iif lo accept                                    # match: input interface is loopback; accept
tcp flags & (syn|ack|fin|rst) == syn drop        # match: TCP SYN with no ACK/FIN/RST; drop (initial-SYN-only)
log prefix "BLOCKED: " drop                      # log the packet, then drop it
```

The match part can chain multiple conditions (implicit AND):

```
ip saddr 203.0.113.0/24 tcp dport 22 ct state new accept
# = match if all of: source in 203.0.113.0/24, TCP dport 22, conntrack state new
```

The verdict part is one of:

- **`accept`** — let the packet through. Stop evaluating this chain.
- **`drop`** — silently discard. Stop evaluating.
- **`reject`** — discard and send ICMP unreachable (or TCP RST). The polite drop.
- **`continue`** — proceed to the next rule. (Implicit when no verdict; rules without a verdict are *counters* — they accumulate statistics but don't decide.)
- **`jump CHAIN`** — go to another chain; come back to the next rule here if `CHAIN` returns.
- **`goto CHAIN`** — go to another chain; do **not** come back.
- **`return`** — pop back to the chain that `jump`ed here.

First match wins. Within a chain, rules are evaluated top to bottom; the first one whose match part is true fires its verdict and the chain is done.

## 4. The canonical hardened-host ruleset

Save this as `/etc/nftables.conf` (Ubuntu) or `/etc/sysconfig/nftables.conf` (Fedora). Confirm the path with `systemctl cat nftables.service`.

```nftables
#!/usr/sbin/nft -f

# Always start from scratch; load is idempotent.
flush ruleset

table inet filter {

    # ---- INPUT: packets destined for this host ----
    chain input {
        type filter hook input priority filter; policy drop;

        # 1. Let existing connections continue.
        ct state established,related accept

        # 2. Drop invalid conntrack states (malformed, late RST, etc).
        ct state invalid drop

        # 3. Loopback is always trusted.
        iif lo accept

        # 4. ICMPv4 echo + a couple of essentials (let people ping you).
        ip protocol icmp icmp type { echo-request, destination-unreachable, time-exceeded, parameter-problem } accept limit rate 4/second

        # 5. ICMPv6 essentials (ND, RA, NS, NA — your IPv6 stops working without these).
        ip6 nexthdr icmpv6 icmpv6 type { destination-unreachable, packet-too-big, time-exceeded, parameter-problem, echo-request, nd-router-advert, nd-neighbor-solicit, nd-neighbor-advert } accept

        # 6. SSH — rate-limited to slow brute-force.
        tcp dport 22 ct state new limit rate 4/minute accept
        tcp dport 22 ct state new log prefix "SSH-RATELIMIT-DROP: " drop

        # 7. HTTP + HTTPS — open.
        tcp dport { 80, 443 } accept

        # 8. Anything else is dropped by the chain policy. We can log it explicitly:
        log prefix "INPUT-DROP: " level info limit rate 1/second
        # The chain policy will drop after this rule's "no-verdict" log fires.
    }

    # ---- FORWARD: packets being routed through this host ----
    chain forward {
        type filter hook forward priority filter; policy drop;
        # This host is not a router. Drop everything.
    }

    # ---- OUTPUT: packets originating on this host ----
    chain output {
        type filter hook output priority filter; policy accept;
        # We trust outbound traffic from this host. Accept all.
        # If you want egress filtering, replace with rules + policy drop.
    }
}
```

Read this ruleset top to bottom. Every line earns its keep:

- **`flush ruleset`** at the top means "load is idempotent" — re-running `nft -f` replaces the ruleset wholesale. Without this, the file is **additive**, and you accumulate duplicate rules every reload.
- **`table inet filter`** uses the `inet` family, so the same chain catches both IPv4 and IPv6.
- **`policy drop`** on `input` means: if nothing accepts the packet, it's dropped. The other rules are **allow-list** entries.
- **`ct state established,related accept`** is rule one because every other rule depends on it. Without it, the SYN-ACK reply to your own outbound connection would be dropped on the way back.
- **`iif lo accept`** comes before everything else. Loopback is `127.0.0.1`/`::1`; many local services (databases, IPC) talk over it; never block it.
- **The SSH block (rule 6)** uses `limit rate 4/minute` to throttle new connections. The second line logs anything that's over the limit. This is a poor man's `Fail2Ban` and is usually enough.
- **`log prefix "..."`** before the implicit policy-drop lets you see what got dropped in the journal (`journalctl -k | grep INPUT-DROP`). The `limit rate 1/second` prevents log spam.

Load it:

```bash
sudo nft -f /etc/nftables.conf
```

Inspect:

```bash
sudo nft list ruleset
```

The output is identical to your file (with default values filled in where you omitted them). Use `nft list ruleset -a` to also print rule handles (numeric IDs you need to delete a single rule).

## 5. Live editing vs file-based editing

There are two ways to run nftables:

1. **File-based.** Edit `/etc/nftables.conf`, then `sudo nft -f /etc/nftables.conf`. The file is canonical; the running ruleset is a copy.
2. **Live.** Use `nft add rule ...`, `nft delete rule ...`. The running ruleset is canonical; the file is, if anything, a snapshot.

For production, **always** file-based. Live editing loses changes on reboot and makes the system's behavior depend on the operator's memory.

For debugging a tricky rule, live editing is faster. The workflow:

```bash
# Add a rule live (the rule appears at the bottom of the chain unless you use 'add ... position N'):
sudo nft add rule inet filter input ip saddr 198.51.100.5 tcp dport 22 accept

# Find the rule's handle:
sudo nft list ruleset -a | grep 198.51.100.5
# (... handle 17 ...)

# Delete by handle:
sudo nft delete rule inet filter input handle 17

# Or insert at the top (before all other rules):
sudo nft insert rule inet filter input ip saddr 198.51.100.5 tcp dport 22 accept

# Once you have it right, copy the rule text into /etc/nftables.conf and reload.
```

`nft monitor trace` plus a `meta nftrace set 1` rule in your chain lets you watch packets traverse the rules. Powerful; outside Lecture 2 scope but in exercise 3.

## 6. Persistence — `nftables.service`

The system ships a `nftables.service` unit that runs `nft -f /etc/nftables.conf` (or the Fedora equivalent path) at boot. Confirm and enable:

```bash
sudo systemctl cat nftables.service
# [Service]
# Type=oneshot
# RemainAfterExit=yes
# ExecStart=/usr/sbin/nft -f /etc/nftables.conf
# ExecReload=/usr/sbin/nft -f /etc/nftables.conf
# ExecStop=/usr/sbin/nft flush ruleset
# ...

sudo systemctl enable nftables.service       # boot-time persistence
sudo systemctl reload nftables.service        # re-read the conf file (after editing)
```

**Do not** `restart` the service over SSH unless you've held a second session. `ExecStop=/usr/sbin/nft flush ruleset` empties the table, which (with no rules) defaults the chain policy back to `accept` — but for the microsecond between flush and reload, a fast scanner could see an open port. `reload` is in-place and safe.

### 6.1 Test before deploy

Always test a new config without making it persistent:

```bash
# Validate syntax without applying:
sudo nft -c -f /etc/nftables.conf
# -c = "check, do not commit". Prints errors if any.

# Apply with a 60-second auto-rollback (the classic trick):
sudo nft -f /etc/nftables.conf
# In another terminal, immediately:
sudo at "now + 1 minute" <<< "/usr/sbin/nft flush ruleset"
# If your new ruleset works, cancel the `at` job within 60 seconds:
# sudo atrm <job_id>
# If it broke your SSH, the `at` will fire and reset.
```

The `at` trick is the firewall analog of "hold a second SSH session open." It is not pretty, but it has saved many an admin from a self-inflicted lockout.

## 7. Sets and maps — when one rule isn't enough

A **set** is a named collection of values you can match against:

```nftables
table inet filter {
    set ssh_allow {
        type ipv4_addr;
        elements = { 203.0.113.0/24, 198.51.100.5, 192.0.2.7 }
    }

    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iif lo accept
        ip saddr @ssh_allow tcp dport 22 accept
        tcp dport { 80, 443 } accept
    }
}
```

`@ssh_allow` references the set. Adding a new allowed source IP is one line of edit, not a new rule. Sets can also be **dynamic** — populated at runtime by other rules (the pattern behind a homegrown port-knocking or rate-limit-then-ban system).

A **map** associates a key with a value-or-verdict:

```nftables
chain input {
    type filter hook input priority filter; policy drop;
    ct state established,related accept
    iif lo accept

    # Per-port verdict map:
    tcp dport vmap { 22 : jump ssh_in, 80 : accept, 443 : accept }
}

chain ssh_in {
    # Rules that apply only to SSH-bound packets.
    ip saddr @ssh_allow accept
    log prefix "SSH-BLOCKED: "
}
```

`vmap` is "verdict map." The destination port indexes into the map; the value is a verdict to apply. Compact and fast (O(1) hash lookup, vs O(N) rule scan).

Sets and maps are the feature that makes `nftables` notably more powerful than `iptables`. We don't lean heavily on them in exercise 3, but the homework asks you to refactor your ruleset to use a set.

## 8. Connection tracking (`conntrack`) in depth

The `ct state` matches we used:

- **`new`** — first packet of a connection (SYN for TCP).
- **`established`** — packet belongs to an existing tracked connection.
- **`related`** — packet is related to a tracked connection (e.g., ICMP-error for an established flow, the data channel of an FTP control connection).
- **`invalid`** — conntrack can't place the packet (malformed, late RST, etc.).
- **`untracked`** — packet has `notrack` set (advanced; outside our scope).

The kernel maintains a hash table of tracked connections (`/proc/net/nf_conntrack`). The table has a finite size; on a busy host you may need to bump it:

```bash
cat /proc/sys/net/netfilter/nf_conntrack_max          # default ~ 262144 on modern kernels
cat /proc/sys/net/netfilter/nf_conntrack_count        # how many are tracked now
```

For a hardened single-host firewall, the default is fine. Tracking is what makes the `established,related accept` rule possible — without conntrack, the firewall would need rules for return traffic too.

## 9. Rate limiting — the standard SSH protection

The line:

```nftables
tcp dport 22 ct state new limit rate 4/minute accept
```

Says: "Accept new SSH connections, but at most 4 per minute." After the limit is hit, subsequent matching packets fall through to the next rule (the explicit drop with log). The brute-forcer who hits 1000 SSHes per minute gets 4 accepted per minute and 996 dropped — their effective attack rate is throttled by 250x.

Per-source-IP rate limiting (the "actually fair" version) requires a set with timeouts:

```nftables
table inet filter {
    set ssh_attempts {
        type ipv4_addr;
        size 65535;
        flags dynamic, timeout;
        timeout 1m;
    }

    chain input {
        type filter hook input priority filter; policy drop;
        ct state established,related accept
        iif lo accept

        # Track every new SSH source, with a 1-minute decay
        tcp dport 22 ct state new add @ssh_attempts { ip saddr limit rate 4/minute }
        tcp dport 22 ct state new accept

        tcp dport { 80, 443 } accept
    }
}
```

This is dense; read the nftables wiki "Rate limiting matchings" page if it isn't clear yet. The pattern: a dynamic set with `limit rate`-flavored elements gives you per-key rate limiting.

## 10. Verifying — `nmap` from outside

The honest test of a firewall is a scan from a **different host**. A local `nmap localhost` proves only that your loopback works.

From your laptop, scan your hardened server:

```bash
nmap -sV -p- --reason your.vps.ip
# -sV : enumerate service versions
# -p- : all 65535 TCP ports
# --reason : show why each port is in its state
```

Expected output for a server hardened per §4:

```
Nmap scan report for your.vps.ip
Host is up, received echo-reply ttl 56 (0.012s latency).
Not shown: 65532 filtered tcp ports (no-response)
PORT    STATE  SERVICE  REASON          VERSION
22/tcp  open   ssh      syn-ack ttl 56  OpenSSH 9.6p1 Ubuntu 3ubuntu13.5 (Ubuntu Linux; protocol 2.0)
80/tcp  open   http     syn-ack ttl 56  nginx 1.24.0 (Ubuntu)
443/tcp open   https    syn-ack ttl 56  nginx 1.24.0 (Ubuntu)
```

Read every line:

- **"Not shown: 65532 filtered tcp ports (no-response)"** — the firewall silently dropped 65,532 SYN probes. This is the right behavior.
- **3 open ports** — exactly what you allowed. Anything else is a hole.

If you see `closed` instead of `filtered`, the firewall is `reject`-ing rather than dropping; the host replied with RST. Neither is wrong; `drop` is slightly stealthier (the scanner gets nothing back; can't distinguish a dead host from a firewalled host).

If you see **open** ports you didn't allow: investigate. `ss -tulpn` on the server to see what's listening; either close it (stop the service) or add a deliberate firewall rule.

`nmap` can also fingerprint the SSH cipher set:

```bash
nmap --script ssh2-enum-algos -p 22 your.vps.ip
```

The output lists the key exchange, cipher, MAC, and host-key algorithms the server offers. Use this to confirm `KexAlgorithms` and `Ciphers` directives in `sshd_config` did what you meant.

## 11. The other three firewalls (mentioned for orientation)

You will see these in the wild; we don't teach them.

- **`iptables` / `iptables-nft`** — on any current distro, `iptables` is `iptables-nft`, a translation layer. It writes nftables rules under the hood. Read-only for understanding old docs; do not use for new rulesets.
- **`ufw`** ("Uncomplicated Firewall") — Ubuntu's wrapper. `sudo ufw allow 22/tcp` writes one iptables rule under the hood (which writes one nftables rule under that). Friendly for one-host setups; obscures everything. If you administer many hosts or want auditable rules, skip `ufw`.
- **`firewalld`** — Red Hat's daemon-based firewall with **zones** (named groups of network interfaces with associated rulesets). More abstraction; useful when you have separate "trusted" (internal) and "public" (internet) interfaces with different rules. Fedora's default; works fine.

The general advice: pick one tool per host and stick with it. Two firewalls (e.g., `nftables` plus `firewalld` plus `ufw`) is a recipe for "the rule disappeared on reboot and nobody knows why."

## 12. The hardening checklist (recap)

For every public-facing host:

1. **Audit listening sockets**: `sudo ss -tulpn`. Confirm you know what each one is. Anything you don't recognize, investigate.
2. **Write `/etc/nftables.conf`** with the §4 template, plus your service ports.
3. **Validate syntax**: `sudo nft -c -f /etc/nftables.conf`.
4. **Apply the ruleset**: `sudo nft -f /etc/nftables.conf`. Hold a session open as the rollback path.
5. **Enable the service**: `sudo systemctl enable --now nftables.service`.
6. **Confirm rules loaded**: `sudo nft list ruleset`. Inspect.
7. **Test from outside**: `nmap -sV -p- your.host` from a different machine. Confirm only your allowed ports are `open`.
8. **Test SSH still works**: `ssh user@host` from a new shell. If it doesn't, use the held-open session to undo.
9. **Reboot the host**: `sudo reboot`. Wait. SSH back in. Confirm `sudo nft list ruleset` still shows the rules (the service brought them back).
10. **Re-scan from outside**: `nmap -sV -p- your.host`. Confirm post-reboot state matches pre-reboot.

Then write nothing else until you have a reason to.

## 13. Bash Yellow caution

- **`nft flush ruleset` over SSH** = your session dies the moment the rule that was permitting it is gone. Always re-load from a file in the same command: `sudo nft -f /etc/nftables.conf` (which `flush`es first, then re-adds — the gap is microseconds and your TCP `established` will survive it). Plain `nft flush ruleset` over SSH is a self-lockout.
- **`policy drop` with no `iif lo accept`** = loopback breaks. The database that talks to itself on `127.0.0.1:5432` stops working. Many local services depend on loopback; never block it.
- **Forgetting `ct state established,related accept`** = your outbound connections appear to "work" (SYN goes out) but the SYN-ACK reply is dropped on the way back. The symptom is "everything I try times out."
- **`nft add rule ...` without persisting** = the rule disappears on reboot. Edit the file; reload the service.
- **Different conf paths on Ubuntu vs Fedora** = your `/etc/nftables.conf` works on Ubuntu but is ignored on Fedora (which reads `/etc/sysconfig/nftables.conf`). Confirm with `systemctl cat nftables.service`.
- **Multiple firewalls fighting**: `firewalld` and a hand-rolled `/etc/nftables.conf` both try to own the ruleset. Whichever loaded last wins, and reboots can change the order. Pick one; `systemctl mask` the other.

## 14. What's next

You've learned how to write a firewall. Next, the exercises put it into practice: exercise 1 distributes a key and writes a `~/.ssh/config`; exercise 2 reaches a private host through a bastion; exercise 3 writes the nftables ruleset above on a real host and verifies with `nmap`. The challenge has you provision a $5/mo VPS and harden it end-to-end. The mini-project is the same VPS, kept alive for the rest of the course, with a written runbook.

---

*A firewall that you never tested with `nmap` is a hypothesis. A firewall that survived `nmap` and a reboot is a fact.*
