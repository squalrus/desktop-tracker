"""
Smoke-tests for Steps 1 & 2: routing layer + config read/write.
Run while tracker.py is running.

Usage:  python test_routing.py
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"

def get_status(path):
    """Returns just the HTTP status code, works for any content type."""
    try:
        with urllib.request.urlopen(BASE + path) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code

def get(path):
    """GET and parse JSON response body."""
    try:
        with urllib.request.urlopen(BASE + path) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def post(path, body=None):
    data = json.dumps(body or {}).encode()
    req  = urllib.request.Request(BASE + path, data=data,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def check(label, actual, expected):
    ok = actual == expected
    print(f"{'PASS' if ok else 'FAIL'}  {label}  (got {actual!r}, expected {expected!r})")
    return ok

passed = True

print("── Step 1: routing layer ────────────────────────────────────────────")

# Static serving still works (HTML response, not JSON)
status = get_status("/index.html")
passed &= check("GET /index.html              → 200", status, 200)

# Config endpoints: implemented in Step 2, so 200 now
status, _ = get("/api/bamboohr/config")
passed &= check("GET  /api/bamboohr/config   → 200", status, 200)

status, _ = post("/api/bamboohr/config")
passed &= check("POST /api/bamboohr/config   → 200", status, 200)

# Projects and sync: still stubs, so 501
status, _ = get("/api/bamboohr/projects")
passed &= check("GET  /api/bamboohr/projects → 501", status, 501)

status, _ = post("/api/bamboohr/sync")
passed &= check("POST /api/bamboohr/sync     → 501", status, 501)

# Unknown API route returns 404
status, _ = get("/api/unknown")
passed &= check("GET  /api/unknown           → 404", status, 404)

print("\n── Step 2: config read/write ────────────────────────────────────────")

# GET returns expected shape
status, body = get("/api/bamboohr/config")
passed &= check("GET config → 200",                  status, 200)
passed &= check("config has company_domain",          "company_domain" in body, True)
passed &= check("config has mappings",                "mappings"       in body, True)
passed &= check("config has synced_dates",            "synced_dates"   in body, True)

# POST saves and returns masked key
status, body = post("/api/bamboohr/config", {
    "company_domain": "testcorp",
    "api_key":        "supersecret",
})
passed &= check("POST config → 200",                  status, 200)
passed &= check("saved company_domain is testcorp",   body.get("company_domain"), "testcorp")
passed &= check("returned api_key is masked",         body.get("api_key"), "****")

# GET after POST reflects saved domain; key still masked
status, body = get("/api/bamboohr/config")
passed &= check("GET after POST: domain persists",    body.get("company_domain"), "testcorp")
passed &= check("GET after POST: key still masked",   body.get("api_key"), "****")

# Sending **** back does NOT overwrite the real stored key
status, body = post("/api/bamboohr/config", {"api_key": "****"})
passed &= check("POST with **** preserves real key",  body.get("api_key"), "****")

# Clean up test data
post("/api/bamboohr/config", {"company_domain": "", "api_key": "x"})
post("/api/bamboohr/config", {"company_domain": "", "api_key": ""})

print(f"\n{'All tests passed.' if passed else 'Some tests FAILED.'}")
sys.exit(0 if passed else 1)
