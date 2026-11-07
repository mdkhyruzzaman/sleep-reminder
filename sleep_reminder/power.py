"""Windows system power actions (shutdown, abort shutdown, sleep/suspend)."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys


def shutdown_system(seconds: int = 30, comment: str = "Sleep Reminder: Bedtime shutdown") -> bool:
    """Initiate a Windows shutdown with a grace period in seconds.

    The user can abort this countdown using abort_shutdown().
    """
    if sys.platform != "win32":
        return False

    try:
        # shutdown /s /t <seconds> /c "<comment>"
        subprocess.run(
            ["shutdown", "/s", "/t", str(max(0, int(seconds))), "/c", comment],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception as e:
        print(f"Error initiating shutdown: {e}", file=sys.stderr)
        return False


def abort_shutdown() -> bool:
    """Cancel any pending Windows shutdown countdown."""
    if sys.platform != "win32":
        return False

    try:
        # shutdown /a
        subprocess.run(
            ["shutdown", "/a"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except Exception as e:
        print(f"Error aborting shutdown: {e}", file=sys.stderr)
        return False


def sleep_system() -> bool:
    """Put the Windows machine into Sleep / Suspend state."""
    if sys.platform != "win32":
        return False

    try:
        powrprof = ctypes.windll.powrprof
        result = powrprof.SetSuspendState(0, 1, 0)
        return bool(result)
    except Exception as e:
        print(f"Error suspending system: {e}", file=sys.stderr)
        try:
            subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)
            return True
        except Exception:
            return False
