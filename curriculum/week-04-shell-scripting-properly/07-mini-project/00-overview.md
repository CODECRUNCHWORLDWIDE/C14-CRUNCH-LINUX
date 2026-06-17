# Mini-Project — Three Useful Scripts

> Write three small, defensive Bash scripts that each do one job well: a backup wrapper, a log rotator, and a "where did my disk space go" reporter. Every script ships with the four-line opener, a `usage()` function, a cleanup trap, and a `shellcheck`-clean bill of health.

**Estimated time:** 6–7 hours, spread Thursday–Saturday.

This mini-project is the deliverable that proves Week 4 took. The three scripts you write are scripts you will *actually use* — they go straight into your `~/bin/` and run for years. They are small enough to fit in your head, robust enough to run unattended, and structured enough to evolve.

The point of three scripts (not one big one) is to drill the **shape** of a defensive script three times. Each one has its own argument parser, its own trap, its own exit-code contract. By the third, the shape is muscle memory.

---

## Deliverable

A directory in your portfolio repo `c14-week-04/mini-project/` containing:

1. `README.md` — your write-up. Design notes, exit-code tables, usage examples, known limitations.
2. `bin/backup.sh` — the backup wrapper. Wraps `tar` or `rsync` with defensive defaults, retention, and atomic output.
3. `bin/rotate-logs.sh` — the log rotator. Gzip files older than N days; delete files older than M days.
4. `bin/disk-usage.sh` — the disk-usage reporter. Finds the top N largest directories under a root, in human-readable form.
5. `tests/test-backup.sh`, `tests/test-rotate.sh`, `tests/test-disk-usage.sh` — minimal test scripts that exercise each in a scratch directory.
6. `Makefile` (or a `run-tests.sh`) — a single command that runs all three tests.
7. `notes.md` — scratch space. Not required to be polished; evidence of your process.

---

## Common requirements (all three scripts)

These apply to every script. Get them right once and copy them across:

### R1 — Defensive opener

Every script starts:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
```

### R2 — Header comment

At least: filename, one-line description, usage example, exit-code table. Roughly 15 lines of comment block.

### R3 — `usage()` function

Prints help text to **stderr** (not stdout) and exits 64 on misuse. Triggered by `-h`, `--help`, or any unknown flag.

### R4 — Named exit codes

At minimum:

```bash
readonly EX_USAGE=64
readonly EX_NOINPUT=66
readonly EX_TEMPFAIL=75
readonly EX_CANTCREAT=73
readonly EX_IOERR=74
```

Use them. `exit 1` everywhere loses information.

### R5 — Logging functions

```bash
log()  { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }
warn() { log "WARN: $*"; }
die()  { log "ERROR: $*"; exit 1; }
```

All log output goes to **stderr**. Stdout is reserved for data that downstream pipelines might consume.

### R6 — Cleanup trap

Every script that creates a temp file or directory must have a `cleanup` function and `trap cleanup EXIT`. The cleanup must work even if the resource was never created (test before remove).

### R7 — Single-instance lock (where it makes sense)

`backup.sh` and `rotate-logs.sh` should refuse to run a second instance concurrently. Use `flock`. `disk-usage.sh` is read-only and doesn't need it.

### R8 — ShellCheck clean

`shellcheck bin/*.sh tests/*.sh` reports zero warnings. Any deliberate exception is annotated with `# shellcheck disable=SCxxxx  # reason: ...` on the line above.

### R9 — Hostile-input safe

Tested against directories containing files with spaces, newlines, and leading dashes. None of your scripts should fail or behave unexpectedly on these.

### R10 — Dry-run support

Each script supports `--dry-run` (or `-n`), which prints what would be done without doing it. Critical for testing destructive operations safely.

---

## Script 1 — `backup.sh`

A `tar`-based backup wrapper.

### Specification

- Usage: `backup.sh [--dry-run] [--retain N] [--notify ADDR] SOURCE DEST_DIR`
- `SOURCE`: a directory to back up.
- `DEST_DIR`: a directory where the backup tarball lands.
- Tarball name: `<basename-of-SOURCE>-YYYYMMDD-HHMMSS.tar.gz`.
- `--retain N` (default 7): after a successful backup, delete tarballs older than N days **matching the same basename prefix**. Never touches unrelated files.
- `--notify ADDR` (optional): on success, mail a summary to `ADDR`. If `mail` is not available, log a warning and continue.
- Atomic output: write to `<name>.tar.gz.tmp`, then `mv` on success.
- Trap removes the `.tmp` file on any failure or interrupt.
- `flock` prevents concurrent runs (one lockfile per `DEST_DIR/basename`).

### Required behavior

```
$ ./backup.sh /etc /var/backups/etc
[2026-05-13T14:00:01+00:00] Starting backup of /etc -> /var/backups/etc/etc-20260513-140001.tar.gz
[2026-05-13T14:00:14+00:00] Tarball: 4.2M, 1738 files
[2026-05-13T14:00:14+00:00] Retention: kept 5 backups, deleted 2 older than 7 days
[2026-05-13T14:00:14+00:00] Done

$ echo $?
0
```

Failure cases:

```
$ ./backup.sh /no/such/dir /var/backups/x
[ERROR] /no/such/dir: not a directory
$ echo $?
66

$ ./backup.sh /etc /var/backups/etc &
$ ./backup.sh /etc /var/backups/etc
[ERROR] another instance is running (lock held on /var/backups/etc/.lock-etc)
$ echo $?
75
```

### Hints

- `tar --warning=no-file-changed -czf` to suppress noise from files that change during the read (logs, sockets).
- `find "$DEST_DIR" -maxdepth 1 -name "${name}-*.tar.gz" -mtime "+$retain" -delete` for retention.
- Don't `cd` into `$SOURCE`; use `tar -C "$SOURCE"`.

### Wrong vs right reference

```bash
# WRONG: doesn't quote, no trap, no flock, leaves partial tarball on Ctrl-C
tar czf $DEST_DIR/backup-$(date +%Y%m%d).tar.gz $SOURCE
ls -t $DEST_DIR/*.tar.gz | tail -n +8 | xargs rm
```

```bash
# RIGHT: defensive
final="$DEST_DIR/${name}-${ts}.tar.gz"
tmp="$final.tmp"
trap 'rm -f -- "$tmp"' EXIT
tar -C "$SOURCE" --warning=no-file-changed -czf "$tmp" .
mv -- "$tmp" "$final"
trap - EXIT
find "$DEST_DIR" -maxdepth 1 -name "${name}-*.tar.gz" -mtime "+$retain" -delete
```

---

## Script 2 — `rotate-logs.sh`

A log rotator. The system kind, not the per-application kind (which is what `logrotate(8)` does).

### Specification

- Usage: `rotate-logs.sh [--dry-run] [--gzip-after-days N] [--delete-after-days M] DIR`
- Walks `DIR` recursively for files matching `*.log`.
- For each file:
  - If modified > `N` days ago and not already gzipped: gzip in place (file becomes `name.log.gz`).
  - If modified > `M` days ago: delete.
- Default: `N=7`, `M=30`. Must have `M > N`.
- `--dry-run`: print actions without performing them. Use the prefix `[DRY]`.
- Atomic gzip: the file is gzipped via `gzip --keep`, then the original is removed only after the `.gz` is verified.
- ShellCheck-clean, hostile-filename-safe, trap-protected.

### Required behavior

```
$ ./rotate-logs.sh /var/log/myapp
[2026-05-13T14:00:01+00:00] Scanning /var/log/myapp
[2026-05-13T14:00:01+00:00] GZIP /var/log/myapp/access-2026-05-05.log (8 days old, 12M)
[2026-05-13T14:00:02+00:00] GZIP /var/log/myapp/access-2026-05-06.log (7 days old, 11M)
[2026-05-13T14:00:02+00:00] DELETE /var/log/myapp/access-2026-04-01.log.gz (42 days old)
[2026-05-13T14:00:02+00:00] Done. 2 gzipped, 1 deleted, 0 errors
```

Dry-run:

```
$ ./rotate-logs.sh --dry-run /var/log/myapp
[DRY] GZIP /var/log/myapp/access-2026-05-05.log (8 days old, 12M)
[DRY] DELETE /var/log/myapp/access-2026-04-01.log.gz (42 days old)
```

### Hints

- `find "$DIR" -type f -name '*.log' -mtime "+$N" -print0` to iterate gzip candidates safely.
- `find "$DIR" -type f \( -name '*.log' -o -name '*.log.gz' \) -mtime "+$M" -print0` for deletion candidates.
- Use `read -r -d ''` to consume `-print0` output.
- `gzip --keep "$f" && rm -- "$f"` if you want safety; or just `gzip -- "$f"` (which removes the original on success).
- Validate `M > N` early; reject configurations where you'd both gzip and immediately delete.

### Wrong vs right reference

```bash
# WRONG: word-splits, no -- separator, deletes mid-iteration if files are renamed
for f in $(find $DIR -name "*.log" -mtime +7); do
    gzip $f
done
for f in $(find $DIR -name "*.log.gz" -mtime +30); do
    rm $f
done
```

```bash
# RIGHT
while IFS= read -r -d '' f; do
    if (( dry_run )); then
        log "[DRY] GZIP $f"
    else
        gzip -- "$f"
        log "GZIP $f"
    fi
done < <(find "$DIR" -type f -name '*.log' -mtime "+$gzip_after" -print0)
```

---

## Script 3 — `disk-usage.sh`

A "where did my disk space go" reporter. Read-only; produces a sorted top-N list.

### Specification

- Usage: `disk-usage.sh [--depth N] [--top K] [--exclude PATTERN]... ROOT`
- Walks `ROOT` to depth `N` (default `2`), computes `du -sh` for each subdirectory.
- Prints the top `K` (default `10`) directories by size, largest first.
- `--exclude PATTERN`: skip paths matching `PATTERN` (a glob, applied with `find -path`). Repeatable.
- Output format: `<size>  <path>`, columns aligned for readability.
- Exits 66 if `ROOT` doesn't exist; 0 on success.

### Required behavior

```
$ ./disk-usage.sh --top 5 /var
2.1G    /var/log
1.8G    /var/lib/docker
850M    /var/cache/apt
210M    /var/backups
180M    /var/lib/postgresql
```

With exclusions:

```
$ ./disk-usage.sh --top 5 --exclude '*/docker*' --exclude '*/cache*' /var
2.1G    /var/log
210M    /var/backups
180M    /var/lib/postgresql
12M     /var/spool
4.0M    /var/lib/dpkg
```

### Hints

- `du -h --max-depth=N "$ROOT"` is the simple core. Parse its output.
- `sort -h -r` sorts human-readable sizes correctly (handles `M`/`G` suffixes).
- `head -n "$K"` for the top-K cut.
- Exclusions are tricky with `du`. Two approaches:
  1. Use `find` to build a directory list with exclusions, then `du -sh` each.
  2. Use `du --exclude=PATTERN` (GNU `du` supports this; check `du --version`).
- This is the **read-only** script. No `flock`, no atomic output, no destructive operations. Smaller script, but full defensive opener still required.

### Wrong vs right reference

```bash
# WRONG: word-splits, doesn't sort correctly (sort doesn't understand M vs G without -h)
du -sh $ROOT/* | sort -r | head -10
```

```bash
# RIGHT
du -h --max-depth="$depth" "$ROOT" 2>/dev/null \
    | sort -h -r \
    | head -n "$top"
```

The `2>/dev/null` suppresses "Permission denied" lines from directories you can't read — common when running against `/` as a non-root user. If you want to know about them, redirect stderr to a log file instead.

---

## Test harness

Each script needs a corresponding test in `tests/`. Tests must be runnable without root (use a scratch directory under `/tmp`).

### `tests/test-backup.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

TESTDIR=$(mktemp -d)
trap 'rm -rf -- "$TESTDIR"' EXIT

# Setup a fake source tree
mkdir -p "$TESTDIR/src/sub"
echo "alpha" > "$TESTDIR/src/a.txt"
echo "beta"  > "$TESTDIR/src/sub/b.txt"
touch -- "$TESTDIR/src/has space.txt"
mkdir -p "$TESTDIR/dest"

# Run backup
../bin/backup.sh "$TESTDIR/src" "$TESTDIR/dest"

# Verify
test -f "$TESTDIR/dest"/src-*.tar.gz || { echo "no tarball produced"; exit 1; }
count=$(tar tzf "$TESTDIR/dest"/src-*.tar.gz | wc -l)
[[ $count -ge 4 ]] || { echo "expected 4+ entries, got $count"; exit 1; }

echo "PASS: test-backup.sh"
```

Write similar tests for `rotate-logs.sh` and `disk-usage.sh`. Each test must:

- Set up a scratch tree.
- Run the script.
- Verify the expected outcome.
- Clean up.
- Print `PASS:` on success.

The `Makefile`:

```make
.PHONY: test lint
test:
	@for t in tests/test-*.sh; do bash "$$t" || exit 1; done

lint:
	@shellcheck bin/*.sh tests/*.sh
```

---

## Acceptance criteria

- All three scripts pass `shellcheck` with zero warnings.
- All three scripts pass their corresponding test in `tests/`.
- `make test && make lint` exits 0 from the project root.
- Each script's `--help` prints a usage block.
- Each script handles `Ctrl-C` mid-execution without leaving partial output.
- Each script tested against a hostile-filename input (file with space, file with newline, file starting with `-`). None breaks.
- `README.md` documents the design choices and limitations.

---

## Grading rubric

| Element | Points |
|---------|-------:|
| All three scripts ShellCheck-clean | 20 |
| Defensive opener (`set -euo pipefail`, `IFS`) in every script | 10 |
| `usage()` and named exit codes | 10 |
| `cleanup()` trap with `mktemp` | 10 |
| `flock`-based single-instance for backup and rotator | 10 |
| Atomic output (backup.sh) | 10 |
| `--dry-run` working on rotator and backup | 5 |
| Hostile-filename robustness verified by test | 10 |
| Test harness runs cleanly | 10 |
| README.md complete with design notes | 5 |
| **Total** | **100** |

90+ = portfolio quality. 80-89 = solid but a rough edge or two. 70-79 = needs revision before week 5. <70 = re-read both lectures.

---

## Stretch goals

- Add a `--verify` flag to `backup.sh` that extracts the tarball into a temp dir, compares file lists with the source, and exits non-zero on mismatch.
- Wire all three scripts into `systemd` user timers (this is Week 5 territory; doing it now is great prep).
- Add `--json` output to `disk-usage.sh` so the report is machine-parseable downstream.
- Write a `rotate-logs.sh` integration test that uses `touch -d '15 days ago' file.log` to simulate aged files, then verifies the rotator catches them.
- Replace `tar` in `backup.sh` with `rsync` to a remote host, using `ssh` and the snapshot-via-hardlinks pattern (covered properly in Week 8 — try a sketch now).

---

## Reflection (after completion)

In `notes.md`, after the project is done, answer:

1. Which of the three scripts was hardest? Why?
2. What did you change in your script template (homework problem 1) after writing all three? Update the template; commit the updated version.
3. Run `bash -x ./bin/backup.sh /etc /tmp/test 2>&1 | head -50`. Read the trace. What does `bash -x` show you that ShellCheck doesn't?
4. Pick the script you'd most trust in production and the script you'd least trust. Argue for both choices.

---

## Up next

Once your three scripts are committed and `make test` is green, you're done with Week 4.

[Week 5 — systemd and services](../../week-05/) — where your three scripts run on a schedule, automatically, with logs in `journalctl`. The scripts you wrote today are the units that systemd will manage tomorrow.

---

*A defensive script is not a paranoid script. It's a script that handles the inputs you didn't think of as gracefully as the ones you did.*
