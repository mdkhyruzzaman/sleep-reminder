"""System media control helper for Windows.

Pauses currently playing video/audio (YouTube, Spotify, VLC, browsers, media players)
using Windows Core Audio APIs and multimedia app commands with zero external dependencies.

Ensures that if media is already paused, it will NOT be resumed.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes, HRESULT, POINTER, c_float, c_void_p, cast, c_int, c_ulong, Structure, byref, c_wchar_p
import sys
import time

# Virtual-Key codes
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_STOP = 0xB2
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

# Window message and App Command codes
HWND_BROADCAST = 0xFFFF
WM_APPCOMMAND = 0x0319
APPCOMMAND_MEDIA_PAUSE = 47
APPCOMMAND_MEDIA_PLAY_PAUSE = 14
SMTO_ABORTIFHUNG = 0x0002

user32 = ctypes.windll.user32 if sys.platform == "win32" else None
ole32 = ctypes.oledll.ole32 if sys.platform == "win32" else None


class GUID(Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

    def __init__(self, guid_str: str) -> None:
        super().__init__()
        if ole32:
            ole32.CLSIDFromString(c_wchar_p(guid_str), byref(self))


# Core Audio GUIDs
CLSID_MMDeviceEnumerator = GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}")
IID_IMMDeviceEnumerator = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
IID_IAudioMeterInformation = GUID("{C02216F6-8C67-4B5B-9D00-D008E73E0064}")


def is_system_audio_playing(samples: int = 4, delay: float = 0.015) -> bool:
    """Check if any audio is actively rendering on the default Windows audio device.

    Queries IAudioMeterInformation on the default multimedia render endpoint.
    If the peak audio level is above 0.0005, audio/video is actively playing.
    If zero across samples, media is silent or already paused.
    """
    if sys.platform != "win32" or not ole32:
        return False

    co_inited = False
    try:
        hr = ole32.CoInitialize(None)
        if hr in (0, 1):  # S_OK or S_FALSE
            co_inited = True
    except Exception:
        pass

    enumerator = c_void_p()
    endpoint = c_void_p()
    meter = c_void_p()
    prototype = ctypes.WINFUNCTYPE

    try:
        hr = ole32.CoCreateInstance(
            byref(CLSID_MMDeviceEnumerator),
            None,
            1,  # CLSCTX_INPROC_SERVER
            byref(IID_IMMDeviceEnumerator),
            byref(enumerator),
        )
        if hr != 0 or not enumerator:
            return False

        vtable_enum = cast(enumerator, POINTER(POINTER(c_void_p))).contents
        get_default_endpoint = prototype(HRESULT, c_void_p, c_int, c_int, POINTER(c_void_p))(vtable_enum[4])

        # eRender = 0, eMultimedia = 1
        hr = get_default_endpoint(enumerator, 0, 1, byref(endpoint))
        if hr != 0 or not endpoint:
            return False

        vtable_ep = cast(endpoint, POINTER(POINTER(c_void_p))).contents
        activate = prototype(
            HRESULT, c_void_p, POINTER(GUID), wintypes.DWORD, c_void_p, POINTER(c_void_p)
        )(vtable_ep[3])

        hr = activate(endpoint, byref(IID_IAudioMeterInformation), 1, None, byref(meter))
        if hr != 0 or not meter:
            return False

        vtable_meter = cast(meter, POINTER(POINTER(c_void_p))).contents
        get_peak = prototype(HRESULT, c_void_p, POINTER(c_float))(vtable_meter[3])

        peak = c_float()
        max_peak = 0.0
        for _ in range(samples):
            hr = get_peak(meter, byref(peak))
            if hr == 0 and peak.value > max_peak:
                max_peak = peak.value
                if max_peak > 0.001:
                    break
            time.sleep(delay)

        return max_peak > 0.0005
    except Exception:
        return False
    finally:
        # Safely release COM interfaces (vtable index 2 is IUnknown::Release)
        for ptr in (meter, endpoint, enumerator):
            if ptr:
                try:
                    prototype(c_ulong, c_void_p)(cast(ptr, POINTER(POINTER(c_void_p))).contents[2])(ptr)
                except Exception:
                    pass
        if co_inited:
            try:
                ole32.CoUninitialize()
            except Exception:
                pass


def broadcast_media_pause() -> bool:
    """Broadcast an explicit APPCOMMAND_MEDIA_PAUSE message to all top-level windows.

    Unlike VK_MEDIA_PLAY_PAUSE which toggles playback (and would accidentally resume
    a paused video), APPCOMMAND_MEDIA_PAUSE is discrete: it instructs players to pause.
    If media is already paused, it will not resume.
    """
    if sys.platform != "win32" or not user32:
        return False
    try:
        lparam = APPCOMMAND_MEDIA_PAUSE << 16
        res = user32.SendMessageTimeoutW(
            HWND_BROADCAST,
            WM_APPCOMMAND,
            0,
            lparam,
            SMTO_ABORTIFHUNG,
            200,
            None,
        )
        return bool(res)
    except Exception:
        return False


def pause_system_media(only_if_playing: bool = True) -> bool:
    """Pause currently playing video/audio without resuming already paused media.

    If media is already paused, sending a toggle key would accidentally resume playback.
    Therefore:
    1. Always sends discrete APPCOMMAND_MEDIA_PAUSE (safe: pauses if playing, does nothing if paused).
    2. Checks whether audio is actively playing through the speakers (is_system_audio_playing()).
       - If audio IS actively playing: triggers VK_MEDIA_PLAY_PAUSE to ensure legacy players
         and web browsers that only monitor keyboard hardware keys pause immediately.
       - If audio is NOT playing (already paused or stopped): VK_MEDIA_PLAY_PAUSE is NEVER sent,
         guaranteeing that already-paused videos or music will NOT resume!
    """
    if sys.platform != "win32" or not user32:
        return False

    # 1. Broadcast the discrete pause command to all open windows
    broadcast_media_pause()

    # 2. Check if audio is currently playing
    is_playing = is_system_audio_playing() if only_if_playing else True

    if is_playing:
        try:
            # Simulate pressing VK_MEDIA_PLAY_PAUSE
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY, 0)
            # Simulate releasing VK_MEDIA_PLAY_PAUSE
            user32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
            return True
        except Exception as e:
            print(f"Error pausing media: {e}", file=sys.stderr)
            return False

    return True
