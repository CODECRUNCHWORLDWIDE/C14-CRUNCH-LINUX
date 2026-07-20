# Exercise 1 — The 50-command tour

**Goal:** Run every command from Lecture 1, at least once, in a real context. Capture the output. Notice what each one does.

**Estimated time:** 40 minutes.

## What to do

Open a terminal. Create a working directory:

```bash
mkdir -p ~/c14-w1/exercise-01
cd ~/c14-w1/exercise-01
```

Then work through the script below, **typing each command** (no copy-paste). After each one, type `<command> --help | head -5` to see its synopsis, or `man <command>` if you're curious.

```bash
# Navigation
pwd
ls
ls -la
ls -lh /etc
cd /tmp
pwd
cd -                  # back to where you were
ls ~

# Make something to look at
echo "hello" > greeting.txt
echo "world" >> greeting.txt
cat greeting.txt
wc -l greeting.txt
wc -w greeting.txt
file greeting.txt
stat greeting.txt

# Read it different ways
head -1 greeting.txt
tail -1 greeting.txt
less greeting.txt     # then press q

# Copy / rename / delete
cp greeting.txt copy.txt
mv copy.txt renamed.txt
ls
rm renamed.txt
ls

# Make directories
mkdir nested/path     # FAILS
mkdir -p nested/path  # succeeds
ls -R nested/

# Touch
touch a.txt b.txt c.txt
ls

# Find
find . -name "*.txt"
find . -type f
find . -size 0

# Grep
grep "hello" greeting.txt
grep -n "world" greeting.txt
grep -r "hello" .          # recursive

# System info
whoami
id
hostname
uname -a
uptime
date
df -h
du -sh .
free -h

# Processes
ps
ps aux | head
top -n 1 | head           # one snapshot of top, then exit
jobs

# Help
which ls
type ls
type cd
man ls | head -10
ls --help | head
apropos copy | head
```

## Acceptance criteria

- [ ] You ran every command above.
- [ ] You captured the output of each in `~/c14-w1/exercise-01/output.log` (use `script` or just redirect: `command >> output.log 2>&1`).
- [ ] For each of these commands, write a one-sentence "what I learned" line in `notes.md`: `find`, `grep -r`, `ps aux`, `df -h`, `type`.
- [ ] You ran `man <cmd>` for at least three commands that were new to you.

## Stretch

- Replace each `ls` above with `ls -la`. See what's different.
- Try every command with `--help`. Note which ones don't support it.
- Run `time ls -la /etc`. Note CPU vs wall time.

## Submission

Commit `output.log` and `notes.md` to your portfolio repo under `c14-week-01/exercise-01/`.
