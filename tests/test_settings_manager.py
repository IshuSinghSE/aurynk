from aurynk.utils.settings import SettingsManager


def test_settings_manager_persistence(tmp_path):
    # Use a temp file for settings
    sm = SettingsManager()
    sm._settings_file = tmp_path / "settings.json"
    sm.set("test", "key", "value")
    assert sm.get("test", "key") == "value"
    sm.set("test", "key2", 123)
    assert sm.get("test", "key2") == 123
    # Simulate reload
    sm2 = SettingsManager()
    sm2._settings_file = sm._settings_file
    sm2.load()
    assert sm2.get("test", "key") == "value"
    assert sm2.get("test", "key2") == 123
