"""PIN entry widget for digit-by-digit input."""

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gtk


class PinEntryBox(Gtk.Box):
    """Custom widget for PIN-style digit entry with separate boxes."""

    def __init__(self, num_digits, label_text, tooltip_text=None):
        """
        Initialize PIN entry widget.

        Args:
            num_digits: Number of digit boxes to display
            label_text: Label text to show above the digit boxes
            tooltip_text: Optional tooltip for each digit box
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.num_digits = num_digits
        self.entries = []

        # Label
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        label.get_style_context().add_class("caption-heading")
        self.append(label)

        # Box for digit entries
        digits_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        digits_box.set_halign(Gtk.Align.CENTER)

        for i in range(num_digits):
            entry = Gtk.Entry()
            entry.set_max_length(1)
            entry.set_width_chars(2)
            entry.set_alignment(0.5)
            entry.set_input_purpose(Gtk.InputPurpose.DIGITS)
            entry.get_style_context().add_class("pin-entry")

            # Connect signals for auto-advance
            entry.connect("changed", self._on_digit_changed, i)

            # Use EventControllerKey with CAPTURE phase to intercept keys before Entry processes them
            key_controller = Gtk.EventControllerKey()
            key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            key_controller.connect("key-pressed", self._on_key_pressed, i)
            entry.add_controller(key_controller)

            if tooltip_text:
                entry.set_tooltip_text(tooltip_text)

            self.entries.append(entry)
            digits_box.append(entry)

        self.append(digits_box)

    def _on_digit_changed(self, entry, index):
        """Auto-advance to next entry when digit is entered."""
        text = entry.get_text()
        # Only keep digits
        if text and not text.isdigit():
            entry.set_text("")
            return

        # Move to next entry if digit entered
        if text and index < self.num_digits - 1:
            self.entries[index + 1].grab_focus()

    def _on_key_pressed(self, controller, keyval, keycode, state, index):
        """Handle navigation keys (backspace, left, right) for PIN entry."""
        entry = self.entries[index]
        current_text = entry.get_text()

        # Use Gdk key constants
        if keyval == Gdk.KEY_BackSpace:
            if not current_text and index > 0:
                # Empty field, go to previous
                self.entries[index - 1].grab_focus()
                return True
            # Has text, let default backspace work but don't move
            return False

        # Left arrow: move to previous box
        elif keyval == Gdk.KEY_Left and index > 0:
            self.entries[index - 1].grab_focus()
            return True

        # Right arrow: move to next box
        elif keyval == Gdk.KEY_Right and index < self.num_digits - 1:
            self.entries[index + 1].grab_focus()
            return True

        return False

    def get_value(self):
        """Get the complete value from all entries."""
        return "".join(entry.get_text() for entry in self.entries)

    def set_value(self, value):
        """Set value across all entries."""
        value_str = str(value)
        for i, entry in enumerate(self.entries):
            if i < len(value_str):
                entry.set_text(value_str[i])
            else:
                entry.set_text("")

    def clear(self):
        """Clear all entries and focus the first one."""
        for entry in self.entries:
            entry.set_text("")
        if self.entries:
            self.entries[0].grab_focus()
