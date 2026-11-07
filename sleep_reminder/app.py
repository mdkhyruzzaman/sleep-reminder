"""
Application orchestrator and entry point for Sleep Reminder.
"""

from __future__ import annotations
import sys
from sleep_reminder.audio import SoundManager
from sleep_reminder.config import ConfigManager
from sleep_reminder.history import HistoryManager
from sleep_reminder.icon import set_windows_app_id
from sleep_reminder.ui.main_window import MainWindow


def run() -> None:
    """Bootstraps and runs the Sleep Reminder application."""
    set_windows_app_id()
    config_mgr = ConfigManager()
    history_mgr = HistoryManager()
    sound_mgr = SoundManager(enabled=config_mgr.config.enable_sound)

    app = MainWindow(
        config_mgr=config_mgr,
        history_mgr=history_mgr,
        sound_mgr=sound_mgr,
    )

    # Check for --minimized argument (useful for startup on login)
    if "--minimized" in sys.argv or "-m" in sys.argv:
        app.withdraw()

    try:
        app.mainloop()
    except KeyboardInterrupt:
        app.exit_application()
        sys.exit(0)


if __name__ == "__main__":
    run()
