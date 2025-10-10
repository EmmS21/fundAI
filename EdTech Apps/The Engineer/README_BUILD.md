# The Engineer - Linux Build Quick Start

## Overview

This creates a standalone Linux executable for The Engineer AI Tutor that can be distributed to users without requiring Python installation.

## Quick Build

```bash
# 1. Make build script executable
chmod +x build.sh

# 2. Run complete build process
./build.sh

# 3. Find your executable
ls dist/Engineer-linux-1.0.0.tar.gz
```

## What Gets Created

- `dist/Engineer/` - Complete application bundle
- `dist/Engineer/Engineer` - Main executable
- `dist/Engineer-linux-1.0.0.tar.gz` - Distribution package
- `dist/checksums.sha256` - File verification checksums

## Distribution

Send users the `.tar.gz` file with these instructions:

```bash
# Extract
tar -xzf Engineer-linux-1.0.0.tar.gz
cd Engineer/

# Install  
chmod +x install.sh
./install.sh

# Run
engineer
```

## Requirements

- Docker Desktop (for building)
- Linux Mint/Ubuntu/Debian (for testing)

**Note**: This builds x86_64 Linux executables. If building from ARM64 Mac (like M1/M2), Docker will use emulation (slower but works fine).

## Build Options

```bash
./build.sh --help           # Show all options
./build.sh --clean-only     # Only clean previous builds  
./build.sh --docker-only    # Only build Docker image
```

## Files Created

| File | Purpose |
|------|---------|
| `engineer.spec` | PyInstaller configuration |
| `Dockerfile` | Build environment |
| `build.sh` | Build automation script |
| `install.sh` | User installation script |
| `hooks/pyi_rth_qt6.py` | Qt6 runtime configuration |
| `new_requirements.txt` | Complete dependency list |

## Troubleshooting

**Build fails?**
- Check Docker is running: `docker info`
- Ensure sufficient disk space (5GB+)
- Try: `./build.sh --clean-only && ./build.sh`

**Executable won't run?**  
- Install Qt6: `sudo apt-get install qt6-qpa-plugins`
- Check dependencies: `ldd dist/Engineer/Engineer`

## Full Documentation

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for complete documentation.

---

**Note**: The AI model file is NOT included in the build. Users need to download and place it at `~/Documents/models/llama/DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` or use cloud AI with a Groq API key. 