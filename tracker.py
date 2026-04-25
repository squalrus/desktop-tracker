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

# --- NEW: Path Resolution for PyInstaller ---
# This ensures the app always looks in the folder where the .exe lives
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Change the working directory so the web server finds index.html
os.chdir(application_path)

# Configuration
DATA_FILE = os.path.join(application_path, "desktop_data.json")
ICO_FILENAME = os.path.join(application_path, "icon.ico")
PORT = 8000
IDLE_THRESHOLD_SECONDS = 300 

tracking_active = True

# ... (keep the rest of your script exactly the same below this line) ...