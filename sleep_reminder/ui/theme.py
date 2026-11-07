"""Modern theme styling for Sleep Reminder.

Supports Light, Dark, and System appearance modes with seamless runtime switching.
"""

from __future__ import annotations
import sys
import tkinter as tk
from tkinter import ttk

# Default Dark Palette (Obsidian Midnight Slate)
DARK_PALETTE = {
    "BG_DARK": "#0b0f19",
    "BG_SURFACE": "#0f172a",
    "BG_CARD": "#131d31",
    "BG_CARD_HOVER": "#1c2a45",
    "BG_CARD_ACTIVE": "#233557",
    "BG_HERO": "#0f192d",
    "BG_SUBTLE": "#080e1a",
    "BG_NAV": "#090f1d",
    "BORDER_COLOR": "#22314e",
    "BORDER_HERO": "#233555",
    "BORDER_NAV": "#1b2840",
    "ACCENT_PRIMARY": "#6366f1",
    "ACCENT_PRIMARY_HOVER": "#4f46e5",
    "ACCENT_MOON": "#fbbf24",
    "ACCENT_CYAN": "#38bdf8",
    "ACCENT_SUCCESS": "#34d399",
    "ACCENT_WARNING": "#f59e0b",
    "ACCENT_ORANGE": "#f97316",
    "ACCENT_DANGER": "#ef4444",
    "ACCENT_DANGER_HOVER": "#dc2626",
    "TEXT_MAIN": "#f8fafc",
    "TEXT_MUTED": "#94a3b8",
    "TEXT_DIM": "#64748b",
    "SWITCH_TRACK_INACTIVE": "#23334d",
    "CHIP_BG": "#080e1a",
    "CHIP_BORDER": "#1b2943",
    "BADGE_BG": "#1e1b4b",
    "BADGE_FG": "#38bdf8",
}

# Clean SaaS Light Palette (Slate 50 / Pure White / Indigo)
LIGHT_PALETTE = {
    "BG_DARK": "#f8fafc",
    "BG_SURFACE": "#ffffff",
    "BG_CARD": "#ffffff",
    "BG_CARD_HOVER": "#f1f5f9",
    "BG_CARD_ACTIVE": "#e2e8f0",
    "BG_HERO": "#f0f4ff",
    "BG_SUBTLE": "#f8fafc",
    "BG_NAV": "#f1f5f9",
    "BORDER_COLOR": "#e2e8f0",
    "BORDER_HERO": "#c7d2fe",
    "BORDER_NAV": "#e2e8f0",
    "ACCENT_PRIMARY": "#4f46e5",
    "ACCENT_PRIMARY_HOVER": "#4338ca",
    "ACCENT_MOON": "#d97706",
    "ACCENT_CYAN": "#0284c7",
    "ACCENT_SUCCESS": "#059669",
    "ACCENT_WARNING": "#d97706",
    "ACCENT_ORANGE": "#ea580c",
    "ACCENT_DANGER": "#dc2626",
    "ACCENT_DANGER_HOVER": "#b91c1c",
    "TEXT_MAIN": "#0f172a",
    "TEXT_MUTED": "#475569",
    "TEXT_DIM": "#94a3b8",
    "SWITCH_TRACK_INACTIVE": "#cbd5e1",
    "CHIP_BG": "#ffffff",
    "CHIP_BORDER": "#e2e8f0",
    "BADGE_BG": "#e0e7ff",
    "BADGE_FG": "#4338ca",
}

# Active theme state
CURRENT_THEME_MODE: str = "system"
IS_DARK: bool = True

# Initialize module-level palette attributes with dark defaults
globals().update(DARK_PALETTE)

# Fonts - Clean Segoe UI typography hierarchy
FONT_FAMILY = "Segoe UI"
FONT_DISPLAY = (FONT_FAMILY, 34, "bold")
FONT_HERO = (FONT_FAMILY, 28, "bold")
FONT_TITLE = (FONT_FAMILY, 20, "bold")
FONT_SUBTITLE = (FONT_FAMILY, 12, "bold")
FONT_BODY = (FONT_FAMILY, 10)
FONT_BODY_BOLD = (FONT_FAMILY, 10, "bold")
FONT_CAPTION = (FONT_FAMILY, 9)
FONT_SMALL = (FONT_FAMILY, 8)


def is_system_dark_mode() -> bool:
    """Check whether Windows is configured in Dark Mode via Windows Registry."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            )
            val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return val == 0
        except Exception:
            return True
    return True


def get_effective_theme(mode: str) -> str:
    """Return 'dark' or 'light' for a given theme mode ('system', 'dark', 'light')."""
    if mode == "system":
        return "dark" if is_system_dark_mode() else "light"
    return "light" if mode == "light" else "dark"


def set_theme_mode(mode: str = "system") -> bool:
    """Update global theme palette attributes to match the specified mode.

    Returns True if effective appearance is Dark Mode, False if Light Mode.
    """
    global CURRENT_THEME_MODE, IS_DARK
    CURRENT_THEME_MODE = mode
    effective = get_effective_theme(mode)
    IS_DARK = (effective == "dark")
    palette = DARK_PALETTE if IS_DARK else LIGHT_PALETTE
    globals().update(palette)
    return IS_DARK


def apply_theme_to_ttk(style: ttk.Style) -> None:
    """Configures ttk widget styles to match the active theme palette."""
    style.theme_use("clam")

    style.configure(
        "TFrame",
        background=BG_DARK,
    )
    style.configure(
        "Card.TFrame",
        background=BG_CARD,
        relief="flat",
    )
    style.configure(
        "TLabel",
        background=BG_DARK,
        foreground=TEXT_MAIN,
        font=FONT_BODY,
    )
    style.configure(
        "Card.TLabel",
        background=BG_CARD,
        foreground=TEXT_MAIN,
        font=FONT_BODY,
    )
    style.configure(
        "Muted.TLabel",
        background=BG_CARD,
        foreground=TEXT_MUTED,
        font=FONT_CAPTION,
    )
    style.configure(
        "Primary.TButton",
        background=ACCENT_PRIMARY,
        foreground="#ffffff",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor="none",
        padding=(16, 9),
    )
    style.map(
        "Primary.TButton",
        background=[("active", ACCENT_PRIMARY_HOVER), ("disabled", "#94a3b8" if not IS_DARK else "#475569")],
    )

    style.configure(
        "Secondary.TButton",
        background=BG_CARD_HOVER,
        foreground=TEXT_MAIN,
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor="none",
        padding=(14, 7),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", BG_CARD_ACTIVE)],
    )

    style.configure(
        "Danger.TButton",
        background=ACCENT_DANGER,
        foreground="#ffffff",
        font=FONT_BODY_BOLD,
        borderwidth=0,
        focuscolor="none",
        padding=(16, 9),
    )
    style.map(
        "Danger.TButton",
        background=[("active", ACCENT_DANGER_HOVER)],
    )

    style.configure(
        "TNotebook",
        background=BG_DARK,
        borderwidth=0,
    )
    style.configure(
        "NoTabs.TNotebook",
        background=BG_DARK,
        borderwidth=0,
    )
    style.layout("NoTabs.TNotebook.Tab", [])
    style.configure(
        "TNotebook.Tab",
        background=BG_CARD,
        foreground=TEXT_MUTED,
        font=FONT_BODY_BOLD,
        padding=(20, 10),
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", ACCENT_PRIMARY), ("active", BG_CARD_HOVER)],
        foreground=[("selected", "#ffffff"), ("active", TEXT_MAIN)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=BG_CARD_HOVER,
        background=BG_CARD_HOVER,
        foreground=TEXT_MAIN,
        arrowcolor=TEXT_MAIN,
        borderwidth=0,
        padding=4,
    )

    style.configure(
        "TSpinbox",
        fieldbackground=BG_CARD_HOVER,
        background=BG_CARD_HOVER,
        foreground=TEXT_MAIN,
        arrowcolor=TEXT_MAIN,
        borderwidth=0,
    )


def draw_rounded_rectangle(
    canvas: tk.Canvas,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    radius: int = 14,
    **kwargs,
) -> int:
    """Draws a smooth rounded rectangle on a Tkinter Canvas."""
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)
