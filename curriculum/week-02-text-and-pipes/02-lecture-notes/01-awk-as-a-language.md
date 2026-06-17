# Lecture 1 — `awk` as a Language

> **Duration:** ~3 hours. **Outcome:** You stop thinking of `awk` as "the print-column-N tool" and start thinking of it as a small, record-oriented programming language built for text.

Most engineers meet `awk` the same way: a stranger in a forum post writes `awk '{print $3}'`, it gets the job done, the engineer copies it forward, and that becomes the lifetime extent of their `awk` knowledge. That is fine, except that `awk` rewards a one-hour investment with a lifetime of one-liners that used to be Python scripts. This lecture is that hour, tripled.

## 1. What `awk` actually is

`awk` is a programming language designed in 1977 by Alfred **A**ho, Peter **W**einberger, and Brian **K**ernighan at Bell Labs. The name is the initials. It was designed for record-oriented text — log files, `/etc/passwd`, tab-separated data, CSV. The semantics are still essentially what they were in 1977; the implementations have multiplied.

You will hear about four implementations:

| Implementation | Where you find it | Notes |
|----------------|--------------------|-------|
| `gawk` (GNU AWK) | Default on Fedora, RHEL, Arch | The reference. Many extensions. We default to it. |
| `mawk` | Default on Debian / Ubuntu (symlinked as `awk`) | Small, fast, fewer extensions. |
| `nawk` (BWK AWK) | Default on FreeBSD, macOS, OpenBSD | The "one true `awk`" from Kernighan himself. |
| `busybox awk` | Embedded systems, Alpine Linux | Cut-down for tiny footprints. |

For everything in this lecture that works only in `gawk` and not in POSIX, we mark it `[gawk-only]`. The portable subset is the POSIX subset.

## 2. The mental model: `pattern { action }`

An `awk` program is a list of `pattern { action }` rules. For each input record (usually a line), `awk`:

1. Reads the record.
2. Splits it into fields by `FS`.
3. For each rule, if the pattern matches, runs the action.
4. Goes back to step 1.

That's it. Everything else is detail.

```bash
# Pattern: anything (empty). Action: print the whole line. Equivalent to `cat`.
awk '{ print }' /etc/passwd

# Pattern: regex matches "root". Action: print field 1.
awk '/root/ { print $1 }' /etc/passwd

# Pattern: empty. Action: print $1. Same as `cut -d' ' -f1` for whitespace-delimited input.
awk '{ print $1 }' /etc/hostname
```

You can omit the action — `awk` defaults to `{ print }`. You can omit the pattern — it defaults to "every record." You cannot omit both. (Well, you can, but you'll get an empty program.)

```bash
# Just a pattern; default action is print:
awk '/sshd/' /var/log/auth.log   # equivalent to `grep sshd`
```

## 3. Fields and `$0`, `$1`, `$NF`

`awk` splits each record into fields. Whitespace by default. You access them by number:

| Reference | Meaning |
|-----------|---------|
| `$0` | The whole record |
| `$1` | The first field |
| `$2` | The second field |
| `$NF` | The last field (NF = "number of fields") |
| `$(NF-1)` | The second-to-last field |

```bash
echo "hello bash yellow world" | awk '{ print $1, $NF }'
# Output: hello world

echo "  spaces  in    front" | awk '{ print $1 }'
# Output: spaces        (awk ignores leading whitespace with default FS)
```

You can assign to fields, too. Assigning rebuilds `$0` using `OFS`:

```bash
echo "a b c d" | awk '{ $2 = "BANG"; print }'
# Output: a BANG c d
```

## 4. Built-in variables

These are the ones you need on day one. `gawk` has many more; the manual has the full list.

| Variable | Meaning | Default |
|----------|---------|---------|
| `NR` | Record number — counts across all inputs | starts at 1 |
| `FNR` | Record number within the current file | resets per file |
| `NF` | Number of fields in the current record | varies per line |
| `FS` | Input field separator | one or more whitespace chars |
| `OFS` | Output field separator | single space |
| `RS` | Input record separator | newline |
| `ORS` | Output record separator | newline |
| `FILENAME` | The current input file name | (empty) on stdin |

A first non-trivial program — print line number and number of fields for every line:

```bash
awk '{ print NR, NF, $0 }' /etc/fstab
```

## 5. Changing the field separator

The most-used pattern. The colon-separated `/etc/passwd`:

```bash
# Print username and shell for every account.
awk -F: '{ print $1, $7 }' /etc/passwd
```

`-F:` sets `FS` to `:`. Equivalently:

```bash
awk 'BEGIN { FS = ":" } { print $1, $7 }' /etc/passwd
```

The `-F` flag accepts regex, too — useful for "split on comma or semicolon":

```bash
echo "a,b;c,d" | awk -F'[,;]' '{ print $3 }'
# Output: c
```

To change the **output** separator:

```bash
awk -F: 'BEGIN { OFS = "\t" } { print $1, $7 }' /etc/passwd
# Username, then a TAB, then the shell.
```

Note: just printing with commas (`print $1, $7`) joins with `OFS`. Printing with concatenation (`print $1 $7`) joins with nothing — they smush together. This bites people.

## 6. `BEGIN` and `END`

`BEGIN { action }` runs once **before** the first record. `END { action }` runs once **after** the last record. They are the entry and exit hooks of an `awk` program.

```bash
# Count lines. Equivalent to `wc -l` for one file.
awk 'END { print NR }' /etc/passwd

# Count lines that contain "root".
awk '/root/ { count++ } END { print count }' /etc/passwd

# Sum the third column of a whitespace-separated file.
awk '{ sum += $3 } END { print "total:", sum }' data.txt
```

That third example is the canonical "why `awk`" example. It's a one-liner; it would be a 6-line Python script. `awk` wins decisively here.

## 7. Conditionals

Inside an action, `if`/`else` is C-shaped:

```bash
awk -F: '{
  if ($3 < 1000) {
    print $1, "(system account)"
  } else {
    print $1, "(human account)"
  }
}' /etc/passwd
```

The pattern itself **is** a conditional, so you can often skip `if`:

```bash
# Same effect, more idiomatic:
awk -F: '$3 < 1000 { print $1, "(system)" }
         $3 >= 1000 { print $1, "(human)" }' /etc/passwd
```

Multiple rules in one program is normal. Each record is tested against every rule, top to bottom.

## 8. Loops

`for` and `while` are C-shaped:

```bash
# Print each field of each line on its own line.
awk '{ for (i = 1; i <= NF; i++) print i, $i }' /etc/hostname
```

```bash
# Reverse the fields of every line.
awk '{ out = ""
       for (i = NF; i >= 1; i--) out = out $i (i > 1 ? " " : "")
       print out }' file.txt
```

The `for (key in array)` form is what makes the next section possible.

## 9. Associative arrays — the killer feature

In `awk`, arrays are associative — keyed by strings, not numbers. There are no declarations. You start using them; they exist.

```bash
# Count occurrences of each shell in /etc/passwd.
awk -F: '
  { shells[$7]++ }
  END {
    for (s in shells) print shells[s], s
  }
' /etc/passwd
```

That's the single most useful `awk` pattern in operations work. Read it three times. Internalize it. You now have a tally tool that beats `sort | uniq -c` when you want to group by something other than "exactly the whole line."

Another example — sum of bytes served per HTTP status code, from an nginx log:

```bash
awk '{ status = $9; bytes = $10; sum[status] += bytes }
     END { for (s in sum) print s, sum[s] }' /var/log/nginx/access.log
```

`awk` arrays do **not** preserve insertion order in POSIX. `gawk` lets you control it via `PROCINFO["sorted_in"] = "@val_num_desc"` — but that's gawk-only. Sort with a pipe to `sort -k2 -n` instead.

## 10. Strings, numbers, and the implicit coercion

`awk` has two scalar types: number and string. It converts automatically. `"42" + 1` is `43`. `"abc" + 1` is `1` (silent zero on bad parse — a footgun, but a deliberate one).

The string concatenation operator is **juxtaposition**. There is no `+` for strings; that always means add.

```bash
awk 'BEGIN { x = "foo" "bar"; print x }'   # foobar
awk 'BEGIN { x = "10" + 5; print x }'      # 15
awk 'BEGIN { x = "10" 5; print x }'        # 105 (string concat)
```

The lack of `+`-for-string is intentional. It means context-sensitive type juggling becomes simpler — you, the reader, can always tell at a glance whether a thing is numeric (uses `+ - * /`) or string (uses juxtaposition).

## 11. Useful built-in functions

| Function | What it does |
|----------|--------------|
| `length(s)` | Length of string `s` (or of `$0` if no arg). `length(arr)` in `gawk` returns count. |
| `substr(s, i, n)` | Substring of `s` starting at `i`, `n` chars long. 1-indexed. |
| `index(s, t)` | First position of `t` in `s`, or `0` if not found. 1-indexed. |
| `split(s, arr, sep)` | Split `s` into `arr` by `sep`. Returns number of fields. |
| `sub(re, sub, in)` | Substitute first match of regex `re` in `in` with `sub`. |
| `gsub(re, sub, in)` | Same but global. Modifies `in` in place. |
| `match(s, re)` | Position of first regex match; sets `RSTART`, `RLENGTH`. |
| `tolower(s)`, `toupper(s)` | Case conversion. |
| `printf(...)` | C-style formatted print. |
| `sprintf(...)` | C-style formatted print into a string. |

Example: `printf` for tidy columns:

```bash
awk -F: '{ printf "%-15s %s\n", $1, $7 }' /etc/passwd
```

`%-15s` means "left-aligned string, padded to 15 characters." That's how you make `awk` output that looks like real tooling.

## 12. Reading from multiple files

`awk` reads files in the order you list them. `NR` keeps counting across files; `FNR` resets.

```bash
awk 'FNR == 1 { print "==>", FILENAME, "<==" } { print }' a.txt b.txt c.txt
```

That replicates `head -n -0` in spirit — file-name banners between files. Useful for log archeology when you have a stack of rotated logs.

## 13. When `awk` wins over Python

`awk` is the right tool when:

- The input is **record-oriented** and the records are simple.
- The transformation is **stateless or has small state** (running counts, max/min, simple groupings).
- Speed matters — `awk` is C, starts in microseconds, processes a million-line log faster than Python imports.
- You need a **one-liner** in a shell pipeline.

Concrete examples where `awk` is the right answer:

- "Sum the 5th column." → `awk '{s+=$5} END {print s}'`
- "Count distinct values in column 3." → `awk '{c[$3]++} END {for (k in c) print c[k], k}'`
- "Print every other line." → `awk 'NR % 2 == 0'`
- "Last field of every line." → `awk '{print $NF}'`

## 14. When to reach for Python instead

`awk` is the wrong tool when:

- The input is **nested** — JSON, XML, anything with a tree structure. Use `jq` for JSON; use Python for XML.
- You need **complex state** — multi-pass joins, lookups against large external tables, anything that wants a real data structure.
- You need **good error messages** when the input is wrong. `awk` is laconic; a misparsed integer becomes a silent zero.
- The program is **longer than 10 lines.** Past 10, you are writing software, not a one-liner. Software belongs in a real language with tests.

The honest rule: write the first 5 lines in `awk`. If you reach 8 and you're not done, stop and rewrite in Python.

## 15. The portability note

You will, sometimes, write an `awk` snippet on Fedora (`gawk`) and ship it to a Debian server (`mawk`). Three things to watch:

1. **`length(arr)`** for an associative-array count — `gawk` only. POSIX: count it yourself in the `END` block with a `++` counter.
2. **`@val_num_desc` sorting via `PROCINFO`** — `gawk` only. Pipe to `sort` instead.
3. **`gensub()`** — `gawk` only. Use `sub`/`gsub` and live with the in-place mutation.

For real portability, write `#!/usr/bin/env -S awk -f` at the top of `.awk` files and stick to POSIX. For "real" programs of even modest size, write `gawk` explicitly with `#!/usr/bin/env -S gawk -f` and require it.

## 16. Two longer examples

### A. A column-summary tool

Given a whitespace-separated numeric file, print min, max, mean, count for column N:

```bash
awk -v col=3 '
  NR == 1 { min = max = $col }
  $col < min { min = $col }
  $col > max { max = $col }
  { sum += $col; n++ }
  END {
    printf "n=%d  min=%g  max=%g  mean=%g\n", n, min, max, sum/n
  }
' data.txt
```

`-v col=3` passes a variable in from the shell. That is how you parameterize an `awk` one-liner without string-interpolating into the program (which would also work, but invites quoting hell).

### B. Top 10 IPs in an nginx access log

```bash
awk '{ ips[$1]++ }
     END { for (ip in ips) print ips[ip], ip }' /var/log/nginx/access.log \
  | sort -rn | head -10
```

That replaces a perfectly reasonable Python script with three lines. The `sort | head` at the end is the right division of labor — `awk` doesn't sort well; `sort` does.

## 17. Self-check

Before you do the exercises, can you answer these without looking back?

- What does `awk '$3 > 1000'` do, given no explicit action?
- What is the difference between `NR` and `FNR`?
- What does `-F:` mean?
- How do you change the output separator?
- What is `$NF`?
- Why does `awk '/error/' file` work without a `{print}`?
- What is the type of `"42" + 1`? Of `"42" "1"`?
- In which implementation does `length(arr)` give the number of keys?

When all eight are easy, the [exercises](../03-exercises/exercise-01-awk-puzzles.md) drill them.

## Further reading

- **`gawk` manual:** <https://www.gnu.org/software/gawk/manual/gawk.html>
- **Eric Pement's `awk` one-liners:** <https://www.pement.org/awk/awk1line.txt>
- **Bruce Barnett's AWK tutorial:** <https://www.grymoire.com/Unix/Awk.html>
- **POSIX awk:** <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/awk.html>

Tomorrow: `sed`, the line-oriented scalpel that pairs with `awk` like `grep` pairs with `find`.
