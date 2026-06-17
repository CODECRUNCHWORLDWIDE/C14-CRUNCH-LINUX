# Exercise 01 — Ten `awk` Puzzles

**Time:** ~2 hours. **Goal:** Build `awk` reflexes from `print $1` up to associative arrays.

For each puzzle: write the one-line (or short multi-line) `awk` solution, run it, paste the first few lines of output. If a puzzle has a more idiomatic alternative, write that too — the goal is not just "correct" but "the way you'd write it on the job."

Use `/etc/passwd` as your dataset where indicated. It is colon-separated; the fields are:

```
username:x:UID:GID:GECOS:home_dir:shell
```

If `/etc/passwd` is too small on your machine, use `/etc/group` or any whitespace-separated log you have.

---

## Puzzle 1 — `print` field N

Print the **shell** (field 7) of every user in `/etc/passwd`.

**Hint:** `-F:` sets the separator.

**Acceptance:** A list of shells, one per line.

---

## Puzzle 2 — `print` two fields with a custom separator

Print username and home directory, separated by a tab, for every user.

**Hint:** `OFS = "\t"` in a `BEGIN` block, OR `printf "%s\t%s\n"`.

**Acceptance:** Two columns, tab-aligned.

---

## Puzzle 3 — `NR` and `NF` as filters

Print the line number, the number of fields, and the line itself for every line in `/etc/fstab` that has more than 4 fields and is not a comment.

**Hint:** Two patterns combined: `NF > 4 && !/^#/`.

**Acceptance:** Lines like `3 6 UUID=... / ext4 defaults 0 1`.

---

## Puzzle 4 — `BEGIN` and `END`

Use `awk` to count the lines in `/etc/passwd` without using `wc`.

**Hint:** `END { print NR }`.

**Acceptance:** A single number.

---

## Puzzle 5 — Sum a column

Sum the third field (UID) of every line in `/etc/passwd`. Then sum only for accounts where UID >= 1000 (real human accounts on Linux).

**Hint:** Two programs. The second one uses a pattern `$3 >= 1000`.

**Acceptance:** Two numbers, with labels.

---

## Puzzle 6 — Associative arrays: count by group

Count how many accounts have each login shell. Use an associative array.

**Hint:**

```awk
{ count[$7]++ }
END { for (s in count) print count[s], s }
```

Pipe to `sort -rn` to get the most common first.

**Acceptance:** Lines like `38 /usr/sbin/nologin` `4 /bin/bash`. The shells will vary by your distro.

---

## Puzzle 7 — Build a histogram

For a numeric data file (any whitespace-separated file with at least 1 numeric column — `/proc/loadavg` won't do, but `ps -eo pid,vsz,rss,comm | tail -n +2` works), bucket the second column into ranges of width 10000 and print a count for each bucket.

**Hint:**

```bash
ps -eo pid,vsz,rss,comm | tail -n +2 | awk '
  { bucket = int($2 / 10000) * 10000
    hist[bucket]++ }
  END {
    for (b in hist) printf "%8d-%-8d : %d\n", b, b+9999, hist[b]
  }
' | sort -n
```

**Acceptance:** Buckets like `0-9999 : 14`, `10000-19999 : 6`, etc.

---

## Puzzle 8 — Multiple-file processing

Use `awk` on **two** files at once: `/etc/passwd` and `/etc/group`. Print the file name as a banner whenever you start a new file, then the first field of every line.

**Hint:** `FNR == 1` is true on the first line of each file. `FILENAME` is the current file.

```awk
FNR == 1 { print "==>", FILENAME, "<==" }
-F: '{ print $1 }'
```

(You'll need one program. The above is illustrative — combine them.)

**Acceptance:** A banner per file, then the usernames or groupnames.

---

## Puzzle 9 — Reformat a record

`/etc/passwd` lines look like `alice:x:1001:1001:Alice Smith:/home/alice:/bin/bash`. Reformat each as:

```
alice (UID 1001) home=/home/alice shell=/bin/bash
```

**Hint:** `printf` with `%s` placeholders. Use `-F:`.

**Acceptance:** Clean, readable lines.

---

## Puzzle 10 — A small `awk` "program"

Write a `awk` program (in a `.awk` file, not on the command line) that does this for `/var/log/auth.log` (Ubuntu) or `journalctl -u sshd > authlog.txt` (Fedora):

1. Count successful logins per user (`Accepted ` lines).
2. Count failed login attempts per user (`Failed password for ` lines).
3. In `END`, print a table with three columns: user, successes, failures.

**Hint:** Two associative arrays — `ok[user]++` and `fail[user]++`. In `END`, iterate the union of keys.

**Suggested skeleton:**

```awk
/Accepted/ {
  for (i = 1; i <= NF; i++) if ($i == "for") { ok[$(i+1)]++; break }
}
/Failed password for/ {
  for (i = 1; i <= NF; i++) if ($i == "for") { fail[$(i+1)]++; break }
}
END {
  printf "%-20s %8s %8s\n", "USER", "OK", "FAIL"
  # iterate union of users:
  for (u in ok)   users[u] = 1
  for (u in fail) users[u] = 1
  for (u in users) printf "%-20s %8d %8d\n", u, ok[u]+0, fail[u]+0
}
```

Run with: `awk -f auth-report.awk /var/log/auth.log`.

**Acceptance:** A 3-column table. The `+0` coerces empty to `0` so you don't print blanks.

---

## Reflection (5 min)

At the bottom of `answers.md`:

- Which puzzle was the cleanest "Aha, I see why `awk` exists" moment?
- Which felt like the wrong tool for the job?
- What would you write in Python instead — and what would you keep in `awk`?

---

When done, push and move on to [exercise-02-sed-substitutions.md](./exercise-02-sed-substitutions.md).
