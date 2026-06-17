# Week 2 — Quiz

Ten multiple-choice. Lectures closed. Aim 9/10 before Week 3.

---

**Q1.** Which of these is the correct mental model of an `awk` program?

- A) A series of `if/else` statements run against the whole file at once.
- B) A list of `pattern { action }` rules; for each input record, every rule whose pattern matches has its action run.
- C) A regex that the shell expands before invoking `awk`.
- D) A single function that returns the transformed file.

---

**Q2.** When you give `awk` a pattern but no action — e.g., `awk '/error/' file.txt` — what is the default action?

- A) Print the matching line.
- B) Print nothing (silent match).
- C) Print the first field of the matching line.
- D) Exit with status 1.

---

**Q3.** In `awk`, what does `$NF` refer to?

- A) The number of fields.
- B) The last field.
- C) The whole record.
- D) The current record number.

---

**Q4.** Which `awk` block runs **once before** the first input line is read?

- A) `BEGIN { ... }`
- B) `END { ... }`
- C) `BEGINFILE { ... }`
- D) The first rule in the program.

---

**Q5.** You want to count occurrences of each shell in `/etc/passwd`. Which best fits?

- A) `awk -F: '{ print $7 }' /etc/passwd`
- B) `awk -F: '{ shells[$7]++ } END { for (s in shells) print shells[s], s }' /etc/passwd`
- C) `awk -F: '{ count++ } END { print count }' /etc/passwd`
- D) `awk '/sh/' /etc/passwd | wc -l`

---

**Q6.** What does `sed -i 's/foo/bar/g' file.txt` do on GNU sed (Linux)?

- A) Replace every `foo` with `bar` in `file.txt`, modifying the file in place, no backup.
- B) Replace every `foo` with `bar` and print to stdout, leaving `file.txt` untouched.
- C) Replace `foo` with `bar` only on the first match.
- D) Error — `-i` requires a suffix argument.

---

**Q7.** On macOS (BSD sed), which form is correct for "in place, no backup"?

- A) `sed -i 's/foo/bar/g' file.txt`
- B) `sed -i '' 's/foo/bar/g' file.txt`
- C) `sed -i.bak 's/foo/bar/g' file.txt`
- D) `sed --in-place 's/foo/bar/g' file.txt`

---

**Q8.** In a `sed` replacement, what is the difference between `\1` and `&`?

- A) `\1` is the whole match; `&` is the first capture group.
- B) `\1` is the first capture group; `&` is the whole match.
- C) Both mean "the whole match."
- D) `\1` is the line number; `&` is the literal `&`.

---

**Q9.** Which of these is a `gawk` extension, NOT in POSIX `awk`?

- A) `NR` (record number)
- B) Associative arrays
- C) `length(array)` returning the count of keys
- D) `BEGIN { ... } END { ... }`

---

**Q10.** When should you NOT reach for `awk`?

- A) When summing a numeric column in a whitespace-separated file.
- B) When parsing JSON.
- C) When counting distinct values in a field.
- D) When extracting field N.

---

## Answer key

<details>
<summary>Reveal after attempting</summary>

1. **B** — `pattern { action }` is the model. Every rule is tested against every record.
2. **A** — when a rule has a pattern but no action block, the default action is `{ print }`. This is what makes `awk '/error/' file.txt` work as a `grep` substitute.
3. **B** — `$NF` is the last field; `NF` (no `$`) is the count of fields.
4. **A** — `BEGIN`. `BEGINFILE` is a `gawk` extension.
5. **B** — the associative-array idiom. A is just printing all shells, no counts. C counts total lines.
6. **A** — in place, no backup. On GNU, `-i` with no suffix is "no backup."
7. **B** — BSD `-i` requires a suffix; the empty string `''` means "no backup."
8. **B** — `\1` is the first capture group; `&` is the whole match.
9. **C** — `length(array)` for the key count is `gawk`. POSIX `length()` works on strings only.
10. **B** — JSON has nested structure; `awk` is record-oriented and flat. Use `jq` or Python.

</details>

If you scored 9+: move to homework. 7–8: re-read the lecture sections you missed. <7: re-read both lectures from the top.
