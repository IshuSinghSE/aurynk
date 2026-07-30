# Aurynk Packaging Troubleshooting

Common issues when building or running Aurynk packages.

## AppImage Issues

### AppImage won't run (FUSE missing)
```bash
# Ubuntu/Debian
sudo apt install fuse libfuse2

# Fedora/RHEL
sudo dnf install fuse

# Arch/Manjaro
sudo pacman -S fuse2
```

### Permission denied
```bash
chmod +x aurynk-x86_64.AppImage
```

### AppImage runs but Aurynk doesn't launch
- Check `~/.local/share/aurynk/` for logs
- Ensure required system dependencies are installed (see below)
- Run with `--verbose` for debug output

## Debian/Ubuntu Package Issues

### dpkg dependency errors
```bash
sudo dpkg -i aurynk_*.deb
sudo apt-get install -f  # Fixes missing dependencies
```

### Missing Python modules (gi, adw, etc)
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### XDG environment variable errors
Ensure XDG vars are set:
```bash
export XDG_DATA_HOME="$HOME/.local/share"
export XDG_CONFIG_HOME="$HOME/.config"
export XDG_CACHE_HOME="$HOME/.cache"
```

## Common Runtime Issues

### "ADB not found" / "scrcpy not found"
Aurynk requires external tools:
```bash
# Ubuntu/Debian/Mint
sudo apt install android-tools-adb scrcpy

# Fedora/RHEL
sudo dnf install android-tools scrcpy

# Arch/Manjaro
sudo pacman -S android-tools scrcpy

# openSUSE
sudo zypper install android-tools scrcpy
```

### Device won't pair / ADB errors
- Enable **Wireless Debugging** on Android (Settings → Developer Options)
- Both devices on **same WiFi network**
- Try restarting Aurynk and re-pairing
- Check `adb devices` shows your device

### Screen mirroring doesn't work
- Install `scrcpy` (see above)
- Ensure USB debugging is enabled on device
- Some devices need **USB debugging (Security settings)** enabled

## Build Issues (CI/CD)

### GitHub Actions: "No space left on device"
- Self-hosted runners need disk space
- Use `actions/cache` for `~/.cache/meson` between runs (optional)

### Meson: "Program 'appstream-util' not found"
```bash
sudo apt install appstream
```

### Meson: "Program 'desktop-file-validate' not found"
```bash
sudo apt install desktop-file-utils
```

### debuild: "Source format '3.0 (quilt)' not supported"
Ensure `debian/source/format` contains `3.0 (quilt)`.

### Python bytecode compilation errors
In `debian/rules`:
```makefile
override_dh_python3:
	dh_python3 --no-compile
```

## Distribution-Specific Notes

### Ubuntu 22.04
- `libadwaita-1` in universe repository
- `python3-qrcode` may need `pip install --break-system-packages qrcode`

### Ubuntu 24.04+
- All dependencies in main/universe
- `python3.12` default

### Debian 12 (Bookworm)
- `libadwaita-1` in backports
- `python3-qrcode` may need manual install

### Fedora 39/40
- All dependencies in main repos
- Use `dnf install ./aurynk.rpm` for auto-deps

### Arch/Manjaro
- Rolling, always latest deps
- `makepkg` builds clean package

### openSUSE Tumbleweed/Leap
- Use `alien --to-rpm` then `zypper in ./aurynk.rpm`

## Reporting Issues

If you encounter a packaging issue:
1. Check this file first
2. Run with verbose output: `./aurynk-x86_64.AppImage --verbose`
3. Check `~/.local/share/aurynk/logs/`
4. Open issue at https://github.com/TheRealFame/Aurynk-Packaged/issues

Include:
- Distro & version
- Package format used
- Error message
- `ldd usr/bin/aurynk` output (for missing libs)