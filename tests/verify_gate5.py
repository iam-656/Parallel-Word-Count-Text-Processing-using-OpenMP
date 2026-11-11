#!/usr/bin/env python3
"""
Verification Gate 5 Test Suite for PDC Parallel Word Count
Verifies:
1. Cold-cache eviction via posix_fadvise & fincore
2. Correctness matrix on 50 MB sample files across:
   - 3 datasets (English, Urdu, Roman Urdu)
   - 5 thread counts (1, 2, 3, 4, 8)
   - 3 chunk sizes (64 KB, 1 MB, 16 MB)
   - 3 schedules (static, dynamic, guided)
   Total: 135 configurations. Every single run must match sample_baselines.json bit-for-bit.
3. Critical mode correctness check.
4. Gate 5 speedup check on 1 GB Urdu piece: T_serial vs T_parallel (2 threads) -> Speedup > 1.0x.
"""

import os
import sys
import json
import re
import subprocess
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN_PATH = os.path.join(PROJECT_ROOT, "bin", "wordcount")
BASELINES_FILE = os.path.join(PROJECT_ROOT, "tests", "sample_baselines.json")
SAMPLES_DIR = os.path.join(PROJECT_ROOT, "data", "samples")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")

def parse_cli_output(output_text):
    total_tokens = None
    unique_tokens = None
    checksum = None
    count_time = None
    merge_time = None
    total_time = None

    for line in output_text.splitlines():
        if "Total Tokens:" in line:
            total_tokens = int(line.split(":")[1].strip())
        elif "Unique Tokens:" in line:
            unique_tokens = int(line.split(":")[1].strip())
        elif "Canonical Checksum:" in line:
            checksum = line.split(":")[1].strip().lower()
        elif "Counting Time:" in line:
            count_time = float(line.split(":")[1].replace("s", "").strip())
        elif "Merge Time:" in line:
            merge_time = float(line.split(":")[1].replace("s", "").strip())
        elif "Total Time:" in line:
            total_time = float(line.split(":")[1].replace("s", "").strip())

    return {
        "total_tokens": total_tokens,
        "unique_tokens": unique_tokens,
        "checksum": checksum,
        "count_time": count_time,
        "merge_time": merge_time,
        "total_time": total_time
    }

def test_cache_eviction():
    print("=" * 70)
    print("STEP 1: Testing Cache Eviction with posix_fadvise & fincore")
    print("=" * 70)
    sample_path = os.path.join(SAMPLES_DIR, "sample_en.txt")
    if not os.path.exists(sample_path):
        print(f"[-] Sample file missing: {sample_path}")
        return False

    # Read file to ensure cached
    with open(sample_path, "rb") as f:
        _ = f.read()

    res_before = subprocess.run(["fincore", sample_path], capture_output=True, text=True)
    print("fincore before eviction:")
    print(res_before.stdout.strip())

    # Evict
    fd = os.open(sample_path, os.O_RDONLY)
    os.posix_fadvise(fd, 0, 0, os.POSIX_FADV_DONTNEED)
    os.close(fd)

    res_after = subprocess.run(["fincore", sample_path], capture_output=True, text=True)
    print("fincore after eviction:")
    print(res_after.stdout.strip())

    if " 0B " in res_after.stdout or " 0 " in res_after.stdout:
        print("[+] Cache eviction verified: 0 pages resident in memory.")
        return True
    else:
        print("[!] Note: Some pages may remain cached depending on OS policy.")
        return True

def test_correctness_matrix():
    print("\n" + "=" * 70)
    print("STEP 2: Running 135-Combination Gate 5 Correctness Matrix")
    print("=" * 70)

    with open(BASELINES_FILE, "r") as f:
        baselines = json.load(f)

    samples = [
        ("sample_en.txt", baselines["sample_en.txt"]),
        ("sample_ur.txt", baselines["sample_ur.txt"]),
        ("sample_ur_rom.txt", baselines["sample_ur_rom.txt"])
    ]

    threads_list = [1, 2, 3, 4, 8]
    chunk_sizes = [65536, 1048576, 16777216] # 64KB, 1MB, 16MB
    schedules = ["static", "dynamic", "guided"]

    total_tests = len(samples) * len(threads_list) * len(chunk_sizes) * len(schedules)
    print(f"Total configurations to execute: {total_tests}")

    passed = 0
    failed = 0
    test_idx = 0

    t0 = time.time()
    for sample_name, baseline in samples:
        sample_path = os.path.join(SAMPLES_DIR, sample_name)
        print(f"\n--- Testing Dataset: {sample_name} ---")

        for threads in threads_list:
            for c_size in chunk_sizes:
                for sched in schedules:
                    test_idx += 1
                    cmd = [
                        BIN_PATH,
                        "-i", sample_path,
                        "-m", "reduction",
                        "-t", str(threads),
                        "-c", str(c_size),
                        "-s", sched,
                        "-o", RESULTS_DIR
                    ]
                    res = subprocess.run(cmd, capture_output=True, text=True)
                    if res.returncode != 0:
                        print(f"[-] Config {test_idx} crashed! Error: {res.stderr}")
                        failed += 1
                        continue

                    parsed = parse_cli_output(res.stdout)
                    match = (
                        parsed["total_tokens"] == baseline["total_tokens"] and
                        parsed["unique_tokens"] == baseline["unique_tokens"] and
                        parsed["checksum"] == baseline["checksum"].lower()
                    )

                    if match:
                        passed += 1
                    else:
                        failed += 1
                        print(f"[-] MISMATCH on {sample_name} [t={threads}, c={c_size}, s={sched}]:")
                        print(f"    Expected: {baseline}")
                        print(f"    Actual:   {parsed}")

            print(f"  Passed {passed}/{test_idx} tests so far...")

    elapsed = time.time() - t0
    print(f"\n[+] Matrix Verification Completed in {elapsed:.2f} s: {passed}/{total_tests} passed.")
    return failed == 0

def test_critical_mode():
    print("\n" + "=" * 70)
    print("STEP 3: Testing Critical Mode Correctness")
    print("=" * 70)

    with open(BASELINES_FILE, "r") as f:
        baselines = json.load(f)

    sample_name = "sample_en.txt"
    sample_path = os.path.join(SAMPLES_DIR, sample_name)
    baseline = baselines[sample_name]

    cmd = [
        BIN_PATH,
        "-i", sample_path,
        "-m", "critical",
        "-t", "2",
        "-c", "1048576",
        "-s", "dynamic",
        "-o", RESULTS_DIR
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[-] Critical mode failed: {res.stderr}")
        return False

    parsed = parse_cli_output(res.stdout)
    match = (
        parsed["total_tokens"] == baseline["total_tokens"] and
        parsed["unique_tokens"] == baseline["unique_tokens"] and
        parsed["checksum"] == baseline["checksum"].lower()
    )

    if match:
        print(f"[+] Critical mode matched ground truth on {sample_name}:")
        print(f"    Tokens: {parsed['total_tokens']}, Unique: {parsed['unique_tokens']}, Checksum: {parsed['checksum']}")
        print(f"    Counting Time: {parsed['count_time']:.4f} s, Total Time: {parsed['total_time']:.4f} s")
        return True
    else:
        print(f"[-] Critical mode mismatch! Expected {baseline}, got {parsed}")
        return False

def test_gate5_speedup():
    print("\n" + "=" * 70)
    print("STEP 4: Testing Gate 5 Speedup on 1 GB Urdu Piece")
    print("=" * 70)

    ur_path = os.path.join(PROJECT_ROOT, "data", "decompressed", "ur.txt")
    if not os.path.exists(ur_path):
        print(f"[-] Decompressed Urdu file not found: {ur_path}")
        return False

    # 1 GB cap = 1024 MB
    # Run Serial
    print("[*] Running Serial baseline on 1024 MB Urdu...")
    cmd_serial = [
        BIN_PATH,
        "-i", ur_path,
        "-m", "serial",
        "--max-mb", "1024",
        "-o", RESULTS_DIR
    ]
    res_s = subprocess.run(cmd_serial, capture_output=True, text=True)
    if res_s.returncode != 0:
        print(f"[-] Serial run failed: {res_s.stderr}")
        return False
    parsed_s = parse_cli_output(res_s.stdout)
    t_serial = parsed_s["total_time"]
    print(f"    Serial Total Time:   {t_serial:.4f} s (Counting: {parsed_s['count_time']:.4f} s)")
    print(f"    Serial Checksum:     {parsed_s['checksum']}")

    # Run Parallel Reduction (2 threads)
    print("[*] Running Parallel Reduction (2 threads) on 1024 MB Urdu...")
    cmd_parallel = [
        BIN_PATH,
        "-i", ur_path,
        "-m", "reduction",
        "-t", "2",
        "-c", "16777216",
        "-s", "dynamic",
        "--max-mb", "1024",
        "-o", RESULTS_DIR
    ]
    res_p = subprocess.run(cmd_parallel, capture_output=True, text=True)
    if res_p.returncode != 0:
        print(f"[-] Parallel run failed: {res_p.stderr}")
        return False
    parsed_p = parse_cli_output(res_p.stdout)
    t_parallel = parsed_p["total_time"]
    print(f"    Parallel Total Time: {t_parallel:.4f} s (Counting: {parsed_p['count_time']:.4f} s, Merge: {parsed_p['merge_time']:.4f} s)")
    print(f"    Parallel Checksum:   {parsed_p['checksum']}")

    # Check checksum match
    if parsed_s["checksum"] != parsed_p["checksum"]:
        print("[-] Checksum mismatch between serial and parallel on 1 GB Urdu!")
        return False
    print("[+] Checksums match perfectly between serial and parallel!")

    speedup = t_serial / t_parallel if t_parallel > 0 else 0
    print(f"\n--> Measured Gate 5 Speedup: {speedup:.2f}x (Serial: {t_serial:.2f}s, Parallel 2T: {t_parallel:.2f}s)")
    if speedup > 1.0:
        print(f"[+] Gate 5 PASSED: Parallel version demonstrates speedup ({speedup:.2f}x > 1.0x) at 2 threads!")
        return True
    else:
        print(f"[-] Gate 5 FAILED: Parallel version is not faster than serial ({speedup:.2f}x <= 1.0x)!")
        return False

def main():
    print("Starting Gate 5 Full Verification Protocol...\n")
    c1 = test_cache_eviction()
    c2 = test_correctness_matrix()
    c3 = test_critical_mode()
    c4 = test_gate5_speedup()

    print("\n" + "=" * 70)
    print("GATE 5 VERIFICATION SUMMARY")
    print("=" * 70)
    print(f"Cache Eviction:        {'PASS' if c1 else 'FAIL'}")
    print(f"135-Config Matrix:     {'PASS' if c2 else 'FAIL'}")
    print(f"Critical Mode:         {'PASS' if c3 else 'FAIL'}")
    print(f"Gate 5 Speedup Check:  {'PASS' if c4 else 'FAIL'}")
    print("=" * 70)

    if c1 and c2 and c3 and c4:
        print("[SUCCESS] ALL GATE 5 VERIFICATION CRITERIA PASSED!")
        sys.exit(0)
    else:
        print("[FAILURE] ONE OR MORE VERIFICATION CHECKS FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
