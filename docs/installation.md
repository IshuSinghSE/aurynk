# Installation

Aurynk is available for various Linux distributions. The recommended way to install is via Flatpak.

## Option 1: Flatpak (Recommended) :star:

Aurynk is available on [Flathub](https://flathub.org/en/apps/io.github.IshuSinghSE.aurynk) for easy installation. This ensures you have all dependencies isolated and up to date.

```bash
flatpak install flathub io.github.IshuSinghSE.aurynk
```

## Option 2: From GitHub Release

You can download pre-built packages from our GitHub Releases page.

1. **Download** the latest release from [GitHub Releases](https://github.com/IshuSinghSE/aurynk/releases)
2. **Install** using your package manager:

=== "Debian/Ubuntu"

    ```bash
    sudo dpkg -i aurynk_*.deb
    ```

=== "Flatpak Bundle"

    ```bash
    flatpak install aurynk_*.flatpak
    ```

## Option 3: Build from Source

If you are a developer or want to build the latest version from source, please check our [Contributing Guide](contributing.md).

## Prerequisites

To use Aurynk's wireless features effectively, you need:

1.  A computer running Linux.
2.  An Android device (Android 11+ recommended for Wireless Debugging).
3.  Both devices connected to the same WiFi network.
