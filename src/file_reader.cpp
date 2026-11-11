#include "file_reader.hpp"
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <iostream>
#include <algorithm>

namespace pdc {

MappedFile::~MappedFile() {
    close();
}

MappedFile::MappedFile(MappedFile&& other) noexcept 
    : fd_(other.fd_), data_(other.data_), size_(other.size_), mapped_size_(other.mapped_size_) {
    other.fd_ = -1;
    other.data_ = nullptr;
    other.size_ = 0;
    other.mapped_size_ = 0;
}

MappedFile& MappedFile::operator=(MappedFile&& other) noexcept {
    if (this != &other) {
        close();
        fd_ = other.fd_;
        data_ = other.data_;
        size_ = other.size_;
        mapped_size_ = other.mapped_size_;
        other.fd_ = -1;
        other.data_ = nullptr;
        other.size_ = 0;
        other.mapped_size_ = 0;
    }
    return *this;
}

bool MappedFile::open(const std::string& path, size_t max_mb, bool cold_cache) {
    close();

    fd_ = ::open(path.c_str(), O_RDONLY);
    if (fd_ < 0) {
        std::cerr << "[-] Error opening file: " << path << std::endl;
        return false;
    }

    struct stat st;
    if (::fstat(fd_, &st) < 0) {
        std::cerr << "[-] Error stating file: " << path << std::endl;
        ::close(fd_);
        fd_ = -1;
        return false;
    }

    if (st.st_size == 0) {
        // Empty file
        size_ = 0;
        mapped_size_ = 0;
        data_ = nullptr;
        return true;
    }

    size_t full_file_size = static_cast<size_t>(st.st_size);

    // Apply cold-cache eviction if requested
    if (cold_cache) {
        ::posix_fadvise(fd_, 0, 0, POSIX_FADV_DONTNEED);
    }

    size_ = full_file_size;
    if (max_mb > 0) {
        size_t cap_bytes = max_mb * 1024ULL * 1024ULL;
        size_ = std::min(size_, cap_bytes);
    }

    mapped_size_ = full_file_size; // mmap full file or up to size_
    void* addr = ::mmap(nullptr, mapped_size_, PROT_READ, MAP_SHARED, fd_, 0);
    if (addr == MAP_FAILED) {
        std::cerr << "[-] Error mmapping file: " << path << std::endl;
        ::close(fd_);
        fd_ = -1;
        data_ = nullptr;
        return false;
    }

    data_ = static_cast<char*>(addr);
    ::madvise(data_, mapped_size_, MADV_SEQUENTIAL);
    return true;
}

void MappedFile::close() {
    if (data_ != nullptr && mapped_size_ > 0) {
        ::munmap(data_, mapped_size_);
        data_ = nullptr;
    }
    if (fd_ >= 0) {
        ::close(fd_);
        fd_ = -1;
    }
    size_ = 0;
    mapped_size_ = 0;
}

} // namespace pdc
