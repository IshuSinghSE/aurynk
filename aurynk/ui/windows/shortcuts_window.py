"""Keyboard shortcuts window for scrcpy."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


def show_shortcuts_window(parent=None):
    """Show the keyboard shortcuts window."""
    builder = Gtk.Builder.new_from_resource("/io/github/IshuSinghSE/aurynk/ui/shortcuts_window.ui")
    window = builder.get_object("shortcuts_window")

    if parent:
        window.set_transient_for(parent)

    window.present()
    return window
