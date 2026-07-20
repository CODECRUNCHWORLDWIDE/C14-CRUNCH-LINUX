# Week 4 — Exercises

Three drills, ~5 hours total. Do them in order; each builds on the last.

| File | Time | Focus |
|------|------|-------|
| [exercise-01-write-3-defensive-scripts.md](./exercise-01-write-3-defensive-scripts.md) | 2h | Write three small scripts from scratch, each one a defensive-coding drill. ShellCheck must pass on all three. |
| [exercise-02-trap-and-cleanup.md](./exercise-02-trap-and-cleanup.md) | 1.5h | Build a script with a `trap`-driven cleanup, then deliberately try to break it (Ctrl-C, kill, SIGKILL). |
| [exercise-03-shellcheck-fixes.md](./exercise-03-shellcheck-fixes.md) | 1.5h | Take a deliberately broken script with 15+ ShellCheck warnings. Fix each one. Explain the fix. |

Commit your answers to your portfolio repo under `c14-week-04/exercises/`. Each exercise produces shell scripts plus a short `notes.md` explaining your choices. Show the command **and** the ShellCheck output, before and after.

**Run ShellCheck on every script before you submit.** Zero warnings is the bar. If you keep a warning, annotate it with `# shellcheck disable=SCxxxx  # reason: ...`.

When in doubt, the references this week are:

- BashGuide: <https://mywiki.wooledge.org/BashGuide>
- BashPitfalls: <https://mywiki.wooledge.org/BashPitfalls>
- ShellCheck wiki: <https://www.shellcheck.net/wiki/>

Read those pages once even when you're not stuck. The reflex is the point.
