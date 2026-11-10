#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="data/raw"
DECOMP_DIR="data/decompressed"
mkdir -p "$DECOMP_DIR"

decompress_file() {
    local src="$1"
    local dest="$2"
    local tmp="${dest}.tmp"

    if [ -f "$dest" ] && [ -s "$dest" ]; then
        echo "==> Destination $dest already exists and is non-empty. Skipping decompression."
        return 0
    fi

    echo "==> Decompressing $src to temporary file $tmp ..."
    xz -dc -T 0 "$src" > "$tmp"
    echo "    Decompression finished. Atomically renaming $tmp to $dest ..."
    mv -f "$tmp" "$dest"
    echo "    Done: $dest ($(du -h "$dest" | cut -f1))"
}

decompress_file "$RAW_DIR/ur.txt.xz" "$DECOMP_DIR/ur.txt"
decompress_file "$RAW_DIR/ur_rom.txt.xz" "$DECOMP_DIR/ur_rom.txt"

echo "==> All CC-100 files decompressed successfully."
