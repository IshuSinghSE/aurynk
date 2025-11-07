#!/usr/bin/env python3
import os
import socket
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AyatanaAppIndicator3", "0.1")

from gi.repository import AyatanaAppIndicator3 as AppIndicator
from gi.repository import Gtk
import signal
import sys

APP_ID = "aurynk-indicator"
ICON_NAME = "io.github.IshuSinghSE.aurynk.tray"  # Icon theme name for tray icon
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
        # Static items
        menu.append(Gtk.SeparatorMenuItem())
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

    def on_show(self, _):
        self.send_command_to_app("show")

    def on_quit(self, _):
        # Best-effort: notify the app via socket, then quit our own loop.
        self.send_command_to_app("quit")
        # If IPC fails for any reason, try to signal the parent app process
        # (pid passed via environment variable) as a fallback.
        try:
            pid_str = os.environ.get("AURYNK_APP_PID")
            if pid_str:
                pid = int(pid_str)
                try:
                    # Send SIGTERM to the app process as a fallback to request shutdown
                    os.kill(pid, signal.SIGTERM)
                except Exception:
                    pass
        except Exception:
            pass
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
                        # Ignore legacy single-device logic
                        pass
                conn.close()
        except Exception as e:
            print(f"[Tray] Socket listen error: {e}")

    def update_device_menu(self, devices):
        # Create a new menu to avoid issues with destroyed/invalid menu
        new_menu = Gtk.Menu()
        # Insert device submenus for each device
        if devices:
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
                new_menu.append(device_label)
        else:
            # Show placeholder if no devices
            placeholder = Gtk.MenuItem(label="No devices found")
            placeholder.set_sensitive(False)
            new_menu.append(placeholder)

        # Add static items once after device submenus
        new_menu.append(Gtk.SeparatorMenuItem())
        pair_item = Gtk.MenuItem(label="Pair New Device")
        pair_item.connect("activate", self.on_pair_new)
        new_menu.append(pair_item)

        show_item = Gtk.MenuItem(label="Show Window")
        show_item.connect("activate", self.on_show)
        new_menu.append(show_item)

        quit_item = Gtk.MenuItem(label="Quit Aurynk")
        quit_item.connect("activate", self.on_quit)
        new_menu.append(quit_item)

        new_menu.show_all()
        # Replace the menu and set it on the indicator
        self.menu = new_menu
        self.indicator.set_menu(self.menu)

    def on_connect_device(self, _, device):
        self.send_command_to_app(f"connect:{device.get('address')}")

    def on_disconnect_device(self, _, device):
        self.send_command_to_app(f"disconnect:{device.get('address')}")

    def on_mirror_device(self, _, device):
        self.send_command_to_app(f"mirror:{device.get('address')}")

    def on_unpair_device(self, _, device):
        self.send_command_to_app(f"unpair:{device.get('address')}")


if __name__ == "__main__":
    helper = TrayHelper()

    def _cleanup_and_quit(signum, frame):
        try:
            if os.path.exists(TRAY_SOCKET):
                os.unlink(TRAY_SOCKET)
        except Exception:
            pass
        try:
            # ensure Gtk main loop quits
            Gtk.main_quit()
        except Exception:
            pass
        # also exit the process
        sys.exit(0)

    # handle SIGINT/SIGTERM gracefully
    signal.signal(signal.SIGINT, _cleanup_and_quit)
    signal.signal(signal.SIGTERM, _cleanup_and_quit)

    try:
        Gtk.main()
    finally:
        # final cleanup
        try:
            if os.path.exists(TRAY_SOCKET):
                os.unlink(TRAY_SOCKET)
        except Exception:
            pass
