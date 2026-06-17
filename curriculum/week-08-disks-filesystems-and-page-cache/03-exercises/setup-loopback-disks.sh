#!/bin/sh
# setup-loopback-disks.sh
# Create three 1 GiB loopback "disks" for the week 08 exercises so you can
# practise partitioning, mkfs, and LVM without touching real hardware.
#
# This script is intentionally POSIX-portable (no bashisms). Run with sudo.
#
# Outputs (on success): three files at /tmp/week08-disk{1,2,3}.img attached
# to three loopback devices (e.g. /dev/loop20, /dev/loop21, /dev/loop22).
# Prints the loop device names to stdout.
#
# To tear down: teardown-loopback-disks.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: this script must run as root (try: sudo $0)" >&2
    exit 1
fi

DISKDIR=/tmp
DISKS="week08-disk1 week08-disk2 week08-disk3"
SIZE=1G

for d in $DISKS; do
    path="$DISKDIR/$d.img"
    if [ -f "$path" ]; then
        echo "INFO: $path already exists; reusing"
    else
        echo "INFO: creating $path ($SIZE sparse)"
        truncate -s "$SIZE" "$path"
    fi
done

echo "INFO: attaching to loopback devices"
LOOPS=""
for d in $DISKS; do
    path="$DISKDIR/$d.img"

    # Is this file already attached to a loop?
    existing=$(losetup -j "$path" | head -n1 | cut -d: -f1)
    if [ -n "$existing" ]; then
        loop="$existing"
        echo "INFO: $path already attached at $loop"
    else
        loop=$(losetup -fP --show "$path")
        echo "INFO: $path attached at $loop"
    fi
    LOOPS="$LOOPS $loop"
done

echo
echo "Loopback devices ready:"
for loop in $LOOPS; do
    printf '  %s\n' "$loop"
done

echo
echo "To use these in the exercises, set:"
i=1
for loop in $LOOPS; do
    printf '  export DISK%d=%s\n' "$i" "$loop"
    i=$((i + 1))
done

echo
echo "When done, tear down with: sudo ./teardown-loopback-disks.sh"
