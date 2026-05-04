"""
Syncs your Markdown CHANGELOG.md to debian/changelog in Debian format.
- Uses the latest release from CHANGELOG.md as the top entry.
- Converts Markdown bullets to indented lines.
- Converts **bold** and *italic* to plain text.
- Footer timestamps use each release's date from CHANGELOG.md (YYYY-MM-DD).
- Preserves maintainer lines from the existing debian/changelog when the version matches.

Usage:
    python3 scripts/changelog_to_debian.py CHANGELOG.md debian/changelog
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if len(sys.argv) != 3:
    print("Usage: python3 scripts/changelog_to_debian.py <CHANGELOG.md> <debian/changelog>")
    sys.exit(1)

changelog_path = Path(sys.argv[1])
debian_changelog_path = Path(sys.argv[2])

DEFAULT_MAINTAINER = "Ishu Singh <ishu.111636@yahoo.com>"
# Used to turn CHANGELOG calendar dates into changelog timestamps (no wall-clock in markdown).
_DEBIAN_CHANGELOG_TZ = ZoneInfo("Asia/Kolkata")


def changelog_iso_to_debian_timestamp(iso_date: str) -> str:
    """Map YYYY-MM-DD from CHANGELOG.md to Debian changelog 'Date' field."""
    y, mo, d = map(int, iso_date.split("-"))
    dt = datetime(y, mo, d, 12, 0, 0, tzinfo=_DEBIAN_CHANGELOG_TZ)
    # e.g. Thu, 29 Jan 2026 12:00:00 +0530
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")


def parse_old_maintainers_by_version(text: str) -> dict[str, str]:
    """Return version -> 'Name <email>' from existing debian/changelog (timestamp ignored)."""
    out: dict[str, str] = {}
    if not text.strip():
        return out
    for block in re.split(r"\n(?=aurynk \()", text.strip()):
        vm = re.match(r"^aurynk \(([^)]+)\)", block)
        if not vm:
            continue
        footer = re.search(r"^ -- (.+?)  .+$", block, re.MULTILINE)
        if footer:
            out[vm.group(1)] = footer.group(1).strip()
    return out


changelog = changelog_path.read_text(encoding="utf-8")

# Parse all releases from changelog
release_re = re.compile(r"^## \[(.*?)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)
matches = list(release_re.finditer(changelog))
if not matches:
    print("No release found in CHANGELOG.md")
    sys.exit(1)

old_maintainers = parse_old_maintainers_by_version(
    debian_changelog_path.read_text(encoding="utf-8") if debian_changelog_path.exists() else ""
)

entries = []
for i, match in enumerate(matches):
    version, iso_date = match.groups()
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
    maint = old_maintainers.get(version, DEFAULT_MAINTAINER)
    date_str = changelog_iso_to_debian_timestamp(iso_date)
    footer = f" -- {maint}  {date_str}"
    entry = f"{version_str}\n" + "\n".join(plain_lines) + f"\n\n{footer}\n\n"
    entries.append(entry)

# Write all entries
with debian_changelog_path.open("w", encoding="utf-8") as f:
    f.writelines(entries)

print(
    f"Updated {debian_changelog_path} with all releases from {changelog_path} "
    f"(footer dates from CHANGELOG.md ISO dates; maintainer preserved per version when present)."
)
