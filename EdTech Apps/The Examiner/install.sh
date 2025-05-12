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

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Setting up Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing required packages..."
pip install -r requirements.txt

# Create necessary directories
echo "Setting up application directories..."
mkdir -p ~/.examiner/logs
mkdir -p ~/.examiner/data

# Copy application files
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

echo "
Installation Complete!

The Examiner has been successfully installed on your system.
You can now launch it from your applications menu or by typing 'examiner'
in your terminal.

For support or feedback, please contact Emmanuel Sibanda.
"
