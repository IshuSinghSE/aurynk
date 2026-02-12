import unittest
from aurynk.services.device_monitor import DeviceMonitor

class TestDeviceMonitor(unittest.TestCase):
    def setUp(self):
        # Reset singleton if possible or just create new instance logic
        # Since it's a singleton, we need to be careful.
        # But for unit testing logic, reusing instance is okay if we clean up.
        self.monitor = DeviceMonitor()
        self.monitor._connected_devices.clear()
        self.monitor._connected_serials.clear()

    def test_device_monitor_add_remove(self):
        device = {"address": "192.168.1.5", "connect_port": "5555", "name": "Test Device"}
        self.monitor.set_paired_devices([device])
        self.assertIn(device["address"], self.monitor._paired_devices)
        self.monitor.remove_device(device["address"])
        self.assertNotIn(device["address"], self.monitor._paired_devices)

    def test_update_cache(self):
        # Test adding to cache
        self.monitor.update_cache("192.168.1.5", "5555", True)
        self.assertTrue(self.monitor.is_device_connected("192.168.1.5"))
        self.assertTrue(self.monitor.is_serial_connected("192.168.1.5", "5555"))
        self.assertFalse(self.monitor.is_serial_connected("192.168.1.5", "6666"))

        # Test removing from cache
        self.monitor.update_cache("192.168.1.5", "5555", False)
        self.assertFalse(self.monitor.is_device_connected("192.168.1.5"))
        self.assertFalse(self.monitor.is_serial_connected("192.168.1.5", "5555"))

    def test_update_cache_multiple_ports(self):
        # Add two ports for same IP
        self.monitor.update_cache("192.168.1.5", "5555", True)
        self.monitor.update_cache("192.168.1.5", "6666", True)

        self.assertTrue(self.monitor.is_device_connected("192.168.1.5"))
        self.assertTrue(self.monitor.is_serial_connected("192.168.1.5", "5555"))
        self.assertTrue(self.monitor.is_serial_connected("192.168.1.5", "6666"))

        # Remove one port
        self.monitor.update_cache("192.168.1.5", "5555", False)
        self.assertTrue(self.monitor.is_device_connected("192.168.1.5")) # Still connected on 6666
        self.assertFalse(self.monitor.is_serial_connected("192.168.1.5", "5555"))
        self.assertTrue(self.monitor.is_serial_connected("192.168.1.5", "6666"))

        # Remove second port
        self.monitor.update_cache("192.168.1.5", "6666", False)
        self.assertFalse(self.monitor.is_device_connected("192.168.1.5"))

if __name__ == '__main__':
    unittest.main()
