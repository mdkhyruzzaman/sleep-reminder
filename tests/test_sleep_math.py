"""Unit tests for sleep_math."""
import unittest
from datetime import datetime
from sleep_reminder.sleep_math import (
    calculate_bedtimes_for_wake_time,
    calculate_wake_times_if_sleep_now,
    format_seconds_remaining,
    get_bedtime_and_winddown,
)

class TestSleepMath(unittest.TestCase):
    def test_wake_time_cycles(self):
        # Target wake at 07:00
        options = calculate_bedtimes_for_wake_time("07:00", fall_asleep_minutes=14)
        self.assertEqual(len(options), 4)
        # 5 cycles = 7.5 hours (450 mins) + 14 mins = 464 mins before 07:00
        # 07:00 minus 7h44m = 23:16
        opt_5 = [o for o in options if o["cycles"] == 5][0]
        self.assertEqual(opt_5["bedtime"], "23:16")

    def test_wake_times_sleep_now(self):
        now = datetime(2026, 11, 7, 22, 0, 0)
        options = calculate_wake_times_if_sleep_now(now=now, fall_asleep_minutes=14)
        self.assertEqual(len(options), 4)
        # 5 cycles = 450 mins + 14 mins = 464 mins = 7h 44m -> 05:44
        opt_5 = [o for o in options if o["cycles"] == 5][0]
        self.assertEqual(opt_5["wake_time"], "05:44")

    def test_format_countdown(self):
        self.assertEqual(format_seconds_remaining(3665), "1h 01m 05s")
        self.assertEqual(format_seconds_remaining(125), "02m 05s")
        self.assertEqual(format_seconds_remaining(0), "00m 00s")

    def test_get_bedtime_and_winddown_same_day(self):
        now = datetime(2026, 11, 7, 20, 0, 0)
        wd, bt = get_bedtime_and_winddown("23:00", 30, now=now)
        self.assertEqual(bt.hour, 23)
        self.assertEqual(bt.minute, 0)
        self.assertEqual(wd.hour, 22)
        self.assertEqual(wd.minute, 30)

    def test_get_bedtime_and_winddown_next_day(self):
        # Bedtime was 22:00, current time is 23:30 (already past)
        now = datetime(2026, 11, 7, 23, 30, 0)
        wd, bt = get_bedtime_and_winddown("22:00", 30, now=now)
        # Should roll over to tomorrow
        self.assertEqual(bt.day, 8)
        self.assertEqual(bt.hour, 22)
        self.assertEqual(wd.hour, 21)
        self.assertEqual(wd.minute, 30)

if __name__ == "__main__":
    unittest.main()
