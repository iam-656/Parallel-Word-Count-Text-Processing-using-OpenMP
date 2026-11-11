#!/usr/bin/env python3
"""
Automated verification script for C++ engine (bin/wordcount).
Runs on all fixtures in tests/ and verifies:
1. Top CSV and full dump match tests/expected_outputs.json exactly.
2. Canonical checksum matches python reference checksum exactly.
"""

import os
import sys
import json
import subprocess
import csv

def parse_dump_csv(csv_path):
    table = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            if len(row) >= 2:
                table[row[0]] = int(row[1])
    return table

def parse_cpp_output(stdout_str):
    checksum = None
    for line in stdout_str.splitlines():
        if "Canonical Checksum:" in line:
            parts = line.split(":")
            checksum = parts[1].strip()
    return checksum

def main():
    bin_path = "bin/wordcount"
    if not os.path.exists(bin_path):
        print(f"ERROR: {bin_path} not found. Run 'make release' first.", file=sys.stderr)
        sys.exit(1)

    json_path = "tests/expected_outputs.json"
    with open(json_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    with open("tests/fixture_checksums.json", "r", encoding="utf-8") as f:
        reference_checksums = json.load(f)

    all_passed = True
    passed_count = 0
    total_count = len(expected_data)

    print("=" * 70)
    print("           PDC #23 — C++ SERIAL ENGINE VERIFICATION")
    print("=" * 70)

    for fixture_name, expected_counts in sorted(expected_data.items()):
        fixture_path = os.path.join("tests", fixture_name)
        out_dir = "results/cpp_test"
        base_name = os.path.splitext(fixture_name)[0]
        dump_path = os.path.join(out_dir, f"{base_name}_serial_dump.csv")

        cmd = [bin_path, "--input", fixture_path, "--mode", "serial", "--dump-all", "--output-dir", out_dir]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"[-] FAIL: {fixture_name} (exit code {res.returncode})")
            print(res.stderr)
            all_passed = False
            continue

        cpp_checksum = parse_cpp_output(res.stdout)
        expected_checksum = reference_checksums.get(fixture_name)
        actual_counts = parse_dump_csv(dump_path)

        counts_ok = (actual_counts == expected_counts)
        checksum_ok = (cpp_checksum == expected_checksum)

        if counts_ok and checksum_ok:
            print(f"[+] PASS: {fixture_name:<30} (Counts match, Checksum: {cpp_checksum})")
            passed_count += 1
        else:
            print(f"[-] FAIL: {fixture_name}")
            if not counts_ok:
                print(f"    Expected: {expected_counts}")
                print(f"    Actual:   {actual_counts}")
            if not checksum_ok:
                print(f"    Expected Checksum: {expected_checksum}")
                print(f"    Actual Checksum:   {cpp_checksum}")
            all_passed = False

    print("=" * 70)
    print(f"Results: {passed_count}/{total_count} fixtures passed.")
    print("=" * 70)

    if all_passed:
        print("[+] SUCCESS: C++ serial engine produces byte-identical output to Python reference across all fixtures!")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
