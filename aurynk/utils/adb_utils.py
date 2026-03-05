def get_adb_path():
    """Return the custom ADB path from settings, or fallback to 'adb'."""
    try:
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        adb_path = settings.get("adb", "adb_path", "").strip()
        if adb_path:
            import os

            if os.path.isfile(adb_path) and os.access(adb_path, os.X_OK):
                return adb_path
    except Exception:
        pass
    return "adb"


import time

_connected_devices_cache = set()
_cache_timestamp = 0.0
_CACHE_TTL = 1.0  # seconds


def get_connected_devices_cached():
    """Return a cached set of connected device serials.

    Optimization: Cache adb device list for 1s to avoid expensive subprocess
    calls during rapid polling (e.g. from UI render loops or tray service).
    Saves ~50-100ms per call.
    """
    global _connected_devices_cache, _cache_timestamp

    current_time = time.time()
    if current_time - _cache_timestamp < _CACHE_TTL:
        return _connected_devices_cache

    import subprocess

    from aurynk.utils.adb_utils import get_adb_path

    new_cache = set()
    try:
        result = subprocess.run([get_adb_path(), "devices"], capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "\tdevice" in line:
                    serial = line.split("\t")[0]
                    new_cache.add(serial)
    except Exception:
        pass

    _connected_devices_cache = new_cache
    _cache_timestamp = current_time
    return _connected_devices_cache


def is_device_connected(address, connect_port):
    """Check if a device is connected via adb."""
    serial = f"{address}:{connect_port}"
    return serial in get_connected_devices_cached()


def clear_device_notifications(serial: str) -> bool:
    """Clear all Aurynk notifications from the Android device.

    Args:
        serial: Device serial (address:port for wireless, or USB serial)

    Returns:
        True if cleared successfully, False otherwise
    """
    import subprocess

    try:
        # Cancel notification with our specific tag
        cancel_cmd = "cmd notification cancel aurynk_status"
        subprocess.run(
            [get_adb_path(), "-s", serial, "shell", cancel_cmd], capture_output=True, timeout=2
        )
        return True
    except Exception:
        return False


def send_device_notification(serial: str, message: str, title: str = "Aurynk") -> bool:
    """Send a notification/toast to the Android device via ADB.

    Args:
        serial: Device serial (address:port for wireless, or USB serial)
        message: Notification message to display
        title: Notification title (default: "Aurynk")

    Returns:
        True if notification was sent successfully, False otherwise
    """
    import subprocess

    try:
        # Clear old notifications first
        clear_device_notifications(serial)

        # Post a system notification using cmd notification
        # Format: cmd notification post [flags] <tag> <text>
        # Need to properly escape the message for shell parsing
        import shlex

        # Build the notification command with proper quoting
        notification_cmd = f"cmd notification post -S bigtext -t {shlex.quote(title)} aurynk_status {shlex.quote(message)}"

        cmd = [get_adb_path(), "-s", serial, "shell", notification_cmd]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)

        # Also log to logcat for debugging
        subprocess.run(
            [get_adb_path(), "-s", serial, "shell", "log", "-t", "Aurynk", message], timeout=2
        )

        return result.returncode == 0
    except Exception:
        return False
