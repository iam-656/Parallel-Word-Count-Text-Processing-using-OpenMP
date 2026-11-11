#include <iostream>
#include <iomanip>
#include <vector>
#include <string>
#include <filesystem>
#include <omp.h>

#include "types.hpp"
#include "file_reader.hpp"
#include "chunking.hpp"
#include "tokenizer.hpp"
#include "frequency_table.hpp"
#include "output_writer.hpp"
#include "resource_monitor.hpp"

// OpenMP User-Defined Reduction combining per-thread FrequencyTables
#pragma omp declare reduction(TableMerge : pdc::FrequencyTable : omp_out.merge(omp_in)) \
    initializer(omp_priv = pdc::FrequencyTable())

namespace pdc {

struct alignas(64) ThreadTimer {
    double finish_time = 0.0;
};

void print_usage(const char* prog_name) {
    std::cout << "Usage: " << prog_name << " [options]\n"
              << "Options:\n"
              << "  --input, -i <file...>    Input file path(s) (required)\n"
              << "  --mode, -m <mode>        Execution mode: serial, critical, reduction (default: serial)\n"
              << "  --threads, -t <n>        Number of OpenMP threads (default: 1)\n"
              << "  --schedule, -s <sched>   OpenMP schedule: static, dynamic, guided (default: dynamic)\n"
              << "  --chunk-size, -c <bytes> Nominal chunk size in bytes (default: 16777216 = 16 MB)\n"
              << "  --top <n>                Number of top words to report (default: 100)\n"
              << "  --dump-all               Dump full word frequency table to CSV\n"
              << "  --cold-cache             Evict file pages from OS cache before run\n"
              << "  --max-mb <mb>            Limit total input megabytes read\n"
              << "  --output-dir, -o <dir>   Directory for output files (default: results)\n"
              << "  --log-file <file>        Append benchmark timing CSV row to file\n"
              << "  --help, -h               Show this help message\n";
}

bool parse_arguments(int argc, char* argv[], RunConfig& config) {
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--input" || arg == "-i") {
            while (i + 1 < argc && argv[i + 1][0] != '-') {
                config.input_files.push_back(argv[++i]);
            }
        } else if (arg == "--mode" || arg == "-m") {
            if (i + 1 < argc) config.mode = argv[++i];
        } else if (arg == "--threads" || arg == "-t") {
            if (i + 1 < argc) config.num_threads = std::stoi(argv[++i]);
        } else if (arg == "--schedule" || arg == "-s") {
            if (i + 1 < argc) config.schedule_kind = argv[++i];
        } else if (arg == "--chunk-size" || arg == "-c") {
            if (i + 1 < argc) config.chunk_size = std::stoull(argv[++i]);
        } else if (arg == "--top") {
            if (i + 1 < argc) config.top_n = std::stoull(argv[++i]);
        } else if (arg == "--dump-all") {
            config.dump_all = true;
        } else if (arg == "--cold-cache") {
            config.cold_cache = true;
        } else if (arg == "--max-mb") {
            if (i + 1 < argc) config.max_mb = std::stoull(argv[++i]);
        } else if (arg == "--output-dir" || arg == "-o") {
            if (i + 1 < argc) config.output_dir = argv[++i];
        } else if (arg == "--log-file") {
            if (i + 1 < argc) config.log_file = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            print_usage(argv[0]);
            return false;
        } else {
            std::cerr << "[-] Unknown argument: " << arg << std::endl;
            print_usage(argv[0]);
            return false;
        }
    }

    if (config.input_files.empty()) {
        std::cerr << "[-] Error: At least one input file must be specified with --input." << std::endl;
        return false;
    }
    return true;
}

} // namespace pdc

int main(int argc, char* argv[]) {
    pdc::RunConfig config;
    if (!pdc::parse_arguments(argc, argv, config)) {
        return 1;
    }

    pdc::StageTimers timers;
    double t_total_start = omp_get_wtime();

    // Stage 1: Reading / Memory Mapping & Chunk Generation
    double t_read_start = omp_get_wtime();
    std::vector<pdc::MappedFile> mapped_files;
    size_t total_input_bytes = 0;

    for (const auto& file_path : config.input_files) {
        pdc::MappedFile mf;
        if (!mf.open(file_path, config.max_mb, config.cold_cache)) {
            std::cerr << "[-] Failed to open file: " << file_path << std::endl;
            return 1;
        }
        total_input_bytes += mf.size();
        mapped_files.push_back(std::move(mf));
    }

    // Partition input files into independent chunks
    std::vector<pdc::Chunk> chunks;
    for (const auto& mf : mapped_files) {
        if (mf.size() > 0) {
            auto file_chunks = pdc::create_file_chunks(mf.data(), mf.size(), config.chunk_size);
            chunks.insert(chunks.end(), file_chunks.begin(), file_chunks.end());
        }
    }
    double t_read_end = omp_get_wtime();
    timers.read_time = t_read_end - t_read_start;

    // Stage 2: Tokenizing, Counting & Merging
    pdc::FrequencyTable global_table;
    const size_t total_chunks = chunks.size();

    // Configure OpenMP runtime schedule (with chunk parameter 1)
    omp_sched_t sched = omp_sched_dynamic;
    if (config.schedule_kind == "static") {
        sched = omp_sched_static;
    } else if (config.schedule_kind == "guided") {
        sched = omp_sched_guided;
    } else {
        sched = omp_sched_dynamic;
    }
    omp_set_schedule(sched, 1);

    if (config.mode == "serial") {
        omp_set_num_threads(1);
        double t_count_start = omp_get_wtime();
        for (size_t i = 0; i < total_chunks; ++i) {
            pdc::tokenize_chunk(chunks[i].start, chunks[i].end, global_table);
        }
        double t_count_end = omp_get_wtime();
        timers.count_time = t_count_end - t_count_start;
        timers.merge_time = 0.0;
    } else if (config.mode == "critical") {
        omp_set_num_threads(config.num_threads);
        double t_count_start = omp_get_wtime();
        #pragma omp parallel for schedule(runtime)
        for (size_t i = 0; i < total_chunks; ++i) {
            pdc::tokenize_chunk_critical(chunks[i].start, chunks[i].end, global_table);
        }
        double t_count_end = omp_get_wtime();
        timers.count_time = t_count_end - t_count_start;
        timers.merge_time = 0.0;
    } else if (config.mode == "reduction") {
        omp_set_num_threads(config.num_threads);
        std::vector<pdc::ThreadTimer> thread_finish(config.num_threads);

        double t_count_start = omp_get_wtime();
        for (int t = 0; t < config.num_threads; ++t) {
            thread_finish[t].finish_time = t_count_start;
        }

        #pragma omp parallel for schedule(runtime) reduction(TableMerge : global_table)
        for (size_t i = 0; i < total_chunks; ++i) {
            pdc::tokenize_chunk(chunks[i].start, chunks[i].end, global_table);
            thread_finish[omp_get_thread_num()].finish_time = omp_get_wtime();
        }
        double t_parallel_end = omp_get_wtime();

        double last_finish_time = t_count_start;
        for (int t = 0; t < config.num_threads; ++t) {
            if (thread_finish[t].finish_time > last_finish_time) {
                last_finish_time = thread_finish[t].finish_time;
            }
        }

        timers.count_time = last_finish_time - t_count_start;
        timers.merge_time = t_parallel_end - last_finish_time;
        if (timers.merge_time < 0.0) {
            timers.merge_time = 0.0;
        }
    } else {
        std::cerr << "[-] Unknown mode: " << config.mode << " (must be serial, critical, or reduction)" << std::endl;
        return 1;
    }

    // Stage 3: Sorting & Output Writing
    double t_write_start = omp_get_wtime();
    auto sorted_entries = global_table.get_sorted_entries();
    uint64_t total_tokens = global_table.total_tokens();
    uint64_t unique_tokens = global_table.unique_tokens();
    uint64_t table_checksum = global_table.checksum();

    std::string base_name = std::filesystem::path(config.input_files[0]).stem().string();
    std::string top_path = config.output_dir + "/" + base_name + "_" + config.mode + "_top.csv";
    pdc::OutputWriter::write_top_words(top_path, sorted_entries, config.top_n);

    if (config.dump_all) {
        std::string dump_path = config.output_dir + "/" + base_name + "_" + config.mode + "_dump.csv";
        pdc::OutputWriter::write_full_dump(dump_path, sorted_entries);
    }
    double t_write_end = omp_get_wtime();
    timers.write_time = t_write_end - t_write_start;

    double t_total_end = omp_get_wtime();
    timers.total_time = t_total_end - t_total_start;

    uint64_t peak_rss = pdc::get_ru_maxrss_kb();
    uint64_t vm_hwm = pdc::get_vm_hwm_kb();

    // Log row to timing file if requested
    if (!config.log_file.empty()) {
        pdc::OutputWriter::append_timing_log(config.log_file, config, timers, total_tokens, 
                                            unique_tokens, table_checksum, peak_rss, total_input_bytes);
    }

    // Print summary report
    std::cout << "\n======================================================================\n"
              << "           PDC #23 — PARALLEL WORD COUNT EXECUTION SUMMARY\n"
              << "======================================================================\n"
              << "Mode:                 " << config.mode << " (Threads: " << config.num_threads 
              << ", Sched: " << config.schedule_kind << ", Chunks: " << total_chunks << ")\n"
              << "Input Size:           " << (total_input_bytes / (1024.0 * 1024.0)) << " MB (" << total_input_bytes << " bytes)\n"
              << "Total Tokens:         " << total_tokens << "\n"
              << "Unique Tokens:        " << unique_tokens << "\n"
              << "Canonical Checksum:   0x" << std::hex << std::setw(16) << std::setfill('0') << table_checksum << std::dec << "\n"
              << "----------------------------------------------------------------------\n"
              << "Stage Timings:\n"
              << "  - Read / Mmap Time: " << std::fixed << std::setprecision(4) << timers.read_time << " s\n"
              << "  - Counting Time:    " << timers.count_time << " s\n"
              << "  - Merge Time:       " << timers.merge_time << " s\n"
              << "  - Write Time:       " << timers.write_time << " s\n"
              << "  - Total Time:       " << timers.total_time << " s\n"
              << "Throughput:           " << std::setprecision(2) 
              << ((total_input_bytes / (1024.0 * 1024.0)) / (timers.total_time > 0 ? timers.total_time : 1.0)) << " MB/s\n"
              << "Peak RSS (getrusage): " << (peak_rss / 1024.0) << " MB (" << peak_rss << " KB)\n"
              << "Peak VmHWM (/proc):   " << (vm_hwm / 1024.0) << " MB (" << vm_hwm << " KB)\n"
              << "======================================================================\n";

    return 0;
}
