#!/bin/bash

echo "Building The Examiner..."

# Ensure virtual environment exists and is activated
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Install requirements
echo "Installing dependencies..."
pip install -r requirements.txt

# Install PyInstaller
pip install pyinstaller

# Build the application
pyinstaller --name="Examiner" \
           --windowed \
           --add-data "src/assets:assets" \
           --add-data "src/config:config" \
           --icon="src/assets/examiner.jpg" \
           src/main.py

echo "Build complete! The application package is in the dist/Examiner directory."
