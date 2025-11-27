# Contributing to Aurynk

Thank you for your interest in contributing to Aurynk! This document provides all the technical information developers need to contribute to the project.

## Development Setup

### Requirements

**Runtime Dependencies**

- Python 3.11 or newer
- GTK 4
- libadwaita 1.0 or newer
- PyGObject
- Android Debug Bridge (adb)

**Build Dependencies**

- Meson (>= 0.59.0)
- Ninja
- GLib development files
- GTK4 development files

### Setting up the Environment

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/IshuSinghSE/aurynk.git
    cd aurynk
    ```

2.  **Install system dependencies:**

    === "Ubuntu/Debian"
        ```bash
        sudo apt install python3-dev python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 \
                         android-tools-adb meson ninja-build
        ```

    === "Fedora"
        ```bash
        sudo dnf install python3-devel python3-gobject gtk4-devel libadwaita-devel \
                         android-tools meson ninja-build
        ```

    === "Arch"
        ```bash
        sudo pacman -S python python-gobject gtk4 libadwaita android-tools meson ninja
        ```

3.  **Install Python dependencies:**
    ```bash
    # Create virtual environment (recommended)
    python -m venv .venv
    source .venv/bin/activate  # or `.venv/bin/activate.fish` for Fish shell

    # Install project with dev dependencies
    pip install -e ".[dev]"
    ```

4.  **Compile GResources:**
    ```bash
    glib-compile-resources --sourcedir=data data/io.github.IshuSinghSE.aurynk.gresource.xml \
        --target=data/io.github.IshuSinghSE.aurynk.gresource
    ```

5.  **Run the application:**
    ```bash
    python -m aurynk
    ```

## Submitting Changes

### Pull Request Process

1.  **Fork the repository** on GitHub.
2.  **Create a feature branch** from `main`.
3.  **Make your changes** following the code style guidelines.
4.  **Test your changes** thoroughly.
5.  **Commit** with descriptive messages.
6.  **Push** to your fork and create a Pull Request.

### Code Style

This project uses `ruff` for linting and formatting.

```bash
# Check code style
ruff check .

# Format code
ruff format .
```

## Packaging

The project supports various packaging formats, including Flatpak, Debian, and Snap. Check the `flatpak/` and `debian/` directories for manifest files.
