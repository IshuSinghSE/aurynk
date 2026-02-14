import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before import
sys.modules["zeroconf"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()
sys.modules["gi.repository.GLib"] = MagicMock()
sys.modules["gi.repository.GObject"] = MagicMock()

import unittest
from aurynk.core.adb_manager import ADBController


class TestADBOptimization(unittest.TestCase):
    @patch("aurynk.core.adb_manager.DeviceStore")
    @patch("aurynk.core.adb_manager.SettingsManager")
    def setUp(self, mock_settings, mock_device_store):
        self.adb_controller = ADBController()

    @patch("aurynk.core.adb_manager.get_adb_path", return_value="adb")
    @patch("subprocess.run")
    def test_fetch_device_info_batched(self, mock_subprocess_run, mock_get_adb_path):
        # Setup the mock to return a single combined output
        # combined output: marketname ||| model ||| manufacturer ||| version
        delimiter = "AURYNK_DELIMITER_v1"
        # Simulating adb shell output with echo delimiter
        combined_output = (
            f"MyMarketName\n{delimiter}\nMyModel\n{delimiter}\nMyManufacturer\n{delimiter}\n13.0"
        )

        mock_subprocess_run.return_value = MagicMock(
            stdout=combined_output, returncode=0, stderr=""
        )

        info = self.adb_controller._fetch_device_info("192.168.1.5", 5555)

        self.assertEqual(info["name"], "MyMarketName")
        self.assertEqual(info["model"], "MyModel")
        self.assertEqual(info["manufacturer"], "MyManufacturer")
        self.assertEqual(info["android_version"], "13.0")

        # Check call count - expected 1 call after optimization
        self.assertEqual(mock_subprocess_run.call_count, 1)

        # Verify the command structure
        args, kwargs = mock_subprocess_run.call_args
        cmd = args[0]
        # cmd should be a list like ['adb', '-s', 'serial', 'shell', '...']
        # We need to join it to check content easily, or check list elements
        self.assertEqual(cmd[0], "adb")
        self.assertIn("shell", cmd)

        # The command string passed to shell should contain all properties
        shell_cmd = cmd[-1]  # Assuming the last argument is the shell command string
        self.assertIn("ro.product.marketname", shell_cmd)
        self.assertIn("ro.product.device", shell_cmd)
        self.assertIn("ro.product.manufacturer", shell_cmd)
        self.assertIn("ro.build.version.release", shell_cmd)
        self.assertIn(delimiter, shell_cmd)


if __name__ == "__main__":
    unittest.main()
