import os

import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import threading

from gi.repository import Adw, Gtk

from aurynk.core.adb_manager import ADBController


class DeviceDetailsWindow(Adw.Window):
    """Window showing detailed device information."""

    def __init__(self, device, parent):
        super().__init__(transient_for=parent)

        self.device = device
        self.adb_controller = ADBController()

        self.set_title(_("Device: {name}").format(name=device.get("name", _("Unknown"))))
        self.set_default_size(900, 600)

        self._setup_ui()

        # Load device specs if not already loaded
        if not device.get("spec"):
            self._fetch_device_data()

    def _setup_ui(self):
        """Setup the window UI."""
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Scrolled window
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)

        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=32)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Left column: Screenshot
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        left_box.set_valign(Gtk.Align.START)

        screenshot_label = Gtk.Label()
        screenshot_label.set_markup(f'<span size="x-large" weight="bold">{_("Preview")}</span>')
        screenshot_label.set_halign(Gtk.Align.CENTER)
        left_box.append(screenshot_label)

        self.screenshot_image = Gtk.Image()
        self.screenshot_image.set_pixel_size(360)

        # Load thumbnail if available
        thumbnail = self.device.get("thumbnail")
        if thumbnail and not os.path.isabs(thumbnail):
            thumbnail = os.path.expanduser(
                os.path.join("~/.local/share/aurynk/screenshots", thumbnail)
            )
        if not thumbnail or not os.path.exists(thumbnail):
            # Use Flatpak-compliant GResource path for fallback icon
            self.screenshot_image.set_from_resource(
                "/io/github/IshuSinghSE/aurynk/icons/io.github.IshuSinghSE.aurynk.device.png"
            )
        else:
            self.screenshot_image.set_from_file(thumbnail)

        left_box.append(self.screenshot_image)

        # Actions section
        actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        actions_box.set_halign(Gtk.Align.CENTER)
        actions_box.set_margin_top(12)

        # Refresh screenshot button (icon only) - camera icon for clarity
        self.refresh_screenshot_btn = Gtk.Button()
        self.refresh_screenshot_btn.set_icon_name("camera-photo-symbolic")
        self.refresh_screenshot_btn.set_tooltip_text(_("Capture screenshot only"))
        self.refresh_screenshot_btn.add_css_class("suggested-action")
        self.refresh_screenshot_btn.connect("clicked", self._on_refresh_screenshot)
        actions_box.append(self.refresh_screenshot_btn)

        # Refresh all data button (icon only) - refresh icon to distinguish from screenshot
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_icon_name("view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text(_("Refresh device info and screenshot"))
        self.refresh_btn.connect("clicked", self._on_refresh_all)
        actions_box.append(self.refresh_btn)

        # Check if device is connected and enable/disable buttons accordingly
        self._update_button_states()

        # Remove device button (icon only) - only show for wireless devices
        if not self.device.get("is_usb"):
            remove_btn = Gtk.Button()
            remove_btn.set_icon_name("user-trash-symbolic")
            remove_btn.set_tooltip_text(_("Remove Device"))
            remove_btn.add_css_class("destructive-action")
            remove_btn.connect("clicked", self._on_remove_device)
            actions_box.append(remove_btn)

        left_box.append(actions_box)
        content.append(left_box)

        # Right column: Device info
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        right_box.set_hexpand(True)
        right_box.set_valign(Gtk.Align.START)

        # Basic info section
        basic_group = Adw.PreferencesGroup()
        basic_group.set_title(_("Basic Information"))

        self.name_row = self._add_info_row(
            basic_group, _("Device Name"), self.device.get("name", _("Unknown"))
        )
        self.manufacturer_row = self._add_info_row(
            basic_group, _("Manufacturer"), self.device.get("manufacturer", _("Unknown"))
        )
        self.android_version_row = self._add_info_row(
            basic_group, _("Android Version"), self.device.get("android_version", _("Unknown"))
        )

        # Show different field based on device type
        if self.device.get("is_usb"):
            # For USB devices, show the ADB serial or connection type
            serial = self.device.get("adb_serial") or self.device.get("short_serial", _("Unknown"))
            self.connection_row = self._add_info_row(basic_group, _("USB Serial"), serial)
        else:
            # For wireless devices, show IP address
            self.connection_row = self._add_info_row(
                basic_group, _("IP Address"), self.device.get("address", _("Unknown"))
            )

        right_box.append(basic_group)

        # Specifications section
        specs_group = Adw.PreferencesGroup()
        specs_group.set_title(_("Specifications"))

        spec = self.device.get("spec", {})
        self.ram_row = self._add_info_row(specs_group, _("RAM"), spec.get("ram", _("Loading...")))
        self.storage_row = self._add_info_row(
            specs_group, _("Storage"), spec.get("storage", _("Loading..."))
        )
        self.battery_row = self._add_info_row(
            specs_group, _("Battery"), spec.get("battery", _("Loading..."))
        )

        right_box.append(specs_group)
        content.append(right_box)

        scrolled.set_child(content)
        main_box.append(scrolled)

        self.set_content(main_box)

    def _add_info_row(self, group, label, value):
        """Add an information row to a preferences group."""
        row = Adw.ActionRow()
        row.set_title(label)
        row.set_subtitle(str(value))
        group.add(row)
        return row

    def _update_button_states(self):
        """Enable or disable buttons based on device connection status."""
        is_connected = self._check_device_connected()

        self.refresh_screenshot_btn.set_sensitive(is_connected)
        self.refresh_btn.set_sensitive(is_connected)

        if not is_connected:
            self.refresh_screenshot_btn.set_tooltip_text(_("Device not connected"))
            self.refresh_btn.set_tooltip_text(_("Device not connected"))
        else:
            self.refresh_screenshot_btn.set_tooltip_text(_("Capture screenshot only"))
            self.refresh_btn.set_tooltip_text(_("Refresh device info and screenshot"))

    def _check_device_connected(self):
        """Check if the device is currently connected via ADB."""
        import subprocess

        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2)

            # Get the device identifier to check
            if self.device.get("is_usb"):
                device_id = self.device.get("adb_serial", "")
            else:
                device_id = f"{self.device.get('address')}:{self.device.get('connect_port')}"

            # Check if device is in the list
            for line in result.stdout.strip().split("\n")[1:]:
                if "\t" in line:
                    serial, status = line.split("\t", 1)
                    if serial.strip() == device_id and status.strip() == "device":
                        return True

            return False
        except Exception:
            return False

    def _fetch_device_data(self):
        """Fetch device specifications in background."""

        def fetch():
            # Check if this is a USB device or wireless device
            if self.device.get("is_usb"):
                # USB device - use adb_serial
                adb_serial = self.device.get("adb_serial")

                # If no adb_serial, try to find it
                if not adb_serial:
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

                        # Try to match with short_serial or use first device
                        short_serial = self.device.get("short_serial")
                        if short_serial and short_serial in adb_devices:
                            adb_serial = short_serial
                        elif len(adb_devices) == 1:
                            adb_serial = adb_devices[0]

                        if adb_serial:
                            self.device["adb_serial"] = adb_serial
                    except Exception:
                        pass

                if adb_serial:
                    # Fetch specs
                    specs = self.adb_controller.fetch_device_specs_by_serial(adb_serial)

                    # Also fetch basic device info if not already present
                    if not self.device.get("android_version") or not self.device.get(
                        "manufacturer"
                    ):
                        import subprocess

                        try:
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
                                        timeout=5,
                                    )
                                    value = result.stdout.strip()
                                    if value:
                                        self.device[key] = value
                                except Exception:
                                    pass

                            # Update name to use the actual model if available
                            if self.device.get("model") and not self.device.get("name"):
                                self.device["name"] = self.device["model"]
                        except Exception:
                            pass
                else:
                    specs = {"ram": _("Unknown"), "storage": _("Unknown"), "battery": _("Unknown")}
            else:
                # Wireless device - use address:port
                # Be defensive: ensure address/connect_port exist
                addr = self.device.get("address")
                port = self.device.get("connect_port")
                if not addr or not port:
                    specs = {"ram": _("Unknown"), "storage": _("Unknown"), "battery": _("Unknown")}
                else:
                    specs = self.adb_controller.fetch_device_specs(addr, port)

            # Update device info
            self.device["spec"] = specs
            if not self.device.get("is_usb"):
                self.adb_controller.save_paired_device(self.device)

            # Update UI on main thread
            from gi.repository import GLib

            GLib.idle_add(self._update_all_device_info, specs)

        threading.Thread(target=fetch, daemon=True).start()

    def _update_all_device_info(self, specs):
        """Update all device information in the UI."""
        # Update specs
        self._update_specs_ui(specs)

        # Update basic info if it was fetched
        if hasattr(self, "name_row"):
            self.name_row.set_subtitle(self.device.get("name", _("Unknown")))
        if hasattr(self, "manufacturer_row"):
            self.manufacturer_row.set_subtitle(self.device.get("manufacturer", _("Unknown")))
        if hasattr(self, "android_version_row"):
            self.android_version_row.set_subtitle(self.device.get("android_version", _("Unknown")))

    def _update_specs_ui(self, specs):
        """Update specifications UI."""
        # Use fallback 'Unknown' when values are empty or falsy
        self.ram_row.set_subtitle(specs.get("ram") or _("Unknown"))
        self.storage_row.set_subtitle(specs.get("storage") or _("Unknown"))
        self.battery_row.set_subtitle(specs.get("battery") or _("Unknown"))

    def _on_refresh_screenshot(self, button):
        """Handle refresh screenshot button click."""
        # Check if device is connected
        if not self._check_device_connected():
            self._update_button_states()
            return

        button.set_sensitive(False)

        def capture():
            # Check if this is a USB device or wireless device
            if self.device.get("is_usb"):
                # USB device - use adb_serial
                adb_serial = self.device.get("adb_serial")
                if adb_serial:
                    screenshot_path = self.adb_controller.capture_screenshot_by_serial(adb_serial)
                else:
                    screenshot_path = None
            else:
                # Wireless device - use address:port
                screenshot_path = self.adb_controller.capture_screenshot(
                    self.device["address"], self.device["connect_port"]
                )

            if screenshot_path:
                self.device["thumbnail"] = screenshot_path
                if not self.device.get("is_usb"):
                    self.adb_controller.save_paired_device(self.device)

            # Update UI on main thread
            from gi.repository import GLib

            GLib.idle_add(self._update_screenshot_ui, screenshot_path, button)

        threading.Thread(target=capture, daemon=True).start()

    def _update_screenshot_ui(self, screenshot_path, button):
        """Update screenshot UI."""
        if screenshot_path:
            self.screenshot_image.set_from_file(screenshot_path)
        # Re-check connection state and update button states
        self._update_button_states()

    def _on_refresh_all(self, button):
        """Handle refresh all data button click."""
        # Check if device is connected
        if not self._check_device_connected():
            self._update_button_states()
            return

        button.set_sensitive(False)

        def refresh():
            # Check if this is a USB device or wireless device
            if self.device.get("is_usb"):
                # USB device - use adb_serial
                adb_serial = self.device.get("adb_serial")
                if adb_serial:
                    specs = self.adb_controller.fetch_device_specs_by_serial(adb_serial)
                    screenshot_path = self.adb_controller.capture_screenshot_by_serial(adb_serial)
                else:
                    specs = {"ram": _("Unknown"), "storage": _("Unknown"), "battery": _("Unknown")}
                    screenshot_path = None
            else:
                # Wireless device - use address:port
                specs = self.adb_controller.fetch_device_specs(
                    self.device["address"], self.device["connect_port"]
                )
                screenshot_path = self.adb_controller.capture_screenshot(
                    self.device["address"], self.device["connect_port"]
                )

            self.device["spec"] = specs
            if screenshot_path:
                self.device["thumbnail"] = screenshot_path

            # Save (only for wireless devices)
            if not self.device.get("is_usb"):
                self.adb_controller.save_paired_device(self.device)

            # Update UI
            from gi.repository import GLib

            GLib.idle_add(self._update_all_ui, specs, screenshot_path, button)

        threading.Thread(target=refresh, daemon=True).start()

    def _update_all_ui(self, specs, screenshot_path, button):
        """Update all UI elements."""
        self._update_specs_ui(specs)
        if screenshot_path:
            self.screenshot_image.set_from_file(screenshot_path)
        # Re-check connection state and update button states
        self._update_button_states()

    def _on_remove_device(self, button):
        """Handle remove device button click."""
        # Show confirmation dialog with improved layout
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading(_("Remove Device"))
        # Use line break and wrapping for the body label
        body_text = _("Are you sure you want to remove \n {device} ?").format(
            device=self.device.get("name", _("this device"))
        )
        dialog.set_body(body_text)
        # Set minimum width for dialog
        dialog.set_default_size(340, 120)
        # Enable label wrapping (Adw.MessageDialog uses a GtkLabel internally)
        body_label = dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
        if body_label:
            body_label.set_line_wrap(True)
            body_label.set_max_width_chars(40)
        dialog.add_response("cancel", _("Cancel"))
        dialog.add_response("remove", _("Remove"))
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_remove_confirmed)
        dialog.present()

    def _on_remove_confirmed(self, dialog, response):
        """Handle remove confirmation."""
        if response == "remove":
            self.adb_controller.remove_device(self.device["address"])
            # DeviceStore now centrally notifies the tray helper after saving,
            # so no direct socket write is necessary here.
            self.close()
