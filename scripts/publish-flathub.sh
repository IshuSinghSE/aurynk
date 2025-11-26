#!/bin/bash
set -e

# Usage: ./scripts/publish-flathub.sh <version> <path-to-flathub-fork>
# Example: ./scripts/publish-flathub.sh v1.0.4 ../flathub

VERSION="$1"
FLATHUB_DIR="$2"
MANIFEST_SRC="flatpak/io.github.IshuSinghSE.aurynk.yml"
MANIFEST_DEST="$FLATHUB_DIR/io.github.IshuSinghSE.aurynk.yml"

if [ -z "$VERSION" ] || [ -z "$FLATHUB_DIR" ]; then
    echo "Usage: $0 <version> <path-to-flathub-fork>"
    exit 1
fi

echo "🚀 Preparing Flathub release for version $VERSION..."

# 1. Calculate SHA256 of the release tarball
ver="${VERSION#v}"
echo "🔄 Updating aurynk/__init__.py to version $ver..."
sed -i "s/^__version__ = \".*\"/__version__ = \"$ver\"/" aurynk/__init__.py

TARBALL_URL="https://github.com/IshuSinghSE/aurynk/releases/download/${VERSION}/aurynk-${VERSION#v}.tar.gz"
echo "📥 Downloading tarball to calculate SHA256..."
wget -q -O /tmp/aurynk.tar.gz "$TARBALL_URL"
SHA256=$(sha256sum /tmp/aurynk.tar.gz | awk '{print $1}')
echo "✅ SHA256: $SHA256"

# 2. define the blocks we want to inject
# The 'shared-modules' block that replaces all your manual Ayatana/Intltool builds
FLATHUB_MODULES='  # Use flathub shared-modules for Ayatana AppIndicator
  - shared-modules/libayatana-appindicator/libayatana-appindicator-gtk3.json'

# The 'scrcpy' block is already clean in your local file? 
# If not, we can force the "clean" hybrid block here.
# For now, let's assume your local file uses the "Complex Shell Script" and we want the "Clean Hybrid" one.
FLATHUB_SCRCPY='  # scrcpy - hybrid build: native client + prebuilt server
  - name: scrcpy
    buildsystem: meson
    config-opts:
      - -Dprebuilt_server=/app/share/scrcpy/scrcpy-server
      - -Dcompile_server=false
      - -Db_lto=true
      - -Dbuildtype=release
    sources:
      - type: archive
        url: https://github.com/Genymobile/scrcpy/archive/refs/tags/v3.3.3.tar.gz
        sha256: 87fcd360a6bb6ca070ffd217bd33b33fb808b0a1572b464da51dde3fd3f6f60e
      - type: file
        url: https://github.com/Genymobile/scrcpy/releases/download/v3.3.3/scrcpy-server-v3.3.3
        sha256: 7e70323ba7f259649dd4acce97ac4fefbae8102b2c6d91e2e7be613fd5354be0
        dest-filename: scrcpy-server
        dest: share/scrcpy'

# The 'aurynk' source block (Archive instead of Dir)
FLATHUB_SOURCE="      - type: archive
        url: $TARBALL_URL
        sha256: $SHA256"

# 3. Perform the transformation
echo "🔄 Transforming manifest..."

# Use python helper to parse and transform the YAML structure
python3 -c "
import sys

src_file = '$MANIFEST_SRC'
dest_file = '$MANIFEST_DEST'
version = '$VERSION'
tarball_url = '$TARBALL_URL'
sha256 = '$SHA256'

with open(src_file, 'r') as f:
    lines = f.readlines()

output = []

# Definitions
ayatana_modules = {'intltool', 'libdbusmenu', 'ayatana-ido', 'libayatana-indicator', 'libayatana-appindicator','scrcpy-source'}
shared_ayatana_block = [
    '  # Use flathub shared-modules for Ayatana AppIndicator\n',
    '  - shared-modules/libayatana-appindicator/libayatana-appindicator-gtk3.json\n',
    '\n'
]
scrcpy_block = [
    '  # scrcpy - hybrid build: native client + prebuilt server\n',
    '  - name: scrcpy\n',
    '    buildsystem: meson\n',
    '    config-opts:\n',
    '      - -Dprebuilt_server=/app/share/scrcpy/scrcpy-server\n',
    '      - -Dcompile_server=false\n',
    '      - -Db_lto=true\n',
    '      - -Dbuildtype=release\n',
    '    sources:\n',
    '      - type: archive\n',
    '        url: https://github.com/Genymobile/scrcpy/archive/refs/tags/v3.3.3.tar.gz\n',
    '        sha256: 87fcd360a6bb6ca070ffd217bd33b33fb808b0a1572b464da51dde3fd3f6f60e\n',
    '      - type: file\n',
    '        url: https://github.com/Genymobile/scrcpy/releases/download/v3.3.3/scrcpy-server-v3.3.3\n',
    '        sha256: 7e70323ba7f259649dd4acce97ac4fefbae8102b2c6d91e2e7be613fd5354be0\n',
    '        dest-filename: scrcpy-server\n',
    '        dest: /app/share/scrcpy\n',
    '\n'
]
aurynk_block = [
    '  # Main application\n',
    '  - name: aurynk\n',
    '    buildsystem: meson\n',
    '    sources:\n',
    '      - type: archive\n',
    f'        url: {tarball_url}\n',
    f'        sha256: {sha256}\n',
    f'        strip-components: 0\n'
]

ayatana_replaced = False

i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()
    
    # Remove specific comment
    if stripped == '# Build Ayatana stack manually since CI clone skips submodules':
        i += 1
        continue

    # Check for module start
    if stripped.startswith('- name:'):
        name = stripped.split(':')[1].strip()
        
        if name in ayatana_modules:
            if not ayatana_replaced:
                output.extend(shared_ayatana_block)
                ayatana_replaced = True
            # Skip this module
            indent = len(line) - len(line.lstrip())
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                # End of module is when we hit a line with same indent starting with '-' or lower indent
                if next_line.strip() and next_indent <= indent:
                     if next_indent < indent or next_line.strip().startswith('-'):
                         break
                i += 1
            continue
            
        elif name == 'scrcpy':
            output.extend(scrcpy_block)
            indent = len(line) - len(line.lstrip())
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_line.strip() and next_indent <= indent:
                     if next_indent < indent or next_line.strip().startswith('-'):
                         break
                i += 1
            continue

        elif name == 'aurynk':
            output.extend(aurynk_block)
            indent = len(line) - len(line.lstrip())
            i += 1
            while i < len(lines):
                next_line = lines[i]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_line.strip() and next_indent <= indent:
                     if next_indent < indent or next_line.strip().startswith('-'):
                         break
                i += 1
            continue

    output.append(line)
    i += 1

with open(dest_file, 'w') as f:
    f.writelines(output)
"

echo "✅ Manifest created at $MANIFEST_DEST"
echo "   Now go to $FLATHUB_DIR, commit, and push!"