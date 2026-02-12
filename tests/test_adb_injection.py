import unittest
from unittest.mock import MagicMock, patch

from aurynk.core.adb_manager import ADBController


class TestADBInjection(unittest.TestCase):
    @patch("aurynk.core.adb_manager.DeviceStore")
    def setUp(self, mock_device_store):
        self.adb_controller = ADBController()

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    def test_capture_screenshot_injection(
        self, mock_exists, mock_makedirs, mock_settings, mock_subprocess_run, mock_get_adb_path
    ):
        mock_settings.return_value.get.return_value = 10

        # Malicious package name
        malicious_app = "com.example;reboot"

        # 1. dumpsys window (screen state) - assume on
        # 2. dumpsys window windows (keyguard) - assume unlocked
        # 3. dumpsys window windows (current app) - RETURN MALICIOUS APP
        # 4. input keyevent 3 (home)
        # 5. screencap
        # 6. monkey (restore app) -> THIS IS THE VULNERABLE CALL
        # 7. pull

        mock_subprocess_run.side_effect = [
            MagicMock(stdout="mScreenOn=true mInteractive=true"),  # 1
            MagicMock(stdout="mShowingLockscreen=false"),  # 2
            MagicMock(
                stdout=f"mCurrentFocus=Window{{... {malicious_app}/com.example.app.MainActivity}}"
            ),  # 3
            MagicMock(returncode=0),  # 4
            MagicMock(returncode=0),  # 5
            MagicMock(returncode=0),  # 6
            MagicMock(returncode=0),  # 7
        ]

        try:
            self.adb_controller.capture_screenshot("192.168.1.5", 5555)
        except Exception as e:
            print(f"Exception: {e}")

        # Check if the malicious command was passed to subprocess.run
        # We are looking for the call to monkey
        # [get_adb_path(), "-s", serial, "shell", "monkey", "-p", current_app, "1"]

        found_vulnerable_call = False
        for call in mock_subprocess_run.call_args_list:
            args, _ = call
            cmd_list = args[0]
            if "monkey" in cmd_list and malicious_app in cmd_list:
                found_vulnerable_call = True
                break

        self.assertFalse(
            found_vulnerable_call,
            "Vulnerable subprocess call FOUND! Command injection is possible.",
        )


if __name__ == "__main__":
    unittest.main()
