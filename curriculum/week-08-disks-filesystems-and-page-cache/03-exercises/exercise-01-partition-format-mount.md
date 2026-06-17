# Exercise 1 — Partition, format, mount, persist

**Time:** 45-60 minutes.
**Goal:** Take a fresh "disk" (a loopback file in this exercise; the same procedure applies to a real disk). Partition with GPT. Format as ext4 with a label. Mount. Add to `/etc/fstab`. Reboot-safely.
**Prerequisites:** Lecture 1 read. The `setup-loopback-disks.sh` helper available (`exercises/setup-loopback-disks.sh`).

---

## Why this exercise

The single most basic Linux storage task is "I have a disk; make it usable." The four-step recipe — **partition, format, mount, persist** — is the foundation of every more sophisticated operation in this week. The exercise drills it on a safe target (a loopback file) so the muscle memory is correct when you face a real disk.

If you cannot do this in under five minutes from memory by Friday, you cannot do anything harder. Earn it.

---

## Part 1 — Set up the loopback "disk"

In a terminal:

```bash
cd /path/to/curriculum/week-08-disks-filesystems-and-page-cache/exercises
sudo ./setup-loopback-disks.sh
```

The script creates three 1 GiB sparse files at `/tmp/week08-disk{1,2,3}.img` and attaches each to a loopback device. Note the device names printed at the end. For this exercise we only need the first one (`DISK1`).

Set the variable for the rest of this exercise:

```bash
export DISK1=$(sudo losetup -j /tmp/week08-disk1.img | head -1 | cut -d: -f1)
echo "Working with $DISK1"
```

Confirm with `lsblk`:

```bash
lsblk "$DISK1"
```

You should see one block device, ~1 GiB, no partitions.

---

## Part 2 — Inspect before you write

Bash Yellow: from here, the commands write to a block device. The loopback file is the blast radius; on a real system it would be your disk.

```bash
# What is on this device right now?
sudo wipefs --no-act "$DISK1"

# Anything mounted from it?
mount | grep "$DISK1" || echo "Nothing mounted from $DISK1"

# Confirm it is the loopback (not a real disk).
sudo losetup -a | grep "$DISK1"
```

If `wipefs --no-act` reports any signatures, the file was reused from a previous exercise. Wipe them:

```bash
sudo wipefs -a "$DISK1"
```

---

## Part 3 — Create the partition table

Use `parted` in scripted mode. We will create one GPT partition spanning 1 MiB to 100 % of the device.

```bash
sudo parted --script "$DISK1" \
    mklabel gpt \
    mkpart primary ext4 1MiB 100%
```

Inspect the result:

```bash
sudo parted --script "$DISK1" print
```

You should see one partition labelled "primary", type ext4 hint, of approximately 1023 MiB. The partition device is `${DISK1}p1`. Confirm:

```bash
sudo partprobe "$DISK1"
ls "${DISK1}"*
```

You should see `$DISK1` and `${DISK1}p1`. If `${DISK1}p1` is not there, `partprobe` was needed or the kernel did not re-read the partition table; the second invocation of `partprobe` usually resolves this.

---

## Part 4 — Format as ext4

```bash
sudo mkfs.ext4 -L week08-disk1 "${DISK1}p1"
```

The output reports:

- Filesystem block size (1024 or 4096).
- Inode count and inode size.
- Block group count.
- Allocation of the journal.

Read it. Get the UUID:

```bash
UUID=$(sudo blkid -s UUID -o value "${DISK1}p1")
echo "UUID is $UUID"
```

You will use the UUID for the fstab entry.

---

## Part 5 — Mount it

```bash
sudo mkdir -p /mnt/week08-disk1
sudo mount "${DISK1}p1" /mnt/week08-disk1
```

Verify:

```bash
df -h /mnt/week08-disk1
mount | grep week08
ls /mnt/week08-disk1
```

You should see one mount line, ~1 GiB total, and a `lost+found` directory (ext4 creates this at `mkfs` time).

Write a test file:

```bash
echo "It works." | sudo tee /mnt/week08-disk1/hello.txt
sudo cat /mnt/week08-disk1/hello.txt
```

---

## Part 6 — Persist in /etc/fstab

Back up `/etc/fstab` first:

```bash
sudo cp /etc/fstab /etc/fstab.bak.$(date +%s)
ls -la /etc/fstab.bak.*
```

Add the fstab line. Use the UUID, set the options to a sensible server default, mark dump as 0, and set pass to 2:

```bash
echo "UUID=${UUID}  /mnt/week08-disk1  ext4  defaults,noatime,nodiratime,errors=remount-ro  0  2" | \
    sudo tee -a /etc/fstab
```

Verify syntax before reboot:

```bash
sudo findmnt --verify
```

If `findmnt --verify` reports errors **on your new line**, fix them now. Other warnings (about your existing root or boot mounts) you can ignore for the purpose of this exercise.

Test the mount works from fstab:

```bash
sudo umount /mnt/week08-disk1
sudo mount /mnt/week08-disk1    # uses /etc/fstab
df -h /mnt/week08-disk1
```

`mount /mnt/week08-disk1` (without a device argument) only succeeds if there is an `/etc/fstab` entry for that mount point. If it succeeds, your fstab line is correct.

---

## Part 7 — Reboot safety check (optional)

If you are willing to reboot the machine:

1. `sudo reboot`
2. After boot, verify the mount survived:

```bash
df -h /mnt/week08-disk1
mount | grep week08
```

If the mount is present, you wrote a correct fstab line. If the boot was interrupted by a "failed to mount" error, your fstab line was wrong; recover by removing the bad line and reboot:

```bash
sudo nano /etc/fstab
# remove the bad line
sudo reboot
```

A broken fstab is recoverable but not fun. The `findmnt --verify` and `mount /mnt/week08-disk1` (without a device argument) tests in Part 6 are how you catch errors **before** they cost you a reboot.

**Note**: because the loopback file is in `/tmp` (a tmpfs on many systems), it will be **gone after reboot**. The fstab line will then fail at boot. This is expected for the exercise; if you actually want the mount to survive reboot for a real disk, the file would be on a persistent location and the loopback would be set up by a separate systemd unit. For now, **revert** the fstab line before rebooting:

```bash
# Restore the backup we made in step 6.
sudo cp /etc/fstab.bak.* /etc/fstab    # use the most recent backup
```

---

## Part 8 — Clean up

```bash
sudo umount /mnt/week08-disk1
sudo rmdir /mnt/week08-disk1

# Restore /etc/fstab from the backup (skip this if you already did in part 7).
LATEST_BACKUP=$(ls -t /etc/fstab.bak.* | head -1)
sudo cp "$LATEST_BACKUP" /etc/fstab

# Tear down the loopback.
cd /path/to/curriculum/week-08-disks-filesystems-and-page-cache/exercises
sudo ./teardown-loopback-disks.sh
```

Confirm cleanup:

```bash
losetup -l | grep week08    # should be empty
ls /tmp/week08-*.img        # should be empty
cat /etc/fstab | grep week08-disk1   # should be empty
```

---

## Reflection

Answer these in your notebook (the homework grader will ask for similar reasoning):

1. **Why does the fstab line use `UUID=` instead of `/dev/loop20p1`?** What concrete failure mode does the UUID protect against?
2. **What does the `pass=2` mean?** What would happen if you set it to `1`? To `0`?
3. **Why `defaults,noatime,nodiratime`?** Which of those three is `defaults` and what does it expand to?
4. **What does `errors=remount-ro` do that the default does not?** When does this fire?
5. **Suppose you formatted the wrong device in Part 4.** What is the one command you ran in Part 2 that would have prevented this if you had read its output? What was the output saying?

---

## Stretch goals

- Repeat Part 3 with **MBR** instead of GPT (`mklabel msdos`) and read the differences in `parted print`. Note the absence of the per-partition UUID.
- Repeat Part 4 with **xfs** (`mkfs.xfs -L week08-disk1 -f ${DISK1}p1`) and observe the differences in `mkfs` output. Read `xfs_info /mnt/week08-disk1` for the structural details.
- Repeat Part 4 with **btrfs** (`mkfs.btrfs -L week08-disk1 -f ${DISK1}p1`) and create a subvolume inside it: `sudo btrfs subvolume create /mnt/week08-disk1/sub1`. Read `man 8 btrfs-subvolume`.

---

*Solutions in `SOLUTIONS.md`.*
