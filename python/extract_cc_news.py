#!/usr/bin/env python3
"""
Stream and extract English news articles from Hugging Face into a plain text file.
One article per line, with whitespace collapsed to single spaces, skipping empty articles.
"""

import os
import sys
import re

def main():
    output_path = "data/decompressed/en_news.txt"
    tmp_path = "data/decompressed/en_news.txt.tmp"
    os.makedirs("data/decompressed", exist_ok=True)

    print("==> Initializing Hugging Face dataset extraction...")
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: 'datasets' package not found in current environment.", file=sys.stderr)
        sys.exit(1)

    dataset_name = "vblagoje/cc_news"
    print(f"==> Loading dataset '{dataset_name}' in streaming mode...")
    try:
        ds = load_dataset(dataset_name, split="train", streaming=True)
    except Exception as e:
        print(f"Warning: Failed loading '{dataset_name}': {e}. Falling back to 'cc_news'...")
        dataset_name = "cc_news"
        ds = load_dataset(dataset_name, split="train", streaming=True)

    whitespace_regex = re.compile(r"\s+")
    article_count = 0
    total_bytes = 0

    print(f"==> Streaming articles to temporary file: {tmp_path}")
    with open(tmp_path, "w", encoding="utf-8") as out_f:
        for item in ds:
            text = item.get("text") or item.get("description") or ""
            if not text:
                continue
            
            # Collapse whitespace (including newlines and tabs) to single spaces
            collapsed = whitespace_regex.sub(" ", text).strip()
            if not collapsed:
                continue

            out_f.write(collapsed + "\n")
            article_count += 1
            total_bytes += len(collapsed.encode("utf-8")) + 1

            if article_count % 50000 == 0:
                print(f"    Extracted {article_count:,} articles (~{total_bytes / (1024*1024):.1f} MB)...")

    print(f"==> Extraction complete. Total articles: {article_count:,}, Size: {total_bytes / (1024*1024):.1f} MB")
    print(f"==> Renaming {tmp_path} -> {output_path}")
    os.replace(tmp_path, output_path)
    print("==> English news dataset ready.")

if __name__ == "__main__":
    main()
