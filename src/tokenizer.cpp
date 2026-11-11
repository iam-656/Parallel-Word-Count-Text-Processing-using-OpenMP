#include "tokenizer.hpp"
#include "counting_rules.hpp"
#include "resource_monitor.hpp"
#include <omp.h>

namespace pdc {

void tokenize_chunk(const char* start, const char* end, FrequencyTable& table) {
    const char* p = start;
    char token_buf[128]; // Stack buffer for normalized UTF-8 token
    uint64_t tokens_processed = 0;

    while (p < end) {
        // Check for candidate hashtag: '#' immediately followed by a token character
        if (*p == '#') {
            size_t next_consumed = 0;
            uint32_t next_cp = decode_utf8(p + 1, end, next_consumed);
            if (classify_codepoint(next_cp) == CharType::TokenChar) {
                // Valid hashtag token!
                size_t token_len = 0;
                token_buf[token_len++] = '#';
                p++; // Consume '#'

                while (p < end) {
                    size_t consumed = 0;
                    uint32_t cp = decode_utf8(p, end, consumed);
                    CharType type = classify_codepoint(cp);

                    if (type == CharType::Separator || type == CharType::Invalid) {
                        break; // End of token
                    }
                    if (type == CharType::Ignorable) {
                        p += consumed; // Strip transparently
                        continue;
                    }
                    // TokenChar: normalize and append
                    if (token_len < 100) {
                        token_len += normalize_and_encode(cp, token_buf + token_len);
                    } else {
                        // Prevent buffer overflow while scanning oversized token
                        token_len += 4;
                    }
                    p += consumed;
                }

                // Apply 64-byte limit on the result
                if (token_len >= 1 && token_len <= 64) {
                    table.add(token_buf, token_len);
                    tokens_processed++;
                }
                continue;
            } else {
                // Isolated '#' is treated as a normal ASCII separator
                p++;
                continue;
            }
        }

        // Decode code point at p
        size_t consumed = 0;
        uint32_t cp = decode_utf8(p, end, consumed);
        CharType type = classify_codepoint(cp);

        // If separator or ignorable or invalid, advance past it
        if (type == CharType::Separator || type == CharType::Ignorable || type == CharType::Invalid) {
            p += consumed;
            continue;
        }

        // Start of a regular token
        size_t token_len = 0;
        while (p < end) {
            cp = decode_utf8(p, end, consumed);
            type = classify_codepoint(cp);

            if (type == CharType::Separator || type == CharType::Invalid) {
                break; // End of token; separator is NOT consumed here
            }
            if (type == CharType::Ignorable) {
                p += consumed; // Strip transparently
                continue;
            }
            // TokenChar: normalize and append
            if (token_len < 100) {
                token_len += normalize_and_encode(cp, token_buf + token_len);
            } else {
                token_len += 4;
            }
            p += consumed;
        }

        // Apply 64-byte limit on the result
        if (token_len >= 1 && token_len <= 64) {
            table.add(token_buf, token_len);
            tokens_processed++;
        }

        // Periodically verify memory cap
        if ((tokens_processed & 0x7FFFF) == 0) { // Every ~524k tokens
            check_memory_cap();
        }
    }
}

void tokenize_chunk_critical(const char* start, const char* end, FrequencyTable& shared_table) {
    const char* p = start;
    char token_buf[128]; // Stack buffer for normalized UTF-8 token
    uint64_t tokens_processed = 0;

    while (p < end) {
        // Check for candidate hashtag: '#' immediately followed by a token character
        if (*p == '#') {
            size_t next_consumed = 0;
            uint32_t next_cp = decode_utf8(p + 1, end, next_consumed);
            if (classify_codepoint(next_cp) == CharType::TokenChar) {
                // Valid hashtag token!
                size_t token_len = 0;
                token_buf[token_len++] = '#';
                p++; // Consume '#'

                while (p < end) {
                    size_t consumed = 0;
                    uint32_t cp = decode_utf8(p, end, consumed);
                    CharType type = classify_codepoint(cp);

                    if (type == CharType::Separator || type == CharType::Invalid) {
                        break; // End of token
                    }
                    if (type == CharType::Ignorable) {
                        p += consumed; // Strip transparently
                        continue;
                    }
                    // TokenChar: normalize and append
                    if (token_len < 100) {
                        token_len += normalize_and_encode(cp, token_buf + token_len);
                    } else {
                        // Prevent buffer overflow while scanning oversized token
                        token_len += 4;
                    }
                    p += consumed;
                }

                // Apply 64-byte limit on the result
                if (token_len >= 1 && token_len <= 64) {
                    #pragma omp critical(critical_table_lock)
                    {
                        shared_table.add(token_buf, token_len);
                    }
                    tokens_processed++;
                }
                continue;
            } else {
                // Isolated '#' is treated as a normal ASCII separator
                p++;
                continue;
            }
        }

        // Decode code point at p
        size_t consumed = 0;
        uint32_t cp = decode_utf8(p, end, consumed);
        CharType type = classify_codepoint(cp);

        // If separator or ignorable or invalid, advance past it
        if (type == CharType::Separator || type == CharType::Ignorable || type == CharType::Invalid) {
            p += consumed;
            continue;
        }

        // Start of a regular token
        size_t token_len = 0;
        while (p < end) {
            cp = decode_utf8(p, end, consumed);
            type = classify_codepoint(cp);

            if (type == CharType::Separator || type == CharType::Invalid) {
                break; // End of token; separator is NOT consumed here
            }
            if (type == CharType::Ignorable) {
                p += consumed; // Strip transparently
                continue;
            }
            // TokenChar: normalize and append
            if (token_len < 100) {
                token_len += normalize_and_encode(cp, token_buf + token_len);
            } else {
                token_len += 4;
            }
            p += consumed;
        }

        // Apply 64-byte limit on the result
        if (token_len >= 1 && token_len <= 64) {
            #pragma omp critical(critical_table_lock)
            {
                shared_table.add(token_buf, token_len);
            }
            tokens_processed++;
        }

        // Periodically verify memory cap
        if ((tokens_processed & 0x7FFFF) == 0) { // Every ~524k tokens
            check_memory_cap();
        }
    }
}

} // namespace pdc
