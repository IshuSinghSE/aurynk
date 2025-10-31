
# Required imports

from gi.repository import Gtk, Adw
import threading
import sys
sys.path.append("../lib")
from lib import adb_pairing
from lib.device_store import load_paired_devices

def build_dashboard_window(app, win):
    # --- Header Bar ---
    header_bar = Adw.HeaderBar()
    header_bar.set_show_end_title_buttons(True)

    # App icon and name
    # icon = Gtk.Image.new_from_icon_name("com.yourdomain.mirage")
    # icon.set_pixel_size(28)
    # app_label = Gtk.Label(label="Mirage")
    # app_label.set_margin_start(0)
    # app_label.set_margin_end(12)
    # app_label.set_xalign(0)
    # app_label.set_valign(Gtk.Align.CENTER)

    # Search entry (placeholder, not functional yet)
    search_entry = Gtk.SearchEntry()
    search_entry.set_placeholder_text("Search")
    search_entry.set_margin_end(12)

    # Add Device button (callback to be set by caller)
    add_btn = Gtk.Button()
    add_btn.set_label("Add Device")
    add_btn.set_margin_end(6)
    add_btn.set_valign(Gtk.Align.CENTER)
    add_btn.set_icon_name("list-add-symbolic")

    # Header bar layout
    header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
    # header_box.append(icon)
    # header_box.append(app_label)
    header_box.append(search_entry)
    header_box.append(add_btn)
    header_bar.set_title_widget(header_box)

    # Main content box
    main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    main_box.append(header_bar)

    device_label = Gtk.Label()
    device_label.set_markup("<span size='large' weight='bold'>Paired Devices</span>")
    device_label.set_halign(Gtk.Align.START)
    device_label.set_xalign(0)
    device_label.set_valign(Gtk.Align.CENTER)
    device_label.set_margin_top(24)
    device_label.set_margin_bottom(8)
    device_label.set_margin_start(32)
    device_label.set_margin_end(16)
    main_box.append(device_label)
    devices = load_paired_devices()

    # --- Devices List ---
    if devices:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        from .device_info_page import build_device_info_page
        for idx, device in enumerate(devices):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            row.set_margin_top(18 if idx == 0 else 12)
            row.set_margin_bottom(18 if idx == len(devices)-1 else 12)
            row.set_margin_start(24)
            row.set_margin_end(24)
            row.set_hexpand(True)
            row.set_vexpand(False)
            # Left: icon + details
            left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            left_box.set_hexpand(True)
            left_box.set_vexpand(False)
            dev_icon = Gtk.Image.new_from_icon_name("com.yourdomain.mirage")
            dev_icon.set_pixel_size(32)
            left_box.append(dev_icon)
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name_label = Gtk.Label()
            dev_name = device.get('name')
            if not dev_name:
                addr = device.get('address', 'Unknown')
                port = device.get('pair_port')
                dev_name = f"{addr}:{port}" if port else addr
            name_label.set_markup(f"<span size='large' weight='bold'>{dev_name}</span>")
            name_label.set_halign(Gtk.Align.START)
            name_label.set_xalign(0)
            name_label.set_valign(Gtk.Align.CENTER)
            info_box.append(name_label)
            details = []
            if device.get('manufacturer'):
                details.append(device['manufacturer'])
            if device.get('android_version'):
                details.append(f"Android {device['android_version']}")
            if details:
                details_label = Gtk.Label(label=" | ".join(details))
                details_label.set_halign(Gtk.Align.START)
                details_label.set_xalign(0)
                details_label.set_margin_top(2)
                details_label.set_valign(Gtk.Align.CENTER)
                details_label.get_style_context().add_class("dim-label")
                info_box.append(details_label)
            left_box.append(info_box)
            row.append(left_box)
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            row.append(spacer)

            # Dynamic Connect/Connected button
            def is_device_connected(address, port):
                import subprocess
                try:
                    result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
                    lines = result.stdout.splitlines()
                    for line in lines[1:]:
                        if not line.strip():
                            continue
                        if f"{address}:{port}" in line and "device" in line:
                            return True
                except Exception:
                    pass
                return False

            address = device.get('address')
            port = device.get('connect_port') or device.get('pair_port')
            connected = is_device_connected(address, port)
            def set_connected():
                label = Gtk.Label()
                label.set_markup("<span weight='bold' foreground='#39ff14'>Connected</span>")
                connect_btn.set_child(label)
                connect_btn.set_sensitive(True)
                for handler_id in getattr(connect_btn, '_handler_ids', []):
                    connect_btn.disconnect(handler_id)
                connect_btn._handler_ids = []
                handler_id = connect_btn.connect("clicked", on_disconnect_clicked)
                connect_btn._handler_ids.append(handler_id)
            def set_disconnected():
                label = Gtk.Label()
                label.set_markup("<span weight='bold'>Connect</span>")
                connect_btn.set_child(label)
                connect_btn.set_sensitive(True)
                for handler_id in getattr(connect_btn, '_handler_ids', []):
                    connect_btn.disconnect(handler_id)
                connect_btn._handler_ids = []
                handler_id = connect_btn.connect("clicked", do_connect)
                connect_btn._handler_ids.append(handler_id)
            def set_offline():
                label = Gtk.Label()
                label.set_markup("<span weight='bold' foreground='red'>Device Offline</span>")
                connect_btn.set_child(label)
                connect_btn.set_sensitive(True)
                for handler_id in getattr(connect_btn, '_handler_ids', []):
                    connect_btn.disconnect(handler_id)
                connect_btn._handler_ids = []
                handler_id = connect_btn.connect("clicked", do_connect)
                connect_btn._handler_ids.append(handler_id)
            connect_btn = Gtk.Button()
            connect_btn._handler_ids = []
            def do_connect(_btn):
                import subprocess
                result = subprocess.run(["adb", "connect", f"{address}:{port}"], capture_output=True, text=True)
                if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                    set_connected()
                else:
                    set_offline()
            def on_disconnect_clicked(_btn, address=address, port=port, dev_name=dev_name):
                alert = Adw.AlertDialog()
                alert.set_title(f"Disconnect {dev_name}?")
                alert.set_body(f"Are you sure you want to disconnect from\n {device.get('name')}?")
                alert.add_response("cancel", "Cancel")
                alert.add_response("ok", "Disconnect")
                alert.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
                def on_response(dialog, response):
                    if response == "ok":
                        import subprocess
                        subprocess.run(["adb", "disconnect", f"{address}:{port}"])
                        set_disconnected()
                alert.connect("response", on_response)
                alert.present()
            if connected:
                set_connected()
            else:
                set_disconnected()
            connect_btn.set_halign(Gtk.Align.END)
            connect_btn.set_valign(Gtk.Align.CENTER)
            row.append(connect_btn)

            # Add spacing between connect button and settings icon
            btn_spacer = Gtk.Box()
            btn_spacer.set_size_request(16, 1)
            row.append(btn_spacer)

            # Settings (gear) button
            settings_btn = Gtk.Button()
            settings_btn.set_icon_name("emblem-system-symbolic")
            settings_btn.set_halign(Gtk.Align.END)
            settings_btn.set_valign(Gtk.Align.CENTER)
            def show_device_details(_btn, d=device):
                page = build_device_info_page(d, screenshot_path="data/192_168_1_2_screen.png")
                dialog = Gtk.Dialog(title=f"Device Details: {d.get('name') or d.get('address')}", transient_for=win, modal=True)
                dialog.set_default_size(600, 600)
                content = dialog.get_content_area()
                content.set_spacing(0)
                content.append(page)
                dialog.show()
                dialog.present()
            settings_btn.connect("clicked", show_device_details)
            row.append(settings_btn)
            card.append(row)
        main_box.append(card)

    # Return both the main_box (window content) and add_btn for signal connection
    return main_box, add_btn