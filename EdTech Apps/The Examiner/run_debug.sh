#!/bin/bash

# run_debug.sh
echo "Starting The Examiner in debug mode..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the debug launcher
python3 debug_launch.py 2>&1 | tee debug_output.txt

# Check logs after app closes
echo "Application closed. Checking logs..."
latest_log=$(ls -t ~/.examiner/logs/debug_*.log | head -1)
if [ -f "$latest_log" ]; then
    echo "Latest log file: $latest_log"
    echo "Log contents:"
    cat "$latest_log"
else
    echo "No log file found"
fi
