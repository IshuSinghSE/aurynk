import os
import socket
import time

from gi.repository import GLib

from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.i18n import _
from aurynk.ui.windows.main_window import AurynkWindow
from aurynk.utils.logger import get_logger

logger = get_logger("TrayController")

TRAY_SOCKET = "/tmp/aurynk_tray.sock"
APP_SOCKET = "/tmp/aurynk_app.sock"


def send_status_to_tray(app, status: str = None):
    """Send a status update for all devices to the tray helper via its socket."""
    import json

    try:
        win = app.props.active_window
        if not win:
            # Try to find existing AurynkWindow (it might be hidden)
            for w in app.get_windows():
                if isinstance(w, AurynkWindow):
                    win = w
                    break

        if not win:
            win = AurynkWindow(application=app)

        devices = win.adb_controller.load_paired_devices()
        device_status = []
        from aurynk.utils.adb_utils import is_device_connected

        scrcpy = ScrcpyManager()

        # Add wireless devices
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
                    "name": d.get("name", _("Unknown Device")),
                    "address": address,
                    "connected": connected,
                    "mirroring": mirroring,
                    "model": d.get("model"),
                    "manufacturer": d.get("manufacturer"),
                    "android_version": d.get("android_version"),
                    "is_usb": False,
                }
            )

        # Add USB devices from main window state
        # This avoids blocking 'adb devices' calls and ensures consistency with UI
        if hasattr(win, "usb_rows"):
            for udev_serial, row_data in win.usb_rows.items():
                try:
                    # Handle both old format (just row) and new format (dict with data)
                    if isinstance(row_data, dict) and "data" in row_data:
                        data = row_data["data"]
                        adb_serial = data.get("adb_serial")

                        # Only list devices that have an ADB serial (are actually connected via ADB)
                        if adb_serial:
                            device_name = data.get("name", "USB Device")
                            display_name = f"* {device_name}"

                            mirroring = scrcpy.is_mirroring_serial(adb_serial)
                            logger.debug(f"USB Device {adb_serial}: mirroring={mirroring}")
                            device_status.append(
                                {
                                    "name": display_name,
                                    "address": adb_serial,
                                    "connected": True,
                                    "mirroring": mirroring,
                                    "model": data.get("model"),
                                    "manufacturer": data.get("manufacturer"),
                                    "android_version": data.get("android_version"),
                                    "is_usb": True,
                                }
                            )
                except Exception as e:
                    logger.error(f"Error adding USB device to tray status: {e}")

        msg = json.dumps({"devices": device_status})
        logger.info(f"Sending tray status: {msg}")
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
    import subprocess

    try:
        from aurynk.utils.adb_utils import is_device_connected
    except Exception:
        # If import fails, fallback to assuming devices are disconnected
        def is_device_connected(a, p):
            return False

    from aurynk.core.scrcpy_runner import ScrcpyManager

    scrcpy = ScrcpyManager()

    device_status = []
    # Add wireless devices
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
                "name": d.get("name", _("Unknown Device")),
                "address": address,
                "connected": connected,
                "mirroring": mirroring,
                "model": d.get("model"),
                "manufacturer": d.get("manufacturer"),
                "android_version": d.get("android_version"),
                "is_usb": False,
            }
        )

    # Add USB devices
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2)
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
        for line in lines:
            if "\t" in line:
                serial, status_str = line.split("\t", 1)
                # USB devices don't have : in serial (wireless have ip:port)
                if ":" not in serial and status_str.strip() == "device":
                    # Try to get device name from active window if possible
                    device_name = None
                    try:
                        from gi.repository import Gtk

                        app = Gtk.Application.get_default()
                        if app and hasattr(app, "props") and app.props.active_window:
                            win = app.props.active_window
                            if hasattr(win, "usb_rows"):
                                for usb_serial, row_data in win.usb_rows.items():
                                    if isinstance(row_data, dict) and "data" in row_data:
                                        if row_data["data"].get("adb_serial") == serial:
                                            device_name = row_data["data"].get("name", "USB Device")
                                            break
                    except Exception:
                        pass

                    # Fallback to generic name if not found
                    if not device_name:
                        device_name = "USB Device"

                    # Add asterisk prefix to indicate USB device
                    device_name = f"* {device_name}"

                    mirroring = scrcpy.is_mirroring_serial(serial)
                    device_status.append(
                        {
                            "name": device_name,
                            "address": serial,
                            "connected": True,
                            "mirroring": mirroring,
                            "model": None,
                            "manufacturer": None,
                            "android_version": None,
                            "is_usb": True,
                        }
                    )
    except Exception as e:
        logger.debug(f"Could not get USB devices: {e}")

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
                    elif msg == "about":
                        GLib.idle_add(app.show_about_dialog)
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
    """Handle mirror command from tray - supports both wireless and USB devices."""
    win = app.props.active_window
    if not win:
        # Try to find existing AurynkWindow (it might be hidden)
        for w in app.get_windows():
            if isinstance(w, AurynkWindow):
                win = w
                break

    if not win:
        win = AurynkWindow(application=app)

    scrcpy = win._get_scrcpy_manager()

    # Try to find in wireless devices first
    # Wireless devices use IP as address, which might not have a colon
    devices = win.adb_controller.load_paired_devices()
    wireless_device = next((d for d in devices if d.get("address") == address), None)

    if wireless_device:
        # Wireless device logic
        connect_port = wireless_device.get("connect_port")
        device_name = wireless_device.get("name")
        if connect_port and device_name:
            if scrcpy.is_mirroring(address, connect_port):
                scrcpy.stop_mirror(address, connect_port)
            else:
                scrcpy.start_mirror(address, connect_port, device_name)
    else:
        # Assume USB device - address is the serial number
        device_name = "USB Device"
        # Try to get device name from USB monitor
        if hasattr(win, "usb_rows"):
            for usb_serial, row_data in win.usb_rows.items():
                # Handle both old format (just row) and new format (dict with data)
                if isinstance(row_data, dict) and "data" in row_data:
                    if row_data["data"].get("adb_serial") == address:
                        device_name = row_data["data"].get("name", "USB Device")
                        break

        # Toggle mirroring for USB device
        if scrcpy.is_mirroring_serial(address):
            scrcpy.stop_mirror_by_serial(address)
        else:
            scrcpy.start_mirror_usb(address, device_name)

    # Update mirror button states in main window
    if hasattr(win, "_update_all_mirror_buttons"):
        GLib.idle_add(win._update_all_mirror_buttons)

    send_status_to_tray(app)


def tray_unpair_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    win.adb_controller.device_store.remove_device(address)
    win._refresh_device_list()
    send_status_to_tray(app)
