#!/usr/bin/env python3
import os
import socket
import subprocess
import sys
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from aurynk.windows.main_window import AurynkWindow  # noqa: E402


def start_tray_helper():
    """Start the tray helper process if not already running."""
    socket_path = "/tmp/aurynk_tray.sock"
    # Try to connect to the tray helper; if successful, reuse it
    if os.path.exists(socket_path):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(socket_path)
            print("[AurynkApp] Tray helper already running. Reusing existing instance.")
            return True
        except Exception:
            # Socket exists but not connectable: remove and start new helper
            try:
                os.unlink(socket_path)
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
            application_id="com.aurynk.aurynk",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

        # Start tray command listener thread
        self.tray_listener_thread = threading.Thread(target=self.tray_command_listener, daemon=True)
        self.tray_listener_thread.start()

    def tray_command_listener(self):
        """Listen for commands from the tray helper (e.g., show, quit)."""
        SOCKET_PATH = "/tmp/aurynk_app.sock"
        # Remove stale socket if exists
        if os.path.exists(SOCKET_PATH):
            try:
                os.unlink(SOCKET_PATH)
            except Exception:
                pass
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(SOCKET_PATH)
        server.listen(1)
        while True:
            try:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if data:
                    msg = data.decode()
                    if msg == "show":
                        # Present the main window
                        GLib.idle_add(self.present_main_window)
                    elif msg == "quit":
                        print("[AurynkApp] Received quit from tray. Exiting.")
                        GLib.idle_add(self.quit)
                conn.close()
            except Exception as e:
                print(f"[AurynkApp] Tray command listener error: {e}")

    def present_main_window(self):
        win = self.props.active_window
        if not win:
            win = AurynkWindow(application=self)
        win.present()

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)
        self._load_gresource()
        start_tray_helper()

    def do_activate(self):
        """Called when the application is activated (main entry point)."""
        # Get or create the main window
        win = self.props.active_window
        if not win:
            win = AurynkWindow(application=self)
        win.present()

    def _load_gresource(self):
        """Load the compiled GResource file."""
        resource = None
        candidates = [
            # Running from source (development)
            os.path.join(os.getcwd(), "data", "com.aurynk.aurynk.gresource"),
            os.path.join(os.path.dirname(__file__), "..", "data", "com.aurynk.aurynk.gresource"),
            # Installed system-wide
            "/usr/share/aurynk/com.aurynk.aurynk.gresource",
            # Flatpak installation
            "/app/share/aurynk/com.aurynk.aurynk.gresource",
        ]

        for path in candidates:
            try:
                if path and os.path.exists(path):
                    resource = Gio.Resource.load(path)
                    Gio.Resource._register(resource)
                    from gi.repository import Gdk, Gtk

                    Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_resource_path(
                        "/com/aurynk/aurynk/icons"
                    )
                    print(f"✓ Loaded GResource from: {path}")
                    break

            except Exception as e:
                print(f"✗ Failed to load GResource from {path}: {e}")

        if resource is None:
            print("⚠ Warning: Could not load GResource file. Some assets may be missing.")

    # --- Tray Helper Communication ---

    def send_tray_command(self, command: str):
        """Send a command to the tray helper process via Unix socket."""
        SOCKET_PATH = "/tmp/aurynk_tray.sock"
        for attempt in range(5):
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(SOCKET_PATH)
                    s.sendall(command.encode())
                return
            except FileNotFoundError:
                time.sleep(0.5)  # Wait for the tray helper to start
            except Exception as e:
                print(f"[AurynkApp] Could not send tray command '{command}': {e}")
                return
        print("[AurynkApp] Tray helper socket not available after retries.")

    # Example usage:
    # self.send_tray_command("connected:Redmi Note 14 5G")
    # self.send_tray_command("disconnected")
    # self.send_tray_command("quit")


def main(argv):
    """Main entry point for the application."""
    app = AurynkApp()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
