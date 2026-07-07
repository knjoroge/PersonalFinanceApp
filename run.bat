@echo off
REM Double-click this file (Windows) to start the Personal Finance Manager.
REM It sets up everything the first time, then opens the app in your browser.
cd /d "%~dp0"

REM Create the virtual environment on first run.
if not exist "venv\" (
    echo First-time setup - this only happens once...
    python -m venv venv
    call venv\Scripts\python -m pip install --quiet --upgrade pip
    call venv\Scripts\pip install --quiet -r requirements.txt
)

echo Starting Personal Finance Manager...
call venv\Scripts\streamlit run app.py
