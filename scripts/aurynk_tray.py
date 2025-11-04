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
TRAY_SOCKET = "/tmp/aurynk_tray.sock"
APP_SOCKET = "/tmp/aurynk_app.sock"


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
                s.connect(APP_SOCKET)
                s.sendall(command.encode())
        except Exception as e:
            print(f"[Tray] Could not send command '{command}': {e}")

    def listen_socket(self):
        # Listen for state updates from the main app (for dynamic menu)
        import json

        try:
            if os.path.exists(TRAY_SOCKET):
                os.unlink(TRAY_SOCKET)
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(TRAY_SOCKET)
            server.listen(1)
            while True:
                conn, _ = server.accept()
                data = conn.recv(4096)
                if data:
                    msg = data.decode()
                    try:
                        status = json.loads(msg)
                        if "devices" in status:
                            self.update_device_menu(status["devices"])
                        else:
                            self.update_device_menu([])
                    except Exception:
                        # Fallback to legacy single-device logic
                        if msg.startswith("connected:"):
                            device = msg.split(":", 1)[1]
                            self.connect_item.set_sensitive(False)
                            self.connect_item.set_label("Connect")
                            self.disconnect_item.set_sensitive(True)
                            self.disconnect_item.set_label(f"Disconnect {device}")
                            self.mirror_item.set_sensitive(True)
                            self.mirror_item.set_label("Start Mirroring")
                        elif msg == "disconnected":
                            self.connect_item.set_sensitive(True)
                            self.connect_item.set_label("Connect")
                            self.disconnect_item.set_sensitive(False)
                            self.disconnect_item.set_label("Disconnect")
                            self.mirror_item.set_sensitive(False)
                            self.mirror_item.set_label("Start Mirroring")
                conn.close()
        except Exception as e:
            print(f"[Tray] Socket listen error: {e}")

    def update_device_menu(self, devices):
        # Remove all device submenus
        menu = self.menu
        # Remove all device submenus (keep static items)
        for item in list(menu):
            if hasattr(item, "get_submenu") and item.get_submenu():
                menu.remove(item)
        # Insert device submenus for each device
        for device in devices:
            device_menu = Gtk.Menu()
            connect_item = Gtk.MenuItem(label="Connect")
            connect_item.set_sensitive(not device.get("connected", False))
            connect_item.connect("activate", self.on_connect_device, device)
            device_menu.append(connect_item)

            disconnect_item = Gtk.MenuItem(label="Disconnect")
            disconnect_item.set_sensitive(device.get("connected", False))
            disconnect_item.connect("activate", self.on_disconnect_device, device)
            device_menu.append(disconnect_item)

            mirror_item = Gtk.MenuItem(label="Start Mirroring")
            mirror_item.set_sensitive(device.get("connected", False))
            mirror_item.connect("activate", self.on_mirror_device, device)
            device_menu.append(mirror_item)

            device_menu.append(Gtk.SeparatorMenuItem())

            unpair_item = Gtk.MenuItem(label="Unpair")
            unpair_item.connect("activate", self.on_unpair_device, device)
            device_menu.append(unpair_item)

            device_label = Gtk.MenuItem(label=device.get("name", "Unknown Device"))
            device_label.set_submenu(device_menu)
            menu.prepend(device_label)

        menu.show_all()

    def on_connect_device(self, _, device):
        self.send_command_to_app(f"connect:{device.get('address')}")

    def on_disconnect_device(self, _, device):
        self.send_command_to_app(f"disconnect:{device.get('address')}")

    def on_mirror_device(self, _, device):
        self.send_command_to_app(f"mirror:{device.get('address')}")

    def on_unpair_device(self, _, device):
        self.send_command_to_app(f"unpair:{device.get('address')}")


if __name__ == "__main__":
    TrayHelper()
    Gtk.main()
