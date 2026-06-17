#!/bin/sh
# teardown-loopback-disks.sh
# Tear down the three loopback "disks" created by setup-loopback-disks.sh
# Also unmounts any leftover mountpoints, deactivates any LVM, and removes
# the backing files. Safe to re-run.
#
# Run with sudo. POSIX-portable.

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: this script must run as root (try: sudo $0)" >&2
    exit 1
fi

DISKDIR=/tmp
DISKS="week08-disk1 week08-disk2 week08-disk3"

# 1. Unmount any mountpoint that lives under a likely week08 location.
for mp in /mnt/week08-disk1 /mnt/week08-disk2 /mnt/week08-disk3 \
          /mnt/week08-lv /mnt/week08-snap /mnt/week08-data; do
    if mountpoint -q "$mp" 2>/dev/null; then
        echo "INFO: unmounting $mp"
        umount "$mp" || true
    fi
done

# 2. Deactivate any LVM volume groups that might be sitting on the loopbacks.
#    The exercises use VG name "week08" by convention; tolerate "not found".
if command -v vgchange >/dev/null 2>&1; then
    if vgs week08 >/dev/null 2>&1; then
        echo "INFO: deactivating VG week08"
        vgchange -an week08 || true
        echo "INFO: removing VG week08 (keeps PV signatures for now)"
        vgremove -f week08 || true
    fi
fi

# 3. Detach the loopback devices that back the week08 files.
for d in $DISKS; do
    path="$DISKDIR/$d.img"
    if [ -f "$path" ]; then
        # Find the loop devices attached to this file.
        losetup -j "$path" | cut -d: -f1 | while IFS= read -r loop; do
            if [ -n "$loop" ]; then
                echo "INFO: detaching $loop ($path)"
                losetup -d "$loop" || true
            fi
        done
    fi
done

# 4. Remove the backing files.
for d in $DISKS; do
    path="$DISKDIR/$d.img"
    if [ -f "$path" ]; then
        echo "INFO: removing $path"
        rm -f "$path"
    fi
done

# 5. Remove the mountpoint directories if they are empty.
for mp in /mnt/week08-disk1 /mnt/week08-disk2 /mnt/week08-disk3 \
          /mnt/week08-lv /mnt/week08-snap /mnt/week08-data; do
    if [ -d "$mp" ] && [ -z "$(ls -A "$mp" 2>/dev/null)" ]; then
        echo "INFO: removing empty directory $mp"
        rmdir "$mp" || true
    fi
done

echo
echo "Teardown complete."
echo "Confirm with: losetup -l ; vgs ; ls /tmp/week08-disk*.img 2>/dev/null"
