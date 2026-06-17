# Week 6 — Exercises

Three exercises, ~7 hours total. Order matters; do them in sequence. Every change you make to `sshd_config` must pass `sudo sshd -t` before reload; every nftables ruleset must pass `sudo nft -c -f FILE` before apply.

| # | File | Time | What you build |
|---|------|------|----------------|
| 01 | [exercise-01-key-auth-and-config.md](./exercise-01-key-auth-and-config.md) | 2 h | Generate an `ed25519` key, distribute it, write `~/.ssh/config`, disable password auth on the server |
| 02 | [exercise-02-proxyjump-bastion.md](./exercise-02-proxyjump-bastion.md) | 2 h | Reach a private host through a bastion with one `ssh` command. ProxyJump in config; scp/rsync work transparently. |
| 03 | [exercise-03-nftables-rules.md](./exercise-03-nftables-rules.md) | 3 h | Write a hardened `nftables` ruleset for an SSH + HTTP + HTTPS host, persist it, verify with `nmap` from a second machine. |

Set up a scratch directory:

```bash
mkdir -p ~/c14-week-06/exercises/{01,02,03}
```

Before each exercise: `ssh -V` shows OpenSSH 9.6 or newer, `nft --version` shows 1.0 or newer, you can `sudo` on the target, and you have **a rollback path** — a held-open second SSH session, your VPS provider's web console, or a hypervisor console. After each exercise: rules / config that aren't needed beyond the exercise are removed.

The clean-up incantations at the end of every exercise:

```bash
# SSH config rollback (server side):
sudo rm /etc/ssh/sshd_config.d/99-exercise.conf
sudo sshd -t && sudo systemctl reload sshd

# nftables rollback (server side):
sudo nft flush ruleset
sudo systemctl restart nftables.service       # re-applies /etc/nftables.conf
```

If you skip the `sshd -t` before reload, you may make `sshd` refuse to start on the next restart. Always test first.
