# Week 3 — Permissions, Users, Groups, ACLs

> *Every file on a Unix system answers three questions before you touch it: who owns me, who's allowed to read me, and who's allowed to change me. By Sunday, you read `-rwxr-x---` like you read English.*

Welcome to **Week 3 of C14 · Crunch Linux**. The first two weeks were about moving through the system: navigating the filesystem and shaping text through pipes. This week we step into the part of Unix that decides whether you're *allowed* to do those things at all. The permission bits, the user and group model, `sudo`, ACLs, and the special bits — `setuid`, `setgid`, the sticky bit — that bend the rules in named, controlled ways.

This is also the first week where a typo can lock you out of your own machine. We will take that seriously. Every destructive command in this week's notes is paired with its inverse, and we will write down rollback steps before we touch anything important. Bash Yellow caution applies.

## Learning objectives

By the end of this week, you will be able to:

- **Read** any `ls -l` line by hand: the file type, owner permissions, group permissions, other permissions, owner, group, and the special bits.
- **Convert** between symbolic (`rwxr-x---`) and octal (`750`) permissions in your head, both directions, without consulting a chart.
- **Use** `chmod`, `chown`, and `chgrp` correctly — including the recursive variants (`-R`) and the symbolic forms (`u+x`, `g-w`, `o=`, `a+r`).
- **Understand** `umask` — what it is, where it's set, why a `umask` of `022` makes new files `644` and new directories `755`, and how to change it for a session, a user, or a service.
- **Apply** the three special bits — `setuid`, `setgid`, sticky — and recognize them in `ls -l` output (`-rwsr-xr-x`, `-rwxr-sr-x`, `drwxrwxrwt`). Know which uses are legitimate and which are red flags.
- **Manage** users and groups: `useradd`, `usermod`, `userdel`, `groupadd`, `gpasswd`, `passwd`. Distinguish primary group from supplementary groups. Read `/etc/passwd`, `/etc/group`, `/etc/shadow`, and `/etc/gshadow`.
- **Configure** `sudo` via `/etc/sudoers` and `/etc/sudoers.d/` — using `visudo`, never a raw editor. Understand the difference between `ALL=(ALL:ALL) ALL` and `ALL=(ALL) NOPASSWD:`.
- **Reach** for POSIX ACLs (`getfacl`, `setfacl`) when the three-tier permission model can't express what you need, and recognize the `+` in `ls -l` that says ACLs are present.
- **Diagnose** a "permission denied" error in under three minutes by reading the failure, the file's mode, the user's groups, and (when needed) the parent directory's mode.

## Prerequisites

- **Weeks 1 and 2 of C14** completed. You can navigate, pipe, and read text.
- A working Ubuntu 24.04 LTS or Fedora 41 environment with `sudo` access. We assume GNU coreutils 9.4+ on Ubuntu 24.04 LTS and 9.5+ on Fedora 41. `chmod --version` will confirm.
- A scratch directory you don't mind breaking — e.g., `~/c14-week-03/sandbox/`. Do **not** practice these commands on `/etc` or on files you care about.

## Topics covered

- The three-tier permission model: owner, group, other. Read, write, execute. Nine bits.
- Symbolic notation (`rwxr-x---`) and octal notation (`750`). The mapping is mechanical; we drill until it's automatic.
- File-type characters in `ls -l`: `-` regular file, `d` directory, `l` symlink, `c` char device, `b` block device, `s` socket, `p` named pipe.
- `chmod` in both symbolic (`chmod g+w file`) and octal (`chmod 644 file`) forms — and why scripts should prefer octal.
- `chown` and `chgrp` — including the colon form (`chown user:group file`) and recursive (`-R`) traversal. The footgun of `chown -R` on a symlink tree.
- `umask` — the inverse mask applied to the default `0666` (files) and `0777` (directories). Where it's set: `/etc/login.defs`, `/etc/profile`, `~/.bashrc`, `~/.profile`.
- The special bits: `setuid` (4xxx), `setgid` (2xxx), sticky (1xxx). What each does on files vs directories. Why `setuid` on a shell script is ignored on modern Linux.
- The user model: `/etc/passwd` (account database), `/etc/shadow` (password hashes — root-only), `/etc/group`, `/etc/gshadow`. UIDs, GIDs. System accounts (UID < 1000 on Debian/Ubuntu; < 1000 on Fedora as well since systemd standardization) vs human accounts.
- User management: `useradd` vs `adduser` (Debian convention vs the low-level tool), `usermod -aG groupname username` (the `-a` matters — without it, you wipe supplementary groups), `userdel -r` (the `-r` removes the home directory).
- Group management: `groupadd`, `gpasswd`, `newgrp`. Primary group (one) vs supplementary groups (many).
- `sudo`: `/etc/sudoers`, `/etc/sudoers.d/`, `visudo`, the syntax. `sudo -i` vs `sudo -s` vs `sudo su -`. `NOPASSWD` and when it's legitimate.
- POSIX ACLs: `getfacl`, `setfacl`. The `+` indicator. When ACLs beat group-mangling, and when they don't.
- The `id` command, the `groups` command, and reading "who am I, really?" — including how `newgrp` and `sg` create subshells with a different primary group.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Permission bits lecture + puzzles              |    3h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Tuesday   | `umask`, special bits, octal drills            |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Wednesday | Users / groups / `sudo` lecture                |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Thursday  | ACLs + setuid investigation; group challenge   |    0h    |    1h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Diagnose-permission-denied drills + homework   |    0h    |    1.5h   |     0h     |    0.5h   |   2h     |     1h       |    0h      |     5h      |
| Saturday  | Mini-project (multi-user shared workspace)     |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                              |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                                | **6h**   | **8.5h**  | **4h**     | **3h**    | **6h**   | **7h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Manuals, books, and the GNU coreutils citations |
| [lecture-notes/01-the-unix-permission-bits.md](./lecture-notes/01-the-unix-permission-bits.md) | The nine bits, `umask`, special bits, `chmod`/`chown` |
| [lecture-notes/02-users-groups-sudo-acls.md](./lecture-notes/02-users-groups-sudo-acls.md) | Account databases, group management, `sudo`, ACLs |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-permission-puzzles.md](./exercises/exercise-01-permission-puzzles.md) | Twelve permission puzzles — read, convert, predict |
| [exercises/exercise-02-add-users-and-groups.md](./exercises/exercise-02-add-users-and-groups.md) | Hands-on user/group lifecycle on a throwaway VM |
| [exercises/exercise-03-setuid-investigation.md](./exercises/exercise-03-setuid-investigation.md) | Audit `setuid` binaries on a real system; explain each |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-multi-user-shared-folder.md](./challenges/challenge-01-multi-user-shared-folder.md) | Build a `setgid` shared folder where three users collaborate |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | Configure a multi-user demo with appropriate permission boundaries |

## A note on which distro and which coreutils

Permissions are POSIX, but the tooling around them varies:

```bash
# Which chmod is this?
chmod --version | head -1
# Ubuntu 24.04 LTS:    chmod (GNU coreutils) 9.4
# Fedora 41:           chmod (GNU coreutils) 9.5
# macOS:               chmod: illegal option -- -    (BSD; no --version flag)
```

On both Linux distros we target, `chmod`, `chown`, `chgrp`, `useradd`, `groupadd`, `getfacl`, `setfacl` behave identically. Where this week's content depends on coreutils 9.x specifics, we cite the version. On macOS the BSD tools differ — most notably, `chmod` has different recursive-symlink semantics. We flag the cases.

For ACL tools (`getfacl`, `setfacl`): on Ubuntu they ship in the `acl` package and are pre-installed since 22.04. On Fedora they're in `acl` and pre-installed since Fedora 38. Verify with `which getfacl` before relying on them.

## Stretch goals

- Read **the `chmod(1)` manual page** from end to end. It's short. The "Setting the file mode creation mask" section is worth careful reading.
- Read **the `sudoers(5)` manual page** until you stop being scared of it. The syntax looks arcane; the underlying grammar is small.
- Skim **the kernel documentation on capabilities** — `man 7 capabilities`. We don't cover capabilities in depth this week (they belong to C6 · Cybersecurity Crunch), but knowing they exist clarifies why `setuid` is the old-school answer and capabilities are the modern one.
- If you have time: read the original **"Setuid Demystified"** paper (Chen, Wagner, Dean, USENIX 2002). It's still the clearest writeup of why `setuid` semantics are subtle.

## Bash Yellow caution

This week contains commands that can:

- Lock you out of `sudo` (broken `/etc/sudoers`).
- Lock you out of your account (broken shell in `/etc/passwd`).
- Make a directory tree unreadable to its owner (bad recursive `chmod`).
- Make `/usr/bin/sudo` non-`setuid` and therefore useless (recursive `chmod` on `/usr/bin`).

Every lecture and exercise that touches these areas tells you the rollback. **Read the rollback before you run the command.** When in doubt, run it in a VM snapshot or a container — `docker run -it --rm ubuntu:24.04 bash` is a five-second sandbox.

## Up next

[Week 4 — Shell scripting properly](../week-04/) — once your multi-user demo is committed and your machine is still bootable.

---

*If you find errors, please open an issue or PR.*
