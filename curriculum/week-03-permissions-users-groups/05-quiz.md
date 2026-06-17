# Week 3 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 4.

---

**Q1.** What octal mode does `rwxr-x---` correspond to?

- A) `0640`
- B) `0750`
- C) `0755`
- D) `0710`

---

**Q2.** A file has mode `0444`. You own the file. The parent directory's mode is `0755` and you own it. What happens when you run `rm file`?

- A) `rm` exits with "Permission denied" because the file isn't writable.
- B) `rm` prompts for confirmation (because the file is not writable), and on `y` it succeeds — deletion is governed by the directory's mode.
- C) `rm` fails silently and the file is unchanged.
- D) `rm` succeeds with no prompt, because you own the file.

---

**Q3.** With `umask 0027`, a new file is created with mode:

- A) `0640`
- B) `0750`
- C) `0644`
- D) `0660`

---

**Q4.** Which of these correctly adds `alice` to the `developers` group without removing her from any other groups?

- A) `usermod -G developers alice`
- B) `usermod -aG developers alice`
- C) `groupadd alice developers`
- D) `chgrp developers alice`

---

**Q5.** What does the `s` in `-rwsr-xr-x` mean?

- A) Symlink.
- B) Sticky bit + execute for owner.
- C) `setuid` + execute for owner. The process runs as the file's owner, not the invoker.
- D) The file is shared across users.

---

**Q6.** Why is `setuid` on a `#!/bin/bash` script silently ignored on modern Linux?

- A) Bash refuses to honor `setuid` for security reasons.
- B) The kernel refuses to honor `setuid` on `#!`-interpreted scripts due to a classic race condition.
- C) `setuid` only works on ELF binaries.
- D) `setuid` works fine — the question's premise is wrong.

---

**Q7.** On Fedora 41, which group grants full sudo access by default?

- A) `sudo`
- B) `wheel`
- C) `admin`
- D) `root`

---

**Q8.** You see `-rw-rw----+` in `ls -l` output. What does the `+` mean?

- A) The file has executable bits (shorthand).
- B) The file is a hardlink.
- C) The file has extended ACL entries beyond the basic owner/group/other.
- D) The file is in a setgid directory.

---

**Q9.** Which of the following is the SAFEST way to edit `/etc/sudoers`?

- A) `sudo nano /etc/sudoers`
- B) `sudo vim /etc/sudoers`
- C) `sudo visudo`
- D) `sudo cp /etc/sudoers /etc/sudoers.bak; sudo vim /etc/sudoers`

---

**Q10.** A directory has mode `2775` and group `developers`. Alice (in `developers`) creates a new file inside. What is the group of the new file?

- A) `alice` — her primary group.
- B) `developers` — inherited from the directory because of the `setgid` (the `2` in `2775`).
- C) `root` — directories owned by `root` propagate ownership.
- D) `users` — the system default group.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **B** — `rwxr-x---` is `7 5 0` → `0750`. Owner = rwx (7), group = r-x (5), other = --- (0).
2. **B** — `rm` looks at the file's mode and prompts when it isn't writable, but the **kernel** governs delete by the **directory's** mode. With `w` and `x` on the directory, `rm` proceeds after the prompt. The file's mode is a `rm` UX nicety, not a kernel rule.
3. **A** — files default to `0666`; `0666 AND NOT 0027` = `0640`.
4. **B** — `-aG` (append to supplementary groups). `-G` alone replaces; that's the classic mistake.
5. **C** — `setuid` plus owner-execute. Capital `S` would mean "setuid set but not executable."
6. **B** — the kernel refuses, because a TOCTOU race between the kernel's permission check and the interpreter's open of the script file would otherwise allow escalation. Capabilities or `sudo` are the modern replacement.
7. **B** — Fedora uses `wheel`. Ubuntu uses `sudo`. Both are conventions enforced by `/etc/sudoers`.
8. **C** — the `+` indicates POSIX ACL entries beyond the base mode. `getfacl` shows them.
9. **C** — `visudo` locks the file and syntax-checks. The others can leave a broken file and lock you out of `sudo`.
10. **B** — the `2` in `2775` is the `setgid` bit. On a directory it makes new entries inherit the directory's group. This is the foundation of shared-team-folder setups.

</details>

If you scored 9+: move to homework. 7–8: re-read the lecture sections you missed (especially `umask` and `-aG`). <7: re-read both lectures from the top.
