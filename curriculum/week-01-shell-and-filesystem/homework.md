# Week 1 — Homework

Six problems, ~6 hours total. Commit each to your portfolio.

---

## Problem 1 — Install Linux somewhere (45 min)

Make a Linux environment you can sustain through C14 and beyond.

**Acceptance:**

- A working Linux environment of your choice (native, VM, WSL2, VPS).
- A screenshot of `uname -a` and `lsb_release -a` (or `cat /etc/os-release`) committed to `setup.md`.
- A description of which option you chose and why.

---

## Problem 2 — Tour your filesystem (60 min)

Run these and write what you observe in `tour.md`:

```bash
ls /
ls /etc | head -20
ls /var
ls /var/log
cat /etc/os-release
cat /proc/cpuinfo | head
cat /proc/meminfo | head
df -h
du -sh /var /usr /etc /home
```

**Acceptance:**

- `tour.md` contains the output of each command (first ~20 lines per).
- Three sentences of "things I noticed" — e.g., the size of `/usr` vs `/var`, what's in `/etc`, what `/proc` looks like.

---

## Problem 3 — Pipeline puzzle (60 min)

Write one pipeline that answers: **"What are the 10 most common words longer than 5 characters in `/usr/share/dict/words`?"**

(If that file doesn't exist on your distro, install `wamerican` or use any large text file you have.)

**Acceptance:**

- A one-line pipeline in `pipeline.md` with output.
- A line-by-line decode: what does each stage do?
- A reflection: "I did not know `<command>` could do that."

---

## Problem 4 — `vi` survival drill (45 min)

In `vi` (or `vim`), perform each of these without quitting between steps:

1. Open a new file: `vi notes-vi.md`.
2. Enter INSERT mode (`i`). Type: "Vim survival.\nLine two."
3. Press Esc.
4. Save without quitting: `:w`.
5. Search for "two": `/two` then Enter.
6. Replace "Line" with "LINE" everywhere: `:%s/Line/LINE/g`.
7. Save and quit: `:wq`.

**Acceptance:**

- The resulting file committed.
- A `vi-cheatsheet.md` in your own words covering: enter insert mode, exit insert mode, save, save+quit, force quit, search, undo, redo, copy line, paste.

---

## Problem 5 — Your first dotfile (45 min)

Add three things to `~/.bashrc` (or `~/.zshrc`):

1. An alias: `alias ll='ls -la'`.
2. A custom prompt that includes the time: `PS1='\t \u@\h:\w\$ '`.
3. An environment variable: `export EDITOR=vim` (or `nano` if you prefer).

Open a new terminal, verify each works.

**Acceptance:**

- A `~/.bashrc.notes.md` showing the three additions and what they do.
- A screenshot or terminal-copy showing the new prompt.

---

## Problem 6 — Reflection (45 min)

`reflection.md`, 300-400 words:

1. Which command in the 50-tour was new to you?
2. Which directory in the filesystem hierarchy did you not know about?
3. What's still confusing? Be specific — "redirection" is too broad; "the difference between `2>&1` placement" is useful.
4. What habit do you want to build into Week 2?

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 1 h |
| 3 | 1 h |
| 4 | 45 min |
| 5 | 45 min |
| 6 | 45 min |
| **Total** | **~5 h** |

After homework, ship the [mini-project](./mini-project/README.md).
