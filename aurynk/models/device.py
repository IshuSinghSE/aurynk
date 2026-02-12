import subprocess
import threading

from gi.repository import GLib, GObject

from aurynk.utils.adb_utils import get_adb_path


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

                # Fetch all properties in a single adb shell command to reduce subprocess overhead
                cmd = (
                    "getprop ro.product.manufacturer; echo '|||'; "
                    "getprop ro.product.model; echo '|||'; "
                    "getprop ro.build.version.release"
                )

                try:
                    result = subprocess.run(
                        [get_adb_path(), "-s", self.adb_serial, "shell", cmd],
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                    )

                    if result.returncode == 0:
                        parts = result.stdout.split("|||")
                        if len(parts) >= 3:
                            manufacturer = parts[0].strip()
                            model = parts[1].strip()
                            version = parts[2].strip()

                            if manufacturer:
                                self._data["manufacturer"] = manufacturer
                            if model:
                                self._data["model"] = model
                            if version:
                                self._data["android_version"] = version
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
