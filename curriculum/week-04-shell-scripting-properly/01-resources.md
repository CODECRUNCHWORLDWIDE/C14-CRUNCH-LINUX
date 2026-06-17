# Week 4 — Resources

Free, public, no signup unless noted. ShellCheck and the Greg's Wiki pages are the two URLs you will bookmark this week.

## Required reading

- **BashGuide** by Lhunath, hosted on Greg's Wiki — the textbook for this week. Roughly 60 web pages. Read the sections on Quotes, Tests and Conditionals, Compound Commands, and Practices. Each section ends with a "Practices" page that is gold:
  <https://mywiki.wooledge.org/BashGuide>
- **BashPitfalls** on Greg's Wiki — forty-plus numbered pitfalls, each one a paragraph plus a wrong-vs-right snippet. Read them all. Several appear in the exercises this week:
  <https://mywiki.wooledge.org/BashPitfalls>
- **ShellCheck wiki** — every numbered warning (`SC2086`, `SC2046`, etc.) has a wiki page explaining the rule and showing the fix. You will reference this dozens of times this week:
  <https://www.shellcheck.net/wiki/>
- **The `bash(1)` man page** — your local reference. Read `Parameter Expansion`, `Compound Commands`, `Conditional Expressions`, and `SHELL BUILTIN COMMANDS` (specifically the `trap` entry). The man page is precise where the internet is approximate.

## Books

- **"Pro Bash Programming" — Chris F. A. Johnson and Jayant Varma (2nd ed., Apress, 2015)** — chapters 4 (parameters and variables), 7 (script control), and 10 (working with files). Solid on the corner cases.
- **"Bash Cookbook" — Albing, Vossen, Newham (2nd ed., O'Reilly, 2017)** — recipe-driven. Chapter 14 ("Writing Secure Shell Scripts") and chapter 19 ("Working Smarter, Not Harder") are the chapters worth the price.
- **"The Linux Command Line" — William Shotts (5th internet ed., 2024)** — Part IV ("Writing Shell Scripts") is free online and a clean overview. Less depth than BashGuide; gentler entry: <https://linuxcommand.org/tlcl.php>
- **"Classic Shell Scripting" — Robbins and Beebe (O'Reilly, 2005)** — older, POSIX-focused, but the chapter on text processing inside scripts (the `awk`/`sed` plumbing) is timeless.

## Cheat sheets

- **ShellCheck — pre-commit hook recipe** — runs ShellCheck automatically on every script you `git commit`:
  <https://www.shellcheck.net/wiki/Integration>
- **Greg's Wiki — "Bash FAQ"** — short answers to the questions people ask every week on `#bash`. The FAQ and BashPitfalls overlap; both are worth reading:
  <https://mywiki.wooledge.org/BashFAQ>
- **`set -euo pipefail` cheat sheet (Aaron Maxwell)** — "Use the Unofficial Bash Strict Mode (Unless You Looove Debugging)". Opinionated, well-argued, and the canonical link people cite for the three-flag opener:
  <http://redsymbol.net/articles/unofficial-bash-strict-mode/>
- **Google Shell Style Guide** — the closest thing to a "Bash style guide" Google has published. Read it once; you don't have to agree with every rule, but the reasoning is sound:
  <https://google.github.io/styleguide/shellguide.html>

## Tools and websites

- **shellcheck.net** — paste a script and get the same warnings the CLI gives, with each `SC` number linked to its wiki page. Useful for sharing snippets in code review:
  <https://www.shellcheck.net/>
- **explainshell.com** — paste a shell pipeline and it annotates every flag with the man-page entry. Useful when you read a script that has `find ... -print0 | xargs -0 -I {}` and you've forgotten what each flag does:
  <https://explainshell.com/>
- **bashate** — a style-and-formatting linter for shell scripts, complementary to ShellCheck (which is semantic). Worth running once per project:
  <https://opendev.org/openstack/bashate>

## Videos (free)

- **MIT 6.NULL "Missing Semester" — Shell Tools and Scripting** — covers the basics this week assumes, plus a touch of the topics we go deeper on. Watch in week 1 of C14 if you haven't already:
  <https://missing.csail.mit.edu/2020/shell-tools/>
- **"Bash Scripting Crash Course" — Traversy Media** — one-hour overview. Useful as a survey before the lectures, not as a replacement for them:
  <https://www.youtube.com/results?search_query=traversy+bash+scripting>
- **"Defensive BASH Programming" — Kfir Lavi (talk transcript)** — the original write-up that introduced "strict mode" to many people:
  <https://kfirlavi.com/blog/2012/11/14/defensive-bash-programming/>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install bash shellcheck shfmt

# Fedora
sudo dnf install bash ShellCheck shfmt
```

- `bash` — assume installed. Confirm `bash --version` shows 5.2 or newer.
- `shellcheck` — the linter. We run it on every script this week. (On Fedora the package name is capitalized `ShellCheck`; on Ubuntu it's lowercase `shellcheck`. The binary itself is `shellcheck`.)
- `shfmt` — a formatter for shell scripts. Optional but recommended once you have a few scripts to maintain. Equivalent of `gofmt` for shell.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| Bash version | 5.2.21 | 5.2.32 |
| `/bin/sh` is... | Dash (POSIX `sh`, not Bash) | Bash, in POSIX mode |
| ShellCheck package name | `shellcheck` | `ShellCheck` |
| `shfmt` package name | `shfmt` | `shfmt` |
| `flock(1)` | `util-linux` (installed) | `util-linux-core` (installed) |
| `mktemp` | GNU coreutils 9.4 | GNU coreutils 9.5 |
| Default `$IFS` | `space tab newline` | `space tab newline` |

The `/bin/sh` divergence is the one that bites. A script that starts `#!/bin/sh` and uses `[[ ]]` works on Fedora and breaks on Ubuntu. Always start your scripts `#!/usr/bin/env bash` — the env wrapper finds Bash on `PATH`, regardless of distro, regardless of `/bin/sh`. This is the rule.

## Free books and write-ups

- **"Use the Unofficial Bash Strict Mode" — Aaron Maxwell** — already linked above; the canonical short essay:
  <http://redsymbol.net/articles/unofficial-bash-strict-mode/>
- **"Safe ways to do things in bash" — Anthony Scopatz** — a long, well-cross-referenced list of common bash tasks and the safe form for each:
  <https://github.com/anordal/shellharden/blob/master/how_to_do_things_safely_in_bash.md>
- **"Shellharden" — Anders Kaseorg / Anthony Scopatz** — a tool that *automatically rewrites* shell scripts to be safer. Useful as a teaching tool: run it on your own code and see what it changes:
  <https://github.com/anordal/shellharden>
- **Greg's Wiki — "QuotesAndEscapes"** — the deep dive on what double-quoting actually does. Beyond what BashGuide covers:
  <https://mywiki.wooledge.org/Quotes>
- **Greg's Wiki — "WordSplitting"** — same series; what splitting actually means and when it happens:
  <https://mywiki.wooledge.org/WordSplitting>
- **Greg's Wiki — "ProcessManagement"** — the canonical reference on `trap`, signals, and child processes:
  <https://mywiki.wooledge.org/ProcessManagement>

## ShellCheck error codes you will see this week

A quick reference. Every code links to a wiki page; we will not duplicate the wiki here.

| Code | Meaning | Fix |
|------|---------|-----|
| `SC2086` | Double-quote to prevent globbing and word splitting. | `"$var"` instead of `$var`. |
| `SC2046` | Quote this to prevent word splitting (in command substitution). | `"$(cmd)"` instead of `$(cmd)`. |
| `SC2155` | Declare and assign separately to avoid masking return values. | `local x` then `x=$(cmd)`. |
| `SC2148` | Tips depend on target shell and yours is unknown. Add a shebang. | `#!/usr/bin/env bash` on line 1. |
| `SC2164` | `cd` may fail; use `cd ... || exit`. | `cd "$dir" || exit 1`. |
| `SC2128` | Expanding an array without an index. | `"${arr[@]}"` (or `"${arr[0]}"` for scalar). |
| `SC2034` | Variable assigned but never used. | Delete it, or `# shellcheck disable=SC2034` with a comment. |
| `SC2059` | Don't use variables in the printf format string. | `printf '%s' "$var"`, not `printf "$var"`. |
| `SC1090` | Can't follow non-constant source. | `# shellcheck source=./file.sh` annotation. |
| `SC2207` | Prefer `mapfile` or `read -a` over array assignment from command substitution. | `mapfile -t arr < <(cmd)`. |

These are the ten you will encounter most. The wiki has the rest: <https://www.shellcheck.net/wiki/>

## Glossary

| Term | Definition |
|------|------------|
| **Shebang** | The `#!/usr/bin/env bash` (or similar) line that tells the kernel which interpreter to run. Must be the first line. |
| **`set -e`** | "Exit immediately if a command exits with non-zero status." The `errexit` option. Famously partial — does not catch every error. |
| **`set -u`** | "Treat unset variables as an error." The `nounset` option. Turns `$TYPO` into a script failure. |
| **`set -o pipefail`** | "The exit status of a pipeline is the rightmost non-zero exit, or zero if all succeed." Without it, `false \| true` returns 0. |
| **Word splitting** | Bash's process of breaking unquoted expansions into words, using `$IFS`. The reason `for f in $(ls)` is wrong. |
| **`IFS`** | Internal Field Separator. Default: space, tab, newline. Controls word-splitting. |
| **`[[ ]]`** | Bash's conditional expression. Safer than `[`: no word-splitting, supports `=~` regex and pattern matching. |
| **`trap`** | Bash builtin that registers a command to run on a signal. `trap CMD EXIT` is the cleanup pattern. |
| **Pseudo-signal** | A trap target that is not a real signal: `EXIT`, `ERR`, `DEBUG`, `RETURN`. |
| **ShellCheck** | Static analyzer for shell scripts. Catches the bugs `set -euo pipefail` does not. |
| **`mktemp`** | Safe temp-file creator. Generates an unguessable name in `/tmp`. Pair with a cleanup trap. |
| **`flock`** | File-lock utility. Wraps a script in a mutex so two copies don't run at once. |
| **`sysexits.h`** | A BSD header defining standard exit codes (64 EX_USAGE, 65 EX_DATAERR, ...). Useful conventions. |

---

*Broken link? Open an issue.*
