#!/usr/bin/env python3
"""Background service for monitoring and auto-connecting to paired devices."""

import subprocess
import threading
import time
from typing import Callable, Dict, Optional

from zeroconf import IPVersion, ServiceBrowser, ServiceStateChange, Zeroconf

from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger("DeviceMonitor")


class DeviceMonitor:
    """Monitors network for paired devices and auto-connects when found."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DeviceMonitor, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the device monitor singleton."""
        if self._initialized:
            return

        self._initialized = True
        self._running = False
        self._zeroconf = None
        self._browsers = []
        self._monitor_thread = None
        self._paired_devices = {}  # {model: {address, connect_port, pair_port, name}}
        self._device_by_address = {}  # {address: model} - for quick IP lookups
        self._connected_devices = set()  # Addresses of currently connected devices
        self._discovered_services = {}  # Temporary storage for mDNS discoveries

        # Initialize callbacks dict here
        self._callbacks = {
            "on_device_found": [],
            "on_device_connected": [],
            "on_device_lost": [],
        }

        # Load settings
        self._settings = SettingsManager()
        self._auto_connect_enabled = self._settings.get("app", "auto_connect", True)
        self._monitor_interval = self._settings.get("app", "monitor_interval", 5)
        self._keep_alive_interval = self._settings.get("adb", "keep_alive_interval", 0)

        # Register settings callbacks for live updates
        self._settings.register_callback("app", "auto_connect", self._on_auto_connect_changed)
        self._settings.register_callback(
            "app", "monitor_interval", self._on_monitor_interval_changed
        )
        self._settings.register_callback(
            "adb", "keep_alive_interval", self._on_keep_alive_interval_changed
        )

    def _on_keep_alive_interval_changed(self, new_value):
        self._keep_alive_interval = new_value
        logger.info(f"ADB keep-alive interval set to {new_value} seconds")

    def _on_auto_connect_changed(self, new_value):
        """Handle auto_connect setting change."""
        self._auto_connect_enabled = new_value
        logger.info(f"Auto-connect {'enabled' if new_value else 'disabled'}")

    def _on_monitor_interval_changed(self, new_value):
        """Handle monitor_interval setting change."""
        self._monitor_interval = new_value
        logger.info(f"Monitor interval set to {new_value} seconds")

    def set_paired_devices(self, devices: list):
        """Update the list of paired devices to monitor."""
        self._paired_devices.clear()
        self._device_by_address.clear()
        for device in devices:
            address = device.get("address")
            if address:
                # Store by address for quick lookup
                self._paired_devices[address] = {
                    "name": device.get("name", "Unknown"),
                    "model": device.get("model"),
                    "connect_port": device.get("connect_port"),
                    "pair_port": device.get("pair_port"),
                }
        logger.debug(f"Monitoring {len(self._paired_devices)} paired devices")

    def start(self):
        """Start monitoring for devices."""
        if self._running:
            logger.debug("Monitor already running")
            return

        logger.info("Starting device monitor...")
        self._running = True

        # Start mDNS discovery
        self._start_mdns_discovery()

        # Start connection monitor thread
        self._monitor_thread = threading.Thread(target=self._monitor_connections, daemon=True)
        self._monitor_thread.start()

        logger.info("Device monitor started")

    def stop(self):
        """Stop monitoring."""
        if not self._running:
            return

        logger.info("Stopping device monitor...")
        self._running = False

        # Stop mDNS
        if self._browsers:
            for browser in self._browsers:
                try:
                    browser.cancel()
                except Exception as e:
                    logger.debug(f"Error stopping browser: {e}")
            self._browsers.clear()

        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception as e:
                logger.debug(f"Error closing zeroconf: {e}")
            self._zeroconf = None

        logger.info("Device monitor stopped")

    def _start_mdns_discovery(self):
        """Start mDNS service discovery for ADB devices."""
        try:
            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)

            # Handler for connect services (these are the ones we want to auto-connect to)
            def on_connect_service_change(zeroconf, service_type, name, state_change):
                if state_change == ServiceStateChange.Added:
                    info = zeroconf.get_service_info(service_type, name)
                    if info and info.addresses:
                        address = ".".join(map(str, info.addresses[0]))
                        port = info.port
                        # Extract device model from service name (format: "adb-<model>-<random>._adb-tls-connect._tcp.local.")
                        model = self._extract_model_from_service_name(name)
                        self._handle_device_discovered(address, port, "connect", model)
                elif state_change == ServiceStateChange.Removed:
                    info = zeroconf.get_service_info(service_type, name)
                    if info and info.addresses:
                        address = ".".join(map(str, info.addresses[0]))
                        self._handle_device_lost(address)

            # Handler for pairing services
            def on_pair_service_change(zeroconf, service_type, name, state_change):
                if state_change == ServiceStateChange.Added:
                    info = zeroconf.get_service_info(service_type, name)
                    if info and info.addresses:
                        address = ".".join(map(str, info.addresses[0]))
                        port = info.port
                        model = self._extract_model_from_service_name(name)
                        self._handle_device_discovered(address, port, "pair", model)

            # Browse for both service types
            browser_connect = ServiceBrowser(
                self._zeroconf,
                "_adb-tls-connect._tcp.local.",
                handlers=[on_connect_service_change],
            )
            browser_pair = ServiceBrowser(
                self._zeroconf,
                "_adb-tls-pairing._tcp.local.",
                handlers=[on_pair_service_change],
            )

            self._browsers = [browser_connect, browser_pair]
            logger.debug("mDNS discovery started")

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")

    def _extract_model_from_service_name(self, service_name: str) -> str:
        """Extract device model from mDNS service name.

        Service name format: adb-<model>-<random>._adb-tls-<type>._tcp.local.
        Example: adb-beryl-abc123._adb-tls-connect._tcp.local.
        Returns: model (e.g., 'beryl')
        """
        try:
            # Remove service type suffix
            base_name = service_name.split("._adb-tls-")[0]
            # Remove 'adb-' prefix
            if base_name.startswith("adb-"):
                base_name = base_name[4:]
            # Extract model (part before last hyphen + random string)
            # Usually format is: <model>-<random>
            parts = base_name.split("-")
            if len(parts) >= 2:
                # Model is everything except the last part (which is random)
                model = "-".join(parts[:-1])
                return model
            return base_name
        except Exception as e:
            logger.debug(f"Could not extract model from service name {service_name}: {e}")
            return ""

    def _handle_device_discovered(
        self, address: str, port: int, service_type: str, model: str = ""
    ):
        """Handle a device discovered via mDNS."""
        logger.debug(f"Discovered {service_type} service: {address}:{port}")

        # Store in temporary discovery cache
        if address not in self._discovered_services:
            self._discovered_services[address] = {}

        if service_type == "connect":
            self._discovered_services[address]["connect_port"] = port
        elif service_type == "pair":
            self._discovered_services[address]["pair_port"] = port

        # Notify callbacks
        for callback in self._callbacks["on_device_found"]:
            try:
                callback(address, port, service_type)
            except Exception as e:
                logger.error(f"Error in device found callback: {e}")

        # Auto-connect to discovered device if it's in our paired list OR if we only have one paired device
        if (
            self._auto_connect_enabled
            and service_type == "connect"
            and address not in self._connected_devices
        ):
            # Check if this exact IP:port is in our paired devices
            if address in self._paired_devices:
                logger.info(f"Found known paired device at {address}:{port}")
                self._auto_connect_to_device(address, port)
            # If we only have one paired device and this is the only device discovered, connect anyway
            elif len(self._paired_devices) == 1:
                paired_address = list(self._paired_devices.keys())[0]
                paired_device = self._paired_devices[paired_address]
                logger.info(
                    f"Single paired device scenario: {paired_device['name']} expected at {paired_address}, discovered at {address}"
                )
                # Update the address if it changed
                if paired_address != address:
                    logger.info(f"Device IP changed: {paired_address} → {address}")
                    # Update in-memory
                    self._paired_devices[address] = self._paired_devices.pop(paired_address)
                    # Update in storage
                    self._update_device_address(paired_device.get("model"), address, port)
                self._auto_connect_to_device(address, port)

    def _update_device_address(self, model: str, new_address: str, new_port: int):
        """Update device address in storage when IP changes."""
        try:
            # Import here to avoid circular dependencies
            from aurynk.core.device_manager import DeviceStorage

            storage = DeviceStorage()
            devices = storage.load_devices()

            for device in devices:
                if device.get("model") == model:
                    device["address"] = new_address
                    device["connect_port"] = new_port
                    storage.save_device(device)
                    logger.info(f"Updated {model} address to {new_address}:{new_port} in storage")
                    break
        except Exception as e:
            logger.error(f"Failed to update device address in storage: {e}")

    def _handle_device_lost(self, address: str):
        """Handle a device that went offline."""
        logger.debug(f"Device lost: {address}")

        # Remove from discovered services
        if address in self._discovered_services:
            del self._discovered_services[address]

        # Notify user
        try:
            from aurynk.utils.notify import notify_device_event

            # Try to get device name if available
            name = address
            for info in self._paired_devices.values():
                if info.get("address") == address:
                    name = info.get("name", address)
                    break
            notify_device_event("disconnected", device=name)
        except Exception:
            pass

        # Notify callbacks
        for callback in self._callbacks["on_device_lost"]:
            try:
                callback(address)
            except Exception as e:
                logger.error(f"Error in device lost callback: {e}")

    def _auto_connect_to_device(self, address: str, port: int):
        """Automatically connect to a paired device."""
        paired_info = self._paired_devices.get(address)
        if not paired_info:
            return

        device_name = paired_info.get("name", address)
        logger.info(f"Auto-connecting to paired device: {device_name} ({address}:{port})")

        try:
            from aurynk.utils.adb_utils import get_adb_path

            result = subprocess.run(
                [get_adb_path(), "connect", f"{address}:{port}"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            output = (result.stdout + result.stderr).lower()

            if ("connected" in output or "already connected" in output) and "unable" not in output:
                self._connected_devices.add(address)
                logger.info(f"✓ Auto-connected to {device_name}")

                # Notify user
                try:
                    from aurynk.utils.notify import notify_device_event

                    notify_device_event("connected", device=device_name)
                except Exception:
                    pass

                # Small delay to ensure connection is fully established before UI update
                time.sleep(0.5)

                # Always notify callbacks on successful connection (for UI refresh)
                for callback in self._callbacks["on_device_connected"]:
                    try:
                        callback(address, port)
                    except Exception as e:
                        logger.error(f"Error in connected callback: {e}")

                # Update paired device info if port changed
                if paired_info.get("connect_port") != port:
                    logger.info(
                        f"Port changed from {paired_info.get('connect_port')} to {port}, updating..."
                    )
                    paired_info["connect_port"] = port
            else:
                logger.warning(f"Failed to auto-connect to {device_name}: {output}")

        except Exception as e:
            logger.error(f"Error auto-connecting to {device_name}: {e}")

    def _monitor_connections(self):
        """Background thread to monitor ADB connection status and send keep-alive if enabled."""
        previous_connected = set()
        last_keep_alive = time.time()

        while self._running:
            try:
                # Check which devices are actually connected
                from aurynk.utils.adb_utils import get_adb_path

                result = subprocess.run(
                    [get_adb_path(), "devices"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    # Parse connected devices
                    current_connected = set()
                    for line in result.stdout.splitlines():
                        if "\tdevice" in line:
                            # Extract address from "IP:PORT\tdevice"
                            serial = line.split("\t")[0]
                            if ":" in serial:
                                address = serial.rsplit(":", 1)[0]
                                current_connected.add(address)

                    # Detect disconnections (devices that were connected but aren't anymore)
                    disconnected = previous_connected - current_connected
                    for address in disconnected:
                        logger.info(f"Device disconnected: {address}")
                        # Notify user
                        try:
                            from aurynk.utils.notify import notify_device_event

                            notify_device_event("disconnected", device=address)
                        except Exception:
                            pass
                        # Notify callbacks about disconnection
                        for callback in self._callbacks["on_device_lost"]:
                            try:
                                callback(address)
                            except Exception as e:
                                logger.error(f"Error in device lost callback: {e}")

                    # Detect new connections (for devices that weren't tracked before)
                    newly_connected = current_connected - previous_connected
                    if newly_connected:
                        logger.debug(f"Newly detected connections: {newly_connected}")
                        # Notify user for each new connection
                        try:
                            from aurynk.utils.notify import notify_device_event

                            for address in newly_connected:
                                notify_device_event("connected", device=address)
                        except Exception:
                            pass

                    # Update internal state
                    self._connected_devices = current_connected
                    previous_connected = current_connected.copy()

                    # --- KEEP ALIVE LOGIC ---
                    now = time.time()
                    if self._keep_alive_interval and self._keep_alive_interval > 0:
                        if now - last_keep_alive >= self._keep_alive_interval:
                            for address in current_connected:
                                try:
                                    # Send a harmless keep-alive command (adb shell echo)
                                    serial = address
                                    subprocess.run(
                                        [get_adb_path(), "-s", serial, "shell", "echo", "ping"],
                                        capture_output=True,
                                        timeout=5,
                                    )
                                    logger.debug(f"Sent keep-alive to {serial}")
                                except Exception as e:
                                    logger.debug(f"Keep-alive failed for {address}: {e}")
                            last_keep_alive = now

                else:
                    logger.debug("adb devices command failed")

            except Exception as e:
                logger.debug(f"Error monitoring connections: {e}")
                try:
                    from aurynk.utils.notify import notify_device_event

                    notify_device_event("error", device="Device Monitor", extra=str(e), error=True)
                except Exception:
                    pass

            # Sleep before next check - use setting value
            time.sleep(self._monitor_interval)

    def register_callback(self, event: str, callback: Callable):
        """Register a callback for device events.

        Events:
            - on_device_found: (address, port, service_type)
            - on_device_connected: (address, port)
            - on_device_lost: (address)
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def is_device_connected(self, address: str) -> bool:
        """Check if a device is currently connected."""
        return address in self._connected_devices

    def get_discovered_device(self, address: str) -> Optional[Dict]:
        """Get discovered service info for a device."""
        return self._discovered_services.get(address)

    def set_auto_connect(self, enabled: bool):
        """Enable or disable auto-connect."""
        self._auto_connect_enabled = enabled
        logger.info(f"Auto-connect {'enabled' if enabled else 'disabled'}")

    def remove_device(self, address: str):
        """Remove a paired device by address."""
        if address in self._paired_devices:
            del self._paired_devices[address]
