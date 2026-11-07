"""Modern Web-App Styled UI Components for Tkinter.

Provides iOS/Linear style pill toggle switches, segmented tab navigation bars,
digital countdown display cards, and quick preset chips.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, List, Optional, Tuple

from sleep_reminder.ui import theme


class ModernSwitch(tk.Canvas):
    """An iOS/Linear-style interactive toggle switch widget."""

    def __init__(
        self,
        parent: tk.Widget,
        variable: Optional[tk.BooleanVar] = None,
        command: Optional[Callable[[bool], None]] = None,
        width: int = 48,
        height: int = 24,
        bg: Optional[str] = None,
        active_color: Optional[str] = None,
        inactive_color: Optional[str] = None,
        knob_color: str = "#ffffff",
    ) -> None:
        bg = bg or theme.BG_CARD
        active_color = active_color or theme.ACCENT_PRIMARY
        inactive_color = inactive_color or theme.SWITCH_TRACK_INACTIVE
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg,
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.width = width
        self.height = height
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.knob_color = knob_color
        self.command = command

        self.variable = variable or tk.BooleanVar(value=False)
        self._state = self.variable.get()

        self.bind("<Button-1>", self._on_click)
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        r = self.height // 2
        w, h = self.width, self.height
        color = self.active_color if self._state else self.inactive_color

        # Draw rounded pill track
        self.create_arc((0, 0, h, h), start=90, extent=180, fill=color, outline="")
        self.create_arc((w - h, 0, w, h), start=270, extent=180, fill=color, outline="")
        self.create_rectangle((r, 0, w - r, h), fill=color, outline="")

        # Draw circular knob
        pad = 3
        knob_d = h - (pad * 2)
        if self._state:
            kx = w - pad - knob_d
        else:
            kx = pad
        ky = pad

        self.create_oval(
            (kx, ky, kx + knob_d, ky + knob_d),
            fill=self.knob_color,
            outline="",
        )

    def _on_click(self, event=None) -> None:
        self._state = not self._state
        self.variable.set(self._state)
        self._draw()
        if self.command:
            self.command(self._state)

    def get(self) -> bool:
        return self._state

    def set(self, val: bool) -> None:
        self._state = bool(val)
        self.variable.set(self._state)
        self._draw()


class SegmentedNavBar(tk.Frame):
    """Modern web-app style segmented pill navigation bar."""

    def __init__(
        self,
        parent: tk.Widget,
        tabs: List[Tuple[str, str]],  # List of (tab_id, label_text)
        on_tab_change: Callable[[str], None],
        initial_tab: Optional[str] = None,
        bg: Optional[str] = None,
    ) -> None:
        bg = bg or theme.BG_NAV
        super().__init__(parent, bg=bg, padx=4, pady=4, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_NAV)
        self.tabs = tabs
        self.on_tab_change = on_tab_change
        self.active_tab = initial_tab or (tabs[0][0] if tabs else "")
        self.buttons = {}

        self._build_pills()

    def _build_pills(self) -> None:
        for tab_id, label in self.tabs:
            is_active = (tab_id == self.active_tab)
            btn = tk.Button(
                self,
                text=label,
                font=theme.FONT_BODY_BOLD if is_active else theme.FONT_BODY,
                bg=theme.ACCENT_PRIMARY if is_active else theme.BG_NAV,
                fg="#ffffff" if is_active else theme.TEXT_MUTED,
                activebackground=theme.ACCENT_PRIMARY_HOVER if is_active else theme.BG_CARD_HOVER,
                activeforeground="#ffffff" if is_active else theme.TEXT_MAIN,
                relief="flat",
                bd=0,
                padx=18,
                pady=7,
                cursor="hand2",
                command=lambda t=tab_id: self.select_tab(t),
            )
            btn.pack(side=tk.LEFT, padx=3)
            self.buttons[tab_id] = btn

    def select_tab(self, tab_id: str) -> None:
        if tab_id == self.active_tab:
            return
        self.active_tab = tab_id
        for tid, btn in self.buttons.items():
            is_active = (tid == tab_id)
            btn.configure(
                bg=theme.ACCENT_PRIMARY if is_active else theme.BG_NAV,
                fg="#ffffff" if is_active else theme.TEXT_MUTED,
                font=theme.FONT_BODY_BOLD if is_active else theme.FONT_BODY,
            )
        self.on_tab_change(tab_id)


class SettingRow(tk.Frame):
    """A modern web-app card row with icon, title, description, and an action widget."""

    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        title: str,
        description: str,
        control_widget: Optional[tk.Widget] = None,
        bg: Optional[str] = None,
    ) -> None:
        bg = bg or theme.BG_CARD
        super().__init__(parent, bg=bg, padx=16, pady=12, bd=1, relief="solid", highlightthickness=1, highlightbackground=theme.BORDER_COLOR)
        self.pack(fill=tk.X, pady=4)

        # Right: Action control container (packed first to guarantee right alignment)
        self.right_box = tk.Frame(self, bg=bg)
        self.right_box.pack(side=tk.RIGHT, padx=(16, 0))

        # Left: Icon & Text
        self.left_box = tk.Frame(self, bg=bg)
        self.left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        header_row = tk.Frame(self.left_box, bg=bg)
        header_row.pack(anchor="w")

        tk.Label(
            header_row,
            text=icon,
            font=(theme.FONT_FAMILY, 14),
            bg=bg,
            fg=theme.ACCENT_CYAN,
        ).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            header_row,
            text=title,
            font=theme.FONT_BODY_BOLD,
            bg=bg,
            fg=theme.TEXT_MAIN,
        ).pack(side=tk.LEFT)

        tk.Label(
            self.left_box,
            text=description,
            font=theme.FONT_CAPTION,
            bg=bg,
            fg=theme.TEXT_MUTED,
            wraplength=480,
            justify=tk.LEFT,
        ).pack(anchor="w", padx=(28, 0), pady=(2, 0))

        if control_widget:
            self.set_control(control_widget)

    def set_control(self, widget: tk.Widget) -> None:
        """Safely attach any control widget inside this card's right box."""
        if widget.master != self and widget.master != self.right_box:
            widget.pack(in_=self.right_box, side=tk.RIGHT)
        else:
            widget.pack(side=tk.RIGHT)

    def add_switch(
        self,
        variable: Optional[tk.BooleanVar] = None,
        command: Optional[Callable[[bool], None]] = None,
    ) -> ModernSwitch:
        """Create and embed an interactive ModernSwitch directly inside this row."""
        switch = ModernSwitch(self.right_box, variable=variable, command=command, bg=self["bg"])
        switch.pack(side=tk.RIGHT)
        return switch


class ScrollableFrame(tk.Frame):
    """A modern, responsive scrollable container with automatic scrollbar and mousewheel support.

    If the content fits completely within the viewable area, the scrollbar automatically hides.
    If the content height exceeds the window, a clean scrollbar appears and the entire tab can be
    scrolled effortlessly using mouse wheel, trackpad, or scrollbar dragging.
    """

    def __init__(
        self,
        parent: tk.Widget,
        bg: Optional[str] = None,
        *args,
        **kwargs,
    ) -> None:
        bg = bg or theme.BG_CARD
        super().__init__(parent, bg=bg, *args, **kwargs)
        self.bg = bg

        self.canvas = tk.Canvas(
            self,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        self.scrollbar = ttk.Scrollbar(
            self,
            orient=tk.VERTICAL,
            command=self.canvas.yview,
        )
        self.content = tk.Frame(self.canvas, bg=bg)

        self._window_id = self.canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content.bind("<Configure>", self._on_content_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Mousewheel interception across the scrollable container and all child widgets
        self.bind_all("<MouseWheel>", self._on_mousewheel, add="+")
        self.bind_all("<Button-4>", self._on_mousewheel, add="+")
        self.bind_all("<Button-5>", self._on_mousewheel, add="+")

    def _on_mousewheel(self, event) -> None:
        if not self.winfo_exists() or not self.winfo_ismapped():
            return
        try:
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
            curr = widget
            while curr:
                if curr == self or curr == self.canvas or curr == self.content:
                    if getattr(event, "num", None) == 4:
                        self.canvas.yview_scroll(-1, "units")
                    elif getattr(event, "num", None) == 5:
                        self.canvas.yview_scroll(1, "units")
                    elif getattr(event, "delta", None):
                        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                    return
                curr = getattr(curr, "master", None)
        except Exception:
            pass

    def _check_scrollbar(self) -> None:
        try:
            bbox = self.canvas.bbox("all")
            if not bbox:
                return
            content_height = bbox[3] - bbox[1]
            canvas_height = self.canvas.winfo_height()
            if content_height > canvas_height and canvas_height > 10:
                if not self.scrollbar.winfo_ismapped():
                    self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                if self.scrollbar.winfo_ismapped():
                    self.scrollbar.pack_forget()
        except Exception:
            pass

    def _on_content_configure(self, event=None) -> None:
        try:
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            self._check_scrollbar()
        except Exception:
            pass

    def _on_canvas_configure(self, event) -> None:
        try:
            # Sync inner content frame width with canvas viewport width
            self.canvas.itemconfig(self._window_id, width=event.width)
            self._check_scrollbar()
        except Exception:
            pass

    def scroll_to_top(self) -> None:
        """Scroll the canvas back to the top position."""
        try:
            self.canvas.yview_moveto(0.0)
        except Exception:
            pass


class ScrollableTab(ScrollableFrame):
    """A tab container integrated directly into the window's master full-page scroll.

    Avoids nested scrollbars while maintaining full API compatibility.
    """

    def __init__(self, parent: tk.Widget, bg: Optional[str] = None, *args, **kwargs) -> None:
        bg = bg or theme.BG_CARD
        tk.Frame.__init__(self, parent, bg=bg, *args, **kwargs)
        self.content = self
        self.bg = bg

    def scroll_to_top(self) -> None:
        """Handled by the master full-page scroll container."""
        pass


