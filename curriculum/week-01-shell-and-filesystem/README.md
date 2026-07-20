# Week 1 — The Shell and the Filesystem

> *Everything in Linux is a file. Everything in the shell is a program. Once both ideas are second-nature, the rest of Linux is recombination.*

Welcome to **C14 · Crunch Linux**. Week 1 takes you from "I can run `ls`" to "I can navigate any Linux system without looking up commands, and I know what each top-level directory is for and why." By Sunday you will live in the terminal for a workday without keyboard-shortcut anxiety, and you'll have drawn — by hand — a map of your machine's filesystem.

## Learning objectives

By the end of this week, you will be able to:

- **Explain** what a shell *is* (a program that reads commands and runs them), the difference between bash / zsh / fish, and which one your system is running by default.
- **Navigate** the filesystem with `cd`, `pwd`, `ls`, `tree`, including absolute vs. relative paths, `.`, `..`, `~`, and shell expansion (`*`, `?`, `[abc]`).
- **Inspect** files with `cat`, `less`, `head`, `tail`, `file`, `stat` — and know when each is appropriate.
- **Find** files with `find` (by name, by type, by size, by modification time) and content with `grep` (with regex basics).
- **Identify** what lives in `/`, `/etc`, `/var`, `/usr`, `/home`, `/tmp`, `/proc`, `/sys`, `/opt`, `/root`, `/dev`, `/boot` and *why* each exists.
- **Read** symbolic links (`ls -l`), follow them to their target, and understand the difference from hard links.
- **Use** `man` and `info` and `--help` and Tab-completion as your first three sources of truth — before searching the web.
- **Survive** in `vi`/`vim` and `nano` long enough to edit a config file without panicking.

## Prerequisites

- **C1 Weeks 1–4** completed (basic Python, comfortable in a terminal at all).
- A computer that can run Linux. Options:
  - Native Linux (Ubuntu LTS or Fedora Workstation — installer guides linked in `resources.md`).
  - VM (UTM on macOS, VirtualBox or Parallels on macOS, VMware Workstation Player on Windows/Linux).
  - WSL2 on Windows.
  - A $5/month VPS (DigitalOcean, Linode, Hetzner). Optional but recommended starting Week 5.

This week we default to **Ubuntu 24.04 LTS** in examples. Fedora differences are called out where they matter.

## Topics covered

- What "Linux" actually is: kernel vs. distribution vs. desktop environment
- A two-page tour of the FHS (Filesystem Hierarchy Standard)
- The shell as a programming language (we use it as one starting Week 4)
- Standard streams: stdin, stdout, stderr, and redirection (`>`, `>>`, `<`, `2>`, `|`)
- File metadata: `ls -l` columns, decoded byte-by-byte
- Globbing: `*`, `?`, `[abc]`, `{a,b,c}`, and why this is NOT regex
- Tab-completion as the most under-used productivity tool
- `man`, `info`, and the discipline of reading the manual first
- A 20-minute `vi` survival kit — enough to escape, save, and quit

## Weekly schedule

The schedule below adds up to approximately **36 hours**. Treat it as a target.

| Day       | Focus                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|----------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | Install / boot Linux; first 50 commands |    2h   |    1.5h   |     0h     |    0.5h   |   1h     |     0h       |    0.5h    |     5.5h    |
| Tuesday   | Filesystem hierarchy + `man` discipline |    2h   |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0h      |     6.5h    |
| Wednesday | Redirection, pipes, globs              |    2h    |    2h     |     1h     |    0.5h   |   1h     |     0h       |    0.5h    |     7h      |
| Thursday  | `find`, `grep`, the "where is" instinct |    0h   |    1.5h   |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Friday    | `vi` / `nano` survival kit             |    0h    |    1.5h   |     1h     |    0.5h   |   1h     |     2h       |    0.5h    |     6.5h    |
| Saturday  | Mini-project (filesystem map)          |    0h    |    0h     |     0h     |    0h     |   1h     |     3h       |    0h      |     4h      |
| Sunday    | Quiz + reflection                      |    0h    |    0h     |     0h     |    0.5h   |   0h     |     0h       |    0h      |     0.5h    |
| **Total** |                                        | **6h**   | **8.5h**  | **4h**     | **3h**    | **6h**   | **7h**       | **1.5h**   | **36h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./README.md) | This overview |
| [resources.md](./resources.md) | Curated free readings + cheat-sheets |
| [lecture-notes/01-what-is-linux-and-what-is-a-shell.md](./lecture-notes/01-what-is-linux-and-what-is-a-shell.md) | The kernel/distro/shell stack, demystified |
| [lecture-notes/02-the-filesystem-hierarchy.md](./lecture-notes/02-the-filesystem-hierarchy.md) | Every top-level directory, what's in it, why |
| [lecture-notes/03-pipes-redirection-globs.md](./lecture-notes/03-pipes-redirection-globs.md) | Streams, pipelines, expansion |
| [exercises/README.md](./exercises/README.md) | Index of exercises |
| [exercises/exercise-01-fifty-commands.md](./exercises/exercise-01-fifty-commands.md) | Run all 50 commands in the cheat-sheet at least once |
| [exercises/exercise-02-find-the-files.md](./exercises/exercise-02-find-the-files.md) | `find` puzzles |
| [exercises/exercise-03-grep-and-pipes.md](./exercises/exercise-03-grep-and-pipes.md) | `grep` + pipes on a real log |
| [challenges/README.md](./challenges/README.md) | Stretch challenges |
| [challenges/challenge-01-recover-from-disaster.md](./challenges/challenge-01-recover-from-disaster.md) | Recover a "broken" machine without reinstalling |
| [challenges/challenge-02-build-your-own-tree.md](./challenges/challenge-02-build-your-own-tree.md) | Reimplement `tree` as a shell script |
| [quiz.md](./quiz.md) | 10 multiple-choice questions |
| [homework.md](./homework.md) | Six practice problems (~6h) |
| [mini-project/README.md](./mini-project/README.md) | Filesystem map mini-project |

## Stretch goals

- Read the **Filesystem Hierarchy Standard** spec end-to-end: <https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html>
- Try a different shell for a day (`zsh`, `fish`) and compare.
- Skim the bash man page (it's 5000+ lines; read the SHELL GRAMMAR section). `man bash` then `/SHELL GRAMMAR`.
- Install [`tldr`](https://tldr.sh/) for community-maintained 5-line summaries of common commands.

## Up next

[Week 2 — Text and Pipes](../week-02-text-and-pipes/) — once your filesystem map is committed.

---

*If you find errors, please open an issue or PR.*
