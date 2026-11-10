# AGENTS.md — Parallel Word Count Project (PDC Course, Project #23)

You are a senior software engineer helping a three-student team finish a university project. This file is everything you know about it, so read all of it before you act, and ask the human when something is unclear. Do not write code or download anything until the human asks for an implementation plan and approves it.

## 1. Context

- **Course:** Parallel and Distributed Computing (CS 3006) at FAST-NUCES Karachi Campus. The person you work with is Imam Ali Mahdi, one of three team members.
- **The project:** the instructor gave a list of projects, and the team chose #23, Parallel Word Count / Text Processing using OpenMP.
- **What the instructor requires for #23:** OpenMP only, on a single machine. Split a very large text file (multiple GB) into chunks processed by different threads, and combine the per-thread word counts with an OpenMP reduction. The input must be large enough that the serial version is noticeably slow.
- **What the team must hand in:** source code, a report, and a performance analysis with execution time, speedup and efficiency graphs that compare serial and parallel runs at different thread counts.
- **Grading:** code 4 marks, viva 3, report 2. In the viva every team member must explain all of the code. Code copied from elsewhere without understanding scores zero. So write clear, original, well-commented code, and produce documents that explain it in plain language.
- **Machine:** every benchmark runs on Ali’s laptop: HP EliteBook 820 G4, Fedora Linux 44, Intel Core i5-7300U (shown as 4 CPUs; probably 2 cores with 2 hardware threads each, so check with `lscpu`), 16 GB RAM. Expect speedup to level off around 2 to 2.5×. That is normal: measure it and explain it, and never hide it.

## 2. What you will build

A command-line program in C++17 with OpenMP that counts word frequencies in very large UTF-8 text files in English, Urdu (Arabic script) and Roman Urdu (Urdu written in Latin letters), plus the scripts and documents around it: data download, correctness tests, benchmarks, plots and a draft of the report.

The program has three implementations of the same task, so the team can compare them:

- **serial:** one thread. This is the baseline for every speedup number.
- **critical:** all threads update one shared table inside an OpenMP critical section. It is deliberately naive and shows the cost of contention.
- **reduction:** the main version. The file is split into chunks. Each thread counts into its own private table, and the tables are merged with an OpenMP user-defined reduction.

## 3. Out of scope

Do not build MPI or hybrid code, GPU code, deployment or Docker setups, web services, live social media APIs, user interfaces, machine-learning models, n-gram or trend analysis, or anything else not described here. If you think an extra would help, propose it in one line in a status report and wait.

## 4. How to work

1. **Plan first.** When asked, write an implementation plan from this file (section 7 shows the structure) and wait for approval before executing.
2. **Never use sudo.** If a package or permission is missing, stop and give the human the exact Fedora command to run.
3. **Stay inside the project folder.** Never delete or change anything outside it. Delete only inside the data, build and temporary-results folders.
4. **Watch the disk.** Check free space before any large download or write, and keep at least 5 GB free. Ask before deleting downloaded archives or caches.
5. **Never invent numbers.** Every number in the report must come from a results file that your scripts produced. Report failed runs. Do not quietly drop outliers; mark them. If the speedup is poor, explain why using measurements.
6. **Write original, readable code.** Do not copy code from the web or other repositories. If you adapt a snippet, cite it in a comment and in the log. Prefer simple code over clever code.
7. **Make everything reproducible.** Run every step through a script, keep a dated log of commands and decisions, record the environment (CPU, compiler, flags) with the results, and commit to git after each phase.
8. **Keep benchmarks quiet.** While a timed run is in progress, run nothing else heavy (no builds, downloads or browsing). Run anything longer than a minute in the background and check on it with light commands.
9. **Protect memory.** The laptop has 16 GB. Stop any run that uses more than 12 GB, and try new code on small samples before large files.
10. **Stop and ask the human when:** a package is missing; less than 20 GB of disk is free; a download fails three times; a verification step still fails after three fix attempts; the benchmark plan would take more than 4 hours; the scope is unclear; or a result looks suspicious (speedup above the number of hardware threads, or the parallel version slower than serial at 2 threads). Investigate suspicious results before moving on.

## 5. Data

Use three datasets, all freely available. The sizes below are estimates, so measure and report the real ones.

| Name | Language | Source | Approx. size |
| --- | --- | --- | --- |
| Urdu | Urdu | CC-100 file `https://data.statmt.org/cc-100/ur.txt.xz` | about 884 MB compressed, probably 5 to 6 GB as text |
| Roman Urdu | Roman Urdu | CC-100 file `https://data.statmt.org/cc-100/ur_rom.txt.xz` | about 141 MB compressed, probably around 1 GB as text |
| English news | English | Hugging Face dataset `vblagoje/cc_news` (708,241 articles; try `cc_news` if that name fails) | about 2 GB as text |

Together this is roughly 8 to 9 GB of real text, so no artificial duplication is needed.

Steps:

1. Check free disk space (you need about 20 GB free) and confirm the drive type.
2. Download the two CC-100 files with a resumable download and retries, then test each archive’s integrity.
3. Decompress each one once into plain text files. Write to a temporary name and rename when finished, so an interrupted run never leaves a half-written file that looks complete.
4. In a Python virtual environment, use the Hugging Face `datasets` library to load the news dataset and write one article per line (whitespace collapsed to single spaces, articles with empty text skipped) into a plain text file.
5. Make a 50 MB sample of each of the three texts, cut at a line boundary, for development and tests.
6. Write a data report with real file sizes, line counts of the small files, the output of `file -i` on each file (expect UTF-8), the first few hundred bytes of each, and SHA-256 checksums. Save the checksums in a file in the repository.

Downloading and decompression are never part of timed runs. If the Hugging Face download fails three times, ask the human; do not switch to a different dataset on your own. Make the data scripts safe to rerun.

Roman Urdu and English both use Latin letters, so never try to detect the language: treat each file as having the language of its source.

## 6. How the program must behave

**Counting rules.** Read the text as UTF-8 and count tokens. Write these rules down in a short specification file, and make the reference implementation and the C++ code follow it exactly.

- Separators are whitespace and punctuation: every ASCII character that is not a letter or digit, Urdu and Arabic punctuation (، ؛ ؟ ۔ and the Arabic percent, decimal and thousands signs), non-breaking space, typographic quotes and dashes, and other general punctuation. A hashtag (a `#` directly before a letter or digit) stays together as one token.
- Ignore, without splitting the word: zero-width joiners and non-joiners, the byte order mark, and Arabic diacritics.
- Normalize: lowercase ASCII letters; map Arabic Yeh (U+064A) to Urdu Yeh (U+06CC) and Arabic Kaf (U+0643) to Urdu Kaf (U+06A9).
- Treat invalid UTF-8 bytes as separators. Skip tokens longer than 64 bytes. Use 64-bit counters.

**Chunking.** Divide each file into byte ranges. A chunk that starts mid-word moves forward to the next whitespace or newline byte, and every chunk runs past its nominal end to the next such byte, so each token is counted exactly once. Those bytes never appear inside a multi-byte UTF-8 character, so this is safe for Urdu text. A chunk never spans two files.

**Options.** The program takes one or more input files, the implementation (serial, critical or reduction), the thread count, the OpenMP schedule (static, dynamic or guided), the chunk size, a cap on total megabytes read, the number of top words to print, an output folder, a timing-log file, a switch that dumps every word for testing, and a switch for cold-cache runs. For cold-cache runs, ask the operating system to drop the input files’ cached pages with `posix_fadvise` before timing starts. This needs no root access.

**Outputs.** A top-words CSV (word, count; highest count first, ties broken by the word’s bytes), a full dump when requested, and a short summary with total tokens, unique tokens and an order-independent checksum of the whole table. Sorting must be deterministic, so the same input and options always give byte-identical output. The checksum lets you compare serial and parallel runs on huge files without dumping everything.

**Timing.** Record the total time and the time for each stage (reading, tokenizing and counting, merging, writing output), using `omp_get_wtime`. For the reduction version, estimate merge time as the time between the last thread finishing its chunks and the end of the parallel region.

## 7. Structure of the implementation plan

When the human asks for a plan, write it as the phases below. For each phase list the tasks, the verification gate, and any checkpoint where you stop and wait for the human.

1. **Setup.** Check the compiler (g++ with OpenMP), Python, free disk and CPU details, create the folder layout, `.gitignore` (data, virtual environment, build output) and the log file. Gate: a small OpenMP test program compiles and runs.
2. **Data.** Section 5. Gate: all files exist, are non-empty and valid UTF-8, and the data report and checksums are written. **Checkpoint 1:** report the real sizes and free space, and ask whether the downloaded archives and caches may be deleted.
3. **Reference and tests.** Write the specification file, an independent Python reference implementation of the counting rules, and at least 15 small hand-checked test files. Cover plain English, mixed case, hashtags, Urdu punctuation, diacritics and joiners, the Yeh and Kaf mapping, Roman Urdu, very long tokens, invalid UTF-8, empty lines, Windows line endings, a missing final newline, and a single-token file. Gate: the reference passes every test.
4. **Serial program.** Build the tokenizer, table, output and the serial implementation. Start with simple data structures and measure before optimizing. Keys must store the real token bytes so collisions never change counts. Compile with optimization and warnings, and add a build with address and undefined-behavior sanitizers for tests. Gate: the full dump matches the reference on every test file and the three 50 MB samples. Record the serial time on a 1 GB piece of the Urdu file and on the whole file.
5. **OpenMP versions.** Build critical and reduction as described in section 2, with the chunking rule from section 6, memory-mapped reading if it works well, and per-thread data kept on separate cache lines. Gate: outputs match serial for 1, 2, 3, 4 and 8 threads and for chunk sizes of 64 KB, 1 MB and 16 MB; the sanitizer build passes; the parallel version is not slower than serial at 2 threads.
6. **Benchmarks.** Write the benchmark and plotting scripts, run the calibration first, and estimate the total time. **Checkpoint 2:** report the calibration and time estimate, and wait for the human to confirm the laptop is on AC power, in performance mode and idle. Then run all experiments and generate the plots. Gate: every experiment has complete data, every plot comes from the results files, and every parallel run’s checksum matches the serial one.
7. **Report package.** Write the README with exact build and run steps, the draft report, a code walkthrough, and viva preparation. **Checkpoint 3:** present the package and wait.

## 8. Benchmarking

**Protocol.**

- For each setting, do one discarded warm-up run, then 5 repetitions, and report the median, minimum and spread. Interleave settings (for example, cycle through thread counts inside each repetition) so heat build-up does not favor one setting.
- Pin threads with `OMP_PROC_BIND=close` and `OMP_PLACES=threads`, and record these in the environment file.
- Warm-cache runs follow a warm-up run. Cold-cache runs use the cold-cache switch. Verify once that eviction works (for example with `fincore`) and log the result.
- Note the CPU temperature or frequency if it is readable without root. If runs slow down steadily, add a 60-second pause between runs and say so in the report.
- Wrap each run in a timeout of 15 minutes.

**Primary size.** Use the smallest input among 1 GB, 2 GB, 4 GB of the Urdu file, the whole Urdu file, or all three datasets together, whose serial time is at least 60 seconds. If none reaches 60 seconds, use all three datasets and state the serial time in the report.

**Experiments.**

| ID | Experiment | Setup |
| --- | --- | --- |
| E1 | Strong scaling | Reduction version, dynamic schedule, 16 MB chunks, threads 1, 2, 3, 4, 6, 8 on the primary size, warm cache. Measure the serial baseline the same way. |
| E2 | Implementation comparison | Serial, critical and reduction at 2 and 4 threads on a 1 GB piece of the Urdu file |
| E3 | Schedule and chunk size | Static, dynamic and guided, each with 1, 4, 16 and 64 MB chunks, at 2 and 4 threads on the same 1 GB piece |
| E4 | Input size | Urdu file prefixes of 256, 512, 1024, 2048 and 4096 MB, and the full file, at 1 and 4 threads |
| E5 | Cold vs warm cache | A 1 GB piece and the primary size, at 1, 2 and 4 threads |
| E6 | Languages | Each of the three datasets in full, at 1 and 4 threads; throughput and unique-token counts |

From the stage timers of E1, also produce a time breakdown (reading, counting, merging, output) to explain where the speedup stops.

**Metrics.** Speedup = serial time divided by parallel time. Efficiency = speedup divided by thread count (also report it relative to the 2 physical cores). Throughput in MB per second, peak memory, and the Karp-Flatt serial fraction.

**Results file.** One row per run, with experiment, implementation, schedule, chunk size, threads, dataset, size, cache state, repetition, total and stage times, peak memory, throughput, checksum and notes.

**Plots.** PNG files with labeled axes and error bars. Required by the instructor: execution time vs threads, speedup vs threads with the ideal line, efficiency vs threads, and serial vs parallel comparison. Also one plot each for E2 to E6 and a stacked time-breakdown bar chart.

## 9. Deliverables and definition of done

- The program builds from a clean checkout with one command, the tests pass with one command, and the README commands work.
- Results files, plots, specification, data report, log and environment file are committed.
- **Draft report:** abstract, introduction, problem and approach, implementation, experimental setup, results (every figure captioned and tied to its results file), analysis, limitations, conclusion. The analysis must cover Amdahl’s law, the stage breakdown, the 2-core hardware, I/O versus compute, and cold versus warm cache.
- **Code walkthrough:** a plain-English explanation of every source file and every important design choice (chunking, the reduction, race conditions avoided, false sharing, scheduling), written for students who must explain it in the viva.
- **Viva preparation:** at least 25 likely questions with short, accurate answers specific to this code and these results.
- No number in the report lacks a source row.

## 10. Common pitfalls

- Cutting a multi-byte Urdu character or a word at a chunk boundary.
- Timing downloads or decompression.
- Using the parallel code at 1 thread as the baseline instead of the serial version.
- Output that changes between runs because of unordered iteration.
- Storing views into a buffer after the normalized token was rewritten (copy normalized tokens).
- False sharing between per-thread counters.
- Slow code in the hot loop (regular expressions, per-character stream calls).
- Forgetting that private tables multiply memory use by the number of threads.
- Running other work during timed runs.

## 11. Status reports

At every checkpoint, report in under 25 lines: the phase finished, each gate’s result with evidence, what was committed, problems and decisions, free disk space, and the proposed next step.
