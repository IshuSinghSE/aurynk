import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from pathlib import Path

from gi.repository import Adw, GLib, Gtk

from aurynk.utils.logger import get_logger
from aurynk.utils.settings import SettingsManager

logger = get_logger(__name__)


class SettingsWindow(Adw.PreferencesWindow):
    """Settings window using Adwaita preferences"""

    def __init__(self, parent=None, transient_for=None, **kwargs):
        """Initialize the settings window."""
        super().__init__(**kwargs)

        self.settings = SettingsManager()

        # Window properties
        self.set_title(_("Settings"))
        self.set_default_size(560, 640)
        self.set_modal(False)  # Allow independent window movement
        self.set_hide_on_close(True)

        # Set transient parent but not modal - allows separate window movement
        parent_window = transient_for or parent
        if parent_window:
            self.set_transient_for(parent_window)
            # Keep window above parent without modal behavior
            self.set_destroy_with_parent(False)

        # Add preference pages directly for sidebar navigation
        self._create_app_page()
        self._create_adb_page()
        self._create_scrcpy_page()

        logger.info("Settings window initialized")

    def _apply_theme(self, theme: str):
        """Apply the selected theme to the application."""
        style_manager = Adw.StyleManager.get_default()

        if theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:  # system
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        logger.info(f"Applied theme: {theme}")

    def _create_app_page(self):
        """Create the Application settings page."""
        page = Adw.PreferencesPage()
        page.set_title(_("Application"))
        page.set_icon_name("applications-system-symbolic")

        # Appearance group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title(_("Appearance"))

        # Theme selector
        theme_row = Adw.ComboRow()
        theme_row.set_title(_("Theme"))
        theme_row.set_subtitle(_("Choose the application theme"))

        theme_model = Gtk.StringList.new([_("System"), _("Light"), _("Dark")])
        theme_row.set_model(theme_model)

        # Set current theme
        current_theme = self.settings.get("app", "theme", "system")
        theme_map = {"system": 0, "light": 1, "dark": 2}
        theme_row.set_selected(theme_map.get(current_theme, 0))
        theme_row.connect("notify::selected", self._on_theme_changed)

        appearance_group.add(theme_row)
        page.add(appearance_group)

        # General group
        general_group = Adw.PreferencesGroup()
        general_group.set_title(_("General"))
        general_group.set_description(_("Application behavior settings"))

        # Auto-connect switch
        auto_connect = Adw.SwitchRow()
        auto_connect.set_title(_("Auto Connect"))
        auto_connect.set_subtitle(_("Automatically connect to devices when detected"))
        auto_connect.set_active(self.settings.get("app", "auto_connect", True))
        auto_connect.connect("notify::active", self._on_auto_connect_changed)
        general_group.add(auto_connect)

        # Show notifications switch
        show_notifications = Adw.SwitchRow()
        show_notifications.set_title(_("Show Notifications"))
        show_notifications.set_subtitle(_("Display system notifications for device events"))
        show_notifications.set_active(self.settings.get("app", "show_notifications", True))
        show_notifications.connect("notify::active", self._on_show_notifications_changed)
        general_group.add(show_notifications)

        # Monitor interval
        monitor_interval = Adw.SpinRow()
        monitor_interval.set_title(_("Monitor Interval"))
        monitor_interval.set_subtitle(_("Device monitoring interval in seconds"))
        adjustment = Gtk.Adjustment(
            value=self.settings.get("app", "monitor_interval", 5),
            lower=1,
            upper=60,
            step_increment=1,
            page_increment=5,
        )
        monitor_interval.set_adjustment(adjustment)
        monitor_interval.set_digits(0)
        monitor_interval.connect("notify::value", self._on_monitor_interval_changed)
        general_group.add(monitor_interval)

        page.add(general_group)

        # System tray group
        tray_group = Adw.PreferencesGroup()
        tray_group.set_title(_("Behavior"))

        # Close to tray switch
        self.close_to_tray = Adw.SwitchRow()
        self.close_to_tray.set_title(_("Close to Tray"))
        self.close_to_tray.set_subtitle(_("Hide window to system tray when closing (X)"))
        self.close_to_tray.set_active(self.settings.get("app", "close_to_tray", True))
        self.close_to_tray.connect("notify::active", self._on_close_to_tray_changed)
        tray_group.add(self.close_to_tray)

        # Start minimized switch
        start_minimized = Adw.SwitchRow()
        start_minimized.set_title(_("Start Minimized"))
        start_minimized.set_subtitle(_("Start application minimized to tray"))
        start_minimized.set_active(self.settings.get("app", "start_minimized", False))
        start_minimized.connect("notify::active", self._on_start_minimized_changed)
        tray_group.add(start_minimized)

        # Start on system startup switch
        start_on_startup = Adw.SwitchRow()
        start_on_startup.set_title(_("Start on System Startup"))
        start_on_startup.set_subtitle(_("Automatically start Aurynk when you log in"))
        start_on_startup.set_active(self.settings.get("app", "start_on_startup", False))
        start_on_startup.connect("notify::active", self._on_start_on_startup_changed)
        tray_group.add(start_on_startup)

        page.add(tray_group)
        self.add(page)

    def _create_adb_page(self):
        """Create the ADB settings page."""
        page = Adw.PreferencesPage()
        page.set_title(_("Device"))
        page.set_icon_name("smartphone-symbolic")

        # Connection group
        connection_group = Adw.PreferencesGroup()
        connection_group.set_title(_("Connection"))
        connection_group.set_description(_("ADB connection settings"))

        # ADB Path row
        adb_path_row = Adw.ActionRow()
        adb_path_row.set_title(_("ADB Path"))
        adb_path_row.set_subtitle(_("Path to adb (leave blank for system default)"))

        adb_path_entry = Gtk.Entry()
        adb_path_entry.set_hexpand(True)
        adb_path_entry.set_placeholder_text("/usr/bin/adb")
        adb_path_entry.set_text(self.settings.get("adb", "adb_path", ""))
        adb_path_entry.connect("changed", self._on_adb_path_changed, adb_path_row)
        adb_path_row.add_suffix(adb_path_entry)

        # File picker button
        adb_path_button = Gtk.Button()
        adb_path_button.set_icon_name("folder-open-symbolic")
        adb_path_button.set_valign(Gtk.Align.CENTER)
        adb_path_button.add_css_class("flat")
        adb_path_button.connect("clicked", self._on_choose_adb_path, adb_path_entry, adb_path_row)
        adb_path_row.add_suffix(adb_path_button)

        connection_group.add(adb_path_row)

        # Connection timeout
        connection_timeout = Adw.SpinRow()
        connection_timeout.set_title(_("Connection Timeout"))
        connection_timeout.set_subtitle(_("Timeout for ADB connections in seconds"))
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "connection_timeout", 10),
            lower=1,
            upper=60,
            step_increment=1,
            page_increment=5,
        )
        connection_timeout.set_adjustment(adjustment)
        connection_timeout.set_digits(0)
        connection_timeout.connect("notify::value", self._on_connection_timeout_changed)
        connection_group.add(connection_timeout)

        # Max retry attempts
        max_retry = Adw.SpinRow()
        max_retry.set_title(_("Max Retry Attempts"))
        max_retry.set_subtitle(_("Maximum number of connection retry attempts"))
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "max_retry_attempts", 5),
            lower=0,
            upper=20,
            step_increment=1,
            page_increment=5,
        )
        max_retry.set_adjustment(adjustment)
        max_retry.set_digits(0)
        max_retry.connect("notify::value", self._on_max_retry_changed)
        connection_group.add(max_retry)

        page.add(connection_group)

        # Keep alive interval
        keep_alive = Adw.SpinRow()
        keep_alive.set_title(_("Keep Alive Connection Interval"))
        keep_alive.set_subtitle(_("Keep the connection alive (0 to disable)"))
        adjustment = Gtk.Adjustment(
            value=self.settings.get("adb", "keep_alive_interval", 0),
            lower=0,
            upper=300,
            step_increment=5,
            page_increment=10,
        )
        keep_alive.set_adjustment(adjustment)
        keep_alive.set_digits(0)
        keep_alive.connect("notify::value", self._on_keep_alive_changed)
        connection_group.add(keep_alive)

        # Security group
        security_group = Adw.PreferencesGroup()
        security_group.set_title(_("Security"))

        # Auto-unpair on disconnect
        auto_unpair = Adw.SwitchRow()
        auto_unpair.set_title(_("Auto-unpair on Disconnect"))
        auto_unpair.set_subtitle(_("Remove device from paired list when disconnected"))
        auto_unpair.set_active(self.settings.get("adb", "auto_unpair_on_disconnect", False))
        auto_unpair.connect("notify::active", self._on_auto_unpair_changed)
        security_group.add(auto_unpair)

        # Require confirmation for unpair
        require_confirm = Adw.SwitchRow()
        require_confirm.set_title(_("Require Confirmation for Unpair"))
        require_confirm.set_subtitle(_("Show confirmation dialog before unpairing a device"))
        require_confirm.set_active(
            self.settings.get("adb", "require_confirmation_for_unpair", True)
        )
        require_confirm.connect("notify::active", self._on_require_confirmation_changed)
        security_group.add(require_confirm)

        page.add(security_group)

        # Power management group
        power_group = Adw.PreferencesGroup()
        power_group.set_title(_("Power Management"))

        # Auto disconnect on sleep
        auto_disconnect = Adw.SwitchRow()
        auto_disconnect.set_title(_("Auto Disconnect on Sleep"))
        auto_disconnect.set_subtitle(_("Disconnect devices when system goes to sleep"))
        auto_disconnect.set_active(self.settings.get("adb", "auto_disconnect_on_sleep", False))
        auto_disconnect.connect("notify::active", self._on_auto_disconnect_changed)
        power_group.add(auto_disconnect)

        page.add(power_group)
        self.add(page)

    def _on_auto_unpair_changed(self, switch, _):
        self.settings.set("adb", "auto_unpair_on_disconnect", switch.get_active())

    def _on_require_confirmation_changed(self, switch, _):
        self.settings.set("adb", "require_confirmation_for_unpair", switch.get_active())

    # scrcpy settings page
    def _create_scrcpy_page(self):
        """Create the Scrcpy settings dashboard page with all features."""
        page = Adw.PreferencesPage()
        page.set_title(_("Mirroring"))
        page.set_icon_name("video-display-symbolic")

        # --- General/Session Options ---
        session_group = Adw.PreferencesGroup()
        session_group.set_title(_("Session Options"))

        # Scrcpy Path (modern: entry + file picker button)
        scrcpy_path_row = Adw.ActionRow()
        scrcpy_path_row.set_title(_("Scrcpy Path"))
        scrcpy_path_row.set_subtitle(_("Path to scrcpy binary (leave blank for system default)"))
        scrcpy_path_entry = Gtk.Entry()
        scrcpy_path_entry.set_hexpand(True)
        scrcpy_path_entry.set_placeholder_text("/usr/bin/scrcpy")
        scrcpy_path_entry.set_text(self.settings.get("scrcpy", "scrcpy_path", ""))
        scrcpy_path_row.add_suffix(scrcpy_path_entry)
        scrcpy_path_button = Gtk.Button()
        scrcpy_path_button.set_icon_name("folder-open-symbolic")
        scrcpy_path_button.set_valign(Gtk.Align.CENTER)
        scrcpy_path_button.add_css_class("flat")

        def on_choose_scrcpy_path(button, entry, row):
            from gi.repository import Gio

            dialog = Gtk.FileDialog()
            dialog.set_title(_("Select scrcpy Binary"))
            dialog.set_modal(True)
            filter_exec = Gtk.FileFilter()
            filter_exec.set_name(_("Executable files"))
            filter_exec.add_pattern("*")
            filters = Gio.ListStore.new(Gtk.FileFilter)
            filters.append(filter_exec)
            dialog.set_filters(filters)

            def on_file_selected(dialog, result):
                try:
                    file = dialog.open_finish(result)
                    if file:
                        path = file.get_path()
                        import os

                        if os.path.isfile(path) and os.access(path, os.X_OK):
                            entry.set_text(path)
                        else:
                            entry.set_text("")
                except Exception:
                    pass

            dialog.open(self, None, on_file_selected)

        scrcpy_path_button.connect(
            "clicked", on_choose_scrcpy_path, scrcpy_path_entry, scrcpy_path_row
        )
        scrcpy_path_row.add_suffix(scrcpy_path_button)
        session_group.add(scrcpy_path_row)

        # Always on Top
        always_on_top = Adw.SwitchRow()
        always_on_top.set_title(_("Always on Top"))
        always_on_top.set_subtitle(_("Keep mirror window above others."))
        always_on_top.set_active(self.settings.get("scrcpy", "always_on_top", False))
        always_on_top.connect("notify::active", self._on_always_on_top_changed)
        session_group.add(always_on_top)

        # Fullscreen
        fullscreen = Adw.SwitchRow()
        fullscreen.set_title(_("Fullscreen"))
        fullscreen.set_subtitle(_("Start in fullscreen mode."))
        fullscreen.set_active(self.settings.get("scrcpy", "fullscreen", False))
        fullscreen.connect("notify::active", self._on_fullscreen_changed)
        session_group.add(fullscreen)

        # Borderless
        borderless = Adw.SwitchRow()
        borderless.set_title(_("Borderless Window"))
        borderless.set_subtitle(_("Remove window decorations."))
        borderless.set_active(self.settings.get("scrcpy", "window_borderless", False))
        borderless.connect("notify::active", self._on_borderless_changed)
        session_group.add(borderless)

        # --- Window Size ---
        size_presets = [
            (_("Default"), None),
            ("360 x 640", (360, 640)),
            ("720 x 1280", (720, 1280)),
            ("1080 x 1920", (1080, 1920)),
            ("1440 x 2560", (1440, 2560)),
            ("1440 x 3200", (1440, 3200)),
            (_("Custom..."), "custom"),
        ]
        geom = self.settings.get("scrcpy", "window_geometry", "")
        try:
            width, height, x, y = [int(v) for v in geom.split(",")]
        except Exception:
            width, height, x, y = 800, 600, 100, 100

        # Determine which preset is selected
        def get_size_preset_idx():
            for i, preset in enumerate(size_presets):
                if preset[1] == (width, height):
                    return i
            if geom == "":
                return 0  # Default
            return len(size_presets) - 1  # Custom

        size_combo = Adw.ComboRow()
        size_combo.set_title(_("Window Initial Size"))
        size_model = Gtk.StringList.new([label for label, _ in size_presets])
        size_combo.set_model(size_model)
        size_combo.set_selected(get_size_preset_idx())

        # Custom size row (hidden unless Custom selected)
        width_adj = Gtk.Adjustment(value=width, lower=100, upper=3840, step_increment=10)
        height_adj = Gtk.Adjustment(value=height, lower=100, upper=2160, step_increment=10)
        width_spin = Gtk.SpinButton(adjustment=width_adj, digits=0)
        width_spin.set_tooltip_text(_("Width"))
        height_spin = Gtk.SpinButton(adjustment=height_adj, digits=0)
        height_spin.set_tooltip_text(_("Height"))
        wh_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        wh_box.append(Gtk.Label(label=_("Width"), xalign=0))
        wh_box.append(width_spin)
        wh_box.append(Gtk.Label(label=_("Height"), xalign=0))
        wh_box.append(height_spin)
        wh_row = Adw.ActionRow()
        wh_row.set_title(_("Custom Size"))
        wh_row.set_activatable(False)
        wh_row.add_suffix(wh_box)
        wh_row.set_visible(get_size_preset_idx() == len(size_presets) - 1)

        def update_size_row():
            idx = size_combo.get_selected()
            wh_row.set_visible(idx == len(size_presets) - 1)
            if idx == 0:
                size_combo.set_subtitle(_("Let scrcpy decide"))
            elif idx == len(size_presets) - 1:
                size_combo.set_subtitle(
                    f"{_('Width')}: {width_spin.get_value_as_int()}  {_('Height')}: {height_spin.get_value_as_int()}"
                )
            else:
                w, h = size_presets[idx][1]
                size_combo.set_subtitle(f"{w} x {h}")

        def on_size_preset_changed(combo, _):
            idx = combo.get_selected()
            update_size_row()
            if idx == 0:
                # Default: clear geometry
                self.settings.set("scrcpy", "window_geometry", "")
            elif idx == len(size_presets) - 1:
                # Custom: use current spin values
                w = width_spin.get_value_as_int()
                h = height_spin.get_value_as_int()
                geom_str = f"{w},{h},{x},{y}"
                self.settings.set("scrcpy", "window_geometry", geom_str)
            else:
                w, h = size_presets[idx][1]
                geom_str = f"{w},{h},{x},{y}"
                self.settings.set("scrcpy", "window_geometry", geom_str)

        def on_custom_size_changed(*_):
            idx = size_combo.get_selected()
            if idx == len(size_presets) - 1:
                w = width_spin.get_value_as_int()
                h = height_spin.get_value_as_int()
                geom_str = f"{w},{h},{x},{y}"
                self.settings.set("scrcpy", "window_geometry", geom_str)
                update_size_row()

        size_combo.connect("notify::selected", on_size_preset_changed)
        width_spin.connect("value-changed", on_custom_size_changed)
        height_spin.connect("value-changed", on_custom_size_changed)
        update_size_row()
        session_group.add(size_combo)
        session_group.add(wh_row)

        # --- Window Position ---
        window_pos_row = Adw.ComboRow()
        window_pos_row.set_title(_("Window Initial Position"))
        pos_labels = [
            _("Center"),
            _("Top Left"),
            _("Top Center"),
            _("Top Right"),
            _("Center Left"),
            _("Center Right"),
            _("Bottom Left"),
            _("Bottom Center"),
            _("Bottom Right"),
            _("Custom..."),
        ]
        pos_values = [
            (-1, -1),  # Center
            (0, 0),  # Top Left
            (-1, 0),  # Top Center
            (1, 0),  # Top Right
            (0, -1),  # Center Left
            (1, -1),  # Center Right
            (0, 1),  # Bottom Left
            (-1, 1),  # Bottom Center
            (1, 1),  # Bottom Right
            (None, None),  # Custom
        ]
        pos_model = Gtk.StringList.new(pos_labels)
        window_pos_row.set_model(pos_model)
        # Find current selection
        try:
            idx = pos_values.index((x, y))
        except ValueError:
            idx = len(pos_labels) - 1  # Custom
        window_pos_row.set_selected(idx)

        # Inline X/Y spin buttons for Custom
        x_adj = Gtk.Adjustment(value=x, lower=0, upper=3840, step_increment=10)
        y_adj = Gtk.Adjustment(value=y, lower=0, upper=2160, step_increment=10)
        x_spin = Gtk.SpinButton(adjustment=x_adj, digits=0)
        x_spin.set_tooltip_text(_("X Position"))
        y_spin = Gtk.SpinButton(adjustment=y_adj, digits=0)
        y_spin.set_tooltip_text(_("Y Position"))
        xy_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        xy_box.append(Gtk.Label(label="X", xalign=0))
        xy_box.append(x_spin)
        xy_box.append(Gtk.Label(label="Y", xalign=0))
        xy_box.append(y_spin)
        xy_row = Adw.ActionRow()
        xy_row.set_title(_("Custom Position"))
        xy_row.set_activatable(False)
        xy_row.add_suffix(xy_box)
        xy_row.set_visible(idx == len(pos_labels) - 1)

        def update_xy_row():
            is_custom = window_pos_row.get_selected() == len(pos_labels) - 1
            xy_row.set_visible(is_custom)
            if is_custom:
                window_pos_row.set_subtitle(
                    f"X: {x_spin.get_value_as_int()}  Y: {y_spin.get_value_as_int()}"
                )
            else:
                window_pos_row.set_subtitle("")

        def on_position_changed(combo, _):
            nonlocal x, y
            idx = combo.get_selected()
            update_xy_row()
            if idx == len(pos_labels) - 1:  # Custom
                return
            x, y = pos_values[idx]
            geom_str = f"{width},{height},{x},{y}"
            self.settings.set("scrcpy", "window_geometry", geom_str)

        def on_custom_value_changed(*_):
            nonlocal x, y
            x = x_spin.get_value_as_int()
            y = y_spin.get_value_as_int()
            geom_str = f"{width},{height},{x},{y}"
            self.settings.set("scrcpy", "window_geometry", geom_str)
            update_xy_row()

        window_pos_row.connect("notify::selected", on_position_changed)
        x_spin.connect("value-changed", on_custom_value_changed)
        y_spin.connect("value-changed", on_custom_value_changed)
        update_xy_row()
        session_group.add(window_pos_row)
        session_group.add(xy_row)

        # Disable Screensaver
        disable_screensaver = Adw.SwitchRow()
        disable_screensaver.set_title(_("Disable Screensaver"))
        disable_screensaver.set_subtitle(_("Prevent computer screensaver during mirroring."))
        disable_screensaver.set_active(self.settings.get("scrcpy", "disable_screensaver", False))
        disable_screensaver.connect("notify::active", self._on_disable_screensaver_changed)
        session_group.add(disable_screensaver)

        page.add(session_group)

        # --- Stream Quality ---
        quality_group = Adw.PreferencesGroup()
        quality_group.set_title(_("Stream Quality"))

        # Resolution Limit
        resolution_row = Adw.ComboRow()
        resolution_row.set_title(_("Resolution Limit"))
        resolution_row.set_subtitle(_("Limit the maximum dimension of the video stream."))
        res_options = [_("Native (Max)"), "1080p", "720p"]
        res_model = Gtk.StringList.new(res_options)
        resolution_row.set_model(res_model)
        current_max = self.settings.get("scrcpy", "max_size", 0)
        if current_max == 0:
            resolution_row.set_selected(0)
        elif current_max >= 1920:
            resolution_row.set_selected(1)
        else:
            resolution_row.set_selected(2)

        def on_resolution_changed(combo, _):
            idx = combo.get_selected()
            if idx == 0:
                self.settings.set("scrcpy", "max_size", 0)
            elif idx == 1:
                self.settings.set("scrcpy", "max_size", 1920)
            else:
                self.settings.set("scrcpy", "max_size", 1280)

        resolution_row.connect("notify::selected", on_resolution_changed)
        quality_group.add(resolution_row)

        # Video Bitrate
        bitrate_row = Adw.ActionRow()
        bitrate_row.set_title(_("Video Bitrate (Mbps)"))
        bitrate_row.set_subtitle(_("Higher is better quality but uses more bandwidth."))
        bitrate_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 2, 16, 1)
        bitrate_scale.set_value(self.settings.get("scrcpy", "video_bitrate", 8))
        bitrate_scale.set_digits(0)
        bitrate_scale.set_hexpand(True)
        bitrate_scale.set_draw_value(True)
        bitrate_scale.set_value_pos(Gtk.PositionType.RIGHT)
        bitrate_scale.set_tooltip_text(_("Video bitrate in Mbps"))

        def on_bitrate_changed(scale):
            self.settings.set("scrcpy", "video_bitrate", int(scale.get_value()))

        bitrate_scale.connect("value-changed", on_bitrate_changed)
        bitrate_row.add_suffix(bitrate_scale)
        quality_group.add(bitrate_row)

        # Frame Rate Cap
        fps_row = Adw.ComboRow()
        fps_row.set_title(_("Frame Rate Cap"))
        fps_row.set_subtitle(_("Limit the frame rate to save resources."))
        fps_options = [_("Max"), "60 FPS", "30 FPS"]
        fps_model = Gtk.StringList.new(fps_options)
        fps_row.set_model(fps_model)
        current_fps = self.settings.get("scrcpy", "max_fps", 0)
        if current_fps == 60:
            fps_row.set_selected(1)
        elif current_fps == 30:
            fps_row.set_selected(2)
        else:
            fps_row.set_selected(0)

        def on_fps_changed(combo, _):
            idx = combo.get_selected()
            if idx == 1:
                self.settings.set("scrcpy", "max_fps", 60)
            elif idx == 2:
                self.settings.set("scrcpy", "max_fps", 30)
            else:
                self.settings.set("scrcpy", "max_fps", 0)

        fps_row.connect("notify::selected", on_fps_changed)
        quality_group.add(fps_row)

        # Video Codec
        codec_row = Adw.ComboRow()
        codec_row.set_title(_("Video Codec"))
        codec_row.set_subtitle(_("Codec for video encoding."))
        codec_options = ["h264", "h265", "av1"]
        codec_model = Gtk.StringList.new(codec_options)
        codec_row.set_model(codec_model)
        current_codec = self.settings.get("scrcpy", "video_codec", "h264")
        codec_row.set_selected(
            codec_options.index(current_codec) if current_codec in codec_options else 0
        )

        def on_codec_changed(combo, _):
            idx = combo.get_selected()
            codecs = ["h264", "h265", "av1"]
            if 0 <= idx < len(codecs):
                self.settings.set("scrcpy", "video_codec", codecs[idx])

        codec_row.connect("notify::selected", on_codec_changed)
        quality_group.add(codec_row)

        page.add(quality_group)

        # --- Audio & Input ---
        audio_group = Adw.PreferencesGroup()
        audio_group.set_title(_("Audio Input"))

        # Enable Audio
        enable_audio = Adw.SwitchRow()
        enable_audio.set_title(_("Enable Audio"))
        enable_audio.set_subtitle(
            _("Stream device audio to PC (experimental, may not work over wireless connection).")
        )
        enable_audio.set_active(not self.settings.get("scrcpy", "no_audio", False))

        def on_enable_audio_changed(switch, _):
            self.settings.set("scrcpy", "no_audio", not switch.get_active())

        enable_audio.connect("notify::active", on_enable_audio_changed)
        audio_group.add(enable_audio)

        # Audio Source
        audio_source_row = Adw.ComboRow()
        audio_source_row.set_title(_("Audio Source (experimental)"))
        audio_source_row.set_subtitle(
            _(
                "Choose between device output or mic (experimental, may not work over wireless connection)."
            )
        )
        audio_source_options = [_("default"), _("output"), _("mic")]
        audio_source_model = Gtk.StringList.new(audio_source_options)
        audio_source_row.set_model(audio_source_model)
        current_audio_source = self.settings.get("scrcpy", "audio_source", "default")
        audio_source_row.set_selected(
            audio_source_options.index(current_audio_source)
            if current_audio_source in audio_source_options
            else 0
        )

        def on_audio_source_changed(combo, _):
            idx = combo.get_selected()
            if 0 <= idx < len(audio_source_options):
                self.settings.set("scrcpy", "audio_source", audio_source_options[idx])

        audio_source_row.connect("notify::selected", on_audio_source_changed)
        audio_group.add(audio_source_row)

        # Show Touches
        show_touches = Adw.SwitchRow()
        show_touches.set_title(_("Show Touches"))
        show_touches.set_subtitle(
            _("Visual feedback for touches (only works for physical device input).")
        )
        show_touches.set_active(self.settings.get("scrcpy", "show_touches", False))

        def on_show_touches_changed(switch, _):
            self.settings.set("scrcpy", "show_touches", switch.get_active())
            # Immediately update device setting via adb
            try:
                import subprocess

                adb_path = self.settings.get("adb", "adb_path", None)
                if not adb_path:
                    adb_path = "adb"
                value = "1" if switch.get_active() else "0"
                import logging

                logging.info(f"Using adb path: {adb_path} for show_touches toggle")
                subprocess.run(
                    [adb_path, "shell", "settings", "put", "system", "show_touches", value],
                    check=False,
                )
            except Exception as e:
                import logging

                logging.warning(f"Failed to set show_touches via adb from settings: {e}")

        show_touches.connect("notify::active", on_show_touches_changed)
        audio_group.add(show_touches)

        # Keep Device Screen On
        stay_awake = Adw.SwitchRow()
        stay_awake.set_title(_("Keep Device Screen On (experimental)"))
        stay_awake.set_subtitle(
            _(
                "Keep device screen on during mirroring (may not work on all devices or wireless mode)."
            )
        )
        stay_awake.set_active(self.settings.get("scrcpy", "stay_awake", False))

        def on_stay_awake_changed(switch, _):
            self.settings.set("scrcpy", "stay_awake", switch.get_active())
            # Mutually exclusive: turning on disables turn_screen_off
            if switch.get_active():
                self.settings.set("scrcpy", "turn_screen_off", False)
                turn_screen_off.set_active(False)

        stay_awake.connect("notify::active", on_stay_awake_changed)
        audio_group.add(stay_awake)

        # Turn Device Screen Off
        turn_screen_off = Adw.SwitchRow()
        turn_screen_off.set_title(_("Turn Device Screen Off"))
        turn_screen_off.set_subtitle(_("Mirror with device screen off."))
        turn_screen_off.set_active(self.settings.get("scrcpy", "turn_screen_off", False))

        def on_turn_screen_off_changed(switch, _):
            self.settings.set("scrcpy", "turn_screen_off", switch.get_active())
            # Mutually exclusive: turning on disables stay_awake
            if switch.get_active():
                self.settings.set("scrcpy", "stay_awake", False)
                stay_awake.set_active(False)

        turn_screen_off.connect("notify::active", on_turn_screen_off_changed)
        audio_group.add(turn_screen_off)

        # Read-only Mode
        readonly_mode = Adw.SwitchRow()
        readonly_mode.set_title(_("View-only Mode"))
        readonly_mode.set_subtitle(_("Disable device control (view only)"))
        readonly_mode.set_active(self.settings.get("scrcpy", "no_control", False))

        def on_readonly_mode_changed(switch, _):
            self.settings.set("scrcpy", "no_control", switch.get_active())

        readonly_mode.connect("notify::active", on_readonly_mode_changed)
        audio_group.add(readonly_mode)

        # Use Keyboard & Mouse via OTG
        otg_row = Adw.ComboRow()
        otg_row.set_title(_("Keyboard/Mouse via OTG (experimental)"))
        otg_row.set_subtitle(_("Control device using OTG keyboard/mouse"))
        otg_options = [
            _("None"),
            _("Keyboard (uhid)"),
            _("Mouse (uhid)"),
            _("Keyboard (aoa)"),
            _("Mouse (aoa)"),
        ]
        otg_model = Gtk.StringList.new(otg_options)
        otg_row.set_model(otg_model)
        current_otg = self.settings.get("scrcpy", "otg_mode", "None")
        otg_row.set_selected(otg_options.index(current_otg) if current_otg in otg_options else 0)

        def on_otg_mode_changed(combo, _):
            idx = combo.get_selected()
            if 0 <= idx < len(otg_options):
                self.settings.set("scrcpy", "otg_mode", otg_options[idx])

        otg_row.connect("notify::selected", on_otg_mode_changed)
        audio_group.add(otg_row)

        # Ensure group is added after all children
        page.add(audio_group)

        # --- Recording ---
        recording_group = Adw.PreferencesGroup()
        recording_group.set_title(_("Recording"))

        # Record Mirroring
        record_session = Adw.SwitchRow()
        record_session.set_title(_("Record Mirroring"))
        record_session.set_subtitle(_("Enable/disable recording of mirroring session."))
        record_session.set_active(self.settings.get("scrcpy", "record", False))

        def on_record_session_changed(switch, _):
            self.settings.set("scrcpy", "record", switch.get_active())

        record_session.connect("notify::active", on_record_session_changed)
        recording_group.add(record_session)

        # Record Format
        record_format_row = Adw.ComboRow()
        record_format_row.set_title(_("Record Format"))
        record_format_row.set_subtitle(_("Select recording format."))
        record_format_options = ["mp4", "mkv", "m4a", "mka", "opus"]
        record_format_model = Gtk.StringList.new(record_format_options)
        record_format_row.set_model(record_format_model)
        current_format = self.settings.get("scrcpy", "record_format", "mp4")
        record_format_row.set_selected(
            record_format_options.index(current_format)
            if current_format in record_format_options
            else 0
        )

        def on_record_format_changed(combo, _):
            idx = combo.get_selected()
            if 0 <= idx < len(record_format_options):
                self.settings.set("scrcpy", "record_format", record_format_options[idx])

        record_format_row.connect("notify::selected", on_record_format_changed)
        recording_group.add(record_format_row)

        # Recording Path
        record_path_row = Adw.ActionRow()
        record_path_row.set_title(_("Recording Path"))
        record_path_row.set_subtitle(
            str(self.settings.get("scrcpy", "record_path", "~/Videos/Aurynk"))
        )
        record_path_button = Gtk.Button()
        record_path_button.set_icon_name("folder-open-symbolic")
        record_path_button.set_valign(Gtk.Align.CENTER)
        record_path_button.add_css_class("flat")

        def on_choose_record_path(button, row):
            from pathlib import Path

            from gi.repository import Gtk as GtkLocal

            dialog = GtkLocal.FileDialog()
            dialog.set_title(_("Choose Recording Directory"))
            dialog.set_modal(True)
            Path(self.settings.get("scrcpy", "record_path", "~/Videos/Aurynk")).expanduser()

            # No set_initial_folder in Gtk4, so skip
            def on_folder_selected(dialog, result, row):
                try:
                    folder = dialog.select_folder_finish(result)
                    if folder:
                        path = folder.get_path()
                        self.settings.set("scrcpy", "record_path", path)
                        row.set_subtitle(str(Path(path).expanduser()))
                except Exception:
                    pass

            dialog.select_folder(self, None, lambda d, r: on_folder_selected(d, r, row))

        record_path_button.connect("clicked", on_choose_record_path, record_path_row)
        record_path_row.add_suffix(record_path_button)
        recording_group.add(record_path_row)

        page.add(recording_group)

        # --- Advanced ---
        advanced_group = Adw.PreferencesGroup()
        advanced_group.set_title(_("Advanced Options (experimental)"))

        # Hardware Acceleration
        hwaccel_row = Adw.ComboRow()
        hwaccel_row.set_title(_("Hardware Acceleration"))
        hwaccel_row.set_subtitle(_("Use GPU for encoding."))
        # Translators: "Default" is a configuration option value meaning the standard or preset value
        hwaccel_options = [_("Default"), "h264", "h265", "av1"]
        hwaccel_model = Gtk.StringList.new(hwaccel_options)
        hwaccel_row.set_model(hwaccel_model)
        current_hwaccel = self.settings.get("scrcpy", "video_encoder", "Default")
        hwaccel_row.set_selected(
            hwaccel_options.index(current_hwaccel) if current_hwaccel in hwaccel_options else 0
        )

        def on_hwaccel_changed(combo, _):
            idx = combo.get_selected()
            if 0 <= idx < len(hwaccel_options):
                self.settings.set("scrcpy", "video_encoder", hwaccel_options[idx])

        hwaccel_row.connect("notify::selected", on_hwaccel_changed)
        advanced_group.add(hwaccel_row)

        # No Window
        no_window = Adw.SwitchRow()
        no_window.set_title(_("No Window"))
        no_window.set_subtitle(_("Run without a window (background only)"))
        no_window.set_active(self.settings.get("scrcpy", "no_window", False))

        def on_no_window_changed(switch, _):
            self.settings.set("scrcpy", "no_window", switch.get_active())

        no_window.connect("notify::active", on_no_window_changed)
        advanced_group.add(no_window)

        # No Video
        no_video = Adw.SwitchRow()
        no_video.set_title(_("No Video"))
        no_video.set_subtitle(_("Audio/control only (no video stream)"))
        no_video.set_active(self.settings.get("scrcpy", "no_video", False))

        def on_no_video_changed(switch, _):
            self.settings.set("scrcpy", "no_video", switch.get_active())

        no_video.connect("notify::active", on_no_video_changed)
        advanced_group.add(no_video)

        # No Audio
        no_audio = Adw.SwitchRow()
        no_audio.set_title(_("No Audio"))
        no_audio.set_subtitle(_("Video/control only (no audio stream)"))
        no_audio.set_active(self.settings.get("scrcpy", "no_audio", False))

        def on_no_audio_changed(switch, _):
            self.settings.set("scrcpy", "no_audio", switch.get_active())

        no_audio.connect("notify::active", on_no_audio_changed)
        advanced_group.add(no_audio)

        # No Control
        no_control = Adw.SwitchRow()
        no_control.set_title(_("No Control"))
        no_control.set_subtitle(_("Mirror only, no input"))
        no_control.set_active(self.settings.get("scrcpy", "no_control", False))

        def on_no_control_changed(switch, _):
            self.settings.set("scrcpy", "no_control", switch.get_active())

        no_control.connect("notify::active", on_no_control_changed)
        advanced_group.add(no_control)

        page.add(advanced_group)
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
            theme = themes[selected]
            self.settings.set("app", "theme", theme)
            # Apply theme immediately
            self._apply_theme(theme)

    def _on_minimize_to_tray_changed(self, switch, _):
        """Handle minimize to tray setting change."""
        pass  # Removed: Minimize to Tray option no longer exists

    def _on_start_minimized_changed(self, switch, _):
        """Handle start minimized setting change."""
        self.settings.set("app", "start_minimized", switch.get_active())

    def _on_close_to_tray_changed(self, switch, _):
        value = switch.get_active()
        self.settings.set("app", "close_to_tray", value)

    def _on_start_on_startup_changed(self, switch, _):
        """Handle start on system startup setting change."""
        enabled = switch.get_active()
        self.settings.set("app", "start_on_startup", enabled)
        if enabled:
            self._create_autostart_entry()
        else:
            self._remove_autostart_entry()

    def _create_autostart_entry(self):
        """Create a .desktop entry in ~/.config/autostart to enable autostart."""
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_entry = autostart_dir / "aurynk.desktop"
        # Always use the launcher script for autostart
        script_path = Path(__file__).parent.parent.parent / "scripts" / "aurynk"
        exec_path = str(script_path)
        entry = f"""[Desktop Entry]\nType=Application\nExec={exec_path}\nHidden=false\nNoDisplay=false\nX-GNOME-Autostart-enabled=true\nName=Aurynk\nComment=Android device manager and mirroring\n"""
        desktop_entry.write_text(entry)

    def _remove_autostart_entry(self):
        """Remove the autostart .desktop entry if it exists."""
        desktop_entry = Path.home() / ".config" / "autostart" / "aurynk.desktop"
        if desktop_entry.exists():
            desktop_entry.unlink()

    # ADB settings callbacks
    def _on_connection_timeout_changed(self, spin, _):
        """Handle connection timeout setting change."""
        self.settings.set("adb", "connection_timeout", int(spin.get_value()))

    def _on_adb_path_changed(self, entry, row):
        """Handle ADB path entry change."""
        import os

        path = entry.get_text().strip()
        if path and (not os.path.isfile(path) or not os.access(path, os.X_OK)):
            row.set_subtitle(_("Invalid path or not executable"))
            entry.get_style_context().add_class("error")
        else:
            row.set_subtitle(_("Path to adb binary (leave blank for system default)"))
            entry.get_style_context().remove_class("error")
            self.settings.set("adb", "adb_path", path)

    def _on_choose_adb_path(self, button, entry, row):
        """Open file chooser for adb binary."""
        from gi.repository import Gio

        dialog = Gtk.FileDialog()
        dialog.set_title(_("Select ADB Binary"))
        dialog.set_modal(True)
        # Only allow single file selection (not folders or multiple files)
        # dialog.select_folder(False)
        # Create a filter for executable files (show all, validate on select)
        filter_exec = Gtk.FileFilter()
        filter_exec.set_name(_("Executable files"))
        filter_exec.add_pattern("*")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_exec)
        dialog.set_filters(filters)

        def on_file_selected(dialog, result):
            try:
                file = dialog.open_finish(result)
                if file:
                    path = file.get_path()
                    import os

                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        entry.set_text(path)
                    else:
                        entry.set_text("")
            except Exception:
                pass

        dialog.open(self, None, on_file_selected)

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
        current_path = Path(
            self.settings.get("scrcpy", "record_path", "~/Videos/Aurynk")
        ).expanduser()
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
