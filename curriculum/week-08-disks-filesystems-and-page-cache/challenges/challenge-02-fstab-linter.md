# Challenge 02 — Write an `/etc/fstab` linter

**Time:** 2-3 hours.
**Goal:** Write a script (Python or shell, your choice) that reads `/etc/fstab`, parses every line, and reports problems. The script should run clean on a properly-configured fstab and produce actionable warnings on a misconfigured one.

---

## Why this challenge

`/etc/fstab` is the file that locks people out of their own systems. The format is unforgiving and the consequences of an error are tedious to recover from. Most distributions ship a default fstab that is acceptable but not optimal: `relatime` is good but `noatime` is better for servers; `/tmp` as a regular ext4 mount is fine but `tmpfs,nodev,nosuid,noexec` is better; `/home` with `defaults` is fine but `defaults,nodev,nosuid` is harder for attackers.

A linter automates the review. A good linter catches the security and performance options a human review would flag, without firing on valid-but-uncommon configurations.

---

## Spec

Your linter reads `/etc/fstab` (or a path given as `--file`) and produces:

- **Errors** (red): the line will not work. Missing fields, unparseable device, mount point that does not exist (or is not a directory).
- **Warnings** (yellow): the line works but is suboptimal. Missing `noatime` on a data mount; `/tmp` mounted ext4 without `nodev,nosuid,noexec`; `pass` field non-zero on xfs or btrfs.
- **Info** (green): observations that are correct but worth noting. "This filesystem is mounted with `discard` — modern advice is to use `fstrim` on a timer."

The output should be greppable from a CI system: each line starts with `ERROR`, `WARN`, or `INFO`; the affected fstab line follows.

Exit code:

- `0` — all clean (no errors, no warnings).
- `1` — warnings only.
- `2` — at least one error.

---

## Rules to check

### Errors (exit 2)

- **Wrong field count.** A non-comment non-blank line has fewer than six fields or more than six.
- **Unknown filesystem type.** The type is not in the known-good list (`ext2`, `ext3`, `ext4`, `xfs`, `btrfs`, `vfat`, `ntfs`, `swap`, `tmpfs`, `proc`, `sysfs`, `devpts`, `cgroup`, `cgroup2`, `nfs`, `nfs4`, `cifs`, `auto`, `none`, `bind`, `overlay`, `fuse.*`).
- **Mount point that does not exist** (except for `none`, `swap`, and `/proc` etc.).
- **Mount point that exists but is not a directory.**
- **Conflicting options** (e.g. both `ro` and `rw`, both `noatime` and `strictatime`).

### Warnings (exit 1)

- **`pass` non-zero on xfs or btrfs.** xfs's `fsck` analog is `xfs_repair` and should not be run at boot; btrfs uses `scrub` online. Both should have `pass=0`.
- **Multiple `pass=1` lines.** Only the root filesystem should be `pass=1`.
- **Device given as `/dev/sdX`** rather than `UUID=` or `LABEL=`. Device names are not stable.
- **`/tmp` mounted from a regular FS** (ext4 etc.) without `nodev,nosuid,noexec`.
- **`/tmp` mounted from a regular FS without `noatime`.**
- **A data mount (anything outside `/`, `/boot`, `/usr`, `/var`) mounted without `noatime`** on ext4 or xfs.
- **`barrier=0` or `nobarrier` set.** Disabling write barriers is data-loss-on-power-fail unless you have a battery-backed cache.
- **`/boot/efi` not type `vfat`.** UEFI firmware reads only FAT.
- **swap line not type `swap`.**

### Info (always show)

- **`discard` mount option.** Note that modern advice is `fstrim` on a timer.
- **A `data=writeback` option on ext4.** Note that this trades safety for throughput.
- **`/home` mounted without `nodev,nosuid`.** Note as security observation.

---

## Output example

For a problematic fstab like:

```
# /etc/fstab
UUID=aaaa  /              ext4   defaults,relatime              0  1
/dev/sdb1  /data          ext4   defaults                       0  2
UUID=bbbb  /var/www       xfs    defaults                       0  2
tmpfs      /tmp           tmpfs  defaults                       0  0
UUID=cccc  /backup        ext4   defaults,nobarrier             0  2
```

Expected output:

```
WARN  line 3 (/data):    device specified as /dev/sdb1; prefer UUID=
WARN  line 3 (/data):    missing 'noatime' on data mount
WARN  line 4 (/var/www): pass=2 on xfs; should be 0 (xfs_repair is not for boot)
WARN  line 5 (/tmp):     missing 'nodev,nosuid,noexec' hardening on /tmp
WARN  line 6 (/backup):  'nobarrier' disables write barriers; data loss risk
INFO  line 2 (/):        using 'relatime'; 'noatime' is better for most servers

Summary: 5 warnings, 1 info, 0 errors. Exit code 1.
```

For a clean fstab, the output is just the summary line and exit 0.

---

## Implementation hints

- **Parse the line** by splitting on whitespace after stripping leading whitespace and the comment marker. Skip blank lines and lines starting with `#`.
- **Field 4 (options) is a comma-separated list**; parse with `field4.split(",")`.
- **Use Python's `pathlib`** for the mountpoint-existence check.
- **The "is this a data mount" heuristic** is "the mount point is not in the small list of system mounts": `/`, `/boot`, `/boot/efi`, `/usr`, `/var`, `/var/log`, `/var/cache`, `/srv`, `/opt`, `/home`, `/tmp`, `/proc`, `/sys`, `/run`, `/dev/shm`. A mount under `/data`, `/srv/web`, `/var/data` is a data mount.
- **`pass=1` count**: increment a counter; warn if it exceeds 1.
- **Make the rule list extensible.** A class hierarchy or a list of `(name, predicate, severity, message)` tuples lets you add rules without rewriting the engine.

---

## Bonus features (stretch)

- **`--fix` mode**: when run with `--fix`, rewrite `/etc/fstab` with the recommended changes (after backing up to `/etc/fstab.bak.TIMESTAMP`). This is dangerous; require `--confirm` to actually write.
- **`--json` output**: structured output for ingestion by a config-drift detector.
- **Cross-check `/etc/fstab` against `/proc/mounts`**: any line in `/etc/fstab` that does not appear in `/proc/mounts` is a mount that "should be mounted but is not." Worth a warning.
- **Cross-check UUIDs against `blkid`**: any `UUID=...` in fstab that does not resolve to a present device is a stale entry; a yellow flag.
- **Run as a systemd unit on boot** with `OnFailure=` pointing at a notification script. Get an email if a new fstab regression appears.

---

## Deliverables

A directory in your portfolio `c14-week-08/challenge-02/` containing:

- `fstab-lint.py` (or `.sh`) — the linter.
- `README.md` — how to install, how to run, what the output means.
- `test-fstab/` — at least three sample fstab files: one clean, one with warnings, one with errors.
- `Makefile` (optional but recommended) with `make test` that runs the linter against each sample and checks the exit code.

---

## Grading rubric (self-assessment)

| Aspect | 0 (missing) | 1 (basic) | 2 (good) | 3 (excellent) |
|--------|-------------|-----------|----------|---------------|
| Parses every well-formed fstab line | No | Some | All standard lines | Plus edge cases (escaped spaces, blank lines, comments mid-line) |
| Catches the errors in the spec | None | 1-2 | All | Plus useful errors not in spec |
| Catches the warnings in the spec | None | 1-3 | All | Plus useful warnings not in spec |
| Output is greppable | No | Yes | Yes, with structured prefix | Yes, with structured prefix + JSON mode |
| Exit code matches spec | No | Sometimes | Yes | Yes, plus documented in README |
| Tests included | No | One | Multiple | Plus CI integration (Make / pytest / shellcheck) |
| Type hints (if Python) | No | Partial | Full on functions | Full plus `mypy --strict` clean |

A score of 14 or above is graduation-level. A score of 10-13 is a working tool you can improve. Below 10, revisit.

---

## Further reading

- `man 5 fstab` — the fstab format.
- `man 8 mount` — every mount option.
- Arch Wiki — "fstab" — examples for every common case: <https://wiki.archlinux.org/title/Fstab>.
- Red Hat — "Filesystem mount options reference" — distro-flavoured but largely portable.

---

*This challenge is intentionally underspecified at the edges so you can make design decisions. Document your decisions in the README.*
