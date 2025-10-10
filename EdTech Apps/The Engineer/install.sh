#!/bin/bash
# The Engineer AI Tutor - Linux Installation Script
# Installs The Engineer to user's home directory and creates desktop entries

set -e  # Exit on any error

# Configuration
APP_NAME="The Engineer"
APP_EXECUTABLE="Engineer"
VERSION="1.0.0"
INSTALL_PARENT_DIR="$HOME/.engineer"
APP_INSTALL_DIR="$INSTALL_PARENT_DIR/app"
DATA_DIR="$INSTALL_PARENT_DIR/data"
LOGS_DIR="$INSTALL_PARENT_DIR/logs"
CONFIG_DIR="$INSTALL_PARENT_DIR/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check for required system libraries
    local missing_libs=()
    
    # Check for basic X11 libraries
    if ! ldconfig -p | grep -q "libX11.so"; then
        missing_libs+=("libx11-6")
    fi
    
    # Check for Qt6 libraries (basic check)
    if ! ldconfig -p | grep -q "libQt6"; then
        log_warning "Qt6 libraries not detected, but might be bundled with the application"
    fi
    
    if [ ${#missing_libs[@]} -ne 0 ]; then
        log_error "Missing required system libraries: ${missing_libs[*]}"
        log_info "Please install them using your package manager:"
        log_info "Ubuntu/Debian: sudo apt-get install ${missing_libs[*]}"
        log_info "Fedora/CentOS: sudo dnf install ${missing_libs[*]}"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

# Create installation directories
create_directories() {
    log_info "Creating installation directories..."
    
    mkdir -p "$APP_INSTALL_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOGS_DIR"
    mkdir -p "$CONFIG_DIR"
    
    log_success "Installation directories created"
}

# Find and extract the application bundle
extract_application() {
    log_info "Extracting application files..."
    
    # Look for the bundle directory in current directory
    local app_bundle_source_dir=""
    
    if [ -d "$APP_EXECUTABLE" ]; then
        app_bundle_source_dir="$APP_EXECUTABLE"
    elif [ -d "dist/$APP_EXECUTABLE" ]; then
        app_bundle_source_dir="dist/$APP_EXECUTABLE"
    else
        log_error "Cannot find application bundle directory '$APP_EXECUTABLE'"
        log_info "Make sure you're running this script from the extracted package directory"
        exit 1
    fi
    
    log_info "Found application bundle at: $app_bundle_source_dir"
    
    # Copy application files using rsync for better handling
    if command -v rsync &> /dev/null; then
        rsync -av --delete "$app_bundle_source_dir/" "$APP_INSTALL_DIR/"
    else
        cp -r "$app_bundle_source_dir/"* "$APP_INSTALL_DIR/"
    fi
    
    # Make the main executable... executable
    chmod +x "$APP_INSTALL_DIR/$APP_EXECUTABLE"
    
    log_success "Application files extracted to: $APP_INSTALL_DIR"
}

# Create desktop entry
create_desktop_entry() {
    log_info "Creating desktop entry..."
    
    local desktop_dir="$HOME/.local/share/applications"
    local desktop_file="$desktop_dir/engineer.desktop"
    
    mkdir -p "$desktop_dir"
    
    # Create the desktop entry file
    cat > "$desktop_file" << EOF
[Desktop Entry]
Name=$APP_NAME
Comment=AI-Powered Engineering Thinking Tutor for Young Learners
Exec=$APP_INSTALL_DIR/$APP_EXECUTABLE
Icon=$APP_INSTALL_DIR/assets/icons/engineer.png
Type=Application
Categories=Education;Development;AI;
StartupNotify=true
StartupWMClass=engineer
Keywords=AI;Education;Engineering;Programming;Tutor;Learning;
MimeType=application/x-engineer-project;
EOF

    chmod +x "$desktop_file"
    
    log_success "Desktop entry created: $desktop_file"
    
    # Try to update desktop database
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$desktop_dir" 2>/dev/null || true
    fi
}

# Create launcher script
create_launcher() {
    log_info "Creating launcher script..."
    
    local launcher_script="$HOME/.local/bin/engineer"
    
    mkdir -p "$(dirname "$launcher_script")"
    
    cat > "$launcher_script" << 'EOF'
#!/bin/bash
# The Engineer AI Tutor Launcher Script

# Set up environment
export ENGINEER_DATA_DIR="$HOME/.engineer/data"
export ENGINEER_LOGS_DIR="$HOME/.engineer/logs"
export ENGINEER_CONFIG_DIR="$HOME/.engineer/config"

# Create directories if they don't exist
mkdir -p "$ENGINEER_DATA_DIR"
mkdir -p "$ENGINEER_LOGS_DIR" 
mkdir -p "$ENGINEER_CONFIG_DIR"

# Change to the application directory
cd "$HOME/.engineer/app"

# Launch the application
exec "./Engineer" "$@"
EOF

    chmod +x "$launcher_script"
    
    log_success "Launcher script created: $launcher_script"
    
    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        log_warning "~/.local/bin is not in your PATH"
        log_info "Add this line to your ~/.bashrc or ~/.zshrc:"
        log_info "export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
}

# Check for AI model
check_ai_model() {
    log_info "Checking for AI model..."
    
    local model_path="$HOME/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
    
    if [ -f "$model_path" ]; then
        log_success "AI model found at: $model_path"
    else
        log_warning "AI model not found at: $model_path"
        log_info ""
        log_info "The Engineer can run without the local AI model, but you'll need:"
        log_info "1. Download the model from: https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B-GGUF"
        log_info "2. Create directory: mkdir -p ~/Documents/models/llama/"
        log_info "3. Place the model file in that directory"
        log_info ""
        log_info "Alternatively, you can use cloud AI by setting up a Groq API key"
        log_info "Visit: https://groq.com to get a free API key"
    fi
}

# Create uninstall script
create_uninstaller() {
    log_info "Creating uninstaller..."
    
    local uninstall_script="$INSTALL_PARENT_DIR/uninstall.sh"
    
    cat > "$uninstall_script" << 'EOF'
#!/bin/bash
# The Engineer AI Tutor Uninstaller

echo "Uninstalling The Engineer AI Tutor..."

# Remove desktop entry
rm -f "$HOME/.local/share/applications/engineer.desktop"

# Remove launcher script
rm -f "$HOME/.local/bin/engineer"

# Ask about user data
read -p "Do you want to remove all user data? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing user data..."
    rm -rf "$HOME/.engineer"
    echo "All data removed."
else
    echo "Keeping user data in $HOME/.engineer/data"
    rm -rf "$HOME/.engineer/app"
    rm -f "$HOME/.engineer/uninstall.sh"
fi

# Try to update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi

echo "The Engineer has been uninstalled."
EOF

    chmod +x "$uninstall_script"
    
    log_success "Uninstaller created: $uninstall_script"
}

# Main installation process
main() {
    log_info "Installing $APP_NAME v$VERSION"
    log_info ""
    
    # Installation steps
    check_requirements
    create_directories
    extract_application
    create_desktop_entry
    create_launcher
    check_ai_model
    create_uninstaller
    
    log_success "🎉 Installation completed successfully!"
    log_info ""
    log_info "You can now run The Engineer in several ways:"
    log_info "1. From desktop: Look for '$APP_NAME' in your applications menu"
    log_info "2. From terminal: engineer"
    log_info "3. Direct execution: $APP_INSTALL_DIR/$APP_EXECUTABLE"
    log_info ""
    log_info "Data directory: $DATA_DIR"
    log_info "Logs directory: $LOGS_DIR"
    log_info "Config directory: $CONFIG_DIR"
    log_info ""
    log_info "To uninstall: $INSTALL_PARENT_DIR/uninstall.sh"
    log_info ""
    log_warning "Don't forget to set up your AI model or API key!"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Install The Engineer AI Tutor to your system"
            echo ""
            echo "Options:"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    log_error "Please do not run this installer as root"
    log_info "This installer installs to your home directory (~/.engineer)"
    exit 1
fi

# Run main installation process
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 