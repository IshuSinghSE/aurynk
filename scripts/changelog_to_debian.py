#!/usr/bin/env python3
"""
Syncs your Markdown CHANGELOG.md to debian/changelog in Debian format.
- Uses the latest release from CHANGELOG.md as the top entry.
- Converts Markdown bullets to indented lines.
- Converts **bold** and *italic* to plain text.
- Appends the maintainer and date line at the end.

Usage:
    python3 changelog_to_debian_changelog.py CHANGELOG.md debian/changelog
"""

import re
import sys
from datetime import datetime
from pathlib import Path

if len(sys.argv) != 3:
    print("Usage: python3 changelog_to_debian_changelog.py <CHANGELOG.md> <debian/changelog>")
    sys.exit(1)

changelog_path = Path(sys.argv[1])
debian_changelog_path = Path(sys.argv[2])

changelog = changelog_path.read_text(encoding="utf-8")


# Parse all releases from changelog
release_re = re.compile(r"^## \[(.*?)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)
matches = list(release_re.finditer(changelog))
if not matches:
    print("No release found in CHANGELOG.md")
    sys.exit(1)

# Read existing changelog and map (version, date) to footer
if debian_changelog_path.exists():
    old = debian_changelog_path.read_text(encoding="utf-8")
else:
    old = ""
footer_re = re.compile(
    r"^aurynk \(([^)]+)\) [^;]+; urgency=medium.*?^ -- (.*?)  (.*?)$", re.MULTILINE | re.DOTALL
)
old_footers = {
    (m.group(1), m.group(3)[:10]): (m.group(2), m.group(3)) for m in footer_re.finditer(old)
}

entries = []
for i, match in enumerate(matches):
    version, date = match.groups()
    start = match.end()
    end = matches[i + 1].start() if i + 1 < len(matches) else len(changelog)
    body = changelog[start:end].strip()
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    plain_lines = []
    for line in lines:
        # Remove Markdown bold/italic
        line = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
        line = re.sub(r"\*(.+?)\*", r"\1", line)
        # Convert bullets to indented lines
        if line.startswith("-"):
            plain_lines.append(f"  * {line[1:].strip()}")
        elif not line.startswith("#"):
            plain_lines.append(f"  {line.strip()}")
    package_name = "aurynk"
    suite = "noble"
    version_str = f"{package_name} ({version}) {suite}; urgency=medium"
    # Use old footer if available, else generate new
    if (version, date) in old_footers:
        maint, date_str = old_footers[(version, date)]
        footer = f" -- {maint}  {date_str}"
    else:
        maint = "Ishu Singh <ishu.111636@yahoo.com>"
        date_str = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z +0530")
        footer = f" -- {maint}  {date_str}"
    entry = f"{version_str}\n" + "\n".join(plain_lines) + f"\n\n{footer}\n\n"
    entries.append(entry)

# Write all entries
with debian_changelog_path.open("w", encoding="utf-8") as f:
    f.writelines(entries)

print(
    f"Updated {debian_changelog_path} with all releases from {changelog_path}, preserving old footers where possible."
)
