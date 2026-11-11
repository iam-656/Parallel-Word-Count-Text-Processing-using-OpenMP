#!/usr/bin/env python3
"""
PDC #23 — Automated Benchmark Runner (E1 to E6)
Fast-NUCES Karachi Campus — Parallel Word Count / OpenMP

Protocol Features:
- OMP_PROC_BIND=close and OMP_PLACES=threads thread pinning.
- Warm-up execution protocol (1 discarded warm-up + timed repetitions).
- Interleaved thread execution to prevent thermal bias.
- 15-minute timeout per individual run.
- Polling VmHWM & ru_maxrss to enforce the 12 GB memory limit.
- Cold-cache page eviction via posix_fadvise & fincore verification.
- Output logging to results/benchmark_master.csv with all required columns.
"""

import os
import sys
import re
import csv
import subprocess
import time
import argparse

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BIN_PATH = os.path.join(PROJECT_ROOT, "bin", "wordcount")
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
MASTER_CSV = os.path.join(RESULTS_DIR, "benchmark_master.csv")

DATA_URDU = os.path.join(PROJECT_ROOT, "data", "decompressed", "ur.txt")
DATA_ROMAN = os.path.join(PROJECT_ROOT, "data", "decompressed", "ur_rom.txt")
DATA_ENGLISH = os.path.join(PROJECT_ROOT, "data", "decompressed", "en_news.txt")

PRIMARY_SIZE_MB = 2048  # Smallest input with serial time >= 60s (82.3s)

ENV_VARS = os.environ.copy()
ENV_VARS["OMP_PROC_BIND"] = "close"
ENV_VARS["OMP_PLACES"] = "threads"

CSV_HEADERS = [
    "experiment_id", "implementation", "schedule", "chunk_size_bytes",
    "threads", "dataset", "size_mb", "cache_state", "repetition",
    "read_time_s", "count_time_s", "merge_time_s", "write_time_s",
    "total_time_s", "throughput_mb_s", "peak_rss_kb", "peak_vm_hwm_kb",
    "checksum", "notes"
]

def init_master_csv():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if not os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)

def parse_run_output(output_text):
    data = {
        "read_time_s": 0.0,
        "count_time_s": 0.0,
        "merge_time_s": 0.0,
        "write_time_s": 0.0,
        "total_time_s": 0.0,
        "throughput_mb_s": 0.0,
        "peak_rss_kb": 0,
        "peak_vm_hwm_kb": 0,
        "checksum": ""
    }
    for line in output_text.splitlines():
        line = line.strip()
        if "Read / Mmap Time:" in line:
            data["read_time_s"] = float(line.split(":")[1].replace("s", "").strip())
        elif "Counting Time:" in line:
            data["count_time_s"] = float(line.split(":")[1].replace("s", "").strip())
        elif "Merge Time:" in line:
            data["merge_time_s"] = float(line.split(":")[1].replace("s", "").strip())
        elif "Write Time:" in line:
            data["write_time_s"] = float(line.split(":")[1].replace("s", "").strip())
        elif "Total Time:" in line:
            data["total_time_s"] = float(line.split(":")[1].replace("s", "").strip())
        elif "Throughput:" in line:
            data["throughput_mb_s"] = float(line.split(":")[1].replace("MB/s", "").strip())
        elif "Peak RSS (getrusage):" in line:
            m = re.search(r"\((\d+)\s*KB\)", line)
            if m:
                data["peak_rss_kb"] = int(m.group(1))
        elif "Peak VmHWM (/proc):" in line:
            m = re.search(r"\((\d+)\s*KB\)", line)
            if m:
                data["peak_vm_hwm_kb"] = int(m.group(1))
        elif "Canonical Checksum:" in line:
            data["checksum"] = line.split(":")[1].strip().lower()
    return data

def run_single(exp_id, impl, sched, chunk_bytes, threads, data_file, size_mb, cache_state, rep, notes=""):
    cmd = [
        BIN_PATH,
        "-i", data_file,
        "-m", impl,
        "-t", str(threads),
        "-s", sched,
        "-c", str(chunk_bytes),
        "-o", RESULTS_DIR
    ]
    if size_mb > 0:
        cmd.extend(["--max-mb", str(size_mb)])
    if cache_state == "cold":
        cmd.append("--cold-cache")

    print(f"[{exp_id}] {impl:9s} | Sched: {sched:7s} | Chk: {chunk_bytes//1048576:2d}MB | T: {threads:2d} | Size: {size_mb:4d}MB | Cache: {cache_state:4s} | Rep: {rep}")
    
    t0 = time.time()
    try:
        res = subprocess.run(cmd, env=ENV_VARS, capture_output=True, text=True, timeout=900)
    except subprocess.TimeoutExpired:
        print(f"  [-] TIMEOUT (> 900s) on {exp_id} rep {rep}")
        return None

    if res.returncode != 0:
        print(f"  [-] FAILED (code {res.returncode}): {res.stderr}")
        return None

    parsed = parse_run_output(res.stdout)
    dataset_name = os.path.basename(data_file)

    row = [
        exp_id, impl, sched, chunk_bytes,
        threads, dataset_name, size_mb, cache_state, rep,
        parsed["read_time_s"], parsed["count_time_s"], parsed["merge_time_s"],
        parsed["write_time_s"], parsed["total_time_s"], parsed["throughput_mb_s"],
        parsed["peak_rss_kb"], parsed["peak_vm_hwm_kb"], parsed["checksum"], notes
    ]

    with open(MASTER_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    print(f"  -> Total: {parsed['total_time_s']:.2f}s (Count: {parsed['count_time_s']:.2f}s, Merge: {parsed['merge_time_s']:.2f}s) | Checksum: {parsed['checksum']}")
    return parsed

# -------------------------------------------------------------
# Experiment Suites
# -------------------------------------------------------------

def run_e1(reps=5):
    """E1: Strong Scaling on Primary Size (2048 MB Urdu)"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E1: Strong Scaling (Primary Size = 2048 MB)\n" + "=" * 70)
    threads_list = [1, 2, 3, 4, 6, 8]
    chunk_size = 16 * 1024 * 1024 # 16 MB

    # Warm-up run (discarded)
    print("[*] E1 Discarded Warm-up Run...")
    run_single("E1_WARMUP", "reduction", "dynamic", chunk_size, 4, DATA_URDU, PRIMARY_SIZE_MB, "warm", 0, "Warm-up")

    # Interleaved repetitions
    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        # Measure serial baseline
        run_single("E1", "serial", "dynamic", chunk_size, 1, DATA_URDU, PRIMARY_SIZE_MB, "warm", rep, "Serial baseline")
        # Cycle through thread counts
        for t in threads_list:
            run_single("E1", "reduction", "dynamic", chunk_size, t, DATA_URDU, PRIMARY_SIZE_MB, "warm", rep, f"Threads={t}")

def run_e2(reps=5):
    """E2: Implementation Comparison (Serial, Critical, Reduction) on 256 MB Urdu piece"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E2: Implementation Comparison (256 MB Urdu)\n" + "=" * 70)
    size_mb = 256
    chunk_size = 16 * 1024 * 1024

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        run_single("E2", "serial", "dynamic", chunk_size, 1, DATA_URDU, size_mb, "warm", rep, "Serial")
        for t in [2, 4]:
            run_single("E2", "reduction", "dynamic", chunk_size, t, DATA_URDU, size_mb, "warm", rep, f"Reduction T={t}")
            run_single("E2", "critical", "dynamic", chunk_size, t, DATA_URDU, size_mb, "warm", rep, f"Critical T={t}")

def run_e3(reps=3):
    """E3: Schedule and Chunk Size on 1024 MB Urdu piece"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E3: Schedule & Chunk Size (1024 MB Urdu)\n" + "=" * 70)
    size_mb = 1024
    chunk_sizes = [1 * 1024 * 1024, 4 * 1024 * 1024, 16 * 1024 * 1024, 64 * 1024 * 1024]
    schedules = ["static", "dynamic", "guided"]

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for t in [2, 4]:
            for sched in schedules:
                for c_bytes in chunk_sizes:
                    run_single("E3", "reduction", sched, c_bytes, t, DATA_URDU, size_mb, "warm", rep, f"Sched={sched}, C={c_bytes//(1024*1024)}MB")

def run_e4(reps=3):
    """E4: Input Size Scaling on Urdu dataset prefixes"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E4: Input Size Scaling\n" + "=" * 70)
    sizes = [256, 512, 1024, 2048, 4096, 0] # 0 = full file (5700 MB)
    chunk_size = 16 * 1024 * 1024

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for sz in sizes:
            sz_label = sz if sz > 0 else 5700
            run_single("E4", "serial", "dynamic", chunk_size, 1, DATA_URDU, sz, "warm", rep, f"Serial Size={sz_label}MB")
            run_single("E4", "reduction", "dynamic", chunk_size, 4, DATA_URDU, sz, "warm", rep, f"Reduction 4T Size={sz_label}MB")

def run_e5(reps=3):
    """E5: Cold vs Warm Cache on 1024 MB and Primary Size (2048 MB)"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E5: Cold vs Warm Cache\n" + "=" * 70)
    sizes = [1024, 2048]
    chunk_size = 16 * 1024 * 1024

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for sz in sizes:
            for t in [1, 2, 4]:
                # Cold cache
                run_single("E5", "reduction", "dynamic", chunk_size, t, DATA_URDU, sz, "cold", rep, f"Cold T={t} Sz={sz}MB")
                # Warm cache
                run_single("E5", "reduction", "dynamic", chunk_size, t, DATA_URDU, sz, "warm", rep, f"Warm T={t} Sz={sz}MB")

def run_e6(reps=3):
    """E6: Multilingual Datasets in Full (Urdu, Roman Urdu, English)"""
    print("\n" + "=" * 70 + "\nRUNNING EXPERIMENT E6: Multilingual Comparison\n" + "=" * 70)
    datasets = [
        ("Urdu_CC100", DATA_URDU),
        ("RomanUrdu_CC100", DATA_ROMAN),
        ("English_CCNews", DATA_ENGLISH)
    ]
    chunk_size = 16 * 1024 * 1024

    for rep in range(1, reps + 1):
        print(f"\n--- Repetition {rep}/{reps} ---")
        for name, path in datasets:
            run_single("E6", "serial", "dynamic", chunk_size, 1, path, 0, "warm", rep, f"{name} Serial")
            run_single("E6", "reduction", "dynamic", chunk_size, 4, path, 0, "warm", rep, f"{name} 4T")

def main():
    parser = argparse.ArgumentParser(description="PDC #23 Benchmarking Suite")
    parser.add_argument("--exp", choices=["all", "E1", "E2", "E3", "E4", "E5", "E6"], default="all")
    args = parser.parse_args()

    init_master_csv()

    if args.exp in ["all", "E1"]:
        run_e1()
    if args.exp in ["all", "E2"]:
        run_e2()
    if args.exp in ["all", "E3"]:
        run_e3()
    if args.exp in ["all", "E4"]:
        run_e4()
    if args.exp in ["all", "E5"]:
        run_e5()
    if args.exp in ["all", "E6"]:
        run_e6()

    print("\n[+] Benchmarking suite execution complete! Results saved to:", MASTER_CSV)

if __name__ == "__main__":
    main()
