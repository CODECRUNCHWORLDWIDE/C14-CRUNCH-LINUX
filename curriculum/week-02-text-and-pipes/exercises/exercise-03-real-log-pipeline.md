# Exercise 03 — A Real Log Pipeline

**Time:** ~2 hours. **Goal:** Combine `awk`, `sed`, `grep`, `sort`, `uniq` into pipelines that answer real questions about a real log file.

This is a warm-up for the mini-project. The mini-project asks five questions; this exercise asks seven smaller ones, with hints, on a single chosen log.

## Setup — pick a log

Pick the first one you have on hand. Order of preference:

```bash
# Ubuntu 24.04 — auth log
ls -l /var/log/auth.log

# Fedora 41 — journal (synthesize a flat file)
sudo journalctl -u sshd --since "1 week ago" > ~/c14-week-02/sshd.log

# Either — nginx access log (if installed)
ls -l /var/log/nginx/access.log

# Last-ditch — kernel ring buffer
dmesg > ~/c14-week-02/dmesg.log
```

If `auth.log` is owned by root and unreadable, copy it with sudo:

```bash
sudo cp /var/log/auth.log ~/c14-week-02/auth.log
sudo chown $USER:$USER ~/c14-week-02/auth.log
```

Work on the copy. The original is the system's; don't mangle it.

For the rest of this exercise we'll call your chosen file `~/c14-week-02/LOG` — substitute as appropriate.

---

## Question 1 — How many lines?

Use `awk` (not `wc`). Report the count.

**Hint:** `awk 'END { print NR }' "$LOG"`.

---

## Question 2 — How many unique source IPs (or hostnames)?

If it's an SSH log, the source IP appears near "from X.X.X.X." If it's nginx, it's field 1.

**For auth.log:**

```bash
awk '/Failed password|Accepted/ {
  for (i = 1; i <= NF; i++) if ($i == "from") { print $(i+1); break }
}' "$LOG" | sort -u | wc -l
```

**For nginx access.log:**

```bash
awk '{ print $1 }' "$LOG" | sort -u | wc -l
```

**Acceptance:** A single number. Note in your answer which log format you chose.

---

## Question 3 — Top 10 by source

Top 10 source IPs (or usernames, if it's auth.log) by frequency.

**Hint:** `awk` to extract the field; `sort | uniq -c | sort -rn | head`.

```bash
awk '/Failed password/ {
  for (i = 1; i <= NF; i++) if ($i == "from") { print $(i+1); break }
}' "$LOG" | sort | uniq -c | sort -rn | head
```

**Acceptance:** 10 rows, count then value, largest first.

---

## Question 4 — When did the activity happen?

Aggregate by hour. For an auth log, the first three fields are typically `Jul 23 14:01:32` — extract the hour from field 3 with `sed` or `awk`'s `substr`.

```bash
awk '{ split($3, t, ":"); print t[1] }' "$LOG" | sort | uniq -c | sort -rn
```

**Acceptance:** A table of hour-of-day vs count. Comment in 1-2 sentences on the busiest hour.

---

## Question 5 — Sanitize PII-ish data with `sed`

Before you commit your log excerpts to a portfolio, strip the source IP addresses. Replace any `from N.N.N.N` with `from X.X.X.X`.

**Hint:** `sed -E 's/from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/from X.X.X.X/g'`.

```bash
sed -E 's/from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/from X.X.X.X/g' "$LOG" > "$LOG.redacted"
```

**Acceptance:** A redacted version of the log, suitable for committing. `diff "$LOG" "$LOG.redacted" | head` shows the redactions.

---

## Question 6 — A multi-step pipeline

Put it together. Build one pipeline that:

1. Reads `$LOG`.
2. Filters to `Failed password` lines only (grep or `awk` pattern).
3. Extracts the username (after `for `) and source IP (after `from`).
4. Sorts and uniques `(username, ip)` pairs.
5. Counts how many distinct `(username, ip)` pairs there are.

```bash
awk '/Failed password for/ {
  user = ""; ip = ""
  for (i = 1; i <= NF; i++) {
    if ($i == "for")  user = $(i+1)
    if ($i == "from") ip   = $(i+1)
  }
  if (user && ip) print user, ip
}' "$LOG" | sort -u | wc -l
```

**Acceptance:** A single count. Save the pipeline in `answers.md` with a sentence per stage explaining its role.

---

## Question 7 — Cross-distro sanity check

If you have both Ubuntu and Fedora available, run Question 4 on both. Notice:

- Ubuntu's `awk` is `mawk` by default — check with `ls -l $(which awk)`.
- Fedora's `awk` is `gawk` by default.
- The pipeline should produce the same answer.

If you can only run it on one, that's fine — but write a paragraph on what difference you'd expect, citing one specific `mawk`-vs-`gawk` feature gap from Lecture 1.

**Acceptance:** Either two runs with identical-shape output, or a paragraph predicting the behavior on the other distro.

---

## Reflection (5 min)

- Which question taught you the most?
- Which one wanted to be Python — and why?
- What's the longest pipeline you wrote, by `|` count? (More than 5 is usually a sign to refactor into a script.)

---

When done, push. You are now ready for the [mini-project](../mini-project/README.md) — a five-question log analysis, with no hand-holding.
