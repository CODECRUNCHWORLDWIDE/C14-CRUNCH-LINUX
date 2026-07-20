# Week 6 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 7.

---

**Q1.** Which SSH key type is the recommended default in 2026 for new keys?

- A) `dsa` (1024-bit)
- B) `rsa` (2048-bit)
- C) `ed25519`
- D) `ecdsa-nistp521`

---

**Q2.** What is the difference between `PermitRootLogin no` and `PermitRootLogin prohibit-password`?

- A) Both forbid root login entirely.
- B) `prohibit-password` permits root with a key but not a password; `no` forbids root entirely.
- C) `no` is an alias for `prohibit-password`.
- D) `prohibit-password` is the OpenSSH 8.x replacement for `no`.

---

**Q3.** You want `ssh private-host` (one command) to tunnel through `bastion`. Which directive does this?

- A) `ForwardAgent yes`
- B) `ProxyCommand ssh -W %h:%p bastion`
- C) `ProxyJump bastion`
- D) `BindAddress bastion`

---

**Q4.** A bastion is compromised. You have been connecting to private hosts through it via `ssh -A` (agent forwarding) all week. What is the blast radius?

- A) Zero. Agent forwarding is end-to-end encrypted.
- B) The compromised bastion can authenticate as you, with your keys, to any host your agent can reach — for as long as you stayed connected.
- C) Only the bastion's own data is at risk.
- D) The brute-forcer learns your public key but cannot derive your private key.

---

**Q5.** Which `nftables` verdict drops a packet but sends ICMP "unreachable" back to the source?

- A) `accept`
- B) `drop`
- C) `reject`
- D) `continue`

---

**Q6.** A hardened-server `nftables` input chain has `policy drop`. Which rule **must** come first?

- A) `tcp dport 22 accept`
- B) `iif lo accept`
- C) `ct state established,related accept`
- D) `ip saddr 0.0.0.0/0 drop`

---

**Q7.** You run `nmap -sV -p- your.host` from a different machine. Three ports show `open`, the rest show `filtered`. What does `filtered` mean?

- A) The port has a service that responded with a banner.
- B) The port replied with TCP RST.
- C) No response was received; a firewall is silently dropping the SYN probe.
- D) The port is in `TIME_WAIT`.

---

**Q8.** You edit `/etc/ssh/sshd_config.d/99-hardened.conf` and want to apply the change. Which sequence is correct?

- A) `sudo systemctl restart sshd` immediately.
- B) `sudo sshd -t` (validate syntax), then `sudo systemctl reload sshd`, while keeping a second SSH session open as the rollback path.
- C) `sudo systemctl reload sshd` and trust the result.
- D) Edit the file; the change takes effect on the next connection automatically.

---

**Q9.** What does `flush ruleset` at the top of `/etc/nftables.conf` do?

- A) Clears the kernel's connection-tracking table.
- B) Removes all existing nftables tables and chains, so the rest of the file builds from empty. Makes `nft -f` idempotent.
- C) Resets the chain policies to `accept`.
- D) Discards packets currently in flight.

---

**Q10.** You run `ssh -G work-bastion` and the output shows `port 22`, but you set `Port 2222` in your `~/.ssh/config`. What's the most likely cause?

- A) `ssh -G` reports defaults, not your config.
- B) A `Host *` block (with no `Port`) appeared **before** your specific `Host work-bastion` block, and a more-specific block overrode the global default — but you've checked and it didn't. Look for **another** matching block (`Host *bastion*`) further up that has `Port 22` explicitly set; `ssh_config` is first-match-wins per directive.
- C) The `~/.ssh/config` file is in the wrong location.
- D) SSH only reads `~/.ssh/config` when invoked with `-F`.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **C** — `ed25519` (Bernstein-Lange curve, 32-byte keys, fast, modern). `rsa-3072` is the acceptable fallback for legacy systems. `dsa` is dead (removed in OpenSSH 7.0). `ecdsa-nistp521` works but uses NIST curves.
2. **B** — `prohibit-password` permits root login with a key only (no password). `no` forbids root login entirely. The two are different defaults; the modern hardened recommendation is `no`.
3. **C** — `ProxyJump bastion` is the OpenSSH 7.3+ directive. It tunnels through `bastion` and does the second SSH handshake end-to-end with the destination — the bastion only forwards bytes. `ProxyCommand ssh -W` is the older form `ProxyJump` replaced.
4. **B** — Agent forwarding exposes your `ssh-agent` socket on the remote host. Any process on the bastion running as your user (or as root) can ask the agent to sign auth challenges as you, for as long as you're connected. The keys never copy to the bastion, but the *use* of them is delegated. `ProxyJump` avoids this entirely.
5. **C** — `reject` drops and sends ICMP "unreachable" (TCP layer: sends RST). `drop` silently discards. Both end the packet; the visible difference is whether the scanner gets a "closed" (rejected) or "filtered" (dropped) status.
6. **C** — `ct state established,related accept` must be first. Without it, the return packets of your own outbound connections (SYN-ACKs, ICMP replies) are dropped by the policy, and "nothing works." `iif lo accept` is rule two; the service-specific accepts come after.
7. **C** — `filtered` means **no response** from the host. The SYN probe went out; nothing came back. The most common cause is a firewall silently dropping the probe. `closed` would mean the host actively replied with RST. `open` would mean SYN-ACK. The three states are the basic vocabulary of `nmap` output.
8. **B** — `sshd -t` validates syntax (catches typos that would otherwise make `sshd` refuse to reload). `reload` is preferable to `restart` (preserves existing sessions). A second SSH session held open is the rollback path if your new config is broken. Skipping any of the three is the canonical self-lockout.
9. **B** — `flush ruleset` removes all tables and chains. The rest of the file rebuilds the ruleset from empty, so re-running `nft -f /etc/nftables.conf` produces the same state regardless of what was loaded before. Without `flush`, the file is additive and re-running accumulates duplicates.
10. **B** — `ssh_config` is **first-match-wins per directive**. If a `Host *bastion*` block appears before your `Host work-bastion` block and sets `Port 22`, that wins. (`Host *` is the explicit catch-all; pattern matching can sneak in earlier blocks unexpectedly.) `ssh -G HOST` shows the resolved values; trust it and trace upward through your config to find the override.

</details>

If you scored 9+: move to homework. 7-8: re-read the lecture sections you missed (especially `ProxyJump` mechanics and the nftables canonical input chain). <7: re-read both lectures from the top, then redo exercise 01.
