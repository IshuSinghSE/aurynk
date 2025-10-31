from gi.repository import Gtk, GLib
from lib.adb_pairing import get_code, pair_device, start_mdns_pairing
from ui.qr_widget import create_qr_widget
from ui.constants import QR_SIZE, QR_CODE_LENGTH, DIALOG_TITLE, TITLE_TEXT, INSTRUCTIONS_TEXT, STATUS_TEXT, STATUS_EXPIRED, TRY_AGAIN_LABEL, CANCEL_LABEL, DONE_LABEL

def show_pairing_dialog(parent_window):
    dialog = Gtk.Dialog(title=DIALOG_TITLE, transient_for=parent_window, modal=True)
    dialog.set_default_size(420, 420)
    content = dialog.get_content_area()
    content.set_spacing(16)
    content.set_margin_top(24)
    content.set_margin_bottom(24)
    content.set_margin_start(24)
    content.set_margin_end(24)

    qr_timeout_id = [None]
    SIZE = QR_CODE_LENGTH
    NAME = "ADB_WIFI_" + get_code(SIZE)
    PASSWORD = get_code(SIZE)
    QR_STRING = f"WIFI:T:ADB;S:{NAME};P:{PASSWORD};;"
    qr_box = None
    title = Gtk.Label()
    title.set_markup(TITLE_TEXT)
    title.set_halign(Gtk.Align.START)
    content.append(title)
    instructions = Gtk.Label(label=INSTRUCTIONS_TEXT)
    instructions.set_justify(Gtk.Justification.LEFT)
    instructions.set_halign(Gtk.Align.START)
    content.append(instructions)
    # Spinner and status will be placed below the QR code
    spinner = Gtk.Spinner()
    spinner.set_halign(Gtk.Align.CENTER)
    status = Gtk.Label(label=STATUS_TEXT)
    status.set_halign(Gtk.Align.CENTER)
    try_again_btn = Gtk.Button(label=TRY_AGAIN_LABEL)
    try_again_btn.set_halign(Gtk.Align.CENTER)
    try_again_btn.set_visible(False)
    content.append(try_again_btn)

    # Cancel/Done button (will be placed below QR/spinner/status)
    cancel_btn = Gtk.Button(label=CANCEL_LABEL)
    cancel_btn.set_halign(Gtk.Align.CENTER)


    def show_qr():
        nonlocal qr_box, NAME, PASSWORD, QR_STRING
        if qr_box is not None:
            try:
                qr_box.set_parent(None)
            except Exception:
                pass
        NAME = "ADB_WIFI_" + get_code(SIZE)
        PASSWORD = get_code(SIZE)
        QR_STRING = f"WIFI:T:ADB;S:{NAME};P:{PASSWORD};;"
        qr_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        qr_box.set_valign(Gtk.Align.CENTER)
        qr_box.set_halign(Gtk.Align.CENTER)
        # Add QR code widget
        qr_img_box = create_qr_widget(QR_STRING, size=QR_SIZE)
        qr_box.append(qr_img_box)
        qr_box.append(spinner)
        qr_box.append(status)
        # Add Cancel/Done button below spinner/status
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(8)
        btn_box.append(cancel_btn)
        qr_box.append(btn_box)
        content.append(qr_box)

    def expire_qr():
        spinner.stop()
        status.set_text(STATUS_EXPIRED)
        if qr_box is not None:
            try:
                qr_box.set_parent(None)
            except Exception:
                pass
        try_again_btn.set_visible(True)
        return False

    def start_qr_timer():
        if qr_timeout_id[0]:
            GLib.source_remove(qr_timeout_id[0])
        qr_timeout_id[0] = GLib.timeout_add_seconds(30, expire_qr)

    def reset_dialog(*_):
        show_qr()
        status.set_text("Scan the QR code with your phone (Developer Options > Wireless Debugging > Pair device with QR code)")
        spinner.start()
        try_again_btn.set_visible(False)
        start_qr_timer()

    try_again_btn.connect("clicked", reset_dialog)
    show_qr()
    device_ports = []
    zc = None

    def on_pair_and_connect(addr, pair_port, connect_port, password):
        pair_device(addr, pair_port, connect_port, password, status_cb=status.set_text)
        # connect_device is now handled inside pair_device, so no need to call it separately
        spinner.stop()
        if qr_box is not None:
            try:
                qr_box.set_parent(None)
            except Exception:
                pass
        cancel_btn.set_label(DONE_LABEL)
        if qr_timeout_id[0]:
            GLib.source_remove(qr_timeout_id[0])
            qr_timeout_id[0] = None

    zc, device_ports = start_mdns_pairing(PASSWORD, on_pair_and_connect, device_ports)

    def on_response(dialog, response):
        zc.close()
        dialog.destroy()

    def on_cancel_clicked(btn):
        zc.close()
        dialog.destroy()

    cancel_btn.connect("clicked", on_cancel_clicked)

    dialog.show()
    dialog.present()
    spinner.start()
    return dialog
