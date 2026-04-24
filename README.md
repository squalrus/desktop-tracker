# Windows Virtual Desktop Time Tracker

A lightweight, background productivity tool that monitors how much time you spend on each Windows Virtual Desktop. It quietly logs your usage from the Windows System Tray and visualizes your daily statistics on a clean, responsive, locally-hosted web dashboard.

This is perfect for freelancers, remote workers, or anyone looking to separate their "Work" desktop context from their "Personal" desktop context natively within Windows.

<img width="1002" height="330" alt="image" src="https://github.com/user-attachments/assets/c003c0c8-310d-4d88-b6ee-e57aa0bdf6ac" />

## ✨ Features

* **System Tray Integration:** Runs silently in the background. Access the dashboard or quit the app directly from your Windows taskbar.
* **Smart Idle Detection:** Automatically stops tracking if you haven't touched your mouse or keyboard in 5 minutes, or if your Windows machine is locked, ensuring highly accurate data.
* **Historical Data & CSV Export:** Use the built-in calendar to view previous days' usage. Export your entire history to a `.csv` file with a single click for invoicing or personal analytics.
* **Privacy First:** All data is stored locally in a simple `desktop_data.json` file. No cloud syncing, no accounts.
* **Real-time Dashboard:** A local web interface that updates automatically every 10 seconds, featuring visual percentage bars and precise time readouts (e.g., `2h 15m 30s`).
* **Automatic Dark Mode:** The dashboard instantly matches your system or browser's Light/Dark mode preference.

---

## 📋 Prerequisites

To run this application, you will need:
* **Operating System:** Windows 10 or Windows 11
* **Python:** Python 3.x installed (ensure **"Add Python to PATH"** is checked during installation).

---

## 🚀 Installation & Setup

**1. Clone or Download the Repository**
```bash
git clone [https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git](https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git)
cd YOUR_REPOSITORY_NAME
```

**2. Install Required Dependencies**

This script relies on libraries to interface with Windows APIs, manage the System Tray, and generate icons. Install them via your command prompt:

```bash
pip install pyvda pystray Pillow
```

---

## ⚙️ Setting Up Auto-Start (Recommended)

To make the tracker feel like a native Windows app, you can set it to run silently in the background as soon as you log into your computer. We've included an automated installer to set this up for you.

Locate the `install_autostart.bat` file in your project folder.

Double-click to run it.

A command prompt will briefly appear to confirm that a silent launcher has been added to your Windows Startup folder.

The tracker will now automatically and invisibly start in your System Tray every time you turn on your PC! (Note: If you ever want to remove this, press Windows Key + R, type `shell:startup`, and delete `DesktopTracker.vbs`).

---

## 💻 Standard Manual Usage

If you prefer not to use the Auto-Start feature and want to run the app manually whenever you need it:

Open a terminal in the project directory and run: `python tracker.py`

A blue icon will appear in your Windows System Tray (near the clock).

Double-click the tray icon to open your dashboard, or manually navigate to `http://localhost:8000` in your browser.

To cleanly exit, right-click the tray icon and select **Quit**.

## 🛠️ How It Works

- `tracker.py`: The master script. It spawns two background threads: one for the local HTTP server, and one for the tracker. The tracker uses pyvda to fetch the active virtual desktop name/number, and `ctypes` to check for workstation locks and system idle time (using `GetLastInputInfo`). It runs entirely from the system tray using `pystray`.

- `desktop_data.json`: A date-keyed dictionary storing your raw tracked seconds. Data is saved in memory and dumped to disk every 5 seconds to minimize writes.

- `index.html`: A static frontend that fetches the JSON data, formats the seconds into readable strings, calculates percentage widths for the progress bars, and dynamically renders the UI. It also handles CSV generation purely on the client side.

- `install_autostart.bat`: A helper script that generates a `.vbs` file in your Windows startup folder. The VBScript forces `tracker.py` to run using `pythonw.exe` (windowless mode) so no terminal windows ever appear on your screen.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page if you want to contribute.

## 📝 License

This project is open source and available under the MIT License.
