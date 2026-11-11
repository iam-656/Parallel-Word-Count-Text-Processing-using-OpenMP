#ifndef PDC_RESOURCE_MONITOR_HPP
#define PDC_RESOURCE_MONITOR_HPP

#include <cstdint>
#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <cstdlib>
#include <sys/resource.h>
#include <unistd.h>

namespace pdc {

constexpr uint64_t MEMORY_LIMIT_BYTES = 12ULL * 1024ULL * 1024ULL * 1024ULL; // 12 GB

// Reads VmHWM (Peak Resident Set Size in KB) from /proc/self/status
inline uint64_t get_vm_hwm_kb() {
    std::ifstream status_file("/proc/self/status");
    if (!status_file.is_open()) return 0;

    std::string line;
    while (std::getline(status_file, line)) {
        if (line.rfind("VmHWM:", 0) == 0) {
            std::istringstream iss(line.substr(6));
            uint64_t kb = 0;
            iss >> kb;
            return kb;
        }
    }
    return 0;
}

// Reads VmRSS (Current Resident Set Size in KB) from /proc/self/status
inline uint64_t get_vm_rss_kb() {
    std::ifstream status_file("/proc/self/status");
    if (!status_file.is_open()) return 0;

    std::string line;
    while (std::getline(status_file, line)) {
        if (line.rfind("VmRSS:", 0) == 0) {
            std::istringstream iss(line.substr(6));
            uint64_t kb = 0;
            iss >> kb;
            return kb;
        }
    }
    return 0;
}

// Check and abort if memory usage exceeds 12 GB limit
inline void check_memory_cap() {
    uint64_t current_rss_bytes = get_vm_rss_kb() * 1024ULL;
    if (current_rss_bytes > MEMORY_LIMIT_BYTES) {
        std::cerr << "\n[FATAL] Memory limit exceeded: " 
                  << (current_rss_bytes / (1024 * 1024)) << " MB > 12 GB cap. Terminating process." << std::endl;
        std::abort();
    }
}

// Returns ru_maxrss in kilobytes (on Linux, ru_maxrss is in KB)
inline uint64_t get_ru_maxrss_kb() {
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
        return static_cast<uint64_t>(usage.ru_maxrss);
    }
    return get_vm_hwm_kb();
}

} // namespace pdc

#endif // PDC_RESOURCE_MONITOR_HPP
