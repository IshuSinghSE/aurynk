# Contributing to Aurynk

Welcome, and thank you for helping move Aurynk forward. This guide keeps contributors aligned on tooling, workflow, and release practices.

## Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Repository Layout](#repository-layout)
- [Environment Setup](#environment-setup)
- [Everyday Tasks](#everyday-tasks)
- [Packaging Guides](#packaging-guides)
- [Release Checklist](#release-checklist)
- [Submitting Changes](#submitting-changes)
- [Support](#support)

## Quick Start

1. Clone and enter the repository:
   ```bash
   git clone https://github.com/IshuSinghSE/aurynk.git
   cd aurynk
   ```
2. Create a development branch for your change:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. Prepare a virtual environment (recommended) and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
4. Launch the application:
   ```bash
   python -m aurynk
   ```

You should now see the Aurynk window and can begin iterating on features or fixes.

## Requirements

### Runtime
- Python 3.11 or newer
- GTK 4 and libadwaita 1.4+
- PyGObject bindings
- Android Debug Bridge (`adb`) available on the host PATH

### Build & Tooling
- Meson ≥ 0.59 and Ninja (for packaged builds)
- GLib and GTK4 development headers
- `pip`, `ruff`, and `pytest`
- Optional: Flatpak SDK/Platform `org.gnome.Platform//49` for sandbox testing

## Repository Layout

```
aurynk/
├── aurynk/                  # Python package
│   ├── application.py       # Adw.Application entry point
│   ├── core/                # Scrcpy integration and runtime helpers
│   ├── services/            # Background services (USB monitor, tray, etc.)
│   ├── ui/                  # GTK windows, dialogs, widgets
│   ├── utils/               # Shared utilities and logging
│   └── models/              # Data models (Device, settings)
├── data/                    # GResources, icons, desktop/metainfo
├── flatpak/                 # Flatpak manifest and patches
├── debian/                  # Debian packaging metadata
├── scripts/                 # Convenience scripts and release helpers
├── tests/                   # Pytest-based regression tests
├── meson.build              # Meson build definition
├── pyproject.toml           # Project metadata & dependencies
└── README.md
```

## Environment Setup

1. **Install system dependencies** (example for Ubuntu/Debian):
   ```bash
   sudo apt install python3-dev python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
       android-tools-adb meson ninja-build
   ```
   Use the equivalent packages for Fedora (`dnf`) or Arch (`pacman`).

2. **Create and activate a virtual environment** (see Quick Start).

3. **Install Python dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Rebuild resources when UI files change**:
   ```bash
   glib-compile-resources \
       --sourcedir=data \
       data/io.github.IshuSinghSE.aurynk.gresource.xml \
       --target=data/io.github.IshuSinghSE.aurynk.gresource
   ```
   Meson and Flatpak builds do this automatically, but running the command is handy during rapid iteration.

5. **Keep your branch current**:
   ```bash
   git fetch origin
   git rebase origin/develop   # or origin/main, depending on target branch
   ```

## Everyday Tasks

- **Run from source**:
  ```bash
  python -m aurynk
  ```

- **Run tests**:
  ```bash
  pytest
  ```

- **Lint and format**:
  ```bash
  ruff check .
  ruff format .
  ```

- **Check type safety** (optional but encouraged when adding complex logic):
  ```bash
  mypy aurynk
  ```
  (Add annotations as you go to keep future work smoother.)

## Packaging Guides

### Meson install (system integration)
```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

### Flatpak workflow
```bash
# Ensure the GNOME runtime remote exists for your user
flatpak --user remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Build and install into the user collection
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml

# Launch the sandboxed build
flatpak run io.github.IshuSinghSE.aurynk
```
To export into a local repo for testing or distribution:
```bash
flatpak-builder --repo=repo --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml
flatpak build-bundle repo aurynk.flatpak io.github.IshuSinghSE.aurynk
```
If the manifest references an icon, confirm it is installed under `data/icons/hicolor/.../apps/` so the Flatpak export step succeeds without warnings.

### Debian package
```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../aurynk_*_all.deb
```

## Release Checklist

1. Update version numbers in `pyproject.toml`, `meson.build`, Debian metadata, and Flatpak manifest.
2. Regenerate resources, screenshots, or translations as needed (`glib-compile-resources`, `po` updates).
3. Run the full test matrix: `pytest`, linting, and both native and Flatpak builds.
4. Refresh Flatpak hashes and archives after dependency bumps.
5. Tag the release and push (`git tag vX.Y.Z && git push --tags`).
6. Publish release notes on GitHub and submit packaging updates (Flathub, distro repos).

## Submitting Changes

1. Keep commits focused; prefer a logical change per commit.
2. Write imperative commit messages with a concise subject (< 50 chars) and an optional detailed body.
3. Update or add tests when fixing bugs or adding features.
4. Ensure `ruff check` and `pytest` pass before opening a pull request.
5. Open the PR against the appropriate branch (`develop` for feature work unless instructed otherwise).
6. Describe the motivation, implementation details, and testing performed. Attach screenshots for UI updates.
7. Stay responsive to review feedback and rebase instead of merging to keep history clean.

## Support

- Report bugs or request features through [GitHub Issues](https://github.com/IshuSinghSE/aurynk/issues).
- Ask questions or discuss ideas in [GitHub Discussions](https://github.com/IshuSinghSE/aurynk/discussions).
- For security concerns, email [ishu.111636@yahoo.com](mailto:ishu.111636@yahoo.com).

By contributing, you agree your work is licensed under GPL-3.0-or-later. Thank you for helping Aurynk grow!