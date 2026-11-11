#ifndef PDC_TYPES_HPP
#define PDC_TYPES_HPP

#include <cstdint>
#include <string>
#include <vector>

namespace pdc {

struct StageTimers {
    double read_time = 0.0;
    double count_time = 0.0;
    double merge_time = 0.0;
    double write_time = 0.0;
    double total_time = 0.0;
};

struct RunConfig {
    std::vector<std::string> input_files;
    std::string mode = "serial"; // "serial", "critical", "reduction"
    int num_threads = 1;
    std::string schedule_kind = "dynamic"; // "static", "dynamic", "guided"
    size_t chunk_size = 16 * 1024 * 1024;  // default 16 MB
    size_t max_mb = 0;                     // 0 = unlimited
    size_t top_n = 100;
    std::string output_dir = "results";
    std::string log_file = "";
    bool dump_all = false;
    bool cold_cache = false;
};

struct WordEntry {
    std::string word;
    uint64_t count;

    bool operator<(const WordEntry& other) const {
        if (count != other.count) {
            return count > other.count; // highest count first
        }
        return word < other.word; // ties broken ascending by raw UTF-8 bytes
    }
};

} // namespace pdc

#endif // PDC_TYPES_HPP
