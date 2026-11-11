#ifndef PDC_FILE_READER_HPP
#define PDC_FILE_READER_HPP

#include <string>
#include <cstddef>
#include <cstdint>

namespace pdc {

class MappedFile {
private:
    int fd_ = -1;
    char* data_ = nullptr;
    size_t size_ = 0;
    size_t mapped_size_ = 0;

public:
    MappedFile() = default;
    ~MappedFile();

    // Disallow copy, allow move
    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;
    MappedFile(MappedFile&& other) noexcept;
    MappedFile& operator=(MappedFile&& other) noexcept;

    bool open(const std::string& path, size_t max_mb = 0, bool cold_cache = false);
    void close();

    const char* data() const { return data_; }
    size_t size() const { return size_; }
    bool is_open() const { return data_ != nullptr; }
};

} // namespace pdc

#endif // PDC_FILE_READER_HPP
