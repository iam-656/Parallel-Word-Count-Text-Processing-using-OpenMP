# PDC #23: Code Walkthrough & Architecture Guide

**Project:** Parallel Word Count / Text Processing using OpenMP (Project #23)  
**Institution:** FAST-NUCES Karachi Campus  
**Course:** Parallel and Distributed Computing (CS 3006)  
**Authors:** PDC Project Team (Imam Ali Mahdi, Hafiz Umer Ahmed, Naveed Ahmed)  
**Target Hardware:** HP EliteBook 820 G4 (Intel Core i5-7300U, 2 Physical Cores, 4 Logical Threads, 16 GB RAM)

---

## 1. Executive Summary & Design Philosophy

The parallel keyword and frequency analyzer is designed to process massive multilingual text corpora (Urdu, Roman Urdu, and English) at tens to hundreds of megabytes per second on resource-constrained multi-core hardware. 

The software architecture is structured into three clean stages:
1. **Stage 1 (Reading & Chunking):** Memory-mapped file access (`mmap`) combined with a whitespace-adjusted chunking algorithm that partitions files into independent, token-safe byte ranges.
2. **Stage 2 (Tokenization & Counting):** RFC 3629-compliant UTF-8 token extraction with custom normalization, followed by multi-threaded accumulation using either OpenMP User-Defined Reductions (`reduction`) or global critical sections (`critical`).
3. **Stage 3 (Aggregation & Deterministic Output):** Top-$N$ word extraction, deterministic tie-breaking, order-independent 64-bit canonical checksum computation, and CSV persistence.

---

## 2. File Reading and Memory Mapping (`src/file_reader.cpp`)

### 2.1 Why `mmap` Over Stream I/O?
Traditional stream I/O (`std::ifstream` or C `fread`) incurs significant kernel-to-user-space buffer copying overhead, system call overhead, and dynamic allocation latency. To achieve maximum throughput:
- We utilize the POSIX `mmap()` system call with `MAP_SHARED` and `PROT_READ`.
- This maps the storage pages of the dataset directly into the process's 64-bit virtual address space.
- The operating system handles paging on-demand via hardware page tables, enabling zero-copy memory reads.
- We issue `madvise(data_, mapped_size_, MADV_SEQUENTIAL)` to signal the Linux kernel readahead algorithm to fetch contiguous physical pages aggressively.

### 2.2 Cache Eviction Protocol (`cold_cache`)
To accurately measure cold-cache I/O versus warm-cache execution (Experiment E5):
- The program invokes `posix_fadvise(fd_, 0, 0, POSIX_FADV_DONTNEED)` before mapping.
- This instructs the Linux page cache manager to invalidate and evict clean disk cache pages associated with the file.
- Cache eviction is verified non-root using `fincore`, proving that 100% of pages are evicted ($0\text{ bytes resident}$) prior to cold-cache benchmarks.

---

## 3. Whitespace-Adjusted Chunking (`include/chunking.hpp`)

### 3.1 The Boundary Problem in Parallel Text Processing
When an arbitrary byte range $[k \cdot C, (k+1) \cdot C)$ is assigned to a thread, words crossing chunk boundaries would ordinarily be split into two truncated tokens (e.g., `"processing"` cut into `"proc"` and `"essing"`), causing word count corruptions and checksum mismatches.

### 3.2 The Boundary Adjustment Function `adjust(b)`
Our algorithm solves this deterministically without communication between threads:
$$\text{adjust}(b) = \begin{cases} 0 & \text{if } b = 0 \\ N & \text{if } b \ge N \\ \min \{ p \ge b \mid \text{byte}[p - 1] \in \{\text{' '}, \text{'\textbackslash t'}, \text{'\textbackslash n'}, \text{'\textbackslash r'}\} \} & \text{if whitespace exists in } [b, N) \\ N & \text{otherwise} \end{cases}$$

Chunk $k$ covers the exact half-open byte interval:
$$[\text{adjust}(k \cdot C), \; \text{adjust}((k + 1) \cdot C))$$

### 3.3 Proof of Correctness & UTF-8 Safety
1. **No Overlaps or Gaps:** The end boundary of chunk $k - 1$ is $\text{adjust}(k \cdot C)$, which is identical to the start boundary of chunk $k$. The union of all chunks covers the entire file $[0, N)$ exactly once.
2. **Token Integrity:** Every adjusted boundary $p$ satisfies the condition that $\text{byte}[p - 1]$ is an ASCII whitespace character (`0x20`, `0x09`, `0x0A`, `0x0D`). Since ASCII whitespace is always a token separator, the cut occurs strictly *between* tokens, never within a token.
3. **Multi-byte UTF-8 Invariance:** In UTF-8 (RFC 3629), multi-byte lead bytes (`0xC0`–`0xFF`) and continuation bytes (`0x80`–`0xBF`) all have the most significant bit set ($1\text{xxxxxxx}$). ASCII whitespace bytes have the most significant bit cleared ($000xxxxx$). Therefore, an ASCII whitespace byte can **never** appear inside a multi-byte sequence (such as Urdu or Arabic characters). Boundary adjustment is guaranteed never to bisect a multi-byte UTF-8 character.
4. **File Isolation:** A chunk never spans two files. Chunks are generated per mapped file and aggregated into a work vector.

---

## 4. Tokenizer & Normalization Pipeline (`src/tokenizer.cpp`, `include/counting_rules.hpp`)

The tokenizer scans byte streams sequentially through a strict state machine:

### 4.1 Strict RFC 3629 UTF-8 Validation
- Rejects overlong encodings (e.g., `0xC0 0x80` for NUL).
- Rejects surrogate code points ($U+D800$ to $U+DFFF$), matching Python's strict standard library behavior.
- Rejects values exceeding the Unicode maximum ($U+10FFFF$).
- Invalid UTF-8 byte sequences act as individual token separators and **never** consume valid subsequent ASCII bytes.
- Genuine Unicode Replacement Characters ($U+FFFD$) in the input are treated as legitimate token characters.

### 4.2 Code Point Classification & Stripping
- **Ignorable Characters (Transparently Stripped):**
  - Zero-Width Non-Joiner (ZWNJ, $U+200C$) and Zero-Width Joiner (ZWJ, $U+200D$).
  - Byte Order Mark (BOM, $U+FEFF$), Zero-Width Space ($U+200B$), Word Joiner ($U+2060$).
  - Bidirectional marks: LRM ($U+200E$), RLM ($U+200F$), ALM ($U+061C$).
  - Arabic/Urdu short vowels and diacritics: Fathatan through Sukun ($U+064B$–$U+065F$), Superscript Alef ($U+0670$).
  - Ignorables do not split words; they are discarded in-place.
- **Normalization:**
  - ASCII uppercase ($A$–$Z$) $\to$ lowercase ($a$–$z$).
  - Arabic Yeh ($U+064A$) $\to$ Urdu Yeh ($U+06CC$).
  - Arabic Kaf ($U+0643$) $\to$ Urdu Kaf ($U+06A9$).
- **Hashtag Rule:**
  - If a `#` is immediately followed by a token character, the `#` is retained as the first byte of the word token (e.g., `#urdu`, `#pdc2026`).
  - An isolated `#` surrounded by separators or whitespace is treated as a regular separator.
- **Token Length Constraint:**
  - Tokens exceeding 64 bytes in their normalized UTF-8 representation are discarded.

---

## 5. Parallelization Architecture (`src/main.cpp`)

### 5.1 OpenMP User-Defined Reduction (`reduction`)
The primary parallel engine employs OpenMP 4.0+ User-Defined Reductions:
```cpp
#pragma omp declare reduction(TableMerge : pdc::FrequencyTable : omp_out.merge(omp_in)) \
    initializer(omp_priv = pdc::FrequencyTable())
```
Inside `main.cpp`:
```cpp
#pragma omp parallel for schedule(runtime) reduction(TableMerge : global_table)
for (size_t i = 0; i < total_chunks; ++i) {
    pdc::tokenize_chunk(chunks[i].start, chunks[i].end, global_table);
    thread_finish[omp_get_thread_num()].finish_time = omp_get_wtime();
}
```

### 5.2 Memory Hierarchy & False Sharing Defense
False sharing occurs when multiple CPU cores modify distinct variables that reside within the same 64-byte L1/L2 cache line, triggering costly cache-coherence invalidation cycles (MESI protocol bus transactions).

Our defense strategy follows a strict two-tier hierarchy:
1. **Primary Defense — Private Per-Thread Hash Tables:**
   - Under the OpenMP user-defined reduction, `omp_priv` is an automatic instance of `pdc::FrequencyTable` allocated on each thread's independent call stack.
   - Each thread operates exclusively on its private `std::unordered_map`, allocating node buckets in thread-local heap areas.
   - Because no two threads ever write to the same table during chunk processing, cache lines are never invalidated between cores during the counting phase.
2. **Secondary Defense — Explicit Cache-Line Padding (`alignas(64)`):**
   - For thread finish instrumentation, shared arrays indexed by thread ID (`thread_finish[tid]`) could suffer from false sharing if packed contiguously.
   - We encapsulate each timer inside `struct alignas(64) ThreadTimer { double finish_time; };`.
   - This guarantees that each thread's write target occupies its own dedicated 64-byte cache line, completely eliminating false sharing.

### 5.3 Stage Timing Isolation
To understand where parallel speedup saturates (Amdahl's Law), we isolate stage timings cleanly:
- `timers.read_time`: Time taken by `mmap` and boundary adjustment chunk creation.
- `timers.count_time`: Time between parallel loop entry and the moment the slowest worker thread finishes its last chunk (`last_finish_time - t_count_start`).
- `timers.merge_time`: Time elapsed from the last thread finish to the exit of the parallel reduction region (`t_parallel_end - last_finish_time`).
- `timers.write_time`: Time spent sorting word entries and generating output CSV files.

### 5.4 Contention Demonstration (`critical`)
To illustrate the severe performance degradation caused by lock contention:
```cpp
#pragma omp parallel for schedule(runtime)
for (size_t i = 0; i < total_chunks; ++i) {
    pdc::tokenize_chunk_critical(chunks[i].start, chunks[i].end, global_table);
}
```
In `tokenize_chunk_critical`, all threads compete for a single mutex:
```cpp
#pragma omp critical(critical_table_lock)
{
    shared_table.add(token_buf, token_len);
}
```
This forces all thread updates into a serialized bottleneck, demonstrating why coarse-grained synchronization fails in multi-threaded data processing.

---

## 6. Order-Independent Checksum Formula (`include/checksum.hpp`)

To verify that parallel reduction across varying thread counts, chunk sizes, and scheduling policies produces bit-identical results without dumping multi-gigabyte CSVs, we compute a 64-bit canonical checksum:

$$\text{Checksum} = \sum_{(w, c) \in \text{Table}} \left( \text{fnv1a64}(w) \oplus (c \times \text{0x9e3779b97f4a7c15ULL}) \right) \pmod{2^{64}}$$

- **FNV-1a 64-bit Hash:** High-entropy dispersion of UTF-8 token bytes.
- **Golden Ratio Multiplier (`0x9e3779b97f4a7c15ULL`):** Multiplies 64-bit frequency counts to diffuse small integer patterns across all 64 bits.
- **Commutative Modular Addition:** Modular addition $(\bmod 2^{64})$ is associative and commutative. Regardless of the iteration order of hash table buckets, the resulting checksum is strictly identical.

---

## 7. Memory Protection & Resource Monitoring (`include/resource_monitor.hpp`)

Per project constraints, peak memory usage must never exceed 12 GB on the 16 GB host:
- The tokenizer polls memory usage every $\sim 524,000$ tokens (`tokens_processed & 0x7FFFF == 0`).
- It reads current Resident Set Size (`VmRSS`) from `/proc/self/status`. If memory exceeds 12 GB, it logs a fatal error and cleanly aborts.
- At process termination, it queries `getrusage(RUSAGE_SELF, &usage)` to capture `ru_maxrss` and reads `VmHWM` (Peak High Water Mark) from `/proc/self/status`. Both metrics are recorded in every benchmark output row.
