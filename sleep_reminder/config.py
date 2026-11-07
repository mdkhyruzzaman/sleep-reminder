"""Configuration manager for Sleep Reminder.

Handles loading, validation, and persistence of user preferences.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List


TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass
class AppConfig:
    bedtime: str = "22:00"
    wake_time: str = "07:00"
    wind_down_minutes: int = 30
    enable_wind_down: bool = True
    enable_bedtime_alert: bool = True
    enable_sound: bool = True
    snooze_duration_minutes: int = 10
    strict_mode: bool = False
    dark_mode: bool = True
    active_days: list[int] = None  # 0=Monday, 6=Sunday
    # Escalating reminder and shutdown settings
    enable_escalating_reminders: bool = True
    escalating_intervals: list[int] = None  # Ladder: [+30m, +15m, +10m, then repeating +5m]
    shutdown_countdown_seconds: int = 30
    autostart: bool = False
    morning_reset_hour: int = 6
    pause_media_on_reminder: bool = True
    fullscreen_reminder: bool = True
    theme_mode: str = "system"  # "system", "dark", or "light"

    def __post_init__(self):
        if self.active_days is None:
            self.active_days = [0, 1, 2, 3, 4, 5, 6]
        if self.escalating_intervals is None:
            self.escalating_intervals = [30, 15, 10, 5]
        if self.theme_mode not in ("system", "dark", "light"):
            self.theme_mode = "dark" if self.dark_mode else "light"
        self.dark_mode = (self.theme_mode != "light")
        self.validate()

    def validate(self) -> None:
        if self.theme_mode not in ("system", "dark", "light"):
            raise ValueError("theme_mode must be 'system', 'dark', or 'light'.")
        if not TIME_PATTERN.match(self.bedtime):
            raise ValueError(f"Invalid bedtime format '{self.bedtime}'. Expected HH:MM in 24-hour format.")
        if not TIME_PATTERN.match(self.wake_time):
            raise ValueError(f"Invalid wake_time format '{self.wake_time}'. Expected HH:MM in 24-hour format.")
        if self.wind_down_minutes < 0 or self.wind_down_minutes > 180:
            raise ValueError("wind_down_minutes must be between 0 and 180 minutes.")
        if self.snooze_duration_minutes < 1 or self.snooze_duration_minutes > 60:
            raise ValueError("snooze_duration_minutes must be between 1 and 60 minutes.")
        if not all(isinstance(d, int) and 0 <= d <= 6 for d in self.active_days):
            raise ValueError("active_days must contain integers between 0 (Mon) and 6 (Sun).")
        if not isinstance(self.escalating_intervals, list) or not self.escalating_intervals:
            raise ValueError("escalating_intervals must be a non-empty list of integers.")
        if not all(isinstance(x, int) and x > 0 for x in self.escalating_intervals):
            raise ValueError("All escalating interval values must be positive integers.")
        if not (5 <= self.shutdown_countdown_seconds <= 300):
            raise ValueError("shutdown_countdown_seconds must be between 5 and 300 seconds.")
        if not (0 <= self.morning_reset_hour <= 23):
            raise ValueError("morning_reset_hour must be between 0 and 23.")


class ConfigManager:
    """Manages reading and writing AppConfig to the filesystem."""

    DEFAULT_CONFIG_DIR = Path.home() / ".sleep_reminder"
    CONFIG_FILENAME = "settings.json"

    def __init__(self, config_dir: Path | str | None = None) -> None:
        if config_dir is None:
            self.config_dir = self.DEFAULT_CONFIG_DIR
        else:
            self.config_dir = Path(config_dir)

        self.config_path = self.config_dir / self.CONFIG_FILENAME
        self._config: AppConfig = self.load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def load(self) -> AppConfig:
        if not self.config_path.exists():
            default = AppConfig()
            self._save_to_disk(default)
            return default

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data: Dict[str, Any] = json.load(f)
            # Filter unknown keys to avoid crashes on forward/backward compatibility
            known_keys = AppConfig.__annotations__.keys()
            filtered_data = {k: v for k, v in data.items() if k in known_keys}
            cfg = AppConfig(**filtered_data)
            return cfg
        except Exception:
            # Fall back to default on corrupted file
            default = AppConfig()
            return default

    def save(self, config: AppConfig | None = None) -> None:
        if config is not None:
            config.validate()
            self._config = config
        self._save_to_disk(self._config)

    def _save_to_disk(self, config: AppConfig) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2)
        except OSError:
            # If home dir cannot be written, try local directory fallback
            fallback_dir = Path(".sleep_data")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            fallback_path = fallback_dir / self.CONFIG_FILENAME
            with open(fallback_path, "w", encoding="utf-8") as f:
                json.dump(asdict(config), f, indent=2)
