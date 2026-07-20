# Exercise 2 — Find the Files

**Goal:** Solve seven `find` puzzles. By the end, `find` is a tool you reach for without thinking.

**Estimated time:** 35 minutes.

## Setup

```bash
mkdir -p ~/c14-w1/exercise-02
cd ~/c14-w1/exercise-02

# Create a small landscape to search
mkdir -p src/{a,b,c} docs/{en,es,fr} build/cache
touch src/a/main.py src/a/util.py src/b/lib.py src/c/legacy.pyc
touch docs/en/{intro,advanced}.md docs/es/{intro,advanced}.md
echo "TODO: fix this" > src/a/main.py
echo "TODO: rewrite" > src/b/lib.py
echo "Done." > src/a/util.py
dd if=/dev/zero of=build/cache/big.bin bs=1M count=2 2>/dev/null
touch -d "2 days ago" src/c/legacy.pyc
```

You now have a small project tree to search.

## The seven puzzles

For each, write the `find` command into `solutions.md`. Run it, paste the output beneath.

1. **Find every `.py` file** in this tree.
2. **Find every `.py` file that's NOT under `build/`.**
3. **Find files larger than 1 MB.**
4. **Find files modified in the last 24 hours.** *(Hint: `-mtime -1`.)*
5. **Find files modified MORE than 24 hours ago.** *(Hint: `-mtime +1`.)*
6. **Find files whose contents contain `TODO`** *(combine `find` and `grep`).*
7. **Find every empty file** in the tree.

## Acceptance criteria

- [ ] `solutions.md` exists with all seven commands and their outputs.
- [ ] For puzzle 6, your command uses `find ... -exec grep ... {} \;` or `find ... | xargs grep` — **not** a recursive `grep -r`.
- [ ] You can explain in one sentence what `-mtime -1` vs `+1` vs `1` (no sign) mean.

## Stretch

- Add: **find every file owned by your user**.
- Add: **find every directory deeper than 2 levels from the project root**.
- Read `man find` and pick one option not mentioned here that surprised you. Write a sentence about it.

## Hints

<details>
<summary>If `-exec` confuses you</summary>

`find PATH -name "*.py" -exec grep TODO {} \;` runs `grep TODO <file>` once per file. The `{}` is replaced with the filename. The `\;` ends the command. Alternative: `find ... | xargs grep TODO` pipes filenames to `xargs`, which is faster (one `grep` call with many files).

</details>

## Submission

Commit `solutions.md` to your portfolio under `c14-week-01/exercise-02/`.
