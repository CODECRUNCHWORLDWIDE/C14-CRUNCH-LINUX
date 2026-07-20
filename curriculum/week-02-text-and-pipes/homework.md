# Week 2 — Homework

Six problems, ~6 hours total. Commit each to your portfolio repo under `c14-week-02/homework/`.

These are the practice problems between the exercises (which drilled the basics) and the mini-project (which asks you to compose freely). Treat them as fluency reps.

---

## Problem 1 — `awk` rewrites of `cut` and `grep` (45 min)

For each command below, write the equivalent `awk` invocation. Run both; verify identical output.

| Original | `awk` equivalent? |
|----------|-------------------|
| `cut -d: -f1 /etc/passwd` | ? |
| `cut -d: -f1,7 /etc/passwd` | ? |
| `grep '^root' /etc/passwd` | ? |
| `grep -v '^#' /etc/services` | ? |
| `wc -l /etc/passwd` | ? |
| `head -5 /etc/hostname` | ? |
| `tail -5 /etc/hostname` (hardest — needs state) | ? |

**Acceptance:** `homework/01-awk-rewrites.md` with the original, your `awk` version, and `diff` output (or "identical") for each pair. For `tail -5`, accept that this is where `awk` stops being clean — explain in one sentence why.

---

## Problem 2 — Field reformatting (45 min)

Given `/etc/passwd`, produce a tab-separated report with these columns:

```
USERNAME    UID    GID    SHELL_BASENAME
```

`SHELL_BASENAME` is the last component of the shell path — e.g., `/bin/bash` becomes `bash`. Use `awk` only. (`split(shell, parts, "/"); basename = parts[length(parts)]` is one way; `gsub(".*/", "", shell)` is another.)

**Acceptance:** `homework/02-passwd-report.md` with the command and a sample of the output. Sort the output by UID descending using a pipe to `sort -t$'\t' -k2 -rn`.

---

## Problem 3 — `sed` cleanup pipeline (60 min)

Take a config file with comments, blank lines, and inconsistent whitespace — for example, `/etc/services` or `/etc/ssh/sshd_config`. Use `sed` (only `sed`, no `awk` or `grep`) to produce a clean version that:

1. Strips comment lines (whole-line comments only — don't break `#` inside strings if any).
2. Strips blank lines.
3. Squeezes multiple spaces into single spaces.
4. Strips trailing whitespace.

Save your `sed` program as `homework/03-cleanup.sed` and run it with `sed -f`.

**Acceptance:** The `.sed` file, plus `cleaned.txt` showing the result, plus a one-paragraph note on which step caused the most regex pain. Don't use `awk`, `grep`, or Python in the pipeline.

---

## Problem 4 — Sanitize a log for sharing (45 min)

You want to share a log excerpt with a friend / on a public issue tracker. Strip PII-ish identifiers:

- IPv4 addresses → `X.X.X.X`.
- IPv6 addresses → `X:X:X:X::X` (rough — full IPv6 regex is its own challenge).
- Hostnames that look like internal hostnames (e.g., `db01.internal.example.com`) → `host.internal`.
- Usernames in lines like `for USER from` → `for U from`.

Write the `sed` (or `sed`-and-`awk`) pipeline. Test it on a copy of your real log file.

**Acceptance:** `homework/04-redact.sh` — a small wrapper that takes a file and writes a redacted version. Include before/after samples (3-5 lines each) in `04-redact-notes.md`.

A trap to avoid: redacting before you've extracted the data you need. Always redact at the **end** of your pipeline, never the start.

---

## Problem 5 — Group-by aggregation (60 min)

For any log on your machine — pick one that has at least 1000 lines (`ls -l /var/log/`) — write **three** different group-by-and-count queries in `awk`. Each should use an associative array.

Examples for `/var/log/auth.log`:

1. Failed logins per username.
2. Failed logins per source IP.
3. Failed logins per hour of day.

Or for `/var/log/syslog`:

1. Lines per program name (the bracketed program in the prefix).
2. Lines per hour.
3. Lines containing "error" or "fail" per program.

**Acceptance:** `homework/05-three-aggregations.md` with three `awk` programs, sample output, and a brief comment per query: was `awk` clean here, or would `cut | sort | uniq -c` have been simpler?

---

## Problem 6 — Reflection (45 min)

`homework/06-reflection.md`, 400-500 words:

1. After this week, which of these would you reach for, in order, for "I need to transform a text file": `cut`, `grep`, `awk`, `sed`, Python? Why?
2. What surprised you about `awk`?
3. What surprised you about `sed`?
4. What's the longest one-liner pipeline you wrote this week, and would you commit it to a script-shared-with-coworkers, or only use it interactively?
5. Cite the Bash Yellow line at the top of your favorite lecture from this week. (Yes, this is a small loyalty test.)

---

## Time budget

| Problem | Time |
|--------:|----:|
| 1 | 45 min |
| 2 | 45 min |
| 3 | 1 h |
| 4 | 45 min |
| 5 | 1 h |
| 6 | 45 min |
| **Total** | **~5 h** |

After homework, ship the [mini-project](./mini-project/README.md).
