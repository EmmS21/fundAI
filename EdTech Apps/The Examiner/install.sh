#!/bin/bash

# ASCII Art Banner
cat << "EOF"
╔════════════════════════════════════════════════════════════════╗
║                       The Examiner                             ║
║                    Part of FundaAI Suite                      ║
║                                                              ║
║           Created by Emmanuel Sibanda                         ║
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

echo "Building The Examiner..."

# Create necessary directories
echo "Creating application directories..."
mkdir -p ~/.examiner/app
mkdir -p ~/.examiner/data
mkdir -p ~/.examiner/logs
mkdir -p ~/.local/share/applications

# Install application files
echo "Installing application files..."
cp -r src/* ~/.examiner/app/

# Create desktop entry
echo "Creating desktop shortcut..."
cat > ~/.local/share/applications/examiner.desktop << EOL
[Desktop Entry]
Version=1.0
Name=The Examiner
Comment=AI-Powered Exam Preparation Tutor
Exec=$HOME/.examiner/app/main.py
Icon=$HOME/.examiner/app/assets/examiner.jpg
Terminal=false
Type=Application
Categories=Education;
Keywords=Education;AI;Tutor;Exams
X-Author=Emmanuel Sibanda
EOL

# Set permissions
chmod +x ~/.examiner/app/main.py

echo "
Installation Complete!

The Examiner has been successfully installed on your system.
You can now launch it from your applications menu or by typing 'examiner'
in your terminal.

For support or feedback, please contact Emmanuel Sibanda.
"
