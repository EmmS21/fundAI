#!/bin/bash

echo "Building The Examiner..."
APP_VERSION="1.0.0" 

# Clean up previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf build dist "Examiner-linux-${APP_VERSION}.tar.gz" "Examiner-macos-${APP_VERSION}.zip"
rm -rf venv

# Create fresh virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip first
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements (including Pillow)
echo "Installing dependencies..."
pip install -r requirements.txt || {
    echo "Error installing dependencies"
    exit 1
}

# Verify critical packages are installed
echo "Verifying critical packages..."
pip list | grep -E "Pillow|PyInstaller|PySide6" || {
    echo "Critical packages not installed properly"
    exit 1
}

ICON_PATH_ARG=""
OUTPUT_NAME="Examiner" # Base name for output

# Platform-specific preparations
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Configuring for macOS build..."
    # Convert icon for macOS
    echo "Converting icon for macOS..."
    python3 - <<EOF
from PIL import Image
import os

def convert_to_icns():
    icon_path = 'src/assets/examiner.jpg'
    iconset_path = 'src/assets/examiner.iconset'
    output_icns_path = 'src/assets/examiner.icns'

    if not os.path.exists(icon_path):
        print(f"Error: Icon not found at {icon_path}")
        return False
        
    os.makedirs(iconset_path, exist_ok=True)
    
    img = Image.open(icon_path)
    
    sizes = [(16,16), (32,32), (64,64), (128,128), (256,256), (512,512)]
    for size_tuple in sizes: # Renamed 'size' to 'size_tuple' to avoid conflict
        resized = img.resize(size_tuple, Image.Resampling.LANCZOS)
        resized.save(f'{iconset_path}/icon_{size_tuple[0]}x{size_tuple[0]}.png')
    
    os.system(f'iconutil -c icns {iconset_path} -o {output_icns_path}')
    os.system(f'rm -rf {iconset_path}')
    
    if os.path.exists(output_icns_path):
        print(f"Successfully created {output_icns_path}")
        return True
    else:
        print(f"Error: Failed to create {output_icns_path}")
        return False

if __name__ == "__main__":
    convert_to_icns()
EOF
    if [ -f "src/assets/examiner.icns" ]; then
        ICON_PATH_ARG="--icon=src/assets/examiner.icns"
    else
        echo "Warning: macOS icon (examiner.icns) not found. Using default."
        ICON_PATH_ARG="--icon=src/assets/examiner.jpg" # Fallback
    fi
    OUTPUT_NAME="Examiner.app" # PyInstaller creates .app bundle on macOS

else # Assuming Linux or other Unix-like
    echo "Configuring for Linux build..."
    ICON_PATH_ARG="--icon=src/assets/examiner.jpg"
fi

# Verify PyInstaller is in path
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Ensuring it's installed..."
    pip install pyinstaller
fi

# Build the application using the .spec file
echo "Building application with PyInstaller using Examiner.spec..."
pyinstaller Examiner.spec 

if [ $? -ne 0 ]; then
    echo "PyInstaller build failed!"
    exit 1
fi

echo "PyInstaller build completed."

# Package the application
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Packaging for macOS..."
    if [ -d "dist/Examiner.app" ]; then
        # Create a ZIP of the .app bundle
        (cd dist && zip -r "../Examiner-macos-${APP_VERSION}.zip" "Examiner.app")
        echo "macOS package created: Examiner-macos-${APP_VERSION}.zip"
    else
        echo "Error: dist/Examiner.app not found!"
        exit 1
    fi
else # Linux
    echo "Packaging for Linux..."
    if [ -d "dist/Examiner" ]; then
        # Copy the modified install.sh into the directory to be archived
        cp install.sh dist/Examiner/
        chmod +x dist/Examiner/install.sh

        # Create a tar.gz archive
        (cd dist && tar -czvf "../Examiner-linux-${APP_VERSION}.tar.gz" "Examiner")
        echo "Linux package created: Examiner-linux-${APP_VERSION}.tar.gz"
    else
        echo "Error: dist/Examiner directory not found!"
        exit 1
    fi
fi

echo "Build and packaging completed successfully!"
echo "Output artifacts are in the project root directory."

deactivate # Deactivate virtual environment