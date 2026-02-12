import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# --- MOCK SETUP START ---
# We need to mock gi BEFORE importing aurynk.models.device
mock_gi = MagicMock()
mock_gi.require_version = MagicMock()

# Mock GLib
# We mock idle_add to execute the callback immediately
mock_glib = MagicMock()


def fake_idle_add(func, *args):
    func(*args)
    return True


mock_glib.idle_add = MagicMock(side_effect=fake_idle_add)

# Mock GObject
mock_gobject = MagicMock()


class MockGObjectBase:
    def __init__(self):
        self.signals = {}

    def emit(self, signal_name, *args):
        pass


mock_gobject.Object = MockGObjectBase
mock_gobject.SignalFlags = MagicMock()
mock_gobject.SignalFlags.RUN_FIRST = 1

# Setup sys.modules so imports work
sys.modules["gi"] = mock_gi
# We need a proper mock for gi.repository
mock_repo = MagicMock()
mock_repo.GLib = mock_glib
mock_repo.GObject = mock_gobject
sys.modules["gi.repository"] = mock_repo
sys.modules["gi.repository.GLib"] = mock_glib
sys.modules["gi.repository.GObject"] = mock_gobject
# --- MOCK SETUP END ---

# Now import the module to test
from aurynk.models.device import Device


class DeviceBenchmark(unittest.TestCase):
    def setUp(self):
        self.call_count = 0

    def test_fetch_details_performance(self):
        # We'll use a Condition variable to detect when threads are done,
        # but since we don't control the thread, we just poll.

        mock_process = MagicMock()
        mock_process.returncode = 0

        def side_effect(*args, **kwargs):
            self.call_count += 1
            # Simulate latency
            time.sleep(0.01)

            cmd = args[0]
            # cmd is like ['adb', '-s', 'serial', 'shell', 'getprop', 'ro.product.manufacturer']

            cmd_str = " ".join(str(x) for x in cmd)

            # Simple logic to return values based on command
            stdout = ""
            if "|||" in cmd_str:
                # Optimized path
                stdout = "TestManufacturer\n|||\nTestModel\n|||\n12\n"
            elif "ro.product.manufacturer" in cmd_str:
                stdout = "TestManufacturer\n"
            elif "ro.product.model" in cmd_str:
                stdout = "TestModel\n"
            elif "ro.build.version.release" in cmd_str:
                stdout = "12\n"
            else:
                # Fallback
                stdout = ""

            mock_process.stdout = stdout
            return mock_process

        with patch("subprocess.run", side_effect=side_effect):
            device = Device(adb_serial="emulator-5554")

            print("\n[Benchmark] Starting fetch_details...")
            start_time = time.time()
            device.fetch_details()

            # Wait for calls to happen
            # We wait up to 1 second
            for _ in range(20):
                time.sleep(0.05)
                # If we exceed expected calls (1), break early (failure case)
                if self.call_count > 1:
                    break

            # Give a little extra buffer
            time.sleep(0.1)

            end_time = time.time()
            duration = end_time - start_time

            print(f"[Benchmark] Calls to subprocess.run: {self.call_count}")
            print(f"[Benchmark] Time taken: {duration:.4f}s")

            # Assertions
            self.assertEqual(self.call_count, 1, "Should only make 1 subprocess call")
            self.assertEqual(device._data.get("manufacturer"), "TestManufacturer")
            self.assertEqual(device._data.get("model"), "TestModel")
            self.assertEqual(device._data.get("android_version"), "12")
            print(f"[Benchmark] Device data: {device._data}")


if __name__ == "__main__":
    unittest.main()
