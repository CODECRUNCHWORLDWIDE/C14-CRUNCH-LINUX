# Challenge 2 — Build Your Own `tree`

**Time:** ~75 minutes. **Difficulty:** Medium.

## Problem

Write a shell function `mytree` that prints a directory's contents like the `tree` command does. Goal:

```
$ mytree
.
├── docs
│   ├── intro.md
│   └── advanced.md
├── src
│   ├── main.py
│   └── util.py
└── README.md
```

No installation of `tree`. Pure shell.

## Acceptance criteria

- [ ] A file `mytree.sh` you can `source` into your shell, defining `mytree() { ... }`.
- [ ] Calling `mytree <dir>` (or just `mytree` for the current directory) produces a recursive listing with proper box-drawing characters or ASCII fallbacks.
- [ ] Handles nested directories at any depth.
- [ ] Hidden files (`.*`) are NOT shown by default.
- [ ] A `mytree -a` shows hidden files.
- [ ] Runs without errors on:
  - An empty directory.
  - A directory with only files.
  - A directory three levels deep.
- [ ] Under 50 lines of shell, including comments.

## Hints

<details>
<summary>Approach</summary>

Two structures will help:

1. **Recursive function** — `mytree` calls itself on each subdirectory.
2. **A depth or prefix argument** — pass along the indent prefix (`│   `, `├── `, `└── `) so subcalls know what to print.

You'll want `find <dir> -mindepth 1 -maxdepth 1` to get *only* the immediate children, not the entire subtree. Or use a `for entry in "$dir"/*; do ... done` loop.

</details>

<details>
<summary>Box-drawing characters</summary>

These are UTF-8:

- `├── ` (`U+251C` then space space)
- `└── ` (`U+2514` then space space)
- `│   ` (`U+2502` then three spaces)

In bash, you can use them literally if your terminal is UTF-8 (it should be). Fallback: `+-- `, `\-- `, `|   ` in ASCII mode.

</details>

<details>
<summary>Test it</summary>

Create the directory layout from the example (`mkdir -p docs src; touch docs/{intro,advanced}.md src/{main,util}.py README.md`) and run `mytree`. Compare against `tree` if you have it installed (you can `apt install tree` just for verification).

</details>

## Stretch

- Add `-L <n>` to limit depth.
- Add `-d` to show only directories.
- Print sizes next to filenames.
- Make it handle symlinks correctly (show the target).

## Submission

Commit `mytree.sh` + a short `README.md` explaining how to use it to your portfolio under `c14-week-01/challenge-02/`.

## Why this matters

This is a microcosm of shell-scripting in C14's later weeks: recursion, argument parsing, string manipulation, dealing with edge cases. If you can write this cleanly, Week 4's "real" scripts will feel routine.
