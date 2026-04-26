# Windows Virtual Desktop Time Tracker

A lightweight, background productivity tool that monitors how much time you spend on each Windows Virtual Desktop. It quietly logs your usage from the Windows System Tray and visualizes your daily statistics on a clean, responsive, locally-hosted web dashboard.

This is perfect for freelancers, remote workers, or anyone looking to separate their "Work" desktop context from their "Personal" desktop context natively within Windows.

<img width="1002" height="330" alt="image" src="https://github.com/user-attachments/assets/c003c0c8-310d-4d88-b6ee-e57aa0bdf6ac" />

## ✨ Features

- **System Tray Integration:** Runs silently in the background. Access the dashboard or quit the app directly from your Windows taskbar.
- **Smart Idle Detection:** Automatically stops tracking if you haven't touched your mouse or keyboard in 5 minutes, or if your Windows machine is locked, ensuring highly accurate data.
- **Historical Data & CSV Export:** Use the built-in calendar to view previous days' usage. Export your entire history to a `.csv` file with a single click for invoicing or personal analytics.
- **Privacy First:** All data is stored locally in a simple `desktop_data.json` file. No cloud syncing, no accounts.
- **Real-time Dashboard:** A local web interface that updates automatically every 10 seconds, featuring visual percentage bars and precise time readouts (e.g., `2h 15m 30s`).
- **Automatic Dark Mode:** The dashboard instantly matches your system or browser's Light/Dark mode preference.

---

## ⚡ Quick Start (No technical experience needed)

1. Go to the [Releases page](../../releases) and download the latest `DesktopTracker-Windows` ZIP.
2. Unzip it and move the folder to `C:\Program Files\DesktopTracker`.
3. Double-click `DesktopTracker.exe` to start the tracker. A small icon will appear near your clock. If Windows shows a security warning, click **More info → Run anyway**.
4. Double-click `install_autostart.bat` so the tracker starts automatically every time you log in.

To open your dashboard, double-click the tray icon or visit `http://localhost:8000` in any browser.

---

## 🚀 Option A: Pre-Built Executable (No Python Required)

The easiest way to get started. Every push to `main` automatically builds a standalone `DesktopTracker.exe` via GitHub Actions — no Python installation needed.

### 1. Download the Latest Build

Go to the [Releases page](../../releases) and download the latest `DesktopTracker-Windows` ZIP.

### 2. Extract the ZIP

Unzip the artifact. You will find:

```text
DesktopTracker.exe
index.html
icon.png
icon.ico
install_autostart.bat
```

Keep all files together in the same folder — the `.exe` serves `index.html` as the dashboard and reads/writes `desktop_data.json` in the same directory.

### 3. Run It

Double-click `DesktopTracker.exe`. A tray icon will appear near your clock.

- **Double-click** the tray icon to open the dashboard, or navigate to `http://localhost:8000`.
- **Right-click → Quit** to exit cleanly.

### 4. Auto-Start (Optional)

Double-click `install_autostart.bat`. It will add a silent launcher to your Windows Startup folder so `DesktopTracker.exe` starts automatically on every login with no terminal window.

To remove auto-start: press `Win + R`, type `shell:startup`, and delete `DesktopTracker.vbs`.

---

## 🐍 Option B: Run from Source (Python)

Use this method if you want to modify the code or prefer running directly with Python.

### Prerequisites

- **Operating System:** Windows 10 or Windows 11
- **Python:** Python 3.x installed (ensure **"Add Python to PATH"** is checked during installation)

### Setup

### 1. Clone the Repository

```bash
git clone https://github.com/squalrus/desktop-tracker.git
cd desktop-tracker
```

### 2. Install Dependencies

```bash
pip install pyvda pystray Pillow
```

### 3. Run the Tracker

```bash
python tracker.py
```

A tray icon will appear near your clock. Double-click it to open the dashboard, or navigate to `http://localhost:8000`.

### Auto-Start (Recommended)

To have the tracker start automatically and invisibly every time you log into Windows:

1. Locate `install_autostart.bat` in the project folder.
2. Double-click to run it.

A command prompt will briefly appear confirming a silent launcher (`DesktopTracker.vbs`) has been added to your Windows Startup folder. The tracker will now start invisibly on every login with no terminal window.

To remove auto-start: press `Win + R`, type `shell:startup`, and delete `DesktopTracker.vbs`.

---

## 🛠️ How It Works

| File | Purpose |
| --- | --- |
| `tracker.py` | Main script. Spawns a tracking thread (pyvda + ctypes for idle/lock detection) and an HTTP server thread, then runs the System Tray icon on the main thread. |
| `index.html` | Static frontend served locally. Fetches `desktop_data.json`, formats times, renders progress bars, and handles CSV export — all client-side. |
| `desktop_data.json` | Date-keyed JSON storing raw tracked seconds per desktop. Written to disk every 5 seconds to minimize I/O. Created automatically on first run. |
| `install_autostart.bat` | Writes a `.vbs` file to `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` that silently launches `DesktopTracker.exe` on login. |
| `icon.png` / `icon.ico` | Application icons. `icon.png` is loaded first for the system tray (RGBA transparency); `icon.ico` is the fallback. `icon.png` is also used as the browser tab favicon. |
| `.github/workflows/build.yml` | GitHub Actions workflow that builds `DesktopTracker.exe` with PyInstaller on every push to `main`, then publishes a GitHub Release with the files attached. |

**Key implementation details:**

- The HTTP server binds to `127.0.0.1` (not `0.0.0.0`) to avoid Windows Firewall prompts.
- Idle detection uses the Win32 `GetLastInputInfo` API. If idle time exceeds 5 minutes, tracking pauses automatically.
- Lock detection uses `OpenDesktop`/`SwitchDesktop` to check if the workstation is locked.
- When packaged as an `.exe` via PyInstaller, path resolution uses `sys.executable` so all files are found relative to the `.exe` rather than the script.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](../../issues).

## 📝 License

This project is open source and available under the MIT License.
