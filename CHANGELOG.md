# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2025-11-26

A massive update with a complete settings overhaul, advanced mirroring controls, and many new features to give you full control over your experience.

### 🚀 New Features
- **Complete Settings Overhaul:** A new modern settings window with dedicated tabs for Application, Device, and Mirroring preferences.
- **Advanced Mirroring Controls:** Full control over bitrate, max FPS, video codec, audio sources, and recording options.
- **Instant Settings:** All changes are saved automatically and applied instantly.
- **Window Management:** Customize window size and position, with handy presets for mobile form factors. Added options for always on top, fullscreen, and borderless modes.
- **New Control Modes:** Added View-only mode and OTG support for using your PC's keyboard and mouse on the device.
- **Recording:** Easily record your mirroring session with customizable formats and save paths.
- **About Page:** A new section with app information and credits.

### 📈 Improvements
- **Improved Connectivity:** Device pairing and discovery are now faster and more reliable.
- **Better Performance:** Added advanced options for hardware acceleration and running without a window.
- **User Interface:** A completely refreshed and consistent user interface across the application.
- **Enhanced Stability:** Improved settings management, device monitoring, and tray icon integration.

## [1.0.5] - 2025-11-24

Critical bug fixes and improvements to enhance application stability and reliability, including a new logging system.

### 🐛 Bug Fixes
- Fixed an issue causing mirroring synchronization problems.
- Fixed a bug where the application would quit prematurely.
- Resolved issues with the tray menu synchronization.
- Fixed GPU permission issues for the Flatpak version.
- Added a centralized logging system for better debugging.

## [1.0.4] - 2025-11-23

A maintenance release with documentation updates.

### 📈 Improvements
- Updated the README with new screenshots.
- General documentation improvements.

## [1.0.3] - 2025-11-16

Under-the-hood improvements for better performance and modern platform support.

### ⚙️ Under the Hood
- Updated to the GNOME 49 runtime for better performance and stability.
- Switched to an inline Ayatana stack.
- Refreshed Flatpak and Debian build artifacts.

## [1.0.2] - 2025-11-20

Important bug fixes to improve reliability and prevent crashes.

### 🐛 Bug Fixes
- Fixed a crash (UnboundLocalError) when starting device mirroring.
- Ensured the main window and tray icon stay perfectly synchronized.
- Fixed an issue where the tray command listener couldn't be stopped.
- Added a PID fallback for better tray icon reliability.

## [0.1.0] - 2025-11-06

Initial release of Aurynk with device management, wireless pairing, low-latency mirroring, and screenshot support for Flatpak and Debian.