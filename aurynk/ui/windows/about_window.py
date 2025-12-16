"""
About Window for Aurynk
Displays application information, credits, and links following GNOME HIG.
"""

import gi

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

        about.present()
