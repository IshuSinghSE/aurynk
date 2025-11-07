# Contributing to Aurynk

Thank you for your interest in contributing to Aurynk! This document provides all the technical information developers need to contribute to the project.

## 📋 Table of Contents

- [Development Setup](#-development-setup)
- [Project Structure](#-project-structure)
- [Building from Source](#-building-from-source)
- [Code Style](#-code-style)
- [Testing](#-testing)
- [Packaging](#-packaging)
- [Submitting Changes](#-submitting-changes)

## 🛠 Development Setup

### Requirements

#### Runtime Dependencies
- Python 3.11 or newer
- GTK 4
- libadwaita 1.0 or newer
- PyGObject
- Android Debug Bridge (adb)

#### Build Dependencies
- Meson (>= 0.59.0)
- Ninja
- GLib development files
- GTK4 development files

### Setting up the Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/IshuSinghSE/aurynk.git
   cd aurynk
   ```

2. **Install system dependencies:**
   ```bash
   # Ubuntu/Debian:
   sudo apt install python3-dev python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
                    android-tools-adb meson ninja-build

   # Fedora:
   sudo dnf install python3-devel python3-gobject gtk4-devel libadwaita-devel \
                    android-tools meson ninja-build

   # Arch:
   sudo pacman -S python python-gobject gtk4 libadwaita android-tools meson ninja
   ```

3. **Install Python dependencies:**
   ```bash
   # Create virtual environment (recommended)
   python -m venv .venv
   source .venv/bin/activate  # or `.venv/bin/activate.fish` for Fish shell

   # Install project with dev dependencies
   pip install -e ".[dev]"
   ```

4. **Compile GResources:**
   ```bash
   glib-compile-resources --sourcedir=data data/io.github.IshuSinghSE.aurynk.gresource.xml \
       --target=data/io.github.IshuSinghSE.aurynk.gresource
   ```

5. **Run the application:**
   ```bash
   python -m aurynk
   ```

## 📁 Project Structure

```
aurynk/                             # Project root (Git repository)
├── aurynk/                         # Python package (importable code)
│   ├── __init__.py
│   ├── __main__.py                 # Module entry point
│   ├── app.py                      # AurynkApp(Adw.Application)
│   ├── windows/
│   │   ├── main_window.py          # AurynkWindow(Adw.ApplicationWindow)
│   │   └── device_details_window.py
│   ├── dialogs/
│   │   └── pairing_dialog.py       # Device pairing dialog
│   ├── widgets/
│   │   └── qr_widget.py            # QR code display widget
│   ├── lib/
│   │   ├── adb_controller.py       # ADB/device management logic
│   │   ├── tray_controller.py      # System tray integration
│   │   └── scrcpy_manager.py       # Screen mirroring functionality
│   └── utils/
│       ├── adb_pairing.py          # Wireless pairing utilities
│       ├── device_events.py        # Device event handling
│       └── device_store.py         # Device data persistence
│
├── data/                           # Application data files
│   ├── io.github.IshuSinghSE.aurynk.gresource.xml
│   ├── io.github.IshuSinghSE.aurynk.desktop.in
│   ├── io.github.IshuSinghSE.aurynk.appdata.xml
│   ├── icons/                      # Application icons
│   ├── styles/                     # CSS stylesheets
│   └── ui/                         # GTK UI files
│       ├── main_window.ui
│       └── device_details_window.ui
│
├── scripts/                        # Helper scripts
│   ├── aurynk                      # Main launcher script
│   └── aurynk_tray.py             # GTK3 system tray helper
│
├── flatpak/                        # Flatpak packaging
│   ├── io.github.IshuSinghSE.aurynk.yml
│   └── appindicator/              # Local AyatanaAppIndicator dependencies
│
├── debian/                         # Debian/Ubuntu packaging
├── snap/                          # Snap packaging
├── vendor/                        # Prebuilt binaries (scrcpy)
├── meson.build                    # Build system configuration
├── pyproject.toml                 # Python project metadata
└── README.md
```

## 🏗️ Building from Source

### Development Build (Meson)

```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

### Debian Package

```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../aurynk_0.1.0-1_all.deb
```

### Flatpak

```bash
# Local build
flatpak-builder --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml

# Install locally
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml

# Create bundle
flatpak-builder --repo=repo --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml
flatpak build-bundle repo aurynk.flatpak io.github.IshuSinghSE.aurynk
```

## 🎨 Code Style

This project uses `ruff` for linting and formatting:

```bash
# Install dev dependencies if not already done
pip install -e ".[dev]"

# Check code style
ruff check .

# Format code
ruff format .

# Check and fix automatically
ruff check --fix .
```

### Code Style Guidelines

- **Line length:** 100 characters maximum
- **Import organization:** Use `ruff`'s import sorting
- **Type hints:** Encouraged for new code
- **Docstrings:** Use for public functions and classes
- **Comments:** Explain complex logic and business rules

## 🧪 Testing

### Manual Testing

1. **Test wireless pairing:**
   - Ensure QR code generation works
   - Test pairing with various Android versions
   - Verify connection persistence

2. **Test device management:**
   - Check device information display
   - Test screenshot capture
   - Verify refresh functionality

3. **Test system tray integration:**
   - Verify tray icon appears
   - Test menu functionality
   - Check minimize-to-tray behavior

### Automated Testing

*Testing framework setup is planned for future releases.*

## 📦 Packaging

### Flatpak Manifest Structure

The Flatpak manifest (`flatpak/io.github.IshuSinghSE.aurynk.yml`) includes:

- **Python dependencies:** Managed via pip modules
- **ADB tools:** Android Debug Bridge
- **AyatanaAppIndicator:** System tray support (local build)
- **Prebuilt scrcpy:** Screen mirroring binaries

### Release Process

1. **Update version** in `pyproject.toml` and `meson.build`
2. **Test packaging** across different formats
3. **Create GitHub release** with proper tagging
4. **Update Flatpak manifest** SHA256 hashes
5. **Submit to Flathub** (for stable releases)

## 🚀 Submitting Changes

### Pull Request Process

1. **Fork the repository** on GitHub
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the code style guidelines
4. **Test your changes** thoroughly
5. **Commit with descriptive messages:**
   ```bash
   git commit -m "Add wireless debugging timeout handling
   
   - Increase pairing timeout to 30 seconds
   - Add user feedback for connection status  
   - Handle network interruption gracefully"
   ```
6. **Push to your fork** and create a Pull Request
7. **Respond to review feedback** promptly

### Commit Message Guidelines

- **Use imperative mood:** "Add feature" not "Added feature"
- **Keep first line under 50 characters**
- **Add detailed description** for complex changes
- **Reference issues:** "Fixes #123" or "Closes #456"

### What to Include in PRs

- **Clear description** of the change and motivation
- **Test steps** for reviewers to verify the change
- **Screenshots** for UI changes
- **Updated documentation** if applicable

## 🐛 Reporting Issues

When reporting bugs or requesting features:

1. **Search existing issues** to avoid duplicates
2. **Use issue templates** when available
3. **Provide system information:**
   - Linux distribution and version
   - Python version (`python --version`)
   - GTK version
   - Android device information (if relevant)
4. **Include steps to reproduce** the issue
5. **Add relevant logs** or error messages

## 📞 Getting Help

- 🐛 **Bug Reports:** [GitHub Issues](https://github.com/IshuSinghSE/aurynk/issues)
- 💬 **Questions:** [GitHub Discussions](https://github.com/IshuSinghSE/aurynk/discussions)
- 📧 **Security Issues:** Email [ishu.111636@yahoo.com](mailto:ishu.111636@yahoo.com)

## 📄 License

By contributing to Aurynk, you agree that your contributions will be licensed under the GPL-3.0-or-later license.

---

Thank you for contributing to Aurynk! 🎉