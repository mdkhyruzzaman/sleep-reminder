"""
Scheduler and background monitoring engine for Sleep Reminder.
Coordinates countdowns, wind-down triggers, bedtime alerts, and escalating reminder checkpoints.
"""

from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
import inspect
import threading
import time
from typing import Callable, List, Optional, Tuple

from sleep_reminder.config import AppConfig
from sleep_reminder.sleep_math import parse_time_str, format_seconds_remaining


class ReminderState(Enum):
    IDLE = "idle"
    WIND_DOWN_ACTIVE = "wind_down_active"
    BEDTIME_ACTIVE = "bedtime_active"
    ESCALATING_ACTIVE = "escalating_active"
    SNOOZED = "snoozed"
    COMPLETED = "completed"


class SleepScheduler:
    """Monitors time and triggers callbacks for sleep milestones and escalating reminders."""

    def __init__(
        self,
        config: AppConfig,
        on_tick: Optional[Callable[[str, str, float], None]] = None,
        on_wind_down: Optional[Callable[[], None]] = None,
        on_bedtime: Optional[Callable[..., None]] = None,
    ) -> None:
        self.config = config
        self.on_tick = on_tick
        self.on_wind_down = on_wind_down
        self.on_bedtime = on_bedtime

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self.state = ReminderState.IDLE
        self.snooze_until: Optional[datetime] = None
        self._last_wind_down_cycle: Optional[str] = None
        self._last_triggered_checkpoint: Optional[datetime] = None
        self._current_bedtime_cycle_id: Optional[str] = None
        self._current_stage: int = 0
        self._paused_for_today: bool = False

    def start(self) -> None:
        """Starts the scheduler thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SleepSchedulerThread")
            self._thread.start()

    def stop(self) -> None:
        """Stops the scheduler thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            self.config = config
            self._last_wind_down_cycle = None
            self._last_triggered_checkpoint = None
            self._current_bedtime_cycle_id = None

    def pause_for_today(self, paused: bool = True) -> None:
        with self._lock:
            self._paused_for_today = paused

    def is_paused_for_today(self) -> bool:
        with self._lock:
            return self._paused_for_today

    def snooze(self, minutes: Optional[int] = None) -> None:
        """Activates snooze mode for the specified duration."""
        if minutes is None:
            minutes = self.config.snooze_duration_minutes

        with self._lock:
            self.snooze_until = datetime.now() + timedelta(minutes=minutes)
            self.state = ReminderState.SNOOZED

    def confirm_sleep(self) -> None:
        """User confirms they are heading to bed or shutting down."""
        with self._lock:
            self.snooze_until = None
            self.state = ReminderState.COMPLETED

    def dismiss(self) -> None:
        """Dismisses alerts for the remainder of the current cycle."""
        with self._lock:
            self.snooze_until = None
            self.state = ReminderState.COMPLETED

    def get_reference_bedtime(self, now: Optional[datetime] = None) -> datetime:
        """Calculate the anchor bedtime corresponding to the current sleep cycle."""
        now = now or datetime.now()
        b_hour, b_min = parse_time_str(self.config.bedtime)

        if now.hour >= self.config.morning_reset_hour:
            if b_hour >= self.config.morning_reset_hour:
                bedtime_dt = now.replace(hour=b_hour, minute=b_min, second=0, microsecond=0)
            else:
                tomorrow = now + timedelta(days=1)
                bedtime_dt = tomorrow.replace(hour=b_hour, minute=b_min, second=0, microsecond=0)
        else:
            if b_hour >= self.config.morning_reset_hour:
                yesterday = now - timedelta(days=1)
                bedtime_dt = yesterday.replace(hour=b_hour, minute=b_min, second=0, microsecond=0)
            else:
                bedtime_dt = now.replace(hour=b_hour, minute=b_min, second=0, microsecond=0)

        return bedtime_dt

    def get_checkpoint(self, stage: int, bedtime_dt: datetime) -> datetime:
        """Calculate the exact datetime for a reminder stage (0, 1, 2, ...)."""
        if stage <= 0:
            return bedtime_dt

        intervals = self.config.escalating_intervals or [30, 15, 10, 5]
        last_interval = intervals[-1] if intervals else 5

        total_minutes = 0
        for i in range(stage):
            if i < len(intervals):
                total_minutes += intervals[i]
            else:
                total_minutes += last_interval

        return bedtime_dt + timedelta(minutes=total_minutes)

    def get_stage_and_minutes_overdue(self, dt: datetime, bedtime_dt: datetime) -> Tuple[int, int]:
        """Determine the current stage index and overdue minutes."""
        if dt < bedtime_dt:
            return 0, 0

        diff_minutes = max(0, int((dt - bedtime_dt).total_seconds() / 60))
        intervals = self.config.escalating_intervals or [30, 15, 10, 5]
        last_interval = intervals[-1] if intervals else 5

        cumulative = 0
        stage = 0
        while True:
            next_interval = intervals[stage] if stage < len(intervals) else last_interval
            if cumulative + next_interval <= diff_minutes:
                cumulative += next_interval
                stage += 1
            else:
                break

        return stage, diff_minutes

    def get_next_checkpoint(self, now: Optional[datetime] = None) -> Tuple[int, datetime]:
        """Return (stage, next_checkpoint_dt)."""
        now = now or datetime.now()
        bedtime_dt = self.get_reference_bedtime(now)

        if now < bedtime_dt:
            return 0, bedtime_dt

        stage = 0
        while True:
            cp = self.get_checkpoint(stage, bedtime_dt)
            if cp > now:
                return stage, cp
            stage += 1
            if stage > 1000:
                return stage, now + timedelta(minutes=5)

    def _run_loop(self) -> None:
        while self._running:
            try:
                self._check_and_notify()
            except Exception:
                pass
            time.sleep(1.0)

    def _invoke_bedtime_callback(self, stage: int, minutes_overdue: int, next_minutes: int) -> None:
        if not self.on_bedtime:
            return
        try:
            sig = inspect.signature(self.on_bedtime)
            params_count = len(sig.parameters)
            if params_count >= 3:
                self.on_bedtime(stage, minutes_overdue, next_minutes)
            elif params_count == 1:
                self.on_bedtime(stage)
            else:
                self.on_bedtime()
        except Exception:
            try:
                self.on_bedtime()
            except Exception:
                pass

    def _check_and_notify(self) -> None:
        now = datetime.now()
        current_weekday = now.weekday()

        # Morning reset logic
        if now.hour == self.config.morning_reset_hour and now.minute == 0 and now.second < 3:
            with self._lock:
                self._paused_for_today = False
                self._last_triggered_checkpoint = None
                self._current_bedtime_cycle_id = None
                if self.state == ReminderState.COMPLETED:
                    self.state = ReminderState.IDLE

        bedtime_dt = self.get_reference_bedtime(now)
        winddown_dt = bedtime_dt - timedelta(minutes=self.config.wind_down_minutes)
        cycle_id = bedtime_dt.strftime("%Y-%m-%d-%H:%M")

        with self._lock:
            if self._paused_for_today:
                return

            # Reset state for new cycle if needed
            if self._current_bedtime_cycle_id != cycle_id:
                if now < winddown_dt:
                    self.state = ReminderState.IDLE
                    self._last_triggered_checkpoint = None
                    self._current_bedtime_cycle_id = cycle_id

            # 1. Handle Active Snooze
            if self.state == ReminderState.SNOOZED and self.snooze_until is not None:
                if now >= self.snooze_until:
                    self.snooze_until = None
                    stage, overdue = self.get_stage_and_minutes_overdue(now, bedtime_dt)
                    next_stage = stage + 1
                    next_cp = self.get_checkpoint(next_stage, bedtime_dt)
                    next_minutes = max(1, int((next_cp - now).total_seconds() / 60))
                    self.state = ReminderState.BEDTIME_ACTIVE
                    self._invoke_bedtime_callback(stage, overdue, next_minutes)

            # 2. Check Bedtime & Escalating Reminders
            elif self.config.enable_bedtime_alert and (current_weekday in self.config.active_days):
                if now >= bedtime_dt and self.state != ReminderState.COMPLETED:
                    stage, overdue = self.get_stage_and_minutes_overdue(now, bedtime_dt)
                    scheduled_cp = self.get_checkpoint(stage, bedtime_dt)

                    if self._last_triggered_checkpoint != scheduled_cp:
                        self._last_triggered_checkpoint = scheduled_cp
                        self._current_stage = stage
                        self.state = ReminderState.BEDTIME_ACTIVE

                        next_stage = stage + 1
                        next_cp = self.get_checkpoint(next_stage, bedtime_dt)
                        next_minutes = max(1, int((next_cp - now).total_seconds() / 60))

                        self._invoke_bedtime_callback(stage, overdue, next_minutes)

            # 3. Check Wind-down
            if self.config.enable_wind_down and (current_weekday in self.config.active_days):
                if winddown_dt <= now < bedtime_dt and self._last_wind_down_cycle != cycle_id:
                    self._last_wind_down_cycle = cycle_id
                    self.state = ReminderState.WIND_DOWN_ACTIVE
                    if self.on_wind_down:
                        self.on_wind_down()

            # 4. Calculate Tick info for UI
            if self.state == ReminderState.SNOOZED and self.snooze_until:
                diff = (self.snooze_until - now).total_seconds()
                event_name = "Snooze Alert"
            elif self.config.enable_wind_down and now < winddown_dt:
                diff = (winddown_dt - now).total_seconds()
                event_name = "Wind-down"
            elif now < bedtime_dt:
                diff = (bedtime_dt - now).total_seconds()
                event_name = "Bedtime"
            else:
                next_stage, next_cp = self.get_next_checkpoint(now)
                diff = (next_cp - now).total_seconds()
                event_name = f"Next Reminder (Stage {next_stage})"

        if self.on_tick:
            countdown_str = format_seconds_remaining(max(0, diff))
            self.on_tick(countdown_str, event_name, diff)
