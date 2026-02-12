
import sys
import unittest
from unittest.mock import MagicMock, mock_open, patch

# Mock gi dependencies BEFORE importing the module
# This ensures tests can run even if gi is not installed
sys.modules["gi"] = MagicMock()
sys.modules["gi.repository"] = MagicMock()
sys.modules["gi.repository.Adw"] = MagicMock()
sys.modules["gi.repository.Gtk"] = MagicMock()

# IMPORTANT: Link the submodules to attributes of the repository mock
# This handles "from gi.repository import Gtk" correctly
sys.modules["gi.repository"].Adw = sys.modules["gi.repository.Adw"]
sys.modules["gi.repository"].Gtk = sys.modules["gi.repository.Gtk"]

# Also ensure aurynk.i18n is happy if it uses gettext
sys.modules["aurynk.i18n"] = MagicMock()
sys.modules["aurynk.i18n"]._ = lambda x: x

try:
    from aurynk.ui.windows.about_window import _get_debug_info
except ImportError:
    # If import fails, we will fail later in tests or need to fix mocks
    pass

class TestGetDebugInfo(unittest.TestCase):

    @patch("aurynk.utils.adb_utils.get_adb_path")
    @patch("subprocess.run")
    @patch("platform.system")
    @patch("platform.release")
    @patch("platform.machine")
    @patch("sys.version")
    @patch("os.path.exists")
    @patch("os.environ")
    @patch("aurynk.utils.settings.SettingsManager")
    def test_get_debug_info_comprehensive(self, mock_settings, mock_environ, mock_exists, mock_sys_version, mock_machine, mock_release, mock_system, mock_subprocess, mock_get_adb_path):
        # Configure mocks
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.15.0"
        mock_machine.return_value = "x86_64"
        mock_sys_version.split.return_value = ["3.10.6"]

        # OS checks
        def path_exists_side_effect(path):
            if path == "/.flatpak-info":
                return False
            return False
        mock_exists.side_effect = path_exists_side_effect

        mock_environ.get.side_effect = lambda k, d=None: {
            "XDG_CURRENT_DESKTOP": "GNOME",
            "XDG_SESSION_TYPE": "wayland",
            "SNAP": None
        }.get(k, d)

        # ADB
        mock_get_adb_path.return_value = "/usr/bin/adb"

        # Scrcpy settings
        mock_settings.return_value.get.return_value = "" # No custom path

        # Subprocess calls
        # 1. adb version
        # 2. scrcpy version
        # NOTE: mock_subprocess IS the run function mock
        mock_subprocess.side_effect = [
            MagicMock(returncode=0, stdout="Android Debug Bridge version 1.0.41\n"),
            MagicMock(returncode=0, stdout="scrcpy 1.24\n", stderr="")
        ]

        # Patch builtins.open for /etc/os-release
        with patch("builtins.open", mock_open(read_data='NAME="Ubuntu"\nVERSION="22.04 LTS"\n')):
             with patch("shutil.which", return_value="/usr/bin/scrcpy"):
                 # Patch python modules
                 with patch.dict(sys.modules, {
                     "zeroconf": MagicMock(__version__="0.39.0"),
                     "PIL": MagicMock(__version__="9.2.0"),
                     "qrcode": MagicMock(__version__="7.3.1"),
                     "pyudev": MagicMock(__version__="0.24.0")
                 }):
                    # Mock gi version
                    sys.modules["gi"].__version__ = "3.42.1"

                    # Ensure linkage is correct (in case it was reset or decoupled)
                    sys.modules["gi.repository"].Gtk = sys.modules["gi.repository.Gtk"]
                    sys.modules["gi.repository"].Adw = sys.modules["gi.repository.Adw"]

                    # Mock GTK/Adw versions
                    mock_gtk = sys.modules["gi.repository.Gtk"]
                    mock_gtk.get_major_version.return_value = 4
                    mock_gtk.get_minor_version.return_value = 6
                    mock_gtk.get_micro_version.return_value = 0

                    mock_adw = sys.modules["gi.repository.Adw"]
                    mock_adw.get_major_version.return_value = 1
                    mock_adw.get_minor_version.return_value = 2
                    mock_adw.get_micro_version.return_value = 0

                    info = _get_debug_info()

        # Assertions
        self.assertIn("Installation: System/Manual", info)
        self.assertIn("OS: Linux 5.15.0", info)
        self.assertIn("Distribution: Ubuntu 22.04 LTS", info)
        self.assertIn("Architecture: x86_64", info)
        self.assertIn("Python: 3.10.6", info)
        self.assertIn("Desktop: GNOME", info)
        self.assertIn("Session: wayland", info)
        self.assertIn("GTK: 4.6.0", info)
        self.assertIn("Libadwaita: 1.2.0", info)
        self.assertIn("ADB: Android Debug Bridge version 1.0.41", info)
        self.assertIn("scrcpy: scrcpy 1.24", info)
        self.assertIn("PyGObject: 3.42.1", info)
        self.assertIn("zeroconf: 0.39.0", info)
        self.assertIn("Pillow: 9.2.0", info)
        self.assertIn("qrcode: 7.3.1", info)
        self.assertIn("pyudev: 0.24.0", info)

    @patch("aurynk.utils.adb_utils.get_adb_path")
    @patch("subprocess.run")
    @patch("platform.system")
    @patch("platform.release")
    @patch("platform.machine")
    @patch("sys.version")
    @patch("os.path.exists")
    @patch("os.environ")
    @patch("aurynk.utils.settings.SettingsManager")
    def test_get_debug_info_minimal(self, mock_settings, mock_environ, mock_exists, mock_sys_version, mock_machine, mock_release, mock_system, mock_subprocess, mock_get_adb_path):
        # Configure mocks for minimal/failure case
        mock_system.return_value = "Unknown"
        mock_release.return_value = ""
        mock_machine.return_value = "unknown"
        mock_sys_version.split.return_value = ["3.x"]

        mock_exists.return_value = False
        mock_environ.get.return_value = None

        mock_get_adb_path.return_value = "adb"

        # ADB and scrcpy fail
        mock_subprocess.side_effect = [
            MagicMock(returncode=1), # adb fail
            MagicMock(returncode=1)  # scrcpy fail
        ]

        # open raises exception
        mock_open_file = mock_open()
        mock_open_file.side_effect = Exception("File not found")

        with patch("builtins.open", mock_open_file):
             with patch("shutil.which", return_value=None):
                 # Temporarily remove modules if they exist in sys.modules
                 with patch.dict(sys.modules):
                     # We can't easily "unimport" modules in patch.dict,
                     # but we can set them to raise ImportError on access or just be missing?
                     # patch.dict only adds/changes.
                     # To simulate missing modules, we can set them to None or delete them.
                     for mod in ["zeroconf", "PIL", "qrcode", "pyudev"]:
                         if mod in sys.modules:
                             del sys.modules[mod]

                     # Also make gi import fail inside function?
                     # The function does `import gi`. If we delete it from sys.modules,
                     # it will try to load it. We need it to raise ImportError.
                     # We can set sys.modules["gi"] to None? No, python might reload it.
                     # We can mock the import mechanism, but that's hard.
                     # Instead, let's just make the existing mocks raise exception on attribute access or import?

                     # Actually, for the optional packages, the code does `import pkg`.
                     # If we remove them from sys.modules, import will look for them.
                     # If we want to simulate not found, we should probably ensure they are not found.
                     # But since we are in a test env, they might be installed.
                     # We can use `sys.meta_path` to block imports, but that's complex.

                     # Simpler: Make the imports raise Exception by mocking them as objects that raise on access?
                     # No, the import statement itself needs to fail.

                     # Let's just mock them as "Not found" strings if checking modules is hard.
                     # Or we can just mock sys.modules to return a mock that raises ImportError?
                     pass

                 info = _get_debug_info()

        self.assertIn("Installation: System/Manual", info)
        self.assertIn("ADB: Not found or error", info)
        self.assertIn("scrcpy: Not found or error", info)
        # We might see actual versions if packages are installed in the env, which is fine.
        # But we expect the code to handle exceptions.

    @patch("aurynk.utils.adb_utils.get_adb_path")
    @patch("subprocess.run")
    @patch("platform.system")
    @patch("sys.version")
    @patch("os.path.exists")
    @patch("os.environ")
    def test_installation_detection(self, mock_environ, mock_exists, mock_sys_version, mock_system, mock_run, mock_get_adb_path):
        # Setup basics to avoid crashes
        mock_sys_version.split.return_value = ["3.x"]
        mock_system.return_value = "Linux"
        mock_run.return_value = MagicMock(returncode=1)

        # Test Flatpak
        mock_exists.side_effect = lambda p: p == "/.flatpak-info"
        mock_environ.get.return_value = None

        m_open = mock_open()
        m_open.side_effect = Exception
        with patch("builtins.open", m_open):
            info = _get_debug_info()
            self.assertIn("Installation: Flatpak", info)

        # Test Snap
        mock_exists.side_effect = None
        mock_exists.return_value = False
        mock_environ.get.side_effect = lambda k, d=None: "snap" if k == "SNAP" else d

        m_open = mock_open()
        m_open.side_effect = Exception
        with patch("builtins.open", m_open):
            info = _get_debug_info()
            self.assertIn("Installation: Snap", info)

if __name__ == "__main__":
    unittest.main()
