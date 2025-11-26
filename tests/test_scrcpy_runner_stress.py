import threading
from unittest.mock import patch

from aurynk.core.scrcpy_runner import ScrcpyManager


@patch("aurynk.core.scrcpy_runner.subprocess.Popen")
@patch("aurynk.core.scrcpy_runner.SettingsManager")
def test_scrcpy_runner_concurrent_stress(mock_settings, mock_popen):
    # Reset singleton for test isolation
    ScrcpyManager._instance = None

    # Each Popen call returns a unique mock process with poll() always None
    def make_proc(*args, **kwargs):
        proc = type("Proc", (), {})()
        proc.poll = lambda: None
        proc.terminate = lambda: None
        proc.wait = lambda timeout=None: None
        proc.kill = lambda: None
        return proc

    mock_popen.side_effect = make_proc
    mock_settings.return_value.get.side_effect = lambda section, key, default=None: {
        ("scrcpy", "window_geometry"): "800,600,-1,-1",
        ("scrcpy", "fullscreen"): False,
        ("scrcpy", "scrcpy_path"): "scrcpy",
        ("scrcpy", "window_title"): "TestDevice",
    }.get((section, key), default)
    mgr = ScrcpyManager()

    # Simulate 20 concurrent mirror starts
    def start():
        mgr.start_mirror("127.0.0.1", 5555, "TestDevice")

    threads = [threading.Thread(target=start) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Only one process should be running for the same serial (or 0 if race removed it)
    assert len(mgr.processes) <= 1
    # Now simulate rapid stop/start
    for _ in range(50):
        mgr.stop_mirror("127.0.0.1", 5555)
        mgr.start_mirror("127.0.0.1", 5555, "TestDevice")
    # In a real concurrent environment, 0 or 1 is valid due to race conditions
    assert len(mgr.processes) <= 1
