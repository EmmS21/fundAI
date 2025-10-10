#!/bin/bash
# Package The Engineer for App Store Distribution
# Creates a .zip file containing tarball + installation materials

set -e

# Configuration
APP_NAME="The Engineer"
VERSION="1.0.0"
BUILD_DIR="dist"
PACKAGE_NAME="Engineer-linux-${VERSION}"
STORE_PACKAGE_NAME="Engineer-AppStore-${VERSION}.zip"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Build Linux executable
build_linux_executable() {
    log_info "Building Linux x86_64 executable..."
    
    # Clean previous builds
    rm -rf dist/ build/
    
    # Run the main build script
    ./build.sh
    
    if [ ! -f "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" ]; then
        log_error "Linux build failed - tarball not found"
        exit 1
    fi
    
    log_success "Linux executable built successfully"
}

# Step 2: Create app store package structure
create_store_package() {
    log_info "Creating app store package..."
    
    # Create temporary packaging directory
    local temp_dir="${BUILD_DIR}/store_package"
    rm -rf "$temp_dir"
    mkdir -p "$temp_dir"
    
    # Copy the main tarball
    cp "${BUILD_DIR}/${PACKAGE_NAME}.tar.gz" "$temp_dir/"
    
    # Copy installation script
    cp install.sh "$temp_dir/"
    
    # Copy checksums
    if [ -f "${BUILD_DIR}/checksums.sha256" ]; then
        cp "${BUILD_DIR}/checksums.sha256" "$temp_dir/"
    fi
    
    # Create README for users
    cat > "$temp_dir/README.txt" << EOF
The Engineer AI Tutor - Linux Installation Package
===============================================

Contents:
- ${PACKAGE_NAME}.tar.gz    - Main application bundle
- install.sh                - Installation script
- checksums.sha256          - File verification checksums
- README.txt                - This file

Installation Instructions:
1. Extract this package to a temporary directory
2. Make the install script executable: chmod +x install.sh
3. Run the installer: ./install.sh
4. Follow the on-screen instructions

The installer will:
- Extract the application to ~/.engineer/
- Create desktop shortcuts
- Set up the application for easy launching

System Requirements:
- Linux x86_64 (64-bit)
- Minimum 4GB RAM (8GB recommended)
- 2GB free disk space
- X11 display server

For support, visit: [Your support URL]
EOF

    # Create the final zip package
    cd "$temp_dir"
    zip -r "../${STORE_PACKAGE_NAME}" .
    cd ../../
    
    # Clean up temp directory
    rm -rf "$temp_dir"
    
    log_success "App store package created: ${BUILD_DIR}/${STORE_PACKAGE_NAME}"
}

# Step 3: Verify package contents
verify_package() {
    log_info "Verifying package contents..."
    
    local package_path="${BUILD_DIR}/${STORE_PACKAGE_NAME}"
    
    if [ ! -f "$package_path" ]; then
        log_error "Package not found: $package_path"
        exit 1
    fi
    
    # Show package contents
    log_info "Package contents:"
    unzip -l "$package_path"
    
    # Show package size
    local package_size=$(du -sh "$package_path" | cut -f1)
    log_info "Package size: $package_size"
    
    log_success "Package verification complete"
}

# Main execution
main() {
    log_info "Starting app store packaging for $APP_NAME v$VERSION"
    log_info "Target: Linux x86_64 distribution package"
    
    # Check if we're in the right directory
    if [ ! -f "build.sh" ]; then
        log_error "build.sh not found. Please run this script from the project root."
        exit 1
    fi
    
    # Execute build and packaging steps
    build_linux_executable
    create_store_package
    verify_package
    
    log_success "🎉 App store package ready!"
    log_info ""
    log_info "Upload this file to your app store:"
    log_info "📦 ${BUILD_DIR}/${STORE_PACKAGE_NAME}"
    log_info ""
    log_info "Package contains:"
    log_info "• Linux executable tarball"
    log_info "• Installation script"
    log_info "• Checksums for verification"
    log_info "• User documentation"
}

# Run main function
main "$@" 