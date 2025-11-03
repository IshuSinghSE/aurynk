#!/usr/bin/env python3
"""Main application class for Aurynk."""

import sys
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

from aurynk.windows.main_window import AurynkWindow


class AurynkApp(Adw.Application):
    """Main application class."""

    def __init__(self):
        super().__init__(
            application_id="com.aurynk.aurynk",
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
            win = AurynkWindow(application=self)
        win.present()

    def _load_gresource(self):
        """Load the compiled GResource file."""
        resource = None
        candidates = [
            # Running from source (development)
            os.path.join(os.getcwd(), "data", "com.aurynk.aurynk.gresource"),
            os.path.join(
                os.path.dirname(__file__), "..", "data", "com.aurynk.aurynk.gresource"
            ),
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
                    from gi.repository import Gtk, Gdk
                    Gtk.IconTheme.get_for_display(Gdk.Display.get_default()).add_resource_path("/com/aurynk/aurynk/icons")
                    print(f"✓ Loaded GResource from: {path}")
                    break
            except Exception as e:
                print(f"✗ Failed to load GResource from {path}: {e}")

        if resource is None:
            print("⚠ Warning: Could not load GResource file. Some assets may be missing.")


def main(argv):
    """Main entry point for the application."""
    app = AurynkApp()
    return app.run(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
