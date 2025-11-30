import os
import socket
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


import signal

from gi.repository import Adw, Gio, GLib

from aurynk.services.device_monitor import DeviceMonitor
from aurynk.services.tray_service import tray_command_listener
from aurynk.ui.windows.main_window import AurynkWindow
from aurynk.utils.logger import get_logger
from aurynk.utils.power import PowerMonitor

logger = get_logger("AurynkApp")


def start_tray_helper():
    """Start the tray helper process if not already running."""
    tray_socket = "/tmp/aurynk_tray.sock"
    # Only reuse the tray helper if the tray socket exists and is connectable
    if os.path.exists(tray_socket):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(tray_socket)
            logger.info("Tray helper already running. Reusing existing instance.")
            return True
        except Exception:
            try:
                os.unlink(tray_socket)
                logger.info("Removed stale tray socket.")
            except Exception as e:
                logger.error(f"Could not remove stale tray socket: {e}")
    # Start new tray helper. Pass our PID so the helper can signal us as a
    # fallback if socket-based IPC fails to deliver a quit request.
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "aurynk_tray.py")
    )
    env = os.environ.copy()
    try:
        env["AURYNK_APP_PID"] = str(os.getpid())
    except Exception:
        pass
    subprocess.Popen(["python3", script_path], env=env)


class AurynkApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="io.github.IshuSinghSE.aurynk",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        # Keep the application running even if no windows are visible (for tray)
        self.hold()

        # Track if this is the first activation (startup)
        self._first_activation = True

        # Initialize device monitor for auto-connect functionality
        self.device_monitor = DeviceMonitor()

        # Power monitor for suspend/resume
        self.power_monitor = PowerMonitor()

        # Register callback for port updates
        def on_port_updated(address, new_port):
            """Update device storage when port changes."""
            try:
                win = self.props.active_window
                if win and hasattr(win, "adb_controller"):
                    devices = win.adb_controller.load_paired_devices()
                    for device in devices:
                        if device.get("address") == address:
                            device["connect_port"] = new_port
                            win.adb_controller.save_paired_device(device)
                            logger.info(f"Updated port for {address} to {new_port}")
                            # Refresh UI on main thread
                            GLib.idle_add(win._refresh_device_list)
                            break
            except Exception as e:
                logger.error(f"Error updating port: {e}")

        # Register callback for successful connections (including auto-connect)
        def on_device_connected_refresh(address, port):
            """Refresh UI when device auto-connects."""
            try:
                win = self.props.active_window
                if win and hasattr(win, "_refresh_device_list"):
                    # Refresh UI on main thread after auto-connect
                    GLib.idle_add(win._refresh_device_list)
                    logger.debug(f"Scheduled UI refresh after auto-connect: {address}:{port}")
            except Exception as e:
                logger.error(f"Error refreshing UI: {e}")

        # Register callback for device disconnection
        def on_device_disconnected_refresh(address):
            """Refresh UI when device disconnects."""
            try:
                win = self.props.active_window
                if win and hasattr(win, "_refresh_device_list"):
                    # Refresh UI on main thread after disconnect
                    GLib.idle_add(win._refresh_device_list)
                    logger.info(f"Scheduled UI refresh after disconnect: {address}")
            except Exception as e:
                logger.error(f"Error refreshing UI on disconnect: {e}")

        def _on_system_sleep():
            """Handle system sleep: disconnect ADB devices if setting enabled."""
            from aurynk.utils.settings import SettingsManager

            settings = SettingsManager()
            if settings.get("adb", "auto_disconnect_on_sleep", False):
                try:
                    import subprocess

                    from aurynk.utils.adb_utils import get_adb_path

                    logger.info("System sleep: disconnecting all ADB devices...")
                    result = subprocess.run(
                        [get_adb_path(), "disconnect"], capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        logger.info("✓ All devices disconnected (sleep)")
                    else:
                        logger.debug(f"ADB disconnect output (sleep): {result.stdout}")
                except Exception as e:
                    logger.warning(f"Error disconnecting devices on sleep: {e}")

        self.device_monitor.register_callback("on_device_connected", on_port_updated)
        self.device_monitor.register_callback("on_device_connected", on_device_connected_refresh)
        self.device_monitor.register_callback("on_device_lost", on_device_disconnected_refresh)
        self.power_monitor.register_callback("sleep", _on_system_sleep)
        self.power_monitor.start()

        # Start tray command listener thread from tray_controller
        self.tray_listener_thread = threading.Thread(
            target=tray_command_listener, args=(self,), daemon=True
        )
        self.tray_listener_thread.start()
        # Give the listener thread time to bind the socket
        import time

        time.sleep(0.1)
        # register signal handlers to quit the app cleanly on SIGINT/SIGTERM
        try:
            signal.signal(signal.SIGINT, lambda s, f: GLib.idle_add(self.quit))
            signal.signal(signal.SIGTERM, lambda s, f: GLib.idle_add(self.quit))
        except Exception:
            pass

    def show_pair_dialog(self):
        """Show main window and open pairing dialog - called from tray icon."""
        # First, activate the app to show the window
        self.activate()
        # Then show the pairing dialog
        win = self.props.active_window
        if win and hasattr(win, "show_pairing_dialog"):
            win.show_pairing_dialog()
        else:
            logger.warning("Pairing dialog method not implemented in AurynkWindow.")

    def present_main_window(self):
        """Present the main window - called from tray icon."""
        logger.info("Activating application to show window")
        # Simply activate the application - do_activate will handle the window
        self.activate()

    def show_about_dialog(self):
        """Show the About dialog - called from tray icon."""
        from aurynk.ui.windows.about_window import AboutWindow

        # Ensure we have a window to be transient for
        win = self.props.active_window
        if not win:
            # Activate to create/show window first
            self.activate()
            win = self.props.active_window

        # Show about dialog
        if win:
            AboutWindow.show(win)
        else:
            logger.warning("Could not show About dialog - no window available")

    def quit(self):
        """Quit the application properly, closing all windows."""
        logger.info("Quitting application...")

        # Disconnect all connected devices before quitting
        try:
            logger.info("Disconnecting all devices...")
            result = subprocess.run(
                ["adb", "disconnect"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                logger.info("✓ All devices disconnected")
            else:
                logger.debug(f"ADB disconnect output: {result.stdout}")
        except Exception as e:
            logger.warning(f"Error disconnecting devices on quit: {e}")

        # Stop device monitor
        try:
            self.device_monitor.stop()
        except Exception as e:
            logger.debug(f"Error stopping device monitor: {e}")

        # Signal the tray command listener thread (if running) to stop.
        try:
            self._stop_tray_listener = True
        except Exception:
            pass
        # Close all windows
        for window in self.get_windows():
            window.destroy()
        # Best-effort: remove the app socket if it exists so the tray helper doesn't hang
        try:
            app_sock = "/tmp/aurynk_app.sock"
            if os.path.exists(app_sock):
                try:
                    # Attempt to wake the listener if it's blocked in accept
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                        try:
                            s.connect(app_sock)
                        except Exception:
                            pass
                except Exception:
                    pass
                os.unlink(app_sock)
        except Exception:
            pass
        # Quit the application
        super().quit()

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)
        self._apply_theme()
        self._load_gresource()
        start_tray_helper()
        # Expose a convenience method on the app instance so windows can call
        # `app.send_status_to_tray()` without importing the tray controller.
        from aurynk.services.tray_service import send_status_to_tray

        # create a small wrapper that binds the app instance
        self.send_status_to_tray = lambda status=None: send_status_to_tray(self, status)
        # Send initial device status to tray so menu is populated
        # Use the bound helper to send the initial status
        self.send_status_to_tray()

    def _apply_theme(self):
        """Apply the theme from settings."""
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        theme = settings.get("app", "theme", "system")

        style_manager = Adw.StyleManager.get_default()

        if theme == "light":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
        elif theme == "dark":
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:  # system
            style_manager.set_color_scheme(Adw.ColorScheme.DEFAULT)

        logger.info(f"Applied theme: {theme}")

    def do_activate(self):
        """Called when the application is activated (main entry point or from tray)."""
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        start_minimized = settings.get("app", "start_minimized", False)

        # Get or create the main window
        win = self.props.active_window
        if not win:
            logger.info("Creating new window")
            win = AurynkWindow(application=self)
        else:
            logger.debug(f"Window exists, visible: {win.get_visible()}")

        if self._first_activation:
            # On first activation, only show window if not start_minimized
            if not start_minimized:
                win.present()
            else:
                logger.info(
                    "Start Minimized to Tray is enabled; not showing main window on startup."
                )
            self._first_activation = False
        else:
            # On subsequent activations (e.g., from tray), always show window
            win.present()

    def _load_gresource(self):
        """Load the compiled GResource file."""
        resource = None
        candidates = [
            # Running from source (development)
            os.path.join(os.getcwd(), "data", "io.github.IshuSinghSE.aurynk.gresource"),
            os.path.join(
                os.path.dirname(__file__), "..", "data", "io.github.IshuSinghSE.aurynk.gresource"
            ),
            # Installed system-wide
            "/usr/share/aurynk/io.github.IshuSinghSE.aurynk.gresource",
            # Flatpak installation
            "/app/share/aurynk/io.github.IshuSinghSE.aurynk.gresource",
        ]

        for path in candidates:
            try:
                if path and os.path.exists(path):
                    resource = Gio.Resource.load(path)
                    Gio.Resource._register(resource)
                    from gi.repository import Gdk, Gtk

                    Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_resource_path(
                        "/io/github/IshuSinghSE/aurynk/icons"
                    )
                    logger.info(f"Loaded GResource from: {path}")
                    break

            except Exception as e:
                logger.warning(f"Failed to load GResource from {path}: {e}")

        if resource is None:
            logger.warning("Could not load GResource file. Some assets may be missing.")

    # Tray communication is now handled by tray_controller. Remove local send_tray_command.


def main(argv=None):
    """Main entry point for the application."""
    if argv is None:
        argv = sys.argv
    app = AurynkApp()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
