# 🌙 Windows Sleep Reminder Application

> An escalating bedtime reminder and PC shutdown assistant for Windows built with pure Python. Configurable to any bedtime, it alerts you when it's time to sleep and persistently repeats warnings at decreasing intervals (+30 min, +15 min, +10 min, then every 5 min) until you shut down your device.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://microsoft.com/windows)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero%20External-emerald.svg)](https://docs.python.org/3/library/)
[![Tests](https://img.shields.io/badge/Tests-24%20Passing-success.svg)](tests/)

---

## ⚡ Key Features

- **🌙 Custom Windows Taskbar & Titlebar Icon**: Custom multi-resolution icon (`.ico` and `.png`) featuring a luminous golden crescent moon with sparkling night stars. Integrates with Windows `AppUserModelID` (`SetCurrentProcessExplicitAppUserModelID`) so the Windows Taskbar and Alt+Tab switcher display the dedicated night icon instead of the generic Python executable icon.
- **📜 Responsive Scrollable Viewports**: Seamless mousewheel and trackpad scrolling across all dashboard tabs (`ScrollableFrame`). Automatically detects content overflow on any display (including 768p laptop displays or high-DPI scaling) and provides an auto-hiding scrollbar so no buttons or settings ever get clipped.

- **⏸️ Smart Video & Audio Pause (Never Resumes)**: Automatically detects if media is actively playing using Windows Core Audio hardware metering. Only pauses running videos or music (YouTube, Spotify, VLC, Netflix); if videos are already paused or stopped, it strictly leaves them paused and never accidentally resumes playback.
- **🖥️ Full Screen Ambient Reminder**: Displays an immersive, full-screen starry night alert with dynamic urgency glow, a real-time ticking clock, sleep science guidance, and easy escape (`Esc` key or close button).
- **🎨 Modern Web-App Dashboard UI**: Sleek dark card dashboard styled like modern SaaS tools (Linear, Raycast), with glowing status pills, live digital clock, segmented pill tabs, and real-time countdown hero.
- **⏰ Hero Bedtime Reminder Setup Studio**:
  - **Large Digital Clock Numerals (32pt)** for `HOUR` and `MINUTE`.
  - **Single-Click `▲` and `▼` Steppers** with smooth wrapping and auto-save.
  - **Interactive AM / PM Pills**: Instant toggle between morning and evening.
  - **Quick Delta Buttons**: `[-30m]`, `[-15m]`, `[+15m]`, `[+30m]` for instant micro-adjustments.
  - **Sleep Recovery Duration Calculator**: Real-time rest calculation (`9.0h Rest / 6 REM Cycles`).
  - **Bedtime Preset Chips**: Quick one-touch presets (`9:00 PM`, `9:30 PM`, `10:00 PM ⭐`, `10:30 PM`, `11:00 PM`, `11:30 PM`, `12:00 AM`).
  - **Real-Time Dynamic Timeline Ladder**: Exact wall-clock timestamps for tonight's alerts (`10:00 PM`, `10:30 PM`, `10:45 PM`, `10:55 PM`, `11:00 PM`).
  - **Modern Switch Cards**: iOS/Linear-style pill toggles replacing old checkboxes.
- **🔄 Escalating Reminder Schedule**:
  - **Bedtime Alert (Stage 0)**: Triggers at your scheduled bedtime ($T_{\text{bedtime}}$).
  - **Stage 1 Warning**: If the PC is still running after **30 minutes** ($T_{\text{bedtime}} + 30\text{m}$).
  - **Stage 2 Alert**: If still running after **15 minutes** ($T_{\text{bedtime}} + 45\text{m}$).
  - **Stage 3 Urgent**: If still running after **10 minutes** ($T_{\text{bedtime}} + 55\text{m}$).
  - **Stage 4+ Critical**: Repeats **every 5 minutes** ($+60\text{m}, +65\text{m}, +70\text{m}\dots$) until the device is shut down!
- **🛑 Windows Power Integration**:
  - **Shut Down PC**: Initiates a Windows shutdown with an interactive 30-second cancellation safety countdown.
  - **Sleep / Suspend PC**: Immediately puts Windows to sleep with one click.
  - **Snooze / Dismiss**: Postpones until the next scheduled interval.
- **💻 Native Windows System Tray**: Runs unobtrusively in the Windows taskbar notification area using pure Win32 `ctypes` (no external libraries needed). Double-click to restore, right-click for quick settings or pause.
- **🚀 Autostart on Boot**: Optional toggle to start automatically on Windows login.
- **🎵 In-Memory Procedural Chimes**: Soothing harmonic chimes generated dynamically using pure Python mathematics (`wave` + `winsound`), with zero audio files needed.
- **🧠 90-Minute REM Sleep Cycle Calculator**: Built-in sleep science calculator recommending optimal sleep cycles (6 cycles / 9h, 5 cycles / 7.5h, 4 cycles / 6h).
- **🛡️ 100% Standard Library**: Built entirely on Python's built-in libraries (`tkinter`, `ctypes`, `winsound`, `json`, `datetime`, `subprocess`). No `pip install` required!

---

## 🚀 Quick Start

### 1. Requirements
- Windows 10 or Windows 11
- Python 3.10+ (tested on Python 3.14 on Windows)

### 2. Launch the App (1-Click Silent Auto-Startup)
Double-click **`launch.vbs`** in the project folder:
* **Runs completely silently** in 0.1s (no black command window flash).
* **Automatic Auto-Run on Boot**: Once launched, Sleep Reminder automatically registers with Windows so it automatically runs in the background whenever your laptop powers on. You do not need to manually launch it every day!

To create a convenient desktop shortcut with the moon icon:
* Double-click **`create_shortcut.bat`**.

### 3. Stop / Exit the Application
* **Method A**: Right-click the crescent moon icon in the Windows System Tray (near the clock) and click **Exit**.
* **Method B**: Double-click **`stop.bat`** to immediately stop the app and disable auto-run on boot.

---

## 🧪 Running Unit Tests

Run the full automated test suite (24 tests covering scheduling, interval escalation, power actions, smart media pause, scrollable views, custom taskbar icon, configuration, and UI):

```powershell
python -m unittest discover -s tests -v
```

---

## 📂 Project Architecture & Developer Guide

> For a complete visual UI-to-code mapping and deep-dive technical reference, see **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)**.

```
sleep-reminder/
├── main.py                     # Main application launcher
├── run.py                      # Alternative entry point
├── run.bat                     # Windows batch double-click runner
├── README.md                   # Documentation
├── sleep_reminder/
│   ├── __init__.py             # Package exports
│   ├── app.py                  # App bootstrapper & CLI arguments
│   ├── config.py               # User settings and JSON persistence
│   ├── scheduler.py            # Escalating timer engine (+30m, +15m, +10m, +5m)
│   ├── power.py                # Windows shutdown, abort, and sleep actions
│   ├── autostart.py            # Windows Registry Run key manager
│   ├── tray.py                 # Pure Win32 ctypes system tray integration
│   ├── audio.py                # Procedural harmonic bell chime synthesizer
│   ├── history.py              # Sleep streak and consistency habit log
│   ├── sleep_math.py           # 90-minute REM cycle calculations & countdowns
│   └── ui/
│       ├── __init__.py         # UI exports
│       ├── theme.py            # Midnight dark theme palette and styles
│       ├── modal.py            # Escalating bedtime popup with power controls
│       ├── toast.py            # Non-intrusive floating desktop notification
│       └── main_window.py      # Primary settings dashboard and countdown
└── tests/
    ├── test_config.py          # Configuration and interval ladder tests
    ├── test_scheduler.py       # Escalating timer and checkpoint tests
    ├── test_sleep_math.py      # Sleep cycle arithmetic tests
    └── test_ui.py              # Modal, power actions, and window tests
```

---

## 📄 License

MIT License. Free to use, adapt, and build upon.
