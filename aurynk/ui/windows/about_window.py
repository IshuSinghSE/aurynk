import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


from gi.repository import Adw

from aurynk import __version__


class AboutWindow:
    """About dialog for Aurynk application."""

    @staticmethod
    def show(parent):
        """
        Show the About dialog.

        Args:
            parent: The parent window (transient for)
        """
        about = Adw.AboutWindow(
            transient_for=parent,
            application_name="Aurynk",
            application_icon="io.github.IshuSinghSE.aurynk",
            developer_name="Ishu Singh",
            version=__version__,
            website="https://github.com/IshuSinghSE/aurynk",
            issue_url="https://github.com/IshuSinghSE/aurynk/issues",
            developers=["IshuSinghSE <ishu.111636@yahoo.com>"],
            artists=["IshuSinghSE"],
            comments=_(
                "Android Device Manager for Linux with wireless pairing and mirroring support"
            ),
        )

        # Add useful links
        about.add_link(_("Documentation"), "https://github.com/IshuSinghSE/aurynk/wiki")
        about.add_link(_("Source Code"), "https://github.com/IshuSinghSE/aurynk")
        about.add_link(_("Donate"), "https://github.com/sponsors/IshuSinghSE")

        # Credits for technologies used
        about.add_credit_section(
            _("Built with"),
            [
                "GTK4 https://gtk.org",
                "Libadwaita https://gnome.pages.gitlab.gnome.org/libadwaita/",
                "Scrcpy https://github.com/Genymobile/scrcpy",
                "Android Debug Bridge (ADB) https://developer.android.com/tools/adb",
            ],
        )

        # Credits for Python dependencies
        about.add_credit_section(
            _("Python Libraries"),
            [
                "PyGObject",
                "Zeroconf (mDNS discovery)",
                "Pillow (image processing)",
                "QRCode (pairing codes)",
            ],
        )

        # Additional acknowledgments
        about.add_acknowledgement_section(
            _("Special Thanks"),
            [
                "GNOME Community",
                "Scrcpy developers",
                "Android Open Source Project",
            ],
        )

        # Add debug information for troubleshooting
        debug_info = _get_debug_info()
        if debug_info:
            about.set_debug_info(debug_info)

        about.present()


def _get_debug_info():
    """Get comprehensive debug information for troubleshooting.

    Returns:
        str: Formatted debug information with system, dependency, and environment details
    """
    import os
    import platform
    import subprocess
    import sys

    from aurynk.utils.adb_utils import get_adb_path

    info_lines = []

    # === Application Info ===
    info_lines.append("=== Application ===")
    info_lines.append(f"Aurynk: {__version__}")

    # Detect installation method
    if os.path.exists("/.flatpak-info"):
        info_lines.append("Installation: Flatpak")
    elif os.environ.get("SNAP"):
        info_lines.append("Installation: Snap")
    else:
        info_lines.append("Installation: System/Manual")

    # === System Info ===
    info_lines.append("\n=== System ===")
    info_lines.append(f"OS: {platform.system()} {platform.release()}")

    # Get Linux distribution info
    try:
        with open("/etc/os-release") as f:
            os_info = {}
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os_info[key] = value.strip('"')
            distro_name = os_info.get("NAME", "Unknown")
            distro_version = os_info.get("VERSION", "")
            info_lines.append(f"Distribution: {distro_name} {distro_version}")
    except Exception:
        pass

    info_lines.append(f"Architecture: {platform.machine()}")
    info_lines.append(f"Python: {sys.version.split()[0]}")

    # === Desktop Environment ===
    info_lines.append("\n=== Desktop Environment ===")
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "Unknown")
    session_type = os.environ.get("XDG_SESSION_TYPE", "Unknown")
    info_lines.append(f"Desktop: {desktop}")
    info_lines.append(f"Session: {session_type}")

    # Get GTK version
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        gtk_version = (
            f"{Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}"
        )
        info_lines.append(f"GTK: {gtk_version}")
    except Exception:
        info_lines.append("GTK: Unknown")

    # Get libadwaita version
    try:
        import gi

        gi.require_version("Adw", "1")
        from gi.repository import Adw

        adw_version = (
            f"{Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}"
        )
        info_lines.append(f"Libadwaita: {adw_version}")
    except Exception:
        info_lines.append("Libadwaita: Unknown")

    # === Dependencies ===
    info_lines.append("\n=== Dependencies ===")

    # Get ADB version
    try:
        adb_path = get_adb_path()
        result = subprocess.run([adb_path, "version"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            info_lines.append(f"ADB: {version_line}")
            info_lines.append(f"ADB Path: {adb_path}")
        else:
            info_lines.append("ADB: Not found or error")
    except Exception as e:
        info_lines.append(f"ADB: Error - {str(e)}")

    # Get scrcpy version
    try:
        from aurynk.utils.settings import SettingsManager

        settings = SettingsManager()
        scrcpy_path = settings.get("scrcpy", "scrcpy_path", "").strip()
        if not scrcpy_path:
            import shutil

            scrcpy_path = shutil.which("scrcpy") or "scrcpy"

        result = subprocess.run(
            [scrcpy_path, "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version_line = (
                result.stderr.strip().split("\n")[0]
                if result.stderr
                else result.stdout.strip().split("\n")[0]
            )
            info_lines.append(f"scrcpy: {version_line}")
            info_lines.append(f"scrcpy Path: {scrcpy_path}")
        else:
            info_lines.append("scrcpy: Not found or error")
    except Exception as e:
        info_lines.append(f"scrcpy: Error - {str(e)}")

    # === Python Packages ===
    info_lines.append("\n=== Python Packages ===")
    packages = ["PyGObject", "zeroconf", "pillow", "qrcode", "pyudev"]
    for package in packages:
        try:
            if package == "PyGObject":
                import gi

                info_lines.append(f"PyGObject: {gi.__version__}")
            elif package == "zeroconf":
                import zeroconf

                info_lines.append(f"zeroconf: {zeroconf.__version__}")
            elif package == "pillow":
                import PIL

                info_lines.append(f"Pillow: {PIL.__version__}")
            elif package == "qrcode":
                import qrcode

                info_lines.append(f"qrcode: {qrcode.__version__}")
            elif package == "pyudev":
                import pyudev

                info_lines.append(f"pyudev: {pyudev.__version__}")
        except Exception:
            info_lines.append(f"{package}: Not found")

    return "\n".join(info_lines)
