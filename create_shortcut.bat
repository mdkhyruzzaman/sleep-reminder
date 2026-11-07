@echo off
REM Creates a Desktop Shortcut for Sleep Reminder with the custom Moon Icon
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM 1. Prefer Python script if Python is available
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0create_shortcut.py"
    if !errorlevel! equ 0 goto done
)

where python >nul 2>&1
if %errorlevel% equ 0 (
    python "%~dp0create_shortcut.py"
    if !errorlevel! equ 0 goto done
)

REM 2. PowerShell Fallback with dynamic OneDrive / local Desktop detection
echo Creating Desktop shortcut via PowerShell...

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$desktop = $ws.SpecialFolders.Item('Desktop'); " ^
    "if (-not $desktop -or -not (Test-Path $desktop)) { " ^
    "    try { " ^
    "        $p = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders').Desktop; " ^
    "        $desktop = [System.Environment]::ExpandEnvironmentVariables($p); " ^
    "    } catch {} " ^
    "} " ^
    "if (-not $desktop -or -not (Test-Path $desktop)) { " ^
    "    $oneDriveDesktop = [System.IO.Path]::Combine($env:USERPROFILE, 'OneDrive', 'Desktop'); " ^
    "    if (Test-Path $oneDriveDesktop) { $desktop = $oneDriveDesktop } else { " ^
    "        $desktop = [System.IO.Path]::Combine($env:USERPROFILE, 'Desktop'); " ^
    "        [System.IO.Directory]::CreateDirectory($desktop) | Out-Null; " ^
    "    } " ^
    "} " ^
    "$shortcutPath = [System.IO.Path]::Combine($desktop, 'Sleep Reminder.lnk'); " ^
    "$s = $ws.CreateShortcut($shortcutPath); " ^
    "$s.TargetPath = 'wscript.exe'; " ^
    "$s.Arguments = '\"%~dp0launch.vbs\"'; " ^
    "$s.WorkingDirectory = '%~dp0'; " ^
    "$s.IconLocation = '%~dp0sleep_reminder\assets\icon.ico,0'; " ^
    "$s.Description = 'Sleep Reminder - Bedtime Assistant'; " ^
    "$s.Save(); " ^
    "if (Test-Path $shortcutPath) { " ^
    "    Write-Host \"[OK] Shortcut successfully created on your Desktop!\" -ForegroundColor Green; " ^
    "    Write-Host \"     Location: $shortcutPath\"; " ^
    "} else { " ^
    "    Write-Host '[!] Shortcut could not be verified automatically.' -ForegroundColor Yellow; " ^
    "}"

:done
echo.
timeout /t 5 >nul 2>&1 || ping -n 6 127.0.0.1 >nul
