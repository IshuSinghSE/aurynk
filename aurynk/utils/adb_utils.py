def is_device_connected(address, connect_port):
    """Check if a device is connected via adb."""
    import subprocess

    serial = f"{address}:{connect_port}"
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        if result.returncode != 0:
            return False
        for line in result.stdout.splitlines():
            if serial in line and "device" in line:
                return True
        return False
    except Exception:
        return False
