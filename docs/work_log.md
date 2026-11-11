# PDC Project #23: Engineering & Audit Work Log

## Project Information
- **Course:** Parallel and Distributed Computing (CS 3006), FAST-NUCES Karachi Campus
- **Project Topic:** #23 — Parallel Word Count / Text Processing using OpenMP
- **Team Member:** Ali Mahdi
- **Hardware:** HP EliteBook 820 G4, Intel Core i5-7300U @ 2.60GHz, 16 GB RAM, Fedora Linux 44
- **Working Directory:** `/home/iamblitz/Documents/PDC_Parallel_Keyword_and_Trend_Analyzer`

---

## 2026-11-10 / 2026-11-11: Phase 1 — Setup & Initialization

### Actions & Decisions
1. **Repository & Directory Configuration:**
   - Initialized Git repository at `/home/iamblitz/Documents/PDC_Parallel_Keyword_and_Trend_Analyzer`.
   - Created project directories: `src/`, `include/`, `python/`, `tests/`, `benchmarks/`, `docs/`, `data/raw/`, `data/decompressed/`, `data/samples/`, `results/`, `bin/`, `build/`.
   - Added comprehensive `.gitignore` ignoring build binaries, Python virtual environments, and large/sample data (`data/raw/`, `data/decompressed/`, `data/samples/`).
2. **Toolchain Verification:**
   - Compiler: `g++ (GCC) 16.2.1 20261029 (Red Hat 16.2.1-3)` with OpenMP support.
   - Python: `Python 3.14.10`.
   - Cache control: `fincore` (util-linux 2.41.6) confirmed available.
   - CPU scaling: All 4 logical cores confirmed running on the `performance` governor via `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`.
   - Storage: 408 GB available on `/dev/nvme0n1p3` (Btrfs NVMe SSD mounted on `/home`).
3. **Documentation:**
   - Documented hardware and system environment in `docs/environment.md`.
   - Synced approved `implementation_plan.md` into repository root.
4. **Verification Gate 1:**
   - Build and execute minimal OpenMP sanity check program verifying multithreading, thread ID assignment, and reduction arithmetic.

### Pre-Phase 3 Refinements (Counting Rules & Verification Spec)
- **RFC 3629 UTF-8 Validation:** Updated `docs/counting_rules.md` to strictly reject overlongs, surrogates, and code points above U+10FFFF. Each ill-formed sequence acts as one separator and never consumes a following valid ASCII byte.
- **Additional Code Points:**
  - Separators: added Unicode spaces `U+2000`–`U+200A`, guillemets `U+00AB` (`«`) and `U+00BB` (`»`).
  - Transparently stripped: added LRM (`U+200E`), RLM (`U+200F`), ALM (`U+061C`), ZWSP (`U+200B`), and WJ (`U+2060`).
- **Boundary Adjustment:** `adjust(b)` returns file size when $b \ge \text{size}$ or when no whitespace follows $b$.
- **Resource Monitoring:** Enforce 12 GB memory cap by polling `VmHWM` in `/proc/<pid>/status`; report `ru_maxrss` via `getrusage` after each run.
- **Verification Strategy:** Gate 5 correctness matrix runs on 50 MB samples; Gate 5 speedup check runs on the 1 GB Urdu piece.
- **Viva Defense Hierarchy:** Credit private per-thread hash tables as the primary defense against false sharing, with `alignas(64)` as secondary.

### Phase 3: Reference Implementation & Test Suite (Completed)
- **Specification:** Refined `docs/counting_rules.md` to define explicit tokenization pipeline order:
  1. Strip ignorable code points
  2. Normalize (ASCII lowercase, Yeh U+06CC, Kaf U+06A9)
  3. Apply hashtag rule (# immediately before token char is retained)
  4. Apply 64-byte limit on result
- **Python Reference:** Built `python/reference_counter.py` using `errors="surrogateescape"`, treating surrogates U+DC80..U+DCFF as separators while authentic U+FFFD is treated as a valid token character.
- **Test Suite:** Built `python/test_runner.py` and 16 comprehensive test fixtures in `tests/`, including `16_replacement_char_ufffd.txt`.
- **Gate 3 Verification:** 16/16 test fixtures passed with 100% agreement against hand-checked ground truth table.
- **50 MB Sample Baselines Computed:**
  - `sample_en.txt`: 8,927,118 tokens, 120,848 unique, checksum `0xfcba47316275e019`
  - `sample_ur.txt`: 6,218,925 tokens, 121,117 unique, checksum `0x0a6932987cb0432a`
  - `sample_ur_rom.txt`: 9,171,954 tokens, 555,427 unique, checksum `0x9bd596a5b0165b82`

### Phase 4: High-Performance Serial C++ Engine (Completed)
- **C++ Modules Implemented:**
  - `include/types.hpp`: Stage timers, run configuration, and deterministic word ordering.
  - `include/counting_rules.hpp`: Character classification, RFC 3629 UTF-8 validation, in-place normalization, boundary lookahead.
  - `include/frequency_table.hpp`: Baseline implementation using `std::unordered_map<std::string, uint64_t>`.
  - `include/checksum.hpp`: Canonical 64-bit FNV-1a hash mixed with 64-bit word count.
  - `include/file_reader.hpp` & `src/file_reader.cpp`: Memory-mapped I/O (`mmap`) with `posix_fadvise(POSIX_FADV_DONTNEED)`.
  - `include/output_writer.hpp` & `src/output_writer.cpp`: Deterministic CSV writer (count desc, raw byte asc).
  - `include/resource_monitor.hpp`: Polling `VmHWM` in `/proc/<pid>/status` and recording `ru_maxrss`.
  - `src/main.cpp`: CLI driver for serial mode.
- **Verification Gate 4:**
  - Automated verification ([`tests/verify_cpp_engine.py`](file:///home/iamblitz/Documents/PDC_Parallel_Keyword_and_Trend_Analyzer/tests/verify_cpp_engine.py)) executed across all 16 fixtures: **16/16 passed** with bit-identical counts and checksums.
  - Verified on all three 50 MB sample files:
    - `sample_en.txt`: checksum `0xfcba47316275e019` (matches reference bit-for-bit, 1.96 s)
    - `sample_ur.txt`: checksum `0x0a6932987cb0432a` (matches reference bit-for-bit, 1.68 s)
    - `sample_ur_rom.txt`: checksum `0x9bd596a5b0165b82` (matches reference bit-for-bit, 2.54 s)
  - Baseline serial benchmarks recorded:
    - 1 GB Urdu piece: 45.37 s counting, 46.28 s total, 22.12 MB/s, 127.8M tokens, checksum `0x8980f4f8a5ec9631`.
    - Full 5.70 GB Urdu dataset: 187.62 s counting, 190.32 s total, 30.68 MB/s, 728.6M tokens, checksum `0x6efa5f6a92a9d4fb`. Peak RSS 1.62 GB.

### Phase 5: Parallel OpenMP Implementations (User Reduction & Critical) (Completed)
- **Parallel Chunking & Boundary Adjustment:**
  - Implemented `include/chunking.hpp` with nominal chunk size $C$ and `adjust(b)` advancing to the first $p \ge b$ where `byte[p-1]` is ASCII whitespace (`0x20`, `0x09`, `0x0A`, `0x0D`), returning `file_size` if $b \ge \text{size}$ or no whitespace follows.
- **OpenMP User-Defined Reduction:**
  - Declared `#pragma omp declare reduction(TableMerge : pdc::FrequencyTable : omp_out.merge(omp_in)) initializer(omp_priv = pdc::FrequencyTable())`.
  - OpenMP loop iterations over chunks with chunk parameter 1 (`schedule(runtime)` configured via `omp_set_schedule(kind, 1)`).
  - Private per-thread hash tables credited as primary defense against false sharing; secondary defense with `alignas(64)` per-thread finish timers (`ThreadTimer`).
  - Stage timings cleanly isolated: `timers.count_time` records time until last thread finishes chunks; `timers.merge_time` records time from last thread finish until end of parallel reduction region.
- **Contention Demonstration (Critical Mode):**
  - Implemented `tokenize_chunk_critical` updating a single shared table inside `#pragma omp critical(critical_table_lock)`.
- **Verification Gate 5 (All Passed):**
  - Cache eviction verified: `posix_fadvise(POSIX_FADV_DONTNEED)` evicted 100% of pages (resident pages dropped from 12,802 to 0 confirmed via `fincore`).
  - Full 135-combination matrix tested on 50 MB sample files across 3 languages $\times$ 5 thread counts (1, 2, 3, 4, 8) $\times$ 3 chunk sizes (64KB, 1MB, 16MB) $\times$ 3 schedules (static, dynamic, guided): **135/135 passed** with exact ground-truth checksum matches.
  - Critical mode verified on sample: exact ground truth checksum match (`0xfcba47316275e019`).
  - Gate 5 Speedup on 1 GB Urdu piece: Serial 31.65 s vs Parallel 2 Threads 17.08 s $\to$ **1.85x speedup ($> 1.0\times$)** with bit-identical checksum (`0x8980f4f8a5ec9631`).
  - ASan + UBSan build (`bin/wordcount_san`) compiled and verified on all fixtures and samples with 0 errors.

### Phase 6: Benchmarks & Empirical Analysis (Completed)
- **Calibration & Checkpoint 2:**
  - Primary Size calibrated to 2048 MB Urdu prefix (serial baseline: 82.33 s, meeting the >= 60 s threshold).
  - CPU governor locked to `performance` on all cores; power profile and AC power verified online.
- **Benchmark Execution (E1 to E6):**
  - Executed all 223 benchmark runs across E1 through E6 with `OMP_PROC_BIND=close`, `OMP_PLACES=threads`, 1 discarded warm-up + 5/3 timed interleaved repetitions, and 15-minute timeout.
  - Logged all data points to `results/benchmark_master.csv` with 19 required columns.
  - Verified 100% bit-identical checksums across all parallel runs and thread counts.
  - Peak memory usage remained under 2.57 GB (strictly bounded within the 12 GB cap).
- **Publication Plots Generated (9 Figures):**
  - `plot1_execution_time_vs_threads.png`: Execution time vs threads (E1).
  - `plot2_speedup_vs_threads.png`: Speedup vs ideal linear scaling (E1).
  - `plot3_efficiency_vs_threads.png`: Parallel efficiency highlighting 2 physical cores vs Hyper-Threading (E1).
  - `plot4_time_breakdown_stacked.png`: Stacked stage time breakdown (E1).
  - `plot5_e2_implementation_comparison.png`: Serial vs Critical contention vs Reduction (E2).
  - `plot6_e3_schedule_chunk_comparison.png`: Static vs Dynamic vs Guided across chunk sizes (E3).
  - `plot7_e4_input_size_scaling.png`: Scaling from 256 MB to 5.7 GB (E4).
  - `plot8_e5_cold_vs_warm_cache.png`: Cold cache vs warm cache on 1 GB and 2 GB (E5).
  - `plot9_e6_multilingual_throughput.png`: Multilingual throughput across Urdu, Roman Urdu, and English (E6).
- **Verification Gate 6:** Complete data across all experiments, all 9 figures generated from CSV data, 100% checksum agreement.

### Phase 7: Academic Research Package & Final Deliverables (Completed)
- **Academic Project Report:** Authored `docs/project_report.md` (abstract, intro, implementation, setup at FAST-NUCES Karachi Campus, empirical results tied directly to benchmark CSV rows, Amdahl/Karp-Flatt analysis, caching evaluation, limitations, and conclusion).
- **Code Walkthrough:** Authored `docs/code_walkthrough.md` with complete architectural explanation, `adjust(b)` chunking proofs, OpenMP user-defined reduction, and memory hierarchy.
- **Viva Defense Preparation:** Authored `docs/viva_preparation.md` with 25 comprehensive technical questions and detailed answers.
- **Root README:** Authored `README.md` with one-command build, verification, and benchmark execution instructions.
- **Verification Gate 7:** All deliverables authored, verified, and committed. Checkpoint 3 reached.
