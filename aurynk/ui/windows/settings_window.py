"""
Settings Window for Aurynk
Provides a preferences interface for configuring application, ADB, and Scrcpy settings.
"""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, GLib
from pathlib import Path

from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger(__name__)


class SettingsWindow(Adw.PreferencesWindow):
    """Settings window using Adwaita preferences."""
    
    def __init__(self, parent=None, transient_for=None, **kwargs):
        """Initialize the settings window."""
        super().__init__(**kwargs)
        
        self.settings = SettingsManager()
        
        # Window properties
        self.set_title("Settings")
        self.set_default_size(600, 700)
        self.set_modal(True)
        self.set_hide_on_close(True)
        
        # Set transient parent (prefer transient_for parameter)
        parent_window = transient_for or parent
        if parent_window:
            self.set_transient_for(parent_window)
        
        # Create preference pages
        self._create_app_page()
        self._create_adb_page()
        self._create_scrcpy_page()
        
        logger.info("Settings window initialized")
    
    def _create_app_page(self):
        """Create the Application settings page."""
        page = Adw.PreferencesPage()
        page.set_title("Application")
        page.set_icon_name("applications-system-symbolic")
        
        # General group
        general_group = Adw.PreferencesGroup()
        general_group.set_title("General")
        general_group.set_description("Application behavior settings")
        
        # Auto-connect switch
        auto_connect = Adw.SwitchRow()
        auto_connect.set_title("Auto Connect")
        auto_connect.set_subtitle("Automatically connect to devices when detected")
        auto_connect.set_active(self.settings.get("app", "auto_connect", True))
        auto_connect.connect("notify::active", self._on_auto_connect_changed)
        general_group.add(auto_connect)
        
        # Show notifications switch
        show_notifications = Adw.SwitchRow()
        show_notifications.set_title("Show Notifications")
        show_notifications.set_subtitle("Display system notifications for device events")
        show_notifications.set_active(self.settings.get("app", "show_notifications", True))
        show_notifications.connect("notify::active", self._on_show_notifications_changed)
        general_group.add(show_notifications)
        
        # Monitor interval
        monitor_interval = Adw.SpinRow()
        monitor_interval.set_title("Monitor Interval")
        monitor_interval.set_subtitle("Device monitoring interval in seconds")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("app", "monitor_interval", 5),
            lower=1,
            upper=60,
            step_increment=1,
            page_increment=5
        )
        monitor_interval.set_adjustment(adjustment)
        monitor_interval.set_digits(0)
        monitor_interval.connect("notify::value", self._on_monitor_interval_changed)
        general_group.add(monitor_interval)
        
        page.add(general_group)
        
        # Appearance group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Appearance")
        
        # Theme selector
        theme_row = Adw.ComboRow()
        theme_row.set_title("Theme")
        theme_row.set_subtitle("Choose the application theme")
        
        theme_model = Gtk.StringList.new(["System", "Light", "Dark"])
        theme_row.set_model(theme_model)
        
        # Set current theme
        current_theme = self.settings.get("app", "theme", "system")
        theme_map = {"system": 0, "light": 1, "dark": 2}
        theme_row.set_selected(theme_map.get(current_theme, 0))
        theme_row.connect("notify::selected", self._on_theme_changed)
        
        appearance_group.add(theme_row)
        page.add(appearance_group)
        
        # System tray group
        tray_group = Adw.PreferencesGroup()
        tray_group.set_title("System Tray")
        
        # Minimize to tray switch
        minimize_to_tray = Adw.SwitchRow()
        minimize_to_tray.set_title("Minimize to Tray")
        minimize_to_tray.set_subtitle("Hide window to system tray instead of closing")
        minimize_to_tray.set_active(self.settings.get("app", "minimize_to_tray", True))
        minimize_to_tray.connect("notify::active", self._on_minimize_to_tray_changed)
        tray_group.add(minimize_to_tray)
        
        # Start minimized switch
        start_minimized = Adw.SwitchRow()
        start_minimized.set_title("Start Minimized")
        start_minimized.set_subtitle("Start application minimized to tray")
        start_minimized.set_active(self.settings.get("app", "start_minimized", False))
        start_minimized.connect("notify::active", self._on_start_minimized_changed)
        tray_group.add(start_minimized)
        
        page.add(tray_group)
        
        self.add(page)
    
    def _create_adb_page(self):
        """Create the ADB settings page."""
        page = Adw.PreferencesPage()
        page.set_title("ADB")
        page.set_icon_name("network-wired-symbolic")
        
        # Connection group
        connection_group = Adw.PreferencesGroup()
        connection_group.set_title("Connection")
        connection_group.set_description("ADB connection settings")
        
        # Connection timeout
        connection_timeout = Adw.SpinRow()
        connection_timeout.set_title("Connection Timeout")
        connection_timeout.set_subtitle("Timeout for ADB connections in seconds")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "connection_timeout", 10),
            lower=1,
            upper=60,
            step_increment=1,
            page_increment=5
        )
        connection_timeout.set_adjustment(adjustment)
        connection_timeout.set_digits(0)
        connection_timeout.connect("notify::value", self._on_connection_timeout_changed)
        connection_group.add(connection_timeout)
        
        # Max retry attempts
        max_retry = Adw.SpinRow()
        max_retry.set_title("Max Retry Attempts")
        max_retry.set_subtitle("Maximum number of connection retry attempts")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "max_retry_attempts", 5),
            lower=0,
            upper=20,
            step_increment=1,
            page_increment=5
        )
        max_retry.set_adjustment(adjustment)
        max_retry.set_digits(0)
        max_retry.connect("notify::value", self._on_max_retry_changed)
        connection_group.add(max_retry)
        
        # Keep alive interval
        keep_alive = Adw.SpinRow()
        keep_alive.set_title("Keep Alive Interval")
        keep_alive.set_subtitle("Send keep-alive packets (0 to disable)")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "keep_alive_interval", 0),
            lower=0,
            upper=300,
            step_increment=5,
            page_increment=10
        )
        keep_alive.set_adjustment(adjustment)
        keep_alive.set_digits(0)
        keep_alive.connect("notify::value", self._on_keep_alive_changed)
        connection_group.add(keep_alive)
        
        page.add(connection_group)
        
        # Power management group
        power_group = Adw.PreferencesGroup()
        power_group.set_title("Power Management")
        
        # Auto disconnect on sleep
        auto_disconnect = Adw.SwitchRow()
        auto_disconnect.set_title("Auto Disconnect on Sleep")
        auto_disconnect.set_subtitle("Disconnect devices when system goes to sleep")
        auto_disconnect.set_active(self.settings.get("adb", "auto_disconnect_on_sleep", False))
        auto_disconnect.connect("notify::active", self._on_auto_disconnect_changed)
        power_group.add(auto_disconnect)
        
        page.add(power_group)
        
        self.add(page)
    
    def _create_scrcpy_page(self):
        """Create the Scrcpy settings page."""
        page = Adw.PreferencesPage()
        page.set_title("Scrcpy")
        page.set_icon_name("video-display-symbolic")
        
        # Display group
        display_group = Adw.PreferencesGroup()
        display_group.set_title("Display")
        display_group.set_description("Screen mirroring display options")
        
        # Always on top
        always_on_top = Adw.SwitchRow()
        always_on_top.set_title("Always on Top")
        always_on_top.set_subtitle("Keep scrcpy window above other windows")
        always_on_top.set_active(self.settings.get("scrcpy", "always_on_top", True))
        always_on_top.connect("notify::active", self._on_always_on_top_changed)
        display_group.add(always_on_top)
        
        # Fullscreen
        fullscreen = Adw.SwitchRow()
        fullscreen.set_title("Fullscreen")
        fullscreen.set_subtitle("Start in fullscreen mode")
        fullscreen.set_active(self.settings.get("scrcpy", "fullscreen", False))
        fullscreen.connect("notify::active", self._on_fullscreen_changed)
        display_group.add(fullscreen)
        
        # Window borderless
        borderless = Adw.SwitchRow()
        borderless.set_title("Borderless Window")
        borderless.set_subtitle("Remove window decorations")
        borderless.set_active(self.settings.get("scrcpy", "window_borderless", False))
        borderless.connect("notify::active", self._on_borderless_changed)
        display_group.add(borderless)
        
        # Max size
        max_size = Adw.SpinRow()
        max_size.set_title("Max Size")
        max_size.set_subtitle("Maximum dimension in pixels (0 for device size)")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("scrcpy", "max_size", 0),
            lower=0,
            upper=2560,
            step_increment=100,
            page_increment=200
        )
        max_size.set_adjustment(adjustment)
        max_size.set_digits(0)
        max_size.connect("notify::value", self._on_max_size_changed)
        display_group.add(max_size)
        
        # Rotation
        rotation = Adw.SpinRow()
        rotation.set_title("Rotation")
        rotation.set_subtitle("Screen rotation in degrees (0, 90, 180, 270)")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("scrcpy", "rotation", 0),
            lower=0,
            upper=270,
            step_increment=90,
            page_increment=90
        )
        rotation.set_adjustment(adjustment)
        rotation.set_digits(0)
        rotation.connect("notify::value", self._on_rotation_changed)
        display_group.add(rotation)
        
        page.add(display_group)
        
        # Audio/Video group
        av_group = Adw.PreferencesGroup()
        av_group.set_title("Audio &amp; Video")
        
        # Enable audio
        enable_audio = Adw.SwitchRow()
        enable_audio.set_title("Enable Audio")
        enable_audio.set_subtitle("Forward device audio (requires scrcpy 2.0+)")
        enable_audio.set_active(self.settings.get("scrcpy", "enable_audio", False))
        enable_audio.connect("notify::active", self._on_enable_audio_changed)
        av_group.add(enable_audio)
        
        # Video codec
        codec_row = Adw.ComboRow()
        codec_row.set_title("Video Codec")
        codec_row.set_subtitle("Video encoding codec")
        
        codec_model = Gtk.StringList.new(["h264", "h265", "av1"])
        codec_row.set_model(codec_model)
        
        current_codec = self.settings.get("scrcpy", "video_codec", "h264")
        codec_map = {"h264": 0, "h265": 1, "av1": 2}
        codec_row.set_selected(codec_map.get(current_codec, 0))
        codec_row.connect("notify::selected", self._on_video_codec_changed)
        av_group.add(codec_row)
        
        # Video bitrate
        bitrate = Adw.SpinRow()
        bitrate.set_title("Video Bitrate")
        bitrate.set_subtitle("Video bitrate in Mbps")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("scrcpy", "video_bitrate", 8),
            lower=1,
            upper=100,
            step_increment=1,
            page_increment=5
        )
        bitrate.set_adjustment(adjustment)
        bitrate.set_digits(0)
        bitrate.connect("notify::value", self._on_bitrate_changed)
        av_group.add(bitrate)
        
        # Max FPS
        max_fps = Adw.SpinRow()
        max_fps.set_title("Max FPS")
        max_fps.set_subtitle("Maximum frame rate (0 for unlimited)")
        adjustment = Gtk.Adjustment(
            value=self.settings.get("scrcpy", "max_fps", 0),
            lower=0,
            upper=120,
            step_increment=10,
            page_increment=30
        )
        max_fps.set_adjustment(adjustment)
        max_fps.set_digits(0)
        max_fps.connect("notify::value", self._on_max_fps_changed)
        av_group.add(max_fps)
        
        page.add(av_group)
        
        # Input group
        input_group = Adw.PreferencesGroup()
        input_group.set_title("Input &amp; Display")
        
        # Show touches
        show_touches = Adw.SwitchRow()
        show_touches.set_title("Show Touches")
        show_touches.set_subtitle("Display touch points on screen")
        show_touches.set_active(self.settings.get("scrcpy", "show_touches", False))
        show_touches.connect("notify::active", self._on_show_touches_changed)
        input_group.add(show_touches)
        
        # Stay awake
        stay_awake = Adw.SwitchRow()
        stay_awake.set_title("Stay Awake")
        stay_awake.set_subtitle("Keep device screen on while mirroring")
        stay_awake.set_active(self.settings.get("scrcpy", "stay_awake", True))
        stay_awake.connect("notify::active", self._on_stay_awake_changed)
        input_group.add(stay_awake)
        
        # Turn screen off
        turn_screen_off = Adw.SwitchRow()
        turn_screen_off.set_title("Turn Screen Off")
        turn_screen_off.set_subtitle("Turn device screen off when mirroring starts")
        turn_screen_off.set_active(self.settings.get("scrcpy", "turn_screen_off", False))
        turn_screen_off.connect("notify::active", self._on_turn_screen_off_changed)
        input_group.add(turn_screen_off)
        
        # Disable screensaver
        disable_screensaver = Adw.SwitchRow()
        disable_screensaver.set_title("Disable Screensaver")
        disable_screensaver.set_subtitle("Prevent computer screensaver during mirroring")
        disable_screensaver.set_active(self.settings.get("scrcpy", "disable_screensaver", True))
        disable_screensaver.connect("notify::active", self._on_disable_screensaver_changed)
        input_group.add(disable_screensaver)
        
        page.add(input_group)
        
        # Recording group
        recording_group = Adw.PreferencesGroup()
        recording_group.set_title("Recording")
        
        # Record format
        format_row = Adw.ComboRow()
        format_row.set_title("Record Format")
        format_row.set_subtitle("Video recording format")
        
        format_model = Gtk.StringList.new(["mp4", "mkv", "m4a", "mka", "opus"])
        format_row.set_model(format_model)
        
        current_format = self.settings.get("scrcpy", "record_format", "mp4")
        format_map = {"mp4": 0, "mkv": 1, "m4a": 2, "mka": 3, "opus": 4}
        format_row.set_selected(format_map.get(current_format, 0))
        format_row.connect("notify::selected", self._on_record_format_changed)
        recording_group.add(format_row)
        
        # Record path
        record_path_row = Adw.ActionRow()
        record_path_row.set_title("Recording Path")
        record_path_row.set_subtitle(str(Path(self.settings.get("scrcpy", "record_path", "~/Videos/Aurynk")).expanduser()))
        
        choose_button = Gtk.Button()
        choose_button.set_icon_name("folder-open-symbolic")
        choose_button.set_valign(Gtk.Align.CENTER)
        choose_button.add_css_class("flat")
        choose_button.connect("clicked", self._on_choose_record_path, record_path_row)
        record_path_row.add_suffix(choose_button)
        
        recording_group.add(record_path_row)
        page.add(recording_group)
        
        self.add(page)
    
    # App settings callbacks
    def _on_auto_connect_changed(self, switch, _):
        """Handle auto-connect setting change."""
        self.settings.set("app", "auto_connect", switch.get_active())
    
    def _on_show_notifications_changed(self, switch, _):
        """Handle show notifications setting change."""
        self.settings.set("app", "show_notifications", switch.get_active())
    
    def _on_monitor_interval_changed(self, spin, _):
        """Handle monitor interval setting change."""
        self.settings.set("app", "monitor_interval", int(spin.get_value()))
    
    def _on_theme_changed(self, combo, _):
        """Handle theme setting change."""
        themes = ["system", "light", "dark"]
        selected = combo.get_selected()
        if 0 <= selected < len(themes):
            self.settings.set("app", "theme", themes[selected])
    
    def _on_minimize_to_tray_changed(self, switch, _):
        """Handle minimize to tray setting change."""
        self.settings.set("app", "minimize_to_tray", switch.get_active())
    
    def _on_start_minimized_changed(self, switch, _):
        """Handle start minimized setting change."""
        self.settings.set("app", "start_minimized", switch.get_active())
    
    # ADB settings callbacks
    def _on_connection_timeout_changed(self, spin, _):
        """Handle connection timeout setting change."""
        self.settings.set("adb", "connection_timeout", int(spin.get_value()))
    
    def _on_max_retry_changed(self, spin, _):
        """Handle max retry attempts setting change."""
        self.settings.set("adb", "max_retry_attempts", int(spin.get_value()))
    
    def _on_keep_alive_changed(self, spin, _):
        """Handle keep alive interval setting change."""
        self.settings.set("adb", "keep_alive_interval", int(spin.get_value()))
    
    def _on_auto_disconnect_changed(self, switch, _):
        """Handle auto disconnect on sleep setting change."""
        self.settings.set("adb", "auto_disconnect_on_sleep", switch.get_active())
    
    # Scrcpy settings callbacks
    def _on_always_on_top_changed(self, switch, _):
        """Handle always on top setting change."""
        self.settings.set("scrcpy", "always_on_top", switch.get_active())
    
    def _on_fullscreen_changed(self, switch, _):
        """Handle fullscreen setting change."""
        self.settings.set("scrcpy", "fullscreen", switch.get_active())
    
    def _on_borderless_changed(self, switch, _):
        """Handle borderless window setting change."""
        self.settings.set("scrcpy", "window_borderless", switch.get_active())
    
    def _on_max_size_changed(self, spin, _):
        """Handle max size setting change."""
        self.settings.set("scrcpy", "max_size", int(spin.get_value()))
    
    def _on_rotation_changed(self, spin, _):
        """Handle rotation setting change."""
        self.settings.set("scrcpy", "rotation", int(spin.get_value()))
    
    def _on_enable_audio_changed(self, switch, _):
        """Handle enable audio setting change."""
        self.settings.set("scrcpy", "enable_audio", switch.get_active())
    
    def _on_video_codec_changed(self, combo, _):
        """Handle video codec setting change."""
        codecs = ["h264", "h265", "av1"]
        selected = combo.get_selected()
        if 0 <= selected < len(codecs):
            self.settings.set("scrcpy", "video_codec", codecs[selected])
    
    def _on_bitrate_changed(self, spin, _):
        """Handle video bitrate setting change."""
        self.settings.set("scrcpy", "video_bitrate", int(spin.get_value()))
    
    def _on_max_fps_changed(self, spin, _):
        """Handle max FPS setting change."""
        self.settings.set("scrcpy", "max_fps", int(spin.get_value()))
    
    def _on_show_touches_changed(self, switch, _):
        """Handle show touches setting change."""
        self.settings.set("scrcpy", "show_touches", switch.get_active())
    
    def _on_stay_awake_changed(self, switch, _):
        """Handle stay awake setting change."""
        self.settings.set("scrcpy", "stay_awake", switch.get_active())
    
    def _on_turn_screen_off_changed(self, switch, _):
        """Handle turn screen off setting change."""
        self.settings.set("scrcpy", "turn_screen_off", switch.get_active())
    
    def _on_disable_screensaver_changed(self, switch, _):
        """Handle disable screensaver setting change."""
        self.settings.set("scrcpy", "disable_screensaver", switch.get_active())
    
    def _on_record_format_changed(self, combo, _):
        """Handle record format setting change."""
        formats = ["mp4", "mkv", "m4a", "mka", "opus"]
        selected = combo.get_selected()
        if 0 <= selected < len(formats):
            self.settings.set("scrcpy", "record_format", formats[selected])
    
    def _on_choose_record_path(self, button, row):
        """Handle choosing recording path."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Choose Recording Directory")
        dialog.set_modal(True)
        
        # Set initial folder
        current_path = Path(self.settings.get("scrcpy", "record_path", "~/Videos/Aurynk")).expanduser()
        if current_path.exists():
            initial_folder = Gtk.LocalFileBackend().create_file(str(current_path))
            dialog.set_initial_folder(initial_folder)
        
        dialog.select_folder(self, None, self._on_folder_selected, row)
    
    def _on_folder_selected(self, dialog, result, row):
        """Handle folder selection result."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                # Convert to path relative to home if possible
                try:
                    home = Path.home()
                    path_obj = Path(path)
                    if path_obj.is_relative_to(home):
                        relative = "~/" + str(path_obj.relative_to(home))
                        path = relative
                except (ValueError, Exception):
                    pass
                
                self.settings.set("scrcpy", "record_path", path)
                row.set_subtitle(str(Path(path).expanduser()))
        except GLib.Error as e:
            if e.matches(Gtk.DialogError.quark(), Gtk.DialogError.DISMISSED):
                logger.debug("Folder selection cancelled")
            else:
                logger.error(f"Error selecting folder: {e}")
