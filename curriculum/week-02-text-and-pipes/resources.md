# Week 2 — Resources

Free, public, no signup unless noted.

## Required reading

- **GNU `gawk` user guide** — the comprehensive reference. Read at least chapters 1–4:
  <https://www.gnu.org/software/gawk/manual/gawk.html>
- **GNU `sed` manual** — short, dense, worth the hour:
  <https://www.gnu.org/software/sed/manual/sed.html>
- **POSIX `awk` specification** — the contract every implementation aspires to meet:
  <https://pubs.opengroup.org/onlinepubs/9699919799/utilities/awk.html>

## Books

- **"The AWK Programming Language" — Aho, Kernighan, Weinberger** (2nd ed., 2023). The original 1988 edition by the original authors. The 2nd edition is the same authors, 35 years later, with modern examples. Search Brian Kernighan's site for the free draft chapters.
  <https://www.cs.princeton.edu/~bwk/>
- **"sed & awk" — Dale Dougherty, Arnold Robbins** (O'Reilly, 2nd ed.). Not free, but the table of contents on its own is a curriculum:
  <https://www.oreilly.com/library/view/sed-awk/1565922255/>
- **"Classic Shell Scripting" — Robbins & Beebe** — pairs `awk`/`sed` with the rest of the shell ecosystem.

## Cheat sheets

- **`gawk` quick reference** (built into the manual, Appendix B):
  <https://www.gnu.org/software/gawk/manual/html_node/Quick-Reference.html>
- **`sed` one-liners explained** — Peter Krumins' "Sed One-Liners Explained" series; legendary:
  <https://catonmat.net/sed-one-liners-explained-part-one>
- **`awk` one-liners explained** — same author, same series:
  <https://catonmat.net/awk-one-liners-explained-part-one>

## Videos (free)

- **Brian Kernighan on AWK** — co-creator, 45 minutes:
  <https://www.youtube.com/results?search_query=brian+kernighan+awk>
- **MIT 6.NULL "Missing Semester" — Data Wrangling lecture** — covers `sed`, `awk`, `grep`, regex:
  <https://missing.csail.mit.edu/2020/data-wrangling/>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install gawk sed pcregrep gron jq

# Fedora
sudo dnf install gawk sed pcre-tools gron jq
```

- `gawk` — install it even if `mawk` is already there. Lectures use `gawk`-style features (`length()` on arrays, etc.).
- `pcregrep` — Perl-compatible regex `grep`, useful when basic/extended regex isn't enough.
- `gron` — flattens JSON for `grep`. Not on the curriculum, but a useful sibling to `awk` for JSON.
- `jq` — JSON's `awk`. Not this week; previewed for Week 5.

## Distro differences cheat sheet

| Concern | Ubuntu 24.04 LTS | Fedora 41 |
|---------|-------------------|-----------|
| `awk` default | `mawk` (symlinked) | `gawk` (symlinked) |
| `sed` flavor | GNU | GNU |
| GNU coreutils | yes | yes |
| Install `gawk` | `apt install gawk` | already installed |
| Locale defaults | `en_US.UTF-8` | `en_US.UTF-8` |

Both are GNU `sed`. The `awk` difference matters: `length(arr)` works in `gawk`, not in strict POSIX or `mawk`. We flag it in lectures.

## Free books and write-ups

- **"AWK — A Tutorial and Introduction" — Bruce Barnett** — a thorough free tutorial, oldest on the web that's still maintained:
  <https://www.grymoire.com/Unix/Awk.html>
- **"Sed — An Introduction and Tutorial" — Bruce Barnett** — companion piece:
  <https://www.grymoire.com/Unix/Sed.html>
- **Julia Evans — "Examples with bash"** — short, drawing-heavy explainers:
  <https://wizardzines.com/comics/>

## One-liner libraries

- **Eric Pement's `awk` one-liners** — a famous text file from the early 2000s, still useful:
  <https://www.pement.org/awk/awk1line.txt>
- **Eric Pement's `sed` one-liners** — same vintage, same value:
  <https://www.pement.org/sed/sed1line.txt>

Print both. Tape them to a wall.

## Glossary

| Term | Definition |
|------|------------|
| **Record** | One unit `awk` processes at a time. By default, one line. |
| **Field** | One substring of a record, split by `FS`. By default, whitespace-separated. |
| **`NR`** | Record number (1-based). Counts across files. |
| **`FNR`** | Record number within the current file. Resets on file change. |
| **`NF`** | Number of fields in the current record. |
| **`FS`** | Input field separator. Default: whitespace. |
| **`OFS`** | Output field separator. Default: single space. |
| **`RS`** | Input record separator. Default: newline. |
| **`ORS`** | Output record separator. Default: newline. |
| **Pattern** | The condition before `{ action }`. A regex, an expression, `BEGIN`, `END`, or empty (every line). |
| **Action** | The code in `{ ... }` to run when the pattern matches. |
| **Hold space** | A second buffer in `sed`. The pattern space is the "main" one. |
| **Pattern space** | The buffer `sed` is currently working on. |
| **GNU vs BSD** | `sed`/`awk` from the GNU project (Linux default) vs Berkeley descendants (macOS default). Differ on `-i`. |

---

*Broken link? Open an issue.*
