CXX ?= g++
CXXFLAGS = -std=c++17 -O3 -Wall -Wextra -fopenmp
SAN_FLAGS = -std=c++17 -O1 -g -Wall -Wextra -fopenmp -fsanitize=address,undefined
TSAN_FLAGS = -std=c++17 -O1 -g -Wall -Wextra -fopenmp -fsanitize=thread

BIN_DIR = bin
BUILD_DIR = build

.PHONY: all clean sanity

all: sanity

sanity: $(BIN_DIR)/openmp_sanity
	@echo "==> Running OpenMP Sanity Test..."
	@$(BIN_DIR)/openmp_sanity

$(BIN_DIR)/openmp_sanity: tests/openmp_sanity.cpp
	@mkdir -p $(BIN_DIR)
	$(CXX) $(CXXFLAGS) $< -o $@

clean:
	rm -rf $(BIN_DIR) $(BUILD_DIR)
