#ifndef PDC_TOKENIZER_HPP
#define PDC_TOKENIZER_HPP

#include <cstddef>
#include <cstdint>
#include "frequency_table.hpp"

namespace pdc {

// Tokenizes memory slice [start, end) and accumulates word frequencies into table
void tokenize_chunk(const char* start, const char* end, FrequencyTable& table);

// Tokenizes memory slice [start, end) updating shared table guarded by OpenMP critical section
void tokenize_chunk_critical(const char* start, const char* end, FrequencyTable& shared_table);

} // namespace pdc

#endif // PDC_TOKENIZER_HPP
