# Week 8 — Resources

Free, public, no signup unless noted. This is the **final week** of C14 — the references below are the ones you will keep on your shelf for a career. Bookmark the kernel admin-guide URL and `man7.org`; you will revisit both for years.

## Required reading

- **Linux kernel — `Documentation/admin-guide/sysctl/vm.rst`** — the authoritative reference for every memory and writeback knob: `vm.dirty_ratio`, `vm.dirty_background_ratio`, `vm.dirty_expire_centisecs`, `vm.swappiness`, `vm.overcommit_memory`. Dense. The only place these are documented officially:
  <https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html>
- **Linux kernel — `Documentation/admin-guide/mm/concepts.rst`** — the kernel's own one-page primer on the memory subsystem. Reads like a textbook chapter; defines page, folio, page cache, anonymous memory:
  <https://www.kernel.org/doc/html/latest/admin-guide/mm/concepts.html>
- **Linux kernel — `Documentation/filesystems/ext4.rst`** — the ext4 design overview. The "Mount options" section is the canonical reference for every `data=`, `journal_async_commit`, `commit=N` option:
  <https://www.kernel.org/doc/html/latest/filesystems/ext4/index.html>
- **Linux kernel — `Documentation/filesystems/xfs.rst`** — the xfs design overview. Less prescriptive than the ext4 docs because xfs is documented in detail in the SGI papers below:
  <https://www.kernel.org/doc/html/latest/filesystems/xfs/index.html>
- **Linux kernel — `Documentation/filesystems/btrfs.rst`** — the btrfs design overview. Worth reading just for the subvolume model:
  <https://www.kernel.org/doc/html/latest/filesystems/btrfs.html>
- **`man 8 mount`** — every mount option, sorted by filesystem. The single most useful man page in storage:
  <https://man7.org/linux/man-pages/man8/mount.8.html>
- **`man 5 fstab`** — the `/etc/fstab` format. Six fields. Read end to end:
  <https://man7.org/linux/man-pages/man5/fstab.5.html>
- **`man 8 lsblk`** — the block-device tree tool. Every flag. The `-o` column list is the value:
  <https://man7.org/linux/man-pages/man8/lsblk.8.html>
- **`man 8 fdisk`** — the partition manipulator. Read the "DEVICES" and "COMMANDS" sections:
  <https://man7.org/linux/man-pages/man8/fdisk.8.html>
- **`man 8 parted`** — the scriptable partition manipulator. `mklabel`, `mkpart`, `print`, `rm`, `resizepart`:
  <https://man7.org/linux/man-pages/man8/parted.8.html>
- **`man 8 lvm`** — the LVM umbrella man page; from here you can reach `pvcreate(8)`, `vgcreate(8)`, `lvcreate(8)`, `lvextend(8)`, `lvconvert(8)`:
  <https://man7.org/linux/man-pages/man8/lvm.8.html>
- **`man 1 fio`** — the IO benchmark. Long man page, exhaustive. The "EXAMPLES" section at the bottom is high-value:
  <https://man7.org/linux/man-pages/man1/fio.1.html>
- **`man 8 fsck`** — the filesystem-check umbrella. Read alongside `fsck.ext4(8)`, `xfs_repair(8)`, `btrfs-check(8)`:
  <https://man7.org/linux/man-pages/man8/fsck.8.html>
- **`man 5 proc`** — the procfs man page (separate from the kernel admin-guide; more terse, example-driven). The `/proc/meminfo` and `/proc/diskstats` sections in particular:
  <https://man7.org/linux/man-pages/man5/proc.5.html>
- **Jens Axboe — "Efficient IO with io_uring"** — the design paper from the author of `io_uring` (and `fio`). 12 pages, 2019. Read once; come back when you need it. Authoritative:
  <https://kernel.dk/io_uring.pdf>

## Books

- **Robert Love — *Linux System Programming* (O'Reilly, 2nd ed., 2013)** — the syscall textbook from a kernel maintainer. Chapter 3 (Buffered IO) and Chapter 4 (Advanced File IO) cover the page cache, `fsync` semantics, `posix_fadvise`, `readahead`, and `O_DIRECT` in detail. The chapter on signals is also one of the clearest explanations in print.
- **Daniel P. Bovet, Marco Cesati — *Understanding the Linux Kernel* (O'Reilly, 3rd ed., 2005)** — old (covers kernel 2.6) but still the clearest single explanation of how the page cache is implemented, how the VFS dispatches calls to filesystem-specific code, how block devices map to gendisks. Chapter 14 (Block Device Drivers), Chapter 15 (The Page Cache), Chapter 18 (The Ext2 and Ext3 Filesystems) are the relevant ones.
- **Brendan Gregg — *Systems Performance: Enterprise and the Cloud* (Pearson, 2nd ed., 2020)** — already required for Week 7. Chapter 8 (File Systems), Chapter 9 (Disks), and Chapter 10 (Network, secondary here) are the relevant ones for Week 8. Sample chapters: <https://www.brendangregg.com/systems-performance-2nd-edition-book.html>
- **W. Richard Stevens — *Advanced Programming in the UNIX Environment* (3rd ed., Addison-Wesley, 2013)** — the syscall textbook. Chapter 3 (File I/O), Chapter 4 (Files and Directories), Chapter 14 (Advanced I/O) are the chapters touching this week's material from the C-programmer view.
- **Marshall Kirk McKusick et al. — *The Design and Implementation of the FreeBSD Operating System* (2nd ed., 2014)** — FreeBSD's filesystem layer is a different design from Linux's but the chapters on the buffer cache and on UFS are the clearest explanation of how a UNIX filesystem works structurally. UFS is similar enough to ext4 that the conceptual transfer is direct.
- **The XFS papers** — Adam Sweeney et al., "Scalability in the XFS File System" (USENIX 1996); Dave Chinner, "xfs: There and Back ... and There Again" (LSF/MM 2015). Both freely available. The 1996 paper is one of the cleanest filesystem-design papers ever written:
  <https://www.usenix.org/legacy/publications/library/proceedings/sd96/sweeney.html>
- **Avi Miller — *LVM HOWTO*** — the official Linux Documentation Project guide. Old (2006) but the model has not changed. Worth reading once to understand the layer-by-layer mental model:
  <https://tldp.org/HOWTO/LVM-HOWTO/>

## Cheat sheets

- **Arch Wiki — "File systems"** — pragmatic distro-agnostic notes on every supported FS. The recommended-defaults sections are the value:
  <https://wiki.archlinux.org/title/File_systems>
- **Arch Wiki — "fstab"** — the same for `/etc/fstab`. Examples for every common case:
  <https://wiki.archlinux.org/title/Fstab>
- **Arch Wiki — "LVM"** — the same for LVM. Walks the full create-extend-snapshot cycle:
  <https://wiki.archlinux.org/title/LVM>
- **Arch Wiki — "Solid state drive"** — the canonical reference for SSD tuning under Linux: TRIM/discard, alignment, scheduler choice. Distro-agnostic, factually precise:
  <https://wiki.archlinux.org/title/Solid_state_drive>
- **Red Hat — "Managing file systems"** — RHEL's own documentation on filesystems, mount options, LVM, and stratis. RHEL-flavoured but largely portable:
  <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/managing_file_systems/index>
- **`fio` "HOWTO" file in the source tree** — the canonical `fio` documentation, distributed with the source and online:
  <https://fio.readthedocs.io/en/latest/fio_doc.html>

## Tools and websites

- **`util-linux`** — provides `lsblk`, `fdisk`, `mount`, `umount`, `wipefs`, `blkid`, `findmnt`, `losetup`. Preinstalled on every Linux distribution. <https://github.com/util-linux/util-linux>
- **`e2fsprogs`** — ext2/3/4 tools: `mkfs.ext4`, `e2fsck`, `tune2fs`, `resize2fs`, `debugfs`. Preinstalled on Debian/Ubuntu/Fedora. <https://e2fsprogs.sourceforge.net/>
- **`xfsprogs`** — xfs tools: `mkfs.xfs`, `xfs_repair`, `xfs_growfs`, `xfs_info`, `xfs_db`. Install: `sudo apt install xfsprogs` / `sudo dnf install xfsprogs`. <https://xfs.wiki.kernel.org/>
- **`btrfs-progs`** — btrfs tools: `mkfs.btrfs`, `btrfs` (the umbrella), `btrfs-check`, `btrfsck`. Install: `sudo apt install btrfs-progs` / `sudo dnf install btrfs-progs`. <https://btrfs.readthedocs.io/>
- **`lvm2`** — `pvcreate`, `vgcreate`, `lvcreate`, `lvextend`, `lvconvert`, `pvs`, `vgs`, `lvs`. Install: `sudo apt install lvm2` / `sudo dnf install lvm2`. <https://sourceware.org/lvm2/>
- **`parted`** — the GNU partition editor. Install: `sudo apt install parted` / `sudo dnf install parted`. <https://www.gnu.org/software/parted/>
- **`gdisk`** — the GPT-specialised partition editor. Smaller, simpler than `parted` for GPT work. Install: `sudo apt install gdisk` / `sudo dnf install gdisk`. <https://www.rodsbooks.com/gdisk/>
- **`fio`** — the canonical IO benchmark. Jens Axboe (kernel block-layer maintainer). Install: `sudo apt install fio` / `sudo dnf install fio`. <https://github.com/axboe/fio>
- **`smartmontools`** — `smartctl` (the SMART data reader) and `smartd` (the daemon that watches and alerts). Install: `sudo apt install smartmontools` / `sudo dnf install smartmontools`. <https://www.smartmontools.org/>
- **`hdparm`** — the legacy SATA/IDE tool. Mostly superseded by `nvme` and `smartctl` but `hdparm -tT /dev/sda` is still the fastest single-line read-bandwidth benchmark. <https://sourceforge.net/projects/hdparm/>
- **`nvme-cli`** — NVMe-specific tools: `nvme list`, `nvme smart-log`, `nvme id-ctrl`. Install: `sudo apt install nvme-cli` / `sudo dnf install nvme-cli`. <https://github.com/linux-nvme/nvme-cli>
- **`liburing`** — the userspace library for `io_uring`. C API. Install: `sudo apt install liburing-dev` / `sudo dnf install liburing-devel`. <https://github.com/axboe/liburing>

## Mini-project tooling (the 7-day capstone)

- **`nginx`** — the web server. Install: `sudo apt install nginx` / `sudo dnf install nginx`. <https://nginx.org/en/docs/>
- **`certbot`** — the Let's Encrypt client. Install: `sudo apt install certbot python3-certbot-nginx` / `sudo dnf install certbot python3-certbot-nginx`. <https://certbot.eff.org/>
- **`fail2ban`** — the log-watcher that bans abusive IPs by inserting iptables/nftables rules. Install: `sudo apt install fail2ban` / `sudo dnf install fail2ban`. <https://www.fail2ban.org/>
- **`unattended-upgrades`** (Debian/Ubuntu) — automatic security updates. Install: `sudo apt install unattended-upgrades`. <https://wiki.debian.org/UnattendedUpgrades>
- **`dnf-automatic`** (Fedora) — Fedora's equivalent. Install: `sudo dnf install dnf-automatic`. <https://dnf.readthedocs.io/en/latest/automatic.html>
- **`prometheus` + `node_exporter`** — optional, free monitoring. The `node_exporter` is a tiny Go binary that exposes machine metrics over HTTP; `prometheus` scrapes and stores them. For a one-host mini-project this is overkill; we recommend using `journalctl` and `sar` as the primary log sources and `node_exporter` only for the stretch goal. <https://prometheus.io/>
- **`uptime-kuma`** (optional) — a self-hosted HTTP-ping monitor. Lightweight, single-container, includes Slack/Discord/email alert routing. <https://github.com/louislam/uptime-kuma>
- **`logwatch`** — daily-summary email of system events. Install: `sudo apt install logwatch` / `sudo dnf install logwatch`. <https://github.com/logwatch/logwatch>

## Free-tier VM providers (mini-project)

These all offer a no-cost tier as of May 2026. Verify pricing before signing up; free tiers change. The mini-project does not require any of them — a local VirtualBox/UTM/Multipass VM is equivalent.

- **Oracle Cloud Always Free** — two AMD VM.Standard.E2.1.Micro instances (1 vCPU, 1 GB RAM) or four Ampere A1 ARM cores total. The most generous free tier in the industry as of mid-2025. <https://www.oracle.com/cloud/free/>
- **AWS Free Tier** — 750 hours/month of `t3.micro` (Linux) for 12 months from account creation. After 12 months, pay-as-you-go. <https://aws.amazon.com/free/>
- **Google Cloud Free Tier** — one `e2-micro` in us-west1/us-central1/us-east1 free indefinitely. 30 GB persistent disk. <https://cloud.google.com/free>
- **Azure Free Account** — $200 credit for 30 days plus a `B1S` for 12 months. <https://azure.microsoft.com/en-us/free/>
- **Fly.io** — 3 shared-cpu-1x VMs, 256 MB RAM each, free. Small but real. <https://fly.io/docs/about/pricing/>
- **Hetzner Cloud Trial** — €20 trial credit. Small `CX22` at €3.79/month afterwards; the cheapest dependable VPS in Europe. <https://www.hetzner.com/cloud>

For purely local: **VirtualBox** (free, Oracle), **UTM** (free, macOS-native, Apple Silicon-aware), **Multipass** (free, Canonical, Ubuntu-specialised), **QEMU** (free, all platforms).

## Videos (free)

- **Christoph Hellwig — "The Linux Storage Stack"** (FOSDEM 2019) — a one-hour walk of the entire stack from the device driver up. Free, in English, recorded:
  <https://archive.fosdem.org/2019/schedule/event/storage_stack/>
- **Jens Axboe — "io_uring: The Latest Performance API"** (Kernel Recipes 2019) — the author of `io_uring` introducing it. Forty minutes:
  <https://www.youtube.com/watch?v=-5T4Cjw46ys>
- **Brendan Gregg — "File Systems Performance: Tunables, Trade-offs"** (USENIX LISA, various years) — the relevant chapter from the *Systems Performance* book in talk form. Forty minutes:
  <https://www.brendangregg.com/Slides/>
- **Avi Miller — "LVM in 20 Minutes"** (LinuxCon, 2017) — the briefest competent introduction to LVM available. Twenty minutes:
  <https://www.youtube.com/results?search_query=LVM+in+20+minutes>
- **Dave Chinner — "XFS: There and Back ... and There Again"** (LSF/MM 2015 keynote) — the maintainer of xfs telling the design story. Forty-five minutes. The technical depth is high:
  <https://lwn.net/Articles/638546/>

## Tools to install on day 1

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install -y util-linux parted gdisk e2fsprogs xfsprogs btrfs-progs \
                    lvm2 fio smartmontools hdparm nvme-cli \
                    nginx fail2ban unattended-upgrades

# Fedora
sudo dnf install -y util-linux parted gdisk e2fsprogs xfsprogs btrfs-progs \
                    lvm2 fio smartmontools hdparm nvme-cli \
                    nginx fail2ban dnf-automatic
```

- `util-linux` — `lsblk`, `fdisk`, `mount`, `wipefs`. Preinstalled; listed for completeness.
- `parted`, `gdisk` — partition editors. `parted` is GNU and scriptable; `gdisk` is small and GPT-specific.
- `e2fsprogs` — ext4 tools. Preinstalled; listed for completeness.
- `xfsprogs` — xfs tools.
- `btrfs-progs` — btrfs tools.
- `lvm2` — Logical Volume Manager. The `dmsetup` tool comes from the related `device-mapper` package, usually pulled in as a dependency.
- `fio` — the IO benchmark.
- `smartmontools` — `smartctl` for disk health.
- `hdparm`, `nvme-cli` — device-specific tools.
- `nginx`, `fail2ban`, `unattended-upgrades` / `dnf-automatic` — for the mini-project capstone.

## Filesystem decision matrix

A one-screen reference. Read alongside lecture 2.

| Workload | Recommended FS | Why |
|----------|----------------|-----|
| General-purpose root filesystem on a server | **ext4** | Conservative, mature, journalled, well-tooled. The safe answer when in doubt. |
| RHEL/CentOS Stream root | **xfs** | RHEL's default since 7. Strong large-file and parallel-write performance. |
| Database (PostgreSQL, MySQL, large random IO) | **xfs** or **ext4** | Both work. xfs scales better with many cores; ext4 has slightly more predictable small-write latency. **Avoid btrfs for high-write databases**: copy-on-write fragments under random writes. |
| File server with many small files | **ext4** | xfs has historically had slower metadata operations for small files; recent versions narrow the gap but ext4 is still the easier choice. |
| Workstation that benefits from snapshots and subvolumes | **btrfs** | CoW snapshots, `send/receive` for backup, subvolumes for per-package isolation. Fedora Workstation's default since 33. |
| Boot/EFI System Partition | **vfat (FAT32)** | UEFI firmware reads only FAT. Use `mkfs.vfat -F 32`. Not negotiable. |
| `/boot` (separate from root, in non-UEFI setups) | **ext4** or **ext2** | Boot loader-readable. GRUB reads ext2/3/4. |
| Swap | **none** (raw partition) or **swapfile** on ext4/xfs | `mkswap`; not a "filesystem" in the read/write sense. |
| Network-attached storage (you mount, do not create) | (whatever the NAS uses) | `cifs`, `nfs`, `sshfs`. Mount via `/etc/fstab` with appropriate options. |

## Mount options reference

The options that show up most often and what they actually do.

| Option | Meaning |
|--------|---------|
| `defaults` | The composite of `rw`, `suid`, `dev`, `exec`, `auto`, `nouser`, `async`. |
| `ro` / `rw` | Read-only / read-write. |
| `noatime` | Do not update access times on read. Significant performance win on read-heavy workloads. Almost always safe. |
| `nodiratime` | Same for directory access times. Implied by `noatime`. |
| `relatime` | Update `atime` only if `mtime` or `ctime` is newer, or `atime` is older than a day. The kernel default since 2.6.30. |
| `strictatime` | Always update `atime`. The pre-2.6.30 default. Avoid. |
| `lazytime` | Defer `atime`/`mtime`/`ctime` updates to memory; flush on `fsync` or hourly. Combined with `relatime` for best results. |
| `nodev` | Do not interpret character or block special devices on this filesystem. Hardening for `/tmp`, `/home`. |
| `nosuid` | Ignore SUID/SGID bits. Hardening for `/tmp`, `/home`, removable media. |
| `noexec` | Do not allow execution of binaries. Hardening for `/tmp`, `/var/tmp`. (Note: this does not stop `bash script.sh` if `bash` itself is elsewhere.) |
| `discard` | Issue TRIM commands to the SSD on file delete. Alternative: a weekly `fstrim` cron. Modern advice leans toward `discard` for desktops, `fstrim` for servers. |
| `commit=N` | ext4: flush the journal every N seconds (default 5). Higher = better write throughput, more data loss on crash. |
| `data=ordered` / `data=writeback` / `data=journal` | ext4: journaling mode. `ordered` is the default and almost always correct. `journal` (data + metadata in journal) is safest but slowest. |
| `errors=remount-ro` | ext4: on a filesystem error, remount read-only rather than continue. The conservative default. |
| `barrier=0` / `barrier=1` | Enable / disable write barriers. **Almost never disable.** Write barriers ensure the journal is consistent on crash; disabling them on a non-battery-backed disk is data-loss-on-power-fail. |
| `user_xattr` | Enable extended attributes. Default on ext4, xfs, btrfs. |
| `acl` | Enable POSIX ACLs. Default on ext4, xfs, btrfs. |
| `subvol=NAME` | btrfs: mount a specific subvolume. |
| `compress=zstd:N` | btrfs: transparently compress with zstd. `N` is the level (1 fast, 15 slow). |

## `/proc` and `/sys` files for storage

| Path | Contents |
|------|----------|
| `/proc/diskstats` | Per-block-device IO counters. The 11 fields per device are documented in `Documentation/admin-guide/iostats.rst`. |
| `/proc/mounts` | The live mount table (a symlink to `/proc/self/mounts`). Same shape as `/etc/fstab`. |
| `/proc/meminfo` | Memory counters. `Cached:`, `Buffers:`, `Dirty:`, `Writeback:` are the storage-relevant ones. |
| `/proc/sys/vm/dirty_ratio` | The dirty-pages-percent-of-RAM ceiling. |
| `/proc/sys/vm/dirty_background_ratio` | The dirty-pages-percent at which background writeback begins. |
| `/proc/sys/vm/dirty_expire_centisecs` | Dirty page age (centiseconds) before forced flush. |
| `/proc/sys/vm/drop_caches` | Write 1 to drop page cache, 2 to drop dentries/inodes, 3 to drop both. |
| `/sys/block/<dev>/queue/scheduler` | The IO scheduler for the device. `mq-deadline`, `none`, `bfq` are the modern options. |
| `/sys/block/<dev>/queue/rotational` | 1 for spinning disks, 0 for SSD/NVMe. |
| `/sys/block/<dev>/queue/read_ahead_kb` | The read-ahead window in KiB. Default 128. |
| `/sys/block/<dev>/queue/nr_requests` | The block-layer queue depth per device. |
| `/sys/block/<dev>/device/model`, `/serial` | Device identification. |

## Glossary

| Term | Definition |
|------|------------|
| **Block device** | A device that delivers fixed-size random-access blocks. Buffered by the page cache. `b` in `ls -l`. Examples: `/dev/sda`, `/dev/nvme0n1`. |
| **Character device** | A device that delivers unbuffered byte streams. `c` in `ls -l`. Examples: `/dev/tty`, `/dev/random`, `/dev/null`. |
| **Major / minor number** | The kernel's identification of a device. Major selects the driver (8 = sd, 259 = nvme); minor selects the specific device within the driver. |
| **MBR** | Master Boot Record. The legacy 1983 partition table; 32-bit LBA (2 TiB ceiling), 4 primary partitions. |
| **GPT** | GUID Partition Table. The modern partition table; 64-bit LBA, 128 default entries, redundant headers, UUIDs everywhere. |
| **ESP** | EFI System Partition. A small (~500 MB) FAT32 partition that UEFI firmware reads to find the boot loader. |
| **Filesystem** | The on-disk format that organises a block device into files, directories, and metadata. `ext4`, `xfs`, `btrfs`, `vfat`. |
| **Mount** | The act of associating a filesystem with a directory in the tree. `mount /dev/sdb1 /mnt/data`. |
| **`/etc/fstab`** | The file that records mounts to be performed at boot. Six fields per line. |
| **Page cache** | The kernel's in-memory cache of file pages. All reads pass through it; the size grows to fill free RAM. |
| **Dirty page** | A page in the page cache whose in-memory copy is newer than the on-disk copy. Flushed by the kernel's writeback threads. |
| **Writeback** | The process by which dirty pages are flushed to disk. Triggered by thresholds, age, or `fsync`. |
| **LVM** | Logical Volume Manager. A layer between block devices and filesystems that pools physical volumes into volume groups and slices them into logical volumes. |
| **PV / VG / LV** | The three LVM objects: **physical volume** (a block device claimed by LVM), **volume group** (a pool of PVs), **logical volume** (a slice of the VG presented as a block device). |
| **`fio`** | Flexible IO tester. Jens Axboe's IO benchmark, the canonical Linux disk-benchmark tool. |
| **`io_uring`** | The Linux 5.1+ asynchronous-IO interface. Submission queue + completion queue, shared with the kernel via mmap. The modern high-performance IO API. |
| **`fsync`** | The syscall `fsync(fd)` that forces all dirty pages of the file to be flushed to durable storage before it returns. The unit of durability for databases. |
| **TRIM / discard** | The SSD command that tells the device "the blocks at LBA X-Y are no longer in use; you may garbage-collect them." Issued by `discard` mount option or `fstrim` command. |
| **SMART** | Self-Monitoring, Analysis, and Reporting Technology. Disk-firmware-tracked health attributes. Read with `smartctl`. |
| **`fsck`** | File System Consistency checK. Runs only on unmounted filesystems. The tool that repairs metadata after a crash. |
| **Swap** | Disk space used as overflow memory when RAM is exhausted. A raw partition (`mkswap`) or a swap file. |
| **`drop_caches`** | The `/proc/sys/vm/drop_caches` knob that flushes the page cache, dentries, and inodes. Diagnostic only; never use in production. |

## Free books and write-ups

- **Linux Kernel Module Programming Guide** — the LKMPG. Free PDF/HTML. Covers writing kernel modules including block-device drivers. Useful if you ever wonder what a filesystem driver actually does:
  <https://sysprog21.github.io/lkmpg/>
- **The Linux Documentation Project (TLDP)** — large, old, mostly still accurate. The "Linux System Administrators' Guide" and "LVM HOWTO" are the relevant Week 8 entries:
  <https://tldp.org/>
- **Greg Kroah-Hartman — "Linux Kernel in a Nutshell"** — free PDF. Older (2007) but the chapter on `/proc` and `/sys` is still the clearest reference outside the source:
  <https://www.kroah.com/lkn/>
- **Julia Evans — *Linux Debugging Tools You'll Love*** — already cited in Week 7. The chapter on `strace` and on `lsof` is relevant when "the disk is busy" turns into "which file?":
  <https://jvns.ca/blog/2014/04/20/debug-your-programs-like-they-are-closed-source/>
- **Adam Leventhal — "Performance Implications of File System Compression"** (USENIX 2018) — a careful empirical study of when compressing data on a fast SSD wins and when it loses. Generalises to "when to use btrfs `compress=zstd`":
  <https://www.usenix.org/conference/atc18/presentation/leventhal>

---

*Broken link? Open an issue.*
