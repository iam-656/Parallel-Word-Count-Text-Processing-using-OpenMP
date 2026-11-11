# Parallel Keyword & Trend Analyzer (OpenMP)

**Course:** Parallel and Distributed Computing (CS 3006)  
**Institution:** FAST-NUCES Karachi Campus  
**Project:** #23 — Parallel Word Count & Multilingual Text Processing  
**Authors:** PDC Project Team (Partner: Ali Mahdi)  
**Target Environment:** Linux x86_64, GCC 16+ with OpenMP 4.5+

---

## Overview

The **Parallel Keyword & Trend Analyzer** is a high-performance C++17 OpenMP CLI application engineered to analyze word frequencies and keywords across multi-gigabyte text corpora in **Urdu** (Arabic script), **Roman Urdu** (Latin transliteration), and **English**.

The project implements and empirically contrasts three execution paradigms:
1. **`serial`:** Single-threaded baseline for Amdahl's Law speedup calculations.
2. **`critical`:** Coarse-grained shared table synchronization guarded by `#pragma omp critical` to demonstrate the severe penalties of lock contention.
3. **`reduction`:** The primary high-performance engine using OpenMP 4.0+ User-Defined Reductions (`#pragma omp declare reduction`) with thread-private hash tables and whitespace-adjusted chunking.

---

## Key Features

- **Strict RFC 3629 UTF-8 Validation:** Rejects overlong encodings and surrogate pairs ($U+D800$–$U+DFFF$); treats invalid sequences as non-consuming separators.
- **Multilingual Urdu Normalization:** Transparently strips diacritics/A'rab ($U+064B$–$U+065F$), joiners (ZWNJ $U+200C$, ZWJ $U+200D$), BOM ($U+FEFF$), and directional marks; maps Arabic Yeh ($U+064A \to U+06CC$) and Kaf ($U+0643 \to U+06A9$); preserves `#hashtag` syntax.
- **Zero-Copy Memory-Mapped I/O:** Uses POSIX `mmap()` with kernel readahead (`madvise(MADV_SEQUENTIAL)`).
- **Whitespace-Adjusted Chunking:** Dynamically adjusts nominal chunk boundaries $b = k \cdot C$ forward to the nearest ASCII whitespace byte (`adjust(b)`), guaranteeing zero severed words and 100% thread isolation without communication.
- **False Sharing Defense Hierarchy:** Thread-private hash tables as primary defense; 64-byte aligned finish timers (`alignas(64)`) as secondary defense.
- **Order-Independent 64-bit Checksum:**
  $$\text{Checksum} = \sum_{(w, c) \in \text{Table}} (\text{fnv1a64}(w) \oplus (c \times \text{0x9e3779b97f4a7c15ULL})) \pmod{2^{64}}$$
- **Active Memory Cap Monitoring:** Continuous polling of `VmRSS` and `VmHWM` against a strict 12 GB hardware limit.

---

## Prerequisites

- **Compiler:** `g++` (GCC 11+ or newer) with OpenMP support (`-fopenmp`)
- **Python:** Python 3.10+ (standard library only; `matplotlib` and `pandas` required for plotting)
- **Linux Tools:** `make`, `fincore` (from `util-linux`)

---

## Quick Start: One-Command Build & Test

### 1. Build the Binary
```bash
# Optimized release build (default)
make release

# AddressSanitizer + UndefinedBehaviorSanitizer debug build
make sanitizer
```
The executable is generated at `bin/wordcount` (or `bin/wordcount_san`).

### 2. Run Verification Tests
```bash
# 1. Verify Python reference counter against all 16 hand-checked fixtures
python3 python/test_runner.py

# 2. Verify C++ serial engine produces byte-identical results to Python reference
python3 tests/verify_cpp_engine.py

# 3. Verify Gate 5 OpenMP parallel engine (135 configurations + speedup check)
python3 tests/verify_gate5.py
```

---

## CLI Usage & Options

```bash
./bin/wordcount [options]
```

### Options Reference:
| Option | Short | Description | Default |
|---|---|---|---|
| `--input <files...>` | `-i` | One or more input file paths (required) | — |
| `--mode <mode>` | `-m` | Execution mode: `serial`, `critical`, `reduction` | `serial` |
| `--threads <n>` | `-t` | Number of OpenMP worker threads | `1` |
| `--schedule <sched>` | `-s` | OpenMP schedule: `static`, `dynamic`, `guided` | `dynamic` |
| `--chunk-size <bytes>` | `-c` | Nominal chunk size in bytes | `16777216` (16 MB) |
| `--top <n>` | | Number of highest frequency words to report | `100` |
| `--dump-all` | | Dump full word frequency dictionary to CSV | `false` |
| `--cold-cache` | | Invalidate and evict file pages from OS page cache | `false` |
| `--max-mb <mb>` | | Cap maximum input megabytes read from file | `0` (unlimited) |
| `--output-dir <dir>` | `-o` | Target directory for CSV outputs | `results` |
| `--log-file <file>` | | Append benchmark timing row to specified CSV | `""` |
| `--help` | `-h` | Display help and usage message | — |

### Example Commands:

```bash
# 1. Parallel reduction on Urdu dataset with 4 threads and dynamic scheduling
./bin/wordcount -i data/decompressed/ur.txt -m reduction -t 4 -s dynamic -c 16777216

# 2. Benchmark serial baseline on 2 GB Urdu prefix
./bin/wordcount -i data/decompressed/ur.txt -m serial --max-mb 2048 -o results

# 3. Test critical mode lock contention on sample file
./bin/wordcount -i data/samples/sample_en.txt -m critical -t 2 -c 1048576

# 4. Cold-cache evaluation with full dictionary dump
./bin/wordcount -i data/samples/sample_ur.txt -m reduction -t 4 --cold-cache --dump-all
```

---

## Benchmarking & Plot Generation

To reproduce the full suite of experiments (**E1 through E6**) and generate the 9 publication figures:

```bash
# Run all benchmark experiments (E1 to E6)
python3 benchmarks/run_benchmarks.py --exp all

# Generate all 9 publication-grade PNG charts with error bars
python3 benchmarks/generate_plots.py
```

Output figures are saved in `results/`:
- `plot1_execution_time_vs_threads.png` — E1: Execution time vs threads
- `plot2_speedup_vs_threads.png` — E1: Speedup vs ideal linear scaling
- `plot3_efficiency_vs_threads.png` — E1: Parallel efficiency vs threads
- `plot4_time_breakdown_stacked.png` — E1: Stacked stage time breakdown
- `plot5_e2_implementation_comparison.png` — E2: Serial vs Critical vs Reduction
- `plot6_e3_schedule_chunk_comparison.png` — E3: Schedules and chunk sizes
- `plot7_e4_input_size_scaling.png` — E4: Dataset size scaling (256 MB to 5.7 GB)
- `plot8_e5_cold_vs_warm_cache.png` — E5: Cold cache vs warm cache
- `plot9_e6_multilingual_throughput.png` — E6: Multilingual processing throughput

---

## Project Structure

```
├── AGENTS.md                  # Detailed course specification and grading criteria
├── Makefile                   # High-performance C++17 build configurations
├── README.md                  # This file
├── benchmarks/
│   ├── generate_plots.py      # Publication-grade plot generation script
│   └── run_benchmarks.py      # Automated benchmark harness (E1–E6)
├── data/
│   ├── checksums.sha256       # SHA-256 manifests for all raw and decompressed data
│   ├── decompressed/          # Full decompressed datasets (Urdu, Roman Urdu, English)
│   ├── raw/                   # Original downloaded archives (.xz)
│   └── samples/               # 50 MB sample files for quick verification
├── docs/
│   ├── code_walkthrough.md    # Plain-English architectural and code walkthrough
│   ├── counting_rules.md      # Ground-truth counting specification and Unicode rules
│   ├── data_report.md         # Dataset sizes, verification, and SHA-256 digests
│   ├── environment.md         # System hardware, CPU governor, and environment dump
│   ├── project_report.md      # Final academic research report
│   ├── viva_preparation.md    # 25+ comprehensive viva defense questions & answers
│   └── work_log.md            # Chronological engineering activity log
├── include/
│   ├── checksum.hpp           # 64-bit order-independent canonical checksum
│   ├── chunking.hpp           # Whitespace-adjusted boundary calculation
│   ├── counting_rules.hpp     # Fast UTF-8 decode, classify, and normalize
│   ├── file_reader.hpp        # POSIX mmap wrapper with posix_fadvise
│   ├── frequency_table.hpp    # High-performance frequency hash table
│   ├── output_writer.hpp      # Deterministic CSV output and log formatter
│   ├── resource_monitor.hpp   # VmRSS/VmHWM memory polling & rusage
│   ├── tokenizer.hpp          # Tokenizer declarations
│   └── types.hpp              # Shared data structures and stage timers
├── python/
│   ├── reference_counter.py   # Ground-truth reference implementation
│   └── test_runner.py         # Verification test harness
├── results/
│   ├── benchmark_master.csv   # Master CSV with all experimental data points
│   └── *.png                  # Generated publication-quality figures
├── src/
│   ├── file_reader.cpp        # mmap and posix_fadvise implementation
│   ├── main.cpp               # OpenMP CLI driver & reduction engine
│   ├── output_writer.cpp      # CSV writing & deterministic tie-breaking
│   └── tokenizer.cpp          # Sequential & critical UTF-8 tokenization
└── tests/
    ├── 01_... to 16_...       # 16 hand-checked edge case test fixtures
    ├── sample_baselines.json  # 50 MB ground-truth tokens & checksums
    ├── verify_cpp_engine.py   # C++ serial vs reference verification
    └── verify_gate5.py        # 135-combination OpenMP matrix verification
```
