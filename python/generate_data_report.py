#!/usr/bin/env python3
"""
Generate docs/data_report.md and data/checksums.sha256.
Captures real file sizes, line counts, file -i encoding, first 500 bytes preview, and SHA-256 hashes.
"""

import os
import sys
import hashlib
import subprocess

FILES = [
    ("Urdu Full (Decompressed)", "data/decompressed/ur.txt"),
    ("Roman Urdu Full (Decompressed)", "data/decompressed/ur_rom.txt"),
    ("English News Full (Decompressed)", "data/decompressed/en_news.txt"),
    ("Urdu Sample (50 MB)", "data/samples/sample_ur.txt"),
    ("Roman Urdu Sample (50 MB)", "data/samples/sample_ur_rom.txt"),
    ("English News Sample (50 MB)", "data/samples/sample_en.txt"),
]

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()

def line_count(filepath):
    try:
        out = subprocess.check_output(["wc", "-l", filepath], text=True)
        return int(out.strip().split()[0])
    except Exception:
        return -1

def file_encoding(filepath):
    try:
        out = subprocess.check_output(["file", "-i", filepath], text=True)
        return out.strip().split(":", 1)[1].strip()
    except Exception as e:
        return str(e)

def format_preview(filepath, byte_count=300):
    with open(filepath, "rb") as f:
        raw = f.read(byte_count)
    text_preview = raw.decode("utf-8", errors="replace")
    hex_preview = " ".join(f"{b:02x}" for b in raw[:64]) + " ..."
    return text_preview, hex_preview

def main():
    print("==> Generating data report and checksums...")
    checksum_lines = []
    report_sections = []

    for label, filepath in FILES:
        if not os.path.exists(filepath):
            print(f"ERROR: File {filepath} does not exist.", file=sys.stderr)
            sys.exit(1)

        size_bytes = os.path.getsize(filepath)
        size_mb = size_bytes / (1024 * 1024)
        size_gb = size_bytes / (1024 * 1024 * 1024)
        size_str = f"{size_gb:.2f} GB ({size_bytes:,} bytes)" if size_gb >= 1.0 else f"{size_mb:.2f} MB ({size_bytes:,} bytes)"
        
        print(f"    Processing {label}: {filepath} ({size_str}) ...")
        sha256 = sha256_file(filepath)
        checksum_lines.append(f"{sha256}  {filepath}\n")
        
        lines = line_count(filepath)
        enc = file_encoding(filepath)
        text_prev, hex_prev = format_preview(filepath, 400)

        section = f"""### {label}
- **Path:** `{filepath}`
- **Size:** {size_str}
- **Line Count:** {lines:,} lines
- **Encoding (`file -i`):** `{enc}`
- **SHA-256:** `{sha256}`
- **Initial 64 Bytes (Hex):**
```
{hex_prev}
```
- **Text Preview (First ~400 bytes):**
```
{text_prev}
```
"""
        report_sections.append(section)

    os.makedirs("data", exist_ok=True)
    with open("data/checksums.sha256", "w", encoding="utf-8") as f:
        f.writelines(checksum_lines)
    print("==> SHA-256 checksums written to data/checksums.sha256")

    df_out = subprocess.check_output(["df", "-h", "/home"], text=True).strip()

    report_content = f"""# Dataset Acquisition & Verification Report

- **Date Generated:** {subprocess.check_output(["date", "-u"], text=True).strip()}
- **Storage Location:** `/home` (Local NVMe SSD)
- **Current Disk Free Space:**
```
{df_out}
```

## Summary Table

| Dataset | Type | File Size | Line Count | Encoding | SHA-256 Checksum |
| --- | --- | --- | --- | --- | --- |
"""
    for label, filepath in FILES:
        sz = os.path.getsize(filepath)
        sz_str = f"{sz / (1024*1024*1024):.2f} GB" if sz >= 1024*1024*1024 else f"{sz / (1024*1024):.2f} MB"
        lines = line_count(filepath)
        enc = file_encoding(filepath)
        sha = [line.split()[0] for line in checksum_lines if filepath in line][0][:16] + "..."
        report_content += f"| {label} | `{filepath}` | {sz_str} | {lines:,} | `{enc}` | `{sha}` |\n"

    report_content += "\n## Detailed Dataset Profiles\n\n" + "\n---\n".join(report_sections)

    os.makedirs("docs", exist_ok=True)
    with open("docs/data_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    print("==> Data report written to docs/data_report.md")

if __name__ == "__main__":
    main()
