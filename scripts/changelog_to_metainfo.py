#!/usr/bin/env python3
"""
Sync CHANGELOG.md to metainfo.xml <releases> section for Flathub/AppStream.
Usage: python3 changelog_to_metainfo.py <CHANGELOG.md> <metainfo.xml>
"""

import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET


def markdown_to_html(text):
    # Replace **bold** with <b>bold</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    # Replace *italic* with <i>italic</i> (avoid matching inside bold)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    return text


if len(sys.argv) != 3:
    print("Usage: python3 changelog_to_metainfo.py <CHANGELOG.md> <metainfo.xml>")
    sys.exit(1)

changelog_path = Path(sys.argv[1])
metainfo_path = Path(sys.argv[2])

changelog = changelog_path.read_text(encoding="utf-8")

# Parse all releases from changelog
release_re = re.compile(r"^## \[(.*?)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)

releases = []
for match in release_re.finditer(changelog):
    version, date = match.groups()
    start = match.end()
    next_match = release_re.search(changelog, start)
    end = next_match.start() if next_match else len(changelog)
    body = changelog[start:end].strip()
    lines = [line.rstrip() for line in body.splitlines() if line.strip()]
    # Find first unbulleted, non-header line as summary
    summary = None
    section_bullets = []  # List of (section, [bullets])
    current_section = None
    current_bullets = []
    section_re = re.compile(r"^###\s+(.+)$")
    for line in lines:
        if summary is None and not line.startswith("-") and not line.startswith("#"):
            summary = markdown_to_html(line.strip())
            continue
        section_match = section_re.match(line)
        if section_match:
            # Save previous section
            if current_section and current_bullets:
                section_bullets.append((current_section, current_bullets))
            current_section = section_match.group(1).strip()
            current_bullets = []
        elif line.startswith("-") and current_section:
            current_bullets.append(markdown_to_html(line[1:].strip()))
    # Save last section
    if current_section and current_bullets:
        section_bullets.append((current_section, current_bullets))
    desc_lines = []
    if summary:
        desc_lines.append(f"<p>{summary}</p>")
    for section, bullets in section_bullets:
        desc_lines.append(f"<p><b>{section}</b></p>")
        desc_lines.append("<ul>")
        for b in bullets:
            desc_lines.append(f"  <li>{b}</li>")
        desc_lines.append("</ul>")
    # Fallback: if no desc_lines and body:
    if not desc_lines and body:
        desc_lines.append(f"<p>{markdown_to_html(body)}</p>")
    releases.append({"version": version, "date": date, "desc": "\n        ".join(desc_lines)})

# Parse metainfo.xml and replace <releases>
tree = ET.parse(metainfo_path)
root = tree.getroot()
releases_el = root.find("releases")
if releases_el is None:
    releases_el = ET.SubElement(root, "releases")
else:
    releases_el.clear()

for rel in releases:
    rel_el = ET.SubElement(releases_el, "release", version=rel["version"], date=rel["date"])
    desc_el = ET.SubElement(rel_el, "description")
    # Insert as raw XML (ElementTree doesn't support this directly, so we use a hack)
    desc_xml = ET.fromstring(f"<desc>{rel['desc']}</desc>")
    for child in desc_xml:
        desc_el.append(child)

# Write back, pretty-print
ET.indent(tree, space="  ")
tree.write(metainfo_path, encoding="utf-8", xml_declaration=True)
print(f"Updated <releases> in {metainfo_path} from {changelog_path}")
