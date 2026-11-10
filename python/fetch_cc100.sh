#!/usr/bin/env bash
set -euo pipefail

RAW_DIR="data/raw"
mkdir -p "$RAW_DIR"

download_with_retry() {
    local url="$1"
    local dest="$2"
    local max_attempts=5
    local attempt=1

    echo "==> Downloading $url to $dest ..."
    while [ $attempt -le $max_attempts ]; do
        echo "    Attempt $attempt of $max_attempts..."
        if curl -L -C - --retry 3 --retry-delay 5 -o "$dest" "$url"; then
            echo "    Download finished. Verifying archive integrity with xz -t..."
            if xz -t "$dest"; then
                echo "    Archive integrity verified successfully for $dest."
                return 0
            else
                echo "    WARNING: Archive integrity check failed for $dest. Retrying..."
                rm -f "$dest"
            fi
        else
            echo "    Curl encountered an error. Retrying in 5 seconds..."
            sleep 5
        fi
        attempt=$((attempt + 1))
    done

    echo "ERROR: Failed to download and verify $url after $max_attempts attempts."
    return 1
}

download_with_retry "https://data.statmt.org/cc-100/ur.txt.xz" "$RAW_DIR/ur.txt.xz"
download_with_retry "https://data.statmt.org/cc-100/ur_rom.txt.xz" "$RAW_DIR/ur_rom.txt.xz"

echo "==> CC-100 datasets downloaded and integrity verified."
