# Tokenization and Word Counting Specification (`docs/counting_rules.md`)

This document defines the formal, deterministic rules for tokenizing and counting word frequencies across English, Urdu, and Roman Urdu texts. Both the Python reference implementation (`python/reference_counter.py`) and the C++ engine (`src/tokenizer.cpp`) must follow these rules identically.

---

## 1. Character Categorization (No Unicode-Category Lookups)

All character classifications are strictly explicit by Unicode code point and UTF-8 byte sequences. Every non-ASCII character not explicitly classified as a separator or stripped is classified as a valid token character.

### 1.1 ASCII Rules
- **ASCII Token Characters:** `a-z`, `A-Z`, `0-9`.
- **ASCII Separators:** Every ASCII character (`0x00`–`0x7F`) that is not an ASCII letter or digit:
  - Whitespace: Space (`0x20`), Horizontal Tab (`0x09`), Line Feed (`0x0A`), Carriage Return (`0x0D`).
  - Control characters: `0x00`–`0x08`, `0x0B`, `0x0C`, `0x0E`–`0x1F`, `0x7F`.
  - Punctuation & symbols: `! " $ % & ' ( ) * + , - . / : ; < = > ? @ [ \ ] ^ _ ` { | } ~`.
  - Number sign / hashtag (`#`, `0x23`): Special handling (see Section 2).

### 1.2 Explicit Non-ASCII Separators
Only the following specific Unicode code points are treated as non-ASCII separators:
- **Unicode Spaces:**
  - `U+00A0`: Non-breaking space (`C2 A0`)
  - `U+2000` through `U+200A`: En quad, em quad, en space, em space, three-per-em space, four-per-em space, six-per-em space, figure space, punctuation space, thin space, hair space (`E2 80 80` through `E2 80 8A`).
- **Guillemets / Angle Quotation Marks:**
  - `U+00AB`: Left-pointing double angle quotation mark `«` (`C2 AB`)
  - `U+00BB`: Right-pointing double angle quotation mark `»` (`C2 BB`)
- **Arabic / Urdu Punctuation:**
  - `U+060C`: Arabic comma `،` (`D8 8C`)
  - `U+061B`: Arabic semicolon `؛` (`D8 9B`)
  - `U+061F`: Arabic question mark `؟` (`D8 9F`)
  - `U+06D4`: Urdu full stop `۔` (`DB 94`)
  - `U+066A`: Arabic percent sign `٪` (`D9 AA`)
  - `U+066B`: Arabic decimal separator `٫` (`D9 AB`)
  - `U+066C`: Arabic thousands separator `٬` (`D9 AC`)
- **General Typographical Punctuation:**
  - `U+2018`–`U+201B`: Single quotation marks `‘`, `’`, `‚`, `‛` (`E2 80 98`–`E2 80 9B`)
  - `U+201C`–`U+201F`: Double quotation marks `“`, `”`, `„`, `‟` (`E2 80 9C`–`E2 80 9F`)
  - `U+2013`: En dash `–` (`E2 80 93`)
  - `U+2014`: Em dash `—` (`E2 80 94`)
  - `U+2015`: Horizontal bar `―` (`E2 80 95`)
  - `U+2026`: Horizontal ellipsis `…` (`E2 80 A6`)

### 1.3 Transparently Stripped Characters (Ignored Without Splitting Tokens)
The following code points are removed transparently from the token stream. They neither split words nor count toward the token's byte length:
- **Joiners & Zero-Width Formatting:**
  - `U+200C`: Zero-Width Non-Joiner (ZWNJ, `E2 80 8C`)
  - `U+200D`: Zero-Width Joiner (ZWJ, `E2 80 8D`)
  - `U+200B`: Zero-Width Space (ZWSP, `E2 80 8B`)
  - `U+2060`: Word Joiner (WJ, `E2 81 A0`)
  - `U+FEFF`: Byte Order Mark / Zero-Width No-Break Space (BOM, `EF BB BF`)
- **Directional & Formatting Marks:**
  - `U+200E`: Left-to-Right Mark (LRM, `E2 80 8E`)
  - `U+200F`: Right-to-Left Mark (RLM, `E2 80 8F`)
  - `U+061C`: Arabic Letter Mark (ALM, `D8 9C`)
- **Arabic Diacritics / Harakat:**
  - `U+064B` through `U+065F`: Fathatan, Dammatan, Kasratan, Fatha, Damma, Kasra, Shadda, Sukun, etc. (`D9 8B` through `D9 9F`)
  - `U+0670`: Superscript Alef / Dagger Alef (`D9 B0`)

### 1.4 Non-ASCII Token Characters (Including Real U+FFFD)
**Every other non-ASCII character** (code point $\ge \text{U+0080}$ not explicitly listed in Section 1.2 or 1.3) is strictly treated as a valid token character.
- **Important:** The Unicode Replacement Character `U+FFFD` (`\ufffd`, encoded in UTF-8 as `EF BF BD`) is NOT a separator; when present as valid UTF-8 in the data, it is treated as a regular token character in both C++ and Python.

### 1.5 Strict UTF-8 Validation & Surrogateescape Rule
- UTF-8 decoding strictly adheres to RFC 3629:
  - Reject overlong encodings (2-byte $< \text{U+0080}$, 3-byte $< \text{U+0800}$, 4-byte $< \text{U+10000}$).
  - Reject UTF-16 surrogates (`U+D800` through `U+DFFF`).
  - Reject out-of-range codepoints ($> \text{U+10FFFF}$, lead bytes `0xF5`–`0xFF`).
  - Isolated continuation bytes (`0x80`–`0xBF`) or truncated sequences are rejected.
- Each maximal ill-formed sequence acts as **one separator**.
- An invalid byte sequence **never consumes a following valid ASCII byte**.
- **Python Reference Implementation Decoding:** The Python reference implementation must decode with `errors="surrogateescape"`. Python maps invalid bytes `0x80`..`0xFF` to surrogate code points `\udc80`..`\udcff`. The Python code treats any character in `\udc80`..`\udcff` as a separator (never using `errors="replace"`), ensuring real `U+FFFD` (`\ufffd`) in the data remains an authentic token character.

---

## 2. Token Processing Pipeline (Strict Order of Operations)

When scanning the text, words are processed in this exact order:

1. **Delimitation:**
   - Scan characters / byte stream. Separators and invalid byte sequences end the current token and start a delimiter region.
   - A `#` character (`0x23`) immediately followed by a valid token character (ASCII letter/digit or non-ASCII token character) is tagged as a candidate hashtag. If `#` is followed by whitespace, punctuation, an invalid byte, or EOF, it is treated as a separator.
2. **Strip Ignorable Code Points:**
   - Remove all ignorable code points listed in Section 1.3 (ZWNJ, ZWJ, ZWSP, WJ, BOM, LRM, RLM, ALM, Arabic diacritics) transparently without word splitting.
3. **Normalize:**
   - Convert uppercase ASCII `A-Z` (`0x41`–`0x5A`) to lowercase `a-z` (`0x61`–`0x7A`).
   - Map Arabic Yeh `U+064A` (`D9 8A`) $\to$ Urdu Yeh `U+06CC` (`DB AC`).
   - Map Arabic Kaf `U+0643` (`D9 83`) $\to$ Urdu Kaf `U+06A9` (`DA A9`).
4. **Apply Hashtag Rule:**
   - If the candidate hashtag `#` immediately preceded the first token character of this word, the `#` is retained as the first byte of the token.
5. **Apply 64-Byte Limit on the Result:**
   - Measure the byte length of the resulting normalized UTF-8 token.
   - If length is 0 or strictly exceeds 64 bytes (`length > 64`), the token is discarded.
   - If length is between 1 and 64 bytes inclusive, the token is recorded in the frequency table with a 64-bit counter (`uint64_t`).

---

## 3. Canonical Checksum Specification

To deterministically verify table consistency across serial and multi-threaded runs without dumping entire multi-gigabyte tables, the exact checksum is defined as:
1. **64-bit FNV-1a Hash of Token Bytes:**
   $$\text{hash} = \text{0xcbf29ce484222325ULL}$$
   $$\forall b \in w_k: \quad \text{hash} = (\text{hash} \oplus b) \times \text{0x100000001b3ULL}$$
2. **Multiplicative Mixing with 64-bit Word Count:**
   $$\text{term}(w_k, c_k) = \text{hash} \oplus (c_k \times \text{0x9e3779b97f4a7c15ULL})$$
3. **Table Checksum:**
   $$\text{Checksum} = \sum_{k=1}^{U} \text{term}(w_k, c_k) \pmod{2^{64}}$$

Because addition modulo $2^{64}$ is commutative, the result is completely independent of hash table iteration order.

---

## 4. Chunking Boundary Adjustment Specification

For a file of size $S$ and chunk size $C$:
- The boundary adjustment function $\text{adjust}(b)$ is defined as:
  - If $b = 0$, $\text{adjust}(b) = 0$.
  - If $b \ge S$, $\text{adjust}(b) = S$.
  - For $0 < b < S$, $\text{adjust}(b)$ is the smallest byte position $p \ge b$ such that $\text{byte}[p - 1]$ is an ASCII whitespace character (`0x20`, `0x09`, `0x0A`, `0x0D`).
  - If no ASCII whitespace character exists in $[b, S)$, $\text{adjust}(b) = S$.
- Chunk $k$ strictly covers the half-open byte range:
  $$[\text{adjust}(k \cdot C), \; \text{adjust}((k + 1) \cdot C))$$
- OpenMP Loop Iteration: Each chunk is an iteration in `#pragma omp parallel for schedule(dynamic, 1) reduction(TableMerge:table)`.
