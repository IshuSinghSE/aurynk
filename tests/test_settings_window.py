from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from aurynk.ui.windows.settings_window import SettingsWindow


@patch("aurynk.ui.windows.settings_window.SettingsManager")
def test_settings_window_loads_and_saves(mock_settings):
    # Simulate settings
    mock_settings.return_value.get.side_effect = lambda section, key, default=None: default
    win = SettingsWindow()
    # Simulate a change
    win._on_theme_changed(MagicMock(get_selected=lambda: 1), None)
    win.settings.set.assert_called()
