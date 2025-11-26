from unittest.mock import MagicMock, patch

from aurynk.core.scrcpy_runner import ScrcpyManager


@patch("aurynk.core.scrcpy_runner.Gdk")
def test_window_geometry_clamping(mock_gdk):
    # Mock monitor geometry
    mock_display = MagicMock()
    mock_monitor = MagicMock()
    mock_geometry = MagicMock()
    mock_geometry.width = 1024
    mock_geometry.height = 768
    mock_monitor.get_geometry.return_value = mock_geometry
    mock_display.get_primary_monitor.return_value = mock_monitor
    mock_gdk.Display.get_default.return_value = mock_display

    mgr = ScrcpyManager()
    # Patch subprocess.Popen to avoid actually running scrcpy
    with patch("subprocess.Popen") as popen_mock:
        # Patch settings
        with patch.object(mgr, "processes", {}):
            with patch("aurynk.core.scrcpy_runner.SettingsManager") as smock:
                smock.return_value.get.side_effect = lambda section, key, default=None: {
                    ("scrcpy", "window_geometry"): "2000,2000,900,900",
                    ("scrcpy", "fullscreen"): False,
                    ("scrcpy", "scrcpy_path"): "scrcpy",
                    ("scrcpy", "window_title"): "Test",
                }.get((section, key), default)
                mgr.start_mirror("127.0.0.1", 5555, "TestDevice")
                args = popen_mock.call_args[0][0]
                # Should clamp to 1024x768
                assert "--window-width" in args and str(1024) in args
                assert "--window-height" in args and str(768) in args
                # Should clamp position to fit
                assert "--window-x" in args and str(0) in args
                assert "--window-y" in args and str(0) in args
