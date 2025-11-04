#!/usr/bin/env python3
import os
import socket
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import AyatanaAppIndicator3 as AppIndicator
from gi.repository import Gtk

APP_ID = "aurynk-indicator"
ICON_NAME = "org.aurynk.aurynk"
SOCKET_PATH = "/tmp/aurynk_tray.sock"


class TrayHelper:
    def __init__(self):
        self.indicator = AppIndicator.Indicator.new(
            APP_ID, ICON_NAME, AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.menu = self.build_menu()
        self.indicator.set_menu(self.menu)
        self.listen_thread = threading.Thread(target=self.listen_socket, daemon=True)
        self.listen_thread.start()

    def build_menu(self):
        menu = Gtk.Menu()

        # Device submenu for already paired device
        device_menu = Gtk.Menu()
        self.connect_item = Gtk.MenuItem(label="Connect")
        self.connect_item.connect("activate", self.on_connect)
        device_menu.append(self.connect_item)

        self.disconnect_item = Gtk.MenuItem(label="Disconnect")
        self.disconnect_item.connect("activate", self.on_disconnect)
        device_menu.append(self.disconnect_item)

        self.mirror_item = Gtk.MenuItem(label="Start Mirroring")
        self.mirror_item.connect("activate", self.on_mirror)
        device_menu.append(self.mirror_item)

        device_menu.append(Gtk.SeparatorMenuItem())

        self.unpair_item = Gtk.MenuItem(label="Unpair")
        self.unpair_item.connect("activate", self.on_unpair)
        device_menu.append(self.unpair_item)

        # Device submenu root
        self.device_label = Gtk.MenuItem(label="Redmi Note 14 5G")
        self.device_label.set_submenu(device_menu)
        menu.append(self.device_label)

        menu.append(Gtk.SeparatorMenuItem())
        # Pair new device
        pair_item = Gtk.MenuItem(label="Pair New Device")
        pair_item.connect("activate", self.on_pair_new)
        menu.append(pair_item)

        show_item = Gtk.MenuItem(label="Show Window")
        show_item.connect("activate", self.on_show)
        menu.append(show_item)

        quit_item = Gtk.MenuItem(label="Quit Aurynk")
        quit_item.connect("activate", self.on_quit)
        menu.append(quit_item)

        menu.show_all()
        return menu

    # --- Menu action handlers ---
    def on_pair_new(self, _):
        self.send_command_to_app("pair_new")

    def on_connect(self, _):
        self.send_command_to_app("connect")

    def on_disconnect(self, _):
        self.send_command_to_app("disconnect")

    def on_mirror(self, _):
        self.send_command_to_app("mirror")

    def on_unpair(self, _):
        self.send_command_to_app("unpair")

    def on_show(self, _):
        self.send_command_to_app("show")

    def on_quit(self, _):
        self.send_command_to_app("quit")
        Gtk.main_quit()

    def send_command_to_app(self, command):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(SOCKET_PATH)
                s.sendall(command.encode())
        except Exception as e:
            print(f"[Tray] Could not send command '{command}': {e}")

    def listen_socket(self):
        # Listen for state updates from the main app (optional, for dynamic menu)
        try:
            if os.path.exists(SOCKET_PATH):
                os.unlink(SOCKET_PATH)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(SOCKET_PATH)
            server.listen(1)
            while True:
                conn, _ = server.accept()
                data = conn.recv(1024)
                if data:
                    msg = data.decode()
                    # Example: update menu based on msg
                    if msg.startswith("connected:"):
                        device = msg.split(":", 1)[1]
                        self.connect_item.set_sensitive(False)
                        self.disconnect_item.set_sensitive(True)
                        self.disconnect_item.set_label(f"Disconnect {device}")
                        self.mirror_item.set_sensitive(True)
                    elif msg == "disconnected":
                        self.connect_item.set_sensitive(True)
                        self.disconnect_item.set_sensitive(False)
                        self.disconnect_item.set_label("Disconnect")
                        self.mirror_item.set_sensitive(False)
                conn.close()
        except Exception as e:
            print(f"[Tray] Socket listen error: {e}")


if __name__ == "__main__":
    TrayHelper()
    Gtk.main()
