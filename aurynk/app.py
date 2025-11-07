#!/usr/bin/env python3
import os
import socket
import subprocess
import sys
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


from gi.repository import Adw, Gio

from aurynk.lib.tray_controller import tray_command_listener
from aurynk.windows.main_window import AurynkWindow


def start_tray_helper():
    """Start the tray helper process if not already running."""
    tray_socket = "/tmp/aurynk_tray.sock"
    # Only reuse the tray helper if the tray socket exists and is connectable
    if os.path.exists(tray_socket):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(tray_socket)
            print("[AurynkApp] Tray helper already running. Reusing existing instance.")
            return True
        except Exception:
            try:
                os.unlink(tray_socket)
                print("[AurynkApp] Removed stale tray socket.")
            except Exception as e:
                print(f"[AurynkApp] Could not remove stale tray socket: {e}")
    # Start new tray helper
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "aurynk_tray.py")
    )
    subprocess.Popen(["python3", script_path])


class AurynkApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="io.github.IshuSinghSE.aurynk",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        # Start tray command listener thread from tray_controller
        self.tray_listener_thread = threading.Thread(
            target=tray_command_listener, args=(self,), daemon=True
        )
        self.tray_listener_thread.start()
        # Give the listener thread time to bind the socket
        import time

        time.sleep(0.1)

    def show_pair_dialog(self):
        """Show main window and open pairing dialog - called from tray icon."""
        # First, activate the app to show the window
        self.activate()
        # Then show the pairing dialog
        win = self.props.active_window
        if win and hasattr(win, "show_pairing_dialog"):
            win.show_pairing_dialog()
        else:
            print("[AurynkApp] Pairing dialog method not implemented in AurynkWindow.")

    def present_main_window(self):
        """Present the main window - called from tray icon."""
        print("[AurynkApp] Activating application to show window")
        # Simply activate the application - do_activate will handle the window
        self.activate()

    def quit(self):
        """Quit the application properly, closing all windows."""
        print("[AurynkApp] Quitting application...")
        # Close all windows
        for window in self.get_windows():
            window.destroy()
        # Quit the application
        super().quit()

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)
        self._load_gresource()
        start_tray_helper()
        # Send initial device status to tray so menu is populated
        from aurynk.lib.tray_controller import send_status_to_tray

        send_status_to_tray(self)

    def do_activate(self):
        """Called when the application is activated (main entry point or from tray)."""
        # Get or create the main window
        win = self.props.active_window
        if not win:
            print("[AurynkApp] Creating new window")
            win = AurynkWindow(application=self)
        else:
            print(f"[AurynkApp] Window exists, visible: {win.get_visible()}")

        # present() will:
        # 1. Show the window if hidden (un-hide)
        # 2. Center it if first time shown
        # 3. Bring to front and give focus
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
                    print(f"✓ Loaded GResource from: {path}")
                    break

            except Exception as e:
                print(f"✗ Failed to load GResource from {path}: {e}")

        if resource is None:
            print("⚠ Warning: Could not load GResource file. Some assets may be missing.")

    # Tray communication is now handled by tray_controller. Remove local send_tray_command.


def main(argv):
    """Main entry point for the application."""
    app = AurynkApp()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
