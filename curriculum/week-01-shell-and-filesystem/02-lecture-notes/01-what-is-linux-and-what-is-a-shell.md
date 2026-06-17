# Lecture 1 — What is Linux, and what is a shell?

> **Duration:** ~2 hours. **Outcome:** You can answer "what is Linux?" in three sentences without using the word "operating system" vaguely, and you can name three different shells and what each is for.

## 1. The vocabulary problem

When people say "Linux" they mean four different things. Lecturer-grade fluency demands telling them apart.

| Word | What it actually refers to |
|------|---------------------------|
| **Linux** (strictly) | The kernel — one C program that manages CPU, memory, processes, devices, and filesystems. About 30 million lines of code. |
| **GNU/Linux** | The kernel + the GNU userland (`bash`, `ls`, `grep`, `gcc`, `coreutils`). What most people mean colloquially. |
| **A Linux distribution** | GNU/Linux + a package manager + a set of defaults. Ubuntu, Fedora, Debian, Arch, Alpine, etc. |
| **"A Linux machine"** | A computer running a Linux distribution. |

So "Linux runs the internet" means: most servers run *some Linux distribution*; the kernel underneath is the same.

This distinction matters when reading docs. A man page for `ls` describes GNU `ls`. A docs page on the Linux kernel describes a system call. A blog post titled "Ubuntu Linux tutorial" is distribution-specific. Treat them differently.

## 2. The kernel in 90 seconds

The kernel sits between your programs and the hardware. When your program wants to do anything *real* — read a file, listen on a network port, create a new process — it asks the kernel via a **system call** (`syscall`). The kernel then asks the hardware, gets a result, and hands it back to your program.

You can see this happen. On Linux, try:

```bash
strace -e openat ls
```

`strace` shows every system call. You'll see hundreds of `openat()` calls as `ls` reads each file's metadata. Every Linux command is a wrapper around system calls.

You **almost never** make system calls directly. You call into a library (the C standard library, Python's `os` module, etc.), which makes the syscall for you. This indirection is the whole point of an OS — your code is portable across kernels because the library hides the differences.

## 3. The shell

A **shell** is just another program. It happens to be one whose job is to read commands and run them on your behalf. When you type `ls -la /etc`, the shell:

1. Parses the line into tokens: `ls`, `-la`, `/etc`.
2. Looks up `ls` in your `PATH` (a colon-separated list of directories).
3. Forks a new process.
4. In the new process, calls `execve("/usr/bin/ls", ["ls", "-la", "/etc"], ...)` — a syscall.
5. Waits for that process to finish.
6. Prints the result and returns you to the prompt.

That entire dance, dozens of times per minute, is what the shell does. Understanding it removes 80% of "weird shell behavior" mysteries.

### Which shell?

There are several. On any Linux box you'll typically have `bash` (default on most). You might install `zsh` (default on macOS since 2019) or `fish` (more opinionated, friendlier defaults).

| Shell | One-line opinion |
|-------|-----|
| `bash` | The default. Reliable. Slightly clunky. Scripts written for `bash` are the lingua franca. |
| `zsh` | Bash-compatible with much better interactive UX (better Tab completion, themes via oh-my-zsh). Slow startup if you over-customize. |
| `fish` | Cleaner syntax, gorgeous defaults, **not POSIX-compatible** — scripts don't run on bash. Use it interactively, write portable scripts in bash. |
| `dash` | The Debian Almquist Shell. Very fast, very minimal, POSIX-strict. What `/bin/sh` is on Debian/Ubuntu. |

To find out what you're running:

```bash
echo $0           # the name of the current shell (usually with a leading -)
echo $SHELL       # your *login* shell, set in /etc/passwd
ps -p $$ -o args= # the actual command line of this shell process
```

For C14 we assume **bash**. If you prefer zsh or fish, that's fine for interactive use — but write all your shell scripts in bash (`#!/usr/bin/env bash`).

## 4. The prompt

When you open a terminal, you see something like:

```
ben@laptop:~/code$
```

That's the **prompt**. It's customizable. Defaults usually show:

- Your username (`ben`)
- Hostname (`laptop`)
- Current working directory (`~/code`)
- A `$` (user) or `#` (root) sigil

The variable that controls it in bash is `PS1`. Run `echo $PS1` to see yours. Customizing it is a Week-2 stretch.

The sigil matters:

- `$` = you're running as a **normal user**. Most commands are safe.
- `#` = you're running as **root**. Most commands are dangerous. Pay attention.

A common safety habit: if you see `#`, type `whoami` to confirm. If you see `root`, breathe before pressing Enter.

## 5. The first 50 commands

Below is the table you will *internalize* this week. Don't just memorize the names — type each one at least once, with `-h` or `--help` or `man`, and read what it does.

### File / directory navigation

| Command | Use |
|---------|-----|
| `pwd` | Print working directory |
| `cd <dir>` | Change directory. `cd` alone goes home. `cd -` goes to previous. |
| `ls` | List files. `-l` long format. `-a` include hidden (dotfiles). `-h` human sizes. |
| `tree` | Recursive directory listing (install with `apt install tree`) |
| `pushd` / `popd` / `dirs` | A stack of directories to jump between |

### File reading

| Command | Use |
|---------|-----|
| `cat <file>` | Print file. Don't use on large files. |
| `less <file>` | Paginate. `q` to quit. `/foo` to search. The default pager. |
| `head -n 20 <file>` | First 20 lines |
| `tail -n 20 <file>` | Last 20 lines. `-f` to follow new writes. |
| `file <file>` | Identify type ("ASCII text," "ELF 64-bit," "PDF document") |
| `stat <file>` | Full metadata |
| `wc <file>` | Word/line/byte count |

### File manipulation

| Command | Use |
|---------|-----|
| `cp <src> <dst>` | Copy. `-r` for directories. |
| `mv <src> <dst>` | Move / rename |
| `rm <file>` | Delete. `-r` recursive. `-i` ask first. **No undo.** |
| `mkdir <dir>` | Make directory. `-p` create parents. |
| `rmdir <dir>` | Remove empty directory |
| `touch <file>` | Create empty file, or update timestamp |
| `ln -s <target> <linkname>` | Create symbolic link |

### Searching

| Command | Use |
|---------|-----|
| `find <dir> -name "*.py"` | Find by name |
| `find <dir> -type f -size +1M` | Find files >1MB |
| `find <dir> -mtime -1` | Modified in last 24h |
| `grep "foo" <file>` | Search file content |
| `grep -r "foo" <dir>` | Search recursively |
| `grep -i "foo"` | Case-insensitive |
| `grep -n "foo" <file>` | Show line numbers |

### System info

| Command | Use |
|---------|-----|
| `whoami` | Current user |
| `id` | User + groups |
| `hostname` | Hostname |
| `uname -a` | Kernel info |
| `uptime` | How long the machine has been on |
| `date` | Current time |
| `df -h` | Disk space |
| `du -sh <dir>` | Directory size |
| `free -h` | Memory usage |

### Process

| Command | Use |
|---------|-----|
| `ps` | List your processes. `ps aux` for all. |
| `top` / `htop` | Live process viewer |
| `kill <pid>` | Send SIGTERM. `kill -9 <pid>` SIGKILL. |
| `pkill <name>` | Kill by name |
| `jobs` | List background jobs |
| `bg` / `fg` | Push to background / foreground |
| `&` | Run command in background (`somecmd &`) |

### Help

| Command | Use |
|---------|-----|
| `man <cmd>` | Manual page. `/foo` to search. `q` to quit. |
| `<cmd> --help` | Quick help. Most commands support it. |
| `info <cmd>` | Hypertext manual (more verbose than `man`) |
| `apropos <word>` | Search man pages for a keyword |
| `which <cmd>` | Where is this command? |
| `type <cmd>` | Is it a builtin, alias, function, or external? |

Fifty commands. Memorize them not by drilling, but by **using each one at least three times this week**. The exercise file `exercise-01-fifty-commands.md` walks you through.

## 6. Tab-completion: the productivity multiplier

Press `Tab` after typing the first few characters of a command, a filename, or a path. The shell completes if it can, beeps if it can't. Press `Tab` twice to see all options.

You should *never* type a full filename. Type the first three or four characters, press `Tab`, the rest fills in. Same for commands and directories.

In bash, install `bash-completion`:

```bash
sudo apt install bash-completion
```

It adds completion for git subcommands, package names, hostnames, etc. Critical productivity boost.

## 7. Reading the man page

`man <cmd>` is canonical. Reading it well takes practice. The structure:

```
NAME             — one-line description
SYNOPSIS         — argument syntax (square brackets = optional)
DESCRIPTION      — prose
OPTIONS          — flag-by-flag
EXAMPLES         — usually at the bottom; jump here first
SEE ALSO         — related commands
```

When stuck, the workflow is: `man <cmd>`, jump to EXAMPLES (`/EXAMPLES` or just `G` to end). Most pages have one or two illustrative examples.

If the command has no `man` page, try `<cmd> --help` or `info <cmd>` or `tldr <cmd>`.

## 8. Self-check

- What is "Linux," strictly?
- What's the difference between a shell and a terminal emulator?
- What does Tab do? What does Tab-Tab do?
- How do you tell which shell you're currently running?
- The prompt ends in `#`. What should you do before typing the next command?
- Where does `ls` live on disk? (Hint: `which ls`.)

If you can answer all six without consulting, move to Lecture 2.

## Further reading

- **MIT Missing Semester — "Course Overview + the Shell":** <https://missing.csail.mit.edu/2020/course-shell/>
- **Bash Reference Manual:** <https://www.gnu.org/software/bash/manual/>
- **Greg's Wiki — Bash Pitfalls:** <https://mywiki.wooledge.org/BashPitfalls>
