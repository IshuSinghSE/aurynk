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

    # Forward Audio
    forward_audio_row = Adw.ActionRow()
    forward_audio_row.set_title(_("Forward Audio"))

    forward_audio_switch = Gtk.Switch()
    forward_audio_switch.set_valign(Gtk.Align.CENTER)
    forward_audio_switch.connect("notify::active", dummy_handler)

    forward_audio_row.add_suffix(forward_audio_switch)
    forward_audio_row.set_activatable_widget(forward_audio_switch)
    group.add(forward_audio_row)

    # Turn Screen Off
    turn_screen_off_row = Adw.ActionRow()
    turn_screen_off_row.set_title(_("Turn Screen Off"))

    turn_screen_off_switch = Gtk.Switch()
    turn_screen_off_switch.set_valign(Gtk.Align.CENTER)
    turn_screen_off_switch.connect("notify::active", dummy_handler)

    turn_screen_off_row.add_suffix(turn_screen_off_switch)
    turn_screen_off_row.set_activatable_widget(turn_screen_off_switch)
    group.add(turn_screen_off_row)

    return group
