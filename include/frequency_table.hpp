#ifndef PDC_FREQUENCY_TABLE_HPP
#define PDC_FREQUENCY_TABLE_HPP

#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>
#include <algorithm>
#include "types.hpp"
#include "checksum.hpp"

namespace pdc {

class FrequencyTable {
public:
    std::unordered_map<std::string, uint64_t> map;

    FrequencyTable() = default;

    inline void add(std::string_view word, uint64_t count = 1) {
        map[std::string(word)] += count;
    }

    inline void add(const char* data, size_t len, uint64_t count = 1) {
        map[std::string(data, len)] += count;
    }

    inline void merge(const FrequencyTable& other) {
        for (const auto& [word, count] : other.map) {
            map[word] += count;
        }
    }

    size_t unique_tokens() const {
        return map.size();
    }

    uint64_t total_tokens() const {
        uint64_t total = 0;
        for (const auto& [_, count] : map) {
            total += count;
        }
        return total;
    }

    uint64_t checksum() const {
        return compute_table_checksum(map);
    }

    std::vector<WordEntry> get_sorted_entries() const {
        std::vector<WordEntry> entries;
        entries.reserve(map.size());
        for (const auto& [word, count] : map) {
            entries.push_back({word, count});
        }
        std::sort(entries.begin(), entries.end());
        return entries;
    }
};

} // namespace pdc

#endif // PDC_FREQUENCY_TABLE_HPP
