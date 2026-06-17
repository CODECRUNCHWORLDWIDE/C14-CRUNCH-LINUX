# Week 3 — Exercises

Three drills, ~5 hours total. Do them in order; each builds on the last.

| File | Time | Focus |
|------|------|-------|
| [exercise-01-permission-puzzles.md](./exercise-01-permission-puzzles.md) | 1.5h | Twelve permission puzzles — read modes, convert symbolic to octal, predict what `umask` produces. |
| [exercise-02-add-users-and-groups.md](./exercise-02-add-users-and-groups.md) | 2h | Hands-on user and group lifecycle on a throwaway VM. Create, modify, audit, delete. |
| [exercise-03-setuid-investigation.md](./exercise-03-setuid-investigation.md) | 1.5h | Find every `setuid` and `setgid` binary on a real Ubuntu or Fedora system. Explain each. |

Commit your answers to your portfolio repo under `c14-week-03/exercises/`. Each exercise should produce one short markdown file (or section in `answers.md`). Show the command **and** a sample of its output.

**Do exercise 02 in a VM or container.** `docker run -it --rm ubuntu:24.04 bash` is enough for everything in this week's exercises that doesn't require a real shell login. For real-login flows (`su -`, `newgrp`), boot a VM — Multipass, VirtualBox, or UTM all work.

When in doubt, `man chmod`, `man useradd`, `man sudoers`. Read them once even when you're not stuck; the reflex is the point.
