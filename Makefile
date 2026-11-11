wCXX ?= g++
CXXFLAGS_COMMON = -std=c++17 -Wall -Wextra -fopenmp -Iinclude
CXXFLAGS_RELEASE = $(CXXFLAGS_COMMON) -O3
CXXFLAGS_SAN = $(CXXFLAGS_COMMON) -O1 -g -fsanitize=address,undefined
CXXFLAGS_TSAN = $(CXXFLAGS_COMMON) -O1 -g -fsanitize=thread

SRCS = src/main.cpp src/tokenizer.cpp src/file_reader.cpp src/output_writer.cpp
BIN_DIR = bin
BUILD_DIR = build

TARGET = $(BIN_DIR)/wordcount
TARGET_SAN = $(BIN_DIR)/wordcount_san
TARGET_TSAN = $(BIN_DIR)/wordcount_tsan
SANITY_TARGET = $(BIN_DIR)/openmp_sanity

.PHONY: all release sanitizer tsan clean test sanity

all: release

release: $(TARGET)

$(TARGET): $(SRCS)
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS_RELEASE) $(SRCS) -o $@

sanitizer: $(TARGET_SAN)

$(TARGET_SAN): $(SRCS)
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS_SAN) $(SRCS) -o $@

tsan: $(TARGET_TSAN)

$(TARGET_TSAN): $(SRCS)
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS_TSAN) $(SRCS) -o $@

sanity: $(SANITY_TARGET)
	@echo "==> Running OpenMP Sanity Test..."
	@$(SANITY_TARGET)

$(SANITY_TARGET): tests/openmp_sanity.cpp
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS_RELEASE) $< -o $@

test: release
	@echo "==> Running Python Reference Test Suite..."
	@python3 python/test_runner.py
	@echo "==> Running C++ Serial Engine Verification on all fixtures..."
	@python3 tests/verify_cpp_engine.py

clean:
	rm -rf $(BIN_DIR) $(BUILD_DIR) results/*_dump.csv results/*_top.csv
