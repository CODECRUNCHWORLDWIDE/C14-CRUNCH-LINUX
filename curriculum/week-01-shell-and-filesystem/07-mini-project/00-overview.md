# Mini-Project — Filesystem Map

> Draw the filesystem of your own Linux machine. By hand. On paper or in a diagram tool. Then explain what each directory is for, in your own words.

**Estimated time:** 6–7 hours, spread across Thursday-Saturday.

This mini-project produces a single artifact: **a one-page filesystem map** of YOUR machine — with notes on what each top-level directory contains, in your own voice, with examples drawn from your actual system. It's the perfect Week-1 deliverable because it forces you to look at the real thing instead of memorizing abstractions.

---

## Deliverable

A directory in your portfolio repo `c14-week-01/mini-project/` containing:

1. `filesystem-map.svg` (or `.png`, or `.pdf`) — the visual.
2. `filesystem-map.md` — the prose write-up.
3. `commands.md` — every command you ran to gather the data.

---

## Suggested workflow

### Phase 1 — Gather data (1h)

For each top-level directory, run something to peek inside:

```bash
ls -la /
du -sh /* 2>/dev/null              # size of each top-level dir
ls /etc | wc -l                    # how many configs?
ls /var/log | head                 # what logs?
ls /usr/bin | wc -l                # how many binaries installed?
cat /proc/version                  # kernel info
df -h                              # disk usage
```

Save the relevant outputs to `commands.md`.

### Phase 2 — Draw (2h)

Pick a tool:

- **Excalidraw** (free, browser-based, sketchy aesthetic): <https://excalidraw.com/>
- **draw.io / diagrams.net** (free, more structured): <https://www.diagrams.net/>
- **Mermaid** in a markdown file: <https://mermaid.live/>
- **Paper + camera**: legitimately fine.

Sketch the root, then each top-level directory as a child, with 2–3 example files inside each that you actually found on your machine.

### Phase 3 — Annotate (2h)

For each top-level directory, write a 2–3 sentence note in `filesystem-map.md`:

1. What's it for? (One sentence.)
2. What did **you** find inside on your machine? (One sentence with a real example.)
3. When might you need to look here? (One sentence.)

### Phase 4 — Polish + commit (1h)

- Export the diagram to SVG or PNG.
- Re-read the write-up out loud. Tighten.
- Commit, push.

---

## Acceptance criteria

- [ ] `filesystem-map.svg` (or equivalent) exists and shows at least 12 top-level directories.
- [ ] `filesystem-map.md` has a section per directory, each ≥ 50 words, with at least one *specific* example from your machine.
- [ ] `commands.md` records every command you ran to investigate.
- [ ] The map is not a copy of FHS — it reflects what's actually on your system. You point out, for instance, that `/opt` on your laptop is empty, or that `/var/log/journal` is the biggest thing in `/var/log`.

---

## Rubric

| Criterion | Weight | "Great" looks like |
|-----------|------:|--------------------|
| Diagram accuracy | 25% | Shows ≥12 top-level dirs with examples |
| Specificity | 25% | Real examples from your machine, not generic |
| Coverage | 20% | All 12+ directories explained, none skipped |
| Writing quality | 15% | Readable without prior knowledge |
| Command log | 15% | Reproducible — someone could re-do the investigation |

---

## Why this matters

You will refer back to this map *frequently* for the rest of C14, and again any time you set up a new Linux machine. Future-you will thank present-you for taking three hours to make it real.

It also serves as the foundation for C6 (security needs filesystem knowledge), C7 (embedded needs `/proc`, `/sys`, `/dev`), and C15 (DevOps needs `/etc`, `/var`, `/srv` fluency).

---

When done: push and start [Week 2 — Text and Pipes](../../week-02-text-and-pipes/) (coming soon).
