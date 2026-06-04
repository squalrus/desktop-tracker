# Desktop Tracker — Claude Code Guide

## What this project is

A lightweight Windows tray app that silently tracks time spent per Virtual Desktop and serves a local browser dashboard at `http://localhost:8000`. No accounts, no cloud, no installers beyond copying a folder.

## Key files

| File | Role |
| --- | --- |
| `tracker.py` | Single Python script — tracking thread, HTTP server thread, tray icon on the main thread. All BambooHR API calls are proxied here. |
| `index.html` | Self-contained dashboard. All rendering is client-side vanilla JS + SVG. No build step. |
| `desktop_data.json` | Runtime data store — `{ "YYYY-MM-DD": { "Desktop Name": seconds } }`. Written every 5 seconds and on exit. |
| `bamboohr_config.json` | BambooHR credentials, desktop→project/task mappings, rounding preference, synced-entry IDs per date. |
| `test_routing.py` | HTTP smoke tests for the API layer. Run while the tracker is running. |
| `.github/workflows/build.yml` | PyInstaller build + GitHub Release on every push to `main`. |

## Architecture rules

- **`data_lock`** must be held for every read or write of `tracking_data`. The tracker thread increments every second; `_post_adjust` mutates directly under the same lock; the 5-second flush uses it too. Never write to `tracking_data` outside the lock.
- **HTTP routing** — `QuietHandler` extends `SimpleHTTPRequestHandler`. Add new endpoints to the `routes` dict in `_dispatch`. Never print or log — `pythonw.exe` crashes when writing to a missing console.
- **BambooHR API calls** always go server-side via `bamboohr_request()`. The API key never leaves the backend.
- **`_post_config` field whitelist** at tracker.py line ~234 — if you add a new config field that the frontend saves, add it to this tuple or it will be silently dropped.
- **PyInstaller path resolution** — use `application_path` (not `__file__`) for any file read/write adjacent to the exe.

## API endpoints

| Method | Path | Handler |
| --- | --- | --- |
| `GET` | `/api/bamboohr/config` | Returns config; API key masked as `****` |
| `POST` | `/api/bamboohr/config` | Saves whitelisted fields; sending `****` as key preserves stored value |
| `GET` | `/api/bamboohr/projects` | Proxies `time_tracking/employees/{id}/projects` from BambooHR |
| `POST` | `/api/bamboohr/sync` | Bulk sync a date; deletes previous entries first; body: `{"date":"YYYY-MM-DD"}` |
| `POST` | `/api/adjust` | Move minutes between desktops; body: `{"date","from","to","minutes"}` |

## BambooHR integration notes

- Employee ID is resolved once via `GET /v1/employees/0?fields=id` and cached in `bamboohr_config.json`.
- Sync uses `POST /v1/time_tracking/hour_entries/store` (bulk, one call per day).
- Delete on re-sync uses `POST /v1/time_tracking/hour_entries/delete` with `{"hourEntryIds":[...]}`.
- Projects endpoint: `GET /v1/time_tracking/employees/{id}/projects` — returns `[{id, name, tasks:[{id,name}]}]`.
- Mappings store `{projectId: int, taskId?: int}`. A bare integer is accepted for backward compat on read.
- Projects that have a non-empty `tasks` array **require** `taskId` in the entry body — BambooHR returns `400 MISSING_DATA` otherwise.
- See `BAMBOOHR.md` for full design decisions and deferred features.

## Dashboard notes

- Desktop color palette is assigned alphabetically at render time — same color across all three views.
- `activeFilter` (a `Set`) is applied before aggregation everywhere: charts, cards, totals, target progress all stay in sync automatically.
- Hour targets live in `localStorage` under `dt_target` — no backend involved.
- Bar chart `renderBarChart(container, days, compact)` — each day object carries `{label, totals, isSelected, target, isPast}`. Per-bar green ticks show daily target; missed past bars are faded to 45% opacity.
- Donut chart accepts an optional `target` (seconds) — shows `of Xh · NN%` and turns green when met.

## Running locally

```bash
pip install pyvda pystray Pillow
python tracker.py
# dashboard at http://localhost:8000

# API smoke tests (separate terminal, tracker must be running):
python test_routing.py
```

## Building

Push to `main` — GitHub Actions runs PyInstaller and publishes a release ZIP automatically.

## What NOT to do

- Do not add `print()` or `logging` output anywhere in `tracker.py` — the process runs without a console under `pythonw.exe`.
- Do not write to `desktop_data.json` directly from a handler without holding `data_lock` — the tracker thread increments every second.
- Do not add new config fields to the frontend POST without also adding them to the `_post_config` whitelist in `tracker.py`.

## Working with the backlog

[BACKLOG.md](./BACKLOG.md) tracks proposed work. Items are candidates, not commitments.

When shipping a backlog item: branch off `main` as `vX.Y.Z`, move the entry to CHANGELOG.md, bump `version` in package.json, build, commit, push. Do not open a PR.
