#ifndef PDC_CHECKSUM_HPP
#define PDC_CHECKSUM_HPP

#include <cstdint>
#include <string>
#include <string_view>
#include <unordered_map>

namespace pdc {

constexpr uint64_t FNV_OFFSET_BASIS = 0xcbf29ce484222325ULL;
constexpr uint64_t FNV_PRIME = 0x100000001b3ULL;
constexpr uint64_t CHECKSUM_MIXER = 0x9e3779b97f4a7c15ULL;

inline uint64_t fnv1a_64(std::string_view s) {
    uint64_t h = FNV_OFFSET_BASIS;
    for (unsigned char b : s) {
        h = (h ^ static_cast<uint64_t>(b)) * FNV_PRIME;
    }
    return h;
}

inline uint64_t compute_table_checksum(const std::unordered_map<std::string, uint64_t>& table) {
    uint64_t total = 0;
    for (const auto& [word, count] : table) {
        uint64_t h = fnv1a_64(word);
        uint64_t term = h ^ (count * CHECKSUM_MIXER);
        total += term; // addition modulo 2^64 is commutative and handles unordered map
    }
    return total;
}

} // namespace pdc

#endif // PDC_CHECKSUM_HPP
