"""
Quick smoke-test for Step 1: verifies the /api/ routing layer works and
that static file serving is still intact. Run while tracker.py is running.

Usage:  python test_routing.py
"""
import urllib.request
import urllib.error
import json
import sys

BASE = "http://127.0.0.1:8000"

def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return r.status, json.loads(r.read())

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
    print(f"{'PASS' if ok else 'FAIL'}  {label}  (got {actual}, expected {expected})")
    return ok

passed = True

# Static serving still works
try:
    with urllib.request.urlopen(BASE + "/index.html") as r:
        passed &= check("GET /index.html → 200",       r.status, 200)
except Exception as e:
    print(f"FAIL  GET /index.html → error: {e}")
    passed = False

# Known API routes return 501 (stub) not 404
status, _ = get("/api/bamboohr/config");    passed &= check("GET  /api/bamboohr/config   → 501", status, 501)
status, _ = post("/api/bamboohr/config");   passed &= check("POST /api/bamboohr/config   → 501", status, 501)
status, _ = get("/api/bamboohr/projects");  passed &= check("GET  /api/bamboohr/projects → 501", status, 501)
status, _ = post("/api/bamboohr/sync");     passed &= check("POST /api/bamboohr/sync     → 501", status, 501)

# Unknown API route returns 404
status, _ = get("/api/unknown");            passed &= check("GET  /api/unknown           → 404", status, 404)

print("\nAll tests passed." if passed else "\nSome tests failed.")
sys.exit(0 if passed else 1)
