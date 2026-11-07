"""Main application entry point for Sleep Reminder.

Supports running directly via:
    python main.py
or
    python run.py
or
    pythonw main.py --minimized
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from sleep_reminder.icon import set_windows_app_id
from sleep_reminder.app import run

if __name__ == "__main__":
    set_windows_app_id()
    run()
