#!/usr/bin/env python3
"""
Automated Test Runner for Phase 3.
Executes python/reference_counter.py on all fixtures in tests/ and verifies
100% agreement against tests/expected_outputs.json.
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath("python"))
from reference_counter import process_file, compute_checksum

def main():
    json_path = "tests/expected_outputs.json"
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found.", file=sys.stderr)
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        expected_data = json.load(f)

    all_passed = True
    total_tests = len(expected_data)
    passed_tests = 0

    print("=" * 70)
    print("           PDC #23 — PHASE 3 REFERENCE TEST SUITE")
    print("=" * 70)

    computed_checksums = {}

    for fixture_name, expected_counts in sorted(expected_data.items()):
        fixture_path = os.path.join("tests", fixture_name)
        if not os.path.exists(fixture_path):
            print(f"[-] FAIL: Fixture file {fixture_path} does not exist.")
            all_passed = False
            continue

        actual_counts = process_file(fixture_path)
        actual_dict = dict(actual_counts)
        checksum = compute_checksum(actual_counts)
        computed_checksums[fixture_name] = f"0x{checksum:016x}"

        if actual_dict == expected_counts:
            print(f"[+] PASS: {fixture_name:<30} (Tokens: {sum(actual_dict.values())}, Unique: {len(actual_dict)}, Checksum: 0x{checksum:016x})")
            passed_tests += 1
        else:
            print(f"[-] FAIL: {fixture_name}")
            print(f"    Expected: {expected_counts}")
            print(f"    Actual:   {actual_dict}")
            all_passed = False

    print("=" * 70)
    print(f"Results: {passed_tests}/{total_tests} test fixtures passed.")
    print("=" * 70)

    # Save computed checksums for test fixtures
    with open("tests/fixture_checksums.json", "w", encoding="utf-8") as f:
        json.dump(computed_checksums, f, indent=2)

    if all_passed:
        print("[+] GATE 3 PASSED: Reference implementation matches all hand-checked ground truth fixtures.")
        sys.exit(0)
    else:
        print("[-] GATE 3 FAILED: One or more test fixtures did not match expected counts.")
        sys.exit(1)

if __name__ == "__main__":
    main()
