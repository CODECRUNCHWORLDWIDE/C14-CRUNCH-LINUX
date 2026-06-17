# Week 3 — Resources

Free, public, no signup unless noted.

## Required reading

- **GNU coreutils manual** — the canonical reference for `chmod`, `chown`, `chgrp`, `id`, `umask`. The "File permissions" chapter is roughly 20 pages and worth the read:
  <https://www.gnu.org/software/coreutils/manual/coreutils.html>
- **`sudo` project documentation** — Todd C. Miller's official site. The `sudoers(5)` page is the syntax reference you will keep open:
  <https://www.sudo.ws/docs/man/>
- **`acl(5)` and `setfacl(1)` manuals** — short, dense, and authoritative:
  <https://man7.org/linux/man-pages/man5/acl.5.html>
  <https://man7.org/linux/man-pages/man1/setfacl.1.html>
- **`passwd(5)` and `shadow(5)` manuals** — the format of `/etc/passwd` and `/etc/shadow`:
  <https://man7.org/linux/man-pages/man5/passwd.5.html>
  <https://man7.org/linux/man-pages/man5/shadow.5.html>

## Books

- **"The Linux Programming Interface" — Michael Kerrisk** — chapters 8 (users and groups), 9 (process credentials), 15 (file attributes), 17 (ACLs), and 38 (writing privileged programs). The gold standard. Not free, but worth owning. The author maintains `man7.org` and most of the Linux man pages.
  <https://man7.org/tlpi/>
- **"How Linux Works" — Brian Ward (3rd ed., No Starch, 2021)** — chapters 2 and 7 cover permissions and users at the level this week targets. Beginner-friendly, terminal-honest.
- **"UNIX and Linux System Administration Handbook" — Nemeth et al. (5th ed.)** — chapter 5 on access control. The classic reference. Older but the fundamentals are unchanged.

## Cheat sheets

- **GNU coreutils `chmod` quick reference** — built into the info manual:
  <https://www.gnu.org/software/coreutils/manual/html_node/chmod-invocation.html>
- **`sudoers` quick examples** — from the official sudo project:
  <https://www.sudo.ws/docs/sudoers_quick_reference/>
- **Julia Evans' "Bite Size Linux" zine** — the permissions section is a one-page mental model:
  <https://wizardzines.com/zines/bite-size-linux/>

## Videos (free)

- **MIT 6.NULL "Missing Semester" — Security and Cryptography** — touches permissions and `setuid` at the level we cover:
  <https://missing.csail.mit.edu/2020/security/>
- **"Linux File Permissions in 6 Minutes" by Brian "Beej" Hall** — short, accurate, and uses real `ls -l` output:
  <https://www.youtube.com/results?search_query=beej+linux+permissions>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install acl sudo passwd coreutils

# Fedora
sudo dnf install acl sudo passwd coreutils
```

- `acl` — provides `getfacl` and `setfacl`. Pre-installed on Ubuntu 24.04 LTS and Fedora 41; verify with `which getfacl`.
- `sudo` — assume installed. If it isn't, you have larger questions to answer about your install.
- `passwd` — the package that ships `passwd`, `useradd`, `usermod`, `userdel`, `groupadd`, `gpasswd`, and friends. On Ubuntu this is `passwd`; on Fedora it's `shadow-utils`.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| GNU coreutils | 9.4 | 9.5 |
| User-add wrapper | `adduser` (Perl) and `useradd` (low-level) | `useradd` only (no `adduser` wrapper) |
| Default `useradd` creates home? | No (use `-m`) | Yes (default `CREATE_HOME yes` in `/etc/login.defs`) |
| Default user shell | `/bin/sh` (Dash) | `/bin/bash` |
| First-human UID | 1000 | 1000 |
| `sudo` group name | `sudo` | `wheel` |
| `/etc/sudoers.d/` | included by default | included by default |
| ACL tools | pre-installed | pre-installed |
| `umask` default | 022 (login.defs) | 022 (login.defs) |

The `sudo` vs `wheel` group split bites people who move between the two distros. On Ubuntu, `usermod -aG sudo alice` grants `sudo` access. On Fedora, the equivalent is `usermod -aG wheel alice`. Both achieve it through a line in `/etc/sudoers` (or a drop-in in `/etc/sudoers.d/`); the group name is the only difference.

## Free books and write-ups

- **The Linux Documentation Project — "User Authentication HOWTO"** — old but still accurate on PAM, `/etc/shadow`, and the account databases:
  <https://tldp.org/HOWTO/User-Authentication-HOWTO/>
- **Arch Wiki — "Users and groups"** — the most carefully-maintained free reference on the topic; not Arch-specific in its core content:
  <https://wiki.archlinux.org/title/Users_and_groups>
- **Arch Wiki — "File permissions and attributes"** — same series, same quality:
  <https://wiki.archlinux.org/title/File_permissions_and_attributes>
- **Arch Wiki — "Access Control Lists"** — short and clear:
  <https://wiki.archlinux.org/title/Access_Control_Lists>
- **Arch Wiki — "Sudo"** — by some distance the clearest sudoers reference on the open web:
  <https://wiki.archlinux.org/title/Sudo>

## Glossary

| Term | Definition |
|------|------------|
| **UID** | User ID — the integer that identifies a user. Stored in `/etc/passwd`. Root is `0`. |
| **GID** | Group ID — the integer that identifies a group. Stored in `/etc/group`. |
| **EUID** | Effective UID — the UID the kernel uses for permission checks. Differs from UID when `setuid` is in play. |
| **Primary group** | The single group a user belongs to "by default." Field 4 of `/etc/passwd`. New files are owned by this group unless overridden. |
| **Supplementary group** | Additional groups a user belongs to. Listed in `/etc/group`. A user has one primary and many supplementary. |
| **Permission bits** | The nine bits encoding owner / group / other × read / write / execute. |
| **Special bits** | The three bits above the nine: setuid (4), setgid (2), sticky (1). |
| **setuid** | When set on an executable, the process runs with the EUID of the file's owner — not the invoker. |
| **setgid** | When set on an executable: same, for group. When set on a directory: new files inherit the directory's group. |
| **Sticky bit** | When set on a directory: only the file's owner (or root) can delete files in it. The reason `/tmp` works. |
| **`umask`** | The bits *removed* from default permissions on file creation. `022` is the typical default. |
| **ACL** | Access Control List — per-user / per-group additions on top of the nine-bit model. POSIX ACLs are the Linux flavor. |
| **`sudo`** | Runs a command as another user (root, by default) per `/etc/sudoers` policy. |
| **`visudo`** | The only sane way to edit `/etc/sudoers`. Locks the file, syntax-checks before save. |

---

*Broken link? Open an issue.*
