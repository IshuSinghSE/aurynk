#!/bin/bash
set -e

# Usage: ./scripts/publish-release.sh
# Example: ./scripts/publish-release.sh

# Parse version from pyproject.toml (requires toml Python package)
VERSION=$(python3 -c "import toml; print(toml.load('pyproject.toml')['project']['version'])")
echo "Detected version: $VERSION"

# Extract latest changelog section for GitHub release notes
CHANGELOG_NOTES=$(awk '/^## \[/{if (found) exit} /\['"$VERSION"'\]/{found=1; print; next} found' CHANGELOG.md | awk 'NR>1')
if [ -z "$CHANGELOG_NOTES" ]; then
    CHANGELOG_NOTES="See CHANGELOG.md for details."
fi

# Update version in aurynk/__init__.py
echo "Updating aurynk/__init__.py version to $VERSION..."
sed -i "s/^__version__ = \".*\"/__version__ = \"$VERSION\"/" aurynk/__init__.py

# Update version in snapcraft.yaml
echo "Updating snapcraft.yaml version to $VERSION..."
sed -i "s/^version: .*/version: '$VERSION'/" snapcraft.yaml

# Update version in meson.build
echo "Updating meson.build version to $VERSION..."
sed -i "s/^  version: '[^']*'/  version: '$VERSION'/" meson.build

echo "✅ Version updated to $VERSION in all relevant files."

git add aurynk/__init__.py snapcraft.yaml meson.build
git commit -m "chore: bump version to v$VERSION"
git tag "v$VERSION"
git push origin HEAD --tags

echo "🚀 Creating GitHub release for v$VERSION..."
if command -v gh >/dev/null 2>&1; then
    gh release create "v$VERSION" --title "v$VERSION" --notes "$CHANGELOG_NOTES"
    echo "✅ GitHub release created."
else
    echo "⚠️  GitHub CLI (gh) not found. Please create the release manually."
fi
