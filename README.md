# Aurynk - Android Device Manager for Linux

<p align="center">
  <img src="data/icons/io.github.IshuSinghSE.aurynk.png" alt="Aurynk Logo" width="128"/>
</p>

A modern Android device manager for Linux that allows you to wirelessly pair and manage your Android devices using ADB (Android Debug Bridge).

## Features

- 🔗 **Wireless Pairing** - Pair devices via QR code using Android's Wireless Debugging feature
- 📱 **Device Management** - View detailed device information and specifications
- 📸 **Screenshot Capture** - Take and view device screenshots
- 🎨 **Modern UI** - Built with GTK4 and libadwaita for a beautiful, native GNOME experience
- 📦 **Multi-format Packaging** - Available as .deb, Flatpak, or run directly from source

## Requirements

### Runtime Dependencies
- Python 3.11 or newer
- GTK 4
- libadwaita 1.0 or newer
- PyGObject
- Android Debug Bridge (adb)
- Python packages: pillow, qrcode, zeroconf

### Build Dependencies (for building from source)
- Meson (>= 0.59.0)
- Ninja
- GLib development files
- GTK4 development files

## Installation

### From Source (Development)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/IshuSinghSE/aurynk.git
   cd aurynk
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -e .
   ```

3. **Compile GResources:**
   ```bash
   glib-compile-resources --sourcedir=data data/io.github.IshuSinghSE.aurynk.gresource.xml \
       --target=data/io.github.IshuSinghSE.aurynk.gresource
   ```

4. **Run directly:**
   ```bash
   python -m aurynk
   ```

### Building with Meson (System Installation)

```bash
meson setup build --prefix=/usr
meson compile -C build
sudo meson install -C build
```

### Building a Debian Package

```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../aurynk_0.1.0-1_all.deb
```

### Building a Flatpak

```bash
flatpak-builder --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml
flatpak-builder --user --install --force-clean build-dir flatpak/io.github.IshuSinghSE.aurynk.yml
```

## Usage

### Pairing a Device

1. Launch Aurynk
2. Click the "Add Device" button
3. On your Android device:
   - Go to **Settings** → **Developer Options** → **Wireless Debugging**
   - Enable **Wireless Debugging**
   - Tap **Pair device with QR code**
4. Scan the QR code displayed in Aurynk
5. Your device will be automatically paired and connected

### Viewing Device Details

1. Click on a paired device in the main window
2. View comprehensive device information including:
   - Device name, manufacturer, and model
   - Android version
   - RAM, storage, and battery status
   - Current screenshot

### Refreshing Device Data

- Click the **Refresh Screenshot** button to capture a new screenshot
- Click **Refresh All Data** to update all device information

## Project Structure

```
aurynk/                             # Project root (Git repository)
├── aurynk/                         # Python package (importable code)
│   ├── __init__.py
│   ├── __main__.py                 # Module entry point
│   ├── app.py                      # AurynkApp(Adw.Application)
│   ├── main_window.py              # AurynkWindow(Adw.ApplicationWindow)
│   ├── adb_controller.py           # All ADB/device management logic
│   ├── pairing_dialog.py           # Pairing dialog
│   ├── device_details_window.py    # Device details window
│   └── qr_widget.py                # QR code widget
│
├── data/                           # Application data
│   ├── io.github.IshuSinghSE.aurynk.gresource.xml
│   ├── io.github.IshuSinghSE.aurynk.desktop.in
│   ├── io.github.IshuSinghSE.aurynk.appdata.xml
│   ├── icons/
│   │   └── io.github.IshuSinghSE.aurynk.png
│   └── ui/
│       ├── main_window.ui
│       └── device_details_window.ui
│
├── flatpak/                        # Flatpak manifest
│   └── io.github.IshuSinghSE.aurynk.yml
│
├── debian/                         # Debian packaging
│   ├── control
│   ├── rules
│   └── ...
│
├── meson.build                     # Build configuration
├── pyproject.toml                  # Python project config
└── README.md
```

## Development

### Running from Source

For development, you can run the app directly without installation:

```bash
# From the project root
python -m aurynk
```

### Code Style

This project uses `ruff` for linting and formatting:

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check .

# Format
ruff format .
```

## Troubleshooting

### ADB Connection Issues

If you're having trouble connecting to devices:

1. Ensure `adb` is installed and in your PATH
2. Check that Wireless Debugging is enabled on your Android device
3. Make sure both devices are on the same network
4. Try restarting the ADB server: `adb kill-server && adb start-server`

### Missing Dependencies

If you encounter import errors, ensure all dependencies are installed:

```bash
pip install pillow pygobject qrcode zeroconf
```

For system packages (Debian/Ubuntu):

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 android-tools-adb
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the GNU General Public License v3.0 or later - see the LICENSE file for details.

## Credits

- Developed by [IshuSinghSE](https://github.com/IshuSinghSE)
- Built with GTK4 and libadwaita
- Uses Android Debug Bridge (ADB)

## Links

- **GitHub**: https://github.com/IshuSinghSE/aurynk
- **Issues**: https://github.com/IshuSinghSE/aurynk/issues
