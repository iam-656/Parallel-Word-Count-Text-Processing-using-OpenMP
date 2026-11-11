#ifndef PDC_CHUNKING_HPP
#define PDC_CHUNKING_HPP

#include <cstddef>
#include <vector>

namespace pdc {

struct Chunk {
    const char* start = nullptr;
    const char* end = nullptr;
};

// Adjust nominal boundary b:
// - b = 0 => 0
// - b >= size => size
// - Otherwise, first position p >= b where data[p - 1] is ASCII whitespace.
// - If no whitespace follows, returns size.
inline size_t adjust_boundary(const char* data, size_t size, size_t b) {
    if (b == 0) return 0;
    if (b >= size) return size;
    for (size_t p = b; p <= size; ++p) {
        char prev = data[p - 1];
        if (prev == ' ' || prev == '\t' || prev == '\n' || prev == '\r') {
            return p;
        }
    }
    return size;
}

// Splits mapped file into chunks using nominal chunk_size C and boundary adjustment.
inline std::vector<Chunk> create_file_chunks(const char* data, size_t size, size_t chunk_size) {
    std::vector<Chunk> chunks;
    if (size == 0 || data == nullptr) {
        return chunks;
    }
    if (chunk_size == 0) {
        chunks.push_back({data, data + size});
        return chunks;
    }

    size_t k = 0;
    while (true) {
        size_t nominal_start = k * chunk_size;
        size_t nominal_end = (k + 1) * chunk_size;

        size_t start_idx = adjust_boundary(data, size, nominal_start);
        size_t end_idx = adjust_boundary(data, size, nominal_end);

        if (start_idx < end_idx) {
            chunks.push_back({data + start_idx, data + end_idx});
        }
        if (end_idx >= size) {
            break;
        }
        k++;
    }
    return chunks;
}

} // namespace pdc

#endif // PDC_CHUNKING_HPP
