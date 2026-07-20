# Week 4 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-04/homework/`.

These are practice problems between the exercises (which drilled the basics) and the mini-project (which asks you to compose freely). Treat them as fluency reps. Every script you write here must pass `shellcheck` with zero warnings.

---

## Problem 1 — Build your script template (45 min)

Write `homework/01-template.sh` — a generic starter you will copy for every script for the rest of your career. It must include:

- The four-line opener (`#!/usr/bin/env bash`, `set -euo pipefail`, `IFS=$'\n\t'`, plus shebang).
- A header comment block: filename, one-line description, usage example, exit-code table.
- Named exit-code constants (at least `EX_USAGE=64`, `EX_NOINPUT=66`, `EX_TEMPFAIL=75`, `EX_NOPERM=77`).
- A `usage()` function that prints to stderr.
- A `log()` function that prefixes with `[ISO timestamp]` and prints to stderr.
- A `die()` function that calls `log` and then `exit 1`.
- A `cleanup()` function and `trap cleanup EXIT`.
- A `main()` function that parses one positional arg and one optional `-v` flag.
- `main "$@"` at the bottom.

**Acceptance:** Save the template. `shellcheck 01-template.sh` is clean. The template runs (`./01-template.sh somearg`) without errors. Use it as the starting point for every other problem in this homework.

---

## Problem 2 — Argument parser (60 min)

Write `homework/02-parse.sh` — a script that demonstrates a full argument parser with positional arguments and flags.

**Specification:**

- Usage: `./02-parse.sh [-v] [-o OUTFILE] [--retries N] INPUT [INPUT ...]`
- `-v` is a boolean flag (verbose).
- `-o OUTFILE` takes one argument.
- `--retries N` is a GNU-style long option with an argument; default `3`.
- After flags, one or more positional `INPUT` arguments.
- Support `--` as the end-of-flags marker.
- Print, in this exact format, what was parsed:

```
verbose=1
output=/tmp/out.txt
retries=5
inputs:
  - file1
  - file2
```

**Wrong vs right reference for flag parsing:**

```bash
# WRONG: doesn't handle --, doesn't handle -- separator, fragile
if [ "$1" = "-v" ]; then VERBOSE=1; shift; fi
if [ "$1" = "-o" ]; then OUTPUT=$2; shift 2; fi
# ... etc, fragile and order-dependent
```

```bash
# RIGHT: a single while loop
verbose=0; output=""; retries=3
while [[ $# -gt 0 ]]; do
    case "$1" in
        -v) verbose=1; shift ;;
        -o) output="$2"; shift 2 ;;
        --retries) retries="$2"; shift 2 ;;
        --retries=*) retries="${1#--retries=}"; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        -*) echo "Unknown flag: $1" >&2; exit 64 ;;
        *) break ;;
    esac
done
# After the loop, $@ contains the positional args
```

**Tests:**

```bash
./02-parse.sh -v file1
./02-parse.sh -o out.txt --retries 5 file1 file2
./02-parse.sh --retries=10 -- -file-starting-with-dash.txt
./02-parse.sh                              # exit 64, usage to stderr
./02-parse.sh --unknown                    # exit 64
```

**Acceptance:** Script. `02-notes.md` with the five test invocations and their outputs.

---

## Problem 3 — Idempotent setup script (60 min)

Write `homework/03-setup.sh` — a script that configures a scratch environment, idempotently. Re-running it must be a no-op.

**Specification:**

- Creates `~/c14-week-04/scratch/` with subdirectories `bin/`, `logs/`, `data/`.
- Drops a `~/c14-week-04/scratch/README.md` file with a generated header (timestamp).
- Drops a `~/c14-week-04/scratch/bin/version.sh` file that prints the script's own version.
- If any of these exist already and match the expected content, leaves them alone.
- If any exist but differ, prompts (or with `-f` overrides without prompt).
- Prints a one-line summary per artifact: `[OK] path` (already correct) or `[CREATED] path` or `[UPDATED] path`.

The wrong way (not idempotent — runs twice produce errors):

```bash
mkdir ~/c14-week-04/scratch                  # fails second time
mkdir ~/c14-week-04/scratch/bin
echo "stuff" >> ~/c14-week-04/scratch/README.md   # appends every time
```

The right way:

```bash
mkdir -p -- "$ROOT" "$ROOT/bin" "$ROOT/logs" "$ROOT/data"
if [[ -f $ROOT/README.md ]] && diff -q <(generate_readme) "$ROOT/README.md" >/dev/null; then
    echo "[OK] $ROOT/README.md"
else
    generate_readme > "$ROOT/README.md"
    echo "[CREATED] $ROOT/README.md"
fi
```

**Tests:**

```bash
./03-setup.sh         # all CREATED
./03-setup.sh         # all OK
echo "manual edit" >> ~/c14-week-04/scratch/README.md
./03-setup.sh         # prompts (or with -f, UPDATED)
```

**Acceptance:** Script. `03-notes.md` showing the three runs.

---

## Problem 4 — Defensive `cp` wrapper (45 min)

Write `homework/04-safe-cp.sh` — a wrapper around `cp` that:

- Refuses to copy over an existing destination unless `-f` is given.
- Prints a clear error for missing source.
- Handles filenames with spaces, newlines, and leading dashes.
- Computes and prints the sha256 of the source and destination after copy; aborts with exit 74 if they differ.

**Spec:**

- Usage: `./04-safe-cp.sh [-f] SOURCE DEST`
- Exit codes: 0 success, 64 wrong usage, 66 source missing, 73 dest exists without `-f`, 74 sha256 mismatch.

**Acceptance:** Script. `04-notes.md` with at least three test cases including one with a space in the filename and one with a leading dash.

---

## Problem 5 — Log filter with traps (60 min)

Write `homework/05-tail-errors.sh` — a script that tails one or more log files and prints any line matching a configurable regex (default: `(?i)error|fatal|panic`).

**Specification:**

- Usage: `./05-tail-errors.sh [-p PATTERN] FILE [FILE ...]`
- Uses `tail -F` (so it survives log rotation).
- On `Ctrl-C`, prints "Stopped. Tailed N lines total." to stderr and exits 130.
- Uses `trap` to register the cleanup handler. Counts lines via a global counter, which the trap reads.
- ShellCheck-clean.

The trick: `tail -F file | grep -E PATTERN` is a pipeline; the `grep` runs in a subshell. Variables modified in `grep`'s `awk` filter don't survive. You'll need to either use a `while read` loop instead of `grep`, or have the script accumulate stats from `wc -l`.

```bash
# Pattern (one approach)
count=0
on_exit() {
    echo "Stopped. Tailed $count matching lines total." >&2
}
trap on_exit EXIT

while IFS= read -r line; do
    count=$((count + 1))
    printf '%s\n' "$line"
done < <(tail -F -- "${@}" 2>/dev/null | grep --line-buffered -Ei "$pattern")
```

**Tests:**

```bash
# In one terminal:
./05-tail-errors.sh test.log

# In another:
for i in {1..5}; do echo "INFO: msg $i" >> test.log; sleep 1; done
echo "ERROR: thing broke" >> test.log
echo "FATAL: dead" >> test.log

# Back in the first terminal: Ctrl-C
# Expected: "Stopped. Tailed 2 matching lines total."
```

**Acceptance:** Script. `05-notes.md` with the test transcript and a paragraph on why the `grep | while` form keeps `count` alive (hint: which shell does the `while` body run in?).

---

## Problem 6 — Reflection (90 min)

`homework/06-reflection.md`, 500-700 words:

1. Of `set -e`, `set -u`, and `set -o pipefail`, which one would catch the largest fraction of bugs in code you've written *before* this week? Walk through one specific example from your history.
2. Pick three BashPitfalls (1, 3, 14, 17, 23 — any three). For each, write the wrong form, the right form, and a real scenario where you saw (or could imagine) the wrong form in production.
3. ShellCheck found warnings in [exercise 03](./exercises/exercise-03-shellcheck-fixes.md). Which warning surprised you? Which one had you been "getting away with" before?
4. The lecture claimed: "There is no defense against SIGKILL — by design." Is this entirely true? (Hint: think about `systemd` `KillSignal=` configuration, or the `prctl(PR_SET_PDEATHSIG)` syscall for child cleanup, or `init` itself.) Two or three sentences.
5. Cite the Bash Yellow caution line at the top of your favorite lecture from this week. (Loyalty test repeats.)
6. The mini-project will ask you to write three independent scripts. Sketch what each one's `cleanup()` function will need to remove.

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 1 h |
| 3 | 1 h |
| 4 | 45 min |
| 5 | 1 h |
| 6 | 1.5 h |
| **Total** | **~6 h** |

After homework, ship the [mini-project](./mini-project/README.md).
