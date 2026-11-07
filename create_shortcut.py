"""
Create Desktop Shortcut for Sleep Reminder.
Dynamically resolves Windows Desktop directory (including OneDrive-backed Desktops).
"""

from __future__ import annotations
import os
import sys
import winreg
import subprocess
from pathlib import Path


def get_desktop_dir() -> Path:
    candidates: list[Path] = []

    # 1. Registry User Shell Folders (primary source of truth in Windows)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        expanded = os.path.expandvars(val)
        candidates.append(Path(expanded))
    except Exception:
        pass

    # 2. Registry Shell Folders (legacy fallback)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders",
        )
        val, _ = winreg.QueryValueEx(key, "Desktop")
        candidates.append(Path(os.path.expandvars(val)))
    except Exception:
        pass

    # 3. Known OneDrive and local profile locations
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidates.append(Path(userprofile) / "OneDrive" / "Desktop")
        candidates.append(Path(userprofile) / "Desktop")

    for path in candidates:
        if path.is_dir():
            return path

    # Fallback: create %USERPROFILE%\Desktop if none exists
    fallback = Path(userprofile or ".") / "Desktop"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return fallback


def create_desktop_shortcut() -> bool:
    repo_root = Path(__file__).resolve().parent
    launch_vbs = repo_root / "launch.vbs"
    icon_file = repo_root / "sleep_reminder" / "assets" / "icon.ico"
    desktop = get_desktop_dir()
    shortcut_path = desktop / "Sleep Reminder.lnk"

    print("=" * 62)
    print("🌙  Sleep Reminder - Desktop Shortcut Creator")
    print("=" * 62)
    print(f"Target Launcher:  {launch_vbs}")
    print(f"Crescent Icon:    {icon_file}")
    print(f"Active Desktop:   {desktop}")
    print(f"Shortcut Path:    {shortcut_path}")
    print("-" * 62)

    ps_cmd = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = 'wscript.exe'; "
        f"$s.Arguments = '\"{launch_vbs}\"'; "
        f"$s.WorkingDirectory = '{repo_root}'; "
        f"$s.IconLocation = '{icon_file},0'; "
        f"$s.Description = 'Sleep Reminder - Bedtime Assistant'; "
        f"$s.Save()"
    )

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        print(f"[!] PowerShell warning: {e}")

    if shortcut_path.is_file():
        print(f"[OK] Shortcut successfully created on your Desktop!")
        print(f"     Location: {shortcut_path}")
        print("=" * 62)
        return True
    else:
        print(f"[!] Shortcut could not be verified automatically at: {shortcut_path}")
        print("=" * 62)
        return False


if __name__ == "__main__":
    success = create_desktop_shortcut()
    if sys.stdin.isatty():
        input("\nPress Enter to exit...")
    sys.exit(0 if success else 1)
