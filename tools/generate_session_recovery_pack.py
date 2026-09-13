#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "notebook_bundle"

OUTPUT_JSON = BUNDLE / "SESSION_START.json"
OUTPUT_MD = BUNDLE / "SESSION_START.md"

CHANGE_REPORT = BUNDLE / "CHANGE_REPORT.json"
BUNDLE_VALIDATION = BUNDLE / "BUNDLE_VALIDATION.json"
CANONICAL_VALIDATION = BUNDLE / "CANONICAL_SYNC_VALIDATION.json"


def run(*args: str, allow_failure: bool = False) -> str:
    result = subprocess.run(
        list(args),
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(
            f"Command failed: {' '.join(args)}\n"
            f"{result.stderr.strip()}"
        )

    output = result.stdout.strip()

    if not output and result.stderr.strip():
        return result.stderr.strip()

    return output


def load_optional_json(path: Path) -> dict | None:
    if not path.is_file():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def classify_status_line(line: str) -> str:
    if line.startswith("??"):
        return "untracked"

    code = line[:2]

    if "D" in code:
        return "deleted"

    if "A" in code:
        return "added"

    if "R" in code:
        return "renamed"

    if "M" in code:
        return "modified"

    return "other"


def main() -> int:
    BUNDLE.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()

    branch = run("git", "branch", "--show-current")
    head = run("git", "rev-parse", "HEAD")
    short_head = run("git", "rev-parse", "--short", "HEAD")
    recent_commits = run(
        "git",
        "log",
        "--oneline",
        "--decorate",
        "-10",
    )

    status_output = run(
        "git",
        "status",
        "--short",
        "--branch",
    )

    diff_stat = run(
        "git",
        "diff",
        "--stat",
        allow_failure=True,
    )

    status_lines = status_output.splitlines()
    change_lines = [
        line
        for line in status_lines
        if line and not line.startswith("##")
    ]

    categories = {
        "modified": [],
        "deleted": [],
        "added": [],
        "renamed": [],
        "untracked": [],
        "other": [],
    }

    for line in change_lines:
        category = classify_status_line(line)
        categories[category].append(line)

    change_report = load_optional_json(CHANGE_REPORT)
    bundle_validation = load_optional_json(BUNDLE_VALIDATION)
    canonical_validation = load_optional_json(CANONICAL_VALIDATION)

    recovery = {
        "generated_at_utc": generated_at,
        "repository": {
            "root": str(ROOT),
            "branch": branch,
            "head": head,
            "short_head": short_head,
        },
        "working_tree": {
            "status": status_output,
            "diff_stat": diff_stat,
            "counts": {
                key: len(value)
                for key, value in categories.items()
            },
            "categories": categories,
        },
        "continuity": {
            "bundle_validation_passed": (
                bundle_validation.get("passed")
                if bundle_validation
                else None
            ),
            "canonical_sync_passed": (
                canonical_validation.get("passed")
                if canonical_validation
                else None
            ),
            "bundle_change_summary": (
                change_report.get("summary")
                if change_report
                else None
            ),
        },
        "recent_commits": recent_commits.splitlines(),
        "first_command": (
            "cd /home/deeoriginalone/fantasy-intelligence "
            "&& source venv/bin/activate "
            "&& git status --short --branch"
        ),
    }

    OUTPUT_JSON.write_text(
        json.dumps(recovery, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# Fantasy Intelligence Session Start",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Repository: `{ROOT}`",
        f"- Branch: `{branch}`",
        f"- HEAD: `{head}`",
        "",
        "## Continuity Status",
        "",
        (
            "- Notebook bundle validation: "
            f"`{bundle_validation.get('passed') if bundle_validation else 'NOT RUN'}`"
        ),
        (
            "- Canonical sync validation: "
            f"`{canonical_validation.get('passed') if canonical_validation else 'NOT RUN'}`"
        ),
        "",
    ]

    if change_report:
        summary = change_report.get("summary", {})

        markdown.extend(
            [
                "## Bundle Changes",
                "",
                f"- Added: `{summary.get('added', 0)}`",
                f"- Removed: `{summary.get('removed', 0)}`",
                f"- Modified: `{summary.get('modified', 0)}`",
                f"- Unchanged: `{summary.get('unchanged', 0)}`",
                "",
            ]
        )

    markdown.extend(
        [
            "## Working Tree Summary",
            "",
            f"- Modified: `{len(categories['modified'])}`",
            f"- Deleted: `{len(categories['deleted'])}`",
            f"- Added: `{len(categories['added'])}`",
            f"- Renamed: `{len(categories['renamed'])}`",
            f"- Untracked: `{len(categories['untracked'])}`",
            f"- Other: `{len(categories['other'])}`",
            "",
        ]
    )

    for category in [
        "modified",
        "deleted",
        "added",
        "renamed",
        "untracked",
        "other",
    ]:
        entries = categories[category]

        if not entries:
            continue

        markdown.extend(
            [
                f"### {category.title()}",
                "",
                *[f"- `{entry}`" for entry in entries],
                "",
            ]
        )

    markdown.extend(
        [
            "## Recent Commits",
            "",
            "```text",
            recent_commits,
            "```",
            "",
            "## Diff Summary",
            "",
            "```text",
            diff_stat if diff_stat else "No unstaged diff summary.",
            "```",
            "",
            "## First Command",
            "",
            "```bash",
            recovery["first_command"],
            "```",
            "",
            "## Continuity Files",
            "",
            "- `BUNDLE_VALIDATION.md`",
            "- `CANONICAL_SYNC_VALIDATION.md`",
            "- `CHANGE_REPORT.md`",
            "- `REPOSITORY_CHECKPOINT.md`",
            "- `BUNDLE_MANIFEST.json`",
            "",
        ]
    )

    OUTPUT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print("Session recovery pack generated.")
    print(f"Branch: {branch}")
    print(f"HEAD: {head}")
    print(f"Markdown: {OUTPUT_MD}")
    print(f"JSON: {OUTPUT_JSON}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
