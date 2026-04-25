import time
import json
import os
import ctypes
import threading
import webbrowser
import http.server
import socketserver
from datetime import date
from pyvda import VirtualDesktop
import pystray
from PIL import Image # Pillow library already used for loading

# Configuration
DATA_FILE = "desktop_data.json"
PORT = 8000
IDLE_THRESHOLD_SECONDS = 300  # 5 minutes of no mouse/keyboard input

# New Configuration for External Icons
ICO_FILENAME = "icon.ico" 

tracking_active = True

# --- Windows API Helpers ---
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

def get_idle_time():
    """Returns the system idle time in seconds."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0

def is_computer_locked():
    """Checks if the Windows workstation is currently locked."""
    user32 = ctypes.windll.User32
    OpenDesktop = user32.OpenDesktopW
    SwitchDesktop = user32.SwitchDesktop
    CloseDesktop = user32.CloseDesktop
    DESKTOP_SWITCHDESKTOP = 0x0100
    hDesktop = OpenDesktop("default", 0, False, DESKTOP_SWITCHDESKTOP)
    if hDesktop:
        result = SwitchDesktop(hDesktop)
        CloseDesktop(hDesktop)
        return not result
    return True

# --- Data Management ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- Background Threads ---
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override the default logging to do absolutely nothing. 
        # This prevents pythonw.exe from crashing when it tries to print to a missing console.
        pass

def tracker_loop():
    data = load_data()
    loop_count = 0
    while tracking_active:
        # Check lock state AND idle time
        if not is_computer_locked() and get_idle_time() < IDLE_THRESHOLD_SECONDS:
            today = str(date.today())
            if today not in data:
                data[today] = {}
            try:
                current = VirtualDesktop.current()
                name = current.name if current.name else f"Desktop {current.number}"
                if name not in data[today]:
                    data[today][name] = 0
                data[today][name] += 1
            except Exception:
                pass # Silently fail to avoid crashing if pyvda hiccups
        
        time.sleep(1)
        loop_count += 1
        if loop_count >= 5:
            save_data(data)
            loop_count = 0

def server_loop():
    socketserver.TCPServer.allow_reuse_address = True
    # Bind specifically to localhost (127.0.0.1) to avoid Windows Firewall silent blocks
    with socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler) as httpd:
        while tracking_active:
            httpd.handle_request()

# --- System Tray Functions ---
def load_icon_image():
    """Loads the customized ICO file from disk."""
    if os.path.exists(ICO_FILENAME):
        try:
            return Image.open(ICO_FILENAME)
        except Exception as e:
            print(f"Error loading icon: {e}")
            
    # Fallback: create a generic error image if loading fails
    from PIL import ImageDraw
    fallback_image = Image.new('RGB', (64, 64), color=(255, 0, 0)) # Red
    ImageDraw.Draw(fallback_image).rectangle([16, 16, 48, 48], fill="white")
    return fallback_image

def open_dashboard(icon, item):
    webbrowser.open(f"http://localhost:{PORT}")

def exit_action(icon, item):
    global tracking_active
    tracking_active = False
    icon.stop()
    os._exit(0) # Force close all daemon threads

def main():
    # Start tracking thread
    t_thread = threading.Thread(target=tracker_loop, daemon=True)
    t_thread.start()

    # Start web server thread
    s_thread = threading.Thread(target=server_loop, daemon=True)
    s_thread.start()

    # Start System Tray Icon (This blocks the main thread)
    menu = pystray.Menu(
        pystray.MenuItem("Open Dashboard", open_dashboard, default=True),
        pystray.MenuItem("Quit", exit_action)
    )
    # New: Use the load_icon_image() function
    icon = pystray.Icon("DesktopTracker", load_icon_image(), "Desktop Tracker", menu)
    icon.run()

if __name__ == "__main__":
    main()