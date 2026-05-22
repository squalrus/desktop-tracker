# Contributing to Desktop Tracker

This document covers the technical architecture, local development setup, and build pipeline for contributors.

---

## How It Works

| File | Purpose |
| --- | --- |
| `tracker.py` | Main script. Spawns a tracking thread and an HTTP server thread, then runs the system tray icon on the main thread. All BambooHR API calls are proxied through this server. |
| `index.html` | Static dashboard served locally. Renders day, week, and month views with SVG charts, desktop filter, per-desktop hour targets, and BambooHR sync. All rendering is client-side. |
| `desktop_data.json` | Date-keyed JSON storing tracked seconds per desktop. Written every 5 seconds. Created automatically on first run. |
| `bamboohr_config.json` | BambooHR credentials, desktop→project mappings, time rounding preference, and sync history (entry IDs per date for re-sync). Created when settings are first saved. |
| `install_autostart.bat` | Writes a `.vbs` launcher to `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` so `DesktopTracker.exe` starts silently on login. |
| `icon.png` / `icon.ico` / `icon.svg` | App icons. `icon.png` is tried first for the system tray (RGBA transparency); `icon.ico` is the fallback. `icon.png` is also the browser favicon. |
| `.github/workflows/build.yml` | Builds `DesktopTracker.exe` via PyInstaller on every push to `main` and publishes a GitHub Release with the bundled ZIP. |
| `test_routing.py` | HTTP API smoke tests for the BambooHR routing layer. Run while the tracker is running. |
| `CHANGELOG.md` | Full history of changes by build. |
| `MACOS.md` | Research notes on a potential macOS port — Spaces API situation, alternative detection strategies, build pipeline considerations. |

---

## Key Implementation Details

**Tracker core**
- The HTTP server binds to `127.0.0.1` only (not `0.0.0.0`) to avoid Windows Firewall prompts.
- Idle detection uses the Win32 `GetLastInputInfo` API via `ctypes`. `GetTickCount64` (64-bit) is used to avoid a 32-bit overflow after ~49 days of uptime.
- Lock detection uses `OpenDesktop`/`SwitchDesktop`; the desktop handle is released in a `finally` block to prevent leaks.
- A named Windows mutex (`DesktopTrackerMutex`) prevents two instances from running simultaneously — a second launch opens the existing dashboard instead.
- `tracking_data` is held in memory and written to `desktop_data.json` every 5 seconds. A final flush is performed before the process exits.

**HTTP routing**
- `QuietHandler` extends `SimpleHTTPRequestHandler`. Requests to `/api/*` are intercepted and dispatched to handler methods; everything else falls through to static file serving.
- All logs are suppressed — `pythonw.exe` crashes if it tries to print to a missing console.

**BambooHR proxy**
- All BambooHR API calls are made server-side to avoid CORS restrictions. The API key is stored in `bamboohr_config.json` and never sent to the browser; the config endpoint masks it as `****`.
- The employee ID is resolved automatically from the API key on the first sync via `GET /v1/employees/0?fields=id`.
- Re-syncing a day deletes the previous BambooHR entries (stored by ID in `bamboohr_config.json`) before creating new ones.

**Dashboard**
- Desktop colours are assigned alphabetically once per render cycle so each desktop maps to the same colour across all three sections.
- The desktop filter (`activeFilter` Set) is applied at the data level before any aggregation, so charts, cards, totals, and target progress all reflect the filtered view consistently.
- Hour targets are stored in `localStorage` under the key `dt_target`. Target type, exclude-weekends, and per-desktop values all live in one object.
- When packaged as a PyInstaller `--onefile` exe, `os.path.dirname(sys.executable)` locates all adjacent files (`index.html`, `desktop_data.json`, etc.) relative to the `.exe`.
- `icon.png` is converted to RGBA mode before being passed to pystray; without this, the tray renders a solid background on Windows.

---

## Run from Source

**Prerequisites:** Windows 10 or 11, Python 3.x with "Add Python to PATH" checked.

```bash
git clone https://github.com/squalrus/desktop-tracker.git
cd desktop-tracker
pip install pyvda pystray Pillow
python tracker.py
```

**Run the API smoke tests** (while `tracker.py` is running in a separate terminal):

```bash
python test_routing.py
```

---

## Build Pipeline

Every push to `main` triggers `.github/workflows/build.yml`, which:

1. Installs Python 3.11 and dependencies (`pyinstaller pyvda pystray Pillow`)
2. Builds `DesktopTracker.exe` with PyInstaller (`--onefile --noconsole --collect-all pyvda`)
3. Bundles `DesktopTracker.exe`, `index.html`, `icon.png`, `icon.ico`, and `install_autostart.bat` into a ZIP
4. Creates a GitHub Release tagged `build-{run_number}` with the ZIP attached

The job requires `permissions: contents: write` to allow release creation via `GITHUB_TOKEN`.

---

## Future Considerations

- **macOS port** — macOS has Spaces (equivalent to Windows Virtual Desktops) but no public API for detecting the current Space. See [MACOS.md](MACOS.md) for research notes and alternative approaches including app-context mapping and window probe strategies.
- **BambooHR auto-sync** — a background thread to sync the previous day automatically each morning. Config fields (`auto_sync`, `auto_sync_hour`) are already stored in `bamboohr_config.json`. See the deferred items section in [MACOS.md](MACOS.md) for context.
- **BambooHR bulk sync** — sync all unsynced days in one action rather than one day at a time.
- **Minimum tracked time threshold** — configurable option to skip desktop entries under a set number of minutes per day.

---

## Contributing

- Keep changes focused — one concern per PR
- The API layer has smoke tests in `test_routing.py`; if you add or change an endpoint, add a test case
- Run `python test_routing.py` with the tracker running and confirm all tests pass before submitting
- Check the [issues page](../../issues) before opening a new one
