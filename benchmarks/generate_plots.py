#!/usr/bin/env python3
"""
PDC #23 — Publication-Grade Benchmark Plot Generator
Produces 9 high-resolution PNG figures with labeled axes and error bars from results/benchmark_master.csv.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS_DIR = os.path.join(PROJECT_ROOT, "results")
MASTER_CSV = os.path.join(RESULTS_DIR, "benchmark_master.csv")

# Set publication style
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 11,
    "axes.labelsize": 12,
    "axes.titlesize": 13,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "figure.titlesize": 14,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "lines.linewidth": 2,
    "lines.markersize": 7
})

def load_data():
    if not os.path.exists(MASTER_CSV):
        print(f"[-] CSV file not found: {MASTER_CSV}")
        return None
    df = pd.read_csv(MASTER_CSV)
    return df

# -------------------------------------------------------------------
# Plot 1: Execution Time vs Threads (E1)
# -------------------------------------------------------------------
def plot_e1_execution_time(df):
    e1 = df[(df["experiment_id"] == "E1") & (df["implementation"] == "reduction")].copy()
    if e1.empty:
        return
    grouped = e1.groupby("threads")["total_time_s"].agg(["median", "min", "max"]).reset_index()

    plt.figure(figsize=(8, 5))
    yerr_lower = grouped["median"] - grouped["min"]
    yerr_upper = grouped["max"] - grouped["median"]

    plt.errorbar(grouped["threads"], grouped["median"], yerr=[yerr_lower, yerr_upper],
                 fmt='-o', color="#1f77b4", capsize=5, capthick=1.5, label="Reduction (Dynamic, 16MB)")

    # Serial baseline
    s_rows = df[(df["experiment_id"] == "E1") & (df["implementation"] == "serial")]
    if not s_rows.empty:
        s_med = s_rows["total_time_s"].median()
        plt.axhline(s_med, color="crimson", linestyle="--", label=f"Serial Baseline ({s_med:.1f}s)")

    plt.axvline(2, color="gray", linestyle=":", alpha=0.7, label="Physical Cores (2)")
    plt.title("E1: Execution Time vs. Thread Count (Primary Size = 2048 MB)")
    plt.xlabel("Number of OpenMP Threads")
    plt.ylabel("Total Execution Time (seconds)")
    plt.xticks([1, 2, 3, 4, 6, 8])
    plt.legend(frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot1_execution_time_vs_threads.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 2: Speedup vs Threads (E1)
# -------------------------------------------------------------------
def plot_e1_speedup(df):
    e1 = df[(df["experiment_id"] == "E1") & (df["implementation"] == "reduction")].copy()
    s_rows = df[(df["experiment_id"] == "E1") & (df["implementation"] == "serial")]
    if e1.empty or s_rows.empty:
        return
    s_med = s_rows["total_time_s"].median()

    grouped = e1.groupby("threads")["total_time_s"].agg(["median", "min", "max"]).reset_index()
    grouped["speedup_med"] = s_med / grouped["median"]
    grouped["speedup_max"] = s_med / grouped["min"]
    grouped["speedup_min"] = s_med / grouped["max"]

    plt.figure(figsize=(8, 5))
    yerr_lower = grouped["speedup_med"] - grouped["speedup_min"]
    yerr_upper = grouped["speedup_max"] - grouped["speedup_med"]

    plt.errorbar(grouped["threads"], grouped["speedup_med"], yerr=[yerr_lower, yerr_upper],
                 fmt='-s', color="#2ca02c", capsize=5, capthick=1.5, label="Measured Speedup ($T_s / T_p$)")

    # Ideal linear speedup
    threads = np.array(grouped["threads"])
    plt.plot(threads, threads, color="black", linestyle="--", alpha=0.6, label="Ideal Linear Speedup ($y = x$)")

    plt.axvline(2, color="gray", linestyle=":", alpha=0.7, label="Physical Cores Boundary (2)")
    plt.title("E1: Speedup vs. Thread Count (Primary Size = 2048 MB)")
    plt.xlabel("Number of OpenMP Threads")
    plt.ylabel("Speedup ($S = T_{serial} / T_{parallel}$)")
    plt.xticks([1, 2, 3, 4, 6, 8])
    plt.legend(frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot2_speedup_vs_threads.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 3: Parallel Efficiency vs Threads (E1)
# -------------------------------------------------------------------
def plot_e1_efficiency(df):
    e1 = df[(df["experiment_id"] == "E1") & (df["implementation"] == "reduction")].copy()
    s_rows = df[(df["experiment_id"] == "E1") & (df["implementation"] == "serial")]
    if e1.empty or s_rows.empty:
        return
    s_med = s_rows["total_time_s"].median()

    grouped = e1.groupby("threads")["total_time_s"].agg(["median", "min", "max"]).reset_index()
    grouped["eff_med"] = (s_med / grouped["median"]) / grouped["threads"] * 100.0
    grouped["eff_max"] = (s_med / grouped["min"]) / grouped["threads"] * 100.0
    grouped["eff_min"] = (s_med / grouped["max"]) / grouped["threads"] * 100.0

    plt.figure(figsize=(8, 5))
    yerr_lower = grouped["eff_med"] - grouped["eff_min"]
    yerr_upper = grouped["eff_max"] - grouped["eff_med"]

    plt.errorbar(grouped["threads"], grouped["eff_med"], yerr=[yerr_lower, yerr_upper],
                 fmt='-^', color="#ff7f0e", capsize=5, capthick=1.5, label="Parallel Efficiency ($S / p$)")

    plt.axhline(100, color="black", linestyle="--", alpha=0.6, label="100% Ideal Efficiency")
    plt.axvline(2, color="gray", linestyle=":", alpha=0.7, label="Physical Cores (2)")
    plt.title("E1: Parallel Efficiency vs. Thread Count (Primary Size = 2048 MB)")
    plt.xlabel("Number of OpenMP Threads")
    plt.ylabel("Efficiency (%)")
    plt.xticks([1, 2, 3, 4, 6, 8])
    plt.legend(frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot3_efficiency_vs_threads.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 4: Stacked Stage Time Breakdown (E1)
# -------------------------------------------------------------------
def plot_e1_stage_breakdown(df):
    e1 = df[(df["experiment_id"] == "E1") & (df["implementation"] == "reduction")].copy()
    if e1.empty:
        return
    grouped = e1.groupby("threads")[["read_time_s", "count_time_s", "merge_time_s", "write_time_s"]].median().reset_index()

    threads = grouped["threads"]
    ind = np.arange(len(threads))
    width = 0.55

    plt.figure(figsize=(9, 5))
    p1 = plt.bar(ind, grouped["read_time_s"], width, label="Read / Mmap", color="#3b82f6")
    p2 = plt.bar(ind, grouped["count_time_s"], width, bottom=grouped["read_time_s"], label="Tokenize & Count", color="#10b981")
    p3 = plt.bar(ind, grouped["merge_time_s"], width, bottom=grouped["read_time_s"] + grouped["count_time_s"], label="Reduction Merge", color="#f59e0b")
    p4 = plt.bar(ind, grouped["write_time_s"], width, bottom=grouped["read_time_s"] + grouped["count_time_s"] + grouped["merge_time_s"], label="Write Output", color="#8b5cf6")

    plt.title("E1: Stage Time Breakdown Across Thread Counts (2048 MB Urdu)")
    plt.xlabel("Number of OpenMP Threads")
    plt.ylabel("Execution Time (seconds)")
    plt.xticks(ind, threads)
    plt.legend(loc="upper right", frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot4_time_breakdown_stacked.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 5: Implementation Comparison (E2)
# -------------------------------------------------------------------
def plot_e2_implementation(df):
    e2 = df[df["experiment_id"] == "E2"].copy()
    if e2.empty:
        return
    grouped = e2.groupby(["implementation", "threads"])["total_time_s"].median().reset_index()

    # Formats: Serial (1T), Reduction (2T, 4T), Critical (2T, 4T)
    labels = ["Serial (1T)", "Critical (2T)", "Critical (4T)", "Reduction (2T)", "Reduction (4T)"]
    times = []
    colors = ["#6b7280", "#ef4444", "#dc2626", "#3b82f6", "#1d4ed8"]

    s = grouped[(grouped["implementation"] == "serial")]["total_time_s"].values
    times.append(s[0] if len(s) > 0 else 0)

    c2 = grouped[(grouped["implementation"] == "critical") & (grouped["threads"] == 2)]["total_time_s"].values
    times.append(c2[0] if len(c2) > 0 else 0)

    c4 = grouped[(grouped["implementation"] == "critical") & (grouped["threads"] == 4)]["total_time_s"].values
    times.append(c4[0] if len(c4) > 0 else 0)

    r2 = grouped[(grouped["implementation"] == "reduction") & (grouped["threads"] == 2)]["total_time_s"].values
    times.append(r2[0] if len(r2) > 0 else 0)

    r4 = grouped[(grouped["implementation"] == "reduction") & (grouped["threads"] == 4)]["total_time_s"].values
    times.append(r4[0] if len(r4) > 0 else 0)

    plt.figure(figsize=(9, 5))
    bars = plt.bar(labels, times, color=colors, width=0.6)
    for bar in bars:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., h + 0.5, f"{h:.2f}s", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.title("E2: Implementation Comparison — Cost of Critical Contention (256 MB Urdu)")
    plt.ylabel("Execution Time (seconds)")
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot5_e2_implementation_comparison.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 6: Schedule and Chunk Size (E3)
# -------------------------------------------------------------------
def plot_e3_schedule_chunk(df):
    e3 = df[df["experiment_id"] == "E3"].copy()
    if e3.empty:
        return
    e3["chunk_mb"] = e3["chunk_size_bytes"] // (1024 * 1024)
    grouped = e3.groupby(["threads", "schedule", "chunk_mb"])["total_time_s"].median().reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    colors = {"static": "#3b82f6", "dynamic": "#10b981", "guided": "#f59e0b"}

    for idx, t in enumerate([2, 4]):
        ax = axes[idx]
        sub = grouped[grouped["threads"] == t]
        for sched in ["static", "dynamic", "guided"]:
            s_data = sub[sub["schedule"] == sched].sort_values("chunk_mb")
            ax.plot(s_data["chunk_mb"], s_data["total_time_s"], marker="o", label=sched.capitalize(), color=colors[sched])

        ax.set_title(f"Threads = {t}")
        ax.set_xlabel("Chunk Size (MB)")
        ax.set_xscale("log", base=2)
        ax.set_xticks([1, 4, 16, 64])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        if idx == 0:
            ax.set_ylabel("Execution Time (seconds)")
        ax.legend(frameon=True)

    fig.suptitle("E3: OpenMP Schedule & Chunk Size Comparison (1024 MB Urdu)")
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot6_e3_schedule_chunk_comparison.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 7: Input Size Scaling (E4)
# -------------------------------------------------------------------
def plot_e4_input_size(df):
    e4 = df[df["experiment_id"] == "E4"].copy()
    if e4.empty:
        return
    # Map size 0 to 5700
    e4["size_mb"] = e4["size_mb"].replace({0: 5700})
    grouped = e4.groupby(["threads", "size_mb"])["total_time_s"].median().reset_index()

    plt.figure(figsize=(8, 5))
    s1 = grouped[grouped["threads"] == 1].sort_values("size_mb")
    s4 = grouped[grouped["threads"] == 4].sort_values("size_mb")

    if not s1.empty:
        plt.plot(s1["size_mb"], s1["total_time_s"], marker="o", color="crimson", label="Serial (1 Thread)")
    if not s4.empty:
        plt.plot(s4["size_mb"], s4["total_time_s"], marker="s", color="#3b82f6", label="Parallel Reduction (4 Threads)")

    plt.title("E4: Input Size Scaling on Urdu Dataset (256 MB to 5.7 GB)")
    plt.xlabel("Input Size (MB)")
    plt.ylabel("Execution Time (seconds)")
    plt.legend(frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot7_e4_input_size_scaling.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 8: Cold vs Warm Cache (E5)
# -------------------------------------------------------------------
def plot_e5_cold_warm(df):
    e5 = df[df["experiment_id"] == "E5"].copy()
    if e5.empty:
        return
    grouped = e5.groupby(["size_mb", "threads", "cache_state"])["total_time_s"].median().reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=False)
    for idx, sz in enumerate([1024, 2048]):
        ax = axes[idx]
        sub = grouped[grouped["size_mb"] == sz]

        threads = [1, 2, 4]
        cold_vals = [sub[(sub["threads"] == t) & (sub["cache_state"] == "cold")]["total_time_s"].values for t in threads]
        warm_vals = [sub[(sub["threads"] == t) & (sub["cache_state"] == "warm")]["total_time_s"].values for t in threads]

        cold_times = [v[0] if len(v) > 0 else 0 for v in cold_vals]
        warm_times = [v[0] if len(v) > 0 else 0 for v in warm_vals]

        ind = np.arange(len(threads))
        width = 0.35

        ax.bar(ind - width/2, cold_times, width, label="Cold Cache", color="#60a5fa")
        ax.bar(ind + width/2, warm_times, width, label="Warm Cache", color="#f59e0b")

        ax.set_title(f"Input Size: {sz} MB")
        ax.set_xlabel("Thread Count")
        ax.set_ylabel("Execution Time (seconds)")
        ax.set_xticks(ind)
        ax.set_xticklabels(threads)
        ax.legend(frameon=True)

    fig.suptitle("E5: Cold Cache vs. Warm Cache Performance")
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot8_e5_cold_vs_warm_cache.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

# -------------------------------------------------------------------
# Plot 9: Multilingual Throughput & Vocabulary (E6)
# -------------------------------------------------------------------
def plot_e6_multilingual(df):
    e6 = df[df["experiment_id"] == "E6"].copy()
    if e6.empty:
        return
    grouped = e6.groupby(["dataset", "threads"])["throughput_mb_s"].median().reset_index()

    datasets = ["ur.txt", "ur_rom.txt", "en_news.txt"]
    d_labels = ["Urdu (5.7GB)", "Roman Urdu (481MB)", "English (1.59GB)"]

    plt.figure(figsize=(9, 5))
    ind = np.arange(len(datasets))
    width = 0.35

    t1_vals = [grouped[(grouped["dataset"] == d) & (grouped["threads"] == 1)]["throughput_mb_s"].values for d in datasets]
    t4_vals = [grouped[(grouped["dataset"] == d) & (grouped["threads"] == 4)]["throughput_mb_s"].values for d in datasets]

    t1_thru = [v[0] if len(v) > 0 else 0 for v in t1_vals]
    t4_thru = [v[0] if len(v) > 0 else 0 for v in t4_vals]

    b1 = plt.bar(ind - width/2, t1_thru, width, label="Serial (1 Thread)", color="#6b7280")
    b2 = plt.bar(ind + width/2, t4_thru, width, label="Parallel (4 Threads)", color="#10b981")

    for bar in b1 + b2:
        h = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., h + 0.5, f"{h:.1f}", ha="center", va="bottom", fontsize=9)

    plt.title("E6: Multilingual Processing Throughput (MB/s)")
    plt.xlabel("Dataset & Language")
    plt.ylabel("Throughput (MB/s)")
    plt.xticks(ind, d_labels)
    plt.legend(frameon=True)
    plt.tight_layout()
    out = os.path.join(RESULTS_DIR, "plot9_e6_multilingual_throughput.png")
    plt.savefig(out)
    plt.close()
    print(f"[+] Saved {out}")

def main():
    df = load_data()
    if df is None:
        return
    print(f"Generating publication plots from {len(df)} benchmark records...")
    plot_e1_execution_time(df)
    plot_e1_speedup(df)
    plot_e1_efficiency(df)
    plot_e1_stage_breakdown(df)
    plot_e2_implementation(df)
    plot_e3_schedule_chunk(df)
    plot_e4_input_size(df)
    plot_e5_cold_warm(df)
    plot_e6_multilingual(df)
    print("[+] All 9 publication plots successfully generated in results/")

if __name__ == "__main__":
    main()
