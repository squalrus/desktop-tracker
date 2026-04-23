import time
import json
import os
from datetime import date
from pyvda import VirtualDesktop

# The file where our data will be saved
DATA_FILE = "desktop_data.json"

def load_data():
    # If the file exists, open and read it. Otherwise, return an empty dictionary.
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    # Save the dictionary to a JSON file
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def main():
    print("Tracking started! Leave this window open (or minimize it). Press Ctrl+C to stop.")
    data = load_data()
    loop_count = 0

    while True:
        # Get today's date in YYYY-MM-DD format
        today = str(date.today())
        
        # Ensure today has an entry in our data
        if today not in data:
            data[today] = {}

        try:
            # Grab the current active virtual desktop
            current = VirtualDesktop.current()
            
            # If the desktop has a name, use it. If not, fallback to "Desktop [Number]"
            name = current.name if current.name else f"Desktop {current.number}"

            # Ensure this desktop has an entry for today
            if name not in data[today]:
                data[today][name] = 0

            # Add one second
            data[today][name] += 1

        except Exception as e:
            print(f"Error accessing desktop: {e}")

        # Wait 1 second
        time.sleep(1)

        # Save to the JSON file every 5 seconds to reduce disk usage
        loop_count += 1
        if loop_count >= 5:
            save_data(data)
            loop_count = 0

if __name__ == "__main__":
    main()