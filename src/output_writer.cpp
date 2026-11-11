#include "output_writer.hpp"
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>

namespace pdc {

static void write_csv_entries(std::ofstream& out, const std::vector<WordEntry>& entries, size_t limit) {
    out << "word,count\n";
    size_t count = 0;
    for (const auto& entry : entries) {
        if (limit > 0 && count >= limit) break;

        // Escape double quotes inside word
        out << "\"";
        for (char c : entry.word) {
            if (c == '"') out << "\"\"";
            else out << c;
        }
        out << "\"," << entry.count << "\n";
        count++;
    }
}

bool OutputWriter::write_top_words(const std::string& path, const std::vector<WordEntry>& entries, size_t top_n) {
    std::filesystem::path p(path);
    if (p.has_parent_path()) {
        std::filesystem::create_directories(p.parent_path());
    }

    std::ofstream out(path);
    if (!out.is_open()) {
        std::cerr << "[-] Error opening top words output file: " << path << std::endl;
        return false;
    }
    write_csv_entries(out, entries, top_n);
    return true;
}

bool OutputWriter::write_full_dump(const std::string& path, const std::vector<WordEntry>& entries) {
    std::filesystem::path p(path);
    if (p.has_parent_path()) {
        std::filesystem::create_directories(p.parent_path());
    }

    std::ofstream out(path);
    if (!out.is_open()) {
        std::cerr << "[-] Error opening full dump output file: " << path << std::endl;
        return false;
    }
    write_csv_entries(out, entries, 0); // 0 = write all
    return true;
}

bool OutputWriter::append_timing_log(const std::string& path, const RunConfig& config, 
                                     const StageTimers& timers, uint64_t total_tokens, 
                                     uint64_t unique_tokens, uint64_t checksum, 
                                     uint64_t peak_rss_kb, size_t file_bytes) {
    std::filesystem::path p(path);
    if (p.has_parent_path()) {
        std::filesystem::create_directories(p.parent_path());
    }

    bool file_exists = std::filesystem::exists(path);
    std::ofstream out(path, std::ios::app);
    if (!out.is_open()) return false;

    if (!file_exists) {
        out << "mode,threads,schedule,chunk_size_bytes,file_bytes,read_sec,count_sec,merge_sec,write_sec,total_sec,throughput_mb_s,peak_rss_mb,total_tokens,unique_tokens,checksum\n";
    }

    double throughput = 0.0;
    if (timers.total_time > 0.0) {
        throughput = (static_cast<double>(file_bytes) / (1024.0 * 1024.0)) / timers.total_time;
    }

    out << config.mode << ","
        << config.num_threads << ","
        << config.schedule_kind << ","
        << config.chunk_size << ","
        << file_bytes << ","
        << std::fixed << std::setprecision(6)
        << timers.read_time << ","
        << timers.count_time << ","
        << timers.merge_time << ","
        << timers.write_time << ","
        << timers.total_time << ","
        << std::setprecision(2)
        << throughput << ","
        << (peak_rss_kb / 1024.0) << ","
        << total_tokens << ","
        << unique_tokens << ","
        << "0x" << std::hex << std::setw(16) << std::setfill('0') << checksum << std::dec << "\n";

    return true;
}

} // namespace pdc
