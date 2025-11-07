#!/usr/bin/env python3
"""Device details window."""

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import threading

from gi.repository import Adw, Gtk

from aurynk.lib.adb_controller import ADBController


class DeviceDetailsWindow(Adw.Window):
    """Window showing detailed device information."""

    def __init__(self, device, parent):
        super().__init__(transient_for=parent)

        self.device = device
        self.adb_controller = ADBController()

        self.set_title(f"Device: {device.get('name', 'Unknown')}")
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
        screenshot_label.set_markup('<span size="x-large" weight="bold">Preview</span>')
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

        # Refresh screenshot button (icon only)
        refresh_screenshot_btn = Gtk.Button()
        refresh_screenshot_btn.set_icon_name("view-refresh-symbolic")
        refresh_screenshot_btn.set_tooltip_text("Refresh Screenshot")
        refresh_screenshot_btn.add_css_class("suggested-action")
        refresh_screenshot_btn.connect("clicked", self._on_refresh_screenshot)
        actions_box.append(refresh_screenshot_btn)

        # Refresh all data button (icon only)
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("system-reboot-symbolic")
        refresh_btn.set_tooltip_text("Refresh All Device Data")
        refresh_btn.connect("clicked", self._on_refresh_all)
        actions_box.append(refresh_btn)

        # Remove device button (icon only)
        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("user-trash-symbolic")
        remove_btn.set_tooltip_text("Remove Device")
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
        basic_group.set_title("Basic Information")

        self._add_info_row(basic_group, "Device Name", self.device.get("name", "Unknown"))
        self._add_info_row(basic_group, "Manufacturer", self.device.get("manufacturer", "Unknown"))
        self._add_info_row(
            basic_group, "Android Version", self.device.get("android_version", "Unknown")
        )
        self._add_info_row(basic_group, "IP Address", self.device.get("address", "Unknown"))

        right_box.append(basic_group)

        # Specifications section
        specs_group = Adw.PreferencesGroup()
        specs_group.set_title("Specifications")

        spec = self.device.get("spec", {})
        self.ram_row = self._add_info_row(specs_group, "RAM", spec.get("ram", "Loading..."))
        self.storage_row = self._add_info_row(
            specs_group, "Storage", spec.get("storage", "Loading...")
        )
        self.battery_row = self._add_info_row(
            specs_group, "Battery", spec.get("battery", "Loading...")
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

    def _fetch_device_data(self):
        """Fetch device specifications in background."""

        def fetch():
            specs = self.adb_controller.fetch_device_specs(
                self.device["address"], self.device["connect_port"]
            )

            # Update device info
            self.device["spec"] = specs
            self.adb_controller.save_paired_device(self.device)

            # Update UI on main thread
            from gi.repository import GLib

            GLib.idle_add(self._update_specs_ui, specs)

        threading.Thread(target=fetch, daemon=True).start()

    def _update_specs_ui(self, specs):
        """Update specifications UI."""
        self.ram_row.set_subtitle(specs.get("ram", "Unknown"))
        self.storage_row.set_subtitle(specs.get("storage", "Unknown"))
        self.battery_row.set_subtitle(specs.get("battery", "Unknown"))

    def _on_refresh_screenshot(self, button):
        """Handle refresh screenshot button click."""
        button.set_sensitive(False)
        button.set_label("Refreshing...")

        def capture():
            screenshot_path = self.adb_controller.capture_screenshot(
                self.device["address"], self.device["connect_port"]
            )

            if screenshot_path:
                self.device["thumbnail"] = screenshot_path
                self.adb_controller.save_paired_device(self.device)

            # Update UI on main thread
            from gi.repository import GLib

            GLib.idle_add(self._update_screenshot_ui, screenshot_path, button)

        threading.Thread(target=capture, daemon=True).start()

    def _update_screenshot_ui(self, screenshot_path, button):
        """Update screenshot UI."""
        if screenshot_path:
            self.screenshot_image.set_from_file(screenshot_path)
        button.set_sensitive(True)
        button.set_icon_name("view-refresh-symbolic")

    def _on_refresh_all(self, button):
        """Handle refresh all data button click."""
        button.set_sensitive(False)

        def refresh():
            # Fetch specs
            specs = self.adb_controller.fetch_device_specs(
                self.device["address"], self.device["connect_port"]
            )
            self.device["spec"] = specs

            # Capture screenshot
            screenshot_path = self.adb_controller.capture_screenshot(
                self.device["address"], self.device["connect_port"]
            )
            if screenshot_path:
                self.device["thumbnail"] = screenshot_path

            # Save
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
        button.set_sensitive(True)

    def _on_remove_device(self, button):
        """Handle remove device button click."""
        # Show confirmation dialog with improved layout
        dialog = Adw.MessageDialog.new(self)
        dialog.set_heading("Remove Device?")
        # Use line break and wrapping for the body label
        body_text = f"Are you sure you want to remove \n {self.device.get('name', 'this device')} ?"
        dialog.set_body(body_text)
        # Set minimum width for dialog
        dialog.set_default_size(340, 120)
        # Enable label wrapping (Adw.MessageDialog uses a GtkLabel internally)
        body_label = dialog.get_body_label() if hasattr(dialog, "get_body_label") else None
        if body_label:
            body_label.set_line_wrap(True)
            body_label.set_max_width_chars(40)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_remove_confirmed)
        dialog.present()

    def _on_remove_confirmed(self, dialog, response):
        """Handle remove confirmation."""
        if response == "remove":
            self.adb_controller.remove_device(self.device["address"])
            self.close()
