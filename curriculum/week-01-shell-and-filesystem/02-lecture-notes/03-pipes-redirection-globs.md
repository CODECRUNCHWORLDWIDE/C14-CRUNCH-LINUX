# Lecture 3 — Pipes, Redirection, and Globs

> **Duration:** ~2 hours. **Outcome:** You can compose programs into pipelines, redirect their I/O explicitly, and use shell globs without confusing them with regex.

This is the lecture where Linux clicks. Three small ideas — streams, pipes, globs — compose into the productivity language that's recognizable across every Unix-like system since 1970.

## 1. The three streams

Every program has three default file descriptors:

| FD | Name | Default destination |
|---:|------|---------------------|
| 0 | **stdin** | The keyboard |
| 1 | **stdout** | The terminal |
| 2 | **stderr** | The terminal (but separate from stdout) |

Programs read from stdin, write success output to stdout, write errors to stderr. Keeping stdout and stderr separate is the *crucial* design choice — it means you can capture or pipe one without interfering with the other.

## 2. Redirection

The shell lets you redirect any of these streams using punctuation **before running the command**.

| Operator | Effect |
|----------|--------|
| `>` | Redirect **stdout** to a file (overwrite) |
| `>>` | Redirect **stdout** to a file (append) |
| `<` | Read **stdin** from a file |
| `2>` | Redirect **stderr** to a file |
| `2>>` | Append **stderr** to a file |
| `&>` | Redirect both stdout and stderr |
| `2>&1` | Send stderr to wherever stdout currently goes |

Examples:

```bash
ls -la /etc > etc-listing.txt           # Save the listing
ls -la /etc >> ~/log.txt                 # Append
sort < unsorted.txt                      # Read from file
grep ERROR app.log 2> grep-errors.log    # Capture grep's own errors
make &> build.log                        # Capture stdout AND stderr
some_cmd > out.txt 2>&1                  # Same: redirect both to out.txt
some_cmd > /dev/null 2>&1                # Discard everything
```

Read the last form carefully. `2>&1` means "send stderr to the same place as stdout." Order matters: `> out.txt 2>&1` puts stderr into `out.txt`. `2>&1 > out.txt` does NOT — it sends stderr to *the original* stdout (terminal) and then redirects stdout to the file.

## 3. The pipe (`|`)

A pipe connects the stdout of one command to the stdin of the next. The shell sets it up; the two programs run in parallel.

```bash
ls | wc -l                          # How many entries in this directory?
cat /etc/passwd | grep alice         # Lines mentioning alice
ps aux | grep python                 # Running Python processes
history | tail -20                   # Last 20 commands you ran
journalctl -u sshd | tail -50        # Last 50 lines of sshd logs
```

Pipes are the entry point to the Unix philosophy: **small programs that each do one thing, composed into pipelines.** When you find yourself reaching for a Python script to "process a log file," ask whether `awk` or `cut` and `sort` can do it in a one-liner first. Often they can.

### Pipe pitfalls

1. **stderr does NOT go through pipes.** `make | grep error` only sees stdout. If `make` writes "ERROR" to stderr (which it usually does), grep won't see it. Add `2>&1` before the pipe: `make 2>&1 | grep error`.
2. **The exit status of a pipeline is the exit of the LAST command.** `false | true` exits successfully because `true` was last. To get the worst exit status, set `set -o pipefail` (Week 4).
3. **A "broken pipe"** error happens when the reader closes before the writer finishes. Usually harmless: `find / -name foo | head` causes `find` to get SIGPIPE.

## 4. Useful one-line compositions

Memorize these patterns; they recombine constantly.

```bash
# Count something
some_cmd | wc -l

# Unique lines, sorted
some_cmd | sort | uniq

# Top N most common values
some_cmd | sort | uniq -c | sort -rn | head -10

# Just the Nth column (space-separated)
some_cmd | awk '{print $3}'

# Just the Nth field (CSV-separated)
some_cmd | cut -d',' -f2

# Filter by pattern, count remaining
some_cmd | grep "ERROR" | wc -l

# Process per-line, tee to a file mid-pipeline
some_cmd | tee output.txt | grep ERROR

# Use a file's contents as command-line arguments
xargs -a files.txt rm

# For each line in input, run a command
some_cmd | xargs -I {} echo "Processing {}"
```

Take your time with these. Each becomes second-nature with maybe 20 repetitions in real situations.

## 5. Globbing — wildcards in the shell

When you type `ls *.py`, the shell — **not `ls`** — expands `*.py` to the list of matching filenames BEFORE invoking `ls`. This is **globbing**.

The glob patterns:

| Pattern | Matches |
|---------|---------|
| `*` | Any sequence of characters (not `/`) |
| `?` | Any single character |
| `[abc]` | Any one of a, b, or c |
| `[a-z]` | Any lowercase letter |
| `[!abc]` | Anything but a, b, c |
| `{foo,bar}` | Literally "foo" or "bar" (brace expansion) |
| `**` | Any number of directories (with `shopt -s globstar`) |

Examples:

```bash
ls *.py                    # all Python files in cwd
ls **/*.py                 # all Python files recursively (with globstar)
rm *.bak                   # remove all .bak files
cp file{1,2,3}.txt /tmp/    # cp file1.txt file2.txt file3.txt /tmp/
mkdir -p project/{src,tests,docs}  # create three subdirs at once
```

### Globs are NOT regex

Repeat after me: **globs are not regular expressions.** Don't try to use `+`, `()`, `|` in a glob — they mean different things or nothing at all.

If you need real regex, use `grep -E`, `sed`, `awk`, or Python.

### When the glob matches nothing

By default in bash, `ls *.foo` when there are no `.foo` files passes the *literal* string `*.foo` to `ls`, which then errors with "No such file." This bites people.

To make unmatched globs expand to nothing instead:

```bash
shopt -s nullglob
```

(In `zsh`, it's the default; you can disable with `setopt no_nomatch`.)

## 6. Quoting

Quoting controls what the shell expands.

| Quoted | Globs expanded? | Variables expanded? | Backslashes interpreted? |
|--------|:---------------:|:-------------------:|:------------------------:|
| `'single'` | No | No | No |
| `"double"` | No | Yes | Yes |
| no quotes  | Yes | Yes | Yes |

Rule of thumb: **wrap variable expansions in double quotes** unless you have a good reason not to:

```bash
file=$1
rm "$file"        # Good — handles filenames with spaces
rm $file          # Bad — splits "my file.txt" into two args: "my" and "file.txt"
```

This is the #1 source of bugs in shell scripts. Quote your variables.

## 7. Two practical pipelines

### A. Find the top 10 largest files in your home directory

```bash
find ~ -type f -exec du -h {} + 2>/dev/null | sort -hr | head -10
```

Decode: `find` finds files. `-exec du -h {} +` runs `du -h` on batches of them. `sort -hr` sorts by human-readable size, reversed (largest first). `head -10` takes the top.

### B. Find the most-frequent words in a file

```bash
cat speech.txt | tr '[:upper:]' '[:lower:]' | tr -cs '[:alpha:]' '\n' | sort | uniq -c | sort -rn | head
```

Decode: `cat` the file. `tr` lowercases it. `tr -cs '[:alpha:]' '\n'` replaces runs of non-letters with newlines (one word per line). `sort | uniq -c` counts each unique word. `sort -rn | head` shows the top.

A one-line word-counter. No Python required.

## 8. Self-check

- What's the difference between `>` and `>>`?
- How do you redirect both stdout and stderr to the same file?
- What's the exit status of `false | true`? Why?
- A glob `*.py` expanded to nothing. What does the shell pass to `ls`?
- Is `[a-z]` regex? Is `[abc]` regex?
- Why is `rm $file` worse than `rm "$file"`?

When all six are easy, the [exercises](../03-exercises/00-overview.md) drill them.

## Further reading

- **The Unix philosophy (Doug McIlroy):** <https://en.wikipedia.org/wiki/Unix_philosophy>
- **Bash redirection — official:** <https://www.gnu.org/software/bash/manual/bash.html#Redirections>
- **Greg's Wiki — quoting:** <https://mywiki.wooledge.org/Quotes>
