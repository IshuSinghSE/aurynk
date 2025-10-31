
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

    def render_devices():
        # Always reload from JSON file
        devices = load_paired_devices()
        # Remove old device rows (all after header and label)
        child = main_box.get_first_child()
        # Skip header_bar and device_label (first two children)
        if child:
            child = child.get_next_sibling()
        if child:
            child = child.get_next_sibling()
        # Remove all remaining children
        while child:
            next_child = child.get_next_sibling()
            main_box.remove(child)
            child = next_child
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
                # ...existing code for connect/settings/scrcpy buttons...
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
                # Per-device state functions, each bound to its own closure
                def make_set_connected(address, port, dev_name, device, connect_btn, set_connected, set_disconnected):
                    def set_connected_fn():
                        label = Gtk.Label()
                        label.set_markup("<span weight='bold' foreground='#39ff14'>Connected</span>")
                        connect_btn.set_child(label)
                        connect_btn.set_sensitive(True)
                        for handler_id in getattr(connect_btn, '_handler_ids', []):
                            connect_btn.disconnect(handler_id)
                        connect_btn._handler_ids = []
                        handler_id = connect_btn.connect("clicked", make_on_disconnect_clicked(address, port, dev_name, device, connect_btn, set_connected, set_disconnected))
                        connect_btn._handler_ids.append(handler_id)
                    return set_connected_fn
                def make_set_disconnected(address, port, dev_name, device, connect_btn, set_connected, set_offline):
                    def set_disconnected_fn():
                        label = Gtk.Label()
                        label.set_markup("<span weight='bold'>Connect</span>")
                        connect_btn.set_child(label)
                        connect_btn.set_sensitive(True)
                        for handler_id in getattr(connect_btn, '_handler_ids', []):
                            connect_btn.disconnect(handler_id)
                        connect_btn._handler_ids = []
                        handler_id = connect_btn.connect("clicked", make_do_connect(address, port, dev_name, device, set_connected, set_offline))
                        connect_btn._handler_ids.append(handler_id)
                    return set_disconnected_fn
                def make_set_offline(address, port, dev_name, device, connect_btn, set_connected, set_offline):
                    def set_offline_fn():
                        label = Gtk.Label()
                        label.set_markup("<span weight='bold' foreground='red'>Device Offline</span>")
                        connect_btn.set_child(label)
                        connect_btn.set_sensitive(True)
                        for handler_id in getattr(connect_btn, '_handler_ids', []):
                            connect_btn.disconnect(handler_id)
                        connect_btn._handler_ids = []
                        handler_id = connect_btn.connect("clicked", make_do_connect(address, port, dev_name, device, set_connected, set_offline))
                        connect_btn._handler_ids.append(handler_id)
                    return set_offline_fn
                def make_do_connect(address, port, dev_name, device, set_connected, set_offline):
                    def do_connect(_btn):
                        import subprocess
                        result = subprocess.run(["adb", "connect", f"{address}:{port}"], capture_output=True, text=True)
                        if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                            set_connected()
                        else:
                            set_offline()
                    return do_connect
                def make_on_disconnect_clicked(address, port, dev_name, device, connect_btn, set_connected, set_disconnected):
                    def on_disconnect_clicked(_btn):
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
                                if is_device_connected(address, port):
                                    set_connected()
                                else:
                                    set_disconnected()
                        alert.connect("response", on_response)
                        alert.present()
                    return on_disconnect_clicked
                connect_btn = Gtk.Button()
                connect_btn._handler_ids = []
                # Use a mutable state object to allow mutual references
                state = {}
                def set_connected():
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold' foreground='#39ff14'>Connected</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", make_on_disconnect_clicked(address, port, dev_name, device, connect_btn, state['set_connected'], state['set_disconnected']))
                    connect_btn._handler_ids.append(handler_id)
                def set_disconnected():
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold'>Connect</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", make_do_connect(address, port, dev_name, device, state['set_connected'], state['set_offline']))
                    connect_btn._handler_ids.append(handler_id)
                def set_offline():
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold' foreground='red'>Device Offline</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", make_do_connect(address, port, dev_name, device, state['set_connected'], state['set_offline']))
                    connect_btn._handler_ids.append(handler_id)
                state['set_connected'] = set_connected
                state['set_disconnected'] = set_disconnected
                state['set_offline'] = set_offline
                connect_btn = Gtk.Button()
                connect_btn._handler_ids = []
                # Scrcpy button (must be defined before set_connected_local etc)
                scrcpy_btn = Gtk.Button()
                scrcpy_btn.set_icon_name("video-display-symbolic")
                scrcpy_btn.set_halign(Gtk.Align.END)
                scrcpy_btn.set_valign(Gtk.Align.CENTER)
                scrcpy_btn.set_tooltip_text("Open scrcpy for screen mirroring")
                def launch_scrcpy(_btn, address=address, port=port):
                    import subprocess
                    import threading
                    proc = subprocess.Popen(["scrcpy", "-s", f"{address}:{port}"])
                    def monitor_scrcpy():
                        proc.wait()
                    threading.Thread(target=monitor_scrcpy, daemon=True).start()
                scrcpy_btn.connect("clicked", launch_scrcpy)
                # Bind all handlers to this device's address/port/dev_name/device using default arguments
                def set_connected_local(address=address, port=port, dev_name=dev_name, device=device):
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold' foreground='#39ff14'>Connected</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    scrcpy_btn.set_sensitive(True)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", lambda _btn, address=address, port=port, dev_name=dev_name, device=device: on_disconnect_clicked_local(_btn, address, port, dev_name, device))
                    connect_btn._handler_ids.append(handler_id)
                def set_disconnected_local(address=address, port=port, dev_name=dev_name, device=device):
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold'>Connect</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    scrcpy_btn.set_sensitive(False)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", lambda _btn, address=address, port=port, dev_name=dev_name, device=device: do_connect_local(_btn, address, port, dev_name, device))
                    connect_btn._handler_ids.append(handler_id)
                def set_offline_local(address=address, port=port, dev_name=dev_name, device=device):
                    label = Gtk.Label()
                    label.set_markup("<span weight='bold' foreground='red'>Device Offline</span>")
                    connect_btn.set_child(label)
                    connect_btn.set_sensitive(True)
                    for handler_id in getattr(connect_btn, '_handler_ids', []):
                        connect_btn.disconnect(handler_id)
                    connect_btn._handler_ids = []
                    handler_id = connect_btn.connect("clicked", lambda _btn, address=address, port=port, dev_name=dev_name, device=device: do_connect_local(_btn, address, port, dev_name, device))
                    connect_btn._handler_ids.append(handler_id)
                def do_connect_local(_btn, address=address, port=port, dev_name=dev_name, device=device):
                    import subprocess
                    result = subprocess.run(["adb", "connect", f"{address}:{port}"], capture_output=True, text=True)
                    if "connected" in result.stdout.lower() or "already connected" in result.stdout.lower():
                        set_connected_local(address, port, dev_name, device)
                    else:
                        set_offline_local(address, port, dev_name, device)
                def on_disconnect_clicked_local(_btn, address=address, port=port, dev_name=dev_name, device=device):
                    alert = Adw.AlertDialog()
                    alert.set_title(f"Disconnect {dev_name}?")
                    alert.set_body(f"Are you sure you want to disconnect from\n {device.get('name')}?")
                    alert.add_response("cancel", "Cancel")
                    alert.add_response("ok", "Disconnect")
                    alert.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
                    def on_response(dialog, response, address=address, port=port, dev_name=dev_name, device=device):
                        if response == "ok":
                            import subprocess
                            subprocess.run(["adb", "disconnect", f"{address}:{port}"])
                            if is_device_connected(address, port):
                                set_connected_local(address, port, dev_name, device)
                            else:
                                set_disconnected_local(address, port, dev_name, device)
                    alert.connect("response", lambda dialog, response, address=address, port=port, dev_name=dev_name, device=device: on_response(dialog, response, address, port, dev_name, device))
                    alert.present()
                if connected:
                    set_connected()
                else:
                    set_disconnected()
                connect_btn.set_halign(Gtk.Align.END)
                connect_btn.set_valign(Gtk.Align.CENTER)
                row.append(connect_btn)
                btn_spacer = Gtk.Box()
                btn_spacer.set_size_request(16, 1)
                row.append(btn_spacer)
                row.append(scrcpy_btn)
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
    render_devices()

    # Return both the main_box (window content) and add_btn for signal connection
    return main_box, add_btn