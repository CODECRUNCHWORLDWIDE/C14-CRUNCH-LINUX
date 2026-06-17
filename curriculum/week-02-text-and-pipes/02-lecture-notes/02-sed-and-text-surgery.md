# Lecture 2 — `sed` and Text Surgery

> **Duration:** ~2 hours. **Outcome:** You can perform substitutions, addressed edits, and small multi-line transformations with `sed` — and you know precisely when to give up and reach for Python or `awk`.

`sed` is the **s**tream **ed**itor. It reads input one line at a time, applies a small program of editing commands to each line, and writes the result. Most of what people use `sed` for is one command: `s` (substitute). The rest of the language repays study, but in moderation — past a few dozen lines, `sed` becomes write-only.

## 1. The model

`sed` operates on a **pattern space** — a buffer holding the current line. For each input line:

1. Read the line into the pattern space.
2. Apply each command of the `sed` script.
3. Print the pattern space (unless `-n` was given).
4. Clear the pattern space and loop.

There is also a **hold space** — a second buffer you can copy to/from. Most scripts never touch it. The ones that do are the ones you should rewrite in `awk` or Python.

## 2. The substitute command

The 95% command. The form:

```
s/pattern/replacement/flags
```

Examples:

```bash
echo "hello world" | sed 's/world/bash/'
# Output: hello bash

# Substitute first match per line:
sed 's/foo/bar/' file.txt

# Substitute every match per line (the g = "global"):
sed 's/foo/bar/g' file.txt

# Substitute the 2nd match per line only:
sed 's/foo/bar/2' file.txt

# Case-insensitive (GNU sed and recent BSD sed):
sed 's/foo/bar/gi' file.txt

# Print only lines that changed (the p = "print"):
sed -n 's/foo/bar/gp' file.txt
```

The `-n` flag suppresses the default print. Combined with `p`, you get "show me only the matches" — which makes `sed` work like `grep` with the bonus of seeing the substitution.

### The delimiter is not sacred

The `/` after `s` is a delimiter, not magic. You can use **any** character. This is the path through "leaning toothpick" hell:

```bash
# Painful:
sed 's/\/usr\/local\/bin/\/opt\/bin/g' file

# Better — use a different delimiter:
sed 's|/usr/local/bin|/opt/bin|g' file

# Also fine:
sed 's#/usr/local/bin#/opt/bin#g' file
```

The standard choices are `|`, `#`, `,`. Pick one and be consistent.

## 3. Capture groups and backreferences

`sed` supports backreferences in the replacement. The syntax depends on the regex flavor:

```bash
# BRE (basic regex) — what `sed` uses by default. Parens must be escaped:
sed 's/\(foo\)bar/\1-baz/' file.txt

# ERE (extended regex) — enable with -E (GNU and modern BSD):
sed -E 's/(foo)bar/\1-baz/' file.txt
```

`\1` refers to the first capture group, `\2` to the second, up to `\9`. The whole match is `&`:

```bash
echo "hello" | sed 's/hello/<&>/'
# Output: <hello>

echo "Linux 6.8" | sed -E 's/([A-Za-z]+) ([0-9.]+)/version \2 of \1/'
# Output: version 6.8 of Linux
```

The `-E` flag is the right default for most modern work. BRE is the historical default and only kept around because the spec says so.

## 4. Addresses — restrict where commands apply

By default, every `sed` command applies to every line. You can restrict with an **address** before the command.

| Address form | Meaning |
|--------------|---------|
| `N` | Line number `N` (e.g., `5s/foo/bar/`) |
| `$` | The last line |
| `/regex/` | Lines matching the regex |
| `N,M` | Lines `N` through `M` |
| `/start/,/end/` | The range from the first match of `start` through the next match of `end` |
| `N,+M` | Line `N` plus `M` more lines (GNU extension) |
| `address!` | NEGATE — apply to lines NOT matching |

Examples:

```bash
# Substitute only on line 5:
sed '5s/foo/bar/' file.txt

# Only on the last line:
sed '$s/foo/bar/' file.txt

# Only on lines that contain "ERROR":
sed '/ERROR/s/foo/bar/' file.txt

# Only on lines from "BEGIN" to "END":
sed '/BEGIN/,/END/s/foo/bar/' file.txt

# Substitute on every line EXCEPT line 1:
sed '1!s/foo/bar/' file.txt

# Print only lines 10-20:
sed -n '10,20p' file.txt

# Delete blank lines:
sed '/^$/d' file.txt
```

The `d` command deletes the pattern space and starts the next cycle (no print). The `p` command prints. Pair `p` with `-n` to "print only matching lines" — that's how `sed` becomes `grep`.

## 5. In-place editing — and the BSD/GNU footgun

In-place editing modifies the file on disk instead of printing to stdout. This is where `sed` flavors diverge hard.

### GNU sed (Linux)

```bash
sed -i 's/foo/bar/g' file.txt           # In-place, no backup
sed -i.bak 's/foo/bar/g' file.txt       # In-place, save backup as file.txt.bak
```

The `-i` flag takes an **optional** suffix. With no suffix, you must NOT pass an empty string — `sed -i '' '...'` on GNU is a syntax error.

### BSD sed (macOS, FreeBSD)

```bash
sed -i '' 's/foo/bar/g' file.txt        # In-place, no backup
sed -i.bak 's/foo/bar/g' file.txt       # In-place, save backup as file.txt.bak
```

The `-i` flag **requires** a suffix argument. To get "no backup," pass an empty string `''`. To get a backup, pass the suffix attached: `-i.bak`. There is no whitespace between `-i` and the suffix in BSD.

### The cross-platform script

```bash
if [[ "$(uname)" == "Darwin" ]]; then
  sed -i '' 's/foo/bar/g' file.txt
else
  sed -i    's/foo/bar/g' file.txt
fi
```

Or, safer, avoid in-place editing entirely:

```bash
sed 's/foo/bar/g' file.txt > file.txt.tmp && mv file.txt.tmp file.txt
```

That's atomic enough for most purposes (the `mv` is atomic on the same filesystem; if `sed` fails, the original is untouched).

**Practical rule:** for one-off shell work, `sed -i` is fine. For scripts that ship between machines, use the temp-file pattern. For scripts that run in production, write the test that proves your `sed` did the right thing — `sed -i` will happily corrupt a file if your regex is wrong.

Always make a backup before running `sed -i` on a config you don't have in version control. Yes, even then.

## 6. Multi-line operations — lightly

Most `sed` commands operate on one line at a time. To handle multi-line patterns, you bring in:

| Command | Meaning |
|---------|---------|
| `N` | Append the next line to the pattern space (with `\n` separator) |
| `D` | Delete up to the first `\n` in the pattern space; start a new cycle |
| `P` | Print up to the first `\n` in the pattern space |
| `h` | Copy pattern space to hold space |
| `H` | Append pattern space to hold space |
| `g` | Copy hold space to pattern space |
| `G` | Append hold space to pattern space |
| `x` | Exchange pattern and hold spaces |

Example — join every two lines:

```bash
seq 1 6 | sed 'N;s/\n/ /'
# Output:
# 1 2
# 3 4
# 5 6
```

That `N;s/\n/ /` reads "append next line to pattern space, then replace the embedded newline with a space."

Another — print only the first match across a multi-line block:

```bash
sed -n '/BEGIN/,/END/p' file.txt
```

That said: **the second you reach for hold-space gymnastics, stop and consider `awk` or Python.** `sed` past three commands per line gets unreadable. There is no shame in switching tools mid-pipeline.

## 7. When `sed` wins over `awk`

`sed` is the right tool when:

- The operation is a **substitution stream** — find-and-replace, possibly with a regex, possibly with backreferences.
- The operation is **stateless** — it only depends on the current line.
- You want **in-place file edits** without a temp file (`-i`).
- The pipeline already uses other commands and `sed` is the one-line surgery in the middle.

Concrete examples where `sed` is the right answer:

- "Replace every `localhost` with `127.0.0.1` in /etc/hosts" — `sed -i 's/localhost/127.0.0.1/g'`.
- "Strip carriage returns from a file edited in Windows" — `sed -i 's/\r$//'`.
- "Show only lines between BEGIN and END" — `sed -n '/BEGIN/,/END/p'`.
- "Delete trailing whitespace on every line" — `sed -i 's/[[:space:]]*$//'`.

## 8. When `awk` wins over `sed`

`awk` is the right tool when:

- You need to operate on **specific fields**, not arbitrary positions in a line.
- You need **counts, sums, or aggregates**.
- You need **conditionals** more complex than a single regex match.
- You need to **remember state** across lines.

Compare:

```bash
# sed — replace 3rd word in the line. Fragile and ugly:
sed -E 's/^([^ ]+ [^ ]+ )[^ ]+/\1NEW/'

# awk — same, clearer:
awk '{ $3 = "NEW"; print }'
```

`awk` knows fields; `sed` knows lines. Use the one whose worldview matches the task.

## 9. When to reach for Python instead

Past `sed -e` chained more than three deep, or any time you find yourself drawing diagrams of the pattern space and hold space on paper, switch to Python (or at minimum `awk`). The break-even points:

- More than two captured groups feeding into a templated string → Python `re.sub` with a replacement function.
- Multi-line input where the boundaries are not regex-detectable → Python.
- Anything that wants a configuration file separate from the substitution rules → Python.
- Anything that needs a unit test → Python.

`sed` is for short, sharp, scriptable surgery. The moment it stops being short or sharp, change tool.

## 10. The `sed` cheat-sheet of common one-liners

```bash
# Print only line 5
sed -n '5p' file

# Print lines 10-20
sed -n '10,20p' file

# Delete the first line
sed '1d' file

# Delete the last line
sed '$d' file

# Delete blank lines
sed '/^$/d' file

# Delete comments (lines starting with #)
sed '/^[[:space:]]*#/d' file

# Strip trailing whitespace
sed 's/[[:space:]]*$//' file

# Squeeze multiple blank lines into one
sed '/^$/N;/^\n$/D' file

# Show file with line numbers
sed = file | sed 'N;s/\n/\t/'

# Convert Windows line endings to Unix
sed -i 's/\r$//' file

# Insert a line before line 5
sed '5i\Inserted text' file

# Append a line after line 5
sed '5a\Appended text' file

# Replace a whole line that matches a pattern
sed '/PATTERN/c\Replacement line' file
```

Print this. Tape it next to Eric Pement's one-liners from `resources.md`.

## 11. Multiple commands in one invocation

Use `-e` (each command) or `;` (separator), or a literal newline in a quoted block:

```bash
# Chained -e:
sed -e 's/foo/bar/g' -e 's/baz/qux/g' file

# Semicolons:
sed 's/foo/bar/g; s/baz/qux/g' file

# Multi-line (readable for non-trivial scripts):
sed '
  s/foo/bar/g
  s/baz/qux/g
  /^$/d
' file
```

For three or more substitutions, the multi-line form is the readable one. For 10+, put it in a `.sed` file and run `sed -f script.sed file`.

## 12. The portability matrix

| Concern | GNU sed (Linux) | BSD sed (macOS) |
|---------|------------------|-----------------|
| `-i` no backup | `-i` | `-i ''` |
| `-i` with backup | `-i.bak` | `-i.bak` |
| Extended regex | `-E` (also `-r`, legacy) | `-E` |
| `+`, `?`, `\|` in BRE | works (GNU extension) | does NOT work in BRE; need `-E` |
| `\b` word boundary | works | does NOT work (use `[[:<:]]` and `[[:>:]]`) |
| `\d`, `\w` shorthand | does NOT work even in `-E` | does NOT work |

Plain ASCII portable `sed` sticks to: BRE with escaped grouping, no `\b`, no `\d`. Anything fancier needs a "this is a GNU script" comment at the top of the file.

## 13. Self-check

- What does the `g` flag do in `s/foo/bar/g`?
- What does `-n` do, and why is it paired with the `p` flag?
- What is the difference between `-i` on GNU sed and BSD sed?
- How do you replace `/usr/local/bin` with `/opt/bin` without escaping every slash?
- What's the difference between `\1` and `&` in a replacement?
- Given lines like `name=value`, how do you delete all `name=` prefixes with `sed`?
- When does the hold space matter? When can you ignore it?

When all seven feel easy, the [`sed` exercises](../03-exercises/exercise-02-sed-substitutions.md) drill them.

## Further reading

- **GNU sed manual:** <https://www.gnu.org/software/sed/manual/sed.html>
- **Eric Pement's sed one-liners:** <https://www.pement.org/sed/sed1line.txt>
- **Bruce Barnett's sed tutorial:** <https://www.grymoire.com/Unix/Sed.html>
- **The `sed` reference for the pattern space and hold space:** <https://www.gnu.org/software/sed/manual/sed.html#Programming-Commands>

Tomorrow: combining `awk` and `sed` into pipelines that answer real questions about real log files. The mini-project is built on this combination.
