"""Pure Win32 ctypes System Tray Integration for Windows.

Provides taskbar notification area icon, right-click context menu,
and balloon notifications with zero external dependencies.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import sys
import threading
from typing import Callable, Optional

from sleep_reminder.icon import get_tray_icon_path

# Win32 Constants
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 20
WM_COMMAND = 0x0111
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002

NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010

NIIF_INFO = 0x00000001

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_RIGHTALIGN = 0x0008
TPM_BOTTOMALIGN = 0x0020
TPM_RETURNCMD = 0x0100

IDI_APPLICATION = 32512
IMAGE_ICON = 1
LR_SHARED = 0x8000

# Menu Command IDs
CMD_OPEN = 1001
CMD_TEST = 1002
CMD_PAUSE = 1003
CMD_EXIT = 1004

user32 = ctypes.windll.user32 if sys.platform == "win32" else None
shell32 = ctypes.windll.shell32 if sys.platform == "win32" else None
kernel32 = ctypes.windll.kernel32 if sys.platform == "win32" else None

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

if user32:
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = LRESULT
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL


class WNDCLASSEX(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HICON),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uTimeoutOrVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class WindowsTrayIcon:
    """Manages system tray icon in the Windows taskbar with zero third-party dependencies."""

    def __init__(
        self,
        tooltip: str = "🌙 Sleep Reminder",
        on_open: Optional[Callable[[], None]] = None,
        on_test: Optional[Callable[[], None]] = None,
        on_pause: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        icon_path: Optional[str] = None,
    ) -> None:
        self.tooltip = tooltip
        self.on_open = on_open
        self.on_test = on_test
        self.on_pause = on_pause
        self.on_exit = on_exit
        self.icon_path = icon_path or get_tray_icon_path()

        self.hwnd: Optional[wintypes.HWND] = None
        self.nid: Optional[NOTIFYICONDATA] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._wndproc_ref = None

    def start(self) -> None:
        """Start the system tray icon message loop in a dedicated background thread."""
        if sys.platform != "win32" or not user32:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_tray_loop, daemon=True, name="TrayThread")
        self._thread.start()

    def stop(self) -> None:
        """Remove tray icon from taskbar and shut down window."""
        self._running = False
        if sys.platform == "win32" and user32 and self.hwnd:
            if self.nid and shell32:
                try:
                    shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
                except Exception:
                    pass
            try:
                user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
            except Exception:
                pass

    def show_balloon(self, title: str, message: str) -> None:
        """Display a Windows notification balloon."""
        if not self.nid or not shell32:
            return
        try:
            self.nid.uFlags |= NIF_INFO
            self.nid.szInfoTitle = title[:63]
            self.nid.szInfo = message[:255]
            self.nid.dwInfoFlags = NIIF_INFO
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))
        except Exception:
            pass

    def update_tooltip(self, text: str) -> None:
        """Update hover tooltip text."""
        self.tooltip = text
        if self.nid and shell32:
            try:
                self.nid.szTip = text[:127]
                shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))
            except Exception:
                pass

    def _run_tray_loop(self) -> None:
        class_name = f"SleepReminderTrayClass_{id(self)}"
        h_inst = kernel32.GetModuleHandleW(None)

        def wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_TRAYICON:
                if lparam in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
                    if self.on_open:
                        self.on_open()
                elif lparam == WM_RBUTTONUP:
                    self._show_context_menu(hwnd)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wndproc_ref = WNDPROC(wndproc)

        wcex = WNDCLASSEX()
        wcex.cbSize = ctypes.sizeof(WNDCLASSEX)
        wcex.lpfnWndProc = self._wndproc_ref
        wcex.hInstance = h_inst
        wcex.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wcex))

        self.hwnd = user32.CreateWindowExW(
            0, class_name, "SleepReminderTrayWindow",
            0, 0, 0, 0, 0, 0, 0, h_inst, None
        )

        # Load custom app icon if available, fallback to system application icon
        LR_LOADFROMFILE = 0x0010
        h_icon = 0
        if self.icon_path:
            try:
                h_icon = user32.LoadImageW(0, str(self.icon_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
            except Exception:
                h_icon = 0
        if not h_icon:
            h_icon = user32.LoadImageW(0, IDI_APPLICATION, IMAGE_ICON, 0, 0, LR_SHARED)

        self.nid = NOTIFYICONDATA()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_TRAYICON
        self.nid.hIcon = h_icon
        self.nid.szTip = self.tooltip[:127]

        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid))

        # Windows message loop
        msg = wintypes.MSG()
        while self._running and user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def _show_context_menu(self, hwnd: wintypes.HWND) -> None:
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        h_menu = user32.CreatePopupMenu()
        user32.AppendMenuW(h_menu, MF_STRING, CMD_OPEN, "⚙️  Open Dashboard")
        user32.AppendMenuW(h_menu, MF_STRING, CMD_TEST, "🔔  Test Bedtime Reminder")
        user32.AppendMenuW(h_menu, MF_STRING, CMD_PAUSE, "⏸️  Pause for Tonight")
        user32.AppendMenuW(h_menu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(h_menu, MF_STRING, CMD_EXIT, "❌  Exit Sleep Reminder")

        user32.SetForegroundWindow(hwnd)
        cmd = user32.TrackPopupMenu(
            h_menu,
            TPM_RIGHTALIGN | TPM_BOTTOMALIGN | TPM_RETURNCMD,
            pt.x,
            pt.y,
            0,
            hwnd,
            None,
        )
        user32.DestroyMenu(h_menu)

        if cmd == CMD_OPEN:
            if self.on_open:
                self.on_open()
        elif cmd == CMD_TEST:
            if self.on_test:
                self.on_test()
        elif cmd == CMD_PAUSE:
            if self.on_pause:
                self.on_pause()
        elif cmd == CMD_EXIT:
            if self.on_exit:
                self.on_exit()
