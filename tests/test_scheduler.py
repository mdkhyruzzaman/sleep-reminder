"""Unit tests for the Sleep Scheduler timing logic and escalating interval ladder."""

import datetime
import unittest

from sleep_reminder.config import AppConfig
from sleep_reminder.scheduler import ReminderState, SleepScheduler


class TestSleepScheduler(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig(
            bedtime="22:00",
            escalating_intervals=[30, 15, 10, 5],
            morning_reset_hour=6,
        )
        self.scheduler = SleepScheduler(config=self.config)

    def test_checkpoint_calculation(self):
        bedtime = datetime.datetime(2026, 11, 7, 22, 0, 0)

        # Stage 0: 22:00 (Bedtime)
        cp0 = self.scheduler.get_checkpoint(0, bedtime)
        self.assertEqual(cp0, datetime.datetime(2026, 11, 7, 22, 0, 0))

        # Stage 1: +30 min -> 22:30
        cp1 = self.scheduler.get_checkpoint(1, bedtime)
        self.assertEqual(cp1, datetime.datetime(2026, 11, 7, 22, 30, 0))

        # Stage 2: +15 min -> 22:45
        cp2 = self.scheduler.get_checkpoint(2, bedtime)
        self.assertEqual(cp2, datetime.datetime(2026, 11, 7, 22, 45, 0))

        # Stage 3: +10 min -> 22:55
        cp3 = self.scheduler.get_checkpoint(3, bedtime)
        self.assertEqual(cp3, datetime.datetime(2026, 11, 7, 22, 55, 0))

        # Stage 4: +5 min -> 23:00
        cp4 = self.scheduler.get_checkpoint(4, bedtime)
        self.assertEqual(cp4, datetime.datetime(2026, 11, 7, 23, 0, 0))

        # Stage 5: +5 min -> 23:05
        cp5 = self.scheduler.get_checkpoint(5, bedtime)
        self.assertEqual(cp5, datetime.datetime(2026, 11, 7, 23, 5, 0))

        # Stage 6: +5 min -> 23:10
        cp6 = self.scheduler.get_checkpoint(6, bedtime)
        self.assertEqual(cp6, datetime.datetime(2026, 11, 7, 23, 10, 0))

    def test_stage_and_overdue_minutes(self):
        bedtime = datetime.datetime(2026, 11, 7, 22, 0, 0)

        # Exact bedtime
        s0, o0 = self.scheduler.get_stage_and_minutes_overdue(bedtime, bedtime)
        self.assertEqual(s0, 0)
        self.assertEqual(o0, 0)

        # 10 minutes past bedtime (between stage 0 and stage 1)
        s_mid, o_mid = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=10), bedtime
        )
        self.assertEqual(s_mid, 0)
        self.assertEqual(o_mid, 10)

        # Exactly 30 minutes past bedtime
        s1, o1 = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=30), bedtime
        )
        self.assertEqual(s1, 1)
        self.assertEqual(o1, 30)

        # Exactly 45 minutes past bedtime
        s2, o2 = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=45), bedtime
        )
        self.assertEqual(s2, 2)
        self.assertEqual(o2, 45)

        # Exactly 55 minutes past bedtime
        s3, o3 = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=55), bedtime
        )
        self.assertEqual(s3, 3)
        self.assertEqual(o3, 55)

        # 60 minutes past bedtime
        s4, o4 = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=60), bedtime
        )
        self.assertEqual(s4, 4)
        self.assertEqual(o4, 60)

        # 75 minutes past bedtime (75 - 55 = 20 -> 4 intervals of 5 min -> stage 3 + 4 = 7)
        s7, o7 = self.scheduler.get_stage_and_minutes_overdue(
            bedtime + datetime.timedelta(minutes=75), bedtime
        )
        self.assertEqual(s7, 7)
        self.assertEqual(o7, 75)

    def test_custom_bedtime_support(self):
        custom_cfg = AppConfig(
            bedtime="23:15",
            escalating_intervals=[30, 15, 10, 5],
        )
        custom_scheduler = SleepScheduler(config=custom_cfg)
        bedtime = datetime.datetime(2026, 11, 7, 23, 15, 0)

        self.assertEqual(custom_scheduler.get_checkpoint(0, bedtime), datetime.datetime(2026, 11, 7, 23, 15, 0))
        # 23:15 + 30m -> 23:45
        self.assertEqual(custom_scheduler.get_checkpoint(1, bedtime), datetime.datetime(2026, 11, 7, 23, 45, 0))
        # 23:45 + 15m -> 00:00 next day
        self.assertEqual(custom_scheduler.get_checkpoint(2, bedtime), datetime.datetime(2026, 11, 8, 0, 0, 0))
        # 00:00 + 10m -> 00:10
        self.assertEqual(custom_scheduler.get_checkpoint(3, bedtime), datetime.datetime(2026, 11, 8, 0, 10, 0))
        # 00:10 + 5m -> 00:15
        self.assertEqual(custom_scheduler.get_checkpoint(4, bedtime), datetime.datetime(2026, 11, 8, 0, 15, 0))

    def test_next_checkpoint(self):
        simulated_now = datetime.datetime(2026, 11, 7, 21, 30, 0)
        stage, next_cp = self.scheduler.get_next_checkpoint(simulated_now)
        self.assertEqual(stage, 0)

        simulated_now = datetime.datetime(2026, 11, 7, 22, 5, 0)
        stage, next_cp = self.scheduler.get_next_checkpoint(simulated_now)
        self.assertEqual(stage, 1)

    def test_pause_and_resume(self):
        self.scheduler.pause_for_today(True)
        self.assertTrue(self.scheduler.is_paused_for_today())
        self.scheduler.pause_for_today(False)
        self.assertFalse(self.scheduler.is_paused_for_today())

    def test_snooze_and_confirm(self):
        self.scheduler.snooze(15)
        self.assertEqual(self.scheduler.state, ReminderState.SNOOZED)
        self.assertIsNotNone(self.scheduler.snooze_until)

        self.scheduler.confirm_sleep()
        self.assertEqual(self.scheduler.state, ReminderState.COMPLETED)
        self.assertIsNone(self.scheduler.snooze_until)


if __name__ == "__main__":
    unittest.main()
