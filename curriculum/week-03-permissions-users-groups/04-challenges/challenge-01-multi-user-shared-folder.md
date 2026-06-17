# Challenge 01 — The Multi-User Shared Folder

> **Time:** ~3 hours. **Outcome:** You can design a shared workspace for several users where collaboration is easy, accidents are hard, and the policy is auditable in `ls -l` plus `getfacl`.

This challenge is the dress rehearsal for the mini-project. The mini-project is a polished deliverable; this challenge is the messy first attempt where you discover the failure modes. Both are worth doing — the challenge first, then the mini-project as the second draft.

You will work in a throwaway VM or container. Snapshot before you start; restore after each task if you want clean state.

```bash
# Container option (fastest)
docker run -it --rm --name c14-chal1 ubuntu:24.04 bash
apt update && apt install -y sudo passwd acl
```

## The scenario

Three users — `alice`, `bob`, `carol` — collaborate on a project at `/srv/project/`. The requirements are:

1. **All three can create, read, edit, and delete files in `/srv/project/`** — within the rules below.
2. **Files created by any of them are group-readable and group-writable by the other two**, automatically, without each user remembering to `chmod`.
3. **Other users on the system cannot read or write inside `/srv/project/`** at all.
4. **`carol` can read everything but cannot modify alice's or bob's files** — she's the auditor. She can write her own files; the others can read but not delete hers.
5. **A subdirectory `/srv/project/secret/`** exists where only `alice` and `bob` have access — `carol` cannot enter or list it. `carol` should not even know what's inside.
6. **Files in `/srv/project/.git/`** are owned by all three with no read access for anyone else. (Yes, you'll be tempted to put a real git repo here. Don't actually — for the challenge, just simulate the directory layout.)

This is the kind of policy real teams need. The interesting question is: **does the three-tier model handle it, or do you need ACLs?**

---

## Task 1 — Try with the three-tier model only

Set up the users and groups:

```bash
useradd -m alice ; echo 'alice:wk3pass' | chpasswd
useradd -m bob   ; echo 'bob:wk3pass'   | chpasswd
useradd -m carol ; echo 'carol:wk3pass' | chpasswd

groupadd project
groupadd writers
groupadd readers

usermod -aG project,writers alice
usermod -aG project,writers bob
usermod -aG project,readers carol
```

Now try to satisfy requirements 1-3 with just `chown`/`chmod`/setgid:

```bash
mkdir -p /srv/project
chgrp project /srv/project
chmod 2770 /srv/project
```

Test by switching to each user and creating files:

```bash
su - alice -c 'touch /srv/project/alice1; ls -l /srv/project/'
su - bob   -c 'touch /srv/project/bob1;   ls -l /srv/project/'
su - carol -c 'touch /srv/project/carol1; ls -l /srv/project/'
```

**Predict** which `touch` calls fail. Then run them. Write down what you observed.

**Now try requirement 4** — carol-can-read-not-modify. With the current setup, she can't even create her own file (she's not in `project`). Restructure your groups to make it work.

**Acceptance:** A `setup-three-tier.sh` script and a `notes-three-tier.md` describing which requirements you got working with this model and which you couldn't. Be specific about the **first** requirement that breaks. (Hint: it's requirement 4 or 5.)

---

## Task 2 — Add ACLs to cover the gaps

For the requirements you couldn't meet with the three-tier model, use POSIX ACLs.

For requirement 4 (carol as read-only auditor on everything alice or bob creates):

```bash
# A default ACL on the directory
setfacl -d -m u:carol:rX /srv/project/

# And one on existing files
setfacl -R -m u:carol:rX /srv/project/
```

For requirement 5 (alice and bob only in `/srv/project/secret/`):

```bash
mkdir /srv/project/secret
chgrp writers /srv/project/secret
chmod 2770 /srv/project/secret

# Block carol explicitly via ACL — the default group permission already excludes her,
# but if carol is ever added to `writers`, we want a defensive zero ACL:
setfacl -m u:carol:--- /srv/project/secret
setfacl -d -m u:carol:--- /srv/project/secret
```

Test as each user:

```bash
su - alice -c 'touch /srv/project/secret/a.txt; ls /srv/project/secret'
su - bob   -c 'ls /srv/project/secret; cat /srv/project/secret/a.txt'
su - carol -c 'ls /srv/project/secret 2>&1; cat /srv/project/secret/a.txt 2>&1'
```

The first two should succeed; the third should fail with "Permission denied."

For requirement 6 (private git directory):

```bash
mkdir /srv/project/.git
chgrp project /srv/project/.git
chmod 2770 /srv/project/.git
setfacl -d -m u:carol:--- /srv/project/.git
setfacl    -m u:carol:--- /srv/project/.git
```

**Acceptance:** A `setup-with-acls.sh` script that goes from a clean state to a fully-working setup. Run it; verify each requirement with a corresponding `su -c` test command. Include the verification commands in a `verify.sh`.

---

## Task 3 — Audit your work

Run these checks and capture the output:

```bash
ls -lR /srv/project/
getfacl /srv/project/
getfacl /srv/project/secret/
getfacl /srv/project/.git/
```

For each user, what's the effective permission on each directory? Write it out:

| User | `/srv/project/` | `/srv/project/secret/` | `/srv/project/.git/` |
|------|-----------------|-------------------------|----------------------|
| alice | rwx | rwx | rwx |
| bob   | rwx | rwx | rwx |
| carol | r-x | --- | --- |

(Your actual answers may differ; that's the table to fill.)

**Acceptance:** The four `getfacl` / `ls` outputs, plus the filled-in table. Plus: ground-truth verification — run `sudo -u carol stat /srv/project/secret/ 2>&1` and confirm it says `Permission denied`.

---

## Task 4 — Stress-test the boundary

Try to break your own setup:

1. As alice, try to chmod a file carol owns. What happens? Why?
2. As carol, try to **delete** alice's file inside `/srv/project/`. What happens? **The answer depends on whether you set the sticky bit.** Test both ways.
3. As alice, create a new file inside `/srv/project/secret/`. Confirm it's group-owned by `writers`, not by `alice`. (This is the setgid bit at work.)
4. As alice, create a new subdirectory. Does it inherit the ACL defaults? (`getfacl /srv/project/newdir`.)

**Acceptance:** Four short paragraphs — one per stress test — with the command, the output, and a one-sentence diagnosis.

---

## Task 5 — Choose and defend a policy

Write `policy.md` (400-500 words):

1. Which requirements did you solve with **just** the three-tier model? Which needed ACLs?
2. Did you use the sticky bit? Why or why not? In this scenario, is "anyone can delete anyone else's file in `/srv/project/`" acceptable?
3. If you had to give an interview answer to "why are POSIX ACLs not used more?" — what would you say? (Hint: discoverability, the `mask::` confusion, NFS portability, the fact that they were added later than the rest of the model.)
4. Suggest one alternative architecture that avoids ACLs entirely — perhaps by splitting `/srv/project/` into per-user subdirectories with cross-mounts or symlinks. Trade-offs?

The point of this task is the **considered opinion**, not the code. The script is the means; the policy is the end.

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Three-tier attempt | 15% | Script runs, you correctly identify which requirements it can't meet |
| ACL solution | 30% | All six requirements met, verified by `su` tests |
| Audit table | 15% | Clear per-user effective permissions per directory; matches verification |
| Stress tests | 15% | Sticky-bit observation done correctly; setgid effect observed |
| Policy write-up | 25% | Specific, opinionated, cites the `mask::` pitfall or another real ACL gotcha |

---

## Stretch

- Replace the ACLs in Task 2 with a more elaborate group hierarchy — can you do it? What's the cost? (Hint: `secret/` requires alice + bob but not carol; `.git/` requires all three but not "other." Each is a group.)
- Add a fourth user, `dave`, who is "read-only on everything." Don't touch any existing user or file's setup; only `setfacl`.
- Make the setup survive a reboot — none of the in-memory state matters, but `chmod`, `chgrp`, `setfacl` are persistent because they live in inodes on disk. Confirm this by `umount`/`mount` of the filesystem (in a VM): are your ACLs still there?
- Read about `mount -o acl` — pre-2.6.13 Linux required explicit `acl` mount option; modern ext4 has it enabled by default. Confirm with `tune2fs -l /dev/...`.

---

The mini-project this week takes this same scenario and polishes it into a one-command-reproducible deliverable with documentation. **Do the challenge first** — the rough draft is where the lessons live. The mini-project rewards the lessons.
