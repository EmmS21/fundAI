#!/bin/bash

echo "Uninstalling The Examiner..."

# Remove application files
rm -rf ~/.examiner

# Remove desktop entry
rm ~/.local/share/applications/examiner.desktop

# Remove virtual environment
rm -rf venv

echo "The Examiner has been successfully uninstalled."
