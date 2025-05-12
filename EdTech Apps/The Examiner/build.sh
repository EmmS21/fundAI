#!/bin/bash

echo "Building The Examiner..."

# Clean up previous build artifacts
echo "Cleaning previous build artifacts..."
rm -rf build dist
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

# Convert icon for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Converting icon for macOS..."
    python3 - <<EOF
from PIL import Image
import os

def convert_to_icns():
    icon_path = 'src/assets/examiner.jpg'
    iconset_path = 'src/assets/examiner.iconset'
    
    if not os.path.exists(icon_path):
        print(f"Error: Icon not found at {icon_path}")
        return False
        
    os.makedirs(iconset_path, exist_ok=True)
    
    img = Image.open(icon_path)
    
    # Generate icons for different sizes
    sizes = [(16,16), (32,32), (64,64), (128,128), (256,256), (512,512)]
    for size in sizes:
        resized = img.resize(size, Image.Resampling.LANCZOS)
        resized.save(f'{iconset_path}/icon_{size[0]}x{size[0]}.png')
    
    # Convert to icns using iconutil
    os.system(f'iconutil -c icns {iconset_path}')
    os.system(f'rm -rf {iconset_path}')
    
    return True

if __name__ == "__main__":
    convert_to_icns()
EOF
    ICON_PATH="src/assets/examiner.icns"
else
    ICON_PATH="src/assets/examiner.jpg"
fi

# Verify PyInstaller is in path
if ! command -v pyinstaller &> /dev/null; then
    echo "PyInstaller not found. Ensuring it's installed..."
    pip install pyinstaller
fi

# Build the application
echo "Building application with PyInstaller..."
pyinstaller --name="Examiner" \
           --windowed \
           --add-data "src/assets:assets" \
           --add-data "src/config:config" \
           --icon="$ICON_PATH" \
           src/main.py

if [ $? -eq 0 ]; then
    echo "Build completed successfully! The application package is in the dist/Examiner directory."
else
    echo "Build failed!"
    exit 1
fi
