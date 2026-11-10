#include <iostream>
#include <vector>
#include <numeric>
#include <cstdint>
#include <omp.h>

int main() {
    std::cout << "[Sanity] OpenMP Specification Date: " << _OPENMP << std::endl;
    std::cout << "[Sanity] Available max threads: " << omp_get_max_threads() << std::endl;

    const int target_threads = 4;
    omp_set_num_threads(target_threads);

    int actual_threads = 0;
    std::vector<int> thread_seen(target_threads, 0);
    uint64_t reduction_sum = 0;
    const uint64_t N = 100000;

    double t_start = omp_get_wtime();

    #pragma omp parallel reduction(+:reduction_sum)
    {
        int tid = omp_get_thread_num();
        #pragma omp single
        {
            actual_threads = omp_get_num_threads();
        }

        #pragma omp atomic
        thread_seen[tid]++;

        #pragma omp for schedule(static)
        for (uint64_t i = 1; i <= N; ++i) {
            reduction_sum += i;
        }
    }

    double t_end = omp_get_wtime();
    uint64_t expected_sum = (N * (N + 1)) / 2;

    std::cout << "[Sanity] Running threads: " << actual_threads << std::endl;
    for (int i = 0; i < target_threads; ++i) {
        std::cout << "  - Thread " << i << " execution count: " << thread_seen[i] << std::endl;
    }
    std::cout << "[Sanity] Reduction sum: " << reduction_sum << " (Expected: " << expected_sum << ")" << std::endl;
    std::cout << "[Sanity] Elapsed time: " << (t_end - t_start) * 1000.0 << " ms" << std::endl;

    if (actual_threads == target_threads && reduction_sum == expected_sum) {
        std::cout << "[Sanity] GATE 1 PASSED: OpenMP compiler and runtime operational." << std::endl;
        return 0;
    } else {
        std::cerr << "[Sanity] GATE 1 FAILED!" << std::endl;
        return 1;
    }
}
