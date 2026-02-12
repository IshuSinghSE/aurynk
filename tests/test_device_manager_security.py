import os
import shutil
import tempfile
import unittest

from aurynk.core.device_manager import DeviceStore


class TestDeviceManagerSecurity(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.file_path = os.path.join(self.temp_dir, "devices.json")
        self.store = DeviceStore(self.file_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_file_permissions(self):
        """Test that the device store file has secure permissions (600)."""
        self.store.add_or_update_device({"address": "192.168.1.100", "name": "Test Device"})

        # Verify file exists
        self.assertTrue(os.path.exists(self.file_path))

        # Check permissions
        st = os.stat(self.file_path)
        mode = st.st_mode & 0o777

        # Should be 0o600 (rw-------)
        self.assertEqual(mode, 0o600, f"File permissions should be 0600, but got {oct(mode)}")

    def test_existing_file_permissions_update(self):
        """Test that an existing file with insecure permissions is updated to 600."""
        # Create a file with insecure permissions
        with open(self.file_path, "w") as f:
            f.write("[]")
        os.chmod(self.file_path, 0o664)

        # Reload store (or just force save)
        self.store.add_or_update_device({"address": "192.168.1.101", "name": "Another Device"})

        st = os.stat(self.file_path)
        mode = st.st_mode & 0o777
        self.assertEqual(mode, 0o600, f"File permissions should be updated to 0600, but got {oct(mode)}")

if __name__ == "__main__":
    unittest.main()
