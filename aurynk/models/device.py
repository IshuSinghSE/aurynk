import subprocess
import threading

from gi.repository import GLib, GObject


class Device(GObject.Object):
    """Lightweight device object that emits 'info-updated' when ADB-backed
    details arrive.

    This keeps UI code simple: rows can listen for 'info-updated' and refresh
    themselves when the Device gains additional information.
    """

    __gsignals__ = {
        "info-updated": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, initial=None, adb_serial=None):
        super().__init__()
        self._data = dict(initial or {})
        self.adb_serial = adb_serial or self._data.get("adb_serial")

    def to_dict(self):
        return dict(self._data)

    def update_from_dict(self, d):
        self._data.update(d)
        # Notify listeners that information has been updated so UI rows
        # listening on 'info-updated' can refresh themselves immediately.
        try:
            GLib.idle_add(self.emit, "info-updated")
        except Exception:
            pass

    def fetch_details(self, timeout=5):
        # Run in a background thread
        def _task():
            try:
                if not self.adb_serial:
                    return

                props_to_fetch = [
                    ("ro.product.manufacturer", "manufacturer"),
                    ("ro.product.model", "model"),
                    ("ro.build.version.release", "android_version"),
                ]

                for prop, key in props_to_fetch:
                    try:
                        result = subprocess.run(
                            ["adb", "-s", self.adb_serial, "shell", "getprop", prop],
                            capture_output=True,
                            text=True,
                            timeout=timeout,
                        )
                        value = result.stdout.strip()
                        if value:
                            self._data[key] = value
                    except Exception:
                        pass

                # Update name if model present
                if self._data.get("model"):
                    self._data["name"] = self._data.get("model")

                # Emit signal on main thread
                GLib.idle_add(self.emit, "info-updated")
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()
