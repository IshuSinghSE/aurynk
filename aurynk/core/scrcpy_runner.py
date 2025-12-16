#!/usr/bin/env python3
"""scrcpy interaction and management for Aurynk."""

import os
import subprocess
import threading
import time

from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

# For monitor geometry
try:
    import gi

    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk
except ImportError:
    Gdk = None

logger = get_logger("ScrcpyManager")


class ScrcpyManager:
    """
    Handles scrcpy process management for device mirroring.

    This class manages the lifecycle of scrcpy processes, including starting, stopping,
    and monitoring them. It implements a singleton pattern to ensure centralized control.
    """

    _instance = None

    def __new__(cls):
        """
        Create or return the singleton instance of ScrcpyManager.

        Returns:
            ScrcpyManager: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = super(ScrcpyManager, cls).__new__(cls)
            cls._instance.processes = {}
            cls._instance.stop_callbacks = []
        return cls._instance

    def __init__(self):
        """Initialize the ScrcpyManager."""
        # Init handled in __new__ to ensure singleton properties
        pass

    def add_stop_callback(self, callback):
        """
        Register a callback to be called when a mirroring process stops.

        Args:
            callback (Callable[[str], None]): The function to call when a process stops.
                It receives the serial number as an argument.
        """
        if callback not in self.stop_callbacks:
            self.stop_callbacks.append(callback)

    def start_mirror(self, address: str, port: int, device_name: str = None) -> bool:
        """
        Start scrcpy for the given device address and port.

        Optionally sets the window title to the device name.

        Args:
            address (str): Device IP address.
            port (int): Device connection port.
            device_name (str, optional): Name of the device to display in the window title.

        Returns:
            bool: True if started successfully or already running, False otherwise.
        """
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

        # Load scrcpy settings
        settings = SettingsManager()

        window_title = settings.get("scrcpy", "window_title")
        if not window_title:
            window_title = f"{device_name}" if device_name else _("Aurynk: {}").format(serial)

        try:
            # Suppress snap launcher notices
            env = os.environ.copy()
            env["SNAP_LAUNCHER_NOTICE_ENABLED"] = "false"

            # Build scrcpy command from settings
            scrcpy_path = settings.get("scrcpy", "scrcpy_path", "").strip()
            if scrcpy_path:
                cmd = [scrcpy_path, "--serial", serial, "--window-title", window_title]
            else:
                cmd = ["scrcpy", "--serial", serial, "--window-title", window_title]

            # --- Monitor geometry logic ---
            window_geom = settings.get("scrcpy", "window_geometry", "")
            if window_geom:
                width, height, x, y = 800, 600, -1, -1
                try:
                    parts = [int(v) for v in window_geom.split(",")]
                    if len(parts) == 4:
                        width, height, x, y = parts
                except Exception:
                    pass

                # Get monitor size using Gdk if available
                screen_width, screen_height = 1920, 1080
                if Gdk is not None:
                    try:
                        display = Gdk.Display.get_default()
                        if display:
                            monitor = display.get_primary_monitor()
                            if monitor:
                                geometry = monitor.get_geometry()
                                screen_width = geometry.width
                                screen_height = geometry.height
                    except Exception:
                        pass

                # Clamp window size to monitor
                width = min(width, screen_width)
                height = min(height, screen_height)

                # Set window position if not fullscreen
                if not settings.get("scrcpy", "fullscreen"):
                    # Only pass --window-height to maintain aspect ratio
                    cmd.extend(["--window-height", str(height)])
                    # Only set position if x/y are not -1 (center)
                    if x != -1 and y != -1:
                        # Clamp position to monitor
                        x = min(max(0, x), screen_width - width)
                        y = min(max(0, y), screen_height - height)
                        cmd.extend(["--window-x", str(x), "--window-y", str(y)])
            # If window_geom is empty, do not add any window size/position args (let scrcpy use its defaults)

            # Display settings
            if settings.get("scrcpy", "always_on_top"):
                cmd.append("--always-on-top")
            if settings.get("scrcpy", "fullscreen"):
                cmd.append("--fullscreen")
            if settings.get("scrcpy", "window_borderless"):
                cmd.append("--window-borderless")

            max_size = settings.get("scrcpy", "max_size", 0)
            if max_size > 0:
                cmd.extend(["--max-size", str(max_size)])

            rotation = settings.get("scrcpy", "rotation", 0)
            if rotation > 0:
                cmd.extend(["--rotation", str(rotation)])

            if settings.get("scrcpy", "stay_awake", True):
                cmd.append("--stay-awake")

            # Audio/Video settings
            if not settings.get("scrcpy", "enable_audio", False):
                cmd.append("--no-audio")

            # Audio source selection (output, mic, default)
            audio_source = settings.get("scrcpy", "audio_source", "default")
            if audio_source == "output":
                cmd.extend(["--audio-source", "output"])
            elif audio_source == "mic":
                cmd.extend(["--audio-source", "mic"])
            # If 'default', do not add the flag (let scrcpy use its default)

            video_codec = settings.get("scrcpy", "video_codec", "h264")
            cmd.extend(["--video-codec", video_codec])

            video_bitrate = settings.get("scrcpy", "video_bitrate", 8)
            cmd.extend(["--video-bit-rate", f"{video_bitrate}M"])

            max_fps = settings.get("scrcpy", "max_fps", 0)
            if max_fps > 0:
                cmd.extend(["--max-fps", str(max_fps)])

            # Recording options
            record_enabled = settings.get("scrcpy", "record", False)
            record_path = settings.get("scrcpy", "record_path", "~/Videos/Aurynk")
            record_format = settings.get("scrcpy", "record_format", "mp4")

            if record_enabled:
                from pathlib import Path

                # Expand ~ and ensure directory exists
                record_dir = Path(record_path).expanduser()
                record_dir.mkdir(parents=True, exist_ok=True)
                # Generate a unique filename with timestamp
                import datetime

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # Format device name for filename: lowercase, spaces to underscores, alphanum/underscore only
                safe_device_name = device_name or serial
                safe_device_name = safe_device_name.lower().replace(" ", "_")
                # Remove any non-alphanumeric or underscore chars
                import re

                safe_device_name = re.sub(r"[^a-z0-9_]+", "", safe_device_name)
                filename = f"aurynk_record_{safe_device_name}_{timestamp}.{record_format}"
                full_path = str(record_dir / filename)
                cmd.extend(["--record", full_path, "--record-format", record_format])

            # Input settings
            # Use adb to set show_touches before starting scrcpy, with serial and delay
            show_touches = settings.get("scrcpy", "show_touches")
            try:
                adb_path = settings.get("adb", "adb_path", "adb")
                value = "1" if show_touches else "0"
                # Use the correct device serial
                subprocess.run(
                    [
                        adb_path,
                        "-s",
                        serial,
                        "shell",
                        "settings",
                        "put",
                        "system",
                        "show_touches",
                        value,
                    ],
                    check=False,
                )
                # Wait a short time to ensure the setting is applied
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Failed to set show_touches via adb: {e}")

            if settings.get("scrcpy", "turn_screen_off", False):
                cmd.append("--turn-screen-off")

            # Read-only mode
            if settings.get("scrcpy", "no_control", False):
                cmd.append("--no-control")

            logger.info(f"Starting scrcpy with command: {' '.join(cmd)}")

            proc = subprocess.Popen(cmd, env=env)
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
        """
        Stop scrcpy for the given device.

        Args:
            address (str): Device IP address.
            port (int): Device connection port.

        Returns:
            bool: True if stopped or not running, False if error.
        """
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
        """
        Check if scrcpy is running for the device.

        Args:
            address (str): Device IP address.
            port (int): Device connection port.

        Returns:
            bool: True if running, False otherwise.
        """
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
        """
        Monitor the process and clean up when it exits.

        Args:
            serial (str): Device serial identifier.
            proc (subprocess.Popen): The process object.
        """
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
