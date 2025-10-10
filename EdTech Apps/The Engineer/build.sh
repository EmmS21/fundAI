#!/bin/bash
# The Engineer AI Tutor - Linux Build Script
# Creates a distributable Linux executable using Docker

set -e  # Exit on any error

# Configuration
APP_NAME="The Engineer"
VERSION="1.0.0"
DOCKER_IMAGE="engineer-builder"
BUILD_DIR="dist"
OUTPUT_NAME="Engineer"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' 

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        log_info "Please install Docker to build The Engineer"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        log_info "Please start Docker daemon and try again"
        exit 1
    fi
    
    log_success "Docker is available and running"
    
    # Check architecture and cross-platform support
    local host_arch=$(uname -m)
    log_info "Host architecture: $host_arch"
    
    if [ "$host_arch" = "arm64" ]; then
        log_warning "Building x86_64 executable from ARM64 Mac"
        log_info "This requires Docker Desktop with QEMU emulation enabled"
        log_info "The build will be slower but will produce x86_64 Linux binaries"
        
        # Test if emulation is working
        if ! docker run --rm --platform linux/amd64 alpine:latest uname -m 2>/dev/null | grep -q "x86_64"; then
            log_error "x86_64 emulation not working in Docker"
            log_info "Please ensure Docker Desktop is installed and emulation is enabled"
            log_info "Go to Docker Desktop > Settings > Features in development > Use containerd"
            exit 1
        fi
        log_success "x86_64 emulation is working"
    fi
}

# Build Docker image
build_docker_image() {
    log_info "Building Docker image: $DOCKER_IMAGE"
    log_info "Target architecture: x86_64/amd64 (for Linux Mint compatibility)"
    
    if docker build --platform linux/amd64 -t "$DOCKER_IMAGE" .; then
        log_success "Docker image built successfully for x86_64 architecture"
    else
        log_error "Failed to build Docker image"
        log_info "Note: Building x86_64 from ARM64 Mac requires Docker Desktop with emulation enabled"
        exit 1
    fi
}

# Clean previous builds
clean_build() {
    log_info "Cleaning previous builds..."
    rm -rf "$BUILD_DIR" build __pycache__ *.pyc
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    log_success "Previous builds cleaned"
}

# Run PyInstaller in Docker
run_pyinstaller() {
    log_info "Running PyInstaller in Docker container..."
    log_info "Building Linux x86_64 executable (compatible with Linux Mint)"
    
    # Create volume mounts for build output with explicit platform
    docker run --rm --platform linux/amd64 \
        -v "$(pwd):/app" \
        -w /app \
        "$DOCKER_IMAGE" \
        pyinstaller --clean engineer.spec
    
    if [ $? -eq 0 ]; then
        log_success "PyInstaller build completed"
    else
        log_error "PyInstaller build failed"
        exit 1
    fi
}

# Verify build output
verify_build() {
    local exe_path="$BUILD_DIR/$OUTPUT_NAME/$OUTPUT_NAME"
    
    if [ ! -f "$exe_path" ]; then
        log_error "Executable not found at: $exe_path"
        exit 1
    fi
    
    if [ ! -x "$exe_path" ]; then
        log_warning "Executable is not marked as executable, fixing..."
        chmod +x "$exe_path"
    fi
    
    local size=$(du -sh "$BUILD_DIR/$OUTPUT_NAME" | cut -f1)
    log_success "Build completed successfully!"
    log_info "Output location: $BUILD_DIR/$OUTPUT_NAME/"
    log_info "Executable: $exe_path"
    log_info "Bundle size: $size"
}

# Create installation package
create_package() {
    log_info "Creating installation package..."
    
    local package_name="${OUTPUT_NAME}-linux-${VERSION}.tar.gz"
    local package_path="$BUILD_DIR/$package_name"
    
    cd "$BUILD_DIR"
    tar -czf "$package_name" "$OUTPUT_NAME/"
    cd ..
    
    if [ -f "$package_path" ]; then
        local package_size=$(du -sh "$package_path" | cut -f1)
        log_success "Installation package created: $package_path"
        log_info "Package size: $package_size"
    else
        log_error "Failed to create installation package"
        exit 1
    fi
}

# Create AppImage for app store distribution
create_appimage() {
    log_info "Creating AppImage for app store distribution..."
    
    local appimage_name="${OUTPUT_NAME}-v${VERSION}.AppImage"
    local appdir_name="${OUTPUT_NAME}.AppDir"
    local appdir="$BUILD_DIR/$appdir_name"
    
    # Clean previous AppDir
    rm -rf "$appdir"
    
    # Create AppDir structure
    mkdir -p "$appdir/usr/bin"
    mkdir -p "$appdir/usr/share/applications"
    mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"
    
    # Copy PyInstaller output
    cp -r "$BUILD_DIR/$OUTPUT_NAME"/* "$appdir/usr/bin/"
    chmod +x "$appdir/usr/bin/$OUTPUT_NAME"
    
    # Copy icon if it exists
    if [ -f "assets/icons/engineer.png" ]; then
        cp "assets/icons/engineer.png" "$appdir/usr/share/icons/hicolor/256x256/apps/engineer.png"
        cp "assets/icons/engineer.png" "$appdir/engineer.png"
    fi
    
    # Create desktop file
    cat > "$appdir/$OUTPUT_NAME.desktop" << EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=AI-Powered Engineering Thinking Tutor for Young Learners
Exec=$OUTPUT_NAME
Icon=engineer
Categories=Education;Development;AI;
Terminal=false
X-AppImage-Version=$VERSION
EOF
    
    # Create AppRun script
    cat > "$appdir/AppRun" << 'EOF'
#!/bin/bash
APPDIR="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="$APPDIR/usr/lib:$LD_LIBRARY_PATH"
export PATH="$APPDIR/usr/bin:$PATH"
export QT_PLUGIN_PATH="$APPDIR/usr/bin/_internal/PySide6/Qt/plugins"
export QT_QPA_PLATFORM_PLUGIN_PATH="$APPDIR/usr/bin/_internal/PySide6/Qt/plugins/platforms"
cd "$APPDIR/usr/bin"
exec "./Engineer" "$@"
EOF
    chmod +x "$appdir/AppRun"
    
    # Create AppImage using mksquashfs directly (simpler approach)
    docker run --rm --platform linux/amd64 \
        -v "$(pwd)/$BUILD_DIR:/workspace" \
        ubuntu:22.04 \
        bash -c "
            apt-get update && apt-get install -y squashfs-tools
            cd /workspace
            # Create AppImage manually using mksquashfs
            mksquashfs $appdir_name $appimage_name -root-owned -noappend
            # Make it executable
            chmod +x $appimage_name
        "
    
    if [ -f "$BUILD_DIR/$appimage_name" ]; then
        local appimage_size=$(du -sh "$BUILD_DIR/$appimage_name" | cut -f1)
        log_success "AppImage created: $BUILD_DIR/$appimage_name"
        log_info "AppImage size: $appimage_size"
    else
        log_error "Failed to create AppImage"
    fi
}

# Generate checksums
generate_checksums() {
    log_info "Generating checksums..."
    
    cd "$BUILD_DIR"
    
    # Generate SHA256 checksums for all distribution files
    if command -v sha256sum &> /dev/null; then
        sha256sum *.tar.gz *.AppImage 2>/dev/null > checksums.sha256 || sha256sum *.tar.gz > checksums.sha256
        log_success "SHA256 checksums generated: $BUILD_DIR/checksums.sha256"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 *.tar.gz *.AppImage 2>/dev/null > checksums.sha256 || shasum -a 256 *.tar.gz > checksums.sha256
        log_success "SHA256 checksums generated: $BUILD_DIR/checksums.sha256"
    else
        log_warning "No SHA256 utility found, skipping checksum generation"
    fi
    
    cd ..
}

# Main build process
main() {
    log_info "Starting build process for $APP_NAME v$VERSION"
    log_info "Target: Linux x86_64 executable"
    
    # Pre-build checks
    check_docker
    
    # Build steps
    clean_build
    build_docker_image
    run_pyinstaller
    verify_build
    
    # Create distribution packages
    if [ "$NO_PACKAGE" != "1" ]; then
        create_package
    fi
    
    # Create AppImage if requested
    if [ "$CREATE_APPIMAGE" = "1" ]; then
        create_appimage
    fi
    
    generate_checksums
    
    log_success "🎉 Build process completed successfully!"
    log_info ""
    log_info "Output files:"
    log_info "• Executable: ./$BUILD_DIR/$OUTPUT_NAME/$OUTPUT_NAME"
    if [ "$NO_PACKAGE" != "1" ]; then
        log_info "• Linux package: $BUILD_DIR/${OUTPUT_NAME}-linux-${VERSION}.tar.gz"
    fi
    if [ "$CREATE_APPIMAGE" = "1" ]; then
        log_info "• AppImage: $BUILD_DIR/${OUTPUT_NAME}-v${VERSION}.AppImage"
    fi
    log_info ""
    log_info "Note: The AI model file is NOT included in the package."
    log_info "Users need to download and place the model file at:"
    log_info "~/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean-only)
            clean_build
            exit 0
            ;;
        --docker-only)
            build_docker_image
            exit 0
            ;;
        --no-package)
            NO_PACKAGE=1
            shift
            ;;
        --appimage)
            CREATE_APPIMAGE=1
            shift
            ;;
        --appimage-only)
            if [ ! -d "$BUILD_DIR/$OUTPUT_NAME" ]; then
                log_error "PyInstaller output not found. Run full build first."
                exit 1
            fi
            create_appimage
            exit 0
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --clean-only      Only clean previous builds"
            echo "  --docker-only     Only build Docker image"
            echo "  --no-package      Skip tar.gz package creation"
            echo "  --appimage        Also create AppImage for app store"
            echo "  --appimage-only   Only create AppImage (requires existing build)"
            echo "  --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./build.sh                    # Standard build with tar.gz package"
            echo "  ./build.sh --appimage         # Build with both tar.gz and AppImage"
            echo "  ./build.sh --appimage-only    # Only create AppImage from existing build"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main build process
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 