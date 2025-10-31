
#!/usr/bin/env python3
import sys
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio
Adw.init()

# Import UI modules
from ui.pairing_dialog import show_pairing_dialog
from ui.dashboard import build_dashboard_window



class MirageApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.example.mirage")

    def do_activate(self):
        resource = Gio.Resource.load("data/mirage.gresource")
        Gio.Resource._register(resource)
        win = Adw.ApplicationWindow(application=self, title="Mirage")
        win.set_icon_name("com.yourdomain.mirage")
        win.set_default_size(700, 520)

        # Build dashboard UI and get Add Device button
        content, add_btn = build_dashboard_window(self, win)
        win.set_content(content)
        add_btn.connect("clicked", lambda btn: show_pairing_dialog(win))
        win.present()

def main(argv):
    app = MirageApp()
    return app.run(argv)

if __name__ == "__main__":
    sys.exit(main(sys.argv))