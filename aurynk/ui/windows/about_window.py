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
    """Get debug information including ADB and scrcpy versions.

    Returns:
        str: Formatted debug information or empty string if unavailable
    """
    import subprocess

    from aurynk.utils.adb_utils import get_adb_path

    info_lines = []

    # Get Aurynk version
    info_lines.append(f"Aurynk: {__version__}")

    # Get ADB version
    try:
        adb_path = get_adb_path()
        result = subprocess.run(
            [adb_path, "version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # ADB output format: "Android Debug Bridge version X.X.XX"
            version_line = result.stdout.strip().split('\n')[0]
            info_lines.append(f"ADB: {version_line}")
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
            [scrcpy_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # scrcpy output format: "scrcpy X.X.X <url>"
            version_line = result.stderr.strip().split('\n')[0] if result.stderr else result.stdout.strip().split('\n')[0]
            info_lines.append(f"scrcpy: {version_line}")
        else:
            info_lines.append("scrcpy: Not found or error")
    except Exception as e:
        info_lines.append(f"scrcpy: Error - {str(e)}")

    return "\n".join(info_lines)
