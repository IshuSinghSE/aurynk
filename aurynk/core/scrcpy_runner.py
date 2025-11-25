#!/usr/bin/env python3
"""scrcpy interaction and management for Aurynk."""

import subprocess
import threading

from aurynk.utils.logger import get_logger

logger = get_logger("ScrcpyManager")


class ScrcpyManager:
    """Handles scrcpy process management for device mirroring."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ScrcpyManager, cls).__new__(cls)
            cls._instance.processes = {}
            cls._instance.stop_callbacks = []
        return cls._instance

    def __init__(self):
        # Init handled in __new__ to ensure singleton properties
        pass

    def add_stop_callback(self, callback):
        """Register a callback to be called when a mirroring process stops."""
        if callback not in self.stop_callbacks:
            self.stop_callbacks.append(callback)

    def start_mirror(self, address: str, port: int, device_name: str = None) -> bool:
        """Start scrcpy for the given device address and port. Returns True if started. Optionally set window title to device name."""
        serial = f"{address}:{port}"

        # Check if already running and clean up dead processes
        if serial in self.processes:
            proc = self.processes[serial]
            poll_status = proc.poll()
            if poll_status is None:
                return True  # Already running
            else:
                # Process finished, remove it
                del self.processes[serial]

        window_title = f"{device_name}" if device_name else f"Aurynk: {serial}"
        try:
            proc = subprocess.Popen(
                [
                    "scrcpy",
                    "--serial",
                    serial,
                    "--window-title",
                    window_title,
                    "--always-on-top",
                    "--no-audio",
                ]
            )
            self.processes[serial] = proc

            # Start monitoring thread to handle window close events
            monitor_thread = threading.Thread(
                target=self._monitor_process, args=(serial, proc), daemon=True
            )
            monitor_thread.start()

            return True
        except Exception as e:
            logger.error(f"Error starting mirror: {e}")
            return False

    def stop_mirror(self, address: str, port: int) -> bool:
        """Stop scrcpy for the given device."""
        serial = f"{address}:{port}"
        proc = self.processes.get(serial)
        if proc:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception as e:
                logger.error(f"Error stopping process: {e}")
            finally:
                if serial in self.processes:
                    del self.processes[serial]
            return True
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
                del self.processes[serial]
        return False

    def _monitor_process(self, serial: str, proc: subprocess.Popen):
        """Monitor the process and clean up when it exits."""
        try:
            proc.wait()
        except Exception as e:
            logger.error(f"Error monitoring process {serial}: {e}")
        finally:
            # Only remove if it's still the same process object (handle race with restart)
            if serial in self.processes and self.processes[serial] == proc:
                del self.processes[serial]
                # Notify callbacks
                for callback in self.stop_callbacks:
                    try:
                        callback(serial)
                    except Exception as e:
                        logger.error(f"Error in stop callback: {e}")
