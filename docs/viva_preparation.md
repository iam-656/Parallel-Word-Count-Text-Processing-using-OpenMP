# PDC #23: Comprehensive Viva Defense & Interview Preparation Guide

**Course:** Parallel and Distributed Computing (CS 3006)  
**Institution:** FAST-NUCES Karachi Campus  
**Project:** Parallel Keyword & Trend Analyzer using OpenMP (Project #23)  
**Target Architecture:** Dual-Core Intel Core i5-7300U (2 Physical Cores, 4 Threads via Hyper-Threading, 16 GB DDR4 RAM)

---

## Section 1: Parallel Computing Theory & Performance Laws

### Q1: What is Amdahl's Law, and how does it apply to this parallel word count project?
**Answer:**  
Amdahl's Law defines the theoretical maximum speedup of a program when using $p$ parallel processors, given that a fraction $s$ of the program is strictly serial:
$$\text{Speedup}(p) = \frac{1}{s + \frac{1 - s}{p}}$$
As $p \to \infty$, the maximum theoretical speedup is bounded by $\frac{1}{s}$.

In our application:
- **Serial components ($s$):** Sequential file opening and `mmap` initialization (`read_time`), final hash table reduction merge (`merge_time`), and serial sorting of top words plus CSV file writing (`write_time`).
- **Parallel component ($1 - s$):** UTF-8 decoding, character classification, normalization, and token accumulation into thread-private hash tables (`count_time`).
Because $s > 0$, speedup inevitably plateaus as thread count increases, regardless of core availability.

---

### Q2: How is the Karp-Flatt metric calculated, and why is it superior to simply looking at Amdahl's serial fraction?
**Answer:**  
While Amdahl's Law assumes a fixed, static serial fraction $s$, real parallel systems suffer from parallel overheads (thread synchronization, reduction merges, lock contention, memory bus saturation, and scheduling overhead). The **Karp-Flatt metric** ($e$) measures the *experimentally observed* serial fraction:
$$e = \frac{\frac{1}{\text{Speedup}} - \frac{1}{p}}{1 - \frac{1}{p}}$$
**Interpretation:**
- If $e$ remains constant as thread count $p$ increases, speedup saturation is primarily caused by inherently serial algorithmic code (Amdahl's serial bottleneck).
- If $e$ increases as $p$ grows, the efficiency loss is driven by parallel overheads, such as thread coordination, memory bus contention, or synchronization latency.

---

### Q3: What is Gustafson's Law, and how does it contrast with Amdahl's Law in our experiments?
**Answer:**  
Amdahl's Law models **strong scaling** (fixed problem size, increasing processors). Gustafson's Law models **weak scaling** (workload scales proportionally with processors):
$$\text{Scaled Speedup}(p) = s + p(1 - s) = p - s(p - 1)$$
In our benchmark suite:
- **Experiment E1 (Strong Scaling):** Measures Amdahl's Law on a fixed 2048 MB dataset while scaling threads from 1 to 8.
- **Experiment E4 (Input Size Scaling):** Tests how parallel efficiency improves as the workload scales from 256 MB to 5.7 GB, demonstrating that parallel overheads become negligible relative to large computation volumes.

---

## Section 2: Hardware Architecture & Multi-Core Execution

### Q4: Explain the physical hardware topology of the HP EliteBook 820 G4 and its impact on parallel scaling.
**Answer:**  
The host system features an **Intel Core i5-7300U (Kaby Lake)** processor:
- **Physical Sockets:** 1
- **Physical Cores:** 2 physical execution cores.
- **Logical CPUs (Hyper-Threading):** 4 logical threads (2 threads per core).
- **Cache Hierarchy:**
  - L1 Data Cache: 32 KB per core.
  - L2 Unified Cache: 256 KB per core.
  - L3 Shared Smart Cache: 3 MB shared across all cores.

**Impact on Scaling:**
1. **From 1 to 2 threads:** Speedup scales near-linearly ($\approx 1.85\times$ to $1.92\times$) because each thread runs on an independent physical core with dedicated ALUs, execution units, and private L1/L2 caches.
2. **From 2 to 4 threads:** Speedup increases moderately ($\approx 2.1\times$ to $2.35\times$) because Hyper-Threading allows logical sibling threads to share execution pipelines during memory stalls, but cannot double physical compute throughput.
3. **Beyond 4 threads (6 and 8 threads):** Speedup flatlines or slightly degrades due to **thread oversubscription**, CPU time-slicing, and operating system context-switching overhead.

---

### Q5: What is Hyper-Threading (Simultaneous Multithreading - SMT), and why doesn't 4 threads give a 4x speedup on 2 physical cores?
**Answer:**  
Hyper-Threading duplicates architectural state registers (program counter, control registers) while sharing the core's underlying physical execution units (ALUs, vector units, branch predictors) and caches. When one thread stalls waiting for a cache miss or memory load, the core switches execution pipelines to the sibling thread.

Because our tokenizer is compute-intensive (executing tight UTF-8 decoding and hash table insertions), both threads actively compete for the same physical execution units and L1 cache ports. Thus, Hyper-Threading yields a $\sim 15\%$ to $25\%$ throughput boost, never a $2\times$ doubling per core.

---

### Q6: What is the Memory Bandwidth Bottleneck, and how does it manifest in parallel word counting?
**Answer:**  
Word frequency counting involves high-volume sequential memory reads and frequent hash table lookups. When 4 threads concurrently stream gigabytes of data through memory, they compete for the shared L3 cache (3 MB) and the single dual-channel DDR4 memory controller ($\sim 34\text{ GB/s}$ peak bandwidth). Once memory bus throughput saturates, additional CPU cores spend idle cycles waiting on DRAM bus transactions, capping maximum achievable speedup.

---

## Section 3: Cache Coherence, False Sharing & Memory Hierarchy

### Q7: What is False Sharing, and how did you prevent it in your implementation?
**Answer:**  
**False sharing** occurs in symmetric multiprocessing (SMP) systems when threads on different cores modify distinct, independent variables that happen to reside within the same 64-byte CPU cache line. When Core 1 updates its variable, the MESI cache coherence protocol marks the entire 64-byte line as *Invalid* in Core 2's L1 cache, forcing Core 2 to reload the line from L3 or DRAM, creating severe bus contention and performance degradation ("cache line bouncing").

**Our Two-Tier Defense Strategy:**
1. **Primary Defense — Private Per-Thread Tables:** Each thread counts into an independent `pdc::FrequencyTable` allocated on its private stack and heap via OpenMP User-Defined Reduction. Threads never write to common memory during chunk processing.
2. **Secondary Defense — Explicit Cache-Line Padding (`alignas(64)`):** For shared thread finish timers (`thread_finish[tid]`), each element is padded to 64 bytes using `struct alignas(64) ThreadTimer { double finish_time; };`, ensuring each thread's timer occupies a distinct cache line.

---

### Q8: Describe the MESI Cache Coherence Protocol and how false sharing interacts with it.
**Answer:**  
The MESI protocol maintains cache consistency across multi-core processors using four states:
- **M (Modified):** The cache line is present only in the current core's cache and is dirty (modified relative to main memory).
- **E (Exclusive):** The line is clean and present only in the current core's cache.
- **S (Shared):** The line is clean and may be cached in multiple cores.
- **I (Invalid):** The line does not contain valid data.

When two threads falsely share a cache line:
1. Thread 1 writes to variable $A$ $\to$ Line transitions to **Modified** on Core 1; Core 2's cache line transitions to **Invalid**.
2. Thread 2 attempts to write to variable $B$ on the same line $\to$ Invalidation miss occurs. Core 2 must broadcast on the interconnect, forcing Core 1 to flush its dirty line, transitioning to **Modified** on Core 2.
3. This continuous ping-ponging ("cache sloshing") degrades throughput by orders of magnitude.

---

## Section 4: OpenMP Architecture & Implementation Specifics

### Q9: How does OpenMP User-Defined Reduction (`#pragma omp declare reduction`) work?
**Answer:**  
Introduced in OpenMP 4.0, User-Defined Reductions extend parallel reduction to custom C++ classes and data structures:
```cpp
#pragma omp declare reduction(TableMerge : pdc::FrequencyTable : omp_out.merge(omp_in)) \
    initializer(omp_priv = pdc::FrequencyTable())
```
**Mechanism:**
1. **Initializer:** At parallel region entry, each thread instantiates a private, empty `pdc::FrequencyTable` (`omp_priv`).
2. **Parallel Accumulation:** Threads process loop iterations (chunks) and populate their private `omp_priv` tables without locks or inter-thread communication.
3. **Combiner:** At the end of the parallel loop, OpenMP automatically executes the combiner clause `omp_out.merge(omp_in)`, iteratively folding the private tables (`omp_in`) into the master table (`omp_out`).

---

### Q10: Why did you use `schedule(runtime)` with chunk parameter 1?
**Answer:**  
In our design, file chunks are pre-computed using the whitespace-adjusted boundary function `adjust(b)`. Each chunk is a self-contained unit of work representing several megabytes (e.g., 16 MB).
- The OpenMP loop iterates over the `chunks` vector: `for (size_t i = 0; i < total_chunks; ++i)`.
- By setting schedule chunk parameter to 1 (`omp_set_schedule(sched, 1)`), each iteration dispatches exactly one full 16 MB chunk to a thread.
- `dynamic, 1` provides automatic load balancing: threads that process simpler text chunks immediately claim the next available chunk from the work queue, preventing faster cores from idling while slower cores finish.

---

### Q11: Explain the difference between OpenMP `static`, `dynamic`, and `guided` schedules.
**Answer:**  
- **`static`:** Pre-allocates iterations in round-robin fashion at compile/launch time. Zero runtime scheduling overhead, but susceptible to severe load imbalance if some chunks take longer to tokenize (e.g., dense vocabulary vs. repeated whitespace).
- **`dynamic`:** Threads pull chunk assignments from a shared thread-safe queue at runtime as they finish work. Incurs minor synchronization overhead per chunk, but guarantees optimal load balancing.
- **`guided`:** Starts with large chunk allocations to minimize scheduling overhead, exponentially decreasing chunk size toward 1 as work nears completion to smooth out tail load imbalance.

---

### Q12: Why is the `critical` implementation so much slower than `reduction`?
**Answer:**  
In `critical` mode, every single token addition is serialized under `#pragma omp critical(critical_table_lock)`.
1. **Lock Contention:** With millions of tokens, threads spend $> 90\%$ of their execution time blocked in mutex wait queues.
2. **Cache Line Invalidation:** Every acquisition modifies the mutex and shared hash table buckets, causing continuous cache line invalidations across all CPU cores.
3. **Negative Scaling:** Running critical sections across more threads actually *increases* execution time due to heightened lock contention and thread switching.

---

## Section 5: Chunking, UTF-8 & Unicode Processing

### Q13: Explain your whitespace-adjusted chunking algorithm and why it guarantees zero lost tokens.
**Answer:**  
Nominal byte boundaries $b = k \cdot C$ are adjusted using:
`adjust(b)`: scans forward to the first byte $p \ge b$ such that $\text{byte}[p - 1]$ is an ASCII whitespace character (`' '`, `'\t'`, `'\n'`, `'\r'`).

**Guarantees:**
1. **Zero Gaps/Overlaps:** Chunk $k-1$ ends at $\text{adjust}(k \cdot C)$ and Chunk $k$ starts at $\text{adjust}(k \cdot C)$. The byte intervals are strictly contiguous.
2. **Token Preservation:** Since $\text{byte}[p - 1]$ is ASCII whitespace, the split occurs inside a token separator. A word is never severed across chunk boundaries.
3. **No Inter-Thread Communication:** Boundaries depend solely on the underlying file bytes and nominal offset, allowing chunks to be constructed independently before parallel execution begins.

---

### Q14: Why can ASCII whitespace never appear inside a multi-byte UTF-8 sequence?
**Answer:**  
RFC 3629 defines UTF-8 encoding rules:
- Single-byte ASCII: `00000000` to `01111111` ($0$ to $127$, high bit is $0$).
- Multi-byte lead bytes: `110xxxxx` (2 bytes), `1110xxxx` (3 bytes), `11110xxx` (4 bytes) (high bits $11$).
- Multi-byte continuation bytes: `10xxxxxx` ($128$ to $191$, high bits $10$).

ASCII whitespace characters (`0x20` space, `0x09` tab, `0x0A` linefeed, `0x0D` carriage return) all have their highest bit set to $0$. Because continuation and lead bytes in multi-byte sequences strictly have the highest bit set to $1$, an ASCII whitespace byte **can never occur as part of a multi-byte character**. Therefore, splitting on ASCII whitespace never cuts an Urdu or Arabic multi-byte character.

---

### Q15: What normalization and diacritic rules were implemented for Urdu text?
**Answer:**  
1. **Diacritic / Harakat Stripping:** Short vowels (Fathatan $U+064B$ through Sukun $U+065F$, Superscript Alef $U+0670$) are stripped in-place because Urdu orthography frequently omits them; stripping ensures consistent word frequencies.
2. **Joiners and Control Codes:** Zero-Width Non-Joiner (ZWNJ $U+200C$), Zero-Width Joiner (ZWJ $U+200D$), BOM ($U+FEFF$), and directional marks (LRM, RLM, ALM) are transparently removed without word splitting.
3. **Character Normalization:**
   - Arabic Yeh ($U+064A$) $\to$ Urdu Yeh ($U+06CC$).
   - Arabic Kaf ($U+0643$) $\to$ Urdu Kaf ($U+06A9$).
   - ASCII uppercase $\to$ lowercase.
4. **Hashtag Retention:** `#` immediately preceding a token character is retained as the first byte of the token.
5. **Length Cap:** Normalized tokens $> 64$ bytes are discarded.

---

## Section 6: Systems, Operating System & Benchmarking Rigor

### Q16: How does `mmap` differ from standard `read` or `ifstream`, and why is it faster?
**Answer:**  
- **`read()` / `ifstream`:** Allocates a user-space buffer, performs a system call, and causes the kernel to copy data from the page cache into user space.
- **`mmap()`:** Maps the file's disk blocks directly into the process's virtual memory address space. No data is copied into intermediate buffers. When the tokenizer accesses memory pointers, hardware page tables trigger page faults that map physical memory pages directly. This **zero-copy** architecture maximizes memory bus throughput.

---

### Q17: What is the difference between a Cold Cache and Warm Cache, and how did you verify eviction?
**Answer:**  
- **Warm Cache:** File data has already been read into the Linux page cache (RAM). Access occurs at memory bus speeds ($\sim 20$–$30\text{ GB/s}$) with zero disk I/O.
- **Cold Cache:** Pages are not resident in RAM; the operating system must issue physical read requests to the storage drive (NVMe SSD $\sim 1.5$–$3\text{ GB/s}$).
- **Eviction Verification:** We issue `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` and verify using `/usr/bin/fincore`. Results confirmed that resident pages dropped from $12,802$ ($50\text{ MB}$) to $0$ pages ($0\text{ bytes resident}$), proving true cold-cache conditions without requiring root privileges.

---

### Q18: What is the purpose of thread pinning (`OMP_PROC_BIND=close`, `OMP_PLACES=threads`)?
**Answer:**  
Without thread affinity, the Linux OS scheduler may migrate active threads between different CPU cores to balance system load or thermal conditions. Thread migration invalidates warm L1/L2 caches and forces expensive cache-coherence reloads. Setting `OMP_PROC_BIND=close` pins OpenMP threads to adjacent execution units on the same socket, preserving cache locality and eliminating migration latency.

---

### Q19: How did you ensure benchmark measurements were free from thermal throttling bias?
**Answer:**  
1. **Interleaved Execution:** Within each repetition cycle, thread counts were interleaved ($t = 1, 2, 3, 4, 6, 8$). Heat accumulated from higher thread counts did not systematically penalize any single configuration.
2. **Discarded Warm-ups:** The first run of each experiment was discarded to prime the OS page cache and stabilize CPU frequencies.
3. **AC Power & Governor Verification:** Host was verified running on AC power with CPU scaling governors locked to `performance` on all cores.

---

### Q20: Explain the canonical 64-bit checksum formula and why it is order-independent.
**Answer:**  
$$\text{Checksum} = \sum_{(w, c) \in \text{Table}} \left( \text{fnv1a64}(w) \oplus (c \times \text{0x9e3779b97f4a7c15ULL}) \right) \pmod{2^{64}}$$
Because hash table bucket traversal order varies depending on thread reduction order and bucket insertion sequences, a simple sequential hash would fail to match. Modular addition $(\bmod 2^{64})$ satisfies both associativity and commutativity:
$$A + B \equiv B + A \pmod{2^{64}}$$
Thus, any two frequency tables containing the exact same words and counts are guaranteed to produce the exact same 64-bit checksum, regardless of how chunks were partitioned or threads scheduled.

---

## Section 7: Defense Scenarios & Troubleshooting Questions

### Q21: If you run your program with 64 threads on this laptop, what will happen?
**Answer:**  
Performance will degrade significantly. The laptop has only 2 physical cores and 4 logical execution threads. Spawning 64 threads creates severe **oversubscription**:
1. High context-switching overhead: The operating system scheduler must frequently preempt threads, swapping register states and flushing TLBs.
2. Thread synchronization latency: Merging 64 private hash tables at the end of the reduction loop will take significantly longer than merging 4 tables.
3. Cache thrashing: 64 thread stacks will compete for the limited 3 MB L3 cache, evicting active hash table nodes.

---

### Q22: Why did you choose `std::unordered_map` over `std::map`?
**Answer:**  
- `std::map` is implemented as a Red-Black self-balancing binary search tree. Each insertion requires $O(\log N)$ pointer comparisons, node rebalancing, and pointer chasing, which causes severe cache misses.
- `std::unordered_map` is a hash table providing average $O(1)$ constant-time lookup and insertion. For tens of millions of word counts, $O(1)$ hashing yields orders of magnitude higher throughput.

---

### Q23: Why did your Gate 5 verification require testing 135 different combinations?
**Answer:**  
To definitively prove that our whitespace-adjusted chunking algorithm and OpenMP user-defined reduction are mathematically robust against any combination of:
- **3 Datasets:** English (ASCII), Urdu (complex multi-byte UTF-8 Arabic script), and Roman Urdu (Latin transliteration).
- **5 Thread Counts:** 1, 2, 3, 4, and 8 threads.
- **3 Chunk Sizes:** 64 KB (fine-grained), 1 MB (medium), 16 MB (coarse).
- **3 Scheduling Policies:** Static, Dynamic, Guided.
Every single run produced the exact same 64-bit checksum and token counts as the serial baseline, proving zero race conditions, zero lost tokens, and zero boundary corruptions.

---

### Q24: How did you isolate `merge_time` from `count_time` in the reduction version?
**Answer:**  
In OpenMP User-Defined Reduction, the runtime implicitly performs the reduction merge after threads exit the parallel loop.
1. Each thread logs its completion timestamp into an aligned array: `thread_finish[tid].finish_time = omp_get_wtime();`.
2. The maximum of these timestamps represents the moment the slowest worker thread finished tokenizing chunks (`last_finish_time`).
3. `count_time = last_finish_time - t_count_start`.
4. The parallel loop finishes at `t_parallel_end` after OpenMP completes all `TableMerge` operations.
5. `merge_time = t_parallel_end - last_finish_time`.

---

### Q25: What are the main limitations of this implementation, and how could it be optimized further?
**Answer:**  
1. **Memory Allocator Overhead:** `std::unordered_map` performs individual dynamic heap allocations (`new`) for each unique word node. A custom flat hash table (open addressing with linear probing and contiguous memory backing) would improve cache locality and eliminate allocator locking overhead.
2. **SIMD Vectorization:** UTF-8 classification and whitespace scanning could be accelerated using AVX2 SIMD vector instructions, processing 32 bytes per clock cycle.
3. **Single-Socket Memory Bus:** On dual-core mobile hardware, memory bus saturation caps maximum throughput. Running on multi-channel server architecture (e.g., AMD EPYC or Intel Xeon with 8 memory channels) would yield significantly higher parallel scaling.
