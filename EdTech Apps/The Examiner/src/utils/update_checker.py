#!/bin/bash

# install.sh
echo "Installing The Examiner..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create installation directories
install -d /usr/local/share/examiner
install -d /usr/local/bin
install -d /usr/local/share/applications

# Copy application files
cp -r dist/Examiner/* /usr/local/share/examiner/

# Create symlink to executable
ln -sf /usr/local/share/examiner/Examiner /usr/local/bin/examiner

# Install desktop file
cp Examiner.desktop /usr/local/share/applications/

# Set permissions
chmod +x /usr/local/bin/examiner
chmod +x /usr/local/share/examiner/Examiner

echo "Installation complete!"
