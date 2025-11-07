#!/usr/bin/env python3
"""ADB/scrcpy controller for device management."""

import os
from aurynk.utils.device_store import DeviceStore
import random
import string
import subprocess
import threading
from datetime import datetime
from typing import Optional, Callable, List, Dict, Any
from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, IPVersion




DEVICE_STORE_DIR = os.path.join(os.path.expanduser("~"), ".local", "share", "aurynk")
DEVICE_STORE_PATH = os.path.join(DEVICE_STORE_DIR, "paired_devices.json")

# ~/.local/share/aurynk/paired_devices.json

class ADBController:
    """Handles all ADB and device management operations."""

    def __init__(self):
        """Initialize the ADB controller."""
        self.device_store = DeviceStore(DEVICE_STORE_PATH)

    # ===== Device Pairing =====

    def generate_code(self, length: int = 5) -> str:
        """Generate a random code for pairing."""
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
            address: Device IP address
            pair_port: Port for pairing
            connect_port: Port for connection (may differ from pair_port)
            password: Pairing password
            status_callback: Optional callback for status updates
            
        Returns:
            True if successful, False otherwise
        """
        import time

        def log(msg: str):
            print(f"[ADB] {msg}")
            if status_callback:
                status_callback(msg)

        # Step 1: Pair
        log(f"Pairing with {address}:{pair_port}...")
        pair_cmd = ["adb", "pair", f"{address}:{pair_port}", password]
        pair_result = subprocess.run(pair_cmd, capture_output=True, text=True)

        if pair_result.returncode == 0:
            log(f"✓ Paired successfully")
        else:
            log(f"⚠ Pairing failed: {pair_result.stderr.strip() or pair_result.stdout.strip()}")

        # Step 2: Connect (attempt even if pairing failed)
        log(f"Connecting to {address}:{connect_port}...")
        connected = False
        
        for attempt in range(5):
            connect_cmd = ["adb", "connect", f"{address}:{connect_port}"]
            connect_result = subprocess.run(connect_cmd, capture_output=True, text=True)
            output = (connect_result.stdout + connect_result.stderr).lower()
            
            if ("connected" in output or "already connected" in output) and "unable" not in output:
                connected = True
                log(f"✓ Connected successfully")
                break
            
            time.sleep(1)

        if not connected:
            log(f"✗ Could not connect to {address}:{connect_port}")
            return False

        # Step 3: Fetch device details
        log("Fetching device information...")
        device_info = self._fetch_device_info(address, connect_port)
        device_info.update({
            "address": address,
            "pair_port": pair_port,
            "connect_port": connect_port,
            "password": password,
        })

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
            on_device_found: Callback when a device is found (address, pair_port, connect_port, password)
            network_name: Expected network SSID
            password: Pairing password
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
                if state_change is ServiceStateChange.Added and service_type == expected_service_type:
                    info = zeroconf.get_service_info(service_type, name)
                    if info:
                        address = ".".join(map(str, info.addresses[0])) if info.addresses else None
                        port = info.port
                        handle_found(address, service_type, port)
            return on_service_state_change

        # Browse for both ADB pairing and connect services
        browser_pair = ServiceBrowser(zeroconf, "_adb-tls-pairing._tcp.local.", handlers=[make_handler("_adb-tls-pairing._tcp.local.")])
        browser_connect = ServiceBrowser(zeroconf, "_adb-tls-connect._tcp.local.", handlers=[make_handler("_adb-tls-connect._tcp.local.")])

        return zeroconf, (browser_pair, browser_connect)

    # ===== Device Information =====

    def _fetch_device_info(self, address: str, connect_port: int) -> Dict[str, Any]:
        """Fetch detailed device information via ADB."""
        serial = f"{address}:{connect_port}"
        device_info = {}

        # Helper to run adb shell command
        def get_prop(prop: str) -> str:
            try:
                result = subprocess.run(
                    ["adb", "-s", serial, "shell", "getprop", prop],
                    capture_output=True,
                    text=True,
                    timeout=5,
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
        """Fetch device specifications (RAM, storage, battery)."""
        serial = f"{address}:{connect_port}"
        specs = {"ram": "", "storage": "", "battery": ""}

        try:
            # RAM
            meminfo = subprocess.run(
                ["adb", "-s", serial, "shell", "cat", "/proc/meminfo"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            import re
            match = re.search(r"MemTotal:\s+(\d+) kB", meminfo.stdout)
            if match:
                ram_mb = int(match.group(1)) // 1000
                ram_gb = ram_mb / 1000
                specs["ram"] = f"{round(ram_gb)} GB"

            # Storage
            df = subprocess.run(
                ["adb", "-s", serial, "shell", "df", "/data"],
                capture_output=True,
                text=True,
                timeout=5,
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
                ["adb", "-s", serial, "shell", "dumpsys", "battery"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            match = re.search(r"level: (\d+)", battery.stdout)
            if match:
                specs["battery"] = f"{match.group(1)}%"

        except Exception as e:
            print(f"[ADB] Error fetching specs: {e}")

        return specs

    def capture_screenshot(self, address: str, connect_port: int) -> Optional[str]:
        """Capture device screenshot and return local path. If locked or screen off, use old image. Otherwise, go to home, take screenshot, return to previous app. Screenshots are stored in ~/.local/share/aurynk/screenshots/."""
        serial = f"{address}:{connect_port}"
        screenshot_dir = os.path.join(DEVICE_STORE_DIR, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        local_path = os.path.join(screenshot_dir, f"aurynk_{address.replace('.', '_')}_screen.png")
        try:
            # 1. Check if device is locked or screen is off
            # Check screen state
            dumpsys = subprocess.run(
                ["adb", "-s", serial, "shell", "dumpsys", "window"],
                capture_output=True, text=True, timeout=5
            )
            screen_off = "mDreamingLockscreen=true" in dumpsys.stdout or "mScreenOn=false" in dumpsys.stdout or "mInteractive=false" in dumpsys.stdout
            # Check keyguard (lock)
            keyguard = subprocess.run(
                ["adb", "-s", serial, "shell", "dumpsys", "window", "windows"],
                capture_output=True, text=True, timeout=5
            )
            locked = "mShowingLockscreen=true" in keyguard.stdout or "mDreamingLockscreen=true" in keyguard.stdout
            if screen_off or locked:
                # Use old image if exists
                if os.path.exists(local_path):
                    return local_path
                else:
                    print("[ADB] Device is locked or screen off, and no previous screenshot available.")
                    return None

            # 2. Get current foreground app/activity
            activity_result = subprocess.run(
                ["adb", "-s", serial, "shell", "dumpsys", "window", "windows"],
                capture_output=True, text=True, timeout=5
            )
            import re
            match = re.search(r"mCurrentFocus=Window\{[^ ]+ ([^/]+)/([^ ]+)\}", activity_result.stdout)
            current_app = match.group(1) if match else None
            current_activity = match.group(2) if match else None

            # 3. Go to home screen
            subprocess.run(["adb", "-s", serial, "shell", "input", "keyevent", "3"], check=True, timeout=5)

            # 4. Take screenshot on home
            subprocess.run(
                ["adb", "-s", serial, "shell", "screencap", "-p", "/sdcard/aurynk_screen.png"],
                check=True,
                timeout=10,
            )

            # 5. Return to previous app if possible
            if current_app:
                subprocess.run(["adb", "-s", serial, "shell", "monkey", "-p", current_app, "1"], timeout=5)

            # 6. Pull to local temp directory
            subprocess.run(
                ["adb", "-s", serial, "pull", "/sdcard/aurynk_screen.png", local_path],
                check=True,
                timeout=10,
            )
            return local_path
        except Exception as e:
            print(f"[ADB] Error capturing screenshot: {e}")
            # If error, fallback to old image if available
            if os.path.exists(local_path):
                return local_path
            return None

    # ===== Device Storage =====

    def load_paired_devices(self) -> List[Dict[str, Any]]:
        """Get paired devices from in-memory store."""
        return self.device_store.get_devices()

    def save_paired_device(self, device_info: Dict[str, Any]):
        """Save or update a paired device."""
        self.device_store.add_or_update_device(device_info)

    def remove_device(self, address: str):
        """Remove a device from storage."""
        self.device_store.remove_device(address)
