# Exercise 02 — ProxyJump and the Bastion Pattern

**Time:** ~2 hours. **Goal:** Stand up a two-host topology — one **bastion** that is reachable from your laptop and one **private host** that is reachable only from the bastion. Configure `~/.ssh/config` so `ssh private` (a single command, no manual hops) works. Confirm `scp` and `rsync` work through the same tunnel. Understand why `ProxyJump` is strictly better than the old `ProxyCommand ssh -W` pattern and why it is strictly better than `ssh -A` (agent forwarding) for this case.

The exercise needs **two** target hosts that can talk to each other but where the second is not directly reachable from your laptop. Three options:

- **Option A (cheap and real).** Spin up two $5/mo VPSes from any provider, put both in the same private network (Hetzner, DigitalOcean, Vultr all support this), give only one a public IP. ~$10/month for one week.
- **Option B (local).** Two VMs on your laptop (UTM, VirtualBox, KVM). NAT one of them. The "bastion" gets the host's port-forward on TCP 22; the "private" host does not.
- **Option C (simulated).** One real VPS (the "bastion") and inside it, a containerized "private" host (`docker run -d --name private -p 127.0.0.1:2222:22 some-image`). Awkward but works.

Pick one. We'll write the exercise as if you're on Option A; the others differ in setup but not in the SSH-level work.

Verify prerequisites on your laptop:

```bash
ssh -V                              # OpenSSH_9.6 or newer (need 7.3+ for ProxyJump)
```

Set up scratch:

```bash
mkdir -p ~/c14-week-06/exercises/02
cd ~/c14-week-06/exercises/02
```

In the rest of this exercise, **`bastion`** means the host with a public IP; **`private`** means the host without one. Substitute your real hostnames / IPs.

---

## Part 1 — Set up the two hosts (30 min)

### Step 1.1 — Make sure both hosts have your public key

You did exercise 01 against one host. Do the same setup against both:

```bash
# On your laptop:
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@bastion.example.com
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@private.example.com   # via the bastion if needed
```

If the private host is unreachable from your laptop (the whole point of the exercise), `ssh-copy-id user@private...` won't work. Instead:

```bash
# SSH to the bastion
ssh bastion

# On the bastion, scp the key to the private host
scp ~/.ssh/id_ed25519.pub user@private:/tmp/
ssh user@private "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat /tmp/id_ed25519.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm /tmp/id_ed25519.pub"
exit
```

(Note: this temporarily uses the bastion's local SSH client. The bastion does **not** need your private key — it just needs the public key to be readable, which it is via your home directory if you have one on the bastion, or by pasting the public key into the `scp` line.)

For a clean cut, an even better approach: include your public key in the **provisioning** step for the private host (every VPS provider supports this).

### Step 1.2 — Confirm both work in the naive form

From your laptop:

```bash
ssh bastion                         # should succeed
exit

ssh user@private.example.com        # if your provider's network setup allows this directly, it might
                                    # succeed. If it times out, that's what we want — proves the private
                                    # host is not internet-reachable.
```

On Option A (private network), `ssh user@private.example.com` should time out. On Options B/C, you may need to confirm that the private host is unreachable from your laptop *outside* the bastion.

### Step 1.3 — Confirm the two hosts can talk

```bash
ssh bastion
user@bastion:~$ ssh user@private    # the bastion can reach the private host
user@private:~$ exit
user@bastion:~$ exit
```

If this works, the topology is right.

---

## Part 2 — Naive multi-hop (10 min)

Before showing the right way, do the wrong way to feel the pain.

### Step 2.1 — Hop manually

```bash
# Terminal 1
ssh bastion
user@bastion:~$ ssh user@private
user@private:~$ uname -a
```

Two prompts. Two passwords (well — no, you used keys, so no passwords, but you do have to invoke `ssh` twice). Two known_hosts entries to maintain.

### Step 2.2 — Try to scp through

```bash
# On your laptop:
scp some-file.txt user@private:/tmp/
# ssh: Could not resolve hostname private: Temporary failure in name resolution
# OR:
# ssh: connect to host private port 22: Network is unreachable
```

There is no way to `scp` directly from your laptop to a host you can't `ssh` to. You'd have to `scp` to the bastion, SSH to the bastion, then `scp` again from the bastion to the private host. Tedious.

---

## Part 3 — `ProxyJump` (30 min)

### Step 3.1 — Add the stanzas

Edit `~/.ssh/config`:

```
Host bastion
    HostName bastion.example.com
    User user
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes

Host private
    HostName private.example.com         # the private DNS name OR the private IP
    User user
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ProxyJump bastion
```

Save.

### Step 3.2 — One-command access

```bash
ssh private
# Welcome to Ubuntu 24.04.2 LTS ...
user@private:~$
```

One command, one prompt. Behind the scenes:

- `ssh` connects to `bastion`, authenticates with your key.
- `ssh` asks the bastion to forward a TCP connection to `private:22`.
- `ssh` does a **second** SSH handshake end-to-end with `private`, again with your key.

The bastion is a TCP forwarder; it sees encrypted bytes only. It cannot decrypt the second session.

Run `ssh -G private` to confirm the directives resolved as you expected:

```bash
ssh -G private | grep -i -E 'hostname|proxyjump|identityfile'
# hostname private.example.com
# identityfile ~/.ssh/id_ed25519
# proxyjump bastion
```

### Step 3.3 — `scp` and `rsync` work through the tunnel

```bash
# On your laptop:
scp some-file.txt private:/tmp/
# 100% transferred via the ProxyJump.

rsync -avz ~/c14-week-06/ private:/tmp/c14-test/
# 1,234 bytes  received via the ProxyJump.

ssh private "ls /tmp/c14-test/"
```

`scp` and `rsync` both honor `~/.ssh/config`. Adding `ProxyJump` once made all three (ssh, scp, rsync) work.

### Step 3.4 — Test from the command line without config

For the historical record, the same thing without the config:

```bash
ssh -J user@bastion.example.com user@private.example.com
# Works, but you typed all that.
```

`-J` is the command-line form of `ProxyJump`. The config form is preferable; the CLI form is for one-off uses.

---

## Part 4 — Bastion `sshd_config` adjustments (20 min)

The bastion has a slightly different role than a leaf host. It needs to **permit TCP forwarding** (or `ProxyJump` won't work) but should otherwise be as locked down as any other server.

### Step 4.1 — Adjust `/etc/ssh/sshd_config.d/99-hardened.conf` on the bastion

```bash
ssh bastion
sudoedit /etc/ssh/sshd_config.d/99-hardened.conf
```

Change `AllowTcpForwarding no` (from exercise 01) to `AllowTcpForwarding yes`:

```
AllowTcpForwarding yes
PermitOpen any                       # explicitly the default; documents intent
GatewayPorts no
```

Optionally, restrict to the private host(s) you actually need:

```
AllowTcpForwarding yes
PermitOpen private.example.com:22    # only permit forwarding to this exact host:port
PermitOpen 10.0.0.10:22              # or use a private IP
```

`PermitOpen` is an allow-list of `host:port` destinations for `-L`, `-W`, and `ProxyJump`. Without it, the bastion will happily forward to anywhere — that's the default. Restricting is defense-in-depth.

Validate and reload:

```bash
sudo sshd -t
sudo systemctl reload sshd
```

### Step 4.2 — Leaf hosts should NOT permit forwarding

On the **private** host:

```bash
# In the SSH session (which is via ProxyJump):
sudoedit /etc/ssh/sshd_config.d/99-hardened.conf
```

```
AllowTcpForwarding no
```

The private host is a leaf; nothing should be tunneling through it.

```bash
sudo sshd -t
sudo systemctl reload sshd
exit
```

Test from your laptop that ProxyJump still works:

```bash
ssh private
```

If it does, you're done.

---

## Part 5 — Multi-hop and chained bastions (15 min, optional)

For completeness, `ProxyJump` supports chains:

```
Host inner
    HostName inner.example.com
    User user
    IdentityFile ~/.ssh/id_ed25519
    ProxyJump bastion-east,bastion-west
```

`ssh inner` would hop through `bastion-east`, then through `bastion-west`, then connect to `inner`. Latency stacks; latency is roughly the sum of the per-hop RTTs.

You probably don't have three bastions. Skip this part if you don't; do not provision more hosts just for this.

---

## Part 6 — Why not just `ssh -A`? (15 min reading + reflection)

Agent forwarding is the "older" answer to the bastion problem. With `ForwardAgent yes`:

```
Host bastion
    HostName bastion.example.com
    User user
    ForwardAgent yes
```

You SSH to the bastion. From the bastion, you SSH to `private`. The second `ssh` invocation uses **your laptop's agent** (forwarded over the bastion connection) to authenticate. It works.

The risk: **any process on the bastion running as your user (or as root) can use your forwarded agent for as long as you're connected**. A compromised bastion gets to authenticate to `private` as you. The compromise is undetectable from your laptop.

`ProxyJump` does not forward your agent. Your laptop authenticates to `private` directly (over the tunnel the bastion provided). The bastion never sees your agent; the bastion is just a TCP forwarder.

**Rule:** `ProxyJump` for "I want to reach private hosts through a bastion." `ForwardAgent` only for "I need a command on the remote that itself uses SSH (e.g., `git clone` of a private repo on a build server)."

### Reflection prompt

Write 3-4 sentences in `notes.md` (Part 7): when, in your workflows, would you reach for agent forwarding rather than `ProxyJump`? Be specific.

---

## Part 7 — Document and commit (10 min)

Save your `~/.ssh/config` (sanitized):

```bash
cp ~/.ssh/config ~/c14-week-06/exercises/02/ssh-config-redacted.txt
# Replace real hostnames with bastion.example.com, private.example.com
```

Capture the resolved config:

```bash
ssh -G private > ~/c14-week-06/exercises/02/ssh-G-private.txt
ssh -G bastion > ~/c14-week-06/exercises/02/ssh-G-bastion.txt
```

Capture an `ssh -vvv` trace of a successful `ssh private`:

```bash
ssh -vvv private 2> ~/c14-week-06/exercises/02/ssh-vvv-trace.txt
exit
# The trace shows both handshakes — laptop-to-bastion, then laptop-to-private through the tunnel.
```

Write `notes.md`:

```markdown
# Exercise 02 — Notes

## Topology
- Bastion: <hostname> (<public IP>)
- Private: <hostname> (<private IP>)
- (sketch of the network arrangement, 2-3 lines)

## What I built
- ~/.ssh/config with bastion and private stanzas.
- Bastion: AllowTcpForwarding yes (with optional PermitOpen restriction)
- Private: AllowTcpForwarding no (defense in depth)

## What ProxyJump does differently from ForwardAgent
- (3-4 sentences)

## scp and rsync verification
- (paste the output of a successful scp through the tunnel)

## A surprise
- (one paragraph)
```

Commit to your portfolio repo.

---

## Acceptance criteria

- `ssh private` succeeds in one command, no manual hops.
- `ssh -G private` shows `proxyjump bastion`.
- `scp some-file private:/tmp/` succeeds.
- `rsync -avz ./dir/ private:/tmp/dest/` succeeds.
- On the bastion: `sudo sshd -T | grep -i allowtcpforwarding` reports `yes`.
- On the private host: `sudo sshd -T | grep -i allowtcpforwarding` reports `no`.
- (Optional) `PermitOpen` on the bastion restricts forwarding to the private host's `:22` only.

---

## Common failure modes

- **`ssh private` hangs forever.**
  The bastion can't reach the private host. `ssh bastion` then `ssh user@private` from there to test. If the second `ssh` fails too, fix that first.
- **`channel 0: open failed: administratively prohibited: open failed` from the bastion.**
  The bastion's `sshd_config` has `AllowTcpForwarding no` (or `PermitOpen` doesn't include the private host). Reload with the right value.
- **`Permission denied (publickey)` connecting to private through the bastion.**
  The private host doesn't have your public key. Distribute it (see step 1.1).
- **`ProxyJump` ignored — SSH connects directly to private and times out.**
  Probably a typo in the `Host` block (Wrong indentation? Wrong Host pattern?). Run `ssh -G private` and look at the `proxyjump` line; if it's `none`, the config didn't apply.
- **Slow first-hop authentication, then fast second.**
  Likely DNS / reverse DNS on the bastion. Set `UseDNS no` on the bastion's `sshd_config`. Subsequent connections cache.
- **`scp` works but `rsync` doesn't.**
  `rsync` uses `ssh` under the hood; the same config should work. If not, try `rsync -e "ssh -F ~/.ssh/config"` explicitly.

---

*A bastion is a host whose only job is to be the SSH entry point. The leaves hide behind it. The agent stays on your laptop. Every directive on the bastion is "for everybody who comes through me"; every directive on the leaf is "for whoever I'm letting in."*
