import os
import socket
import time

from gi.repository import GLib

from aurynk.lib.scrcpy_manager import ScrcpyManager
from aurynk.utils.logger import get_logger
from aurynk.windows.main_window import AurynkWindow

logger = get_logger("TrayController")

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

        scrcpy = ScrcpyManager()

        for d in devices:
            address = d.get("address")
            connect_port = d.get("connect_port")
            connected = False
            mirroring = False
            if address and connect_port:
                connected = is_device_connected(address, connect_port)
                mirroring = scrcpy.is_mirroring(address, connect_port)
            device_status.append(
                {
                    "name": d.get("name", "Unknown Device"),
                    "address": address,
                    "connected": connected,
                    "mirroring": mirroring,
                    "model": d.get("model"),
                    "manufacturer": d.get("manufacturer"),
                    "android_version": d.get("android_version"),
                }
            )
        msg = json.dumps({"devices": device_status})
    except Exception as e:
        logger.error(f"Error building device status for tray: {e}")
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
            logger.warning(f"Could not send tray status '{msg}': {e}")
            return
    logger.warning("Tray helper socket not available after retries.")


def send_devices_to_tray(devices):
    """Send a list of device dicts directly to the tray helper socket.

    This is a low-level helper used by code paths that don't have an
    application instance available (for example DeviceStore). It will
    compute the `connected` state for each device and send the same JSON
    payload the tray helper expects.
    """
    import json

    try:
        from aurynk.utils.adb_pairing import is_device_connected
    except Exception:
        # If import fails, fallback to assuming devices are disconnected
        def is_device_connected(a, p):
            return False

    from aurynk.lib.scrcpy_manager import ScrcpyManager
    scrcpy = ScrcpyManager()

    device_status = []
    for d in devices:
        address = d.get("address")
        connect_port = d.get("connect_port")
        connected = False
        mirroring = False
        if address and connect_port:
            try:
                connected = is_device_connected(address, connect_port)
                mirroring = scrcpy.is_mirroring(address, connect_port)
            except Exception:
                connected = False
        device_status.append(
            {
                "name": d.get("name", "Unknown Device"),
                "address": address,
                "connected": connected,
                "mirroring": mirroring,
                "model": d.get("model"),
                "manufacturer": d.get("manufacturer"),
                "android_version": d.get("android_version"),
            }
        )

    msg = json.dumps({"devices": device_status})

    for attempt in range(6):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(TRAY_SOCKET)
                s.sendall(msg.encode())
            return
        except FileNotFoundError:
            time.sleep(0.25)
        except Exception as e:
            logger.warning(f"Could not send devices to tray (attempt {attempt}): {e}")
            return
    logger.warning("Tray helper socket not available after retries.")


def tray_command_listener(app):
    """Listen for commands from the tray helper (e.g., show, quit, pair_new, per-device actions)."""
    if os.path.exists(APP_SOCKET):
        try:
            os.unlink(APP_SOCKET)
        except Exception:
            pass
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        server.bind(APP_SOCKET)
        server.listen(1)
        # Allow accept to timeout periodically so we can check app state and exit cleanly
        server.settimeout(1.0)
        logger.info(f"Command listener ready on {APP_SOCKET}")
        # The app can set `app._stop_tray_listener = True` to request shutdown
        while not getattr(app, "_stop_tray_listener", False):
            try:
                conn, _ = server.accept()
            except socket.timeout:
                continue
            except Exception as e:
                # If accept fails (socket closed/unlinked), break out
                logger.error(f"Tray command listener accept error: {e}")
                break

            try:
                data = conn.recv(1024)
                if data:
                    msg = data.decode()
                    logger.debug(f"Received command: {msg}")
                    if msg == "show":
                        GLib.idle_add(app.present_main_window)
                    elif msg == "pair_new":
                        GLib.idle_add(app.show_pair_dialog)
                    elif msg == "quit":
                        logger.info("Received quit from tray. Exiting.")
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
            except Exception as e:
                logger.error(f"Error reading tray command: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    finally:
        try:
            server.close()
        except Exception:
            pass
        # best-effort cleanup of socket path
        try:
            if os.path.exists(APP_SOCKET):
                os.unlink(APP_SOCKET)
        except Exception:
            pass


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
            if scrcpy.is_mirroring(address, connect_port):
                scrcpy.stop_mirror(address, connect_port)
            else:
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
