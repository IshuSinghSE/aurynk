import json
import os
import re
import socket
import threading
import time

from gi.repository import GLib

from aurynk.core.scrcpy_runner import ScrcpyManager
from aurynk.i18n import _
from aurynk.services.udev_proxy_client import UdevProxyClient
from aurynk.ui.windows.main_window import AurynkWindow
from aurynk.utils.logger import get_logger

logger = get_logger("TrayController")

TRAY_SOCKET = "/tmp/aurynk_tray.sock"
APP_SOCKET = "/tmp/aurynk_app.sock"

# Udev proxy client (lazy)
_udev_client = None
_udev_client_lock = threading.Lock()
_subscription_started = False
_subscription_lock = threading.Lock()
_cached_devices = None
_cached_devices_lock = threading.Lock()


def _update_device_row_labels(row_widget, device_data):
    """Update the labels in a device row widget to reflect updated device data.
    This is used when tray canonicalization merges new data into an existing
    row widget, ensuring the UI displays the latest information.
    """
    try:
        from gi.repository import Gtk

        # Find the info_box containing the labels (second child after icon)
        child = row_widget.get_first_child()
        if child:
            child = child.get_next_sibling()  # Skip icon, get info_box

        if not child or not isinstance(child, Gtk.Box):
            return

        # Update name label (first child of info_box)
        name_label = child.get_first_child()
        if name_label and isinstance(name_label, Gtk.Label):
            dev_name = device_data.get("name", _("Unknown Device"))
            # Strip the "* " prefix if present (helper adds it for USB devices)
            if dev_name.startswith("* "):
                dev_name = dev_name[2:]
            name_label.set_markup(f'<span size="large" weight="bold">{dev_name}</span>')

        # Update details label (second child of info_box)
        details_label = name_label.get_next_sibling() if name_label else None
        if details_label and isinstance(details_label, Gtk.Label):
            details = []
            if device_data.get("manufacturer"):
                details.append(device_data["manufacturer"])
            if device_data.get("model"):
                details.append(device_data["model"])
            if device_data.get("android_version"):
                details.append(f"Android {device_data['android_version']}")

            if details:
                details_label.set_label(" • ".join(details))
                details_label.set_visible(True)
            else:
                details_label.set_visible(False)
    except Exception as e:
        logger.debug(f"Failed to update device row labels: {e}")


def _canonicalize_adb_devices(devs):
    """Return a list of canonical adb device dicts deduplicated by adb serial.

    Prioritizes devices with action == 'adb_present' (these provide the
    adb serial). For other udev entries that indicate adb capability we try
    to derive a short serial (ID_SERIAL_SHORT) and merge if it matches an
    existing adb device. The returned list contains dicts with at least
    'adb_serial' and 'name' keys suitable for caching or populating
    `win.usb_rows`.
    """
    if not devs:
        return []

    canonical = {}

    # Use a normalized-key map to deduplicate variants of the same serial
    # (different punctuation/case). Normalization strips non-alphanum and
    # lowercases: e.g. 'SM-G610F' and 'SM_G610F' -> 'smg610f'.
    def _norm(s):
        if not s:
            return None
        try:
            return re.sub(r"[^0-9a-z]", "", str(s).lower())
        except Exception:
            return str(s).lower()

    norm_map = {}

    # First pass: add explicit adb_present devices (authoritative)
    for dev in devs:
        try:
            if dev.get("action") != "adb_present":
                continue
            serial = dev.get("serial")
            if not serial:
                continue
            adb_props = dev.get("adb_props") or {}
            name = (
                adb_props.get("model")
                or dev.get("properties", {}).get("ID_MODEL")
                or dev.get("name")
                or serial
            )
            entry = {
                "adb_serial": serial,
                "name": name,
                "model": adb_props.get("model"),
                "manufacturer": adb_props.get("manufacturer"),
                "android_version": adb_props.get("version"),
            }
            n = _norm(serial)
            if n:
                norm_map[n] = entry
            else:
                canonical[serial] = entry
        except Exception:
            continue

    # Second pass: include other udev entries that indicate adb but aren't
    # explicit adb_present. Prefer short serials (ID_SERIAL_SHORT) and
    # avoid adding entries that would duplicate existing adb devices.
    for dev in devs:
        try:
            is_adb = False
            if dev.get("action") == "adb_present":
                is_adb = True
            if dev.get("adb_props"):
                is_adb = True
            if dev.get("properties", {}).get("adb_user") == "yes":
                is_adb = True
            if not is_adb:
                continue

            props = dev.get("properties", {}) or {}
            short = props.get("ID_SERIAL_SHORT")
            serial = dev.get("serial") or dev.get("address")

            # Choose key: prefer short if available
            key = short or serial
            if not key:
                continue

            n = _norm(key)
            # Skip if normalized key already present (dedupe variants)
            if n and n in norm_map:
                continue

            adb_props = dev.get("adb_props") or {}
            name = adb_props.get("model") or props.get("ID_MODEL") or dev.get("name") or key

            entry = {
                "adb_serial": key,
                "name": name,
                "model": adb_props.get("model"),
                "manufacturer": adb_props.get("manufacturer"),
                "android_version": adb_props.get("version"),
            }

            if n:
                norm_map[n] = entry
            else:
                # fallback to raw key
                canonical[key] = entry
        except Exception:
            continue

    # Merge norm_map + canonical into a single list
    raw = []
    for v in norm_map.values():
        raw.append(v)
    for v in canonical.values():
        raw.append(v)

    # Final dedupe pass: prefer entries with adb_serial and merge entries
    # that share a normalized serial. For entries lacking a serial, fall
    # back to normalized (model|manufacturer) to merge name-only variants.
    final_map = {}

    def _fallback_key(e):
        m = e.get("model") or ""
        mf = e.get("manufacturer") or ""
        k = f"{m}|{mf}"
        return re.sub(r"[^0-9a-z]", "", k.lower())

    for e in raw:
        nserial = _norm(e.get("adb_serial")) if e.get("adb_serial") else None
        if nserial:
            key = f"s:{nserial}"
        else:
            key = f"m:{_fallback_key(e)}"

        if key in final_map:
            # Merge missing fields into existing entry, keep existing adb_serial
            existing = final_map[key]
            for fld in ("name", "model", "manufacturer", "android_version"):
                if not existing.get(fld) and e.get(fld):
                    existing[fld] = e.get(fld)
            if not existing.get("adb_serial") and e.get("adb_serial"):
                existing["adb_serial"] = e.get("adb_serial")
        else:
            final_map[key] = dict(e)

    return list(final_map.values())


def _get_udev_client():
    global _udev_client
    with _udev_client_lock:
        if _udev_client is None:
            try:
                _udev_client = UdevProxyClient()
            except Exception:
                _udev_client = None
        return _udev_client


def start_udev_subscription(app):
    """Start subscription to host helper events to refresh UI automatically.

    Idempotent: safe to call multiple times.
    """
    global _subscription_started
    with _subscription_lock:
        if _subscription_started:
            return
        client = _get_udev_client()
        if not client:
            # client may be unavailable inside sandbox; caller may retry later
            return

        def _on_event(msg):
            try:
                t = msg.get("type")
            except Exception:
                return

            # If we received a lightweight 'device' notification, fetch a
            # full 'status' from the helper in a background thread and
            # re-dispatch it as a 'state' message so the main window can
            # update `usb_rows` deterministically.
            if t == "device":

                def _fetch_status_and_dispatch():
                    try:
                        client = _get_udev_client()
                        if not client:
                            return
                        try:
                            resp = client.send_command({"cmd": "status"}, timeout=1.0)
                        except Exception:
                            return
                        state_msg = {"type": "state", "devices": resp.get("devices", [])}
                        try:
                            _on_event(state_msg)
                        except Exception:
                            pass
                    except Exception:
                        pass

                try:
                    threading.Thread(target=_fetch_status_and_dispatch, daemon=True).start()
                except Exception:
                    pass

                    # Also schedule an immediate UI refresh on the GTK main loop so
                    # plugged/unplugged devices show up instantly while the
                    # background status fetch is in-flight.
                    try:

                        def _immediate_ui_refresh():
                            try:
                                win = None
                                if hasattr(app, "props") and getattr(app, "props", None):
                                    win = app.props.active_window
                                if not win:
                                    for w in app.get_windows():
                                        if isinstance(w, AurynkWindow):
                                            win = w
                                            break
                                if not win:
                                    return False

                                try:
                                    if hasattr(win, "_refresh_usb_list"):
                                        win._refresh_usb_list()
                                except Exception:
                                    pass
                                try:
                                    if hasattr(win, "_refresh_device_list"):
                                        win._refresh_device_list()
                                except Exception:
                                    pass
                                try:
                                    if hasattr(win, "_update_all_mirror_buttons"):
                                        win._update_all_mirror_buttons()
                                except Exception:
                                    pass
                                try:
                                    send_status_to_tray(app)
                                except Exception:
                                    pass
                            finally:
                                # single-shot
                                return False

                        GLib.idle_add(_immediate_ui_refresh)
                    except Exception:
                        pass

            if t in ("device", "process", "state"):
                # Notify GTK to refresh device list and tray
                def _refresh():
                    try:
                        win = None
                        if hasattr(app, "props") and getattr(app, "props", None):
                            win = app.props.active_window
                        if not win:
                            for w in app.get_windows():
                                if isinstance(w, AurynkWindow):
                                    win = w
                                    break
                        if not win:
                            # No window yet; cache the device list so a window
                            # created later can pick it up during initialization.
                            try:
                                devs = None
                                if isinstance(msg.get("devices"), list):
                                    devs = msg.get("devices")
                                if devs is not None:
                                    try:
                                        # Canonicalize before caching so window can
                                        # pick up deduplicated adb entries.
                                        canonical = _canonicalize_adb_devices(devs)
                                        with _cached_devices_lock:
                                            global _cached_devices
                                            _cached_devices = list(canonical)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            return False
                        # Update usb_rows from helper-provided state if present
                        try:
                            # msg may be 'state' with devices list
                            if t == "state" and isinstance(msg.get("devices"), list):
                                try:
                                    if not hasattr(win, "usb_rows") or win.usb_rows is None:
                                        win.usb_rows = {}
                                except Exception:
                                    win.usb_rows = {}

                                # Build a canonical list of adb devices and populate
                                # win.usb_rows from it. This avoids duplicates when
                                # both udev and adb_present entries exist for the
                                # same physical device.
                                canonical = _canonicalize_adb_devices(msg.get("devices"))
                                try:
                                    # Replace usb_rows with canonical mapping, reusing any
                                    # existing widgets to avoid duplicate rows created by
                                    # earlier immediate refreshes.
                                    try:
                                        old_rows = dict(win.usb_rows or {})
                                    except Exception:
                                        old_rows = {}

                                    new_rows = {}

                                    def _match_and_extract_old_row(d):
                                        adb = d.get("adb_serial")
                                        serial = d.get("serial")
                                        short = d.get("short_serial")

                                        candidates = []
                                        if adb:
                                            try:
                                                k = (
                                                    win._norm_serial(adb)
                                                    if hasattr(win, "_norm_serial")
                                                    else adb
                                                )
                                            except Exception:
                                                k = adb
                                            if k in old_rows:
                                                candidates.append(k)
                                        if serial:
                                            try:
                                                k2 = (
                                                    win._norm_serial(serial)
                                                    if hasattr(win, "_norm_serial")
                                                    else serial
                                                )
                                            except Exception:
                                                k2 = serial
                                            if k2 in old_rows:
                                                candidates.append(k2)
                                        if short:
                                            try:
                                                k3 = (
                                                    win._norm_serial(short)
                                                    if hasattr(win, "_norm_serial")
                                                    else short
                                                )
                                            except Exception:
                                                k3 = short
                                            if k3 in old_rows:
                                                candidates.append(k3)

                                        for c in candidates:
                                            entry = old_rows.get(c)
                                            if not entry:
                                                continue
                                            if isinstance(entry, dict) and "row" in entry:
                                                return c, entry.get("row")
                                            # If entry itself looks like a widget with _device_data
                                            try:
                                                if hasattr(entry, "_device_data"):
                                                    return c, entry
                                            except Exception:
                                                pass
                                        return None, None

                                    for d in canonical:
                                        serial = d.get("adb_serial")
                                        if not serial:
                                            continue
                                        try:
                                            norm_key = (
                                                win._norm_serial(serial)
                                                if hasattr(win, "_norm_serial")
                                                else None
                                            )
                                        except Exception:
                                            norm_key = None
                                        key = norm_key or serial

                                        old_key, old_row = _match_and_extract_old_row(d)
                                        if old_key and old_row:
                                            # Merge canonical data with existing local data to preserve
                                            # manufacturer, model, android_version fetched locally
                                            existing_data = old_rows.get(old_key, {}).get(
                                                "data", {}
                                            )
                                            merged_data = (
                                                dict(existing_data)
                                                if isinstance(existing_data, dict)
                                                else {}
                                            )
                                            # Update with canonical data (adds adb_serial, name from helper)
                                            merged_data.update(d)
                                            # But preserve local-only fields if they exist and canonical doesn't have them
                                            for field in [
                                                "manufacturer",
                                                "model",
                                                "android_version",
                                            ]:
                                                if (
                                                    field in existing_data
                                                    and existing_data[field]
                                                    and not d.get(field)
                                                ):
                                                    merged_data[field] = existing_data[field]
                                            new_rows[key] = {"data": merged_data, "row": old_row}

                                            # Update the widget labels to reflect merged data
                                            try:
                                                if hasattr(old_row, "_device_data"):
                                                    old_row._device_data = merged_data
                                                _update_device_row_labels(old_row, merged_data)
                                            except Exception:
                                                pass

                                            try:
                                                old_rows.pop(old_key, None)
                                            except Exception:
                                                pass
                                        else:
                                            new_rows[key] = {"data": d}

                                    # Remove any stale widgets left in old_rows
                                    # IMPORTANT: Only remove if the device is explicitly marked as
                                    # disconnected in helper data. Don't remove devices just because
                                    # they're not in canonical list - they might be USB devices the
                                    # helper hasn't seen yet.
                                    try:
                                        for stale_k, stale_entry in list(old_rows.items()):
                                            # Preserve devices not in canonical list - they might be local USB devices
                                            new_rows[stale_k] = stale_entry
                                    except Exception:
                                        pass

                                    win.usb_rows = new_rows
                                    # Create UI rows for any entries that don't yet have a widget
                                    try:
                                        if hasattr(win, "usb_group") and win.usb_group is not None:
                                            for serial, entry in list(win.usb_rows.items()):
                                                try:
                                                    if (
                                                        isinstance(entry, dict)
                                                        and "data" in entry
                                                        and "row" not in entry
                                                    ):
                                                        dev_data = entry["data"]
                                                        try:
                                                            row = win._create_device_row(
                                                                dev_data, is_usb=True
                                                            )
                                                            win.usb_group.add(row)
                                                            entry["row"] = row
                                                            win.usb_group.set_visible(True)
                                                        except Exception:
                                                            # Creating a row failed; ignore
                                                            pass
                                                except Exception:
                                                    # Skip problematic entry
                                                    pass
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            win._refresh_device_list()
                        except Exception:
                            pass
                        try:
                            if hasattr(win, "_update_all_mirror_buttons"):
                                win._update_all_mirror_buttons()
                        except Exception:
                            pass
                        # push status to tray
                        try:
                            send_status_to_tray(app)
                        except Exception:
                            pass
                    finally:
                        return False

                GLib.idle_add(_refresh)

        try:
            client.subscribe(_on_event)
            _subscription_started = True
        except Exception:
            pass


# Debounce mechanism to prevent tray update spam
_last_tray_update = 0
_tray_update_lock = __import__("threading").Lock()
_pending_tray_update = None
_TRAY_UPDATE_MIN_INTERVAL = 0.2  # Minimum 200ms between tray updates


def send_status_to_tray(app, status: str = None):
    """Send a status update for all devices to the tray helper via its socket.

    Uses trailing-edge debouncing: if called too frequently, schedules a delayed
    update to ensure tray always gets the final state.
    """
    global _last_tray_update, _pending_tray_update

    with _tray_update_lock:
        current_time = time.time()
        time_since_last = current_time - _last_tray_update

        # If we updated very recently, schedule a delayed update instead of dropping it
        if time_since_last < _TRAY_UPDATE_MIN_INTERVAL:
            # Cancel any existing pending update (safely handle if already fired)
            if _pending_tray_update is not None:
                try:
                    GLib.source_remove(_pending_tray_update)
                except Exception:
                    pass  # Source already removed/fired

            # Schedule new update after the minimum interval
            delay_ms = int((_TRAY_UPDATE_MIN_INTERVAL - time_since_last) * 1000) + 50
            logger.debug(
                f"Scheduling delayed tray update in {delay_ms}ms (last update {time_since_last:.3f}s ago)"
            )
            _pending_tray_update = GLib.timeout_add(delay_ms, lambda: _do_tray_update(app, status))
            return

        # Clear any pending update since we're doing it now (safely handle if already fired)
        if _pending_tray_update is not None:
            try:
                GLib.source_remove(_pending_tray_update)
            except Exception:
                pass  # Source already removed/fired
            _pending_tray_update = None

        _last_tray_update = current_time

    # Perform the actual update (outside the lock)
    _do_tray_update(app, status)


def _do_tray_update(app, status: str = None):
    """Internal function that actually performs the tray update."""
    global _last_tray_update, _pending_tray_update

    # Update timestamp and clear pending flag
    with _tray_update_lock:
        _last_tray_update = time.time()
        _pending_tray_update = None

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
        # Query helper for running processes (non-blocking small timeout)
        helper_processes = {}
        client = _get_udev_client()
        if client:
            try:
                resp = client.send_command({"cmd": "status"}, timeout=0.5)
                helper_processes = resp.get("processes", {}) or {}
            except Exception:
                helper_processes = {}

        # Add wireless devices
        # Prefer using the main window's row data to ensure consistency with UI
        wireless_devices_processed = False
        if hasattr(win, "_wireless_rows") and win._wireless_rows:
            try:
                for row in win._wireless_rows:
                    # Skip placeholder rows or rows without device data
                    if not hasattr(row, "_device_data") or not row._device_data:
                        continue

                    d = row._device_data
                    address = d.get("address")
                    connect_port = d.get("connect_port")
                    connected = False
                    mirroring = False

                    if address and connect_port:
                        connected = is_device_connected(address, connect_port)
                        # Prefer helper process status when available
                        key = f"{address}:{connect_port}"
                        mirroring = False
                        if key in helper_processes:
                            mirroring = True
                        else:
                            mirroring = scrcpy.is_mirroring(address, connect_port)
                        logger.debug(
                            f"Wireless {address}:{connect_port}: connected={connected}, mirroring={mirroring}, processes={list(scrcpy.processes.keys())}"
                        )

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
                wireless_devices_processed = True
            except Exception as e:
                logger.error(f"Error reading wireless rows for tray: {e}")

        # Fallback to loading from storage if UI rows aren't available
        if not wireless_devices_processed:
            devices = win.adb_controller.load_paired_devices()
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

                            mirroring = False
                            if adb_serial in helper_processes:
                                mirroring = True
                            else:
                                mirroring = scrcpy.is_mirroring_serial(adb_serial)
                            logger.debug(
                                f"USB Device {adb_serial}: mirroring={mirroring}, processes={list(scrcpy.processes.keys())}"
                            )
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
        # logger.info(f"Sending tray status: {msg}")
    except Exception as e:
        logger.error(f"Error building device status for tray: {e}")
        msg = status if status else ""
    for attempt in range(5):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(TRAY_SOCKET)
                s.sendall(msg.encode())
            return False  # Don't repeat if called from GLib.timeout_add
        except FileNotFoundError:
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Could not send tray status '{msg}': {e}")
            return False
    logger.warning("Tray helper socket not available after retries.")
    return False


def send_devices_to_tray(devices):
    """Send a list of device dicts directly to the tray helper socket.

    This is a low-level helper used by code paths that don't have an
    application instance available (for example DeviceStore). It will
    compute the `connected` state for each device and send the same JSON
    payload the tray helper expects.
    """
    import subprocess

    try:
        from aurynk.utils.adb_utils import is_device_connected
    except Exception:
        # If import fails, fallback to assuming devices are disconnected
        def is_device_connected(a, p):
            return False

    from aurynk.core.scrcpy_runner import ScrcpyManager

    scrcpy = ScrcpyManager()
    # Try to get helper process list
    helper_processes = {}
    client = _get_udev_client()
    if client:
        try:
            resp = client.send_command({"cmd": "status"}, timeout=0.5)
            helper_processes = resp.get("processes", {}) or {}
        except Exception:
            helper_processes = {}

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

                    mirroring = False
                    if serial in helper_processes:
                        mirroring = True
                    else:
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
    wireless_device = None

    # Check UI rows first for most up-to-date state (especially connect_port)
    if hasattr(win, "_wireless_rows") and win._wireless_rows:
        try:
            for row in win._wireless_rows:
                if hasattr(row, "_device_data") and row._device_data:
                    d = row._device_data
                    if d.get("address") == address:
                        wireless_device = d
                        break
        except Exception:
            pass

    if not wireless_device:
        # Fallback to storage
        devices = win.adb_controller.load_paired_devices()
        wireless_device = next((d for d in devices if d.get("address") == address), None)

    if wireless_device:
        # Wireless device logic
        connect_port = wireless_device.get("connect_port")
        device_name = wireless_device.get("name")
        logger.debug(f"Tray mirror toggle for {address}:{connect_port} (Name: {device_name})")

        if connect_port:
            # Prefer delegating start/stop to the host helper when available
            client = _get_udev_client()
            is_mirroring = False
            helper_processes = {}
            if client:
                try:
                    resp = client.send_command({"cmd": "status"}, timeout=0.5)
                    helper_processes = resp.get("processes", {}) or {}
                except Exception:
                    helper_processes = {}

            key = f"{address}:{connect_port}"
            if key in helper_processes:
                is_mirroring = True
            else:
                is_mirroring = scrcpy.is_mirroring(address, connect_port)

            logger.debug(f"Current mirroring state for {address}:{connect_port} is {is_mirroring}")

            if is_mirroring:
                # Stop via helper if possible, else local manager
                if client:
                    try:
                        client.send_command({"cmd": "stop_mirror", "serial": key}, timeout=0.5)
                        # Clear any UI override we may have set when starting via tray
                        try:
                            # find matching wireless row and clear override
                            if hasattr(win, "_wireless_rows") and win._wireless_rows:
                                for row in win._wireless_rows:
                                    if hasattr(row, "_device_data") and row._device_data:
                                        if row._device_data.get("address") == address:
                                            row._device_data.pop("_mirroring_override", None)
                                            break
                        except Exception:
                            pass
                    except Exception:
                        scrcpy.stop_mirror(address, connect_port)
                else:
                    scrcpy.stop_mirror(address, connect_port)
            else:
                # Stop stale helper processes for this address if any
                if client:
                    for s in list(helper_processes.keys()):
                        if s.startswith(f"{address}:"):
                            try:
                                client.send_command(
                                    {"cmd": "stop_mirror", "serial": s}, timeout=0.5
                                )
                            except Exception:
                                pass
                    # Start new mirror via helper
                    try:
                        client.send_command(
                            {
                                "cmd": "start_mirror",
                                "serial": key,
                                "options": {"scrcpy_cmd": "scrcpy"},
                            },
                            timeout=0.5,
                        )
                        # Mark a transient UI override so main window shows mirroring
                        try:
                            if hasattr(win, "_wireless_rows") and win._wireless_rows:
                                for row in win._wireless_rows:
                                    if hasattr(row, "_device_data") and row._device_data:
                                        if row._device_data.get("address") == address:
                                            row._device_data["_mirroring_override"] = True
                                            break
                        except Exception:
                            pass
                    except Exception:
                        started = False
                        try:
                            started = scrcpy.start_mirror(address, connect_port, device_name)
                        except Exception:
                            started = False
                        if not started:
                            try:
                                GLib.idle_add(
                                    lambda: (
                                        win._show_scrcpy_unavailable_dialog(
                                            f"{address}:{connect_port}"
                                        )
                                        or False
                                    )
                                )
                            except Exception:
                                logger.exception(
                                    "Failed to schedule scrcpy unavailable dialog from tray"
                                )
                else:
                    # Fallback to local start
                    for s in list(scrcpy.processes.keys()):
                        if s.startswith(f"{address}:"):
                            logger.info(
                                f"Found stale process {s} for {address}, stopping before start"
                            )
                            scrcpy.stop_mirror(address, int(s.split(":")[1]))

                    scrcpy.start_mirror(address, connect_port, device_name)

            # Update main window mirror buttons on GTK thread.
            # If we just started mirroring (is_mirroring == False previously),
            # schedule a small delay so the helper/scrcpy process has time to
            # register before UI polls `is_mirroring*`.
            try:
                if hasattr(win, "_update_all_mirror_buttons"):
                    if is_mirroring:
                        # We were mirroring and have just stopped: update immediately
                        GLib.idle_add(win._update_all_mirror_buttons)
                    else:
                        # We have just started mirroring: delay update slightly
                        GLib.timeout_add(120, lambda: (win._update_all_mirror_buttons() or False))
            except Exception:
                pass

            # Sync tray: use a small delay when starting so process bookkeeping completes
            if is_mirroring:
                GLib.timeout_add(100, lambda: send_status_to_tray(app))
            else:
                GLib.timeout_add(120, lambda: send_status_to_tray(app))
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

        # Check if currently mirroring (prefer helper)
        client = _get_udev_client()
        helper_processes = {}
        if client:
            try:
                resp = client.send_command({"cmd": "status"}, timeout=0.5)
                helper_processes = resp.get("processes", {}) or {}
            except Exception:
                helper_processes = {}

        is_mirroring = False
        if address in helper_processes:
            is_mirroring = True
        else:
            is_mirroring = scrcpy.is_mirroring_serial(address)

        # Toggle mirroring for USB device
        if is_mirroring:
            if client and address in helper_processes:
                try:
                    client.send_command({"cmd": "stop_mirror", "serial": address}, timeout=0.5)
                    # Clear any UI override set earlier for this USB serial
                    try:
                        if hasattr(win, "usb_rows") and win.usb_rows:
                            entry = win.usb_rows.get(address)
                            if isinstance(entry, dict) and "data" in entry:
                                entry["data"].pop("_mirroring_override", None)
                    except Exception:
                        pass
                except Exception:
                    scrcpy.stop_mirror_by_serial(address)
            else:
                scrcpy.stop_mirror_by_serial(address)
        else:
            if client:
                try:
                    client.send_command(
                        {
                            "cmd": "start_mirror",
                            "serial": address,
                            "options": {"scrcpy_cmd": "scrcpy"},
                        },
                        timeout=0.5,
                    )
                    # Mark transient UI override so main window reflects immediate start
                    try:
                        if hasattr(win, "usb_rows") and win.usb_rows:
                            entry = win.usb_rows.get(address)
                            if isinstance(entry, dict) and "data" in entry:
                                entry["data"]["_mirroring_override"] = True
                    except Exception:
                        pass
                except Exception:
                    started = False
                    try:
                        started = scrcpy.start_mirror_usb(address, device_name)
                    except Exception:
                        started = False
                    if not started:
                        try:
                            GLib.idle_add(
                                lambda: (win._show_scrcpy_unavailable_dialog(address) or False)
                            )
                        except Exception:
                            logger.exception(
                                "Failed to schedule scrcpy unavailable dialog from tray"
                            )
            else:
                started = False
                try:
                    started = scrcpy.start_mirror_usb(address, device_name)
                except Exception:
                    started = False
                if not started:
                    try:
                        GLib.idle_add(
                            lambda: (win._show_scrcpy_unavailable_dialog(address) or False)
                        )
                    except Exception:
                        logger.exception("Failed to schedule scrcpy unavailable dialog from tray")

        # Update main window mirror buttons on GTK thread.
        try:
            if hasattr(win, "_update_all_mirror_buttons"):
                if is_mirroring:
                    GLib.idle_add(win._update_all_mirror_buttons)
                else:
                    GLib.timeout_add(120, lambda: (win._update_all_mirror_buttons() or False))
        except Exception:
            pass

        # Sync tray: delay slightly when starting so helper/process state settles
        if is_mirroring:
            GLib.timeout_add(100, lambda: send_status_to_tray(app))
        else:
            GLib.timeout_add(120, lambda: send_status_to_tray(app))


def tray_unpair_device(app, address):
    win = app.props.active_window
    if not win:
        win = AurynkWindow(application=app)
    win.adb_controller.device_store.remove_device(address)
    win._refresh_device_list()
    send_status_to_tray(app)
