#!/usr/bin/env python3
"""scrcpy interaction and management for Aurynk."""

import subprocess
from typing import Optional

class ScrcpyManager:
    """Handles scrcpy process management for device mirroring."""

    def __init__(self):
        self.processes = {}

    def start_mirror(self, address: str, port: int, device_name: str = None) -> bool:
        """Start scrcpy for the given device address and port. Returns True if started. Optionally set window title to device name."""
        serial = f"{address}:{port}"
        print(f"[scrcpy] Request to start mirror for {serial}", flush=True)
        
        # Check if already running and clean up dead processes
        if serial in self.processes:
            proc = self.processes[serial]
            poll_status = proc.poll()
            if poll_status is None:
                print(f"[scrcpy] Mirror already running for {serial}", flush=True)
                return True  # Already running
            else:
                # Process finished, remove it
                print(f"[scrcpy] Cleaning up dead process for {serial} (exit code: {poll_status})", flush=True)
                del self.processes[serial]

        window_title = f"{device_name}" if device_name else f"Aurynk: {serial}"
        try:
            print(f"[scrcpy] Launching scrcpy for {serial}", flush=True)
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
            print(f"[scrcpy] Error starting mirror: {e}", flush=True)
            return False

    def stop_mirror(self, address: str, port: int) -> bool:
        """Stop scrcpy for the given device."""
        serial = f"{address}:{port}"
        print(f"[scrcpy] Request to stop mirror for {serial}", flush=True)
        proc = self.processes.get(serial)
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"[scrcpy] Process did not terminate, killing {serial}", flush=True)
                    proc.kill()
            except Exception as e:
                print(f"[scrcpy] Error stopping process: {e}", flush=True)
            finally:
                if serial in self.processes:
                    del self.processes[serial]
            return True
        print(f"[scrcpy] No process found to stop for {serial}", flush=True)
        return False

    def is_mirroring(self, address: str, port: int) -> bool:
        """Check if scrcpy is running for the device."""
        serial = f"{address}:{port}"
        proc = self.processes.get(serial)
        if proc:
            poll_status = proc.poll()
            if poll_status is None:
                return True
            else:
                # Process finished, clean up
                print(f"[scrcpy] Process {serial} finished (detected in is_mirroring) with {poll_status}", flush=True)
                del self.processes[serial]
        return False
