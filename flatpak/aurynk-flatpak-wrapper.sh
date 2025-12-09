#!/bin/bash
# Flatpak wrapper script for Aurynk
# Automatically starts the udev proxy helper in the background on the host

set -e

# Check if udev proxy helper is already running
SOCKET_PATH="${XDG_RUNTIME_DIR}/aurynk-udev.sock"

# Use host's real home directory (accessible via flatpak-spawn)
# Inside Flatpak, $HOME is /var/home/username, but on host it's /home/username
HOST_HOME=$(flatpak-spawn --host bash -c 'echo $HOME' 2>/dev/null || echo "$HOME")
HELPER_DIR="${HOST_HOME}/.local/share/aurynk"
HOST_HELPER_PATH="${HELPER_DIR}/aurynk_udev_proxy.py"

if [ ! -S "$SOCKET_PATH" ]; then
    # Socket doesn't exist, try to start the helper
    if command -v flatpak-spawn >/dev/null 2>&1; then
        # Create helper directory on host and copy the script there
        flatpak-spawn --host mkdir -p "${HELPER_DIR}"
        flatpak-spawn --host cp /app/bin/aurynk_udev_proxy.py "${HOST_HELPER_PATH}" 2>/dev/null || {
            # Fallback: use cat to copy if cp doesn't work
            cat /app/bin/aurynk_udev_proxy.py | flatpak-spawn --host tee "${HOST_HELPER_PATH}" >/dev/null
        }
        flatpak-spawn --host chmod +x "${HOST_HELPER_PATH}"
        
        # Start the helper on the host using flatpak-spawn
        flatpak-spawn --host python3 "${HOST_HELPER_PATH}" >/dev/null 2>&1 &
        
        # Wait a moment for socket to be created
        for i in {1..15}; do
            if [ -S "$SOCKET_PATH" ]; then
                break
            fi
            sleep 0.3
        done
    fi
fi

# Launch the main application
exec python3 -m aurynk "$@"
