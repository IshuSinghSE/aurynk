import os
import threading

import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from aurynk.core.adb_manager import ADBController
from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.models.device import Device
from aurynk.services.usb_monitor import USBMonitor
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

        # Initialize USB monitor even inside Flatpak now that --device=all is granted.
        import os

        self._is_flatpak = os.path.exists("/.flatpak-info")

        self.usb_monitor = None
        try:
            monitor = USBMonitor()
            monitor.connect("device-connected", self._on_usb_device_connected)
            monitor.connect("device-disconnected", self._on_usb_device_disconnected)
            monitor.start()
            for existing in monitor.get_connected_devices():
                try:
                    GLib.idle_add(self._add_usb_device_row, existing)
                except Exception:
                    logger.debug("Failed to seed USB device row", exc_info=True)
            self.usb_monitor = monitor
            logger.info("USB monitor started for direct device access")
        except Exception:
            logger.exception("USB monitor unavailable; falling back to manual refreshes")
            self.usb_monitor = None

        # Track USB device rows: serial -> widget
        self.usb_rows = {}
        # Track device path to key mapping for reliable disconnect detection
        self.usb_device_paths = {}

        # Helper: normalize serials for consistent keys
        def _norm_serial(s):
            import re

            if not s:
                return None
            try:
                return re.sub(r"[^0-9a-z]", "", str(s).lower())
            except Exception:
                return str(s).lower()

        self._norm_serial = _norm_serial
        # If the tray helper already reported devices before the window was
        # constructed, cache that list and apply it once the UI is ready.
        self._initial_cached_devices = None
        try:
            from aurynk.services import tray_service

            try:
                with tray_service._cached_devices_lock:
                    cached = tray_service._cached_devices
            except Exception:
                cached = None

            if cached:
                # store for later application after UI setup
                try:
                    self._initial_cached_devices = list(cached)
                except Exception:
                    self._initial_cached_devices = cached
        except Exception:
            # best-effort
            self._initial_cached_devices = None

        # If we have cached usb_rows data create corresponding UI rows now
        try:
            if self.usb_rows:
                for usn, entry in list(self.usb_rows.items()):
                    try:
                        if isinstance(entry, dict) and "data" in entry and "row" not in entry:
                            dev_data = entry["data"]
                            # Create a UI row from data (do not call adb here)
                            row = self._create_device_row(dev_data, is_usb=True)
                            self.usb_group.add(row)
                            entry["row"] = row
                            self.usb_group.set_visible(True)
                    except Exception:
                        logger.debug("Failed creating UI row for cached USB device %s", usn)
        except Exception:
            pass
        # If we have cached usb_rows data create corresponding UI rows now
        try:
            if self.usb_rows:
                for usn, entry in list(self.usb_rows.items()):
                    try:
                        if isinstance(entry, dict) and "data" in entry and "row" not in entry:
                            dev_data = entry["data"]
                            # Create a UI row from data (do not call adb here)
                            row = self._create_device_row(dev_data, is_usb=True)
                            self.usb_group.add(row)
                            entry["row"] = row
                            self.usb_group.set_visible(True)
                    except Exception:
                        logger.debug("Failed creating UI row for cached USB device %s", usn)
        except Exception:
            logger.debug("Error applying cached USB devices at window init", exc_info=True)

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

        # Apply any cached devices now that UI (and `usb_group`) exists.
        try:
            GLib.idle_add(self._apply_initial_cached_devices)
        except Exception:
            pass

    def _apply_initial_cached_devices(self):
        """Create UI rows for devices received from the helper before
        the window was constructed.
        Returns False so the idle source is removed after running once.
        """
        try:
            if not self._initial_cached_devices:
                return False
            # Ensure usb_group exists
            if not hasattr(self, "usb_group") or self.usb_group is None:
                return False

            for dev in self._initial_cached_devices:
                serial = dev.get("serial") or dev.get("adb_serial") or dev.get("address")
                if not serial:
                    continue
                key = self._norm_serial(serial) or serial
                # avoid duplicates
                if key in self.usb_rows:
                    continue
                adb_props = dev.get("adb_props") or {}
                name = (
                    adb_props.get("model")
                    or dev.get("properties", {}).get("ID_MODEL")
                    or dev.get("name")
                    or serial
                )
                dev_data = {
                    "adb_serial": dev.get("adb_serial") or serial,
                    "name": name,
                    "model": adb_props.get("model"),
                    "manufacturer": adb_props.get("manufacturer"),
                }
                try:
                    row = self._create_device_row(dev_data, is_usb=True)
                    self.usb_group.add(row)
                    self.usb_rows[key] = {"row": row, "data": dev_data}
                    self.usb_group.set_visible(True)
                except Exception:
                    logger.debug("Failed creating UI row for cached USB device %s", serial)
        except Exception:
            logger.exception("Error applying cached devices")
        finally:
            # Clear cache after applying
            self._initial_cached_devices = None
            return False

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
        if hasattr(self, "usb_monitor") and self.usb_monitor:
            self.usb_monitor.stop()
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

            # Setup groups
            self._setup_device_groups()

            add_device_btn = builder.get_object("add_device_button")
            if add_device_btn:
                add_device_btn.connect("clicked", self._on_add_device_clicked)
            # No search entry, no app logo/name in template path
            self._refresh_device_list()
            self._refresh_usb_list()
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
        menu_button.set_tooltip_text(_("Main Menu"))
        menu = Gio.Menu()

        # Primary menu section
        menu.append(_("Preferences"), "win.preferences")

        # About section (separated as per GNOME HIG)
        about_section = Gio.Menu()
        about_section.append(_("About"), "win.about")
        menu.append_section(None, about_section)

        menu_button.set_menu_model(menu)
        header_bar.pack_end(menu_button)

        # Header content box
        header_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Add Device button
        add_device_btn = Gtk.Button()
        add_device_btn.set_label(_("Add Device"))
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

        scrolled.set_child(self.device_list_box)
        main_box.append(scrolled)

        self.set_content(main_box)

        # Setup groups
        self._setup_device_groups()

        # Load initial device list
        self._refresh_device_list()
        self._refresh_usb_list()

    def _setup_device_groups(self):
        # Clear main box just in case
        child = self.device_list_box.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.device_list_box.remove(child)
            child = next_child

        self.usb_group = Adw.PreferencesGroup(title=_("Connected via USB"))
        self.usb_group.set_visible(False)
        self.device_list_box.append(self.usb_group)

        self.wireless_group = Adw.PreferencesGroup(title=_("Wireless Devices"))
        self.device_list_box.append(self.wireless_group)
        self._wireless_rows = []

    def _refresh_device_list(self):
        """Refresh the device list from storage and sync tray."""
        if not hasattr(self, "wireless_group") or self.wireless_group is None:
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

        # Clear existing wireless rows
        self._wireless_rows = getattr(self, "_wireless_rows", [])
        for row in self._wireless_rows:
            self.wireless_group.remove(row)
        self._wireless_rows = []

        # Add device rows
        if devices:
            for device in devices:
                device_row = self._create_device_row(device)
                self.wireless_group.add(device_row)
                self._wireless_rows.append(device_row)
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
            empty_image.set_tooltip_text(_("Click to add a device"))

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
            # use intermediate variable to avoid f-string escaping issues in older python
            click_msg = _('Click "Add Device" to get started')
            empty_label.set_markup(f'<span alpha="50%" >{click_msg}</span>')
            empty_label.set_justify(Gtk.Justification.CENTER)
            empty_label.set_margin_bottom(64)
            empty_label.set_halign(Gtk.Align.CENTER)
            empty_box.append(empty_label)

            self.wireless_group.add(empty_box)
            self._wireless_rows.append(empty_box)

        # Always sync tray after device list changes
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _refresh_usb_list(self):
        if self.usb_monitor:
            devices = self.usb_monitor.get_connected_devices()
            for device in devices:
                self._add_usb_device_row(device)

    def _add_usb_device_row(self, device):
        serial = device.get("ID_SERIAL")
        if not serial:
            return

        # Initially assume we will key by the normalized ID_SERIAL, but if
        # we can determine an ADB serial for this device, prefer using the
        # normalized ADB serial as the canonical key so it matches helper
        # state which uses adb_serial-based keys.
        provisional_key = self._norm_serial(serial) or serial

        # If any existing entry corresponds to the same physical device
        # (match by adb_serial, short_serial, or normalized stored serial),
        # skip creating a new row to avoid duplicates from multiple udev
        # interfaces being reported for the same device.
        try:
            for k, entry in list(self.usb_rows.items()):
                try:
                    data = entry["data"] if isinstance(entry, dict) and "data" in entry else {}
                    # Match by adb serial (best)
                    adb = data.get("adb_serial")
                    if adb and adb == device.get("ID_SERIAL_SHORT"):
                        return
                    if adb and adb == device.get("ID_SERIAL"):
                        return
                    # Match by short_serial
                    short = data.get("short_serial")
                    if short and short == device.get("ID_SERIAL_SHORT"):
                        return
                    # Match by normalized stored serial
                    stored = data.get("serial")
                    if stored and (self._norm_serial(stored) or stored) == (
                        self._norm_serial(serial) or serial
                    ):
                        return
                except Exception:
                    pass
        except Exception:
            pass

        if provisional_key in self.usb_rows:
            return  # Already added

        # Fetch detailed device info via ADB
        import subprocess

        dev_data = {
            "name": device.get("ID_MODEL", "Unknown Model"),
            "manufacturer": device.get("ID_VENDOR", "Unknown Vendor"),
            "model": device.get("ID_MODEL"),
            "serial": serial,
            "short_serial": device.get("ID_SERIAL_SHORT"),
            "is_usb": True,
        }

        # Try to get actual Android device serial from adb devices
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
            adb_devices = []
            # Parse for USB device (no colon in serial)
            for line in result.stdout.strip().split("\n")[1:]:
                if "\t" in line:
                    s, st = line.split("\t", 1)
                    if ":" not in s and st.strip() == "device":
                        adb_devices.append(s)

            # Try to match using ID_SERIAL_SHORT from udev
            short_serial = dev_data.get("short_serial")
            matched_serial = None

            if short_serial and short_serial in adb_devices:
                matched_serial = short_serial
            elif len(adb_devices) == 1:
                # If only one device connected, assume it's the one
                matched_serial = adb_devices[0]
            elif adb_devices:
                # Fallback: just pick the first one if we can't match
                matched_serial = adb_devices[0]

            if matched_serial:
                dev_data["adb_serial"] = matched_serial
                # Use normalized ADB serial as canonical key when available
                try:
                    adb_key = self._norm_serial(matched_serial) or matched_serial
                except Exception:
                    adb_key = matched_serial
                key = adb_key
            else:
                # Fallback to normalized ID_SERIAL
                key = provisional_key
        except Exception as e:
            logger.debug(f"Could not fetch USB device info: {e}")

        # Create the UI row immediately with whatever data we have.
        row = self._create_device_row(dev_data, is_usb=True)
        self.usb_group.add(row)
        # Create a Device object to manage ADB-backed details and signals.
        device_obj = Device(initial=dev_data, adb_serial=dev_data.get("adb_serial"))
        # Attach device_obj to row and store in usb_rows so other code can access it
        self.usb_rows[key] = {"row": row, "data": dev_data, "device_obj": device_obj}
        row._device = device_obj
        # Store device path -> key mapping for disconnect detection
        device_path = device.device_path
        self.usb_device_paths[device_path] = key

        # Show USB group when device is added
        self.usb_group.set_visible(True)

        # When the Device object emits 'info-updated', refresh the row labels
        try:

            def _on_info_updated(devobj):
                try:
                    new_data = devobj.to_dict()
                    # update stored data and refresh labels
                    if key in self.usb_rows:
                        self.usb_rows[key]["data"] = new_data
                        try:
                            from aurynk.services.tray_service import _update_device_row_labels

                            _update_device_row_labels(row, new_data)
                        except Exception:
                            pass
                        app = self.get_application()
                        if hasattr(app, "send_status_to_tray"):
                            app.send_status_to_tray()
                except Exception:
                    pass

            device_obj.connect("info-updated", _on_info_updated)
            # Start the background fetch asynchronously (non-blocking)
            if device_obj.adb_serial:
                device_obj.fetch_details()
        except Exception:
            pass

        # Update tray status after adding USB device
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _on_usb_device_connected(self, monitor, device):
        GLib.idle_add(self._add_usb_device_row, device)

    def _on_usb_device_disconnected(self, monitor, device):
        device_path = device.device_path

        # First, try to find the key using device path (most reliable)
        if device_path in self.usb_device_paths:
            key = self.usb_device_paths[device_path]
            logger.debug(f"Found device to remove by path: {device_path} -> {key}")
            GLib.idle_add(self._remove_usb_device_row, key, device_path)
            return

        # Fallback: try to match by serial if metadata is present
        serial = device.get("ID_SERIAL")
        if not serial or serial == "unknown":
            logger.warning(f"Device disconnected but no path mapping found: {device_path}")
            return

        norm = self._norm_serial(serial) or serial

        # If a direct key exists, remove it. Otherwise, search for matching
        # entries by comparing normalized ID_SERIAL, short_serial, or adb_serial
        keys_to_remove = []
        if norm in self.usb_rows:
            keys_to_remove.append(norm)
        else:
            for k, entry in list(self.usb_rows.items()):
                try:
                    data = entry["data"] if isinstance(entry, dict) and "data" in entry else {}
                    # Compare normalized stored serials
                    stored_serial = data.get("serial")
                    if (
                        stored_serial
                        and (self._norm_serial(stored_serial) or stored_serial) == norm
                    ):
                        keys_to_remove.append(k)
                        continue
                    short = data.get("short_serial")
                    if short and (self._norm_serial(short) or short) == norm:
                        keys_to_remove.append(k)
                        continue
                    adb = data.get("adb_serial")
                    if adb and (self._norm_serial(adb) or adb) == norm:
                        keys_to_remove.append(k)
                        continue
                except Exception:
                    pass

        for key in keys_to_remove:
            GLib.idle_add(self._remove_usb_device_row, key, None)

    def _remove_usb_device_row(self, serial, device_path=None):
        # `serial` here is already a normalized key
        key = serial
        if key in self.usb_rows:
            row_data = self.usb_rows[key]
            row = row_data["row"] if isinstance(row_data, dict) else row_data
            try:
                self.usb_group.remove(row)
            except Exception:
                pass
            del self.usb_rows[key]

        # Clean up device path mapping
        if device_path and device_path in self.usb_device_paths:
            del self.usb_device_paths[device_path]
        else:
            # Find and remove by key
            for path, k in list(self.usb_device_paths.items()):
                if k == key:
                    del self.usb_device_paths[path]
                    break

        # Hide USB group when no USB devices
        if not self.usb_rows:
            self.usb_group.set_visible(False)

        # Update tray status after removing USB device
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            app.send_status_to_tray()

    def _background_fetch_and_update(self, key, adb_serial):
        """Background thread: fetch ADB-backed device info and update UI."""
        try:
            # Ensure we have a dev_data object to populate
            entry = self.usb_rows.get(key)
            if not entry:
                return
            dev_data = entry.get("data", {})

            # Reuse existing helper to fetch properties (this blocks but runs off-main-thread)
            try:
                self._fetch_usb_device_info(dev_data, adb_serial)
            except Exception:
                pass

            # Update stored data and refresh labels on the main thread
            GLib.idle_add(self._apply_updated_usb_info, key, dev_data)
        except Exception:
            pass

    def _apply_updated_usb_info(self, key, dev_data):
        """Apply updated dev_data to the row and refresh labels.

        Called on the GTK main thread via GLib.idle_add.
        """
        try:
            entry = self.usb_rows.get(key)
            if not entry:
                return False
            row = entry.get("row") if isinstance(entry, dict) else entry
            # Update stored data
            try:
                self.usb_rows[key]["data"] = dev_data
            except Exception:
                pass

            # Update the row labels using the shared helper from tray_service
            try:
                from aurynk.services.tray_service import _update_device_row_labels

                _update_device_row_labels(row, dev_data)
            except Exception:
                # Best-effort: no-op on failure
                pass

            # Update tray status if available
            app = self.get_application()
            if hasattr(app, "send_status_to_tray"):
                app.send_status_to_tray()

        except Exception:
            pass
        finally:
            # return False to remove idle source if needed
            return False

    def _fetch_usb_device_info(self, dev_data, adb_serial):
        """Fetch detailed USB device information via ADB."""
        import subprocess

        try:
            timeout = 5

            # Get device properties
            props_to_fetch = [
                ("ro.product.model", "model"),
                ("ro.product.manufacturer", "manufacturer"),
                ("ro.build.version.release", "android_version"),
            ]

            for prop, key in props_to_fetch:
                try:
                    result = subprocess.run(
                        ["adb", "-s", adb_serial, "shell", "getprop", prop],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )
                    value = result.stdout.strip()
                    if value:
                        dev_data[key] = value
                        logger.info(f"Fetched USB {key} = '{value}' for device {adb_serial}")
                except Exception as e:
                    logger.debug(f"Error fetching {prop}: {e}")

            # Update name to use the actual model if available (prefer real model over udev ID_MODEL)
            if dev_data.get("model") and dev_data.get("model") != dev_data.get("ID_MODEL"):
                dev_data["name"] = dev_data["model"]
                logger.info(f"Updated USB device name to '{dev_data['name']}'")

        except Exception as e:
            logger.debug(f"Error fetching USB device properties: {e}")

        # logger.info(
        #     f"Final USB dev_data for {adb_serial}: name='{dev_data.get('name')}', manufacturer='{dev_data.get('manufacturer')}', model='{dev_data.get('model')}', android_version='{dev_data.get('android_version')}'"
        # )

    def _create_device_row(self, device, is_usb=False):
        """Create a row widget for a device."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_margin_start(24)
        row.set_margin_end(24)

        # Store device data on the row for easier updates
        row._device_data = device

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
        dev_name = device.get("name", _("Unknown Device"))
        name_label.set_markup(f'<span size="large" weight="bold">{dev_name}</span>')
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        # Device details (show for both USB and wireless)
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

        # Connect/Status button (same for both USB and wireless)
        status_btn = Gtk.Button()
        status_btn.set_valign(Gtk.Align.CENTER)

        if is_usb:
            # USB devices are always "connected"
            status_btn.set_label(_("Connected"))
            status_btn.set_sensitive(False)  # Disabled for USB
            status_btn.add_css_class("suggested-action")
        else:
            # Wireless devices can connect/disconnect
            address = device.get("address")
            connect_port = device.get("connect_port")
            connected = False
            if address and connect_port:
                connected = is_device_connected(address, connect_port)
            if connected:
                status_btn.set_label(_("Disconnect"))
                status_btn.add_css_class("destructive-action")
            else:
                status_btn.set_label(_("Connect"))
                status_btn.add_css_class("suggested-action")
            status_btn.connect("clicked", self._on_status_clicked, device, connected)

        status_box.append(status_btn)

        # Mirror button (same for both USB and wireless)
        mirror_btn = Gtk.Button()
        mirror_btn.set_valign(Gtk.Align.CENTER)
        mirror_btn.add_css_class("mirror-button")

        if is_usb:
            # USB devices are always ready to mirror
            mirror_btn.set_sensitive(True)
            # Check if already mirroring and set appropriate style
            adb_serial = device.get("adb_serial")
            if adb_serial:
                scrcpy = self._get_scrcpy_manager()
                if scrcpy.is_mirroring_serial(adb_serial):
                    mirror_btn.set_label(_("Mirroring"))
                    mirror_btn.add_css_class("destructive-action")
                else:
                    mirror_btn.set_label(_("Mirror"))
                    mirror_btn.add_css_class("suggested-action")
            else:
                mirror_btn.set_label(_("Mirror"))
                mirror_btn.add_css_class("suggested-action")
            mirror_btn.connect("clicked", self._on_usb_mirror_clicked, device)
        else:
            # Wireless devices need to be connected first
            address = device.get("address")
            connect_port = device.get("connect_port")
            connected = False
            if address and connect_port:
                connected = is_device_connected(address, connect_port)
            mirror_btn.set_sensitive(connected)
            if connected:
                # Check if already mirroring and set appropriate style
                scrcpy = self._get_scrcpy_manager()
                if scrcpy.is_mirroring(address, connect_port):
                    mirror_btn.set_label(_("Mirroring"))
                    mirror_btn.add_css_class("destructive-action")
                else:
                    mirror_btn.set_label(_("Mirror"))
                    mirror_btn.add_css_class("suggested-action")
            else:
                mirror_btn.set_label(_("Mirror"))
                mirror_btn.add_css_class("suggested-action")
            mirror_btn.connect("clicked", self._on_mirror_clicked, device)

        status_box.append(mirror_btn)

        # Details button (same for both USB and wireless)
        details_btn = Gtk.Button()
        details_btn.set_icon_name("preferences-system-details-symbolic")
        details_btn.set_tooltip_text(_("Details"))
        details_btn.set_valign(Gtk.Align.CENTER)

        # Use a small closure so the button resolves the most up-to-date
        # device object or data at click time. This avoids stale dicts
        # being passed when tray_service creates a Device object later.
        def _details_clicked(btn):
            try:
                # Prefer a Device object attached to the row
                target = getattr(row, "_device", None)
                if target and hasattr(target, "to_dict"):
                    self._on_device_details_clicked(btn, target)
                else:
                    # Fallback to the latest device data dict attached to the row
                    self._on_device_details_clicked(btn, getattr(row, "_device_data", {}))
            except Exception:
                try:
                    self._on_device_details_clicked(btn, getattr(row, "_device_data", {}))
                except Exception:
                    pass

        details_btn.connect("clicked", lambda btn, *a: _details_clicked(btn))
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
                    dialog.set_heading(_("Remove Device?"))
                    body_text = _("Are you sure you want to remove\n{device} ?").format(
                        device=address
                    )
                    dialog.set_body(body_text)
                    dialog.set_default_size(340, 120)
                    body_label = (
                        dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
                    )
                    if body_label:
                        body_label.set_line_wrap(True)
                        body_label.set_max_width_chars(40)
                    dialog.add_response("cancel", _("Cancel"))
                    dialog.add_response("remove", _("Remove"))
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
                connection_success = False
                if (
                    "connected" in output or "already connected" in output
                ) and "unable" not in output:
                    connection_success = True
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
                            connection_success = True
                        else:
                            logger.error(
                                "Connection still failed. Please ensure device is on the network."
                            )
                    else:
                        logger.error(
                            f"Could not find device at {address}. Make sure wireless debugging is enabled."
                        )

                # Show error dialog if connection failed
                if not connection_success:
                    error_msg = self._parse_connection_error(output)
                    GLib.idle_add(
                        self._show_connection_error_dialog, device.get("name", address), error_msg
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
            # connecting is a status message, we can wrap it, but it has dynamic dots.
            # "Connecting" should be translated.
            base_label = _("Connecting")
            dots = "." * (self._animation_counter % 4)
            button.set_label(f"{base_label}{dots}")
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

        # If caller passed a Device object, prefer its live data. If a dict
        # was passed (common when tray_service created the row), attempt to
        # locate an associated Device object from `self.usb_rows` so we can
        # show the most up-to-date information.
        try:
            # If it's a Device-like object with `to_dict`, use that
            if hasattr(device, "to_dict"):
                data = device.to_dict()
                # mark as usb if it has an adb serial (or caller likely intended this)
                if data.get("adb_serial"):
                    data["is_usb"] = True
            else:
                # Try to find a Device object for this serial in usb_rows
                serial = (
                    device.get("adb_serial") or device.get("serial") or device.get("short_serial")
                )
                data = device
                if serial:
                    try:
                        key = self._norm_serial(serial) or serial
                    except Exception:
                        key = serial
                    entry = self.usb_rows.get(key) if hasattr(self, "usb_rows") else None
                    if entry and isinstance(entry, dict) and entry.get("device_obj"):
                        try:
                            data = entry.get("device_obj").to_dict()
                            data["is_usb"] = True
                        except Exception:
                            data = device
            details_window = DeviceDetailsWindow(data, self)
            details_window.present()
        except Exception:
            # Fallback to original behavior
            try:
                details_window = DeviceDetailsWindow(device, self)
                details_window.present()
            except Exception:
                pass

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
        # Use _update_all_mirror_buttons to ensure both wireless (via refresh)
        # and USB buttons (via iteration) are updated
        self._update_all_mirror_buttons()
        # No tray sync needed here - the stop handler already did it with proper timing

    def _update_all_mirror_buttons(self):
        """Update only mirror button states without rebuilding UI.
        This is called when tray triggers mirroring to sync main window."""
        scrcpy = self._get_scrcpy_manager()
        from aurynk.utils.adb_utils import is_device_connected

        # Update wireless device rows
        if hasattr(self, "_wireless_rows"):
            for row in self._wireless_rows:
                if not hasattr(row, "_device_data"):
                    continue

                device = row._device_data
                address = device.get("address")
                connect_port = device.get("connect_port")

                # Find mirror button
                child = row.get_first_child()
                while child:
                    if isinstance(child, Gtk.Box):
                        btn_child = child.get_first_child()
                        mirror_btn = None
                        while btn_child:
                            if isinstance(btn_child, Gtk.Button) and btn_child.has_css_class(
                                "mirror-button"
                            ):
                                mirror_btn = btn_child
                                break
                            btn_child = btn_child.get_next_sibling()

                        if mirror_btn:
                            connected = False
                            if address and connect_port:
                                connected = is_device_connected(address, connect_port)

                            mirror_btn.set_sensitive(connected)
                            if connected:
                                if scrcpy.is_mirroring(address, connect_port):
                                    mirror_btn.set_label(_("Mirroring"))
                                    mirror_btn.remove_css_class("suggested-action")
                                    mirror_btn.add_css_class("destructive-action")
                                else:
                                    mirror_btn.set_label(_("Mirror"))
                                    mirror_btn.remove_css_class("destructive-action")
                                    mirror_btn.add_css_class("suggested-action")
                            else:
                                mirror_btn.set_label(_("Mirror"))
                                mirror_btn.remove_css_class("destructive-action")
                                mirror_btn.add_css_class("suggested-action")
                            break
                    child = child.get_next_sibling()

        # Also update USB device mirror buttons
        for serial, row_data in self.usb_rows.items():
            if isinstance(row_data, dict) and "row" in row_data:
                row = row_data["row"]
                # Find the mirror button in this row
                # Row structure: icon -> info_box -> status_box (contains buttons)
                child = row.get_first_child()
                while child:
                    if isinstance(child, Gtk.Box):
                        # Check if this is the status_box by looking for buttons
                        btn_child = child.get_first_child()
                        mirror_btn = None
                        while btn_child:
                            if isinstance(btn_child, Gtk.Button):
                                # Check if this is the mirror button
                                if btn_child.has_css_class("mirror-button"):
                                    mirror_btn = btn_child
                                    break
                            btn_child = btn_child.get_next_sibling()

                        if mirror_btn:
                            # Update button state based on mirroring status
                            adb_serial = row_data["data"].get("adb_serial", serial)
                            # Honor transient override set when tray started mirroring via helper
                            is_mirroring = False
                            try:
                                if row_data["data"].get("_mirroring_override"):
                                    is_mirroring = True
                                else:
                                    is_mirroring = scrcpy.is_mirroring_serial(adb_serial)
                            except Exception:
                                is_mirroring = scrcpy.is_mirroring_serial(adb_serial)
                            if is_mirroring:
                                mirror_btn.set_label(_("Mirroring"))
                                mirror_btn.remove_css_class("suggested-action")
                                mirror_btn.add_css_class("destructive-action")
                            else:
                                mirror_btn.set_label(_("Mirror"))
                                mirror_btn.remove_css_class("destructive-action")
                                mirror_btn.add_css_class("suggested-action")
                            break
                    child = child.get_next_sibling()

    def _on_mirror_clicked(self, button, device):
        address = device.get("address")
        connect_port = device.get("connect_port")
        device_name = device.get("name")
        if not address or not connect_port:
            return
        scrcpy = self._get_scrcpy_manager()

        # Check if currently mirroring
        is_currently_mirroring = scrcpy.is_mirroring(address, connect_port)

        # Toggle mirroring
        if is_currently_mirroring:
            scrcpy.stop_mirror(address, connect_port)
        else:
            scrcpy.start_mirror(address, connect_port, device_name)

        # Update UI immediately using _update_all_mirror_buttons
        self._update_all_mirror_buttons()

        # Sync tray - with small delay only when stopping to let process cleanup complete
        app = self.get_application()
        if hasattr(app, "send_status_to_tray"):
            if is_currently_mirroring:
                # Stopping - wait for process to fully terminate
                GLib.timeout_add(100, lambda: app.send_status_to_tray())
            else:
                # Starting - sync immediately
                app.send_status_to_tray()

    def _on_usb_mirror_clicked(self, button, device):
        """Handle mirror click for USB devices."""
        # Try to use the stored ADB serial first
        usb_serial = device.get("adb_serial")

        # If not found, try to find it via adb devices (fallback)
        if not usb_serial:
            import subprocess

            try:
                result = subprocess.run(
                    ["adb", "devices"], capture_output=True, text=True, timeout=5
                )
                adb_devices = []
                for line in result.stdout.strip().split("\n")[1:]:
                    if "\t" in line:
                        s, st = line.split("\t", 1)
                        if ":" not in s and st.strip() == "device":
                            adb_devices.append(s)

                short_serial = device.get("short_serial")
                if short_serial and short_serial in adb_devices:
                    usb_serial = short_serial
                elif len(adb_devices) == 1:
                    usb_serial = adb_devices[0]
                elif adb_devices:
                    usb_serial = adb_devices[0]

                if usb_serial:
                    # Store it for future use to ensure consistency
                    device["adb_serial"] = usb_serial
            except Exception as e:
                logger.error(f"Error finding USB serial: {e}")

        if not usb_serial:
            logger.warning("No USB device serial found")
            return

        try:
            device_name = device.get("name", "USB Device")
            scrcpy = self._get_scrcpy_manager()

            # Check if already mirroring using the USB serial
            is_mirroring = scrcpy.is_mirroring_serial(usb_serial)
            logger.info(
                f"USB Mirror button clicked. Serial: {usb_serial}, Is mirroring: {is_mirroring}"
            )

            if is_mirroring:
                logger.info(f"Stopping mirror for USB device {usb_serial}")
                scrcpy.stop_mirror_by_serial(usb_serial)
            else:
                logger.info(f"Starting mirror for USB device {usb_serial}")

                # Check if USB device is authorized before attempting to mirror
                is_authorized, state = self._check_usb_authorization(usb_serial)

                if not is_authorized:
                    if state == "unauthorized":
                        # Show USB authorization dialog
                        self._show_usb_unauthorized_dialog(device_name)
                        return
                    else:
                        logger.warning(f"USB device {usb_serial} in unexpected state: {state}")

                started = scrcpy.start_mirror_usb(usb_serial, device_name)
                if not started:
                    # Show a user-facing dialog explaining common causes and remediation
                    try:
                        self._show_scrcpy_unavailable_dialog(usb_serial)
                    except Exception:
                        logger.exception("Failed to show scrcpy unavailable dialog")

            # Update UI immediately using _update_all_mirror_buttons
            self._update_all_mirror_buttons()

            # Sync tray - with small delay only when stopping to let process cleanup complete
            app = self.get_application()
            if hasattr(app, "send_status_to_tray"):
                if is_mirroring:
                    # Stopping - wait for process to fully terminate
                    GLib.timeout_add(100, lambda: app.send_status_to_tray())
                else:
                    # Starting - sync immediately
                    app.send_status_to_tray()
        # end of try block for USB mirror click
        except subprocess.TimeoutExpired:
            logger.error("adb devices command timed out")
        except Exception as e:
            logger.error(f"Error starting USB mirror: {e}")

    def _parse_connection_error(self, output: str) -> str:
        """Parse ADB connection error output and return user-friendly message."""
        output_lower = output.lower()

        if "refused" in output_lower or "cannot connect" in output_lower:
            return _("Connection refused. Make sure Wireless Debugging is enabled on your device.")
        elif "timed out" in output_lower or "timeout" in output_lower:
            return _(
                "Connection timed out. Check if your device is on the same network and Wireless Debugging is enabled."
            )
        elif "no route" in output_lower or "unreachable" in output_lower:
            return _("Cannot reach device. Verify the device is on the same Wi-Fi network.")
        elif "unable" in output_lower:
            return _(
                "Unable to connect. The device may have changed ports. Try removing and re-pairing the device."
            )
        else:
            return _(
                "Connection failed. Ensure Wireless Debugging is enabled and the device is on the same network."
            )

    def _show_connection_error_dialog(self, device_name: str, error_message: str):
        """Show error dialog when wireless connection fails."""
        try:
            from gi.repository import Adw

            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading(_("Connection Failed"))
            body = _(
                "Failed to connect to {device}.\n\n{error}\n\nTroubleshooting:\n"
                "  • Ensure Wireless Debugging is enabled\n"
                "  • Check both devices are on the same Wi-Fi\n"
                "  • Try removing and re-pairing the device"
            ).format(device=device_name, error=error_message)

            dialog.set_body(body)
            dialog.set_default_size(400, 200)
            body_label = dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
            if body_label:
                body_label.set_line_wrap(True)
                body_label.set_max_width_chars(50)

            dialog.add_response("ok", _("OK"))
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()
        except Exception as e:
            logger.error(f"Failed to show connection error dialog: {e}")

    def _check_usb_authorization(self, usb_serial: str) -> tuple[bool, str]:
        """Check if USB device is authorized. Returns (is_authorized, state)."""
        import subprocess

        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
            for line in result.stdout.strip().split("\n")[1:]:
                if "\t" in line:
                    serial, state = line.split("\t", 1)
                    state = state.strip()
                    if serial == usb_serial:
                        return (state == "device", state)
            return (False, "not_found")
        except Exception:
            return (False, "error")

    def _show_usb_unauthorized_dialog(self, device_name: str):
        """Show dialog when USB device is not authorized."""
        try:
            from gi.repository import Adw

            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading(_("USB Debugging Not Authorized"))
            body = _(
                "Device {device} is connected via USB but not authorized.\n\n"
                "Please check your device and tap 'Allow' to authorize USB debugging.\n\n"
                "Note: You may need to enable 'Always allow from this computer' for persistent authorization."
            ).format(device=device_name)

            dialog.set_body(body)
            dialog.set_default_size(400, 180)
            body_label = dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
            if body_label:
                body_label.set_line_wrap(True)
                body_label.set_max_width_chars(50)

            dialog.add_response("ok", _("OK"))
            dialog.connect("response", lambda d, r: d.destroy())
            dialog.present()
        except Exception as e:
            logger.error(f"Failed to show USB unauthorized dialog: {e}")

    def _show_scrcpy_unavailable_dialog(self, serial: str):
        """Show a concise dialog describing why scrcpy may not have started.

        This provides common remediation steps (non-snap scrcpy, connect snap raw-usb,
        or configure `scrcpy_path` in settings).
        """
        try:
            from gi.repository import Adw

            dialog = Adw.MessageDialog.new(self)
            dialog.set_heading(_("Unable to start screen mirroring"))
            body = _(
                "Aurynk was unable to start scrcpy for device: {serial}.\n\n"
                "Common causes: scrcpy cannot see the ADB device (ADB does not list it), or "
                "you are using a snap-packaged scrcpy which lacks raw USB access.\n\n"
                "Remedies:\n"
                "  • Install a non-snap scrcpy from your distribution or build it locally.\n"
                "  • If you installed scrcpy via snap, connect the raw-usb interface:\n"
                "    sudo snap connect scrcpy:raw-usb :raw-usb\n"
                "  • Or set a full path to a non-snap `scrcpy` binary in Aurynk settings."
            ).format(serial=serial)

            dialog.set_body(body)
            dialog.set_default_size(420, 180)
            body_label = dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
            if body_label:
                body_label.set_line_wrap(True)
                body_label.set_max_width_chars(60)

            dialog.add_response("ok", _("OK"))

            def _on_resp(dlg, resp):
                dlg.destroy()

            dialog.connect("response", _on_resp)
            dialog.present()
        except Exception:
            # If Adw isn't available or dialog creation fails, fall back to logging only
            logger.warning("scrcpy unavailable for %s and UI dialog could not be shown", serial)

    def show_unpair_confirmation_dialog(address):
        """Show a confirmation dialog before unpairing a device. Returns True if confirmed, False otherwise."""
        # This is a blocking dialog for simplicity; can be made async if needed
        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Unpair Device?"),
        )
        dialog.format_secondary_text(
            _("Are you sure you want to unpair device {}?").format(address)
        )
        response = dialog.run()
        dialog.destroy()
        return response == Gtk.ResponseType.YES
