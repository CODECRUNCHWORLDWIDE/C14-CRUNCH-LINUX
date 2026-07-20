# Week 4 — Shell Scripting Properly

> *Almost every "weird Bash bug" in production traces to two missing characters: a quote, or a `set -e`. This week we add both, and a dozen other small habits, until the scripts you write today still work when a filename contains a space, a backup partition is full, and a network call hangs at 03:00.*

Welcome to **Week 4 of C14 · Crunch Linux**. The first three weeks taught you to live in the shell — navigate, pipe, and lock things down. This week we promote shell from "what I type" to "what runs unattended." The discipline of writing scripts that don't surprise you, even when the world surprises them.

If Week 1 was the keyboard and Week 2 was the pipeline and Week 3 was the permission bit, Week 4 is the **`set -euo pipefail`** and the **double quote**. Two cheap habits that prevent more outages than any other Bash trivia combined. We will earn them by writing scripts that fail correctly, by breaking scripts that fail incorrectly, and by feeding everything through ShellCheck until ShellCheck stops complaining.

## Learning objectives

By the end of this week, you will be able to:

- **Open every script you write with `#!/usr/bin/env bash` and `set -euo pipefail`** — and explain what each of `-e`, `-u`, `-o pipefail` does, and the cases where each one is insufficient on its own.
- **Quote everything** — variables, command substitutions, glob expansions — and recognize the four canonical word-splitting bugs in unquoted code on sight.
- **Choose** `[[ ]]` over `[ ]` for all new Bash code, and know the three things `[[` does that `[` cannot: pattern matching, regex, no word-splitting inside the brackets.
- **Write functions** with `local` variables, explicit `return` codes, and a documented contract for stdin / stdout / stderr.
- **Trap signals** (`EXIT`, `INT`, `TERM`, `ERR`) and write cleanup code that runs on success, on Ctrl-C, on `kill`, and on `set -e` failure — all four paths.
- **Run** ShellCheck (`shellcheck script.sh`) on every script before committing, read its warnings, and either fix them or annotate the deliberate exception with the documented `# shellcheck disable=SCxxxx` form.
- **Recognize** the Bash pitfalls that BashGuide and Greg's Wiki document: `for f in $(ls)`, `cat file | while read`, `if [ $foo = "bar" ]`, `[[ -n $UNSET ]]`, and the others — and rewrite each one safely.
- **Compose** a script with proper argument parsing (positional + flags), a usage function, an exit-code contract, and stderr / stdout separation that downstream pipelines can rely on.
- **Reach** for `mktemp`, `flock`, and `IFS=` when the situation calls for them, instead of inventing temp-file or lock-file schemes by hand.

## Prerequisites

- **Weeks 1, 2, and 3 of C14** completed. You can navigate, pipe, and reason about who-can-do-what.
- A working Ubuntu 24.04 LTS or Fedora 41 environment. This week we target **Bash 5.2+** (Ubuntu 24.04 ships 5.2.21; Fedora 41 ships 5.2.32). Older Bash versions have subtly different behavior for `[[ ]]` regex and associative arrays.
- `shellcheck` installed: `sudo apt install shellcheck` on Ubuntu, `sudo dnf install ShellCheck` on Fedora. Confirm with `shellcheck --version` — we expect 0.9.0+.
- A scratch directory for the week's scripts — e.g., `~/c14-week-04/scripts/`. Several exercises deliberately produce scripts that fail; isolate them from anything you care about.

## Topics covered

- **The three-flag opener:** `set -e` (exit on error), `set -u` (error on unset variable), `set -o pipefail` (a pipeline's exit code is the rightmost non-zero exit, not just the last command's). Why all three matter. Why `set -e` alone is famously not enough.
- **Quoting:** the double quote as default, the single quote for literals, the dollar-curly form `"${var}"` versus the bare form `"$var"`, and when each matters. Why `$@` and `"$@"` are different worlds.
- **Word-splitting and globbing:** the rules Bash applies to unquoted text. `IFS`. The "filename has a space" bug. The "filename starts with a dash" bug.
- **`[[ ]]` versus `[ ]` versus `test`:** the three forms, the gotchas, the reason `[[` exists in Bash. `=~` regex. `==` glob pattern matching. The `&&` and `||` chaining inside `[[`.
- **Conditionals and loops the safe way:** `while IFS= read -r line; do ... done < file`. `find ... -print0 | xargs -0`. Why `for f in $(ls)` is in BashPitfalls #1.
- **Functions:** declaration, `local` variables, returning exit codes, returning strings via stdout, the `( )` subshell-function form, when to use each.
- **Trap signals:** `trap CMD SIGNAL`. The pseudo-signals `EXIT`, `ERR`, `DEBUG`, `RETURN`. The cleanup-on-exit pattern. Why `trap '' INT` is rude.
- **`mktemp` and the cleanup trap:** the canonical pattern for a script that needs a temp file or temp directory and must not leak it.
- **`flock` and single-instance scripts:** how to prevent two copies of your backup script from running concurrently on the same data.
- **Exit codes:** the convention (0 success, 1 generic failure, 2 misuse, 64-78 sysexits.h, 126-128 shell-specific). Why `exit 1` everywhere loses information.
- **Argument parsing:** positional vs flags. The `while [[ $# -gt 0 ]]` pattern. Why `getopts` is fine and `getopt` (GNU) is a different beast.
- **ShellCheck:** what it catches, what it doesn't, how to read SC codes, the `# shellcheck disable=` annotation, and the wiki page for every warning.
- **stdout vs stderr discipline:** scripts that pipe cleanly. The `>&2` redirect. The `log()` function pattern.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                          | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | `set -euo pipefail`, quoting lecture           |    3h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Tuesday   | `[[ ]]` drills, ShellCheck onboarding          |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Wednesday | Functions and traps lecture                    |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Thursday  | Rewrite-bad-script challenge; design mini-proj |    0h    |    1h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Argument parsing, exit codes, polish homework  |    0h    |    1.5h   |     0h     |    0.5h   |   2h     |     1h       |    0h      |     5h      |
| Saturday  | Mini-project — three useful scripts            |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                              |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                                | **6h**   | **8.5h**  | **4h**     | **3h**    | **6h**   | **7h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | BashGuide, BashPitfalls, ShellCheck, and the references we cite |
| [lecture-notes/01-set-euo-pipefail-and-quoting.md](./lecture-notes/01-set-euo-pipefail-and-quoting.md) | The three-flag opener, quoting, `[[ ]]`, ShellCheck |
| [lecture-notes/02-functions-and-trap-signals.md](./lecture-notes/02-functions-and-trap-signals.md) | Functions, traps, cleanup patterns, `mktemp`, `flock` |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-write-3-defensive-scripts.md](./exercises/exercise-01-write-3-defensive-scripts.md) | Three small scripts, each one a defensive-coding drill |
| [exercises/exercise-02-trap-and-cleanup.md](./exercises/exercise-02-trap-and-cleanup.md) | Build a script with a trap-driven cleanup, then try to break it |
| [exercises/exercise-03-shellcheck-fixes.md](./exercises/exercise-03-shellcheck-fixes.md) | A deliberately broken script — fix every ShellCheck warning |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-rewrite-bad-script.md](./challenges/challenge-01-rewrite-bad-script.md) | A real-world "bad backup script" — rewrite it properly |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | Three useful scripts: backup wrapper, log rotator, disk-usage reporter |

## A note on which Bash and which ShellCheck

Bash is not POSIX `sh`. This week's content is written for Bash 5.2+, deliberately, and uses Bash-only features (`[[ ]]`, arrays, `local`, `${var,,}`) without apology. If you must write portable POSIX shell, that's a different course — and a much harder one. We will note the few places it matters.

```bash
# Which Bash?
bash --version | head -1
# Ubuntu 24.04 LTS:    GNU bash, version 5.2.21(1)-release (x86_64-pc-linux-gnu)
# Fedora 41:           GNU bash, version 5.2.32(1)-release (x86_64-redhat-linux-gnu)

# Which ShellCheck?
shellcheck --version
# Both distros ship ShellCheck 0.9.0 or newer in 2025.
```

If you're on macOS, **Apple ships Bash 3.2.57 from 2007**, frozen at the last GPL-2 release. Install a modern Bash via Homebrew (`brew install bash`) and put it on your PATH, or do this week's work inside a Linux container. The Bash 3.2 / Bash 5.x gap is wide enough to mislead you.

## Stretch goals

- Read **BashGuide** end to end (Lhunath, on the Greg's Wiki mirror). It's roughly 60 web pages; treat it as the textbook this week is structured around: <https://mywiki.wooledge.org/BashGuide>
- Read **BashPitfalls** (Greg's Wiki). Forty-plus numbered pitfalls; each one is one paragraph. The "for f in $(ls)" pitfall is #1, and it appears in production scripts every day: <https://mywiki.wooledge.org/BashPitfalls>
- Read the **ShellCheck wiki** — every numbered warning has a wiki page explaining the rule and the fix: <https://www.shellcheck.net/wiki/>
- Read the **`bash(1)` man page** from `SHELL GRAMMAR` through `Parameter Expansion`. It's dense but precise. The behavior of `${var:-default}` versus `${var-default}` is documented exactly once.

## Bash Yellow caution

This week contains scripts that can:

- Delete files in directories other than the one you meant (a missing `set -u`, an unset path variable, `rm -rf "$DIR/"`).
- Lock you out of a system by running for hours without progress (a missing `set -o pipefail`, a silent pipe failure).
- Corrupt a backup by writing a partial file (a missing trap, a Ctrl-C at the wrong moment).
- Leave temp files in `/tmp` that never get cleaned (a missing `trap "rm -rf $TMP" EXIT`).

Every lecture and exercise that runs destructive code uses a scratch directory and a Bash Yellow warning. Snapshot before you start. The line is: **untrusted input, unset variable, unquoted expansion** — every footgun this week reduces to one of those three.

## Up next

[Week 5 — systemd and services](../week-05/) — when your three scripts in the mini-project run themselves on a schedule, automatically, with logs in `journalctl`.

---

*If you find errors, please open an issue or PR.*
