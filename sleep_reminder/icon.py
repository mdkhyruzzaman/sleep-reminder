"""Application Icon & Windows Taskbar Manager.

Generates and manages multi-resolution Windows taskbar, window titlebar,
and system tray icons with zero external dependencies.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
from pathlib import Path
import struct
import sys
import tkinter as tk
from typing import Optional, Tuple
import zlib

APP_USER_MODEL_ID = "Antigravity.SleepReminder.App.v2"
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICO_PATH = ASSETS_DIR / "icon.ico"
PNG_PATH = ASSETS_DIR / "icon.png"

_cached_photo_image: Optional[tk.PhotoImage] = None


def render_sleep_pixel(x: int, y: int, w: int, h: int) -> Tuple[int, int, int, int]:
    """Generates a high-contrast glowing crescent moon with night stars."""
    nx = (x + 0.5) / (w / 2.0) - 1.0
    ny = (y + 0.5) / (h / 2.0) - 1.0
    dist = math.sqrt(nx * nx + ny * ny)

    # Circular mask with smooth anti-aliased edge
    if dist > 0.96:
        if dist < 1.02:
            alpha = int(255 * max(0.0, min(1.0, (1.02 - dist) / 0.06)))
            return (11, 17, 32, alpha)
        return (0, 0, 0, 0)

    # Deep space radial gradient background (#0b1120 to #1e1b4b)
    t = dist / 0.96
    bg_r = int(11 * (1 - t) + 17 * t)
    bg_g = int(17 * (1 - t) + 24 * t)
    bg_b = int(32 * (1 - t) + 48 * t)

    # Subtle cyan accent ring around circle border
    if 0.88 <= dist <= 0.95:
        ring_t = 1.0 - abs(dist - 0.915) / 0.035
        bg_r = int(bg_r * (1 - ring_t) + 56 * ring_t)
        bg_g = int(bg_g * (1 - ring_t) + 189 * ring_t)
        bg_b = int(bg_b * (1 - ring_t) + 248 * ring_t)

    # Golden Crescent Moon
    d_out = math.sqrt((nx - (-0.08)) ** 2 + (ny - 0.04) ** 2)
    d_in = math.sqrt((nx - 0.16) ** 2 + (ny - (-0.16)) ** 2)

    moon_edge_out = 0.54 - d_out
    moon_edge_in = d_in - 0.44
    moon_factor = min(moon_edge_out, moon_edge_in) / 0.04
    moon_factor = max(0.0, min(1.0, moon_factor))

    # Stars
    star1_d = math.sqrt((nx - 0.42) ** 2 + (ny - (-0.38)) ** 2)
    star1_shape = abs(nx - 0.42) + abs(ny - (-0.38))
    is_star1 = star1_shape < 0.14 or star1_d < 0.04

    star2_d = math.sqrt((nx - 0.48) ** 2 + (ny - 0.35) ** 2)
    is_star2 = star2_d < 0.05

    star3_d = math.sqrt((nx - (-0.46)) ** 2 + (ny - (-0.46)) ** 2)
    is_star3 = star3_d < 0.035

    if moon_factor > 0:
        m_t = (ny + 0.5) / 1.0
        m_r = int(254 * (1 - m_t) + 245 * m_t)
        m_g = int(240 * (1 - m_t) + 158 * m_t)
        m_b = int(138 * (1 - m_t) + 11 * m_t)
        return (
            int(bg_r * (1 - moon_factor) + m_r * moon_factor),
            int(bg_g * (1 - moon_factor) + m_g * moon_factor),
            int(bg_b * (1 - moon_factor) + m_b * moon_factor),
            255,
        )

    if is_star1:
        s_t = max(0.0, 1.0 - star1_shape / 0.14)
        return (
            int(bg_r * (1 - s_t) + 255 * s_t),
            int(bg_g * (1 - s_t) + 255 * s_t),
            int(bg_b * (1 - s_t) + 255 * s_t),
            255,
        )

    if is_star2:
        s_t = max(0.0, 1.0 - star2_d / 0.05)
        return (
            int(bg_r * (1 - s_t) + 186 * s_t),
            int(bg_g * (1 - s_t) + 230 * s_t),
            int(bg_b * (1 - s_t) + 253 * s_t),
            255,
        )

    if is_star3:
        s_t = max(0.0, 1.0 - star3_d / 0.035)
        return (
            int(bg_r * (1 - s_t) + 186 * s_t),
            int(bg_g * (1 - s_t) + 230 * s_t),
            int(bg_b * (1 - s_t) + 253 * s_t),
            255,
        )

    return (bg_r, bg_g, bg_b, 255)


def make_png(width: int, height: int) -> bytes:
    """Encode an RGBA PNG byte stream using standard library zlib & struct."""
    png = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    ihdr = b"IHDR" + ihdr_data
    png += struct.pack(">I", len(ihdr_data)) + ihdr + struct.pack(">I", zlib.crc32(ihdr) & 0xFFFFFFFF)

    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type None
        for x in range(width):
            raw.extend(render_sleep_pixel(x, y, width, height))

    compressed = zlib.compress(bytes(raw))
    idat = b"IDAT" + compressed
    png += struct.pack(">I", len(compressed)) + idat + struct.pack(">I", zlib.crc32(idat) & 0xFFFFFFFF)

    iend = b"IEND"
    png += struct.pack(">I", 0) + iend + struct.pack(">I", zlib.crc32(iend) & 0xFFFFFFFF)
    return png


def make_bmp_ico_frame(width: int, height: int) -> bytes:
    """Encode a native 32-bit uncompressed DIB frame with XOR and AND masks for Windows GDI."""
    # BITMAPINFOHEADER (40 bytes)
    # biHeight must be height * 2 to account for both XOR and AND masks
    bih = struct.pack(
        "<IIIHHIIIIII",
        40, width, height * 2, 1, 32, 0, width * height * 4, 0, 0, 0, 0
    )
    # XOR pixels (bottom-up BGRA format)
    pixels = bytearray()
    for y in reversed(range(height)):
        for x in range(width):
            r, g, b, a = render_sleep_pixel(x, y, width, height)
            pixels.extend((b, g, r, a))

    # AND mask (1 bit per pixel, bottom-up, row padded to 32-bit boundary)
    row_bytes = ((width + 31) // 32) * 4
    and_mask = bytearray(row_bytes * height)
    for y in reversed(range(height)):
        row_offset = (height - 1 - y) * row_bytes
        for x in range(width):
            _, _, _, a = render_sleep_pixel(x, y, width, height)
            if a < 128:
                and_mask[row_offset + (x // 8)] |= (1 << (7 - (x % 8)))

    return bih + bytes(pixels) + bytes(and_mask)


def make_ico(sizes: list[int]) -> bytes:
    """Encode a multi-resolution Windows ICO container with native DIB frames."""
    frames = [(s, make_bmp_ico_frame(s, s)) for s in sizes]
    ico = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + len(frames) * 16

    for s, data in frames:
        w_b = s if s < 256 else 0
        h_b = s if s < 256 else 0
        ico += struct.pack("<BBBBHHII", w_b, h_b, 0, 0, 1, 32, len(data), offset)
        offset += len(data)

    for s, data in frames:
        ico += data

    return ico


def ensure_icon_files() -> Tuple[str, str]:
    """Ensure both icon.ico and icon.png exist on disk, creating them if necessary."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # Multi-resolution ICO for Win32 Taskbar, System Tray, Alt+Tab, and Window Titlebar
    ico_bytes = make_ico([16, 24, 32, 48, 64])
    ICO_PATH.write_bytes(ico_bytes)

    if not PNG_PATH.exists():
        png_bytes = make_png(256, 256)
        PNG_PATH.write_bytes(png_bytes)

    return str(ICO_PATH), str(PNG_PATH)


def set_windows_app_id() -> None:
    """Register explicit AppUserModelID so Windows Taskbar isolates and groups this app properly."""
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
        except Exception:
            pass


def _apply_win32_taskbar_icon(window: tk.Tk | tk.Toplevel, ico_path: str) -> bool:
    """Send Win32 WM_SETICON and SetClassLongPtrW directly to top-level HWND to force Windows Taskbar update."""
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32
        window.update_idletasks()

        hwnds = set()
        try:
            inner_hwnd = window.winfo_id()
            if inner_hwnd:
                hwnds.add(inner_hwnd)
                parent_hwnd = user32.GetParent(inner_hwnd)
                if parent_hwnd:
                    hwnds.add(parent_hwnd)
        except Exception:
            pass

        try:
            wm_frame = window.wm_frame()
            if wm_frame:
                top_hwnd = int(wm_frame, 16) if wm_frame.startswith("0x") else int(wm_frame)
                if top_hwnd:
                    hwnds.add(top_hwnd)
        except Exception:
            pass

        if not hwnds:
            return False

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCLP_HICON = -14
        GCLP_HICONSM = -34

        h_icon_big = user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        h_icon_small = user32.LoadImageW(0, str(ico_path), IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if not h_icon_big and not h_icon_small:
            return False

        SetClassLong = getattr(user32, "SetClassLongPtrW", getattr(user32, "SetClassLongW", None))
        if SetClassLong:
            SetClassLong.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            SetClassLong.restype = ctypes.c_ssize_t

        for hwnd in hwnds:
            if h_icon_big:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
                if SetClassLong:
                    try:
                        SetClassLong(hwnd, GCLP_HICON, h_icon_big)
                    except Exception:
                        pass
            if h_icon_small:
                user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
                if SetClassLong:
                    try:
                        SetClassLong(hwnd, GCLP_HICONSM, h_icon_small)
                    except Exception:
                        pass

        return True
    except Exception:
        return False


def apply_window_icon(window: tk.Tk | tk.Toplevel) -> None:
    """Apply the custom crescent moon icon to the window titlebar and Windows Taskbar."""
    global _cached_photo_image
    set_windows_app_id()

    try:
        ico_path, png_path = ensure_icon_files()

        if sys.platform == "win32" and Path(ico_path).exists():
            # 1. Native Windows iconbitmap (.ico)
            try:
                window.iconbitmap(ico_path)
            except Exception:
                pass

            # 2. Directly send Win32 WM_SETICON and SetClassLongPtrW to top-level HWND
            # This directly forces the Windows Taskbar button to show the crescent moon icon!
            _apply_win32_taskbar_icon(window, ico_path)

            # Re-assert after window is displayed by Windows DWM
            try:
                window.after(60, lambda: _apply_win32_taskbar_icon(window, ico_path))
            except Exception:
                pass
        else:
            # Linux / macOS fallback using PhotoImage
            if Path(png_path).exists():
                try:
                    if _cached_photo_image is None:
                        _cached_photo_image = tk.PhotoImage(file=png_path)
                    window.iconphoto(True, _cached_photo_image)
                except Exception:
                    pass
    except Exception:
        pass


def get_tray_icon_path() -> Optional[str]:
    """Return the absolute path to the .ico file for Windows system tray icon loading."""
    try:
        ico_path, _ = ensure_icon_files()
        return ico_path
    except Exception:
        return None
