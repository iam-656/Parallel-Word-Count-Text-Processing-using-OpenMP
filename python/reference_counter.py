#!/usr/bin/env python3
"""
Independent Python Reference Implementation for Parallel Word Count Project.
Follows docs/counting_rules.md strictly:
- Decodes with errors="surrogateescape"
- Treats surrogate escapes (U+DC80 - U+DCFF) as separators
- Real U+FFFD is treated as a token character
- Order: Strip ignorable code points -> Normalize -> Apply hashtag rule -> 64-byte limit
- Produces deterministic sorted CSV dumps and single canonical 64-bit checksum.
"""

import sys
import os
import argparse
from collections import Counter

# 64-bit Checksum constants
FNV_OFFSET_BASIS = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3
MASK64 = 0xffffffffffffffff
MIXER = 0x9e3779b97f4a7c15

# Character sets
EXPLICIT_NON_ASCII_SEPARATORS = {
    0x00A0,  # Non-breaking space
    # Unicode spaces U+2000 - U+200A
    0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200A,
    # Guillemets
    0x00AB, 0x00BB,
    # Arabic / Urdu punctuation
    0x060C, 0x061B, 0x061F, 0x06D4, 0x066A, 0x066B, 0x066C,
    # Typographical quotes
    0x2018, 0x2019, 0x201A, 0x201B, 0x201C, 0x201D, 0x201E, 0x201F,
    # Dashes
    0x2013, 0x2014, 0x2015,
    # Ellipsis
    0x2026,
}

TRANSPARENTLY_STRIPPED = {
    0x200C,  # ZWNJ
    0x200D,  # ZWJ
    0x200B,  # ZWSP
    0x2060,  # Word Joiner
    0xFEFF,  # BOM
    0x200E,  # LRM
    0x200F,  # RLM
    0x061C,  # ALM
    0x0670,  # Superscript Alef
}

def is_arabic_diacritic(cp):
    return 0x064B <= cp <= 0x065F

def is_surrogate_escape(cp):
    # Python surrogateescape maps raw invalid bytes 0x80..0xFF to U+DC80..U+DCFF
    return 0xDC80 <= cp <= 0xDCFF

def is_separator(cp):
    if cp < 128:
        # ASCII: anything not alphanumeric is separator
        return not ((0x30 <= cp <= 0x39) or (0x41 <= cp <= 0x5A) or (0x61 <= cp <= 0x7A))
    if is_surrogate_escape(cp):
        return True
    return cp in EXPLICIT_NON_ASCII_SEPARATORS

def is_ignorable(cp):
    return cp in TRANSPARENTLY_STRIPPED or is_arabic_diacritic(cp)

def is_token_char(cp):
    # A token character is anything that is not a separator and not ignorable
    return not is_separator(cp) and not is_ignorable(cp)

def normalize_char(ch):
    cp = ord(ch)
    # ASCII uppercase -> lowercase
    if 0x41 <= cp <= 0x5A:
        return chr(cp + 32)
    # Arabic Yeh U+064A -> Urdu Yeh U+06CC
    if cp == 0x064A:
        return '\u06CC'
    # Arabic Kaf U+0643 -> Urdu Kaf U+06A9
    if cp == 0x0643:
        return '\u06A9'
    return ch

def tokenize(text):
    """
    Tokenizes text following strict docs/counting_rules.md order.
    Yields valid normalized tokens.
    """
    n = len(text)
    i = 0

    while i < n:
        cp = ord(text[i])

        # Check for hashtag candidate: '#' followed immediately by a token char
        if cp == 0x23:  # '#'
            if i + 1 < n and is_token_char(ord(text[i + 1])):
                # Valid hashtag!
                token_chars = ['#']
                i += 1
                while i < n:
                    curr_cp = ord(text[i])
                    if is_separator(curr_cp):
                        break
                    if not is_ignorable(curr_cp):
                        token_chars.append(normalize_char(text[i]))
                    i += 1

                token_str = ''.join(token_chars)
                token_bytes = token_str.encode('utf-8')
                if 1 <= len(token_bytes) <= 64:
                    yield token_str
                continue
            else:
                # Isolated '#' is an ASCII separator
                i += 1
                continue

        # Non-hashtag: if separator or ignorable, skip
        if is_separator(cp) or is_ignorable(cp):
            i += 1
            continue

        # Start of a normal token
        token_chars = []
        while i < n:
            curr_cp = ord(text[i])
            if is_separator(curr_cp):
                break
            if not is_ignorable(curr_cp):
                token_chars.append(normalize_char(text[i]))
            i += 1

        if token_chars:
            token_str = ''.join(token_chars)
            token_bytes = token_str.encode('utf-8')
            if 1 <= len(token_bytes) <= 64:
                yield token_str

def compute_checksum(frequency_table):
    """
    Computes the canonical 64-bit table checksum:
    term(w, c) = fnv1a64(w) ^ ((c * MIXER) & MASK64)
    checksum = sum(terms) & MASK64
    """
    total = 0
    for word_str, count in frequency_table.items():
        w_bytes = word_str.encode('utf-8')
        h = FNV_OFFSET_BASIS
        for b in w_bytes:
            h = ((h ^ b) * FNV_PRIME) & MASK64
        term = (h ^ ((count * MIXER) & MASK64)) & MASK64
        total = (total + term) & MASK64
    return total

def process_file(filepath, max_mb=None):
    with open(filepath, 'rb') as f:
        if max_mb:
            raw_bytes = f.read(int(max_mb * 1024 * 1024))
        else:
            raw_bytes = f.read()

    # Crucial: errors="surrogateescape" ensures invalid bytes become \udc80..\udcff
    # while authentic U+FFFD remains \ufffd!
    text = raw_bytes.decode('utf-8', errors='surrogateescape')
    counts = Counter(tokenize(text))
    return counts

def main():
    parser = argparse.ArgumentParser(description="Reference Tokenizer & Counter (PDC #23)")
    parser.add_argument("--input", "-i", required=True, nargs="+", help="Input file path(s)")
    parser.add_argument("--output-dir", "-o", default="results", help="Directory for output CSV")
    parser.add_argument("--top", type=int, default=100, help="Number of top words to report")
    parser.add_argument("--dump-all", action="store_true", help="Dump all words and counts to CSV")
    parser.add_argument("--max-mb", type=float, default=None, help="Cap megabytes read")
    parser.add_argument("--summary", action="store_true", help="Print summary with checksum")
    args = parser.parse_args()

    total_counts = Counter()
    for fp in args.input:
        total_counts.update(process_file(fp, args.max_mb))

    total_tokens = sum(total_counts.values())
    unique_tokens = len(total_counts)
    checksum = compute_checksum(total_counts)

    # Sort descending by count; ties broken ascending by raw UTF-8 bytes
    sorted_items = sorted(total_counts.items(), key=lambda kv: (-kv[1], kv[0].encode('utf-8')))

    os.makedirs(args.output_dir, exist_ok=True)
    out_basename = os.path.splitext(os.path.basename(args.input[0]))[0]

    if args.dump_all:
        dump_path = os.path.join(args.output_dir, f"{out_basename}_reference_dump.csv")
        with open(dump_path, 'w', encoding='utf-8') as f:
            f.write("word,count\n")
            for w, c in sorted_items:
                f.write(f'"{w}",{c}\n')
        print(f"==> Reference dump written to: {dump_path}")

    top_path = os.path.join(args.output_dir, f"{out_basename}_reference_top.csv")
    with open(top_path, 'w', encoding='utf-8') as f:
        f.write("word,count\n")
        for w, c in sorted_items[:args.top]:
            f.write(f'"{w}",{c}\n')
    print(f"==> Top-{args.top} written to: {top_path}")

    print(f"Total Tokens: {total_tokens:,}")
    print(f"Unique Tokens: {unique_tokens:,}")
    print(f"Canonical Checksum: 0x{checksum:016x}")

if __name__ == "__main__":
    main()
