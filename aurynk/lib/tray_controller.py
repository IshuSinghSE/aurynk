import os
import socket
import time

from gi.repository import GLib

from aurynk.windows.main_window import AurynkWindow

TRAY_SOCKET = "/tmp/aurynk_tray.sock"
APP_SOCKET = "/tmp/aurynk_app.sock"


def send_status_to_tray(app, status: str = None):
    """Send a status update for all devices to the tray helper via its socket."""
    import json

    try:
        win = app.props.active_window
        if not win:
            win = AurynkWindow(application=app)
        devices = win.adb_controller.load_paired_devices()
        device_status = []
        from aurynk.utils.adb_pairing import is_device_connected

        for d in devices:
            address = d.get("address")
            connect_port = d.get("connect_port")
            connected = False
            if address and connect_port:
                connected = is_device_connected(address, connect_port)
            device_status.append(
                {
                    "name": d.get("name", "Unknown Device"),
                    "address": address,
                    "connected": connected,
                    "model": d.get("model"),
                    "manufacturer": d.get("manufacturer"),
                    "android_version": d.get("android_version"),
                }
            )
        msg = json.dumps({"devices": device_status})
    except Exception as e:
        print(f"[TrayController] Error building device status for tray: {e}")
        msg = status if status else ""
    for attempt in range(5):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(TRAY_SOCKET)
                s.sendall(msg.encode())
            return
        except FileNotFoundError:
            time.sleep(0.5)
        except Exception as e:
            print(f"[TrayController] Could not send tray status '{msg}': {e}")
            return
    print("[TrayController] Tray helper socket not available after retries.")


def tray_command_listener(app):
    """Listen for commands from the tray helper (e.g., show, quit, pair_new, per-device actions)."""
    if os.path.exists(APP_SOCKET):
        try:
            os.unlink(APP_SOCKET)
        except Exception:
            pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(APP_SOCKET)
    server.listen(1)
    print(f"[TrayController] Command listener ready on {APP_SOCKET}")
    while True:
        try:
            conn, _ = server.accept()
            data = conn.recv(1024)
            if data:
                msg = data.decode()
                print(f"[TrayController] Received command: {msg}")
                if msg == "show":
                    GLib.idle_add(app.present_main_window)
                elif msg == "pair_new":
                    GLib.idle_add(app.show_pair_dialog)
                elif msg == "quit":
                    print("[TrayController] Received quit from tray. Exiting.")
                    GLib.idle_add(app.quit)
                elif msg.startswith("connect:"):
                    address = msg.split(":", 1)[1]
                    GLib.idle_add(tray_connect_device, app, address)
                elif msg.startswith("disconnect:"):
                    address = msg.split(":", 1)[1]
                    GLib.idle_add(tray_disconnect_device, app, address)
                elif msg.startswith("mirror:"):
                    address = msg.split(":", 1)[1]
                    GLib.idle_add(tray_mirror_device, app, address)
                elif msg.startswith("unpair:"):
                    address = msg.split(":", 1)[1]
                    GLib.idle_add(tray_unpair_device, app, address)
            conn.close()
        except Exception as e:
            print(f"[TrayController] Tray command listener error: {e}")


def tray_connect_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    devices = win.adb_controller.load_paired_devices()
    device = next((d for d in devices if d.get("address") == address), None)
    if device:
        connect_port = device.get("connect_port")
        if connect_port:
            import subprocess

            subprocess.run(["adb", "connect", f"{address}:{connect_port}"])
        win._refresh_device_list()
        send_status_to_tray(app)


def tray_disconnect_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    devices = win.adb_controller.load_paired_devices()
    device = next((d for d in devices if d.get("address") == address), None)
    if device:
        connect_port = device.get("connect_port")
        if connect_port:
            import subprocess

            subprocess.run(["adb", "disconnect", f"{address}:{connect_port}"])
        win._refresh_device_list()
        send_status_to_tray(app)


def tray_mirror_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    devices = win.adb_controller.load_paired_devices()
    device = next((d for d in devices if d.get("address") == address), None)
    if device:
        connect_port = device.get("connect_port")
        device_name = device.get("name")
        if connect_port and device_name:
            scrcpy = win._get_scrcpy_manager()
            if not scrcpy.is_mirroring(address, connect_port):
                scrcpy.start_mirror(address, connect_port, device_name)
        win._refresh_device_list()
        send_status_to_tray(app)


def tray_unpair_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    win.adb_controller.device_store.remove_device(address)
    win._refresh_device_list()
    send_status_to_tray(app)
