# Lecture 2 — Functions and Trap Signals

> **Duration:** ~2 hours. **Outcome:** You write functions with `local` variables and an explicit return contract; you install an `EXIT` trap that cleans up temp files even on Ctrl-C; you can describe what happens when SIGINT, SIGTERM, and SIGKILL hit your script — and which one you can't catch.

The first lecture made your script *fail correctly*. This lecture makes your script *clean up correctly* when it fails. Two parts: functions as units of structure, and traps as the mechanism that runs your cleanup no matter how the script exits.

Both topics are short. Both are non-obvious enough that production scripts get them wrong constantly. We will set them right.

## 1. Functions

A function in Bash is a named block of code. The syntax has two forms; one is preferred:

```bash
# Preferred form: name() { ... }
greet() {
    echo "Hello, $1!"
}

# Older form: function name { ... }
function greet {
    echo "Hello, $1!"
}
```

Use the first form. It's POSIX-compatible (the `function` keyword is Bash-specific) and the convention in every modern shell style guide.

### 1.1 Local variables — always

Without `local`, every variable inside a function is **global**. This is rarely what you want and is a major source of bugs:

```bash
# WRONG: $tmp is global, leaks to caller
build_tempfile() {
    tmp=$(mktemp)
    echo "$tmp"
}

# Caller:
tmp=/important/data
build_tempfile     # silently overwrites $tmp
rm -rf "$tmp"      # rm -rf /tmp/tmp.aBc12 — but we meant /important/data
```

The fix is the `local` keyword:

```bash
# RIGHT: $tmp is scoped to the function
build_tempfile() {
    local tmp
    tmp=$(mktemp)
    echo "$tmp"
}
```

`local` only works inside a function — it's an error at the top level. **Declare every variable inside a function with `local`** unless you specifically intend to mutate a caller's variable (which you should almost never do).

A subtlety: `local x=$(cmd)` swallows `cmd`'s exit code into `local`'s exit code, which is always 0. Under `set -e`, this defeats the safety:

```bash
# WRONG: $? from cmd is lost
local x=$(cmd_that_might_fail)

# RIGHT: declare and assign separately
local x
x=$(cmd_that_might_fail)
```

ShellCheck flags the wrong form as `SC2155` — "Declare and assign separately to avoid masking return values." Always two lines.

### 1.2 Returning values: exit code vs stdout

Bash functions can return data in two ways. Pick the right one:

- **Exit code (0–255):** for success/failure boolean. Set via `return N`.
- **Stdout (a string):** for arbitrary data. Captured via `$(func)`.

```bash
# Returning success/failure
is_root() {
    [[ $EUID -eq 0 ]]
}

if is_root; then
    echo "Yes, root."
fi

# Returning a string
detect_distro() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        echo "$ID"
    else
        echo "unknown"
    fi
}

distro=$(detect_distro)
```

Do **not** mix the two by trying to return a string via the exit code (which is 0–255 and can only encode small integers). And do **not** print debug output to stdout from a function whose stdout is captured — the captured value will include your debug line. Send debug output to stderr:

```bash
# RIGHT: stderr for diagnostics, stdout for the return value
detect_distro() {
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        printf '%s\n' "$ID"
    else
        printf 'warning: no /etc/os-release found\n' >&2
        printf 'unknown\n'
    fi
}
```

### 1.3 The `main()` pattern

A script that grows past 30 lines should have a `main()` function and call it at the bottom:

```bash
#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

readonly EX_USAGE=64

usage() {
    cat <<'EOF' >&2
Usage: rotate-logs.sh DIR

Rotate logs in DIR. Files older than 30 days are gzipped.
EOF
}

rotate_one() {
    local file="$1"
    gzip -- "$file"
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
        exit "$EX_USAGE"
    fi
    local dir="$1"
    local file
    while IFS= read -r -d '' file; do
        rotate_one "$file"
    done < <(find "$dir" -type f -mtime +30 -print0)
}

main "$@"
```

The benefits:

- The script's entry point is one line: `main "$@"`. Easy to find.
- All logic is in named functions. Easy to read.
- `set -e` works correctly through functions; you can `return 1` from a helper and the script exits.
- Testing becomes easier — you can `source` the file with `main()` guarded:

```bash
# Only run main if invoked directly, not when sourced
if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
    main "$@"
fi
```

### 1.4 The subshell-function form `( )`

Replacing `{ }` with `( )` makes the function body run in a **subshell**:

```bash
# Subshell function — changes to cwd, exported variables, etc. don't leak
safe_cd_and_run() (
    cd "$1"
    ./build.sh
)
```

A subshell function:

- Cannot mutate the caller's variables.
- Has its own current directory, traps, and exit handlers.
- Costs one `fork()` per call.

Use it when isolation is more important than performance. Most functions should use `{ }`; reach for `( )` when you specifically want the subshell sandbox.

## 2. Signals and `trap`

A signal is a message the kernel delivers to a process. The common ones for scripts:

| Signal | Number | Default action | Notes |
|--------|-------:|----------------|-------|
| `SIGHUP`  | 1  | Terminate | Sent when the controlling terminal closes. |
| `SIGINT`  | 2  | Terminate | Ctrl-C from the keyboard. |
| `SIGQUIT` | 3  | Terminate + core dump | Ctrl-\ from the keyboard. |
| `SIGKILL` | 9  | Terminate | **Cannot be caught.** The kernel just kills the process. |
| `SIGTERM` | 15 | Terminate | The polite "please shut down" signal. `kill PID` sends this. |
| `SIGSTOP` | 19 | Stop | Cannot be caught. Pauses the process. |
| `SIGCONT` | 18 | Continue | Resumes a stopped process. |

Plus two Bash pseudo-signals:

| Pseudo | Trigger |
|--------|---------|
| `EXIT` | The shell is about to exit, for any reason — clean exit, signal, error, set -e. |
| `ERR`  | A command returned non-zero (only if `set -e` is in effect or `trap ERR` is set). |

The list is in `man 7 signal` (or `kill -l` for your shell's view).

### 2.1 The `trap` builtin

```bash
trap 'COMMAND' SIGNAL [SIGNAL ...]
```

Register `COMMAND` to run when `SIGNAL` is delivered. The classic cleanup pattern:

```bash
#!/usr/bin/env bash
set -euo pipefail

TMPDIR=$(mktemp -d)
trap 'rm -rf -- "$TMPDIR"' EXIT

# ... do work in $TMPDIR ...
```

What this guarantees:

- Normal exit: `EXIT` fires, `rm -rf $TMPDIR` runs.
- Error (set -e abort): `EXIT` fires, `rm -rf $TMPDIR` runs.
- Ctrl-C (SIGINT): Bash receives the signal, exits, `EXIT` fires, `rm -rf $TMPDIR` runs.
- `kill PID` (SIGTERM): same, `EXIT` fires, cleanup runs.

The one case it doesn't catch: `kill -9` (SIGKILL). The kernel kills the process before any cleanup runs. There is no defense against SIGKILL — by design.

### 2.2 Wrong vs right cleanup

```bash
# WRONG: only cleans up on success
mkdir /tmp/scratch.$$
do_work /tmp/scratch.$$
rm -rf /tmp/scratch.$$
```

If `do_work` fails (under `set -e`) or you Ctrl-C, the cleanup is skipped. `/tmp/scratch.$$` is left behind. Run the script ten times, get ten leaked directories.

```bash
# RIGHT: trap cleans up unconditionally
set -euo pipefail
TMPDIR=$(mktemp -d)
trap 'rm -rf -- "$TMPDIR"' EXIT
do_work "$TMPDIR"
```

The `mktemp -d` form is itself important — it creates a directory with an unguessable random name, in `$TMPDIR` (or `/tmp` if `$TMPDIR` isn't set), with mode 0700. No race condition, no name collision, no readable-by-the-world contents.

### 2.3 A multi-handler example

You can register handlers for multiple signals:

```bash
cleanup() {
    local exit_code=$?
    rm -rf -- "$TMPDIR" || true
    echo "Exiting with code $exit_code" >&2
}

on_interrupt() {
    echo "Interrupted. Cleaning up..." >&2
    exit 130   # 128 + SIGINT(2) — the conventional code
}

trap cleanup EXIT
trap on_interrupt INT TERM
```

Notes:

- The `EXIT` trap fires last, after any signal handler that ends with `exit`. So `on_interrupt` calls `exit 130`, which triggers `EXIT`, which runs `cleanup`. Both handlers run.
- `$?` inside the trap is the exit code of the most-recent command — capture it at the top of the handler.
- The `|| true` after `rm -rf` keeps the cleanup from failing under `set -e` if the directory was already removed.

### 2.4 The `ERR` trap

```bash
trap 'echo "Error on line $LINENO" >&2' ERR
```

`ERR` fires whenever a command returns non-zero, before `set -e` triggers the exit. Useful for printing context — the line number, the command, the variables — when something goes wrong.

The caveat: `ERR` has the same exemptions as `set -e`. It doesn't fire inside an `if` test, a `&&` chain, a function called from `&&`, etc. Read BashFAQ #105 for the full list: <https://mywiki.wooledge.org/BashFAQ/105>.

### 2.5 Re-raising a signal

If your handler does cleanup and you want the script to exit *as if* the signal had killed it (preserving the exit code convention 128+N), the pattern is:

```bash
on_interrupt() {
    cleanup
    trap - INT          # reset the INT trap to default
    kill -INT $$        # re-send INT to ourselves
}
trap on_interrupt INT
```

Three steps: clean up, restore the default handler, re-deliver the signal. Now the parent shell sees the script exit as if it had been Ctrl-C'd, which is the truth.

For most scripts, `exit 130` is sufficient and simpler. Re-raise only when the calling context cares about the exact exit-code convention.

## 3. `mktemp` and `flock`

Two utilities every defensive script reaches for.

### 3.1 `mktemp` — safe temp files

```bash
# A single temp file
tmpfile=$(mktemp)
trap 'rm -f -- "$tmpfile"' EXIT

# A temp directory
tmpdir=$(mktemp -d)
trap 'rm -rf -- "$tmpdir"' EXIT

# With a template (helps debugging — name includes purpose)
tmpfile=$(mktemp --tmpdir my-backup.XXXXXX)
```

The `XXXXXX` (at least 6 X's) gets replaced with random characters. The default `$TMPDIR` is `/tmp`; override with `--tmpdir=DIR` if you need a temp file on the same filesystem as a target (for `mv`-as-atomic-rename).

Do **not** invent your own temp names with `$$` (the PID). Two processes can have the same PID on different runs. Two processes with the same PID can race on `test -e`. Use `mktemp`.

### 3.2 `flock` — single-instance scripts

A backup script that takes 20 minutes should not have two copies running at once. `flock` (from `util-linux`) wraps a script in a file-lock mutex:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Re-exec under flock if not already locked
exec 9>/var/lock/my-backup.lock
flock --nonblock 9 || { echo "Another instance is running" >&2; exit 75; }

# The lock is held for the rest of the script; released on exit.
do_backup
```

Three lines, one guarantee. Notes:

- File descriptor 9 is an arbitrary choice; pick anything >2 and <255 that you're not otherwise using.
- `--nonblock` (`-n`) makes `flock` exit immediately with code 1 if the lock is held. Drop the flag to wait for the lock.
- Exit code 75 corresponds to `EX_TEMPFAIL` from `sysexits.h` — "the action might succeed if retried later." A reasonable convention for "another copy is running."
- The lock is held by the file descriptor, which Bash closes on exit. No trap needed; the kernel releases the lock when the process dies.

## 4. The full defensive script template

Take everything from this lecture and the last, and you get this template. Save it as `~/c14-week-04/template.sh`:

```bash
#!/usr/bin/env bash
#
# template.sh — one-line description.
#
# Usage:
#   template.sh [-v] ARG1 ARG2
#
# Exit codes:
#   0  — success
#   64 — wrong usage
#   75 — another instance running
#   77 — permission denied

set -euo pipefail
IFS=$'\n\t'

# ---------- Constants ----------
readonly SCRIPT_NAME="${0##*/}"
readonly LOCKFILE="/var/lock/${SCRIPT_NAME}.lock"
readonly EX_USAGE=64
readonly EX_TEMPFAIL=75
readonly EX_NOPERM=77

# ---------- Logging ----------
log()  { printf '[%s] %s\n' "$(date -Iseconds)" "$*" >&2; }
die()  { log "ERROR: $*"; exit 1; }

# ---------- Usage ----------
usage() {
    cat <<EOF >&2
Usage: $SCRIPT_NAME [-v] ARG1 ARG2

  -v   verbose output
EOF
}

# ---------- Cleanup ----------
cleanup() {
    local exit_code=$?
    [[ -n ${TMPDIR:-} && -d ${TMPDIR:-} ]] && rm -rf -- "$TMPDIR"
    log "Exiting with code $exit_code"
}

# ---------- Main ----------
main() {
    local verbose=0
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -v) verbose=1; shift ;;
            -h|--help) usage; exit 0 ;;
            --) shift; break ;;
            -*) usage; exit "$EX_USAGE" ;;
            *)  break ;;
        esac
    done
    if [[ $# -ne 2 ]]; then
        usage
        exit "$EX_USAGE"
    fi
    local arg1="$1"
    local arg2="$2"

    # Single-instance lock
    exec 9>"$LOCKFILE"
    flock --nonblock 9 || die "another instance is running"

    # Temp area + cleanup trap
    TMPDIR=$(mktemp -d)
    trap cleanup EXIT

    (( verbose )) && log "Running with arg1=$arg1, arg2=$arg2"

    # ... your work here ...
}

main "$@"
```

Roughly 70 lines. Every script in the mini-project this week is a specialization of this template.

## 5. Common cleanup mistakes

Five mistakes worth flagging explicitly.

### 5.1 Trap registered too late

```bash
# WRONG
TMPDIR=$(mktemp -d)
do_long_thing       # if Ctrl-C hits here, no cleanup
trap 'rm -rf -- "$TMPDIR"' EXIT
```

Register the trap **immediately** after creating the resource it cleans up. Atomically, if you can:

```bash
# RIGHT
TMPDIR=$(mktemp -d) && trap 'rm -rf -- "$TMPDIR"' EXIT
```

### 5.2 Cleanup that uses an unset variable

```bash
# WRONG (under set -u)
trap 'rm -rf "$TMPDIR"' EXIT
exit 0   # $TMPDIR was never set; trap runs `rm -rf ""`, prints error
```

Guard the cleanup:

```bash
# RIGHT
trap 'if [[ -n ${TMPDIR:-} && -d ${TMPDIR:-} ]]; then rm -rf -- "$TMPDIR"; fi' EXIT
```

### 5.3 Multiple traps on the same signal

`trap CMD EXIT` **replaces** any existing trap for EXIT. If you want to add a handler, you must compose by hand:

```bash
# WRONG: clobbers earlier trap
trap 'echo step1' EXIT
trap 'echo step2' EXIT   # only step2 runs

# RIGHT: chain via a function
cleanup() {
    echo step1
    echo step2
}
trap cleanup EXIT
```

### 5.4 Forgetting `--` before user-controlled paths in cleanup

```bash
# WRONG: if $TMPDIR somehow starts with -, rm interprets it as a flag
trap 'rm -rf "$TMPDIR"' EXIT

# RIGHT
trap 'rm -rf -- "$TMPDIR"' EXIT
```

The `--` is a sentinel that says "no more flags, the rest are arguments." Almost every command accepts it. Use it whenever a variable expansion follows the command.

### 5.5 Cleaning up partial output without atomicity

If your script generates an output file, write to a temp name and `mv` only on success:

```bash
# WRONG: partial output left behind on failure
generate > /var/lib/myapp/data.json

# RIGHT: atomic rename
local tmp
tmp=$(mktemp --tmpdir=/var/lib/myapp data.json.XXXXXX)
trap 'rm -f -- "$tmp"' EXIT
generate > "$tmp"
mv -- "$tmp" /var/lib/myapp/data.json
trap - EXIT   # mv succeeded; nothing to clean
```

`mv` within a single filesystem is atomic — the rename either fully succeeds or doesn't happen. Consumers of `data.json` never see a half-written file.

## 6. Quick recall

After this lecture you should be able to answer, without notes:

- What does `local` do, and why is `local x=$(cmd)` worse than `local x; x=$(cmd)`?
- Which pseudo-signal lets you register a "runs no matter how the script exits" handler? What's the one signal you cannot catch?
- When you Ctrl-C a Bash script, what's the chain of events between the keypress and the EXIT trap?
- What does `mktemp -d` give you that a hand-rolled `mkdir /tmp/scratch.$$` doesn't?
- How does `flock --nonblock 9 || exit 75` enforce single-instance, and why is exit code 75?

If any of these stalled, re-read the relevant section. Now go write a script that uses every pattern above — that's [exercise 02](../03-exercises/exercise-02-trap-and-cleanup.md).

---

*Two lectures down. Now you write code, you break code, and you run ShellCheck until ShellCheck stops finding things.*
