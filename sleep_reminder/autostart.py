"""Windows startup autostart manager using HKCU Run registry key."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REG_SUBKEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "SleepReminderApp"


def get_launch_command() -> str:
    """Return the command line to silently start the application on Windows login."""
    root_dir = Path(__file__).resolve().parent.parent
    launch_vbs = root_dir / "launch.vbs"
    if launch_vbs.exists():
        return f'wscript.exe "{launch_vbs}" --minimized'

    python_exe = sys.executable
    if "python.exe" in python_exe.lower():
        pythonw_candidate = python_exe.lower().replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw_candidate):
            python_exe = pythonw_candidate

    main_script = root_dir / "run.py"
    return f'"{python_exe}" "{main_script}" --minimized'


def is_autostart_enabled() -> bool:
    """Check if the application is currently registered to run at startup."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart(enable: bool) -> bool:
    """Register or unregister the application in Windows startup."""
    if sys.platform != "win32":
        return False

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_SUBKEY, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                cmd = get_launch_command()
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False
