# Exercise 01 — Write Three Defensive Scripts

**Time:** ~2 hours. **Goal:** Build the muscle memory for the four-line opener, full quoting, `[[ ]]`, exit codes, and ShellCheck-clean output. Three scripts, each one slightly harder than the last.

For each: write the script, run ShellCheck on it, fix every warning, test with a hostile filename, and commit.

You will need Bash 5.2+ and ShellCheck 0.9+. Verify:

```bash
bash --version | head -1
shellcheck --version | head -2
```

Set up a scratch directory:

```bash
mkdir -p ~/c14-week-04/exercises/01
cd ~/c14-week-04/exercises/01
```

---

## Script 1 — `count-lines.sh` (30 min)

Write a script that counts the number of non-blank, non-comment lines in one or more files.

**Specification:**

- Usage: `./count-lines.sh FILE [FILE ...]`
- For each file: print `<count>  <filename>` to stdout, one line per file.
- A "comment" line is one whose first non-whitespace character is `#`.
- A "blank" line is one that contains only whitespace (spaces, tabs, nothing else).
- Exit codes: `0` on success, `64` if no files given, `66` if any file is unreadable.
- Handles filenames with spaces, newlines, and dashes correctly.

**Wrong vs right reference:**

The wrong way to do this iteration:

```bash
# WRONG: word-splits filenames, fails on spaces
for f in $@; do
    grep -cE '^[^#]' $f
done
```

The right way:

```bash
# RIGHT: quoted "$@", quoted "$f"
for f in "$@"; do
    if [[ ! -r $f ]]; then
        echo "Cannot read: $f" >&2
        exit 66
    fi
    count=$(grep -cE '^[[:space:]]*[^#[:space:]]' -- "$f")
    printf '%d  %s\n' "$count" "$f"
done
```

**Test inputs:**

```bash
# A normal file
cat > normal.txt <<'EOF'
# this is a comment
hello
   # indented comment
   
world
EOF
# Expected: count = 2

# A file with a hostile name
touch -- 'has spaces.txt' '-rfile.txt' "$(printf 'has\nnewline.txt')"
echo "real content" > 'has spaces.txt'
echo "more content" > -- '-rfile.txt'

# Run the script
./count-lines.sh normal.txt 'has spaces.txt' ./-rfile.txt
```

**Acceptance:**

- `shellcheck count-lines.sh` is clean.
- The script handles `'has spaces.txt'` and `./-rfile.txt` correctly. (The `./` prefix matters — see BashPitfalls #3 on filenames starting with `-`.)
- The exit code is `66` when given an unreadable file.

Commit as `01-count-lines.sh` and write three sentences in `notes.md` on what changed between your first draft and the final version.

---

## Script 2 — `safe-mv.sh` (45 min)

Write a wrapper around `mv` that refuses to overwrite an existing destination unless `-f` (force) is passed.

**Specification:**

- Usage: `./safe-mv.sh [-f] SOURCE DEST`
- If `DEST` exists and `-f` was not given, print to stderr and exit `73` (`EX_CANTCREAT`).
- If `-f` is given, overwrite without prompt.
- If `SOURCE` doesn't exist, exit `66` (`EX_NOINPUT`).
- Exit codes: `0` success, `64` wrong usage, `66` source missing, `73` dest exists without `-f`.
- The script must handle a `--` separator between flags and filenames.
- The script must work when `SOURCE` or `DEST` begins with a dash.

**Wrong vs right reference:**

The naïve form has multiple bugs:

```bash
# WRONG: no quoting, no flag parsing, no -- separator, vulnerable to spaces and dashes
if [ -e $2 ]; then echo "exists"; exit 1; fi
mv $1 $2
```

The right form:

```bash
# RIGHT
set -euo pipefail
force=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        -f) force=1; shift ;;
        --) shift; break ;;
        -*) echo "Unknown flag: $1" >&2; exit 64 ;;
        *) break ;;
    esac
done
if [[ $# -ne 2 ]]; then exit 64; fi
src="$1"; dst="$2"
if [[ ! -e $src ]]; then echo "No such source: $src" >&2; exit 66; fi
if [[ -e $dst && $force -eq 0 ]]; then echo "Destination exists: $dst" >&2; exit 73; fi
mv -- "$src" "$dst"
```

**Tests:**

```bash
echo "alpha" > a.txt
echo "beta"  > b.txt
./safe-mv.sh a.txt c.txt           # should succeed; a.txt -> c.txt
./safe-mv.sh c.txt b.txt           # should fail (exit 73): b.txt already exists
./safe-mv.sh -f c.txt b.txt        # should succeed: -f overrides
./safe-mv.sh missing.txt z.txt     # should fail (exit 66): no source

# Dash-prefixed source
echo "rare" > -- '-data.txt'
./safe-mv.sh -- '-data.txt' moved.txt   # should succeed
```

**Acceptance:**

- `shellcheck safe-mv.sh` is clean.
- All five test cases produce the expected outcome and the expected exit code.
- `notes.md` notes which BashPitfalls numbers the wrong-form version exhibits (hint: at least #1, #3, #14).

---

## Script 3 — `find-large.sh` (45 min)

Write a script that finds files larger than a given size threshold under a given directory, and reports them in human-readable form, sorted largest first.

**Specification:**

- Usage: `./find-large.sh DIR THRESHOLD`
- `THRESHOLD` is a size accepted by `find(1)` — e.g., `100M`, `1G`, `500k`. Pass it through to `find -size`.
- Output: one file per line, `<human-size>  <path>`, sorted largest first. Use `du -h` and `sort -h`.
- The script must handle directories with filenames containing spaces and newlines. Use `-print0` and `read -d ''`.
- Exit codes: `0` success, `64` wrong usage, `66` if `DIR` doesn't exist or isn't a directory.

**Wrong vs right reference:**

The wrong way:

```bash
# WRONG: word-splits on space, fails on filenames with newlines
for f in $(find $1 -size +$2 -type f); do
    du -h $f
done | sort -h -r
```

Multiple sins: unquoted `$1`, unquoted `$2`, command substitution unquoted, `du` unquoted, no `--`, `for` over command substitution. Every line a textbook BashPitfall.

The right way:

```bash
# RIGHT
set -euo pipefail
IFS=$'\n\t'

if [[ $# -ne 2 ]]; then echo "Usage: $0 DIR THRESHOLD" >&2; exit 64; fi
dir="$1"; threshold="$2"
if [[ ! -d $dir ]]; then echo "No such directory: $dir" >&2; exit 66; fi

# -print0 + while read -r -d '' handles every filename
while IFS= read -r -d '' f; do
    du -h -- "$f"
done < <(find "$dir" -type f -size "+$threshold" -print0) | sort -h -r
```

The `< <(...)` construct is **process substitution** — the output of `find` is exposed as a file for the `while` loop's redirect. This keeps the loop body in the current shell (unlike `find ... | while`, which subshells).

**Tests:**

```bash
mkdir -p testdir/'sub one'/sub2
dd if=/dev/zero of=testdir/big.bin       bs=1M count=10 status=none
dd if=/dev/zero of=testdir/'sub one'/m.bin bs=1M count=5 status=none
dd if=/dev/zero of=testdir/small.bin     bs=1k count=10 status=none

./find-large.sh testdir 1M
# Expected output (order: largest first):
# 10M    testdir/big.bin
# 5.0M   testdir/sub one/m.bin

./find-large.sh missing 1M       # should exit 66
./find-large.sh testdir          # should exit 64
```

**Acceptance:**

- `shellcheck find-large.sh` is clean.
- The script correctly reports the file under `sub one/` (with the space).
- Output is sorted largest first.
- `notes.md` answers: why does `< <(find ...)` work where `find ... | while` would lose variables set inside the loop?

---

## Wrap-up

After all three scripts, run:

```bash
shellcheck *.sh
```

Zero output is the goal. If you have a `# shellcheck disable=` annotation anywhere, your `notes.md` must explain why ShellCheck is wrong in that one specific case. (Spoiler: it almost never is.)

Commit. Move to [exercise 02](./exercise-02-trap-and-cleanup.md).
