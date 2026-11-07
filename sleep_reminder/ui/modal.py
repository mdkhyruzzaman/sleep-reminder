"""
Bedtime Alert Modal Window - Full Screen Ambient Overlay with Windows Power Actions.
Displays full-screen escalating reminders (Bedtime, +30m, +15m, +10m, and repeating 5m)
with direct PC Shutdown (safety countdown), Sleep, and Snooze options.
"""

from __future__ import annotations
from datetime import datetime
import tkinter as tk
from typing import Callable, Optional

from sleep_reminder.icon import apply_window_icon
from sleep_reminder.power import shutdown_system, abort_shutdown, sleep_system
from sleep_reminder.ui import theme


class BedtimeModal(tk.Toplevel):
    """Modern full-screen ambient alert displayed when bedtime is reached or overdue."""

    # Urgency color schemes per stage
    STAGE_THEMES = [
        # Stage 0: Bedtime (Twilight & Crescent Moon)
        {
            "header_bg": "#050811",
            "card_bg": "#0d1527",
            "border_color": "#38bdf8",
            "accent": "#38bdf8",
            "title": "Time for Sleep",
            "icon": "🌙",
            "tag": "BEDTIME REACHED",
            "btn_shutdown_bg": "#dc2626",
            "glow_color": "#1e3a8a",
        },
        # Stage 1: +30m (Amber Warning)
        {
            "header_bg": "#0c0803",
            "card_bg": "#1c1407",
            "border_color": "#f59e0b",
            "accent": "#f59e0b",
            "title": "30 Minutes Past Bedtime",
            "icon": "⚠️",
            "tag": "STAGE 1 WARNING • +30 MIN",
            "btn_shutdown_bg": "#dc2626",
            "glow_color": "#78350f",
        },
        # Stage 2: +45m (Orange Alert)
        {
            "header_bg": "#100603",
            "card_bg": "#221108",
            "border_color": "#f97316",
            "accent": "#f97316",
            "title": "45 Minutes Past Bedtime",
            "icon": "⏰",
            "tag": "STAGE 2 WARNING • +45 MIN",
            "btn_shutdown_bg": "#dc2626",
            "glow_color": "#7c2d12",
        },
        # Stage 3: +55m (Red Urgency)
        {
            "header_bg": "#130405",
            "card_bg": "#270c0e",
            "border_color": "#ef4444",
            "accent": "#ef4444",
            "title": "55 Minutes Past Bedtime",
            "icon": "🚨",
            "tag": "STAGE 3 URGENT • +55 MIN",
            "btn_shutdown_bg": "#b91c1c",
            "glow_color": "#881337",
        },
        # Stage 4+: Repeating 5m (Critical Crimson)
        {
            "header_bg": "#160305",
            "card_bg": "#2c090c",
            "border_color": "#f43f5e",
            "accent": "#f43f5e",
            "title": "Critical: 1+ Hour Past Bedtime",
            "icon": "🛑",
            "tag": "CRITICAL • REPEATING EVERY 5 MIN",
            "btn_shutdown_bg": "#991b1b",
            "glow_color": "#9f1239",
        },
    ]

    def __init__(
        self,
        parent: tk.Tk,
        bedtime_str: str,
        on_sleep: Optional[Callable[[], None]] = None,
        on_snooze: Optional[Callable[[int], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        snooze_minutes: int = 10,
        strict_mode: bool = False,
        stage: int = 0,
        minutes_overdue: int = 0,
        next_reminder_in_minutes: int = 30,
        shutdown_countdown_seconds: int = 30,
        fullscreen: bool = True,
    ) -> None:
        super().__init__(parent)
        self.bedtime_str = bedtime_str
        self.on_sleep = on_sleep
        self.on_snooze = on_snooze
        self.on_dismiss = on_dismiss
        self.snooze_minutes = snooze_minutes
        self.strict_mode = strict_mode
        self.stage = stage
        self.minutes_overdue = minutes_overdue
        self.next_reminder_in_minutes = next_reminder_in_minutes
        self.shutdown_countdown_seconds = shutdown_countdown_seconds
        self.fullscreen = fullscreen

        self._shutdown_active = False
        self._countdown_remaining = 0
        self._timer_id: Optional[str] = None
        self._clock_timer_id: Optional[str] = None

        self.title("🌙 Sleep Reminder - Bedtime Alert")
        apply_window_icon(self)
        self.configure(bg="#050811")
        self.attributes("-topmost", True)

        if self.fullscreen:
            try:
                self.attributes("-fullscreen", True)
            except Exception:
                screen_w = self.winfo_screenwidth()
                screen_h = self.winfo_screenheight()
                self.geometry(f"{screen_w}x{screen_h}+0+0")
        else:
            self._center_window(560, 600)

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self._handle_snooze())

        self._build_ui()
        self._tick_clock()

    def _center_window(self, width: int, height: int) -> None:
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

    def update_stage(self, stage: int, minutes_overdue: int, next_reminder_in_minutes: int) -> None:
        """Update window in place if already open when a new interval is reached."""
        self.stage = stage
        self.minutes_overdue = minutes_overdue
        self.next_reminder_in_minutes = next_reminder_in_minutes
        for widget in self.winfo_children():
            widget.destroy()
        self._build_ui()
        self.lift()
        self.attributes("-topmost", True)

    def _get_stage_theme(self) -> dict:
        idx = min(self.stage, len(self.STAGE_THEMES) - 1)
        return self.STAGE_THEMES[idx]

    def _build_ui(self) -> None:
        st = self._get_stage_theme()
        self.configure(bg=st["header_bg"])

        # Main background canvas with starry constellations and radial ambient glow
        self.bg_canvas = tk.Canvas(
            self,
            bg=st["header_bg"],
            bd=0,
            highlightthickness=0,
        )
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)

        # Draw decorative stars
        stars = [
            (0.08, 0.12), (0.15, 0.25), (0.22, 0.08), (0.35, 0.18), (0.42, 0.06),
            (0.58, 0.14), (0.65, 0.08), (0.78, 0.22), (0.88, 0.11), (0.92, 0.28),
            (0.12, 0.75), (0.20, 0.88), (0.32, 0.82), (0.72, 0.85), (0.84, 0.76),
            (0.91, 0.88), (0.05, 0.50), (0.95, 0.52), (0.18, 0.42), (0.82, 0.38),
        ]
        self.bind("<Configure>", lambda e: self._redraw_background(stars, st))

        # Top-right quick exit/snooze button
        top_bar = tk.Frame(self, bg=st["header_bg"])
        top_bar.pack(side=tk.TOP, fill=tk.X, padx=24, pady=16)

        esc_hint = tk.Label(
            top_bar,
            text="Press [Esc] to Snooze",
            font=theme.FONT_SMALL,
            bg=st["header_bg"],
            fg=theme.TEXT_DIM,
        )
        esc_hint.pack(side=tk.LEFT)

        close_btn = tk.Button(
            top_bar,
            text="✕  Exit Full Screen",
            font=theme.FONT_CAPTION,
            bg=st["header_bg"],
            fg=theme.TEXT_MUTED,
            activebackground=st["card_bg"],
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._handle_snooze,
        )
        close_btn.pack(side=tk.RIGHT)

        # Centered Content Wrapper
        center_frame = tk.Frame(self, bg=st["header_bg"])
        center_frame.pack(expand=True)

        # Modern Glass Card
        self.card = tk.Frame(
            center_frame,
            bg=st["card_bg"],
            padx=42,
            pady=36,
            highlightthickness=2,
            highlightbackground=st["border_color"],
            highlightcolor=st["border_color"],
        )
        self.card.pack()

        # Stage Icon & Moon Graphic
        icon_frame = tk.Frame(self.card, bg=st["card_bg"])
        icon_frame.pack(pady=(0, 10))

        if self.stage == 0:
            moon_canvas = tk.Canvas(icon_frame, bg=st["card_bg"], width=90, height=90, bd=0, highlightthickness=0)
            moon_canvas.pack()
            # Golden glowing full circle
            moon_canvas.create_oval(15, 15, 75, 75, fill=theme.ACCENT_MOON, outline="")
            # Eclipse circle to create crescent
            moon_canvas.create_oval(28, 8, 85, 68, fill=st["card_bg"], outline="")
        else:
            stage_icon_lbl = tk.Label(
                icon_frame,
                text=st["icon"],
                font=(theme.FONT_FAMILY, 46),
                bg=st["card_bg"],
                fg=st["accent"],
            )
            stage_icon_lbl.pack()

        # Tag Badge
        tag_badge = tk.Label(
            self.card,
            text=f"  {st['tag']}  ",
            font=(theme.FONT_FAMILY, 9, "bold"),
            bg=st["header_bg"],
            fg=st["accent"],
            padx=8,
            pady=4,
        )
        tag_badge.pack(pady=(0, 12))

        # Main Title
        title_lbl = tk.Label(
            self.card,
            text=st["title"],
            font=(theme.FONT_FAMILY, 26, "bold"),
            bg=st["card_bg"],
            fg=theme.TEXT_MAIN,
        )
        title_lbl.pack(pady=(0, 4))

        # Real-time Live Clock in modal
        self.clock_lbl = tk.Label(
            self.card,
            text=datetime.now().strftime("%I:%M:%S %p").lstrip("0"),
            font=(theme.FONT_FAMILY, 18, "bold"),
            bg=st["card_bg"],
            fg=st["accent"],
        )
        self.clock_lbl.pack(pady=(0, 12))

        # Detailed Status & Overdue Info
        if self.stage == 0:
            status_text = f"Scheduled Bedtime: {self.bedtime_str}  •  Next reminder in {self.next_reminder_in_minutes} min"
        else:
            status_text = f"Scheduled Bedtime was {self.bedtime_str}  •  {self.minutes_overdue} Minutes Overdue"

        status_lbl = tk.Label(
            self.card,
            text=status_text,
            font=theme.FONT_BODY_BOLD,
            bg=st["card_bg"],
            fg=theme.TEXT_MAIN,
        )
        status_lbl.pack(pady=(0, 8))

        # Urgency Description Message
        if self.stage == 0:
            desc = "It's time to conclude your tasks, protect your eyes from bright displays, and power down your PC for a healthy night of rest."
        elif self.stage == 1:
            desc = "30 minutes have elapsed past your target bedtime. Every hour awake late diminishes tomorrow's mental energy and immune defense."
        elif self.stage == 2:
            desc = "45 minutes overdue. Working or browsing late disrupts your circadian cycle. Please save all open documents and shut down."
        elif self.stage == 3:
            desc = "Urgent: 55 minutes past bedtime! Please wrap up right now and allow your body to enter deep restorative sleep."
        else:
            desc = "Critical bedtime reminder: Over 1 hour past bedtime! This reminder will continue repeating every 5 minutes until shutdown."

        desc_lbl = tk.Label(
            self.card,
            text=desc,
            font=theme.FONT_BODY,
            bg=st["card_bg"],
            fg=theme.TEXT_MUTED,
            justify=tk.CENTER,
            wraplength=480,
        )
        desc_lbl.pack(pady=(0, 22))

        # Shutdown Countdown Banner (if user triggers shutdown)
        self.shutdown_banner = tk.Frame(self.card, bg="#7f1d1d", padx=16, pady=12, bd=1, relief="solid")
        self.shutdown_banner_lbl = tk.Label(
            self.shutdown_banner,
            text="Shutting down in 30s...",
            font=(theme.FONT_FAMILY, 12, "bold"),
            bg="#7f1d1d",
            fg="#ffffff",
        )
        self.shutdown_banner_lbl.pack(side=tk.LEFT, padx=(0, 14))

        cancel_btn = tk.Button(
            self.shutdown_banner,
            text="Cancel Shutdown",
            font=theme.FONT_BODY_BOLD,
            bg="#ffffff",
            fg="#7f1d1d",
            activebackground="#fca5a5",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self._cancel_shutdown,
        )
        cancel_btn.pack(side=tk.RIGHT)

        # Action Buttons Container
        self.btn_frame = tk.Frame(self.card, bg=st["card_bg"])
        self.btn_frame.pack(fill=tk.X, pady=(0, 14))

        # 1. Primary Action: Shut Down PC
        self.shutdown_btn = tk.Button(
            self.btn_frame,
            text="🛑   Shut Down PC Now",
            font=(theme.FONT_FAMILY, 12, "bold"),
            bg=st["btn_shutdown_bg"],
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief="flat",
            pady=12,
            cursor="hand2",
            command=self._handle_shutdown_click,
        )
        self.shutdown_btn.pack(fill=tk.X, pady=(0, 10))

        # 2. Secondary Action: Sleep / Suspend PC
        self.sleep_btn = tk.Button(
            self.btn_frame,
            text="🌙   Sleep / Suspend PC",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.ACCENT_PRIMARY,
            activeforeground="#ffffff",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=self._handle_sleep_suspend_click,
        )
        self.sleep_btn.pack(fill=tk.X, pady=(0, 10))

        # 3. Snooze / Next Reminder Button
        snooze_text = f"⏳   Snooze (Remind Me in {self.next_reminder_in_minutes} Min)"
        self.snooze_btn = tk.Button(
            self.btn_frame,
            text=snooze_text,
            font=theme.FONT_BODY,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
            activebackground=theme.BG_CARD_HOVER,
            activeforeground=theme.TEXT_MAIN,
            relief="flat",
            pady=9,
            cursor="hand2",
            command=self._handle_snooze,
        )
        self.snooze_btn.pack(fill=tk.X)

        # Subtle dismiss action
        confirm_btn = tk.Button(
            self.card,
            text="✓ Log Bedtime & Dismiss for Tonight",
            font=theme.FONT_CAPTION,
            bg=st["card_bg"],
            fg=theme.TEXT_DIM,
            activebackground=st["card_bg"],
            activeforeground=theme.TEXT_MUTED,
            relief="flat",
            pady=4,
            cursor="hand2",
            command=self._handle_sleep,
        )
        confirm_btn.pack()

    def _redraw_background(self, stars: list, st: dict) -> None:
        """Redraw starry background on resize."""
        w = self.winfo_width()
        h = self.winfo_height()
        self.bg_canvas.delete("all")

        # Draw stars
        for rx, ry in stars:
            sx = int(rx * w)
            sy = int(ry * h)
            self.bg_canvas.create_oval(sx, sy, sx + 2, sy + 2, fill="#475569", outline="")

    def _tick_clock(self) -> None:
        """Update live clock inside modal every second."""
        if hasattr(self, "clock_lbl") and self.clock_lbl.winfo_exists():
            now_str = datetime.now().strftime("%I:%M:%S %p").lstrip("0")
            self.clock_lbl.config(text=now_str)
            self._clock_timer_id = self.after(1000, self._tick_clock)

    # -------------------------------------------------------------------------
    # Shutdown & Sleep Handlers
    # -------------------------------------------------------------------------

    def _handle_shutdown_click(self) -> None:
        """Starts the safety countdown and schedules Windows shutdown."""
        self._shutdown_active = True
        self._countdown_remaining = self.shutdown_countdown_seconds

        # Hide buttons and show countdown banner
        self.btn_frame.pack_forget()
        self.shutdown_banner.pack(fill=tk.X, pady=(0, 16))

        shutdown_system(
            seconds=self.shutdown_countdown_seconds,
            comment=f"Sleep Reminder: Scheduled bedtime {self.bedtime_str}",
        )

        self._tick_shutdown_countdown()

    def _tick_shutdown_countdown(self) -> None:
        if not self._shutdown_active:
            return

        if self._countdown_remaining > 0:
            self.shutdown_banner_lbl.config(
                text=f"🚨 Shutting down Windows in {self._countdown_remaining}s... (Save files!)"
            )
            self._countdown_remaining -= 1
            self._timer_id = self.after(1000, self._tick_shutdown_countdown)
        else:
            self.shutdown_banner_lbl.config(text="Shutting down now...")

    def _cancel_shutdown(self) -> None:
        """Aborts the Windows shutdown and restores UI buttons."""
        self._shutdown_active = False
        if self._timer_id:
            self.after_cancel(self._timer_id)
            self._timer_id = None

        abort_shutdown()

        self.shutdown_banner.pack_forget()
        self.btn_frame.pack(fill=tk.X, pady=(0, 14))

    def _handle_sleep_suspend_click(self) -> None:
        """Puts Windows to sleep."""
        if self.on_sleep:
            self.on_sleep()
        sleep_system()
        self.destroy()

    def _handle_sleep(self) -> None:
        if self.on_sleep:
            self.on_sleep()
        self.destroy()

    def _handle_snooze(self) -> None:
        if self.on_snooze:
            self.on_snooze(self.next_reminder_in_minutes)
        self.destroy()

    def _handle_dismiss(self) -> None:
        if self.on_dismiss:
            self.on_dismiss()
        self.destroy()

    def destroy(self) -> None:
        if self._clock_timer_id:
            try:
                self.after_cancel(self._clock_timer_id)
            except Exception:
                pass
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
        super().destroy()
