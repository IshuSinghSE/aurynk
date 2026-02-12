import unittest
from unittest.mock import patch, MagicMock
import os
import shlex
from aurynk.utils.adb_utils import get_adb_path, is_device_connected, clear_device_notifications, send_device_notification

class TestAdbUtils(unittest.TestCase):

    @patch('aurynk.utils.settings.SettingsManager')
    def test_get_adb_path_default(self, mock_settings_manager):
        # Setup mock to return empty
        mock_settings_manager.return_value.get.return_value = ""

        path = get_adb_path()
        self.assertEqual(path, "adb")

    @patch('aurynk.utils.settings.SettingsManager')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_get_adb_path_custom(self, mock_access, mock_isfile, mock_settings_manager):
        custom_path = "/usr/bin/custom_adb"
        mock_settings_manager.return_value.get.return_value = custom_path
        mock_isfile.return_value = True
        mock_access.return_value = True

        path = get_adb_path()
        self.assertEqual(path, custom_path)
        mock_isfile.assert_called_with(custom_path)
        mock_access.assert_called_with(custom_path, os.X_OK)

    @patch('aurynk.utils.settings.SettingsManager')
    @patch('os.path.isfile')
    def test_get_adb_path_invalid(self, mock_isfile, mock_settings_manager):
        custom_path = "/invalid/path"
        mock_settings_manager.return_value.get.return_value = custom_path
        mock_isfile.return_value = False

        path = get_adb_path()
        self.assertEqual(path, "adb")

    @patch('aurynk.utils.settings.SettingsManager')
    def test_get_adb_path_exception(self, mock_settings_manager):
        mock_settings_manager.side_effect = Exception("Config error")

        path = get_adb_path()
        self.assertEqual(path, "adb")

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_is_device_connected_true(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "List of devices attached\n192.168.1.5:5555\tdevice\n"

        result = is_device_connected("192.168.1.5", 5555)
        self.assertTrue(result)
        mock_run.assert_called_with(["adb", "devices"], capture_output=True, text=True)

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_is_device_connected_false(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "List of devices attached\n"

        result = is_device_connected("192.168.1.5", 5555)
        self.assertFalse(result)

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_is_device_connected_offline(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "List of devices attached\n192.168.1.5:5555\toffline\n"

        result = is_device_connected("192.168.1.5", 5555)
        self.assertFalse(result)

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_is_device_connected_error(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 1

        result = is_device_connected("192.168.1.5", 5555)
        self.assertFalse(result)

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_is_device_connected_exception(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.side_effect = Exception("ADB error")

        result = is_device_connected("192.168.1.5", 5555)
        self.assertFalse(result)

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_clear_device_notifications_success(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 0

        result = clear_device_notifications("serial")
        self.assertTrue(result)
        mock_run.assert_called_with(
            ["adb", "-s", "serial", "shell", "cmd notification cancel aurynk_status"],
            capture_output=True,
            timeout=2
        )

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_clear_device_notifications_failure(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        mock_run.side_effect = Exception("ADB error")

        result = clear_device_notifications("serial")
        self.assertFalse(result)

    @patch('aurynk.utils.adb_utils.clear_device_notifications')
    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_send_device_notification_success(self, mock_run, mock_get_adb_path, mock_clear):
        mock_get_adb_path.return_value = "adb"
        mock_run.return_value.returncode = 0
        mock_clear.return_value = True

        result = send_device_notification("serial", "message", "title")
        self.assertTrue(result)

        mock_clear.assert_called_with("serial")
        # Check that subprocess was called with the correct command
        expected_cmd = f"cmd notification post -S bigtext -t {shlex.quote('title')} aurynk_status {shlex.quote('message')}"
        mock_run.assert_any_call(
            ["adb", "-s", "serial", "shell", expected_cmd],
            capture_output=True, text=True, timeout=3
        )

    @patch('aurynk.utils.adb_utils.get_adb_path')
    @patch('subprocess.run')
    def test_send_device_notification_failure(self, mock_run, mock_get_adb_path):
        mock_get_adb_path.return_value = "adb"
        with patch('aurynk.utils.adb_utils.clear_device_notifications') as mock_clear:
             mock_run.return_value.returncode = 1
             result = send_device_notification("serial", "message")
             self.assertFalse(result)
