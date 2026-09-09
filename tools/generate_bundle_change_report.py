#!/usr/bin/env python3

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "notebook_bundle"
CURRENT = BUNDLE / "BUNDLE_MANIFEST.json"
STATE_DIR = ROOT / ".continuity"
PREVIOUS = STATE_DIR / "last_bundle_manifest.json"

BUNDLE_PREVIOUS = BUNDLE / "PREVIOUS_BUNDLE_MANIFEST.json"
REPORT_JSON = BUNDLE / "CHANGE_REPORT.json"
REPORT_MD = BUNDLE / "CHANGE_REPORT.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def file_map(manifest: dict) -> dict[str, dict]:
    return {
        entry["name"]: entry
        for entry in manifest.get("files", [])
        if isinstance(entry, dict) and entry.get("name")
    }


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    if not CURRENT.is_file():
        print(f"ERROR: missing current manifest: {CURRENT}")
        print("Run tools/validate_notebook_bundle.py first.")
        return 1

    current_manifest = load_json(CURRENT)
    current_files = file_map(current_manifest)

    first_run = not PREVIOUS.is_file()

    if first_run:
        previous_manifest = {
            "generated_at_utc": None,
            "files": [],
        }
    else:
        previous_manifest = load_json(PREVIOUS)

    previous_files = file_map(previous_manifest)

    added = sorted(set(current_files) - set(previous_files))
    removed = sorted(set(previous_files) - set(current_files))

    modified = sorted(
        name
        for name in set(current_files).intersection(previous_files)
        if current_files[name].get("sha256")
        != previous_files[name].get("sha256")
    )

    unchanged = sorted(
        name
        for name in set(current_files).intersection(previous_files)
        if current_files[name].get("sha256")
        == previous_files[name].get("sha256")
    )

    changes = []

    for name in added:
        changes.append(
            {
                "name": name,
                "change": "added",
                "current_bytes": current_files[name].get("bytes"),
                "current_sha256": current_files[name].get("sha256"),
            }
        )

    for name in removed:
        changes.append(
            {
                "name": name,
                "change": "removed",
                "previous_bytes": previous_files[name].get("bytes"),
                "previous_sha256": previous_files[name].get("sha256"),
            }
        )

    for name in modified:
        changes.append(
            {
                "name": name,
                "change": "modified",
                "previous_bytes": previous_files[name].get("bytes"),
                "current_bytes": current_files[name].get("bytes"),
                "previous_sha256": previous_files[name].get("sha256"),
                "current_sha256": current_files[name].get("sha256"),
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()

    report = {
        "generated_at_utc": generated_at,
        "first_run": first_run,
        "previous_manifest_generated_at_utc": (
            previous_manifest.get("generated_at_utc")
        ),
        "current_manifest_generated_at_utc": (
            current_manifest.get("generated_at_utc")
        ),
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": len(unchanged),
        },
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "changes": changes,
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# Notebook Bundle Change Report",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- First recorded bundle: `{'YES' if first_run else 'NO'}`",
        f"- Added files: `{len(added)}`",
        f"- Removed files: `{len(removed)}`",
        f"- Modified files: `{len(modified)}`",
        f"- Unchanged files: `{len(unchanged)}`",
        "",
    ]

    if first_run:
        markdown.extend(
            [
                "## Baseline Created",
                "",
                "No previous manifest existed.",
                "This bundle becomes the comparison baseline.",
                "",
            ]
        )

    for title, names in [
        ("Added Files", added),
        ("Removed Files", removed),
        ("Modified Files", modified),
        ("Unchanged Files", unchanged),
    ]:
        markdown.extend([f"## {title}", ""])

        if names:
            markdown.extend(f"- `{name}`" for name in names)
        else:
            markdown.append("- None")

        markdown.append("")

    REPORT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    if PREVIOUS.is_file():
        shutil.copy2(PREVIOUS, BUNDLE_PREVIOUS)
    else:
        BUNDLE_PREVIOUS.write_text(
            json.dumps(previous_manifest, indent=2) + "\n",
            encoding="utf-8",
        )

    shutil.copy2(CURRENT, PREVIOUS)

    print("Bundle change report generated.")
    print(f"First run: {'YES' if first_run else 'NO'}")
    print(f"Added: {len(added)}")
    print(f"Removed: {len(removed)}")
    print(f"Modified: {len(modified)}")
    print(f"Unchanged: {len(unchanged)}")
    print(f"Report: {REPORT_MD}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
