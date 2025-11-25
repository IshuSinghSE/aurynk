#!/usr/bin/env python3
"""Main window for Aurynk application."""

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

from aurynk.core.adb_manager import ADBController
from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.utils.adb_utils import is_device_connected
from aurynk.utils.device_events import (
    register_device_change_callback,
    unregister_device_change_callback,
)
from aurynk.utils.logger import get_logger

logger = get_logger("MainWindow")


class AurynkWindow(Adw.ApplicationWindow):
    """Main application window."""

    __gtype_name__ = "AurynkWindow"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialize ADB controller
        self.adb_controller = ADBController()
        # Register for device change events
        from gi.repository import GLib

        def safe_refresh():
            GLib.idle_add(self._refresh_device_list)

        self._device_change_callback = safe_refresh
        register_device_change_callback(self._device_change_callback)
        # Load custom CSS for outlined button
        self._load_custom_css()
        # Window properties
        self.set_title("Aurynk")
        self.set_icon_name("io.github.IshuSinghSE.aurynk")
        self.set_default_size(700, 520)
        # Store window position when hiding
        self._stored_position = None
        # Handle close-request to hide window instead of closing app
        self.connect("close-request", self._on_close_request)
        # Try to load UI from GResource, fall back to programmatic UI
        try:
            self._setup_ui_from_template()
        except Exception as e:
            logger.error(f"Could not load UI template: {e}")
            self._setup_ui_programmatically()

    def do_close(self):
        unregister_device_change_callback(self._device_change_callback)
        super().do_close()

    def _on_close_request(self, window):
        """Handle close request - hide window instead of destroying it."""
        logger.info("Close requested - hiding window instead of closing app")
        self.hide()
        # Return True to prevent the default close behavior
        return True

    def show_pairing_dialog(self):
        from aurynk.dialogs.pairing_dialog import PairingDialog

        dialog = PairingDialog(self)
        dialog.present()

    def _setup_ui_from_template(self):
        """Load UI from XML template (GResource)."""
        builder = Gtk.Builder.new_from_resource("/io/github/IshuSinghSE/aurynk/ui/main_window.ui")
        main_content = builder.get_object("main_content")
        if main_content:
            self.set_content(main_content)
            self.device_list_box = builder.get_object("device_list")
            add_device_btn = builder.get_object("add_device_button")
            if add_device_btn:
                add_device_btn.connect("clicked", self._on_add_device_clicked)
            # No search entry, no app logo/name in template path
            self._refresh_device_list()
        else:
            raise Exception("Could not find main_content in UI template")

    def _load_custom_css(self):
        css_provider = Gtk.CssProvider()
        css_path = "/io/github/IshuSinghSE/aurynk/styles/aurynk.css"
        try:
            css_provider.load_from_resource(css_path)
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except Exception as e:
            logger.warning(f"Could not load CSS from {css_path}: {e}")

    def _setup_ui_programmatically(self):
        """Create UI programmatically if template loading fails."""
        # Main vertical box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_show_end_title_buttons(True)

        # Header content box
        header_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Add Device button
        add_device_btn = Gtk.Button()
        add_device_btn.set_label("Add Device")
        add_device_btn.set_icon_name("list-add-symbolic")
        add_device_btn.border_width = 2
        add_device_btn.connect("clicked", self._on_add_device_clicked)

        # header_content.append(app_header_box)
        header_content.append(add_device_btn)
        header_bar.set_title_widget(header_content)

        main_box.append(header_bar)

        # Scrolled window for device list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        # Device list container
        self.device_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.device_list_box.set_margin_top(24)
        self.device_list_box.set_margin_bottom(24)
        self.device_list_box.set_margin_start(32)
        self.device_list_box.set_margin_end(32)

        # Title label
        devices_label = Gtk.Label()
        devices_label.set_markup('<span size="large" weight="bold">Paired Devices</span>')
        devices_label.set_halign(Gtk.Align.START)
        devices_label.set_margin_bottom(12)
        self.device_list_box.append(devices_label)

        scrolled.set_child(self.device_list_box)
        main_box.append(scrolled)

        self.set_content(main_box)

        # Load initial device list
        self._refresh_device_list()

    def _refresh_device_list(self):
        """Refresh the device list from storage and sync tray."""
        if not hasattr(self, "device_list_box") or self.device_list_box is None:
            # UI template not loaded yet, skip
            return

        # Force reload from file to get latest changes from other windows/processes
        self.adb_controller.device_store.reload()
        devices = self.adb_controller.load_paired_devices()

        # Clear existing device rows
        child = self.device_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.device_list_box.remove(child)
            child = next_child

        # Add device rows
        if devices:
            for device in devices:
                device_row = self._create_device_row(device)
                self.device_list_box.append(device_row)
        else:
            # Show empty state with image and text
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_halign(Gtk.Align.CENTER)
            empty_box.set_hexpand(True)
            empty_box.set_vexpand(True)
            # Use Gtk.Image with EventControllerMotion for pointer cursor and scaling
            empty_image = Gtk.Image.new_from_resource(
                "/io/github/IshuSinghSE/aurynk/icons/io.github.IshuSinghSE.aurynk.add-device.png"
            )
            empty_image.set_pixel_size(120)
            empty_image.set_halign(Gtk.Align.CENTER)
            empty_image.set_valign(Gtk.Align.CENTER)
            empty_image.add_css_class("clickable-image")
            empty_image.set_tooltip_text("Click to add a device")

            # Add scaling and pointer cursor on hover
            def on_enter(controller, x, y, image):
                image.add_css_class("hovered-image")
                image.set_cursor_from_name("pointer")

            def on_leave(controller, image):
                image.remove_css_class("hovered-image")
                image.set_cursor_from_name(None)

            motion_controller = Gtk.EventControllerMotion.new()
            motion_controller.connect("enter", on_enter, empty_image)
            motion_controller.connect("leave", on_leave, empty_image)
            empty_image.add_controller(motion_controller)

            # Click gesture
            gesture = Gtk.GestureClick.new()
            gesture.connect(
                "released", lambda gesture, n, x, y: self._on_add_device_clicked(empty_image)
            )
            empty_image.add_controller(gesture)

            # Load CSS for scaling effect from external file if not already loaded
            css_provider = Gtk.CssProvider()
            css_path = "/io/github/IshuSinghSE/aurynk/styles/aurynk.css"
            try:
                css_provider.load_from_resource(css_path)
                Gtk.StyleContext.add_provider_for_display(
                    Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
            except Exception as e:
                logger.warning(f"Could not load CSS from {css_path}: {e}")

            empty_box.append(empty_image)

            empty_label = Gtk.Label()
            empty_label.set_markup('<span alpha="50%" >Click "Add Device" to get started</span>')
            empty_label.set_justify(Gtk.Justification.CENTER)
            empty_label.set_margin_bottom(64)
            empty_label.set_halign(Gtk.Align.CENTER)
            empty_box.append(empty_label)

            self.device_list_box.append(empty_box)

        # Always sync tray after device list changes
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _create_device_row(self, device):
        """Create a row widget for a device."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_start(24)
        row.set_margin_end(24)

        # Add CSS classes for styling
        row.add_css_class("card")

        # Device icon
        # Use permanent location for screenshots
        screenshot_path = device.get("thumbnail")
        if screenshot_path and not os.path.isabs(screenshot_path):
            screenshot_path = os.path.expanduser(
                os.path.join("~/.local/share/aurynk/screenshots", screenshot_path)
            )
        if not screenshot_path or not os.path.exists(screenshot_path):
            # Use Flatpak-compliant GResource path for fallback icon
            icon = Gtk.Image.new_from_resource(
                "/io/github/IshuSinghSE/aurynk/icons/io.github.IshuSinghSE.aurynk.device.png"
            )
        else:
            icon = Gtk.Image.new_from_file(screenshot_path)
        icon.set_margin_top(4)
        icon.set_margin_bottom(4)

        icon.set_pixel_size(56)
        row.append(icon)

        # Device info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_margin_top(12)
        info_box.set_margin_bottom(8)
        info_box.set_hexpand(True)

        # Device name
        name_label = Gtk.Label()
        dev_name = device.get("name", "Unknown Device")
        name_label.set_markup(f'<span size="large" weight="bold">{dev_name}</span>')
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        # Device details
        details = []
        if device.get("manufacturer"):
            details.append(device["manufacturer"])
        if device.get("model"):
            details.append(device["model"])
        if device.get("android_version"):
            details.append(f"Android {device['android_version']}")

        if details:
            details_label = Gtk.Label(label=" • ".join(details))
            details_label.set_halign(Gtk.Align.START)
            details_label.add_css_class("dim-label")
            info_box.append(details_label)

        row.append(info_box)

        # Status and actions
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_box.set_margin_end(12)
        status_btn = Gtk.Button()
        address = device.get("address")
        connect_port = device.get("connect_port")
        connected = False
        if address and connect_port:
            connected = is_device_connected(address, connect_port)
        if connected:
            status_btn.set_label("Disconnect")
            status_btn.add_css_class("destructive-action")
        else:
            status_btn.set_label("Connect")
            status_btn.add_css_class("suggested-action")
        status_btn.set_valign(Gtk.Align.CENTER)
        status_btn.connect("clicked", self._on_status_clicked, device, connected)
        status_box.append(status_btn)

        # Mirror button
        mirror_btn = Gtk.Button()
        mirror_btn.set_icon_name("screen-shared-symbolic")
        mirror_btn.set_tooltip_text("Screen Mirror")
        mirror_btn.set_sensitive(connected)
        mirror_btn.set_valign(Gtk.Align.CENTER)
        if connected:
            mirror_btn.add_css_class("suggested-action")
        else:
            mirror_btn.add_css_class("destructive-action")
        mirror_btn.connect("clicked", self._on_mirror_clicked, device)
        status_box.append(mirror_btn)

        # Details button
        details_btn = Gtk.Button()
        details_btn.set_icon_name("preferences-system-details-symbolic")
        details_btn.set_tooltip_text("Details")
        details_btn.set_valign(Gtk.Align.CENTER)
        details_btn.connect("clicked", self._on_device_details_clicked, device)
        status_box.append(details_btn)

        row.append(status_box)
        return row

    def _on_status_clicked(self, button, device, connected):
        address = device.get("address")
        connect_port = device.get("connect_port")
        if not address or not connect_port:
            return
        if connected:
            # Disconnect logic
            import subprocess

            subprocess.run(["adb", "disconnect", f"{address}:{connect_port}"])
        else:
            # Connect logic
            import subprocess

            subprocess.run(["adb", "connect", f"{address}:{connect_port}"])
        # Refresh device list to update status (will sync tray)
        self._refresh_device_list()

    def _on_add_device_clicked(self, button):
        """Handle Add Device button click."""
        from aurynk.ui.dialogs.pairing_dialog import PairingDialog

        dialog = PairingDialog(self)
        dialog.present()

    def _on_device_details_clicked(self, button, device):
        """Handle device details button click."""
        from aurynk.ui.windows.device_details import DeviceDetailsWindow

        details_window = DeviceDetailsWindow(device, self)
        details_window.present()

    def _on_search_changed(self, search_entry):
        """Handle search entry text change."""
        search_text = search_entry.get_text().lower()

        # Filter device list based on search text
        # TODO: Implement filtering logic
        logger.debug(f"Search: {search_text}")

    def _get_scrcpy_manager(self):
        if not hasattr(self, "_scrcpy_manager"):
            self._scrcpy_manager = ScrcpyManager()
            self._scrcpy_manager.add_stop_callback(self._on_mirror_stopped)
        return self._scrcpy_manager

    def _on_mirror_stopped(self, serial):
        """Callback when scrcpy process exits."""
        logger.info(f"Mirror stopped for {serial}, refreshing UI")
        from gi.repository import GLib

        GLib.idle_add(self._handle_mirror_stop_ui_update)

    def _handle_mirror_stop_ui_update(self):
        self._refresh_device_list()
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _on_mirror_clicked(self, button, device):
        address = device.get("address")
        connect_port = device.get("connect_port")
        device_name = device.get("name")
        if not address or not connect_port:
            return
        scrcpy = self._get_scrcpy_manager()
        if scrcpy.is_mirroring(address, connect_port):
            scrcpy.stop_mirror(address, connect_port)
        else:
            scrcpy.start_mirror(address, connect_port, device_name)
        # Sync tray after mirroring
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()
