#!/usr/bin/env python3
"""
Challenge 01 — Cache-aware cp

A type-hinted Python `cp` clone that copies a file from SRC to DST and, after
each read of SRC, hints to the kernel that those pages are no longer needed
(via posix_fadvise(POSIX_FADV_DONTNEED)).

The use case: copying a very large file (say, a 50 GiB backup archive) without
polluting the page cache. A naive cp pulls the whole 50 GiB into cache,
evicting the hot pages of every running application. This script keeps the
page cache mostly intact by telling the kernel "I have read this; you do not
need to keep it."

Type-hinted, standard library only, runs on any Linux 4.x+ (posix_fadvise has
been in the Python standard library since 3.3, October 2012).

Usage:
    python3 challenge-01-cache-aware-cp.py SRC DST
    python3 challenge-01-cache-aware-cp.py --no-fadvise SRC DST  # for comparison
    python3 challenge-01-cache-aware-cp.py --buffer 65536 SRC DST  # 64k buffer

Reference:
  - man 2 posix_fadvise
  - man 2 read, man 2 write
  - Python docs: https://docs.python.org/3/library/os.html#os.posix_fadvise

This is a teaching toy. For production copies of huge files consider the
`nocache` utility (https://github.com/Feh/nocache) or `cp --reflink` on btrfs.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Final


# Default read buffer size. 1 MiB is a reasonable trade-off between syscall
# overhead and memory footprint. The kernel's readahead is typically 128 KiB
# by default; with a 1 MiB buffer we get one readahead per buffer-full.
DEFAULT_BUFFER_SIZE: Final[int] = 1 * 1024 * 1024  # 1 MiB


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy a file without polluting the page cache.",
    )
    parser.add_argument(
        "src",
        type=Path,
        help="Source file to read from.",
    )
    parser.add_argument(
        "dst",
        type=Path,
        help="Destination file to write to. Must not be the same as src.",
    )
    parser.add_argument(
        "--buffer",
        type=int,
        default=DEFAULT_BUFFER_SIZE,
        help=f"Read buffer size in bytes (default {DEFAULT_BUFFER_SIZE}).",
    )
    parser.add_argument(
        "--no-fadvise",
        action="store_true",
        help="Disable the POSIX_FADV_DONTNEED hint (for comparison).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print progress every 100 MiB.",
    )
    return parser.parse_args()


def validate_paths(src: Path, dst: Path) -> None:
    """Confirm the source exists and the destination is not the same file.

    Raises SystemExit on validation failure.
    """
    if not src.exists():
        print(f"ERROR: source does not exist: {src}", file=sys.stderr)
        sys.exit(2)

    if not src.is_file():
        print(f"ERROR: source is not a regular file: {src}", file=sys.stderr)
        sys.exit(2)

    # Compare inodes to detect "cp a a" or "cp a ./a" where the destination
    # is the same file. os.path.samefile follows symlinks; we want that.
    if dst.exists() and src.resolve() == dst.resolve():
        print("ERROR: source and destination are the same file", file=sys.stderr)
        sys.exit(2)

    # If the destination is a directory, append the source's basename.
    # (We do not currently support this; the caller should give a file path.
    # Bail rather than do something surprising.)
    if dst.exists() and dst.is_dir():
        print(f"ERROR: destination is a directory; give a file path: {dst}",
              file=sys.stderr)
        sys.exit(2)


def open_src_with_advice(src: Path, use_fadvise: bool) -> int:
    """Open the source for reading and set POSIX_FADV_SEQUENTIAL.

    Returns the file descriptor. The caller must close it.

    POSIX_FADV_SEQUENTIAL tells the kernel "expect sequential reads";
    the kernel responds by doubling the readahead window. Combined
    with POSIX_FADV_DONTNEED after each read, we get aggressive
    readahead and aggressive eviction — exactly what a streaming
    copy wants.
    """
    fd = os.open(str(src), os.O_RDONLY)
    if use_fadvise:
        # Hint: we will read sequentially. The kernel adjusts readahead.
        os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_SEQUENTIAL)
    return fd


def open_dst(dst: Path) -> int:
    """Open the destination for writing, truncating if it exists.

    Returns the file descriptor. The caller must close it.

    We use O_CREAT|O_WRONLY|O_TRUNC and create the file with mode 0o644.
    """
    flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
    return os.open(str(dst), flags, 0o644)


def copy_loop(
    src_fd: int,
    dst_fd: int,
    buffer_size: int,
    use_fadvise: bool,
    verbose: bool,
) -> int:
    """Copy src_fd to dst_fd in chunks of buffer_size.

    After each successful read, hint the kernel via posix_fadvise that
    we no longer need the just-read pages cached.

    Returns the total number of bytes copied.
    """
    total: int = 0
    last_progress_print_mb: int = 0

    while True:
        chunk = os.read(src_fd, buffer_size)
        if not chunk:
            break

        # Write the chunk to dst. os.write may return short writes; loop.
        offset = 0
        while offset < len(chunk):
            written = os.write(dst_fd, chunk[offset:])
            if written == 0:
                raise OSError("os.write returned 0; cannot continue")
            offset += written

        # Hint to drop the just-read source pages from cache.
        # The arguments to posix_fadvise: (fd, offset, len, advice).
        # offset is the start of the range we just read; len is its length.
        if use_fadvise:
            # We do not know the exact file offset of this read without
            # tracking it; use the running total minus the chunk size.
            chunk_start = total
            os.posix_fadvise(
                src_fd,
                chunk_start,
                len(chunk),
                os.POSIX_FADV_DONTNEED,
            )

        total += len(chunk)

        if verbose:
            current_mb = total // (1024 * 1024)
            if current_mb >= last_progress_print_mb + 100:
                print(f"  copied {current_mb} MiB ...", file=sys.stderr)
                last_progress_print_mb = current_mb

    return total


def fsync_and_advise_dst(dst_fd: int, total: int, use_fadvise: bool) -> None:
    """fsync the destination and (optionally) hint POSIX_FADV_DONTNEED on it too.

    The destination pages are also cache pollution for the same reason as
    the source. After fsync, the pages are clean; dropping them is cheap.
    """
    os.fsync(dst_fd)
    if use_fadvise:
        os.posix_fadvise(dst_fd, 0, total, os.POSIX_FADV_DONTNEED)


def main() -> int:
    """Entry point."""
    args = parse_args()
    validate_paths(args.src, args.dst)

    use_fadvise: bool = not args.no_fadvise
    if args.verbose:
        msg = "with" if use_fadvise else "without"
        print(
            f"Copying {args.src} -> {args.dst} "
            f"({msg} POSIX_FADV_DONTNEED, buffer {args.buffer} bytes)",
            file=sys.stderr,
        )

    start: float = time.monotonic()
    src_fd = open_src_with_advice(args.src, use_fadvise)
    try:
        dst_fd = open_dst(args.dst)
        try:
            total = copy_loop(
                src_fd=src_fd,
                dst_fd=dst_fd,
                buffer_size=args.buffer,
                use_fadvise=use_fadvise,
                verbose=args.verbose,
            )
            fsync_and_advise_dst(dst_fd, total, use_fadvise)
        finally:
            os.close(dst_fd)
    finally:
        os.close(src_fd)

    elapsed: float = time.monotonic() - start
    mb: float = total / (1024 * 1024)
    rate_mb_per_s: float = mb / elapsed if elapsed > 0 else 0.0
    print(
        f"Copied {total} bytes ({mb:.1f} MiB) "
        f"in {elapsed:.2f} s ({rate_mb_per_s:.1f} MiB/s)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
