import json
import os
from datetime import datetime

DEVICE_STORE_PATH = os.path.join(os.getcwd(), "data", "mirage_paired_devices.json")

def load_paired_devices():
    if not os.path.exists(DEVICE_STORE_PATH):
        return []
    try:
        with open(DEVICE_STORE_PATH, "r") as f:
            data = f.read().strip()
            if not data:
                return []
            return json.loads(data)
    except Exception:
        # If file is invalid/corrupt, reset to empty list
        with open(DEVICE_STORE_PATH, "w") as f:
            f.write("[]")
        return []

def save_paired_device(device_info):
    devices = load_paired_devices()
    # Remove any existing device with same address/port
    devices = [d for d in devices if d.get("address") != device_info["address"] or d.get("pair_port") != device_info["pair_port"]]
    device_info["last_seen"] = datetime.now().isoformat()
    # Ensure 'spec' and 'thumbnail' fields exist
    if "spec" not in device_info or not isinstance(device_info["spec"], dict):
        device_info["spec"] = {"ram": "", "storage": "", "cpu": "", "battery": ""}
    if "thumbnail" not in device_info:
        device_info["thumbnail"] = ""
    devices.insert(0, device_info)  # Most recent first
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DEVICE_STORE_PATH), exist_ok=True)
    with open(DEVICE_STORE_PATH, "w") as f:
        json.dump(devices, f, indent=2)

def get_most_recent_device():
    devices = load_paired_devices()
    return devices[0] if devices else None
