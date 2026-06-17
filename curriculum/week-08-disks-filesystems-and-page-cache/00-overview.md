# Week 8 — Disks, filesystems, and the page cache

> *Last week you learned to **see** that the disk was busy. This week you learn what the disk **is** and why it is busy. A "disk" on Linux is a stack: a physical device underneath, a block device node in the middle, a partition table that says where the slices begin, optionally an LVM layer that pools the slices, then a filesystem on top, then a mount point in the directory tree, then the page cache between user space and all of it. Each layer has its own knobs and its own failure modes. The final week of C14 walks the stack top to bottom, names every layer, and ends with a 7-day capstone in which you run a real Linux server in the real world.*

Welcome to **Week 8 of C14 · Crunch Linux** — the final week of the track. Seven weeks behind: shell, pipes, permissions, scripting, services, ssh and firewalls, observability. You can now log in, navigate, write scripts, manage units, harden network access, and see when something is slow. This week we look at the substrate everything sits on: the **block layer**, the **filesystem**, the **page cache**. We end with a postmortem on a server you ran for a full week.

If Week 7 was "the disk is at 99 % `%util`", Week 8 is "the disk is at 99 % `%util` because ext4 is journalling each tiny write and `noatime,nodiratime,commit=60` would have batched the journal flushes — here is the `/etc/fstab` line." It is the bridge from **measuring** to **fixing**, and it is the last set of vocabulary you need before you can read a Linux engineer's incident postmortem and follow every sentence.

## Learning objectives

By the end of this week, you will be able to:

- **Distinguish block devices from character devices** and explain why this matters. Block devices (`/dev/sda`, `/dev/nvme0n1`, `/dev/vda`) deliver fixed-size, random-access blocks and are buffered by the page cache; character devices (`/dev/tty`, `/dev/random`, `/dev/null`) deliver an unbuffered byte stream. Read the major / minor numbers from `ls -l /dev/sda` and explain what each identifies. Reference: `mknod(1)`, `Documentation/admin-guide/devices.txt`.
- **Read a partition table** with `lsblk -f`, `fdisk -l`, and `parted -l`. Know the difference between **MBR** (the legacy 32-bit table, 2 TiB ceiling, 4 primary partitions) and **GPT** (the modern table, 128 entries by default, no 2 TiB ceiling, redundant headers, UUIDs everywhere). Recognise a typical UEFI layout: ESP, root, swap.
- **Choose a filesystem with reasons**. **ext4** — the conservative default, journalling, mature; you should choose it when in doubt. **xfs** — strong for large files and parallel writes; the default on RHEL since 7. **btrfs** — copy-on-write, snapshots, send/receive; the default on Fedora Workstation; the right choice when snapshots or subvolumes matter. Know the trade-offs well enough to defend the choice in a code review.
- **Mount filesystems by hand and at boot.** Read `man 8 mount` end to end. Use `mount /dev/sdb1 /mnt/data` and `umount /mnt/data`. Write `/etc/fstab` lines correctly, with the six fields and the right options. Know what `noatime`, `nodiratime`, `relatime`, `discard`, `nodev`, `nosuid`, `noexec`, `ro`, `commit=N` actually change. Reference: `fstab(5)`, `mount(8)`.
- **Use LVM at a beginner level.** Create a **physical volume** with `pvcreate`, a **volume group** with `vgcreate`, a **logical volume** with `lvcreate`, then format and mount. Display with `pvs`, `vgs`, `lvs`. Extend an LV with `lvextend -r`. Know **why** people use LVM: online resize, snapshot for backup, span multiple physical disks. Reference: `lvm(8)`.
- **Read the page cache.** Know that on Linux every file read passes through the **page cache** (an in-kernel cache of file pages, sized by the kernel automatically, displayed as `Cached` in `/proc/meminfo` and as `buff/cache` in `free`). Demonstrate the speed difference between a cold read and a warm read with `dd` and `vmstat`. Use `echo 3 > /proc/sys/vm/drop_caches` (as root) to clear the cache between benchmarks. Reference: `Documentation/admin-guide/mm/concepts.rst`.
- **Read dirty pages and writeback.** Know that **dirty pages** are file pages modified in cache but not yet written to disk. The kernel flushes them lazily via the `kworker/u*:*` writeback threads. The thresholds are `vm.dirty_ratio` (the percentage of RAM that may be dirty before user processes are forced to write), `vm.dirty_background_ratio` (the percentage at which background flush begins), and `vm.dirty_expire_centisecs` (the age at which a dirty page is forcibly flushed). Adjust with `sysctl`. Reference: `Documentation/admin-guide/sysctl/vm.rst`.
- **Run a basic disk benchmark with `fio`.** Run `fio` (free, in every distro's repo) with sane job files for random-read 4k, sequential-write 1m, mixed workloads. Read the output: IOPS, bandwidth, latency p50/p99. Compare a cold-cache run to a warm-cache run and explain the difference. Reference: `fio(1)`, <https://fio.readthedocs.io/>.
- **Identify what `io_uring` is at a beginner-aware level.** Know that **`io_uring`** is the modern Linux asynchronous-IO interface introduced in kernel **5.1** (May 2019). It replaces the older `aio` (POSIX `libaio`) interface, supports a much wider set of syscalls, and is the substrate for high-performance servers since 2020. You do **not** need to write an `io_uring` program this week; you need to recognise the name in a job description, in a perf flame graph, and in a kernel-version-requirement note. Reference: <https://kernel.dk/io_uring.pdf> (Jens Axboe's design paper).
- **Apply filesystem-maintenance rules of thumb.** Know the cardinal rule: **never run `fsck` on a mounted filesystem**. You can lose all data. `fsck` is for unmounted filesystems or for the root filesystem at boot (when systemd hands the FS over to `systemd-fsck` before mounting it `rw`). Schedule periodic checks via the filesystem's own facilities: `tune2fs -c -i` for ext4, `xfs_repair` for xfs (and never on a mounted FS), btrfs `scrub` for btrfs (which **does** run online). Reference: `fsck(8)`, `tune2fs(8)`, `xfs_repair(8)`, `btrfs-scrub(8)`.
- **Run a real server for seven days.** Provision a small VM (free tier or local). Install nginx (or a tiny Flask app) and serve real content. Configure logs, monitoring, fail2ban, unattended upgrades. Watch the disk, the cache, and the journal for a week. Write a postmortem.

## Prerequisites

- **Weeks 1-7 of C14** completed. You can shell, script, manage units, harden SSH, and apply the USE method. Week 7 is strictly required: the mini-project is a 7-day operational exercise and you need the observability vocabulary to write the postmortem.
- A working Ubuntu 24.04 LTS or Fedora 41 environment. The exercises run on any modern Linux; the command output and `fstab` formats match Ubuntu 24.04 by default. For the mini-project you need a Linux box you have root on, with a public IP — see the mini-project for the free-tier provider menu.
- Packages: `util-linux` (provides `lsblk`, `fdisk`, `mount`, preinstalled), `parted`, `lvm2`, `fio`, `e2fsprogs` (ext4 tools, preinstalled), `xfsprogs` (xfs tools), `btrfs-progs` (btrfs tools), `smartmontools` (the `smartctl` disk-health tool), `fail2ban` (mini-project), `unattended-upgrades` (mini-project), `nginx` or `python3-flask` (mini-project). On Ubuntu: `sudo apt install parted lvm2 fio xfsprogs btrfs-progs smartmontools fail2ban unattended-upgrades nginx`. On Fedora: `sudo dnf install parted lvm2 fio xfsprogs btrfs-progs smartmontools fail2ban dnf-automatic nginx`.
- Python 3.10 or newer for the challenges. Standard library only.
- Patience to **measure twice and cut once**. Filesystem and disk operations are durable in a way that other Linux work is not: a partition table you wrote five minutes ago lives on the device until you overwrite it; an `fsck` on a mounted filesystem can corrupt every file. Read the man page before you run the command.

## Topics covered

- **The block device stack.** Hardware (NVMe, SATA, virtual disk) → block-device driver → block device node (`/dev/sda`, `/dev/nvme0n1`) → partition (`/dev/sda1`) → optional LVM (`/dev/mapper/vg-lv`) → optional encryption (`/dev/mapper/crypt-name`) → filesystem (`mkfs.ext4`) → mount point (`/mnt/data`) → directory tree (the user's `cd /mnt/data`). We walk the whole stack on a real device.
- **Block versus character devices.** The two kinds of Unix device. Block devices deliver fixed-size random-access pages and are buffered; character devices deliver byte streams. The `b` versus `c` column in `ls -l /dev/`. Major and minor numbers. The `mknod(2)` syscall and why almost nobody calls it directly any more (udev populates `/dev/` automatically).
- **Partitions and partition tables.** **MBR** (legacy, 4 primary partitions, 2 TiB ceiling, 32-bit LBA). **GPT** (modern, 128 entries default, 64-bit LBA, redundant primary/backup headers, every partition has a UUID). The boot-loader implications: BIOS systems read MBR; UEFI systems read GPT and look for the ESP (EFI System Partition). Tools: `fdisk` (BSD-style, supports MBR and GPT), `parted` (scriptable, GNU), `gdisk` (GPT-specialized), `sfdisk` (script-driven `fdisk`). The lecture walks one partitioning end to end on a virtual disk.
- **`lsblk`** — the block-device tree. `lsblk` shows physical → partition → LVM → mount in one ASCII tree. `lsblk -f` adds filesystem type and UUID. `lsblk -o NAME,SIZE,TYPE,MOUNTPOINTS,UUID` lets you pick columns. The most-used disk-discovery command on Linux.
- **`fdisk`, `parted`, `sfdisk`** — partition manipulation. `fdisk -l` to list. `parted /dev/sdb print` for the same. `sfdisk --dump /dev/sdb > backup.txt` saves the layout; `sfdisk /dev/sdb < backup.txt` restores. Read `man 8 fdisk`, `man 8 parted`.
- **Filesystem choice.** **ext4** is the conservative default: journalled, robust, mature, present on every Linux distribution. **xfs** is faster than ext4 for parallel large-file workloads; the default on RHEL since 7. **btrfs** is copy-on-write with native snapshots, subvolumes, and `send/receive`; the default on Fedora Workstation since 33; not yet the default on Debian or RHEL. We cover **what each one is good at**, **what each one is bad at**, and **when to pick which**.
- **`mkfs` and friends.** `mkfs.ext4 /dev/sdb1`, `mkfs.xfs /dev/sdb1`, `mkfs.btrfs /dev/sdb1`. The options that matter: `-L LABEL` to set a label, `-U UUID` to set a UUID (rare), `-T DESC` to optimise for typical file size (ext4), `-d agcount=N` for xfs to set the number of allocation groups, `-d single` versus `-d raid1` for btrfs to set the data profile. The defaults are sane; departing from them is intermediate-level.
- **Mounting.** `mount /dev/sdb1 /mnt/data` to mount; `umount /mnt/data` to unmount. The `man 8 mount` man page has every option. The options that show up in real `/etc/fstab` lines: `defaults` (rw, suid, dev, exec, auto, nouser, async), `noatime` and `nodiratime` (do not record access times — the single most impactful performance option on most workloads), `relatime` (the modern default — record `atime` only if `mtime` or `ctime` is newer or `atime` is older than a day), `discard` (issue TRIM to SSD on file delete; controversial; usually preferable to a weekly `fstrim`), `nodev`, `nosuid`, `noexec` (security hardening for mount points that should never run code), `ro` (read-only), `errors=remount-ro` (ext4 — remount read-only on filesystem error rather than crashing).
- **`/etc/fstab`.** The six fields: device, mount point, type, options, dump, pass. The device is best given as a `UUID=` to survive device-name changes. The pass column controls `fsck` order at boot (0 means never; 1 for the root filesystem; 2 for everything else). The dump column is almost always 0; the `dump` tool that used it is essentially extinct.
- **LVM essentials.** **Physical volume (PV)** — a block device made available to LVM (`pvcreate /dev/sdb1`). **Volume group (VG)** — a pool of PVs (`vgcreate data /dev/sdb1 /dev/sdc1`). **Logical volume (LV)** — a slice of the VG that looks like a block device (`lvcreate -L 50G -n web data`; appears as `/dev/data/web` and `/dev/mapper/data-web`). The four display commands: `pvs`, `vgs`, `lvs` (terse one-line summaries), and `pvdisplay` / `vgdisplay` / `lvdisplay` (verbose). The two operations you will actually do: extend an LV (`lvextend -L +20G -r /dev/data/web` — the `-r` resizes the filesystem too) and snapshot for backup (`lvcreate -L 10G -s -n web-snap /dev/data/web`).
- **The page cache.** Every file read on Linux first checks the page cache. A cache hit returns the data without touching the device; a cache miss reads from disk and fills the cache. The cache size is automatic: it grows to use all otherwise-free memory and shrinks under memory pressure. The size shows in `/proc/meminfo` as `Cached:` (file pages) and `Buffers:` (block-device metadata pages). The "Linux ate my RAM" panic — high `used` and low `free` — is almost always the cache doing its job: the `available` column in `free` reports the usable-by-other-processes total.
- **`drop_caches`.** `echo 3 > /proc/sys/vm/drop_caches` (as root) drops all clean cached pages and dentries/inodes. Use it between benchmark runs to compare cold-cache numbers. Do not use it in production: it is a destructive operation against the cache and the cache will refill on the next access.
- **Dirty pages and writeback.** When a process writes to a file, the kernel writes into the page cache and marks the page **dirty** — meaning the in-memory copy is newer than the on-disk copy. The dirty page is flushed by the kernel's writeback threads (`kworker/u*:*` in `ps`) at one of three triggers: (1) `vm.dirty_background_ratio` percent of RAM is dirty, (2) the page is older than `vm.dirty_expire_centisecs`, (3) `fsync` or `sync` is called. The "fast write that then stalls" pattern — `dd` reports a fast 200 MB/s for the first 5 seconds then drops to 30 MB/s — is the writeback throttling at `vm.dirty_ratio`.
- **`vm.dirty_*` sysctls.** `vm.dirty_ratio` (default 20, often dropped to 10 on servers with fast disks), `vm.dirty_background_ratio` (default 10), `vm.dirty_expire_centisecs` (default 3000, i.e. 30 s), `vm.dirty_writeback_centisecs` (default 500, i.e. 5 s — how often `pdflush`/writeback wakes up). The kernel docs at `Documentation/admin-guide/sysctl/vm.rst` are the authoritative reference.
- **`fio`** — the canonical disk-benchmark tool. Free, open-source, in every distro's repo. Job files describe a workload (random reads, sequential writes, mixed); `fio` runs them with configurable depth, IO size, duration. The output is IOPS, bandwidth, latency percentiles. We learn the four canonical jobs: 4k random read, 4k random write, 1m sequential read, 1m sequential write.
- **`io_uring` at a beginner-aware level.** The Linux 5.1+ asynchronous-IO interface, designed by Jens Axboe (who also wrote `fio`). Submission queue + completion queue, both shared with the kernel via mmap; the kernel polls the SQ and posts results to the CQ. We do **not** write an `io_uring` program this week; we explain what it is, mention it is the substrate of every modern high-performance Linux server, and point at the design paper for the curious. The mention is **deliberate** — students will see `io_uring` in job descriptions, in `perf` output, and in postmortems, and they need to recognise the name.
- **Filesystem maintenance.** `fsck` only runs on unmounted filesystems (or at boot, before the root FS is mounted `rw`). On ext4: `tune2fs -l /dev/sdb1` shows the last-checked time; `tune2fs -c 30 -i 6m /dev/sdb1` schedules a periodic check; `fsck.ext4 -y /dev/sdb1` runs one. On xfs: `xfs_repair` (also requires unmounted). On btrfs: `btrfs scrub start /` (runs **online** — btrfs's scrub is one of its features). The single most dangerous Linux command in this week is `fsck.ext4 /dev/sda1` when `/dev/sda1` is mounted; we cover the rule explicitly.
- **SMART disk health.** `smartctl -a /dev/sda` shows the SMART attributes the disk firmware tracks. `smartctl -t short /dev/sda` schedules a short self-test; `smartctl -l selftest /dev/sda` shows the result. The attribute that matters most: `Reallocated_Sector_Ct` — bad sectors the firmware has remapped; non-zero is a yellow flag, growing is a red flag.
- **Capstone: run a real server for seven days.** The integration project. Provision a VM. Configure logging, monitoring, fail2ban, unattended upgrades. Serve a real service. Watch it. Write the postmortem.

## Weekly schedule

The schedule below adds up to approximately **40 hours** — slightly more than a normal week, because the capstone runs in the background for a calendar week and the active work is front-loaded. Treat it as a target, not a contract.

| Day       | Focus                                                  | Lectures | Exercises | Challenges | Quiz/Read | Homework | Mini-Project | Self-Study | Daily Total |
|-----------|--------------------------------------------------------|---------:|----------:|-----------:|----------:|---------:|-------------:|-----------:|------------:|
| Monday    | The block stack; partitions and partition tables. Lecture 1. Provision the capstone VM. |    3h    |    1h     |     0h     |    0.5h   |   1h     |     1h       |    0h      |     6.5h    |
| Tuesday   | Filesystem choice and mounting. Lecture 2. Capstone Day 2 (nginx install, TLS). |    2.5h  |    2h     |     0h     |    0.5h   |   1h     |     1h       |    0h      |     7h      |
| Wednesday | LVM, page cache, writeback. Lecture 3. Capstone Day 3 (logging, fail2ban). |    2.5h  |    1h     |     1h     |    0.5h   |   1h     |     1.5h     |    0h      |     7.5h    |
| Thursday  | `fio` benchmarks; `io_uring` mention. Capstone Day 4 (monitoring, unattended upgrades). |    0h    |    2h     |     2h     |    0.5h   |   1h     |     1.5h     |    0h      |     7h      |
| Friday    | Filesystem maintenance; SMART. Polish homework. Capstone Day 5 (watch + tune). |    0h    |    1h     |     1h     |    0.5h   |   2h     |     1h       |    0h      |     5.5h    |
| Saturday  | Capstone Day 6 — induce a small load, watch the reaction. |    0h    |    0h     |     0h     |    0h     |   0h     |     3h       |    0.5h    |     3.5h    |
| Sunday    | Capstone Day 7 — postmortem write-up. Final quiz. Reflection. |    0h    |    0h     |     0h     |    1h     |   0h     |     2h       |    0h      |     3h      |
| **Total** |                                                        | **8h**   | **7h**    | **4h**     | **3.5h**  | **6h**   | **11h**      | **0.5h**   | **40h**     |

## How to navigate this week

| File | What's inside |
|------|---------------|
| [README.md](./00-overview.md) | This overview |
| [resources.md](./01-resources.md) | Kernel admin-guide docs, man pages by section, the `fio` and `io_uring` references |
| [lecture-notes/01-block-devices-partitions-and-the-mount-stack.md](./02-lecture-notes/01-block-devices-partitions-and-the-mount-stack.md) | The block device stack, partition tables, `lsblk`, `fdisk`, `parted` |
| [lecture-notes/02-filesystems-and-mount-options.md](./02-lecture-notes/02-filesystems-and-mount-options.md) | ext4 vs xfs vs btrfs, `mkfs.*`, `/etc/fstab`, the options that matter |
| [lecture-notes/03-lvm-page-cache-writeback-and-fio.md](./02-lecture-notes/03-lvm-page-cache-writeback-and-fio.md) | LVM essentials, the page cache, dirty pages, `vm.dirty_*`, `fio`, `io_uring` mention |
| [exercises/exercise-01-partition-format-mount.md](./03-exercises/exercise-01-partition-format-mount.md) | Take a fresh disk (or loopback file). Partition with `parted`. `mkfs.ext4`. Mount. Add to `/etc/fstab`. Reboot-safe. |
| [exercises/exercise-02-page-cache-cold-vs-warm.md](./03-exercises/exercise-02-page-cache-cold-vs-warm.md) | Demonstrate the page cache with `dd` and `drop_caches`. Measure cold and warm reads. Explain. |
| [exercises/exercise-03-lvm-create-extend-snapshot.md](./03-exercises/exercise-03-lvm-create-extend-snapshot.md) | Three-PV VG, an LV, extend it, snapshot it, restore from the snapshot. |
| [exercises/exercise-04-fio-four-canonical-jobs.md](./03-exercises/exercise-04-fio-four-canonical-jobs.md) | Run `fio` with 4k-randread, 4k-randwrite, 1m-seqread, 1m-seqwrite. Read the output. Compare cold and warm cache. |
| [exercises/setup-loopback-disks.sh](./03-exercises/setup-loopback-disks.sh) | Helper: create three 1 GiB loopback files for the LVM exercise (no real disks needed) |
| [exercises/teardown-loopback-disks.sh](./03-exercises/teardown-loopback-disks.sh) | Helper: tear down the loopbacks cleanly |
| [exercises/SOLUTIONS.md](./03-exercises/SOLUTIONS.md) | Step-by-step solutions to all four exercises |
| [challenges/challenge-01-cache-aware-cp.py](./04-challenges/challenge-01-cache-aware-cp.py) | A type-hinted Python `cp` clone that uses `posix_fadvise` to tell the kernel not to cache the source — useful for one-shot copies of huge files |
| [challenges/challenge-02-fstab-linter.md](./04-challenges/challenge-02-fstab-linter.md) | Write a script that reads `/etc/fstab`, validates every line, flags missing `nodev,nosuid,noexec` on /tmp, missing `noatime` on data mounts, etc. |
| [quiz.md](./05-quiz.md) | 10 final-exam-style questions covering the whole week |
| [homework.md](./06-homework.md) | Six practice problems plus rubric (~6 hours) |
| [mini-project/README.md](./07-mini-project/00-overview.md) | The C14 **track capstone** — run a real Linux server for 7 days; write a postmortem |

## A note on which kernel and which tools

Linux storage is more conservative than Linux observability: the `/etc/fstab` format has not changed since 1985, `ext4` has been stable since 2008, GPT has been the partition default since 2010. The version-sensitive parts are:

- **Kernel 6.8** (Ubuntu 24.04 LTS) and **kernel 6.11** (Fedora 41). Older kernels (5.1+) have `io_uring`; 4.x kernels do not. Everything else in this week works back to kernel 3.x.
- **`util-linux` 2.39** (Ubuntu) / **2.40** (Fedora) — provides `lsblk`, `fdisk`, `mount`, `umount`, `wipefs`. The `lsblk -o MOUNTPOINTS` (plural) form is `util-linux` 2.37+; older shows `MOUNTPOINT` (singular).
- **`e2fsprogs` 1.47** (both) — ext4 tools: `mkfs.ext4`, `e2fsck`, `tune2fs`, `resize2fs`.
- **`xfsprogs` 6.6** (Ubuntu) / **6.10** (Fedora) — xfs tools: `mkfs.xfs`, `xfs_repair`, `xfs_growfs`.
- **`btrfs-progs` 6.6** (both) — btrfs tools.
- **`lvm2` 2.03.x** (both) — LVM tools: `pvcreate`, `vgcreate`, `lvcreate`, `lvextend`.
- **`fio` 3.36** (Ubuntu) / **3.37** (Fedora) — the IO benchmark.
- **`parted` 3.6** (both), **`smartmontools` 7.4** (both).

```bash
# Versions
uname -r                       # 6.8.0-x or 6.11.x
lsblk -V | head -1             # lsblk from util-linux 2.39.x
mkfs.ext4 -V 2>&1 | head -1    # mke2fs 1.47.x
mkfs.xfs -V | head -1          # mkfs.xfs version 6.6.x
btrfs --version | head -1      # btrfs-progs v6.6
lvm version | head -2          # LVM version: 2.03.x
fio --version                  # fio-3.36
parted --version | head -1     # parted 3.6
```

If you are on macOS, install a Linux VM. Most of this week's tooling does not exist on macOS (`mkfs.ext4`, `lvm`, `fio` all fail or report unrelated output); UTM with Ubuntu 24.04 is the smallest path. WSL2 works for most exercises but the **block layer is virtualised** and you will not be able to partition `/dev/sda` — use loopback files (the `setup-loopback-disks.sh` helper) on WSL2.

## Track wrap-up

> **You have reached the last week of C14 · Crunch Linux.** Eight weeks ago you opened your first shell and learned what `pwd` meant. You now know what a block device is, what a filesystem is, what a service is, what an `iptables` rule is, what a process state is, what `/proc/<pid>/io` contains, and why `fsck` on a mounted filesystem is forbidden.
>
> **What you can now do that you could not eight weeks ago:**
>
> - **Week 1** — Move around a Linux filesystem. Read pathnames as sentences. Use `cd`, `ls`, `cp`, `mv`, `rm`, `find`. Know the difference between absolute and relative paths.
> - **Week 2** — Compose pipelines. `grep`, `sort`, `uniq`, `cut`, `awk`, `sed`. Understand stdin, stdout, stderr, redirection, the exit-status convention.
> - **Week 3** — Reason about permissions. `ls -l`'s rwx columns. `chmod`, `chown`. Owners, groups, others. SUID, SGID, sticky. The principle of least privilege.
> - **Week 4** — Write defensible shell scripts. `set -euo pipefail`. Quoting hygiene. Functions, locals, `getopts`. POSIX versus bash. Style and testing.
> - **Week 5** — Write systemd units. Manage services with `systemctl`. Read journals with `journalctl`. Timers as cron replacements. Dependency ordering.
> - **Week 6** — Configure SSH and firewalls. Key-only auth, `~/.ssh/config`, `~/.ssh/authorized_keys`. `nftables` and `ufw`. Tunnels and jump hosts.
> - **Week 7** — Diagnose performance problems. The USE method. `htop`, `iostat`, `vmstat`, `free`, `ss`, `strace`. Read `/proc`. Measure before changing.
> - **Week 8** — Manage storage. Partitions, filesystems, LVM, the page cache, dirty pages. Benchmark with `fio`. Run a real server for a week and write the postmortem.
>
> **The graduation criterion is the mini-project.** A 7-day capstone running a real Linux server you control, with logs you read, alerts you receive, attacks you fend off (you will be probed; every public IPv4 address is portscanned within minutes), and a postmortem you write. If you can produce that postmortem, you are a junior Linux engineer in the operational sense — somebody who can be handed an unfamiliar box and be productive on it in an afternoon.
>
> **Where to go next:**
>
> - **C7 · Crunch Wire** for networking depth — TCP, TLS, DNS, BGP, the protocol stack from the wire up.
> - **C16 · Crunch Containers** for the orchestration layer — Docker, Kubernetes, namespaces, cgroups (the Linux primitives underneath containers, which is why you take it after C14).
> - **C18 · Crunch GCP**, **C19 · Crunch AWS** for cloud operations at scale.
> - **C23 · Crunch Agents** for the LLM-driven operations layer that is replacing on-call rotations in 2026.
> - Brendan Gregg's *Systems Performance* (2nd ed.) cover to cover — you have earned the depth.
> - The Linux Foundation's free *Introduction to Linux* (LFS101) — a complementary survey that fills in subjects we did not have time for (X11/Wayland, package management depth, container-specific subjects).
>
> The Linux ecosystem is large and old, and you have learned enough of it to read documentation on the rest. The discipline that distinguishes a Linux engineer from a Linux user is not raw command knowledge but **habits**: **read the man page**, **measure before changing**, **never `fsck` a mounted filesystem**, **the box that has been up for 800 days deserves the same care as the box that came up an hour ago**. Carry the habits forward.

## Bash Yellow caution

This week contains commands that can:

- **Destroy a partition table.** `parted /dev/sda mklabel gpt` on the wrong device replaces the partition table and renders every partition unreadable. Confirm with `lsblk` before every partition command. Practise on a loopback file (`setup-loopback-disks.sh`) before touching real devices.
- **Format the wrong device.** `mkfs.ext4 /dev/sda1` on a mounted, in-use partition is unrecoverable. Confirm the device with `blkid` and `mount | grep sdX` before every `mkfs.*` invocation. Read the line twice; the difference between `/dev/sda1` (your root) and `/dev/sdb1` (the new disk) is one character.
- **Overwrite your `/etc/fstab`.** Edit with a copy: `sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)` before any edit. Always `sudo mount -a` after editing to test before reboot. A broken `/etc/fstab` can prevent the system from booting; the recovery is single-user mode.
- **Lock up a workstation.** Filesystem stress, dirty-page generators, and `fio` with `--rw=randwrite --size=10G` can fill the page cache, force writeback, saturate the disk for minutes, and stall every other process on the box. Run in a VM or set `--size` modestly.
- **Wear an SSD.** Repeated `fio --rw=randwrite --size=10G` writes 10 GB per run. SSDs have finite write endurance; do this two or three times for the exercise and then `rm` the test files. Do not loop it.
- **Run `fsck` on a mounted filesystem.** The single sentence to remember from this week: **never run `fsck` on a mounted filesystem**. The kernel and `fsck` will both write to the filesystem from different cached views and the result is corruption. `fsck` runs on unmounted devices; at boot, before mount; or, for btrfs, via `btrfs scrub` which is explicitly online-safe.
- **Drop the cache in production.** `echo 3 > /proc/sys/vm/drop_caches` empties the page cache, the slab caches, and dentries. The cache refills on the next access, but every next access is a cold miss. Use only in benchmarks and never on production hosts.

Every lecture and exercise that runs destructive code says so on the line above, uses a scratch directory, a loopback file, or a VM, and shows the cleanup command. The line is: **read the device path twice and the man page once before you run the command**.

## Up next

There is no "up next." This is the final week. Open the mini-project, provision the VM, and run a server for a week. The track is complete when the postmortem is written.

---

*If you find errors, please open an issue or PR.*
