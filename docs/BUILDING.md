# Building Aurynk

This guide covers how to build Aurynk from source using different methods.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Methods](#build-methods)
  - [Development Build (Python)](#development-build-python)
  - [Meson Build (System Install)](#meson-build-system-install)
  - [Flatpak Build](#flatpak-build)
  - [Debian Package](#debian-package)
  - [Snap Package](#snap-package)
- [Building Dependencies](#building-dependencies)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y \
    python3 python3-dev python3-pip python3-venv python3-pyudev \
    python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
    android-tools-adb \
    meson ninja-build \
    gettext desktop-file-utils appstream-util \
    libglib2.0-dev libgtk-4-dev libadwaita-1-dev
```

**Fedora:**
```bash
sudo dnf install -y \
    python3 python3-devel python3-pip \
    python3-gobject gtk4 libadwaita \
    android-tools \
    meson ninja-build \
    gettext desktop-file-utils appstream \
    glib2-devel gtk4-devel libadwaita-devel
```

**Arch Linux:**
```bash
sudo pacman -S --needed \
    python python-pip python-gobject \
    gtk4 libadwaita \
    android-tools \
    meson ninja \
    gettext desktop-file-utils appstream
```

### Python Dependencies

See [pyproject.toml](pyproject.toml) for the complete list. Key dependencies:
- `pillow>=12.0.0`
- `pygobject>=3.54.5`
- `pyudev>=0.24.0`
- `qrcode>=8.2`
- `zeroconf>=0.148.0`

Development dependencies:
- `rich>=14.2.0`
- `ruff>=0.14.3`

## Quick Start

The fastest way to get started with development:

```bash
# Clone the repository
git clone https://github.com/IshuSinghSE/aurynk.git
cd aurynk

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run from source
python -m aurynk
```

## Build Methods

### Development Build (Python)

Best for rapid development and testing:

```bash
# Create virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run the application
python -m aurynk

# Or run directly
python3 -m aurynk
```

**Benefits:**
- Fast iteration
- No installation required
- Easy debugging
- Changes take effect immediately

### Meson Build (System Install)

For system-wide installation:

```bash
# Configure build directory
meson setup build --prefix=/usr

# Compile
meson compile -C build

# Install (requires root)
sudo meson install -C build

# Run installed version
aurynk
```

**Custom prefix:**
```bash
# Install to custom location (e.g., ~/.local)
meson setup build --prefix=$HOME/.local
meson compile -C build
meson install -C build

# Make sure ~/.local/bin is in your PATH
export PATH="$HOME/.local/bin:$PATH"
aurynk
```

**Uninstall:**
```bash
sudo ninja -C build uninstall
```

### Flatpak Build

For sandboxed installation with all dependencies included:

#### Prerequisites

```bash
# Install Flatpak and flatpak-builder
sudo apt install flatpak flatpak-builder  # Ubuntu/Debian
sudo dnf install flatpak flatpak-builder  # Fedora
sudo pacman -S flatpak flatpak-builder    # Arch

# Add Flathub repository
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Install GNOME SDK/Platform
flatpak install --user flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

#### Build and Install

```bash
# Build and install directly
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml

# Run the Flatpak
flatpak run io.github.IshuSinghSE.aurynk
```

#### Build Bundle for Distribution

```bash
# Build and export to repository
flatpak-builder --repo=repo --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml

# Create a single-file bundle
flatpak build-bundle repo aurynk.flatpak io.github.IshuSinghSE.aurynk

# Others can install the bundle with:
flatpak install aurynk.flatpak
```

#### Development with Flatpak

```bash
# Build without installing
flatpak-builder --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml

# Enter the build environment for debugging
flatpak-builder --run build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml \
    /bin/bash
```

### Debian Package

For Debian/Ubuntu systems:

#### Prerequisites

```bash
sudo apt install devscripts build-essential debhelper dh-python
```

#### Build Package

```bash
# Build the .deb package
dpkg-buildpackage -us -uc -b

# Package will be in parent directory
ls ../aurynk_*.deb

# Install the package
sudo dpkg -i ../aurynk_*_all.deb

# Fix any dependency issues
sudo apt-get install -f
```

#### Build for Different Ubuntu Versions

```bash
# Update debian/changelog for target version
dch --local ubuntu24.04

# Build
dpkg-buildpackage -us -uc -b
```

### Snap Package

For Snap-based distributions:

#### Prerequisites

```bash
sudo apt install snapd snapcraft  # Ubuntu
sudo snap install snapcraft --classic
```

#### Build Snap

```bash
# Clean build
snapcraft clean

# Build snap package
snapcraft

# Install locally
sudo snap install --dangerous aurynk_*.snap

# Run
aurynk
```

## Building Dependencies

### Scrcpy (Screen Mirroring)

Aurynk uses scrcpy for screen mirroring. It will use the system scrcpy if available:

```bash
# Ubuntu/Debian
sudo apt install scrcpy

# Fedora
sudo dnf install scrcpy

# Arch
sudo pacman -S scrcpy
```

**Building scrcpy from source** (optional, for latest features):

```bash
cd vendor/scrcpy
meson setup build --buildtype=release --strip -Db_lto=true
cd build
ninja
sudo ninja install
```

### ADB (Android Debug Bridge)

Required for device communication:

```bash
# Ubuntu/Debian
sudo apt install android-tools-adb

# Fedora
sudo dnf install android-tools

# Arch
sudo pacman -S android-tools
```

**Verify installation:**
```bash
adb version
```

## Troubleshooting

### Missing Dependencies

**Error: `No module named 'gi'`**
```bash
# Install PyGObject
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0
```

**Error: `No package 'gtk4' found`**
```bash
# Install GTK4 development files
sudo apt install libgtk-4-dev
```

**Error: `No package 'libadwaita-1' found`**
```bash
# Install libadwaita development files
sudo apt install libadwaita-1-dev
```

### Build Errors

**Meson configuration fails:**
```bash
# Clean and reconfigure
rm -rf build
meson setup build --prefix=/usr
```

**GResource compilation fails:**
```bash
# Manually compile resources
glib-compile-resources \
    --sourcedir=data \
    data/io.github.IshuSinghSE.aurynk.gresource.xml \
    --target=data/io.github.IshuSinghSE.aurynk.gresource
```

**Python import errors:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall in editable mode
pip install -e ".[dev]"
```

### Flatpak Build Issues

**Platform/SDK not found:**
```bash
# Install required runtime
flatpak install flathub org.gnome.Platform//47 org.gnome.Sdk//47
```

**Build cache issues:**
```bash
# Clean build directory
rm -rf .flatpak-builder build-dir repo

# Rebuild from scratch
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml
```

**Permission issues:**
```bash
# Use --user flag for user installation
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml
```

### Runtime Issues

**ADB not found:**
```bash
# Add ADB to PATH
export PATH="$PATH:$HOME/Android/Sdk/platform-tools"

# Or install system-wide
sudo apt install android-tools-adb
```

**Device not detected:**
```bash
# Check ADB connection
adb devices

# Restart ADB server
adb kill-server
adb start-server
```

## Next Steps

- See [TESTING.md](TESTING.md) for running tests
- See [CONTRIBUTING.md](../CONTRIBUTING.md) for development guidelines
- Report build issues on [GitHub Issues](https://github.com/IshuSinghSE/aurynk/issues)

---

**Need Help?** 
- 📖 [Documentation](https://ishusinghse.github.io/aurynk/)
- 💬 [Discussions](https://github.com/IshuSinghSE/aurynk/discussions)
- 🐛 [Bug Reports](https://github.com/IshuSinghSE/aurynk/issues)
