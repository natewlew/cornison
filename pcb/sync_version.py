#!/usr/bin/env python3
"""
Copy the board version from VERSION (repo root) into every file that
carries it, or check that they all agree.

VERSION is the one place to bump it. KiCad can't read an outside file, so
the title blocks hold a copy: the PCB's is what the silkscreen label
("Cornison v${REVISION}") reads. The FR4 plates carry the same number
(a plate for that PCB revision); make_fr4_plate.py reads VERSION itself
when it regenerates them, and this script updates them in place so a bump
doesn't need a full plate rebuild.

  ./build.sh version           write VERSION into every file
  ./build.sh version --check   exit 1 if any file disagrees (e.g. after
                               the revision was changed in KiCad's Page
                               Settings instead of in VERSION)

Plain python3, no KiCad needed: each edit is one field in a text file.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_version():
    v = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+(\.\d+)*", v):
        raise SystemExit(f"VERSION: expected something like 1.1, got {v!r}")
    return v


def title_rev(path, version, write):
    """Title-block revision of a .kicad_pcb / .kicad_sch file."""
    text = path.read_text()
    start = text.find("(title_block")
    end = text.find("\n\t)", start)
    m = re.compile(r'\(rev "([^"]*)"\)').search(text, start, end) if start >= 0 else None
    if not m:
        raise SystemExit(f"{path.relative_to(ROOT)}: no (rev ...) in its title block")
    if m.group(1) != version and write:
        path.write_text(text[: m.start(1)] + version + text[m.end(1) :])
    return m.group(1)


def archive_name(path, template, version, write):
    """fabrication-toolkit's ARCHIVE_NAME: the name of the zip it exports."""
    text = path.read_text()
    opts = json.loads(text)
    old, new = opts["ARCHIVE_NAME"], template.format(version=version)
    if old != new and write:
        opts["ARCHIVE_NAME"] = new
        # the plugin writes one line, ", " / ": " separators, no trailing newline
        path.write_text(json.dumps(opts) + ("\n" if text.endswith("\n") else ""))
    return old, new


def main():
    write = "--check" not in sys.argv[1:]
    version = read_version()
    stale = []

    for rel in ("pcb/cornison.kicad_pcb", "pcb/cornison.kicad_sch",
                "case/plate-fr4-left/plate-fr4-left.kicad_pcb",
                "case/plate-fr4-right/plate-fr4-right.kicad_pcb"):
        old = title_rev(ROOT / rel, version, write)
        if old != version:
            stale.append(f"{rel}: title block rev {old}")

    for rel, template in (
        ("pcb/fabrication-toolkit-options.json", "cornison_v{version}"),
        ("case/plate-fr4-left/fabrication-toolkit-options.json", "cornison_fr4_plate_left_v{version}"),
        ("case/plate-fr4-right/fabrication-toolkit-options.json", "cornison_fr4_plate_right_v{version}"),
    ):
        old, new = archive_name(ROOT / rel, template, version, write)
        if old != new:
            stale.append(f"{rel}: ARCHIVE_NAME {old} (want {new})")

    if not stale:
        print(f"version {version}: every file agrees")
    elif write:
        print(f"version {version}: updated")
        for s in stale:
            print("  " + s)
    else:
        print(f"version {version} (from VERSION) doesn't match:", file=sys.stderr)
        for s in stale:
            print("  " + s, file=sys.stderr)
        print("run ./build.sh version to update them (or fix VERSION)", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
