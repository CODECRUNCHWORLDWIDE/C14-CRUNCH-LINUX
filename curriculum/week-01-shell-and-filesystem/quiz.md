# Week 1 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 2.

---

**Q1.** Strictly speaking, "Linux" refers to:

- A) An operating system.
- B) A distribution like Ubuntu or Fedora.
- C) A kernel.
- D) A shell.

---

**Q2.** Which of these is **not** typically a separate program?

- A) `bash`
- B) `gnome-terminal`
- C) `cd`
- D) `ls`

---

**Q3.** What does `~` expand to?

- A) The root of the filesystem.
- B) The current working directory.
- C) The current user's home directory.
- D) The previous directory.

---

**Q4.** Where do system-wide configuration files live by convention?

- A) `/usr/config`
- B) `/etc`
- C) `/var/conf`
- D) `~/.config`

---

**Q5.** Which command shows the **absolute path** of an executable?

- A) `which`
- B) `where`
- C) `find`
- D) `pwd`

---

**Q6.** What does `2>&1` mean?

- A) Send file descriptor 1 to descriptor 2.
- B) Send stderr to wherever stdout currently goes.
- C) Send stdout to wherever stderr goes.
- D) Redirect both to the file named `&1`.

---

**Q7.** Globs are NOT:

- A) Wildcards.
- B) Expanded by the shell.
- C) Regular expressions.
- D) Useful for matching filenames.

---

**Q8.** Inside double quotes, which is expanded?

- A) Globs only.
- B) Variables only.
- C) Both globs and variables.
- D) Neither.

---

**Q9.** Which directory is virtual (not on disk)?

- A) `/home`
- B) `/proc`
- C) `/var`
- D) `/etc`

---

**Q10.** Your prompt ends in `#` instead of `$`. What does that signal?

- A) The command will be slow.
- B) You're in the middle of a multi-line command.
- C) You're running as **root**.
- D) Tab-completion is disabled.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **C** — the kernel. Strictly. GNU/Linux is closer to "the OS most people mean."
2. **C** — `cd` is a shell **builtin**; it doesn't fork an external process. The others are external programs.
3. **C** — `~` is the home directory. `$HOME` and `~` are equivalent.
4. **B** — `/etc`.
5. **A** — `which`. (`type` also works and is sometimes more accurate.)
6. **B** — "send stderr to wherever stdout currently goes." Order matters when combined with `>`.
7. **C** — globs are NOT regex. They look similar but have different semantics.
8. **B** — variables expand in double quotes, globs do NOT. (Single quotes expand neither.)
9. **B** — `/proc` is virtual; the kernel synthesizes its contents on read.
10. **C** — root. Pause and verify with `whoami` before pressing Enter.

</details>

If you scored 9+: move to homework. 7–8: re-read the missed lecture sections. <7: re-read Lecture 1 and 2 from the top.
