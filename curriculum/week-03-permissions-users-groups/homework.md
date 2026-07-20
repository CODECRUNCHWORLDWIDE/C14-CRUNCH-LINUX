# Week 3 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-03/homework/`.

These are practice problems between the exercises (which drilled the basics) and the mini-project (which asks you to compose freely). Treat them as fluency reps. Use a throwaway VM or container for anything touching `/etc` or user accounts.

---

## Problem 1 — Octal / symbolic fluency drill (45 min)

Build a two-column flashcard table you can read at speed. At least 20 rows. Columns: **symbolic** (e.g., `rwxr-x---`) and **octal** (e.g., `0750`).

Include at least:

- Six common base modes (`0644`, `0755`, `0600`, `0700`, `0444`, `0000`).
- Four with `setuid`/`setgid`/sticky (`4755`, `2755`, `1777`, `6755`).
- Four "almost right but wrong" cases people typo (`0764`, `0746`, `0641`, `0773`) — explain in a sentence what each one allows that the canonical version doesn't.

**Acceptance:** `homework/01-mode-table.md` with the table. Time yourself on the last five conversions: under 10 seconds each is the target.

---

## Problem 2 — Write your `umask` (45 min)

Inspect your current shell:

```bash
umask
umask -S
```

For your normal day-to-day work, decide whether `0022` (the default), `0027`, or `0077` is appropriate. Trade-offs:

- `0022`: world-readable everything you create. Convenient; not private.
- `0027`: world cannot read your files. Group can read but not write.
- `0077`: only you can read. Maximum privacy; group-shared files require explicit `chmod`.

Set the value you chose in `~/.bashrc` (or `~/.zshrc`, or wherever your shell reads on startup). Confirm it survives a new shell:

```bash
echo 'umask 0027' >> ~/.bashrc
bash -c 'umask'
```

**Acceptance:** `homework/02-umask.md` — your choice, your reasoning (3-4 sentences), the line you added, and the verification output. Include a paragraph on why a service running as you would NOT inherit this `umask` (hint: services started by systemd ignore `.bashrc`).

---

## Problem 3 — Bootstrap a user with one script (60 min)

Write `homework/03-new-user.sh`:

```bash
#!/usr/bin/env bash
# Usage: sudo ./new-user.sh USERNAME GROUP1[,GROUP2,...]

set -euo pipefail
```

The script:

1. Takes a username and a comma-separated list of supplementary groups.
2. Creates the user with a home directory and `/bin/bash` shell.
3. Creates any of the listed groups that don't exist.
4. Adds the user to the supplementary groups with `-aG`.
5. Sets a temporary password and forces it to be changed on first login (`chage -d 0 USERNAME`).
6. Refuses (cleanly, with an exit code) if the user already exists.
7. Prints a one-line summary: `Created USERNAME (uid=N) in groups: a,b,c`.

Test it inside a container:

```bash
docker run -it --rm --name c14-hw3 -v "$PWD:/work" ubuntu:24.04 bash
apt update && apt install -y sudo passwd
cd /work
./03-new-user.sh alice developers,wheel
./03-new-user.sh bob developers
./03-new-user.sh alice developers   # should fail cleanly
```

**Acceptance:** The script. A `notes.md` with the three test runs and their outputs.

---

## Problem 4 — A locked-down `sudoers.d` drop-in (45 min)

In a container, configure `/etc/sudoers.d/10-deploy` to grant a `deploy` user **only** these commands, no password:

- `systemctl restart nginx`
- `systemctl status nginx`
- `journalctl -u nginx -n 100`

**No other root commands.** `sudo ls` as `deploy` must fail.

Use `visudo -f` to edit the drop-in. Test:

```bash
useradd -m deploy
sudo -u deploy sudo -l                       # what's deploy allowed?
sudo -u deploy sudo systemctl status nginx   # should work (no password)
sudo -u deploy sudo ls /                     # should be denied
```

**Acceptance:** `homework/04-deploy-sudoers` containing the drop-in file's content, plus a `04-notes.md` with the three test commands and their outputs. Highlight: what did `sudo -l` show?

---

## Problem 5 — Using ACLs to grant cross-group read (45 min)

You have a directory `/srv/reports` owned by `manager:management` with mode `0750`. You want **everyone in the `auditors` group** to also have read access, **without adding them to `management`** (which would grant them write access).

Configure this with ACLs. Verify with `getfacl` and with `su - <auditor> -c 'ls /srv/reports/'`.

Then, ten lines down, add the requirement: **new files** created in `/srv/reports` should also be readable by `auditors`. Use a default ACL.

**Acceptance:** `homework/05-acls.md` — the commands run, the `getfacl` output, the verification test. Plus: a paragraph on what `mask::` showed in the `getfacl` output, and what it means.

---

## Problem 6 — Reflection (90 min)

`homework/06-reflection.md`, 500-700 words:

1. After this week, when you see `-rw-r-----` in `ls -l`, what do you immediately know? Walk through your mental decode.
2. Of `chmod`, `chown`, `usermod`, `visudo`, `setfacl` — which feels most dangerous in your hands right now? Why? What would you do to feel safer with it?
3. The lecture claimed: "Most 'permission denied' errors come from one of three places." Did the three-minute method work for you on Puzzle 12 (or wherever else you tried it this week)? Where did it fail?
4. Read the `sudoers(5)` man page from start to finish, even just once. Write a paragraph on what you found that surprised you. (Hint: cmnd aliases, host aliases, log_input/log_output, runas_default, the `Defaults` lines.)
5. Cite the Bash Yellow caution line at the top of your favorite lecture from this week. (Loyalty test repeats.)
6. The shared-folder challenge had requirement 4 — carol the read-only auditor. Could you do it with groups alone, or did you need ACLs? Why?

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 45 min |
| 3 | 1 h |
| 4 | 45 min |
| 5 | 45 min |
| 6 | 1.5 h |
| **Total** | **~5.5 h** |

After homework, ship the [mini-project](./mini-project/README.md).
