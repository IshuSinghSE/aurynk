#!/usr/bin/env python3
"""Main window for Aurynk application."""

import os
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from aurynk.core.adb_manager import ADBController
from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.ui.windows.about_window import AboutWindow
from aurynk.ui.windows.settings_window import SettingsWindow
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
        # Setup actions
        self._setup_actions()
        # Try to load UI from GResource, fall back to programmatic UI
        try:
            self._setup_ui_from_template()
        except Exception as e:
            logger.error(f"Could not load UI template: {e}")
            self._setup_ui_programmatically()

    def _setup_actions(self):
        """Setup window actions."""
        # Preferences action
        preferences_action = Gio.SimpleAction.new("preferences", None)
        preferences_action.connect("activate", self._on_preferences_clicked)
        self.add_action(preferences_action)

        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about_clicked)
        self.add_action(about_action)

    def _on_preferences_clicked(self, action, param):
        """Open settings window."""
        settings_window = SettingsWindow(transient_for=self)
        settings_window.present()

    def _on_about_clicked(self, action, param):
        """Show About dialog."""
        AboutWindow.show(self)

    def do_close(self):
        unregister_device_change_callback(self._device_change_callback)
        super().do_close()

    def _on_close_request(self, window):
        """Handle close request - hide window to tray if 'close_to_tray' is enabled, else quit."""
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        close_to_tray = settings.get("app", "close_to_tray", True)
        if close_to_tray:
            logger.info(
                "Close requested - hiding window instead of closing app (Close to Tray enabled)"
            )
            self.hide()
            return True  # Prevent default close
        else:
            logger.info("Close requested - quitting app and tray (Close to Tray disabled)")
            # Remove tray icon if present, and terminate tray helper process if running
            app = self.get_application()
            # Attempt to terminate tray helper by sending 'quit' command to its socket
            import socket

            tray_socket = "/tmp/aurynk_tray.sock"
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(tray_socket)
                    s.sendall(b"quit")
                    logger.info("Sent 'quit' command to tray helper via socket.")
            except Exception as e:
                logger.warning(f"Could not send 'quit' to tray helper: {e}")
            if app:
                app.quit()
            return False  # Allow default close (app will quit)

    def show_pairing_dialog(self):
        from aurynk.ui.dialogs.pairing_dialog import PairingDialog

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

        # Add menu button with settings (following GNOME HIG)
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Main Menu")
        menu = Gio.Menu()

        # Primary menu section
        menu.append("Preferences", "win.preferences")

        # About section (separated as per GNOME HIG)
        about_section = Gio.Menu()
        about_section.append("About Aurynk", "win.about")
        menu.append_section(None, about_section)

        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

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

        # Update device monitor with current paired devices and start monitoring
        app = self.get_application()
        if app and hasattr(app, "device_monitor"):
            app.device_monitor.set_paired_devices(devices)
            if not app.device_monitor._running:
                app.device_monitor.start()

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
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        auto_unpair = settings.get("adb", "auto_unpair_on_disconnect", False)
        require_confirm = settings.get("adb", "require_confirmation_for_unpair", True)
        if connected:
            # Disconnect logic
            import subprocess

            subprocess.run(["adb", "disconnect", f"{address}:{connect_port}"])
            # Immediately trigger unpair/confirmation if auto-unpair is enabled
            if auto_unpair:
                if require_confirm:
                    from gi.repository import Adw

                    dialog = Adw.MessageDialog.new(self)
                    dialog.set_heading("Remove Device?")
                    body_text = f"Are you sure you want to remove\n{address} ?"
                    dialog.set_body(body_text)
                    dialog.set_default_size(340, 120)
                    body_label = (
                        dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
                    )
                    if body_label:
                        body_label.set_line_wrap(True)
                        body_label.set_max_width_chars(40)
                    dialog.add_response("cancel", "Cancel")
                    dialog.add_response("remove", "Remove")
                    dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)

                    def on_response(dlg, response):
                        if response == "remove":
                            from aurynk.core.adb_manager import ADBController

                            ADBController().remove_device(address)
                            self._refresh_device_list()
                        dlg.destroy()

                    dialog.connect("response", on_response)
                    dialog.present()
                else:
                    from aurynk.core.adb_manager import ADBController

                    ADBController().remove_device(address)
                    self._refresh_device_list()
        else:
            # Connect logic with loading indicator - run in thread to not block UI
            def do_connection():
                nonlocal connect_port  # Declare at the top
                import subprocess
                import time

                app = self.get_application()
                discovered_port = None

                # Try to get port from device monitor (if device is currently discoverable)
                if app and hasattr(app, "device_monitor"):
                    discovered_info = app.device_monitor.get_discovered_device(address)
                    if discovered_info and discovered_info.get("connect_port"):
                        discovered_port = discovered_info["connect_port"]
                        if discovered_port != connect_port:
                            logger.info(
                                f"Using discovered port {discovered_port} instead of stored {connect_port}"
                            )
                            connect_port = discovered_port

                logger.info(f"Attempting to connect to {address}:{connect_port}...")

                # Try connection with one retry (sometimes ADB needs a moment)
                max_attempts = 2
                for attempt in range(max_attempts):
                    result = subprocess.run(
                        ["adb", "connect", f"{address}:{connect_port}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    output = (result.stdout + result.stderr).lower()

                    # Check if connection succeeded
                    if (
                        "connected" in output or "already connected" in output
                    ) and "unable" not in output:
                        if attempt > 0:
                            logger.info(f"✓ Connected successfully on attempt {attempt + 1}")
                        else:
                            logger.info(f"✓ Connected successfully to {address}:{connect_port}")
                        break
                    elif attempt < max_attempts - 1:
                        # First attempt failed, wait a moment and retry
                        logger.debug(f"Connection attempt {attempt + 1} failed, retrying...")
                        time.sleep(0.5)
                    else:
                        # All attempts failed
                        logger.warning(f"Connection failed: {output.strip()}")

                # Check final connection status
                if (
                    "connected" in output or "already connected" in output
                ) and "unable" not in output:
                    # Update stored port if it changed
                    if discovered_port and discovered_port != device.get("connect_port"):
                        device["connect_port"] = discovered_port
                        self.adb_controller.save_paired_device(device)
                        logger.info(f"Updated stored port to {discovered_port}")
                else:
                    # Connection failed - try fallback discovery
                    logger.warning(f"Connection failed: {output.strip()}")
                    logger.info("Trying to rediscover device...")

                    # Fallback to adb mdns services
                    ports = self.adb_controller.get_current_ports(address, timeout=3)
                    if ports and ports.get("connect_port"):
                        new_port = ports["connect_port"]
                        logger.info(f"Found device on port {new_port}, retrying connection...")

                        result = subprocess.run(
                            ["adb", "connect", f"{address}:{new_port}"],
                            capture_output=True,
                            text=True,
                        )

                        if result.returncode == 0:
                            device["connect_port"] = new_port
                            self.adb_controller.save_paired_device(device)
                            logger.info(f"✓ Connected and updated port to {new_port}")
                        else:
                            logger.error(
                                "Connection still failed. Please ensure device is on the network."
                            )
                    else:
                        logger.error(
                            f"Could not find device at {address}. Make sure wireless debugging is enabled."
                        )

                # Restore button state on main thread
                GLib.idle_add(self._restore_connect_button, button, original_label)
                # Refresh device list to update status
                GLib.idle_add(self._refresh_device_list)

            # Disable button and show animated connecting state
            button.set_sensitive(False)
            original_label = button.get_label()

            # Start animated dots for "Connecting..."
            self._start_connecting_animation(button)

            # Run connection in background thread
            thread = threading.Thread(target=do_connection, daemon=True)
            thread.start()
            return  # Return immediately, don't block UI

        # Refresh device list to update status (will sync tray)
        self._refresh_device_list()

    def _start_connecting_animation(self, button):
        """Animate button label with dots: Connecting -> Connecting. -> Connecting.. -> Connecting..."""
        self._animation_counter = 0
        self._animation_active = True

        def animate_dots():
            if not self._animation_active:
                return False  # Stop the animation

            dots = "." * (self._animation_counter % 4)
            button.set_label(f"Connecting{dots}")
            self._animation_counter += 1
            return True  # Continue animation

        # Update every 400ms for smooth animation
        GLib.timeout_add(400, animate_dots)

    def _restore_connect_button(self, button, original_label):
        """Restore button to its original state after connection attempt."""
        self._animation_active = False  # Stop animation
        button.set_label(original_label)
        button.set_sensitive(True)
        return False  # Don't repeat

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

    def show_unpair_confirmation_dialog(address):
        """Show a confirmation dialog before unpairing a device. Returns True if confirmed, False otherwise."""
        # This is a blocking dialog for simplicity; can be made async if needed
        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text="Unpair Device?",
        )
        dialog.format_secondary_text(f"Are you sure you want to unpair device {address}?")
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
