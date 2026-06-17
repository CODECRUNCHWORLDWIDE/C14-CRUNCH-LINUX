# Exercise 02 — Add Users and Groups

**Time:** ~2 hours. **Goal:** Walk the full user/group lifecycle hands-on, in a throwaway environment, so you've made every mistake once before you make one on a real server.

This exercise needs root and **must run in a throwaway VM or container**. A clean Ubuntu 24.04 LTS or Fedora 41 image is ideal. Two zero-cost options:

```bash
# Option A: a container with /sbin available
docker run -it --rm --name c14-wk3 ubuntu:24.04 bash
# inside the container:
apt update && apt install -y sudo passwd

# Option B: a Multipass VM (Ubuntu only)
multipass launch 24.04 --name c14-wk3
multipass shell c14-wk3
```

Take a snapshot or commit your container before starting Task 7 — it's destructive on purpose.

---

## Task 1 — Inspect the current state

Before you change anything, audit what's there:

```bash
wc -l /etc/passwd /etc/group /etc/shadow
awk -F: '$3 >= 1000 { print $1, $3 }' /etc/passwd
awk -F: '$3 < 1000 { print $1, $3 }' /etc/passwd | head -20
```

**Acceptance:** Three sections in your answer file:

1. How many accounts in `/etc/passwd`? How many groups in `/etc/group`?
2. Which accounts have UID >= 1000? (These are the "human" accounts on Debian/Ubuntu and Fedora.)
3. Pick three system accounts (UID < 1000) and look up — from their shell field — whether they're meant for login. (`/usr/sbin/nologin` and `/bin/false` mean "no login.")

---

## Task 2 — Create three users

Create users `alice`, `bob`, and `carol` with home directories and a real shell:

```bash
useradd -m -s /bin/bash alice
useradd -m -s /bin/bash bob
useradd -m -s /bin/bash carol

# Set passwords (in real life: do this interactively)
echo 'alice:wk3pass-alice' | chpasswd
echo 'bob:wk3pass-bob'     | chpasswd
echo 'carol:wk3pass-carol' | chpasswd
```

`chpasswd` reads `user:password` pairs from stdin. It's the scriptable equivalent of `passwd`. **Do not use this on real systems** — passwords show up in shell history.

Verify:

```bash
tail -3 /etc/passwd
ls -ld /home/alice /home/bob /home/carol
```

**Acceptance:** The three `tail` lines, plus the three home-directory listings. Note which UIDs they got.

---

## Task 3 — Create a shared group

Create a group `developers`. Then add `alice` and `bob` to it. Leave `carol` out.

```bash
groupadd developers
usermod -aG developers alice
usermod -aG developers bob
```

Verify:

```bash
getent group developers
id alice
id bob
id carol
```

**Acceptance:** The `getent` output (which shows the member list), plus the three `id` outputs. Confirm that `developers` appears in alice and bob's group lists but not carol's.

---

## Task 4 — The `-aG` vs `-G` mistake (do it once)

Run **the wrong command** to feel the consequence:

```bash
usermod -G testgroup1 alice    # WRONG: no -a, no testgroup1 yet
groupadd testgroup1
usermod -G testgroup1 alice    # WRONG: missing the -a
id alice
```

What happened to alice's supplementary group memberships?

Fix it:

```bash
usermod -aG developers alice
id alice
```

**Acceptance:** Three `id alice` outputs — before, after the broken command, after the fix. Write a sentence on why `-G` without `-a` is dangerous.

---

## Task 5 — A shared setgid directory

Create `/srv/team` owned by `root:developers`, mode `2775`:

```bash
mkdir -p /srv/team
chgrp developers /srv/team
chmod 2775 /srv/team
ls -ld /srv/team
```

The `s` in the group-execute position confirms setgid is on.

Now switch to alice and create a file:

```bash
su - alice
cd /srv/team
touch alice-was-here.txt
ls -l alice-was-here.txt
exit
```

**Predict** the group of `alice-was-here.txt` before running `ls -l`. Then verify.

**Acceptance:** The mode of `/srv/team`, the `ls -l` of `alice-was-here.txt`, and a one-sentence explanation of why the group is `developers` rather than `alice`.

---

## Task 6 — Grant `sudo` to one user

Add `alice` to the appropriate sudo group for your distro:

- **Ubuntu 24.04 LTS:** `usermod -aG sudo alice`
- **Fedora 41:** `usermod -aG wheel alice`

Test:

```bash
su - alice
sudo -l
exit
```

**Acceptance:** The `sudo -l` output for alice. Confirm she is allowed to run `(ALL : ALL) ALL`.

---

## Task 7 — Lock and unlock an account

Lock bob's account:

```bash
usermod -L bob
grep '^bob:' /etc/shadow
```

The shadow line should now start with `bob:!` — the `!` prefix blocks password auth.

Try to login as bob (e.g., from another terminal or `su - bob` from root — note that `su` from root doesn't prompt for a password, so this isn't a perfect test). On a real system, an interactive login as bob would now fail.

Unlock:

```bash
usermod -U bob
grep '^bob:' /etc/shadow
```

**Acceptance:** Both `grep` outputs. A sentence on the role of the `!` prefix.

---

## Task 8 — Delete a user, keep their files

Delete carol but keep her home directory:

```bash
userdel carol
ls -ld /home/carol
stat /home/carol | grep Uid
```

The home directory should still exist, owned by a UID with no name in `/etc/passwd`. `ls -l` will show the bare UID.

**Acceptance:** The `ls -ld` output (showing the home dir still there but unowned), plus the `stat` line showing the orphan UID. Then: clean up:

```bash
rm -rf /home/carol
```

---

## Task 9 — Delete a user, remove everything

Delete bob and his home directory in one shot:

```bash
userdel -r bob
ls -ld /home/bob 2>&1
```

The `-r` flag removes the home directory and mail spool.

**Acceptance:** The `ls -ld` failure (no such file) and the absence of bob from `/etc/passwd` (`grep '^bob:' /etc/passwd`).

---

## Task 10 — Audit who is in which group

Write a one-line pipeline that lists every supplementary group and its members. Build on `awk` from Week 2:

```bash
awk -F: '$4 != "" { print $1, ":", $4 }' /etc/group
```

(That's the simple version. For "all groups, even those with no members," drop the `$4 != ""` filter.)

**Acceptance:** The output of your pipeline, plus a one-sentence note on whether **primary** group memberships appear in this output. (They don't — primary groups are in `/etc/passwd` field 4, not `/etc/group`. That's a classic gotcha.)

---

## Reflection (5 min)

At the bottom of `answers.md`:

- Which task was the closest to "yes, this is how real systems get configured"?
- Where would you reach for `adduser` (the Debian wrapper) over `useradd`, and where would you not? Note that Fedora has no `adduser`.
- What would you change about your `useradd` invocations to make them idempotent (safe to run twice)?

---

## Cleanup

Exit the container or VM. If using Docker:

```bash
exit
docker rm c14-wk3  # auto-removed if you used --rm
```

If using Multipass:

```bash
multipass delete c14-wk3
multipass purge
```

The whole exercise leaves no trace on your host. That is the point.

---

When done, push and move on to [exercise-03-setuid-investigation.md](./exercise-03-setuid-investigation.md).
