import sys
import unittest
from unittest.mock import MagicMock, Mock

# --- MOCK SETUP START ---
# Mock gi
mock_gi = MagicMock()
mock_gi.require_version = MagicMock()

# Mock GLib
mock_glib = MagicMock()
mock_glib.IO_IN = 1
mock_glib.io_add_watch = MagicMock(return_value=123)
mock_glib.source_remove = MagicMock()

# Mock GObject
mock_gobject = MagicMock()


class MockGObjectBase:
    def __init__(self):
        self.signals_emitted = []

    def emit(self, signal_name, *args):
        # print(f"DEBUG: MockGObjectBase.emit {signal_name}")
        self.signals_emitted.append((signal_name, args))


mock_gobject.Object = MockGObjectBase
mock_gobject.SignalFlags = MagicMock()
mock_gobject.SignalFlags.RUN_LAST = 1

# Setup gi.repository
mock_repo = MagicMock()
mock_repo.GLib = mock_glib
mock_repo.GObject = mock_gobject

sys.modules["gi"] = mock_gi
sys.modules["gi.repository"] = mock_repo
sys.modules["gi.repository.GLib"] = mock_glib
sys.modules["gi.repository.GObject"] = mock_gobject

# Mock pyudev
mock_pyudev = MagicMock()
sys.modules["pyudev"] = mock_pyudev
# --- MOCK SETUP END ---

from aurynk.services.usb_monitor import USBMonitor


class TestUSBMonitor(unittest.TestCase):
    def setUp(self):
        # Reset mocks
        mock_pyudev.reset_mock()
        mock_glib.io_add_watch.reset_mock()
        mock_glib.source_remove.reset_mock()

        # Setup pyudev returns
        self.mock_context = Mock(name="context")
        self.mock_monitor = Mock(name="monitor")

        # Ensure side_effect is None
        mock_pyudev.Context.side_effect = None
        mock_pyudev.Context.return_value = self.mock_context

        mock_pyudev.Monitor.from_netlink.side_effect = None
        mock_pyudev.Monitor.from_netlink.return_value = self.mock_monitor

        self.monitor = USBMonitor()

    def test_initialization(self):
        mock_pyudev.Context.assert_called_once()
        mock_pyudev.Monitor.from_netlink.assert_called_once_with(self.mock_context)
        self.mock_monitor.filter_by.assert_called_once_with(subsystem="usb")

    def test_start_monitoring(self):
        self.monitor.start()
        self.mock_monitor.start.assert_called_once()
        self.assertTrue(self.monitor._running)
        mock_glib.io_add_watch.assert_called_once()

    def test_stop_monitoring(self):
        self.monitor.start()
        self.monitor.stop()
        self.assertFalse(self.monitor._running)
        mock_glib.source_remove.assert_called_once_with(123)

    def test_android_detection_by_serial(self):
        mock_device = Mock(name="device")
        mock_device.action = "add"

        def get_side_effect(key, default=None):
            if key == "ID_SERIAL":
                return "Android"
            return default

        mock_device.get.side_effect = get_side_effect

        self.monitor._process_device(mock_device)

        self.assertEqual(len(self.monitor.signals_emitted), 1)
        self.assertEqual(self.monitor.signals_emitted[0][0], "device-connected")

    def test_android_detection_by_vendor(self):
        mock_device = Mock(name="device")
        mock_device.action = "add"

        def get_side_effect(key, default=None):
            if key == "ID_VENDOR_ID":
                return "18d1"
            return default

        mock_device.get.side_effect = get_side_effect

        self.monitor._process_device(mock_device)

        self.assertEqual(len(self.monitor.signals_emitted), 1)
        self.assertEqual(self.monitor.signals_emitted[0][0], "device-connected")

    def test_ignore_non_android(self):
        mock_device = Mock(name="device")
        mock_device.action = "add"
        mock_device.get.return_value = None

        self.monitor._process_device(mock_device)

        self.assertEqual(len(self.monitor.signals_emitted), 0)

    def test_device_removal(self):
        mock_device = Mock(name="device")
        mock_device.action = "remove"

        def get_side_effect(key, default=None):
            if key == "ID_SERIAL":
                return "Android"
            return default

        mock_device.get.side_effect = get_side_effect

        self.monitor._process_device(mock_device)

        self.assertEqual(len(self.monitor.signals_emitted), 1)
        self.assertEqual(self.monitor.signals_emitted[0][0], "device-disconnected")


if __name__ == "__main__":
    unittest.main()
