# Environment Profile & System Details

- **Date Recorded:** 2026-11-10 20:45:57 UTC
- **Project Directory:** `/home/iamblitz/Documents/PDC_Parallel_Keyword_and_Trend_Analyzer`
- **Host / Machine:** HP EliteBook 820 G4
- **OS / Distribution:** Fedora Linux 44 (KDE Plasma Desktop Edition)
- **Kernel Version:** `7.2.15-200.fc44.x86_64 #1 SMP PREEMPT_DYNAMIC Sun Nov  1 16:10:54 UTC 2026`
- **CPU Architecture:** x86_64
- **CPU Model:** Intel(R) Core(TM) i5-7300U CPU @ 2.60GHz
- **Logical CPUs:** 4
- **Physical Sockets:** 1
- **Cores per Socket:** 2 (Total physical cores: 2)
- **Threads per Core:** 2 (Hyper-threading enabled)
- **CPU Scaling Governors:**
- cpu0: performance
  - cpu1: performance
  - cpu2: performance
  - cpu3: performance
- **Power Profile Status:** `powerprofilesctl` missing on system; `performance` governor verified active on all CPUs via sysfs.
- **Memory (RAM):**
```
total        used        free      shared  buff/cache   available
Mem:            15Gi        11Gi       368Mi       1.5Gi       5.3Gi       3.8Gi
Swap:           15Gi       5.1Gi        10Gi
```
- **Filesystem & Free Disk Space:**
```
Filesystem      Size  Used Avail Use% Mounted on
/dev/nvme0n1p3  475G   66G  408G  14% /home
```
- **C++ Compiler:** `g++ (GCC) 16.2.1 20261029 (Red Hat 16.2.1-3)`
- **Python Version:** `Python 3.14.10`
- **Cache Eviction Tool:** `fincore from util-linux 2.41.6`
- **OpenMP Environment Defaults:**
  - `OMP_PROC_BIND=close`
  - `OMP_PLACES=threads`

- **AC Power State:** AC Adapter Online (`/sys/class/power_supply/*/online = 1`)
- **Primary Size Benchmark Input:** 2048 MB (2 GB prefix of `data/decompressed/ur.txt`, measured serial runtime: 82.33 s, exceeding the 60-second threshold per Section 8)
- **1 GB Urdu Calibration:** Measured serial runtime 31.65 s, parallel reduction (2 threads) 17.08 s (Speedup: 1.85x)
