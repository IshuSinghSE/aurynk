import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add repo root to path
sys.path.insert(0, os.getcwd())

# Mock gi modules BEFORE importing anything from aurynk
# Create mocks for submodules first
mock_gi = MagicMock()
mock_repo = MagicMock()
mock_glib = MagicMock()
mock_gobject = MagicMock()

sys.modules["gi"] = mock_gi
sys.modules["gi.repository"] = mock_repo
sys.modules["gi.repository.GLib"] = mock_glib
sys.modules["gi.repository.GObject"] = mock_gobject

# Explicit assignment as per memory
sys.modules["gi.repository"].GLib = mock_glib
sys.modules["gi.repository"].GObject = mock_gobject


# Setup GObject mock
class MockGObject:
    def __init__(self, **kwargs):
        pass

    def emit(self, *args):
        pass


# Assign MockGObject to Object attribute of the mock GObject module
mock_gobject.Object = MockGObject
mock_gobject.SignalFlags = MagicMock()

from aurynk.models.device import Device


class TestDeviceOptimization(unittest.TestCase):
    @patch("aurynk.models.device.subprocess.run")
    @patch("threading.Thread")
    def test_fetch_details_batches_calls(self, mock_thread_class, mock_subprocess_run):
        print("\n--- Running test_fetch_details_batches_calls ---")

        # We need to capture the task passed to thread and run it
        def side_effect(*args, **kwargs):
            # print(f"Thread created with args={args} kwargs={kwargs}")
            target = kwargs.get("target")
            # Run the target immediately
            if target:
                target()
            return MagicMock()  # Return a mock thread object

        mock_thread_class.side_effect = side_effect

        # Setup device
        device = Device(adb_serial="serial123")

        # Mock subprocess to return output for the batched command
        mock_subprocess_run.return_value = MagicMock(
            stdout="Google\n|||\nPixel 6\n|||\n13\n", returncode=0
        )

        # Run
        device.fetch_details()

        # Verification
        print(f"Subprocess called {mock_subprocess_run.call_count} times")

        # This test expects the new implementation to call subprocess.run 1 time (batched)
        self.assertEqual(
            mock_subprocess_run.call_count, 1, "Expected 1 call in optimized implementation"
        )

        # Verify data was updated correctly from the mocked output
        self.assertEqual(device._data.get("manufacturer"), "Google")
        self.assertEqual(device._data.get("model"), "Pixel 6")
        self.assertEqual(device._data.get("android_version"), "13")
        self.assertEqual(device._data.get("name"), "Pixel 6")  # Name should be updated to model


if __name__ == "__main__":
    unittest.main()
