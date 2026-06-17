# Lecture 2 — Filesystems and mount options

> *Lecture 1 left you at the partition. This lecture is about what goes inside it. There are three production-quality filesystems on Linux in 2026 — **ext4**, **xfs**, **btrfs** — and one specialised file-server filesystem (**zfs**, available out-of-tree). Each has a personality, a default, and a set of trade-offs. The skill is not to memorise every option but to know **which filesystem suits which workload** well enough to defend the choice in a code review, and to know **which mount options actually move the needle** at runtime. We end with the six fields of `/etc/fstab` and the mistakes that lock you out of your own machine at boot.*

---

## 1. What a filesystem actually is

A filesystem is the **on-disk format** that turns a block device into a tree of files and directories. The format is a contract between:

- **The kernel module** (e.g. `ext4`, `xfs`, `btrfs`) that knows how to read and write the format.
- **The userspace tools** (e.g. `mkfs.ext4`, `e2fsck`, `tune2fs`) that create, check, and tune the format.
- **The filesystem documentation** (in the kernel source tree under `Documentation/filesystems/`) that defines what is on disk.

When the kernel mounts a filesystem, it reads the **superblock** — a small region of the device that contains the filesystem's signature, UUID, label, size, free-block count, root inode pointer, and feature flags. From the superblock, the kernel knows how to walk the rest of the on-disk structures. Every filesystem has a superblock; the layout differs by filesystem.

A filesystem provides at minimum:

- **Files** — sequences of bytes addressable by an opaque integer (the **inode number**).
- **Directories** — files that contain a list of name-to-inode mappings.
- **Metadata** — for each inode: owner UID/GID, permissions, atime/mtime/ctime, size, link count, type (regular, directory, symlink, device, fifo, socket).
- **Allocation** — a way to track which blocks of the device are used and which are free.

Modern Linux filesystems add:

- **Journalling** (ext4, xfs) — a write-ahead log of metadata changes so the filesystem can recover after a crash without a full `fsck`.
- **Copy-on-write** (btrfs, zfs) — every write goes to a new block; the old data is preserved until garbage-collected. Enables snapshots and cheap rollback.
- **Extended attributes** (`xattr`) — arbitrary `name=value` metadata per file. Used by SELinux, file capabilities, ACLs, and modern utilities like `borg` for backup metadata.
- **POSIX ACLs** — finer-grained permissions than the classic owner/group/other model.
- **Quotas** — per-user or per-group disk-usage limits.

The three filesystems we care about — ext4, xfs, btrfs — all support these. The differences are in the **design**: how data is laid out on disk, how the journal is structured, what is fast and what is slow.

---

## 2. ext4 — the conservative default

### 2.1 History and design

`ext4` is the fourth in the ext family: `ext` (1992) → `ext2` (1993) → `ext3` (2001, added journalling) → `ext4` (2008, added extents, 48-bit block addresses, delayed allocation). It is the default on Debian, Ubuntu, and most distributions that do not specifically prefer xfs or btrfs.

Design highlights:

- **Block groups.** The disk is divided into fixed-size groups (typically 128 MiB), each with its own bitmap, inode table, and data blocks. This keeps allocation local — files and their inodes tend to live in the same group, reducing seeks on rotating disks.
- **Extents.** Where ext2/3 tracked file allocation as a list of individual blocks, ext4 uses **extents**: contiguous-block runs described by (start, length). A 1 GB sequential file might be one or a few extents, not 250,000 block pointers.
- **Delayed allocation.** Writes go into the page cache first; the actual block allocation is deferred until writeback, by which time the kernel knows the size of the write and can allocate a single contiguous extent.
- **HTree directories.** Large directories use a B-tree-like hash index for fast lookup. `ls /huge/directory/` does not scan a linear list.
- **Journalling, three modes.** `data=ordered` (default): data is written before metadata is journalled, so on crash you do not see metadata pointing to garbage. `data=writeback`: data is not ordered with metadata; faster, but you can see garbage after a crash. `data=journal`: data **and** metadata are journalled; slowest, safest, used only for very high-integrity workloads.

### 2.2 When to choose ext4

- **You do not have a reason to choose something else.** This is the most common case. ext4 is mature, well-tooled, well-understood, and supported by every Linux administrator on Earth.
- **Workloads with mixed file sizes** and no particular pattern. ext4 is the generalist.
- **Boot and root filesystems.** Almost every Linux installer offers ext4 as a sensible default for `/`.
- **Workloads where you need to read post-crash recovery logs and people-readable fsck output.** `fsck.ext4` is the most diagnostic tool in this space.

### 2.3 When **not** to choose ext4

- **Very large filesystems** (10 TB+) with parallel-write workloads. xfs scales better.
- **You want snapshots without LVM**. ext4 has no snapshots; you have to use LVM's snapshot facility.
- **You have many small files in deep directory trees**. ext4 is fine here, but btrfs's subvolumes can be more ergonomic.

### 2.4 Key options at `mkfs.ext4` time

```bash
sudo mkfs.ext4 \
    -L mylabel \
    -U random \
    -T news \
    -E lazy_itable_init=1 \
    /dev/sdb1
```

- `-L LABEL` — filesystem label, up to 16 characters. Shows in `lsblk -f`.
- `-U UUID` — explicit UUID (rare; `random` is the default).
- `-T DESC` — usage hint. `-T news` (many small files), `-T largefile` (few large files), `-T largefile4` (very few, very large). Tunes the inode-to-block-group ratio.
- `-E lazy_itable_init=1` — do not zero the inode table at format time; let it happen lazily. Faster format; some performance tools show transient activity afterwards as the table is filled.
- `-m PERCENT` — reserved blocks (default 5 % of the filesystem reserved for `root`). Drop to 1 % on data-only volumes (`-m 1`) to recover 4 %.

Run `mkfs.ext4 -h` (or `man 8 mkfs.ext4`) for the full list.

### 2.5 Key options at mount time

The ext4-relevant entries from `man 8 mount`:

| Option | Default? | What it does |
|--------|----------|--------------|
| `data=ordered` | yes | Journal metadata; write data before metadata. The safe default. |
| `data=writeback` | no | Journal metadata; do not order data writes. Faster, weaker safety. |
| `data=journal` | no | Journal data and metadata. Slowest, strongest safety. |
| `commit=N` | 5 | Flush the journal every N seconds. Higher = better throughput, more data loss on crash. |
| `barrier=1` | yes | Use write barriers. **Do not disable.** |
| `errors=remount-ro` | yes | Remount read-only on FS error. The right default. |
| `noatime` | no | Do not update `atime` on read. Big win on read-heavy workloads. |
| `nodiratime` | no | Same for directories. Implied by `noatime`. |
| `relatime` | yes | Update `atime` only when `mtime`/`ctime` is newer or `atime` > 1 day. Kernel default since 2.6.30. |
| `discard` | no | Issue TRIM on file delete. Alternative: weekly `fstrim`. |
| `journal_async_commit` | no | Asynchronously commit the journal. Faster; slightly weaker ordering. |

The line that does most of the work on a typical server:

```
UUID=... /var/data ext4 defaults,noatime,nodiratime,errors=remount-ro 0 2
```

Reference: kernel `Documentation/filesystems/ext4.rst`, `man 8 mount` (the "Filesystem-independent mount options" and "Mount options for ext4" sections).

---

## 3. xfs — large files, parallel writes, RHEL's default

### 3.1 History and design

`xfs` was designed by SGI in 1993 for the Irix operating system and ported to Linux in 2001. It is now maintained by Red Hat and is the default filesystem on RHEL (since 7) and its derivatives.

Design highlights:

- **Allocation groups.** xfs divides the filesystem into a configurable number (default 4) of **allocation groups** (AGs). Each AG has its own free-space and inode bitmaps and is largely independent. This means **parallel writes to different AGs do not contend**, which is why xfs scales beautifully on many-core machines and SSDs with high IOPS.
- **B+tree everywhere.** Free-space tracking, inode tracking, extent maps — all B+trees. No linear scans on metadata operations.
- **64-bit on disk.** xfs has always been 64-bit; no `2^32` ceilings to design around.
- **Journalled metadata only.** xfs journals metadata; data writes are not journalled. The justification: a journal protects you from filesystem inconsistency, not from the application's view of partial writes. The application is responsible for `fsync` if it cares about durability.
- **Online operations.** xfs can be grown online (`xfs_growfs`), defragmented online (`xfs_fsr`), and tuned online (`xfs_io`).

### 3.2 When to choose xfs

- **Large filesystems** (10 TB+, especially with many parallel writers).
- **Workloads with many large files**: video, scientific data, large databases.
- **You are on RHEL, AlmaLinux, Rocky Linux, or CentOS Stream.** The default; the supported configuration; sticking with it removes class of subtle interaction problems.
- **You need to grow a filesystem online without unmounting.** `xfs_growfs` works on a mounted FS.

### 3.3 When **not** to choose xfs

- **You need to shrink the filesystem.** xfs **cannot** be shrunk. There is no `xfs_shrink`. If you over-allocate, you must dump and re-create.
- **Very small filesystems** (< 100 MB). xfs has more overhead than ext4 at small sizes; ext4 wins.
- **Workloads with massive metadata churn on small files**. Recent xfs versions have closed the gap; old benchmarks showed ext4 winning on directories with millions of tiny files. Test before believing.

### 3.4 Key options at `mkfs.xfs` time

```bash
sudo mkfs.xfs \
    -L mylabel \
    -f \
    -d agcount=8,su=64k,sw=4 \
    /dev/sdb1
```

- `-L LABEL` — label.
- `-f` — force; overwrite existing filesystem. Required if the device has any previous signature.
- `-d agcount=N` — number of allocation groups. The default scales with device size; you rarely need to override.
- `-d su=N,sw=M` — stripe unit and stripe width, for RAID arrays. Tells xfs to align its allocation to the RAID geometry. Useful, but specialised.
- `-i size=N` — inode size in bytes. Default 512; increase to 1024 or 2048 if you store many extended attributes (SELinux, ACLs).

Run `mkfs.xfs -h` for the full list. `man 8 mkfs.xfs`.

### 3.5 Key options at mount time

| Option | Default? | What it does |
|--------|----------|--------------|
| `noatime` | no | Same as ext4. Big win on read-heavy. |
| `relatime` | yes | Kernel default. |
| `discard` | no | TRIM on delete. xfs supports this; same trade-off as ext4. |
| `inode64` | yes (since 3.7) | Allow 64-bit inode numbers. Required for large filesystems. The default since kernel 3.7. |
| `logbsize=N` | 32k | Log buffer size. Larger = better write throughput on bursty workloads. |
| `nobarrier` | no | Disable write barriers. **Do not.** |
| `allocsize=N` | 64k | Preallocation size for streaming writes. Larger = less fragmentation on growing files. |

The line that does most of the work on an xfs data volume:

```
UUID=... /var/data xfs defaults,noatime,nodiratime 0 0
```

Note the `0` in the `pass` field for xfs: the xfs maintainers recommend `pass=0` because `xfs_repair` is **not** a `fsck.xfs` and should not be run at boot. On xfs, integrity is the journal's job; `xfs_repair` exists for the cases where the journal cannot recover.

Reference: kernel `Documentation/filesystems/xfs.rst`, `man 8 mount` (the "Mount options for xfs" section), the SGI 1996 USENIX paper "Scalability in the XFS File System."

---

## 4. btrfs — copy-on-write, snapshots, subvolumes

### 4.1 History and design

`btrfs` (B-tree File System) is a copy-on-write filesystem started at Oracle in 2007 and merged into the mainline kernel in 2009. It became the default for Fedora Workstation in version 33 (October 2020) and is widely used on SUSE.

Design highlights:

- **Copy-on-write.** Every write goes to a new block; the old block is preserved (and freed only when no reference remains). This is the basis for snapshots: a snapshot is just a new tree root pointing at the existing blocks. The snapshot is created in `O(1)` time and uses zero extra space until divergence.
- **Subvolumes.** A btrfs filesystem can contain many **subvolumes**, each with its own tree. Subvolumes can be mounted independently, snapshotted independently, sent over the network independently (`btrfs send | btrfs receive`).
- **Transparent compression.** `compress=zstd:3` (or `lzo`, or `zlib`) at mount time enables per-block compression. Good for log-heavy or text-heavy workloads.
- **Built-in RAID.** Single, RAID0, RAID1, RAID10, RAID5/6 (the last two still flagged as unstable in 2026; do not use for production data). You give btrfs multiple devices at `mkfs.btrfs` time, and it manages them.
- **Online operations.** Grow, balance, scrub, defrag — all online. `btrfs scrub` reads every block, verifies the checksum, and repairs from a RAID copy if the checksum fails.

### 4.2 When to choose btrfs

- **Workstation systems** that benefit from snapshots. `dnf` and `zypper` can snapshot the system before each update, allowing rollback in seconds if the update breaks something. Both Fedora and openSUSE wire this in by default.
- **Backup targets** that want `btrfs send / receive` for incremental, efficient, compressed transfers.
- **NAS-style workloads** with mixed file sizes and a desire for snapshots without LVM.
- **You want compression without a separate compression layer.** `compress=zstd:3` mounts cleanly and is approximately free for most workloads.

### 4.3 When **not** to choose btrfs

- **High-write databases** (PostgreSQL, MySQL with InnoDB heavy random writes). CoW fragments under random writes; you can mitigate with `chattr +C` on the database directory (turns off CoW for that subtree), but at that point ext4 or xfs is the simpler answer.
- **You need RAID 5/6 in production.** As of 2026, btrfs RAID 5/6 is still flagged as not-fully-ready. Use mdraid + ext4 or zfs instead.
- **You are on a kernel older than 5.x.** btrfs has had a rough history; the recent kernels are much better. Check that your kernel is recent.
- **You need predictable behaviour under heavy memory pressure.** btrfs's CoW interacts with the page cache in complex ways. ext4 and xfs are more predictable.

### 4.4 Key options at `mkfs.btrfs` time

```bash
sudo mkfs.btrfs \
    -L mylabel \
    -d single \
    -m dup \
    /dev/sdb1
```

- `-L LABEL` — label.
- `-d PROFILE` — data profile: `single` (one copy), `dup` (two copies on same device), `raid0`, `raid1`, `raid10`. Default is `single` for one device.
- `-m PROFILE` — metadata profile. Default is `dup` for single-device filesystems on SSDs (metadata is doubly stored for resilience).

For multi-device:

```bash
sudo mkfs.btrfs -d raid1 -m raid1 /dev/sdb /dev/sdc
```

### 4.5 Key options at mount time

| Option | Default? | What it does |
|--------|----------|--------------|
| `subvol=NAME` | n/a | Mount a specific subvolume instead of the root subvolume. |
| `subvolid=N` | n/a | Same, by ID. |
| `compress=zstd:N` | no | Transparently compress with zstd. `N` is the level (1 fast, 15 slow; 3 is a good default). |
| `compress-force=zstd:N` | no | Same, but compress even small or incompressible files. Usually a mistake. |
| `noatime` | no | Same as elsewhere. |
| `ssd` | autodetected | Enable SSD-optimised allocation. |
| `discard=async` | no | Asynchronous TRIM. Better than the synchronous `discard` for SSD wear; use this on btrfs SSDs. |
| `autodefrag` | no | Automatic defragmentation on writes. Useful for desktop workloads with many small writes. |

A typical btrfs mount line on a workstation:

```
UUID=... /              btrfs defaults,subvol=@,compress=zstd:3,noatime,discard=async 0 0
UUID=... /home          btrfs defaults,subvol=@home,compress=zstd:3,noatime,discard=async 0 0
```

The same filesystem mounted twice, at two different subvolumes. This is the canonical btrfs layout.

Reference: kernel `Documentation/filesystems/btrfs.rst`, the upstream wiki at <https://btrfs.readthedocs.io/>.

---

## 5. A few words on zfs

`zfs` is the fourth contender. It is **not in the upstream Linux kernel** because of CDDL/GPL licence incompatibility, but the **OpenZFS** project maintains a high-quality out-of-tree kernel module. zfs is the gold standard for storage in 2026, but you have to install it yourself, and you have to keep it in step with kernel updates (which sometimes lag).

For the C14 curriculum we cover zfs as a **resource pointer**, not as a topic of instruction. If you find yourself running a file server with strict integrity requirements and snapshots-and-send capabilities, study zfs. The OpenZFS documentation is at <https://openzfs.github.io/openzfs-docs/>; the canonical book is *FreeBSD Mastery: ZFS* by Lucas and Jude (also covers Linux installations).

The single most important zfs concept is the **pool** (`zpool`): a layer that combines and pools devices, including RAID, before any filesystem is created on top. zfs blurs the lines between LVM and the filesystem in a way Linux's native tools deliberately do not.

---

## 6. `/etc/fstab` — the six fields

`/etc/fstab` is the file `mount -a` reads at boot to perform every mount. It is also re-read on `mount /point` when the device is left out: `mount /home` finds `/home` in `fstab` and uses the recorded device, type, and options.

The format is six whitespace-separated fields:

```
<device>  <mountpoint>  <type>  <options>  <dump>  <pass>
```

Example, well-commented:

```
# /etc/fstab — mountpoints persisted across reboots.

# <device>                                <mountpoint>  <type>  <options>                                       <dump>  <pass>

# Root filesystem.
UUID=11111111-2222-3333-4444-555555555555 /             ext4    defaults,errors=remount-ro                       0       1

# EFI System Partition (UEFI systems).
UUID=AAAA-BBBB                             /boot/efi     vfat    umask=0077,shortname=winnt                       0       1

# Separate /home, on a different disk.
UUID=66666666-7777-8888-9999-AAAAAAAAAAAA /home         ext4    defaults,noatime,nodiratime                     0       2

# Data volume on an LVM logical volume.
/dev/mapper/data-web                       /srv/web      xfs     defaults,noatime,nodiratime                     0       0

# Swap, on a partition.
UUID=BBBBBBBB-CCCC-DDDD-EEEE-FFFFFFFFFFFF none          swap    sw                                              0       0

# Bind mount: expose /srv/web as /var/www inside a chroot.
/srv/web                                   /var/www      none    bind                                            0       0

# Temporary filesystem in memory, hardened.
tmpfs                                      /tmp          tmpfs   defaults,nodev,nosuid,noexec,size=2G            0       0
```

Read it field by field.

### 6.1 Field 1: device

The block device, or a `UUID=` or `LABEL=` reference to one. **Always prefer `UUID=` over `/dev/...`** because device names can change (you add a USB stick, `/dev/sdb` is now the USB stick, and your data disk is now `/dev/sdc`).

For network filesystems (`nfs`, `cifs`) the "device" field is a network address: `server:/export` for NFS.

For special filesystems (`tmpfs`, `proc`, `sysfs`) the field is conventionally a string like `tmpfs` or `none` — it is not actually used.

### 6.2 Field 2: mountpoint

The directory at which to mount. Must exist (create it with `mkdir -p` before adding the line). For swap, conventionally `none` or `swap`.

### 6.3 Field 3: type

The filesystem type. `ext4`, `xfs`, `btrfs`, `vfat`, `tmpfs`, `nfs`, `cifs`, `swap`, etc. Use `auto` to let the kernel detect, but explicit is better.

### 6.4 Field 4: options

Comma-separated mount options. `defaults` is the convention for "I have nothing special to say"; on top of it you typically add `noatime`, `nodiratime`, `errors=remount-ro` (ext4), or filesystem-specific options.

The full list of generic options is in `man 8 mount` under "FILESYSTEM-INDEPENDENT MOUNT OPTIONS". Filesystem-specific options are under "FILESYSTEM-SPECIFIC MOUNT OPTIONS" further down.

### 6.5 Field 5: dump

Used by the `dump(8)` backup utility, which is essentially extinct in 2026. **Set to 0.** Old `fstab` files sometimes have `1` here; it is harmless but unused.

### 6.6 Field 6: pass

Determines `fsck` order at boot:

- `0` — never `fsck` this filesystem at boot.
- `1` — `fsck` first. Use only for the root filesystem.
- `2` — `fsck` after the root filesystem. Use for other ext4 filesystems.

For **xfs** and **btrfs**, set `pass=0`: these filesystems do not have a `fsck.<type>` that should run at boot. xfs's journal recovers automatically at mount; btrfs's integrity is checksummed. For **ext4**, set `pass=1` for root, `pass=2` for everything else, `0` for non-essential mounts where a boot delay is unacceptable.

### 6.7 The cardinal rule: always test before reboot

```bash
sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)   # back up
sudo nano /etc/fstab                            # edit
sudo findmnt --verify                           # syntax check
sudo mount -a                                   # mount everything; errors will show
```

If `mount -a` fails, the system **will not boot**. You will see "Failed to start Local File Systems target" and drop into emergency mode. The recovery is to boot single-user, `mount -o remount,rw /`, edit `/etc/fstab`, reboot. Not catastrophic, but not fun.

`findmnt --verify` (added in `util-linux` 2.32, 2018) catches most typos:

```
$ sudo findmnt --verify
/                                                   [W] non-canonical target path (recommended is "/")
/mnt/foo: target does not exist
/home: 'noatime' is not allowed on a /home mount  (false; demo)
```

Run it after every edit.

---

## 7. The options that matter

The mount-options space is large; in practice three or four options carry most of the weight.

### 7.1 `noatime`

By default, every read of a file updates the file's **access time** (`atime`) in its inode. This means every read becomes a write: even `cat` and `grep` modify the disk. On read-heavy workloads (log files, static-asset serving) this is a real cost.

`noatime` disables `atime` updates entirely. Almost always safe; the few programs that actually use `atime` (mutt-style mail clients to detect "new mail in mbox", some backup tools) are rare.

The kernel default is `relatime`, a compromise: update `atime` only if `mtime` or `ctime` is newer, or `atime` is older than one day. This makes `mutt` happy without writing on every read. For most server workloads, **`noatime` is strictly better than `relatime`**.

Recommended for almost all server mounts. Implies `nodiratime`.

### 7.2 `discard` versus `fstrim`

SSDs need to know which blocks are no longer in use so the firmware can garbage-collect. Linux has two ways to tell them:

1. **`discard` mount option** — issues a TRIM command on every `unlink` (file delete). Synchronous, in line with the delete. Works on every filesystem.
2. **`fstrim` command** — issues a bulk TRIM for all currently-free blocks. Run periodically (typically weekly via a systemd timer).

For most years, **`fstrim` was the recommended approach**: the `discard` mount option produced too many small TRIM commands and slowed down workloads with many deletes (mail spools, build directories). In 2026 the picture is more nuanced: modern SSDs handle in-line TRIM well, and the systemd-distros (Fedora, recent Ubuntu) tend to enable both.

The btrfs `discard=async` option is a compromise — TRIM in a kernel work queue, not on the delete syscall. Strong default for btrfs SSDs.

### 7.3 `errors=remount-ro` (ext4)

On a filesystem error (a corrupted block, an unrecoverable journal failure), ext4 by default **panics the kernel**. The `errors=remount-ro` option changes this: remount the filesystem read-only and continue. The system stays up; you have time to investigate; nothing else gets written.

This is what Ubuntu's installer puts on the root filesystem by default. Keep it.

### 7.4 `nodev`, `nosuid`, `noexec`

Hardening options for mount points that should never have privileged content:

- `nodev` — do not interpret block or character device nodes on this filesystem. Even if a malicious file is named `/tmp/sda` with the right mode, the kernel will refuse to open it as a device.
- `nosuid` — ignore SUID and SGID bits. A SUID binary on a `nosuid` mount runs with the calling user's privileges.
- `noexec` — refuse to execute files from this mount. **Note**: this does not stop `bash /tmp/script.sh` because `bash` itself is on a `exec` mount.

The conventional hardening is `defaults,nodev,nosuid,noexec` on `/tmp`, `/var/tmp`, `/dev/shm`, and `/home` if you do not allow user-installed binaries.

---

## 8. Worked example: adding a data disk to a server

The full sequence, ready to copy. **Bash Yellow**: this writes to a real block device. Practise on a loopback first.

```bash
# 1. Confirm the device.
lsblk

# 2. Wipe any previous signature (paranoia).
sudo wipefs -a /dev/sdb

# 3. Partition (GPT, one partition).
sudo parted --script /dev/sdb \
    mklabel gpt \
    mkpart primary ext4 1MiB 100%

# 4. Format.
sudo mkfs.ext4 -L data /dev/sdb1

# 5. Get the UUID.
UUID=$(sudo blkid -s UUID -o value /dev/sdb1)

# 6. Create the mountpoint.
sudo mkdir -p /var/data

# 7. Add the fstab line.
echo "UUID=${UUID}  /var/data  ext4  defaults,noatime,nodiratime,errors=remount-ro  0  2" | \
    sudo tee -a /etc/fstab

# 8. Back up fstab and verify.
sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)
sudo findmnt --verify

# 9. Mount it now (and confirm fstab is correct).
sudo mount -a
df -h /var/data

# 10. Set ownership.
sudo chown -R www-data:www-data /var/data
```

Ten steps. Read the device name twice. Back up `/etc/fstab`. Test with `mount -a` before rebooting. After all this, the disk is mounted, persistent across reboots, owned by the right user, and will survive the next kernel update.

---

## 9. Bash Yellow: the cardinal rules

- **Never `mkfs` a mounted filesystem.** `mkfs.ext4 /dev/sda1` while `/dev/sda1` is mounted as `/` destroys your operating system. Confirm with `mount | grep ${DEV}` first.
- **Never `fsck` a mounted filesystem.** `fsck.ext4 /dev/sda1` while `/dev/sda1` is mounted corrupts it. Boot from rescue media or unmount first.
- **Always back up `/etc/fstab` before editing.** A wrong line locks you out of the system at next reboot.
- **Always `findmnt --verify` and `mount -a` after editing `/etc/fstab`.** Catches typos before they catch you.
- **Always use `UUID=` in `/etc/fstab`, not `/dev/sdX`.** Device names are not stable.
- **Always read the man page section for the filesystem you are mounting.** `man 8 mount` has every option; the filesystem-specific sections (`man 5 ext4`, `man 5 xfs`) have the rest.

---

## Summary

- The three production filesystems are **ext4** (conservative, default), **xfs** (parallel writes, large files, RHEL default), **btrfs** (CoW, snapshots, subvolumes, Fedora Workstation default). Choose ext4 when in doubt.
- `mkfs.<type>` creates the on-disk format. `-L LABEL` is almost always worth setting. `-U UUID` is occasionally useful.
- `man 8 mount` documents every option. The four to know cold: **`noatime`** (the read-write reduction), **`discard`** or `fstrim` (SSD TRIM), **`errors=remount-ro`** (ext4 crash safety), **`nodev,nosuid,noexec`** (hardening for `/tmp`).
- `/etc/fstab` has six fields: device, mountpoint, type, options, dump, pass. Use `UUID=`, set `dump=0`, set `pass=1` for ext4 root, `2` for ext4 data, `0` for xfs and btrfs.
- **Back up `/etc/fstab` before editing.** **`findmnt --verify`** and **`mount -a`** after. A broken `/etc/fstab` is a single-user-mode recovery.
- **Never `mkfs`, `fsck`, or `parted` a mounted filesystem.** Confirm with `mount | grep DEV` first. Use loopback files (`losetup`) to practise destructive operations safely.

Reference: `man 8 mount`, `man 5 fstab`, `man 8 mkfs.ext4`, `man 8 mkfs.xfs`, `man 8 mkfs.btrfs`, kernel `Documentation/filesystems/`.

Next lecture: LVM (how to combine and slice block devices), the page cache (the in-memory file cache that makes Linux fast), dirty pages and writeback (the part where the cache must eventually meet the disk), and a brief tour of `fio` and `io_uring`.
