# Challenge 01 — Rewrite a Bad Script

> **Time:** ~3 hours. **Outcome:** You read a 50-line script in the wild and within ten minutes you can list every defect, give each one a ShellCheck code or BashPitfalls number, and produce a rewritten version that handles every edge case the original ignores.

This challenge is the bridge between the exercises (which drilled isolated fixes) and the mini-project (which asks you to build from scratch). You will take a real-shaped "looks like it works" script — the kind that runs fine in dev and corrupts data the first time someone names a file with a space — and rewrite it from first principles.

You will work in a scratch directory. Snapshot if you're paranoid; the script writes only inside your scratch tree.

```bash
mkdir -p ~/c14-week-04/challenges/01
cd ~/c14-week-04/challenges/01
```

---

## The bad script

Save the following as `original.sh`. **Do not run it as-is** — first you read it, find the bugs, and only then run the fixed version.

```bash
#!/bin/bash
# original.sh — "Daily backup of important stuff"
# (Found in production, used unmodified for 18 months.)

BACKUP_ROOT=/var/backups
SOURCE=$1
NAME=`basename $SOURCE`
DATE=`date +%Y%m%d`
DEST=$BACKUP_ROOT/$NAME-$DATE

# Make sure the backup dir exists
mkdir $DEST

# Copy files
for f in `find $SOURCE -type f`; do
    cp $f $DEST/
done

# Compress
cd $DEST
tar czvf $NAME-$DATE.tar.gz *

# Remove uncompressed
rm -rf $DEST/*
mv $NAME-$DATE.tar.gz $BACKUP_ROOT

# Email notification
SIZE=`du -sh $BACKUP_ROOT/$NAME-$DATE.tar.gz | cut -f1`
echo "Backup of $SOURCE completed. Size: $SIZE" | mail -s "Backup" admin@example.com

# Keep only the last 7 backups
ls -t $BACKUP_ROOT/*.tar.gz | tail -n +8 | xargs rm

echo "Done"
```

---

## Task 1 — Catalog the bugs (45 min)

Read the script line by line. For **every defect**, write an entry in `bugs.md`:

- The line(s) involved.
- The bug name (ShellCheck `SCxxxx` code, BashPitfalls number, or a descriptive name).
- One concrete input that triggers it.
- The expected wrong behavior.

You should find at least **20 distinct defects.** A non-exhaustive starting list:

1. No `set -euo pipefail`. Script continues past failures.
2. No quoting on `$SOURCE`, `$NAME`, `$DATE`, `$DEST`, `$f` — every variable expansion.
3. `basename $SOURCE` without `--` and without quoting. Breaks on `-rfoo` and on paths with spaces.
4. Backticks instead of `$(...)` — `SC2006`.
5. `mkdir $DEST` without `-p`. Re-running the script the same day fails.
6. `for f in $(find ...)` — `SC2045`, BashPitfalls #1. Breaks on filenames with whitespace.
7. `cd $DEST` without error handling. If `mkdir` failed, the next `tar` runs in cwd. `SC2164`.
8. `tar czvf $NAME-$DATE.tar.gz *` — unquoted glob, hostile-filename starts-with-dash, no `--`. Also reads `.dotfiles` differently than the rest.
9. `rm -rf $DEST/*` — if `$DEST` is empty (because `mkdir` failed silently and `cd` succeeded into a different dir), this `rm -rf` runs in cwd. `SC2086` + a footgun.
10. `mv $NAME-$DATE.tar.gz $BACKUP_ROOT` — if `$NAME` contains slashes (which `basename` *almost* prevents but not on edge cases), this writes outside the backup dir.
11. `ls -t | tail | xargs rm` — `SC2012` ("don't parse `ls`"). Also, `xargs rm` without `-r` runs `rm` even with no input, asking for cwd deletion on some old `xargs`. Use `xargs -r` (or `xargs --no-run-if-empty`).
12. No trap. If the script is interrupted between `cd $DEST` and the `mv`, partial `.tar.gz` left behind.
13. No `flock`. Two cron-triggered copies running at midnight produce corrupted tarballs.
14. No `--` before user-controlled paths in `cp`, `mv`, `rm`, `tar`. BashPitfalls #3.
15. `du -sh ... | cut -f1` — works, but on `du`'s output the size and name are tab-separated by GNU `du` and *space*-separated by BSD `du`. Portability bug. Use `awk '{print $1}'`.
16. `mail -s` — no error path if `mail` is not installed or no MTA is configured.
17. `find $SOURCE -type f` then `cp` flattens the directory structure. Two files with the same name in different subdirs collide.
18. `tar` reads the temp dir, including the in-progress tarball it's writing. (It catches itself in some cases but the result is unsafe.)
19. No exit code discipline. Every failure produces "Done" anyway because there's nothing checking.
20. `echo "Done"` at the end is misleading — the script does many things, "Done" doesn't tell you which.

Bonus credit for finding 25+ defects.

---

## Task 2 — Rewrite from scratch (90 min)

Build `rewritten.sh` that produces the same intended behavior, correctly. Required elements:

### Defensive opener
- `#!/usr/bin/env bash`
- `set -euo pipefail`
- `IFS=$'\n\t'`
- Header comment with usage, exit codes, dependencies.

### Argument parsing
- Usage function. Exit `64` on misuse.
- Support a `-h` / `--help` flag.
- Validate that `$SOURCE` exists and is readable.

### Single-instance lock
- `flock` on `/var/lock/backup-NAME.lock`. Exit `75` if another instance is running.

### Atomic output
- Write the tarball to a `.tmp` name inside `$BACKUP_ROOT`.
- `mv` to the final name only if the tar succeeded.
- On any error or interrupt, the `.tmp` is removed.

### Cleanup trap
- `trap cleanup EXIT` that removes the staging temp dir and any in-progress tarball.

### Tar safely
- `tar -C "$SOURCE" -czf "$tmp_tarball" .` — the `-C` changes directory before reading, so paths in the tarball are relative; no need to copy first.
- Eliminates the entire `for f in $(find ...); cp` step. Tar reads the source tree directly.

### Quoting and `--`
- Every variable expansion quoted.
- Every command that takes paths gets `--` before path arguments.

### Retention without `ls`
- Use `find -mtime +N` or `find -printf '%T@ %p\n' | sort -n | head -n -7 | cut -d' ' -f2-` to find old tarballs.
- Or, simplest: name files `NAME-YYYYMMDD.tar.gz` and use a `find -name 'NAME-*.tar.gz' -mtime +7 -delete` rule.

### Email or no email — make it optional
- Add a `--notify ADDR` flag. If unset, skip mailing. The script must not fail because no MTA exists.

### Exit code discipline
- `0` only if everything succeeded.
- `64` for usage errors, `66` for missing source, `75` for lock contention, `74` for tar failure, etc.

### ShellCheck-clean
- `shellcheck rewritten.sh` reports zero warnings.

---

## Task 3 — Verify with hostile inputs (45 min)

Set up a hostile source tree to test the rewrite:

```bash
mkdir -p source/'a folder with spaces'
echo "data" > source/normal.txt
echo "data" > 'source/file with spaces.txt'
echo "data" > -- 'source/-dashfile.txt'
touch -- "$(printf 'source/has\nnewline.txt')"
mkdir source/sub
echo "more" > source/sub/normal.txt
```

Run your rewrite:

```bash
./rewritten.sh source
```

Verify:

```bash
# The tarball exists and has a sane name
ls -l /var/backups/

# The tarball contains every file, including the weird ones
tar tzf /var/backups/source-*.tar.gz
```

Now test the failure modes:

```bash
./rewritten.sh                              # exit 64, prints usage to stderr
./rewritten.sh /nonexistent                 # exit 66, prints error
./rewritten.sh source & ./rewritten.sh source   # second one exits 75 (lock contention)
```

Run **twice in the same day** — the second run must succeed without colliding with the first run's tarball name. (Hint: include the time in the name, or refuse to overwrite, or rotate the existing one.)

---

## Task 4 — Compare ShellCheck output (30 min)

Run ShellCheck on both:

```bash
shellcheck original.sh   > original-sc.txt 2>&1 || true
shellcheck rewritten.sh  > rewritten-sc.txt 2>&1 || true

wc -l original-sc.txt rewritten-sc.txt
```

`rewritten-sc.txt` must be empty.

Save both. Commit `bugs.md`, `rewritten.sh`, `original-sc.txt`, `rewritten-sc.txt`, plus a `reflection.md` answering:

1. Which of the original's bugs would have caused a *silent data loss* — i.e., the script appears to have succeeded but the backup is corrupted or incomplete? List at least three.
2. Which bug, in your assessment, is the most dangerous? Why?
3. Would the mini-project's `backup.sh` reuse code from this rewrite? Which parts?
4. The original script ran "unmodified for 18 months" in production. Why didn't it cause an outage sooner? (Hint: the script's failure modes are *quiet*, not loud.)

---

## Stretch (optional)

- Add a `--dry-run` flag that prints what would be done without doing it.
- Add a checksum file alongside the tarball — `sha256sum > NAME-DATE.tar.gz.sha256`.
- Add a verify step that extracts the tarball to a temp dir and confirms the file list matches the source.
- Make the script work as a `systemd` timer unit (Week 5 preview).

---

## Acceptance

- `bugs.md` with 20+ entries.
- `rewritten.sh` passes ShellCheck and the hostile-input tests.
- `reflection.md` with the four answers.

You have now done in three hours what most teams take a sprint to do. The pattern transfers — every legacy Bash script you inherit will look like `original.sh`. You know the playbook.
