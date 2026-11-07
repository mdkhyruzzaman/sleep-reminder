"""
Main application window for Sleep Reminder.
Modern Web-Application styled desktop dashboard with segmented navigation,
digital hero countdown, interactive bedtime reminder studio, and power integrations.
"""

from __future__ import annotations
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any

from sleep_reminder.audio import SoundManager
from sleep_reminder.config import AppConfig, ConfigManager
from sleep_reminder.history import HistoryManager
from sleep_reminder.scheduler import SleepScheduler, ReminderState
from sleep_reminder.sleep_math import (
    calculate_bedtimes_for_wake_time,
    calculate_wake_times_if_sleep_now,
    get_random_sleep_tip,
    parse_time_str,
)
from sleep_reminder.autostart import is_autostart_enabled, set_autostart
from sleep_reminder.icon import apply_window_icon
from sleep_reminder.media import pause_system_media
from sleep_reminder.tray import WindowsTrayIcon
from sleep_reminder.ui import theme
from sleep_reminder.ui.components import ModernSwitch, ScrollableFrame, ScrollableTab, SegmentedNavBar, SettingRow
from sleep_reminder.ui.modal import BedtimeModal
from sleep_reminder.ui.toast import ToastNotification


class MainWindow(tk.Tk):
    """Modern Web-Application Dashboard for Sleep Reminder."""

    PRESET_BEDTIMES = [
        ("21:00", "9:00 PM"),
        ("21:30", "9:30 PM"),
        ("22:00", "10:00 PM ⭐"),
        ("22:30", "10:30 PM"),
        ("23:00", "11:00 PM"),
        ("23:30", "11:30 PM"),
        ("00:00", "12:00 AM"),
    ]

    def __init__(
        self,
        config_mgr: ConfigManager,
        history_mgr: HistoryManager,
        sound_mgr: SoundManager,
    ) -> None:
        super().__init__()
        self.config_mgr = config_mgr
        self.history_mgr = history_mgr
        self.sound_mgr = sound_mgr

        self.title("🌙 Sleep Reminder - Bedtime Assistant")
        screen_h = self.winfo_screenheight()
        # Adapt height to user's monitor and Windows display scaling (e.g., 768p, 1080p, 125%/150%)
        initial_h = min(780, max(520, screen_h - 100))
        self.geometry(f"960x{initial_h}")
        self.minsize(680, 480)

        # Apply theme configuration (System, Light, or Dark)
        initial_theme_mode = getattr(self.config_mgr.config, "theme_mode", "system")
        theme.set_theme_mode(initial_theme_mode)
        self.configure(bg=theme.BG_DARK)

        # Apply custom crescent moon icon to titlebar & Windows taskbar
        apply_window_icon(self)

        # Style configuration
        self.style = ttk.Style(self)
        theme.apply_theme_to_ttk(self.style)

        # Open maximized on launch so the user has full view, with instant restore/resize support
        try:
            self.state("zoomed")
        except Exception:
            pass

        # Active popups tracking
        self._active_toast: Optional[ToastNotification] = None
        self._active_modal: Optional[BedtimeModal] = None
        self._save_feedback_timer_id: Optional[str] = None
        self.timeline_step_labels: Dict[str, tk.Label] = {}

        # Scheduler
        self.scheduler = SleepScheduler(
            config=self.config_mgr.config,
            on_tick=self._on_scheduler_tick,
            on_wind_down=self._on_wind_down_triggered,
            on_bedtime=self._on_bedtime_triggered,
        )

        self._build_ui()
        self.scheduler.start()

        # Initial refresh of the digital time studio
        b_h, b_m = parse_time_str(self.config_mgr.config.bedtime)
        self._update_time_display(b_h, b_m)

        # System Tray icon for background operation
        self.tray: Optional[WindowsTrayIcon] = None
        try:
            self.tray = WindowsTrayIcon(
                tooltip="🌙 Sleep Reminder",
                on_open=self._restore_from_tray,
                on_test=lambda: self._on_bedtime_triggered(0, 0, 30),
                on_pause=self._toggle_pause_for_today,
                on_exit=self.exit_application,
            )
            self.tray.start()
        except Exception:
            self.tray = None

        # Window closing handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        # Full-page scroll container: eliminates all sticky regions so the entire dashboard scrolls cohesively
        self.main_scroll = ScrollableFrame(self, bg=theme.BG_DARK)
        self.main_scroll.pack(fill=tk.BOTH, expand=True)

        content = self.main_scroll.content

        # 1. Modern Web Navbar Header
        self._build_header(content)

        # 2. Modern Segmented Tab Bar (Section 2: tab bar directly above content)
        self._build_nav_bar(content)

        # 3. Modern Hero Countdown Card (Section 1)
        self._build_hero_card(content)

        # 4. Content Container with Notebook (desktop tab headers hidden; controlled exclusively by modern pill bar)
        self.notebook = ttk.Notebook(content, style="NoTabs.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=22, pady=(2, 10))

        self.tab_schedule = ScrollableTab(self.notebook, bg=theme.BG_CARD)
        self.tab_calculator = ScrollableTab(self.notebook, bg=theme.BG_CARD)
        self.tab_history = ScrollableTab(self.notebook, bg=theme.BG_CARD)

        self.notebook.add(self.tab_schedule, text="Schedule & Escalation")
        self.notebook.add(self.tab_calculator, text="Sleep Cycles (REM)")
        self.notebook.add(self.tab_history, text="Habit Streak & Stats")

        self._build_schedule_tab()
        self._build_calculator_tab()
        self._build_history_tab()

        # 5. Modern Footer Bar
        self._build_footer(content)

    # -------------------------------------------------------------------------
    # UI Component Builders
    # -------------------------------------------------------------------------

    def _build_header(self, parent: Optional[tk.Widget] = None) -> None:
        p = parent if parent is not None else self
        header = tk.Frame(p, bg=theme.BG_DARK, padx=24, pady=12)
        header.pack(fill=tk.X)

        # Brand Logo & Tag
        brand_box = tk.Frame(header, bg=theme.BG_DARK)
        brand_box.pack(side=tk.LEFT)

        logo_lbl = tk.Label(
            brand_box,
            text="🌙",
            font=(theme.FONT_FAMILY, 22),
            bg=theme.BG_DARK,
            fg=theme.ACCENT_MOON,
        )
        logo_lbl.pack(side=tk.LEFT, padx=(0, 10))

        brand_text_box = tk.Frame(brand_box, bg=theme.BG_DARK)
        brand_text_box.pack(side=tk.LEFT)

        title_row = tk.Frame(brand_text_box, bg=theme.BG_DARK)
        title_row.pack(anchor="w")

        app_title = tk.Label(
            title_row,
            text="SLEEP REMINDER",
            font=(theme.FONT_FAMILY, 15, "bold"),
            bg=theme.BG_DARK,
            fg=theme.TEXT_MAIN,
        )
        app_title.pack(side=tk.LEFT, padx=(0, 8))

        version_badge = tk.Label(
            title_row,
            text="PRO v2.0",
            font=(theme.FONT_FAMILY, 8, "bold"),
            bg=theme.BADGE_BG,
            fg=theme.BADGE_FG,
            padx=6,
            pady=1,
        )
        version_badge.pack(side=tk.LEFT)

        self.status_badge = tk.Label(
            brand_text_box,
            text="● Active Monitoring",
            font=theme.FONT_CAPTION,
            bg=theme.BG_DARK,
            fg=theme.ACCENT_SUCCESS,
        )
        self.status_badge.pack(anchor="w")

        # Right Controls: Real-time Clock Chip, Sound Pill, and Theme Mode Switcher
        controls_box = tk.Frame(header, bg=theme.BG_DARK)
        controls_box.pack(side=tk.RIGHT)

        clock_chip = tk.Frame(controls_box, bg=theme.BG_SUBTLE, padx=12, pady=5, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        clock_chip.pack(side=tk.RIGHT, padx=(10, 0))

        self.clock_lbl = tk.Label(
            clock_chip,
            text="--:--:--",
            font=(theme.FONT_FAMILY, 12, "bold"),
            bg=theme.BG_SUBTLE,
            fg=theme.ACCENT_CYAN,
        )
        self.clock_lbl.pack()

        self.sound_toggle_btn = tk.Button(
            controls_box,
            text="🔔 Sound On" if self.config_mgr.config.enable_sound else "🔕 Muted",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._toggle_sound,
        )
        self.sound_toggle_btn.pack(side=tk.RIGHT, padx=(8, 0))

        current_theme_mode = getattr(self.config_mgr.config, "theme_mode", "system")
        mode_icon = "💻" if current_theme_mode == "system" else ("☀️" if current_theme_mode == "light" else "🌙")
        self.theme_btn = tk.Button(
            controls_box,
            text=f"{mode_icon} {current_theme_mode.capitalize()}",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=5,
            cursor="hand2",
            command=self._cycle_theme,
        )
        self.theme_btn.pack(side=tk.RIGHT)

    def _build_nav_bar(self, parent: Optional[tk.Widget] = None) -> None:
        p = parent if parent is not None else self
        nav_container = tk.Frame(p, bg=theme.BG_DARK, padx=22, pady=4)
        nav_container.pack(fill=tk.X, pady=(2, 4))

        tabs = [
            ("tab_schedule", "⏰  Schedule & Escalation"),
            ("tab_calculator", "🌙  Sleep Cycles (REM)"),
            ("tab_history", "📊  Habit & Streak Stats"),
        ]
        self.segmented_nav = SegmentedNavBar(
            nav_container,
            tabs=tabs,
            on_tab_change=self._on_tab_switched,
            initial_tab="tab_schedule",
        )
        self.segmented_nav.pack(fill=tk.X)

    def _on_tab_switched(self, tab_id: str) -> None:
        if tab_id == "tab_schedule":
            self.notebook.select(self.tab_schedule)
        elif tab_id == "tab_calculator":
            self.notebook.select(self.tab_calculator)
        elif tab_id == "tab_history":
            self.notebook.select(self.tab_history)
        self.main_scroll.scroll_to_top()

    def _build_hero_card(self, parent: Optional[tk.Widget] = None) -> None:
        p = parent if parent is not None else self
        hero_container = tk.Frame(p, bg=theme.BG_DARK, padx=22, pady=6)
        hero_container.pack(fill=tk.X)

        card = tk.Frame(
            hero_container,
            bg=theme.BG_HERO,
            padx=20,
            pady=14,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=theme.BORDER_HERO,
        )
        card.pack(fill=tk.X)

        top_row = tk.Frame(card, bg=theme.BG_HERO)
        top_row.pack(fill=tk.X, pady=(0, 4))

        self.hero_event_lbl = tk.Label(
            top_row,
            text="COUNTDOWN TO BEDTIME",
            font=(theme.FONT_FAMILY, 9, "bold"),
            bg=theme.BG_HERO,
            fg=theme.ACCENT_CYAN,
        )
        self.hero_event_lbl.pack(side=tk.LEFT)

        self.hero_tag_pill = tk.Label(
            top_row,
            text="LIVE TRACKER",
            font=(theme.FONT_FAMILY, 8, "bold"),
            bg=theme.BG_CARD_HOVER,
            fg=theme.ACCENT_SUCCESS,
            padx=8,
            pady=2,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=theme.BORDER_COLOR,
        )
        self.hero_tag_pill.pack(side=tk.RIGHT)

        countdown_row = tk.Frame(card, bg=theme.BG_HERO)
        countdown_row.pack(fill=tk.X, pady=(2, 6))

        # Segmented Digital Countdown Chips
        self.chip_hrs_frame = tk.Frame(countdown_row, bg=theme.CHIP_BG, padx=12, pady=5, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.CHIP_BORDER)
        self.chip_hrs_frame.pack(side=tk.LEFT)
        self.chip_hrs_val = tk.Label(self.chip_hrs_frame, text="00", font=(theme.FONT_FAMILY, 22, "bold"), bg=theme.CHIP_BG, fg=theme.TEXT_MAIN)
        self.chip_hrs_val.pack()
        tk.Label(self.chip_hrs_frame, text="HOURS", font=(theme.FONT_FAMILY, 7, "bold"), bg=theme.CHIP_BG, fg=theme.TEXT_MUTED).pack()

        tk.Label(countdown_row, text=":", font=(theme.FONT_FAMILY, 18, "bold"), bg=theme.BG_HERO, fg=theme.TEXT_DIM).pack(side=tk.LEFT, padx=5)

        self.chip_mins_frame = tk.Frame(countdown_row, bg=theme.CHIP_BG, padx=12, pady=5, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.CHIP_BORDER)
        self.chip_mins_frame.pack(side=tk.LEFT)
        self.chip_mins_val = tk.Label(self.chip_mins_frame, text="00", font=(theme.FONT_FAMILY, 22, "bold"), bg=theme.CHIP_BG, fg=theme.TEXT_MAIN)
        self.chip_mins_val.pack()
        tk.Label(self.chip_mins_frame, text="MINUTES", font=(theme.FONT_FAMILY, 7, "bold"), bg=theme.CHIP_BG, fg=theme.TEXT_MUTED).pack()

        tk.Label(countdown_row, text=":", font=(theme.FONT_FAMILY, 18, "bold"), bg=theme.BG_HERO, fg=theme.TEXT_DIM).pack(side=tk.LEFT, padx=5)

        self.chip_secs_frame = tk.Frame(countdown_row, bg=theme.CHIP_BG, padx=12, pady=5, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.CHIP_BORDER)
        self.chip_secs_frame.pack(side=tk.LEFT)
        self.chip_secs_val = tk.Label(self.chip_secs_frame, text="00", font=(theme.FONT_FAMILY, 22, "bold"), bg=theme.CHIP_BG, fg=theme.ACCENT_CYAN)
        self.chip_secs_val.pack()
        tk.Label(self.chip_secs_frame, text="SECONDS", font=(theme.FONT_FAMILY, 7, "bold"), bg=theme.CHIP_BG, fg=theme.TEXT_MUTED).pack()

        # Legacy label kept for test assertions
        self.countdown_lbl = tk.Label(countdown_row, text="", bg=theme.BG_HERO)

        # Right quick actions inside hero
        hero_actions = tk.Frame(countdown_row, bg=theme.BG_HERO)
        hero_actions.pack(side=tk.RIGHT, pady=2)

        sleep_now_btn = tk.Button(
            hero_actions,
            text="🌙  Sleep Now",
            font=theme.FONT_BODY_BOLD,
            bg=theme.ACCENT_PRIMARY,
            fg="#ffffff",
            activebackground=theme.ACCENT_PRIMARY_HOVER,
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=self._handle_sleep_confirmed,
        )
        sleep_now_btn.pack(side=tk.TOP, fill=tk.X, pady=(0, 4))

        test_alert_hero = tk.Button(
            hero_actions,
            text="🔔  Test Bedtime Alert",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=lambda: self._on_bedtime_triggered(0, 0, 30),
        )
        test_alert_hero.pack(side=tk.TOP, fill=tk.X)

        detail_row = tk.Frame(card, bg=theme.BG_HERO)
        detail_row.pack(fill=tk.X, pady=(4, 0))

        self.hero_detail_lbl = tk.Label(
            detail_row,
            text=f"Target Bedtime: {self.config_mgr.config.bedtime}  •  Escalation: +30m, +15m, +10m, then every 5m",
            font=theme.FONT_CAPTION,
            bg=theme.BG_HERO,
            fg=theme.TEXT_MUTED,
        )
        self.hero_detail_lbl.pack(side=tk.LEFT)

    def _build_schedule_tab(self) -> None:
        container = tk.Frame(self.tab_schedule.content, bg=theme.BG_CARD, padx=18, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        cfg = self.config_mgr.config
        b_hour, b_min = parse_time_str(cfg.bedtime)
        w_hour, w_min = parse_time_str(cfg.wake_time)

        # =====================================================================
        # SECTION 1: HERO REMINDER TIME STUDIO
        # =====================================================================
        studio_card = tk.Frame(
            container,
            bg=theme.BG_CARD,
            padx=16,
            pady=12,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=theme.BORDER_COLOR,
        )
        studio_card.pack(fill=tk.X, pady=(0, 10))

        # Header of Studio
        studio_header = tk.Frame(studio_card, bg=theme.BG_CARD)
        studio_header.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            studio_header,
            text="⏰  BEDTIME REMINDER SETUP STUDIO",
            font=(theme.FONT_FAMILY, 11, "bold"),
            bg=theme.BG_CARD,
            fg=theme.ACCENT_MOON,
        ).pack(side=tk.LEFT)

        tk.Label(
            studio_header,
            text="Configure your target sleep time and see real-time escalation",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
        ).pack(side=tk.LEFT, padx=(10, 0))

        # Center Hero Digital Clock Picker Card
        picker_container = tk.Frame(studio_card, bg=theme.BG_CARD)
        picker_container.pack(fill=tk.X, pady=(0, 8))

        clock_center_box = tk.Frame(
            picker_container,
            bg=theme.BG_SUBTLE,
            padx=20,
            pady=10,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=theme.BORDER_COLOR,
        )
        clock_center_box.pack(side=tk.LEFT, padx=(0, 16))

        # Hours Column
        hrs_col = tk.Frame(clock_center_box, bg=theme.BG_SUBTLE)
        hrs_col.pack(side=tk.LEFT)

        btn_h_up = tk.Button(
            hrs_col, text="▲", font=(theme.FONT_FAMILY, 9, "bold"), bg=theme.BG_CARD_HOVER, fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE, relief="flat", bd=0, padx=14, pady=2, cursor="hand2",
            command=lambda: self._increment_bed_hour(1),
        )
        btn_h_up.pack()

        self.big_hour_lbl = tk.Label(
            hrs_col,
            text=f"{b_hour:02d}",
            font=(theme.FONT_FAMILY, 32, "bold"),
            bg=theme.BG_SUBTLE,
            fg=theme.TEXT_MAIN,
        )
        self.big_hour_lbl.pack(pady=1)

        btn_h_down = tk.Button(
            hrs_col, text="▼", font=(theme.FONT_FAMILY, 9, "bold"), bg=theme.BG_CARD_HOVER, fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE, relief="flat", bd=0, padx=14, pady=2, cursor="hand2",
            command=lambda: self._increment_bed_hour(-1),
        )
        btn_h_down.pack()

        tk.Label(hrs_col, text="HOUR", font=(theme.FONT_FAMILY, 7, "bold"), bg=theme.BG_SUBTLE, fg=theme.TEXT_MUTED).pack(pady=(2, 0))

        # Colon separator
        tk.Label(clock_center_box, text=":", font=(theme.FONT_FAMILY, 28, "bold"), bg=theme.BG_SUBTLE, fg=theme.ACCENT_CYAN).pack(side=tk.LEFT, padx=10)

        # Minutes Column
        mins_col = tk.Frame(clock_center_box, bg=theme.BG_SUBTLE)
        mins_col.pack(side=tk.LEFT)

        btn_m_up = tk.Button(
            mins_col, text="▲", font=(theme.FONT_FAMILY, 9, "bold"), bg=theme.BG_CARD_HOVER, fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE, relief="flat", bd=0, padx=14, pady=2, cursor="hand2",
            command=lambda: self._increment_bed_min(5),
        )
        btn_m_up.pack()

        self.big_min_lbl = tk.Label(
            mins_col,
            text=f"{b_min:02d}",
            font=(theme.FONT_FAMILY, 32, "bold"),
            bg=theme.BG_SUBTLE,
            fg=theme.TEXT_MAIN,
        )
        self.big_min_lbl.pack(pady=1)

        btn_m_down = tk.Button(
            mins_col, text="▼", font=(theme.FONT_FAMILY, 9, "bold"), bg=theme.BG_CARD_HOVER, fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE, relief="flat", bd=0, padx=14, pady=2, cursor="hand2",
            command=lambda: self._increment_bed_min(-5),
        )
        btn_m_down.pack()

        tk.Label(mins_col, text="MINUTE", font=(theme.FONT_FAMILY, 7, "bold"), bg=theme.BG_SUBTLE, fg=theme.TEXT_MUTED).pack(pady=(2, 0))

        # AM / PM Toggle Pills
        ampm_col = tk.Frame(clock_center_box, bg=theme.BG_SUBTLE)
        ampm_col.pack(side=tk.LEFT, padx=(14, 0))

        is_pm = (b_hour >= 12)
        self.ampm_am_btn = tk.Button(
            ampm_col,
            text="AM",
            font=(theme.FONT_FAMILY, 9, "bold"),
            bg=theme.BG_CARD_HOVER if is_pm else theme.ACCENT_PRIMARY,
            fg=theme.TEXT_MUTED if is_pm else "#ffffff",
            activebackground=theme.ACCENT_PRIMARY_HOVER,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: self._set_bed_ampm("AM"),
        )
        self.ampm_am_btn.pack(pady=2)

        self.ampm_pm_btn = tk.Button(
            ampm_col,
            text="PM",
            font=(theme.FONT_FAMILY, 9, "bold"),
            bg=theme.ACCENT_PRIMARY if is_pm else theme.BG_CARD_HOVER,
            fg="#ffffff" if is_pm else theme.TEXT_MUTED,
            activebackground=theme.ACCENT_PRIMARY_HOVER,
            relief="flat",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=lambda: self._set_bed_ampm("PM"),
        )
        self.ampm_pm_btn.pack(pady=2)

        # Quick Adjustments & Wake Time container (Right of Clock)
        studio_right_col = tk.Frame(picker_container, bg=theme.BG_CARD)
        studio_right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Quick Increments Row
        inc_row = tk.Frame(studio_right_col, bg=theme.BG_CARD)
        inc_row.pack(anchor="w", pady=(2, 6))

        tk.Label(inc_row, text="Quick Adjust:", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 6))
        for delta_mins in [-30, -15, 15, 30]:
            lbl = f"+{delta_mins}m" if delta_mins > 0 else f"{delta_mins}m"
            b = tk.Button(
                inc_row, text=lbl, font=theme.FONT_CAPTION, bg=theme.BG_CARD_HOVER, fg=theme.TEXT_MAIN,
                activebackground=theme.ACCENT_PRIMARY, activeforeground="#ffffff", relief="flat", bd=0, padx=8, pady=2,
                cursor="hand2", command=lambda d=delta_mins: self._adjust_bed_minutes(d),
            )
            b.pack(side=tk.LEFT, padx=2)

        # Target Wake Time row
        wake_row = tk.Frame(studio_right_col, bg=theme.BG_CARD)
        wake_row.pack(anchor="w", pady=(4, 6))

        tk.Label(wake_row, text="Morning Wake Time:", font=theme.FONT_BODY, bg=theme.BG_CARD, fg=theme.TEXT_MAIN).pack(side=tk.LEFT, padx=(0, 6))

        self.wake_hour_spin = ttk.Spinbox(wake_row, from_=0, to=23, width=3, format="%02.0f", wrap=True, command=self._on_wake_changed)
        self.wake_hour_spin.set(f"{w_hour:02d}")
        self.wake_hour_spin.pack(side=tk.LEFT, padx=(0, 2))

        tk.Label(wake_row, text=":", bg=theme.BG_CARD, fg=theme.TEXT_MAIN).pack(side=tk.LEFT)

        self.wake_min_spin = ttk.Spinbox(wake_row, from_=0, to=59, width=3, format="%02.0f", wrap=True, command=self._on_wake_changed)
        self.wake_min_spin.set(f"{w_min:02d}")
        self.wake_min_spin.pack(side=tk.LEFT, padx=(2, 8))

        self.wake_12h_preview = tk.Label(
            wake_row,
            text=f"({datetime(2026, 1, 1, w_hour, w_min).strftime('%I:%M %p').lstrip('0')})",
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
            font=theme.FONT_CAPTION,
        )
        self.wake_12h_preview.pack(side=tk.LEFT)

        # Sleep Duration Visualizer Badge
        self.sleep_duration_badge = tk.Label(
            studio_right_col,
            text="",
            font=(theme.FONT_FAMILY, 9, "bold"),
            bg=theme.BG_SUBTLE,
            fg=theme.ACCENT_CYAN,
            padx=10,
            pady=4,
            bd=1,
            relief="solid",
            highlightthickness=1,
            highlightbackground=theme.BORDER_COLOR,
        )
        self.sleep_duration_badge.pack(anchor="w")

        # Hidden / legacy inputs for compatibility with automated tests
        legacy_frame = tk.Frame(studio_card, bg=theme.BG_CARD)
        self.bed_hour_spin = ttk.Spinbox(legacy_frame, from_=0, to=23, width=3, format="%02.0f")
        self.bed_hour_spin.set(f"{b_hour:02d}")
        self.bed_min_spin = ttk.Spinbox(legacy_frame, from_=0, to=59, width=3, format="%02.0f")
        self.bed_min_spin.set(f"{b_min:02d}")
        self.bed_12h_preview = tk.Label(legacy_frame, text="")

        # Preset Chips Grid Row
        presets_box = tk.Frame(studio_card, bg=theme.BG_CARD)
        presets_box.pack(fill=tk.X, pady=(6, 0))

        tk.Label(presets_box, text="Bedtime Presets:", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 8))

        for preset_time, preset_display in self.PRESET_BEDTIMES:
            chip_btn = tk.Button(
                presets_box,
                text=f"{preset_display}",
                font=theme.FONT_CAPTION,
                bg=theme.BG_CARD_HOVER,
                fg=theme.TEXT_MAIN,
                activebackground=theme.ACCENT_PRIMARY,
                activeforeground="#ffffff",
                relief="flat",
                bd=0,
                padx=8,
                pady=3,
                cursor="hand2",
                command=lambda p=preset_time: self._apply_preset_bedtime(p),
            )
            chip_btn.pack(side=tk.LEFT, padx=3)

        # =====================================================================
        # SECTION 2: DYNAMIC ESCALATING TIMELINE LADDER
        # =====================================================================
        section2 = tk.Frame(container, bg=theme.BG_CARD, padx=14, pady=10, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        section2.pack(fill=tk.X, pady=(0, 10))

        sec2_header = tk.Frame(section2, bg=theme.BG_CARD)
        sec2_header.pack(fill=tk.X, pady=(0, 6))
        tk.Label(sec2_header, text="⚡  ESCALATING REMINDER TIMELINE", font=(theme.FONT_FAMILY, 10, "bold"), bg=theme.BG_CARD, fg=theme.ACCENT_CYAN).pack(side=tk.LEFT)
        tk.Label(sec2_header, text="Calculated exact alert schedule for tonight", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.TEXT_MUTED).pack(side=tk.LEFT, padx=(10, 0))

        # Dynamic Timeline Step Cards
        timeline_bar = tk.Frame(section2, bg=theme.BG_SUBTLE, padx=8, pady=8, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        timeline_bar.pack(fill=tk.X, pady=(0, 10))

        ladder_steps = [
            ("stage0", "🌙 Bedtime Alert", theme.ACCENT_MOON),
            ("arrow1", "──►", theme.TEXT_DIM),
            ("stage1", "⚠️ 1st Warning (+30m)", theme.ACCENT_WARNING),
            ("arrow2", "──►", theme.TEXT_DIM),
            ("stage2", "⏰ 2nd Warning (+15m)", theme.ACCENT_ORANGE),
            ("arrow3", "──►", theme.TEXT_DIM),
            ("stage3", "🚨 3rd Warning (+10m)", theme.ACCENT_DANGER),
            ("arrow4", "──►", theme.TEXT_DIM),
            ("stage4", "🛑 Repeating Every 5m", theme.ACCENT_DANGER),
        ]

        for step_id, step_name, col in ladder_steps:
            box = tk.Frame(timeline_bar, bg=theme.BG_SUBTLE)
            box.pack(side=tk.LEFT, padx=3)

            tk.Label(box, text=step_name, font=theme.FONT_SMALL, bg=theme.BG_SUBTLE, fg=col).pack()

            if "stage" in step_id:
                time_lbl = tk.Label(box, text="--:--", font=(theme.FONT_FAMILY, 8, "bold"), bg=theme.BG_SUBTLE, fg=theme.TEXT_MAIN)
                time_lbl.pack()
                self.timeline_step_labels[step_id] = time_lbl

        # =====================================================================
        # SECTION 3: MODERN SETTING SWITCH CARDS
        # =====================================================================
        # Appearance Theme Selection SettingRow
        row_theme = SettingRow(
            section2,
            icon="🎨",
            title="Appearance Theme",
            description="Choose between Light theme, Dark theme, or automatically match Windows System theme.",
        )
        theme_btn_box = tk.Frame(row_theme.right_box, bg=theme.BG_CARD)
        theme_btn_box.pack(side=tk.RIGHT)

        current_theme_mode = getattr(self.config_mgr.config, "theme_mode", "system")
        for mode_key, mode_icon, mode_title in [
            ("light", "☀️", "Light"),
            ("dark", "🌙", "Dark"),
            ("system", "💻", "System"),
        ]:
            is_active = (current_theme_mode == mode_key)
            t_btn = tk.Button(
                theme_btn_box,
                text=f"{mode_icon} {mode_title}",
                font=theme.FONT_BODY_BOLD if is_active else theme.FONT_CAPTION,
                bg=theme.ACCENT_PRIMARY if is_active else theme.BG_CARD_HOVER,
                fg="#ffffff" if is_active else theme.TEXT_MUTED,
                activebackground=theme.ACCENT_PRIMARY_HOVER if is_active else theme.BG_CARD_ACTIVE,
                activeforeground="#ffffff" if is_active else theme.TEXT_MAIN,
                relief="flat",
                bd=0,
                padx=10,
                pady=4,
                cursor="hand2",
                command=lambda m=mode_key: self.set_theme(m),
            )
            t_btn.pack(side=tk.LEFT, padx=3)

        self.enable_escalating_check = tk.BooleanVar(value=cfg.enable_escalating_reminders)
        row_esc = SettingRow(
            section2,
            icon="⚡",
            title="Enable Escalating Interval Reminders",
            description="Remind at bedtime, +30m, +15m, +10m, then repeatedly every 5m until device shutdown.",
        )
        row_esc.add_switch(variable=self.enable_escalating_check)

        self.pause_media_check = tk.BooleanVar(value=cfg.pause_media_on_reminder)
        row_media = SettingRow(
            section2,
            icon="⏸️",
            title="Auto-Pause Video & Audio on Reminders",
            description="Automatically pause YouTube, Spotify, VLC, and browser audio when reminder triggers.",
        )
        row_media.add_switch(variable=self.pause_media_check)

        self.fullscreen_check = tk.BooleanVar(value=cfg.fullscreen_reminder)
        row_fs = SettingRow(
            section2,
            icon="🖥️",
            title="Full-Screen Ambient Reminder Overlay",
            description="Display reminders in a full-screen ambient starry display with real-time digital clock and controls.",
        )
        row_fs.add_switch(variable=self.fullscreen_check)

        self.autostart_check = tk.BooleanVar(value=is_autostart_enabled() or cfg.autostart)
        row_auto = SettingRow(
            section2,
            icon="🚀",
            title="Start with Windows on Boot",
            description="Silently launch in background system tray when computer turns on.",
        )
        row_auto.add_switch(variable=self.autostart_check)

        # Shutdown Grace Row
        row_sd = SettingRow(
            section2,
            icon="🛡️",
            title="Shutdown Grace Countdown Period",
            description="Safety cancellation window with 'Cancel Shutdown' button before Windows powers down.",
        )
        sd_control = tk.Frame(row_sd.right_box, bg=theme.BG_CARD)
        sd_control.pack(side=tk.RIGHT)
        self.shutdown_seconds_spin = ttk.Spinbox(sd_control, from_=10, to=120, width=4)
        self.shutdown_seconds_spin.set(str(cfg.shutdown_countdown_seconds))
        self.shutdown_seconds_spin.pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(sd_control, text="sec", font=theme.FONT_CAPTION, bg=theme.BG_CARD, fg=theme.TEXT_MUTED).pack(side=tk.LEFT)

        # Legacy variables
        self.enable_winddown_check = tk.BooleanVar(value=cfg.enable_wind_down)
        self.enable_bedtime_check = tk.BooleanVar(value=cfg.enable_bedtime_alert)
        self.winddown_var = tk.StringVar(value=f"{cfg.wind_down_minutes} minutes before")
        self.snooze_var = tk.StringVar(value=f"{cfg.snooze_duration_minutes} minutes")

        # =====================================================================
        # SAVE & ACTION ROW
        # =====================================================================
        action_row = tk.Frame(container, bg=theme.BG_CARD)
        action_row.pack(fill=tk.X, pady=(6, 0))

        save_btn = tk.Button(
            action_row,
            text="✓   Save Bedtime & Activate Schedule",
            font=theme.FONT_BODY_BOLD,
            bg=theme.ACCENT_PRIMARY,
            fg="#ffffff",
            activebackground=theme.ACCENT_PRIMARY_HOVER,
            activeforeground="#ffffff",
            relief="flat",
            padx=22,
            pady=9,
            cursor="hand2",
            command=self._save_schedule_settings,
        )
        save_btn.pack(side=tk.LEFT)

        preview_btn = tk.Button(
            action_row,
            text="🔔  Preview Reminder Now",
            font=theme.FONT_BODY,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=9,
            cursor="hand2",
            command=lambda: self._on_bedtime_triggered(0, 0, 30),
        )
        preview_btn.pack(side=tk.LEFT, padx=(10, 0))

        self.save_feedback_lbl = tk.Label(
            action_row,
            text="",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.ACCENT_SUCCESS,
        )
        self.save_feedback_lbl.pack(side=tk.LEFT, padx=(14, 0))

    # -------------------------------------------------------------------------
    # Time Studio Synchronizers
    # -------------------------------------------------------------------------

    def _increment_bed_hour(self, delta: int) -> None:
        try:
            cur_h = int(self.bed_hour_spin.get())
        except Exception:
            cur_h = 22
        new_h = (cur_h + delta) % 24
        self.bed_hour_spin.set(f"{new_h:02d}")
        self._update_time_display(new_h, None)
        self._save_schedule_settings()

    def _increment_bed_min(self, delta: int) -> None:
        try:
            cur_m = int(self.bed_min_spin.get())
        except Exception:
            cur_m = 0
        new_m = (cur_m + delta) % 60
        self.bed_min_spin.set(f"{new_m:02d}")
        self._update_time_display(None, new_m)
        self._save_schedule_settings()

    def _adjust_bed_minutes(self, delta_mins: int) -> None:
        try:
            cur_h = int(self.bed_hour_spin.get())
            cur_m = int(self.bed_min_spin.get())
        except Exception:
            cur_h, cur_m = 22, 0
        total = (cur_h * 60 + cur_m + delta_mins) % (24 * 60)
        new_h = total // 60
        new_m = total % 60
        self.bed_hour_spin.set(f"{new_h:02d}")
        self.bed_min_spin.set(f"{new_m:02d}")
        self._update_time_display(new_h, new_m)
        self._save_schedule_settings()

    def _set_bed_ampm(self, target_ampm: str) -> None:
        try:
            cur_h = int(self.bed_hour_spin.get())
        except Exception:
            cur_h = 22
        is_pm = cur_h >= 12
        if target_ampm == "PM" and not is_pm:
            new_h = (cur_h + 12) % 24
            self.bed_hour_spin.set(f"{new_h:02d}")
            self._update_time_display(new_h, None)
            self._save_schedule_settings()
        elif target_ampm == "AM" and is_pm:
            new_h = (cur_h - 12) % 24
            self.bed_hour_spin.set(f"{new_h:02d}")
            self._update_time_display(new_h, None)
            self._save_schedule_settings()

    def _apply_preset_bedtime(self, preset_str: str) -> None:
        h, m = parse_time_str(preset_str)
        self.bed_hour_spin.set(f"{h:02d}")
        self.bed_min_spin.set(f"{m:02d}")
        self._update_time_display(h, m)
        self._save_schedule_settings()

    def _on_wake_changed(self) -> None:
        try:
            w_h = int(self.wake_hour_spin.get())
            w_m = int(self.wake_min_spin.get())
            self.wake_12h_preview.config(text=f"({datetime(2026, 1, 1, w_h, w_m).strftime('%I:%M %p').lstrip('0')})")
            self._update_time_display()
        except Exception:
            pass

    def _update_time_display(self, b_h: Optional[int] = None, b_m: Optional[int] = None) -> None:
        try:
            if b_h is None:
                b_h = int(self.bed_hour_spin.get())
            if b_m is None:
                b_m = int(self.bed_min_spin.get())
        except Exception:
            return

        # Update big numerals
        if hasattr(self, "big_hour_lbl") and self.big_hour_lbl.winfo_exists():
            self.big_hour_lbl.config(text=f"{b_h:02d}")
        if hasattr(self, "big_min_lbl") and self.big_min_lbl.winfo_exists():
            self.big_min_lbl.config(text=f"{b_m:02d}")

        # Update AM/PM indicator pills
        is_pm = (b_h >= 12)
        if hasattr(self, "ampm_am_btn") and self.ampm_am_btn.winfo_exists():
            self.ampm_am_btn.config(
                bg=theme.BG_CARD_HOVER if is_pm else theme.ACCENT_PRIMARY,
                fg=theme.TEXT_MUTED if is_pm else "#ffffff",
            )
            self.ampm_pm_btn.config(
                bg=theme.ACCENT_PRIMARY if is_pm else theme.BG_CARD_HOVER,
                fg="#ffffff" if is_pm else theme.TEXT_MUTED,
            )

        # 12h preview
        dt_base = datetime(2026, 1, 1, b_h, b_m)
        time_12h = dt_base.strftime("%I:%M %p").lstrip("0")
        if hasattr(self, "bed_12h_preview") and self.bed_12h_preview.winfo_exists():
            self.bed_12h_preview.config(text=f"({time_12h})")

        # Update Rest Duration calculation
        try:
            w_h = int(self.wake_hour_spin.get())
            w_m = int(self.wake_min_spin.get())
            b_total = b_h * 60 + b_m
            w_total = w_h * 60 + w_m
            diff = (24 * 60 - b_total + w_total) if w_total <= b_total else (w_total - b_total)
            hours = diff / 60.0
            cycles = diff / 90.0
            if hasattr(self, "sleep_duration_badge") and self.sleep_duration_badge.winfo_exists():
                self.sleep_duration_badge.config(
                    text=f"🌙 {time_12h} Bedtime ── {hours:.1f}h Rest ({cycles:.1f} Cycles) ──► ☀️ {datetime(2026, 1, 1, w_h, w_m).strftime('%I:%M %p').lstrip('0')} Wake"
                )
        except Exception:
            pass

        # Update timeline ladder timestamps dynamically
        if hasattr(self, "timeline_step_labels") and self.timeline_step_labels:
            t0 = time_12h
            t1 = (dt_base + timedelta(minutes=30)).strftime("%I:%M %p").lstrip("0")
            t2 = (dt_base + timedelta(minutes=45)).strftime("%I:%M %p").lstrip("0")
            t3 = (dt_base + timedelta(minutes=55)).strftime("%I:%M %p").lstrip("0")
            t4 = (dt_base + timedelta(minutes=60)).strftime("%I:%M %p").lstrip("0")

            times = [t0, t1, t2, t3, t4]
            for key, t_str in zip(["stage0", "stage1", "stage2", "stage3", "stage4"], times):
                if key in self.timeline_step_labels and self.timeline_step_labels[key].winfo_exists():
                    self.timeline_step_labels[key].config(text=t_str)

    def _build_calculator_tab(self) -> None:
        container = tk.Frame(self.tab_calculator.content, bg=theme.BG_CARD, padx=20, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        intro = tk.Label(
            container,
            text="Smart Sleep Cycles (90-Minute REM Cycles)",
            font=theme.FONT_SUBTITLE,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MAIN,
        )
        intro.pack(anchor="w", pady=(0, 4))

        explanation = tk.Label(
            container,
            text="A normal human sleep cycle lasts 90 minutes. Waking up between cycles helps you feel alert and energised. Waking mid-cycle causes sleep inertia and grogginess.",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
            wraplength=680,
            justify=tk.LEFT,
        )
        explanation.pack(anchor="w", pady=(0, 14))

        calc_header = tk.Frame(container, bg=theme.BG_CARD)
        calc_header.pack(fill=tk.X, pady=(0, 10))

        tk.Label(
            calc_header,
            text="Wake-Up Time:",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MAIN,
        ).pack(side=tk.LEFT, padx=(0, 8))

        self.calc_wake_hour = ttk.Spinbox(calc_header, from_=0, to=23, width=3, format="%02.0f", wrap=True)
        self.calc_wake_hour.set(self.config_mgr.config.wake_time.split(":")[0])
        self.calc_wake_hour.pack(side=tk.LEFT, padx=2)

        tk.Label(calc_header, text=":", bg=theme.BG_CARD, fg=theme.TEXT_MAIN).pack(side=tk.LEFT)

        self.calc_wake_min = ttk.Spinbox(calc_header, from_=0, to=59, width=3, format="%02.0f", wrap=True)
        self.calc_wake_min.set(self.config_mgr.config.wake_time.split(":")[1])
        self.calc_wake_min.pack(side=tk.LEFT, padx=2)

        calc_btn = tk.Button(
            calc_header,
            text="Calculate Optimal Bedtimes",
            font=theme.FONT_CAPTION,
            bg=theme.ACCENT_PRIMARY,
            fg="#ffffff",
            activebackground=theme.ACCENT_PRIMARY_HOVER,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._calculate_cycles,
        )
        calc_btn.pack(side=tk.LEFT, padx=(12, 10))

        sleep_now_calc_btn = tk.Button(
            calc_header,
            text="Sleep Right Now →",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_HOVER,
            fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._calculate_sleep_now,
        )
        sleep_now_calc_btn.pack(side=tk.LEFT)

        self.cycle_cards_frame = tk.Frame(container, bg=theme.BG_CARD)
        self.cycle_cards_frame.pack(fill=tk.BOTH, expand=True)

        self._calculate_cycles()

    def _calculate_cycles(self) -> None:
        for w in self.cycle_cards_frame.winfo_children():
            w.destroy()

        try:
            h = int(self.calc_wake_hour.get())
            m = int(self.calc_wake_min.get())
            wake_str = f"{h:02d}:{m:02d}"
        except Exception:
            wake_str = self.config_mgr.config.wake_time

        options = calculate_bedtimes_for_wake_time(wake_str)

        header_lbl = tk.Label(
            self.cycle_cards_frame,
            text=f"To wake up feeling refreshed at {wake_str}, go to bed at one of these times:",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.ACCENT_MOON,
        )
        header_lbl.pack(anchor="w", pady=(0, 6))

        for opt in options:
            card = tk.Frame(self.cycle_cards_frame, bg=theme.BG_SUBTLE, padx=14, pady=8, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
            card.pack(fill=tk.X, pady=4)

            left_box = tk.Frame(card, bg=theme.BG_SUBTLE)
            left_box.pack(side=tk.LEFT)

            time_lbl = tk.Label(
                left_box,
                text=opt["bedtime"],
                font=(theme.FONT_FAMILY, 15, "bold"),
                bg=theme.BG_SUBTLE,
                fg=opt["color"],
            )
            time_lbl.pack(side=tk.LEFT, padx=(0, 8))

            display_12h = tk.Label(
                left_box,
                text=f"({opt['display_12h']})",
                font=theme.FONT_CAPTION,
                bg=theme.BG_SUBTLE,
                fg=theme.TEXT_MUTED,
            )
            display_12h.pack(side=tk.LEFT, padx=(0, 12))

            tag_lbl = tk.Label(
                left_box,
                text=f"{opt['tag']} • {opt['duration_str']}",
                font=theme.FONT_CAPTION,
                bg=theme.BG_SUBTLE,
                fg=theme.TEXT_MAIN,
            )
            tag_lbl.pack(side=tk.LEFT)

            bedtime_val = opt["bedtime"]
            apply_btn = tk.Button(
                card,
                text="Set as Bedtime",
                font=theme.FONT_CAPTION,
                bg=theme.BG_CARD_HOVER,
                fg=theme.TEXT_MAIN,
                activebackground=theme.ACCENT_PRIMARY,
                activeforeground="#ffffff",
                relief="flat",
                padx=10,
                pady=2,
                cursor="hand2",
                command=lambda b=bedtime_val: self._apply_calculated_bedtime(b),
            )
            apply_btn.pack(side=tk.RIGHT)

    def _calculate_sleep_now(self) -> None:
        for w in self.cycle_cards_frame.winfo_children():
            w.destroy()

        wake_options = calculate_wake_times_if_sleep_now()

        header_lbl = tk.Label(
            self.cycle_cards_frame,
            text="If you fall asleep right now (including ~14 mins to drift off), set alarm for:",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.ACCENT_CYAN,
        )
        header_lbl.pack(anchor="w", pady=(0, 6))

        for opt in wake_options:
            card = tk.Frame(self.cycle_cards_frame, bg=theme.BG_SUBTLE, padx=14, pady=8, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
            card.pack(fill=tk.X, pady=4)

            time_lbl = tk.Label(
                card,
                text=opt["wake_time"],
                font=(theme.FONT_FAMILY, 15, "bold"),
                bg=theme.BG_SUBTLE,
                fg=opt["color"],
            )
            time_lbl.pack(side=tk.LEFT, padx=(0, 8))

            display_12h = tk.Label(
                card,
                text=f"({opt['display_12h']})",
                font=theme.FONT_CAPTION,
                bg=theme.BG_SUBTLE,
                fg=theme.TEXT_MUTED,
            )
            display_12h.pack(side=tk.LEFT, padx=(0, 12))

            tag_lbl = tk.Label(
                card,
                text=opt["tag"],
                font=theme.FONT_CAPTION,
                bg=theme.BG_SUBTLE,
                fg=theme.TEXT_MAIN,
            )
            tag_lbl.pack(side=tk.LEFT)

    def _apply_calculated_bedtime(self, bedtime_str: str) -> None:
        h, m = parse_time_str(bedtime_str)
        self.bed_hour_spin.set(f"{h:02d}")
        self.bed_min_spin.set(f"{m:02d}")
        self._update_time_display(h, m)
        self._save_schedule_settings()
        self.segmented_nav.select_tab("tab_schedule")

    def _build_history_tab(self) -> None:
        container = tk.Frame(self.tab_history.content, bg=theme.BG_CARD, padx=20, pady=16)
        container.pack(fill=tk.BOTH, expand=True)

        stats = self.history_mgr.calculate_stats()

        stats_row = tk.Frame(container, bg=theme.BG_CARD)
        stats_row.pack(fill=tk.X, pady=(0, 16))

        c1 = tk.Frame(stats_row, bg=theme.BG_SUBTLE, padx=16, pady=12, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        tk.Label(c1, text="CURRENT STREAK", font=theme.FONT_SMALL, bg=theme.BG_SUBTLE, fg=theme.ACCENT_MOON).pack(anchor="w")
        self.streak_val_lbl = tk.Label(c1, text=f"🔥 {stats['current_streak']} Days", font=theme.FONT_SUBTITLE, bg=theme.BG_SUBTLE, fg=theme.TEXT_MAIN)
        self.streak_val_lbl.pack(anchor="w", pady=(4, 0))

        c2 = tk.Frame(stats_row, bg=theme.BG_SUBTLE, padx=16, pady=12, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        tk.Label(c2, text="7-DAY ON-TIME RATE", font=theme.FONT_SMALL, bg=theme.BG_SUBTLE, fg=theme.ACCENT_CYAN).pack(anchor="w")
        self.rate_val_lbl = tk.Label(c2, text=f"{stats['recent_on_time_rate']}% Consistent", font=theme.FONT_SUBTITLE, bg=theme.BG_SUBTLE, fg=theme.TEXT_MAIN)
        self.rate_val_lbl.pack(anchor="w", pady=(4, 0))

        c3 = tk.Frame(stats_row, bg=theme.BG_SUBTLE, padx=16, pady=12, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(c3, text="TOTAL RECORDED", font=theme.FONT_SMALL, bg=theme.BG_SUBTLE, fg=theme.ACCENT_SUCCESS).pack(anchor="w")
        self.total_val_lbl = tk.Label(c3, text=f"{stats['total_logged']} Nights", font=theme.FONT_SUBTITLE, bg=theme.BG_SUBTLE, fg=theme.TEXT_MAIN)
        self.total_val_lbl.pack(anchor="w", pady=(4, 0))

        list_header = tk.Frame(container, bg=theme.BG_CARD)
        list_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(list_header, text="Recent Sleep Activity", font=theme.FONT_BODY_BOLD, bg=theme.BG_CARD, fg=theme.TEXT_MAIN).pack(side=tk.LEFT)

        log_now_btn = tk.Button(
            list_header,
            text="+ Log Tonight's Sleep",
            font=theme.FONT_CAPTION,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.ACCENT_PRIMARY,
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            command=self._handle_sleep_confirmed,
        )
        log_now_btn.pack(side=tk.RIGHT)

        self.history_list_frame = tk.Frame(container, bg=theme.BG_CARD)
        self.history_list_frame.pack(fill=tk.BOTH, expand=True)

        self._refresh_history_list()

    def _refresh_history_list(self) -> None:
        for w in self.history_list_frame.winfo_children():
            w.destroy()

        entries = self.history_mgr.get_recent_entries(limit=6)
        if not entries:
            empty_lbl = tk.Label(
                self.history_list_frame,
                text="No sleep events logged yet. Confirm bedtime to build your streak!",
                font=theme.FONT_CAPTION,
                bg=theme.BG_CARD,
                fg=theme.TEXT_MUTED,
                pady=16,
            )
            empty_lbl.pack()
            return

        for e in entries:
            dt = datetime.fromisoformat(e.timestamp)
            row = tk.Frame(self.history_list_frame, bg=theme.BG_SUBTLE, padx=12, pady=6, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
            row.pack(fill=tk.X, pady=2)

            date_str = dt.strftime("%b %d, %Y  %I:%M %p")
            tk.Label(row, text=date_str, font=theme.FONT_CAPTION, bg=theme.BG_SUBTLE, fg=theme.TEXT_MAIN).pack(side=tk.LEFT)

            action_color = theme.ACCENT_SUCCESS if "on_time" in e.action else theme.ACCENT_MOON
            action_text = "🌙 Slept On-Time" if "on_time" in e.action else ("⏳ Snoozed" if e.action == "snoozed" else "Dismissed")
            tk.Label(row, text=action_text, font=theme.FONT_CAPTION, bg=theme.BG_SUBTLE, fg=action_color).pack(side=tk.RIGHT)

    def _build_footer(self, parent: Optional[tk.Widget] = None) -> None:
        p = parent if parent is not None else self
        footer = tk.Frame(p, bg=theme.BG_DARK, padx=22, pady=8)
        footer.pack(fill=tk.X)

        self.tip_lbl = tk.Label(
            footer,
            text=f"💡 Tip: {get_random_sleep_tip()}",
            font=theme.FONT_CAPTION,
            bg=theme.BG_DARK,
            fg=theme.TEXT_MUTED,
            wraplength=440,
            justify=tk.LEFT,
        )
        self.tip_lbl.pack(side=tk.LEFT)

        test_box = tk.Frame(footer, bg=theme.BG_DARK)
        test_box.pack(side=tk.RIGHT)

        test_toast_btn = tk.Button(
            test_box,
            text="Toast",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MUTED,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._on_wind_down_triggered,
        )
        test_toast_btn.pack(side=tk.LEFT, padx=3)

        test_modal_btn = tk.Button(
            test_box,
            text="Test Bedtime",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._on_bedtime_triggered(0, 0, 30),
        )
        test_modal_btn.pack(side=tk.LEFT, padx=3)

        test_esc_btn = tk.Button(
            test_box,
            text="Test +30m",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=lambda: self._on_bedtime_triggered(1, 30, 15),
        )
        test_esc_btn.pack(side=tk.LEFT, padx=3)

        pause_media_test_btn = tk.Button(
            test_box,
            text="⏸ Pause Media",
            font=theme.FONT_SMALL,
            bg=theme.BG_CARD_HOVER,
            fg=theme.ACCENT_CYAN,
            activebackground=theme.BG_CARD_ACTIVE,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=pause_system_media,
        )
        pause_media_test_btn.pack(side=tk.LEFT, padx=3)

        quit_btn = tk.Button(
            test_box,
            text="Exit",
            font=theme.FONT_SMALL,
            bg=theme.ACCENT_DANGER,
            fg="#ffffff",
            activebackground=theme.ACCENT_DANGER_HOVER,
            relief="flat",
            padx=8,
            pady=3,
            cursor="hand2",
            command=self.exit_application,
        )
        quit_btn.pack(side=tk.LEFT, padx=3)

    # -------------------------------------------------------------------------
    # Theme Switching & Handlers
    # -------------------------------------------------------------------------

    def set_theme(self, mode: str) -> None:
        """Switch appearance theme between 'system', 'light', and 'dark'."""
        if mode not in ("system", "dark", "light"):
            return
        cfg = self.config_mgr.config
        cfg.theme_mode = mode
        cfg.dark_mode = (mode != "light")
        self.config_mgr.save(cfg)

        theme.set_theme_mode(mode)
        theme.apply_theme_to_ttk(self.style)
        self.configure(bg=theme.BG_DARK)

        # Preserve current active tab
        current_tab = "tab_schedule"
        if hasattr(self, "segmented_nav") and hasattr(self.segmented_nav, "active_tab"):
            current_tab = self.segmented_nav.active_tab

        # Rebuild UI with new theme palette
        if hasattr(self, "main_scroll") and self.main_scroll.winfo_exists():
            self.main_scroll.destroy()

        self._build_ui()

        # Restore active tab
        if hasattr(self, "segmented_nav"):
            self.segmented_nav.select_tab(current_tab)

        # Refresh time displays
        b_h, b_m = parse_time_str(self.config_mgr.config.bedtime)
        self._update_time_display(b_h, b_m)

    def _cycle_theme(self) -> None:
        """Cycle through appearance modes: system -> light -> dark -> system."""
        cur = getattr(self.config_mgr.config, "theme_mode", "system")
        cycle_map = {"system": "light", "light": "dark", "dark": "system"}
        next_mode = cycle_map.get(cur, "system")
        self.set_theme(next_mode)

    # -------------------------------------------------------------------------
    # Actions & Handlers
    # -------------------------------------------------------------------------

    def _toggle_sound(self) -> None:
        cfg = self.config_mgr.config
        cfg.enable_sound = not cfg.enable_sound
        self.config_mgr.save(cfg)
        self.sound_mgr.enabled = cfg.enable_sound
        self.sound_toggle_btn.config(
            text="🔔 Sound On" if cfg.enable_sound else "🔕 Muted",
        )
        if cfg.enable_sound:
            self.sound_mgr.play_snooze()

    def _save_schedule_settings(self) -> None:
        try:
            b_h = int(self.bed_hour_spin.get())
            b_m = int(self.bed_min_spin.get())
            w_h = int(self.wake_hour_spin.get())
            w_m = int(self.wake_min_spin.get())

            if not (0 <= b_h <= 23 and 0 <= b_m <= 59 and 0 <= w_h <= 23 and 0 <= w_m <= 59):
                raise ValueError("Hour must be 0-23, Minute 0-59.")

            bed_str = f"{b_h:02d}:{b_m:02d}"
            wake_str = f"{w_h:02d}:{w_m:02d}"

            cfg = self.config_mgr.config
            cfg.bedtime = bed_str
            cfg.wake_time = wake_str
            cfg.enable_escalating_reminders = self.enable_escalating_check.get()
            cfg.pause_media_on_reminder = self.pause_media_check.get()
            cfg.fullscreen_reminder = self.fullscreen_check.get()

            try:
                sd_secs = int(self.shutdown_seconds_spin.get())
                cfg.shutdown_countdown_seconds = max(10, min(120, sd_secs))
            except Exception:
                pass

            enable_autostart = self.autostart_check.get()
            if enable_autostart != cfg.autostart:
                cfg.autostart = enable_autostart
                set_autostart(enable_autostart)

            self.config_mgr.save(cfg)
            self.scheduler.update_config(cfg)

            # Update live displays
            self._update_time_display(b_h, b_m)
            self.hero_detail_lbl.config(text=f"Target Bedtime: {bed_str}  •  Ladder: +30m, +15m, +10m, then every 5m")

            self.save_feedback_lbl.config(text="✓ Saved & Active!", fg=theme.ACCENT_SUCCESS)
            if self._save_feedback_timer_id:
                try:
                    self.after_cancel(self._save_feedback_timer_id)
                except Exception:
                    pass
            self._save_feedback_timer_id = self.after(3000, self._clear_save_feedback)
        except Exception as e:
            messagebox.showerror("Invalid Schedule", str(e))

    def _clear_save_feedback(self) -> None:
        self._save_feedback_timer_id = None
        if hasattr(self, "save_feedback_lbl") and self.save_feedback_lbl.winfo_exists():
            try:
                self.save_feedback_lbl.config(text="")
            except Exception:
                pass

    def _on_scheduler_tick(self, countdown_str: str, next_event: str, seconds_left: float) -> None:
        """Called every second by the background scheduler thread."""
        def update():
            now = datetime.now()
            self.clock_lbl.config(text=now.strftime("%I:%M:%S %p").lstrip("0"))

            # Update segmented countdown chips
            total_sec = max(0, int(seconds_left))
            hrs = total_sec // 3600
            mins = (total_sec % 3600) // 60
            secs = total_sec % 60

            self.chip_hrs_val.config(text=f"{hrs:02d}")
            self.chip_mins_val.config(text=f"{mins:02d}")
            self.chip_secs_val.config(text=f"{secs:02d}")

            # Keep legacy countdown_lbl updated for test assertions
            self.countdown_lbl.config(text=countdown_str)
            self.hero_event_lbl.config(text=f"COUNTDOWN TO {next_event.upper()}")

            # Status badge
            if self.scheduler.state == ReminderState.SNOOZED:
                self.status_badge.config(text="● Snoozed", fg=theme.ACCENT_MOON)
            elif self.scheduler.state == ReminderState.WIND_DOWN_ACTIVE:
                self.status_badge.config(text="● Wind-down Active", fg=theme.ACCENT_CYAN)
            elif self.scheduler.state == ReminderState.BEDTIME_ACTIVE:
                self.status_badge.config(text="● Bedtime Active", fg=theme.ACCENT_DANGER)
            else:
                self.status_badge.config(text="● Active Monitoring", fg=theme.ACCENT_SUCCESS)

            # System Tray tooltip
            if self.tray:
                self.tray.update_tooltip(
                    f"Sleep Reminder • Bedtime: {self.config_mgr.config.bedtime} ({countdown_str} left)"
                )

        self.after(0, update)

    def _on_wind_down_triggered(self) -> None:
        """Triggers the wind-down toast."""
        def show():
            self.sound_mgr.play_wind_down()
            if self._active_toast:
                try:
                    self._active_toast.destroy()
                except Exception:
                    pass

            cfg = self.config_mgr.config
            self._active_toast = ToastNotification(
                parent=self,
                title="Wind-down Reminder",
                message=f"Bedtime is in {cfg.wind_down_minutes} minutes. Start wrapping up tasks and prepare for rest.",
                on_snooze=lambda: self.scheduler.snooze(10),
                on_dismiss=lambda: None,
            )

        self.after(0, show)

    def _on_bedtime_triggered(self, stage: int = 0, minutes_overdue: int = 0, next_minutes: int = 30) -> None:
        """Triggers the bedtime modal alert with escalating urgency and auto-pauses playing media."""
        def show():
            cfg = self.config_mgr.config

            # 1. Automatically pause playing video / audio
            if cfg.pause_media_on_reminder:
                pause_system_media()

            # 2. Play alert sound
            self.sound_mgr.play_bedtime()

            if self._active_modal and self._active_modal.winfo_exists():
                try:
                    self._active_modal.update_stage(
                        stage=stage,
                        minutes_overdue=minutes_overdue,
                        next_reminder_in_minutes=next_minutes,
                    )
                    return
                except Exception:
                    pass

            self._active_modal = BedtimeModal(
                parent=self,
                bedtime_str=cfg.bedtime,
                on_sleep=self._handle_sleep_confirmed,
                on_snooze=lambda mins: self.scheduler.snooze(mins),
                on_dismiss=self._handle_dismiss,
                snooze_minutes=cfg.snooze_duration_minutes,
                strict_mode=cfg.strict_mode,
                stage=stage,
                minutes_overdue=minutes_overdue,
                next_reminder_in_minutes=next_minutes,
                shutdown_countdown_seconds=cfg.shutdown_countdown_seconds,
                fullscreen=cfg.fullscreen_reminder,
            )

        self.after(0, show)

    def _handle_sleep_confirmed(self) -> None:
        self.scheduler.confirm_sleep()
        self.sound_mgr.play_snooze()
        self.history_mgr.log_event(self.config_mgr.config.bedtime, "slept_on_time")

        stats = self.history_mgr.calculate_stats()
        self.streak_val_lbl.config(text=f"🔥 {stats['current_streak']} Days")
        self.rate_val_lbl.config(text=f"{stats['recent_on_time_rate']}% Consistent")
        self.total_val_lbl.config(text=f"{stats['total_logged']} Nights")
        self._refresh_history_list()

        messagebox.showinfo("Good Night", "Sleep time recorded! Have a restorative, peaceful rest. 🌙")

    def _handle_dismiss(self) -> None:
        self.scheduler.dismiss()
        self.history_mgr.log_event(self.config_mgr.config.bedtime, "dismissed")

    def _restore_from_tray(self) -> None:
        def restore():
            self.deiconify()
            try:
                self.state("zoomed")
            except Exception:
                pass
            self.lift()
            self.focus_force()
        self.after(0, restore)

    def _toggle_pause_for_today(self) -> None:
        def toggle():
            currently_paused = self.scheduler.is_paused_for_today()
            self.scheduler.pause_for_today(not currently_paused)
            if self.tray:
                if not currently_paused:
                    self.tray.show_balloon("Sleep Reminder Paused", "Reminders are paused for tonight.")
                else:
                    self.tray.show_balloon("Sleep Reminder Resumed", "Reminders are active.")
        self.after(0, toggle)

    def exit_application(self, disable_autostart: bool = True) -> None:
        if disable_autostart:
            try:
                from sleep_reminder.autostart import set_autostart
                set_autostart(False)
                self.config_mgr.config.autostart = False
                self.config_mgr.save()
            except Exception:
                pass
        if self._save_feedback_timer_id:
            try:
                self.after_cancel(self._save_feedback_timer_id)
            except Exception:
                pass
            self._save_feedback_timer_id = None
        self.scheduler.stop()
        if self.tray:
            self.tray.stop()
        try:
            self.destroy()
        except Exception:
            pass

    def _on_close(self) -> None:
        if self.tray and self.tray.hwnd:
            self.withdraw()
            self.tray.show_balloon(
                "Sleep Reminder Active",
                "Sleep Reminder is running in the background. Right-click or double-click the tray icon to open.",
            )
        else:
            self.exit_application()
