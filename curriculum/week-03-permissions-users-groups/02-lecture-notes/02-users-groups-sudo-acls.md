# Lecture 2 — Users, Groups, `sudo`, ACLs

> **Duration:** ~2 hours. **Outcome:** You manage users and groups without consulting `man` for every flag, you write `/etc/sudoers` rules that grant exactly what you intend, and you reach for POSIX ACLs only when the three-tier model genuinely can't express the policy.

The nine permission bits are a 1979 design. They scale to two-party access (owner, group) plus a fallback (other) and stop there. Real systems have more than two stakeholders. The Unix answer was: **manage who is in which group, carefully**, and use the bits to express coarse policy. The Linux answer, from the mid-2000s on, is **POSIX ACLs** for the cases the group model can't express — but you should reach for them last, after you've tried groups properly.

This lecture is about the **who** of permissions: the user and group model, the account databases, `sudo`, and ACLs.

## 1. Users and groups — the kernel's view

Every process the kernel runs has a **UID** and a **GID** — both integers — plus a list of **supplementary GIDs**. When the process tries to read a file, the kernel does the permission check we covered in Lecture 1, using those numbers and the file's owner UID, group GID, and mode.

That is the whole model at the kernel level. **Names** — "alice," "developers" — are a userspace convention. The kernel deals in numbers.

```bash
id
# uid=1001(alice) gid=1001(alice) groups=1001(alice),27(sudo),100(users)
```

The mapping from name to number lives in two text files: `/etc/passwd` (for users) and `/etc/group` (for groups). The kernel doesn't read these — `glibc`'s NSS (Name Service Switch) does, in userspace, on behalf of every program that asks "what's the name for UID 1001?"

## 2. `/etc/passwd` — the account database

One account per line. Seven colon-separated fields:

```
alice:x:1001:1001:Alice Smith,,,:/home/alice:/bin/bash
```

| Field | Name | Meaning |
|-------|------|---------|
| 1 | login name | What you type at a login prompt |
| 2 | password placeholder | Always `x` on modern systems — the real hash is in `/etc/shadow` |
| 3 | UID | This user's UID |
| 4 | GID | This user's **primary** group GID |
| 5 | GECOS | Comment field. Historically "full name, office, work phone, home phone." Now: usually just the full name, often with trailing commas. |
| 6 | home directory | Absolute path |
| 7 | login shell | Absolute path to the shell — `/bin/bash`, `/usr/sbin/nologin` for service accounts |

`/etc/passwd` is **world-readable**. That is by design — every `ls -l` needs to map UIDs to names. It contains no secrets.

The password hash used to be in field 2 (Unix 1970s-80s). When CPUs got fast enough to brute-force the hashes, the hashes moved to `/etc/shadow`, root-readable only.

## 3. `/etc/shadow` — the password hashes

```bash
sudo head -2 /etc/shadow
# root:!:19580:0:99999:7:::
# alice:$y$j9T$abc.../...:19582:0:99999:7:::
```

Nine colon-separated fields:

| Field | Name | Meaning |
|-------|------|---------|
| 1 | login name | Joins this row to `/etc/passwd` |
| 2 | password hash | `$<algo>$<salt>$<hash>`. Or `!`/`*` for "no login." Or `!` prefix for "account locked." |
| 3 | last password change | Days since 1970-01-01 |
| 4 | minimum age | Min days between password changes |
| 5 | maximum age | Days password is valid |
| 6 | warn period | Days before expiry to warn user |
| 7 | inactive period | Days after expiry before account locked |
| 8 | expire date | Days since 1970-01-01 at which account becomes invalid |
| 9 | reserved | Unused |

Algorithm prefixes you'll see in field 2: `$y$` (yescrypt — Fedora 41 default), `$6$` (SHA-512 — Ubuntu 24.04 LTS default), `$2y$` (bcrypt), `$argon2id$` (some 2025+ systems). Older `$1$` (MD5) should not exist on systems you set up now.

`/etc/shadow` is **mode 640, owned by root:shadow**. `cat /etc/shadow` as a normal user fails. That's the point.

## 4. `/etc/group` and `/etc/gshadow`

`/etc/group`, world-readable, four colon-separated fields:

```
developers:x:1100:alice,bob,carol
```

| Field | Meaning |
|-------|---------|
| 1 | group name |
| 2 | password placeholder (rarely used; `x`) |
| 3 | GID |
| 4 | comma-separated supplementary members |

A user's **primary group** is field 4 of their `/etc/passwd` line — it is **not** repeated in `/etc/group`'s member list. Their supplementary groups appear in `/etc/group` lines.

`/etc/gshadow` exists for the rare case of group passwords. You will almost never edit it.

## 5. Creating users — `useradd` vs `adduser`

Two tools, depending on distro convention:

- **`useradd`** — low-level. Same on Ubuntu 24.04 LTS and Fedora 41. Does the minimum.
- **`adduser`** — Perl wrapper, Debian/Ubuntu only. Prompts interactively, creates home dir, sets shell. Friendlier defaults. Not present on Fedora.

The portable approach is `useradd` with explicit flags:

```bash
# Create alice with a home directory, bash shell, and primary group "alice"
sudo useradd --create-home --shell /bin/bash alice

# Equivalent short form
sudo useradd -m -s /bin/bash alice

# Set her password
sudo passwd alice
```

Important defaults to know:

- `-m` / `--create-home`: create `/home/alice` and copy `/etc/skel/.` into it. **Required on Ubuntu**, default on Fedora — set `CREATE_HOME yes` in `/etc/login.defs` to match Fedora's behavior on Ubuntu.
- `-s` / `--shell`: login shell. If you omit it, you get whatever `/etc/default/useradd` says — `/bin/sh` on Ubuntu.
- `-g` / `--gid`: primary group. If omitted, `useradd` creates a new group with the same name as the user (USERGROUPS_ENAB on most modern distros).
- `-G` / `--groups`: comma-separated supplementary groups. **This replaces** the user's supplementary groups when used with `usermod`; on `useradd` for a fresh user it's fine.
- `-u` / `--uid`: explicit UID. Useful for matching UIDs across systems (e.g., NFS).

## 6. Modifying users — `usermod`

```bash
# Add alice to the developers group, keeping her existing supplementary groups
sudo usermod -aG developers alice

# Change alice's login shell
sudo usermod -s /bin/zsh alice

# Lock alice's account (prepends ! to the shadow hash)
sudo usermod -L alice

# Unlock alice's account
sudo usermod -U alice
```

**The `-a` in `-aG` is load-bearing.** Without it, `usermod -G developers alice` *replaces* alice's supplementary groups with just `developers` — she loses `sudo`, she loses every other group. Always type `-aG`, not `-G`. (The mnemonic: `a` for "append.")

`usermod` changes do **not** affect existing logged-in sessions. The user has to log out and back in for new group membership to be visible to processes she starts. `id` in her existing shell will still show the old groups. This trips up everyone the first time.

## 7. Deleting users — `userdel`

```bash
# Delete alice. Keep her home directory.
sudo userdel alice

# Delete alice AND remove her home directory and mail spool.
sudo userdel -r alice
```

`userdel -r` is destructive. Take a backup if there's any chance the home dir contains things you'll regret losing.

`userdel` will refuse to delete a user with running processes unless you pass `-f`. **Don't pass `-f` carelessly** — those processes don't go away; they become orphans owned by a deleted UID and can be confusing to clean up.

## 8. Groups — `groupadd`, `gpasswd`, `newgrp`

```bash
# Create a group
sudo groupadd developers

# Create a group with a specific GID
sudo groupadd --gid 1100 developers

# Add alice to developers
sudo gpasswd -a alice developers
# or, equivalently:
sudo usermod -aG developers alice

# Remove alice from developers
sudo gpasswd -d alice developers

# Delete a group
sudo groupdel developers
```

`gpasswd -a` is the single-operation alternative to `usermod -aG`. Use whichever you remember. The result is identical: a name added to field 4 of the relevant `/etc/group` line.

`newgrp <group>` and `sg <group> -c '<cmd>'` start a subshell with the named group as the **primary** group temporarily. Useful when a setgid directory needs files created with a specific group. Modern setgid directories make this less necessary, but the commands exist.

## 9. `sudo` — temporary, audited privilege elevation

`sudo` (Todd Miller's project, ubiquitous since the early 2000s) lets a user run a command as another user — usually root — per a policy in `/etc/sudoers`. The policy controls **who** can run **what** as **whom**, with or without a password.

### Always edit `/etc/sudoers` with `visudo`

```bash
sudo visudo
```

`visudo` locks the file (only one editor at a time), then syntax-checks before saving. If the syntax is bad, it refuses to save and offers to re-edit. **Editing `/etc/sudoers` with a raw editor and saving a broken file locks you out of `sudo`** — and if you set a root password, that's your recovery; if not, you're booting single-user.

Drop-in files in `/etc/sudoers.d/` are the modern pattern:

```bash
sudo visudo -f /etc/sudoers.d/10-developers
```

Files in `/etc/sudoers.d/` are included by the main file (`#includedir /etc/sudoers.d` near the bottom). Names with dots are skipped — `10-developers.bak` is ignored. Mode must be `0440` (root:root); `visudo -f` enforces this.

### The sudoers syntax

Lines look like:

```
USER  HOST=(RUNAS:RUNAS_GROUP)  TAG: COMMAND
```

Examples:

```
# Grant alice full root access, with password prompt
alice ALL=(ALL:ALL) ALL

# Grant the wheel group full root access (Fedora's default)
%wheel ALL=(ALL:ALL) ALL

# Grant the sudo group full root access (Ubuntu's default)
%sudo ALL=(ALL:ALL) ALL

# Grant alice the ability to run systemctl restart nginx, no password
alice ALL=(root) NOPASSWD: /bin/systemctl restart nginx

# Grant the deployers group three specific commands, no password
%deployers ALL=(root) NOPASSWD: /usr/bin/apt update, /usr/bin/apt -y upgrade, /bin/systemctl restart nginx
```

The `%` prefix means "group." `ALL=(ALL:ALL)` means "from any host, run as any user and any group." `NOPASSWD:` means no password is required for the listed commands.

### `NOPASSWD` is for automation, not convenience

The most-misused sudoers feature is `NOPASSWD: ALL`. Granting it to your own user "so I don't have to type my password" turns every shell injection in any program you run into root code execution. The password prompt is your last line of defense against your own bashrc.

Legitimate uses:

- A deployment user that runs one specific, audited command.
- A monitoring agent that reads a specific file via `cat /var/log/...`.

Illegitimate uses:

- "I'm tired of typing my password."

### `sudo -i` vs `sudo -s` vs `sudo su -`

| Command | What it does |
|---------|--------------|
| `sudo cmd` | Run one command as root, then return |
| `sudo -s` | Start a root shell, with **your** environment |
| `sudo -i` | Start a root login shell, with **root's** environment (reads root's `.bashrc`, `cd`s to `/root`) |
| `sudo su -` | Same idea as `sudo -i`, via `su`. The hyphen makes it a login shell. |

Prefer `sudo -i` when you want "be root for a while." It gives you a clean, root-configured shell with no surprises from your own dotfiles.

### Reading the sudoers log

`sudo` logs every invocation. On Ubuntu, `/var/log/auth.log`. On Fedora, `journalctl _COMM=sudo`. Lines look like:

```
May 13 09:55:01 host sudo:    alice : TTY=pts/0 ; PWD=/home/alice ; USER=root ; COMMAND=/bin/cat /etc/shadow
```

`sudo -l` shows the current user what they're allowed to run:

```bash
sudo -l
# User alice may run the following commands on host:
#     (ALL : ALL) ALL
```

That's the first thing to run when you inherit a server. It tells you, exactly, what your `sudo` policy is.

## 10. POSIX ACLs — when groups aren't enough

The three-tier model — owner, one group, other — can't express:

- "Alice and Bob can read this file. Carol cannot. Dave can write it."
- "Everyone in `developers` can read. Alice specifically can also write, even though she isn't in `developers`."

These need either (a) re-engineering the group structure or (b) ACLs.

### Reading ACLs — `getfacl`

```bash
getfacl /srv/shared/notes.txt
# # file: srv/shared/notes.txt
# # owner: alice
# # group: developers
# user::rw-
# user:bob:rw-
# group::r--
# group:auditors:r--
# mask::rw-
# other::---
```

The base owner/group/other lines look like `chmod` output. Then come **named** entries: `user:bob:rw-` grants bob read+write directly, on top of his group memberships. `group:auditors:r--` grants the `auditors` group read access even though `auditors` is not the file's primary group.

The `mask::` line is the maximum permission any named entry can have. Setting `mask::r--` would silently reduce `user:bob:rw-` to read-only. This is the most-confusing ACL feature; read `man acl` carefully.

A file with ACLs shows a `+` at the end of its mode in `ls -l`:

```bash
ls -l /srv/shared/notes.txt
# -rw-rw----+ 1 alice developers 1024 May 13 10:00 /srv/shared/notes.txt
#          ^
#          + indicates ACLs present
```

### Setting ACLs — `setfacl`

```bash
# Give bob read+write on a specific file
sudo setfacl -m u:bob:rw notes.txt

# Give the auditors group read-only
sudo setfacl -m g:auditors:r notes.txt

# Remove a specific entry
sudo setfacl -x u:bob notes.txt

# Remove all named ACL entries (revert to plain mode)
sudo setfacl -b notes.txt

# Recursive
sudo setfacl -R -m u:bob:rwX /srv/shared/
```

The capital `X` again — execute only on directories and existing executables. The recursive variant is `-R`.

### Default ACLs — for directories

A directory can carry a **default ACL** that new entries inside inherit:

```bash
sudo setfacl -d -m g:developers:rwX /srv/shared/
```

`-d` means "default." Now any file or subdirectory created inside `/srv/shared/` starts with `group:developers:rwX` baked in. This is the ACL alternative to setgid — it gives finer control (you can grant specific named groups, not just one) at the cost of complexity.

### When to use ACLs

The honest rule:

1. **First, try groups.** Create a group, add the users, set the directory setgid. The three-tier model with thoughtful groups solves 90% of real cases.
2. **If two stakeholders need overlapping-but-not-identical access**, ACLs are the right tool.
3. **If you find yourself with more than a half-dozen ACL entries per file**, you've reinvented file-level RBAC badly. Reach for a real access-control system (LDAP groups, Kerberos, or move the data into a proper application).

## 11. The "who am I, really?" cheat sheet

```bash
id                          # current user, primary group, supplementary groups
id -u                       # just the UID
id -g                       # just the primary GID
id -G                       # all GIDs, space-separated
id -un                      # current username (same as `whoami`)
groups                      # group names
whoami                      # current effective username
who                         # who is logged in to this machine
w                           # who is logged in and what they're doing
last -n 10                  # most recent logins (from /var/log/wtmp)
```

`whoami` answers "who does the kernel think I am right now?" — useful inside `sudo` and inside scripts. `id` is the comprehensive answer; reach for it first.

## 12. Common failure modes — annotated

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `sudo: command not found` | Either `sudo` isn't installed, or your `PATH` doesn't include `/usr/bin` | `/usr/bin/sudo` directly; check `PATH` |
| `alice is not in the sudoers file` | alice's user/group isn't in `/etc/sudoers` or `/etc/sudoers.d/*` | `visudo` and add her |
| `usermod -aG` change "didn't apply" | The user's existing shell still has the old group list | Log out and back in |
| New files in a shared dir owned by the wrong group | Directory isn't setgid | `chmod g+s /srv/shared` |
| `+` in `ls -l` and unexpected access | ACL is granting more than the mode suggests | `getfacl` to see what's there |
| `chmod` won't change a file | Filesystem mounted with `noexec` / `ro`, or you don't own it | `mount | grep <fs>`; `chown` first |
| `useradd` succeeds, login fails | No password set, or shadow line is `!` | `passwd <user>` |

## 13. Self-check

Without scrolling up:

- What's the difference between primary and supplementary groups?
- What's the GECOS field?
- Where do password hashes live, and what's the mode of that file?
- Why does `usermod -G developers alice` lose alice's other groups?
- What's `visudo` and why is it the only safe way to edit `/etc/sudoers`?
- What does the `+` at the end of a mode in `ls -l` mean?
- Name two legitimate uses of `NOPASSWD:`.
- What's the difference between `sudo -s` and `sudo -i`?
- Which Fedora group is the equivalent of Ubuntu's `sudo` group?
- When should you reach for ACLs, and when should you reach for groups?

When all ten are easy, the [user/group exercise](../03-exercises/exercise-02-add-users-and-groups.md) drills them hands-on.

## Further reading

- **`useradd(8)`, `usermod(8)`, `userdel(8)`:** the canonical manuals.
- **`sudoers(5)`:** the syntax reference. Long; worth a careful read.
- **`acl(5)`, `getfacl(1)`, `setfacl(1)`:** the ACL trio.
- **Arch Wiki on Users and Groups:** <https://wiki.archlinux.org/title/Users_and_groups>
- **Arch Wiki on Sudo:** <https://wiki.archlinux.org/title/Sudo>
- **Michael Kerrisk, "The Linux Programming Interface", chapters 8, 9, 17, 38** — the textbook treatment.
