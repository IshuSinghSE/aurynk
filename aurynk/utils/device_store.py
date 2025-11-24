import json
import os
from typing import List, Dict, Any, Optional

from aurynk.utils.logger import get_logger

logger = get_logger("DeviceStore")

class DeviceStore:
    """Manages in-memory device list and syncs with JSON file."""
    def __init__(self, path: str):
        self.path = path
        self._devices: List[Dict[str, Any]] = []
        self._load_from_file()

    def _load_from_file(self):
        if not os.path.exists(self.path):
            self._devices = []
            return
        try:
            with open(self.path, "r") as f:
                data = f.read().strip()
                self._devices = json.loads(data) if data else []
        except Exception as e:
            logger.error(f"Error loading devices: {e}")
            self._devices = []

    def get_devices(self) -> List[Dict[str, Any]]:
        return self._devices.copy()

    def add_or_update_device(self, device_info: Dict[str, Any]):
        from aurynk.utils.device_events import notify_device_changed
        from aurynk.utils.notify import show_notification
        address = device_info.get("address")
        existing_idx = None
        for idx, device in enumerate(self._devices):
            if device.get("address") == address:
                existing_idx = idx
                break
        if existing_idx is not None:
            self._devices[existing_idx].update(device_info)
            title = "Device updated"
        else:
            self._devices.append(device_info)
            title = "Device added"
        self._save_to_file()
        notify_device_changed()
        try:
            name = device_info.get("name") or address or "Device"
            show_notification(title, str(name))
        except Exception:
            pass

    def remove_device(self, address: str):
        from aurynk.utils.device_events import notify_device_changed
        from aurynk.utils.notify import show_notification
        import subprocess
        # Find the device to get its connect_port
        device = next((d for d in self._devices if d.get("address") == address), None)
        should_disconnect = False
        if device:
            connect_port = device.get("connect_port")
            # Check if device is connected
            if connect_port:
                try:
                    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
                    serial = f"{address}:{connect_port}"
                    if serial in result.stdout:
                        should_disconnect = True
                except Exception as e:
                    logger.error(f"Error checking device connection: {e}")
            # Disconnect using adb if connected
            if should_disconnect:
                try:
                    subprocess.run(["adb", "disconnect", f"{address}:{connect_port}"], check=False)
                except Exception as e:
                    logger.error(f"Error disconnecting device: {e}")
        self._devices = [d for d in self._devices if d.get("address") != address]
        self._save_to_file()
        notify_device_changed()
        try:
            show_notification("Device removed", address)
        except Exception:
            pass

    def _save_to_file(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        try:
            with open(self.path, "w") as f:
                json.dump(self._devices, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving devices: {e}")
        else:
            # After a successful save, notify the tray helper via a central
            # helper so the tray menu is kept in sync. Run in a daemon thread
            # to avoid blocking the caller.
            try:
                import threading

                def _notify():
                    try:
                        # Import locally to avoid import cycles at module import time
                        from aurynk.lib.tray_controller import send_devices_to_tray

                        send_devices_to_tray(self._devices)
                    except Exception as e:
                        # Do not escalate errors from tray notification.
                        logger.warning(f"Tray notify failed: {e}")

                threading.Thread(target=_notify, daemon=True).start()
            except Exception:
                pass

    def reload(self):
        """Reload device list from file (if changed externally)."""
        self._load_from_file()

    def clear(self):
        self._devices = []
        self._save_to_file()
