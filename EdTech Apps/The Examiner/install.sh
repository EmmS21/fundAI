#!/bin/bash

# ASCII Art Banner
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                     AI Tutor: The Examiner                     ║
║                    Part of FundaAI AI School                   ║
║                                                                ║
║                   Created by Emmanuel Sibanda                  ║
║                             2025                               ║
╚════════════════════════════════════════════════════════════════╝
EOF

echo "
Welcome to The Examiner!

The Examiner is an AI Tutor amongst a school of AI Tutors; FundaAI. 
This intelligent system is designed to help you prepare for your exams,
guided by an AI Tutor who will mark your past papers and give you 
feedback to help you improve.

Installing The Examiner...
"

INSTALL_PARENT_DIR="$HOME/.examiner"
APP_INSTALL_DIR="$INSTALL_PARENT_DIR/app"
DATA_DIR="$INSTALL_PARENT_DIR/data" 
LOGS_DIR="$INSTALL_PARENT_DIR/logs" 
DESKTOP_ENTRY_DIR="$HOME/.local/share/applications"

echo "Building The Examiner..."
echo "Creating application directories in $INSTALL_PARENT_DIR..."
mkdir -p "$APP_INSTALL_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$LOGS_DIR"
mkdir -p "$DESKTOP_ENTRY_DIR" 

SCRIPT_SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# The actual application files are in a subdirectory (e.g., "Examiner")
APP_BUNDLE_SOURCE_DIR="$SCRIPT_SOURCE_DIR/Examiner" # Assuming PYINSTALLER_OUTPUT_DIR_NAME is "Examiner"

echo "Installing application files from $APP_BUNDLE_SOURCE_DIR to $APP_INSTALL_DIR..."
if [ -d "$APP_BUNDLE_SOURCE_DIR" ]; then
    if rsync -av --delete "$APP_BUNDLE_SOURCE_DIR/" "$APP_INSTALL_DIR/"; then
        echo "Application files installed."
    else
        echo "ERROR: Failed to copy application files from $APP_BUNDLE_SOURCE_DIR. Aborting."
        exit 1
    fi
else
    echo "ERROR: Application bundle directory not found at $APP_BUNDLE_SOURCE_DIR. Aborting."
    exit 1
fi

EXECUTABLE_NAME="Examiner"
EXECUTABLE_PATH="$APP_INSTALL_DIR/$EXECUTABLE_NAME"
ICON_FILENAME="examiner.jpg"
ICON_PATH_IN_APP="$APP_INSTALL_DIR/src/assets/$ICON_FILENAME"

if [ ! -f "$EXECUTABLE_PATH" ]; then
    echo "ERROR: Main executable not found at $EXECUTABLE_PATH after installation."
    echo "Please check the archive content and the PyInstaller build."
    exit 1
fi
chmod +x "$EXECUTABLE_PATH" 

if [ ! -f "$ICON_PATH_IN_APP" ]; then
    echo "WARNING: Icon file not found at $ICON_PATH_IN_APP. The desktop shortcut might not have an icon."
    ICON_PATH_IN_APP="" 
fi

# Create .desktop file for application menu integration
echo "Creating desktop shortcut at $DESKTOP_ENTRY_DIR/examiner.desktop..."
cat > "$DESKTOP_ENTRY_DIR/examiner.desktop" << EOL
[Desktop Entry]
Version=1.0
Name=The Examiner
Comment=AI-Powered Exam Preparation Tutor
Exec=$EXECUTABLE_PATH
Icon=$ICON_PATH_IN_APP
Terminal=false
Type=Application
Categories=Education;AI;
Keywords=Education;AI;Tutor;Exams;FundaAI;
X-Author=Emmanuel Sibanda
StartupNotify=true
EOL

if command -v update-desktop-database &> /dev/null; then
    echo "Updating desktop database..."
    update-desktop-database "$DESKTOP_ENTRY_DIR"
fi

echo "
Installation Complete!

The Examiner has been successfully installed in: $APP_INSTALL_DIR
You should be able to launch it from your applications menu.
(If it doesn't appear, you might need to log out and log back in, or restart your desktop environment).

The application expects the GGUF model file to be pre-installed at:
'$HOME/Documents/models/llama/$MODEL_FILENAME'

To uninstall The Examiner:
1. Remove the installation directory: rm -rf \"$INSTALL_PARENT_DIR\"
2. Remove the desktop entry: rm -f \"$DESKTOP_ENTRY_DIR/examiner.desktop\"
   And then run 'update-desktop-database \"$DESKTOP_ENTRY_DIR\"' if you wish.

For support or feedback, please contact Emmanuel Sibanda @ emmanuel@emmanuelsibanda.com
"