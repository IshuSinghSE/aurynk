"""Pairing dialog for adding new devices."""

import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
import threading

from gi.repository import Adw, GLib, Gtk

from aurynk.core.adb_manager import ADBController
from aurynk.ui.widgets.pin_entry import PinEntryBox
from aurynk.ui.widgets.qr_view import create_qr_widget
from aurynk.utils.settings import SettingsManager


class PairingDialog(Gtk.Dialog):
    """Dialog for pairing new Android devices."""

    def __init__(self, parent):
        super().__init__(title=_("Pair New Device"), transient_for=parent, modal=True)

        self.adb_controller = ADBController()
        self.settings = SettingsManager()
        self.zeroconf = None
        self.browser = None
        self.qr_timeout_id = None

        self.set_default_size(500, 600)

        # Setup UI
        self._setup_ui()

        # Start QR pairing by default
        self._start_qr_pairing()

    def _setup_ui(self):
        """Setup the dialog UI with tabbed interface for QR and Manual pairing."""
        content = self.get_content_area()
        content.set_spacing(0)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)

        # ViewStack for switching between QR and Manual methods
        self.view_stack = Adw.ViewStack()

        # QR Code pairing page
        qr_page = self._create_qr_page()
        qr_stack_page = self.view_stack.add_titled(qr_page, "qr", _("QR Code"))
        qr_stack_page.set_icon_name("qrscanner-symbolic")

        # Manual pairing page
        manual_page = self._create_manual_page()
        manual_stack_page = self.view_stack.add_titled(manual_page, "manual", _("Manual"))
        manual_stack_page.set_icon_name("input-keyboard-symbolic")

        # ViewSwitcher for tabs
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.view_stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_margin_bottom(20)

        content.append(switcher)
        content.append(self.view_stack)

    def _create_qr_page(self):
        """Create QR code pairing page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.set_margin_top(12)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_margin_bottom(12)

        # Title (centered, bold, large)
        title = Gtk.Label()
        title.set_markup(f'<span size="x-large" weight="bold">{_("Scan QR Code")}</span>')
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(8)
        page.append(title)

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
        page.append(instructions)

        # QR code container (centered)
        self.qr_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.qr_container.set_halign(Gtk.Align.CENTER)
        self.qr_container.set_valign(Gtk.Align.CENTER)
        self.qr_container.set_margin_top(16)
        page.append(self.qr_container)

        # Spinner (centered, below QR)
        self.spinner = Gtk.Spinner()
        self.spinner.set_halign(Gtk.Align.CENTER)
        self.spinner.start()

        # Status label (centered, subtle)
        self.qr_status_label = Gtk.Label(label=_("Generating QR code..."))
        self.qr_status_label.set_halign(Gtk.Align.CENTER)
        self.qr_status_label.set_margin_top(8)
        self.qr_status_label.get_style_context().add_class("dim-label")

        # Action button (dynamically changes between Cancel and Try Again)
        self.qr_action_btn = Gtk.Button()
        self.qr_action_btn.set_label(_("Cancel"))
        self.qr_action_btn.add_css_class("destructive-action")
        self.qr_action_btn.connect("clicked", self._on_cancel)
        self.qr_action_btn.set_halign(Gtk.Align.CENTER)
        self.qr_action_btn.set_margin_top(18)
        page.append(self.qr_action_btn)

        return page

    def _create_manual_page(self):
        """Create manual pairing page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        page.set_margin_top(12)
        page.set_margin_start(12)
        page.set_margin_end(12)
        page.set_margin_bottom(12)

        # Title
        title = Gtk.Label()
        title.set_markup(f'<span size="x-large" weight="bold">{_("Manual Pairing")}</span>')
        title.set_halign(Gtk.Align.CENTER)
        title.set_margin_bottom(8)
        page.append(title)

        # Instructions
        instructions = Gtk.Label()
        instructions.set_markup(
            f'<span size="medium">{_("Enter the IP address, port, and pairing code")}\n{_("from Wireless Debugging settings")}</span>'
        )
        instructions.set_halign(Gtk.Align.CENTER)
        instructions.set_wrap(True)
        instructions.set_justify(Gtk.Justification.CENTER)
        instructions.set_margin_bottom(20)
        instructions.get_style_context().add_class("dim-label")
        page.append(instructions)

        # Main form box
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        form_box.set_margin_top(20)
        form_box.set_margin_bottom(20)
        form_box.set_margin_start(40)
        form_box.set_margin_end(40)

        # IP Address Entry (traditional entry row)
        ip_group = Adw.PreferencesGroup()
        ip_row = Adw.EntryRow()
        ip_row.set_title(_("IP Address"))
        ip_row.set_text("192.168.")
        ip_row.set_tooltip_text(
            _(
                "Find this in: Settings → Developer Options → Wireless Debugging\n"
                "Example: 192.168.1.100"
            )
        )
        self.ip_entry = ip_row
        ip_group.add(ip_row)
        form_box.append(ip_group)

        # Port Entry (PIN-style with 5 boxes)
        port_pin = PinEntryBox(
            5,
            _("Pairing Port"),
            _(
                "Tap 'Pair device with pairing code' and note the port number\n"
                "Example: 45678 (valid for a few minutes only)"
            ),
        )
        self.port_entry = port_pin
        form_box.append(port_pin)

        # Pairing Code Entry (PIN-style with 6 boxes)
        code_pin = PinEntryBox(
            6,
            _("Pairing Code"),
            _(
                "The 6-digit code shown when you tap 'Pair device with pairing code'\n"
                "Example: 123456 (expires after pairing or timeout)"
            ),
        )
        self.code_entry = code_pin
        form_box.append(code_pin)

        page.append(form_box)

        # Status label
        self.manual_status_label = Gtk.Label(label="")
        self.manual_status_label.set_halign(Gtk.Align.CENTER)
        self.manual_status_label.set_margin_top(12)
        self.manual_status_label.set_wrap(True)
        self.manual_status_label.get_style_context().add_class("dim-label")
        page.append(self.manual_status_label)

        # Buttons box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)

        # Cancel button
        cancel_btn = Gtk.Button(label=_("Cancel"))
        cancel_btn.connect("clicked", self._on_cancel)
        button_box.append(cancel_btn)

        # Pair button
        pair_btn = Gtk.Button(label=_("Pair"))
        pair_btn.add_css_class("suggested-action")
        pair_btn.connect("clicked", self._on_manual_pair)
        self.manual_pair_btn = pair_btn
        button_box.append(pair_btn)

        page.append(button_box)

        return page

    def _start_qr_pairing(self):
        """Start the QR pairing process."""
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
        self.qr_container.append(self.qr_status_label)

        self.qr_status_label.set_text(_("Scan the QR code with your phone"))
        self.spinner.start()

        # Start mDNS discovery in background thread
        threading.Thread(target=self._discover_devices, daemon=True).start()

        # Set timeout for QR code expiry (get from settings)
        timeout_seconds = self.settings.get("adb", "qr_timeout", 60)
        if self.qr_timeout_id:
            GLib.source_remove(self.qr_timeout_id)
        self.qr_timeout_id = GLib.timeout_add_seconds(timeout_seconds, self._on_qr_expired)

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
            GLib.idle_add(self._update_qr_status, _("Error: {}").format(e))

    def _on_device_found(self, address, pair_port, connect_port, password):
        """Handle device discovery."""
        self._update_qr_status(_("Device found: {name}").format(name=address))

        # Start pairing in background thread
        def pair():
            success = self.adb_controller.pair_device(
                address,
                pair_port,
                connect_port,
                self.password,
                status_callback=lambda msg: GLib.idle_add(self._update_qr_status, msg),
            )
            if success:
                GLib.idle_add(self._on_pairing_complete)

        threading.Thread(target=pair, daemon=True).start()

    def _on_manual_pair(self, button):
        """Handle manual pairing button click."""
        ip = self.ip_entry.get_text().strip()
        port = self.port_entry.get_value().strip()
        code = self.code_entry.get_value().strip()

        # Validate inputs
        if not ip or not port or not code:
            self._update_manual_status(_("⚠ Please fill all fields"), error=True)
            return

        if not port.isdigit() or len(port) != 5:
            self._update_manual_status(_("⚠ Port must be a 5-digit number"), error=True)
            return

        if not code.isdigit() or len(code) != 6:
            self._update_manual_status(_("⚠ Pairing code must be 6 digits"), error=True)
            return

        # Disable button and show progress
        self.manual_pair_btn.set_sensitive(False)
        self._update_manual_status(_("Pairing with {ip}:{port}...").format(ip=ip, port=port))

        # Start pairing in background thread
        def pair():
            try:
                # Use the existing pair_device method
                # First, we need to pair with the pairing port, then connect
                import subprocess

                from aurynk.utils.adb_utils import get_adb_path

                # Step 1: Pair
                pair_cmd = [get_adb_path(), "pair", f"{ip}:{port}", code]
                pair_result = subprocess.run(pair_cmd, capture_output=True, text=True, timeout=15)

                # Check if pairing succeeded (ignore "protocol fault" as it's often misleading)
                error_output = pair_result.stderr.strip() or pair_result.stdout.strip()

                # "protocol fault" is misleading - pairing often succeeds despite this message
                # Check if it's a real failure by looking for other error indicators
                is_protocol_fault_only = (
                    pair_result.returncode != 0
                    and "protocol fault" in error_output.lower()
                    and "refused" not in error_output.lower()
                    and "unreachable" not in error_output.lower()
                )

                if pair_result.returncode != 0 and not is_protocol_fault_only:
                    # Real pairing error
                    if "refused" in error_output.lower():
                        error_msg = _(
                            "Connection refused. Make sure Wireless Debugging is enabled."
                        )
                    elif "timed out" in error_output.lower() or "timeout" in error_output.lower():
                        error_msg = _(
                            "Connection timed out. Check if device is on the same network."
                        )
                    elif (
                        "no route" in error_output.lower() or "unreachable" in error_output.lower()
                    ):
                        error_msg = _(
                            "Cannot reach device. Verify the IP address and network connection."
                        )
                    else:
                        # For other errors, show a generic message (log the details)
                        error_msg = _("Pairing failed. Please verify IP, port, and code.")
                        # Log the actual error for debugging
                        import logging

                        logging.getLogger(__name__).debug(f"Pairing error: {error_output}")

                    GLib.idle_add(self._update_manual_status, f"✗ {error_msg}", True)
                    GLib.idle_add(self.manual_pair_btn.set_sensitive, True)
                    return

                # If we get here, pairing succeeded (or is likely successful despite protocol fault message)
                GLib.idle_add(self._update_manual_status, _("✓ Paired! Discovering device..."))

                # Step 2: Auto-discover the connection port via mDNS
                import time

                time.sleep(2)  # Give device time to advertise mDNS service

                discovered_port = None
                port_info = self.adb_controller.get_current_ports(ip, timeout=5)
                if port_info and port_info.get("connect_port"):
                    discovered_port = port_info["connect_port"]
                else:
                    # Fallback: check adb devices for this IP
                    devices_cmd = [get_adb_path(), "devices", "-l"]
                    devices_result = subprocess.run(
                        devices_cmd, capture_output=True, text=True, timeout=5
                    )
                    for line in devices_result.stdout.splitlines():
                        if ip in line and ":" in line:
                            # Extract port from serial like "192.168.1.35:12345"
                            serial = line.split()[0]
                            if ":" in serial:
                                discovered_port = int(serial.split(":")[-1])
                                break

                if not discovered_port:
                    GLib.idle_add(
                        self._update_manual_status,
                        _(
                            "⚠ Paired, but couldn't auto-detect connection port. Check device status."
                        ),
                        True,
                    )
                    GLib.idle_add(self.manual_pair_btn.set_sensitive, True)
                    return

                connect_port = discovered_port
                GLib.idle_add(
                    self._update_manual_status,
                    _("✓ Found device at port {port}. Connecting...").format(port=connect_port),
                )

                # Try to connect
                connect_cmd = [get_adb_path(), "connect", f"{ip}:{connect_port}"]
                connect_result = subprocess.run(
                    connect_cmd, capture_output=True, text=True, timeout=10
                )

                output = (connect_result.stdout + connect_result.stderr).lower()
                if "connected" in output and "unable" not in output:
                    GLib.idle_add(
                        self._update_manual_status, _("✓ Connected! Fetching device info...")
                    )

                    # Fetch device info and save
                    device_info = self.adb_controller._fetch_device_info(ip, connect_port)
                    device_info.update(
                        {
                            "address": ip,
                            "pair_port": int(port),
                            "connect_port": connect_port,
                            "password": code,
                        }
                    )
                    self.adb_controller.save_paired_device(device_info)

                    GLib.idle_add(self._on_pairing_complete)
                else:
                    GLib.idle_add(
                        self._update_manual_status,
                        _("⚠ Paired but unable to connect. Try reconnecting from main window."),
                        True,
                    )
                    GLib.idle_add(self.manual_pair_btn.set_sensitive, True)

            except subprocess.TimeoutExpired:
                GLib.idle_add(
                    self._update_manual_status,
                    _("✗ Connection timed out. Check network and try again."),
                    True,
                )
                GLib.idle_add(self.manual_pair_btn.set_sensitive, True)
            except Exception as e:
                # Log technical errors but show friendly message
                import logging

                logging.getLogger(__name__).debug(f"Manual pairing error: {e}")
                GLib.idle_add(
                    self._update_manual_status,
                    _("✗ An error occurred. Please check your entries and try again."),
                    True,
                )
                GLib.idle_add(self.manual_pair_btn.set_sensitive, True)

        threading.Thread(target=pair, daemon=True).start()

    def _on_pairing_complete(self):
        """Handle successful pairing."""
        self.spinner.stop()
        # Update the status on whichever tab is currently active
        current_page = self.view_stack.get_visible_child_name()
        if current_page == "manual":
            self._update_manual_status(_("✓ Device paired successfully!"))
        else:
            self._update_qr_status(_("✓ Device paired successfully!"))
        # Close dialog after a short delay
        from aurynk.utils.device_events import notify_device_changed

        notify_device_changed()  # Defensive, but not strictly needed since DeviceStore does this
        # DeviceStore.save triggers notify_device_changed(), and DeviceStore now
        # centrally notifies the tray helper after each save. No direct socket
        # write is needed here.
        GLib.timeout_add_seconds(2, self._on_cancel, None)

    def _update_qr_status(self, message):
        """Update QR status label."""
        self.qr_status_label.set_text(message)

    def _update_manual_status(self, message, error=False):
        """Update manual status label."""
        if error:
            self.manual_status_label.set_markup(f'<span foreground="red">{message}</span>')
        else:
            self.manual_status_label.set_text(message)

    def _on_qr_expired(self):
        """Handle QR code expiry."""
        self.spinner.stop()
        self.qr_status_label.set_text(_("QR code expired. Try again."))
        # Change action button to Try Again
        self.qr_action_btn.set_label(_("Try Again"))
        self.qr_action_btn.remove_css_class("destructive-action")
        self.qr_action_btn.add_css_class("suggested-action")
        self.qr_action_btn.disconnect_by_func(self._on_cancel)
        self.qr_action_btn.connect("clicked", self._on_try_again)
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
        self.qr_action_btn.set_label(_("Cancel"))
        self.qr_action_btn.remove_css_class("suggested-action")
        self.qr_action_btn.add_css_class("destructive-action")
        self.qr_action_btn.disconnect_by_func(self._on_try_again)
        self.qr_action_btn.connect("clicked", self._on_cancel)
        self._start_qr_pairing()

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
