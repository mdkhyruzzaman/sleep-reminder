@echo off
REM Sleep Reminder Launcher
cd /d "%~dp0"

IF EXIST ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" main.py %*
) ELSE IF EXIST ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" main.py %*
) ELSE (
    start "" pythonw main.py %*
)
