# Week 8 Quiz — Final exam

Ten questions covering the whole of C14 · Crunch Linux's Week 8 plus a few synthesising questions that touch the prior weeks. **This is the final week's quiz**; treat it as a closed-book exam. Answers and explanations follow the questions; resist looking until you have written your answers.

---

## Questions

### 1.

You run `ls -l /dev/sda /dev/random` and see:

```
brw-rw---- 1 root disk 8, 0 ... /dev/sda
crw-rw-rw- 1 root root 1, 8 ... /dev/random
```

What does the `b` in `brw-rw----` mean, and what does it imply about how the kernel treats reads of `/dev/sda` versus reads of `/dev/random`?

A. `b` means "binary"; the kernel reads `/dev/sda` as binary and `/dev/random` as text.
B. `b` means "block"; reads of `/dev/sda` are buffered by the page cache and are random-access in fixed-size blocks. Reads of `/dev/random` (which is a character device) are unbuffered byte streams.
C. `b` means "boot"; `/dev/sda` is the boot device. The page cache is not involved.
D. `b` means "blockable"; reads of `/dev/sda` may block, reads of `/dev/random` cannot.

---

### 2.

You run `lsblk -f` and see:

```
nvme0n1
├─nvme0n1p1 vfat        ESP   1234-5678  /boot/efi
├─nvme0n1p2 ext4        boot  abcd-...   /boot
└─nvme0n1p3 crypto_LUKS       efgh-...
  └─cryptroot ext4      root  ijkl-...   /
```

What does the indented `cryptroot` row represent?

A. A second filesystem on the same partition (impossible).
B. A device-mapper device (specifically, a LUKS-encrypted block device) that has been created from `nvme0n1p3`. The filesystem (ext4, mounted as `/`) lives on the dm-device, not on the raw partition.
C. A symbolic link to `/etc/cryptroot` configuration.
D. A subvolume of the ext4 filesystem.

---

### 3.

Which of the following is **the** reason GPT is preferred over MBR for new installations in 2026?

A. GPT supports compression of partition metadata.
B. GPT permits up to 128 partitions, supports 64-bit LBA (no 2 TiB ceiling), has redundant primary and backup headers, and every partition has a UUID. MBR's 4-primary-partition limit and 2 TiB ceiling are no longer acceptable.
C. GPT is required by all Linux filesystems.
D. GPT has hardware acceleration in modern CPUs.

---

### 4.

You add this line to `/etc/fstab`:

```
UUID=abcd-1234  /var/data  ext4  defaults,noatime,nodiratime,errors=remount-ro  0  2
```

What does the **last `2`** mean, and is it the right choice for an ext4 data filesystem?

A. The number of times the filesystem has been mounted; informational only.
B. The `pass` field, used by `systemd-fsck@.service` at boot to decide order. `2` means "check after the root filesystem"; for a non-root ext4 data mount this is correct. `0` would mean "never check at boot"; `1` is for the root filesystem only.
C. The number of seconds to wait before mounting.
D. The number of filesystems to mount in parallel.

---

### 5.

You run `free -h` on a server with 16 GiB RAM and see:

```
              total        used        free      shared  buff/cache   available
Mem:           15Gi       7.2Gi       1.1Gi       400Mi       7.0Gi        10Gi
```

The application owner panics: "memory is 7.2 / 15 = 48 % used and only 1.1 GiB free; we are about to swap." Which response is correct?

A. They are right; immediately add more RAM.
B. The `buff/cache` column is **also** RAM in use, so the system is essentially full and should be rebooted.
C. The `available` column (10 GiB) is the number that matters; the 7 GiB of `buff/cache` is reclaimable on demand. The kernel is using free RAM as page cache to make file reads faster; that is not memory pressure.
D. The `shared` column indicates a memory leak.

---

### 6.

You run a `dd if=/dev/zero of=/tmp/big bs=1M count=5000` on a fresh, otherwise idle Linux server. The transfer rate starts at 2.4 GB/s, then suddenly drops to 200 MB/s and stays there. What happened, and what `sysctl` knob controls when the transition happens?

A. The disk's SLC cache filled up.
B. The kernel's writeback throttling kicked in: dirty pages reached `vm.dirty_ratio` (default 20 % of RAM), and the writing process is now forced to wait for writeback before each new write. The initial 2.4 GB/s was the RAM-to-cache bandwidth; the 200 MB/s is the actual disk bandwidth.
C. The CPU thermal-throttled.
D. The TCP congestion-control kicked in (irrelevant on a local `dd`).

---

### 7.

You inherit a server with this `/etc/fstab` entry:

```
UUID=...  /var/log  ext4  defaults,nobarrier  0  2
```

Why is `nobarrier` a red flag, and what specifically can go wrong?

A. `nobarrier` is a typo; the kernel ignores unknown options.
B. `nobarrier` disables write barriers, meaning the kernel does not flush the disk's volatile write cache on `fsync`. On power loss, data written but not yet persisted past the disk's cache is lost — and the filesystem journal can be inconsistent because journal commits also rely on barriers. On non-battery-backed disks (i.e., almost all consumer hardware), this is a real data-loss vulnerability.
C. `nobarrier` makes the filesystem read-only.
D. `nobarrier` is an old name for `noatime` and the entry is functionally fine.

---

### 8.

You want to extend a mounted LVM logical volume `/dev/data/web` by 50 GiB and resize the ext4 filesystem on top **without unmounting**. Which command does both in one step?

A. `lvextend -L +50G /dev/data/web && resize2fs /dev/data/web`
B. `lvextend -L +50G -r /dev/data/web` — the `-r` flag automatically runs `resize2fs` (for ext4) / `xfs_growfs` (for xfs) / `btrfs filesystem resize` (for btrfs) after the LV is extended.
C. `lvresize +50G /dev/data/web`
D. You cannot extend a mounted filesystem.

---

### 9.

You run `fio` with a job file containing `direct=1`, `bs=4k`, `rw=randread`, `iodepth=32`, `runtime=30`. The output reports `IOPS=98.7k, BW=386MiB/s, clat 99.99th=2345 usec`. What does the **`clat 99.99th=2345 usec`** mean, and why is it more useful than the mean for predicting end-user-visible performance?

A. The 99.99th-percentile completion latency is 2345 microseconds. That is the **tail**: 1 in 10,000 IOs took at least this long. The mean is dominated by the fast common case; real users hit the tail surprisingly often (especially in aggregate over many IOs per request), so the tail matters more for predicting "the slow query that the user complained about."
B. The 99.99 % of IOs completed within 2345 microseconds (so the mean is roughly the same).
C. The total runtime was 2345 microseconds.
D. The completion latency includes the disk's seek time, which is rare to measure.

---

### 10.

The single most important sentence about `fsck` from Week 8 is:

A. Always run `fsck` once a week.
B. **Never run `fsck` on a mounted filesystem.** The kernel and `fsck` will both write to the filesystem from different cached views, and the result is unrecoverable corruption. `fsck` runs on unmounted devices; at boot, before mount; or, for btrfs, via `btrfs scrub` which is explicitly online-safe.
C. `fsck` is only needed on ext2; ext3 and ext4 have journals.
D. `fsck` runs automatically every night via cron.

---

## Answer key

| Q | Answer | One-sentence explanation |
|---|--------|--------------------------|
| 1 | B | `b` is the block-device marker in `ls -l`. Block devices are page-cache-buffered and random-access; character devices are unbuffered byte streams. |
| 2 | B | The indented row in `lsblk -f` shows a device-mapper child of the partition above it. `cryptroot` is a LUKS-encrypted block device; the filesystem lives on it, not on the raw partition. |
| 3 | B | GPT removes MBR's 4-primary-partition limit and 2 TiB ceiling, has redundant headers, and gives every partition a UUID. The reason for the preference is the combination, not any single feature. |
| 4 | B | `pass` is `0` (never `fsck` at boot), `1` (root, first), or `2` (non-root, after root). For an ext4 data mount, `2` is correct. For xfs or btrfs, `0` is correct. |
| 5 | C | `MemAvailable` (or `available` in `free`) is the right number. `buff/cache` looks like used memory but is reclaimable; the kernel uses free RAM as page cache. See <https://www.linuxatemyram.com/>. |
| 6 | B | The fast→slow `dd` pattern is dirty-page throttling at `vm.dirty_ratio` (default 20 %). The early bandwidth is RAM bandwidth; the late is disk bandwidth. Controlled by `vm.dirty_ratio` and `vm.dirty_background_ratio`. |
| 7 | B | `nobarrier` disables write barriers; on power loss, the disk's volatile cache contents are lost, and the filesystem journal can be inconsistent. Only safe on battery-backed-cache hardware. Modern kernels have phased out the option; older systems still have it as a foot-gun. |
| 8 | B | `lvextend -r` runs the appropriate filesystem-grow tool after extending the LV. The whole operation is online; the mount is not interrupted. The two-step form in A also works but is more typing and you can forget the second step. |
| 9 | A | The 99.99th-percentile latency is the tail: 1-in-10,000 IOs took at least that long. A single user request often issues hundreds of IOs; the cumulative chance of hitting the tail is non-trivial. The mean hides this. |
| 10 | B | Never `fsck` a mounted filesystem. The dual-writer corruption is unrecoverable. `fsck` runs on unmounted devices; at boot, before mount; or, for btrfs specifically, via `btrfs scrub`. |

---

## Grading

- **9-10 correct**: You have the material. Move to the mini-project with confidence.
- **7-8 correct**: Re-read the lecture for any question you missed before starting the mini-project.
- **5-6 correct**: Re-read both lecture 1 and lecture 3; the gap is foundational.
- **Under 5**: This is the final week; the prior seven weeks should not have left you here. Schedule office hours with the instructor, or set aside a full day to re-read all three lectures.

The mini-project covers the practical side; the quiz covers the conceptual side. You need both to graduate the track.

---

*If you disagree with an answer, open an issue with reasoning. Errata welcome.*
