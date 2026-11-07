"""
Modern dark midnight theme styling for Sleep Reminder.
Calming palette inspired by twilight and deep sleep with vibrant glassmorphic accents.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk

# Palette - Modern Obsidian Midnight Slate
BG_DARK = "#0b0f19"          # Deep obsidian navy
BG_SURFACE = "#0f172a"       # Slate base
BG_CARD = "#131d31"          # Glass card surface
BG_CARD_HOVER = "#1c2a45"    # Card hover
BG_CARD_ACTIVE = "#233557"   # Active card
BORDER_COLOR = "#22314e"     # Card border outline
BORDER_ACCENT = "#38bdf8"    # Accent border

ACCENT_PRIMARY = "#6366f1"   # Vibrant Indigo
ACCENT_PRIMARY_HOVER = "#4f46e5"
ACCENT_MOON = "#fbbf24"      # Luminous Warm Amber
ACCENT_CYAN = "#38bdf8"      # Twilight Sky Cyan
ACCENT_SUCCESS = "#34d399"   # Restorative Emerald
ACCENT_WARNING = "#f59e0b"   # Overdue Amber
ACCENT_ORANGE = "#f97316"    # Urgent Orange
ACCENT_DANGER = "#ef4444"    # Critical Red
ACCENT_DANGER_HOVER = "#dc2626"

TEXT_MAIN = "#f8fafc"        # Ultra crisp white
TEXT_MUTED = "#94a3b8"       # Medium slate
TEXT_DIM = "#64748b"         # Dark slate

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


def apply_theme_to_ttk(style: ttk.Style) -> None:
    """Configures ttk widget styles to match the modern midnight theme."""
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
        background=[("active", ACCENT_PRIMARY_HOVER), ("disabled", "#475569")],
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
