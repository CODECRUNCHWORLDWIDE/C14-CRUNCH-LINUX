# Exercise 03 — ShellCheck Fixes

**Time:** ~1.5 hours. **Goal:** Read a script that violates roughly 15 ShellCheck rules. Fix each one. Explain the fix. Run ShellCheck after each change and watch the warning list shrink.

This is the most useful drill in the week. Most "I learned Bash from blog posts" code looks something like the script below. Every change you make here is one you will recognize in real code review.

Setup:

```bash
mkdir -p ~/c14-week-04/exercises/03
cd ~/c14-week-04/exercises/03
```

---

## Part A — The bad script

Save the following as `bad-script.sh`. Do **not** fix anything yet — we will fix it methodically below.

```bash
#!/bin/sh
# bad-script.sh — back up a directory of logs.
# Tries to do too much, does most of it wrong.

LOG_DIR=/var/log/myapp
BACKUP_DIR=/var/backups/myapp
DATE=`date +%Y-%m-%d`

if [ $1 = "" ]; then
    echo "Usage: bad-script.sh DIR"
    exit 1
fi

if [ -d $1 ]; then
    LOG_DIR=$1
fi

cd $BACKUP_DIR
mkdir $DATE

for f in `ls $LOG_DIR/*.log`; do
    cp $f $DATE/
done

TOTAL_SIZE=`du -sh $BACKUP_DIR/$DATE | awk '{print $1}'`
echo "Backed up $TOTAL_SIZE to $BACKUP_DIR/$DATE"

cat $BACKUP_DIR/$DATE/*.log | wc -l > $BACKUP_DIR/$DATE.linecount

if [ -e $BACKUP_DIR/$DATE/error.log ]; then
    grep ERROR $BACKUP_DIR/$DATE/error.log | mail -s "Errors" root
fi

if [ $? = 0 ]; then
    echo "Success"
fi
```

Run ShellCheck on it:

```bash
shellcheck bad-script.sh
```

You will get a long list of warnings. Save the output:

```bash
shellcheck bad-script.sh > before.txt 2>&1 || true
wc -l before.txt
```

The exact count varies by ShellCheck version, but expect 15+ warnings.

---

## Part B — Fix the warnings, one category at a time

For each category below, find every instance in the script, fix it, and re-run ShellCheck.

### Category 1 — Shebang and shell-mode (`SC2148`, `SC2039`)

The script declares `#!/bin/sh` but uses Bash-isms. Either commit to POSIX `sh` or use Bash. Since we want `[[ ]]` and other niceties, switch to Bash:

```bash
# WRONG
#!/bin/sh

# RIGHT
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

Add the four-line opener. Re-run ShellCheck.

### Category 2 — Backticks (`SC2006`)

Backticks are legacy command substitution. They don't nest and they handle escaping badly.

```bash
# WRONG
DATE=`date +%Y-%m-%d`
TOTAL_SIZE=`du -sh $BACKUP_DIR/$DATE | awk '{print $1}'`

# RIGHT
DATE=$(date +%Y-%m-%d)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR/$DATE" | awk '{print $1}')
```

Use `$(...)` everywhere. Re-run.

### Category 3 — Unquoted variables (`SC2086`)

The most common warning. Every variable expansion that's not inside `[[ ]]` must be quoted:

```bash
# WRONG
cd $BACKUP_DIR
mkdir $DATE
cp $f $DATE/

# RIGHT
cd -- "$BACKUP_DIR"
mkdir -- "$DATE"
cp -- "$f" "$DATE/"
```

Note the `--` sentinel before user-controlled paths. Re-run.

### Category 4 — `[ ]` instead of `[[ ]]` (`SC2086` related, plus general Bash style)

POSIX `[` word-splits its arguments. Switch to `[[`:

```bash
# WRONG
if [ $1 = "" ]; then ... fi
if [ -d $1 ]; then ... fi
if [ -e $BACKUP_DIR/$DATE/error.log ]; then ... fi

# RIGHT
if [[ -z ${1:-} ]]; then ... fi
if [[ -d $1 ]]; then ... fi
if [[ -e $BACKUP_DIR/$DATE/error.log ]]; then ... fi
```

Note the `${1:-}` form — under `set -u`, a bare `$1` aborts if no arguments. The `:-` form treats unset as empty for this single test. Re-run.

### Category 5 — `for f in $(ls)` (`SC2045`, `SC2086`)

BashPitfalls #1.

```bash
# WRONG
for f in `ls $LOG_DIR/*.log`; do
    cp $f $DATE/
done

# RIGHT
for f in "$LOG_DIR"/*.log; do
    [[ -e $f ]] || continue   # if no matches, glob expands to literal "$LOG_DIR/*.log"
    cp -- "$f" "$DATE/"
done
```

The `[[ -e $f ]] || continue` handles the case where no `*.log` files exist (without `shopt -s nullglob`, the literal `*.log` is iterated). Alternatively:

```bash
shopt -s nullglob
for f in "$LOG_DIR"/*.log; do
    cp -- "$f" "$DATE/"
done
shopt -u nullglob
```

Re-run.

### Category 6 — `cd` without error handling (`SC2164`)

```bash
# WRONG
cd $BACKUP_DIR

# RIGHT (under set -e, this aborts; without set -e, you must check):
cd -- "$BACKUP_DIR" || exit 1
```

Under `set -e`, `cd "$BACKUP_DIR"` will abort on failure. ShellCheck still flags it because not every script uses `set -e`. Either keep `set -e` (which we have) and accept the warning, or write `cd -- "$BACKUP_DIR" || exit 1` to silence ShellCheck explicitly.

### Category 7 — `$?` immediately after a chain (`SC2181`)

```bash
# WRONG
grep ERROR $BACKUP_DIR/$DATE/error.log | mail -s "Errors" root
if [ $? = 0 ]; then ... fi

# RIGHT: check directly
if grep -q ERROR "$BACKUP_DIR/$DATE/error.log"; then
    grep ERROR "$BACKUP_DIR/$DATE/error.log" | mail -s "Errors" root
fi
```

`$?` checks the last command's exit. But by the time the `if` runs, you may have run other commands. Check the command itself.

### Category 8 — Useless `cat` (`SC2002`)

```bash
# WRONG
cat $BACKUP_DIR/$DATE/*.log | wc -l > $BACKUP_DIR/$DATE.linecount

# RIGHT
wc -l "$BACKUP_DIR/$DATE"/*.log > "$BACKUP_DIR/$DATE.linecount"
```

`wc -l` accepts file arguments directly. The `cat` adds nothing. (Slightly different output format — `wc -l file` includes a `total` line at the end. If you need just the total number, use `wc -l --total=only`.)

### Category 9 — Missing `--` separators (`SC2114`, defensive)

Wherever a variable is passed to a command that takes file arguments, prefix with `--`:

```bash
# Defensive
rm -rf -- "$dir"
cp -- "$src" "$dst"
mv -- "$src" "$dst"
```

ShellCheck does not always warn about this; it's a habit you build. (BashPitfalls #3.)

### Category 10 — `mkdir` without `-p` if the directory might exist

Not strictly a ShellCheck warning, but a frequent bug:

```bash
# WRONG: if $DATE directory already exists, mkdir fails, set -e aborts
mkdir -- "$DATE"

# RIGHT: -p makes mkdir idempotent
mkdir -p -- "$DATE"
```

---

## Part C — The fixed version

Your final script should look approximately like this. Save as `fixed-script.sh`:

```bash
#!/usr/bin/env bash
# fixed-script.sh — back up a directory of logs.

set -euo pipefail
IFS=$'\n\t'

LOG_DIR=${1:-/var/log/myapp}
BACKUP_DIR=/var/backups/myapp
DATE=$(date +%Y-%m-%d)

if [[ ! -d $LOG_DIR ]]; then
    echo "No such log dir: $LOG_DIR" >&2
    exit 66
fi

mkdir -p -- "$BACKUP_DIR/$DATE"

shopt -s nullglob
for f in "$LOG_DIR"/*.log; do
    cp -- "$f" "$BACKUP_DIR/$DATE/"
done
shopt -u nullglob

TOTAL_SIZE=$(du -sh -- "$BACKUP_DIR/$DATE" | awk '{print $1}')
echo "Backed up $TOTAL_SIZE to $BACKUP_DIR/$DATE"

wc -l "$BACKUP_DIR/$DATE"/*.log > "$BACKUP_DIR/$DATE.linecount" 2>/dev/null || true

if [[ -e $BACKUP_DIR/$DATE/error.log ]] && grep -q ERROR "$BACKUP_DIR/$DATE/error.log"; then
    grep ERROR "$BACKUP_DIR/$DATE/error.log" | mail -s "Errors" root
fi

echo "Success"
```

Run:

```bash
shellcheck fixed-script.sh > after.txt 2>&1 || true
wc -l after.txt
```

`after.txt` should have **zero lines** (ShellCheck prints nothing when clean).

---

## Part D — Write `fixes.md`

For each category 1–10, write one paragraph in `fixes.md`:

1. The original wrong line.
2. The ShellCheck code (e.g., `SC2086`).
3. The fix.
4. One sentence on **why it's a real bug, not just a style preference** — with a concrete failure scenario.

Example entry:

> **Category 3 — Unquoted `$1`.**
>
> Original: `if [ -d $1 ]; then`
>
> ShellCheck: `SC2086` — "Double quote to prevent globbing and word splitting."
>
> Fix: `if [[ -d $1 ]]; then` (or `if [ -d "$1" ]; then` if forced to keep `[`).
>
> Real bug: if `$1` is `/var/log/my app`, the unquoted form passes two arguments (`/var/log/my` and `app`) to `[`, which then prints `bash: [: too many arguments` and the script exits non-zero. With `[[`, the quoted form, or both, the script works.

Ten entries. Roughly 200 words total.

---

## Acceptance

- `shellcheck fixed-script.sh` is clean (zero warnings).
- `before.txt` shows 15+ warnings; `after.txt` is empty.
- `fixes.md` has ten entries, each one with a real-failure scenario.

Commit. You now read ShellCheck output the way a code reviewer reads a stylistic comment — quickly, methodically, and without disagreement.
