# The Engineer - Linux Executable Build Guide

This guide explains how to create a Linux executable for **The Engineer** application using PyInstaller. The Engineer is an AI-powered engineering thinking tutor built with PySide6 and various AI/ML libraries.

## Overview

The Engineer is packaged as a **one-file executable bundle** using PyInstaller, which creates a distributable directory containing all necessary dependencies. The build process uses Docker to ensure consistent Linux builds across different development environments.

## Prerequisites

- Docker installed on your system
- Python 3.11+ (for local development)
- Git (for cloning the repository)

## Project Structure

```
The Engineer/
├── src/                    # Main application source code
│   ├── main.py            # Application entry point
│   ├── config/            # Configuration and secrets management
│   ├── core/              # Core application logic
│   │   ├── ai/            # AI inference modules
│   │   ├── ai_manager.py  # AI service coordination
│   │   ├── database.py    # Database management
│   │   └── questions.py   # Assessment questions
│   ├── data/              # Data handling and database models
│   ├── ui/                # User interface components
│   │   ├── main_window.py # Main application window
│   │   ├── dashboard_view.py # Student dashboard
│   │   ├── assessment_view.py # Assessment interface
│   │   └── views/         # Additional UI views
│   └── utils/             # Utility modules
├── assets/                # Application assets
│   └── icons/             # Application icons
│       └── engineer.png   # Main application icon
├── engineer.spec          # PyInstaller specification file
├── Dockerfile             # Docker build environment
├── new_requirements.txt   # Comprehensive dependency list with versions
├── install.sh             # Installation script for end users
├── build.sh               # Build script for creating executable
└── BUILD_GUIDE.md         # This documentation file
```

## Build Process

### 1. Docker-Based Build Environment

The application uses a Docker-based build system to ensure consistent Linux binaries. The `Dockerfile` sets up:

- **Base Image**: Python 3.11 on Debian Bookworm
- **System Dependencies**: Qt6, X11 libraries, build tools
- **Python Dependencies**: All required packages with locked versions

Key system packages installed:
```dockerfile
# Graphics and Qt6 support
qt6-base-dev qt6-tools-dev qt6-qpa-plugins
libqt6gui6 libqt6widgets6 libqt6dbus6
libqt6svg6-dev libqt6printsupport6 libqt6opengl6-dev

# X11 and graphics support  
libgl1-mesa-dev libegl1-mesa-dev
libxcb1-dev libxcb-icccm4-dev libxcb-image0-dev
libxkbcommon-dev libxkbcommon-x11-dev

# Build tools
build-essential cmake git patchelf
```

### 2. PyInstaller Configuration

The build is configured through `engineer.spec`, which includes:

#### Platform Detection
```python
if sys.platform == "darwin":
    # macOS configuration
    app_icon_main = 'assets/icons/engineer.png'
    exe_icon = None
else:
    # Linux configuration  
    app_icon_main = 'assets/icons/engineer.png'
    exe_icon = app_icon_main
```

#### Dynamic Library Bundling
The spec file automatically discovers and bundles llama-cpp libraries:
```python
# Dynamic discovery of llama_cpp shared libraries
llama_cpp_libs_to_bundle = []
for root, _, files in os.walk(llama_cpp_dir):
    for file_name in files:
        if file_name.endswith(('.so', '.dylib', '.dll')):
            lib_path = os.path.join(root, file_name)
            destination = os.path.join('llama_cpp_libs', os.path.relpath(root, llama_cpp_dir))
            llama_cpp_libs_to_bundle.append((lib_path, destination))
```

#### Qt6/PySide6 Runtime Hook
A custom runtime hook (`hooks/pyi_rth_qt6.py`) ensures Qt plugins are properly configured:
```python
# Set QT_PLUGIN_PATH for bundled Qt plugins
qt_plugin_path = bundle_dir / 'PySide6' / 'Qt' / 'plugins'
os.environ['QT_PLUGIN_PATH'] = str(qt_plugin_path)
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(qt_plugin_path / 'platforms')
```

#### Hidden Imports
Critical modules that PyInstaller might miss:
```python
hiddenimports = [
    # Database and ORM
    'sqlalchemy.sql.default_comparator',
    'sqlalchemy.dialects.sqlite',
    'src.data.database.models',
    
    # AI libraries
    'llama_cpp', 'llama_cpp.llama', 'groq',
    
    # PySide6 components
    'PySide6.QtSvg', 'PySide6.QtPrintSupport',
    'PySide6.QtOpenGL', 'PySide6.QtMultimedia',
    
    # Application modules
    'src.core.ai_manager', 'src.core.database',
    'src.ui.main_window', 'src.ui.dashboard_view',
    # ... additional imports
]
```

#### Data Files
```python
datas = [
    ('assets', 'assets'),              # Icons and images
    ('src/config', 'src/config'),      # Configuration files
]
```

### 3. Build Output Structure

For Linux, PyInstaller creates:
```python
# Linux build configuration
exe = EXE(pyz, a.scripts, [], 
    exclude_binaries=True,
    name='Engineer',
    debug=True,
    console=True,
    icon=exe_icon
)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False,
    name='Engineer'  # Output folder in dist/
)
```

This produces: `dist/Engineer/` directory containing:
- `Engineer` (main executable)
- All shared libraries and dependencies
- Bundled Python runtime
- Application assets and configuration

## Building the Executable

### Quick Start
```bash
# Make build script executable (if needed)
chmod +x build.sh

# Run the complete build process
./build.sh
```

### Step-by-Step Process

#### Step 1: Build Environment Setup
```bash
# Build the Docker image with all dependencies
./build.sh --docker-only
```

#### Step 2: Clean Previous Builds
```bash
# Clean build artifacts
./build.sh --clean-only
```

#### Step 3: Run Complete Build
```bash
# Run PyInstaller build inside Docker container
./build.sh
```

#### Step 4: Package for Distribution
The build automatically creates:
```bash
dist/Engineer-linux-1.0.0.tar.gz    # Distribution package
dist/checksums.sha256               # SHA256 checksums
```

### Build Script Options
```bash
./build.sh --help           # Show all options
./build.sh --clean-only     # Only clean previous builds
./build.sh --docker-only    # Only build Docker image
./build.sh --no-package     # Skip package creation
```

## Installation Process

The distributed package includes an `install.sh` script that:

1. **Creates Installation Directories**:
   ```bash
   INSTALL_PARENT_DIR="$HOME/.engineer"
   APP_INSTALL_DIR="$INSTALL_PARENT_DIR/app"
   DATA_DIR="$INSTALL_PARENT_DIR/data"
   LOGS_DIR="$INSTALL_PARENT_DIR/logs"
   CONFIG_DIR="$INSTALL_PARENT_DIR/config"
   ```

2. **Copies Application Files**:
   ```bash
   rsync -av --delete "$APP_BUNDLE_SOURCE_DIR/" "$APP_INSTALL_DIR/"
   chmod +x "$APP_INSTALL_DIR/Engineer"
   ```

3. **Creates Desktop Entry**:
   ```ini
   [Desktop Entry]
   Name=The Engineer
   Comment=AI-Powered Engineering Thinking Tutor for Young Learners
   Exec=$HOME/.engineer/app/Engineer
   Icon=$HOME/.engineer/app/assets/icons/engineer.png
   Type=Application
   Categories=Education;Development;AI;
   ```

4. **Creates Command Line Launcher**:
   ```bash
   # Installs to ~/.local/bin/engineer
   export PATH="$HOME/.local/bin:$PATH"
   engineer  # Launch from anywhere
   ```

## Key Dependencies

The application requires these major components:

- **PySide6** (==6.8.0.2) - Qt6-based GUI framework
- **llama-cpp-python** (==0.3.9) - Local AI model inference
- **groq** (>=0.5.0) - Cloud AI API client
- **SQLAlchemy** (>=2.0.0) - Database ORM
- **PyInstaller** (>=5.7.0) - Application bundling
- **firebase-admin** (>=6.1.0) - Cloud backend integration
- **pymongo** (>=4.3.3) - MongoDB integration
- **python-dotenv** (>=1.0.0) - Environment configuration
- **requests** (>=2.31.0) - HTTP client library

## Runtime Requirements

### System Requirements
- Linux x86_64 (tested on Ubuntu 20.04+, Debian 11+)
- Minimum 4GB RAM (8GB recommended for AI model)
- 2GB disk space for installation
- X11 display server (Wayland with XWayland compatibility)

### Required System Libraries
The installer checks for and may require:
```bash
# Ubuntu/Debian
sudo apt-get install libx11-6 qt6-qpa-plugins

# Fedora/CentOS  
sudo dnf install libX11 qt6-qtbase
```

### AI Model Requirement
The application expects a GGUF model file to be present at:
```
~/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf
```

This model is **not** bundled with the executable to keep the distribution size manageable.

**Model Setup**:
1. Download from: https://huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B-GGUF
2. Create directory: `mkdir -p ~/Documents/models/llama/`
3. Place the `.gguf` file in that directory

**Alternative**: Use cloud AI by setting `GROQ_API_KEY` environment variable

## User Installation

### End User Instructions
1. **Extract Package**:
   ```bash
   tar -xzf Engineer-linux-1.0.0.tar.gz
   cd Engineer/
   ```

2. **Run Installer**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

3. **Launch Application**:
   ```bash
   # From applications menu
   # OR from terminal
   engineer
   # OR direct execution
   ~/.engineer/app/Engineer
   ```

### Uninstallation
```bash
~/.engineer/uninstall.sh
```

## Troubleshooting

### Common Build Issues

1. **Qt Plugin Loading Errors**:
   - Ensure Qt6 development packages are installed in Docker
   - Verify the runtime hook is properly setting plugin paths
   - Check `hooks/pyi_rth_qt6.py` for correct paths

2. **llama-cpp Library Not Found**:
   - Check that llama-cpp-python is properly installed
   - Verify the dynamic library discovery in engineer.spec
   - May fail on ARM64 - this is expected and handled gracefully

3. **Missing Hidden Imports**:
   - Add missing modules to `hiddenimports` list in engineer.spec
   - Use `--debug=all` flag with PyInstaller for detailed analysis
   - Check import errors in build logs

4. **Docker Build Failures**:
   - Ensure Docker has sufficient memory (4GB+)
   - Check internet connectivity for package downloads
   - Try rebuilding Docker image: `./build.sh --docker-only`

### Runtime Issues

1. **"Cannot find Qt platform plugin"**:
   ```bash
   # Install additional Qt platform plugins
   sudo apt-get install qt6-qpa-plugins
   
   # Set environment variable if needed
   export QT_QPA_PLATFORM=xcb
   ```

2. **Shared Library Errors**:
   ```bash
   # Check library dependencies
   ldd dist/Engineer/Engineer
   
   # Install missing libraries
   sudo apt-get install libxcb1 libxkbcommon0
   ```

3. **Model Loading Failures**:
   - Ensure model file exists at expected path
   - Check file permissions: `chmod 644 ~/Documents/models/llama/*.gguf`
   - Verify sufficient disk space and memory
   - Check logs in `~/.engineer/logs/`

4. **Application Won't Start**:
   ```bash
   # Run with debug output
   QT_LOGGING_RULES="*.debug=true" ~/.engineer/app/Engineer
   
   # Check system requirements
   echo $DISPLAY  # Should show :0 or similar
   ```

### Performance Issues

1. **Slow Startup**:
   - First run may be slower due to Qt initialization
   - Local AI model loading takes time on first use
   - Subsequent launches should be faster

2. **High Memory Usage**:
   - Expected 200-400MB baseline memory usage
   - AI model requires 2-4GB additional memory when loaded
   - Monitor with: `ps aux | grep Engineer`

3. **UI Responsiveness**:
   - Ensure X11 forwarding works properly
   - Check graphics driver compatibility
   - Disable composition if using older hardware

## Development Workflow

1. **Make Changes** to source code in `src/`
2. **Update Dependencies** in `requirements.txt` if needed
3. **Test Locally** with: `python src/main.py`
4. **Build Executable**:
   ```bash
   ./build.sh --clean-only  # Clean previous builds
   ./build.sh               # Full build process
   ```
5. **Test Executable** on target Linux system
6. **Distribute Package**: `dist/Engineer-linux-1.0.0.tar.gz`

### Testing Different Distributions
Test the executable on various Linux distributions:
- Ubuntu 20.04 LTS, 22.04 LTS, 24.04 LTS
- Debian 11, 12
- Fedora 38, 39, 40
- CentOS Stream 9
- openSUSE Leap 15.5
- Arch Linux (rolling)

## Security Considerations

- Application includes error tracking capabilities
- Local data is stored in `~/.engineer/` directory with user permissions
- Cloud sync requires network connectivity and API keys
- Model files should be verified for integrity before use
- No elevated privileges required for installation or operation

## Performance Considerations

- **Startup Time**: First run ~5-10 seconds, subsequent runs ~2-3 seconds
- **Memory Usage**: 200-400MB baseline, +2-4GB when AI model loaded
- **Disk Usage**: ~500MB installation, +1-2GB for AI model
- **Network Usage**: Only for cloud AI and optional cloud sync

---

This build system provides a robust, reproducible way to create Linux executables for The Engineer application, ensuring all dependencies are properly bundled and the application runs consistently across different Linux distributions while maintaining the simplicity of the original implementation. 