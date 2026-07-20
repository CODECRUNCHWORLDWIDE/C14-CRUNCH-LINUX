# Exercise 02 — Ten `sed` Substitutions

**Time:** ~1.5 hours. **Goal:** Build `sed` reflexes from `s/foo/bar/` up to addressed, ranged, multi-command scripts.

For each puzzle: write the `sed` command, run it on the suggested input, paste the first few lines of output. Use a copy of the file, never the original — `sed -i` will overwrite without asking and there is no undo.

Make a working directory:

```bash
mkdir -p ~/c14-week-02/sed-drill
cd ~/c14-week-02/sed-drill
cp /etc/hosts hosts.txt
cp /etc/passwd passwd.txt
cp /etc/services services.txt
```

Now you have local copies safe to mangle.

---

## Puzzle 1 — Basic substitution

In `hosts.txt`, replace every `localhost` with `myhost`. Print to stdout (don't modify the file yet).

**Hint:** `sed 's/localhost/myhost/g' hosts.txt`.

**Acceptance:** Original on screen with `myhost` everywhere `localhost` used to be.

---

## Puzzle 2 — Case-insensitive substitution

In `hosts.txt`, replace `localhost`, `LocalHost`, and `LOCALHOST` (none may actually be present — but the command should handle all three) with `myhost`.

**Hint:** The `i` flag: `sed 's/localhost/myhost/gi'`.

**Acceptance:** Command output, plus a one-sentence note: which `sed` (GNU vs BSD) was this tested on? Both flavors support `i`, but `gi` ordering is fine on GNU and BSD.

---

## Puzzle 3 — In-place editing (with backup)

Now actually modify `hosts.txt` — replace `localhost` with `myhost` IN PLACE, keeping a backup as `hosts.txt.bak`.

**GNU sed (Linux):**

```bash
sed -i.bak 's/localhost/myhost/g' hosts.txt
```

**BSD sed (macOS):**

```bash
sed -i.bak 's/localhost/myhost/g' hosts.txt
```

(Both flavors work the same when you provide a non-empty suffix.)

**Acceptance:** Two files exist: `hosts.txt` (modified) and `hosts.txt.bak` (original). `diff hosts.txt hosts.txt.bak` shows the change.

---

## Puzzle 4 — Backreferences

In `passwd.txt`, reformat lines so that `username:x:UID:...` becomes `username (UID)` and drop the rest.

**Hint:** A regex with two capture groups, then a replacement that uses `\1` and `\2`.

```bash
sed -E 's/^([^:]+):x:([0-9]+):.*$/\1 (\2)/' passwd.txt
```

**Acceptance:** Lines like `root (0)`, `alice (1001)`.

---

## Puzzle 5 — Delete lines

Delete every comment line (starting with `#`) and every blank line from `services.txt`.

**Hint:** Two commands chained: `/^#/d; /^$/d`.

```bash
sed '/^#/d; /^$/d' services.txt | head
```

**Acceptance:** Output starts with non-comment, non-blank lines (likely `tcpmux 1/tcp` or similar).

---

## Puzzle 6 — Addressed substitution

In `passwd.txt`, change `:x:` to `:HIDDEN:` only on lines 1 through 5.

**Hint:** Prefix the substitute with an address range: `1,5s/...`.

```bash
sed '1,5s/:x:/:HIDDEN:/' passwd.txt | head -6
```

**Acceptance:** First 5 lines show `HIDDEN`; line 6 and onward still show `x`.

---

## Puzzle 7 — Substitute only on lines matching a regex

In `services.txt`, on lines that contain `tcp` (but not `udp`), replace `tcp` with `TCP`.

**Hint:** `/tcp/!d` would delete non-tcp lines — that's not what we want. Use an addressed substitution: `/tcp/s/tcp/TCP/g`.

But that breaks if a line contains both. A safer form:

```bash
sed '/^[^#]/{ /tcp/{ /udp/!s/tcp/TCP/g } }' services.txt | head
```

That nested form reads "on non-comment lines, on tcp-containing lines, on lines NOT containing udp, do the substitution." It's a mouthful — and a good cue that you might prefer `awk` for anything more complex.

**Acceptance:** Lines like `tcpmux  1/TCP`. Lines containing both `tcp` and `udp` are left alone.

---

## Puzzle 8 — Range with regex addresses

Print only the lines from the first `Accepted` to the next `Failed password` in `/var/log/auth.log` (Ubuntu) — or from any pair of marker patterns in a file you have.

**Hint:** Use `-n` to suppress default print, then `/start/,/end/p`:

```bash
sudo sed -n '/Accepted/,/Failed password/p' /var/log/auth.log | head
```

**Acceptance:** A multi-line excerpt bounded by your markers.

---

## Puzzle 9 — Strip trailing whitespace

Strip trailing whitespace (spaces and tabs) from every line of `passwd.txt`. Print the result.

**Hint:** `s/[[:space:]]*$//`.

```bash
sed 's/[[:space:]]*$//' passwd.txt | head
```

**Acceptance:** Lines visibly identical (unless there was trailing whitespace, which `/etc/passwd` usually lacks — confirm with `cat -A passwd.txt | head`).

Bonus: create a test file with deliberate trailing whitespace and prove your `sed` removes it:

```bash
printf "alpha   \nbeta\t\t\ngamma\n" > trailing.txt
cat -A trailing.txt                   # see the trailing whitespace
sed 's/[[:space:]]*$//' trailing.txt | cat -A
```

---

## Puzzle 10 — A small `sed` "script" file

In a file `cleanup.sed`, write a `sed` program that:

1. Deletes comment lines (`#...`).
2. Deletes blank lines.
3. Squeezes multiple spaces into one.
4. Strips trailing whitespace.

```sed
# cleanup.sed
/^[[:space:]]*#/d
/^$/d
s/[[:space:]]\{2,\}/ /g
s/[[:space:]]*$//
```

Run it:

```bash
sed -f cleanup.sed services.txt | head
```

**Acceptance:** Clean, single-spaced, no-comment, no-blank-line output. The script file committed to your portfolio.

---

## Reflection (5 min)

At the bottom of `answers.md`:

- Which puzzle made the BSD-vs-GNU distinction matter? (Probably Puzzle 3 if you tried it on macOS too.)
- Which puzzle felt like a stretch — where you'd really want `awk` or Python instead?
- What pattern from Eric Pement's `sed1line.txt` did you reach for?

---

When done, push and move on to [exercise-03-real-log-pipeline.md](./exercise-03-real-log-pipeline.md).
