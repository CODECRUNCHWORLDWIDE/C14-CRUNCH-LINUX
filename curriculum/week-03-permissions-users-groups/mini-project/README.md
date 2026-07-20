# Mini-Project — A Multi-User Demo with Permission Boundaries

> Configure a Linux machine for three users collaborating on a shared codebase, with auditable permission boundaries that survive a reboot, are reproducible from one script, and reject every "but what if?" attack you try against them.

**Estimated time:** 6–7 hours, spread Thursday–Saturday.

This mini-project is the deliverable that proves Week 3 took. Anyone who finishes it can stand up a multi-user Linux environment — the unglamorous but constant work of every team-shared server. The polished version of the [challenge](../challenges/challenge-01-multi-user-shared-folder.md), with documentation, idempotent setup, and a verification harness.

---

## Deliverable

A directory in your portfolio repo `c14-week-03/mini-project/` containing:

1. `README.md` — the prose write-up, structured as the design, the policy, and the verification.
2. `setup.sh` — a single idempotent shell script that goes from a clean Ubuntu 24.04 LTS or Fedora 41 system to the fully-configured multi-user state. Re-running it on an already-set-up system must be a no-op (no errors, no double additions).
3. `verify.sh` — a test harness that runs every "should this work?" and "should this fail?" check as the appropriate user, and exits 0 iff all checks behave as expected.
4. `teardown.sh` — the inverse of `setup.sh`. Removes the users, groups, directory tree, sudoers drop-ins. Idempotent.
5. `POLICY.md` — the human-readable description of the access policy. The artifact your team would read to understand what's allowed.
6. `notes.md` — your scratch space. Not required to be polished; it's your evidence of process.

---

## The scenario

A small company — call it "Crunch Co." — needs a shared Linux box for three developers and one auditor. The roles:

- **alice** — senior dev. Read/write everywhere developers work. Can `sudo` for ops tasks (within reason).
- **bob** — junior dev. Read/write in the project tree. No `sudo`.
- **carol** — intern. Read/write in her own scratch area, read-only elsewhere in the project. No `sudo`.
- **dave** — auditor. Read-only across everything, including a `.git` directory. No `sudo`. Never writes.

The directory layout is:

```
/srv/crunchco/
├── project/         <- main codebase; devs write, auditor reads
│   ├── src/
│   ├── docs/
│   └── .git/        <- private; only devs read/write; auditor reads
├── scratch/
│   ├── alice/       <- alice writes; others read; nobody else writes
│   ├── bob/
│   └── carol/
├── secrets/         <- only alice; nobody else can even list it
└── public/          <- everyone reads; only alice writes; sticky so people can leave files
```

The policy reflects three forces in tension: **collaboration** (devs need to be able to edit each other's work), **boundaries** (carol can't break the build by accident; dave can't write anywhere), and **privacy** (some secrets are alice-only).

---

## Required policy

Your setup must enforce **every** rule below. Your `verify.sh` must test every rule.

### Membership

- **R1.** `alice`, `bob`, `carol`, `dave` exist as accounts with home directories and `/bin/bash` shells.
- **R2.** Groups exist: `developers` (alice, bob, carol), `auditors` (dave), `crunchco` (all four).
- **R3.** `alice` is in the `sudo` group (Ubuntu) or `wheel` group (Fedora); others are not.

### `/srv/crunchco/project/`

- **R4.** alice, bob, carol can all create, edit, and delete files anywhere in `project/`.
- **R5.** Files created by any developer in `project/` are group-owned by `developers`, automatically, via `setgid`.
- **R6.** dave can read every file under `project/` but cannot create, modify, or delete anything.
- **R7.** No user outside `crunchco` can read, write, or list `project/`.

### `/srv/crunchco/project/.git/`

- **R8.** alice, bob, carol can read and write in `.git/`. dave can read; he cannot write.
- **R9.** Everyone outside `developers` and `auditors` is denied entirely — they cannot even `ls /srv/crunchco/project/.git/`.

### `/srv/crunchco/scratch/`

- **R10.** Each scratch subdirectory (`scratch/alice/`, etc.) is writable only by its named owner.
- **R11.** Other developers and the auditor can read inside scratch subdirectories, but they cannot delete or modify.
- **R12.** carol cannot accidentally `rm -rf` alice's scratch (and vice versa). This is the sticky-bit / per-directory-ownership requirement.

### `/srv/crunchco/secrets/`

- **R13.** Only alice can list `secrets/`. bob, carol, and dave get "Permission denied" on `ls`.
- **R14.** alice can create, read, edit, and delete files in `secrets/`.
- **R15.** The directory exists with no readable mode for anyone except alice.

### `/srv/crunchco/public/`

- **R16.** Everyone in `crunchco` can read files in `public/`.
- **R17.** Everyone in `crunchco` can write **their own** files in `public/`.
- **R18.** Only the file's owner (or alice, or root) can delete a file — sticky bit applied.

### `sudo`

- **R19.** alice can run `(ALL:ALL) ALL` with password prompt (the `sudo`/`wheel` group membership).
- **R20.** A drop-in `/etc/sudoers.d/10-crunchco` grants the `developers` group **only** these commands without a password: `systemctl restart nginx`, `systemctl status nginx`, `journalctl -u nginx -n 100`. dave is not in `developers` so he cannot use any of these.

---

## Constraints

- **One setup script.** `setup.sh` must be the single entry point. It calls helper functions, sourced files, whatever you like, but `bash setup.sh` is the only command the grader runs.
- **Idempotent.** Running `bash setup.sh` twice in a row must produce no errors and no duplicate group additions, sudoers entries, or anything else. Use `getent passwd`, `getent group`, and `grep -q` to gate operations.
- **`set -euo pipefail` at the top.** No exceptions.
- **Verification covers every rule.** `verify.sh` runs at least one test per rule, in `su - USER -c '...'` form (or `sudo -u USER`). It exits 0 iff every test behaves as required. Print a checklist as it runs (`R1 ... ok`).
- **Teardown is clean.** After `bash teardown.sh`, `getent passwd alice` returns empty, `/srv/crunchco/` is gone, and `/etc/sudoers.d/10-crunchco` is removed.
- **No Python, no Ansible, no Puppet, no Salt.** This is the shell. The point is to be able to do this with just `useradd`, `groupadd`, `chmod`, `chown`, `setfacl`, and `visudo -cf`.
- **Works on Ubuntu 24.04 LTS AND Fedora 41.** The only distro-specific code is the sudo-group name (`sudo` vs `wheel`); guard it with `if grep -q '^ID=fedora' /etc/os-release; then SUDO_GROUP=wheel; else SUDO_GROUP=sudo; fi`.

---

## Suggested workflow

### Phase 1 — Sketch the design (30 min)

Open `POLICY.md`. Write the 20-rule list in your own words, then map each rule to **which mechanism** enforces it: standard mode bits, setgid, sticky, ACL, or sudoers. The mapping is the design.

### Phase 2 — Write `setup.sh` rule by rule (3h)

Don't try to write the whole script then test. Write the section that enforces R1-R3 (users and groups). Run it. Run it again — it should be idempotent already. Then R4-R7. Then R8-R9. And so on.

Each block in `setup.sh` should be a clearly-labeled section with a comment naming the rules it implements:

```bash
# === R4–R7: /srv/crunchco/project ===
mkdir -p /srv/crunchco/project
chgrp developers /srv/crunchco/project
chmod 2770 /srv/crunchco/project
# Dave (auditor) gets read+traverse via ACL
setfacl    -m u:dave:rX /srv/crunchco/project
setfacl -d -m u:dave:rX /srv/crunchco/project
```

### Phase 3 — Write `verify.sh` (1.5h)

For each rule, write one or more tests:

```bash
# R4: alice can write in project/
if su - alice -c 'touch /srv/crunchco/project/r4-test && rm /srv/crunchco/project/r4-test'; then
  echo "R4 ... ok"
else
  echo "R4 ... FAIL" ; FAIL=1
fi

# R6: dave cannot write in project/
if su - dave -c 'touch /srv/crunchco/project/r6-test' 2>/dev/null; then
  echo "R6 ... FAIL (dave wrote successfully!)" ; FAIL=1
  rm -f /srv/crunchco/project/r6-test
else
  echo "R6 ... ok"
fi
```

The pattern: positive tests must succeed; negative tests must fail. Both contribute to a passing run.

### Phase 4 — Write `teardown.sh` (45 min)

Reverse `setup.sh`. The order matters: remove users before groups; remove sudoers drop-in before deleting groups it references.

```bash
rm -f /etc/sudoers.d/10-crunchco
for u in alice bob carol dave; do
  if getent passwd "$u" >/dev/null; then userdel -r "$u" 2>/dev/null || true; fi
done
for g in developers auditors crunchco; do
  if getent group "$g" >/dev/null; then groupdel "$g" || true; fi
done
rm -rf /srv/crunchco
```

### Phase 5 — Write the README and POLICY (1h)

The README explains how to run it; the POLICY explains what's enforced. Both reference the 20 rules.

### Phase 6 — Adversarial testing (45 min)

Beyond the verify harness, **try to break it**. What does carol see if she runs `find /srv/crunchco -type f`? Can dave learn the names of files in `secrets/` via any side channel? Can bob `chmod` a file owned by alice? Document the results in `notes.md`.

---

## Acceptance criteria

- [ ] `bash setup.sh` runs cleanly on a fresh container of both Ubuntu 24.04 LTS and Fedora 41.
- [ ] `bash setup.sh` run twice produces no errors and no duplicate state.
- [ ] `bash verify.sh` prints a checklist of 20 rules and exits 0.
- [ ] `bash teardown.sh` returns the system to clean state; `getent passwd alice` returns nothing; `/srv/crunchco/` is gone.
- [ ] `setup.sh` uses `set -euo pipefail`.
- [ ] `POLICY.md` describes every rule in plain English.
- [ ] No Python, no config-management tools — shell only.
- [ ] A specific call-out (in README) of which rules required ACLs and why the three-tier model couldn't express them.

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Correctness of rules | 30% | All 20 rules enforced; `verify.sh` exits 0 |
| Idempotence | 15% | `setup.sh` runs twice with no errors and no duplicate state |
| Teardown | 10% | `teardown.sh` leaves no residue; the system is bootable; `userdel -r` cleaned up |
| Documentation | 15% | `POLICY.md` is readable by a non-technical stakeholder |
| Adversarial robustness | 15% | At least 3 documented adversarial tests, with diagnosis |
| Portability | 10% | Works on both Ubuntu 24.04 LTS and Fedora 41 |
| Verify-harness coverage | 5% | Each of the 20 rules has at least one explicit test |

---

## Why this matters

Every team-managed Linux server in production has a version of this setup. The companies that get it right have one script that builds the policy; the companies that get it wrong have a Google Doc that nobody can find. Permissions configured by hand drift; permissions configured by script don't.

This mini-project also previews the patterns you'll deploy in:

- **Week 5** (systemd) — services run as users with explicit groups and `umask`. You'll set up service accounts the same way.
- **Week 6** (SSH and firewalls) — `sshd` configuration, `AllowGroups`, `chroot` for sftp users.
- **C6 — Cybersecurity Crunch** — Linux hardening starts with "do you know what every account on the box can do?" If you finished this project, the answer is yes.
- **C15 — Crunch DevOps** — IaC tools (Ansible, etc.) automate this same pattern at scale. The shell script you write here is the *intent* those tools encode.

The shell script you ship this week is the muscle memory that "real" sysadmin work runs on.

---

When done: push and start [Week 4 — Shell scripting properly](../../week-04/) (the discipline week — `set -euo pipefail`, quoting, traps).
