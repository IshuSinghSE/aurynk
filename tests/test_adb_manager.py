import unittest
from unittest.mock import MagicMock, patch

from aurynk.core.adb_manager import ADBController


class TestADBController(unittest.TestCase):
    @patch("aurynk.core.adb_manager.DeviceStore")
    def setUp(self, mock_device_store):
        self.mock_device_store = mock_device_store
        self.adb_controller = ADBController()

    def test_generate_code(self):
        code = self.adb_controller.generate_code(10)
        self.assertEqual(len(code), 10)
        self.assertTrue(code.isalpha())

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    def test_pair_device_success(
        self, mock_settings_manager, mock_subprocess_run, mock_get_adb_path
    ):
        mock_settings_manager.return_value.get.side_effect = lambda section, key, default: default

        # Mock pair command success
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # pair
            MagicMock(returncode=0, stdout="connected to 192.168.1.5:5555", stderr=""),  # connect
            MagicMock(stdout="MyPhone\n"),  # getprop marketname
            MagicMock(stdout="Pixel 5\n"),  # getprop device
            MagicMock(stdout="Google\n"),  # getprop manufacturer
            MagicMock(stdout="12\n"),  # getprop android_version
        ]

        # Use a mock for _fetch_device_info to simplify if needed, but integration testing the flow is better here
        # Actually _fetch_device_info calls subprocess.run multiple times.
        # Let's mock _fetch_device_info to make test simpler and more focused on pair_device logic
        with patch.object(self.adb_controller, "_fetch_device_info") as mock_fetch_info:
            mock_fetch_info.return_value = {"name": "Test Device"}

            # Reset side_effect for subprocess.run because we are mocking _fetch_device_info
            mock_subprocess_run.side_effect = [
                MagicMock(returncode=0, stdout="", stderr=""),  # pair
                MagicMock(
                    returncode=0, stdout="connected to 192.168.1.5:5555", stderr=""
                ),  # connect
            ]

            result = self.adb_controller.pair_device("192.168.1.5", 3000, 5555, "password")

            self.assertTrue(result)
            mock_subprocess_run.assert_any_call(
                ["adb", "pair", "192.168.1.5:3000", "password"], capture_output=True, text=True
            )
            mock_subprocess_run.assert_any_call(
                ["adb", "connect", "192.168.1.5:5555"], capture_output=True, text=True, timeout=10
            )
            mock_fetch_info.assert_called_once_with("192.168.1.5", 5555)

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    @patch("time.sleep")
    def test_pair_device_connect_fail(
        self, mock_sleep, mock_settings_manager, mock_subprocess_run, mock_get_adb_path
    ):
        # Configure settings to return 1 for max_retries
        def get_setting(section, key, default):
            if key == "max_retry_attempts":
                return 1
            return default

        mock_settings_manager.return_value.get.side_effect = get_setting

        # Pair success, connect fail
        # We need to ensure we provide enough side effects.
        # 1. pair
        # 2. connect (attempt 1)
        mock_subprocess_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # pair
            MagicMock(returncode=0, stdout="unable to connect", stderr=""),  # connect attempt 1
        ]

        result = self.adb_controller.pair_device("192.168.1.5", 3000, 5555, "password")
        self.assertFalse(result)

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    def test_get_current_ports_success(self, mock_subprocess_run, mock_get_adb_path):
        output = """
adb-serial._adb-tls-connect._tcp    192.168.1.5:5555
other-device._adb-tls-connect._tcp  192.168.1.6:6666
"""
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout=output)

        ports = self.adb_controller.get_current_ports("192.168.1.5")
        self.assertEqual(ports, {"connect_port": 5555, "pair_port": None})

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    def test_get_current_ports_fail(self, mock_subprocess_run, mock_get_adb_path):
        mock_subprocess_run.return_value = MagicMock(returncode=1)
        ports = self.adb_controller.get_current_ports("192.168.1.5")
        self.assertIsNone(ports)

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    def test_fetch_device_specs(self, mock_settings, mock_subprocess_run, mock_get_adb_path):
        mock_settings.return_value.get.return_value = 10

        # meminfo, df, dumpsys battery
        mock_subprocess_run.side_effect = [
            MagicMock(stdout="MemTotal:        8000000 kB\n"),
            MagicMock(
                stdout="Filesystem 1K-blocks Used Available Use% Mounted on\n/dev/block/dm-0 120000000 10000 110000000 1% /data\n"
            ),
            MagicMock(stdout="  level: 85\n"),
        ]

        specs = self.adb_controller.fetch_device_specs("192.168.1.5", 5555)
        self.assertEqual(specs["ram"], "8 GB")
        self.assertEqual(specs["storage"], "120 GB")
        self.assertEqual(specs["battery"], "85%")

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    @patch("os.makedirs")
    @patch("os.path.exists", return_value=False)
    def test_capture_screenshot_success(
        self, mock_exists, mock_makedirs, mock_settings, mock_subprocess_run, mock_get_adb_path
    ):
        mock_settings.return_value.get.return_value = 10

        # 1. dumpsys window (screen state) - assume on
        # 2. dumpsys window windows (keyguard) - assume unlocked
        # 3. dumpsys window windows (current app)
        # 4. input keyevent 3 (home)
        # 5. screencap
        # 6. monkey (restore app)
        # 7. pull

        mock_subprocess_run.side_effect = [
            MagicMock(stdout="mScreenOn=true mInteractive=true"),  # 1
            MagicMock(stdout="mShowingLockscreen=false"),  # 2
            MagicMock(
                stdout="mCurrentFocus=Window{... com.example.app/com.example.app.MainActivity}"
            ),  # 3
            MagicMock(returncode=0),  # 4
            MagicMock(returncode=0),  # 5
            MagicMock(returncode=0),  # 6
            MagicMock(returncode=0),  # 7
        ]

        path = self.adb_controller.capture_screenshot("192.168.1.5", 5555)
        self.assertTrue(path.endswith("aurynk_192_168_1_5_screen.png"))

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    @patch("aurynk.core.adb_manager.SettingsManager")
    def test_capture_screenshot_locked(self, mock_settings, mock_subprocess_run, mock_get_adb_path):
        mock_settings.return_value.get.return_value = 10
        # Screen on, but locked
        mock_subprocess_run.side_effect = [
            MagicMock(stdout="mScreenOn=true mInteractive=true"),
            MagicMock(stdout="mShowingLockscreen=true"),
        ]

        path = self.adb_controller.capture_screenshot("192.168.1.5", 5555)
        self.assertIsNone(path)

    def test_load_paired_devices(self):
        self.adb_controller.device_store.get_devices.return_value = [{"name": "Test"}]
        devices = self.adb_controller.load_paired_devices()
        self.assertEqual(devices, [{"name": "Test"}])

    def test_save_paired_device(self):
        self.adb_controller.save_paired_device({"name": "New"})
        self.adb_controller.device_store.add_or_update_device.assert_called_once_with(
            {"name": "New"}
        )

    def test_remove_device(self):
        self.adb_controller.remove_device("192.168.1.5")
        self.adb_controller.device_store.remove_device.assert_called_once_with("192.168.1.5")


if __name__ == "__main__":
    unittest.main()
