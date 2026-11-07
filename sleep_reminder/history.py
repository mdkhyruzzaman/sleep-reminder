"""
Sleep history and habit streak tracker.
Logs bedtimes and computes consistency metrics.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass
from datetime import datetime, date, timedelta
import json
from pathlib import Path
from typing import List, Dict, Any


@dataclass
class SleepLogEntry:
    timestamp: str  # ISO format
    target_bedtime: str
    action: str  # "slept_on_time", "slept_late", "snoozed", "dismissed"
    note: str = ""


class HistoryManager:
    """Manages sleep consistency logs and streak calculations."""

    DEFAULT_DIR = Path.home() / ".sleep_reminder"
    HISTORY_FILE = "history.json"

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        if storage_dir is None:
            self.storage_dir = self.DEFAULT_DIR
        else:
            self.storage_dir = Path(storage_dir)

        self.file_path = self.storage_dir / self.HISTORY_FILE
        self.entries: List[SleepLogEntry] = []
        self.load()

    def load(self) -> None:
        if not self.file_path.exists():
            self.entries = []
            return

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.entries = [SleepLogEntry(**item) for item in data]
        except Exception:
            self.entries = []

    def save(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self.entries], f, indent=2)
        except OSError:
            fallback = Path(".sleep_data")
            fallback.mkdir(parents=True, exist_ok=True)
            self.file_path = fallback / self.HISTORY_FILE
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([asdict(e) for e in self.entries], f, indent=2)

    def log_event(self, target_bedtime: str, action: str, note: str = "") -> SleepLogEntry:
        entry = SleepLogEntry(
            timestamp=datetime.now().isoformat(),
            target_bedtime=target_bedtime,
            action=action,
            note=note,
        )
        self.entries.append(entry)
        self.save()
        return entry

    def calculate_stats(self) -> Dict[str, Any]:
        """Calculates current streak, total entries, and recent consistency."""
        if not self.entries:
            return {
                "current_streak": 0,
                "total_logged": 0,
                "recent_on_time_rate": 0,
                "last_logged": None,
            }

        # Filter only confirmed sleeps: "slept_on_time" or "slept_late"
        sleep_events = [e for e in self.entries if e.action in ("slept_on_time", "slept_late")]
        if not sleep_events:
            return {
                "current_streak": 0,
                "total_logged": len(self.entries),
                "recent_on_time_rate": 0,
                "last_logged": self.entries[-1].timestamp if self.entries else None,
            }

        # Group by day
        dates_on_time: set[date] = set()
        dates_logged: set[date] = set()

        for e in sleep_events:
            dt = datetime.fromisoformat(e.timestamp).date()
            dates_logged.add(dt)
            if e.action == "slept_on_time":
                dates_on_time.add(dt)

        # Compute current streak of consecutive on-time days
        today = date.today()
        streak = 0
        check_day = today

        # If today isn't logged yet, streak could still be valid from yesterday
        if check_day not in dates_on_time:
            check_day = today - timedelta(days=1)

        while check_day in dates_on_time:
            streak += 1
            check_day -= timedelta(days=1)

        # Calculate last 7 days rate
        last_7_days = [today - timedelta(days=i) for i in range(7)]
        logged_last_7 = sum(1 for d in last_7_days if d in dates_logged)
        on_time_last_7 = sum(1 for d in last_7_days if d in dates_on_time)
        rate = int((on_time_last_7 / max(1, logged_last_7)) * 100) if logged_last_7 > 0 else 0

        return {
            "current_streak": streak,
            "total_logged": len(self.entries),
            "recent_on_time_rate": rate,
            "last_logged": self.entries[-1].timestamp,
        }

    def get_recent_entries(self, limit: int = 10) -> List[SleepLogEntry]:
        """Returns the most recent entries up to `limit`."""
        return self.entries[-limit:][::-1]
