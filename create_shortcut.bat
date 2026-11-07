@echo off
REM Creates a Desktop Shortcut for Sleep Reminder with the custom Moon Icon
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "TARGET_VBS=%~dp0launch.vbs"
set "ICON_FILE=%~dp0sleep_reminder\assets\icon.ico"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\Sleep Reminder.lnk"

echo Creating Desktop shortcut...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%SHORTCUT_PATH%'); " ^
    "$s.TargetPath = 'wscript.exe'; " ^
    "$s.Arguments = '\"%TARGET_VBS%\"'; " ^
    "$s.WorkingDirectory = '%~dp0'; " ^
    "$s.IconLocation = '%ICON_FILE%,0'; " ^
    "$s.Description = '🌙 Sleep Reminder - Bedtime Assistant'; " ^
    "$s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [OK] Shortcut 'Sleep Reminder' successfully created on your Desktop!
) else (
    echo [!] Shortcut could not be verified automatically.
)
timeout /t 3 >nul
