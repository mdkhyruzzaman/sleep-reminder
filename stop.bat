@echo off
REM Cleanly stops Sleep Reminder and unregisters autostart
echo ==========================================
echo  🌙 Stopping Sleep Reminder...
echo ==========================================

REM 1. Remove Windows autostart registry entry
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "SleepReminderApp" /f >nul 2>&1

REM 2. Terminate running pythonw instances running Sleep Reminder
powershell -NoProfile -Command ^
    "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*sleep_reminder*' -or $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo.
echo [OK] Sleep Reminder has been stopped and Windows startup has been disabled.
echo Next time your laptop boots up, Sleep Reminder will NOT auto-run.
echo To re-enable and run again, simply double-click 'launch.vbs'.
echo.
timeout /t 3
