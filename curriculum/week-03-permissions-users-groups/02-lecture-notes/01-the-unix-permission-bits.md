# Lecture 1 — The Unix Permission Bits

> **Duration:** ~3 hours. **Outcome:** You read `-rwxr-x---` and `drwxrwxrwt` at a glance, you convert between symbolic and octal in your head, and you can predict what `umask 022` produces without testing.

The permission model has been essentially unchanged since 7th Edition Unix in 1979. Linux inherits it, every modern Unix inherits it, and your macOS box uses the same nine-bit encoding under the hood. It is small, finite, and learnable in an afternoon. The hard part is not the model — the hard part is the muscle memory.

This lecture builds that muscle memory. Read it once at the keyboard with a scratch directory open.

## 1. The shape of `ls -l`

Open a terminal. Run this:

```bash
mkdir -p ~/c14-week-03/sandbox
cd ~/c14-week-03/sandbox
touch hello.txt
mkdir scripts
ls -l
```

You see something like:

```
-rw-r--r-- 1 alice alice    0 May 13 09:14 hello.txt
drwxr-xr-x 2 alice alice 4096 May 13 09:14 scripts
```

Every `ls -l` line has the same shape:

```
[type][owner-bits][group-bits][other-bits] [links] [owner] [group] [size] [mtime] [name]
```

Take the first ten characters apart. Position 1 is the **file type**. Positions 2-4 are the **owner permissions**. Positions 5-7 are the **group permissions**. Positions 8-10 are the **other permissions**.

```
-  rw-  r--  r--      hello.txt
^   ^    ^    ^
|   |    |    other:   r-- (read only)
|   |    group:        r-- (read only)
|   owner:             rw- (read+write)
type:                  -   (regular file)
```

The type characters you will see:

| Char | Meaning |
|------|---------|
| `-` | Regular file |
| `d` | Directory |
| `l` | Symbolic link |
| `c` | Character device (e.g., `/dev/tty`) |
| `b` | Block device (e.g., `/dev/sda`) |
| `s` | Unix-domain socket |
| `p` | Named pipe (FIFO) |

That covers everything in `/dev` and `/var`. You will recognize them on sight by Week 5.

## 2. The nine bits

The nine permission characters break into three groups of three. Each triple is the same shape: `r`, `w`, `x` — or `-` if that bit is off.

| Bit | On a regular file | On a directory |
|-----|-------------------|----------------|
| `r` | Read the file's contents | List the directory's entries (`ls`) |
| `w` | Modify the file's contents | Create / rename / delete entries inside |
| `x` | Execute as a program | Traverse — `cd` into, or resolve a path through |

The directory bits are the part that confuses people. To `ls` a directory you need `r`. To `cd` into it you need `x`. To create or delete files inside it you need `w` (on the directory) — independent of the file's own permissions. **Deleting a file you don't own can be allowed**, if you have `w` on the *containing directory*. This is the source of half of all "permission denied" surprises.

A concrete demo:

```bash
mkdir -p /tmp/perm-demo/locked
chmod 755 /tmp/perm-demo
chmod 700 /tmp/perm-demo/locked
ls -l /tmp/perm-demo
# drwx------ 2 alice alice 4096 May 13 09:20 locked
```

You can `ls /tmp/perm-demo` because you have `rx` on it. You can `cd /tmp/perm-demo/locked` and `ls` inside because you own it. Another user can `ls /tmp/perm-demo` (sees `locked` exists) but cannot `cd locked` (no `x` for them) and cannot `ls locked` (no `r` for them).

## 3. Octal — the nine bits as one number

Each triple is three bits, so it's a number 0-7.

| `rwx` | Binary | Octal |
|-------|--------|-------|
| `---` | `000`  | `0`   |
| `--x` | `001`  | `1`   |
| `-w-` | `010`  | `2`   |
| `-wx` | `011`  | `3`   |
| `r--` | `100`  | `4`   |
| `r-x` | `101`  | `5`   |
| `rw-` | `110`  | `6`   |
| `rwx` | `111`  | `7`   |

Add the bit values to compose:

- `r` is **4**, `w` is **2**, `x` is **1**.
- `rwx` = 4+2+1 = **7**.
- `r-x` = 4+0+1 = **5**.
- `rw-` = 4+2+0 = **6**.

Three triples become a three-digit octal number:

| Symbolic | Octal | Common name |
|----------|-------|-------------|
| `rwxr-xr-x` | `755` | Standard for executables and most directories |
| `rw-r--r--` | `644` | Standard for regular files |
| `rwx------` | `700` | Owner-only — `~/.ssh` |
| `rw-------` | `600` | Owner-only file — `~/.ssh/id_ed25519` |
| `rwxrwxrwx` | `777` | World-writable. Almost always wrong. |
| `rwxrwxrwt` | `1777` | World-writable with sticky bit — `/tmp` |
| `rwsr-xr-x` | `4755` | `setuid`, owner-executable — `/usr/bin/sudo`, `/usr/bin/passwd` |

You should be able to do the conversion both ways in your head by Tuesday. Drill until you can. The exercises are built around it.

## 4. `chmod` — changing permissions

`chmod` (GNU coreutils 9.4 on Ubuntu 24.04 LTS, 9.5 on Fedora 41) takes either an octal mode or a symbolic spec.

### Octal form

```bash
chmod 644 hello.txt
chmod 755 scripts
chmod 600 ~/.ssh/id_ed25519
```

The octal form is **absolute** — it sets the mode to exactly what you wrote. If you `chmod 644` on a file that was `755`, you have removed `x` even though you didn't say so. Always octal in scripts; octal is unambiguous.

### Symbolic form

```bash
chmod u+x script.sh        # add execute for owner
chmod g-w file.txt         # remove write for group
chmod o=  secrets.txt      # remove all permissions for other
chmod a+r public.txt       # add read for all (a = u+g+o)
chmod ug=rw,o=  data.txt   # set owner+group to rw, other to nothing
```

The symbolic form is **relative** (with `+`/`-`) or **absolute** (with `=`). Read it as "who, op, what":

| Who | Op | What |
|-----|----|------|
| `u` (user/owner) | `+` (add) | `r` (read) |
| `g` (group) | `-` (remove) | `w` (write) |
| `o` (other) | `=` (set exactly) | `x` (execute) |
| `a` (all = ugo) |  | `X` (execute, but only if it's a directory or already has any `x`) |

The capital `X` is genuinely useful for recursive operations:

```bash
chmod -R u=rwX,g=rX,o=  ~/some-project
```

That means: "owner read/write, plus execute on directories and existing executables; group read, plus execute likewise; other nothing." Capital `X` saves you from making every `.txt` executable when you only meant to make directories traversable.

### Recursive `chmod`

```bash
chmod -R 755 ~/c14-week-03/sandbox/scripts
```

That recurses into the tree. Two warnings:

1. `chmod -R 777` on a real directory is almost always a mistake. It removes meaningful boundaries between owner, group, and other.
2. `chmod -R` on a tree with symlinks: the symlink's mode is irrelevant (symlinks always have mode `lrwxrwxrwx`), but the **target** is what gets chmoded. If your tree contains a symlink to `/etc`, recursive `chmod` will follow it. The GNU coreutils `chmod` defaults to `--no-dereference` for symlinks themselves, but does follow them when recursing through directories. Read `man chmod` on `-H`, `-L`, `-P` before running `-R` near anything important.

**Bash Yellow caution.** The worst command in this section: `chmod -R 777 /`. Even partial — `chmod 777 /usr/bin` — neutralizes the system's `setuid` bits and unowns sensitive directories. There is no clean rollback short of reinstall or `restorecon`-equivalent. Practice in a VM.

## 5. `chown` and `chgrp` — changing ownership

```bash
# Change owner only
sudo chown bob hello.txt

# Change group only
sudo chgrp developers hello.txt

# Change both at once
sudo chown bob:developers hello.txt

# Recursive
sudo chown -R bob:developers ~bob/project
```

Two ownership entries on every file: the **owner** (a UID) and the **group** (a GID). They control which of the three permission triples applies. The owner triple applies if you are the owner. Otherwise, if you are in the file's group, the group triple applies. Otherwise the "other" triple applies. **The kernel checks in that order — and stops at the first match, regardless of which triple is more permissive.** That last point is non-obvious. If a file is `---r--r--` (octal `044`) and owned by you, you cannot read it — even though everyone else can. The owner triple matched and said "no."

To work around such a file: `chmod u+r` (you own it) or `cat` it as root.

`chown` requires root for changing the owner. `chgrp` can be run by the owner if the target group is one the owner belongs to.

## 6. `umask` — the inverse mask on new files

When you `touch newfile`, the file's mode is **not** `0666` (rw-rw-rw-, the C library default). It's whatever `0666` becomes after the `umask` is subtracted.

```bash
umask
# 0022

touch /tmp/freshfile
ls -l /tmp/freshfile
# -rw-r--r-- 1 alice alice 0 May 13 09:30 /tmp/freshfile
```

The math: `0666` (default for new files) AND NOT `0022` (the umask) = `0644`. Translation: "remove the write bit from group and other."

For new directories: `0777` AND NOT `umask`. With `umask 0022` that gives `0755`.

| `umask` | Files become | Directories become |
|---------|--------------|---------------------|
| `0000`  | `0666`       | `0777`              |
| `0022`  | `0644`       | `0755`              |
| `0027`  | `0640`       | `0750`              |
| `0077`  | `0600`       | `0700`              |
| `0277`  | `0400`       | `0500`              |

You change `umask` for the current shell with `umask 0027`. For a user, set it in `~/.bashrc` or `~/.profile`. For all users on a system, edit `/etc/login.defs` (look for `UMASK`) and `/etc/profile` or files in `/etc/profile.d/`. For services, set it in the systemd unit (`UMask=0027`) — we cover that in Week 5.

A common mistake: setting `umask 077` in your shell, then being surprised that the file you created is unreadable by the web server. Services run with their own `umask`. Your shell's `umask` only affects files **you** create.

Why `umask` exists at all: it lets administrators set a default privacy policy without changing every program. Without it, every `touch`, every `vim newfile`, every `gcc -o`, would need to know the local policy. `umask` centralizes it.

## 7. The special bits

There are three bits above the nine. Octal-wise, they live in the thousands place: `4755`, `2755`, `1755`.

### setuid — octal `4xxx`

When set on an **executable file**, processes that exec it run with the **effective UID of the file's owner**, not the invoker. `/usr/bin/sudo` is owned by root and has setuid:

```bash
ls -l /usr/bin/sudo
# -rwsr-xr-x 1 root root 277936 May 13 09:35 /usr/bin/sudo
#    ^
#    s (instead of x) means setuid+execute
```

The lowercase `s` in the owner-execute position is setuid + owner-execute. A capital `S` means setuid + **no** owner-execute (the bit is set but the file is not executable — almost always a bug).

Set it:

```bash
sudo chmod u+s some-binary
sudo chmod 4755 some-binary    # equivalent
```

`setuid` on a **shell script** is silently ignored on modern Linux. The reason is a 1980s race condition involving the script interpreter; the kernel refuses to honor setuid on `#!/...` scripts. If you need privilege escalation in a script, the modern answer is `sudo` with a tightly-scoped sudoers rule, not a setuid script.

### setgid — octal `2xxx`

Two meanings, depending on what it's set on:

- **On an executable file:** processes run with the file's GROUP as their effective GID. Used for utilities that need access to a specific group's resources (e.g., `wall` is setgid `tty` to write to all terminals).
- **On a directory:** new files created inside inherit the directory's group, regardless of the creator's primary group. This is the foundation of shared-folder workflows.

```bash
sudo mkdir /srv/shared
sudo chgrp developers /srv/shared
sudo chmod 2775 /srv/shared
ls -ld /srv/shared
# drwxrwsr-x 2 root developers 4096 May 13 09:40 /srv/shared
#       ^
#       s = setgid + group-execute
```

Now any file alice or bob (both in `developers`) creates in `/srv/shared` is group-owned by `developers`, not by `alice` or `bob` individually. The mini-project this week is built on this pattern.

### sticky bit — octal `1xxx`

On a **directory**, the sticky bit means: a file inside can only be deleted (or renamed) by the file's owner, or the directory's owner, or root. Without it, anyone with `w` on the directory can delete anyone's file. The sticky bit makes `/tmp` safe:

```bash
ls -ld /tmp
# drwxrwxrwt 22 root root 4096 May 13 09:42 /tmp
#          ^
#          t = sticky + other-execute
```

Set it:

```bash
sudo chmod 1755 /some/shared-tmp
sudo chmod +t /some/shared-tmp    # equivalent
```

The sticky bit has no useful meaning on a regular file on modern Linux. Historically it meant "keep this executable in swap" — long obsolete.

## 8. Combinations and the four-digit octal

When you write `chmod 2755`, you are setting:

| Digit | Position | What |
|-------|----------|------|
| `2`   | special  | setgid (no setuid, no sticky) |
| `7`   | owner    | rwx |
| `5`   | group    | r-x |
| `5`   | other    | r-x |

The thousands digit is the sum of: setuid (4) + setgid (2) + sticky (1). Same encoding as the others. `chmod 6755` is setuid AND setgid. `chmod 1777` is just sticky.

If you `chmod 755` (three digits), the kernel does **not** clear the special bits — `chmod` only sets what you wrote. If you want to clear all specials, write the four-digit form: `chmod 0755`.

## 9. Reading "permission denied" — the three-minute method

Most "permission denied" errors come from one of three places. When you see one:

1. **What user are you?** `id` — confirms UID, GID, and supplementary groups.
2. **What does the file say?** `ls -l <file>` — owner, group, mode.
3. **What does the parent directory say?** `ls -ld <dir>` — for `w` (delete/create) and `x` (traverse).

A worked example. You see:

```bash
$ cat /var/log/secret.log
cat: /var/log/secret.log: Permission denied
```

Step 1: `id` says you're alice, UID 1001, in groups `alice` and `sudo`. Step 2: `ls -l /var/log/secret.log` says `-rw-r----- 1 root adm 4096 May 13 secret.log`. Owner is root (you aren't), group is `adm` (you aren't a member). Other has no permissions. Denied. Step 3: was the parent traversable? `ls -ld /var/log` shows `drwxr-xr-x` — yes, `x` for other. Diagnosis confirmed: it's the file's mode, not the directory's.

Fixes (in order of safety):

- Read it as root: `sudo cat /var/log/secret.log`.
- Add yourself to the group: `sudo usermod -aG adm alice`. (Requires logout + login to take effect for new sessions.)
- Change the file's group or mode: `sudo chmod o+r /var/log/secret.log`. Almost always the wrong answer for system files — it broadens access for everyone.

Internalize the three-step method. It is the single most useful skill in this week.

## 10. Self-check

Without scrolling up, answer:

- What octal is `rwxr-x---`?
- What octal is `rw-rw----`?
- What symbolic does `750` correspond to?
- What does `chmod g+s some-dir` do?
- What does `umask 027` produce for a new file? For a new directory?
- What is the file mode of a file at `/tmp/foo` created by `touch` with `umask 022`?
- Why does setuid on `myscript.sh` do nothing?
- Why is `chmod -R 777 /` a disaster?
- What's the difference between `s` and `S` in `ls -l`?

When all nine are easy, the [permission puzzles exercise](../03-exercises/exercise-01-permission-puzzles.md) drills them at speed.

## Further reading

- **`chmod(1)` manual page:** `man chmod`. The "DESCRIPTION" and "SETTING THE FILE MODE CREATION MASK" sections.
- **`chown(1)` and `chgrp(1)`:** short reads.
- **GNU coreutils manual, "File permissions":** <https://www.gnu.org/software/coreutils/manual/html_node/File-permissions.html>
- **"Setuid Demystified" — Chen, Wagner, Dean (USENIX 2002):** the paper that explains why setuid semantics are subtle. Skim it.
