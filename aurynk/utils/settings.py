"""
Settings Manager for Aurynk
Handles application configuration with persistence and change notifications.
"""

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from aurynk.utils.logger import get_logger

logger = get_logger(__name__)


class SettingsManager:
    """Singleton class for managing application settings."""

    _instance: Optional["SettingsManager"] = None
    _initialized: bool = False

    # Default settings structure
    DEFAULT_SETTINGS = {
        "app": {
            "auto_connect": True,
            "monitor_interval": 5,
            "show_notifications": True,
            "close_to_tray": True,
            "start_minimized": False,
            "theme": "system",
        },
        "adb": {
            "connection_timeout": 10,
            "max_retry_attempts": 5,
            "auto_disconnect_on_sleep": False,
            "keep_alive_interval": 0,
        },
        "scrcpy": {
            "always_on_top": True,
            "fullscreen": False,
            "window_borderless": False,
            "max_size": 0,
            "rotation": 0,
            "stay_awake": True,
            "enable_audio": False,
            "video_codec": "h264",
            "video_bitrate": 8,
            "max_fps": 0,
            "show_touches": False,
            "turn_screen_off": False,
            "disable_screensaver": True,
            "record_format": "mp4",
            "record_path": "~/Videos/Aurynk",
        },
    }

    def __new__(cls) -> "SettingsManager":
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the settings manager."""
        if self._initialized:
            return

        self._settings: Dict[str, Dict[str, Any]] = {}
        self._callbacks: Dict[str, Dict[str, list[Callable]]] = {}
        self._config_dir = self._get_config_dir()
        self._config_file = self._config_dir / "settings.json"

        # Ensure config directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Load settings from file or use defaults
        self.load()

        self._initialized = True
        logger.info(f"Settings manager initialized with config at {self._config_file}")

    def _get_config_dir(self) -> Path:
        """Get the configuration directory path, respecting XDG_CONFIG_HOME."""
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            config_base = Path(xdg_config_home)
        else:
            config_base = Path.home() / ".config"

        return config_base / "aurynk"

    def load(self) -> None:
        """Load settings from the configuration file."""
        try:
            if self._config_file.exists():
                with open(self._config_file, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)

                # Merge loaded settings with defaults (to add any new keys)
                self._settings = self._merge_settings(self.DEFAULT_SETTINGS.copy(), loaded_settings)
                logger.info("Settings loaded successfully")
            else:
                # Use default settings if file doesn't exist
                self._settings = self.DEFAULT_SETTINGS.copy()
                logger.info("Using default settings (no config file found)")
                # Save defaults to create the file
                self.save()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse settings file: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
            logger.warning("Using default settings due to parse error")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._settings = self.DEFAULT_SETTINGS.copy()
            logger.warning("Using default settings due to error")

    def _merge_settings(self, defaults: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded settings with defaults."""
        result = defaults.copy()

        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value

        return result

    def save(self) -> bool:
        """Save current settings to the configuration file."""
        try:
            with open(self._config_file, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            logger.info("Settings saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            category: The settings category (e.g., 'app', 'adb', 'scrcpy')
            key: The setting key
            default: Default value if setting doesn't exist

        Returns:
            The setting value or default
        """
        try:
            return self._settings.get(category, {}).get(key, default)
        except Exception as e:
            logger.error(f"Error getting setting {category}.{key}: {e}")
            return default

    def set(self, category: str, key: str, value: Any, save_immediately: bool = True) -> bool:
        """
        Set a setting value.

        Args:
            category: The settings category
            key: The setting key
            value: The new value
            save_immediately: Whether to save to file immediately

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure category exists
            if category not in self._settings:
                self._settings[category] = {}

            # Store old value for comparison
            old_value = self._settings[category].get(key)

            # Set new value
            self._settings[category][key] = value

            # Save if requested
            if save_immediately:
                self.save()

            # Trigger callbacks if value changed
            if old_value != value:
                self._trigger_callbacks(category, key, value, old_value)

            logger.debug(f"Setting {category}.{key} = {value}")
            return True

        except Exception as e:
            logger.error(f"Error setting {category}.{key}: {e}")
            return False

    def register_callback(
        self, category: str, key: str, callback: Callable[[Any, Any], None]
    ) -> None:
        """
        Register a callback for setting changes.

        Args:
            category: The settings category
            key: The setting key
            callback: Function to call when setting changes, receives (new_value, old_value)
        """
        if category not in self._callbacks:
            self._callbacks[category] = {}

        if key not in self._callbacks[category]:
            self._callbacks[category][key] = []

        self._callbacks[category][key].append(callback)
        logger.debug(f"Registered callback for {category}.{key}")

    def unregister_callback(
        self, category: str, key: str, callback: Callable[[Any, Any], None]
    ) -> None:
        """
        Unregister a callback for setting changes.

        Args:
            category: The settings category
            key: The setting key
            callback: The callback function to remove
        """
        try:
            if category in self._callbacks and key in self._callbacks[category]:
                self._callbacks[category][key].remove(callback)
                logger.debug(f"Unregistered callback for {category}.{key}")
        except ValueError:
            logger.warning(f"Callback not found for {category}.{key}")

    def _trigger_callbacks(self, category: str, key: str, new_value: Any, old_value: Any) -> None:
        """Trigger all registered callbacks for a setting change."""
        if category in self._callbacks and key in self._callbacks[category]:
            for callback in self._callbacks[category][key]:
                try:
                    callback(new_value, old_value)
                except Exception as e:
                    logger.error(f"Error in callback for {category}.{key}: {e}")

    def get_all(self, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Get all settings or all settings in a category.

        Args:
            category: Optional category to filter by

        Returns:
            Dictionary of settings
        """
        if category:
            return self._settings.get(category, {}).copy()
        return self._settings.copy()

    def reset(self, category: Optional[str] = None, key: Optional[str] = None) -> bool:
        """
        Reset settings to defaults.

        Args:
            category: Optional category to reset (None = reset all)
            key: Optional specific key to reset

        Returns:
            True if successful
        """
        try:
            if category and key:
                # Reset specific setting
                if category in self.DEFAULT_SETTINGS and key in self.DEFAULT_SETTINGS[category]:
                    default_value = self.DEFAULT_SETTINGS[category][key]
                    self.set(category, key, default_value)
                    logger.info(f"Reset {category}.{key} to default")
            elif category:
                # Reset entire category
                if category in self.DEFAULT_SETTINGS:
                    self._settings[category] = self.DEFAULT_SETTINGS[category].copy()
                    self.save()
                    logger.info(f"Reset category {category} to defaults")
            else:
                # Reset everything
                self._settings = self.DEFAULT_SETTINGS.copy()
                self.save()
                logger.info("Reset all settings to defaults")

            return True
        except Exception as e:
            logger.error(f"Error resetting settings: {e}")
            return False

    def export_settings(self, file_path: str) -> bool:
        """
        Export settings to a JSON file.

        Args:
            file_path: Path to export to

        Returns:
            True if successful
        """
        try:
            export_path = Path(file_path).expanduser()
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            logger.info(f"Settings exported to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> bool:
        """
        Import settings from a JSON file.

        Args:
            file_path: Path to import from

        Returns:
            True if successful
        """
        try:
            import_path = Path(file_path).expanduser()
            with open(import_path, "r", encoding="utf-8") as f:
                imported = json.load(f)

            self._settings = self._merge_settings(self.DEFAULT_SETTINGS.copy(), imported)
            self.save()
            logger.info(f"Settings imported from {import_path}")
            return True
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False


# Convenience function to get the singleton instance
def get_settings_manager() -> SettingsManager:
    """Get the SettingsManager singleton instance."""
    return SettingsManager()
