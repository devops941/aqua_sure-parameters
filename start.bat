@echo off
REM =========================================================
REM  AquaSure — Windows convenience launcher
REM  Usage:
REM    start.bat              — Flask API + static frontend
REM    start.bat streamlit    — Streamlit dashboard
REM    start.bat api --no-browser
REM  Any extra arguments are forwarded to run.py (%*)
REM =========================================================

REM Change to the directory containing this batch file so relative
REM paths in run.py resolve correctly regardless of where the user
REM invokes start.bat from.
cd /d "%~dp0"

REM Activate the project virtual environment (if it exists)
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else (
    echo [AquaSure] WARNING: venv\Scripts\activate.bat not found.
    echo [AquaSure] Running with the system Python. Install dependencies first:
    echo [AquaSure]   pip install -r requirements.txt
    echo [AquaSure]   pip install -r backend\requirements.txt
    echo.
)

REM Launch the unified Python launcher, forwarding all CLI arguments
python run.py %*
