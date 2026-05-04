# BambooHR Integration Plan

This document covers the design decisions and implementation plan for syncing Desktop Tracker time data into BambooHR's Time Tracking module. It is intended for review before any code is written.

---

## Authentication

BambooHR does not use OAuth client ID / client secret. It uses a **per-user API key** that each employee generates from their own BambooHR account (Profile → API Keys). Authentication is HTTP Basic with the API key as the username and the literal string `x` as the password.

The two required credentials are:

| Field | Description | Example |
| --- | --- | --- |
| Company domain | The subdomain of your BambooHR account | `mycompany` (from `mycompany.bamboohr.com`) |
| API key | Generated in BambooHR → Profile → API Keys | `abc123def456` |

All API calls use: `https://api.bamboohr.com/api/gateway.php/{companyDomain}/v1/`

The employee ID (`/v1/employees/0?fields=id`) can be resolved automatically from the API key at first connection, so the user does not need to find it manually.

---

## Why API calls must go through the Python backend

BambooHR's API does not support CORS from browser origins, so the dashboard JavaScript cannot call it directly. All BambooHR requests must be proxied through `tracker.py`. This also keeps the API key out of the browser entirely — it is stored on disk and used server-side only, never transmitted to the frontend.

---

## Configuration file

A new `bamboohr_config.json` stored alongside `desktop_data.json`:

```json
{
  "company_domain": "mycompany",
  "api_key": "abc123def456",
  "employee_id": "42",
  "mappings": {
    "Work":    "PROJECT_ID_A",
    "Dev":     "PROJECT_ID_B",
    "Personal": null
  },
  "synced_dates": {
    "2026-05-01": { "status": "ok", "timestamp": "2026-05-01T23:05:00" },
    "2026-05-02": { "status": "ok", "timestamp": "2026-05-02T23:05:00" }
  },
  "auto_sync": false,
  "auto_sync_hour": 23
}
```

`mappings` maps each known desktop name to a BambooHR project ID, or `null` to skip that desktop during sync. `synced_dates` tracks which dates have already been submitted and when, enabling re-sync detection.

The config file is readable only by the local user and never leaves the machine.

---

## Desktop → Project mapping

Each virtual desktop the tracker has ever seen needs to be assignable to a BambooHR project (or explicitly excluded). The project list is fetched from the BambooHR API (`GET /v1/timetracking/projects`) at configuration time and cached locally.

The mapping editor in the dashboard settings panel would show one row per known desktop:

```
Desktop Name     →   BambooHR Project
──────────────────────────────────────
Work             →   [ Client Work ▼ ]
Dev              →   [ Internal Dev ▼ ]
Personal         →   [ — skip — ▼ ]
```

Unmapped desktops (not in the config yet) are skipped during sync with a warning shown to the user.

---

## Sync strategy

### Recommendation: manual button, with optional previous-day auto-sync

**Manual sync** is the right default. Time tracking data submitted to an employer should be reviewed before it is sent — users may want to adjust the desktop→project mapping, exclude personal time, or verify the numbers look correct. A "Sync to BambooHR" button in the Day section header gives explicit control.

**Auto-sync for the previous day** is the right optional enhancement. Rather than syncing mid-day (where data is incomplete), auto-sync would trigger each morning for the *previous* calendar day. By 9 AM, yesterday's data is final and unlikely to change. This setting would be off by default and configurable:

```
Auto-sync: [off]  or  [sync previous day at 09:00 ▼]
```

This avoids the partial-day problem of syncing mid-day while still being hands-free.

### Re-sync behaviour

If the user syncs a day and then more time is tracked (e.g., they sync mid-afternoon and keep working), the next sync should **delete the previous entries and recreate them** rather than appending. The BambooHR entry IDs from the first sync should be stored in `synced_dates` so they can be deleted before the new entries are created.

---

## Data flow

```
desktop_data.json
       │
       ▼
[ Day aggregation ]   ──→  {Work: 14400s, Dev: 7200s, Personal: 3600s}
       │
       ▼
[ Apply mappings ]    ──→  {PROJECT_ID_A: 4.0h, PROJECT_ID_B: 2.0h}  (Personal skipped)
       │
       ▼
[ POST to BambooHR ]  ──→  one time entry per mapped desktop per day
       │
       ▼
[ Write synced_dates ] ──→  record entry IDs + timestamp in bamboohr_config.json
```

Each synced desktop becomes one BambooHR time entry:

```json
{
  "employeeId": "42",
  "date": "2026-05-02",
  "trackingHours": 4.0,
  "projectId": "PROJECT_ID_A",
  "note": "Tracked by Desktop Tracker"
}
```

Hours are rounded to two decimal places. Seconds are not submitted.

---

## Backend changes (tracker.py)

Four new HTTP endpoints served by the existing `SimpleHTTPRequestHandler`, which will need to be replaced with a handler that supports routing:

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/bamboohr/config` | Returns config (API key masked as `****`) |
| `POST` | `/api/bamboohr/config` | Saves updated config to disk |
| `GET` | `/api/bamboohr/projects` | Proxies project list from BambooHR API |
| `POST` | `/api/bamboohr/sync` | Syncs a given date; body: `{"date": "2026-05-02"}` |

`SimpleHTTPRequestHandler` only serves static files. The handler class will need to intercept `/api/` paths and handle them explicitly, falling through to file-serving for everything else.

---

## Frontend changes (index.html)

### Settings panel

A collapsible section (or modal) reachable from a gear icon in the page header:

- Company domain field
- API key field (masked after entry, with a "reveal" toggle)
- "Test connection" button — calls `/api/bamboohr/config` to validate credentials and auto-fill the employee ID
- Project mapping table (one row per known desktop, dropdown per row)
- Auto-sync toggle and time selector

### Day section additions

- **Sync button** in the Day section header: "Sync to BambooHR"
- **Sync status badge**: small indicator showing last sync time for the selected date, or "Not synced" if the date has no entry in `synced_dates`
- **Warning**: if the selected date has unmapped desktops with non-zero time, show a prompt before syncing

---

## Edge cases and open questions

**1. Which BambooHR time tracking mode does the company use?**
BambooHR has two time tracking modes: Clock In/Out (start/end times required) and Daily Totals (just hours). The sync endpoint will differ. This needs to be detected or made configurable. *Decision needed before implementation.*

**2. Timesheet approval workflow**
Some companies require time entries to go through an approval workflow. Programmatically created entries may land in a "pending approval" state. This is the expected behaviour and should be noted in the UI ("Entries submitted — pending manager approval if required").

**3. Time rounding**
Should tracked seconds be rounded to the nearest 6 minutes (0.1h), 15 minutes, or left as precise decimals? BambooHR accepts decimal hours. A rounding setting in the config would give users control. *Decision needed before implementation.*

**4. What happens to desktops with very small amounts of time?**
A desktop with 30 seconds tracked is technically a valid entry but adds noise. A minimum threshold (e.g., skip desktops with less than 5 minutes for the day) should be configurable.

**5. Multi-day sync**
The initial design syncs one day at a time. A "sync all unsynced days" option would be valuable for users who accumulate several days before syncing. This can be added in a follow-up.

**6. `desktop_data.json` is the only data source**
The sync reads from the same file the tracker writes to. If the file is corrupt on the day of a sync, the sync would silently send zero-time entries. The `load_data()` error handling already returns `{}` on corrupt files — the sync should detect an empty result for a date that should have data and warn the user before proceeding.

---

## Implementation sequence (suggested order)

1. **Backend routing** — extend the HTTP handler to support `/api/` routes alongside static file serving
2. **Config read/write endpoints** — `/api/bamboohr/config` GET and POST
3. **Project fetch endpoint** — `/api/bamboohr/projects` with BambooHR proxy call
4. **Settings panel in UI** — credentials, test connection, project mapping editor
5. **Sync endpoint** — `/api/bamboohr/sync` with full data-flow logic
6. **Sync button and status badge in UI** — Day section
7. **Auto-sync (optional)** — background thread checking the configured hour

Steps 1–4 can be reviewed and tested independently before the actual sync (step 5) is built.

---

## Summary

| Decision | Recommendation |
| --- | --- |
| Auth mechanism | API key + company domain (not OAuth) |
| Where API calls are made | Python backend (CORS blocker on browser side) |
| Config storage | `bamboohr_config.json` alongside `desktop_data.json` |
| Default sync mode | Manual button per day |
| Auto-sync | Optional: previous day, triggered each morning |
| Re-sync behaviour | Delete previous entries, recreate |
| Unmapped desktops | Skip with a warning shown before sync |
| Decisions needed before starting | BambooHR time tracking mode (clock in/out vs daily totals), time rounding increment |
