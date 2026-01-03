"""scrcpy interaction and management for Aurynk."""

import os
import shutil
import subprocess
import threading
import time

from aurynk.i18n import _
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
            window_title = (
                f"{device_name}"
                if device_name
                else _("Aurynk: {serial_number}").format(serial_number=serial)
            )

        try:
            # Suppress snap launcher notices
            env = os.environ.copy()
            env["SNAP_LAUNCHER_NOTICE_ENABLED"] = "false"

            # Quick sanity check: ensure ADB sees this USB serial before
            # attempting to launch scrcpy. This avoids launching a snap
            # scrcpy that will immediately fail with "Could not find any ADB device".
            try:
                adb_path = settings.get("adb", "adb_path", "adb")
                res = subprocess.run(
                    [adb_path, "devices"], capture_output=True, text=True, timeout=3
                )
                adb_list = []
                for line in res.stdout.strip().splitlines()[1:]:
                    if "\t" in line:
                        s, st = line.split("\t", 1)
                        if st.strip() == "device":
                            adb_list.append(s)
                if serial not in adb_list:
                    logger.warning("ADB does not list serial %s; aborting scrcpy start", serial)
                    return False
            except Exception:
                # If adb check fails, continue and attempt to start; let scrcpy report errors
                logger.debug("ADB presence check failed or timed out; proceeding to start scrcpy")

            # Build scrcpy command from settings
            scrcpy_path = settings.get("scrcpy", "scrcpy_path", "").strip()
            # Resolve which scrcpy binary we'll execute. If user configured
            # a path, prefer it; otherwise resolve from PATH. Detect snap
            # launcher variants that lack raw USB access and warn early.
            resolved = None
            if scrcpy_path:
                resolved = scrcpy_path
            else:
                resolved = shutil.which("scrcpy") or "scrcpy"

            # Detect snap launcher that will not have raw-usb access.
            if isinstance(resolved, str) and (
                "/snap/" in resolved or resolved.endswith("scrcpy-launch")
            ):
                logger.warning(
                    "Detected snap-packaged scrcpy (%s). This build may not have raw USB access; "
                    "install scrcpy from your distro or set scrcpy_path in settings to a non-snap binary, "
                    "or connect the snap 'raw-usb' interface.",
                    resolved,
                )

            if scrcpy_path:
                cmd = [scrcpy_path, "--serial", serial, "--window-title", window_title]
            else:
                cmd = [resolved, "--serial", serial, "--window-title", window_title]

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
                adb_path = settings.get("adb", "adb_path") or "adb"
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
        target_serial = None

        # Check exact match first
        if serial in self.processes:
            target_serial = serial
        else:
            # Fallback: check if any process is running for this IP
            # This handles cases where the port changed but scrcpy is still running on old port
            for s in list(self.processes.keys()):
                if s.startswith(f"{address}:"):
                    target_serial = s
                    break

        if target_serial:
            proc = self.processes.get(target_serial)
            if proc:
                try:
                    logger.debug(f"Terminating process for {target_serial}")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.debug(f"Force killing process for {target_serial}")
                        proc.kill()
                except Exception as e:
                    logger.error(f"Error stopping process (terminate): {e}")
                    # Try kill if terminate failed
                    try:
                        proc.kill()
                    except Exception as e2:
                        logger.error(f"Error killing process: {e2}")
                finally:
                    if target_serial in self.processes:
                        logger.debug(f"Removing {target_serial} from processes dict")
                        del self.processes[target_serial]
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

        # Check exact match
        proc = self.processes.get(serial)
        if proc:
            poll_status = proc.poll()
            if poll_status is None:
                return True
            else:
                # Process finished, clean up
                del self.processes[serial]

        # Fallback: check if any process is running for this IP
        # This handles cases where the port changed but scrcpy is still running on old port
        for s in list(self.processes.keys()):
            if s.startswith(f"{address}:"):
                proc = self.processes[s]
                if proc.poll() is None:
                    return True
                else:
                    # Process finished, clean up
                    del self.processes[s]

        return False

    def is_mirroring_serial(self, serial: str) -> bool:
        """
        Check if scrcpy is running for the device by serial.

        Args:
            serial (str): Device serial number.

        Returns:
            bool: True if running, False otherwise.
        """
        proc = self.processes.get(serial)
        if proc:
            poll_status = proc.poll()
            if poll_status is None:
                return True
            else:
                # Process finished, clean up
                del self.processes[serial]
        return False

    def stop_mirror_by_serial(self, serial: str) -> bool:
        """
        Stop scrcpy for the given device by serial.

        Args:
            serial (str): Device serial number.

        Returns:
            bool: True if stopped or not running, False if error.
        """
        logger.info(f"Attempting to stop mirror for serial: {serial}")
        proc = self.processes.get(serial)
        if proc:
            try:
                logger.debug(f"Terminating process for {serial}")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process for {serial} did not terminate, killing...")
                    proc.kill()
            except Exception as e:
                logger.error(f"Error stopping process (terminate): {e}")
                # Try to kill if terminate failed (e.g. PermissionError)
                try:
                    logger.debug(f"Force killing process for {serial}")
                    proc.kill()
                    proc.wait(timeout=1)
                except Exception as e2:
                    logger.error(f"Error killing process: {e2}")
            finally:
                if serial in self.processes:
                    logger.debug(f"Removing {serial} from processes dict")
                    del self.processes[serial]
            return True
        logger.warning(f"No process found for serial: {serial}")
        return False

    def start_mirror_usb(self, serial: str, device_name: str = None) -> bool:
        """
        Start scrcpy for a USB-connected device.

        Args:
            serial (str): USB device serial number.
            device_name (str, optional): Name of the device to display in the window title.

        Returns:
            bool: True if started successfully or already running, False otherwise.
        """
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
            window_title = (
                f"{device_name}"
                if device_name
                else _("Aurynk: {serial_number}").format(serial_number=serial)
            )

        try:
            # Suppress snap launcher notices
            env = os.environ.copy()
            env["SNAP_LAUNCHER_NOTICE_ENABLED"] = "false"

            # Build scrcpy command from settings. Resolve executable path
            # and detect snap-packaged launchers which may lack raw USB access.
            scrcpy_path = settings.get("scrcpy", "scrcpy_path", "").strip()
            resolved = None
            if scrcpy_path:
                resolved = scrcpy_path
            else:
                resolved = shutil.which("scrcpy") or "scrcpy"

            if isinstance(resolved, str) and (
                "/snap/" in resolved or resolved.endswith("scrcpy-launch")
            ):
                logger.warning(
                    "Detected snap-packaged scrcpy (%s). This build may not have raw USB access; "
                    "install scrcpy from your distro or set scrcpy_path in settings to a non-snap binary, "
                    "or connect the snap 'raw-usb' interface.",
                    resolved,
                )

            if scrcpy_path:
                cmd = [scrcpy_path, "--serial", serial, "--window-title", window_title]
            else:
                cmd = [resolved, "--serial", serial, "--window-title", window_title]

            # Apply all the same settings as wireless devices
            # (reusing the same settings logic from start_mirror)

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
                    cmd.extend(["--window-height", str(height)])
                    if x != -1 and y != -1:
                        x = min(max(0, x), screen_width - width)
                        y = min(max(0, y), screen_height - height)
                        cmd.extend(["--window-x", str(x), "--window-y", str(y)])

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

            audio_source = settings.get("scrcpy", "audio_source", "default")
            if audio_source == "output":
                cmd.extend(["--audio-source", "output"])
            elif audio_source == "mic":
                cmd.extend(["--audio-source", "mic"])

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

                record_dir = Path(record_path).expanduser()
                record_dir.mkdir(parents=True, exist_ok=True)
                import datetime
                import re

                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_device_name = device_name or serial
                safe_device_name = safe_device_name.lower().replace(" ", "_")
                safe_device_name = re.sub(r"[^a-z0-9_]+", "", safe_device_name)
                filename = f"aurynk_record_{safe_device_name}_{timestamp}.{record_format}"
                full_path = str(record_dir / filename)
                cmd.extend(["--record", full_path, "--record-format", record_format])

            # Input settings
            show_touches = settings.get("scrcpy", "show_touches")
            try:
                adb_path = settings.get("adb", "adb_path", "adb")
                value = "1" if show_touches else "0"
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
                time.sleep(0.3)
            except Exception as e:
                logger.warning(f"Failed to set show_touches via adb: {e}")

            if settings.get("scrcpy", "turn_screen_off", False):
                cmd.append("--turn-screen-off")

            if settings.get("scrcpy", "no_control", False):
                cmd.append("--no-control")

            logger.info(f"Starting USB scrcpy with command: {' '.join(cmd)}")

            proc = subprocess.Popen(cmd, env=env)
            self.processes[serial] = proc

            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_process, args=(serial, proc), daemon=True
            )
            monitor_thread.start()

            return True
        except Exception as e:
            logger.error(f"Error starting USB mirror: {e}")
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
