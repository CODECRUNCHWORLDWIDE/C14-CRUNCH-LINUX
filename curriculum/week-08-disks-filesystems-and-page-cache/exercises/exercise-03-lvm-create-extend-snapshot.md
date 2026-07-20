# Exercise 3 — LVM: create, extend, snapshot

**Time:** 60-75 minutes.
**Goal:** Build a complete LVM stack on three loopback "disks": create three PVs, combine them into one VG, slice an LV, format and mount, write some data, extend the LV online, take a snapshot, modify the data, restore from the snapshot.
**Prerequisites:** Lecture 3 read. `setup-loopback-disks.sh` available. Root.

---

## Why this exercise

LVM is the layer between the partition and the filesystem on every Linux server in production. Three operations cover 90 % of real-world LVM work: **create**, **extend**, **snapshot**. The exercise drills all three on a safe target. After this you can grow a production filesystem online without anyone noticing.

---

## Part 1 — Set up three loopback disks

```bash
cd /path/to/curriculum/week-08-disks-filesystems-and-page-cache/exercises
sudo ./setup-loopback-disks.sh
```

The script attaches three 1 GiB loopbacks. Set variables:

```bash
export DISK1=$(sudo losetup -j /tmp/week08-disk1.img | head -1 | cut -d: -f1)
export DISK2=$(sudo losetup -j /tmp/week08-disk2.img | head -1 | cut -d: -f1)
export DISK3=$(sudo losetup -j /tmp/week08-disk3.img | head -1 | cut -d: -f1)
echo "DISK1=$DISK1 DISK2=$DISK2 DISK3=$DISK3"
lsblk "$DISK1" "$DISK2" "$DISK3"
```

You should see three 1 GiB block devices with no partitions and no filesystems.

---

## Part 2 — Create three Physical Volumes

```bash
sudo pvcreate "$DISK1" "$DISK2" "$DISK3"
sudo pvs
```

The output should show three PVs, each ~1 GiB, all with `VG` blank (not yet in a VG) and `PFree` ~1 GiB.

What `pvcreate` did: wrote a small LVM signature (about 1 MiB at the start of each device) so the kernel can identify them as LVM physical volumes. The rest of the device is now available for LVM's allocator.

Reference: `man 8 pvcreate`.

---

## Part 3 — Create a Volume Group

```bash
sudo vgcreate week08 "$DISK1" "$DISK2"
sudo vgs
sudo pvs
```

`vgcreate week08` made a VG named "week08" containing the first two PVs. (We will add `$DISK3` later to demonstrate online extension.) `vgs` should show one VG, ~2 GiB total, ~2 GiB free.

`pvs` should show `DISK1` and `DISK2` now have `VG = week08`; `DISK3` is still empty.

Reference: `man 8 vgcreate`.

---

## Part 4 — Create a Logical Volume

```bash
sudo lvcreate -L 500M -n web week08
sudo lvs
ls -la /dev/mapper/ | grep week08
```

`lvcreate -L 500M -n web week08` carved a 500 MiB slice out of the VG, named it "web". The LV appears at `/dev/mapper/week08-web` (and as a symlink `/dev/week08/web`).

Notice the LV size (500 MiB) is smaller than the VG size (2 GiB); the rest is still in the free pool, available for more LVs or for growing this one.

Reference: `man 8 lvcreate`.

---

## Part 5 — Format and mount the LV

The LV is now a block device. Format it like any other:

```bash
sudo mkfs.ext4 -L week08-web /dev/mapper/week08-web
sudo mkdir -p /mnt/week08-lv
sudo mount /dev/mapper/week08-web /mnt/week08-lv
df -h /mnt/week08-lv
```

You should see ~480 MiB usable (the difference from 500 MiB is the filesystem overhead — superblock, inode tables, reserved blocks).

Write some data:

```bash
sudo bash -c 'for i in $(seq 1 20); do
    dd if=/dev/urandom of=/mnt/week08-lv/file$i bs=1M count=10 status=none
done'

sudo ls -lh /mnt/week08-lv
df -h /mnt/week08-lv
```

20 files of 10 MiB each = 200 MiB used, ~280 MiB free. Confirm.

---

## Part 6 — Extend the LV online

You are at 200/480 MiB used. Suppose the user calls and says "we need this filesystem to be 1.5 GiB by end of week." You have two options:

1. **Extend within the VG** (there is 1.5 GiB free in the VG; we can use it).
2. **Add the third disk to the VG**, then extend.

Do both, in sequence, to practise the full procedure.

### 6.1 Extend within the existing VG

```bash
sudo vgs                                      # see free space in VG (~1.5 GiB)
sudo lvextend -L +500M -r /dev/week08/web     # +500 MiB, with -r to resize the FS
sudo lvs
df -h /mnt/week08-lv
```

The LV is now 1000 MiB and the filesystem on top has been resized **online** by `resize2fs` (which `-r` invoked automatically). `df` should show the new size. The mount was not interrupted. The files you wrote in Part 5 are intact:

```bash
sudo ls -lh /mnt/week08-lv | head
```

### 6.2 Add the third PV to the VG, extend further

```bash
sudo pvcreate "$DISK3"                        # if not already done
sudo vgextend week08 "$DISK3"
sudo vgs                                      # now ~3 GiB total

sudo lvextend -L +500M -r /dev/week08/web
sudo lvs
df -h /mnt/week08-lv
```

The LV is now 1500 MiB. The VG now spans three PVs. The filesystem still mounted, files still intact.

This is the bread and butter of LVM on production servers: a disk fills up, you add a new disk, you grow the LV, the application never notices.

Reference: `man 8 lvextend`, `man 8 vgextend`, `man 8 pvcreate`.

---

## Part 7 — Take a snapshot

Snapshots are the second killer feature. We will:

1. Take a snapshot of the LV.
2. Modify the original (delete some files, add others).
3. Mount the snapshot read-only and confirm it shows the pre-modification state.
4. Restore the original by copying from the snapshot.

### 7.1 Create the snapshot

```bash
sudo lvcreate -L 200M -s -n web-snap /dev/week08/web
sudo lvs
```

`lvs` should show two LVs: `web` (the original) and `web-snap` (the snapshot). The snapshot has an `Origin` column pointing at `web`, and the `Data%` column starts at 0.00 — no divergence yet.

### 7.2 Modify the original

```bash
# Delete some files.
sudo rm /mnt/week08-lv/file1 /mnt/week08-lv/file2 /mnt/week08-lv/file3

# Add new content.
echo "This is new content after snapshot" | sudo tee /mnt/week08-lv/after-snapshot.txt
sudo ls /mnt/week08-lv | sort
```

Now check the snapshot's Data%:

```bash
sudo lvs
```

The snapshot's `Data%` is now non-zero — the kernel is preserving the pre-deletion blocks in the snapshot so the snapshot's view does not change.

### 7.3 Mount the snapshot read-only

```bash
sudo mkdir -p /mnt/week08-snap
sudo mount -o ro /dev/week08/web-snap /mnt/week08-snap
sudo ls /mnt/week08-snap | sort
```

Compare with `sudo ls /mnt/week08-lv | sort`. The snapshot shows the **pre-modification** state: `file1`, `file2`, `file3` are still there; `after-snapshot.txt` is not.

### 7.4 Restore from the snapshot

This is the canonical "I made a mistake and need to recover from the snapshot" procedure. Several approaches; we will use the simplest: `cp` from the snapshot mount.

```bash
# Restore the deleted files.
sudo cp /mnt/week08-snap/file1 /mnt/week08-lv/
sudo cp /mnt/week08-snap/file2 /mnt/week08-lv/
sudo cp /mnt/week08-snap/file3 /mnt/week08-lv/

sudo ls /mnt/week08-lv | sort
```

`file1`, `file2`, `file3` are back; `after-snapshot.txt` is also still there (it was created after the snapshot, so it is intentionally preserved).

### 7.5 Remove the snapshot

When the snapshot is no longer needed:

```bash
sudo umount /mnt/week08-snap
sudo lvremove -f /dev/week08/web-snap
sudo lvs
```

Only `web` remains. The blocks the snapshot was using are returned to the VG's free pool.

Reference: `man 8 lvcreate` (the `-s` section), `man 8 lvremove`.

---

## Part 8 — A note on snapshot sizing

The snapshot is sized for the **delta**, not the source. A 200 MiB snapshot of a 1.5 GiB LV is enough if fewer than 200 MiB of unique blocks are written to the source while the snapshot exists.

If the snapshot fills up, it is **invalidated** and silently dropped:

```bash
sudo lvs                # check the snapshot's status; "S" in the Attr column means snapshot, "X" means inactive
```

A best practice for backup snapshots is to size them at 10-20 % of the source LV (rarely needed beyond that for short-lived backup operations), then `lvremove` immediately after the backup finishes. Long-lived snapshots are a btrfs/zfs feature; LVM's snapshots are a "short window for backup" tool.

---

## Part 9 — Clean up

```bash
sudo umount /mnt/week08-lv
sudo umount /mnt/week08-snap 2>/dev/null    # in case still mounted

cd /path/to/curriculum/week-08-disks-filesystems-and-page-cache/exercises
sudo ./teardown-loopback-disks.sh
```

The teardown script deactivates the VG, removes it, detaches the loopbacks, and deletes the backing files. Confirm:

```bash
sudo vgs                # should not show week08
sudo lvs                # should not show week08-web
sudo losetup -l         # should not show the week08 loops
ls /tmp/week08*.img     # should be empty
```

---

## Reflection

Answer in your notebook:

1. **Why use LVM at all?** Name three concrete operations that LVM enables that raw partitions do not.
2. **What does the `-r` flag to `lvextend` do, and why is it almost always what you want?**
3. **Suppose the snapshot fills up during a backup.** What happens? What is the failure mode you would see in your scripts?
4. **`lvreduce` exists but is dangerous.** Explain why shrinking is harder than growing. Mention at least one filesystem that cannot be shrunk at all.
5. **A snapshot is "free" to take in `O(1)` time.** What is it not free in — what resource does the snapshot consume over its lifetime?

---

## Stretch goals

- **Practice `pvmove`**: with the LV active, move all extents off `$DISK1` onto `$DISK2` and `$DISK3` using `pvmove $DISK1`. Then `vgreduce week08 $DISK1`. The mount stays up the whole time. This is the procedure for "I need to swap out a failing disk."
- **Create a thin-provisioned LV**: use `lvcreate --thinpool` to make a thin pool, then `lvcreate --thin` to make a thin LV inside it. The thin LV reports a "logical" size but consumes only the blocks actually written. Useful for densely-packed virtualisation.
- **RAID-1 mirror at the LVM layer**: `lvconvert --type raid1 -m 1 /dev/week08/web` converts the LV to a 2-way mirror across PVs. Now the LV is fault-tolerant. Read `man 8 lvconvert`.
- **Read `/sys/block/dm-0/`** and trace which device-mapper objects correspond to your LV. The kernel `Documentation/admin-guide/device-mapper/` is the canonical reference.

---

*Solutions in `SOLUTIONS.md`.*
