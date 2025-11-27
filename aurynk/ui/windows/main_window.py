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
        # Load custom CSS
        self._load_custom_css()
        # Window properties
        self.set_title("Aurynk")
        self.set_icon_name("io.github.IshuSinghSE.aurynk")
        self.set_default_size(800, 600)
        # Store window position when hiding
        self._stored_position = None
        # Handle close-request to hide window instead of closing app
        self.connect("close-request", self._on_close_request)
        # Setup actions
        self._setup_actions()

        self._setup_ui()

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

    def _setup_ui(self):
        """Create UI programmatically."""
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # Header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_show_end_title_buttons(True)

        # Add Device button
        add_device_btn = Gtk.Button()
        add_device_btn.set_icon_name("list-add-symbolic")
        add_device_btn.set_tooltip_text("Add Device")
        add_device_btn.connect("clicked", self._on_add_device_clicked)
        # Use primary style for CTA
        add_device_btn.add_css_class("suggested-action")
        header_bar.pack_start(add_device_btn)

        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Main Menu")
        menu = Gio.Menu()
        menu.append("Preferences", "win.preferences")
        about_section = Gio.Menu()
        about_section.append("About Aurynk", "win.about")
        menu.append_section(None, about_section)
        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        main_box.append(header_bar)

        # Content area with clamping for better layout on wide screens
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_tightening_threshold(600)

        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_child(clamp)
        main_box.append(scrolled)

        # Device list container (PreferencesGroup style)
        self.device_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.device_list_box.set_margin_top(24)
        self.device_list_box.set_margin_bottom(24)
        self.device_list_box.set_margin_start(12)
        self.device_list_box.set_margin_end(12)

        clamp.set_child(self.device_list_box)

        # Load initial device list
        self._refresh_device_list()

    def _refresh_device_list(self):
        """Refresh the device list from storage and sync tray."""
        if not hasattr(self, "device_list_box") or self.device_list_box is None:
            return

        # Force reload from file
        self.adb_controller.device_store.reload()
        devices = self.adb_controller.load_paired_devices()

        # Update device monitor
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

        if devices:
            # Create a PreferencesGroup for the list
            group = Adw.PreferencesGroup()
            group.set_title("Paired Devices")

            for device in devices:
                row = self._create_device_row(device)
                group.add(row)

            self.device_list_box.append(group)
        else:
            # Empty state using Adw.StatusPage
            status_page = Adw.StatusPage()
            status_page.set_icon_name("io.github.IshuSinghSE.aurynk")
            status_page.set_title("No Devices Paired")
            status_page.set_description("Scan a QR code to wirelessly connect your Android device.")
            status_page.set_vexpand(True)

            # Add CTA button to status page
            cta_btn = Gtk.Button()
            cta_btn.set_label("Add Device")
            cta_btn.set_icon_name("list-add-symbolic")
            cta_btn.add_css_class("pill")
            cta_btn.add_css_class("suggested-action")
            cta_btn.set_halign(Gtk.Align.CENTER)
            cta_btn.connect("clicked", self._on_add_device_clicked)
            status_page.set_child(cta_btn)

            self.device_list_box.append(status_page)

        # Always sync tray after device list changes
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _create_device_row(self, device):
        """Create an Adw.ActionRow for a device."""
        row = Adw.ActionRow()
        row.set_selectable(False)

        # Device name and subtitle
        dev_name = device.get("name", "Unknown Device")
        row.set_title(dev_name)

        details = []
        if device.get("model"):
            details.append(device["model"])
        if device.get("android_version"):
            details.append(f"Android {device['android_version']}")
        row.set_subtitle(" • ".join(details) if details else "Unknown Model")

        # Icon prefix
        screenshot_path = device.get("thumbnail")
        if screenshot_path and not os.path.isabs(screenshot_path):
            screenshot_path = os.path.expanduser(
                os.path.join("~/.local/share/aurynk/screenshots", screenshot_path)
            )

        if screenshot_path and os.path.exists(screenshot_path):
            icon_paintable = Gtk.Image.new_from_file(screenshot_path).get_paintable()
            row.add_prefix(Gtk.Image.new_from_paintable(icon_paintable))
        else:
             row.add_prefix(Gtk.Image.new_from_icon_name("smartphone-symbolic"))

        # Connection Status & Actions
        address = device.get("address")
        connect_port = device.get("connect_port")
        connected = False
        if address and connect_port:
            connected = is_device_connected(address, connect_port)

        # Action Box (Suffix)
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions_box.set_valign(Gtk.Align.CENTER)

        # Mirror Button
        mirror_btn = Gtk.Button()
        mirror_btn.set_icon_name("screen-shared-symbolic")
        mirror_btn.set_tooltip_text("Screen Mirror")
        mirror_btn.add_css_class("flat")
        mirror_btn.set_sensitive(connected)
        mirror_btn.connect("clicked", self._on_mirror_clicked, device)
        actions_box.append(mirror_btn)

        # Details Button
        details_btn = Gtk.Button()
        details_btn.set_icon_name("preferences-system-details-symbolic")
        details_btn.set_tooltip_text("Device Details")
        details_btn.add_css_class("flat")
        details_btn.connect("clicked", self._on_device_details_clicked, device)
        actions_box.append(details_btn)

        # Connect/Disconnect Button
        status_btn = Gtk.Button()
        if connected:
            status_btn.set_label("Disconnect")
            status_btn.add_css_class("destructive-action")
        else:
            status_btn.set_label("Connect")
            status_btn.add_css_class("suggested-action")
        status_btn.connect("clicked", self._on_status_clicked, device, connected)

        actions_box.append(status_btn)

        row.add_suffix(actions_box)
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
