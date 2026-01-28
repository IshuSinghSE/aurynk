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


def is_device_connected(address, connect_port):
    """Check if a device is connected via adb."""
    import subprocess

    serial = f"{address}:{connect_port}"
    from aurynk.utils.adb_utils import get_adb_path

    try:
        result = subprocess.run([get_adb_path(), "devices"], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            # Must have tab separator and "device" status (not "offline" or other states)
            if serial in line and "\tdevice" in line:
                return True
        return False
    except Exception:
        return False


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
