#!/usr/bin/env python3
"""ADB/scrcpy controller for device management."""

import os
import random
import string
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf

from aurynk.core.device_manager import DeviceStore
from aurynk.utils.adb_utils import get_adb_path
from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger("ADBController")

# Use XDG_DATA_HOME when available (works inside Flatpak); fall back to
# ~/.local/share/aurynk for regular installs. Ensure the directory exists.
_xdg_data = os.environ.get("XDG_DATA_HOME")
if _xdg_data:
    DEVICE_STORE_DIR = os.path.join(_xdg_data, "aurynk")
else:
    DEVICE_STORE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "aurynk")

# Ensure the directory exists (safe no-op on non-Flatpak too)
Path(DEVICE_STORE_DIR).mkdir(parents=True, exist_ok=True)

DEVICE_STORE_PATH = os.path.join(DEVICE_STORE_DIR, "paired_devices.json")

# ~/.local/share/aurynk/paired_devices.json


class ADBController:
    """
    Handles all ADB and device management operations.

    This class provides methods to pair, connect, and manage Android devices via ADB.
    It handles mDNS discovery, device information retrieval, and screenshot capture.
    """

    def __init__(self):
        """Initialize the ADB controller."""
        self.device_store = DeviceStore(DEVICE_STORE_PATH)

    # ===== Device Pairing =====

    def generate_code(self, length: int = 5) -> str:
        """
        Generate a random code for pairing.

        Args:
            length (int): Length of the code to generate. Defaults to 5.

        Returns:
            str: A random string of the specified length.
        """
        return "".join(random.choices(string.ascii_letters, k=length))

    def pair_device(
        self,
        address: str,
        pair_port: int,
        connect_port: int,
        password: str,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """
        Pair and connect to a device, then fetch device details.

        Args:
            address (str): Device IP address.
            pair_port (int): Port for pairing.
            connect_port (int): Port for connection (may differ from pair_port).
            password (str): Pairing password.
            status_callback (Optional[Callable[[str], None]]): Optional callback for status updates.

        Returns:
            bool: True if successful, False otherwise.
        """
        import time

        def log(msg: str):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        # Step 1: Pair
        log(f"Pairing with {address}:{pair_port}...")
        pair_cmd = [get_adb_path(), "pair", f"{address}:{pair_port}", password]
        pair_result = subprocess.run(pair_cmd, capture_output=True, text=True)

        if pair_result.returncode == 0:
            log("✓ Paired successfully")
        else:
            log(f"⚠ Pairing failed: {pair_result.stderr.strip() or pair_result.stdout.strip()}")

        # Step 2: Connect (attempt even if pairing failed)
        log(f"Connecting to {address}:{connect_port}...")
        connected = False

        # Load retry settings
        settings = SettingsManager()
        max_retries = settings.get("adb", "max_retry_attempts", 5)
        timeout = settings.get("adb", "connection_timeout", 10)

        for attempt in range(max_retries):
            connect_cmd = [get_adb_path(), "connect", f"{address}:{connect_port}"]
            connect_result = subprocess.run(
                connect_cmd, capture_output=True, text=True, timeout=timeout
            )
            output = (connect_result.stdout + connect_result.stderr).lower()

            if ("connected" in output or "already connected" in output) and "unable" not in output:
                connected = True
                log("✓ Connected successfully")
                break

            time.sleep(1)

        if not connected:
            log(f"✗ Could not connect to {address}:{connect_port}")
            return False

        # Step 3: Fetch device details
        log("Fetching device information...")
        device_info = self._fetch_device_info(address, connect_port)
        device_info.update(
            {
                "address": address,
                "pair_port": pair_port,
                "connect_port": connect_port,
                "password": password,
            }
        )

        # Step 4: Save device
        self.save_paired_device(device_info)
        log(f"✓ Device saved: {device_info.get('name', 'Unknown')}")

        return True

    def start_mdns_discovery(
        self,
        on_device_found: Callable[[str, int, int, str], None],
        network_name: str,
        password: str,
    ):
        """
        Start mDNS discovery for ADB devices.

        Args:
            on_device_found (Callable[[str, int, int, str], None]): Callback when a device is found
                (address, pair_port, connect_port, password).
            network_name (str): Expected network SSID.
            password (str): Pairing password.

        Returns:
            tuple: A tuple containing the Zeroconf instance and a tuple of ServiceBrowsers.
        """
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

        # We'll collect discovered services by address
        discovered = {}

        def handle_found(address, service_type, port):
            if not address:
                return
            if address not in discovered:
                discovered[address] = {}
            if service_type == "_adb-tls-pairing._tcp.local.":
                discovered[address]["pair_port"] = port
            elif service_type == "_adb-tls-connect._tcp.local.":
                discovered[address]["connect_port"] = port
            # If both ports are found, call the callback
            if "pair_port" in discovered[address] and "connect_port" in discovered[address]:
                pair_port = discovered[address]["pair_port"]
                connect_port = discovered[address]["connect_port"]
                on_device_found(address, pair_port, connect_port, password)
                # Optionally, remove to avoid duplicate callbacks
                del discovered[address]

        def make_handler(expected_service_type):
            # Handler must match zeroconf's expected signature: (zeroconf, service_type, name, state_change)
            def on_service_state_change(zeroconf, service_type, name, state_change, **kwargs):
                if (
                    state_change is ServiceStateChange.Added
                    and service_type == expected_service_type
                ):
                    info = zeroconf.get_service_info(service_type, name)
                    if info:
                        address = ".".join(map(str, info.addresses[0])) if info.addresses else None
                        port = info.port
                        handle_found(address, service_type, port)

            return on_service_state_change

        # Browse for both ADB pairing and connect services
        browser_pair = ServiceBrowser(
            zeroconf,
            "_adb-tls-pairing._tcp.local.",
            handlers=[make_handler("_adb-tls-pairing._tcp.local.")],
        )
        browser_connect = ServiceBrowser(
            zeroconf,
            "_adb-tls-connect._tcp.local.",
            handlers=[make_handler("_adb-tls-connect._tcp.local.")],
        )

        return zeroconf, (browser_pair, browser_connect)

    def get_current_ports(self, address: str, timeout: int = 3) -> Optional[Dict[str, int]]:
        """
        Try to get current ports for a device via mDNS discovery.

        Args:
            address (str): The device IP address to look for.
            timeout (int): Timeout in seconds for the mDNS query. Defaults to 3.

        Returns:
            Optional[Dict[str, int]]: Dict with 'pair_port' and 'connect_port' if found, None otherwise.
        """

        # Try using adb mdns services first (faster)
        try:
            result = subprocess.run(
                [get_adb_path(), "mdns", "services"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode == 0:
                # Parse output for the device's IP address
                # Format: "adb-XXXXX-XXXXXX._adb-tls-connect._tcp    192.168.1.2:37985"
                for line in result.stdout.splitlines():
                    if address in line:
                        if "_adb-tls-connect" in line:
                            # Extract port
                            parts = line.split()
                            for part in parts:
                                if address in part and ":" in part:
                                    port = part.split(":")[-1]
                                    try:
                                        return {"connect_port": int(port), "pair_port": None}
                                    except ValueError:
                                        pass
        except Exception as e:
            logger.debug(f"Could not query mDNS services: {e}")

        return None

    # ===== Device Information =====

    def _fetch_device_info(self, address: str, connect_port: int) -> Dict[str, Any]:
        """
        Fetch detailed device information via ADB.

        Args:
            address (str): Device IP address.
            connect_port (int): Port used for the connection.

        Returns:
            Dict[str, Any]: A dictionary containing device information like name, model, manufacturer, etc.
        """
        serial = f"{address}:{connect_port}"
        device_info = {}

        # Helper to run adb shell command
        def get_prop(prop: str) -> str:
            try:
                timeout = SettingsManager().get("adb", "connection_timeout", 10)
                result = subprocess.run(
                    [get_adb_path(), "-s", serial, "shell", "getprop", prop],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return result.stdout.strip()
            except Exception:
                return ""

        # Fetch basic properties
        marketname = get_prop("ro.product.marketname")
        model = get_prop("ro.product.device")
        manufacturer = get_prop("ro.product.manufacturer")
        android_version = get_prop("ro.build.version.release")

        device_info["name"] = f"{marketname}" if marketname else (model or "Unknown")
        device_info["model"] = model
        device_info["manufacturer"] = manufacturer
        device_info["android_version"] = android_version
        device_info["last_seen"] = datetime.now().isoformat()

        return device_info

    def fetch_device_specs(self, address: str, connect_port: int) -> Dict[str, str]:
        """
        Fetch device specifications (RAM, storage, battery).

        Args:
            address (str): Device IP address.
            connect_port (int): Port used for the connection.

        Returns:
            Dict[str, str]: A dictionary containing RAM, storage, and battery info.
        """
        serial = f"{address}:{connect_port}"
        specs = {"ram": "", "storage": "", "battery": ""}

        try:
            # RAM
            timeout = SettingsManager().get("adb", "connection_timeout", 10)
            meminfo = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "cat", "/proc/meminfo"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            import re

            match = re.search(r"MemTotal:\s+(\d+) kB", meminfo.stdout)
            if match:
                ram_mb = int(match.group(1)) // 1000
                ram_gb = ram_mb / 1000
                specs["ram"] = f"{round(ram_gb)} GB"

            # Storage
            df = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "df", "/data"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            lines = df.stdout.splitlines()
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) > 1:
                    storage_mb = int(parts[1]) // 1000
                    storage_gb = storage_mb / 1000
                    specs["storage"] = f"{round(storage_gb)} GB"

            # Battery
            battery = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            match = re.search(r"level: (\d+)", battery.stdout)
            if match:
                specs["battery"] = f"{match.group(1)}%"

        except Exception as e:
            logger.error(f"Error fetching specs: {e}")

        return specs

    def capture_screenshot(self, address: str, connect_port: int) -> Optional[str]:
        """
        Capture device screenshot and return local path.

        If locked or screen off, use old image. Otherwise, go to home,
        take screenshot, return to previous app. Screenshots are stored
        in ~/.local/share/aurynk/screenshots/.

        Args:
            address (str): Device IP address.
            connect_port (int): Port used for the connection.

        Returns:
            Optional[str]: Path to the screenshot file if successful, None otherwise.
        """
        serial = f"{address}:{connect_port}"
        screenshot_dir = os.path.join(DEVICE_STORE_DIR, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        local_path = os.path.join(screenshot_dir, f"aurynk_{address.replace('.', '_')}_screen.png")
        try:
            # 1. Check if device is locked or screen is off
            # Check screen state
            timeout = SettingsManager().get("adb", "connection_timeout", 10)
            dumpsys = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "dumpsys", "window"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            screen_off = (
                "mDreamingLockscreen=true" in dumpsys.stdout
                or "mScreenOn=false" in dumpsys.stdout
                or "mInteractive=false" in dumpsys.stdout
            )
            # Check keyguard (lock)
            keyguard = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "dumpsys", "window", "windows"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            locked = (
                "mShowingLockscreen=true" in keyguard.stdout
                or "mDreamingLockscreen=true" in keyguard.stdout
            )
            if screen_off or locked:
                # Use old image if exists
                if os.path.exists(local_path):
                    return local_path
                else:
                    logger.warning(
                        "Device is locked or screen off, and no previous screenshot available."
                    )
                    return None

            # 2. Get current foreground app/activity
            activity_result = subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "dumpsys", "window", "windows"],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            import re

            match = re.search(
                r"mCurrentFocus=Window\{[^ ]+ ([^/]+)/([^ ]+)\}", activity_result.stdout
            )
            current_app = match.group(1) if match else None

            # 3. Go to home screen
            subprocess.run(
                [get_adb_path(), "-s", serial, "shell", "input", "keyevent", "3"],
                check=True,
                timeout=timeout,
            )

            # 4. Take screenshot on home
            subprocess.run(
                [
                    get_adb_path(),
                    "-s",
                    serial,
                    "shell",
                    "screencap",
                    "-p",
                    "/sdcard/aurynk_screen.png",
                ],
                check=True,
                timeout=timeout,
            )

            # 5. Return to previous app if possible
            if current_app:
                subprocess.run(
                    [get_adb_path(), "-s", serial, "shell", "monkey", "-p", current_app, "1"],
                    timeout=timeout,
                )

            # 6. Pull to local temp directory
            subprocess.run(
                [get_adb_path(), "-s", serial, "pull", "/sdcard/aurynk_screen.png", local_path],
                check=True,
                timeout=timeout,
            )
            return local_path
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")
            # If error, fallback to old image if available
            if os.path.exists(local_path):
                return local_path
            return None

    # ===== Device Storage =====

    def load_paired_devices(self) -> List[Dict[str, Any]]:
        """
        Get paired devices from in-memory store.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a paired device.
        """
        return self.device_store.get_devices()

    def save_paired_device(self, device_info: Dict[str, Any]):
        """
        Save or update a paired device.

        Args:
            device_info (Dict[str, Any]): Dictionary containing device information to save.
        """
        self.device_store.add_or_update_device(device_info)

    def remove_device(self, address: str):
        """
        Remove a device from storage.

        Args:
            address (str): The IP address of the device to remove.
        """
        self.device_store.remove_device(address)
