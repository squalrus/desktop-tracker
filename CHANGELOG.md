# Changelog

All notable changes to Desktop Tracker are documented here.

---

## [Build 10] — 2026-06-11

### Changed

- **Sync status shows date and time** — the "✓ Synced" / "⚠ Partial" badge in the Day section now displays the full date and time of the last successful sync, not just the time. (`index.html`)

### Fixed

- **Settings date fields stay in sync** — the "Adjust Time" date field in the settings panel now tracks the main date picker (and vice versa) while the settings panel is open, instead of going stale when you navigate to a different day. (`index.html`)
- **Settings calendar icon visible in dark mode** — the date picker icon in the "Adjust Time" field now uses the same lightened filter as the main date picker, so it's no longer invisible against the dark background. (`index.html`)

---

## [Build 9] — 2026-06-09

### Added

- **Add time to desktop** — new Transfer / Add mode toggle in the Adjust Time settings panel. Transfer mode works as before (move minutes from one desktop to another). Add mode lets you inject time directly into any desktop on any date without requiring a tracked source — useful for accounting for offline work. Backed by `POST /api/add-time`. (`tracker.py`, `index.html`)

---

## [Build 8] — 2026-06-04

### Changed

- **Day navigation arrows and Today button** — `‹` and `›` buttons flank the date picker to step backward or forward one day; a "Today" button jumps back to the current date and disables itself automatically when you're already viewing today. (`index.html`)
- **Lighter calendar picker icon** — the calendar icon in the date picker is now visibly lighter via `filter: invert(0.6)`, making it easier to see against the dark card background. (`index.html`)

---

## [Build 7] — May 2026

### Added
- **Per-desktop hour targets** — set an individual hour target per desktop (daily, weekly, or monthly). The other two periods extrapolate automatically via a shared daily rate. Targets are stored in `localStorage` — no backend changes required.
- **Target progress on cards** — each card's progress bar now shows progress toward the desktop's own target (blue while in progress, green when met). Falls back to % of period total when no target is set.
- **Aggregate target bar** — section headers show a combined progress bar for all desktops that have a target, with text: `28h of 38h target · 74% · 10h to go`.
- **Target reference line on bar charts** — a dashed green horizontal line on the week and month bar charts marks the daily target level, filter-aware so it adjusts when you scope to a single desktop.
- **Exclude weekends toggle** — when enabled, Saturday and Sunday are excluded from avg/day, avg/week, tracked-day counts, and target progress calculations. Weekend days still appear in charts but are not counted toward any target.
- **Targets settings** — set per-desktop hour goals via the gear-icon settings panel. Shows one row per known desktop with a number input, a shared period selector, and the exclude-weekends checkbox.
- **Desktop filter dropdown** — multi-select dropdown in the header controls. Filter to one or more desktops; the selection applies simultaneously to day, week, and month views including all cards and charts. Button label updates to reflect the active selection (PR #20).
- **avg/week on month cards** — month cards now show avg/day, avg/week, and tracked-days count on separate lines (PR #21).
- **macOS port research** — `MACOS.md` documents the Spaces API situation, five alternative Space-detection strategies (config mapping, tray registration, app-context mapping, notification-driven detection, window probe), and build pipeline considerations for a future macOS port.
- **CONTRIBUTING.md** — technical architecture, file reference, build pipeline details, and contributing guidelines.
- **BambooHR integration** — sync tracked desktop time to BambooHR Time Tracking, verified end-to-end against a live BambooHR account.
  - `GET/POST /api/bamboohr/config` — read and write credentials locally (API key masked as `****` in responses)
  - `GET /api/bamboohr/projects` — proxy project list from BambooHR API
  - `POST /api/bamboohr/sync` — sync a selected date; deletes previous entries on re-sync to prevent double-counting; configurable time rounding (15 min default, 6 min, or exact)
  - Settings panel accessible from a gear icon — company domain, API key, per-desktop project + task mapping (task picker appears for projects that require one), rounding preference
  - **Sync to BambooHR** button in the Day section with a status badge (last synced time, partial/full/error state)
  - Employee ID resolved automatically from the API key on first sync
  - See [BAMBOOHR.md](BAMBOOHR.md) for full design notes

### Changed
- `install_autostart.bat` updated to launch `DesktopTracker.exe` directly rather than `pythonw.exe tracker.py` (PR #19).
- HTTP handler extended to support `/api/*` routing alongside existing static file serving — `QuietHandler` now intercepts API paths and falls through to `SimpleHTTPRequestHandler` for everything else.
- **Settings consolidated** — Targets and Export CSV moved from the header into the gear-icon settings panel alongside the BambooHR section. Panel uses a responsive 2-column grid that collapses to one column on narrow viewports.
- **Adjust Time** — new section in the gear settings panel to move minutes from one desktop to another on a given date without stopping the tracker. Backed by `POST /api/adjust`, which mutates `tracking_data` under the same lock the tracker thread uses for its 5-second flushes, so the change survives the next save.
- README restructured — user-facing content in `README.md`; technical detail in `CONTRIBUTING.md`.

---

## [Build 6] — April–May 2026

### Added
- **Day, Week & Month dashboard views** — redesigned layout with three sections, each with a section header, totals, and daily/weekly averages (PR #16).
- **SVG donut chart** — day section shows a ring chart of desktop time split with hover tooltips and total time in the centre.
- **Stacked bar charts** — week and month sections each have a stacked bar chart with a legend. The selected day is highlighted with a blue underline.
- **Redesigned cards** — coloured left border accent per desktop, large hero time value, slim 5px progress bar, percentage bottom-right. Week/month cards add avg/day and tracked-days metadata.
- **Consistent desktop colour palette** — colours are assigned alphabetically across all three sections so each desktop always maps to the same colour.
- **MIT License** — added `LICENSE` file and attribution footer to the dashboard (PR via `9271422`).

### Changed

- Dashboard screenshot updated.

### Fixed
- **Data loss on quit** — `tracking_data` promoted to module level; `exit_action` acquires the data lock and flushes to disk before calling `os._exit(0)`.
- **Duplicate instance guard** — named Windows mutex (`DesktopTrackerMutex`) prevents two tracker instances from running simultaneously; second launch opens the existing dashboard.
- **Corrupted data file on startup** — `load_data()` now catches `JSONDecodeError` and falls back to `{}` instead of crashing.
- **`GetTickCount` 32-bit overflow** — replaced with `GetTickCount64` (set up at module level with `c_uint64` return type) to prevent incorrect idle-time readings after ~49 days of uptime.
- **`is_computer_locked` handle leak** — `CloseDesktop` now runs in a `finally` block so the handle is always released even if `SwitchDesktop` raises.
- **Print crash in windowless mode** — removed `print()` call in `load_icon_image` that caused `pythonw.exe` to crash when no console is attached.
- **Redundant `ImageDraw` import** — removed local `from PIL import ImageDraw` inside the fallback branch (already imported at module level).
- **Dead code in `exit_action`** — removed `tracking_active = False` assignment that had no effect before `os._exit(0)`.
- **XSS via desktop names** — dashboard cards rebuilt with `document.createElement` + `textContent` instead of `innerHTML` string interpolation.
- **CSV export field quoting** — fields containing commas, quotes, or newlines are now wrapped in double quotes per RFC 4180.
- **CSV download corruption** — replaced `encodeURI(data:...)` with `Blob` + `URL.createObjectURL` to prevent special-character corruption.
- **`innerHTML +=` in render loop** — all card rendering now uses `DocumentFragment` to avoid repeated DOM re-parses.
- **GitHub Release permissions** — added `permissions: contents: write` to the build job to allow `gh release create` via `GITHUB_TOKEN` (PR #9).
- **Icon transparency** — `icon.png` is tried before `icon.ico` for the system tray; both are converted to RGBA mode so transparency renders correctly. Previously pystray rendered a solid background (PR #12).
- **PyInstaller path resolution** — `application_path` uses `os.path.dirname(sys.executable)` when frozen so all adjacent files are found relative to the `.exe` rather than the extraction temp directory.

---

## [Build 4–5] — April 2026

### Added
- **GitHub Actions build pipeline** — `.github/workflows/build.yml` builds `DesktopTracker.exe` via PyInstaller on every push to `main` and publishes a GitHub Release with the bundled ZIP (PR #6, fixed in PR #10, PR #13).
- **Standalone `.exe`** — PyInstaller `--onefile --noconsole --collect-all pyvda` packages the full application into a single executable; no Python installation required.
- **`install_autostart.bat`** — writes a `.vbs` launcher to the Windows Startup folder so the tracker starts silently on login (PR #6).
- **Weekly breakdown** — day view was extended with a Monday–Sunday weekly summary below it (PR #14).
- **Alphabetical desktop ordering** — desktops are sorted A–Z across all views (PR #14).
- **ZIP artifact release** — build workflow updated to bundle all release files into a ZIP before uploading (PR #13).

### Changed
- README updated with detailed installation instructions including auto-start setup (PR #11).
- `.gitignore` updated (PR #11).
- Build artifact renamed to include run number for traceability.

---

## [Early Releases] — April 2026

### Added
- **Initial tracker** (`134eb3f`) — Python script using `pyvda` to detect the active virtual desktop and log seconds per desktop per day to `desktop_data.json`.
- **Lock detection** (PR #1) — `OpenDesktop`/`SwitchDesktop` used to detect workstation lock; tracking pauses automatically when locked.
- **Dark mode** (PR #2) — dashboard auto-matches system light/dark preference via `prefers-color-scheme`.
- **Major dashboard update** (PR #4) — progress bars, percentage readouts, real-time auto-refresh every 10 seconds, date picker for historical data, CSV export.
- **Icon support** (PR #5) — custom `.ico` file applied to the system tray and the PyInstaller executable.
- **Windows API idle detection** (PR #6) — `GetLastInputInfo` added to pause tracking after 5 minutes of inactivity.
- **`icon.svg`** added alongside PNG/ICO for use in the README and dashboard (PR #7).

---

## Notes

- Build numbers correspond to GitHub Actions run numbers visible in the [Releases page](../../releases).
- For technical architecture and contributor setup, see [CONTRIBUTING.md](CONTRIBUTING.md).
- For BambooHR integration design decisions and deferred features, see [BAMBOOHR.md](BAMBOOHR.md).
- For macOS port research, see [MACOS.md](MACOS.md).
