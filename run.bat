@echo off
REM Double-click this file (Windows) to start the Personal Finance Manager.
REM It sets up everything the first time, then opens the app in your browser.
cd /d "%~dp0"

REM Find Python 3.11 or newer. "py" is the Python launcher that python.org installs.
set "PY="
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul && set "PY=python"
if not defined PY (
    echo.
    echo Python 3.11 or newer is needed.
    echo Download it from https://www.python.org/downloads/ and install it.
    echo During install, tick "Add python.exe to PATH". Then double-click run.bat again.
    goto :fail
)

REM A setup made with an older Python can't be reused, so start it fresh.
if exist "venv\" (
    venv\Scripts\python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul || rmdir /s /q venv
)

if not exist "venv\" (
    echo First-time setup - this only happens once...
    %PY% -m venv venv || (echo Couldn't create the app's Python environment. & goto :fail)
)

REM Install packages the first time, and again whenever requirements.txt changes.
REM The copy saved at the end means a failed install is retried next time.
fc /b requirements.txt venv\installed-requirements.txt >nul 2>nul && goto :start
echo Installing the app's packages (needs internet, takes about a minute)...
venv\Scripts\python -m pip install --quiet --upgrade pip
venv\Scripts\python -m pip install --quiet -r requirements.txt || (echo Couldn't install the app's packages. Check your internet connection and try again. & goto :fail)
copy /y requirements.txt venv\installed-requirements.txt >nul

:start
echo Starting Personal Finance Manager...
echo (Keep this window open while you use the app. Close it to stop the app.)
venv\Scripts\streamlit run app.py || goto :fail
exit /b 0

:fail
echo.
pause
exit /b 1
