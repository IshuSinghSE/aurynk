
from gi.repository import Gtk, Adw
from .utils import human_gb, human_storage

def build_device_info_page(device, screenshot_path=None, on_refresh_screenshot=None, on_close=None):
    # Card-like main container
    card = Adw.Bin()
    card.set_margin_top(16)
    card.set_margin_bottom(16)
    card.set_margin_start(16)
    card.set_margin_end(16)
    card.set_css_classes(["frame", "background"])

    # Top bar for refresh icon button (right aligned)
    topbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    topbar.set_halign(Gtk.Align.END)
    topbar.set_hexpand(True)
    refresh_icon_btn = Gtk.Button()
    refresh_icon_btn.set_icon_name("view-refresh-symbolic")
    refresh_icon_btn.set_tooltip_text("Refresh all device data")
    refresh_icon_btn.get_style_context().add_class("flat")
    refresh_icon_btn.set_valign(Gtk.Align.CENTER)
    def on_refresh_all(_btn):
        # Full data refresh: screenshot, spec, thumbnail, etc.
        from lib.device_store import fetch_and_update_device_data, load_paired_devices
        fetch_and_update_device_data(device)
        # Optionally reload UI or notify user here
        if on_refresh_screenshot:
            on_refresh_screenshot(full_refresh=True)
    refresh_icon_btn.connect("clicked", on_refresh_all)
    topbar.append(refresh_icon_btn)

    # Use a grid for two-column layout
    grid = Gtk.Grid()
    grid.set_column_spacing(32)
    grid.set_row_spacing(0)
    grid.set_margin_top(16)
    grid.set_margin_bottom(16)
    grid.set_margin_start(16)
    grid.set_margin_end(16)

    # --- Left: Screenshot ---
    screenshot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    screenshot_box.set_hexpand(False)
    screenshot_box.set_vexpand(True)
    screenshot_img = Gtk.Image()
    # Use thumbnail from device schema if available, else fallback to screenshot_path
    thumb_path = device.get('thumbnail') or screenshot_path
    if thumb_path:
        screenshot_img.set_from_file(thumb_path)
    screenshot_img.set_pixel_size(340)
    screenshot_img.set_halign(Gtk.Align.CENTER)
    screenshot_img.set_valign(Gtk.Align.START)
    screenshot_box.append(screenshot_img)
    # Refresh button (blue, bottom left)
    if on_refresh_screenshot:
        refresh_btn = Adw.ButtonContent()
        refresh_btn.set_label("Refresh Screesshot")
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_use_underline(True)
        refresh_btn_box = Gtk.Button(child=refresh_btn)
        refresh_btn_box.get_style_context().add_class("suggested-action")
        refresh_btn_box.set_margin_top(12)
        refresh_btn_box.set_halign(Gtk.Align.START)
        refresh_btn_box.connect("clicked", lambda btn: on_refresh_screenshot())
        screenshot_box.append(refresh_btn_box)
    grid.attach(screenshot_box, 0, 0, 1, 2)

    # --- Right: Info ---
    info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
    # Basic Info Section
    basic_header = Gtk.Label()
    basic_header.set_markup("<span size='x-large' weight='bold'>Basic Info</span>")
    basic_header.set_halign(Gtk.Align.START)
    info_box.append(basic_header)
    basic_grid = Gtk.Grid()
    basic_grid.set_column_spacing(12)
    basic_grid.set_row_spacing(6)
    def add_basic_row(label, value, row):
        l = Gtk.Label(label=label)
        l.set_halign(Gtk.Align.START)
        l.set_valign(Gtk.Align.CENTER)
        l.get_style_context().add_class("dim-label")
        v = Gtk.Label(label=value)
        v.set_halign(Gtk.Align.START)
        v.set_valign(Gtk.Align.CENTER)
        basic_grid.attach(l, 0, row, 1, 1)
        basic_grid.attach(v, 1, row, 1, 1)
    row = 0
    add_basic_row("Device Name:", device.get('name',''), row); row+=1
    add_basic_row("Manufacturer:", device.get('manufacturer',''), row); row+=1
    add_basic_row("Model:", device.get('model',''), row); row+=1
    add_basic_row("Android Version:", device.get('android_version',''), row); row+=1
    info_box.append(basic_grid)

    # Separator
    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    sep.set_margin_top(8)
    sep.set_margin_bottom(8)
    info_box.append(sep)

    # Connection Section
    conn_header = Gtk.Label()
    conn_header.set_markup("<span size='large' weight='bold'>Connection</span>")
    conn_header.set_halign(Gtk.Align.START)
    info_box.append(conn_header)
    conn_grid = Gtk.Grid()
    conn_grid.set_column_spacing(12)
    conn_grid.set_row_spacing(6)


    def add_conn_row(label, value, row):
        l = Gtk.Label(label=label)
        l.set_halign(Gtk.Align.START)
        l.set_valign(Gtk.Align.CENTER)
        l.get_style_context().add_class("dim-label")
        v = Gtk.Label(label=value)
        v.set_halign(Gtk.Align.START)
        v.set_valign(Gtk.Align.CENTER)
        conn_grid.attach(l, 0, row, 1, 1)
        conn_grid.attach(v, 1, row, 1, 1)
    row = 0
    add_conn_row("IP Address:", device.get('address',''), row); row+=1
    add_conn_row("Last Seen:", device.get('last_seen',''), row); row+=1
    info_box.append(conn_grid)

    # Specs Section
    specs_header = Gtk.Label()
    specs_header.set_markup("<span size='large' weight='bold'>Specs</span>")
    specs_header.set_halign(Gtk.Align.START)
    specs_header.set_margin_top(8)
    info_box.append(specs_header)
    spec = device.get('spec', {})
    ram = spec.get('ram', '')
    storage = spec.get('storage', '')
    battery = spec.get('battery', '')
    # Horizontal box for RAM, Battery, Storage
    hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
    hbox.set_halign(Gtk.Align.START)
    hbox.append(Gtk.Label(label=f"RAM: {ram}"))
    hbox.append(Gtk.Label(label=f"Battery: {battery}"))
    hbox.append(Gtk.Label(label=f"Storage: {storage}"))
    info_box.append(hbox)

    # Add info_box to grid
    grid.attach(info_box, 1, 0, 1, 2)

    # Stack topbar above grid in a vertical box
    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    vbox.append(topbar)
    vbox.append(grid)
    card.set_child(vbox)
    return card
