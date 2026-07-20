# Exercise 01 — Twelve Permission Puzzles

**Time:** ~1.5 hours. **Goal:** Build the reflex of reading `ls -l` modes at a glance and converting symbolic <-> octal without thinking.

For each puzzle: write down the answer, then verify on your machine. Several puzzles ask you to predict — predict first, run second. Don't peek at the shell before committing to a guess.

You will need a scratch directory and a shell on Ubuntu 24.04 LTS or Fedora 41. GNU coreutils 9.4+ assumed.

```bash
mkdir -p ~/c14-week-03/puzzles
cd ~/c14-week-03/puzzles
```

---

## Puzzle 1 — Read modes (symbolic to octal)

Convert each symbolic mode to four-digit octal:

1. `rwxr-xr-x`
2. `rw-r--r--`
3. `rwx------`
4. `rwxrwxrwx`
5. `rwsr-xr-x`  (note the `s`)
6. `rwxrwxrwt`  (note the `t`)
7. `rw-r-----`
8. `---r--r--`

**Acceptance:** A two-column list. Verify your answers with `stat -c '%a %A' <file>` for files you can construct.

---

## Puzzle 2 — Read modes (octal to symbolic)

Convert each octal to symbolic:

1. `0755`
2. `0644`
3. `0600`
4. `2770`
5. `4755`
6. `1777`
7. `6755`
8. `0400`

**Acceptance:** Same as above; verify with a file you `chmod` to that mode.

---

## Puzzle 3 — Make `hello.sh` executable

Create a script `hello.sh` containing `#!/bin/bash\necho hello`. Make it executable only by you, readable by everyone, and writable by no one but you.

**Hint:** That's `0744` (or `u=rwx,g=r,o=r`). Verify with `ls -l` and `./hello.sh`.

**Acceptance:** The mode line, plus output of `./hello.sh`.

---

## Puzzle 4 — Predict `umask`

For each `umask` value, write the resulting mode for **(a) a new file** and **(b) a new directory**:

1. `umask 0000`
2. `umask 0022`
3. `umask 0027`
4. `umask 0077`
5. `umask 0026`
6. `umask 0007`

**Hint:** Files default to `0666`, directories to `0777`. Subtract the `umask` bitwise (AND NOT).

**Acceptance:** A 3-column table (`umask`, file mode, directory mode). Then verify two of the rows: `umask 0027; touch x; mkdir y; ls -l x y`.

---

## Puzzle 5 — Restrict and unrestrict

You have a file `secret.txt` with mode `0644`. Write the **shortest symbolic `chmod`** to make it readable only by the owner.

Then write the inverse — restore it to `0644` — in symbolic form.

**Acceptance:** Two `chmod` commands, plus `ls -l` before and after each.

---

## Puzzle 6 — The "can't delete the file" puzzle

In a scratch directory, create a file owned by you with mode `0444`:

```bash
touch protected.txt
chmod 444 protected.txt
```

Try to delete it:

```bash
rm protected.txt
```

The behavior differs depending on whether you're in an interactive shell. **Predict** what happens. Then run it.

**Hint:** `rm` looks at the file's mode and may prompt; the kernel looks at the **directory's** mode. The kernel decides.

**Acceptance:** A paragraph: did `rm` prompt? Did it succeed? Why? What's the role of the directory's mode here vs the file's mode?

---

## Puzzle 7 — The `x` bit on a directory

Create two directories. In one, leave the default mode (probably `0755`). In the other, remove the `x` bit for "other":

```bash
mkdir reach
mkdir noreach
chmod o-x noreach
```

As yourself, `cd noreach`. Does it work? Now ask a second user (or, if alone, use `sudo -u nobody`) to do the same. **Predict** before running.

```bash
sudo -u nobody ls reach
sudo -u nobody ls noreach
sudo -u nobody cd noreach  # this won't actually work because cd is a shell builtin and `sudo -u nobody cd` exits immediately
sudo -u nobody sh -c 'cd noreach && ls'
```

**Acceptance:** A short table showing what each command did, and a one-sentence diagnosis of why `o-x` blocked the `cd`.

---

## Puzzle 8 — Two ways to be denied

Construct two files, both unreadable to you, by **two different mechanisms**:

1. A file you own where you removed your own `r` bit.
2. A file owned by another user (or root) where the "other" bits don't include `r`.

For each, run `cat <file>` and capture the **exact** error message. Are they identical?

**Hint:** Use `sudo install -o root -m 600 /etc/hostname /tmp/p8.txt` for case 2.

**Acceptance:** Two `cat` invocations with their error output. Plus: explain why both produce the same "Permission denied" — what does the kernel know that user-facing tools don't?

---

## Puzzle 9 — setgid on a directory

Create a directory `shared/`. Make it `chown root:users` (use `sudo` or pick a group you're in) and `chmod 2775`:

```bash
sudo groupadd -f wk3shared
sudo usermod -aG wk3shared $USER     # log out and back in afterwards
mkdir shared
sudo chgrp wk3shared shared
sudo chmod 2775 shared
ls -ld shared
```

Now (after re-login so your shell sees the new group), `touch shared/file1`. What's the group of `shared/file1`?

**Predict** first. Then verify.

**Acceptance:** `ls -l shared/file1` output, plus a sentence on why the group is what it is.

---

## Puzzle 10 — The four-digit `chmod` trap

Set a file's mode to `4755`, then run `chmod 755` (three digits). Does the `setuid` bit survive?

```bash
sudo touch /tmp/p10
sudo chmod 4755 /tmp/p10
ls -l /tmp/p10
sudo chmod 755 /tmp/p10
ls -l /tmp/p10
```

**Acceptance:** Two `ls -l` outputs. A sentence on what `chmod 755` does to the high bits.

---

## Puzzle 11 — Reading `stat`

`stat` gives you a lot more than `ls -l`. For a file you own, run:

```bash
stat ~/c14-week-03/puzzles/hello.sh
```

Identify in the output:

- The numeric (octal) mode.
- The owner and group.
- The "Access," "Modify," and "Change" times. Which is touched by `chmod`?

**Acceptance:** The output, with the relevant fields highlighted (in a markdown file: use `**bold**`).

---

## Puzzle 12 — Diagnose a permission denied

You see this:

```
$ vim /var/log/auth.log
"/var/log/auth.log" [Permission Denied]
```

Run the three-minute diagnostic from the lecture:

1. `id` — what are you?
2. `ls -l /var/log/auth.log` — owner, group, mode?
3. `ls -ld /var/log` — parent dir mode?

Write a paragraph that explains, given what you found, exactly *why* you can't open the file in `vim`. Propose three different remedies (in order of safety / sanity).

**Acceptance:** The three commands' outputs, plus the diagnosis paragraph, plus the three remedies — with a one-sentence assessment of each remedy's tradeoffs.

---

## Reflection (5 min)

At the bottom of `answers.md`:

- Which puzzle changed your mental model the most?
- Was octal-to-symbolic harder or easier than symbolic-to-octal?
- After these twelve, can you read `drwxrwsr-x` and `-rwsr-xr-x` at a glance? If not, redo Puzzles 1 and 2.

---

When done, push and move on to [exercise-02-add-users-and-groups.md](./exercise-02-add-users-and-groups.md).
