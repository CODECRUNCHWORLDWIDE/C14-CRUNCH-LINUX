# Exercise 01 — Key Auth and `~/.ssh/config`

**Time:** ~2 hours. **Goal:** Generate an `ed25519` key on your laptop, distribute the public half to a target server, prove key auth works, write a `~/.ssh/config` stanza so you never type a long SSH command line again, and then disable password authentication on the server. Build the muscle memory for the ten-step lifecycle (Lecture 1, §9). Every step exists for a reason; if you skip steps, you will lock yourself out.

You will need a **client** (your laptop) and a **target server**. The target can be a Ubuntu 24.04 VM, a Fedora 41 VM, a Raspberry Pi on your home network, or — recommended — a $5/mo VPS from any provider. The exercise assumes you have password SSH (or some other admin access) to the target. If your target is a fresh VPS that requires a key at provisioning, paste your laptop's `~/.ssh/id_ed25519.pub` into the provider's "SSH keys" field when creating it; you can still do the rest of the exercise.

Verify prerequisites on your laptop:

```bash
ssh -V                                    # OpenSSH_9.6 or newer
ssh-keygen --help 2>&1 | grep -- -a       # confirm -a (KDF rounds) is supported
```

Verify on the target server (you'll need this later):

```bash
ssh user@target sudo sshd -V              # 9.6 or newer
ssh user@target sudo sshd -T | grep -i passwordauth
# passwordauthentication yes        # the current default; we will flip this
```

Set up a scratch directory on your laptop:

```bash
mkdir -p ~/c14-week-06/exercises/01
cd ~/c14-week-06/exercises/01
```

---

## Part 1 — Generate the key (15 min)

### Step 1.1 — Generate

If you already have an `~/.ssh/id_ed25519`, skip to step 1.2. If you don't:

```bash
ssh-keygen -t ed25519 -a 100 -C "your-email@example.com $(date +%Y-%m-%d)"
```

Accept the default path (`~/.ssh/id_ed25519`). **Set a passphrase.** Yes, even on your laptop. The passphrase is what makes the key safe to back up.

Confirm:

```bash
ls -la ~/.ssh/id_ed25519*
# -rw-------  1 you you  411 May 13 14:00 /home/you/.ssh/id_ed25519
# -rw-r--r--  1 you you   99 May 13 14:00 /home/you/.ssh/id_ed25519.pub
ssh-keygen -lf ~/.ssh/id_ed25519.pub
# 256 SHA256:Az9K... your-email 2026-05-13 (ED25519)
```

The permissions matter. If they're wrong (`chmod 644` on the private), SSH will refuse the key. Force them:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### Step 1.2 — Load into the agent

```bash
ssh-add -l
# "The agent has no identities."  -- expected on a fresh shell
# (If you see "Could not open a connection to your authentication agent", start one:
#  eval "$(ssh-agent -s)" )

ssh-add ~/.ssh/id_ed25519
# Enter passphrase for /home/you/.ssh/id_ed25519:
# Identity added: /home/you/.ssh/id_ed25519 (your-email 2026-05-13)

ssh-add -l
# 256 SHA256:Az9K... your-email 2026-05-13 (ED25519)
```

You will type the passphrase **once per agent session**, not once per SSH.

---

## Part 2 — Distribute the public key (15 min)

### Step 2.1 — Use `ssh-copy-id`

The canonical way:

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@target.example.com
# Number of key(s) added: 1
```

Type the **target user's password** when prompted. `ssh-copy-id` will create `~/.ssh/` on the target if missing, append the public key to `~/.ssh/authorized_keys`, and chmod everything correctly.

If `ssh-copy-id` is unavailable (Windows, embedded target), use the pipeline fallback:

```bash
cat ~/.ssh/id_ed25519.pub | ssh user@target 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'
```

### Step 2.2 — Confirm key auth works

```bash
ssh -o PasswordAuthentication=no user@target.example.com
# (should not prompt for a password)
# Welcome to Ubuntu 24.04.2 LTS (...)
user@target:~$
```

The `-o PasswordAuthentication=no` flag forces the client to **not** offer a password. If the server accepts the connection, the key worked. If it refuses, the key did not get installed properly; do **not** disable password auth on the server yet.

On the target, check that the public key is there:

```bash
user@target:~$ cat ~/.ssh/authorized_keys
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKr7...  your-email 2026-05-13
```

Exit the SSH session:

```bash
user@target:~$ exit
```

---

## Part 3 — Write `~/.ssh/config` (30 min)

Now stop typing `ssh user@target.example.com` every time.

### Step 3.1 — Create the file

```bash
touch ~/.ssh/config
chmod 600 ~/.ssh/config
```

### Step 3.2 — Add a global block and a host stanza

Edit `~/.ssh/config`:

```
# ~/.ssh/config
# Global defaults
Host *
    AddKeysToAgent yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    IdentitiesOnly yes
    HashKnownHosts yes
    StrictHostKeyChecking accept-new

# Your target server
Host target
    HostName target.example.com
    User your-username-on-target
    Port 22
    IdentityFile ~/.ssh/id_ed25519
```

Save. Now `ssh target` should "just work":

```bash
ssh target
# Welcome to Ubuntu ...
your-username@target:~$ exit
```

### Step 3.3 — Inspect the resolved config

```bash
ssh -G target | head -30
# user your-username-on-target
# hostname target.example.com
# port 22
# identityfile ~/.ssh/id_ed25519
# serveraliveinterval 60
# ... (the resolved values for every directive, including defaults)
```

`ssh -G` shows you exactly what `ssh target` will use. If the wrong directive applies, this is how you find out.

### Step 3.4 — Add a second host

Add another stanza for a second server (your VM, a friend's box, your Raspberry Pi, or a second VPS). If you don't have a second host, add a `Host github.com` stanza:

```
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Test:

```bash
ssh -T github.com
# Hi <your-handle>! You've successfully authenticated, but GitHub does not provide shell access.
```

(That message is GitHub's expected output for a successful SSH auth check.)

---

## Part 4 — Harden `sshd_config` on the server (30 min)

Now the destructive part. **Hold a second SSH session open in a separate terminal** before you proceed:

```bash
# Terminal A — your "safe" session. Don't touch this.
ssh target

# Terminal B — where you will make changes. Open it now.
ssh target
```

In Terminal B, prepare the hardened config:

### Step 4.1 — Create the drop-in file

```bash
sudoedit /etc/ssh/sshd_config.d/99-hardened.conf
```

Contents:

```
# /etc/ssh/sshd_config.d/99-hardened.conf
# C14 Week 6 Exercise 01 — hardened SSH

Port 22

PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AuthenticationMethods publickey
AllowUsers your-username-on-target

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
```

Replace `your-username-on-target` with the actual username (`whoami` if unsure). **Do not omit `AllowUsers`** — but make sure the value is correct. A typo here will lock you out for everyone.

### Step 4.2 — Validate

```bash
sudo sshd -t
# (silent = OK)
```

If `sshd -t` prints an error, fix it. Common errors: a directive misspelled, a value where a `Match` block was expected, an `Include` path that doesn't exist.

### Step 4.3 — Confirm the effective config

```bash
sudo sshd -T | grep -i -E 'permitroot|passwordauth|pubkeyauth|authenticationmeth|allowusers'
# permitrootlogin no
# passwordauthentication no
# pubkeyauthentication yes
# authenticationmethods publickey
# allowusers your-username-on-target
```

If any line shows the **wrong** value, your drop-in didn't apply (or the main `sshd_config` overrode it). Investigate before reload.

### Step 4.4 — Reload `sshd`

```bash
sudo systemctl reload sshd
# (Ubuntu calls the service "ssh.service"; both names work.)
```

**Reload preserves existing sessions.** Your Terminal A session is still alive.

### Step 4.5 — Test from a new shell

In a **new** terminal:

```bash
ssh target
# Should succeed instantly with no password prompt.
```

If it succeeds: you're done with the hard part. Move to part 5.

If it fails: drop to Terminal A (the held-open session) and undo:

```bash
# In Terminal A:
sudo rm /etc/ssh/sshd_config.d/99-hardened.conf
sudo sshd -t && sudo systemctl reload sshd
# Now try the new shell again.
```

Then read the error in your client (`ssh -vvv target` is your friend) and fix the drop-in before retrying.

---

## Part 5 — Verify with `ssh-audit` (20 min)

Install `ssh-audit` on your laptop:

```bash
pip install --user ssh-audit
# OR: pipx install ssh-audit
```

Run it against your hardened server:

```bash
ssh-audit target.example.com
```

The output is multi-page. Look at the `(rec)` (recommendation) and `(fail)` (failure) lines. A baseline hardened OpenSSH 9.6 should report mostly green; some `(rec)` lines suggest tightening `KexAlgorithms`, `Ciphers`, or `HostKeyAlgorithms` further. That tightening is optional for this exercise and required for the homework.

Save the output:

```bash
ssh-audit target.example.com > ~/c14-week-06/exercises/01/ssh-audit-before.txt 2>&1
```

You'll diff against an "after" run in the homework problem on crypto tightening.

---

## Part 6 — Document and commit (15 min)

Save your `~/.ssh/config` (sanitized — no real hostnames or IPs in a public repo) to your portfolio:

```bash
cp ~/.ssh/config ~/c14-week-06/exercises/01/ssh-config-redacted.txt
# Edit to remove real hostnames, replace with target.example.com etc.
```

Save the server-side drop-in:

```bash
ssh target "sudo cat /etc/ssh/sshd_config.d/99-hardened.conf" > ~/c14-week-06/exercises/01/sshd-hardened.conf
```

Write `notes.md`:

```markdown
# Exercise 01 — Notes

## What I built
- Generated an ed25519 key with a passphrase.
- Distributed the public key to <target>.
- Wrote ~/.ssh/config with <N> host stanzas.
- Hardened sshd_config on the target: PermitRootLogin no, PasswordAuthentication no, AuthenticationMethods publickey, AllowUsers <user>.

## What surprised me
- (one paragraph)

## What broke
- (any rollback you had to use, and why)

## The `ssh-audit` baseline
- (paste the summary section)
```

Commit to your portfolio repo under `c14-week-06/exercises/01/`.

---

## Acceptance criteria

- `ssh target` succeeds with no password prompt and your key.
- `ssh -G target` shows `hostname`, `user`, `port`, `identityfile` resolved correctly.
- On the server: `sudo sshd -T | grep passwordauthentication` reports `no`.
- On the server: `sudo sshd -T | grep authenticationmethods` reports `publickey`.
- On the server: `sudo sshd -T | grep permitrootlogin` reports `no`.
- A fresh `ssh -o PreferredAuthentications=password user@target` (forcing password) **fails** with `Permission denied (publickey)` — the server rejected the auth method.
- `~/.ssh/config` is `chmod 600`; `~/.ssh/id_ed25519` is `chmod 600`; `~/.ssh/` is `chmod 700`.

If all six pass, exercise 01 is done. Move to exercise 02.

---

## Common failure modes

- **"Permission denied (publickey)" on `ssh target` after the reload.**
  Your key isn't in the right `authorized_keys` for the right user. SSH `-vvv` will show the key offer. Verify on the server: `cat ~/.ssh/authorized_keys` as the user named in `AllowUsers`. If the key isn't there, copy it again.
- **"Bad configuration option: XYZ" from `sshd -t`.**
  Typo in the drop-in. Edit and re-test. `sshd -t` is fail-loud; trust it.
- **Reload succeeded but existing sessions die anyway.**
  Probably not a `reload` — somebody (you?) ran `restart`. Restart kills sessions. Use `reload`.
- **`AllowUsers` typoed; nobody can log in.**
  Use Terminal A (the held-open session) to undo. If Terminal A is gone, use the provider's web console.
- **`~/.ssh/config` ignored.**
  Check permissions: `chmod 600 ~/.ssh/config`. If the file is world-readable, `ssh` ignores it. If it's `chmod 644`, `ssh` issues a warning and proceeds — but some directives behave oddly.
- **The agent prompts for the passphrase on every `ssh`.**
  `ssh-add ~/.ssh/id_ed25519` once, then check `ssh-add -l` shows the key. If the agent loses keys across terminals, ensure your shell rc sets `SSH_AUTH_SOCK` consistently.

---

*A key without a passphrase is a credential on disk. A `sshd_config` reload without a held-open session is a coin flip. A `~/.ssh/config` that `ssh -G` doesn't recognize is your problem, not SSH's.*
