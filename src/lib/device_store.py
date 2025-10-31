# --- TypedDict schema for device info ---
from typing import TypedDict, Optional
import json
import os
from datetime import datetime

DEVICE_STORE_PATH = os.path.join(os.getcwd(), "data", "mirage_paired_devices.json")

class DeviceSpec(TypedDict, total=False):
    ram: str
    storage: str
    battery: str

class DeviceInfo(TypedDict, total=False):
    address: str
    pair_port: int
    connect_port: int
    password: str
    name: str
    android_version: str
    manufacturer: str
    model: str
    last_seen: str
    spec: DeviceSpec
    thumbnail: str
# DeviceInfo type (schema for device dicts stored in JSON)
# {
#   "address": str,
#   "pair_port": int,
#   "connect_port": int,
#   "password": str,
#   "name": str,
#   "android_version": str,
#   "manufacturer": str,
#   "model": str,
#   "last_seen": str (ISO8601),
#   "spec": {"ram": str, "storage": str, "cpu": str, "battery": str},
#   "thumbnail": str (path to screenshot/thumbnail)
# }

# Fetch all device data (screenshot, spec, thumbnail) and update the JSON file
def fetch_and_update_device_data(device_info):
    import subprocess
    # Fetch RAM
    try:
        meminfo = subprocess.run(["adb", "shell", "cat", "/proc/meminfo"], capture_output=True, text=True)
        import re
        match = re.search(r"MemTotal:\s+(\d+) kB", meminfo.stdout)
        ram = f"{int(match.group(1))//1024} MB" if match else ""
    except Exception:
        ram = ""
    # Fetch storage
    try:
        df = subprocess.run(["adb", "shell", "df", "/data"], capture_output=True, text=True)
        lines = df.stdout.splitlines()
        if len(lines) > 1:
            parts = lines[1].split()
            storage = f"{int(parts[1])//1000} MB" if len(parts) > 1 else ""
        else:
            storage = ""
    except Exception:
        storage = ""
    # Fetch battery
    try:
        battery = subprocess.run(["adb", "shell", "dumpsys", "battery"], capture_output=True, text=True)
        import re
        match = re.search(r"level: (\d+)", battery.stdout)
        battery_str = f"{match.group(1)}%" if match else ""
    except Exception:
        battery_str = ""
    # Fetch screenshot (thumbnail)
    try:
        subprocess.run(["adb", "shell", "screencap", "-p", "/sdcard/screen.png"])
        local_path = f"/tmp/{device_info['address'].replace('.', '_')}_screen.png"
        subprocess.run(["adb", "pull", "/sdcard/screen.png", local_path])
        thumbnail = local_path
    except Exception:
        thumbnail = ""
    # Update device_info
    device_info["spec"] = {
        "ram": ram,
        "storage": storage,
        "cpu": cpu,
        "battery": battery_str
    }
    device_info["thumbnail"] = thumbnail
    device_info["last_seen"] = datetime.now().isoformat()
    # Save updated device
    save_paired_device(device_info)

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
