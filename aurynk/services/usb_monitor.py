"""USB monitor service for detecting Android devices."""

from typing import Optional, Set

import pyudev

from aurynk.utils.logger import get_logger

# Import GObject and GLib, handling the case where they are not available (e.g., testing)
try:
    import gi

    gi.require_version("GObject", "2.0")
    from gi.repository import GLib, GObject
except (ImportError, ValueError):
    # Create dummy classes for testing/linting in environments without GObject
    class GObject:  # type: ignore
        class Object:
            def __init__(self):
                pass

        class SignalFlags:
            RUN_LAST = 1

        def Signal(self, *args, **kwargs):
            pass

    class GLib:  # type: ignore
        IO_IN = 1

        @staticmethod
        def io_add_watch(fd, condition, callback):
            return 1

        @staticmethod
        def source_remove(id):
            pass


logger = get_logger("USBMonitor")

# Common Android USB Vendor IDs (hex strings, lowercase)
ANDROID_VENDOR_IDS: Set[str] = {
    "18d1",  # Google
    "04e8",  # Samsung
    "0bb4",  # HTC
    "22b8",  # Motorola
    "1004",  # LG
    "12d1",  # Huawei
    "2717",  # Xiaomi
    "0fce",  # Sony
    "2a70",  # OnePlus
    "19d2",  # ZTE
    "0b05",  # Asus
    "17ef",  # Lenovo
    "0955",  # Nvidia
    "2a45",  # Meizu
}


class USBMonitor(GObject.Object):
    """Monitors USB subsystem for Android devices."""

    __gsignals__ = {
        "device-connected": (GObject.SignalFlags.RUN_LAST, None, (object,)),
        "device-disconnected": (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self) -> None:
        """Initialize the USB monitor."""
        super().__init__()
        self._context = pyudev.Context()
        self._monitor = pyudev.Monitor.from_netlink(self._context)
        self._monitor.filter_by(subsystem="usb")
        self._watch_id: Optional[int] = None
        self._running = False

    def start(self) -> None:
        """Start monitoring for USB events."""
        if self._running:
            return

        # Start the monitor (binds the socket)
        self._monitor.start()

        # Add watch to GLib main loop
        self._watch_id = GLib.io_add_watch(
            self._monitor.fileno(), GLib.IO_IN, self._on_monitor_event
        )
        self._running = True
        logger.info("USB Monitor started")

    def get_connected_devices(self) -> list[pyudev.Device]:
        """Get currently connected Android devices."""
        devices = []
        try:
            for device in self._context.list_devices(subsystem="usb"):
                if self._is_android_device(device):
                    devices.append(device)
        except Exception as e:
            logger.error(f"Error listing USB devices: {e}")
        return devices

    def stop(self) -> None:
        """Stop monitoring."""
        if not self._running:
            return

        if self._watch_id:
            GLib.source_remove(self._watch_id)
            self._watch_id = None

        # Note: pyudev Monitor doesn't have a stop() method to unbind,
        # but stopping the watch is sufficient.
        self._running = False
        logger.info("USB Monitor stopped")

    def _on_monitor_event(self, source: int, condition: int) -> bool:
        """Handle monitor event from GLib main loop.

        Args:
            source: The file descriptor.
            condition: The IO condition.

        Returns:
            True to keep watching, False to stop.
        """
        if condition & GLib.IO_IN:
            device = self._monitor.poll(timeout=0)
            if device:
                self._process_device(device)
        return True

    def _process_device(self, device: pyudev.Device) -> None:
        """Process a udev device event.

        Args:
            device: The pyudev Device object.
        """
        action = device.action
        if action == "add":
            if self._is_android_device(device):
                serial = device.get("ID_SERIAL", "unknown")
                logger.info(f"Android device connected: {serial}")
                self.emit("device-connected", device)
        elif action == "remove":
            # On remove, we check if it was likely an Android device
            if self._is_android_device(device):
                serial = device.get("ID_SERIAL", "unknown")
                logger.info(f"Android device disconnected: {serial}")
                self.emit("device-disconnected", device)

    def _is_android_device(self, device: pyudev.Device) -> bool:
        """Check if the device is likely an Android device.

        Args:
            device: The pyudev Device object.

        Returns:
            True if it matches Android criteria.
        """
        # 1. Check ID_SERIAL containing "Android" (case insensitive)
        serial = device.get("ID_SERIAL", "")
        if serial and ("Android" in serial or "android" in serial.lower()):
            return True

        # 2. Check Vendor ID
        vendor_id = device.get("ID_VENDOR_ID")
        if vendor_id and vendor_id.lower() in ANDROID_VENDOR_IDS:
            return True

        return False
