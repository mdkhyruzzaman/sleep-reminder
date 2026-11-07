"""Unit tests for UI components instantiation, escalation stages, and behavior."""
import unittest
import tkinter as tk
from unittest.mock import MagicMock, patch

from sleep_reminder.config import ConfigManager
from sleep_reminder.history import HistoryManager
from sleep_reminder.audio import SoundManager
from sleep_reminder.ui.components import ScrollableFrame
from sleep_reminder.ui.main_window import MainWindow
from sleep_reminder.ui.modal import BedtimeModal
from sleep_reminder.ui.toast import ToastNotification


class TestUIComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
            cls.has_display = True
        except Exception:
            cls.has_display = False

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "has_display", False) and cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def test_toast_instantiation(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        snooze_mock = MagicMock()
        dismiss_mock = MagicMock()
        toast = ToastNotification(
            parent=self.root,
            title="Wind-down",
            message="Time to prepare for bed",
            on_snooze=snooze_mock,
            on_dismiss=dismiss_mock,
            duration_ms=0,
        )
        toast.update()
        toast.dismiss()
        dismiss_mock.assert_called_once()

    def test_modal_instantiation_and_escalation(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        sleep_mock = MagicMock()
        snooze_mock = MagicMock()
        modal = BedtimeModal(
            parent=self.root,
            bedtime_str="22:00",
            on_sleep=sleep_mock,
            on_snooze=snooze_mock,
            stage=0,
            minutes_overdue=0,
            next_reminder_in_minutes=30,
            fullscreen=False,
        )
        modal.update()

        # Verify Stage 0 properties
        self.assertEqual(modal.stage, 0)
        self.assertEqual(modal.minutes_overdue, 0)

        # Test escalating to Stage 1 (+30m)
        modal.update_stage(stage=1, minutes_overdue=30, next_reminder_in_minutes=15)
        modal.update()
        self.assertEqual(modal.stage, 1)
        self.assertEqual(modal.minutes_overdue, 30)
        self.assertEqual(modal.next_reminder_in_minutes, 15)

        # Test snooze call
        modal._handle_snooze()
        snooze_mock.assert_called_once_with(15)

    @patch("sleep_reminder.ui.modal.shutdown_system")
    @patch("sleep_reminder.ui.modal.abort_shutdown")
    def test_modal_shutdown_and_cancel(self, mock_abort, mock_shutdown):
        if not self.has_display:
            self.skipTest("No GUI display available")

        modal = BedtimeModal(
            parent=self.root,
            bedtime_str="22:00",
            stage=1,
            minutes_overdue=30,
            shutdown_countdown_seconds=30,
            fullscreen=False,
        )
        modal.update()

        # Click shutdown
        modal._handle_shutdown_click()
        mock_shutdown.assert_called_once()
        self.assertTrue(modal._shutdown_active)

        # Cancel shutdown
        modal._cancel_shutdown()
        mock_abort.assert_called_once()
        self.assertFalse(modal._shutdown_active)
        modal.destroy()

    def test_main_window_instantiation_and_save(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        cfg = ConfigManager()
        hist = HistoryManager()
        snd = SoundManager(enabled=False)

        app = MainWindow(cfg, hist, snd)
        app.update()

        # Change hour and save
        app.bed_hour_spin.set("22")
        app.bed_min_spin.set("45")
        app._save_schedule_settings()

        self.assertEqual(cfg.config.bedtime, "22:45")
        app.exit_application()

    @patch("sleep_reminder.media.is_system_audio_playing", return_value=True)
    @patch("sleep_reminder.media.user32")
    def test_pause_system_media_when_playing(self, mock_user32, mock_is_audio):
        from sleep_reminder.media import pause_system_media
        result = pause_system_media()
        self.assertTrue(result)
        # When media is playing, keybd_event is called to pause it
        self.assertEqual(mock_user32.keybd_event.call_count, 2)
        # And SendMessageTimeoutW is called to broadcast APPCOMMAND_MEDIA_PAUSE
        self.assertEqual(mock_user32.SendMessageTimeoutW.call_count, 1)

    @patch("sleep_reminder.media.is_system_audio_playing", return_value=False)
    @patch("sleep_reminder.media.user32")
    def test_do_not_resume_if_already_paused(self, mock_user32, mock_is_audio):
        from sleep_reminder.media import pause_system_media
        result = pause_system_media()
        self.assertTrue(result)
        # When media is already paused, keybd_event must NEVER be called to avoid resuming
        self.assertEqual(mock_user32.keybd_event.call_count, 0)
        # Only discrete APPCOMMAND_MEDIA_PAUSE is broadcasted
        self.assertEqual(mock_user32.SendMessageTimeoutW.call_count, 1)

    def test_scrollable_frame_functionality(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        # Test standalone ScrollableFrame
        sf = ScrollableFrame(self.root)
        sf.pack(fill=tk.BOTH, expand=True)

        for i in range(20):
            tk.Label(sf.content, text=f"Item {i}").pack(pady=10)

        self.root.update()
        self.assertIsNotNone(sf.canvas.cget("scrollregion"))
        sf.scroll_to_top()

        # Test MainWindow tabs are instances of ScrollableFrame
        cfg = ConfigManager()
        hist = HistoryManager()
        snd = SoundManager(enabled=False)
        app = MainWindow(cfg, hist, snd)
        app.update()

        self.assertIsInstance(app.tab_schedule, ScrollableFrame)
        self.assertIsInstance(app.tab_calculator, ScrollableFrame)
        self.assertIsInstance(app.tab_history, ScrollableFrame)
        app.exit_application()
        sf.destroy()

    def test_window_title_and_icon(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        from sleep_reminder.icon import ensure_icon_files
        from pathlib import Path

        ico_path, png_path = ensure_icon_files()
        self.assertTrue(Path(ico_path).exists())
        self.assertTrue(Path(png_path).exists())

        cfg = ConfigManager()
        hist = HistoryManager()
        snd = SoundManager(enabled=False)
        app = MainWindow(cfg, hist, snd)
        app.update()

        self.assertIn("Sleep Reminder", app.title())
        self.assertIn("🌙", app.title())
        app.exit_application()

    def test_window_maximized_on_launch(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        import sys
        cfg = ConfigManager()
        hist = HistoryManager()
        snd = SoundManager(enabled=False)
        app = MainWindow(cfg, hist, snd)
        app.update()

        if sys.platform == "win32":
            self.assertEqual(app.state(), "zoomed")
        app.exit_application()

    def test_theme_mode_switching(self):
        if not self.has_display:
            self.skipTest("No GUI display available")

        from sleep_reminder.ui import theme
        cfg = ConfigManager()
        hist = HistoryManager()
        snd = SoundManager(enabled=False)
        app = MainWindow(cfg, hist, snd)
        app.update()

        # Verify theme_select Combobox exists and is styled
        from tkinter import ttk
        self.assertIsInstance(app.theme_select, ttk.Combobox)
        self.assertIn("Light", app.theme_select.cget("values")[0])

        # Test selecting via Combobox dropdown event
        app.theme_select.set("☀️ Light")
        app._on_header_theme_selected()
        app.update()
        self.assertEqual(app.config_mgr.config.theme_mode, "light")
        self.assertFalse(theme.IS_DARK)

        app.theme_select.set("🌙 Dark")
        app._on_header_theme_selected()
        app.update()
        self.assertEqual(app.config_mgr.config.theme_mode, "dark")
        self.assertTrue(theme.IS_DARK)

        # Switch to light
        app.set_theme("light")
        app.update()
        self.assertEqual(app.config_mgr.config.theme_mode, "light")
        self.assertFalse(theme.IS_DARK)
        self.assertEqual(theme.BG_DARK, "#f8fafc")

        # Switch to dark
        app.set_theme("dark")
        app.update()
        self.assertEqual(app.config_mgr.config.theme_mode, "dark")
        self.assertTrue(theme.IS_DARK)
        self.assertEqual(theme.BG_DARK, "#0b0f19")

        # Cycle theme
        app._cycle_theme()  # dark -> system
        app.update()
        self.assertEqual(app.config_mgr.config.theme_mode, "system")

        app.exit_application()


if __name__ == "__main__":
    unittest.main()
