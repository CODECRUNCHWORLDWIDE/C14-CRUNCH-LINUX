# Exercise 02 — Trap and Cleanup

**Time:** ~1.5 hours. **Goal:** Build a script that creates a temp directory, does some work in it, and uses a `trap` to clean up — then deliberately try to break the cleanup. Learn what `trap EXIT` catches and what it doesn't.

Setup:

```bash
mkdir -p ~/c14-week-04/exercises/02
cd ~/c14-week-04/exercises/02
```

---

## Part A — Build `slow-work.sh` (30 min)

Write a script that simulates "slow work":

**Specification:**

- Creates a temp directory via `mktemp -d`.
- Writes 10 files into it, sleeping 1 second between each.
- After all 10 files exist, prints "Done" and exits.
- Installs a `trap` on `EXIT` that prints `Cleaning up: $TMPDIR` to stderr and removes the directory.

The first draft:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

TMPDIR=$(mktemp -d)
trap 'echo "Cleaning up: $TMPDIR" >&2; rm -rf -- "$TMPDIR"' EXIT

for i in {1..10}; do
    touch -- "$TMPDIR/file-$i.txt"
    echo "Wrote file-$i.txt"
    sleep 1
done

echo "Done"
```

Run it:

```bash
./slow-work.sh
```

You should see ten "Wrote file-N.txt" lines, then "Done", then "Cleaning up: /tmp/tmp.XXXXXX" on stderr. Verify the directory is gone:

```bash
./slow-work.sh
ls /tmp/tmp.*    # should not include the directory you saw
```

---

## Part B — Break it on purpose (45 min)

Now we deliberately interrupt the script and observe what happens. For each scenario below, run the script, interrupt it, and verify cleanup.

### Scenario 1 — Ctrl-C (SIGINT)

Run the script. After three or four files have been written, press **Ctrl-C**.

```bash
./slow-work.sh
# Wait for "Wrote file-3.txt", then Ctrl-C
```

Expected:

- "Cleaning up: $TMPDIR" appears on stderr.
- The temp directory is removed.

Verify the directory is gone:

```bash
ls /tmp/tmp.*  # should not include the interrupted run's tempdir
```

Write in `notes.md` what exit code the shell got. Hint: it's not 0, not 1, and not 2. Look up "shell exit code when killed by signal."

### Scenario 2 — SIGTERM (the polite kill)

Start the script in the background:

```bash
./slow-work.sh &
PID=$!
sleep 3
kill "$PID"           # SIGTERM by default
wait "$PID" || true
```

Expected: same outcome as Ctrl-C. Cleanup runs, directory is gone.

### Scenario 3 — SIGHUP (terminal closed)

This is the scenario behind "I closed my SSH session and my script died, did it clean up?"

```bash
./slow-work.sh &
PID=$!
sleep 3
kill -HUP "$PID"
wait "$PID" || true
```

Expected: same outcome. SIGHUP is caught by the EXIT trap.

### Scenario 4 — SIGKILL (the uncatchable signal)

```bash
./slow-work.sh &
PID=$!
sleep 3
kill -KILL "$PID"
wait "$PID" || true

# Now check /tmp
ls -d /tmp/tmp.* 2>/dev/null
```

Expected: **the temp directory is left behind.** SIGKILL is delivered by the kernel directly; the process never gets a chance to run any handler. Note in `notes.md` what was left behind and explain why this is unavoidable.

### Scenario 5 — Script error (set -e abort)

Edit `slow-work.sh` to inject a failure on the 5th iteration:

```bash
for i in {1..10}; do
    touch -- "$TMPDIR/file-$i.txt"
    echo "Wrote file-$i.txt"
    if [[ $i -eq 5 ]]; then
        false   # forces non-zero exit; set -e aborts
    fi
    sleep 1
done
```

Run it. Expected: the script aborts on iteration 5; the EXIT trap fires; the temp directory is removed.

Remove the injected `false` before continuing.

---

## Part C — A more realistic cleanup (30 min)

Real scripts often have **partial output to clean up**, not just a temp directory. Write `partial-output.sh`:

**Specification:**

- Takes one argument: an output file path.
- Generates 100 lines of `RANDOM` integers into a temp file, sleeping 100ms between each.
- On successful completion, atomically `mv` the temp file to the destination.
- On any failure or interrupt, the temp file is removed; the destination is **not** touched.

**Wrong vs right reference:**

The wrong way:

```bash
# WRONG: writes directly to the destination; partial output left on Ctrl-C
for i in {1..100}; do
    echo "$RANDOM" >> "$1"
    sleep 0.1
done
```

If you Ctrl-C halfway, the destination has 50 lines. A consumer reading that file sees corruption.

The right way:

```bash
# RIGHT: write to temp, atomic-rename on success
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

if [[ $# -ne 1 ]]; then echo "Usage: $0 OUTPUT" >&2; exit 64; fi
dest="$1"
destdir=$(dirname -- "$dest")

# Temp file on the same filesystem as $dest (so mv is atomic)
tmp=$(mktemp --tmpdir="$destdir" .partial.XXXXXX)
trap 'rm -f -- "$tmp"' EXIT

for i in {1..100}; do
    echo "$RANDOM" >> "$tmp"
    sleep 0.1
done

mv -- "$tmp" "$dest"
trap - EXIT   # mv succeeded; nothing left to clean
echo "Wrote $dest"
```

**Tests:**

```bash
# Run to completion
./partial-output.sh out.txt
wc -l out.txt   # 100

# Now run again, Ctrl-C halfway
./partial-output.sh out.txt
# Ctrl-C after ~5 seconds
# Verify: out.txt from the previous successful run is untouched
wc -l out.txt   # still 100, NOT 50

# Verify no leaked temp files
ls .partial.* 2>/dev/null   # should be empty
```

**The key insight:** the destination file `out.txt` either has the *previous* successful run's content, or the *new* run's content. It never has a half-written mix. This is the atomic-rename pattern and it's the foundation of every safe "update a config file" or "write a backup index" operation in shell.

---

## Wrap-up

Acceptance:

- `slow-work.sh` cleans up on Ctrl-C, SIGTERM, SIGHUP, and set -e abort.
- `slow-work.sh` does **not** clean up on SIGKILL — and you can explain why.
- `partial-output.sh` writes atomically; the destination never sees a partial file.
- `shellcheck *.sh` is clean.
- `notes.md` includes:
  - The exit code Bash reports after Ctrl-C (and the 128+N convention).
  - One sentence on why `trap EXIT` is preferable to `trap INT TERM HUP` separately.
  - One sentence on why atomic rename requires the temp file to be on the **same filesystem** as the destination.

Commit. Move to [exercise 03](./exercise-03-shellcheck-fixes.md).
