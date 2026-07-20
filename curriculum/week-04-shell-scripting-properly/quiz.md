# Week 4 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 5.

---

**Q1.** Which line should appear at the top of every new Bash script you write?

- A) `#!/bin/sh` followed by `set -e`
- B) `#!/usr/bin/env bash` followed by `set -euo pipefail`
- C) `#!/bin/bash --norc`
- D) `#!/usr/bin/bash -e`

---

**Q2.** Under `set -o pipefail`, what is the exit code of `false | true`?

- A) 0 — the last command succeeded.
- B) 1 — `false` returned 1, and pipefail propagates it.
- C) 2 — pipeline failure code.
- D) Undefined; it depends on the Bash version.

---

**Q3.** Why is `for f in $(ls /var/log); do ...; done` flagged as BashPitfalls #1?

- A) `ls` is deprecated; use `find` instead.
- B) Command substitution is slow.
- C) `ls` output is word-split, breaking on filenames containing whitespace, newlines, or glob characters; use a glob (`for f in /var/log/*`) instead.
- D) The `$(...)` form requires Bash 4.0+.

---

**Q4.** Which trap fires whenever the shell exits, for any reason — clean exit, signal, error, or `set -e` abort?

- A) `trap CMD ERR`
- B) `trap CMD INT`
- C) `trap CMD EXIT`
- D) `trap CMD TERM`

---

**Q5.** You write `local x=$(some_command)` inside a function. ShellCheck flags `SC2155`. What's the bug?

- A) `local` is not a POSIX builtin.
- B) The exit code of `some_command` is swallowed by `local`'s exit code (always 0), defeating `set -e`.
- C) `local` requires `=` to be surrounded by spaces.
- D) Command substitution is forbidden inside `local`.

---

**Q6.** A script does:

```bash
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
# ... work ...
```

What happens if the script is killed with `kill -9 PID` (SIGKILL)?

- A) The `EXIT` trap runs; `$TMPDIR` is removed.
- B) The `EXIT` trap runs after a delay.
- C) The kernel kills the process before any handler can run; `$TMPDIR` is left in `/tmp`.
- D) SIGKILL is ignored by Bash; the script continues.

---

**Q7.** Which of these is the safe way to iterate over a directory's files, robust to filenames with spaces and newlines?

- A) `for f in $(ls $DIR); do ...; done`
- B) `for f in $DIR/*; do ...; done`
- C) `while IFS= read -r -d '' f; do ...; done < <(find "$DIR" -type f -print0)`
- D) Both B and C are safe; A is the textbook wrong answer.

---

**Q8.** What does ShellCheck `SC2086` mean, and what's the fix?

- A) "Use `printf` instead of `echo`." Fix: replace `echo` with `printf`.
- B) "Variable assigned but never used." Fix: delete the variable.
- C) "Double-quote to prevent globbing and word splitting." Fix: `"$var"` instead of `$var`.
- D) "Command not found." Fix: install the package.

---

**Q9.** What's the difference between `$@` (unquoted) and `"$@"` (quoted) when used as `for arg in $@; do ...; done` versus `for arg in "$@"; do ...; done`?

- A) None — they behave identically.
- B) `$@` is for arrays, `"$@"` is for positional parameters.
- C) `$@` word-splits each argument, breaking arguments that contain spaces; `"$@"` preserves each argument as a single word.
- D) `"$@"` is only valid inside `[[ ]]`.

---

**Q10.** You want to ensure only one copy of `backup.sh` runs at a time on a system. Which approach is the canonical one?

- A) Write a `.pid` file; check on startup if the PID is alive.
- B) Wrap the script with `flock` on a lockfile (`exec 9>/var/lock/backup.lock; flock -n 9 || exit 75`).
- C) Use `pgrep backup.sh` to check; exit if another copy is found.
- D) Rely on cron to never schedule overlapping runs.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **B** — the `env` form finds Bash on `$PATH` (matters on macOS where `/bin/bash` is 3.2); `set -euo pipefail` is the three-flag opener.
2. **B** — without `pipefail`, the exit is 0 (last command's). With `pipefail`, the rightmost non-zero is returned — here, `false`'s 1.
3. **C** — `ls`'s output goes through word-splitting on `$IFS`. Filenames with space, tab, newline, or glob characters break. The fix is a glob or `find -print0`.
4. **C** — `EXIT` is the pseudo-signal that fires unconditionally on shell exit. The other three fire on specific signals or errors.
5. **B** — `local x=$(cmd)` is two operations in one. `local` always returns 0, masking `cmd`'s exit code. `set -e` therefore won't catch the failure. Always: `local x; x=$(cmd)`.
6. **C** — SIGKILL is delivered by the kernel directly, before the process can run any handler. The cleanup never runs. This is by design and there's no defense.
7. **D** — both globs (B) and `find -print0 | read -d ''` (C) handle hostile filenames correctly. The `$(ls)` form (A) is BashPitfalls #1.
8. **C** — the most-flagged warning. The fix is "double-quote to prevent globbing and word splitting." Every unquoted variable is a potential bug.
9. **C** — `"$@"` is a special syntax. Each positional argument is preserved as one word; word-splitting is suppressed on the *contents* of each one. The unquoted `$@` splits everything.
10. **B** — `flock` is the canonical answer. The lock is released by the kernel when the process dies (even on SIGKILL); `.pid` files become stale, `pgrep` is racy, cron has no enforcement.

</details>

If you scored 9+: move to homework. 7–8: re-read the lecture sections you missed (especially `set -e` exemptions and the trap chain). <7: re-read both lectures from the top.
