import time
import json
import os
import sys
import ctypes
import threading
import webbrowser
import http.server
import socketserver
from datetime import date
from pyvda import VirtualDesktop
import pystray
from PIL import Image, ImageDraw

# Path resolution for PyInstaller: look in the folder where the .exe lives,
# not the temp extraction directory.
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)

# Configuration
DATA_FILE            = os.path.join(application_path, "desktop_data.json")
BAMBOOHR_CONFIG_FILE = os.path.join(application_path, "bamboohr_config.json")
PNG_FILENAME         = os.path.join(application_path, "icon.png")
ICO_FILENAME         = os.path.join(application_path, "icon.ico")
PORT = 8000
IDLE_THRESHOLD_SECONDS = 300

tracking_active = True
tracking_data = {}
data_lock = threading.Lock()

# Set up GetTickCount64 once at module level to avoid 32-bit wraparound after ~49 days.
_GetTickCount64 = ctypes.windll.kernel32.GetTickCount64
_GetTickCount64.restype = ctypes.c_uint64

# --- Duplicate instance guard ---
def acquire_instance_mutex():
    """Returns a Windows named mutex, or None if another instance is already running."""
    ERROR_ALREADY_EXISTS = 183
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "DesktopTrackerMutex")
    if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        if mutex:
            ctypes.windll.kernel32.CloseHandle(mutex)
        return None
    return mutex

# --- Windows API Helpers ---
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def get_idle_time():
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = _GetTickCount64() - lii.dwTime
    return millis / 1000.0

def is_computer_locked():
    user32 = ctypes.windll.User32
    DESKTOP_SWITCHDESKTOP = 0x0100
    hDesktop = user32.OpenDesktopW("default", 0, False, DESKTOP_SWITCHDESKTOP)
    if hDesktop:
        result = user32.SwitchDesktop(hDesktop)
        user32.CloseDesktop(hDesktop)
        return not result
    return True

# --- Data Management ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass  # Corrupted or unreadable — start fresh
    return {}

def save_data(data):
    # Direct write is more reliable on Windows than tempfile+os.replace, which
    # can raise PermissionError if the file is momentarily held by antivirus or
    # the HTTP server.
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except OSError:
        pass

# --- HTTP handler with API routing ---
class QuietHandler(http.server.SimpleHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress all HTTP logs — pythonw.exe crashes when it tries to print
        # to a missing console.
        pass

    # Route GET requests: /api/* goes to the API layer; everything else is
    # served as a static file by SimpleHTTPRequestHandler.
    def do_GET(self):
        if self.path.split('?')[0].startswith('/api/'):
            self._dispatch('GET')
        else:
            super().do_GET()

    # Route POST requests: only /api/* is expected; anything else gets 405.
    def do_POST(self):
        if self.path.split('?')[0].startswith('/api/'):
            self._dispatch('POST')
        else:
            self._send_json(405, {'error': 'Method not allowed'})

    def _dispatch(self, method):
        path = self.path.split('?')[0]
        routes = {
            ('GET',  '/api/bamboohr/config'):   self._get_config,
            ('POST', '/api/bamboohr/config'):   self._post_config,
            ('GET',  '/api/bamboohr/projects'): self._get_projects,
            ('POST', '/api/bamboohr/sync'):     self._post_sync,
        }
        handler = routes.get((method, path))
        if handler:
            handler()
        else:
            self._send_json(404, {'error': 'Not found'})

    # ── Shared helpers ────────────────────────────────────────────────────

    def _read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode())

    def _send_json(self, status, data):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── API endpoint stubs (implemented in Steps 2–5) ─────────────────────

    def _get_config(self):
        self._send_json(501, {'error': 'Not implemented'})

    def _post_config(self):
        self._send_json(501, {'error': 'Not implemented'})

    def _get_projects(self):
        self._send_json(501, {'error': 'Not implemented'})

    def _post_sync(self):
        self._send_json(501, {'error': 'Not implemented'})

def tracker_loop():
    loop_count = 0
    while tracking_active:
        try:
            if not is_computer_locked() and get_idle_time() < IDLE_THRESHOLD_SECONDS:
                today = str(date.today())
                with data_lock:
                    if today not in tracking_data:
                        tracking_data[today] = {}
                    try:
                        current = VirtualDesktop.current()
                        name = current.name if current.name else f"Desktop {current.number}"
                        tracking_data[today][name] = tracking_data[today].get(name, 0) + 1
                    except Exception:
                        pass
        except Exception:
            pass  # Prevent any Windows API failure from killing the thread

        time.sleep(1)
        loop_count += 1
        if loop_count >= 5:
            with data_lock:
                save_data(tracking_data)
            loop_count = 0

def server_loop():
    socketserver.TCPServer.allow_reuse_address = True
    # Bind to 127.0.0.1 explicitly to avoid Windows Firewall silent blocks.
    with socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
        while tracking_active:
            httpd.handle_request()

# --- System Tray Functions ---
def load_icon_image():
    # PNG is tried first — pystray handles PNG alpha channels more reliably than
    # ICO on Windows. Both are converted to RGBA so the tray renders transparency
    # correctly; without RGBA mode, pystray renders a solid background.
    for filename in [PNG_FILENAME, ICO_FILENAME]:
        if os.path.exists(filename):
            try:
                return Image.open(filename).convert('RGBA')
            except Exception:
                pass

    fallback_image = Image.new('RGBA', (64, 64), color=(255, 0, 0, 255))
    ImageDraw.Draw(fallback_image).rectangle([16, 16, 48, 48], fill="white")
    return fallback_image

def open_dashboard(icon, item):
    # Use 127.0.0.1 to match the server binding and avoid IPv6 ambiguity.
    webbrowser.open(f"http://127.0.0.1:{PORT}")

def exit_action(icon, item):
    with data_lock:
        save_data(tracking_data)
    icon.stop()
    os._exit(0)

def main():
    global tracking_data

    mutex = acquire_instance_mutex()
    if mutex is None:
        # Another instance is already running; open its dashboard instead.
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        sys.exit(0)

    # Load persisted data before threads start to avoid a race with exit_action.
    tracking_data = load_data()

    t_thread = threading.Thread(target=tracker_loop, daemon=True)
    t_thread.start()

    s_thread = threading.Thread(target=server_loop, daemon=True)
    s_thread.start()

    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
        pystray.MenuItem("Quit", exit_action)
    )
    icon = pystray.Icon("DesktopTracker", load_icon_image(), "Desktop Tracker", menu)
    icon.run()

if __name__ == "__main__":
    main()
