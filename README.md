<div align="center">
  
[![Flathub Release](https://img.shields.io/flathub/v/io.github.IshuSinghSE.aurynk?logo=flathub&label=Flathub&color=4a90d9)](https://flathub.org/apps/io.github.IshuSinghSE.aurynk)
[![GitHub Release](https://img.shields.io/github/v/release/IshuSinghSE/aurynk?logo=github&label=Latest&color=2ea44f)](https://github.com/IshuSinghSE/aurynk/releases)
[![Nightly Build](https://github.com/IshuSinghSE/aurynk/actions/workflows/flatpak-nightly.yml/badge.svg)](https://github.com/IshuSinghSE/aurynk/actions/workflows/flatpak-nightly.yml)
[![Translation status](https://hosted.weblate.org/widgets/aurynk/-/svg-badge.svg)](https://hosted.weblate.org/engage/aurynk/)
</div>

# 🚀 Aurynk - Your Android Device Manager for Linux

<p align="center">
  <a href="https://ishusinghse.github.io/aurynk/">
    <img src="data/icons/io.github.IshuSinghSE.aurynk.png" alt="Aurynk Logo" width="128"/>
  </a>
</p>

<p align="center">
  <strong>Wirelessly connect, manage and control your Android devices from Linux</strong>
</p>

<p align="center">
  <a href="https://ishusinghse.github.io/aurynk/">🌏 Website</a> •
  <a href="#-installation">📦 Install</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-features">✨ Features</a> •
  <a href="#-troubleshooting">🔧 Help</a> •
  <a href="https://ishusinghse.github.io/aurynk/nightly">🌙 Nightly</a>
</p>

## 🎯 What is Aurynk?

Aurynk (Aura + Sync, pronounced “aw-rink”) makes managing your Android devices from Linux **simple and wireless**. No more cables, no more complicated setup - just scan a QR code and you're connected!

## 🎨 Screenshots

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="data/screenshots/screenshot-1-main.png" alt="Main Dashboard showing connected devices list" width="250"/>
        <br />
        <strong>Main Dashboard</strong>
      </td>
      <td align="center">
        <img src="data/screenshots/screenshot-2-pairing.png" alt="Pairing Dialog with QR Code scanner" width="250"/>
        <br />
        <strong>Wireless Pairing</strong>
      </td>
      <td align="center">
        <img src="data/screenshots/screenshot-3-menu.png" alt="Device Context Menu with actions" width="250"/>
        <br />
        <strong>Device Controls</strong>
      </td>
    </tr>
  </table>
</div>

Perfect for:

- 📱 **Developers** testing apps on multiple devices
- 🎮 **Gamers** managing Android gaming setups
- 👨‍💻 **Power users** who want full device control
- 📸 **Content creators** capturing device screenshots

## ✨ Features

| Feature                   | Description                                        |
| ------------------------- | -------------------------------------------------- |
| 🔗 **Wireless Pairing**   | Connect via QR code - no cables needed!            |
| 📱 **Device Management**  | View detailed specs, battery, storage info         |
| 📸 **Screenshot Capture** | Instantly capture and save device screenshots      |
| 🖥️ **Screen Mirroring**   | View and control your device screen (via scrcpy)   |
| 🎨 **Modern Interface**   | Beautiful GTK4 design that fits your Linux desktop |
| � **Multiple Devices**    | Manage several Android devices simultaneously      |

## 📦 Installation

### Option 1: Flatpak [(Recommended)](https://flathub.org/en/apps/io.github.IshuSinghSE.aurynk) 🌟

Now Aurynk is available on Flathub for easy installation:

```bash
# Once published on Flathub:
flatpak install flathub io.github.IshuSinghSE.aurynk
```

> **USB device support:** The Flatpak version automatically handles USB device monitoring - no additional setup needed!

### Option 2: From GitHub Release

**Download** the latest release from [GitHub Releases](https://github.com/IshuSinghSE/aurynk/releases)

### 🌙 Nightly Builds [(Unstable)](https://ishusinghse.github.io/aurynk/nightly)

To test the latest development features, add the nightly repository:

```bash
flatpak remote-add --user --if-not-exists --no-gpg-verify aurynk-nightly https://theishu.xyz/aurynk/nightly
flatpak install --user aurynk-nightly io.github.IshuSinghSE.aurynk
```

Note: Nightly builds may be unstable and contain bugs. (<a href="https://ishusinghse.github.io/aurynk/nightly">Unstable</a>)

## 🚀 Quick Start

### Step 1: Prepare Your Android Device 📱

1. **Enable Developer Options:**

   - Go to **Settings** → **About Phone**
   - Tap **Build Number** 7 times
   - Developer Options will appear in Settings

2. **Enable Wireless Debugging:** (for Android 11+)
    - Go to **Settings** → **Developer Options**
    - Turn on **Wireless Debugging**

### Step 2: Pair Your Device 🤝

1. **Launch Aurynk** from your applications menu
2. **Click "Add Device"** (the + button)
3. **On your Android device:**
   - Tap **"Pair device with QR code"** in Wireless Debugging
4. **Scan the QR code** shown in Aurynk
5. **Done!** Your device is now connected wirelessly

### Step 3: Manage Your Device 🎛️

- **Click on your device** to view detailed information
- **Take screenshots** with the camera button
- **Mirror your screen** with the monitor button
- **Refresh data** anytime with the refresh button

### Optional: USB Cable Connection 🔌
If you prefer a USB cable connection, enable USB debugging and authorize the host:

- Connect your Android device to the PC with a USB cable.
- Open **Settings** → **Developer Options** → enable **USB debugging**.
- When the device prompts, tap **Allow** (accept the RSA key) to authorize the computer.
- On some devices (for example Samsung with Knox), also enable **USB debugging (Security settings)** or **Install via USB** if present.
- If the device does not appear in `adb devices`, set USB mode to **File Transfer (MTP)** or a similar mode that exposes ADB, and ensure `adb` is installed on your PC.

This wired workflow is useful when wireless debugging is unavailable or when initial pairing requires a cable.


## 🔧 Troubleshooting

### Can't find Developer Options?

- Make sure you tapped "Build Number" exactly 7 times
- Look for "Developer Options" in your main Settings menu

### Device won't pair?

- ✅ Both devices are on the **same WiFi network**
- ✅ **Wireless Debugging is enabled** on Android
- ✅ Try **restarting Aurynk** and trying again

### ADB not working?

```bash
# Install ADB on your Linux system:
# Ubuntu/Debian:
sudo apt install android-tools-adb

# Fedora:
sudo dnf install android-tools

# Arch:
sudo pacman -S android-tools
```

### Still having issues?

- 🐛 [Report a bug](https://github.com/IshuSinghSE/aurynk/issues)
- 💬 [Ask for help](https://github.com/IshuSinghSE/aurynk/discussions)

## 🤝 Contributing

Want to help make Aurynk better? We'd love your contribution!

**📚 Documentation:**
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines and workflow
- **[BUILDING.md](docs/BUILDING.md)** - Detailed build instructions for all platforms
- **[TESTING.md](docs/TESTING.md)** - Testing guide and debugging tips

**🛠️ Quick Start for Contributors:**

```bash
# Clone the repository
git clone https://github.com/IshuSinghSE/aurynk.git
cd aurynk

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run from source
python -m aurynk

# Run tests
pytest

# Format code
ruff format .
```

**What can you contribute?**
- 🐛 Fix bugs or report issues
- ✨ Add new features
- 📖 Improve documentation
- 🌍 Add translations
- 🎨 Improve UI/UX
- 🧪 Write tests

## 🌍 Translations

Aurynk is being translated into many languages, and we need your help!

You can help translate Aurynk into your native language directly in your browser using Weblate. No coding knowledge is required.

👉 **[Start Translating on Weblate](https://hosted.weblate.org/engage/aurynk/)**

_This project uses Hosted [Weblate](https://www.google.com/search?q=https://hosted.weblate.org/) for translations._

## 📄 License

Aurynk is free and open source software licensed under GPL-3.0-or-later.

## ❤️ Credits

- **Developer:** [IshuSinghSE](https://github.com/IshuSinghSE)
- **Screen Mirroring:** Powered by [scrcpy](https://github.com/Genymobile/scrcpy)
- **UI Framework:** Built with GTK4 and libadwaita
- **ADB Integration:** Uses Android Debug Bridge

---

<p align="center">
  <strong>⭐ Star us on GitHub if you find Aurynk useful!</strong><br>
  <a href="https://github.com/IshuSinghSE/aurynk">🔗 GitHub Repository</a>
</p>

## Installation via Debian Package

Debian packages (.deb) are built automatically via GitHub Actions. Download the latest `.deb` from the [Actions page](https://github.com/TheRealFame/Aurynk-Packaged/actions) and install:

```bash
sudo dpkg -i aurynk_*.deb
sudo apt-get install -f
```

### Python Dependencies

The deb package requires Python modules that are installed via pip:

```bash
pip install --break-system-packages zeroconf pyudev qrcode
```

### Building from Source

```bash
sudo apt-get install -y meson ninja-build python3 python3-gi python3-setuptools pkg-config libglib2.0-dev libgtk-4-dev libadwaita-1-dev python3-dev gettext
pip install --break-system-packages zeroconf pyudev qrcode
meson setup builddir --prefix=/usr
ninja -C builddir
sudo ninja -C builddir install
```
