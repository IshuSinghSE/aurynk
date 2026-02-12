import json
import os
import unittest
from unittest.mock import call, patch

from aurynk.core.device_manager import DeviceStore


class TestDeviceStore(unittest.TestCase):
    def setUp(self):
        # Create a temporary file path
        self.test_file = os.path.abspath("test_devices.json")
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        # Patch dependencies
        self.notify_patcher = patch("aurynk.utils.device_events.notify_device_changed")
        self.mock_notify = self.notify_patcher.start()

        self.notification_patcher = patch("aurynk.utils.notify.show_notification")
        self.mock_notification = self.notification_patcher.start()

        self.subprocess_patcher = patch("subprocess.run")
        self.mock_subprocess = self.subprocess_patcher.start()

        self.adb_path_patcher = patch("aurynk.utils.adb_utils.get_adb_path")
        self.mock_adb_path = self.adb_path_patcher.start()
        self.mock_adb_path.return_value = "adb"

        # Patch threading to avoid background threads
        self.thread_patcher = patch("threading.Thread")
        self.mock_thread = self.thread_patcher.start()

    def tearDown(self):
        self.notify_patcher.stop()
        self.notification_patcher.stop()
        self.subprocess_patcher.stop()
        self.adb_path_patcher.stop()
        self.thread_patcher.stop()

        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_init_empty(self):
        """Test initialization with non-existent file."""
        store = DeviceStore(self.test_file)
        self.assertEqual(store.get_devices(), [])

    def test_init_existing(self):
        """Test initialization with existing file."""
        devices = [{"address": "192.168.1.1", "name": "Test Device"}]
        with open(self.test_file, "w") as f:
            json.dump(devices, f)

        store = DeviceStore(self.test_file)
        self.assertEqual(store.get_devices(), devices)

    def test_init_corrupted(self):
        """Test initialization with corrupted file."""
        with open(self.test_file, "w") as f:
            f.write("{invalid_json")

        store = DeviceStore(self.test_file)
        self.assertEqual(store.get_devices(), [])

    def test_add_or_update_device(self):
        """Test adding and updating devices."""
        store = DeviceStore(self.test_file)

        # Add new device
        device_info = {"address": "192.168.1.5", "name": "Phone 1", "connect_port": "5555"}
        store.add_or_update_device(device_info)

        self.assertEqual(len(store.get_devices()), 1)
        self.assertEqual(store.get_devices()[0], device_info)

        # Verify file saved
        with open(self.test_file, "r") as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, [device_info])

        # Verify notifications
        self.mock_notify.assert_called()
        self.mock_notification.assert_called_with("Device added", "Phone 1")

        # Update existing device
        update_info = {"address": "192.168.1.5", "name": "Phone 1 Updated", "connect_port": "5555"}
        store.add_or_update_device(update_info)

        self.assertEqual(len(store.get_devices()), 1)
        self.assertEqual(store.get_devices()[0]["name"], "Phone 1 Updated")
        self.mock_notification.assert_called_with("Device updated", "Phone 1 Updated")

    def test_remove_device_connected(self):
        """Test removing a connected device."""
        store = DeviceStore(self.test_file)
        device_info = {
            "address": "192.168.1.10",
            "name": "Tablet",
            "connect_port": "5555",
            "pair_port": "4444",
        }
        store.add_or_update_device(device_info)

        # Mock ADB 'devices' output to simulate connected device
        self.mock_subprocess.return_value.stdout = (
            "List of devices attached\n192.168.1.10:5555\tdevice\n"
        )
        self.mock_subprocess.return_value.returncode = 0

        store.remove_device("192.168.1.10")

        # Verify device removed
        self.assertEqual(store.get_devices(), [])

        # Verify ADB commands
        calls = [
            call(["adb", "devices"], capture_output=True, text=True),
            call(["adb", "disconnect", "192.168.1.10:5555"], check=False),
            call(["adb", "unpair", "192.168.1.10:5555"], capture_output=True, text=True, timeout=5),
        ]
        self.mock_subprocess.assert_has_calls(calls, any_order=True)

        # Verify notification
        self.mock_notification.assert_called()

    def test_remove_device_not_connected(self):
        """Test removing a device that is not connected."""
        store = DeviceStore(self.test_file)
        device_info = {"address": "192.168.1.11", "name": "Tablet 2", "connect_port": "5555"}
        store.add_or_update_device(device_info)

        # Mock ADB 'devices' output to show NO connected device
        self.mock_subprocess.return_value.stdout = "List of devices attached\n"
        self.mock_subprocess.return_value.returncode = 0

        store.remove_device("192.168.1.11")

        # Verify device removed
        self.assertEqual(store.get_devices(), [])

        # Verify disconnect NOT called
        disconnect_call = call(["adb", "disconnect", "192.168.1.11:5555"], check=False)
        self.assertNotIn(disconnect_call, self.mock_subprocess.call_args_list)

    def test_clear(self):
        """Test clearing all devices."""
        store = DeviceStore(self.test_file)
        store.add_or_update_device({"address": "1.1.1.1"})
        store.add_or_update_device({"address": "2.2.2.2"})

        self.assertEqual(len(store.get_devices()), 2)

        store.clear()

        self.assertEqual(store.get_devices(), [])
        with open(self.test_file, "r") as f:
            self.assertEqual(json.load(f), [])

    def test_reload(self):
        """Test reloading from file."""
        store = DeviceStore(self.test_file)
        store.add_or_update_device({"address": "1.1.1.1"})

        # Modify file externally
        external_update = [{"address": "3.3.3.3", "name": "External Device"}]
        with open(self.test_file, "w") as f:
            json.dump(external_update, f)

        store.reload()

        self.assertEqual(store.get_devices(), external_update)
