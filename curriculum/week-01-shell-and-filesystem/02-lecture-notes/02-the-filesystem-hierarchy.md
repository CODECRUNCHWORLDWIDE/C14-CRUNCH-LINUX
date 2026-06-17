# Lecture 2 — The Filesystem Hierarchy

> **Duration:** ~2 hours. **Outcome:** You know what every top-level directory in a Linux system is for and why it exists, and you can predict where a given config / log / binary will live before searching.

Linux organizes its filesystem according to the **Filesystem Hierarchy Standard (FHS)**. It's not arbitrary; each directory has a job. Once you internalize the map, you can navigate any Linux machine — even one you've never seen — without `find / -name`.

## 1. The map (one diagram to print)

```
/                       ← the root of everything
├── bin/                ← essential user binaries (cp, ls, sh) — usually a symlink to /usr/bin
├── boot/               ← kernel, initramfs, bootloader. Touch carefully.
├── dev/                ← device files: /dev/sda, /dev/null, /dev/tty
├── etc/                ← system-wide config. Plain text. Editable.
├── home/               ← user home directories. /home/alice/, /home/bob/
├── lib/                ← essential shared libraries — usually symlinked into /usr/lib
├── media/              ← removable media auto-mounts: USB sticks, optical discs
├── mnt/                ← mount points for sysadmins ("mount this manually here")
├── opt/                ← optional/third-party software (Chrome, Slack, large self-contained installs)
├── proc/               ← virtual filesystem exposing kernel and process info
├── root/               ← the root user's home directory (NOT /)
├── run/                ← runtime data: pid files, sockets. Lost on reboot.
├── sbin/               ← essential system binaries (mount, fsck) — usually symlinked
├── srv/                ← service-served data (e.g., /srv/www for a web server)
├── sys/                ← virtual filesystem for kernel objects and devices
├── tmp/                ← temporary files. Cleared on reboot. World-writable.
├── usr/                ← the "user system resource" tree (most installed software lives here)
│   ├── bin/            ← most user binaries
│   ├── lib/            ← most libraries
│   ├── local/          ← locally-installed software (NOT package-manager-managed)
│   ├── share/          ← architecture-independent data (man pages, docs, images)
│   └── ...
└── var/                ← variable data: logs, caches, mail, databases
    ├── log/            ← system logs
    ├── cache/          ← non-essential caches
    ├── lib/            ← state for daemons (apt's database, postgres data, etc.)
    └── tmp/            ← temp files that survive reboot (unlike /tmp)
```

Read this twice. Then we go directory by directory.

## 2. Directory by directory

### `/etc` — config

Every system-wide configuration file. Plain text. Always.

- `/etc/passwd` — user accounts (publicly readable; passwords are NOT here, see `/etc/shadow`).
- `/etc/shadow` — hashed passwords. Root-only readable.
- `/etc/fstab` — what gets mounted at boot.
- `/etc/hosts` — local DNS overrides (`127.0.0.1 localhost`).
- `/etc/resolv.conf` — DNS resolver configuration.
- `/etc/ssh/sshd_config` — SSH server config.
- `/etc/systemd/system/*.service` — your custom systemd units.

When a guide says "edit the config," it almost always means a file under `/etc`. If you can't find a config, `grep -r "<keyword>" /etc 2>/dev/null` is the standard reflex.

### `/home`

One subdirectory per user. Yours is `/home/<username>` — but the shell variable `$HOME` is a more portable way to refer to it. The `~` character is shorthand: `cd ~`, `ls ~/Documents`, `~/.bashrc`.

Hidden files (starting with `.`) live here too — `~/.bashrc`, `~/.gitconfig`, `~/.ssh/`. These are "dotfiles," your personal configuration. Many engineers version-control their dotfiles in a public repo (the canonical "dotfiles repo" career artifact).

### `/var` — variable data

Anything that grows or changes during normal operation.

- `/var/log/` — your system logs. `/var/log/syslog` and `/var/log/auth.log` are the most-read.
- `/var/lib/` — daemon state: databases, package manager records, etc.
- `/var/cache/` — caches you can wipe without breaking anything.
- `/var/spool/` — work queues (print jobs, mail spool, cron jobs in progress).
- `/var/www/` — historically where web content lived (some distros).

If a service is "missing data" or "lost its history," look in `/var/lib/<service>` first.

### `/usr` — the bulk of installed software

The historical "user system resources" tree. Today, most binaries and libraries are here.

- `/usr/bin/` — most commands (`ls`, `git`, `python3`, `vim`).
- `/usr/local/bin/` — software you installed *outside* the package manager.
- `/usr/share/` — read-only architecture-independent data: `/usr/share/doc`, `/usr/share/man`, theme files.

The split between `/bin` and `/usr/bin` is historical. On modern distros (Ubuntu 24, Fedora) `/bin` is a symlink to `/usr/bin`. They're the same now.

### `/tmp` and `/var/tmp`

Two temporary directories. The difference:

- `/tmp` is usually cleared on reboot. Often mounted as `tmpfs` (RAM-backed) — small, fast, gone when you power off.
- `/var/tmp` survives reboots. Use this if your temp file matters for ≥1 day.

Both are world-writable with the "sticky bit" set — anyone can write, but you can only delete your own files. Never put secrets in `/tmp`.

### `/proc` — the kernel as files

A "virtual" filesystem. Not real files on disk. Each entry is the kernel reporting state.

- `/proc/cpuinfo` — CPU model and features.
- `/proc/meminfo` — memory summary.
- `/proc/<pid>/` — one directory per running process. `cat /proc/$$/status` shows your shell.
- `/proc/version` — kernel version string.

Try:

```bash
cat /proc/cpuinfo | head
cat /proc/meminfo | head
ls /proc/$$/
```

Everything is text. Everything is readable. This is the *Unix philosophy* in action.

### `/sys` — devices as files

Similar virtual filesystem, but for hardware and kernel subsystems. `/sys/class/net/` lists your network interfaces. `/sys/block/sda/` describes your disk. Less commonly touched than `/proc`.

### `/dev` — device files

Each entry represents a device.

- `/dev/null` — the bit bucket. Write anything; it goes nowhere. Read it; you get an empty stream.
- `/dev/zero` — read it, you get an infinite stream of zero bytes. Useful for benchmarks.
- `/dev/random` and `/dev/urandom` — sources of random bytes.
- `/dev/sda`, `/dev/sda1` — your first disk and its first partition.
- `/dev/tty` — the current terminal.

`echo "hello" > /dev/null` discards "hello." `cat file > /dev/null` reads a file without showing it (useful for warming caches).

### `/opt`

Optional software, usually large self-contained installs. Chrome (`/opt/google/chrome`), Slack (`/opt/slack`), some development tools live here. Package-manager-installed software does NOT generally go in `/opt`.

### `/srv`

"Service data." A web server's content might live in `/srv/www`. Less universally used than other directories; some distros prefer `/var/www`.

### `/root`

The home directory of the `root` user. **Not** the same as `/`. The most-confused pair of paths in Linux.

### `/boot`

Kernel images, initramfs, bootloader configuration. Touch only if you know exactly what you're doing.

## 3. Finding things — the instinctive map

When you wonder "where is X?", here's the mental flowchart:

| Looking for… | Try first |
|--------------|-----------|
| A command's binary | `which <cmd>` — usually `/usr/bin` or `/usr/local/bin` |
| A program's config | `/etc/<program>/` or `/etc/<program>.conf` |
| A user's settings | `~/.<program>` or `~/.config/<program>/` |
| Logs | `/var/log/<program>.log` or `journalctl -u <service>` |
| A daemon's state | `/var/lib/<program>/` |
| A package's installed files | `dpkg -L <package>` (Debian) or `rpm -ql <package>` (Red Hat) |
| A man page | `/usr/share/man/` |
| Boot config | `/boot/grub/` |
| Network config | `/etc/netplan/` (Ubuntu) or `/etc/NetworkManager/` |

This map is more valuable than memorizing commands. It's the *organizing principle* of the system.

## 4. Symbolic links

Several "essential" directories like `/bin`, `/sbin`, `/lib` are now **symbolic links** to their `/usr/*` counterparts. You can see them:

```bash
ls -l / | grep ^l
```

A symlink is a tiny file whose content is "follow me to that path." They look like normal files but `ls -l` shows them with `l` at the start of the permissions string and an `->` arrow:

```
lrwxrwxrwx 1 root root 7 May 1 14:02 /bin -> usr/bin
```

You can make your own:

```bash
ln -s /usr/share/doc/bash/INTRO ~/bash-intro
```

Now `~/bash-intro` is a symlink. Reading it actually reads `/usr/share/doc/bash/INTRO`.

Symlinks are how `python` works across versions, how dotfile-management tools function, and how containers compose filesystems. Worth understanding deeply.

## 5. Permissions in `ls -l`

The columns of `ls -l`:

```
-rw-r--r-- 1 alice users 1234 May  1 14:00 notes.txt
│└┬┘└┬┘└┬┘  │ │     │     │    │      │       │
│ │  │  │   │ │     │     │    └──────┴──────┴── modification time + name
│ │  │  │   │ │     │     └─ size in bytes
│ │  │  │   │ │     └─ group
│ │  │  │   │ └─ owner
│ │  │  │   └─ link count
│ │  │  └─ "other" permissions (everyone else)
│ │  └─ group permissions
│ └─ owner permissions
└─ file type (- file, d directory, l symlink, c char device, b block device)
```

Each rwx triplet is: **r**ead, **w**rite, e**x**ecute. `-rw-r--r--` is "owner can read+write; everyone else can only read." `-rwxr-xr-x` is "owner can do everything; others can read+execute" — typical for installed programs.

We dive into `chmod` and ACLs in Week 3.

## 6. Self-check

- Where would you look for the SSH server's configuration?
- What's the difference between `/tmp` and `/var/tmp`?
- What command tells you which directory `git` is installed in?
- `/root` is not the same as `/`. What is `/root`?
- A package is "missing its config" after install. Where do you look first?
- `ls -l` shows a file with `l` at the start. What does that mean?

If those are clear, Lecture 3 covers pipes and redirection — the next compositional skill.

## Further reading

- **FHS 3.0 official spec:** <https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html>
- **Wikipedia — Filesystem Hierarchy Standard:** <https://en.wikipedia.org/wiki/Filesystem_Hierarchy_Standard>
- **The Debian Administrator's Handbook, Ch. 5 — Packaging System:** <https://debian-handbook.info/browse/stable/packaging-system.html>
