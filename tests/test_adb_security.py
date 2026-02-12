import unittest
from unittest.mock import MagicMock, patch
import re
from aurynk.core.adb_manager import ADBController

class TestVulnerability(unittest.TestCase):
    @patch("aurynk.core.adb_manager.DeviceStore")
    def setUp(self, mock_device_store):
        self.mock_device_store = mock_device_store
        self.adb_controller = ADBController()

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    @patch("aurynk.core.adb_manager.logger")
    def test_capture_screenshot_injection_prevention(
        self, mock_logger, mock_exists, mock_makedirs, mock_settings_manager, mock_subprocess_run, mock_get_adb_path
    ):
        mock_settings_manager.return_value.get.return_value = 10

        malicious_app = "com.example;reboot"

        mock_subprocess_run.side_effect = [
            MagicMock(stdout="mScreenOn=true mInteractive=true"),  # 1
            MagicMock(stdout="mShowingLockscreen=false"),  # 2
            MagicMock(
                stdout=f"mCurrentFocus=Window{{... {malicious_app}/.MainActivity}}"
            ),  # 3
            MagicMock(returncode=0),  # 4
            MagicMock(returncode=0),  # 5
            # Note: Monkey call should be skipped now
            MagicMock(returncode=0),  # 6 (Pull)
        ]

        try:
            self.adb_controller.capture_screenshot("192.168.1.5", 5555)
        except Exception as e:
            self.fail(f"Exception during capture_screenshot: {e}")

        # Verify that monkey command was NOT called with malicious payload
        expected_call_arg = ["adb", "-s", "192.168.1.5:5555", "shell", "monkey", "-p", malicious_app, "1"]

        found = False
        for call in mock_subprocess_run.call_args_list:
            args, kwargs = call
            if args[0] == expected_call_arg:
                found = True
                break

        self.assertFalse(found, "Vulnerability still present! subprocess.run called with malicious argument.")

        # Verify that a warning was logged
        # We need to match the log message which contains the malicious app name
        log_calls = mock_logger.warning.call_args_list
        warning_found = False
        for call in log_calls:
            args, _ = call
            if malicious_app in args[0] and "Invalid package name" in args[0]:
                warning_found = True
                break

        self.assertTrue(warning_found, "Warning log not found for invalid package name.")

if __name__ == "__main__":
    unittest.main()
