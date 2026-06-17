# Lecture 1 — SSH Keys, `ssh-agent`, `~/.ssh/config`, ProxyJump

> **Duration:** ~3 hours. **Outcome:** You generate an `ed25519` key, load it into `ssh-agent`, distribute the public half, write a `~/.ssh/config` stanza per host you talk to, harden `sshd_config` on a target server, and reach a private host through a bastion in one command. You read `ssh -G`, `ssh -vvv`, and `sshd -T` fluently.

SSH is older than most of the engineers who use it. It is also the single tool you touch most often once you start managing remote machines: a developer pushing to `git` uses SSH; an admin debugging a server uses SSH; a CI runner deploying a container uses SSH. The protocol has barely changed in twenty years. The **way we use it** has — keys instead of passwords, agent forwarding (carefully), ProxyJump instead of nested `ssh ... ssh ...` chains, `~/.ssh/config` instead of long command lines. This lecture is about the configuration that turns SSH from "a tool that works" into "a tool that scales to fifty hosts and survives audit."

Read at the keyboard. `ssh -V` should report **9.6 or newer**; older OpenSSH lacks a few of the defaults we lean on.

## 1. The protocol in one paragraph

SSH (Secure Shell, RFCs 4250-4254) is a client/server protocol over a single TCP connection (default port 22). The connection has three layers:

1. **Transport** — key exchange (Curve25519 by default since OpenSSH 8.5), server-host-key verification, symmetric encryption (ChaCha20-Poly1305 or AES-GCM), and integrity (HMAC, or AEAD-implicit).
2. **User-auth** — the client proves who it claims to be. Methods include `publickey`, `password`, `keyboard-interactive` (PAM, sometimes 2FA), `gssapi-with-mic` (Kerberos), `hostbased`.
3. **Connection** — once authenticated, the client opens *channels* multiplexed over the one TCP socket: a shell channel, a `scp` data channel, a `-L` port-forwarding channel, an `ssh-agent` forwarding channel.

You almost never think about layers 1 and 3. Layer 2 is where every decision lives.

## 2. Keys, generation, and the algorithm choice

The right key algorithm in 2026 is **Ed25519** (`ssh-keygen -t ed25519`). Why:

- Small (32-byte private, 32-byte public). The `authorized_keys` line fits on one screen.
- Fast verification. SSH handshake is microseconds.
- Modern cryptography. Bernstein-Lange curve; no NIST trust issue.
- Supported by every OpenSSH since 6.5 (2014). If you're talking to an OpenSSH from before 2014, the world has bigger problems.

The acceptable alternatives, ranked:

- **`rsa-3072`** (`ssh-keygen -t rsa -b 3072`) — older, larger, slower, fine. Use only if the target requires it (some legacy embedded systems and some compliance regimes).
- **`ecdsa-nistp256`** (`ssh-keygen -t ecdsa -b 256`) — fine cryptographically, awkward politically (NIST-blessed curve). Not wrong; just not preferred.
- **`dsa`** — dead. OpenSSH 7.0 (2015) removed support. If a tutorial says `dsa`, the tutorial is from a previous decade.

The generation incantation:

```bash
ssh-keygen -t ed25519 -a 100 -C "your-email@example.com $(date +%Y-%m-%d)"
# -t ed25519       : key type
# -a 100           : 100 rounds of the bcrypt KDF for the passphrase (slow; that's the point)
# -C "comment"     : a comment, stored in the public key
```

The interactive prompts:

```
Enter file in which to save the key (/home/you/.ssh/id_ed25519):
Enter passphrase (empty for no passphrase):
Enter same passphrase again:
```

- **File path.** The default (`~/.ssh/id_ed25519`) is fine for your main key. If you want a per-host or per-service key, use a different name: `~/.ssh/id_ed25519_github`, `~/.ssh/id_ed25519_work`. We will reference these by `IdentityFile=` in `~/.ssh/config`.
- **Passphrase.** Yes, use one. The passphrase encrypts the private key on disk. Without it, anyone who reads `~/.ssh/id_ed25519` (a backup tape, a stolen laptop, a misconfigured `find /home -name id_ed25519`) has your identity. `ssh-agent` will cache the unlocked key in memory so you type the passphrase **once per session**, not once per `ssh` invocation.

The two files that result:

- `~/.ssh/id_ed25519` — private key. Permissions `0600`. **Never** copy this off the machine that generated it.
- `~/.ssh/id_ed25519.pub` — public key. Permissions `0644`. Distribute this freely.

```bash
ls -la ~/.ssh/id_ed25519*
# -rw-------  1 you you 411 May 13 14:00 /home/you/.ssh/id_ed25519
# -rw-r--r--  1 you you  99 May 13 14:00 /home/you/.ssh/id_ed25519.pub
```

The `~/.ssh/` directory itself must be `0700`. SSH will refuse a private key if either the file or its parent is loose:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

A bad permissions error from `ssh` looks like:

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@         WARNING: UNPROTECTED PRIVATE KEY FILE!          @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Permissions 0644 for '/home/you/.ssh/id_ed25519' are too open.
```

`chmod 600` is the fix.

### Fingerprinting

The fingerprint is a one-line hash of the public key, used for "did you really mean to connect to that host" prompts and for confirming "is this the key I expect."

```bash
ssh-keygen -lf ~/.ssh/id_ed25519.pub
# 256 SHA256:Az9KdR+...your-fingerprint... your-email (ED25519)
```

The fingerprint format defaults to SHA256-base64 since OpenSSH 6.8 (2015). Old MD5-hex fingerprints still appear in old documentation; ignore them.

## 3. Distributing the public key

Two scenarios.

### 3.1 You already have password SSH to the target

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@target.example.com
```

`ssh-copy-id` SSHes in (you type the password), creates `~/.ssh/` if missing, appends your public key to `~/.ssh/authorized_keys`, and sets the correct permissions. Idempotent: re-running doesn't duplicate.

### 3.2 You don't have password SSH (e.g., a fresh VPS that already wants key auth)

Most VPS providers in 2026 accept a public key at provisioning time. Paste the **contents** of `~/.ssh/id_ed25519.pub` (one line) into the "SSH keys" field when you create the instance. The provider injects it into `/root/.ssh/authorized_keys` (or `/home/<distro-user>/.ssh/authorized_keys` for distros where root login is disabled, e.g., Ubuntu's `ubuntu` user).

The manual fallback when `ssh-copy-id` won't work and password auth is permitted:

```bash
cat ~/.ssh/id_ed25519.pub | ssh user@target 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

One pipeline. Idempotent in the "appends to the file" sense; rerun and the key appears twice, which is harmless but ugly.

### 3.3 What `authorized_keys` looks like

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKr7...the-public-key-bytes... your-email 2026-05-13
```

One line per allowed key. The first field is the type, the second the base64-encoded key bytes, the third the comment. Optional **restrictions** go at the front of the line:

```
restrict,from="203.0.113.0/24",command="/usr/local/bin/limited-shell" ssh-ed25519 AAAA... you@laptop
```

- `restrict` — disables all defaults (no port forwarding, no agent forwarding, no X11, no PTY). Useful for service keys.
- `from="..."` — only allow this key from this source network.
- `command="..."` — force a specific command on login; ignore whatever the client asked for. The pattern behind `git` over SSH.

Read `sshd(8)`'s `AUTHORIZED_KEYS FILE FORMAT` section for the full list.

## 4. `ssh-agent` — passphrase once, not every time

`ssh-agent` is a daemon that holds unlocked private keys in memory. The client (`ssh`) talks to it over a Unix socket (path in `$SSH_AUTH_SOCK`). When `ssh` needs to authenticate with a key, it asks the agent to sign a challenge — the private key never leaves the agent's address space.

On most desktop distros and on macOS, an agent is started for you at login. Confirm:

```bash
echo "$SSH_AUTH_SOCK"
# Should print a path. If empty, no agent.
ssh-add -l
# Lists keys currently in the agent. "The agent has no identities." if empty.
```

If no agent, start one in your shell:

```bash
eval "$(ssh-agent -s)"
```

(The `eval` is because `ssh-agent -s` prints shell statements to set `SSH_AUTH_SOCK` and `SSH_AGENT_PID` in the **current** shell.)

Add a key:

```bash
ssh-add ~/.ssh/id_ed25519
# Enter passphrase for /home/you/.ssh/id_ed25519:
# Identity added: /home/you/.ssh/id_ed25519 (your-email 2026-05-13)
```

Time-limited entry (forgets after one hour):

```bash
ssh-add -t 1h ~/.ssh/id_ed25519
```

List loaded keys:

```bash
ssh-add -l
# 256 SHA256:Az9KdR+...fingerprint... your-email 2026-05-13 (ED25519)
ssh-add -L
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKr7... your-email 2026-05-13
```

`-l` shows fingerprints; `-L` dumps the full public keys. Use `-L` when you want to add the in-memory key to a remote's `authorized_keys` without `cat`-ing a file.

Remove a key:

```bash
ssh-add -d ~/.ssh/id_ed25519
# OR remove all keys:
ssh-add -D
```

### 4.1 macOS Keychain integration

On macOS, you can ask the agent to fetch passphrases from the system Keychain (instead of prompting):

```
# ~/.ssh/config
Host *
    UseKeychain yes
    AddKeysToAgent yes
```

`AddKeysToAgent yes` makes the first `ssh` invocation that needs a key add it to the agent automatically. Without this, you must `ssh-add` manually after each login.

### 4.2 Persistent agents on Linux

`gnome-keyring`, `ksh`, `kwallet`, and others provide agent-like services on Linux desktops. For a server / minimal install: a `~/.bashrc` snippet that starts an agent if none is running:

```bash
# ~/.bashrc
if [ -z "$SSH_AUTH_SOCK" ] && command -v ssh-agent >/dev/null; then
    eval "$(ssh-agent -s)" >/dev/null
fi
```

For a more polished setup, look at `keychain` (a wrapper that persists the agent across logins) or `gpg-agent` with `enable-ssh-support` in `gpg-agent.conf`.

## 5. `~/.ssh/config` — the configuration file that scales

Once you talk to more than two remote hosts, the command line gets long:

```bash
ssh -i ~/.ssh/id_ed25519_work -p 2222 -o ConnectTimeout=10 -o ServerAliveInterval=60 deploy@bastion-east.work.example.com
```

That command appears in your shell history, in scripts, in muscle memory. The right answer is to put it in `~/.ssh/config` once and never type the long form again. The file is INI-like; the order of stanzas matters (first match wins for **most** directives; some accumulate).

A minimal example:

```
# ~/.ssh/config
Host *
    AddKeysToAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    IdentitiesOnly yes

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519_github

Host work-bastion
    HostName bastion-east.work.example.com
    User deploy
    Port 2222
    IdentityFile ~/.ssh/id_ed25519_work
```

Now `ssh work-bastion` does what the long command line did. `ssh github.com` uses your GitHub-specific key. The catch-all `Host *` stanza applies to **every** host (its directives merge with later, more specific stanzas; first-match wins per directive).

### 5.1 The directives you will use most

- **`Host pattern`** — pattern for the stanza. Glob-aware: `Host *.work.example.com` matches all work hosts. Comma-separates multiple: `Host alpha,beta,gamma`.
- **`HostName`** — the real DNS name or IP. The `Host` line is the *alias* you type; `HostName` is what `ssh` resolves.
- **`User`** — the remote username. Default: your local username.
- **`Port`** — TCP port. Default: 22.
- **`IdentityFile`** — which private key. Can repeat; ssh tries them in order. Combine with `IdentitiesOnly yes` to prevent the agent from offering unrelated keys.
- **`IdentitiesOnly yes`** — when set, `ssh` uses only the `IdentityFile`s listed; ignores the agent's other keys. **Use this whenever you have more than three keys** — otherwise you'll hit `MaxAuthTries` on the server after offering five wrong keys.
- **`ProxyJump`** — tunnel through one or more intermediate hosts (see §7).
- **`ForwardAgent yes`** — forward your `ssh-agent` socket to the remote (see §8).
- **`ServerAliveInterval N`** — send a keep-alive every N seconds. Keeps NAT mappings alive on flaky links.
- **`ConnectTimeout N`** — fail the TCP connect after N seconds. Default: OS default (≈ 75 sec).
- **`StrictHostKeyChecking`** — `yes` (refuse new hosts), `accept-new` (auto-accept new hosts, refuse changed), `no` (accept anything, danger), `ask` (the default — prompt). Use `accept-new` in scripted contexts.
- **`UserKnownHostsFile`** — path to the `known_hosts` file. Default: `~/.ssh/known_hosts`.

### 5.2 `Match` blocks — programmable selectors

`Match` is `Host` on steroids. The selectors include `user`, `host`, `originalhost`, `localuser`, `exec "command"` (run the command; match if exit 0).

```
# Use a specific key only when logging in as the deploy user
Match user deploy
    IdentityFile ~/.ssh/id_ed25519_deploy
    IdentitiesOnly yes

# Use a different config branch when on a specific network
Match exec "test \"$(/usr/bin/iwgetid -r 2>/dev/null)\" = 'work-wifi'"
    ProxyJump work-bastion
```

`Match` is evaluated **every** time SSH considers a host. For dynamic configs (different keys when at home vs at work, different jump hosts on different networks), `Match exec` is the lever.

### 5.3 `Include` — modular configs

```
# ~/.ssh/config
Include ~/.ssh/config.d/*.conf
```

Drop per-project config files into `~/.ssh/config.d/`. The main file stays short.

### 5.4 `ssh -G` — show me the effective config

The killer debugging command:

```bash
ssh -G work-bastion
# user deploy
# hostname bastion-east.work.example.com
# port 2222
# identityfile ~/.ssh/id_ed25519_work
# serveraliveinterval 60
# ... 50 more lines ...
```

`-G` resolves your config (including `Host *`, `Match` blocks, and `Include`s) and dumps the result. When you change `~/.ssh/config` and the wrong thing happens, **always** run `ssh -G HOSTNAME` first.

## 6. `sshd_config` — the server side, hardened

Move now to the **target** machine (your VPS, your VM, the box you SSH into). The configuration file is `/etc/ssh/sshd_config`; on modern Debian/Ubuntu and Fedora, it `Include`s `/etc/ssh/sshd_config.d/*.conf`, so put overrides in a separate `.conf` instead of editing the vendor file.

The minimum-viable hardened `/etc/ssh/sshd_config.d/99-hardened.conf`:

```
# Listen
Port 22

# Auth
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers your-username

# Resource limits
LoginGraceTime 30
MaxAuthTries 3
MaxSessions 4

# Keep-alives
ClientAliveInterval 300
ClientAliveCountMax 2

# Disable what you don't use
X11Forwarding no
AllowTcpForwarding no
PermitTunnel no
GatewayPorts no
PermitUserEnvironment no
```

Each line in plain English:

- **`Port 22`** — listen on 22. Moving to 2222 reduces log noise but is not security; brute-forcers scan all ports.
- **`PermitRootLogin no`** — root cannot SSH in. Period. Create a user, give them `sudo`, log in as the user.
- **`PasswordAuthentication no`** — passwords are not accepted. With this off, only keys work. **The single most important line.** Make sure your key auth works **before** flipping this.
- **`PubkeyAuthentication yes`** — public-key auth is accepted. (Default is `yes` since the dawn of OpenSSH; the line is for explicitness.)
- **`AuthenticationMethods publickey`** — only `publickey` is accepted. Stronger than `PasswordAuthentication no` alone because it also disables `keyboard-interactive` (which can be PAM, which can be passwords).
- **`AllowUsers your-username`** — allow-list. Only the listed users may log in. `AllowGroups ssh-users` is the alternative when you have many users.
- **`LoginGraceTime 30`** — 30 seconds to complete auth before disconnect. Reduces auth-flood resource burn.
- **`MaxAuthTries 3`** — 3 failed auth attempts per connection. (The brute-forcer reconnects; this only slightly slows them. The real defense is `PasswordAuthentication no`.)
- **`ClientAliveInterval 300`** — server pings every 300 seconds. Combined with `ClientAliveCountMax 2`, an idle client is disconnected after 10 minutes of silence. Useful for closing dead sessions.
- **`X11Forwarding no`** — no GUI forwarding. You're SSHing into a server; you don't need X11.
- **`AllowTcpForwarding no`** — no `-L` / `-R` tunnels. Exception: bastion hosts need `AllowTcpForwarding yes` (or specifically `local`) for ProxyJump and tunneling to work.

### 6.1 The reload-not-restart distinction

```bash
# Always test the config syntax FIRST:
sudo sshd -t                                    # silent if OK; prints error and line number if not

# Reload (preserves existing sessions):
sudo systemctl reload sshd                      # or "ssh.service" on Debian

# Restart (kills existing sessions; needed for some Port/ListenAddress changes):
sudo systemctl restart sshd                     # use sparingly; reload is almost always enough
```

**Never** `restart` `sshd` from the SSH session you're using to administer it without holding a second SSH session open as the rollback path. If the new config is broken, the rollback session is your only way back in.

### 6.2 `Match` blocks on the server

`Match` blocks on the server side gate access by user, group, or address. Example: allow password auth for one specific user (e.g., a deploy bot reachable only from the CI runner's IP):

```
# /etc/ssh/sshd_config.d/99-hardened.conf
# Default: deny everything except publickey
PasswordAuthentication no
AuthenticationMethods publickey

# Exception: deploy bot from CI, with a password, restricted to one command
Match User deploy-bot Address 203.0.113.42
    PasswordAuthentication yes
    AuthenticationMethods password
    ForceCommand /usr/local/bin/deploy-runner
```

`Match` directives apply **only** until the next `Match` line (or end of file). The indented form is convention, not syntax.

### 6.3 `sshd -T` — show me the effective server config

The server-side analog of `ssh -G`:

```bash
sudo sshd -T | grep -i password
# passwordauthentication no
# kbdinteractiveauthentication no
```

`sshd -T` evaluates the full config (including `Include`s, `Match` blocks for a default principal) and dumps the resolved values. Use it after every edit to confirm the change applied.

## 7. `ProxyJump` — the bastion pattern done right

A common topology: one **bastion** host is reachable from the internet on TCP 22. Behind it, a private network of hosts that have **no** internet-facing SSH at all. To reach `private-host-1`, you SSH to the bastion, then SSH from the bastion to `private-host-1`.

The naive way:

```bash
ssh bastion
# (now on bastion)
ssh private-host-1
# (now on private-host-1)
```

This works. It is awkward: two prompts, two sets of credentials, agent forwarding required if you want to use your laptop's keys, and `scp` / `rsync` from your laptop to the private host doesn't work without per-hop magic.

The right way, OpenSSH 7.3+ (2016):

```bash
ssh -J bastion private-host-1
```

Or, as a config stanza:

```
# ~/.ssh/config
Host bastion
    HostName bastion.example.com
    User you
    IdentityFile ~/.ssh/id_ed25519

Host private-*
    User you
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump bastion
```

Now `ssh private-host-1` does the right thing. `scp` and `rsync` over the same tunnel also work, transparently — `scp file private-host-1:/tmp/` goes through the bastion.

### 7.1 What `ProxyJump` actually does

`ssh` opens a TCP connection to the bastion, authenticates with the bastion's key configuration, then asks the bastion to forward a TCP connection to `private-host-1:22`. The second SSH handshake happens **end-to-end between your laptop and `private-host-1`** — the bastion only forwards the bytes. The bastion cannot decrypt the second session. The bastion cannot see what you type.

Multiple jumps:

```bash
ssh -J bastion1,bastion2 private-host-3
```

Each comma-separated entry is a hop. Up to a half-dozen is fine; latency stacks.

### 7.2 ProxyJump vs ProxyCommand

Older configs use:

```
Host private-*
    ProxyCommand ssh -W %h:%p bastion
```

This is the pre-7.3 way to do the same thing. `ProxyJump` is strictly better: shorter, supports multi-hop, supports agent-less, and `-W` requires the bastion's `sshd_config` to have `AllowTcpForwarding yes` for the `-W` direct-tcpip channel. `ProxyJump` requires the same on the bastion, but the failure mode is clearer.

Replace `ProxyCommand ssh -W %h:%p X` with `ProxyJump X` in any config you maintain.

### 7.3 Bastion `sshd_config` differences

The bastion needs to **permit forwarding**:

```
# /etc/ssh/sshd_config.d/99-bastion.conf on the bastion only
AllowTcpForwarding yes
PermitTunnel no
GatewayPorts no
X11Forwarding no
# All the other hardening from §6 still applies.
```

The private hosts do **not** need `AllowTcpForwarding yes` — they're being SSH-ed *to*, not through.

## 8. Agent forwarding — convenience, with a footnote

`ssh -A target` (or `ForwardAgent yes` in config) exposes your laptop's `ssh-agent` to `target`. From `target`, you can `git push`, or `ssh another-host`, and the auth uses your laptop's keys without copying them.

```bash
ssh -A bastion
# (now on bastion)
ssh private-host-1               # uses your forwarded agent; same key as if you'd ProxyJumped
```

It works. It also means: **any process on the bastion running as your user (or as root) can use your forwarded agent for as long as you're connected**. A compromised bastion gets to authenticate to private hosts as you, indefinitely-while-you're-logged-in.

`ProxyJump` is strictly better for the "I want to reach private hosts through a bastion" case. The agent is only on your laptop; the bastion never sees it.

**Use agent forwarding when**: you actually need to run a command on the remote that itself uses SSH, and `ProxyJump` doesn't fit. Example: you're on the remote, debugging a `git clone` from a private repo that needs your GitHub key. In that case, `ForwardAgent yes` for that one session is the right call.

**Do not use agent forwarding when**: you can `ProxyJump`, when the remote is shared with other users, when the remote is internet-facing.

## 9. The hardening checklist (recap)

For every SSH server you administer:

1. **Generate a key on your laptop**: `ssh-keygen -t ed25519 -a 100`. Passphrase. `chmod 600` the private; `chmod 700` the `.ssh/` directory.
2. **Distribute the public key**: `ssh-copy-id` or paste at provider provisioning.
3. **Test key auth works** *while password auth is still on*: `ssh -o PasswordAuthentication=no user@host`. Must succeed without prompting for a password.
4. **Edit `/etc/ssh/sshd_config.d/99-hardened.conf`** on the server: paste the block from §6.
5. **Test the new config syntax**: `sudo sshd -t`. Silent = OK.
6. **Hold a second SSH session open** (your rollback path).
7. **Reload sshd**: `sudo systemctl reload sshd`.
8. **In a NEW terminal**, confirm SSH still works: `ssh user@host`. If it doesn't, use the held-open session to undo.
9. **Confirm `sshd -T`** shows the values you expect: `sudo sshd -T | grep -i 'permitroot\|passwordauthentication\|pubkey'`.
10. **Run `ssh-audit` (or `nmap --script ssh2-enum-algos`)** from your laptop against the server. Confirm the algorithm allow-list matches your intent.

Then write `~/.ssh/config` on your laptop so you never have to type the long form again.

## 10. Bash Yellow caution

- **`PasswordAuthentication no` plus a missing `authorized_keys`** = locked out. The fix requires a provider web console or a hypervisor console. Always test key auth before disabling passwords.
- **`AllowUsers your-username`** typoed = locked out for everyone. `sshd -t` does **not** catch typos in `AllowUsers` (it can't know the spelling). Hold a session open.
- **`AddressFamily inet6` on a server with no IPv6** = `sshd` won't bind = no SSH. The default (`any`) is almost always right.
- **`PermitRootLogin without-password`** is *not* `PermitRootLogin no`. It permits root with a key. If you want root entirely off, use `no`.
- **`StrictHostKeyChecking no` in client config** = silent acceptance of any host key change. That's exactly how MITM works. Use `accept-new` instead.
- **`Match` block continuation**: a `Match` block applies until the next `Match` or end of file. The first non-`Match` line is **already inside the previous `Match`**. A common mistake: writing `Match User deploy-bot ...` then continuing to write what you think is "global" config below; in fact it applies only to `deploy-bot`. Always end with `Match all` to "close" or re-place the global directives above.

## 11. What's next

Lecture 2 covers the network layer: TCP, ports, listening sockets, and `nftables`. The hardened SSH server you built in this lecture is still reachable on every interface; the firewall is what restricts that. By the end of lecture 2, your `sshd` will be reachable only on the public interface, only on TCP 22, only from a sensibly-bounded source, with rate-limiting on new connections.

---

*A key without a passphrase is a credential on disk. A `sshd_config` without `sshd -t` is a coin flip. A `sshd reload` without a second session is a self-inflicted outage. We do not do any of those things.*
