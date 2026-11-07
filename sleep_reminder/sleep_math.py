"""
Sleep mathematics and cycle calculation engine.
Based on 90-minute ultradian REM/non-REM sleep cycle science.
"""

from __future__ import annotations
from datetime import datetime, time, timedelta
import random
from typing import List, Dict, Any


DEFAULT_FALL_ASLEEP_MINUTES = 14
CYCLE_MINUTES = 90

SLEEP_TIPS = [
    "Turn down overhead lights 1 hour before bed to signal melatonin production.",
    "The optimal bedroom temperature for deep sleep is around 18-20°C (65-68°F).",
    "Avoid caffeine at least 6 hours before sleep as its half-life can disrupt deep sleep.",
    "Waking up at the end of a 90-minute sleep cycle helps you feel refreshed rather than groggy.",
    "A consistent bedtime and wake time helps anchor your body's circadian rhythm.",
    "Gentle stretches or deep diaphragmatic breathing can lower your heart rate before sleep.",
    "Put away high-stimulation screens or activate night-light / blue light filters.",
    "Writing down tomorrow's to-do list before bed clears cognitive clutter and anxiety.",
]


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Parses 'HH:MM' string to (hour, minute)."""
    parts = time_str.strip().split(":")
    return int(parts[0]), int(parts[1])


def get_next_occurrence(hour: int, minute: int, now: datetime | None = None) -> datetime:
    """Returns the next datetime for the given hour:minute relative to now."""
    if now is None:
        now = datetime.now()

    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def get_bedtime_and_winddown(
    bedtime_str: str,
    wind_down_minutes: int,
    now: datetime | None = None,
) -> tuple[datetime, datetime]:
    """
    Computes upcoming (wind_down_dt, bedtime_dt).
    Handles edge cases around midnight cleanly.
    """
    if now is None:
        now = datetime.now()

    b_hour, b_min = parse_time_str(bedtime_str)
    
    # Candidate for today's bedtime
    candidate_bedtime = now.replace(hour=b_hour, minute=b_min, second=0, microsecond=0)
    candidate_winddown = candidate_bedtime - timedelta(minutes=wind_down_minutes)

    # If the entire cycle for today is already in the past, move to tomorrow
    if now > candidate_bedtime:
        candidate_bedtime += timedelta(days=1)
        candidate_winddown = candidate_bedtime - timedelta(minutes=wind_down_minutes)

    return candidate_winddown, candidate_bedtime


def calculate_bedtimes_for_wake_time(
    wake_time_str: str,
    fall_asleep_minutes: int = DEFAULT_FALL_ASLEEP_MINUTES,
) -> List[Dict[str, Any]]:
    """
    Given a desired wake-up time, calculates recommended bedtimes based on 90-minute cycles.
    """
    w_hour, w_min = parse_time_str(wake_time_str)
    # Reference base date
    base_wake = datetime(2026, 1, 2, w_hour, w_min)

    cycles_options = [
        {"cycles": 6, "label": "6 Cycles (9h 00m)", "tag": "Long Rest", "color": "#38bdf8"},
        {"cycles": 5, "label": "5 Cycles (7h 30m)", "tag": "Recommended", "color": "#34d399"},
        {"cycles": 4, "label": "4 Cycles (6h 00m)", "tag": "Adequate", "color": "#fbbf24"},
        {"cycles": 3, "label": "3 Cycles (4h 30m)", "tag": "Power Minimum", "color": "#f87171"},
    ]

    results = []
    for opt in cycles_options:
        cycles = opt["cycles"]
        total_sleep_mins = (cycles * CYCLE_MINUTES) + fall_asleep_minutes
        bedtime_dt = base_wake - timedelta(minutes=total_sleep_mins)
        results.append({
            "cycles": cycles,
            "bedtime": bedtime_dt.strftime("%H:%M"),
            "display_12h": bedtime_dt.strftime("%I:%M %p").lstrip("0"),
            "duration_str": f"{cycles * 1.5:.1f} hrs",
            "tag": opt["tag"],
            "color": opt["color"],
            "label": opt["label"],
        })
    return results


def calculate_wake_times_if_sleep_now(
    now: datetime | None = None,
    fall_asleep_minutes: int = DEFAULT_FALL_ASLEEP_MINUTES,
) -> List[Dict[str, Any]]:
    """
    Calculates wake up times if the user falls asleep starting now.
    """
    if now is None:
        now = datetime.now()

    sleep_start = now + timedelta(minutes=fall_asleep_minutes)

    cycles_options = [
        {"cycles": 6, "tag": "9h Sleep - Deeply Rested", "color": "#38bdf8"},
        {"cycles": 5, "tag": "7.5h Sleep - Optimal Natural", "color": "#34d399"},
        {"cycles": 4, "tag": "6h Sleep - Fast Rebound", "color": "#fbbf24"},
        {"cycles": 3, "tag": "4.5h Sleep - Power Nap", "color": "#f87171"},
    ]

    results = []
    for opt in cycles_options:
        cycles = opt["cycles"]
        wake_dt = sleep_start + timedelta(minutes=cycles * CYCLE_MINUTES)
        results.append({
            "cycles": cycles,
            "wake_time": wake_dt.strftime("%H:%M"),
            "display_12h": wake_dt.strftime("%I:%M %p").lstrip("0"),
            "duration_str": f"{cycles * 1.5:.1f} hrs",
            "tag": opt["tag"],
            "color": opt["color"],
        })
    return results


def format_seconds_remaining(seconds: float) -> str:
    """Formats seconds into readable 'Xh Ym Zs' or 'Ym Zs'."""
    sec = max(0, int(seconds))
    hours, remainder = divmod(sec, 3600)
    minutes, s = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}h {minutes:02d}m {s:02d}s"
    return f"{minutes:02d}m {s:02d}s"


def get_random_sleep_tip() -> str:
    """Returns a random sleep science tip."""
    return random.choice(SLEEP_TIPS)
