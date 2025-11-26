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
