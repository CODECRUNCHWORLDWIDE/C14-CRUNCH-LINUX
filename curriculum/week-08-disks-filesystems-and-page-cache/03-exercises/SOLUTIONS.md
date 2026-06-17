# Exercises — Solutions

Worked solutions and answers to the reflection questions for all four exercises. Read these **after** you have attempted the exercises; reading them first defeats the purpose.

---

## Exercise 1 — Partition, format, mount, persist

The full sequence (assuming `setup-loopback-disks.sh` has been run and `$DISK1` is set):

```bash
# 1. Pre-flight: inspect.
sudo wipefs --no-act "$DISK1"
mount | grep "$DISK1" || echo "Nothing mounted from $DISK1"

# 2. Wipe any previous signatures.
sudo wipefs -a "$DISK1"

# 3. Partition with GPT, one partition.
sudo parted --script "$DISK1" mklabel gpt mkpart primary ext4 1MiB 100%
sudo partprobe "$DISK1"

# 4. Format.
sudo mkfs.ext4 -L week08-disk1 "${DISK1}p1"
UUID=$(sudo blkid -s UUID -o value "${DISK1}p1")

# 5. Mount.
sudo mkdir -p /mnt/week08-disk1
sudo mount "${DISK1}p1" /mnt/week08-disk1

# 6. Persist.
sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)
echo "UUID=${UUID}  /mnt/week08-disk1  ext4  defaults,noatime,nodiratime,errors=remount-ro  0  2" \
    | sudo tee -a /etc/fstab
sudo findmnt --verify
sudo umount /mnt/week08-disk1
sudo mount /mnt/week08-disk1     # uses /etc/fstab

# Clean up at the end.
sudo umount /mnt/week08-disk1
sudo rmdir /mnt/week08-disk1
LATEST_BACKUP=$(ls -t /etc/fstab.bak.* | head -1)
sudo cp "$LATEST_BACKUP" /etc/fstab
sudo ./teardown-loopback-disks.sh
```

### Reflection answers

1. **Why `UUID=` and not `/dev/loop20p1`?** Device names are kernel-assigned at boot and can change. Add a USB stick before next boot and `/dev/sdb` may now be the USB stick, while your data disk has become `/dev/sdc`. A UUID is baked into the filesystem at `mkfs` time and is stable across reboots, hardware changes, and even kernel upgrades. The fstab entry refers to "the filesystem with this UUID, wherever it appears" rather than "whatever happens to be at this device path."

2. **`pass=2` means**: at boot, after the root filesystem (which is `pass=1`), `systemd-fsck@.service` runs `fsck` on this filesystem before mounting. `pass=1` means "this is the root filesystem; check first"; only one filesystem should be `pass=1`. `pass=0` means "never `fsck` at boot" — appropriate for non-ext-family filesystems (xfs, btrfs) and for filesystems where boot speed matters more than crash recovery.

3. **`defaults,noatime,nodiratime`**: `defaults` is shorthand for `rw,suid,dev,exec,auto,nouser,async`. `noatime` disables the access-time update on read, which is a significant write reduction on read-heavy workloads. `nodiratime` is the same for directories and is implied by `noatime`; listing it is redundant but harmless.

4. **`errors=remount-ro`**: on a filesystem error (corrupt inode, journal failure, etc.), instead of the kernel panicking and crashing the system, remount the filesystem read-only and continue. This keeps the system up — you can SSH in, investigate, dump the kernel log, take a backup — while preventing further writes that might worsen the corruption. The Ubuntu installer's default.

5. **`wipefs --no-act` would have shown the existing partition / filesystem signatures.** If you saw `ext4` or `gpt` reported by `wipefs` on a device you thought was blank, you would have known to investigate before formatting. The "no-act" form is the safe way to inspect.

---

## Exercise 2 — The page cache, cold versus warm

The exercise is mostly observation; the "solution" is "did you see the numbers move as predicted?" Sample numbers from a modest SSD-backed laptop:

| Phase | Time for 500 MB read | Bandwidth |
|-------|----------------------|-----------|
| Cold (after drop_caches) | 2.4 s | 208 MB/s |
| Warm (back-to-back)      | 0.18 s | 2.8 GB/s |
| After drop_caches again  | 2.6 s | 192 MB/s |
| After `fadvise(DONTNEED)` | 2.5 s | 200 MB/s |

The exact numbers depend on your hardware; the **ratio** is what to confirm. Warm/cold should be 5-20×.

### Reflection answers

1. **Why so much faster warm?** The disk is not involved on a warm read. The kernel copies bytes from the page cache (which lives in RAM) to the user buffer. The bandwidth you measure is RAM bandwidth (~3-20 GB/s on modern systems) rather than disk bandwidth (200-3000 MB/s).

2. **`MemAvailable` vs `MemFree`**: `MemFree` is RAM allocated to nothing. `MemAvailable` is the estimated RAM that could be made available to a new application **without swapping** — it includes reclaimable cache. On a system with 16 GB RAM, 6 GB used by processes, 9 GB in page cache, and 1 GB truly free: `MemFree=1G`, `MemAvailable=~10G`. The 9 GB of cache will be reclaimed if a new process needs it.

3. **Why not use `drop_caches` in production?** It is a destructive operation against the cache. Every program that was relying on cached file pages must re-read them from disk, causing a wave of slow IO across the system. Real production workloads have hot files that benefit enormously from caching; flushing the cache slows the next minute of operation across every process. Use only in benchmarks where you specifically want a cold cache.

4. **`posix_fadvise(POSIX_FADV_DONTNEED)` use case**: a backup script that reads every file once. Without the hint, the backup fills the page cache with files that will not be re-read, evicting the application's hot data. With `POSIX_FADV_DONTNEED` after each file's `read`, the kernel knows the backup will not re-read and keeps the application's data cached.

5. **Repeating-the-workload benchmark is wrong** because the second through fifth runs are reading from cache, not from the device. The mean is dominated by warm reads and overstates real-world performance. Fix: drop caches before each run, or use `O_DIRECT`, or design the test to read different data each time.

---

## Exercise 3 — LVM: create, extend, snapshot

The full command sequence:

```bash
# Setup.
sudo ./setup-loopback-disks.sh
export DISK1=$(sudo losetup -j /tmp/week08-disk1.img | head -1 | cut -d: -f1)
export DISK2=$(sudo losetup -j /tmp/week08-disk2.img | head -1 | cut -d: -f1)
export DISK3=$(sudo losetup -j /tmp/week08-disk3.img | head -1 | cut -d: -f1)

# Create PVs (DISK3 done in part 6.2).
sudo pvcreate "$DISK1" "$DISK2"

# Create VG with two PVs.
sudo vgcreate week08 "$DISK1" "$DISK2"

# Create LV.
sudo lvcreate -L 500M -n web week08

# Format and mount.
sudo mkfs.ext4 -L week08-web /dev/mapper/week08-web
sudo mkdir -p /mnt/week08-lv
sudo mount /dev/mapper/week08-web /mnt/week08-lv

# Write data.
sudo bash -c 'for i in $(seq 1 20); do
    dd if=/dev/urandom of=/mnt/week08-lv/file$i bs=1M count=10 status=none
done'

# Extend within existing VG.
sudo lvextend -L +500M -r /dev/week08/web

# Add third PV and extend further.
sudo pvcreate "$DISK3"
sudo vgextend week08 "$DISK3"
sudo lvextend -L +500M -r /dev/week08/web

# Snapshot.
sudo lvcreate -L 200M -s -n web-snap /dev/week08/web

# Modify original.
sudo rm /mnt/week08-lv/file1 /mnt/week08-lv/file2 /mnt/week08-lv/file3
echo "After snapshot" | sudo tee /mnt/week08-lv/after-snapshot.txt

# Mount snapshot read-only.
sudo mkdir -p /mnt/week08-snap
sudo mount -o ro /dev/week08/web-snap /mnt/week08-snap

# Restore.
sudo cp /mnt/week08-snap/file1 /mnt/week08-snap/file2 /mnt/week08-snap/file3 /mnt/week08-lv/

# Tear down snapshot.
sudo umount /mnt/week08-snap
sudo lvremove -f /dev/week08/web-snap

# Clean up.
sudo umount /mnt/week08-lv
sudo ./teardown-loopback-disks.sh
```

### Reflection answers

1. **Why LVM?** Three concrete operations: **online extend** (grow a mounted filesystem without unmounting), **snapshot for backup** (a consistent point-in-time view of a busy filesystem), **multi-disk spanning** (an LV can be larger than any single disk because it draws from a VG of multiple PVs). A fourth: **decoupling of names from physical location** — the LV path is stable across disk swaps. None of these are possible on a raw partition.

2. **`-r` flag**: tells `lvextend` to **also resize the filesystem on top of the LV** after extending. Without `-r`, you grow the LV but the filesystem still believes it is the old size; you have to run `resize2fs` / `xfs_growfs` / `btrfs filesystem resize` manually. With `-r`, lvm does it automatically and atomically. Almost always what you want.

3. **Snapshot fills up**: the snapshot is **invalidated** and silently dropped. The `lvs` output's `Attr` column shows `X` (inactive). Any process holding the snapshot mounted gets an IO error. Backup scripts should monitor `lvs` and either grow the snapshot (`lvextend`) or alert.

4. **Shrinking is harder than growing** because shrinking requires that the filesystem first relocate any data in the to-be-removed region before the LV is truncated. ext4 can shrink only when unmounted (and only with `resize2fs SMALLER_SIZE`). **xfs cannot be shrunk at all** — there is no `xfs_shrink` and the maintainers have stated there will not be. btrfs can shrink online, but only if there is sufficient free space. Growing is "extend the bitmap and you are done"; shrinking is "find every block in the removed range and move it elsewhere first."

5. **Snapshots consume IO** over their lifetime, not at creation. Every write to the source LV must first copy the old block into the snapshot (Copy-on-Write) before the write proceeds. Long-lived snapshots on a write-heavy LV impose a real cost; this is why LVM's snapshots are for short backup windows, not for the indefinite history that btrfs / zfs / `dm-thin` provide via different mechanisms.

---

## Exercise 4 — `fio`: the four canonical jobs

The exercise produces real numbers; the "solution" is the methodology. Sample numbers from a representative NVMe SSD on a desktop:

| Job | IOPS | BW |
|-----|------|-----|
| 4k random read (direct, qd=32) | 380,000 | 1.5 GB/s |
| 4k random write (direct, qd=32) | 290,000 | 1.1 GB/s |
| 1m sequential read (direct, qd=8) | 3,300 | 3.4 GB/s |
| 1m sequential write (direct, qd=8) | 2,700 | 2.8 GB/s |
| 4k random read (no direct, cold) | similar to direct above |
| 4k random read (no direct, warm) | 5,000,000+ | 20+ GB/s |

The warm number is RAM bandwidth, not the disk.

### Reflection answers

1. **`direct=1`** opens the file with `O_DIRECT`, bypassing the page cache. Without it, you measure the **combination** of cache and device; with it, you measure the **device alone**. For "characterise the disk" benchmarks: `direct=1`. For "predict application performance" benchmarks: `direct=0`, with realistic workload sizing relative to cache.

2. **SATA SSD with 500 MB/s sequential** typically does **60-90k IOPS random 4k read**: 500 MB/s / 4 KB = 125,000 IOPS theoretical, but the random access pattern and queue depth interactions usually yield 60-90k in practice. Cheaper drives may be lower (20-40k); enterprise drives often hit the theoretical.

3. **The 99.99th percentile is much higher than the mean** because the kernel and the device both have rare slow events: garbage collection on the SSD (the firmware pauses the foreground IO to compact internal blocks), block-layer queue saturation, scheduler pre-emption of the IO-completion thread, interrupt coalescing. The mean is dominated by the fast common case; the tail captures these rare events. Real users care about the tail because a 1-in-10,000 1-second-stall on a database server is a 1-in-10,000 visibly-broken request.

4. **80,000 measured vs. 90,000 spec**: within 11 %, so within tolerance. Spec sheets are best-case (often measured on a specific kernel, specific filesystem, specific queue depth). 10-20 % below spec is normal. If you measured 30,000, you would investigate (filesystem overhead, wrong scheduler, PCIe lane count). 80,000 is healthy.

5. **A database's IO pattern is mostly 4k or 8k random read and write.** Index lookups are random reads. Write-ahead log writes are sequential small-block writes. Transaction commits are `fsync` calls. The **4k random read** job is the closest match to "the index lookups during a query"; the **4k random write** job matches "the heap writes during an update"; a database benchmark like `pgbench` or `sysbench` is a more realistic but more expensive measurement.

---

## Common errors across all exercises

- **`losetup -d` while still mounted** — first `umount`, then `losetup -d`. The script handles this; if you ran commands manually, you may need to retry the teardown.
- **`partprobe` not picking up new partition** — try `kpartx -a "$DISK1"` as an alternative, or detach and re-attach the loopback.
- **`mkfs.ext4` complaining "device is mounted"** — confirm with `mount | grep DEV` and unmount before retrying.
- **fstab edit prevents reboot** — boot single-user (`init=/bin/bash` from GRUB), `mount -o remount,rw /`, edit `/etc/fstab`, reboot. Always back up first.
- **`fio` saying "permission denied"** — the test file might be owned by root from a previous run. `sudo rm fio.testfile` and re-run.

---

*If you spot a step that does not work on your distro, open an issue.*
