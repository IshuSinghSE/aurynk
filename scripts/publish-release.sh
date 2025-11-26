#!/bin/bash
set -e

# Usage: ./scripts/publish-release.sh
# Example: ./scripts/publish-release.sh

# Parse version from pyproject.toml (requires toml Python package)
NEW_VERSION=$(python3 -c "import toml; print(toml.load('pyproject.toml')['project']['new_version'])")
echo "Detected new_version: $NEW_VERSION"

# Extract latest changelog section for GitHub release notes
CHANGELOG_NOTES=$(awk '/^## \[/{if (found) exit} /\['"$NEW_VERSION"'\]/{found=1; print; next} found' CHANGELOG.md | awk 'NR>1')
if [ -z "$CHANGELOG_NOTES" ]; then
    CHANGELOG_NOTES="See CHANGELOG.md for details."
fi

# Update new_version in aurynk/__init__.py
echo "Updating aurynk/__init__.py new_version to $NEW_VERSION..."
sed -i "s/^__new_version__ = \".*\"/__new_version__ = \"$NEW_VERSION\"/" aurynk/__init__.py

# Update new_version in snapcraft.yaml
echo "Updating snapcraft.yaml new_version to $NEW_VERSION..."
sed -i "s/^new_version: .*/new_version: '$NEW_VERSION'/" snapcraft.yaml

# Update new_version in meson.build
echo "Updating meson.build new_version to $NEW_VERSION..."
sed -i "s/^new_version: *'[^']*'/new_version: '$NEW_VERSION'/" meson.build

echo "✅ New_version updated to $NEW_VERSION in all relevant files."

git add aurynk/__init__.py snapcraft.yaml meson.build
git commit -m "chore: bump new_version to v$NEW_VERSION"
git tag "v$NEW_VERSION"
git push origin HEAD --tags

echo "🚀 Creating GitHub release for v$NEW_VERSION..."
if command -v gh >/dev/null 2>&1; then
    gh release create "v$NEW_VERSION" --title "v$NEW_VERSION" --notes "$CHANGELOG_NOTES"
    echo "✅ GitHub release created."
else
    echo "⚠️  GitHub CLI (gh) not found. Please create the release manually."
fi
