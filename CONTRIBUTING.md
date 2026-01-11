# Contributing to Aurynk

Welcome, and thank you for helping move Aurynk forward. This guide keeps contributors aligned on tooling, workflow, and release practices.

## Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Repository Layout](#repository-layout)
- [Environment Setup](#environment-setup)
- [Everyday Tasks](#everyday-tasks)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Packaging Guides](#packaging-guides)
- [Release Checklist](#release-checklist)
- [Submitting Changes](#submitting-changes)
- [Support](#support)

## Additional Guides

For more detailed information, see:
- **[BUILDING.md](docs/BUILDING.md)** - Comprehensive build instructions for all platforms
- **[TESTING.md](docs/TESTING.md)** - Testing strategies, running tests, and debugging

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
├── aurynk/                      # Python package
│   ├── __init__.py              # Package initialization
│   ├── __main__.py              # Entry point for python -m aurynk
│   ├── application.py           # Adw.Application main class
│   ├── i18n.py                  # Internationalization helpers
│   ├── core/                    # Core functionality
│   │   ├── adb_manager.py       # ADB operations and device pairing
│   │   ├── device_manager.py    # Device lifecycle management
│   │   └── scrcpy_runner.py     # Screen mirroring integration
│   ├── services/                # Background services
│   │   ├── device_monitor.py    # Device discovery and monitoring
│   │   ├── tray_service.py      # System tray integration
│   │   └── usb_monitor.py       # USB device detection
│   ├── ui/                      # GTK4/Libadwaita UI components
│   │   ├── windows/             # Application windows
│   │   ├── dialogs/             # Dialog widgets
│   │   └── widgets/             # Reusable widgets
│   ├── utils/                   # Shared utilities
│   │   ├── adb_utils.py         # ADB helper functions
│   │   ├── logger.py            # Logging configuration
│   │   └── power.py             # Power management
│   ├── models/                  # Data models
│   │   ├── device.py            # Device data model
│   │   └── settings.py          # Settings manager
│   └── scripts/                 # Runtime scripts
│       └── __init__.py          # Scripts package init
├── scripts/                     # Build-time scripts
│   ├── aurynk                   # Launcher script
│   ├── aurynk_tray.py           # System tray helper
│   └── publish-*.sh             # Release automation
├── data/                        # Application data
│   ├── icons/                   # Application icons
│   ├── ui/                      # GTK UI templates
│   ├── styles/                  # CSS stylesheets
│   ├── *.desktop.in             # Desktop entry
│   ├── *.metainfo.xml           # AppStream metadata
│   └── *.gresource.xml          # GResource definition
├── flatpak/                     # Flatpak packaging
│   ├── io.github.IshuSinghSE.aurynk.yml  # Manifest
│   └── patches/                 # Patches for dependencies
├── debian/                      # Debian packaging
│   ├── control                  # Package dependencies
│   ├── install                  # File installation rules
│   └── rules                    # Build rules
├── po/                          # Translations
│   ├── *.po                     # Translation files
│   └── POTFILES                 # Files to translate
├── tests/                       # Test suite
### Running the Application

```bash
# Run from source (recommended during development)
python -m aurynk

# Run with debug logging
G_MESSAGES_DEBUG=all python -m aurynk

# Run with Python warnings
python -Wd -m aurynk
```

### Code Quality

```bash
# Lint code (check for issues)
ruff check .

# Format code (auto-fix)
ruff format .

# Run both
ruff check . && ruff format .
```

### Type Checking

```bash
# Check type safety (optional but encouraged)
mypy aurynk

# Or install and use pyright
pip install pyright
pyright aurynk
```

### Localization

```bash
# Update translation templates
cd po
xgettext --files-from=POTFILES --output=aurynk.pot

# Update existing translations
msgmerge -U fr.po aurynk.pot

# Compile translations
msgfmt fr.po -o fr.mo
```

## Testing

Quick testing commands. See [TESTING.md](docs/TESTING.md) for comprehensive guide.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_adb_manager.py

# Run with coverage
pytest --cov=aurynk

# Generate HTML coverage report
pytest --cov=aurynk --cov-report=html
xdg-open htmlcov/index.html
```

## Code Quality

### Code Style

- Follow [PEP 8](https://pep8.org/) style guide
- Use `ruff` for linting and formatting
- Keep line length to 100 characters (configured in `pyproject.toml`)
- Use meaningful variable and function names

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings:
  ```python
  def pair_device(ip: str, port: int) -> bool:
      """Pair with an Android device.
      
      Args:
          ip: Device IP address
          port: Pairing port number
          
      Returns:
          True if pairing succeeded, False otherwise
          
      Raises:
          ConnectionError: If device is unreachable
      """
      pass
  ```
- Update user-facing documentation when adding features
### Pre-release

- [ ] Update version numbers:
  - [ ] `pyproject.toml` (`version = "X.Y.Z"`)
  - [ ] `meson.build` (`version: 'X.Y.Z'`)
  - [ ] `debian/changelog` (run `dch -v X.Y.Z-1`)
  - [ ] `flatpak/io.github.IshuSinghSE.aurynk.yml` (tag/commit reference)

- [ ] Update `CHANGELOG.md` with release notes

- [ ] Update dependencies if needed:
  - [ ] `pyproject.toml` dependencies
  - [ ] Flatpak manifest hashes (run `flatpak-pip-generator` if needed)

- [ ] Regenerate resources:
  ```bash
  glib-compile-resources \
      --sourcedir=data \
      data/io.github.IshuSinghSE.aurynk.gresource.xml \
      --target=data/io.github.IshuSinghSE.aurynk.gresource
  ```

- [ ] Update translations:
  ```bash
  cd po
  ./update-potfiles.sh  # Update POTFILES if new translatable files added
  xgettext --files-from=POTFILES --output=aurynk.pot
  ```

### Quality Checks

- [ ] All tests pass: `pytest`
- [ ] No linting errors: `ruff check .`
- [ ] Code formatted: `ruff format .`
- [ ] Test all build methods:
  - [ ] Python/pip build
  - [ ] Meson build
  - [ ] Flatpak build
  - [ ] Debian package build

- [ ] Manual testing:
  - [ ] Wireless pairing works
  - [ ] USB detection works
  - [ ] Screen mirroring works
  - [ ] Screenshot capture works
  - [ ] Settings persist correctly
  - [ ] Tray icon works
  - [ ] Multi-device support works

### Release

1. **Create release branch** (optional, for major releases):
   ```bash
   git checkout -b release/vX.Y.Z
   ```

2. **Commit version updates**:
   ```bash
   git add pyproject.toml meson.build debian/changelog CHANGELOG.md
   git commit -m "chore: bump version to X.Y.Z"
   ```

3. **Tag the release**:
   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   git push origin vX.Y.Z
   ```

4. **Create GitHub Release**:
   - Go to https://github.com/IshuSinghSE/aurynk/releases/new
   - Select the tag
   - Title: `Aurynk vX.Y.Z`
   - Copy release notes from CHANGELOG.md
   - Attach build artifacts if available

### Post-release

- [ ] Submit Flatpak update to Flathub:
  ```bash
  # Fork flathub/io.github.IshuSinghSE.aurynk if not done
  # Update manifest with new version
  # Submit PR to Flathub
  ```

- [ ] Update AUR package (if maintaining)

- [ ] Announce release:
  - [ ] GitHub Discussions
  - [ ] Social media (if applicable)
  - [ ] Project website

- [ ] Monitor for bug reports

## Packaging Guides

For detailed build instructions, see [BUILDING.md](docs/BUILDING.md).

### Quick Reference

#### Meson Build
```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

#### Flatpak Build
```bash
# Build and install
flatpak-builder --user --install --force-clean build-dir \
    flatpak/io.github.IshuSinghSE.aurynk.yml

# Run
flatpak run io.github.IshuSinghSE.aurynk
```

#### Debian Package
```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../aurynk_*_all.deb
```

#### Development Build
```bash
# Most common during development
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m aurynk
```
  type(scope): description
  
  [optional body]
  [optional footer]
  ```
  Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
  
  Examples:
  ```
  feat(pairing): add QR code pairing support
  fix(usb): resolve device detection on Ubuntu 22.04
  docs(readme): update installation instructions
  ```

- Keep commits focused and atomic
- Rebase instead of merge to keep history clean`pacman`).

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