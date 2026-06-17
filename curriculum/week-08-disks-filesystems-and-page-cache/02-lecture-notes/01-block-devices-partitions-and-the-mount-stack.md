# Lecture 1 — Block devices, partitions, and the mount stack

> *Before you can choose a filesystem, you need a place to put it. That place is a **block device**: a kernel-managed view of a physical storage unit that delivers fixed-size pages and is buffered by the page cache. Before you can put a filesystem on the block device, you usually want to **partition** it — slice it into named regions. Before the partitions are usable, you have to **mount** them somewhere in the directory tree, which means the kernel reads the filesystem superblock, validates it, and exposes the files at a path. This lecture walks that stack from the device up to the mount, on a real example. Every command is one you will run in the exercises.*

---

## 1. What "a disk" actually is on Linux

A user says "the disk is full." What is "the disk"?

On Linux, **storage hardware** (an NVMe SSD, a SATA HDD, a virtual disk from your hypervisor, a USB stick, a SD card) is exposed to the kernel by a **driver**, and the driver registers one or more **block devices** with the block subsystem. Each block device is given a node under `/dev/`:

- **SATA / SAS disks**: `/dev/sda`, `/dev/sdb`, `/dev/sdc`, ... (the `sd` is "SCSI disk", which is also what SATA looks like through the kernel's `libata` translation layer)
- **NVMe disks**: `/dev/nvme0n1`, `/dev/nvme0n2`, `/dev/nvme1n1`, ... (the format is `nvme<controller>n<namespace>`; for a typical consumer SSD you have one controller and one namespace, so `nvme0n1`)
- **MMC / SD cards**: `/dev/mmcblk0`, `/dev/mmcblk1`, ...
- **Virtio block** (KVM/QEMU virtual disks): `/dev/vda`, `/dev/vdb`, ...
- **Xen block** (Xen virtual disks): `/dev/xvda`, `/dev/xvdb`, ...
- **Loopback devices** (a file presented as a block device, used in the exercises): `/dev/loop0`, `/dev/loop1`, ...

Run `lsblk` on any Linux box and you see the tree. On a typical laptop:

```
$ lsblk
NAME        MAJ:MIN RM   SIZE RO TYPE MOUNTPOINTS
nvme0n1     259:0    0 476.9G  0 disk
├─nvme0n1p1 259:1    0   512M  0 part /boot/efi
├─nvme0n1p2 259:2    0   1.7G  0 part /boot
└─nvme0n1p3 259:3    0 474.7G  0 part
  └─cryptroot 252:0    0 474.7G  0 crypt /
```

Three lines, one device with three partitions, one of which is a LUKS-encrypted container that contains the root filesystem. Read top to bottom:

- `nvme0n1` is the **whole physical device** (476.9 GiB).
- `nvme0n1p1`, `nvme0n1p2`, `nvme0n1p3` are **partitions** of that device.
- `cryptroot` is an **encrypted block device** sitting on top of the third partition.
- The mountpoints (`/boot/efi`, `/boot`, `/`) show where each is presented in the directory tree.

The `lsblk` tree is the single most important picture in this week. Memorise the layout.

### 1.1 Major and minor numbers

The `MAJ:MIN` column is the kernel's identification of the device. Every device has a **major number** (which selects the driver) and a **minor number** (which selects the specific device within the driver). The major numbers are allocated in `Documentation/admin-guide/devices.txt` in the kernel source tree:

- **8** — SCSI disk (`sd*`)
- **252** — device-mapper (LVM, dm-crypt)
- **253** — local/experimental
- **259** — NVMe
- **7** — loopback

The minor number identifies the specific device: `/dev/sda` is `8:0`, `/dev/sda1` is `8:1`, `/dev/sdb` is `8:16` (with a 16-step gap reserved for partitions of `sda`).

You will rarely care about major/minor in 2026 because `udev` creates the device nodes for you, but the numbers are how the kernel internally identifies "this read goes to that driver."

### 1.2 Block versus character

Run `ls -l /dev/sda /dev/null`:

```
$ ls -l /dev/sda /dev/null
brw-rw---- 1 root disk 8, 0 May 14 09:01 /dev/sda
crw-rw-rw- 1 root root 1, 3 May 14 09:01 /dev/null
```

The first character of the permissions column is `b` for `sda` and `c` for `null`. That is the **block-vs-character distinction**:

- A **block device** delivers fixed-size random-access pages, buffered by the page cache. The unit is the **block** (usually 4 KiB). Reading byte 0 of a block device reads block 0, fills the cache, and returns the byte; reading byte 1 returns the cached version, so cost is amortised. Block devices have **seek**: you can read block 1000 directly without reading 0-999 first. Examples: `/dev/sda`, `/dev/nvme0n1`, `/dev/loop0`, `/dev/mapper/cryptroot`.
- A **character device** delivers unbuffered byte streams. The unit is the byte; there is no random access. Read returns whatever bytes the driver has available now; if there are no bytes, read blocks. Examples: `/dev/tty` (the terminal), `/dev/null` (the bit bucket), `/dev/random` and `/dev/urandom` (the kernel CSPRNG), serial ports, the `kvm` device, the `fb0` framebuffer.

A filesystem sits on a **block device**, never on a character device. This is why `mkfs.ext4 /dev/null` is a category error.

The numbers after the device type in the `ls -l` column (`8, 0` and `1, 3`) are the major and minor numbers; for character devices they are reported in the same place, but they mean different things (major 1 is the "memory" driver: minor 3 is `/dev/null`, minor 5 is `/dev/zero`, minor 8 is `/dev/random`).

Reference: kernel `Documentation/admin-guide/devices.txt` (the canonical allocation table); `mknod(1)`, `mknod(2)` (the syscall and command that create device nodes — almost never invoked directly any more because `udev` does it for you).

---

## 2. Listing block devices: `lsblk`, `blkid`, `findmnt`

Three commands, three views. Run all three.

### 2.1 `lsblk` — the tree view

```bash
lsblk                          # ASCII tree, default columns
lsblk -f                       # adds FSTYPE, LABEL, UUID, FSAVAIL, FSUSE%
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS,UUID
lsblk -p                       # full paths (/dev/sda1 not sda1)
lsblk -l                       # list (not tree)
lsblk -S                       # SCSI hosts only
lsblk -n                       # no header (scripting)
```

The `-f` form is the workhorse:

```
$ lsblk -f
NAME        FSTYPE      LABEL UUID                                 MOUNTPOINTS
nvme0n1
├─nvme0n1p1 vfat        ESP   1234-5678                            /boot/efi
├─nvme0n1p2 ext4        boot  abcd-...-1234                        /boot
└─nvme0n1p3 crypto_LUKS       efgh-...-5678
  └─cryptroot ext4      root  ijkl-...-9012                        /
```

Every column is labelled. **UUID** is the filesystem's UUID (set at `mkfs` time, persists across reboots, survives device renumbering — `sda` becoming `sdb` because you added another disk). This is why `/etc/fstab` uses `UUID=...` instead of `/dev/sda1`: a UUID is stable, a device name is not.

### 2.2 `blkid` — the UUID and label printer

```bash
sudo blkid                     # all block devices
sudo blkid /dev/sda1           # one
sudo blkid -o full /dev/sda1   # full output
sudo blkid -s UUID -o value /dev/sda1  # just the UUID, no labels
```

`blkid` reads the filesystem superblock to learn the UUID, label, and type. It is the canonical way to look up a UUID for an `/etc/fstab` entry.

### 2.3 `findmnt` — the mount-table view

```bash
findmnt                        # all current mounts in a tree
findmnt /                      # just the root mount
findmnt -t ext4                # only ext4 mounts
findmnt --fstab                # what is configured in /etc/fstab
findmnt --verify               # check /etc/fstab for errors before reboot
```

`findmnt --verify` is the command you run after editing `/etc/fstab` and before rebooting. It catches typos, missing devices, and conflicting options.

### 2.4 A small POSIX script to summarise

Reasonably portable; works on Ubuntu and Fedora.

```sh
#!/bin/sh
# inventory.sh — print a one-line summary of every block device.
# Bashism-free; runs on /bin/sh.
set -eu

lsblk -ndo NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS | while IFS= read -r line; do
    printf '%s\n' "$line"
done
```

`lsblk -ndo NAME,SIZE,TYPE,FSTYPE,MOUNTPOINTS`: `-n` no header, `-d` no partitions (top-level only), `-o ...` columns. Useful in dashboards.

---

## 3. Partition tables: MBR versus GPT

A block device is a flat array of blocks (usually 512 B or 4 KiB each). The **partition table** is a small region at the start (and, for GPT, also at the end) that says "blocks 2048 through 1052671 are partition 1, of type Linux filesystem, named ROOT." Without a partition table, you can still put a filesystem on the whole device — `mkfs.ext4 /dev/sdb` works — but that costs flexibility.

Two formats exist:

### 3.1 MBR — Master Boot Record (1983)

The legacy partition table. Lives in the first 512 bytes of the disk (the same 512 bytes that contain the boot loader on BIOS systems). Constraints:

- **32-bit LBA**. The maximum addressable block is 2^32 − 1, so the maximum partition size is about **2.2 TB** on a 512-B-block disk. Beyond that you cannot describe the partition with MBR.
- **4 primary partitions maximum**. One of them can be marked "extended", which contains "logical" partitions in a linked list, but the design is awkward and modern installers prefer GPT.
- **No redundancy.** A single corrupted sector at LBA 0 wipes the partition table.
- **No UUIDs.** Partitions have a 1-byte "type" field but no per-partition identifier.

You will still see MBR on USB sticks, on legacy hardware, and on virtual machines from old templates. Recognise the shape; do not use it for new installations.

### 3.2 GPT — GUID Partition Table (2000, EFI spec)

The modern partition table. Lives in the first **34 sectors** (LBA 0-33) and is mirrored at the end of the disk:

- **64-bit LBA**. The 2 TB ceiling is gone; current ceiling is in the exabytes.
- **128 partition entries by default**, expandable. No artificial primary/extended distinction.
- **Redundant primary and backup headers**. A corrupted GPT can be repaired from the backup automatically by `gdisk` or `parted`.
- **Every partition has a 128-bit GUID** (the `PARTUUID`) **and a 36-byte name**.
- **The first sector (LBA 0) holds a "protective MBR"** — a single dummy partition that says "this disk is GPT" so legacy tools do not misinterpret it as empty.

GPT is the default on every UEFI system (almost everything since ~2012). Use it.

### 3.3 The UEFI implication: ESP

On UEFI systems, the firmware reads the GPT, finds the partition typed `EFI System Partition` (commonly "ESP"), and looks for the boot loader inside it. The ESP is a small (typically 256 MB to 1 GB) FAT32-formatted partition mounted at `/boot/efi`. You did not "choose" to have an ESP; the installer made one because UEFI demands it.

You see it in `lsblk -f`:

```
nvme0n1p1 vfat ESP 1234-5678 /boot/efi
```

Do not format it with anything other than `vfat`. Do not delete it. Do not change its UUID. The firmware looks for it by GPT partition type GUID (`c12a7328-f81f-11d2-ba4b-00a0c93ec93b`), not by name, so if you must rebuild it: `mkfs.vfat -F 32 /dev/nvme0n1p1` and re-install the boot loader.

---

## 4. Partition tools: `fdisk`, `parted`, `sfdisk`, `gdisk`

Four tools that do the same job in different styles. All four are free; all four are in every distro.

### 4.1 `fdisk` — interactive, supports MBR and GPT

`fdisk` is the BSD-style interactive editor. Since `util-linux` 2.23 it supports GPT (the older Linux `fdisk` was MBR-only; people still occasionally write that, but it is no longer true). The session is line-oriented:

```
$ sudo fdisk /dev/sdb

Welcome to fdisk (util-linux 2.39.3).
Changes will remain in memory only, until you decide to write them.
Be careful before using the write command.

Command (m for help): m

Help:

  GPT
   M   enter protective/hybrid MBR

  Generic
   d   delete a partition
   F   list free unpartitioned space
   l   list known partition types
   n   add a new partition
   p   print the partition table
   t   change a partition type
   v   verify the partition table
   i   print information about a partition

  Save & Exit
   w   write table to disk and exit
   q   quit without saving changes

  Create a new label
   g   create a new empty GPT partition table
   G   create a new empty SGI (IRIX) partition table
   o   create a new empty MBR partition table
   s   create a new empty Sun partition table

Command (m for help):
```

The canonical interactive sequence:

1. `g` — create a new GPT label (or `o` for MBR).
2. `n` — new partition; accept defaults for partition number, start sector (the tool aligns to 1 MiB by default), and choose a size (`+50G`, `+512M`).
3. `t` — change type (optional; defaults to "Linux filesystem"). Run `l` to see the list.
4. `p` — print the table to check.
5. `w` — write and exit. **Nothing is committed until you run `w`.** Quitting with `q` discards.

Read `man 8 fdisk`. The "DESCRIPTION" section explains the alignment rules and why `fdisk` defaults to 2048-sector (1 MiB) boundaries.

### 4.2 `parted` — scriptable, GNU

`parted` is the GNU partition editor. Same job, scriptable. The interactive form:

```bash
sudo parted /dev/sdb
(parted) print
(parted) mklabel gpt
(parted) mkpart primary ext4 1MiB 50%
(parted) mkpart primary ext4 50% 100%
(parted) print
(parted) quit
```

The one-shot form (preferred in scripts):

```bash
sudo parted --script /dev/sdb \
    mklabel gpt \
    mkpart primary ext4 1MiB 50% \
    mkpart primary ext4 50% 100% \
    print
```

`parted` accepts sizes in absolute units (`100MiB`, `1GiB`) or percentages of the device. The latter is convenient and self-aligning.

### 4.3 `sfdisk` — script-only, fast, backupable

`sfdisk` is `fdisk`'s scripted cousin. The killer feature is **backup and restore**:

```bash
# Backup the partition table to a text file
sudo sfdisk --dump /dev/sdb > sdb-partitions.txt

# Restore from the text file (after a wipe, say)
sudo sfdisk /dev/sdb < sdb-partitions.txt
```

Read `man 8 sfdisk` for the input format. This is how you reproduce a partition layout across many identical disks in a fleet.

### 4.4 `gdisk` — GPT-specialised

`gdisk` is `fdisk` for GPT only. Smaller, simpler interface, every GPT feature exposed (including changing the partition GUID, the disk GUID, the partition name). When you need to do something GPT-specific that `fdisk` does not expose, `gdisk` is the tool.

```bash
sudo gdisk /dev/sdb
```

Read `man 8 gdisk`. The maintainer (Rod Smith) publishes excellent prose: <https://www.rodsbooks.com/gdisk/>.

### 4.5 Which one when?

| Use case | Tool |
|----------|------|
| Quick partitioning interactively | `fdisk` |
| Scripted partitioning in a deployment pipeline | `parted --script` or `sfdisk` |
| Backup/restore a partition table | `sfdisk --dump` / `sfdisk` |
| GPT-specific operations (rename, recolour, repair) | `gdisk` |
| Resize an existing partition (rare; usually grow a filesystem with LVM instead) | `parted` (read-only); manually with `sfdisk`; consider `growpart` |

The rule that matters: **read the man page section before you write to a device.** A wrong sector start can corrupt the filesystem at the previous partition.

---

## 5. The partition is not the filesystem

A partition is a region of a block device. A filesystem is the on-disk format that lives inside the partition. **These are different things and you have to do both.**

Sequence on a fresh disk:

1. **Partition.** `parted /dev/sdb mklabel gpt`; `parted /dev/sdb mkpart primary ext4 1MiB 100%`. Now you have `/dev/sdb1` (a partition; a region of bytes).
2. **Format.** `mkfs.ext4 -L data /dev/sdb1`. Now `/dev/sdb1` contains an ext4 filesystem with a label of "data". Lecture 2 covers `mkfs`.
3. **Mount.** `mount /dev/sdb1 /mnt/data`. Now you can `cd /mnt/data` and create files.
4. **Persist.** Edit `/etc/fstab` to make the mount happen at boot.

If you stop at step 1, the partition has no filesystem and is useless. If you stop at step 2, the filesystem is not visible. If you stop at step 3, the mount disappears on reboot.

Each step has its own commands, its own man page, its own failure modes. The next two lectures cover steps 2 and 3 in detail.

---

## 6. Mounting and unmounting

The kernel exposes a filesystem at a directory via the `mount` syscall (`mount(2)`). The userspace command `mount(8)` is the friendly wrapper.

### 6.1 The simplest mount

```bash
sudo mkdir -p /mnt/data
sudo mount /dev/sdb1 /mnt/data
ls /mnt/data
```

Three lines. The first creates the mount point (a directory; the directory has to exist before you mount onto it). The second mounts the filesystem. The third confirms.

The mount is **non-persistent**: rebooting unmounts everything not in `/etc/fstab`. To persist, add a line to `/etc/fstab` (covered in lecture 2).

### 6.2 Unmounting

```bash
sudo umount /mnt/data
# or by device:
sudo umount /dev/sdb1
```

If `umount` says "target is busy", **do not** unmount with `-f` as your first move. Find what is using it:

```bash
sudo lsof +D /mnt/data        # which processes have files open under /mnt/data
sudo fuser -vm /mnt/data      # alternative, more compact
```

Close those, then `umount`. If you cannot close them and you must unmount: `umount -l /mnt/data` (lazy unmount) detaches the filesystem from the tree but waits for the last close before fully releasing it.

`umount -f` is for the case where the filesystem is on a removed device (an USB stick that was yanked) and the kernel needs to be told to give up. It is **not** for "I cannot find what is using this."

### 6.3 The current mount table

```bash
mount                          # human-readable list of all mounts
cat /proc/mounts               # the canonical kernel view (a symlink to /proc/self/mounts)
findmnt                        # tree view
```

`/proc/mounts` is what the kernel **actually has mounted right now**. `/etc/mtab` used to be a separate file that `mount(8)` maintained; on modern systems it is a symlink to `/proc/mounts` and the two are the same.

### 6.4 Bind mounts

A bind mount makes one directory appear at another path:

```bash
sudo mkdir -p /mnt/foo /mnt/bar
sudo mount --bind /mnt/foo /mnt/bar
# Now /mnt/foo and /mnt/bar are the same directory.
```

Used heavily by containers (Docker uses bind mounts under the hood to give a container access to a host directory). Also useful for chroots, jails, and "I want this directory to also appear over there."

### 6.5 Loop mounts

A **loop device** presents a file as a block device. The exercises use loop devices to simulate fresh disks without touching real hardware:

```bash
# Create a 1 GiB file, format as ext4, mount.
truncate -s 1G /tmp/disk1.img
sudo losetup -fP /tmp/disk1.img       # find next free loop device, set up, scan partitions
sudo losetup -l                       # list active loops
# Suppose losetup picked /dev/loop0:
sudo mkfs.ext4 /dev/loop0
sudo mkdir -p /mnt/loop0
sudo mount /dev/loop0 /mnt/loop0

# Clean up:
sudo umount /mnt/loop0
sudo losetup -d /dev/loop0
rm /tmp/disk1.img
```

`losetup -fP` finds the first free loop device (`-f`) and rescans the file for a partition table (`-P`). The `-P` is important if your file contains a partition table — without it the partitions inside the file are not exposed as `/dev/loop0p1` etc.

The exercise `setup-loopback-disks.sh` does this for three disks at once so you can practise LVM with no risk.

---

## 7. A worked walk: from a blank loopback to a mounted ext4

The exercise that follows in `exercises/exercise-01-partition-format-mount.md` walks the full sequence. Here is the condensed version, with commentary, so you have one place to read the whole flow.

```bash
# Bash Yellow: this writes to a block device. We use a loopback file so the
# blast radius is one tmp file, not a real disk.

# 1. Create a 1 GiB sparse file.
truncate -s 1G /tmp/disk1.img

# 2. Set it up as a loopback block device.
LOOP=$(sudo losetup -fP --show /tmp/disk1.img)
echo "Loopback at $LOOP"
# e.g. LOOP=/dev/loop0

# 3. Partition with GPT, one partition spanning the whole device.
sudo parted --script "$LOOP" \
    mklabel gpt \
    mkpart primary ext4 1MiB 100%

# 4. Re-scan to make the kernel notice the new partition.
sudo partprobe "$LOOP"

# 5. Format the partition as ext4 with a label.
sudo mkfs.ext4 -L week08-disk1 "${LOOP}p1"

# 6. Get the UUID for /etc/fstab.
UUID=$(sudo blkid -s UUID -o value "${LOOP}p1")
echo "UUID is $UUID"

# 7. Mount.
sudo mkdir -p /mnt/week08-disk1
sudo mount "${LOOP}p1" /mnt/week08-disk1

# 8. Verify.
df -h /mnt/week08-disk1
ls /mnt/week08-disk1     # only lost+found will be there

# 9. Use it.
sudo touch /mnt/week08-disk1/hello.txt
echo "It works." | sudo tee /mnt/week08-disk1/hello.txt

# 10. Clean up.
sudo umount /mnt/week08-disk1
sudo losetup -d "$LOOP"
rm /tmp/disk1.img
sudo rmdir /mnt/week08-disk1
```

Ten steps, every one of which corresponds to a man page (`truncate(1)`, `losetup(8)`, `parted(8)`, `partprobe(8)`, `mkfs.ext4(8)`, `blkid(8)`, `mount(8)`, `df(1)`, `umount(8)`). Read them all once; refer back to them for life.

The two non-obvious bits:

- **`partprobe`**. After you write a partition table, the kernel does not automatically notice. `partprobe DEV` tells it to re-read the table. Some tools (including modern `parted`) do this for you; making it explicit is safer.
- **The `p1` suffix on a loopback partition.** Real disks use `/dev/sda1`; loopback partitions use `/dev/loop0p1` (with a `p`). The kernel needs to be told this with `losetup -P` (or `partprobe`); without it the partitions inside the loopback file are invisible.

---

## 8. When to use whole-disk filesystems (no partition table)

You **can** put a filesystem directly on a block device with no partition table:

```bash
sudo mkfs.ext4 /dev/sdb         # not /dev/sdb1 — the whole device
```

When is this appropriate?

- **Inside an LVM logical volume**. The LV is already a slice of a VG, which is a slice of a PV (which is itself usually on a partition). Adding another partition inside the LV is pointless.
- **For a single-purpose data disk** (e.g. a backup target, a swap file's container, a single huge dataset) where you will never want to repartition.
- **For loopback files** when the file is a single filesystem (not a multi-partition disk image).

When is it inappropriate?

- **On a boot device.** The boot loader expects a partition table.
- **On a disk you might want to slice later.** Once a filesystem is on the whole device you cannot add a partition without destroying the filesystem.
- **On a disk presented to other operating systems.** Windows refuses to recognise a disk with no partition table.

The rule: **partition by default**. Use whole-disk only when you have a reason.

---

## 9. Bash Yellow: things that go wrong

The single most common mistake of the week is **writing to the wrong device**. The difference between `/dev/sda` (your root) and `/dev/sdb` (the new disk) is one character. The following two commands are both legal:

```bash
sudo mkfs.ext4 /dev/sda1       # destroys your root filesystem
sudo mkfs.ext4 /dev/sdb1       # formats the new disk
```

Habits to prevent the catastrophe:

- **Always run `lsblk` first**, look at the SIZE column, look at the MOUNTPOINTS column. A device that is mounted to `/` is **not** the one you want to format.
- **Confirm the device is unmounted** with `mount | grep "^${DEV}"`. If anything matches, do not write to it.
- **Run `wipefs --no-act` first** to confirm what is there. `wipefs --no-act /dev/sdb` shows you the signatures it would erase without erasing.
- **Practise on a loopback file**. The exercise uses `truncate -s 1G /tmp/disk1.img` so a mistake costs one tmp file.

The second most common mistake is **forgetting to `umount` before `losetup -d`**. The loopback device is held open by the mount; tearing it down with an active mount produces a "resource busy" error and, on older kernels, can leave the loop device in a half-destroyed state.

The third most common mistake is **editing `/etc/fstab` without backing it up** and then editing it incorrectly. The system will refuse to boot, drop you into emergency mode, and you will spend a tense ten minutes recovering. Always:

```bash
sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)
# ...edit...
sudo findmnt --verify          # sanity-check the syntax
sudo mount -a                  # test all new mounts
# only then reboot
```

The cardinal rule of storage work: **read the device path twice before you write to it**.

---

## Summary

- A **block device** is a kernel-managed view of a storage unit that delivers fixed-size random-access pages, buffered by the page cache. A **character device** is an unbuffered byte stream. Filesystems sit on block devices.
- `lsblk` is the tree view; `blkid` is the UUID lookup; `findmnt` is the mount-table view. Run all three when you are getting your bearings.
- **GPT** is the modern partition table: 64-bit LBA, 128 entries, redundant headers, every partition has a UUID. **MBR** is the legacy fallback. Use GPT.
- `fdisk` is interactive; `parted --script` is the scripted GNU tool; `sfdisk` is for backup/restore; `gdisk` is for GPT-specific work. All four edit the same on-disk structure.
- A **partition** is a region of bytes. A **filesystem** is the on-disk format inside the partition. A **mount** is the exposure of the filesystem at a directory. You have to do all three; each has its own command.
- `mount(8)` is the wrapper around the `mount(2)` syscall. `/proc/mounts` is the live mount table.
- **Loopback devices** (`losetup -fP /path/file.img`) present a file as a block device. The whole week's exercises use loopbacks to avoid touching real hardware.
- **Always read the device path twice.** The difference between formatting a new disk and destroying your root filesystem is one character.

Reference: `man 8 mount`, `man 5 fstab`, `man 8 lsblk`, `man 8 fdisk`, `man 8 parted`, `man 8 sfdisk`, `man 8 gdisk`, `man 8 losetup`, `man 1 blkid`, `man 8 findmnt`. The kernel admin-guide at <https://www.kernel.org/doc/html/latest/admin-guide/> has the authoritative deep-dive references.

Next lecture: filesystem choice (ext4 vs xfs vs btrfs), `mkfs.*` options, the `/etc/fstab` format, and the mount options that actually matter.
