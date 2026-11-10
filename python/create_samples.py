#!/usr/bin/env python3
"""
Generate 50 MB sample files from decompressed datasets, split cleanly at line boundaries.
"""

import os
import sys

TARGET_BYTES = 50 * 1024 * 1024  # 50 MB

DATASETS = [
    ("data/decompressed/ur.txt", "data/samples/sample_ur.txt"),
    ("data/decompressed/ur_rom.txt", "data/samples/sample_ur_rom.txt"),
    ("data/decompressed/en_news.txt", "data/samples/sample_en.txt"),
]

def make_sample(src, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if not os.path.exists(src):
        print(f"ERROR: Source file {src} not found.", file=sys.stderr)
        return False

    print(f"==> Generating 50 MB sample: {src} -> {dest} ...")
    written_bytes = 0
    lines_count = 0

    with open(src, "rb") as in_f, open(dest, "wb") as out_f:
        for line in in_f:
            out_f.write(line)
            written_bytes += len(line)
            lines_count += 1
            if written_bytes >= TARGET_BYTES:
                break

    print(f"    Done: {dest} ({written_bytes:,} bytes, {lines_count:,} lines)")
    return True

def main():
    all_ok = True
    for src, dest in DATASETS:
        if not make_sample(src, dest):
            all_ok = False
    if not all_ok:
        sys.exit(1)
    print("==> All 50 MB sample files generated successfully.")

if __name__ == "__main__":
    main()
