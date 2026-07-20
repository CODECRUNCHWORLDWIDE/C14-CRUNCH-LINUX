# Week 2 — Text and Pipes

> *Most of what a sysadmin does is read text, transform text, and pipe text into other text. By Sunday, `awk` and `sed` are not commands you look up — they are commands you reach for.*

Welcome to **Week 2 of C14 · Crunch Linux**. Last week you learned to navigate the filesystem and compose `|` pipelines from `grep`, `cut`, `sort`, `uniq`, and friends. This week we go a layer deeper: `awk` as a small programming language for record-oriented text, and `sed` as a stream-editor scalpel for line-oriented surgery. By Friday, the question "should I write a Python script for this?" gets a smaller answer surface than you expect.

## Learning objectives

By the end of this week, you will be able to:

- **Read and write** `awk` programs of the form `pattern { action }`, with `BEGIN` / `END` blocks, field variables (`$1`, `$NF`), built-ins (`NR`, `NF`, `FS`, `OFS`), conditionals, loops, and associative arrays.
- **Recognize** when `awk` is the right tool versus `cut`, versus `grep`, versus Python — and articulate the cut-off point ("anything stateful or with nested data, leave `awk`").
- **Apply** `sed` substitutions (`s/foo/bar/g`), addressed edits (line numbers, regex, ranges), and multi-line operations — without breaking your file.
- **Use** in-place editing (`sed -i`) safely on both GNU and BSD `sed`, knowing that `sed -i ''` is a macOS footgun (and the inverse: `sed -i ''` on GNU is a syntax error).
- **Compose** `awk` and `sed` into longer pipelines that answer real operational questions about real log files in `/var/log`.
- **Cite** portability: GNU `awk` (`gawk`), `mawk`, `nawk`, and BWK `awk` are not the same program. Same for GNU `sed` vs BSD `sed`.

## Prerequisites

- **Week 1 of C14** completed. You can navigate, redirect, and pipe.
- You can read `grep`, `cut`, `sort`, `uniq`, and `wc` without consulting `man`.
- A working Ubuntu 24.04 LTS or Fedora 41 environment. Snippets are tested on both.

## Topics covered

- `awk` as a record-oriented programming language — not just `awk '{print $1}'`.
- The `pattern { action }` model, `BEGIN`, `END`, and the default record loop.
- Field and record separators (`FS`, `OFS`, `RS`), and how to set them on the command line.
- Built-in variables: `NR` (record number), `NF` (number of fields), `FILENAME`, `FNR`.
- Conditionals, `for` / `while` loops, and associative arrays (the killer feature).
- `sed` substitution: `s/pattern/replacement/flags`, capture groups, and the delimiter trick (`s|/path|/other|g`).
- Addresses: line numbers, line ranges, regex matches, `$` (last line).
- In-place editing: GNU `sed -i` vs BSD `sed -i ''`. The footgun, and the workaround.
- Multi-line operations: `N`, `D`, `P`, the hold space — covered lightly, with a clear "use Python if it gets harder than this" boundary.
- Portability: `awk` on Ubuntu defaults to `mawk`; on Fedora it's `gawk`. They differ.

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target, not a contract.

| Day       | Focus                                       | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|---------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | `awk` lecture + first puzzles               |    3h    |    2h     |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Tuesday   | `awk` arrays, conditionals, real logs       |    1h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     6h      |
| Wednesday | `sed` lecture + substitutions               |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Thursday  | `sed` addresses + multi-line; CSV challenge |    0h    |    1h     |     2h     |    0.5h   |   1h     |     2h       |    0.5h    |     7h      |
| Friday    | Real log pipeline exercise + homework       |    0h    |    1.5h   |     0h     |    0.5h   |   2h     |     1h       |    0h      |     5h      |
| Saturday  | Mini-project (log-analysis pipeline)        |    0h    |    0h     |     0h     |    0h     |   0h     |     4h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                           |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                             | **6h**   | **8.5h**  | **4h**     | **3h**    | **6h**   | **7h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Books, papers, and reference cards |
| [lecture-notes/01-awk-as-a-language.md](./lecture-notes/01-awk-as-a-language.md) | `awk` from the ground up — patterns, actions, arrays |
| [lecture-notes/02-sed-and-text-surgery.md](./lecture-notes/02-sed-and-text-surgery.md) | `sed` substitutions, addresses, in-place editing |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-awk-puzzles.md](./exercises/exercise-01-awk-puzzles.md) | Ten `awk` puzzles, escalating in difficulty |
| [exercises/exercise-02-sed-substitutions.md](./exercises/exercise-02-sed-substitutions.md) | `sed` substitution drills |
| [exercises/exercise-03-real-log-pipeline.md](./exercises/exercise-03-real-log-pipeline.md) | Mixed `awk` + `sed` on `/var/log` |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-csv-without-python.md](./challenges/challenge-01-csv-without-python.md) | Parse a real CSV with `awk` alone |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6 hours) |
| [mini-project/README.md](./mini-project/README.md) | Build a log-analysis pipeline answering five questions about `/var/log` |

## A note on which `awk` and which `sed` you have

Distros do not ship the same implementations.

```bash
# What awk is installed?
ls -l "$(command -v awk)"

# Ubuntu 24.04 typically shows:
# /usr/bin/awk -> /etc/alternatives/awk -> /usr/bin/mawk

# Fedora 41 typically shows:
# /usr/bin/awk -> gawk
```

`mawk` is small and fast but lacks some GNU extensions. `gawk` is the GNU implementation and is the de facto reference. `nawk` is the modern BWK ("New AWK") on BSDs and macOS. We write `awk` in lecture and call out where `gawk` extensions sneak in.

For `sed`:

```bash
sed --version 2>/dev/null | head -1
# GNU sed prints:    sed (GNU sed) 4.x
# BSD sed prints:    no --version flag at all; that's how you know.
```

On macOS, `sed` is BSD. On any Linux we use, `sed` is GNU. The biggest practical difference: in-place editing. GNU: `sed -i 's/x/y/' file`. BSD: `sed -i '' 's/x/y/' file`. Cross-platform scripts handle this with `if [[ "$(uname)" == "Darwin" ]]; then ...`.

## Stretch goals

- Read **"The AWK Programming Language" (Aho, Kernighan, Weinberger)** — yes, the original 1988 book; the second edition is from 2023 and free as a PDF from one of the authors' pages.
- Skim `man gawk` — at 4000+ lines, it's a small textbook on its own.
- Try `gawk -f` with a multi-line `.awk` script file. Programs longer than ~5 lines belong in a file, not on the command line.
- Watch Brian Kernighan's "AWK at 45" talk: <https://www.youtube.com/results?search_query=brian+kernighan+awk>.

## Up next

[Week 3 — Permissions, users, groups, ACLs](../week-03/) — once your log-analysis pipeline is committed.

---

*If you find errors, please open an issue or PR.*
