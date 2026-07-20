# Challenge 01 — CSV Without Python

> **Time:** ~3 hours. **Outcome:** You can parse a real-world CSV with `awk`, and you have a personal, well-defended opinion on where `awk` stops being the right tool.

CSV looks easy. "Just split on commas." Then you meet a real CSV with:

- Quoted fields: `"hello, world",42`.
- Quoted fields containing embedded commas: `"Smith, Alice",42`.
- Quoted fields containing embedded quotes (escaped by doubling): `"She said ""hi""",42`.
- Quoted fields containing embedded newlines: `"line one\nline two",42`.
- Mixed line endings (CRLF vs LF).
- A UTF-8 BOM on the first line.

`awk` with `-F,` handles the first case. The rest is where it gets interesting.

This challenge gives you a real CSV with these horrors, asks you to parse it correctly, and asks you to write down the threshold at which you'd switch to Python's `csv` module.

## The dataset

Generate it locally — no download required. Save as `~/c14-week-02/messy.csv`:

```bash
mkdir -p ~/c14-week-02
cat > ~/c14-week-02/messy.csv <<'CSV'
id,name,role,note,salary
1,Alice Smith,engineer,clean record,95000
2,"Bob, Jones",engineer,"Has a comma in name",105000
3,Carol Lee,manager,"Uses ""quoted"" words",125000
4,Dan Ng,intern,"Multi-line
note here",30000
5,Eve OConnor,engineer,plain,98000
6,Frank,manager,"Has both ""quotes"" and a , comma",115000
CSV
```

Open it in `cat -A` to see exactly what is in there:

```bash
cat -A ~/c14-week-02/messy.csv
```

You should see `$` at line ends and notice the multi-line "note" field is broken across two physical lines.

## Tasks

### Task 1 — Naïve parse

Write the obvious `awk -F,` one-liner that prints field 2 (the name) of each line. Note where it goes wrong on this dataset.

```bash
awk -F, '{ print $2 }' ~/c14-week-02/messy.csv
```

**Acceptance:** Output, plus a list of the specific lines where the naïve parser is wrong, plus a one-sentence diagnosis of each.

---

### Task 2 — Use the right `FS` for the simple case

`gawk` supports `FPAT` — define a pattern for what a *field* looks like, not what the *separator* looks like. This handles quoted fields containing commas (but not embedded newlines):

```bash
awk -v FPAT='([^,]*)|("[^"]*")' '{ print $2 }' ~/c14-week-02/messy.csv
```

Run it. **Note:** `FPAT` is a `gawk` extension; this will fail on `mawk`. Check with `ls -l $(which awk)`. If you're on Ubuntu, install `gawk` and call it explicitly:

```bash
sudo apt install gawk
gawk -v FPAT='([^,]*)|("[^"]*")' '{ print $2 }' ~/c14-week-02/messy.csv
```

**Acceptance:** Output that handles commas inside quotes correctly. The multi-line field will still be broken — that's the next task.

---

### Task 3 — Handle multi-line fields

The "Dan Ng" row has a quoted field that spans two physical lines in the file but is logically one record. Two approaches:

**A. Pre-process with `awk`** — set `RS` (record separator) to a smarter pattern. This is hard. Skim and skip if it's not your thing:

```awk
# Concatenate physical lines until quotes balance.
{
  buf = buf $0
  n = gsub(/"/, "&", buf)
  if (n % 2 == 0) {
    # Quotes balanced. Process buf as a complete record.
    print "RECORD: " buf
    buf = ""
  } else {
    # Inside a quoted field. Keep accumulating.
    buf = buf " "  # or "\n" if you want to preserve
  }
}
```

Run that as a script file `csv-join.awk`:

```bash
awk -f csv-join.awk ~/c14-week-02/messy.csv
```

**B. Pre-process with Python** — admit defeat on the `awk`-only constraint:

```python
import csv
with open('/Users/.../messy.csv', newline='') as f:
    for row in csv.reader(f):
        print(row)
```

Run both. Note how many lines of code each is. **This is the lesson.** `awk` can do it. `csv.reader` does it in two lines.

**Acceptance:** Two implementations — `awk` and Python — and a paragraph comparing them.

---

### Task 4 — A real query

With your CSV parsed correctly, answer:

> What is the average salary by role?

In `awk` (assuming Task 3's joined records and `FPAT` from Task 2):

```bash
gawk -v FPAT='([^,]*)|("[^"]*")' '
  NR > 1 {
    role   = $3
    salary = $5
    gsub(/"/, "", salary)
    sum[role] += salary
    n[role]++
  }
  END {
    for (r in sum) printf "%-12s %.0f\n", r, sum[r]/n[r]
  }
' ~/c14-week-02/messy.csv
```

In Python:

```python
import csv, collections
sums = collections.Counter()
counts = collections.Counter()
with open('messy.csv', newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        sums[row['role']]   += int(row['salary'])
        counts[row['role']] += 1
for r in sums:
    print(f"{r:<12} {sums[r] / counts[r]:.0f}")
```

**Acceptance:** Both implementations work and produce the same numbers.

---

### Task 5 — Write your "switch point"

In `decision.md`, write 300 words on:

1. At what kind of CSV does `awk` stop being the right tool? Be specific about CSV features (embedded newlines, BOMs, mixed encodings, etc.).
2. What would you keep in `awk` even on a "rich" CSV? Are there queries that are fine to write in `awk` against a pre-cleaned file?
3. Would you ever use `awk` on CSV in production code (not a one-off shell session)? Why or why not?

This is the artifact the challenge is really about. The code is the means; the considered opinion is the end.

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Naïve parse + diagnosis | 15% | Identifies all 3+ failure modes in the dataset |
| `FPAT` parse | 20% | Working `gawk` command, with `mawk`-vs-`gawk` note |
| Multi-line handling | 25% | Either a working `awk` script OR a clear "I switched to Python here, because…" |
| Real query | 20% | Same answer from both implementations |
| Decision write-up | 20% | A defensible, specific opinion with examples |

---

## Stretch

- Try [`csvkit`](https://csvkit.readthedocs.io/) — `csvcut`, `csvgrep`, `csvstat`. It's Python under the hood but feels like Unix tools. Sometimes the right answer is "use the right tool, even if it's not `awk`."
- Try [`miller`](https://miller.readthedocs.io/) (`mlr`) — "the awk of CSV/JSON." Same model, but knows CSV. `apt install miller` or `dnf install miller`.
- Try [`q`](http://harelba.github.io/q/) — SQL queries on CSV files. Sometimes you really want SQL.

The honest summary: real CSV processing in production uses Python's `csv` or one of `mlr`/`csvkit`/`q`. `awk` is for pipelines where the input is *clean* — and your judgment call about what "clean" means is the actual skill.
