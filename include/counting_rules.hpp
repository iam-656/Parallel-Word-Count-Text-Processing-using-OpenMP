#ifndef PDC_COUNTING_RULES_HPP
#define PDC_COUNTING_RULES_HPP

#include <cstdint>
#include <cstddef>
#include <string>
#include <string_view>

namespace pdc {

// Classification of a decoded Unicode code point
enum class CharType {
    TokenChar,
    Separator,
    Ignorable,
    Invalid
};

// Decodes one UTF-8 code point from buffer [p, end).
// Returns the code point and sets bytes_consumed.
// Conforms strictly to RFC 3629: rejects overlongs, surrogates, and > U+10FFFF.
// On invalid sequence, returns 0xFFFFFFFF (representing invalid) and consumes
// only the maximal invalid subpart (never consuming following valid ASCII bytes).
inline uint32_t decode_utf8(const char* p, const char* end, size_t& bytes_consumed) {
    if (p >= end) {
        bytes_consumed = 0;
        return 0;
    }

    const unsigned char b0 = static_cast<unsigned char>(*p);

    // 1-byte ASCII
    if (b0 < 0x80) {
        bytes_consumed = 1;
        return b0;
    }

    // 2-byte sequence (U+0080 - U+07FF)
    // Overlong 0xC0..0xC1 rejected
    if (b0 >= 0xC2 && b0 <= 0xDF) {
        if (p + 1 < end) {
            const unsigned char b1 = static_cast<unsigned char>(p[1]);
            if ((b1 & 0xC0) == 0x80) {
                bytes_consumed = 2;
                return ((b0 & 0x1F) << 6) | (b1 & 0x3F);
            }
        }
        bytes_consumed = 1;
        return 0xFFFFFFFF; // Invalid sequence
    }

    // 3-byte sequence (U+0800 - U+FFFF)
    if (b0 >= 0xE0 && b0 <= 0xEF) {
        if (p + 1 < end) {
            const unsigned char b1 = static_cast<unsigned char>(p[1]);
            // Check second byte validity (including overlong & surrogate rejection)
            bool b1_valid = false;
            if (b0 == 0xE0) {
                b1_valid = (b1 >= 0xA0 && b1 <= 0xBF); // Reject overlong
            } else if (b0 == 0xED) {
                b1_valid = (b1 >= 0x80 && b1 <= 0x9F); // Reject UTF-16 surrogates U+D800..U+DFFF
            } else {
                b1_valid = ((b1 & 0xC0) == 0x80);
            }

            if (b1_valid) {
                if (p + 2 < end) {
                    const unsigned char b2 = static_cast<unsigned char>(p[2]);
                    if ((b2 & 0xC0) == 0x80) {
                        bytes_consumed = 3;
                        return ((b0 & 0x0F) << 12) | ((b1 & 0x3F) << 6) | (b2 & 0x3F);
                    }
                    bytes_consumed = 2;
                    return 0xFFFFFFFF;
                }
                bytes_consumed = 2;
                return 0xFFFFFFFF;
            }
        }
        bytes_consumed = 1;
        return 0xFFFFFFFF;
    }

    // 4-byte sequence (U+10000 - U+10FFFF)
    if (b0 >= 0xF0 && b0 <= 0xF4) {
        if (p + 1 < end) {
            const unsigned char b1 = static_cast<unsigned char>(p[1]);
            bool b1_valid = false;
            if (b0 == 0xF0) {
                b1_valid = (b1 >= 0x90 && b1 <= 0xBF); // Reject overlong
            } else if (b0 == 0xF4) {
                b1_valid = (b1 >= 0x80 && b1 <= 0x8F); // Reject > U+10FFFF
            } else {
                b1_valid = ((b1 & 0xC0) == 0x80);
            }

            if (b1_valid) {
                if (p + 2 < end) {
                    const unsigned char b2 = static_cast<unsigned char>(p[2]);
                    if ((b2 & 0xC0) == 0x80) {
                        if (p + 3 < end) {
                            const unsigned char b3 = static_cast<unsigned char>(p[3]);
                            if ((b3 & 0xC0) == 0x80) {
                                bytes_consumed = 4;
                                return ((b0 & 0x07) << 18) | ((b1 & 0x3F) << 12) | ((b2 & 0x3F) << 6) | (b3 & 0x3F);
                            }
                            bytes_consumed = 3;
                            return 0xFFFFFFFF;
                        }
                        bytes_consumed = 3;
                        return 0xFFFFFFFF;
                    }
                    bytes_consumed = 2;
                    return 0xFFFFFFFF;
                }
                bytes_consumed = 2;
                return 0xFFFFFFFF;
            }
        }
        bytes_consumed = 1;
        return 0xFFFFFFFF;
    }

    // Isolated continuation bytes (0x80..0xBF) or invalid lead (0xC0, 0xC1, 0xF5..0xFF)
    bytes_consumed = 1;
    return 0xFFFFFFFF;
}

// Classifies code point according to Section 1 of docs/counting_rules.md
inline CharType classify_codepoint(uint32_t cp) {
    if (cp == 0xFFFFFFFF) {
        return CharType::Invalid;
    }

    // ASCII range
    if (cp < 128) {
        if ((cp >= 'a' && cp <= 'z') || (cp >= 'A' && cp <= 'Z') || (cp >= '0' && cp <= '9')) {
            return CharType::TokenChar;
        }
        return CharType::Separator;
    }

    // Explicit Transparently Stripped (Ignorable)
    if ((cp >= 0x064B && cp <= 0x065F) || cp == 0x0670) return CharType::Ignorable; // Arabic diacritics
    if (cp == 0x200C || cp == 0x200D || cp == 0x200B || cp == 0x2060 || cp == 0xFEFF) return CharType::Ignorable; // Joiners / BOM
    if (cp == 0x200E || cp == 0x200F || cp == 0x061C) return CharType::Ignorable; // Directional / ALM marks

    // Explicit Non-ASCII Separators
    if (cp == 0x00A0) return CharType::Separator; // NBSP
    if (cp >= 0x2000 && cp <= 0x200A) return CharType::Separator; // Unicode spaces
    if (cp == 0x00AB || cp == 0x00BB) return CharType::Separator; // Guillemets
    if (cp == 0x060C || cp == 0x061B || cp == 0x061F || cp == 0x06D4 ||
        cp == 0x066A || cp == 0x066B || cp == 0x066C) return CharType::Separator; // Arabic / Urdu punctuation
    if (cp >= 0x2018 && cp <= 0x201F) return CharType::Separator; // Quotes
    if (cp >= 0x2013 && cp <= 0x2015) return CharType::Separator; // Dashes
    if (cp == 0x2026) return CharType::Separator; // Ellipsis

    // Every other non-ASCII character (including real U+FFFD) is a valid token character
    return CharType::TokenChar;
}

// Normalizes code point: ASCII lowercase, Arabic Yeh -> Urdu Yeh, Arabic Kaf -> Urdu Kaf.
// Writes normalized UTF-8 bytes to out_buf, returns number of bytes written.
inline size_t normalize_and_encode(uint32_t cp, char* out_buf) {
    // ASCII uppercase to lowercase
    if (cp >= 'A' && cp <= 'Z') {
        out_buf[0] = static_cast<char>(cp + 32);
        return 1;
    }
    if (cp < 128) {
        out_buf[0] = static_cast<char>(cp);
        return 1;
    }

    // Normalizations:
    // Arabic Yeh U+064A -> Urdu Yeh U+06CC (UTF-8: 0xDB 0xAC)
    if (cp == 0x064A) cp = 0x06CC;
    // Arabic Kaf U+0643 -> Urdu Kaf U+06A9 (UTF-8: 0xDA 0xA9)
    if (cp == 0x0643) cp = 0x06A9;

    // Encode cp to UTF-8
    if (cp <= 0x07FF) {
        out_buf[0] = static_cast<char>(0xC0 | ((cp >> 6) & 0x1F));
        out_buf[1] = static_cast<char>(0x80 | (cp & 0x3F));
        return 2;
    }
    if (cp <= 0xFFFF) {
        out_buf[0] = static_cast<char>(0xE0 | ((cp >> 12) & 0x0F));
        out_buf[1] = static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out_buf[2] = static_cast<char>(0x80 | (cp & 0x3F));
        return 3;
    }
    if (cp <= 0x10FFFF) {
        out_buf[0] = static_cast<char>(0xF0 | ((cp >> 18) & 0x07));
        out_buf[1] = static_cast<char>(0x80 | ((cp >> 12) & 0x3F));
        out_buf[2] = static_cast<char>(0x80 | ((cp >> 6) & 0x3F));
        out_buf[3] = static_cast<char>(0x80 | (cp & 0x3F));
        return 4;
    }
    return 0;
}

// Check if byte is ASCII whitespace (0x20, 0x09, 0x0A, 0x0D)
inline bool is_ascii_whitespace(char c) {
    return (c == ' ' || c == '\t' || c == '\n' || c == '\r');
}

// Chunking boundary adjustment function:
// adjust(0) = 0
// adjust(file_size) = file_size
// For 0 < b < file_size, moves to first p >= b where byte[p - 1] is ASCII whitespace.
// If no whitespace exists up to EOF, returns file_size.
inline size_t adjust_boundary(const char* data, size_t file_size, size_t b) {
    if (b == 0) return 0;
    if (b >= file_size) return file_size;

    for (size_t p = b; p < file_size; ++p) {
        if (is_ascii_whitespace(data[p - 1])) {
            return p;
        }
    }
    return file_size;
}

} // namespace pdc

#endif // PDC_COUNTING_RULES_HPP
