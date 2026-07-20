# Challenge 1 — Recover from a (Simulated) Disaster

**Time:** ~75 minutes. **Difficulty:** Medium.

## Setup

In a **VM you don't care about** (NOT your daily-driver machine), run this script. It simulates a common "I broke it" state.

```bash
# DO NOT RUN ON A MACHINE YOU CARE ABOUT.
# Read the script first.

set -e
cd /tmp
mkdir -p disaster-sim
cd disaster-sim

# Symptoms we will install:
# 1) A user's $HOME suddenly shows "permission denied" on ~/.bashrc
# 2) The PATH variable is broken so most commands "don't exist"
# 3) A file in /etc has the wrong permission

sudo chmod 000 ~/.bashrc  2>/dev/null || true
echo 'export PATH=/tmp' >> ~/.bashrc.broken  # we'll source this manually
```

Then **source the broken environment** in a new terminal:

```bash
bash --rcfile ~/.bashrc.broken
```

## Symptoms you'll see

- `ls` doesn't work (`command not found`).
- `cd` works (it's a builtin).
- `cat ~/.bashrc` fails with permission denied.

## What to do

Diagnose and fix, using only commands you can find through:

- The shell's **builtins** (which work regardless of PATH): `cd`, `echo`, `pwd`, `type`, `read`, `set`, `unset`, `command`.
- **Absolute paths** to programs you remember: `/usr/bin/ls`, `/bin/sh`, `/usr/bin/cat`.

## Acceptance criteria

- [ ] You diagnose **PATH** as the cause of "command not found." Verify with `echo $PATH`.
- [ ] You restore a working PATH at least temporarily: `export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`.
- [ ] You diagnose `~/.bashrc` as unreadable (`/usr/bin/stat ~/.bashrc` shows `000`).
- [ ] You restore readability: `/usr/bin/chmod 644 ~/.bashrc`.
- [ ] You delete the bad file: `/usr/bin/rm ~/.bashrc.broken`.
- [ ] You write up the incident in `incident.md` with a timeline (when did I notice X, what did I try, what worked).

## Why this matters

Real production incidents look like this — except instead of `chmod 000`, someone deployed bad config; instead of a broken PATH, a service is in a crash loop. The skills are the same: keep calm, use absolute paths, read the error output, diagnose before fixing, document what happened.

## Submission

Commit `incident.md` to your portfolio under `c14-week-01/challenge-01/`.
