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
