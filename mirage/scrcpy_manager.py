#!/usr/bin/env python3
"""scrcpy interaction and management for Mirage."""

import subprocess
from typing import Optional

class ScrcpyManager:
    """Handles scrcpy process management for device mirroring."""

    def __init__(self):
        self.processes = {}

    def start_mirror(self, address: str, port: int, device_name: str = None) -> bool:
        """Start scrcpy for the given device address and port. Returns True if started. Optionally set window title to device name."""
        serial = f"{address}:{port}"
        if serial in self.processes:
            return True  # Already running
        window_title = f"Mirage: {device_name}" if device_name else f"Mirage: {serial}"
        try:
            proc = subprocess.Popen([
                "scrcpy",
                "--serial", serial,
                "--window-title", window_title,
                "--always-on-top",
                "--no-audio",
            ])
            self.processes[serial] = proc
            return True
        except Exception as e:
            print(f"[scrcpy] Error starting mirror: {e}")
            return False

    def stop_mirror(self, address: str, port: int) -> bool:
        """Stop scrcpy for the given device."""
        serial = f"{address}:{port}"
        proc = self.processes.get(serial)
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            del self.processes[serial]
            return True
        return False

    def is_mirroring(self, address: str, port: int) -> bool:
        """Check if scrcpy is running for the device."""
        serial = f"{address}:{port}"
        proc = self.processes.get(serial)
        return proc is not None and proc.poll() is None
