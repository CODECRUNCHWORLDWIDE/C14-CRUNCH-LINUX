# Week 1 — Resources

Free, public, no signup unless noted.

## Required reading

- **Filesystem Hierarchy Standard 3.0** — the normative reference for what every directory is for:
  <https://refspecs.linuxfoundation.org/FHS_3.0/fhs/index.html>
- **GNU Bash Reference Manual — Quick Reference**:
  <https://www.gnu.org/software/bash/manual/html_node/index.html>
- **The Linux Foundation Open Source Guide — "What is Linux?"**:
  <https://www.linuxfoundation.org/blog/blog/what-is-linux>

## Cheat sheets (keep open in tabs)

- **`tldr` pages** — community-maintained 5-line command summaries: <https://tldr.inbrowser.app/>
- **`explainshell`** — paste any shell command and get an annotated breakdown: <https://explainshell.com/>
- **The Art of Command Line** (free, GitHub): <https://github.com/jlevy/the-art-of-command-line>

## Distro install guides

- **Ubuntu 24.04 LTS** (the default in our examples): <https://ubuntu.com/tutorials/install-ubuntu-desktop>
- **Fedora Workstation 41**: <https://docs.fedoraproject.org/en-US/quick-docs/installing-fedora/>
- **WSL2 on Windows**: <https://learn.microsoft.com/en-us/windows/wsl/install>
- **UTM on macOS** (Apple Silicon-friendly VM): <https://mac.getutm.app/>

## Free books and write-ups

- **"The Linux Command Line" — William Shotts** — the canonical free PDF:
  <https://linuxcommand.org/tlcl.php>
- **"Linux Pocket Guide" excerpts** — not fully free, but the table of contents itself doubles as a curriculum.
- **"The Debian Administrator's Handbook"** — fully free, applies broadly:
  <https://debian-handbook.info/browse/stable/>
- **Julia Evans' "wizard zines"** — exceptional free explainers on bash, networking, debugging:
  <https://wizardzines.com/comics/>

## Videos (free)

- **MIT 6.NULL "Missing Semester"** — free MIT lecture series on shell, vim, git, debugging, the things they don't teach in CS:
  <https://missing.csail.mit.edu/>
- **The first 5 lectures are exactly Week 1 of C14.** Treat them as supplementary, not replacement.

## Tools to install on day 1

- A terminal you like. macOS: iTerm2 or Ghostty. Linux: GNOME Terminal, Konsole, Alacritty. Windows (WSL): Windows Terminal.
- `tree` — visualize directories: `sudo apt install tree` (Debian/Ubuntu) or `sudo dnf install tree` (Fedora).
- `tldr` — `sudo apt install tldr` or `pip install tldr`.
- `htop` — friendlier `top`: `sudo apt install htop`.
- `vim` — ships everywhere. Optionally try `neovim`.
- `git` and `gh` — git CLI + GitHub CLI.

## Reference cards (one-pagers worth printing)

- **vi/vim cheat sheet** — many free PDFs on the web; the one in `lecture-notes/02` is enough.
- **Bash one-liners** — Greg's Wiki, free: <https://mywiki.wooledge.org/BashOneLiners>
- **Bash pitfalls** — what NOT to do: <https://mywiki.wooledge.org/BashPitfalls>

## Glossary

| Term | Definition |
|------|------------|
| **Kernel** | The core program managing CPU/memory/devices. "Linux" *technically* refers only to this. |
| **Distribution** ("distro") | Kernel + GNU userland + package manager + defaults. Ubuntu, Fedora, Arch, Debian, etc. |
| **Shell** | Program that reads commands and runs them. `bash`, `zsh`, `fish`, `dash`, `sh`. |
| **Terminal emulator** | The window the shell runs in. iTerm2, GNOME Terminal, Windows Terminal. |
| **Path** (filesystem) | Where a file lives. Absolute starts with `/`; relative does not. |
| **PATH** (env var) | The list of directories the shell searches for executables. `echo $PATH`. |
| **Working directory** | Where you currently "are." `pwd` prints it. |
| **Home directory** | Your personal directory. `~` expands to it. |
| **Glob** | Wildcard expansion in the shell. `*.py` matches all `.py` files. NOT regex. |
| **stdin / stdout / stderr** | Standard input / output / error streams. Numbered 0, 1, 2. |
| **Pipe** (`\|`) | Connects stdout of one command to stdin of another. |
| **Redirection** | `>` overwrites, `>>` appends, `<` reads, `2>` redirects stderr. |
| **Tab-completion** | Press Tab to complete a command/file. Press Tab twice to list options. The fastest way to type. |

---

*Broken link? Open an issue.*
