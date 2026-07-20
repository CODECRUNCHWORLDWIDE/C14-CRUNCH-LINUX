# Exercise 03 — `setuid` Investigation

**Time:** ~1.5 hours. **Goal:** Build an inventory of every `setuid` and `setgid` binary on a real Linux system, and be able to explain why each one is privileged.

Most Linux compromises that involve local privilege escalation use a `setuid` binary as their lever — either a known bug in `sudo`, `pkexec`, or `passwd`, or a third-party `setuid` binary that nobody audited. Knowing what's on your system, and being unsurprised by every entry, is the first defense.

Do this on Ubuntu 24.04 LTS or Fedora 41. A fresh install is best; a system you actually use is even more informative because you'll find the third-party `setuid` bits you forgot you installed.

---

## Task 1 — Find every `setuid` file

```bash
sudo find / -xdev -type f -perm /4000 -ls 2>/dev/null
```

Three flags worth knowing:

- `-xdev`: don't cross filesystem boundaries (skip `/proc`, `/sys`, mounts).
- `-perm /4000`: match files where **any of** the setuid bit is set. (`/` means "any of"; `-` would mean "all of".)
- `-ls`: like running `ls -l` on each match. Includes owner, group, mode, size.
- `2>/dev/null`: silence the `Permission denied` noise on directories you can't read.

**Acceptance:** The full output. On a fresh Ubuntu 24.04 LTS, expect roughly 15-25 entries. On a fresh Fedora 41, similar.

---

## Task 2 — Find every `setgid` file

```bash
sudo find / -xdev -type f -perm /2000 -ls 2>/dev/null
```

Same shape, different bit.

**Acceptance:** The full output.

---

## Task 3 — Classify each `setuid` binary

For each `setuid` file in your Task 1 output, write a one-line "what is this for?" classification. Use one of:

- **Auth / login:** modifies the user database (`/etc/passwd`, `/etc/shadow`). Examples: `passwd`, `chsh`, `chfn`.
- **Privilege elevation:** runs commands as another user. Examples: `sudo`, `pkexec`, `su`.
- **Mount / network:** modifies system state without full root. Examples: `ping` (historical), `mount`, `umount`, `fusermount`.
- **Scheduling:** runs jobs in the user's name. Examples: `at`, `crontab`.
- **Hardware / display:** access to consoles or devices. Examples: `Xorg.wrap`, `dbus-daemon-launch-helper`.
- **Mystery — investigate:** anything you don't recognize. **Look it up.**

Suggested format for your answer:

```markdown
| Path | Owner | Mode | Purpose |
|------|-------|------|---------|
| /usr/bin/sudo | root | 4755 | Privilege elevation per /etc/sudoers |
| /usr/bin/passwd | root | 4755 | Auth — modifies /etc/shadow |
| ... | ... | ... | ... |
```

**Acceptance:** A complete table covering every line from Task 1. No "Mystery — investigate" rows in the final submission — every binary must be classified.

---

## Task 4 — Note distro differences

If you can, run Task 1 on both Ubuntu 24.04 LTS and Fedora 41 (a container is enough). Compare:

```bash
# Ubuntu
docker run --rm ubuntu:24.04 sh -c 'find / -xdev -type f -perm /4000 -ls 2>/dev/null' > ubuntu-setuid.txt

# Fedora
docker run --rm fedora:41 sh -c 'find / -xdev -type f -perm /4000 -ls 2>/dev/null' > fedora-setuid.txt

diff <(awk '{print $NF}' ubuntu-setuid.txt | sort) \
     <(awk '{print $NF}' fedora-setuid.txt | sort)
```

**Acceptance:** The `diff` output. Pick one path that's `setuid` on one distro but not the other, and write a sentence on why. (Hint: Fedora has historically been more aggressive about removing `setuid` in favor of `pkexec`/capabilities. Ubuntu has been more conservative.)

---

## Task 5 — The "should this still be `setuid`?" question

For three binaries from your Task 3 table, ask: **is `setuid` still the right mechanism, or could this be done with capabilities or `pkexec`?**

Candidates worth examining:

- `/usr/bin/ping` — historically `setuid` to open raw sockets; on modern Ubuntu, it usually isn't anymore (the `cap_net_raw+ep` capability is used). Check yours: `getcap /usr/bin/ping`.
- `/usr/bin/mount` — still `setuid` on most distros. Why? Could it be `pkexec`?
- `/usr/bin/passwd` — still `setuid root`. Could it be otherwise?

**Acceptance:** Three short paragraphs, one per binary. Each names the mechanism the binary uses, the alternative, and the tradeoff. There is no single right answer — the lesson is being able to weigh `setuid` vs capabilities vs `polkit`/`pkexec`.

---

## Task 6 — Find files in `/home` that shouldn't be `setuid`

Most `setuid` binaries live in `/usr/bin`, `/usr/sbin`, `/usr/libexec`. **A `setuid` binary in `/home`, `/tmp`, `/var/tmp`, or a user's directory is almost always suspicious** — either a tool you installed manually, or an attacker's foothold.

```bash
sudo find /home /tmp /var/tmp -xdev -type f -perm /4000 -ls 2>/dev/null
```

**Acceptance:** The output. On a clean machine this is empty. If yours has entries, investigate each one — there should be no surprises by the time you finish this task.

---

## Reflection (5 min)

At the bottom of `answers.md`:

- Which `setuid` binary surprised you the most — that you had no idea was `setuid`?
- Which `setuid` binary did you classify as "Mystery" the longest? What did you eventually find?
- If you were tightening this system, what would you take `setuid` off, and what would you replace it with?

---

## Optional follow-ups

- Read `man 7 capabilities` to learn what replaces `setuid` in modern systems.
- Read about **`polkit`** (formerly PolicyKit) — the framework that `pkexec` and most GUI privilege prompts use. It's a userspace replacement for many `setuid` use cases.
- For a real audit: run `lynis audit system` and read the section on `setuid` files. Lynis is in `apt`/`dnf`.

---

When done, push. You've completed Week 3's exercises. On to the [challenge](../challenges/challenge-01-multi-user-shared-folder.md) and the [mini-project](../mini-project/README.md).
