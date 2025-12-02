import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk


def create_session_group() -> Adw.PreferencesGroup:
    """
    Creates a Libadwaita Preferences Group for 'Session Options'.

    Returns:
        Adw.PreferencesGroup: The configured preferences group.
    """
    group = Adw.PreferencesGroup()
    group.set_title(_("Session Options"))

    # Dummy handler for signals
    def dummy_handler(*args):
        pass

    # Helper to add a switch row
    def add_switch_row(title, subtitle=None):
        row = Adw.ActionRow()
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)

        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("notify::active", dummy_handler)

        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        group.add(row)

    # Helper to add an action button row
    def add_button_row(title, icon_name, subtitle=None):
        row = Adw.ActionRow()
        row.set_title(title)
        if subtitle:
            row.set_subtitle(subtitle)

        button = Gtk.Button()
        button.set_icon_name(icon_name)
        button.set_valign(Gtk.Align.CENTER)
        button.add_css_class("flat")
        button.connect("clicked", dummy_handler)

        row.add_suffix(button)
        # For buttons, we might not want the whole row to be activatable
        # unless it triggers the button.
        # But 'activatable_widget' is for switches/checks mostly.
        # We can just leave it as is.
        group.add(row)

    # --- Toggles ---
    add_switch_row(_("Forward Audio"))
    add_switch_row(_("Turn Screen Off"))
    add_switch_row(_("Stay Awake"), _("Keep device screen on"))
    add_switch_row(_("Fullscreen"), _("Start in fullscreen mode"))
    add_switch_row(_("Show Touches"), _("Visual feedback for touches"))
    add_switch_row(_("Always on Top"), _("Keep window above others"))
    add_switch_row(_("Record Session"), _("Record mirroring session"))

    # --- Actions ---
    add_button_row(_("Volume Up"), "audio-volume-high-symbolic", _("Increase device volume"))
    add_button_row(_("Volume Down"), "audio-volume-low-symbolic", _("Decrease device volume"))
    add_button_row(_("Take Screenshot"), "camera-photo-symbolic", _("Capture device screen"))

    return group
