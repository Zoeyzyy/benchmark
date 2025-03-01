# Gloo version
GLOO_VERSION = e6d509b527712a143996f2f59a10480efa804f8b

# Installation directory
INSTALL_DIR = $(shell echo $$HOME)
BUILD_DIR = build
CMAKE_FLAGS = -DUSE_REDIS=1 -DBUILD_BENCHMARK=1 -DCMAKE_CXX_STANDARD=17

.PHONY: all install clean redis gloo

all: install

# Install everything
install: redis gloo

# Install and configure Redis
redis:
	@echo "Installing Redis..."
	sudo apt-get update
	sudo apt-get install -y redis-server
	@echo "Redis installation complete"

# Clone and build Gloo
gloo:
	@echo "Building Gloo benchmark..."
	cd $(INSTALL_DIR) && git clone https://github.com/facebookincubator/gloo.git || (cd gloo && git fetch)
	cd $(INSTALL_DIR)/gloo && git checkout $(GLOO_VERSION)
	mkdir -p $(INSTALL_DIR)/gloo/$(BUILD_DIR)
	cd $(INSTALL_DIR)/gloo/$(BUILD_DIR) && cmake .. $(CMAKE_FLAGS)
	cd $(INSTALL_DIR)/gloo/$(BUILD_DIR) && make -j$$(nproc)
	@echo "Gloo benchmark built successfully"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -rf $(INSTALL_DIR)/gloo/$(BUILD_DIR)
	@echo "Clean complete"

# Clean everything including repositories
distclean: clean
	@echo "Removing all installed components..."
	rm -rf $(INSTALL_DIR)/gloo
	@echo "Full cleanup complete"

# Status check
status:
	@echo "Checking Redis status..."
	@systemctl status redis-server || true
	@echo "\nChecking Gloo installation..."
	@if [ -d "$(INSTALL_DIR)/gloo/$(BUILD_DIR)" ]; then \
		echo "Gloo appears to be built in $(INSTALL_DIR)/gloo/$(BUILD_DIR)"; \
	else \
		echo "Gloo build directory not found"; \
	fi

# Help
help:
	@echo "Available targets:"
	@echo "  make install    - Install Redis and build Gloo benchmark"
	@echo "  make redis     - Install and configure Redis only"
	@echo "  make gloo      - Build Gloo benchmark only"
	@echo "  make clean     - Remove build artifacts"
	@echo "  make distclean - Remove all components"
	@echo "  make status    - Check installation status"
	@echo "  make help      - Show this help message"