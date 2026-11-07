"""
Non-intrusive floating desktop toast notification for wind-down reminders.
Positions gracefully in the lower-right corner of the active monitor.
"""

from __future__ import annotations
import tkinter as tk
from typing import Callable, Optional

from sleep_reminder.ui import theme


class ToastNotification(tk.Toplevel):
    """Sleek dark-mode toast notification positioned above the Windows taskbar."""

    def __init__(
        self,
        parent: tk.Tk,
        title: str,
        message: str,
        on_snooze: Optional[Callable[[], None]] = None,
        on_dismiss: Optional[Callable[[], None]] = None,
        duration_ms: int = 15000,
    ) -> None:
        super().__init__(parent)
        self.on_snooze = on_snooze
        self.on_dismiss = on_dismiss

        # Window properties
        self.overrideredirect(True)  # Frameless
        self.attributes("-topmost", True)
        self.configure(bg=theme.BG_CARD)

        self._auto_close_id: Optional[str] = None
        self._build_ui(title, message)
        self._position_bottom_right()

        if duration_ms > 0:
            self._auto_close_id = self.after(duration_ms, self.dismiss)

    def _build_ui(self, title: str, message: str) -> None:
        # Outer border frame
        outer = tk.Frame(self, bg=theme.ACCENT_PRIMARY, bd=1)
        outer.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(outer, bg=theme.BG_CARD, padx=16, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)

        # Header row: Icon + Title + Close Button
        header_row = tk.Frame(inner, bg=theme.BG_CARD)
        header_row.pack(fill=tk.X, pady=(0, 6))

        icon_lbl = tk.Label(
            header_row,
            text="🌙",
            font=(theme.FONT_FAMILY, 14),
            bg=theme.BG_CARD,
            fg=theme.ACCENT_MOON,
        )
        icon_lbl.pack(side=tk.LEFT, padx=(0, 8))

        title_lbl = tk.Label(
            header_row,
            text=title,
            font=theme.FONT_SUBTITLE,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MAIN,
        )
        title_lbl.pack(side=tk.LEFT)

        close_btn = tk.Label(
            header_row,
            text="✕",
            font=theme.FONT_BODY_BOLD,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
            cursor="hand2",
        )
        close_btn.pack(side=tk.RIGHT)
        close_btn.bind("<Button-1>", lambda e: self.dismiss())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=theme.TEXT_MAIN))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=theme.TEXT_MUTED))

        # Message body
        msg_lbl = tk.Label(
            inner,
            text=message,
            font=theme.FONT_BODY,
            bg=theme.BG_CARD,
            fg=theme.TEXT_MUTED,
            justify=tk.LEFT,
            wraplength=320,
        )
        msg_lbl.pack(anchor="w", pady=(0, 12))

        # Action Buttons
        btn_row = tk.Frame(inner, bg=theme.BG_CARD)
        btn_row.pack(fill=tk.X)

        snooze_btn = tk.Button(
            btn_row,
            text="⏳ Snooze 10m",
            bg=theme.BG_CARD_HOVER,
            fg=theme.TEXT_MAIN,
            activebackground=theme.BORDER_COLOR,
            activeforeground="#ffffff",
            relief="flat",
            font=theme.FONT_CAPTION,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._handle_snooze,
        )
        snooze_btn.pack(side=tk.LEFT, padx=(0, 8))

        dismiss_btn = tk.Button(
            btn_row,
            text="Got it",
            bg=theme.ACCENT_PRIMARY,
            fg="#ffffff",
            activebackground="#4f46e5",
            activeforeground="#ffffff",
            relief="flat",
            font=theme.FONT_CAPTION,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self.dismiss,
        )
        dismiss_btn.pack(side=tk.RIGHT)

    def _position_bottom_right(self) -> None:
        self.update_idletasks()
        width = 380
        height = self.winfo_reqheight()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # Position 20px above taskbar
        margin_x = 24
        margin_y = 60
        x = screen_w - width - margin_x
        y = screen_h - height - margin_y

        self.geometry(f"{width}x{height}+{x}+{y}")

    def _handle_snooze(self) -> None:
        if self._auto_close_id:
            self.after_cancel(self._auto_close_id)
        if self.on_snooze:
            self.on_snooze()
        self.destroy()

    def dismiss(self) -> None:
        if self._auto_close_id:
            try:
                self.after_cancel(self._auto_close_id)
            except Exception:
                pass
        if self.on_dismiss:
            self.on_dismiss()
        self.destroy()
