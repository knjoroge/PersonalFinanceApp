#!/bin/bash
# Double-click this file (macOS) to start the Personal Finance Manager.
# It sets up everything the first time, then opens the app in your browser.
cd "$(dirname "$0")" || exit 1

# Show a clear message and keep the window open so it can be read.
fail() {
    echo ""
    echo "❌ $1"
    echo ""
    read -n 1 -s -r -p "Press any key to close this window..."
    exit 1
}

# Returns success if the given Python is version 3.11 or newer.
new_enough() {
    "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' >/dev/null 2>&1
}

# Find a new-enough Python. The python3 built into macOS is often too old,
# so check the versions installed from python.org first.
PY=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3; do
    if command -v "$cmd" >/dev/null 2>&1 && new_enough "$cmd"; then
        PY="$cmd"
        break
    fi
done
[ -z "$PY" ] && fail "Python 3.11 or newer is needed.
   Download it from https://www.python.org/downloads/ and install it,
   then double-click run.command again."

# A setup made with an older Python can't be reused, so start it fresh.
if [ -d "venv" ] && ! new_enough venv/bin/python; then
    rm -rf venv
fi

if [ ! -d "venv" ]; then
    echo "First-time setup — this only happens once..."
    "$PY" -m venv venv || fail "Couldn't create the app's Python environment."
fi

# Install packages the first time, and again whenever requirements.txt changes
# (for example after downloading a newer version of the app). The copy saved
# at the end means a failed install is retried next time instead of skipped.
if ! cmp -s requirements.txt venv/installed-requirements.txt; then
    echo "Installing the app's packages (needs internet, takes about a minute)..."
    ./venv/bin/python -m pip install --quiet --upgrade pip \
        && ./venv/bin/python -m pip install --quiet -r requirements.txt \
        || fail "Couldn't install the app's packages. Check your internet connection and try again."
    cp requirements.txt venv/installed-requirements.txt
fi

echo "Starting Personal Finance Manager..."
echo "(Keep this window open while you use the app. Close it to stop the app.)"
./venv/bin/streamlit run app.py || fail "The app stopped because of an error (see the messages above)."
