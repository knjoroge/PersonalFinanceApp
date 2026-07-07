#!/bin/bash
# Double-click this file (macOS) to start the Personal Finance Manager.
# It sets up everything the first time, then opens the app in your browser.
cd "$(dirname "$0")" || exit 1

# Create the virtual environment on first run.
if [ ! -d "venv" ]; then
    echo "First-time setup — this only happens once..."
    python3 -m venv venv
    ./venv/bin/pip install --quiet --upgrade pip
    ./venv/bin/pip install --quiet -r requirements.txt
fi

echo "Starting Personal Finance Manager..."
./venv/bin/streamlit run app.py
