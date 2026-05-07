# Contributing to Desktop Tracker

This document covers the technical architecture, local development setup, and build pipeline for contributors.

---

## How It Works

| File | Purpose |
| --- | --- |
| `tracker.py` | Main script. Spawns a tracking thread and an HTTP server thread, then runs the system tray icon on the main thread. All BambooHR API calls are proxied through this server. |
| `index.html` | Static dashboard served locally. Renders day, week, and month views with SVG charts, a BambooHR settings panel, and a sync button. All rendering is client-side. |
| `desktop_data.json` | Date-keyed JSON storing tracked seconds per desktop. Written every 5 seconds. Created automatically on first run. |
| `bamboohr_config.json` | BambooHR credentials, desktop→project mappings, time rounding preference, and sync history. Created when the user first saves settings. |
| `install_autostart.bat` | Writes a `.vbs` launcher to the Windows Startup folder so `DesktopTracker.exe` starts silently on login. |
| `icon.png` / `icon.ico` / `icon.svg` | Application icons. `icon.png` is used for the system tray (RGBA, tried first), `icon.ico` is the fallback. `icon.png` is also the browser tab favicon. |
| `.github/workflows/build.yml` | GitHub Actions workflow that builds `DesktopTracker.exe` via PyInstaller on every push to `main` and publishes a GitHub Release. |
| `test_routing.py` | Smoke tests for the HTTP API layer. Run while the tracker is running. |
| `BAMBOOHR.md` | Design decisions and implementation notes for the BambooHR integration. |
| `MACOS.md` | Research notes on a potential macOS port. |

---

## Key Implementation Details

- **HTTP routing** — `QuietHandler` extends `SimpleHTTPRequestHandler`. Requests to `/api/*` are intercepted and dispatched to handler methods; everything else falls through to static file serving.
- **Server binding** — binds to `127.0.0.1` only, not `0.0.0.0`, to avoid Windows Firewall prompts.
- **Idle detection** — uses the Win32 `GetLastInputInfo` API via `ctypes`. Uses `GetTickCount64` (64-bit) to avoid a 32-bit overflow after ~49 days of uptime.
- **Lock detection** — uses `OpenDesktop`/`SwitchDesktop` to check if the workstation is locked.
- **Duplicate instance guard** — a named Windows mutex (`DesktopTrackerMutex`) prevents two instances from running simultaneously. A second launch opens the existing dashboard instead.
- **Data persistence** — tracking data is held in memory and written to `desktop_data.json` every 5 seconds. On clean exit, a final flush is performed before the process terminates.
- **Path resolution** — when packaged as a PyInstaller `--onefile` exe, `sys.executable` points to the `.exe` file, so `os.path.dirname(sys.executable)` correctly locates adjacent files (`index.html`, `desktop_data.json`, etc.).
- **Icon transparency** — `icon.png` is loaded and converted to RGBA mode before being passed to pystray. Without explicit RGBA conversion, pystray renders the tray icon with a solid background.
- **BambooHR proxy** — all BambooHR API calls are made server-side to avoid CORS restrictions. The API key is stored in `bamboohr_config.json` and never sent to the browser; the config endpoint masks it as `****`.

---

## Run from Source

**Prerequisites:** Windows 10 or 11, Python 3.x with "Add Python to PATH" checked.

```bash
git clone https://github.com/squalrus/desktop-tracker.git
cd desktop-tracker
pip install pyvda pystray Pillow
python tracker.py
```

**Run the API smoke tests** (while `tracker.py` is running):

```bash
python test_routing.py
```

---

## Build Pipeline

Every push to `main` triggers `.github/workflows/build.yml`, which:

1. Builds `DesktopTracker.exe` with PyInstaller (`--onefile --noconsole --collect-all pyvda`)
2. Bundles `DesktopTracker.exe`, `index.html`, `icon.png`, `icon.ico`, and `install_autostart.bat` into a ZIP
3. Publishes a GitHub Release with the ZIP attached, tagged `build-{run_number}`

Builds require `permissions: contents: write` on the job to allow release creation via the `GITHUB_TOKEN`.

---

## Future Considerations

- **macOS port** — macOS has Spaces (equivalent to Windows Virtual Desktops) but no public API for detecting the current Space. See [MACOS.md](MACOS.md) for research notes and alternative approaches.
- **BambooHR auto-sync** — a background thread that syncs the previous day automatically each morning. Config fields (`auto_sync`, `auto_sync_hour`) are already in place. See [BAMBOOHR.md](BAMBOOHR.md) for details.
- **BambooHR bulk sync** — sync all unsynced days in one action rather than one day at a time.
- **Minimum time threshold** — configurable option to skip desktop entries under a set number of minutes.

---

## Contributing

Contributions, issues, and feature requests are welcome. Please check the [issues page](../../issues) before opening a new one.

When submitting a pull request:
- Keep changes focused — one concern per PR
- The existing code has no test suite beyond `test_routing.py`; if you add a feature that touches the API layer, add a test case there
- Run `python test_routing.py` and confirm all tests pass before submitting
