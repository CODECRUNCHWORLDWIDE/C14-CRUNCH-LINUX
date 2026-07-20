# Mini-Project — A Log-Analysis Pipeline

> Take a real log file from your own machine's `/var/log` (or `journalctl` output) and answer five non-trivial questions about it, using a single shell pipeline per question. No Python. No notebooks. Just `awk`, `sed`, `grep`, `sort`, `uniq`, `cut`, `wc`, and the rest of the Week 2 toolkit.

**Estimated time:** 6–7 hours, spread Thursday–Saturday.

This mini-project is the artifact that proves Week 2 took. Anyone who finishes it can read a log file with command-line tools — which is most of what an operator does on a bad day. You will not write a single line of Python.

---

## Deliverable

A directory in your portfolio repo `c14-week-02/mini-project/` containing:

1. `README.md` — the prose write-up, structured as the five questions and their answers.
2. `pipelines.sh` — every pipeline you ran, in order, runnable end-to-end. (Treat this as a script — even if it's just `set -euo pipefail` and a list of `awk`/`sed` commands.)
3. `redacted.log` — the redacted excerpt of the log you analyzed, safe to commit to a public repo.
4. `notes.md` — your scratch space. Not required to be polished; it is your evidence of process.

---

## Choose your log

Pick **one** log file with at least 1000 lines. Order of preference:

1. `/var/log/auth.log` on Ubuntu, or `journalctl -u sshd > sshd.log` on Fedora.
2. `/var/log/nginx/access.log` if you have nginx running.
3. `/var/log/syslog` (Ubuntu) or `journalctl --since "1 week ago" > syslog.log` (Fedora).
4. `dmesg > dmesg.log` — kernel ring buffer; smaller and quirkier but workable.
5. The auth log from a $5/mo VPS you've spun up — these are *gold* for SSH brute-force analysis.

**Sudo-restricted reads:** copy with sudo to your home dir first, change ownership:

```bash
mkdir -p ~/c14-week-02/mini-project
sudo cp /var/log/auth.log ~/c14-week-02/mini-project/auth.log
sudo chown "$USER:$USER" ~/c14-week-02/mini-project/auth.log
```

If you're on Fedora 41 where `/var/log/auth.log` doesn't exist (most logging is in journald):

```bash
journalctl -u sshd --since "1 week ago" > ~/c14-week-02/mini-project/auth.log
```

That gives you a flat file in roughly the same shape.

---

## The five questions

You must answer all five for the log you chose. Adapt the wording to your log format — the **questions** are about activity patterns, not auth specifically.

### Question 1 — Volume

> How many lines does the log have, and over what time window? What is the average rate (lines per hour)?

Pipeline must use `awk` for the count, and `awk` (or `sed` + `date`) for parsing the first and last timestamps.

### Question 2 — Top actors

> What are the top 10 source IPs (or usernames, or program names, depending on log type) by frequency? What proportion of the log do the top 10 represent?

Pipeline must use an `awk` associative array to count, and then `sort | head` for the top-10.

### Question 3 — Temporal pattern

> How is activity distributed across the hours of a day? Is there a clear peak hour?

Pipeline must extract the hour from the timestamp using `awk`'s `substr` or `split`, count per hour, and produce a small histogram (a count + a row of `#` chars works fine):

```
00 |####
01 |######
...
14 |##############################
```

The histogram itself can be done with `awk` `printf` and a loop.

### Question 4 — Anomaly detection (light)

> Identify the top 3 source IPs (or actors) by a "suspicious" criterion. For SSH: top 3 IPs by failed-login count where the count is more than 10. For nginx: top 3 IPs returning 4xx responses. For syslog: top 3 programs that emitted lines containing "error" or "fail" (case-insensitive).

Pipeline must combine `grep` (or `awk` pattern) to filter, `awk` to aggregate, and `awk` again (or `sort` + `awk`) to threshold and rank.

### Question 5 — Redact for sharing

> Produce a `redacted.log` — your raw log with all IP addresses replaced with `X.X.X.X` and all usernames in `for USER` patterns replaced with `U`. Demonstrate that the redacted log still answers Question 2 correctly (the top-N rankings should still be derivable, even though the names are now `U`).

Pipeline must use `sed` — not `awk` — for the substitution.

---

## Constraints

- Each question must be answered with **one pipeline**. A pipeline is whatever can be written on one line (line continuations are fine), but it has to read top to bottom without temp files.
- You may use: `awk`, `sed`, `grep` (basic and `-E`), `cut`, `sort`, `uniq`, `wc`, `head`, `tail`, `tr`, `paste`, `tee`, `xargs`. You may use shell variables.
- You may NOT use: Python, Perl, Ruby, Node, `jq` (next week's tool), a notebook, a spreadsheet.
- For Question 3, the histogram is part of the pipeline output — not a separate "now plot it" step.
- Every command must work on Ubuntu 24 AND Fedora 41. If a command relies on `gawk`-specific behavior, call out the dependency in a comment.

---

## Suggested workflow

### Phase 1 — Pick the log and get a feel for it (30 min)

```bash
wc -l ~/c14-week-02/mini-project/auth.log
head -20 ~/c14-week-02/mini-project/auth.log
tail -20 ~/c14-week-02/mini-project/auth.log
# What's the line shape? What fields are there?
awk '{ print NF }' ~/c14-week-02/mini-project/auth.log | sort -u | head
```

Write a one-paragraph "log format" note in `notes.md` — what each field appears to mean, sample line, source.

### Phase 2 — Answer questions 1 and 2 (1.5h)

These are warm-ups. Use the patterns from the lectures and exercises directly.

### Phase 3 — Answer question 3 (1.5h)

The histogram is the part most people overthink. Hint: build it in two passes if you have to.

```bash
awk '{ split($3, t, ":"); hours[t[1]]++ }
     END {
       max = 0; for (h in hours) if (hours[h] > max) max = hours[h]
       for (h = 0; h < 24; h++) {
         hr = sprintf("%02d", h)
         bar = ""
         scaled = int(hours[hr] * 40 / max)
         for (i = 0; i < scaled; i++) bar = bar "#"
         printf "%s |%-40s %d\n", hr, bar, hours[hr]+0
       }
     }' ~/c14-week-02/mini-project/auth.log
```

That's one pipeline. Read it line-by-line in `notes.md`.

### Phase 4 — Answer question 4 (1h)

The "threshold + rank" combination. Be explicit about what "suspicious" means; document your criterion.

### Phase 5 — Answer question 5 and redact (1h)

`sed -E` with IPv4 and `for USER` patterns. Verify by re-running Question 2 against `redacted.log` — the ranks should hold even though the labels are now anonymous.

### Phase 6 — Write up and commit (1h)

In `README.md`, for each question:

- The question, restated.
- The pipeline, in a fenced code block.
- The output (first 10 lines or summary; full output in a folder if it's long).
- Two sentences of interpretation: what does this answer tell you about the system?

---

## Acceptance criteria

- [ ] `README.md` answers all five questions.
- [ ] `pipelines.sh` runs end-to-end and produces the same outputs as `README.md`.
- [ ] `redacted.log` exists and is genuinely redacted — `grep -E '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' redacted.log` returns only `X.X.X.X`.
- [ ] No Python, no `jq`, no notebooks.
- [ ] Each pipeline is a single pipeline (line continuations OK; temp files NOT OK).
- [ ] At least one pipeline uses an `awk` associative array.
- [ ] At least one pipeline uses `sed` with a capture group OR a regex address.
- [ ] A "this would not work on `mawk` because…" comment exists somewhere if you used a `gawk`-only feature.

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Correctness of answers | 30% | All five questions have working pipelines and correct outputs |
| Pipeline elegance | 20% | Pipelines read top to bottom; no temp files; each tool does what it's best at |
| `awk` depth | 15% | At least two distinct `awk` techniques (arrays, `BEGIN`/`END`, conditionals, `printf`) |
| `sed` depth | 10% | Redaction uses `sed` with regex; ideally a capture group |
| Write-up quality | 15% | Each pipeline is explained; output is interpreted, not just shown |
| Portability note | 10% | At least one explicit GNU-vs-`mawk` or GNU-vs-BSD callout |

---

## Why this matters

Every Linux job — sysadmin, SRE, security analyst, embedded debugger, DevOps engineer — has a "read the log, find the pattern" reflex as a core skill. Most people never build it because the first time they need it they're under pressure, and they reach for the language they already know. This mini-project builds the reflex when there's no pressure.

It also feeds directly into:

- **Week 5** (`systemd` and `journald`) — you'll be reading `journalctl` output constantly.
- **Week 7** (observability and "why is it slow?") — log analysis is half of that week.
- **C6 — Cybersecurity Crunch** — log analysis is half of security work.
- **C15 — Crunch DevOps** — same story, at scale.

The pipelines you write this week are the muscle memory you'll deploy on real incidents for the rest of your career.

---

When done: push and start [Week 3 — Permissions, users, groups, ACLs](../../week-03/) (coming soon).
