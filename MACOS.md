# macOS Port Considerations

macOS has **Spaces** (Mission Control) — the direct equivalent of Windows Virtual Desktops. The dashboard, HTTP server, JSON storage, and system tray would all port cleanly. The only platform-specific layer is detection.

## The core problem: no public API

Windows exposes `IVirtualDesktopManager` as a documented COM interface (wrapped by `pyvda`). macOS has no equivalent public API. The practical approach is private CoreGraphics session functions that have been present since OS X Leopard and remain in current macOS releases:

```python
import ctypes

cgs = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')

def get_current_space():
    connection = cgs.CGSMainConnectionID()
    space_id   = cgs.CGSGetActiveSpace(connection)
    return f"Space {space_id}"
```

`CGSGetActiveSpace` and `CGSMainConnectionID` are private symbols — reliable in practice but could be removed by Apple without notice. There is no maintained Python library equivalent to `pyvda` for macOS Spaces.

## Space names

Unlike Windows, where desktop names are readable via the API, macOS Space names set in Mission Control are only stored in `~/Library/Preferences/com.apple.spaces.plist`. Reading this at runtime is fragile (the format has changed across OS versions) and unavailable to sandboxed apps. The most practical approach is showing `Space 1`, `Space 2`, etc. derived from the integer Space ID.

## Platform-specific pieces to replace

| Concern | Windows | macOS |
| --- | --- | --- |
| Current desktop | `pyvda` → `IVirtualDesktopManager` COM | `CGSGetActiveSpace` via ctypes |
| Idle time | `GetLastInputInfo` (ctypes/win32) | `IOKit` `IOHIDGetParameter` or `NSWorkspace.idleTime` via PyObjC |
| Lock detection | `OpenDesktop`/`SwitchDesktop` (ctypes/win32) | `NSWorkspace` `sessionDidResignActive` notification |
| Low-level calls | `ctypes.windll` | `ctypes.cdll` + macOS frameworks |

## Recommended implementation approach

Abstract the platform-specific calls behind a small bridge interface so `tracker.py` stays unchanged:

```
tracker.py
platform/
  __init__.py      # imports the right bridge based on sys.platform
  bridge_win.py    # current Windows implementation
  bridge_mac.py    # macOS implementation
```

`tracker.py` would call `get_desktop_name()`, `get_idle_time()`, and `is_locked()` from the bridge rather than calling Windows APIs directly. The HTTP server, JSON storage, pystray tray icon, and entire frontend need no changes.

## Alternative Tracking Strategies

Because the macOS Spaces API is private and Space IDs are opaque integers, there are a few approaches worth considering that either work around the API entirely or make the mapping problem more manageable.

---

### Option 1 — Config file Space mapping

The simplest workaround: ship a `spaces.json` alongside the app that maps Space IDs to friendly names. The user fills it in once and the tracker uses it at runtime.

```json
{
  "3": "Work",
  "5": "Personal",
  "8": "Media"
}
```

The tracker falls back to `Space {id}` for any unmapped ID. The main weakness is that Space IDs are **not guaranteed to be stable across reboots** — they can be reassigned when macOS rebuilds the Spaces graph. This makes the config file a maintenance burden rather than a one-time setup.

---

### Option 2 — Interactive registration from the tray

A better UX than editing a file: add a **"Name this Space…"** item to the system tray menu. When the user selects it, the tracker captures the current Space ID and prompts for a name. The mapping is stored in `spaces.json` automatically.

```
Tray menu
├── Open Dashboard
├── Name this Space…   ← captures CGSGetActiveSpace() right now
└── Quit
```

This turns the one-time calibration into an intentional user action rather than file editing, and the mapping can be updated at any time by revisiting a Space and re-naming it.

---

### Option 3 — App-to-context mapping (no Space API at all)

The most macOS-native approach: **stop tracking Spaces entirely** and instead track which application is in the foreground. The user defines named contexts as lists of applications:

```json
{
  "Work":     ["Xcode", "Terminal", "Slack", "Figma"],
  "Personal": ["Safari", "Messages", "Music"],
  "Admin":    ["Mail", "Calendar"]
}
```

`NSWorkspace.didActivateApplicationNotification` (fully public API) fires whenever the frontmost app changes. The tracker looks up the active app name against the config and credits the matching context.

This has some real advantages over Space tracking on macOS:

- Uses only public APIs — no private symbols, no Gatekeeper/sandbox concerns
- More semantically meaningful (what you're doing matters more than which desktop tile you're on)
- A context can span multiple Spaces (e.g., Terminal on both your Work and Dev Spaces counts as "Work")
- Survives reboots and macOS updates with no reconfiguration

The trade-off: it requires the user to categorise their apps upfront, and any app not in the config goes to an "Other" bucket.

---

### Option 4 — Notification-driven detection with minimal private API use

Rather than polling `CGSGetActiveSpace` every second, the tracker can use the **fully public** `NSWorkspaceActiveSpaceDidChangeNotification` for timing and only call the private function at the exact moment of a transition:

```python
from AppKit import NSWorkspace, NSWorkspaceActiveSpaceDidChangeNotification

def on_space_change(notification):
    space_id = cgs.CGSGetActiveSpace(cgs.CGSMainConnectionID())
    # credit the previous Space, start timer for new one

NSWorkspace.sharedWorkspace().notificationCenter().addObserver_selector_name_object_(
    observer, 'onSpaceChange:', NSWorkspaceActiveSpaceDidChangeNotification, None
)
```

This is more efficient than polling (event-driven rather than once-per-second), and the private `CGSGetActiveSpace` call only happens on Space switches rather than continuously. If Apple ever removes the symbol, the fallback is graceful — the notification still fires, you just lose the Space ID.

---

### Option 5 — Window probe (no direct Space API at all)

The most creative approach: instead of asking macOS "which Space am I on?", use Desktop Tracker's own windows to answer the question indirectly.

The idea: at startup, create one small invisible utility window per known Space and pin each to its Space using `NSWindowCollectionBehaviorManaged` (which keeps a window from following you as you switch). When `NSWorkspaceActiveSpaceDidChangeNotification` fires, query which of your own probe windows is currently on the active display area using `NSWindow.isOnActiveSpace` — a **fully public** property added in macOS 10.9.

```python
# pseudo-code
for probe in space_probes:
    if probe.window.isOnActiveSpace():
        current_space_name = probe.name
        break
```

This requires the user to do a one-time "place a probe on each Space" setup step (similar to Option 2), but after that, the running detection uses zero private APIs. The probe windows are 1×1 pixels, fully transparent, and never receive focus.

---

### Recommendation

| Approach | API risk | User setup | Name quality |
| --- | --- | --- | --- |
| Config file mapping | Private (polling) | Manual file edit | User-defined |
| Tray registration | Private (on-demand) | Click per Space | User-defined |
| App-context mapping | None (fully public) | List apps per context | User-defined |
| Notification + private | Low (on-demand only) | Click per Space | User-defined |
| Window probe | None (fully public) | Click per Space | User-defined |

For a first macOS release, **Option 2 (tray registration) or Option 3 (app-context mapping)** are the most practical. Option 3 is the most forward-compatible since it carries no private API risk at all.

---

## Build Pipeline Considerations

The current `build.yml` is Windows-only. Extending it for macOS requires changes across every step.

### Runner and architecture

```yaml
runs-on: macos-latest   # ARM64 (Apple Silicon) as of macos-14
```

GitHub's `macos-latest` is now Apple Silicon (M1). The last Intel runner is `macos-13`. To ship a single binary that runs on both:

```
pyinstaller --target-arch universal2 ...
```

This requires a universal Python build (available from `python.org` installers). The `setup-python` action does not provide a universal Python by default, so building universal binaries in CI is non-trivial — the simpler path is two separate matrix jobs and two release artifacts (`DesktopTracker-macOS-arm64` and `DesktopTracker-macOS-x64`).

### App bundle, not a single file

On macOS, PyInstaller without `--onefile` produces a `.app` bundle, which is the standard distribution format. Using `--onefile` produces a plain Unix binary with no extension — functional but unconventional. The `.app` bundle is preferred:

```
pyinstaller --windowed --icon=icon.icns --name "DesktopTracker" tracker.py
```

`--windowed` is the macOS equivalent of `--noconsole` and is required for the app to run without a terminal window.

### Icon format

macOS requires `.icns`, not `.ico`. The `.icns` file can be generated from the existing `icon.png` during the build step using built-in macOS tools:

```bash
mkdir icon.iconset
sips -z 16 16   icon.png --out icon.iconset/icon_16x16.png
sips -z 32 32   icon.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32   icon.png --out icon.iconset/icon_32x32.png
sips -z 64 64   icon.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128 icon.png --out icon.iconset/icon_128x128.png
sips -z 256 256 icon.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256 icon.png --out icon.iconset/icon_256x256.png
sips -z 512 512 icon.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512 icon.png --out icon.iconset/icon_512x512.png
iconutil -c icns icon.iconset
```

### Info.plist entries

For a background tray app, the bundle's `Info.plist` needs `LSUIElement = true` so the app does not appear in the Dock. PyInstaller accepts an `--osx-bundle-identifier` flag and a custom `Info.plist` can be injected via a `.spec` file:

```python
# DesktopTracker.spec (relevant section)
app = BUNDLE(
    exe,
    name='DesktopTracker.app',
    icon='icon.icns',
    info_plist={
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    },
)
```

### Dependencies

`pyvda` is Windows-only and must be excluded from the macOS install step. `pystray` on macOS depends on `pyobjc-framework-Cocoa`, which it lists as a dependency and installs automatically. The macOS bridge would additionally need `pyobjc-framework-ApplicationServices` for CoreGraphics access:

```yaml
- name: Install Dependencies (macOS)
  run: |
    python -m pip install --upgrade pip
    pip install pyinstaller pystray Pillow pyobjc-framework-ApplicationServices
```

### Data file path

The current code writes `desktop_data.json` next to `sys.executable`. Inside a `.app` bundle, `sys.executable` resolves to `DesktopTracker.app/Contents/MacOS/DesktopTracker` — a path inside the read-only bundle. This will silently fail to write on macOS.

The data path needs to fall back to a user-writable location when the bundle directory is not writable:

```python
import sys, os

if sys.platform == 'darwin' and getattr(sys, 'frozen', False):
    data_dir = os.path.expanduser('~/Library/Application Support/DesktopTracker')
    os.makedirs(data_dir, exist_ok=True)
else:
    data_dir = application_path

DATA_FILE = os.path.join(data_dir, 'desktop_data.json')
```

### Code signing and Gatekeeper

Without a code signature, macOS Gatekeeper blocks the app on first launch. Options in increasing order of effort:

| Approach | Result |
| --- | --- |
| No signature | "App is damaged and can't be opened" (quarantine attribute from download) |
| Ad-hoc signature (`codesign --sign -`) | Removes the damaged error; still shows "unidentified developer" warning |
| Developer ID certificate + notarization | Passes Gatekeeper silently; requires Apple Developer account ($99/year) |

Ad-hoc signing is achievable in CI at no cost and removes the worst user experience:

```bash
codesign --force --deep --sign - dist/DesktopTracker.app
```

Users can also clear the quarantine attribute manually: `xattr -d com.apple.quarantine DesktopTracker.app`

### Shell syntax

The existing workflow uses Windows-specific shell commands. The macOS equivalent steps use standard bash:

```yaml
- name: Prepare Release Folder
  run: |
    mkdir Release
    cp -r dist/DesktopTracker.app Release/
    cp index.html icon.png Release/

- name: Zip Release
  run: |
    cd Release && zip -r ../DesktopTracker-macOS.zip .
```

### Auto-start equivalent

`install_autostart.bat` has no macOS equivalent. macOS uses a **LaunchAgent** plist placed in `~/Library/LaunchAgents/`. A small shell script shipped with the release could install it:

```xml
<!-- ~/Library/LaunchAgents/com.desktoptracker.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
  <key>Label</key>           <string>com.desktoptracker</string>
  <key>ProgramArguments</key><array><string>/Applications/DesktopTracker.app/Contents/MacOS/DesktopTracker</string></array>
  <key>RunAtLoad</key>       <true/>
</dict>
</plist>
```

### Matrix strategy (both platforms)

```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
```

With a matrix build, platform-specific steps (icon conversion, shell commands, PyInstaller flags, release packaging) would be gated with `if: runner.os == 'macOS'` / `if: runner.os == 'Windows'` conditions.

---

## Summary

A macOS port is feasible with moderate effort. The main trade-off compared to the Windows version is that Space detection relies on a private API and Space names are numeric rather than user-defined strings. Everything else — tracking loop, data format, dashboard — is cross-platform already.
