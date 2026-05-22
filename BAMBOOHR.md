# BambooHR Integration

This document covers the design decisions and implementation notes for syncing Desktop Tracker time data into BambooHR's Time Tracking module.

---

## Authentication

BambooHR does not use OAuth. It uses a **per-user API key** generated from each employee's own BambooHR account (Profile → API Keys → Add New Key). Authentication is HTTP Basic with the API key as the username and the literal string `x` as the password.

| Field | Description | Example |
| --- | --- | --- |
| Company domain | The subdomain of your BambooHR account | `mycompany` (from `mycompany.bamboohr.com`) |
| API key | Generated in BambooHR → Profile → API Keys | `abc123def456` |

All API calls use: `https://api.bamboohr.com/api/gateway.php/{companyDomain}/v1/`

The employee ID is resolved automatically from the API key on the first sync (`GET /v1/employees/0?fields=id`) and stored in `bamboohr_config.json`. The user never needs to find it manually.

---

## Why API calls go through the Python backend

BambooHR's API does not support CORS from browser origins. All BambooHR requests are proxied through `tracker.py`. This also keeps the API key server-side only — it is stored on disk and never transmitted to the browser. The GET `/api/bamboohr/config` endpoint masks the key as `****` before returning it to the frontend.

---

## Configuration file

`bamboohr_config.json` is stored alongside `desktop_data.json` in the application directory:

```json
{
  "company_domain": "mycompany",
  "api_key": "abc123def456",
  "employee_id": "42",
  "mappings": {
    "Work":     "PROJECT_ID_A",
    "Dev":      "PROJECT_ID_B",
    "Personal": null
  },
  "synced_dates": {
    "2026-05-01": {
      "status":    "ok",
      "timestamp": "2026-05-01T17:05:00",
      "entry_ids": ["1001", "1002"]
    }
  },
  "rounding":       "15min",
  "auto_sync":      false,
  "auto_sync_hour": 23
}
```

`mappings` maps each known desktop name to a BambooHR project ID, or `null` to skip that desktop. `synced_dates` stores the BambooHR entry IDs from each sync so re-syncing a day can delete them before creating new ones — preventing double-counting.

---

## Decisions made during implementation

| Decision | Outcome |
| --- | --- |
| BambooHR time tracking mode | **Daily Totals** (POST a single hours value per desktop per day) |
| Time rounding | **Configurable** — 15 minutes (default), 6 minutes, or exact decimal |
| Auth mechanism | API key + company domain |
| Where API calls are made | Python backend (CORS prevents browser-side calls) |
| Config storage | `bamboohr_config.json` alongside `desktop_data.json` |
| Default sync mode | Manual button per day |
| Auto-sync | **Deferred** — manual sync via the date picker covers previous days |
| Re-sync behaviour | Delete previous entries by stored ID, then recreate |
| Unmapped desktops | Skip with a confirmation prompt shown before sync |

---

## Time rounding

Three options are configurable in the settings panel:

| Setting | Behaviour | Example |
| --- | --- | --- |
| `15min` (default) | Round to nearest 0.25h | 3h 47m → 3.75h |
| `6min` | Round to nearest 0.1h | 3h 47m → 3.8h |
| `exact` | Four decimal places | 3h 47m → 3.7833h |

Entries that round to exactly zero are skipped.

---

## Data flow

```
desktop_data.json
       │
       ▼
[ Day aggregation ]    ──→  {Work: 14400s, Dev: 7200s, Personal: 3600s}
       │
       ▼
[ Apply mappings ]     ──→  {PROJECT_ID_A: 4.0h, PROJECT_ID_B: 2.0h}  (Personal skipped)
       │
       ▼
[ Delete old entries ] ──→  DELETE /timetracking/employees/{id}/entries/{entryId}  (if re-sync)
       │
       ▼
[ POST to BambooHR ]   ──→  one time entry per mapped desktop
       │
       ▼
[ Write synced_dates ] ──→  store entry IDs + timestamp in bamboohr_config.json
```

Each synced desktop produces one BambooHR time entry:

```json
{
  "date":          "2026-05-02",
  "trackingHours": 4.0,
  "projectId":     "PROJECT_ID_A",
  "note":          "Tracked by Desktop Tracker"
}
```

---

## API endpoints added to tracker.py

`QuietHandler` (which extends `SimpleHTTPRequestHandler`) was extended to intercept `/api/` paths and route them, falling through to static file serving for everything else.

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/bamboohr/config` | Returns config with API key masked as `****` |
| `POST` | `/api/bamboohr/config` | Saves config; sending `****` as the key preserves the stored value |
| `GET` | `/api/bamboohr/projects` | Proxies project list from BambooHR API |
| `POST` | `/api/bamboohr/sync` | Syncs a given date; body: `{"date": "2026-05-02"}` |

---

## Sync sync for previous days

The **Sync to BambooHR** button syncs whichever date is selected in the date picker — today or any past day. Re-syncing a previously submitted day deletes the stored BambooHR entry IDs before posting new ones.

> **Approval workflow caveat:** If your company routes time entries through an approval workflow, re-syncing an already-approved day may require manager-level permissions to delete the old entries. In practice, avoid re-syncing days older than a few days.

---

## Deferred: auto-sync (Step 7)

Auto-sync was designed but not implemented. The intent was a background thread that fires each morning to sync the previous calendar day automatically. It was deferred because:

- Manual sync via the date picker already covers the previous-day case
- Silent auto-sync can submit incorrect data if mappings are wrong, with no user review
- Companies with approval workflows may prefer conscious submission

All config fields for it (`auto_sync`, `auto_sync_hour`) are already in `bamboohr_config.json`, so it can be added later without a schema change.

---

## Open items

- **Minimum time threshold** — entries under ~5 minutes are currently included. A configurable threshold to skip noise would be a small addition.
- **Multi-day bulk sync** — sync all unsynced days with one action. Currently each day requires a separate sync.
- **Approval workflow awareness** — the UI currently has no way to know if a previously synced entry has been approved. Attempting to re-sync an approved entry may fail silently.
