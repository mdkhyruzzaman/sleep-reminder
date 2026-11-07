"""
Sleep Reminder entry point.
Run with: python run.py
"""

import sys
from pathlib import Path

# Ensure workspace root is in python path
workspace_dir = Path(__file__).resolve().parent
if str(workspace_dir) not in sys.path:
    sys.path.insert(0, str(workspace_dir))

from sleep_reminder.icon import set_windows_app_id
from sleep_reminder.app import run

if __name__ == "__main__":
    set_windows_app_id()
    run()
