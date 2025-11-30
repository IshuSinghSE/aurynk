"""Pairing dialog for adding new devices."""

import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import threading

from gi.repository import GLib, Gtk

from aurynk.core.adb_manager import ADBController
from aurynk.ui.widgets.qr_view import create_qr_widget


class PairingDialog(Gtk.Dialog):
    """Dialog for pairing new Android devices."""

    def __init__(self, parent):
        super().__init__(title=_("Pair New Device"), transient_for=parent, modal=True)

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
        """Setup the dialog UI (minimal, modern, beautiful)."""
        content = self.get_content_area()
        content.set_spacing(0)
        content.set_margin_top(32)
        content.set_margin_bottom(32)
        content.set_margin_start(32)
        content.set_margin_end(32)

        # Title (centered, bold, large)
        title = Gtk.Label()
        title.set_markup(
            f'<span size="xx-large" weight="bold">{_("How to Pair New Device")}</span>'
        )
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(8)
        content.append(title)

        # Instructions (modern, clear, above QR)
        instructions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        instructions.set_halign(Gtk.Align.CENTER)
        instructions.set_margin_bottom(18)

        instr1 = Gtk.Label()
        instr1.set_markup(
            # translators: <b> and </b> tags are used for bold text, please preserve them in the translation.
            f'<span size="medium">{_("1. On your phone, go to <b>Developer Options → Wireless Debugging</b>")}</span>'
        )
        instr1.set_halign(Gtk.Align.CENTER)
        instr1.get_style_context().add_class("dim-label")
        instr2 = Gtk.Label()
        instr2.set_markup(
            # translators: <b> and </b> tags are used for bold text, please preserve them in the translation.
            f'<span size="medium">{_("2. Tap <b>Pair device with QR code</b> and scan below")}</span>'
        )
        instr2.set_halign(Gtk.Align.CENTER)
        instr2.get_style_context().add_class("dim-label")
        instructions.append(instr1)
        instructions.append(instr2)
        content.append(instructions)

        # QR code container (centered)
        self.qr_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.qr_container.set_halign(Gtk.Align.CENTER)
        self.qr_container.set_valign(Gtk.Align.CENTER)
        self.qr_container.set_margin_top(16)
        content.append(self.qr_container)

        # Spinner (centered, below QR)
        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.start()

        # Status label (centered, subtle)
        self.status_label = Gtk.Label(label=_("Generating QR code..."))
        self.status_label.set_halign(Gtk.Align.CENTER)
        self.status_label.set_margin_top(8)
        self.status_label.get_style_context().add_class("dim-label")

        # Action button (dynamically changes between Cancel and Try Again)
        self.action_btn = Gtk.Button()
        self.action_btn.set_label(_("Cancel"))
        self.action_btn.add_css_class("destructive-action")
        self.action_btn.connect("clicked", self._on_cancel)
        self.action_btn.set_halign(Gtk.Align.CENTER)
        self.action_btn.set_margin_top(18)
        content.append(self.action_btn)

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

        self.status_label.set_text(_("Scan the QR code with your phone"))
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
            GLib.idle_add(self._update_status, _("Error: {}").format(e))

    def _on_device_found(self, address, pair_port, connect_port, password):
        """Handle device discovery."""
        self._update_status(_("Device found: {}").format(address))

        # Start pairing in background thread
        def pair():
            success = self.adb_controller.pair_device(
                address,
                pair_port,
                connect_port,
                self.password,
                status_callback=lambda msg: GLib.idle_add(self._update_status, msg),
            )
            if success:
                GLib.idle_add(self._on_pairing_complete)

        threading.Thread(target=pair, daemon=True).start()

    def _on_pairing_complete(self):
        """Handle successful pairing."""
        self.spinner.stop()
        self._update_status(_("✓ Device paired successfully!"))
        # Close dialog after a short delay
        from aurynk.utils.device_events import notify_device_changed

        notify_device_changed()  # Defensive, but not strictly needed since DeviceStore does this
        # DeviceStore.save triggers notify_device_changed(), and DeviceStore now
        # centrally notifies the tray helper after each save. No direct socket
        # write is needed here.
        GLib.timeout_add_seconds(2, self._on_cancel, None)

    def _update_status(self, message):
        """Update status label."""
        self.status_label.set_text(message)

    def _on_qr_expired(self):
        """Handle QR code expiry."""
        self.spinner.stop()
        self.status_label.set_text(_("QR code expired. Try again."))
        # Change action button to Try Again
        self.action_btn.set_label(_("Try Again"))
        self.action_btn.remove_css_class("destructive-action")
        self.action_btn.add_css_class("suggested-action")
        self.action_btn.disconnect_by_func(self._on_cancel)
        self.action_btn.connect("clicked", self._on_try_again)
        # Cleanup
        if self.qr_timeout_id is not None:
            GLib.source_remove(self.qr_timeout_id)
            self.qr_timeout_id = None
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception:
                pass
        return False  # Don't repeat timeout

    def _on_try_again(self, button):
        """Handle Try Again button click."""
        # Change action button back to Cancel
        self.action_btn.set_label(_("Cancel"))
        self.action_btn.remove_css_class("suggested-action")
        self.action_btn.add_css_class("destructive-action")
        self.action_btn.disconnect_by_func(self._on_try_again)
        self.action_btn.connect("clicked", self._on_cancel)
        self._start_pairing()

    def _on_cancel(self, button):
        """Handle Cancel button click."""
        # Cleanup
        if self.qr_timeout_id is not None:
            GLib.source_remove(self.qr_timeout_id)
            self.qr_timeout_id = None
        if self.zeroconf:
            try:
                self.zeroconf.close()
            except Exception:
                pass
        self.close()
