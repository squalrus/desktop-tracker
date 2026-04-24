import time
import json
import os
import ctypes
from datetime import date
from pyvda import VirtualDesktop

# The file where our data will be saved
DATA_FILE = "desktop_data.json"

def is_computer_locked():
    """Checks if the Windows workstation is currently locked."""
    user32 = ctypes.windll.User32
    OpenDesktop = user32.OpenDesktopW
    SwitchDesktop = user32.SwitchDesktop
    CloseDesktop = user32.CloseDesktop
    
    # Access rights flag required to switch desktops
    DESKTOP_SWITCHDESKTOP = 0x0100

    # Try to open the default desktop
    hDesktop = OpenDesktop("default", 0, False, DESKTOP_SWITCHDESKTOP)
    
    if hDesktop:
        # If we can't switch to the default desktop, the screen is locked
        result = SwitchDesktop(hDesktop)
        CloseDesktop(hDesktop)
        return not result
    
    # If we can't even open the default desktop, assume it's locked
    return True

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def main():
    print("Tracking started! Leave this window open (or minimize it). Press Ctrl+C to stop.")
    data = load_data()
    loop_count = 0

    while True:
        # 1. Check if the computer is locked first!
        if not is_computer_locked():
            
            today = str(date.today())
            if today not in data:
                data[today] = {}

            try:
                # Grab the current active virtual desktop
                current = VirtualDesktop.current()
                name = current.name if current.name else f"Desktop {current.number}"

                if name not in data[today]:
                    data[today][name] = 0

                # Add one second only if unlocked
                data[today][name] += 1

            except Exception as e:
                print(f"Error accessing desktop: {e}")

        # Wait 1 second (we still wait 1 second even if locked, so it doesn't spin out of control)
        time.sleep(1)

        # Save to the JSON file every 5 seconds
        loop_count += 1
        if loop_count >= 5:
            save_data(data)
            loop_count = 0

if __name__ == "__main__":
    main()
