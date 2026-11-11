#ifndef PDC_OUTPUT_WRITER_HPP
#define PDC_OUTPUT_WRITER_HPP

#include <string>
#include <vector>
#include "types.hpp"
#include "frequency_table.hpp"

namespace pdc {

class OutputWriter {
public:
    static bool write_top_words(const std::string& path, const std::vector<WordEntry>& entries, size_t top_n);
    static bool write_full_dump(const std::string& path, const std::vector<WordEntry>& entries);
    static bool append_timing_log(const std::string& path, const RunConfig& config, 
                                 const StageTimers& timers, uint64_t total_tokens, 
                                 uint64_t unique_tokens, uint64_t checksum, 
                                 uint64_t peak_rss_kb, size_t file_bytes);
};

} // namespace pdc

#endif // PDC_OUTPUT_WRITER_HPP
