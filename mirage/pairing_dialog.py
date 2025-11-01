#!/usr/bin/env python3
"""Pairing dialog for adding new devices."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib
import threading

from mirage.adb_controller import ADBController
from mirage.qr_widget import create_qr_widget


class PairingDialog(Gtk.Dialog):
    """Dialog for pairing new Android devices."""

    def __init__(self, parent):
        super().__init__(title="Pair New Device", transient_for=parent, modal=True)
        
        self.adb_controller = ADBController()
        self.zeroconf = None
        self.browser = None
        self.qr_timeout_id = None
        
        self.set_default_size(420, 500)
        
        # Setup UI
        self._setup_ui()
        
        # Start pairing process
        self._start_pairing()

    def _setup_ui(self):
        """Setup the dialog UI."""
        content = self.get_content_area()
        content.set_spacing(16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)

        # Title
        title = Gtk.Label()
        title.set_markup('<span size="x-large" weight="bold">How to Pair New Device</span>')
        title.set_halign(Gtk.Align.START)
        content.append(title)

        # Instructions
        instructions = Gtk.Label(
            label="1. On your phone, go to: Developer Options > Wireless Debugging\n"
                  "2. Tap 'Pair device with QR code' and scan"
        )
        instructions.set_justify(Gtk.Justification.LEFT)
        instructions.set_halign(Gtk.Align.START)
        content.append(instructions)

        # QR code container
        self.qr_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.qr_container.set_halign(Gtk.Align.CENTER)
        self.qr_container.set_valign(Gtk.Align.CENTER)
        content.append(self.qr_container)

        # Spinner
        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.start()

        # Status label
        self.status_label = Gtk.Label(label="Generating QR code...")
        self.status_label.set_halign(Gtk.Align.CENTER)

        # Try again button (hidden initially)
        self.try_again_btn = Gtk.Button(label="Try Again")
        self.try_again_btn.set_halign(Gtk.Align.CENTER)
        self.try_again_btn.set_visible(False)
        self.try_again_btn.connect("clicked", self._on_try_again)
        content.append(self.try_again_btn)

        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(12)

        # Cancel button
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", self._on_cancel)
        button_box.append(cancel_btn)

        content.append(button_box)

    def _start_pairing(self):
        """Start the pairing process."""
        # Generate credentials
        self.network_name = f"ADB_WIFI_{self.adb_controller.generate_code(5)}"
        self.password = self.adb_controller.generate_code(5)
        qr_data = f"WIFI:T:ADB;S:{self.network_name};P:{self.password};;"

        # Clear QR container
        while True:
            child = self.qr_container.get_first_child()
            if not child:
                break
            self.qr_container.remove(child)

        # Add QR code
        qr_widget = create_qr_widget(qr_data, size=200)
        self.qr_container.append(qr_widget)
        self.qr_container.append(self.spinner)
        self.qr_container.append(self.status_label)

        self.status_label.set_text("Scan the QR code with your phone")
        self.spinner.start()

        # Start mDNS discovery in background thread
        threading.Thread(target=self._discover_devices, daemon=True).start()

        # Set timeout for QR code expiry
        if self.qr_timeout_id:
            GLib.source_remove(self.qr_timeout_id)
        self.qr_timeout_id = GLib.timeout_add_seconds(30, self._on_qr_expired)

    def _discover_devices(self):
        """Start mDNS discovery for devices."""
        def on_device_found(address, pair_port, connect_port, password):
            # Update UI on main thread
            GLib.idle_add(self._on_device_found, address, pair_port, connect_port, password)

        try:
            self.zeroconf, self.browser = self.adb_controller.start_mdns_discovery(
                on_device_found, self.network_name, self.password
            )
        except Exception as e:
            GLib.idle_add(self._update_status, f"Error: {e}")

    def _on_device_found(self, address, pair_port, connect_port, password):
        """Handle device discovery."""
        self._update_status(f"Device found: {address}")
        
        # Start pairing in background thread
        def pair():
            success = self.adb_controller.pair_device(
                address, pair_port, connect_port, self.password,
                status_callback=lambda msg: GLib.idle_add(self._update_status, msg)
            )
            if success:
                GLib.idle_add(self._on_pairing_complete)

        threading.Thread(target=pair, daemon=True).start()

    def _on_pairing_complete(self):
        """Handle successful pairing."""
        self.spinner.stop()
        self._update_status("✓ Device paired successfully!")
        
        # Close dialog after a short delay
        GLib.timeout_add_seconds(2, self._on_cancel, None)

    def _update_status(self, message):
        """Update status label."""
        self.status_label.set_text(message)

    def _on_qr_expired(self):
        """Handle QR code expiry."""
        self.spinner.stop()
        self.status_label.set_text("QR code expired. Click 'Try Again' to generate a new one.")
        self.try_again_btn.set_visible(True)
        
        # Cleanup
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except:
                pass
        
        return False  # Don't repeat timeout

    def _on_try_again(self, button):
        """Handle Try Again button click."""
        self.try_again_btn.set_visible(False)
        self._start_pairing()

    def _on_cancel(self, button):
        """Handle Cancel button click."""
        # Cleanup
        if self.qr_timeout_id:
            GLib.source_remove(self.qr_timeout_id)
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except:
                pass
        
        self.close()
