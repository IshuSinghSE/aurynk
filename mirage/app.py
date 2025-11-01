#!/usr/bin/env python3
"""Main application class for Mirage."""

import sys
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from mirage.main_window import MirageWindow


class MirageApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.yourdomain.mirage",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_startup(self):
        """Called once when the application starts."""
        Adw.Application.do_startup(self)
        self._load_gresource()

    def do_activate(self):
        """Called when the application is activated (main entry point)."""
        # Get or create the main window
        win = self.props.active_window
        if not win:
            win = MirageWindow(application=self)
        win.present()

    def _load_gresource(self):
        """Load the compiled GResource file."""
        resource = None
        candidates = [
            # Running from source (development)
            os.path.join(os.getcwd(), "data", "com.yourdomain.mirage.gresource"),
            os.path.join(
                os.path.dirname(__file__), "..", "data", "com.yourdomain.mirage.gresource"
            ),
            # Installed system-wide
            "/usr/share/mirage/com.yourdomain.mirage.gresource",
            # Flatpak installation
            "/app/share/mirage/com.yourdomain.mirage.gresource",
        ]

        for path in candidates:
            try:
                if path and os.path.exists(path):
                    resource = Gio.Resource.load(path)
                    Gio.Resource._register(resource)
                    print(f"✓ Loaded GResource from: {path}")
                    break
            except Exception as e:
                print(f"✗ Failed to load GResource from {path}: {e}")

        if resource is None:
            print("⚠ Warning: Could not load GResource file. Some assets may be missing.")


def main(argv):
    """Main entry point for the application."""
    app = MirageApp()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
