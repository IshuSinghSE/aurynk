import os
import xml.etree.ElementTree as ET
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import gi

from aurynk.i18n import _

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


from gi.repository import Adw, Gtk

from aurynk import __version__

_METAINFO_NAME = "io.github.IshuSinghSE.aurynk.metainfo.xml"


def _python_pkg_version_line(label: str, dist_names: tuple[str, ...]) -> str:
    """Resolve PyPI / distro package version via importlib.metadata (qrcode has no __version__)."""
    for dist in dist_names:
        try:
            return f"{label}: {version(dist)}"
        except PackageNotFoundError:
            continue
    if label == "PyGObject":
        try:
            import gi

            return f"PyGObject: {gi.__version__}"
        except Exception:
            pass
    return f"{label}: Not found"


def _xml_local_name(tag: str) -> str:
    return tag.split("}", maxsplit=1)[-1] if "}" in tag else tag


def _find_metainfo_path() -> Path | None:
    """Resolve installed or source-tree AppStream metainfo (CHANGELOG-derived <releases>)."""
    candidates: list[Path] = []
    candidates.append(Path("/app/share/metainfo") / _METAINFO_NAME)
    snap = os.environ.get("SNAP")
    if snap:
        candidates.append(Path(snap) / "usr" / "share" / "metainfo" / _METAINFO_NAME)
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidates.append(parent / "data" / _METAINFO_NAME)
    for root in (Path("/usr/share"), Path("/usr/local/share")):
        candidates.append(root / "metainfo" / _METAINFO_NAME)
    xdg_home = os.environ.get("XDG_DATA_HOME")
    if xdg_home:
        candidates.append(Path(xdg_home) / "metainfo" / _METAINFO_NAME)
    for part in os.environ.get("XDG_DATA_DIRS", "").split(":"):
        if part.strip():
            candidates.append(Path(part) / "metainfo" / _METAINFO_NAME)
    for path in candidates:
        if path.is_file():
            return path
    return None


def _release_notes_xml_from_metainfo(version: str) -> str | None:
    """Return AppStream-style XML fragment for Adw.AboutWindow.set_release_notes (current version)."""
    path = _find_metainfo_path()
    if path is None:
        return None
    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except (ET.ParseError, OSError):
        return None

    releases_el = None
    for child in root:
        if _xml_local_name(child.tag) == "releases":
            releases_el = child
            break
    if releases_el is None:
        return None

    release_el = None
    for rel in releases_el:
        if _xml_local_name(rel.tag) != "release":
            continue
        if rel.get("version") == version:
            release_el = rel
            break
    if release_el is None:
        for rel in releases_el:
            if _xml_local_name(rel.tag) == "release":
                release_el = rel
                break
    if release_el is None:
        return None

    desc_el = None
    for child in release_el:
        if _xml_local_name(child.tag) == "description":
            desc_el = child
            break
    if desc_el is None:
        return None

    chunks: list[str] = []
    for child in list(desc_el):
        try:
            chunks.append(ET.tostring(child, encoding="unicode", method="xml"))
        except Exception:
            continue
    out = "".join(chunks).strip()
    return out or None


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
            license_type=Gtk.License.GPL_3_0,
            developers=["IshuSinghSE <ishu.111636@yahoo.com>"],
            artists=["IshuSinghSE"],
            comments=_(
                "Android Device Manager for Linux with wireless pairing and mirroring support"
            ),
        )

        # Add useful links
        about.add_link(_("Documentation"), "https://github.com/IshuSinghSE/aurynk/wiki")
        about.add_link(
            _("Changelog"), "https://github.com/IshuSinghSE/aurynk/blob/main/CHANGELOG.md"
        )
        about.add_link(_("Source Code"), "https://github.com/IshuSinghSE/aurynk")
        about.add_link(_("Report an Issue"), "https://github.com/IshuSinghSE/aurynk/issues/new")
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
            about.set_debug_info_filename("aurynk-debug-info.txt")

        # "What's new" expects AppStream subset XML (same shape as <release><description> in metainfo).
        notes = _release_notes_xml_from_metainfo(__version__)
        if not notes:
            notes = "<p>{0}</p>".format(
                _(
                    "Release notes are unavailable (metainfo not found). See the Changelog link above."
                )
            )
        about.set_release_notes(notes)

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
    from aurynk.utils.settings import SettingsManager

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

    settings = SettingsManager()

    # Get scrcpy version
    try:
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
    info_lines.append(_python_pkg_version_line("PyGObject", ("PyGObject",)))
    info_lines.append(_python_pkg_version_line("zeroconf", ("zeroconf",)))
    info_lines.append(_python_pkg_version_line("Pillow", ("pillow", "Pillow")))
    info_lines.append(_python_pkg_version_line("qrcode", ("qrcode",)))
    info_lines.append(_python_pkg_version_line("pyudev", ("pyudev",)))

    # === Environment Variables ===
    info_lines.append("\n=== Environment Variables ===")
    if "LANG" in os.environ:
        info_lines.append(f"- LANG: {os.environ['LANG']}")
    else:
        info_lines.append("- LANG: (unset)")
    for env in sorted(os.environ):
        if env.startswith(("GTK_", "ADB_", "ANDROID_")):
            info_lines.append(f"- {env}: {os.environ[env]}")

    # === Settings ===
    info_lines.append("\n=== Settings ===")
    def _append_setting_lines(prefix: str, value, indent: int = 0) -> None:
        pad = "  " * indent
        if isinstance(value, dict):
            if prefix:
                info_lines.append(f"{pad}- {prefix}:")
            for child_key, child_value in value.items():
                _append_setting_lines(child_key, child_value, indent + (1 if prefix else 0))
        else:
            info_lines.append(f"{pad}- {prefix}: {value}")

    for key, value in settings.get_all().items():
        _append_setting_lines(key, value)

    return "\n".join(info_lines)
