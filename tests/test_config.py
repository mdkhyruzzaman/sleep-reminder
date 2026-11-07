"""Unit tests for config, escalating intervals, and history."""
import tempfile
import unittest
from pathlib import Path
from sleep_reminder.config import AppConfig, ConfigManager
from sleep_reminder.history import HistoryManager


class TestConfig(unittest.TestCase):
    def test_default_config(self):
        cfg = AppConfig()
        self.assertIn(cfg.bedtime, ("22:00", "23:00"))
        self.assertEqual(cfg.wake_time, "07:00")
        self.assertEqual(cfg.wind_down_minutes, 30)
        self.assertEqual(cfg.escalating_intervals, [30, 15, 10, 5])
        self.assertEqual(cfg.shutdown_countdown_seconds, 30)
        self.assertTrue(cfg.enable_escalating_reminders)
        self.assertTrue(cfg.pause_media_on_reminder)
        self.assertTrue(cfg.fullscreen_reminder)

    def test_invalid_time_raises(self):
        with self.assertRaises(ValueError):
            AppConfig(bedtime="25:99")

    def test_invalid_intervals_raises(self):
        with self.assertRaises(ValueError):
            AppConfig(escalating_intervals=[])
        with self.assertRaises(ValueError):
            AppConfig(escalating_intervals=[-5, 10])

    def test_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = ConfigManager(config_dir=tmpdir)
            cfg = mgr.config
            cfg.bedtime = "22:15"
            cfg.escalating_intervals = [25, 15, 10, 5]
            mgr.save(cfg)

            # Reload
            mgr2 = ConfigManager(config_dir=tmpdir)
            self.assertEqual(mgr2.config.bedtime, "22:15")
            self.assertEqual(mgr2.config.escalating_intervals, [25, 15, 10, 5])


class TestHistory(unittest.TestCase):
    def test_history_logging_and_streak(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            hm = HistoryManager(storage_dir=tmpdir)
            self.assertEqual(hm.calculate_stats()["current_streak"], 0)

            hm.log_event("23:00", "slept_on_time")
            stats = hm.calculate_stats()
            self.assertEqual(stats["current_streak"], 1)
            self.assertEqual(stats["total_logged"], 1)


if __name__ == "__main__":
    unittest.main()
